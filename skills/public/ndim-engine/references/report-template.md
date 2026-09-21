# Report template

Use this structure for any write-up of engine results. Keep the limitations section even when the researcher asks for a
short version. Shorten it, do not drop it.

```markdown
# <Title: the research question>

**Status:** Exploratory draft. Illustrative model output. Pending researcher review.

## 1. Question and scope
- Research question (the researcher's words)
- Workspace, workflow (evidence / scenario / sensitivity / sweep), model family
- What this analysis does not cover

## 2. Evidence
- Source name, how many texts, language, consent status as stated by the researcher
- Preprocessing you did (translation, redaction, chunking), and who confirmed it
- `source_sha256` (first 12 characters is enough)

## 3. Approved plan
- Steps and parameters, as approved. Quote the researcher's approval and when they gave it
- Warnings the engine attached

## 4. Results
- Encoding: trust, barrier, sentiment, themes, labelled "keyword heuristic"
- Diagnosis: flags, labelled "heuristic, requires review"
- Simulation: baseline and intervention endpoints and delta, or the sweep table (from `markdown_table`)
- Numerical checks: passed or not, with the sentence "numerical consistency only"
- Comparability notes when several runs are compared

## 5. What this does and does not show
- Plain-language reading, using the wording rules in interpreting-results.md
- Saturation or ceiling effects if present

## 6. Limitations (keep)
- Keyword encoding of English text, one narrative per run
- Uncalibrated, illustrative model; no field validation
- Bands are heuristic envelopes, not confidence intervals
- Deterministic sweeps show sensitivity, not uncertainty
- Inoculation parameters are not wired from the diagnosis in the current harness; intervention_strength is the only lever
- Anything you computed outside the engine is exploratory (list it)

## 7. Provenance
- Run ids, `code_version` (first 19 characters), engine URL and deployment mode, date
- Audit log location for approvals

## 8. Next steps for the researcher
- Review each run (the review step is theirs and is not done)
- What data would be needed to calibrate or validate
```

## Checklist before sending

- [ ] Every number traces to an engine tool result, or is labelled exploratory
- [ ] No word from the "do not write" list in interpreting-results.md
- [ ] The approval quote is theirs, not yours
- [ ] Consent status is what they told you
- [ ] Comparability is stated for any multi-run comparison
- [ ] The report says the researcher's review is still pending
