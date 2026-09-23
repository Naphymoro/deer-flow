---
name: dft-harness
description: Use this skill to run Quantum ESPRESSO DFT calculations (relaxation, equation of state, convergence, band structure/DOS, phonons, NEB barriers) through harness-dft, a resource-adaptive orchestration layer on AiiDA + ASE. Covers asking whether to run locally or on remote HPC before planning, resource-adaptive mpiprocs/npool/walltime (CPU allocation in batches of 8), GPU offload routing, pseudopotential family selection from the full installed SSSP library, remote cluster setup, and reading results honestly with AiiDA provenance. Triggers on DFT, Quantum ESPRESSO, QE, pw.x, structure relaxation, equation of state, bulk modulus, band structure, density of states, phonon dispersion, NEB barrier, pseudopotential, or "run this on the cluster"/"run this locally". Requires the harness-dft MCP server.
version: 0.1.0
---

# harness-dft

## What this is

`harness-dft` wraps a real Quantum ESPRESSO install with AiiDA (provenance, retry/error-handling, remote
submission) and ASE (structure building, the one workflow — NEB — that doesn't need provenance). It is not a DFT
engine of its own; QE does the physics. What this harness adds is **resource-adaptive job sizing**: before any
calculation runs, it estimates memory/bands/plane-waves from the structure and picks mpiprocs, npool and walltime
automatically, and decides whether the job belongs on this machine, on a GPU, or on a remote cluster. You drive it
through the `harness-dft` MCP server (tools named `hd_*`).

Every `hd_submit_*` tool returns an AiiDA node `pk` immediately — it does not block for the run. DFT jobs take
minutes to hours; poll with `hd_wait_for_job`/`hd_get_job` rather than expecting one call to finish it.

## Hard rule #1: ask local vs. remote HPC before planning anything

**Never assume the execution target.** The very first thing to do in any DFT conversation is:

1. Call `hd_status`. It reports this machine's CPU count, RAM, GPU (if any, with name/VRAM), whether a GPU-enabled
   QE code is registered, the installed pseudopotential families, and any remote computers already configured.
2. Show the researcher what's available and ask directly: **"Should this run on this machine, or on a remote HPC
   cluster?"** If a GPU is present and `gpu_code_registered` is true, mention GPU as a third option for jobs above
   a small-system threshold (see `references/gpu-and-remote.md`).
3. If they say remote and no computer is configured for their cluster yet, walk them through
   `hd_setup_remote_computer` / `hd_register_remote_code` — this needs the researcher's own hostname, username,
   scheduler, and QE module path. **Never guess or invent cluster details**; if they don't know them, have them run
   `ssh <cluster> 'module load <qe-module> && which pw.x'` and report back.
4. Only after this is settled, call `hd_estimate` and proceed. `allow_remote`/`allow_gpu` on every tool are opt-in
   flags reflecting this choice — they don't default to true.

This mirrors how the underlying resource estimator actually works: it only *recommends* a target
(`local`/`local-gpu`/`remote`); it never silently sends a job somewhere the researcher didn't choose.

## Before every calculation

1. `hd_status` (if not already called this conversation, or if hardware/config may have changed).
2. `hd_estimate` on the structure — show the researcher the job size (atoms, estimated memory, plane waves) and the
   resource plan (target, mpiprocs, npool, walltime) **before** submitting. If `plan.target` doesn't match what the
   researcher chose in the local/remote question, say so and ask how to proceed (a job that "fits locally" but the
   researcher wants on the cluster anyway is their call, not an error).
3. `hd_validate_pseudo_coverage` for the structure against the pseudo family you intend to use. A missing element
   fails here with a clear message instead of deep inside a submitted QE job.

## Resource allocation model

- **CPU targets (`local`, `remote`) are quantized to whole batches of `cpu_batch_size` CPUs (default 8).** A
  2-atom job on a 24-core machine still gets 8 ranks, not 2 — QE's per-rank overhead makes single-digit rank counts
  inefficient, and real clusters schedule in socket/NUMA-node-sized chunks anyway, not individual cores. A 30-core
  request on a 24-core machine gets all 24 (3 batches), not more than what's there.
- **GPU targets use one MPI rank per GPU**, not a CPU batch — that's QE-GPU's supported parallelization model.
  GPU is only recommended above a minimum atom count (`gpu_min_atoms`, default 8; kernel-launch overhead isn't
  worth it below that) and only if the job's estimated memory fits GPU VRAM, not just host RAM.
- None of this is exact. AiiDA's `PwBaseWorkChain` already resubmits automatically with more walltime/resources on
  out-of-walltime or diagonalization errors — the harness's job is to not start absurdly wrong, not to predict
  exactly. Never present a resource plan as a guarantee.

Full detail: `references/gpu-and-remote.md`.

## Choosing pseudopotentials

The full SSSP 1.3 library is installed: `SSSP/1.3/{PBE,PBEsol}/{efficiency,precision}` (call
`hd_list_pseudo_families` to confirm what's actually present in this profile — it may have grown since this skill
was written). **PBEsol is the default functional inside `get_builder_from_protocol()`'s own `fast`/`moderate`/
`precise` protocols** — pass `pseudo_family_label` explicitly on every `hd_submit_*` call, matching whichever
functional the researcher's structure/comparison actually needs. Mixing a PBE-relaxed structure with PBEsol
pseudopotentials for production numbers is a correctness bug, not a style choice.

## Choosing the workflow

| The researcher wants | Tool(s) |
|---|---|
| Relax a structure's geometry | `hd_submit_relax` |
| Equilibrium volume, bulk modulus, E-V curve | `hd_submit_scf` once per volume scaling, compare energies yourself (no separate EOS tool — see `references/tool-reference.md`) |
| Confidence that ecutwfc/k-mesh isn't an artifact | `hd_submit_scf` once per cutoff/mesh value, compare energy-per-atom deltas |
| Band structure / band gap | `hd_submit_bands` (needs an already-relaxed structure) |
| DOS / PDOS | `hd_submit_pdos` (needs an already-relaxed structure, pw+dos+projwfc codes) |
| Phonon dispersion / dynamical stability | `hd_submit_ph` → `hd_submit_q2r` → `hd_submit_matdyn`, chained by pk |
| Reaction/diffusion barrier | `hd_submit_neb` (ASE-native, no AiiDA provenance — mark results exploratory) |

## Reading results honestly

- Always check `hd_get_job`'s `is_finished_ok` before reading `hd_get_job_results`. A `finished` process_state with
  nonzero `exit_status` is a **failed** calculation, not a completed one.
- `output_parameters.convergence_info.scf_conv.convergence_achieved` — check this is `true` before trusting
  `energy`/`forces`/`stress` from any SCF-family result.
- NEB results (`hd_submit_neb`/`hd_get_neb_job`) are not AiiDA-tracked and live only in the MCP server's memory for
  that process's lifetime. Label them exploratory in any report, per the harness's own ASE/AiiDA layering choice.
- Never claim a number is final from a job that hasn't reached a terminal state (`hd_get_job.is_terminal`).

## When things go wrong

| Symptom | First move |
|---|---|
| `hd_status` unreachable / tool call fails entirely | The MCP server isn't running, or the AiiDA profile/daemon isn't up on its host. `references/troubleshooting.md` |
| `hd_status.daemon_running` is false | Nothing submitted will ever start. Needs `verdi daemon start` on the server's host — tell the researcher, this harness can't start its own daemon from inside a tool call. |
| `hd_validate_pseudo_coverage` reports missing elements | Install the missing family/element coverage rather than working around it; do not substitute a different element's pseudopotential. |
| A submitted job's `exit_status` is nonzero | Read `hd_get_job_results`' error, or ask the researcher to check the AiiDA report (`verdi process report <pk>`) on the server host — this MCP surface doesn't expose full process reports. |
| Job stuck in `waiting`/`running` far longer than `hd_estimate`'s walltime | Keep polling with `hd_wait_for_job`; AiiDA's own error handlers resubmit automatically on out-of-walltime, this is not necessarily stuck. |

## Reference index

- `references/gpu-and-remote.md`: full detail on GPU routing thresholds, remote computer setup, and known
  unverified paths (GPU-built QE code, live SSH clusters).
- `references/tool-reference.md`: every `hd_*` tool, arguments, returns.
- `references/troubleshooting.md`: server not reachable, daemon not running, common AiiDA errors.
