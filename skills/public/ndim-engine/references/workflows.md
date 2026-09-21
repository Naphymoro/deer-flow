# Workflows in detail

## How the engine picks a workflow

`skill="auto"` lowercases the question and checks, in this order:

1. contains `sensitivity`, `sensitive` or `sweep` -> **sensitivity**
2. contains `scenario`, `compare`, `intervention`, `what if` or `adoption change` -> **scenario**
3. otherwise -> **evidence**

A question like "sensitivity of the scenario..." becomes a 13-step sensitivity run. **Always set `skill` explicitly.**

## evidence (4 steps)

`encode`, `diagnose`, `check`, `brief`. No simulation. Use it to see what the keyword encoder and inoculation heuristic
extract, before deciding whether a simulation is worth running. Any model family is allowed.

## scenario (6 steps)

Adds `baseline` (strength 0) and `intervention` (your strength). Every other input is identical, so the only difference is
`intervention_strength`. Result: `comparison.baseline_vs_intervention` with the endpoint difference.

Sanity check: rerun with `intervention_strength=0`. Baseline and intervention must match (delta 0.0). If not, stop and
report it.

The difference is between two illustrative model endpoints. It is not an estimated treatment effect.

## sensitivity (6 + grid steps)

Adds baseline, intervention and one `sweep_i` per grid point, evenly spaced over 0-1:

| profile | grid points |
|---|---|
| economy | 3 (0, 0.5, 1) |
| balanced | 7 |
| thorough | 11 |

`profile="auto"` picks economy on a constrained host (fewer than 2 CPUs, or under 2 GB free) else balanced. Result:
`comparison.sensitivity_curve`. It shows response to *intervention strength only*. Other parameters stay fixed. For other
factors use a parameter sweep (`sweeps-and-parallel-work.md`).

## Blockers (the plan cannot run)

| Blocker | Cause | Right response |
|---|---|---|
| "English keywords ... supply an explicitly translated English source" | `language` is not `en` | Do not relabel the language as `en` to get past it. Follow "Translation" below. |
| "agent-based proxy does not use intervention_strength" | `model=agent_based` with scenario or sensitivity | Use `compartmental` or `hybrid`. The engine will not substitute a model for you. |

Blockers do not depend on the numeric parameters, so re-planning with different values will not clear them.

## Consent

| `consent` | When | Effect |
|---|---|---|
| `synthetic` | demo or teaching data such as `ndim_list_lessons().sample` | none |
| `research_use` | the researcher confirmed permission to use this evidence | none |
| `unconfirmed` (default) | anything else | plan warning: confirm research use before retaining or sharing |

Ask if unsure. Real interview text about people in Rwanda is `unconfirmed` until the researcher says otherwise.

## Preparing evidence

Run `scripts/evidence_preflight.py` first. It reports character count against the 20,000 limit, likely language,
and personal-data patterns. What to do with the results:

- **Too long (over 20,000 characters).** Split at paragraph boundaries (`--split-dir`) and plan one experiment per chunk,
  or condense with the researcher's agreement. Never silently truncate. Truncation changes `source_sha256` and the science.
- **Personal data** (emails, phone numbers incl. `+250`, 16-digit national IDs). Tell the researcher. The engine persists
  the evidence text in the workspace. Redact only with their agreement and record that you did.
- **Language.** See below.
- **Too short.** Under 20 characters is rejected; under a few sentences the encoder has little to work with.

### Translation

The encoder only understands English keywords. If the evidence is Kinyarwanda or French:

1. Tell the researcher the engine cannot score it as is.
2. Offer to translate, and say translation is an interpretive step that changes the evidence.
3. Keep the original text and your translation together, and note in `source_name` that it is an agent translation
   (e.g. `"Interview 3 (agent translation from Kinyarwanda, unreviewed)"`).
4. Get the researcher to confirm or correct the translation, then plan with `language="en"`.

## Prior context

`prior_run_ids` accepts up to 3 runs that are `completed` and carry a researcher review. They are attached as context
notes only and never change model parameters. If none has a review you cannot use them, and you cannot create the review.

## Cancelling, resuming

`ndim_cancel_experiment`: in-flight tools finish first, completed steps are kept. `ndim_resume_experiment` continues from
checkpoints after `failed`, `interrupted` or `cancelled`, needs approval again, and fails with 409 if the code or environment
changed (then plan again).
