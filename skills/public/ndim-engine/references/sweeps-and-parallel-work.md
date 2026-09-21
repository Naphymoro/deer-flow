# Sweeps, comparison and parallel work

## Pick the right kind of parallelism

The engine is fast (a full run takes a fraction of a second) and deterministic. The right tool depends on what varies:

| What varies | Use | Why |
|---|---|---|
| Model parameters on the same evidence | `ndim_plan_sweep` + `ndim_run_sweep` | Server-side fan-out: identical evidence text every time, queue limits respected, deterministic comparison |
| The evidence (many interviews or documents) | DeerFlow subagents via `task` / `batch_task`, one per document | Reading, language checks, translation and preflight are agent work and parallelize well |
| Analysis of results (plots, statistics beyond the engine) | A sandbox | Exploratory, labelled as such |
| Repeats of one identical run | Nothing | Identical output; no information |

Do **not** start one subagent per parameter value. Spinning up a sandboxed agent to make a 0.3-second call adds cost and
lets the evidence text drift between calls. Drift changes `source_sha256` and quietly invalidates the comparison.

## Parameter sweeps

```
ndim_plan_sweep(workspace_id, question, evidence, consent,
                vary={"narrative_influence": [0.2, 0.6, 0.9], "intervention_strength": [0.0, 0.6, 1.0]},
                mode="one_at_a_time")
  -> present design to researcher -> approval
ndim_run_sweep(workspace_id, run_ids=[...all planned...], approval_statement="...", reference_run_id=<from plan>)
```

- **one_at_a_time** (default): one base run plus each value of each factor alone. Every run differs from the base in exactly
  one factor, so differences are attributable. 2 factors x 3 values gives 1 + 6 = 7 runs.
- **grid**: all combinations. Shows interactions but a single run's difference cannot be blamed on one factor. 3 x 3 gives 9.
- Limits: 12 values per factor, 24 runs. Vary only what the question needs.
- Include `intervention_strength = 0` when sweeping strength: it is your built-in consistency check (delta must be 0.0).
- Sweep values are the researcher's design choices. Propose ranges with reasons, but confirm them.

Reading `comparison.comparability`:

| Field | Meaning |
|---|---|
| `varied_factors` | Factors that differ anywhere in the set |
| `controlled` | True only if there are no notes and (with a reference) each run differs from it in at most one factor, or (without) exactly one factor varies |
| `notes` | Why not: different evidence hash, different code versions, different model families, several factors varying |
| `reference_run_id` | The base run used |

If `controlled` is false, say so in the report and do not attribute differences to a single cause.

`errors` lists runs that could not start; `still_running` lists runs not finished within `wait_seconds` (call
`ndim_wait_for_run` on each, then `ndim_compare_runs`); `comparison.excluded` lists runs that ended without a
comparable simulation.

## Comparing runs you already have

`ndim_compare_runs(workspace_id, run_ids, reference_run_id?)` works on any completed runs in a workspace. It flags different
evidence and code versions. Use it instead of transcribing numbers.

## Many documents (subagent fan-out)

Use when the researcher has, say, 12 interview transcripts and wants each encoded and compared.

1. **Lead agent** confirms with the researcher: workspace, consent for these documents, wording of the question, model and
   parameters (identical across documents so differences reflect the evidence).
2. **Lead** runs `evidence_preflight.py` per file, or delegates it.
3. **Subagents** (one per document, `batch_task` with a modest concurrency): read the document, handle language and
   personal data per `workflows.md`, and call `ndim_plan_experiment` with the shared parameters. **They stop at the
   plan** and return `run_id` plus the plan summary. Give them explicit instructions not to start runs.
4. **Lead** shows all plans (or a table of them) and gets one approval from the researcher covering the batch.
5. **Lead** calls `ndim_start_experiment` for each with the researcher's quoted approval (the engine queue holds 8 and
   worker_limit is 1-2; the tool retries on 429, but do not fire more than about 4 at once).
6. **Lead** calls `ndim_compare_runs` on the set. Expect `controlled: false` with a note about different evidence. That is
   correct: the documents differ on purpose. Report the spread of encodings and outcomes, not a single cause.

Subagent prompt essentials: the file path, the exact parameters, "plan only, never start", "never write an approval
statement", "return the run_id and any blockers".

## Sandbox analysis (exploratory)

Sandboxes are for reading files, preflight, writing reports, and analysis code. What they can and cannot see:

- The MCP server runs on the engine host, not in the sandbox. Tool results reach you as text. There is no shared file path.
- Run statistics and comparison tables are small enough to reason about directly, or to paste into a script.
- Full trajectories (`include_trajectories=true`) are large. Only request them for one or two runs, and do not retype them
  into files by hand. If you need bulk trajectory analysis, ask the maintainers for an export tool that writes to a mounted
  directory instead of copying numbers.
- Label anything you compute, plot or fit yourself as **exploratory, not an engine result**, name the method, and keep it
  out of the engine record.

## Concurrency budget

| Limit | Value | What to do |
|---|---|---|
| `worker_limit` | 1-2 (from `ndim_engine_status`) | Runs are serialized behind it. That is fine at these speeds. |
| Queue | 8 active | `ndim_run_sweep` starts 4 at a time and retries on 429 |
| Sweep size | 24 runs | Reduce values or use `one_at_a_time` |
| One engine per data dir | 1 | Never point two engines at the same data directory |
