# 2D monolayer stability screening

For questions like "is there a stable 2D monolayer of element X, and which structural prototype?" — the
elemental-monolayer ("Xene") family: honeycombs (graphene/silicene/borophene/arsenene-alpha type) and puckered
black-phosphorus-type structures (phosphorene and its As/Sb/Bi analogs).

## Workflow

1. **`hd_generate_2d_prototype(element, prototype)`** for each candidate structure you want to try for an
   element. `"honeycomb"` for group 13/14-type elements and many pnictogens' alpha phase; `"puckered"`
   specifically for phosphorene-family (P, As, Sb, Bi) beta-phase candidates. This is a topological *seed*
   (covalent-radius bond lengths, not literature values) — never treat it as a finished structure.
2. **Always relax with `cell_dofree="2Dxy"`** (`hd_submit_relax`). This is not optional for a slab-with-vacuum
   structure: without it, vc-relax has no way to know the third lattice direction is vacuum, not a real axis, and
   will collapse or tilt it. Use the `kpoints_mesh_suggestion` from `hd_generate_2d_prototype`
   (always `(Nx, Ny, 1)` — a 2D structure has no periodicity to sample along the vacuum direction).
3. **Check dynamical stability** before calling anything "stable": run the phonon chain
   (`hd_submit_ph` → `hd_submit_q2r` → `hd_submit_matdyn`, q-mesh also `(Nqx, Nqy, 1)`) on the relaxed structure,
   then **`hd_check_phonon_stability(matdyn_pk)`**. A `stable=False` result with `imaginary_modes` spanning
   several q-points is a real instability, not a numerical artifact — the tool's default tolerance already
   absorbs the small Gamma-point noise that's typical even with the acoustic-sum-rule correction applied.
   A single Gamma-only q-point is **not** an adequate stability check for a 2D structure — instabilities away
   from Gamma are common and won't show up without sampling more of the Brillouin zone.
4. **Compare prototypes for the same element** with **`hd_rank_prototypes`** once you have finished relaxations
   for each candidate — but only if every candidate used the same ecutwfc/k-density/pseudo family (same
   correctness requirement as any other energy comparison in this skill).

## What "stable" does and doesn't mean here

Passing the phonon check (no imaginary modes) means the structure is a genuine local minimum on the
zero-temperature potential-energy surface — necessary, not sufficient, for calling it a real material. It says
nothing about:
- **Formation/exfoliation energy** relative to competing prototypes or the bulk 3D allotrope (if one exists) —
  a dynamically stable structure can still be far higher in energy than another candidate or the bulk phase.
- **Finite-temperature stability** (this harness has no AIMD/MD-based thermal-stability workflow).
- **Electronic-structure sanity** — always sanity-check with `hd_submit_bands`/`hd_submit_pdos` once you have a
  stable candidate, especially for elements likely to be metallic in 2D form even if the bulk element isn't (or
  vice versa).

## Known gaps (pilot results, 8 elements: Al/Ga/In/Tl honeycomb, P/As/Sb/Bi puckered)

All 8 relaxed successfully with vacuum intact. **2 of 8 (As, Ga) got a complete phonon-stability verdict** —
both found genuinely dynamically **unstable**, real results. The other 5 are blocked by one still-open external
bug, not by anything wrong in this harness:

- **A real QE 7.5 `ph.x` crash was found, root-caused, and FIXED** (Ga, Tl, In, Bi originally hit it) — a missing
  comma in a `WRITE` FORMAT string in `PHonon/PH/phq_summary.f90`, confirmed via a debug rebuild that produced a
  precise compiler error, and fixed with a one-line patch, rebuilt, and verified against the exact previously-
  crashing case (`JOB DONE`, correct frequencies). Registered as `ph-7.5-fixed@localhost` in this profile. An
  earlier diagnosis (that `-northo 0`/disabling ScaLAPACK fixed it) was **wrong** — a false positive from a
  not-fully-faithful manual reproduction — and has been corrected; don't reach for that workaround. Patch and
  full writeup: `harness-dft/docs/upstream-bugs/`.
- **A real, still-open `aiida-quantumespresso` restart-handler bug** (now blocks Tl, In, Bi, P, Sb — 5 of 8, once
  the QE crash above stopped being the thing blocking them first): a `PhCalculation` restart after any
  auto-handled failure raises `KeyError: 'INPUTPH'` in `ph.py`'s `prepare_for_submission` — the restart path
  drops the INPUTPH namelist entirely. These elements also genuinely take longer than the default ~32-minute
  walltime estimate for a `(2,2,1)` q-mesh on this hardware (confirmed up to 2 hours for P/Sb), which is what
  triggers the restart in the first place — a real compute-cost finding, separate from the bug itself.

If you hit the `aiida-quantumespresso` pattern when driving this skill: don't keep escalating walltime or
retrying blindly — a `KeyError: 'INPUTPH'` in a process report after a handled restart is this exact bug; tell
the researcher it needs upstream investigation (or a calculation cheap enough to finish in one attempt), not more
resource tuning. If you see the *other* pattern (near-instant crash right after "Computing dynamical matrix" with
a `libgfortran`/`data_transfer_init` crash) on a `ph_code_label` other than `ph-7.5-fixed@localhost`, that's the
now-fixed QE bug — point at the fixed code instead of debugging further.

Other real gaps:
- No 2D electrostatics correction (QE's `assume_isolated='2D'` or ESM) is wired in — the "big vacuum supercell"
  approach used here is the standard method but is less accurate for polar/charged structures than a proper 2D
  Coulomb cutoff.
- No formation-energy-vs-bulk or exfoliation-energy calculation exists — `hd_rank_prototypes` only compares
  candidates against each other, not against a bulk reference, and hasn't yet been used on a real comparison
  (only mechanically sort-order-tested) since no element in the pilot has two complete prototype results.

Full design detail, the complete 8-element results table, and the resource-estimator/`force_metal` bugs this
screening caught in the harness itself: `harness-dft/docs/2d-screening.md`.
