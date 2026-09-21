---
name: ndim-engine
description: Use this skill to run, sweep, compare and report experiments on the NDIM (Narrative Inoculation Diffusion Model) scientific engine, a deterministic digital twin of how narratives spread and shape adoption of clean cooking and energy in Rwanda. Covers planning reviewable experiments from field notes or interview text, the researcher approval gate, scenario and sensitivity workflows, parameter sweeps, comparing runs, reading the engine's numerical checks, and writing honest reports. Triggers on NDIM, NIDM, narrative inoculation, digital twin, clean cooking adoption, CHW or field narrative simulation, intervention scenario, or sensitivity sweep. Requires the ndim-engine MCP server.
version: 0.1.0
---

# NDIM Engine

## What this is

NDIM turns narrative evidence (interview text, field notes) into structured signals and runs an **illustrative**
S/M/T/I/R compartment model of adoption over time. You drive it through the `ndim-engine` MCP server (tools named
`ndim_*`). The engine is deterministic and allowlisted: **only its own tools produce scientific results**. Your job is to
plan well, get the researcher's approval, run, read results honestly, and never claim more than the engine supports.

Everything the engine outputs is `illustrative_uncalibrated`. It is not a forecast, not a confidence interval, and not
validated against field data.

## Hard rules (never break these)

1. **Never approve on the researcher's behalf.** `ndim_start_experiment`, `ndim_resume_experiment` and `ndim_run_sweep`
   need `approval_statement`: the researcher's own words approving *this* plan, quoted from the conversation. If they
   have not approved, show the plan and ask. Do not paraphrase yourself into an approval.
2. **Never set `consent` above what the researcher told you.** `research_use` only if they confirmed permission to use
   the evidence. `synthetic` only for demo data. Otherwise `unconfirmed`.
3. **Never write, imply or fake a researcher review.** Review is the human's certification. There is no tool for it.
4. **Never present output as a forecast or finding.** Use the wording rules in `references/interpreting-results.md`.
5. **Never repeat an identical run to get "replicates" or "Monte Carlo".** The engine has no randomness; identical
   inputs give identical outputs. Vary parameters instead.
6. **Never translate silently.** The encoder reads English keywords only. Non-English evidence is blocked. If you
   translate, tell the researcher, keep the original, and get their confirmation before planning.
7. **Never copy numbers between tool calls by hand** when a tool can compute them (`ndim_compare_runs`,
   `ndim_run_sweep`). Retyped numbers drift.
8. **Anything you compute yourself in a sandbox is exploratory** and must be labelled so. Only the engine's tools
   produce results that may be called engine results.

Details and rationale: `references/guardrails-and-approval.md`.

## Before you start

1. Call `ndim_engine_status`. If it fails, tell the researcher the engine is not reachable and how to start it
   (`references/troubleshooting.md`). Note `worker_limit` and the `unavailable` list.
2. Call `ndim_list_workspaces` and pick the workspace with the researcher. Runs belong to one workspace.
3. If the evidence is a file, run the preflight (checks length, language, personal data):
   ```bash
   python /mnt/skills/public/ndim-engine/scripts/evidence_preflight.py --file /mnt/user-data/uploads/notes.txt
   ```
   Fix what it flags first (`references/workflows.md`, "Preparing evidence").

## Choose the workflow

| The researcher wants to know | Workflow | Tool |
|---|---|---|
| What signals are in this narrative? | `evidence` | `ndim_plan_experiment` (skill=`evidence`) |
| What changes if we intervene at strength X? | `scenario` (baseline vs intervention) | `ndim_plan_experiment` (skill=`scenario`) |
| How does the endpoint respond across intervention strengths? | `sensitivity` (fixed 3/7/11-point grid) | `ndim_plan_experiment` (skill=`sensitivity`) |
| How does the outcome respond to narrative influence, initial adoption, horizon, or strength together? | parameter sweep | `ndim_plan_sweep` then `ndim_run_sweep` |
| Many interviews or documents, each analysed separately | one experiment per document | see `references/sweeps-and-parallel-work.md` |

Set `skill` explicitly. `auto` guesses from keywords in the question, and "sensitivity" beats "scenario".

## Standard workflow (single experiment)

1. **Plan.** `ndim_plan_experiment(workspace_id, question, evidence, consent, skill, model, ...)`. Nothing runs yet.
2. **Read the plan aloud to the researcher.** Steps, model family, parameters, `warnings`, and any `blockers`.
   Blockers (non-English evidence, `agent_based` with an intervention) must be resolved with a *new* plan.
3. **Get explicit approval.** Ask directly. Wait for the answer.
4. **Run.** `ndim_start_experiment(..., approval_statement="<their words>", wait_seconds=30)`.
5. **Wait if needed.** `ndim_wait_for_run` until `status` is `completed`, `failed`, `cancelled` or `interrupted`.
6. **Read.** `ndim_get_run` (statistics only). Use `include_trajectories=true` only if you must, it is large.
7. **Check.** `numerical_checks.passed` must be true. It proves finite, bounded numbers, nothing more.
8. **Brief.** `ndim_get_brief` returns the engine's Markdown brief, marked as an exploratory draft.
9. **Report** with `references/report-template.md`. Tell the researcher the review step is theirs.

## Parameters

| Parameter | Range | Effect and caution |
|---|---|---|
| `intervention_strength` | 0-1 | The only intervention lever wired into the simulation. 0 must reproduce baseline exactly; use it as a sanity check. |
| `narrative_influence` | 0-1 | Raises adoption in `compartmental`/`hybrid`. Has **no effect** in `agent_based`. |
| `initial_adoption` | 0-1 | Starting adoption share. |
| `horizon_days` | 7-365 | Simulated days. Long horizons can saturate adoption and hide differences (see interpreting-results). |
| `model` | `compartmental`, `agent_based`, `hybrid` | `agent_based` ignores intervention strength and narrative influence. `hybrid` is 55% compartmental + 45% proxy, its compartments describe only the compartmental part. |
| `profile` | `auto`, `economy`, `balanced`, `thorough` | Sensitivity grid density: 3, 7, 11 points. Density gives resolution, not confidence. |
| `language` | `en`, `rw`, `fr`, `other` | Anything but `en` blocks the plan. |
| `prior_run_ids` | up to 3 | Only completed, researcher-reviewed runs. Context only; never alters parameters. |

More: `references/engine-model.md`.

## Sweeps in one paragraph

`ndim_plan_sweep(vary={"narrative_influence": [0.2, 0.6, 0.9]}, mode="one_at_a_time")` creates a base run plus one run per
value, all on identical evidence (max 24). Show the design, get approval, then `ndim_run_sweep(run_ids, approval_statement,
reference_run_id)` runs them within the engine's queue limits and returns the comparison. Read
`comparison.comparability`: it is only *controlled* when the runs differ from the reference in one factor. Full guidance,
including using DeerFlow subagents for many documents: `references/sweeps-and-parallel-work.md`.

## When things go wrong

| Symptom | First move |
|---|---|
| `Cannot reach the NDIM engine` | Engine not running or wrong `NDIM_ENGINE_URL`. `references/troubleshooting.md` |
| 409 "Scientific code changed" | Create a new plan. Checkpoints cannot mix code versions. |
| 422 on plan | Read the field named in the message; limits are in `references/tool-reference.md` |
| Blocked plan | Explain the blocker; do not work around it (`references/workflows.md`) |
| `failed` or `interrupted` | Ask the researcher, then `ndim_resume_experiment` with their approval |
| 429 | The server retries; if it persists, the queue of 8 is full: wait, then retry |

## Reference index (read when relevant)

- `references/engine-model.md`: what the engine computes, compartments, models, parameter provenance, current limitations
- `references/workflows.md`: evidence / scenario / sensitivity in detail, blockers, consent, preparing evidence
- `references/tool-reference.md`: every `ndim_*` tool, arguments, returns, errors
- `references/guardrails-and-approval.md`: the trust boundary, approval, consent, review, audit log
- `references/interpreting-results.md`: reading outputs, saturation, allowed and forbidden claims, example wording
- `references/sweeps-and-parallel-work.md`: parameter sweeps, comparability, subagent fan-out, sandbox analysis
- `references/report-template.md`: the structure for the final write-up
- `references/troubleshooting.md`: errors, recovery, running and debugging the engine and MCP server
- `scripts/evidence_preflight.py`: pre-flight check for evidence files
