# Guardrails and approval

## The trust boundary

```
 researcher  ->  you (agent)  ->  ndim_* tools  ->  NDIM engine (allowlisted, deterministic)
   decides        proposes,         guarded,           the ONLY source of engine results
                  explains          audited
```

You may reason, read documents, translate (with permission), write analysis code and draft reports. You may not
manufacture engine results, and you may not take the decisions that belong to the researcher.

## What only the researcher decides

| Decision | Your role |
|---|---|
| Approve a plan (run, resume, sweep) | Present it. Ask. Quote their words in `approval_statement`. |
| Confirm consent to use evidence | Ask. Record what they said. |
| Accept a translation of the evidence | Offer, then wait. |
| Review a completed run (certify it was read and understood) | Tell them it is theirs to do. There is no tool for it. |
| Delete runs, edit workspaces | Not exposed. Refer them to the engine UI. |

## Approval, precisely

- `approval_statement` is required by the tool schema (>= 12 characters). A missing or trivial value is rejected before
  any request is sent.
- It must be **their** words about **this** plan. "The researcher approved" is not their words. "Yes, run the
  narrative-influence sweep on the synthetic sample" is.
- Approval of one plan is not approval of the next. If you change any parameter, re-plan and re-ask.
- If the researcher gave approval earlier in the conversation for the same plan, quoting it is fine.
- For sweeps, approval covers the whole design shown to them, and is logged once per run.
- If the researcher is not available (unattended run), **stop after planning** and return the plan. Do not run.

Honest limit: the server cannot verify that a human said the words. The audit log records what you claimed. Treat a
false `approval_statement` as a serious integrity violation.

## Audit log

Each approval-gated call appends a JSON line to `~/.ndim-mcp/audit.jsonl` on the MCP host (path from
`NDIM_MCP_AUDIT_LOG`, `off` disables): time, tool, workspace, run id, approval statement. Cancels are logged without a statement.
The engine also keeps per-run events (`planned`, `approved`, `tool_started`, ...) in its own run record.

## Evidence handling

- Text you send becomes part of the run record in the workspace on the engine host. Treat it as stored.
- Run `scripts/evidence_preflight.py` and tell the researcher about personal data before planning.
- Do not put secrets, credentials or unrelated documents in `evidence`.
- The engine has no authentication. Do not describe workspace IDs as access control.

## Claims

Rules for what you may say about results are in `interpreting-results.md`. The short version: results are illustrative
model output from keyword encodings of one narrative, useful for exploring assumptions and generating hypotheses.

## Sandbox work

You can spawn sandboxes and subagents; the engine cannot. Rule: **engine results come from `ndim_*` tools. Anything else
you compute is exploratory** and is labelled that way in your report (see `sweeps-and-parallel-work.md`). Never feed
sandbox-computed numbers back into a run as if they were engine outputs, and never edit the engine's code or data
directory from a sandbox to change results.

## Subagents

Subagents inherit these rules. A subagent may prepare (preflight, translate with permission, plan) but starting a run needs
the researcher's approval, so pass an approved plan and their quoted statement down explicitly, or return the plan to the
lead agent for approval. Do not let a subagent write its own approval statement.
