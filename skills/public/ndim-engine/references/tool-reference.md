# MCP tool reference (`ndim-engine` server, 14 tools)

Server source: `nidm-rwanda-dashboard/mcp_server/ndim_mcp/server.py`. If a tool list here differs from
`tools/list`, the server wins; `backend/tests/test_ndim_engine_skill.py` fails when they drift.

Tool names are used as is (the DeerFlow config sets `tool_name_prefix: false`).

## Read-only

| Tool | Arguments | Returns |
|---|---|---|
| `ndim_engine_status` | none | `reachable`, `deployment_mode`, `resources` (`cpu_available`, `memory_available_mb`, `recommended_profile`, `worker_limit`, `profiles`, `dependencies`), `planner`, `implemented`, `unavailable`, `access`. No filesystem paths. |
| `ndim_list_workspaces` | none | `workspaces[]`: `workspace_id`, `name`, `description`, `domain`, `countries`, `updated_at` |
| `ndim_list_lessons` | none | The engine's three teaching lessons and a **synthetic** sample field note (`sample`). Use `consent="synthetic"` with it. |
| `ndim_list_runs` | `workspace_id`, `offset=0`, `limit=30` (1-100) | The engine's run listing and `total` |
| `ndim_get_run` | `workspace_id`, `run_id`, `include_trajectories=false` | See "Run summary" |
| `ndim_wait_for_run` | `workspace_id`, `run_id`, `timeout_seconds=60` (0-120) | Run summary once terminal, or current state at timeout |
| `ndim_get_brief` | `workspace_id`, `run_id` | `markdown` of the engine brief and a `notice`. Only for completed runs (409 otherwise) |
| `ndim_compare_runs` | `workspace_id`, `run_ids` (2-24), `reference_run_id?` | `rows`, `excluded`, `comparability`, `markdown_table`, `notice` |

### Run summary (`ndim_get_run`, `ndim_wait_for_run`, start/resume/cancel)

`run_id`, `status`, `question`, `workflow`, `progress` (`completed_steps`, `total_steps`, `pending`), `request`,
`provenance` (`source_sha256`, `code_version`), `recent_events` (last 6), `review`, `warnings`, `notice`, `next` (what to do
now), `encoding` (scalar scores + themes; long text dropped), `inoculation_diagnosis`, `simulations[]` (`step_id`,
`intervention_strength`, `model`, `method_status`, `stats`), `model_parameters`, `comparison`, `numerical_checks`,
`brief_available`.

`stats`: `points`, `initial_adoption`, `final_adoption`, `peak_adoption`, `peak_day`, `final_heuristic_band`,
`final_compartments`. With `include_trajectories=true` each simulation also has the full daily `trajectory`
(about 90 rows x 16 fields). Avoid it unless you need it.

## Plan (writes a plan record only; nothing runs)

### `ndim_plan_experiment`

| Argument | Type / range | Default |
|---|---|---|
| `workspace_id` | slug | required |
| `question` | 8-1000 chars | required |
| `evidence` | 20-20000 chars, English | required |
| `consent` | `synthetic` \| `research_use` \| `unconfirmed` | `unconfirmed` |
| `skill` | `auto` \| `evidence` \| `scenario` \| `sensitivity` | `auto` (set it explicitly) |
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

Returns `run_id`, `status: planned`, `workflow`, `request`, `steps[]`, `sensitivity_grid`, `execution_profile`,
`warnings`, `blockers`, `provenance`, and `next`.

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
| `ndim_start_experiment` | `workspace_id`, `run_id`, `approval_statement`, `wait_seconds=30` (0-120) | Only `planned` runs. Retries on 429. Returns run summary. |
| `ndim_resume_experiment` | same | Only `failed`, `interrupted`, `cancelled`. 409 if code or environment changed. |
| `ndim_run_sweep` | `workspace_id`, `run_ids` (2-24), `approval_statement`, `reference_run_id?`, `wait_seconds=60` | Starts all (4 at a time, queue-aware), waits, compares. Returns `comparison`, `errors`, `still_running`, `next`. One failure does not discard the rest. |

## No approval needed

| Tool | Arguments | Notes |
|---|---|---|
| `ndim_cancel_experiment` | `workspace_id`, `run_id` | Logged. Planned runs cancel immediately; running ones stop at the next tool boundary. |

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
