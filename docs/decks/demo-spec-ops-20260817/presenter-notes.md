# Presenter Notes — HypergraphAI Business Briefing (Special Operations / Mission Support BD Audience)

Companion to `deck-hgai-specops-bd.md`. Read this before you present it —
it's the talk track, timing, and the honest answers to the questions this
specific audience reliably asks.

## Why this deck's example is MEDEVAC/ISR-fusion, not fires or targeting

Say this up front if anyone asks why the worked example is casualty
evacuation rather than something more "kinetic": it's a deliberate choice,
not an oversight. Three reasons, and they're all legitimate to state
plainly to this audience:

1. **It's the strongest technical example, not just the safest one.** A
   9-line MEDEVAC request is a genuinely N-ary fact (element, location,
   asset, and a variable number of patients, all at once) — it shows off
   hyperedges, variable-arity membership, and point-in-time updates better
   than almost any other mission-support scenario would.
2. **It's grounded in unclassified, publicly published doctrine.** The
   9-line MEDEVAC format is taught to every U.S. service member and
   appears in open-source training material. Nothing about referencing its
   structure discloses anything sensitive.
3. **The AI agent's role stays unambiguous.** The recommendation hyperedge
   in the example is explicitly framed as decision support *for a human
   controller* — never as an automated action. That's not a hedge; it's
   the correct scope for what this kind of knowledge platform should do,
   and it's worth stating that plainly rather than letting the audience
   assume otherwise.

If a prospect specifically wants to talk through a fires, targeting, or
strike-coordination use case, that's a real conversation to have — but
it's a different conversation, with a different (likely classified) venue
and a different set of stakeholders than a BD briefing deck. Don't
improvise that discussion from this material.

## Who's in the room, and how to calibrate

Business development and product leads at large defense/gov consulting
firms are not naive about vendor pitches. They will mentally file this
presentation within the first two slides as either "another AI wrapper
pitch" or "an actual infrastructure story." Slide 2 (the hyperedge
diagram) and Slide 11 onward (the worked comparison) are what earn the
second bucket. Don't rush past the worked example to get to the
business-fit slides — the worked example *is* the credibility.

## Suggested timing (45-minute slot)

- Slides 1–3 (framing + concepts): 8 minutes
- Slides 4–5 (general knowledge platform): 5 minutes
- Slides 6–10 (AI memory + MCP): 10 minutes
- Slides 11–17 (the worked example): 15 minutes — don't compress this;
  it's the section that converts skeptics
- Slides 18–21 (honesty scorecard, mission fit, business fit, next steps):
  7 minutes

If you only have 20 minutes, keep 1–3, 11–17, and 21. Cut everything else
or hand it out as leave-behind reading.

## Anticipated questions and how to answer them honestly

**"Is this cleared for classified environments?"**
No. Say so plainly. It's MIT-licensed, self-hosted, Docker-based software
— the same category of thing your organization already puts through its
own ATO/accreditation process for other self-hosted stacks on classified
networks. Nothing about it is pre-certified for any environment,
classified or otherwise. The honest pitch is "this is a fit for the
environments and accreditation processes you already run," not "this is
already approved for a SCIF or a tactical network."

**"Can it run disconnected, at the tactical edge?"**
Architecturally, yes — it's a single lightweight Docker Compose stack
(a document database plus a small API server), not a large cloud
platform, so running it forward on a single node is a realistic pattern.
Be precise: that's a statement about the architecture's footprint, not a
claim that it's been tested/validated in an actual DIL (disconnected,
intermittent, limited) environment. If asked for field-validated
performance numbers under real DIL conditions, say that hasn't been done
yet rather than improvising a number.

**"How mature is this? What are the production references?"**
Be direct: this is an early-stage platform, not a decade-old incumbent.
The technical proof in Section 11 of the deck is real, runnable syntax
against a real system — that's the credibility you can offer today.
Maturity claims beyond that should come from whoever owns the commercial
relationship, not from this deck.

**"How is this different from Palantir Gotham/Foundry, or Anduril
Lattice?"**
Don't be defensive — the comparison is fair and worth answering plainly.
Those are large, mature, heavily productized platforms with their own
sensor-integration, ops, and mission-command tooling, and a substantial
cost and integration footprint. hgai is a much smaller, focused,
open-source semantic *storage and query* layer — it doesn't compete with
that breadth, and in many environments it's plausible to run *alongside*
an existing Gotham/Lattice-style deployment as a lightweight,
MCP-reachable knowledge layer for a specific AI-agent use case, rather
than as a wholesale replacement. If asked "would you rip out our existing
C2/ISR platform for this," the honest answer is almost always no — that's
not the pitch.

**"How is this different from a vector database we already use for RAG
over intel reporting?"**
A vector store answers "what's similar to this text." hgai answers "what's
structurally and semantically related to this thing, as of when." They're
complementary, not competitive — Section 5's comparison table in the deck
says this directly. If the firm already has a RAG pipeline over reporting,
the pitch is "hgai is where the *distilled, fused conclusions* from that
pipeline should live, not a replacement for the retrieval step."

**"Can an AI agent write bad or hallucinated information into this and
create a false picture?"**
Yes, and don't downplay it — this is the single most important honest
caveat in the whole pitch, and it matters more in this domain than almost
any other. That's exactly why Section 10 of the deck insists on
**provenance and confidence as first-class fields**, and why the worked
example's recommendation hyperedge is explicitly scoped as decision
support for a human, not an automated trigger: an AI-generated hyperedge
is tagged `ai-generated`, attributed to a specific model/session, and
carries a confidence score precisely so a human reviewer can filter,
weigh, or discount it — instead of it silently blending into confirmed
reporting the way an unstructured text summary would. The platform makes
bad or low-confidence writes visible and attributable; it does not, and
should not be pitched as, a system that removes the human from the
decision loop.

**"Does inferencing/reasoning happen automatically, like some knowledge
graph marketing implies?"**
No — and Section 18 of the deck exists specifically to head this off
before someone asks it in front of a government customer later. Say
plainly: SKOS/inverse-relation inferencing is designed into the data
model but not yet wired into query execution. Nothing in the worked
example (Sections 11–17) relies on it. This is a deliberate choice in how
this deck was built — a different internal deck overstated this exact
capability, and it was corrected specifically so nobody in your
organization repeats an inaccurate claim to a federal customer.

**"What if we want to swap the query languages/scenario for our own
domain before we show this internally?"**
Everything in `data/` and `queries/` is small and self-contained on
purpose — the whole scenario is ~9 nodes and ~6 edges. Swapping
"MEDEVAC request / ISR confirmation" for your own domain's N-ary fact
(a sustainment resupply request, a multi-source targeting-track
*deconfliction* record kept at the appropriate classification and venue,
an equipment-readiness report with multiple contributing systems) is a
low-effort adaptation, not a rebuild — talk to your technical team about
scope before adapting the example for a more sensitive domain.

## Delivery notes on the worked example (Sections 11–17)

- Have `specops-rdf-comparison.ttl` and `specops-sql-comparison.sql` open
  in a side-by-side editor if presenting live — the visual density
  difference (one hyperedge vs. a manufactured resource plus a
  `GROUP_CONCAT`, or a four-way join including a bridge table) lands
  harder seen than described.
- The precedence-upgrade / point-in-time beat (Section 16) is the
  strongest moment in the deck for this audience — a request's picture
  changing as new information arrives, without losing the prior state, is
  something everyone who has worked a watch floor or a TOC has lived
  through personally. Let that land before moving on; don't rush to
  Section 17.
- If someone asks to see it actually run (not just read the YAML), that's
  exactly what `demo-alpha/deck-demo-alpha.md` (the engineering-audience
  deck in this repo) is for — offer that as the immediate follow-up
  meeting, not something to attempt cold in this session.
