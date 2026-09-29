# MCP tool reference (`ndim-engine` server, 21 tools)

Server source: `nidm-rwanda-dashboard/mcp_server/ndim_mcp/server.py`. If a tool list here differs from
`tools/list`, the server wins; `backend/tests/test_ndim_engine_skill.py` fails when they drift.

Tool names are used as is (the DeerFlow config sets `tool_name_prefix: false`).

## Read-only

| Tool | Arguments | Returns |
|---|---|---|
| `ndim_engine_status` | none | `reachable`, `deployment_mode`, `resources` (`cpu_available`, `memory_available_mb`, `recommended_profile`, `worker_limit`, `profiles`, `dependencies`), `planner`, `implemented`, `unavailable`, `access`. No filesystem paths. |
| `ndim_list_workspaces` | none | `workspaces[]`: `workspace_id`, `name`, `description`, `domain`, `countries`, `updated_at` |
| `ndim_list_lessons` | none | The engine's three teaching lessons (tutorials), each with a `link` to it in the web app, and a **synthetic** sample field note (`sample`). Use `consent="synthetic"` with it. |
| `ndim_list_runs` | `workspace_id`, `offset=0`, `limit=30` (1-100) | What has been run: rows of `title`, `skill`, `status`, `created_at`, `reviewed`, `lesson_id` (**no run ids**, on purpose), `total`, and `next`. Each row has `matching_tutorial` (`lesson_id`, `title`, `teaches`, `duration`, `link`) for its workflow. These are existing runs: never present one as an answer; offer its tutorial instead, and a new plan for the researcher's own question |
| `ndim_get_run` | `workspace_id`, `run_id`, `include_trajectories=false` | See "Run summary" |
| `ndim_wait_for_run` | `workspace_id`, `run_id`, `timeout_seconds=60` (0-120) | Run summary once terminal, or current state at timeout |
| `ndim_get_brief` | `workspace_id`, `run_id` | `markdown` of the engine brief, `question`, `created_at`, `matching_tutorial`, a `notice`, `reporting_rules` and `next`. For a run not planned in this conversation, `next` says to offer the tutorial instead of the brief; for one planned here, it carries the same report instructions as `ndim_get_run`. Only for completed runs (409 otherwise) |
| `ndim_compare_runs` | `workspace_id`, `run_ids` (2-24), `reference_run_id?` | `rows`, `excluded`, `comparability`, `markdown_table`, `notice`. Each row carries `shape`, `fastest_growth_day`, and `peak_day` (empty unless `peaks_before_end`) |

### Run summary (`ndim_get_run`, `ndim_wait_for_run`, start/resume/cancel)

`run_id`, `status`, `question`, `workflow`, `progress` (`completed_steps`, `total_steps`, `pending`), `request`,
`provenance` (`source_sha256`, `code_version`), `recent_events` (last 6), `review`, `warnings`, `notice`, `next` (what to do
now), `encoding` (scalar scores + themes; long text dropped), `evidence_signals` (a ready-made sentence on the encoded
trust, barrier and misinformation inputs; report it after the headline; a list is fine if
every number and the caveat stay), `inoculation_diagnosis`, `simulations[]` (`step_id`,
`intervention_strength`, `model`, `method_status`, `stats`), `model_parameters`, `comparison`, `numerical_checks`,
`brief_available`. For a scenario, `comparison.baseline_vs_intervention` includes `headline`: a ready-made, non-causal
sentence with both endpoints and the delta in percentage points. Quote it rather than rewording the numbers. `conclusion` is the matching closing sentence; quote it too.

`stats`: `points`, `initial_adoption`, `final_adoption`, `shape` (`rises_to_end`, `peaks_before_end` or `flat`),
`fastest_growth_day` and `fastest_growth` (largest one-step rise, absent if adoption never rises), `final_heuristic_band`,
`final_compartments` with `compartment_names` (S susceptible, M misinformed, T truth-aligned, I inoculated, R durable adoption belief; use these names, never others). `peak_adoption` and `peak_day` appear only when `shape` is `peaks_before_end`: when adoption rises
to the last day, the maximum is just the endpoint, so there is no peak to report. With `include_trajectories=true` each simulation also has the full daily `trajectory`
(about 90 rows x 16 fields). Avoid it unless you need it.

## Plan (writes a plan record only; nothing runs)

### `ndim_plan_experiment`

| Argument | Type / range | Default |
|---|---|---|
| `workspace_id` | slug | required |
| `question` | 8-1000 chars | required; the researcher's words verbatim, never rephrased |
| `evidence` | 20-20000 chars, English | required |
| `skill` | `scenario` \| `sensitivity` \| `evidence` \| `auto` | required; choose it yourself (see SKILL.md, "Choose the workflow"), avoid `auto` |
| `consent` | `synthetic` \| `research_use` \| `unconfirmed` | `unconfirmed` |
| `model` | `compartmental` \| `agent_based` \| `hybrid` | `compartmental` |
| `profile` | `auto` \| `economy` \| `balanced` \| `thorough` | `auto` |
| `horizon_days` | 7-365 | 90 |
| `intervention_strength` | 0-1 | 0.3 |
| `initial_adoption` | 0-1 | 0.1 |
| `narrative_influence` | 0-1 | 0.38 |
| `language` | `en` \| `rw` \| `fr` \| `other` | `en` |
| `expertise` | `guided` \| `researcher` \| `expert` | `guided` |
| `source_name` | 1-240 chars | "Researcher-supplied field note" |
| `prior_run_ids` | up to 3 reviewed, completed runs | none |
| `strength_reason` | 8-400 chars, optional | Why this `intervention_strength`. Quote the researcher only if they gave a value or level; never attribute the default to them. Shown in `intervention_mapping` and kept in the audit log |
| `lesson_id` | `evidence` \| `scenario` \| `sensitivity`, optional | Only to run a tutorial here: `skill` must match the lesson, evidence is the synthetic `sample`. The run counts as that lesson in the web app, where the researcher answers its check |

Returns `run_id`, `status: planned`, `workflow`, `request`, `steps[]`, `sensitivity_grid`, `execution_profile`,
`intervention_mapping` (scenario and sensitivity: how the intervention enters the engine, to state before approval;
`null` for evidence), `warnings`, `blockers`, `provenance`, and `next`.

### `ndim_plan_sweep`

`workspace_id`, `question`, `evidence`, `vary` (`{factor: [values]}`), `consent`, `mode` (`one_at_a_time` default, or
`grid`), `model` (`compartmental` \| `hybrid`), `horizon_days`, `intervention_strength`, `initial_adoption`,
`narrative_influence`, `language`, `source_name`.

- Factors: `narrative_influence`, `initial_adoption`, `intervention_strength` (0-1), `horizon_days` (7-365, whole days).
- At most 12 distinct values per factor and 24 runs total. `one_at_a_time` = base run + each value once (values equal to
  the base are skipped). `grid` = cartesian product.
- Workflow is always `scenario`. Evidence is sent once and reused, so all runs share one `source_sha256`.
- Returns `planned[]` (`run_id`, `label`, `varied`, `blockers`), `n_runs`, `reference_run_id` (one_at_a_time), `shared`,
  `warnings`, `next`. If the first plan has blockers it stops and returns `blocked: true`.

## Execution (approval required)

`approval_statement`: 12-1000 characters, the researcher's own words approving this plan. It is written to the audit log.

| Tool | Arguments | Notes |
|---|---|---|
| `ndim_start_experiment` | `workspace_id`, `run_id`, `approval_statement`, `wait_seconds=30` (0-120) | Only `planned` runs; any other status is refused before the approval is logged, with what to do instead. Retries on 429. Returns run summary. |
| `ndim_resume_experiment` | same | Only `failed`, `interrupted`, `cancelled`. 409 if code or environment changed. |
| `ndim_run_sweep` | `workspace_id`, `run_ids` (2-24), `approval_statement`, `reference_run_id?`, `wait_seconds=60` | Starts all (4 at a time, queue-aware), waits, compares. Returns `comparison`, `errors`, `still_running`, `next`. One failure does not discard the rest. |

## No approval needed

| Tool | Arguments | Notes |
|---|---|---|
| `ndim_cancel_experiment` | `workspace_id`, `run_id` | Logged. Planned runs cancel immediately; running ones stop at the next tool boundary. |

## The 13-stage journey

Full walkthrough and wording: `references/journey.md`. Every journey tool returns the same view: `journey_id`,
`question`, `next_stage`, `progress` (one line per stage with its status), `records` (each with `gate`, `gate_flags`,
`decision`) and `next`. After a stage runs it also has `stage`, `result` (compact: curve `stats`, never full
trajectories), `limits` (what the numbers are not) and, when a re-run cleared later stages, `cleared_later_stages`.

| Tool | Arguments | Notes |
|---|---|---|
| `ndim_journey_guide` | none | The 13 stages (`does`, `needs`, `researcher_decision`, `optional`, `limits`), `principles`, `web_app` link. Read-only |
| `ndim_journey_list` | `workspace_id` | Existing journeys. Continue one only if the researcher confirms it is theirs. Read-only |
| `ndim_journey_start` | `workspace_id`, `question` (verbatim), `country="Rwanda"` | Creates the journey; nothing is scored |
| `ndim_journey_status` | `workspace_id`, `journey_id` | Where it stands. Read-only |
| `ndim_journey_add_evidence` | `workspace_id`, `journey_id`, `records[]` (1-50: `text`, `admin_unit`, `source_name`, `period`, `source_type`, `language`, `consent`) | Stages 1-2: stores each record unchanged and gate-checks it (`eligible`, `review_before_accepting`, `blocked`). Frozen once encoding runs |
| `ndim_journey_record_decisions` | `workspace_id`, `journey_id`, `decisions[]` (`record_id`, `decision` accept\|reject, `reason?`), `approval_statement` | Stage 3: the researcher's decisions in their words. A blocked record cannot be accepted. Audited after the engine accepts |
| `ndim_journey_run_stage` | `workspace_id`, `journey_id`, `stage`, stage settings below, `approval_statement` (digital, policy) | Stages 4-13, in order (409 names the missing stages). Audited after the engine accepts |

`ndim_journey_run_stage` settings: `horizon_days=180` (compartmental, agents, digital); `peer_effect=0.08`,
`media_effect=0.05` (agents); `observed_adoption`, `trust_shift`, `barrier_shift` (digital, required, no defaults),
`observed_series` (digital, optional, 3+ observed values), `feedback_note`; `priors` (bayes: `trust_a`, `trust_b`,
`barrier_a`, `barrier_b`); `regional_mode` (`isolated`\|`grouped`), `regional_target` (`barrier`\|`trust`\|`diffusion`);
`audience`, `tone`, `apply_to_twin=false` (inoculation).

## Deliberately absent

Delete run, save researcher review, create/edit workspace, answer lessons. Those belong to the researcher in the engine UI.

## Errors you will see

Errors arrive as `Error executing tool ...: <message>`.

| Message starts with | Meaning |
|---|---|
| `Cannot reach the NDIM engine at ...` | Engine down or wrong URL |
| `The NDIM engine did not answer within Ns` | Timeout |
| `Invalid workspace_id` / `Invalid run_id` | Not a slug / UUID; rejected before any request |
| `Engine returned 422: ...` | Field validation; the message names the field |
| `Engine returned 409: ...` | Wrong state (already run, code changed, not completed yet) |
| `Engine returned 429: ...` | Queue full after retries |
| `1 validation error for ...Arguments` | Your arguments break the tool schema (for example a short `approval_statement`). No request was sent. |
