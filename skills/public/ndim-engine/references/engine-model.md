# What the engine computes

Source of truth: `nidm-rwanda-dashboard/backend/app/` (`engine_tools.py`, `modelling.py`, `encoding.py`,
`inoculation.py`, `engine_harness.py`). If this file and the code disagree, the code wins; update this file.

## Pipeline

Each run is a plan of allowlisted tools executed in order, checkpointed after every step:

| Step id | Tool | What it does |
|---|---|---|
| `encode` | encode | English **keyword** interpretation of the evidence: `themes`, `sentiment`, `trust_score`, `adoption_barrier_score`, `confidence` (all 0-1 except sentiment -1..1). |
| `diagnose` | diagnose | Heuristic inoculation diagnosis: `threat_type`, `misinformation_mechanism`, `misinformation_risk_score`, `identity_threat_score`, `reactance_risk_score`, `narrative_resilience_score`, susceptible group, trusted messenger, and so on. Always `requires_review`. |
| `baseline` | simulate | Model run at `intervention_strength = 0`. (scenario, sensitivity) |
| `intervention` | simulate | Same run at the requested strength. (scenario, sensitivity) |
| `sweep_0..N` | simulate | One run per grid strength. (sensitivity) |
| `check` | check | Finite values, adoption within 0-1, normalized compartment sums. Fails the run if not passed. |
| `brief` | brief | Markdown bundle of question, evidence, interpretation, assumptions and limitations. |

## Where simulation parameters come from

`parameters(run)` in `engine_tools.py` builds them, and this matters for interpretation:

- From **encoding**: `trust_score`, `barrier_score` (= adoption barrier), `confidence`.
- From **diagnosis**: `misinformation_risk` only.
- From the **request**: `narrative_influence`, `initial_adoption`, `intervention_strength` (per step), `horizon_days`, `model`.
- Everything else uses the model's internal defaults. In particular the inoculation parameters
  (`inoculation_strength`, `reactance_penalty`, `trusted_messenger_fit`, ...) are **not** fed from the diagnosis in this
  harness; they stay 0 in the output rows. `intervention_strength` is the only intervention lever.

So one narrative's keyword scores set the trust and barrier inputs. That is exactly why a single narrative cannot
support population claims.

## Models

### compartmental (the full NDIM model)

Normalized proportions summing to 1 after every step:

| Compartment | Meaning | Output alias |
|---|---|---|
| S | susceptible | |
| M | misinformed | `misinformation` |
| T | truth-aligned | `truth_aligned` |
| I | inoculated | `inoculated` |
| R | durable adoption / resistance | `resistant` |

**`adoption = T + I + R`.** Each row also has `adoption_lower` and `adoption_upper`, a heuristic envelope, **not** a
statistical confidence interval.

The engine normalizes after each step, so the `check` step's "compartment sum = 1" is a post-normalization check,
not evidence that the raw ODE conserved mass.

### agent_based (proxy)

A simple peer/media contact recursion on adoption alone. It does **not** use `intervention_strength` and does **not**
use `narrative_influence`. Consequently the harness blocks it for scenario and sensitivity workflows: a comparison
would show no effect and mean nothing. Fine for `evidence`-only runs.

### hybrid

`adoption = 0.55 x compartmental + 0.45 x agent-based proxy`, same for the band. Reported S/M/T/I/R describe only the
compartmental component. The plan carries a warning saying so. Because 45% of it ignores the intervention, expect
muted intervention effects.

## Determinism and provenance

- No random sampling. `random_seed` is null in the environment manifest with the reason recorded. Same inputs, same code,
  same environment give byte-identical results.
- Every run stores `source_sha256` (hash of the evidence text), `code_version` (SHA-256 of the scientific modules) and an
  environment manifest (Python, platform, numpy/scipy/torch/pyro versions).
- A run cannot be resumed if `code_version` or the environment changed; you must plan again.

## Engine limits

| Limit | Value |
|---|---|
| Question length | 8-1000 characters |
| Evidence length | 20-20000 characters |
| Attempt budget | 30 seconds of tool time per attempt (a full run normally takes well under 1 second) |
| Concurrent execution | `worker_limit` = 1 (constrained host) or 2 |
| Queue | 8 active experiments; more are rejected with 429 |
| Owners | one engine worker per data directory (SQLite exclusive lock) |
| Model-provider calls | none. `remote_calls` and `provider_cost` are always 0 |
| Authentication | none. Workspace IDs are not authorization boundaries |

## What the engine cannot do (`unavailable` in `ndim_engine_status`)

An LLM planner, sandboxed generated code, MCP, LLM subagents, and user authentication. That list describes the engine
itself. You (DeerFlow) supply agents and sandboxes *around* it, but they cannot add capabilities *inside* it.

## Statuses

`planned` -> `queued` -> `running` -> `completed`. Also `cancelling`, `cancelled`, `failed`, `interrupted` (the engine
stopped mid-run; checkpoints remain). `ndim_wait_for_run` treats completed, failed, cancelled, interrupted as terminal.
