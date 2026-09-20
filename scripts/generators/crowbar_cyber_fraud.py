#!/usr/bin/env python3
"""
Generate the "Alchemy" cybersecurity / fraud-detection hypergraph from the
`crowbar` source folder (two synthetic banking-fraud datasets, ~2M transactions).

    python scripts/generators/crowbar_cyber_fraud.py --source ~/Downloads/crowbar            # full load into the configured MongoDB
    python scripts/generators/crowbar_cyber_fraud.py --source ... --sample 20000 --db hgai_pilot   # pilot on a scratch database
    python scripts/generators/crowbar_cyber_fraud.py --source ... --dry-run                  # build everything, write nothing

The data is written straight to MongoDB with bulk inserts (a REST round trip per
document would take many hours), using exactly the document shape the engine
stores (hgai.core.engine.create_hypernode/create_hyperedge), the engine's own
hyperkey function, and the storage layer's indexes (so uniqueness is enforced).

Modelling rules (see the generation Note the run also writes):
  * Every entity is a hypernode; every attribute that is a plain data literal is a
    property (`attributes`) of that node; every attribute that references another
    entity is a hyperedge instead of a property.
  * Provenance lives in `attributes.provenance` on the hypergraph, every hypernode
    and every hyperedge.
  * Domain ontology (classes, relation types, SKOS concept schemes) and its axioms
    (owl:inverse-of / owl:symmetric / owl:transitive / skos:broaderTransitive /
    skos:narrowerTransitive) are ordinary hypernodes and hyperedges.
  * Hub-flavor hyperedges group all spokes of one relation for one hub (e.g. an
    account and every transaction it initiated), chunked at MAX_SPOKES per edge;
    each spoke is an independent (hub, spoke) fact (see hgai.core.inference).
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pymongo import MongoClient  # noqa: E402

from hgai.config import get_settings  # noqa: E402
from hgai.core.engine import generate_hyperkey  # noqa: E402
from hgai.models.hyperedge import HyperedgeInDB  # noqa: E402
from hgai.models.hypergraph import HypergraphCreate  # noqa: E402
from hgai.models.hypernode import HypernodeInDB  # noqa: E402

GENERATOR_VERSION = "1.0.0"
MAX_SPOKES = 250          # spokes per hub hyperedge (keeps each document a few KB)
BATCH = 5000
CREATED_BY = "admin"
AGENT = "Claude (Anthropic) via Claude Code"

FD = "fraud-detection"
SB = "synthetic-banking-txns"
SRC_FILES = {
    "account_profiles": (FD, "fraud-detection/account_profiles.csv"),
    "fraud_patterns": (FD, "fraud-detection/fraud_patterns.csv"),
    "network_edges": (FD, "fraud-detection/network_edges.csv"),
    "time_series_stats": (FD, "fraud-detection/time_series_stats.csv"),
    "transactions": (FD, "fraud-detection/transactions.csv"),
    "sb_transactions": (SB, "synthetic-banking-txns/fraud-detection-dataset.csv"),
}

# ─── helpers ──────────────────────────────────────────────────────────────────

def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def num(text):
    """CSV text -> int when it is an integral value ('49', '49.0'), otherwise float."""
    f = float(text)
    return int(f) if f == int(f) and re.fullmatch(r"-?\d+(\.0+)?", text) else f


def flag(text):
    return float(text) != 0


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path):
    with open(path, "rb") as fh:
        return sum(1 for _ in fh) - 1


def iso(ts_text):
    """'2023-02-21 08:02:38' -> '2023-02-21T08:02:38' (zone-less, as in the source)."""
    return ts_text.replace(" ", "T")


# ─── sink: bulk writer + statistics ───────────────────────────────────────────

class Sink:
    def __init__(self, db, graph_id, dry_run):
        self.graph_id = graph_id
        self.dry_run = dry_run
        self.nodes_col = None if dry_run else db["hypernodes"]
        self.edges_col = None if dry_run else db["hyperedges"]
        self.node_buf, self.edge_buf = [], []
        self.node_types, self.relations = Counter(), Counter()
        self.node_count = self.edge_count = 0
        self.member_slots = 0
        self.now = datetime.now(timezone.utc).replace(tzinfo=None)
        self.checked = set()          # types / relations whose first document was validated against the storage models
        self.known_relations = set()

    def node(self, id_, label, type_, attributes, provenance, description=None, tags=None,
             valid_from=None, valid_to=None):
        attributes = dict(attributes)
        attributes["provenance"] = provenance
        doc = {
            "id": id_, "label": label, "type": type_, "description": description,
            "attributes": attributes, "tags": tags or [], "status": "active",
            "valid_from": valid_from, "valid_to": valid_to, "media": [], "default_media_id": None,
            "hypergraph_id": self.graph_id, "system_created": self.now, "system_updated": self.now,
            "created_by": CREATED_BY, "version": 1,
            "mutations": [{"ts": self.now, "by": CREATED_BY, "mutation": "create",
                           "delta": [{"field": "label", "old": None, "new": label}]}],
        }
        if ("node", type_) not in self.checked:
            HypernodeInDB(**doc)                        # schema check on the first document of each type
            self.checked.add(("node", type_))
        self.node_types[type_] += 1
        self.node_count += 1
        self.node_buf.append(doc)
        if len(self.node_buf) >= BATCH:
            self.flush_nodes()

    def edge(self, id_, relation, members, label, attributes, provenance, flavor="hub", tags=None,
             description=None):
        attributes = dict(attributes)
        attributes["provenance"] = provenance
        member_docs = [{"node_id": m, "seq": i} for i, m in enumerate(members)]
        doc = {
            "id": id_, "relation": relation, "label": label, "flavor": flavor, "members": member_docs,
            "description": description, "attributes": attributes, "tags": tags or [], "status": "active",
            "valid_from": None, "valid_to": None, "skos_broader": [], "skos_narrower": [], "skos_related": [],
            "relation_node_id": relation if relation in self.known_relations else None, "media": [],
            "default_media_id": None, "hypergraph_id": self.graph_id,
            "hyperkey": generate_hyperkey(relation, members, self.graph_id),
            "system_created": self.now, "system_updated": self.now, "created_by": CREATED_BY, "version": 1,
            "mutations": [{"ts": self.now, "by": CREATED_BY, "mutation": "create",
                           "delta": [{"field": "relation", "old": None, "new": relation}]}],
        }
        if ("edge", relation) not in self.checked:
            HyperedgeInDB(**doc)
            self.checked.add(("edge", relation))
        self.relations[relation] += 1
        self.edge_count += 1
        self.member_slots += len(members)
        self.edge_buf.append(doc)
        if len(self.edge_buf) >= BATCH:
            self.flush_edges()

    def flush_nodes(self):
        if self.node_buf and not self.dry_run:
            self.nodes_col.insert_many(self.node_buf, ordered=False)
        self.node_buf = []

    def flush_edges(self):
        if self.edge_buf and not self.dry_run:
            self.edges_col.insert_many(self.edge_buf, ordered=False)
        self.edge_buf = []

    def flush(self):
        self.flush_nodes()
        self.flush_edges()


# ─── domain ontology (authored) ───────────────────────────────────────────────

# (id, label, description, parent class id or None)
CLASSES = [
    ("class:Entity", "Entity", "Anything represented as a hypernode in the fraud-detection domain.", None),
    ("class:Party", "Party", "A person or organisation that holds an account or initiates transactions.", "class:Entity"),
    ("class:Account", "Account", "A bank/card account whose profile is analysed for fraud risk (fraud-detection dataset).", "class:Party"),
    ("class:Customer", "Customer", "A bank customer identified in the synthetic banking dataset.", "class:Party"),
    ("class:Instrument", "Payment Instrument", "A means of paying: a card.", "class:Entity"),
    ("class:Card", "Card", "A payment card issued to a customer.", "class:Instrument"),
    ("class:DigitalIdentifier", "Digital Identifier", "A technical identifier that can link activity: a device or an IP address.", "class:Entity"),
    ("class:Device", "Device", "A device fingerprint used to originate transactions.", "class:DigitalIdentifier"),
    ("class:IPAddress", "IP Address", "A network address from which a transaction originated.", "class:DigitalIdentifier"),
    ("class:Merchant", "Merchant", "A payee that accepts payments.", "class:Party"),
    ("class:Event", "Event", "Something that happened at a point in time.", "class:Entity"),
    ("class:Transaction", "Transaction", "A payment, transfer or ATM event; the central event class for fraud analysis.", "class:Event"),
    ("class:Location", "Location", "A geographic place.", "class:Entity"),
    ("class:Region", "Region", "A grouping of countries (continent or world).", "class:Location"),
    ("class:Country", "Country", "A nation, identified by ISO 3166-1 alpha-2 code.", "class:Location"),
    ("class:City", "City", "A city as recorded for a merchant location.", "class:Location"),
    ("class:FraudRing", "Fraud Ring", "A group of accounts linked by shared attributes and investigated together.", "class:Entity"),
    ("class:Statistic", "Statistic", "An aggregate observation over a period of time.", "class:Entity"),
    ("class:TimeBucket", "Hourly Time Bucket", "One hour of aggregate transaction statistics.", "class:Statistic"),
    ("class:Concept", "Concept", "A SKOS concept: a category in a controlled vocabulary.", "class:Entity"),
    ("class:MerchantCategory", "Merchant Category", "A merchant category (with MCC code where the source provides one).", "class:Concept"),
    ("class:DeviceType", "Device / Channel Type", "The channel through which a transaction was made (mobile app, POS, ATM...).", "class:Concept"),
    ("class:AccountType", "Account Type", "The product type of an account (personal, business, premium).", "class:Concept"),
    ("class:FraudPattern", "Fraud Pattern / Type", "A fraud typology into which a fraudulent transaction is classified.", "class:Concept"),
    ("class:ConceptScheme", "Concept Scheme", "A SKOS concept scheme grouping related concepts.", "class:Entity"),
    ("class:Class", "Class", "An ontology class (this hypergraph's own schema).", "class:Entity"),
    ("class:RelationType", "Relation Type", "A relation used by hyperedges, with its semantic characteristics.", "class:Entity"),
]

# Relation types. characteristics: inverse (id), symmetric, transitive, broader (skos:broaderTransitive parent),
# domain / range (class ids).  Hub relations read "hub <relation> spoke".
RELATIONS = [
    # transaction structure (hub = the thing the transaction was made by / with / through)
    ("rel:initiated", "initiated", "The party (account or customer) started the transaction.", "rel:initiated-by", ["class:Party"], ["class:Transaction"], None),
    ("rel:initiated-by", "initiated by", "The transaction was started by the party.", "rel:initiated", ["class:Transaction"], ["class:Party"], None),
    ("rel:charged-card", "charged card", "The card was used for the transaction.", "rel:charged-via-card", ["class:Card"], ["class:Transaction"], None),
    ("rel:charged-via-card", "charged via card", "The transaction was made with the card.", "rel:charged-card", ["class:Transaction"], ["class:Card"], None),
    ("rel:originated-device", "originated device", "The device was the origin of the transaction.", "rel:originated-from-device", ["class:Device"], ["class:Transaction"], None),
    ("rel:originated-from-device", "originated from device", "The transaction came from the device.", "rel:originated-device", ["class:Transaction"], ["class:Device"], None),
    ("rel:originated-ip", "originated ip", "The IP address was the network origin of the transaction.", "rel:originated-from-ip", ["class:IPAddress"], ["class:Transaction"], None),
    ("rel:originated-from-ip", "originated from ip", "The transaction came from the IP address.", "rel:originated-ip", ["class:Transaction"], ["class:IPAddress"], None),
    ("rel:received-transaction", "received transaction", "The merchant was the payee of the transaction.", "rel:at-merchant", ["class:Merchant"], ["class:Transaction"], None),
    ("rel:at-merchant", "at merchant", "The transaction was paid to the merchant.", "rel:received-transaction", ["class:Transaction"], ["class:Merchant"], None),
    ("rel:categorizes", "categorizes", "The concept classifies the entity (generic).", "rel:categorized-as", ["class:Concept"], ["class:Entity"], None),
    ("rel:categorized-as", "categorized as", "The entity is classified by the concept (generic).", "rel:categorizes", ["class:Entity"], ["class:Concept"], None),
    ("rel:categorizes-transaction", "categorizes transaction", "The merchant category (or channel/fraud pattern/time bucket) classifies the transaction.", "rel:has-transaction-category", ["class:Concept", "class:TimeBucket"], ["class:Transaction"], "rel:categorizes"),
    ("rel:has-transaction-category", "has transaction category", "The transaction is classified by the category / channel / pattern.", "rel:categorizes-transaction", ["class:Transaction"], ["class:Concept", "class:TimeBucket"], "rel:categorized-as"),
    ("rel:categorizes-merchant", "categorizes merchant", "The merchant category classifies the merchant.", "rel:has-merchant-category", ["class:MerchantCategory"], ["class:Merchant"], "rel:categorizes"),
    ("rel:has-merchant-category", "has merchant category", "The merchant belongs to the category.", "rel:categorizes-merchant", ["class:Merchant"], ["class:MerchantCategory"], "rel:categorized-as"),
    ("rel:categorizes-account", "categorizes account", "The account type / home country classifies the account.", "rel:has-account-category", ["class:AccountType", "class:Country"], ["class:Account"], "rel:categorizes"),
    ("rel:has-account-category", "has account category", "The account has the account type / home country.", "rel:categorizes-account", ["class:Account"], ["class:AccountType", "class:Country"], "rel:categorized-as"),
    ("rel:typifies", "typifies", "The fraud pattern classifies the (fraudulent) transaction.", "rel:classified-as-fraud", ["class:FraudPattern"], ["class:Transaction"], "rel:categorizes"),
    ("rel:classified-as-fraud", "classified as fraud pattern", "The transaction is classified into the fraud pattern.", "rel:typifies", ["class:Transaction"], ["class:FraudPattern"], "rel:categorized-as"),
    ("rel:aggregates", "aggregates", "The hourly statistic summarises the transactions of its hour.", "rel:counted-in-bucket", ["class:TimeBucket"], ["class:Transaction"], None),
    ("rel:counted-in-bucket", "counted in bucket", "The transaction is counted in the hourly statistic.", "rel:aggregates", ["class:Transaction"], ["class:TimeBucket"], None),
    ("rel:location-of-transaction", "location of transaction", "The transaction took place at the location (country or city).", "rel:occurred-at-location", ["class:Location"], ["class:Transaction"], None),
    ("rel:occurred-at-location", "occurred at location", "The transaction took place at the location.", "rel:location-of-transaction", ["class:Transaction"], ["class:Location"], None),
    # ownership / usage
    ("rel:owns-card", "owns card", "The customer holds the card.", "rel:owned-by", ["class:Customer"], ["class:Card"], None),
    ("rel:owned-by", "owned by", "The card is held by the customer.", "rel:owns-card", ["class:Card"], ["class:Customer"], None),
    ("rel:uses-device", "uses device", "The customer was observed using the device.", "rel:used-by", ["class:Customer"], ["class:Device"], None),
    ("rel:used-by", "used by", "The device was observed in use by the customer.", "rel:uses-device", ["class:Device"], ["class:Customer"], None),
    ("rel:located-in", "located in", "The merchant operates at (was observed in) the city.", "rel:hosts-merchant", ["class:Merchant"], ["class:City"], None),
    ("rel:hosts-merchant", "hosts merchant", "The city is where the merchant was observed.", "rel:located-in", ["class:City"], ["class:Merchant"], None),
    # geography
    ("rel:contains", "contains", "The larger place contains the smaller one (world > region > country > city). Transitive.", "rel:part-of", ["class:Location"], ["class:Location"], None),
    ("rel:part-of", "part of", "The place is part of the larger place. Transitive.", "rel:contains", ["class:Location"], ["class:Location"], None),
    # links between parties (fraud networks)
    ("rel:linked-to", "linked to", "The parties are connected by some shared attribute. Symmetric and transitive: connectivity defines a network.", None, ["class:Party"], ["class:Party"], None),
    ("rel:shares-attribute-with", "shares attribute with", "The parties share an identifying attribute. Symmetric.", None, ["class:Party"], ["class:Party"], "rel:linked-to"),
    ("rel:shares-phone-with", "shares phone with", "The accounts share a phone number.", None, ["class:Account"], ["class:Account"], "rel:shares-attribute-with"),
    ("rel:shares-email-domain-with", "shares email domain with", "The accounts share an e-mail domain.", None, ["class:Account"], ["class:Account"], "rel:shares-attribute-with"),
    ("rel:shares-ip-address-with", "shares IP address with", "The parties were observed using the same IP address.", None, ["class:Party"], ["class:Party"], "rel:shares-attribute-with"),
    ("rel:shares-device-with", "shares device with", "The parties were observed using the same device.", None, ["class:Party"], ["class:Party"], "rel:shares-attribute-with"),
    ("rel:shares-card-with", "shares card with", "The customers were observed using the same card.", None, ["class:Customer"], ["class:Customer"], "rel:shares-attribute-with"),
    ("rel:has-ring-member", "has ring member", "The fraud ring includes the account.", "rel:member-of-ring", ["class:FraudRing"], ["class:Account"], None),
    ("rel:member-of-ring", "member of ring", "The account belongs to the fraud ring.", "rel:has-ring-member", ["class:Account"], ["class:FraudRing"], None),
    ("rel:has-link", "has link", "The fraud ring includes the link (a hyperedge) between two of its accounts.", None, ["class:FraudRing"], ["class:Entity"], None),
    # ontology / SKOS structure
    ("rel:subclass-of", "subclass of", "The class is a subclass of the other. Transitive.", "rel:superclass-of", ["class:Class"], ["class:Class"], None),
    ("rel:superclass-of", "superclass of", "The class is a superclass of the other. Transitive.", "rel:subclass-of", ["class:Class"], ["class:Class"], None),
    ("skos:broader", "broader", "SKOS: the concept has a more general concept. Transitive.", "skos:narrower", ["class:Concept"], ["class:Concept"], None),
    ("skos:narrower", "narrower", "SKOS: the concept has a more specific concept. Transitive.", "skos:broader", ["class:Concept"], ["class:Concept"], None),
    ("skos:exactMatch", "exact match", "SKOS: the concepts from different sources mean the same. Symmetric and transitive.", None, ["class:Concept"], ["class:Concept"], "skos:mappingRelation"),
    ("skos:closeMatch", "close match", "SKOS: the concepts are close enough to be used interchangeably in some contexts. Symmetric.", None, ["class:Concept"], ["class:Concept"], "skos:mappingRelation"),
    ("skos:mappingRelation", "mapping relation", "SKOS: generic link between concepts of different schemes. Symmetric.", None, ["class:Concept"], ["class:Concept"], None),
    ("skos:inScheme", "in scheme", "SKOS: the concept belongs to the concept scheme.", "rel:includes-concept", ["class:Concept"], ["class:ConceptScheme"], None),
    ("rel:includes-concept", "includes concept", "The concept scheme includes the concept.", "skos:inScheme", ["class:ConceptScheme"], ["class:Concept"], None),
    ("skos:hasTopConcept", "has top concept", "SKOS: the scheme's top-level concept.", "skos:topConceptOf", ["class:ConceptScheme"], ["class:Concept"], None),
    ("skos:topConceptOf", "top concept of", "SKOS: the concept is a top-level concept of the scheme.", "skos:hasTopConcept", ["class:Concept"], ["class:ConceptScheme"], None),
    ("rel:has-domain", "has domain", "Schema: the relation's subject class(es).", None, ["class:RelationType"], ["class:Class"], None),
    ("rel:has-range", "has range", "Schema: the relation's object class(es).", None, ["class:RelationType"], ["class:Class"], None),
]
SYMMETRIC = ["rel:linked-to", "rel:shares-attribute-with", "rel:shares-phone-with", "rel:shares-email-domain-with",
             "rel:shares-ip-address-with", "rel:shares-device-with", "rel:shares-card-with", "skos:exactMatch",
             "skos:closeMatch", "skos:mappingRelation"]
TRANSITIVE = ["rel:contains", "rel:part-of", "rel:linked-to", "rel:subclass-of", "rel:superclass-of",
              "skos:broader", "skos:narrower", "skos:exactMatch"]
# narrower -> broader relation hierarchy, spelled skos:broaderTransitive [narrower, broader] ...
BROADER_TRANSITIVE = [
    ("rel:shares-phone-with", "rel:shares-attribute-with"), ("rel:shares-email-domain-with", "rel:shares-attribute-with"),
    ("rel:shares-ip-address-with", "rel:shares-attribute-with"), ("rel:shares-device-with", "rel:shares-attribute-with"),
    ("rel:shares-card-with", "rel:shares-attribute-with"), ("rel:shares-attribute-with", "rel:linked-to"),
    ("skos:exactMatch", "skos:mappingRelation"), ("skos:closeMatch", "skos:mappingRelation"),
]
# ... and the mirror spelling skos:narrowerTransitive [broader, narrower]
NARROWER_TRANSITIVE = [
    ("rel:categorizes", "rel:categorizes-transaction"), ("rel:categorizes", "rel:categorizes-merchant"),
    ("rel:categorizes", "rel:categorizes-account"), ("rel:categorizes-transaction", "rel:typifies"),
    ("rel:categorized-as", "rel:has-transaction-category"), ("rel:categorized-as", "rel:has-merchant-category"),
    ("rel:categorized-as", "rel:has-account-category"), ("rel:has-transaction-category", "rel:classified-as-fraud"),
]

# ── SKOS concept schemes ──
SCHEMES = {
    "merchant-category": ("Merchant Categories", "Merchant categories used by both datasets, with authored groupings."),
    "fraud-typology": ("Fraud Typology", "Fraud patterns / types observed in the data with authored parent typologies."),
    "channel": ("Channels", "Device / channel types through which transactions are made."),
    "account-type": ("Account Types", "Account product types."),
}
# concept id -> (scheme, label, definition, broader ids, source-notation). Leaves are added from the data;
# groupings here are authored.
MCAT_GROUPS = {
    "mcat:retail-and-shopping": ("Retail and Shopping", "Purchases of goods, in store or online."),
    "mcat:food-and-dining": ("Food and Dining", "Groceries and prepared food."),
    "mcat:travel-and-hospitality": ("Travel and Hospitality", "Travel bookings and lodging."),
    "mcat:automotive-and-fuel": ("Automotive and Fuel", "Fuel and vehicle-related purchases."),
    "mcat:utilities-and-bills": ("Utilities and Bills", "Recurring utility payments."),
    "mcat:entertainment-and-leisure": ("Entertainment and Leisure", "Entertainment, gaming and gambling."),
    "mcat:health-and-wellness": ("Health and Wellness", "Pharmacy and health services."),
    "mcat:cash-and-cash-equivalents": ("Cash and Cash Equivalents", "Cash withdrawal, transfers and crypto — categories where value can be moved out of the banking system quickly, a common money-laundering concern."),
}
MCAT_ROOT = ("mcat:merchant-category", "Merchant Category", "Top concept of the merchant category scheme.")
# leaf label (as in the sources) -> (concept id, groupings, definition)
MCAT_LEAVES = {
    "grocery": ("mcat:grocery", ["mcat:food-and-dining", "mcat:retail-and-shopping"], "Supermarkets and grocery stores."),
    "restaurant": ("mcat:restaurant", ["mcat:food-and-dining"], "Restaurants (fraud-detection dataset label)."),
    "restaurants": ("mcat:restaurants", ["mcat:food-and-dining"], "Restaurants (synthetic-banking-txns label)."),
    "online_retail": ("mcat:online-retail", ["mcat:retail-and-shopping"], "Online retailers."),
    "online_marketplace": ("mcat:online-marketplace", ["mcat:retail-and-shopping"], "Online marketplaces."),
    "clothing": ("mcat:clothing", ["mcat:retail-and-shopping"], "Clothing stores (fraud-detection dataset label)."),
    "fashion": ("mcat:fashion", ["mcat:retail-and-shopping"], "Fashion retailers (synthetic-banking-txns label)."),
    "electronics": ("mcat:electronics", ["mcat:retail-and-shopping"], "Electronics retailers."),
    "pharmacy": ("mcat:pharmacy", ["mcat:health-and-wellness", "mcat:retail-and-shopping"], "Pharmacies."),
    "gas_station": ("mcat:gas-station", ["mcat:automotive-and-fuel"], "Fuel stations."),
    "hotel": ("mcat:hotel", ["mcat:travel-and-hospitality"], "Hotels and lodging."),
    "travel": ("mcat:travel", ["mcat:travel-and-hospitality"], "Airlines and travel agencies."),
    "utilities": ("mcat:utilities", ["mcat:utilities-and-bills"], "Utility payments."),
    "entertainment": ("mcat:entertainment", ["mcat:entertainment-and-leisure"], "Entertainment venues and services."),
    "gambling": ("mcat:gambling", ["mcat:entertainment-and-leisure"], "Gambling and betting."),
    "atm": ("mcat:atm", ["mcat:cash-and-cash-equivalents"], "ATM cash withdrawals."),
    "money_transfer": ("mcat:money-transfer", ["mcat:cash-and-cash-equivalents"], "Money-transfer services (fraud-detection dataset label)."),
    "transfer": ("mcat:transfer", ["mcat:cash-and-cash-equivalents"], "Account-to-account transfers (synthetic-banking-txns label)."),
    "crypto": ("mcat:crypto", ["mcat:cash-and-cash-equivalents"], "Cryptocurrency purchases."),
}
MCAT_MATCHES = [("mcat:restaurant", "mcat:restaurants", "skos:exactMatch"), ("mcat:clothing", "mcat:fashion", "skos:closeMatch"),
                ("mcat:online-retail", "mcat:online-marketplace", "skos:closeMatch"), ("mcat:money-transfer", "mcat:transfer", "skos:closeMatch")]
FRAUD_GROUPS = {
    "fraud:financial-crime": ("Financial Crime", "Top concept: crimes involving the misuse of financial services.", []),
    "fraud:fraud": ("Fraud", "Deception for financial gain.", ["fraud:financial-crime"]),
    "fraud:money-laundering-group": ("Money Laundering", "Disguising the origin of illicit funds.", ["fraud:financial-crime"]),
    "fraud:payment-fraud": ("Payment Fraud", "Fraud using payment cards or channels.", ["fraud:fraud"]),
    "fraud:identity-fraud": ("Identity Fraud", "Fraud using another person's identity or credentials.", ["fraud:fraud"]),
    "fraud:first-party-fraud": ("First-Party Fraud", "Fraud committed by the legitimate account holder.", ["fraud:fraud"]),
    "fraud:behavioural-anomaly": ("Behavioural Anomaly", "Activity inconsistent with normal behaviour that may indicate fraud.", ["fraud:fraud"]),
}
# pattern label -> (id, groupings)
FRAUD_LEAVES = {
    "card_not_present": ("fraud:card-not-present", ["fraud:payment-fraud"]),
    "card_present_stolen": ("fraud:card-present-stolen", ["fraud:payment-fraud"]),
    "atm_fraud": ("fraud:atm-fraud", ["fraud:payment-fraud"]),
    "card_testing": ("fraud:card-testing", ["fraud:card-not-present"]),
    "account_takeover": ("fraud:account-takeover", ["fraud:identity-fraud"]),
    "identity_theft": ("fraud:identity-theft", ["fraud:identity-fraud"]),
    "friendly_fraud": ("fraud:friendly-fraud", ["fraud:first-party-fraud"]),
    "money_laundering": ("fraud:money-laundering", ["fraud:money-laundering-group"]),
    "money_laundering_ring": ("fraud:money-laundering-ring", ["fraud:money-laundering"]),
    "geo_anomaly": ("fraud:geo-anomaly", ["fraud:behavioural-anomaly"]),
}
CHANNELS = {
    "mobile_app": ("channel:mobile-app", "channel:digital", "Transactions made in a mobile banking/payment app."),
    "web_browser": ("channel:web-browser", "channel:digital", "Transactions made in a web browser."),
    "phone_ivr": ("channel:phone-ivr", "channel:remote", "Transactions made by phone (interactive voice response)."),
    "pos_terminal": ("channel:pos-terminal", "channel:physical", "Card-present transactions at a point-of-sale terminal."),
    "atm": ("channel:atm", "channel:physical", "Transactions at an ATM."),
}
CHANNEL_GROUPS = {"channel:channel": ("Channel", "Top concept of the channel scheme.", None),
                  "channel:digital": ("Digital Channel", "Online and app-based channels.", "channel:channel"),
                  "channel:remote": ("Remote Channel", "Non-digital remote channels.", "channel:channel"),
                  "channel:physical": ("Physical Channel", "In-person channels.", "channel:channel")}
ACCOUNT_TYPES = {"personal": "Personal accounts held by individuals.", "business": "Business accounts.", "premium": "Premium-tier accounts."}
REGIONS = {
    "region:world": ("World", None), "region:north-america": ("North America", "region:world"),
    "region:europe": ("Europe", "region:world"), "region:asia": ("Asia", "region:world"),
    "region:oceania": ("Oceania", "region:world"), "region:south-america": ("South America", "region:world"),
    "region:africa": ("Africa", "region:world"),
}
COUNTRIES = {  # code -> (name, region id)
    "US": ("United States", "region:north-america"), "CA": ("Canada", "region:north-america"), "MX": ("Mexico", "region:north-america"),
    "GB": ("United Kingdom", "region:europe"), "FR": ("France", "region:europe"), "DE": ("Germany", "region:europe"),
    "ES": ("Spain", "region:europe"), "IT": ("Italy", "region:europe"), "RO": ("Romania", "region:europe"),
    "AU": ("Australia", "region:oceania"), "CN": ("China", "region:asia"), "IN": ("India", "region:asia"),
    "BR": ("Brazil", "region:south-america"), "NG": ("Nigeria", "region:africa"),
}


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# ─── generation ───────────────────────────────────────────────────────────────

class Generator:
    def __init__(self, source, graph_id, run_id, sample, sink, hashes):
        self.src = Path(source)
        self.graph_id = graph_id
        self.run_id = run_id
        self.sample = sample
        self.sink = sink
        self.files = hashes
        self.notes = []          # data-quality observations for the audit note
        self.stats = {}

    # provenance builders -----------------------------------------------------
    def prov(self, method, dataset=None, file=None, **extra):
        p = {"run_id": self.run_id, "generator": f"crowbar_cyber_fraud.py {GENERATOR_VERSION}", "method": method}
        if dataset:
            p["dataset"] = dataset
        if file:
            p["source_file"] = file
        p.update(extra)
        return p

    def authored(self, basis, **extra):
        return self.prov("ontology-authored", authored_by=AGENT, basis=basis, **extra)

    def rows(self, name):
        dataset, rel = SRC_FILES[name]
        path = self.src / rel
        with open(path, newline="", encoding="utf-8") as fh:
            yield from enumerate(csv.DictReader(fh), start=2)      # line number in the file (header = line 1)

    # ontology ----------------------------------------------------------------
    def build_ontology(self):
        s = self.sink
        onto_tags = ["alchemy-cyber-fraud", "ontology"]
        for id_, label, desc, parent in CLASSES:
            s.node(id_, label, "Class", {"subclass_of": parent} if parent else {}, self.authored("domain modelling of the cybersecurity / fraud-detection domain"),
                   description=desc, tags=onto_tags)
        for cid, label, parent in [(c[0], c[1], c[3]) for c in CLASSES if c[3]]:
            s.edge(f"edge:subclass-of:{cid}", "rel:subclass-of", [cid, parent], f"{label} is a subclass of {parent}",
                   {}, self.authored("class hierarchy"), tags=onto_tags)
        rel_index = {r[0]: r for r in RELATIONS}
        for rid, label, desc, inverse, dom, rng, broader in RELATIONS:
            attrs = {"inverse_of": inverse, "domain": dom, "range": rng, "broader_relation": broader,
                     "symmetric": rid in SYMMETRIC, "transitive": rid in TRANSITIVE}
            s.node(rid, label, "RelationType", attrs, self.authored("relation semantics for the fraud-detection ontology"),
                   description=desc, tags=onto_tags)
            s.edge(f"edge:domain:{rid}", "rel:has-domain", [rid] + dom, f"Domain of {rid}", {}, self.authored("schema"), tags=onto_tags)
            s.edge(f"edge:range:{rid}", "rel:has-range", [rid] + rng, f"Range of {rid}", {}, self.authored("schema"), tags=onto_tags)
        # axioms (control vocabulary understood by the inference engine)
        done = set()
        for rid, *_rest in RELATIONS:
            inv = rel_index[rid][3]
            if inv and (inv, rid) not in done:
                done.add((rid, inv))
                s.edge(f"edge:axiom:inverse-of:{slug(rid)}--{slug(inv)}", "owl:inverse-of", [rid, inv], f"Inverse-Of: {rid} / {inv}",
                       {}, self.authored("relation semantics: inverse pair"), tags=onto_tags + ["axiom"])
        for rid in SYMMETRIC:
            s.edge(f"edge:axiom:symmetric:{slug(rid)}", "owl:symmetric", [rid], f"Symmetric: {rid}", {},
                   self.authored("relation semantics: symmetric"), tags=onto_tags + ["axiom"])
        for rid in TRANSITIVE:
            s.edge(f"edge:axiom:transitive:{slug(rid)}", "owl:transitive", [rid], f"Transitive: {rid}", {},
                   self.authored("relation semantics: transitive"), tags=onto_tags + ["axiom"])
        for narrow, broad in BROADER_TRANSITIVE:
            s.edge(f"edge:axiom:broaderTransitive:{slug(narrow)}--{slug(broad)}", "skos:broaderTransitive", [narrow, broad],
                   f"{narrow} is narrower than {broad}", {}, self.authored("relation hierarchy (spelled broaderTransitive [narrower, broader])"),
                   tags=onto_tags + ["axiom"])
        for broad, narrow in NARROWER_TRANSITIVE:
            s.edge(f"edge:axiom:narrowerTransitive:{slug(broad)}--{slug(narrow)}", "skos:narrowerTransitive", [broad, narrow],
                   f"{narrow} is narrower than {broad}", {}, self.authored("relation hierarchy (spelled narrowerTransitive [broader, narrower])"),
                   tags=onto_tags + ["axiom"])

    def concept(self, id_, label, type_, scheme, definition, broaders, sources, notation=None, extra=None):
        attrs = {"concept_scheme": f"scheme:{scheme}", "definition": definition, "pref_label": label, "source_labels": sources["labels"]}
        if notation:
            attrs["notation"] = notation
        if extra:
            attrs.update(extra)
        self.sink.node(id_, label, type_, attrs, sources["prov"], description=definition, tags=["alchemy-cyber-fraud", "skos-concept", scheme])
        self.concepts.setdefault(scheme, []).append(id_)
        if not broaders:
            self.top_ids.add(id_)
        for b in broaders:
            self.broader_edges.append((id_, b, scheme))

    def build_concepts(self, patterns, sb_fraud_types, fd_cats, sb_cats):
        """SKOS concept schemes + hierarchies. Leaf concepts come from the data (only labels present are created)."""
        s = self.sink
        self.concepts, self.broader_edges, self.top_ids = {}, [], set()
        onto = ["alchemy-cyber-fraud", "ontology"]
        for scheme, (label, desc) in SCHEMES.items():
            s.node(f"scheme:{scheme}", label, "ConceptScheme", {"skos_uri_hint": f"scheme:{scheme}"}, self.authored("SKOS scheme"), description=desc, tags=onto)
        auth = lambda basis: {"labels": [], "prov": self.authored(basis)}
        # merchant categories
        self.concept(MCAT_ROOT[0], MCAT_ROOT[1], "MerchantCategory", "merchant-category", MCAT_ROOT[2], [], auth("scheme root"), extra={"concept_role": "top"})
        for gid, (label, desc) in MCAT_GROUPS.items():
            self.concept(gid, label, "MerchantCategory", "merchant-category", desc, [MCAT_ROOT[0]], auth("authored merchant-category grouping"), extra={"concept_role": "grouping"})
        for label, (cid, groups, desc) in MCAT_LEAVES.items():
            present_in = [ds for ds, cats in ((FD, fd_cats), (SB, sb_cats)) if label in cats]
            if not present_in:
                continue
            observed = {ds: cats[label]["count"] for ds, cats in ((FD, fd_cats), (SB, sb_cats)) if label in cats}
            prov = self.prov("direct mapping of distinct category labels + authored grouping", dataset="+".join(present_in), source_field="merchant_category",
                             source_files=[SRC_FILES["transactions" if ds == FD else "sb_transactions"][1] for ds in present_in],
                             observed_transactions=observed, authored_parts=["grouping under parent categories", "definition"])
            self.concept(cid, label.replace("_", " ").title(), "MerchantCategory", "merchant-category", desc, groups,
                         {"labels": [label], "prov": prov}, notation=fd_cats[label]["mcc"] if label in fd_cats else None,
                         extra={"concept_role": "leaf", "datasets": present_in})
        for a, b, rel in MCAT_MATCHES:
            if a in self.all_ids and b in self.all_ids:
                s.edge(f"edge:match:{slug(a)}--{slug(b)}", rel, [a, b], f"{a} {rel.split(':')[1]} {b}", {"note": "cross-dataset label alignment"},
                       self.authored("alignment of category labels used by the two source datasets"), flavor="symmetric", tags=onto + ["alignment"])
        # fraud typology
        for gid, (label, desc, broaders) in FRAUD_GROUPS.items():
            self.concept(gid, label, "FraudPattern", "fraud-typology", desc, broaders, auth("authored typology grouping"), extra={"concept_role": "grouping" if broaders else "top"})
        self.fraud_ids = {}
        for label, (cid, groups) in FRAUD_LEAVES.items():
            info = patterns.get(label)
            in_sb = label in sb_fraud_types
            if not info and not in_sb:
                continue
            datasets = ([FD] if info else []) + ([SB] if in_sb else [])
            extra = {"concept_role": "leaf", "datasets": datasets}
            if info:
                extra.update({k: v for k, v in info["props"].items()})
            prov = self.prov("direct mapping", dataset="+".join(datasets), source_field="fraud_pattern / fraud_type",
                             source_files=([SRC_FILES["fraud_patterns"][1]] if info else []) + ([SRC_FILES["sb_transactions"][1]] if in_sb else []),
                             source_row=info["row"] if info else None, fraud_type_observed_transactions_sb=sb_fraud_types.get(label))
            desc = info["description"] if info else {
                "card_testing": "Small probing transactions to validate stolen card numbers.",
                "geo_anomaly": "Transactions inconsistent with the customer's usual geography.",
                "money_laundering_ring": "Transfers among coordinated customers to layer illicit funds.",
                "account_takeover": "Fraudster gains access to a legitimate account.",
            }.get(label, label)
            self.fraud_ids[label] = cid
            self.concept(cid, label.replace("_", " ").title(), "FraudPattern", "fraud-typology", desc, groups, {"labels": [label], "prov": prov}, extra=extra)
        # channels
        for gid, (label, desc, broader) in CHANNEL_GROUPS.items():
            self.concept(gid, label, "DeviceType", "channel", desc, [broader] if broader else [], auth("authored channel grouping"), extra={"concept_role": "grouping" if broader else "top"})
        self.channel_ids = {}
        for label, (cid, group, desc) in CHANNELS.items():
            self.channel_ids[label] = cid
            self.concept(cid, label.replace("_", " ").title(), "DeviceType", "channel", desc, [group],
                         {"labels": [label], "prov": self.prov("direct mapping", dataset=FD, source_file=SRC_FILES["transactions"][1], source_field="device_type")}, extra={"concept_role": "leaf"})
        # account types
        self.concept("acctype:account-type", "Account Type", "AccountType", "account-type", "Top concept of the account type scheme.", [], auth("scheme root"), extra={"concept_role": "top"})
        self.acctype_ids = {}
        for label, desc in ACCOUNT_TYPES.items():
            cid = f"acctype:{label}"
            self.acctype_ids[label] = cid
            self.concept(cid, label.title(), "AccountType", "account-type", desc, ["acctype:account-type"],
                         {"labels": [label], "prov": self.prov("direct mapping", dataset=FD, source_file=SRC_FILES["account_profiles"][1], source_field="account_type")}, extra={"concept_role": "leaf"})
        # SKOS structure edges
        for cid, broad, scheme in self.broader_edges:
            s.edge(f"edge:skos-broader:{slug(cid)}--{slug(broad)}", "skos:broader", [cid, broad], f"{cid} has broader concept {broad}", {},
                   self.authored("concept hierarchy: source label placed under authored groupings"), tags=onto + ["skos"])
        narrower = defaultdict(list)
        for cid, broad, scheme in self.broader_edges:
            narrower[broad].append(cid)
        for broad, kids in narrower.items():
            for i, batch in enumerate(chunks(kids, MAX_SPOKES), 1):
                s.edge(f"edge:skos-narrower:{slug(broad)}~{i}", "skos:narrower", [broad] + batch, f"{broad} has {len(batch)} narrower concepts", {"part": i},
                       self.authored("concept hierarchy (inverse assertion of skos:broader, grouped by broader concept)"), tags=onto + ["skos"])
        for scheme, ids in self.concepts.items():
            tops = [c for c in ids if c in self.top_ids]
            s.edge(f"edge:top-concept:{scheme}", "skos:hasTopConcept", [f"scheme:{scheme}"] + tops, f"Scheme {scheme} has {len(tops)} top concept(s)", {},
                   self.authored("scheme structure"), tags=onto + ["skos"])
            for i, batch in enumerate(chunks(ids, MAX_SPOKES), 1):
                s.edge(f"edge:includes-concept:{scheme}:{i}", "rel:includes-concept", [f"scheme:{scheme}"] + batch,
                       f"Scheme {scheme} includes {len(batch)} concepts (part {i})", {"part": i}, self.authored("scheme membership"), tags=onto + ["skos"])

    def build_geography(self, city_registry, countries_seen):
        s = self.sink
        geo_tags = ["alchemy-cyber-fraud", "geography"]
        for rid, (label, parent) in REGIONS.items():
            s.node(rid, label, "Region", {"level": "world" if parent is None else "continent"}, self.authored("geographic grouping of countries"), tags=geo_tags)
        for rid, (label, parent) in REGIONS.items():
            if parent:
                s.edge(f"edge:contains:{slug(parent)}--{slug(rid)}", "rel:contains", [parent, rid], f"{parent} contains {rid}", {}, self.authored("geographic hierarchy"), tags=geo_tags)
        by_region = defaultdict(list)
        for code in sorted(countries_seen):
            name, region = COUNTRIES[code]
            ds = sorted(countries_seen[code])
            s.node(f"country:{code}", name, "Country", {"iso_3166_1_alpha2": code},
                   self.prov("direct mapping of distinct country codes + authored name/region lookup", dataset="+".join(ds), source_fields=["home_country", "merchant_country"], authored_lookup="country name and continent"),
                   tags=geo_tags)
            by_region[region].append(f"country:{code}")
        for region, members in by_region.items():
            for i, batch in enumerate(chunks(members, MAX_SPOKES), 1):
                s.edge(f"edge:contains:{slug(region)}:countries:{i}", "rel:contains", [region] + batch, f"{region} contains {len(batch)} countries", {},
                       self.authored("geographic hierarchy"), tags=geo_tags)
        by_country = defaultdict(list)
        for (city, cc), info in sorted(city_registry.items()):
            cid = f"city:{slug(city)}-{cc.lower()}"
            s.node(cid, city, "City", {"country_code": cc}, self.prov("entity resolution: distinct (merchant_city, merchant_country)", dataset=SB,
                                                                         source_file=SRC_FILES["sb_transactions"][1], source_fields=["merchant_city", "merchant_country"],
                                                                         first_seen_row=info["first"], observed_transactions=info["count"]), tags=geo_tags)
            by_country[cc].append(cid)
        for cc, cities in by_country.items():
            for i, batch in enumerate(chunks(cities, MAX_SPOKES), 1):
                s.edge(f"edge:contains:country-{cc.lower()}:cities:{i}", "rel:contains", [f"country:{cc}"] + batch,
                       f"Country {cc} contains {len(batch)} cities (part {i})", {"part": i},
                       self.prov("derived: distinct (city, country) pairs", dataset=SB, source_file=SRC_FILES["sb_transactions"][1], source_fields=["merchant_city", "merchant_country"]), tags=geo_tags)

    # hub edge emitter ----------------------------------------------------------
    def hub_edges(self, relation, hub_id, hub_label, spokes, info, dataset, file, grouping_field, verb, tags):
        parts = list(chunks(spokes, MAX_SPOKES))
        for i, batch in enumerate(parts, 1):
            prov = self.prov("relationship extraction: group rows by key", dataset=dataset, source_file=file, grouping_key=grouping_field,
                             group_source_rows={"count": info["n"], "first_row": info["first"], "last_row": info["last"]},
                             spoke_provenance="each spoke transaction hypernode carries its own source_row")
            self.sink.edge(f"edge:{relation.split(':')[1]}:{'fd' if dataset == FD else 'sb'}:{hub_id}~{i}", relation, [hub_id] + batch,
                           f"{hub_label} {verb} {len(batch)} transactions" + (f" (part {i}/{len(parts)})" if len(parts) > 1 else ""),
                           {"spoke_count": len(batch), "part": i, "parts": len(parts)}, prov, tags=tags)

    # dataset A -----------------------------------------------------------------
    def load_fraud_patterns(self):
        pats = {}
        for row_no, r in self.rows("fraud_patterns"):
            props = {"transaction_count": num(r["transaction_count"]), "fraud_share_pct": num(r["fraud_share_pct"]), "avg_amount": num(r["avg_amount"]),
                     "median_amount": num(r["median_amount"]), "pct_night_0_5": num(r["pct_night_0_5"]), "pct_foreign": num(r["pct_foreign"]),
                     "pct_card_not_present": num(r["pct_card_not_present"]), "avg_velocity_1h": num(r["avg_velocity_1h"]),
                     "avg_ip_risk": num(r["avg_ip_risk"]), "pct_no_2fa": num(r["pct_no_2fa"])}
            pats[r["fraud_pattern"]] = {"description": r["description"], "props": props, "row": row_no}
        return pats

    def stream_fd_transactions(self):
        s = self.sink
        file = SRC_FILES["transactions"][1]
        hubs = {k: defaultdict(lambda: {"ids": [], "first": None, "last": None, "n": 0}) for k in ("acct", "cat", "country", "chan", "pattern", "hour")}
        cats = {}
        countries = defaultdict(set)
        t0 = time.time()
        processed = 0
        for row_no, r in self.rows("transactions"):
            if self.sample and row_no - 1 > self.sample:
                break
            processed += 1
            tid = f"txn:fd:{r['transaction_id']}"
            attrs = {
                "transaction_id": r["transaction_id"], "timestamp": iso(r["timestamp"]), "hour_of_day": int(r["hour_of_day"]), "day_of_week": int(r["day_of_week"]),
                "is_weekend": flag(r["is_weekend"]), "amount": num(r["amount"]), "mcc_code": r["mcc_code"], "card_present": flag(r["card_present"]),
                "device_known": flag(r["device_known"]), "ip_risk_score": num(r["ip_risk_score"]), "is_foreign_txn": flag(r["is_foreign_txn"]),
                "time_since_last_s": num(r["time_since_last_s"]), "velocity_1h": num(r["velocity_1h"]), "amount_vs_avg_ratio": num(r["amount_vs_avg_ratio"]),
                "account_age_days": num(r["account_age_days"]), "has_2fa": flag(r["has_2fa"]), "credit_limit": num(r["credit_limit"]), "is_fraud": flag(r["is_fraud"]),
            }
            s.node(tid, f"Transaction {r['transaction_id']}", "Transaction", attrs,
                   {"run_id": self.run_id, "dataset": FD, "source_file": file, "source_row": row_no, "source_record_id": r["transaction_id"],
                    "method": "direct mapping", "mapping": "fd.transactions -> Transaction"}, tags=["alchemy-cyber-fraud", FD, "fraud" if attrs["is_fraud"] else "legitimate"])
            cat = r["merchant_category"]
            cats.setdefault(cat, {"mcc": r["mcc_code"], "count": 0})["count"] += 1
            countries[r["merchant_country"]].add(FD)
            if attrs["is_fraud"]:
                self.acct_fraud[r["account_id"]] += 1
                self.fd_hour_fraud[r["timestamp"][:13].replace(" ", "T")] += 1
            keys = [("acct", f"acct:{r['account_id']}"), ("cat", cat), ("country", r["merchant_country"]), ("chan", r["device_type"]), ("hour", r["timestamp"][:13].replace(" ", "T"))]
            if r["fraud_pattern"]:
                keys.append(("pattern", r["fraud_pattern"]))
            for kind, key in keys:
                h = hubs[kind][key]
                h["ids"].append(tid)
                h["first"] = h["first"] or row_no
                h["last"] = row_no
                h["n"] += 1
        self.stats["fd_transactions"] = processed
        self.fd_hubs, self.fd_cats = hubs, cats
        self.fd_countries = countries
        print(f"  fraud-detection/transactions.csv streamed in {time.time() - t0:.0f}s")

    def load_accounts(self):
        s = self.sink
        file = SRC_FILES["account_profiles"][1]
        acct_type = defaultdict(list)
        home = defaultdict(list)
        n = 0
        for row_no, r in self.rows("account_profiles"):
            aid = f"acct:{r['account_id']}"
            attrs = {
                "account_id": r["account_id"], "account_age_days": num(r["account_age_days"]), "credit_limit": num(r["credit_limit"]), "risk_score": num(r["risk_score"]),
                "is_high_risk": flag(r["is_high_risk"]), "avg_txn_amount": num(r["avg_txn_amount"]), "avg_monthly_txns": num(r["avg_monthly_txns"]), "has_2fa": flag(r["has_2fa"]),
                "total_transactions": num(r["total_transactions"]), "total_amount": num(r["total_amount"]), "avg_amount": num(r["avg_amount"]), "max_amount": num(r["max_amount"]),
                "fraud_count": num(r["fraud_count"]), "fraud_amount": num(r["fraud_amount"]), "pct_foreign": num(r["pct_foreign"]), "avg_velocity": num(r["avg_velocity"]),
                "unique_countries": num(r["unique_countries"]), "unique_categories": num(r["unique_categories"]), "avg_ip_risk": num(r["avg_ip_risk"]),
                "fraud_rate": num(r["fraud_rate"]), "is_fraudster": flag(r["is_fraudster"]),
            }
            s.node(aid, f"Account {r['account_id']}", "Account", attrs,
                   {"run_id": self.run_id, "dataset": FD, "source_file": file, "source_row": row_no, "source_record_id": r["account_id"],
                    "method": "direct mapping", "mapping": "fd.account_profiles -> Account",
                    "note": "profile aggregates are as supplied in the source; they were not recomputed from transactions.csv"},
                   tags=["alchemy-cyber-fraud", FD, "fraudster" if attrs["is_fraudster"] else "non-fraudster"])
            acct_type[r["account_type"]].append(aid)
            home[r["home_country"]].append(aid)
            self.account_rows[r["account_id"]] = row_no
            self.profile_counts[r["account_id"]] = {"total_transactions": attrs["total_transactions"], "fraud_count": attrs["fraud_count"]}
            n += 1
        self.stats["fd_accounts"] = n
        self.acct_type, self.home = acct_type, home

    def account_edges(self):
        info_of = lambda ids: {"n": len(ids), "first": self.account_rows[ids[0][5:]], "last": self.account_rows[ids[-1][5:]]}
        for label, ids in self.acct_type.items():
            for i, batch in enumerate(chunks(ids, MAX_SPOKES), 1):
                self.sink.edge(f"edge:categorizes-account:acctype-{label}~{i}", "rel:categorizes-account", [self.acctype_ids[label]] + batch,
                               f"Account type {label} categorizes {len(batch)} accounts (part {i})", {"spoke_count": len(batch), "part": i},
                               self.prov("relationship extraction: group rows by key", dataset=FD, source_file=SRC_FILES["account_profiles"][1], grouping_key="account_type",
                                         group_source_rows={"count": len(ids), "first_row": info_of(ids)["first"], "last_row": info_of(ids)["last"]}), tags=["alchemy-cyber-fraud", FD])
        for cc, ids in self.home.items():
            for i, batch in enumerate(chunks(ids, MAX_SPOKES), 1):
                self.sink.edge(f"edge:categorizes-account:home-{cc}~{i}", "rel:categorizes-account", [f"country:{cc}"] + batch,
                               f"Country {cc} is the home country of {len(batch)} accounts (part {i})", {"spoke_count": len(batch), "part": i, "role": "home_country"},
                               self.prov("relationship extraction: group rows by key", dataset=FD, source_file=SRC_FILES["account_profiles"][1], grouping_key="home_country",
                                         group_source_rows={"count": len(ids)}), tags=["alchemy-cyber-fraud", FD])

    def reconcile(self, patterns):
        """Compare aggregates supplied in the sources with values recomputed from the transaction files."""
        out = {}
        # account profiles vs transactions.csv (only meaningful for a full run)
        acct_hub = self.fd_hubs["acct"]
        mism_total = mism_fraud = checked = 0
        for aid, prof in self.profile_counts.items():
            h = acct_hub.get(f"acct:{aid}")
            n = h["n"] if h else 0
            checked += 1
            mism_total += n != prof["total_transactions"]
            mism_fraud += self.acct_fraud.get(aid, 0) != prof["fraud_count"]
        out["account_profiles_vs_transactions"] = {"accounts_checked": checked, "total_transactions_mismatch": mism_total, "fraud_count_mismatch": mism_fraud,
                                                   "accounts_without_transactions": sum(1 for aid in self.profile_counts if f"acct:{aid}" not in acct_hub)}
        pat = {}
        for label, h in self.fd_hubs["pattern"].items():
            pat[label] = {"fraud_patterns.csv": patterns[label]["props"]["transaction_count"], "recomputed": h["n"]}
        out["fraud_patterns_vs_transactions"] = pat
        out["fraud_transactions_recomputed"] = sum(h["n"] for h in self.fd_hubs["pattern"].values())
        buckets_sum = self.bucket_totals
        recomputed = {k: h["n"] for k, h in self.fd_hubs["hour"].items()}
        out["time_series_vs_transactions"] = {"buckets": len(buckets_sum), "sum_transaction_count_in_time_series": sum(v[0] for v in buckets_sum.values()),
                                              "transactions_recomputed": sum(recomputed.values()),
                                              "buckets_with_different_count": sum(1 for k, v in buckets_sum.items() if recomputed.get(k, 0) != v[0]),
                                              "buckets_with_different_fraud_count": sum(1 for k, v in buckets_sum.items() if self.fd_hour_fraud.get(k, 0) != v[1])}
        return out

    def emit_fd_transaction_edges(self):
        file = SRC_FILES["transactions"][1]
        tags = ["alchemy-cyber-fraud", FD, "transactional"]
        for key, h in self.fd_hubs["acct"].items():
            self.hub_edges("rel:initiated", key, key, h["ids"], h, FD, file, "account_id", "initiated", tags)
        for cat, h in self.fd_hubs["cat"].items():
            cid = MCAT_LEAVES[cat][0]
            self.hub_edges("rel:categorizes-transaction", cid, cid, h["ids"], h, FD, file, "merchant_category", "categorizes", tags)
        for cc, h in self.fd_hubs["country"].items():
            self.hub_edges("rel:location-of-transaction", f"country:{cc}", f"country:{cc}", h["ids"], h, FD, file, "merchant_country", "is the location of", tags)
        for dt, h in self.fd_hubs["chan"].items():
            self.hub_edges("rel:categorizes-transaction", self.channel_ids[dt], self.channel_ids[dt], h["ids"], h, FD, file, "device_type", "categorizes", tags)
        for pat, h in self.fd_hubs["pattern"].items():
            self.hub_edges("rel:typifies", self.fraud_ids[pat], self.fraud_ids[pat], h["ids"], h, FD, file, "fraud_pattern", "typifies", tags)
        for hour, h in self.fd_hubs["hour"].items():
            self.hub_edges("rel:aggregates", f"hour:{hour}", f"hour:{hour}", h["ids"], h, FD, file, "timestamp (truncated to the hour)", "aggregates", tags)

    def load_time_buckets(self):
        s = self.sink
        file = SRC_FILES["time_series_stats"][1]
        n = 0
        for row_no, r in self.rows("time_series_stats"):
            start = datetime.strptime(r["hour"], "%Y-%m-%d %H:%M:%S")
            hid = f"hour:{r['hour'][:13].replace(' ', 'T')}"
            attrs = {"hour": iso(r["hour"]), "transaction_count": num(r["transaction_count"]), "fraud_count": num(r["fraud_count"]), "total_amount": num(r["total_amount"]),
                     "avg_amount": num(r["avg_amount"]), "avg_ip_risk": num(r["avg_ip_risk"]), "fraud_rate": num(r["fraud_rate"]), "hour_of_day": int(r["hour_of_day"]),
                     "day_of_week": int(r["day_of_week"]), "is_weekend": flag(r["is_weekend"])}
            self.bucket_totals[r["hour"][:13].replace(" ", "T")] = (attrs["transaction_count"], attrs["fraud_count"])
            s.node(hid, f"Hour {r['hour'][:16]}", "TimeBucket", attrs,
                   {"run_id": self.run_id, "dataset": FD, "source_file": file, "source_row": row_no, "source_record_id": r["hour"], "method": "direct mapping",
                    "mapping": "fd.time_series_stats -> TimeBucket"}, valid_from=start, valid_to=start + timedelta(hours=1), tags=["alchemy-cyber-fraud", FD, "statistic"])
            n += 1
        self.stats["fd_time_buckets"] = n

    def load_network(self):
        s = self.sink
        file = SRC_FILES["network_edges"][1]
        rel_of = {"phone": "rel:shares-phone-with", "email_domain": "rel:shares-email-domain-with", "ip_address": "rel:shares-ip-address-with", "device_id": "rel:shares-device-with"}
        rings = defaultdict(lambda: {"accounts": set(), "edge_ids": [], "both_fraud": 0, "first": None, "count": 0})
        missing = 0
        n = 0
        for row_no, r in self.rows("network_edges"):
            a, b = f"acct:{r['account_a']}", f"acct:{r['account_b']}"
            for x in (r["account_a"], r["account_b"]):
                if x not in self.account_rows:
                    missing += 1
            rel = rel_of[r["shared_type"]]
            eid = f"edge:link:{r['shared_type']}:{r['account_a']}--{r['account_b']}"
            prov = {"run_id": self.run_id, "dataset": FD, "source_file": file, "source_row": row_no, "method": "direct mapping", "mapping": "fd.network_edges -> symmetric link hyperedge",
                    "source_values": {"shared_type": r["shared_type"], "ring_id": r["ring_id"] or None}}
            s.edge(eid, rel, [a, b], f"{r['account_a']} shares {r['shared_type']} with {r['account_b']}",
                   {"connection_count": num(r["connection_count"]), "both_fraud": flag(r["both_fraud"])}, prov, flavor="symmetric", tags=["alchemy-cyber-fraud", FD, "network-link"])
            if r["ring_id"]:
                g = rings[r["ring_id"]]
                g["accounts"].update([a, b])
                g["edge_ids"].append(eid)
                g["both_fraud"] += 1 if flag(r["both_fraud"]) else 0
                g["first"] = g["first"] or row_no
                g["count"] += 1
            n += 1
            if not r["ring_id"]:
                self.stats["fd_links_without_ring"] = self.stats.get("fd_links_without_ring", 0) + 1
        self.stats["fd_network_links"] = n
        if missing:
            self.notes.append(f"network_edges.csv references {missing} account ids that are not in account_profiles.csv")
        self.rings = rings

    def emit_rings(self):
        s = self.sink
        file = SRC_FILES["network_edges"][1]
        for ring_id, g in sorted(self.rings.items()):
            rid = f"ring:{ring_id}"
            accts = sorted(g["accounts"])
            s.node(rid, f"Fraud Ring {ring_id}", "FraudRing",
                   {"ring_id": ring_id, "member_account_count": len(accts), "link_count": g["count"], "both_fraud_link_count": g["both_fraud"]},
                   {"run_id": self.run_id, "dataset": FD, "source_file": file, "source_field": "ring_id", "method": "entity resolution: distinct ring_id",
                    "first_seen_row": g["first"], "derived_properties": ["member_account_count", "link_count", "both_fraud_link_count"],
                    "derivation": "counted from the ring's rows in network_edges.csv"}, tags=["alchemy-cyber-fraud", FD])
            base_prov = {"run_id": self.run_id, "dataset": FD, "source_file": file, "method": "relationship extraction: group rows by key", "grouping_key": "ring_id", "source_values": {"ring_id": ring_id}}
            for rel, members, label in (("rel:has-ring-member", accts, "accounts"), ("rel:has-link", g["edge_ids"], "links")):
                for i, batch in enumerate(chunks(members, MAX_SPOKES), 1):
                    s.edge(f"edge:{rel.split(':')[1]}:{rid}~{i}", rel, [rid] + batch, f"{ring_id} has {len(batch)} {label} (part {i})", {"spoke_count": len(batch), "part": i},
                           base_prov, tags=["alchemy-cyber-fraud", FD, "fraud-ring"])

    # dataset B -----------------------------------------------------------------
    def stream_sb_transactions(self):
        s = self.sink
        file = SRC_FILES["sb_transactions"][1]
        mk = lambda: {"ids": [], "first": None, "last": None, "n": 0}
        hubs = {k: defaultdict(mk) for k in ("cust", "card", "dev", "ip", "merch", "city", "fraud")}
        ent = {k: {} for k in ("cust", "card", "dev", "ip", "merch")}
        city_reg = {}
        merch_cat, merch_city = {}, defaultdict(Counter)
        cust_cards, cust_devs = defaultdict(set), defaultdict(set)
        first_owner = {"card": {}, "dev": {}, "ip": {}}
        shared = {"card": defaultdict(set), "dev": defaultdict(set), "ip": defaultdict(set)}
        cats, fraud_types = {}, Counter()
        t0 = time.time()
        processed = 0
        for row_no, r in self.rows("sb_transactions"):
            if self.sample and row_no - 1 > self.sample:
                break
            processed += 1
            tid = f"txn:sb:{r['transaction_id']}"
            attrs = {"transaction_id": r["transaction_id"], "timestamp": r["timestamp"], "amount": num(r["amount"]), "currency": r["currency"], "transaction_type": r["transaction_type"],
                     "merchant_latitude": num(r["merchant_latitude"]), "merchant_longitude": num(r["merchant_longitude"]), "is_fraud": flag(r["is_fraud"])}
            s.node(tid, f"Transaction {r['transaction_id']}", "Transaction", attrs,
                   {"run_id": self.run_id, "dataset": SB, "source_file": file, "source_row": row_no, "source_record_id": r["transaction_id"], "method": "direct mapping",
                    "mapping": "sb.transactions -> Transaction"}, tags=["alchemy-cyber-fraud", SB, "fraud" if attrs["is_fraud"] else "legitimate"])
            cust, card, dev = r["customer_id"], r["card_id"], r["device_id"]
            ip_id = r["ip_address"].replace(".", "-")
            city_key = (r["merchant_city"], r["merchant_country"])
            cats.setdefault(r["merchant_category"], {"count": 0})["count"] += 1
            for kind, key, raw in (("cust", f"cust:{cust}", cust), ("card", f"card:{card}", card), ("dev", f"dev:{dev}", dev), ("ip", f"ip:{ip_id}", r["ip_address"]), ("merch", f"merch:{r['merchant_id']}", r["merchant_id"])):
                e = ent[kind].get(key)
                if e is None:
                    ent[kind][key] = {"raw": raw, "first": row_no, "count": 1}
                else:
                    e["count"] += 1
                h = hubs[kind][key]
                h["ids"].append(tid)
                h["first"] = h["first"] or row_no
                h["last"] = row_no
                h["n"] += 1
            ci = city_reg.setdefault(city_key, {"first": row_no, "count": 0})
            ci["count"] += 1
            h = hubs["city"][city_key]
            h["ids"].append(tid)
            h["first"] = h["first"] or row_no
            h["last"] = row_no
            h["n"] += 1
            if r["fraud_type"]:
                fraud_types[r["fraud_type"]] += 1
                h = hubs["fraud"][r["fraud_type"]]
                h["ids"].append(tid)
                h["first"] = h["first"] or row_no
                h["last"] = row_no
                h["n"] += 1
            merch_cat.setdefault(r["merchant_id"], {"cat": r["merchant_category"], "first": row_no, "n": 0})["n"] += 1
            if merch_cat[r["merchant_id"]]["cat"] != r["merchant_category"]:
                self.notes.append(f"merchant {r['merchant_id']} has more than one merchant_category (row {row_no})")
            merch_city[r["merchant_id"]][city_key] += 1
            cust_cards[cust].add(card)
            cust_devs[cust].add(dev)
            for kind, key in (("card", card), ("dev", dev), ("ip", ip_id)):
                owner = first_owner[kind].setdefault(key, cust)
                if owner != cust:
                    shared[kind][key].update([owner, cust])
        self.stats["sb_transactions"] = processed
        self.sb = {"hubs": hubs, "ent": ent, "city": city_reg, "merch_cat": merch_cat, "merch_city": merch_city, "cust_cards": cust_cards,
                   "cust_devs": cust_devs, "shared": shared, "cats": cats, "fraud_types": fraud_types}
        print(f"  synthetic-banking-txns/fraud-detection-dataset.csv streamed in {time.time() - t0:.0f}s")

    def emit_sb_entities(self):
        s = self.sink
        file = SRC_FILES["sb_transactions"][1]
        ent = self.sb["ent"]
        spec = [("cust", "customer_id", "Customer", "customer"), ("card", "card_id", "Card", "card"), ("dev", "device_id", "Device", "device"),
                ("ip", "ip_address", "IPAddress", "ip"), ("merch", "merchant_id", "Merchant", "merchant")]
        for kind, field, type_, word in spec:
            for key, e in ent[kind].items():
                attrs = {field: e["raw"]}
                s.node(key, f"{type_} {e['raw']}", type_, attrs,
                       {"run_id": self.run_id, "dataset": SB, "source_file": file, "source_field": field, "method": "entity resolution: distinct values",
                        "first_seen_row": e["first"], "observed_transactions": e["count"]}, tags=["alchemy-cyber-fraud", SB, word])

    def emit_sb_edges(self):
        s = self.sink
        file = SRC_FILES["sb_transactions"][1]
        tags = ["alchemy-cyber-fraud", SB, "transactional"]
        hubs = self.sb["hubs"]
        for key, h in hubs["cust"].items():
            self.hub_edges("rel:initiated", key, key, h["ids"], h, SB, file, "customer_id", "initiated", tags)
        for key, h in hubs["card"].items():
            self.hub_edges("rel:charged-card", key, key, h["ids"], h, SB, file, "card_id", "was charged for", tags)
        for key, h in hubs["dev"].items():
            self.hub_edges("rel:originated-device", key, key, h["ids"], h, SB, file, "device_id", "originated", tags)
        for key, h in hubs["ip"].items():
            self.hub_edges("rel:originated-ip", key, key, h["ids"], h, SB, file, "ip_address", "originated", tags)
        for key, h in hubs["merch"].items():
            self.hub_edges("rel:received-transaction", key, key, h["ids"], h, SB, file, "merchant_id", "received", tags)
        for (city, cc), h in hubs["city"].items():
            cid = f"city:{slug(city)}-{cc.lower()}"
            self.hub_edges("rel:location-of-transaction", cid, cid, h["ids"], h, SB, file, "(merchant_city, merchant_country)", "is the location of", tags)
        for ft, h in hubs["fraud"].items():
            self.hub_edges("rel:typifies", self.fraud_ids[ft], self.fraud_ids[ft], h["ids"], h, SB, file, "fraud_type", "typifies", tags)
        # ownership / usage (derived from co-occurrence within rows)
        for cust, cards in self.sb["cust_cards"].items():
            cards = sorted(f"card:{c}" for c in cards)
            for i, batch in enumerate(chunks(cards, MAX_SPOKES), 1):
                s.edge(f"edge:owns-card:cust:{cust}~{i}", "rel:owns-card", [f"cust:{cust}"] + batch, f"Customer {cust} owns {len(batch)} cards", {"spoke_count": len(batch), "part": i},
                       self.prov("relationship extraction: distinct (customer_id, card_id) pairs co-occurring in a row", dataset=SB, source_file=file, source_fields=["customer_id", "card_id"]),
                       tags=["alchemy-cyber-fraud", SB, "ownership"])
        for cust, devs in self.sb["cust_devs"].items():
            devs = sorted(f"dev:{d}" for d in devs)
            for i, batch in enumerate(chunks(devs, MAX_SPOKES), 1):
                s.edge(f"edge:uses-device:cust:{cust}~{i}", "rel:uses-device", [f"cust:{cust}"] + batch, f"Customer {cust} used {len(batch)} devices", {"spoke_count": len(batch), "part": i},
                       self.prov("relationship extraction: distinct (customer_id, device_id) pairs co-occurring in a row", dataset=SB, source_file=file, source_fields=["customer_id", "device_id"],
                                 caveat="association inferred from co-occurrence in the same transaction row"), tags=["alchemy-cyber-fraud", SB, "usage"])
        # merchant -> category, merchant -> city
        by_cat = defaultdict(list)
        for mid, info in self.sb["merch_cat"].items():
            by_cat[info["cat"]].append((f"merch:{mid}", info))
        for cat, items in by_cat.items():
            cid = MCAT_LEAVES[cat][0]
            ids = [i for i, _ in items]
            for i, batch in enumerate(chunks(ids, MAX_SPOKES), 1):
                s.edge(f"edge:categorizes-merchant:{cid}~{i}", "rel:categorizes-merchant", [cid] + batch, f"{cid} categorizes {len(batch)} merchants (part {i})", {"spoke_count": len(batch), "part": i},
                       self.prov("relationship extraction: group rows by key", dataset=SB, source_file=file, grouping_key="merchant_category"), tags=["alchemy-cyber-fraud", SB])
        for mid, cities in self.sb["merch_city"].items():
            ordered = sorted(cities.items())
            members = [f"merch:{mid}"] + [f"city:{slug(c)}-{cc.lower()}" for (c, cc), _ in ordered]
            s.edge(f"edge:located-in:merch:{mid}", "rel:located-in", members, f"Merchant {mid} located in {len(ordered)} city/cities", {"observations_per_city": {f"{c}, {cc}": n for (c, cc), n in ordered}},
                   self.prov("relationship extraction: distinct (merchant_id, merchant_city, merchant_country)", dataset=SB, source_file=file, source_fields=["merchant_id", "merchant_city", "merchant_country"],
                             anomaly="merchant observed in more than one city" if len(ordered) > 1 else None), tags=["alchemy-cyber-fraud", SB, "location"])
        # shared identifiers (fraud signals), symmetric n-ary hyperedges between customers
        rel_of = {"card": "rel:shares-card-with", "dev": "rel:shares-device-with", "ip": "rel:shares-ip-address-with"}
        field_of = {"card": "card_id", "dev": "device_id", "ip": "ip_address"}
        for kind, groups in self.sb["shared"].items():
            # the same set of customers can share several identifiers; an identical (relation, members) pair is one
            # hyperedge (hyperkey uniqueness), so those identifiers are listed on a single edge
            by_members = defaultdict(list)
            for key, custs in groups.items():
                by_members[tuple(sorted(custs))].append(key)
            for custs, keys in sorted(by_members.items(), key=lambda kv: sorted(kv[1])[0]):
                keys = sorted(keys)
                members = [f"cust:{c}" for c in custs]
                s.edge(f"edge:shared:{kind}:{keys[0]}", rel_of[kind], members, f"{len(members)} customers share {len(keys)} {field_of[kind]} value(s), e.g. {keys[0]}",
                       {"shared_identifier_count": len(keys), "shared_identifiers": [f"{kind}:{k}" for k in keys]},
                       self.prov("derived: identifier observed with more than one customer_id", dataset=SB, source_file=file, source_fields=["customer_id", field_of[kind]]),
                       flavor="symmetric", tags=["alchemy-cyber-fraud", SB, "shared-identifier"])
        self.stats["sb_shared"] = {k: len(v) for k, v in self.sb["shared"].items()}     # identifiers observed with >1 customer

    # orchestration -------------------------------------------------------------
    def run(self):
        t0 = time.time()
        self.account_rows = {}
        self.acct_fraud, self.fd_hour_fraud = Counter(), Counter()
        self.profile_counts, self.bucket_totals = {}, {}
        print("Streaming source files ...")
        patterns = self.load_fraud_patterns()
        self.stream_fd_transactions()
        self.stream_sb_transactions()
        sb_cats = self.sb["cats"]          # label -> {"count"}
        fd_cats = self.fd_cats             # label -> {"mcc", "count"}
        self.all_ids = {v[0] for k, v in MCAT_LEAVES.items() if k in fd_cats or k in sb_cats}
        unknown = (set(fd_cats) | set(sb_cats)) - set(MCAT_LEAVES)
        if unknown:
            raise SystemExit(f"unmapped merchant categories: {unknown}")
        unknown_f = (set(patterns) | set(self.sb["fraud_types"])) - set(FRAUD_LEAVES)
        if unknown_f:
            raise SystemExit(f"unmapped fraud patterns: {unknown_f}")
        # concepts: fd_cats maps label -> {"mcc", "count"}; sb cats label -> count (int)
        print("Building ontology and concepts ...")
        self.build_ontology()
        self.build_concepts(patterns, self.sb["fraud_types"], fd_cats, sb_cats)
        countries_seen = defaultdict(set)
        for cc in self.fd_countries:
            countries_seen[cc].add(FD)
        for (_city, cc) in self.sb["city"]:
            countries_seen[cc].add(SB)
        countries_seen["US"].add(FD)          # every account's home_country
        print("Geography ...")
        self.build_geography(self.sb["city"], countries_seen)
        print("Dataset fraud-detection ...")
        self.load_time_buckets()
        self.load_accounts()
        self.account_edges()
        self.load_network()
        self.emit_rings()
        self.emit_fd_transaction_edges()
        print("Dataset synthetic-banking-txns ...")
        self.emit_sb_entities()
        self.emit_sb_edges()
        self.sink.flush()
        self.stats["reconciliation"] = self.reconcile(patterns)
        multi_city = sum(1 for c in self.sb["merch_city"].values() if len(c) > 1)
        if multi_city:
            self.notes.append(f"synthetic-banking-txns: {multi_city} merchants are observed in more than one (city, country); each location is kept as a separate rel:located-in spoke")
        for kind, word in (("card", "cards"), ("dev", "devices"), ("ip", "IP addresses")):
            n = len(self.sb["shared"][kind])
            if n:
                self.notes.append(f"synthetic-banking-txns: {n} {word} are used by more than one customer_id; captured as symmetric hyperedges (rel:shares-{ {'card':'card','dev':'device','ip':'ip-address'}[kind] }-with)")
        no_ring = self.stats.get("fd_links_without_ring")
        if no_ring:
            self.notes.append(f"fraud-detection: {no_ring} network_edges rows have no ring_id; kept as rel:shares-*-with links but not attached to any FraudRing")
        no_txn = self.stats["reconciliation"]["account_profiles_vs_transactions"]["accounts_without_transactions"]
        if no_txn and not self.sample:
            self.notes.append(f"fraud-detection: {no_txn} accounts in account_profiles.csv have no rows in transactions.csv (their profile aggregates are 0 / as supplied)")
        self.notes.append("both datasets: no shared identifiers between fraud-detection (ACC*, TXN 9-digit) and synthetic-banking-txns (CUST*, CARD*, TXN 12-digit); they are two disconnected components apart from the shared ontology")
        self.notes.append("synthetic-banking-txns: merchant_latitude / merchant_longitude do not correspond to merchant_country / merchant_city (values span the full -90..90 / -180..180 range for every country); kept as literals on the transaction, not used for geography")
        self.notes.append("fraud-detection: transactions.csv timestamps and time_series_stats hours carry no time zone (stored as zone-less ISO strings); synthetic-banking-txns timestamps are UTC (+00:00)")
        self.stats["generation_seconds"] = round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=os.path.expanduser("~/Downloads/crowbar"))
    ap.add_argument("--db", default=None, help="MongoDB database (default: HGAI_MONGO_DB)")
    ap.add_argument("--sample", type=int, default=0, help="only read the first N data rows of each transaction file (pilot)")
    ap.add_argument("--graph-id", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", default=None, help="write the run report (JSON) to this path")
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    graph_id = args.graph_id or f"alchemy-cyber-fraud-generated-{stamp}"
    settings = get_settings()
    db_name = args.db or settings.mongo_db
    started = datetime.now(timezone.utc)
    print(f"Run {graph_id}  db={db_name}  sample={args.sample or 'all rows'}  dry_run={args.dry_run}")

    hashes = {}
    for name, (dataset, rel) in SRC_FILES.items():
        path = Path(args.source) / rel
        hashes[name] = {"dataset": dataset, "path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path), "data_rows": count_rows(path)}
        print(f"  {rel}: {hashes[name]['data_rows']:,} rows  sha256 {hashes[name]['sha256'][:16]}...")

    db = None
    if not args.dry_run:
        client = MongoClient(settings.mongo_uri)
        db = client[db_name]
        if db["hypergraphs"].find_one({"id": graph_id}):
            raise SystemExit(f"hypergraph {graph_id} already exists")
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        graph = HypergraphCreate(id=graph_id, label=graph_id, description="(generation in progress)", tags=["alchemy-cyber-fraud", "generating"]).model_dump()
        graph.update(system_created=now, system_updated=now, created_by=CREATED_BY, version=1, node_count=0, edge_count=0)
        db["hypergraphs"].insert_one(graph)

    sink = Sink(db, graph_id, args.dry_run)
    sink.known_relations = {r[0] for r in RELATIONS}
    gen = Generator(args.source, graph_id, graph_id, args.sample, sink, hashes)
    try:
        gen.run()
    except BaseException:
        if db is not None:
            print("FAILED — leaving partial data in place for inspection; remove with: db.hypergraphs/hypernodes/hyperedges deleteMany({hypergraph_id/id: '%s'})" % graph_id)
        raise
    finished = datetime.now(timezone.utc)

    report = {
        "graph_id": graph_id, "db": db_name, "sample": args.sample or None, "dry_run": args.dry_run, "generator_version": GENERATOR_VERSION,
        "generator_sha256": sha256_file(__file__), "started_at": started.isoformat(), "finished_at": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 1),
        "counts": {"hypernodes": sink.node_count, "hyperedges": sink.edge_count, "member_slots": sink.member_slots},
        "hypernodes_by_type": dict(sink.node_types.most_common()), "hyperedges_by_relation": dict(sink.relations.most_common()),
        "sources": hashes, "stats": gen.stats, "data_quality_notes": gen.notes[:50],
    }
    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: report[k] for k in ("graph_id", "duration_seconds", "counts")}, indent=2))
    if db is not None:
        finalize_graph(db, graph_id, report, stamp)


def finalize_graph(db, graph_id, report, stamp):
    """Write the hypergraph's own definition: id/label, generated description, tags, and
    `attributes` (name + provenance), now that the counts are known."""
    c = report["counts"]
    t = report["hypernodes_by_type"]
    date = datetime.strptime(stamp, "%Y%m%d%H%M%S").strftime("%Y-%m-%d")
    description = (
        f"Cybersecurity / fraud-detection knowledge hypergraph generated on {date} from two synthetic banking datasets (the 'crowbar' folder): "
        f"the fraud-detection dataset ({t.get('Account', 0):,} accounts, transactions, {t.get('FraudRing', 0)} fraud rings and {report['stats'].get('fd_network_links', 0):,} shared-attribute links, "
        f"hourly statistics) and the synthetic-banking-txns dataset (customers, cards, devices, IP addresses, merchants and cities). "
        f"{c['hypernodes']:,} hypernodes and {c['hyperedges']:,} hyperedges model transactions and their parties as entities and relationships, over a domain ontology of classes, "
        f"relation types (owl:inverse-of, owl:symmetric, owl:transitive, skos:broaderTransitive / narrowerTransitive axioms) and SKOS concept schemes for merchant categories, "
        f"fraud typologies, channels and account types. Every hypergraph, hypernode and hyperedge records its provenance under attributes.provenance."
    )
    provenance = {
        "run_id": graph_id, "generated_at": report["finished_at"], "started_at": report["started_at"], "duration_seconds": report["duration_seconds"],
        "generator": {"script": "scripts/generators/crowbar_cyber_fraud.py", "version": report["generator_version"], "sha256": report["generator_sha256"]},
        "generated_by": AGENT, "method": "scripted transformation of CSV files into hypernodes/hyperedges; bulk insert into MongoDB",
        "sources": report["sources"], "counts": c, "hypernodes_by_type": report["hypernodes_by_type"], "hyperedges_by_relation": report["hyperedges_by_relation"],
        "reconciliation": report["stats"].get("reconciliation"), "data_quality_notes": report["data_quality_notes"],
        "audit_note": "see the Note whose id starts with 'hgai-note-generation-' and is tagged with this run id",
    }
    db["hypergraphs"].update_one({"id": graph_id}, {"$set": {
        "label": graph_id, "description": description, "tags": ["cybersecurity", "fraud-detection", "alchemy", "generated", "synthetic-data", "alchemy-cyber-fraud"],
        "node_count": c["hypernodes"], "edge_count": c["hyperedges"], "system_updated": datetime.now(timezone.utc).replace(tzinfo=None),
        "attributes": {"name": f"Fraud Detection - Alchemy ({date})", "domain": "cybersecurity / fraud detection", "provenance": provenance},
    }})


if __name__ == "__main__":
    main()
