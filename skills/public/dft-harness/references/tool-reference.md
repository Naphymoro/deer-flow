# Tool reference

All structures are passed as inline text (`structure_text`) plus an ASE format name (`structure_format`, e.g.
`"cif"`, `"vasp"`, `"extxyz"`, `"xyz"`, `"json"`) — never a file path. The MCP server may run on a different
machine/filesystem than your sandbox, so read the structure file yourself and pass its content through.

## Status / discovery (read-only)

- **`hd_status()`** — local CPU/RAM/GPU (name, count, VRAM), `daemon_running`, installed pseudo families,
  registered codes (label, plugin, computer), configured computers, `gpu_code_registered`. Call first, every
  session.
- **`hd_list_pseudo_families()`** — labels of every aiida-pseudo family actually installed.

## Estimate / validate (read-only, no submission)

- **`hd_estimate(structure_text, structure_format, pseudo_family_label="SSSP/1.3/PBE/efficiency", ecutwfc_ry=40.0, kpoints_mesh=(4,4,4), allow_remote=False, allow_gpu=False, cpu_batch_size=8, local_atom_ceiling=40)`**
  → `{job: {n_atoms, n_electrons, n_bands, n_kpoints, estimated_pw_per_kpoint, estimated_memory_gb}, plan: {target, mpiprocs, npool, walltime_seconds, reason, cpu_batch_size}, is_likely_metal}`.
  Show this to the researcher before any `hd_submit_*` call.
- **`hd_validate_pseudo_coverage(structure_text, structure_format, pseudo_family_label)`** →
  `{covered: bool, missing: [symbols], message?}`.

## Job polling (read-only, generic across every hd_submit_* below)

- **`hd_get_job(pk)`** → `{pk, label, process_state, exit_status, is_finished_ok, is_terminal, daemon_running}`.
- **`hd_wait_for_job(pk, timeout_seconds=60)`** — polls up to `timeout_seconds` (max 600 per call); call repeatedly
  for long jobs.
- **`hd_get_job_results(pk)`** — plain-dict output namespace of a finished, successful job, recursing into
  namespaced sub-outputs (e.g. `PdosWorkChain`'s outputs come back as `results["dos"]["output_dos"]`, not dropped
  or flattened). Raises if not finished or not `is_finished_ok` — check `hd_get_job` first. Non-Dict/scalar
  outputs (structures, folders, trajectories) come back as `{node_type, pk, uuid}` references rather than full
  content.

## Submit (write, needs researcher's local-vs-remote decision already made)

- **`hd_submit_relax(structure_text, structure_format, code_label, pseudo_family_label, protocol, kpoints_mesh, ecutwfc_ry, allow_remote, allow_gpu, cpu_batch_size, local_atom_ceiling)`**
  → `{pk, plan}`. `PwRelaxWorkChain`.
- **`hd_submit_scf(structure_text, structure_format, code_label, pseudo_family_label, protocol, kpoints_mesh, ecutwfc_ry, allow_remote, allow_gpu, cpu_batch_size, local_atom_ceiling)`**
  → `{pk, plan, cell_volume_ang3}`. `PwBaseWorkChain` single point. The building block for EOS (submit once per
  volume-scaled structure, compare `output_parameters.energy`) and convergence sweeps (submit once per
  ecutwfc/k-mesh, compare energy-per-atom deltas) — there is no separate EOS/convergence tool; compose from this.
- **`hd_submit_bands(structure_text, structure_format, code_label, pseudo_family_label, protocol, kpoints_mesh, ecutwfc_ry, allow_remote, allow_gpu, cpu_batch_size, local_atom_ceiling)`**
  → `{pk, scf_plan, bands_plan}`. `PwBandsWorkChain` (SCF + seekpath auto k-path). Structure must already be relaxed.
- **`hd_submit_pdos(structure_text, structure_format, pw_code_label, dos_code_label, projwfc_code_label, pseudo_family_label, protocol, kpoints_mesh, ecutwfc_ry, allow_remote, allow_gpu, cpu_batch_size, local_atom_ceiling)`**
  → `{pk, scf_plan, nscf_plan}`. `PdosWorkChain`. Structure must already be relaxed. `allow_gpu`/`cpu_batch_size`
  only affect the scf/nscf pw.x sub-steps — `dos_code_label`/`projwfc_code_label` pointed at a GPU-built code
  selects it, but dos.x/projwfc.x get no adaptive resource plan at all (pre-existing, not GPU-specific). Results
  are namespaced: `dos.output_dos`, `projwfc.Dos`, `projwfc.Pdos`, `projwfc.projections`, `nscf.output_band`, etc.
- **`hd_submit_ph(parent_scf_pk, ph_code_label, structure_text, structure_format, pseudo_family_label, ecutwfc_ry, qpoints_mesh, protocol, is_metal, allow_remote, allow_gpu, cpu_batch_size, local_atom_ceiling)`**
  → `{pk, plan}`. Step 1/3 of phonons: DFPT from a **finished** SCF/relax pk.
- **`hd_submit_q2r(ph_pk, q2r_code_label)`** → `{pk}`. Step 2/3: force constants from a **finished** `hd_submit_ph` pk.
- **`hd_submit_matdyn(q2r_pk, matdyn_code_label, dispersion_kpoints_mesh=(8,8,8))`** → `{pk}`. Step 3/3: interpolated
  dispersion on a q-point mesh from a **finished** `hd_submit_q2r` pk. Mesh only — no high-symmetry path yet.
- **`hd_submit_neb(initial_structure_text, initial_structure_format, final_structure_text, final_structure_format, pseudopotentials, pseudo_dir, pw_command="pw.x", kpoints_mesh, ecutwfc_ry, n_images=5, climb=True, fmax=0.05)`**
  → `{neb_job_id}`. Runs in a background thread on the **server's host** — `pseudo_dir`/`pw_command` are paths
  there, not your sandbox. Not AiiDA-tracked; poll with `hd_get_neb_job`, not `hd_get_job`.
- **`hd_get_neb_job(neb_job_id)`** → `{status: running|finished|failed, barrier_ev?, image_energies_ev?, error?}`.
  Lost if the MCP server process restarts.

## Remote HPC setup (write)

- **`hd_setup_remote_computer(label, hostname, username, scheduler="slurm", work_dir="/scratch/{username}/aiida_run", mpiprocs_per_machine=24, prepend_text="")`**
  → `{label, hostname, enabled}`. Idempotent. Requires key-based SSH auth to already work — this tool does not set
  up keys.
- **`hd_register_remote_code(computer_label, label, remote_executable_path, plugin_entry_point, prepend_text="")`**
  → `{full_label, pk}`. Idempotent. `remote_executable_path` must be the path *after* whatever `prepend_text`
  module-loads run.
