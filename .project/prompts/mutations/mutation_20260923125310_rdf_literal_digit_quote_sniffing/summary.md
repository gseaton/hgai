# Mutation Summary

## Intent
The user wanted RDF-imported literal values classified into text vs. numeric attribute values based on a simple, predictable rule: an object that "starts with a quote" (a string) becomes text, and an object that "starts with a digit" becomes a number — with an explicit `-1` fallback if that number fails to parse. Their motivating example (`ex:Eve ex:rating 12.2` should become a true numeric `12.2`, not text) pointed at a real, pre-existing bug: Turtle's default type for a bare decimal literal like `12.2` is `xsd:decimal`, whose `rdflib` `.toPython()` value is a `decimal.Decimal` — a type the existing code didn't recognize as BSON/JSON-safe, so it silently fell back to storing it as the lexical string `"12.2"` instead of a real number.

The user's request also asked for the attribute *field name* to become the predicate's fully expanded IRI, and clarified in a follow-up turn that resource-valued (IRI) objects should remain hyperedges, never attributes (already true structurally, but worth confirming explicitly).

## Context
`hgai/core/rdf_import.py` already had a deliberate, documented design decision from earlier in this project's history: attribute *keys* stay as sanitized CURIEs (e.g. `ex:sex`), never expanded to full IRIs — because attribute keys become literal MongoDB subdocument field names, and SHQL's `attributes: {key: value}` pattern filter (`hgai_module_storage_mongodb/stores/hypernodes.py`) builds a dot-path query (`f"attributes.{k}"`) from that key. A key containing `.` (which almost any real IRI does, via its domain name) would make that filter address the wrong, nonexistent nested path and silently stop matching — a real regression risk, not a style preference.

Before making any change, this conflict was surfaced to the user directly via AskUserQuestion, since it pitted their explicit request against a previously verified, tested design constraint. The user chose to keep CURIE-compacted keys and only wanted the value-classification (text vs. numeric) part implemented.

## What Changed and Why
`_literal_value()` was rewritten to classify by the literal's own lexical form (its first character as text) rather than by its RDF-declared datatype. A digit-led lexical string is parsed directly via Python's `int()`/`float()`, sidestepping `toPython()`'s type-mapping gaps entirely — this is what fixes the `12.2` → `decimal.Decimal` → text bug the user's example exposed, and also means a literal RDF-typed as a plain string that merely *looks* numeric (e.g. a quoted `"12345"`, with no datatype) still becomes a true number, exactly as the user's rule describes ("if the Object starts with a digit character... numeric").

Two exemptions were added deliberately, without being asked, to avoid *removing* already-correct behavior the user's rule didn't address: booleans (`"true"`/`"false"` don't naturally read as numbers) and dates/timestamps (`xsd:date`, `xsd:dateTime` are digit-led lexically, e.g. `"2026-09-23"`, and would otherwise be swept into a failed numeric parse and destroyed as `-1`). These keep their pre-existing native-type handling. A negative RDF-typed number (e.g. `"-5"^^xsd:integer`, lexically `-`-led, not digit-led) also still passes through as a native number rather than regressing to text, since it was already RDF-typed correctly and nothing in the user's rule called for changing that.

The attribute-key format (CURIE vs. full IRI) was intentionally left unchanged, per the user's own choice after the AskUserQuestion conflict — this mutation implements the value-classification half of the request only.

## Key Decisions
- Checked the literal's own `toPython()`-derived type for bool/date/dateTime *before* applying the digit-led lexical rule, so the new rule only takes over the cases the user actually described (numeric-looking or string-looking values), not cases where RDF typing already gives an unambiguous, correct, non-numeric native type.
- Attempted `int()` before `float()` on a digit-led lexical string, so integer-looking values (`"12345"`, `"30"`) stay Python `int` rather than becoming `12345.0`.
- Declined the full-IRI attribute-key change rather than silently keeping the old CURIE behavior or silently implementing the risky full-IRI behavior — this was a genuine conflict with a previously verified design constraint, not a judgment call to make unilaterally, so it was surfaced to the user via AskUserQuestion before any code was touched.
