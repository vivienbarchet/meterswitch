Code for the experiment to switch between different meters (Telluride 2026).

## Repo structure

```
main_exp/, main_experiment_start.m, start_tapping.m   MATLAB experiment code
save/<subject>/                                       raw audio + trial log per participant
save/first tests/                                     early pilot recordings (not real subjects)
save/derived/<subject>/                                extraction + model outputs
analysis/                                             the analysis pipeline (see below)
docs/                                                  model math, pipeline overview, background reading
```

The analysis pipeline lives in `analysis/`, run in this order:

1. `01_extract_onsets.ipynb` -- detects metronome clicks + tap onsets/loudness from raw audio
2. `02_fit_model.ipynb` -- fits the switch-detection model (PyMC/NUTS) per trial
3. `power_analysis.ipynb` -- simulation-based power analysis for future data collection
4. `03_analyse.Rmd` -- renders the report (`03_analyse.pdf`)

Full walkthrough: `docs/analysis_pipeline_summary.md`. Model math: `docs/model_math.md`.

## Installing the environment

Python (steps 1-3 above), requires Python >=3.10:

```bash
python -m venv .venv && source .venv/bin/activate
pip install uv
uv pip install -r pyproject.toml
```

R (step 4, `03_analyse.Rmd`):

```r
install.packages(c("rmarkdown", "data.table", "ggplot2", "gridExtra", "knitr"))
```
