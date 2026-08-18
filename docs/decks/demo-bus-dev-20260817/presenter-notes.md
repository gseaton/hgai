# Presenter Notes — HypergraphAI Business Briefing (Defense/Gov BD Audience)

Companion to `deck-hgai-defense-bd.md`. Read this before you present it —
it's the talk track, timing, and the honest answers to the questions this
specific audience reliably asks.

## Who's in the room, and how to calibrate

Business development and product leads at large defense/gov consulting
firms are not naive about vendor pitches — most have sat through a dozen
"AI will transform your business" decks this year alone. They will
mentally file this presentation within the first two slides as either
"another AI wrapper pitch" or "an actual infrastructure story." Slide 2
(the hyperedge diagram) and Slide 11 onward (the worked comparison) are
what earn the second bucket. Don't rush past the worked example to get to
the business-model slides — the worked example *is* the credibility.

## Suggested timing (45-minute slot)

- Slides 1–3 (framing + concepts): 8 minutes
- Slides 4–5 (general knowledge platform): 5 minutes
- Slides 6–10 (AI memory + MCP): 10 minutes
- Slides 11–17 (the worked example): 15 minutes — don't compress this;
  it's the section that converts skeptics
- Slides 18–21 (honesty scorecard, defense fit, business fit, next steps):
  7 minutes

If you only have 20 minutes, keep 1–3, 11–17, and 21. Cut everything else
or hand it out as leave-behind reading.

## Anticipated questions and how to answer them honestly

**"Is this FedRAMP / IL5 / IL6 authorized?"**
No. Say so plainly. It's MIT-licensed, self-hosted, Docker-based software
— the same category of thing your organization already puts through its
own ATO process for other self-hosted stacks. Nothing about it is
pre-certified for any environment. The honest pitch is "this is a fit for
the environments you already know how to accredit," not "this is already
accredited."

**"How mature is this? What are the production references?"**
Be direct: this is an early-stage platform, not a decade-old incumbent.
The technical proof in Section 11 of the deck is real, runnable syntax
against a real system — that's the credibility you can offer today.
Maturity claims beyond that should come from whoever owns the commercial
relationship, not from this deck.

**"How is this different from Palantir Foundry / Gotham?"**
Don't be defensive — the comparison is fair and worth answering plainly.
Foundry is a large, mature, heavily productized enterprise platform with
its own ontology/pipeline/ops tooling and a substantial cost and
integration footprint. hgai is a much smaller, focused, open-source
semantic hypergraph *storage and query layer* — it doesn't compete with
Foundry's pipeline/ops breadth, and in many environments it's plausible to
run *alongside* an existing Foundry deployment as a lightweight,
MCP-reachable semantic layer for a specific AI-agent use case rather than
as a wholesale replacement. If asked "would you rip out Foundry for
this," the honest answer is almost always no — that's not the pitch.

**"How is this different from a vector database (Pinecone, Weaviate) we
already use for RAG?"**
A vector store answers "what's similar to this text." hgai answers
"what's structurally and semantically related to this thing, as of when."
They're complementary, not competitive — Section 5's comparison table in
the deck says this directly. If the firm already has a RAG pipeline, the
pitch is "hgai is where the *distilled conclusions* from that pipeline
should live, not a replacement for the retrieval step."

**"What's the licensing model — what does this cost us?"**
Core engine is MIT-licensed and open source. The deck deliberately does
not include a pricing/business-model slide aimed at *this* audience,
because they are potential adopters/partners, not investors — pricing
should come from whoever owns that commercial conversation, not get
improvised in a BD briefing.

**"Can an AI agent write bad or hallucinated 'facts' into this and
poison the knowledge base?"**
Yes, and don't downplay it — this is the single most important honest
caveat in the whole pitch. That's exactly why Section 10 of the deck
insists on **provenance and confidence as first-class fields**, not an
afterthought: an AI-generated hyperedge is tagged `ai-generated`,
attributed to a specific model/session, and carries a confidence score
precisely so a human or downstream process can filter, review, or
discount it — instead of it silently blending in with verified facts the
way an unstructured text dump would. The platform doesn't *prevent* bad
writes; it makes bad writes visible and attributable, which is the
realistic bar, not a false promise of infallibility.

**"Does inferencing/reasoning happen automatically, like the marketing
implies for some knowledge graph products?"**
No — and Section 18 of the deck exists specifically to head this off
before someone asks it in front of a government customer later. Say
plainly: SKOS/inverse-relation inferencing is designed into the data
model but not yet wired into query execution. Nothing in the worked
example (Sections 11–17) relies on it. This is a deliberate choice in how
this deck was built — an earlier internal deck overstated this exact
capability, and it was corrected specifically so nobody in your
organization repeats an inaccurate claim to a federal customer.

**"What if we want to swap the query languages/scenario for our own
domain before we show this internally?"**
Everything in `data/` and `queries/` is small and self-contained
on purpose — the whole scenario is ~10 nodes and ~6 edges. Swapping
"task order / labor category / person" for your own domain's N-ary fact
(a contract clause with multiple parties, a sensor-fusion event with
multiple sources, a security-incident report with multiple involved
systems) is a low-effort adaptation, not a rebuild.

## Delivery notes on the worked example (Sections 11–17)

- Have `staffing-rdf-comparison.ttl` and `staffing-sql-comparison.sql`
  open in a side-by-side editor if presenting live — the visual density
  difference (one hyperedge vs. a manufactured resource plus five
  triples, or a three-way join) lands harder seen than described.
- The LCAT-mod / point-in-time beat (Section 16) is the single strongest
  moment in the deck for this audience specifically — contract
  modifications changing a person's labor category is something everyone
  in a defense-consulting BD room has lived through personally. Let that
  land before moving on; don't rush to Section 17.
- If someone asks to see it actually run (not just read the YAML), that's
  exactly what `demo-alpha/deck-demo-alpha.md` (the engineering-audience
  deck in this repo) is for — offer that as the immediate follow-up
  meeting, not something to attempt cold in this session.
