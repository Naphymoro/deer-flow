# GPU routing and remote HPC, in detail

## GPU routing

`hd_estimate`/every `hd_submit_*` accept `allow_gpu=True` to opt into GPU recommendation. Even then, the
estimator (`harness_dft.estimate.choose_resources`) only recommends `target="local-gpu"` when **all** of:

- `allow_gpu=True` was passed (the researcher chose it — never default this on),
- a GPU is actually visible (`hd_status().local_resources.gpu_count > 0`),
- the job fits within the local RAM/atom-count comfort thresholds (GPU doesn't rescue a job that's already too
  big for the machine in other ways),
- estimated memory fits within 70% of the GPU's VRAM (`gpu_memory_gb`), not just host RAM,
- the structure has at least `gpu_min_atoms` atoms (default 8) — below that, kernel-launch overhead usually isn't
  worth the offload.

When it recommends GPU, `mpiprocs` in the returned plan equals the GPU count (one MPI rank per GPU — QE-GPU's
supported parallelization model), **not** a CPU-batch multiple. `code_label` on the `hd_submit_*` call must still
point at an actual CUDA-built QE code registered in AiiDA (check `hd_status().gpu_code_registered` /
`hd_status().codes` for one whose label suggests it, e.g. `pw-7.5-gpu@localhost`) — `choose_resources` only
recommends the resource shape, it never swaps which code a builder uses.

**Known gap as of this skill's writing:** the GPU-built QE code was still being built via NVIDIA's HPC SDK
(`nvfortran`/CUDA Fortran) when this integration was put together, and had not yet been verified against a live
GPU run. Treat the first real GPU submission as validation, not a known-good path — watch for exit codes related
to CUDA-aware MPI or device visibility, and fall back to `allow_gpu=False` if it fails.

## Remote HPC, in detail

`harness_dft.remote` is deliberately cluster-agnostic — nothing about any specific cluster's hostname, scheduler,
or module system is hardcoded, and `hd_setup_remote_computer`/`hd_register_remote_code` never guess these. Before
calling them:

1. **Verify SSH works outside AiiDA first**: have the researcher confirm `ssh <username>@<hostname> echo ok`
   succeeds. `hd_setup_remote_computer` assumes key-based auth already works; it does not set up keys.
2. **Confirm the scheduler** (`slurm` is the default; `pbspro`/`sge`/`torque` are also supported) — ask the
   researcher, or have them check `sinfo`/`squeue` availability on the cluster.
3. **Get the exact remote executable path and any module-load lines** (`prepend_text`) from the researcher, e.g.
   `ssh <cluster> 'module load quantum-espresso/7.2 && which pw.x'`. `remote_executable_path` in
   `hd_register_remote_code` must be the path *after* those module-loads run, or jobs fail at submission with a
   scheduler-side "command not found", not a clear AiiDA-side error.
4. This whole remote path (`harness_dft.remote`) was built and reviewed against `aiida-core`'s SSH transport
   source but **never tested against a live SSH connection or scheduler**. Treat the first real remote submission
   as the actual validation, and warn the researcher accordingly.
5. `choose_resources`'s generic remote mpiprocs default (`min(n_kpoints * 4, 128)`, then quantized to
   `cpu_batch_size`) is a placeholder, not tuned to any real cluster's node topology. Once a researcher's cluster
   is configured, prefer setting `metadata.options.resources` to match its actual node size rather than trusting
   this default for production remote jobs — this MCP surface doesn't expose that override yet; flag it as a
   follow-up if it matters for their cluster.

## CPU batching rationale

`cpu_batch_size` (default 8) exists because real HPC schedulers allocate in socket/NUMA-node-sized chunks, and
QE's MPI communication pattern (band/k-point/plane-wave parallelization layers) is inefficient at single-digit
rank counts anyway. `choose_resources` rounds *up* to the next whole batch for small jobs (so even a 2-atom
structure gets one full batch's worth of ranks) and caps at whatever the machine/allocation actually has — a
24-core machine never gets asked for 32. Change `cpu_batch_size` per-call if the target machine's actual
socket/node size differs from 8 (e.g. a cluster with 16-core nodes).
