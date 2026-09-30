# Guiding the 13-stage journey

The journey takes a researcher from their own field evidence to a policy draft, the same 13 stages as the NDIM
workbench (`/classic-workbench`), run server-side by the engine. Use it when the researcher wants the whole path. For a
single question about one narrative, the experiment workflow in `SKILL.md` is shorter.

| Phase | Stages | The researcher decides |
|---|---|---|
| Evidence | 1 Narrative intake, 2 SDMX gate, 3 Repository | accept or reject each record (stage 3) |
| Encode | 4 Encoding | |
| Model | 5 Compartmental model, 6 Agent-based model | |
| Twin | 7 Digital twin, 8 Bayesian update, 9 RL optimizer | their field observations (stage 7) |
| Strategy | 10 Regional analysis (optional), 11 Knowledge graph, 12 Inoculation lab | |
| Export | 13 Policy output | approve the export (stage 13) |

## How to guide

1. `ndim_journey_guide`, then describe the journey in a few sentences: the six phases, and all three decision points
   (stages 3, 7 and 13). Ask for their question if they have not given one.
2. **Confirm the question.** Show it back in quotes, exactly as you will pass it, and ask the researcher to confirm or
   correct it. Do not add "in Rwanda" or any other context; the country has its own field.
3. `ndim_journey_start` with the question **verbatim** and their reply as `question_confirmation` (audited).
4. **Intake (1-2).** Ask for their stories or field notes. For each: the text unchanged, the place (`admin_unit`), who or
   what it came from (`source_name`), when (`period`), the language, and whether they have permission to use it
   (`consent`). Ask for what is missing; never guess a period or a place. One record per story. Call
   `ndim_journey_add_evidence`; the SDMX gate runs on each record.
5. **Repository (3).** Show each record with its gate result and flags (personal data, instruction-like text, short
   text, duplicates, consent). Ask the researcher to accept or reject each one. Call `ndim_journey_record_decisions` with
   their words. A `blocked` record (for example non-English) cannot be accepted: explain why.
6. **Stages 4-13, one at a time.** Before each stage, say what it does in one sentence and ask whether to continue.
   After it, explain the `result` in plain words with its `limits`. Follow the tool's `next`.
7. **Digital twin (7).** Ask for their field observations: the adoption share they observed (0-1), any change in trust
   and in barriers they saw (-1 to 1, 0 if none), and optionally an observed adoption series over time (3+ values). There
   are no defaults. If they have no observations, say the digital twin and the stages after it cannot run without them,
   and stop there or skip to what does not depend on it (regional analysis, knowledge graph).
8. **Policy output (13).** Ask them to approve the export in their own words.

Stages must run in order; a 409 names the stages still missing. Re-running a stage clears the later stages that read
it (`cleared_later_stages`): say so and run them again if the researcher wants. Evidence and decisions are frozen once
encoding runs; to change them, start a new journey.

One journey per question. Copy `journey_id` exactly from the last journey result. If a call rejects the id, the
error names the journey you meant: use that id. The journey and its stages are intact; never start a new journey or
re-enter the evidence to recover.

## What each stage's numbers are

| Stage | Say | Never say |
|---|---|---|
| 2 SDMX gate | "The gate flagged a phone-like number in record 2." | that the gate checked whether a record is true |
| 4 Encoding | "The keyword heuristic scored these records 0.62 on trust." | measured trust in the community |
| 5-6 Models | "In the illustrative model, adoption is 0.41 at day 180." | adoption will reach 0.41 |
| 7 Digital twin | "Re-run from your observed adoption of 0.2." | the model is now fitted or calibrated |
| 8 Bayesian | "The signal priors moved to 0.61 trust; the pseudo-trial count is a tool convention." | a posterior interval from field data, unless they gave an observed series |
| 9 RL | "Under the tool's fixed assumed effects, consumer_subsidy ranks first." | that consumer subsidies would work or should be chosen |
| 10 Regional | "The tool's threshold rule labels Niboye 'reduce practical friction first' (barrier > 0.48)." | that Niboye needs that intervention |
| 11 Graph | "Cost and trust risk occur together in Gatenga's records." | that cost causes low trust |
| 12 Inoculation | "Three message drafts, for your review before any use." | that the messages would work; the curves are a fixed lift formula |
| 13 Policy | "Evidence grade D: do not use for policy yet." Options for discussion. | recommendations |

The reporting rules of the experiment workflow apply to every stage (`references/interpreting-results.md`): no causal
verbs, no recommendations, no "validated", no peak unless `stats.shape` is `peaks_before_end`.

## Where it differs from the workbench

The journey never invents evidence, so it is stricter than the browser workbench in four places:

- The digital twin has no default observations (the workbench pre-fills 0.48 observed adoption).
- The Bayesian stage never fits model output as if it were observations; it fits only a series the researcher gave.
- The RL stage is a deterministic ranking under disclosed assumed effects, not a random exploration.
- Only the rule-based English encoder runs; no remote AI model sees the evidence.

Journeys live in the engine workspace. Their full outputs, including every curve, are at
`GET /engine/workspaces/{workspace}/journeys/{journey_id}?full=true` for sandbox analysis; anything you compute from
them is exploratory.
