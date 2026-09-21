# Interpreting results

## What each number is

| Output | It is | It is not |
|---|---|---|
| `trust_score`, `adoption_barrier_score`, `sentiment`, `themes` | A keyword-based reading of one English text | Measured trust or barriers in a population |
| `misinformation_risk_score` and other diagnosis scores | A heuristic flag for review | Proof a narrative is false or harmful |
| `final_adoption`, `peak_adoption` | An endpoint of an uncalibrated model | A forecast |
| `final_heuristic_band` | A heuristic envelope | A confidence or credible interval |
| `delta_final_adoption` (baseline vs intervention) | The difference between two model endpoints | An estimated treatment effect |
| `sensitivity_curve` | Response of the endpoint to one parameter | Uncertainty, or evidence about the true response |
| `numerical_checks.passed` | Values are finite, adoption within 0-1, compartments normalized | Scientific validity |

Every simulation carries `method_status: illustrative_uncalibrated`. Keep that phrase when you report.

## Reading a scenario

1. Confirm `numerical_checks.passed` is true.
2. Confirm the plan matches what was approved (model, strength, horizon).
3. Report the baseline and intervention endpoints and the delta, each labelled illustrative.
4. Say what drove the inputs: the trust and barrier scores came from one narrative's keywords.
5. Say what would be needed to make a real claim: calibration against independent field data.

## Saturation: check before you interpret

Adoption in the compartmental model is bounded by 1 and can approach it. In the synthetic sample at 90 days, baseline
endpoints were already about 0.79-0.86 and intervention endpoints about 0.86-0.95. Two consequences:

- **Deltas shrink near the ceiling.** In that sample (intervention strength 0.3), raising `narrative_influence` from 0.2 to
  0.9 raised the baseline endpoint (about 0.79 to 0.86) while *lowering* the intervention delta (about 0.076 to 0.045). That
  is ceiling compression, not "narratives make interventions less useful."
- **`peak_adoption` equals `final_adoption` and `peak_day` is the last day** when adoption never falls. Then the peak
  tells you nothing. Say so instead of reporting a peak.

If `final_adoption` is above roughly 0.95 in both arms, or the trajectories converge, try a shorter `horizon_days` (for
example 30 or 45) and compare timing, not just endpoints. Present it as a robustness check, not as a better answer.
(Numbers above come from the engine's synthetic sample and are examples, not general properties.)

## Sanity checks worth running

| Check | Expected | If not |
|---|---|---|
| `intervention_strength = 0` scenario | delta exactly 0.0 | Stop. Report a possible engine defect. |
| Same plan run twice | identical results | Code or environment changed, or a bug. Compare `code_version`. |
| Higher `intervention_strength` | delta rises (compartmental) | Check model family; `agent_based` ignores it |
| `narrative_influence` under `agent_based` | no change | Expected: that model ignores it |

## Allowed and forbidden wording

| Do not write | Write instead |
|---|---|
| "Adoption will reach 91% in 90 days" | "In the illustrative model, endpoint adoption is 0.91 at day 90 under these assumptions." |
| "The intervention increases adoption by 11 points" | "The model's intervention arm ends 0.11 above its baseline arm; this is not an estimated effect." |
| "Trust is 0.59 in this community" | "The keyword heuristic scored this narrative 0.59 on trust." |
| "The sweep shows the result is robust" | "The endpoint moves from A to B across the grid; a grid shows sensitivity, not uncertainty." |
| "Validated", "calibrated", "confirmed" | "Exploratory", "illustrative", "pending researcher review" |
| "The narrative is misinformation" | "The heuristic flagged possible misinformation mechanisms for human review." |
| "Statistically significant" | Never. There is no statistical test. |
| "The engine says people in Rwanda will..." | Scope claims to "this narrative" and "this model". |

## Multiple narratives

One run encodes one evidence text. To describe a set of interviews, run each separately and compare, and report the
spread of encodings. Do not concatenate interviews to get one "community" score unless the researcher asks, and if you
do, say the encoder treats the joined text as one narrative.

## What would make a claim defensible

Independent field data, calibration of the parameters against it, out-of-sample checks, and a review by the researcher.
None of these exist in the engine today. Say so, and record it under "Limitations".
