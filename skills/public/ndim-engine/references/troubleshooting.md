# Troubleshooting

## Where things run

```
DeerFlow agent --stdio--> python -m ndim_mcp --HTTP--> NDIM engine (uvicorn backend.app.main:app, port 8010)
                                 |                          |
                     ~/.ndim-mcp/audit.jsonl        <NDIM data dir>/workspaces/<ws>/evidence/engine-runs/*.json
```

## Symptoms

| Symptom | Cause | Fix |
|---|---|---|
| `Cannot reach the NDIM engine at http://127.0.0.1:8010` | Engine not running, or wrong `NDIM_ENGINE_URL` in the MCP server's environment (the MCP server, not DeerFlow, connects to the engine) | Start: `uvicorn backend.app.main:app --port 8010 --workers 1` from `nidm-rwanda-dashboard/`. |
| DeerFlow cannot connect to the MCP server at `host.docker.internal:8766` | The gateway runs in Docker: the MCP server must listen on `172.17.0.1`, and a host firewall may block container-to-host ports. See `mcp_server/README.md`, "Firewall caveat". |
| MCP tools missing in DeerFlow | `ndim-engine` is `enabled: false` in `extensions_config.json`, or the server failed to start | Enable it (DeerFlow MCP settings, or `"enabled": true`). If you edited the file by hand, reload or restart DeerFlow. Run `python -m ndim_mcp` by hand with `PYTHONPATH=.../mcp_server` and read stderr. |
| Server starts, then tool calls hang or time out | Engine slow or stuck; DeerFlow `tool_call_timeout` (150 s) shorter than your `wait_seconds` | Use shorter waits and poll with `ndim_wait_for_run`. |
| `1 validation error for ... approval_statement` | Approval missing or under 12 characters | Ask the researcher and quote their words. Do not pad it. |
| 409 `not eligible for this action` | Wrong state: started twice, resuming a completed run, brief of an unfinished run | Read `status` with `ndim_get_run`. |
| 409 `Scientific code changed` / `environment changed` | Engine code or dependencies changed since planning | Create a new plan. Checkpoints cannot mix versions. |
| 422 `Prior context must be a completed run with an explicit researcher review` | `prior_run_ids` includes an unreviewed run | Drop it, or ask the researcher to review it in the UI. |
| 422 with a `loc` such as `evidence` | Field out of range | Check limits in `tool-reference.md`. |
| 429 `execution queue is full` | 8 active experiments | Wait, then retry. `ndim_run_sweep` already retries. |
| 503 `The execution worker is unavailable` | Engine still starting or shutting down | Retry after a few seconds. |
| Run `interrupted` | Engine restarted mid-run | Ask the researcher, then `ndim_resume_experiment`. |
| Run `failed` | A tool raised or the 30 s attempt budget ran out. The engine hides internal details | Resume once. If it fails again, report the run id and events. Do not loop. |
| `RuntimeError: ... requires one server worker per data directory` in engine logs | A second engine or `--workers 2` on the same data dir | Run one worker. Stop the other engine. |
| Plan `blocked` | Language or model issue | See `workflows.md`. |
| Comparison says `controlled: false` | Evidence, code, or several factors differ | Read `notes`. It is information, not an error. |
| No audit file | `NDIM_MCP_AUDIT_LOG=off`, or the home directory is not writable (a warning goes to the server log) | Set a writable path. Work continues without it, so fix it before relying on the log. |

## Checking the pieces independently

```bash
curl -s localhost:8010/health                 # engine up?
curl -s localhost:8010/engine/capabilities    # limits and worker_limit
cd nidm-rwanda-dashboard/mcp_server && python -m pytest -q      # server logic, offline
```

Inspect a run's raw record (engine host): `<data dir>/workspaces/<workspace>/evidence/engine-runs/<run_id>.json`. The data
dir is `NDIM_DATA_DIR`, else `~/.local/share/<app>` on Linux (`ndim_engine_status` does not expose paths).

## Reporting an engine problem

Give: run id, workspace, `status`, `recent_events`, `code_version` prefix, the tool and arguments (without evidence text if
sensitive), and the exact error message. Do not paste raw evidence into a bug report.

## Keeping this skill correct

- Tool names or arguments changed: update `tool-reference.md`; `backend/tests/test_ndim_engine_skill.py` catches missing names.
- Engine behaviour changed (models, limits, planner rules): update `engine-model.md` and `workflows.md`, and re-check the
  numbers in `interpreting-results.md` against a live run.
- New MCP capability or new guardrail: update `guardrails-and-approval.md` and the hard rules in `SKILL.md`.
