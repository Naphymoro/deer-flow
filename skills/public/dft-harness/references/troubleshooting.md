# Troubleshooting

## The `harness-dft` MCP tools aren't available at all

The server isn't running, isn't reachable from wherever DeerFlow's gateway runs, or is disabled in
`extensions_config.json`. This server imports AiiDA and calls QE binaries directly — unlike `ndim-engine`, there's
no separate "is the engine up" HTTP health check to point at; the tools simply won't be offered. Tell the
researcher to check (on the server's host, inside the `dft-harness` conda env):

```bash
AIIDA_PROFILE=dft-harness verdi status
python -m harness_dft_mcp --transport streamable-http --host <bind-address> --port 8767
```

If DeerFlow's gateway runs in Docker (this workspace's default dev stack does), the MCP entry points at
`http://host.docker.internal:8767/mcp`. `host.docker.internal` resolves to the Docker bridge address
(commonly `172.17.0.1`) inside the container. A host firewall dropping container→host traffic on that port is a
known failure mode in this environment (hit previously with the `ndim-engine` integration) — from inside the
gateway container, even a plain listener on `0.0.0.0` can time out while the host itself is fine. Fixing it needs
root: `ufw allow from 172.16.0.0/12 to any port 8767 proto tcp`, then re-test with
`docker exec -i deer-flow-gateway python -c "import httpx;print(httpx.get('http://host.docker.internal:8767/mcp').status_code)"`
(any HTTP status, even 4xx, means it's reachable).

If DeerFlow runs directly on the host (not Docker), use `stdio` transport instead and point `command` at the
`dft-harness` conda env's Python — see the harness-dft README's "Wire into DeerFlow" section.

## `hd_status().daemon_running` is `false`

`verdi daemon start` (as the `dft-harness` profile, with that conda env's `bin/` on `PATH`) hasn't been run on the
server's host. Every `hd_submit_*` call will succeed (the node gets created) but nothing will ever actually run —
`hd_wait_for_job` will just time out repeatedly. This harness's MCP tools cannot start the daemon themselves (no
tool for it, deliberately — daemon lifecycle is host administration, not a per-conversation action). Tell the
researcher to start it on that host.

## `hd_submit_*` raises about a missing code

`code_label` doesn't match a registered `orm.InstalledCode` (local) or the wrong one for the chosen target
(local vs. `local-gpu` vs. remote). Call `hd_status` and check `codes` for the exact label — labels follow
`<name>-<version>@<computer>`, e.g. `pw-7.5@localhost` or `pw-remote@my-cluster`.

## `hd_validate_pseudo_coverage` reports missing elements

The named family doesn't have every element the structure needs. Do not substitute a different element's
pseudopotential or fabricate coverage — either pick a family that does cover it (check `hd_list_pseudo_families`)
or tell the researcher that element needs a pseudopotential installed on the server host
(`aiida-pseudo install ...`, see the harness-dft README/`dft-pseudo-select` package-level skill).

## A submitted job's `exit_status` is nonzero

`hd_get_job_results` raises with the exit status and exit message, which is often enough (e.g. walltime exceeded,
convergence not reached within the allowed steps). For the full AiiDA process report (scheduler stderr/stdout,
retry history), there is no MCP tool for it yet — ask the researcher to run `verdi process report <pk>` on the
server host, or note it as a follow-up if this comes up often.

## Numbers look wrong / suspiciously perfect

Check `output_parameters.convergence_info.scf_conv.convergence_achieved` is `true` first — an unconverged SCF
still returns an `energy` field, but it isn't physically meaningful. This is a QE/AiiDA-level output, not
something this harness adds a separate check for.
