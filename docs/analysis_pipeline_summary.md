# Summary: metric-switching tapping analysis

*2026-07-10 Roberto Barumerli*

What the experiment is: see `README.md` at the repo root. This file documents how the analysis
pipeline fits together; `model_math.md` (also in this `docs/` folder) documents the model itself.

## Pipeline at a glance

Everything -- notebooks, report, and the data they read/write -- lives in this one repo now.
Notebooks (`01_extract_onsets.ipynb`, `02_fit_model.ipynb`, `power_analysis.ipynb`) and the report
(`03_analyse.Rmd`) are in `analysis/`; the raw and derived data they read/write are in `../save/`
and `../save/derived/` (every notebook hardcodes the absolute repo path, so it doesn't matter which
directory you launch Jupyter from). Outputs of `power_analysis.ipynb` land in `analysis/results/`.

```
save/<subject>/                     raw audio + trial log
        |
        v
01_extract_onsets.ipynb          -> save/derived/<subject>/*_click_tap_alignment.csv (+ QC)
        |
        v
02_fit_model.ipynb               -> save/derived/sub02/*_tau_fit.csv, *_posterior_draws.csv,
        |                            *_group_comparisons.csv
        v
power_analysis.ipynb             -> analysis/results/power_required_trials.csv,
        |                            analysis/results/power_required_participants.csv
        v
03_analyse.Rmd                   -> analyse.pdf   (the actual report, analysis/)
```

Every stage writes its output to disk before the next stage reads it, so you can re-run any single
stage without repeating the ones before it (useful, since fitting is the slow part -- tens of
minutes of MCMC across all trials).

Environment: everything Python (`01_extract_onsets.ipynb`, `02_fit_model.ipynb`,
`power_analysis.ipynb`) runs in the `bayesian_listener` conda environment (librosa, PyMC, ArviZ).
The report (`03_analyse.Rmd`) is plain R + `rmarkdown`/`data.table`/`ggplot2`.

## 1. Raw data

Lives in `../save/<subject>/` -- one `<subject>_log.csv` (trial-by-trial condition, meter, BPM,
cue time) plus paired `.wav` recordings per trial (metronome click track + participant tapping
mic).

**Only `sub02` is currently usable.** `sub01`'s recordings were too quiet/noisy to trust -- see
`01_extract_onsets.ipynb`'s QC section and `03_analyse.Rmd`'s data-loading chunk for how that was
determined and why the whole subject is excluded rather than partially salvaged.

## 2. Extraction: `01_extract_onsets.ipynb`

Detects metronome clicks and tap onsets from the raw audio, matches each tap to its nearest click,
and records that tap's timing offset (asynchrony) and loudness (amplitude). Per-trial QC plots are
saved alongside the CSVs so detection quality can be checked by eye, not just trusted (not tracked
in git -- regenerate locally if needed). Output is one row per metronome click, per subject:
`../save/derived/<subject>/<subject>_click_tap_alignment.csv`.

## 3. Fitting: `02_fit_model.ipynb`

The model itself -- what it fits, the exact formulas, priors, and a graphical-model diagram -- is
documented in **`model_math.md`** (this folder). Don't duplicate that here -- read it for the model
itself.

Full MCMC (NUTS via PyMC) for every trial, independently, in both the cued and spontaneous
conditions. It also validates the model against the cued trials' known cue times, and computes
credible-interval group comparisons (cued vs. spontaneous, meter 2 vs. meter 3) across the fitted
parameters. This is the notebook to re-run if the input data or model changes. (A separate
MAP-only sanity-check notebook was used during development to catch broken model specs quickly,
before committing to slow MCMC -- not included here since it's not where any reported result comes
from.)

Outputs land in `../save/derived/sub02/`: `sub02_cued_tau_fit.csv`, `sub02_spontaneous_tau_fit.csv`
(one row per trial), `sub02_posterior_draws.csv` (full posterior samples, long format -- needed for
any further credible-interval analysis), and `sub02_group_comparisons.csv` (the condition/meter
comparison table).

## 4. Power analysis: `power_analysis.ipynb`

Monte Carlo simulation, grounded in `sub02`'s real fitted values, answering "how much more data
would we need": trials/cell in the 2x2 (meter x condition) design to detect `tau`/`s` effects, and
participants needed to detect a musical-training/selectivity relationship. Outputs
`results/power_required_trials.csv` and `results/power_required_participants.csv`, which
`03_analyse.Rmd` (Part 5) loads directly.

## 5. Reporting: `03_analyse.Rmd`

The actual write-up, aimed at collaborators who aren't modellers -- descriptive stats first, then a
plain-language (no-code, no-formula) explanation of what the model does, then results: cued
validation, spontaneous switch detection with confidence, a model-free cross-check, condition/meter
parameter comparisons, and the power analysis. Renders to `analyse.pdf`.

## Reproducing it end to end

```bash
conda activate bayesian_listener
cd analysis

# 1. Extraction (per subject; re-run if raw audio changes)
jupyter nbconvert --to notebook --execute --inplace 01_extract_onsets.ipynb

# 2. Fitting (slow -- full MCMC over every trial)
jupyter nbconvert --to notebook --execute --inplace 02_fit_model.ipynb

# 3. Power analysis (writes into results/)
jupyter nbconvert --to notebook --execute --inplace power_analysis.ipynb

# 4. Report
Rscript -e 'rmarkdown::render("03_analyse.Rmd", output_format = "pdf_document")'
```

## Current status / caveats

- **n = 1 subject** (`sub02`). Everything here is exploratory, not confirmatory -- see
  `03_analyse.Rmd`'s own Summary section for the actual findings and how tentatively they're framed.
- One cued trial (trial 12) is excluded from validation/group-comparison statistics -- its sampler
  didn't converge, traced to genuinely weak/ambiguous accent signal in that trial's data (not a
  model bug). Flagged automatically via a convergence check, not hand-picked.
- The model uses **loudness only** -- asynchrony/timing was checked as a second signal (twice: a
  periodic-template hypothesis and a switch-related noise-inflation hypothesis) and rejected both
  times on a proper BIC comparison. Don't re-add it without re-checking that finding.
- The power analysis (`power_analysis.ipynb`, Part 5 of `03_analyse.Rmd`) suggests **~20 trials/cell
  (80/participant)** as a practical target for future data collection, and **~30 participants** to
  detect a moderate musical-training effect on switch selectivity -- see that section for the
  full reasoning and per-effect breakdown.
