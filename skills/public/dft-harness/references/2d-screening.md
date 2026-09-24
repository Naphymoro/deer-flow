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

## Known gaps (as of this skill's writing)

- Only bulk Si's phonon dispersion has been run through `hd_check_phonon_stability` — no 2D candidate has been
  taken through the full relax→phonon→stability-check pipeline yet. Treat the first one as validation.
- The puckered prototype has only been geometry-checked (correct bond lengths/coordination), not DFT-relaxed.
- No 2D electrostatics correction (QE's `assume_isolated='2D'` or ESM) is wired in — the "big vacuum supercell"
  approach used here is the standard method but is less accurate for polar/charged structures than a proper 2D
  Coulomb cutoff.
- No formation-energy-vs-bulk or exfoliation-energy calculation exists — `hd_rank_prototypes` only compares
  candidates against each other, not against a bulk reference.

Full design detail and the resource-estimator bug this screening caught (`npool` divisibility):
`harness-dft/docs/2d-screening.md`.
