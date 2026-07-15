# %% [markdown]
# # Fitting the barebone soft-change-point model to sub02's real tap data
# 
# *2026-07-10 Roberto Barumerli*
# 
# Fits model per-trial to real data from
# `save/derived/sub02/sub02_click_tap_alignment.csv`

# %%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import pymc as pm
import pytensor.tensor as pt
import arviz as az

az.style.use("arviz-darkgrid")
mpl.rcParams["figure.dpi"] = 110
mpl.rcParams["axes.titlesize"] = 11
mpl.rcParams["axes.labelsize"] = 10
mpl.rcParams["figure.constrained_layout.use"] = True

print("PyMC", pm.__version__, "| ArviZ", az.__version__)

# %% [markdown]
# ## 0. Config

# %%
SUBJECT = "sub08"
ALIGNMENT_CSV = f"../save/derived/{SUBJECT}/{SUBJECT}_click_tap_alignment.csv"
OUT_DIR = f"../save/derived/{SUBJECT}"

DB_PER_NAT = 20 / np.log(10)  # rms_db = 20*log10(rms) = 8.686 * ln(rms)

# %% [markdown]
# ## 1. Define Helper Functions & PyMC Models
# *Note: These must be defined at the global level so Windows child processes can import them.*

# %%
def other_meter(meter):
    return 3 if meter == 2 else 2


def build_cued_trial_model(n, log_v, start_meter, switch_beat, n_pulses, tau_prior_sd=None):
    """Single cued trial, mixing a template sized to the trial's starting meter
    with one sized to the other meter."""
    end_meter = other_meter(start_meter)
    pos_start = np.mod(n, start_meter).astype(int)
    pos_other = np.mod(n, end_meter).astype(int)

    with pm.Model() as model:
        if tau_prior_sd is None:
            tau = pm.Normal("tau", mu=n_pulses / 2, sigma=n_pulses / 4)
        else:
            tau = pm.Normal("tau", mu=switch_beat, sigma=tau_prior_sd)

        log_s = pm.Normal("log_s", mu=np.log(0.15), sigma=0.4)
        s = pm.Deterministic("s", pt.exp(log_s))

        baseline = pm.Normal("baseline", mu=log_v.mean(), sigma=2.0)

        g_start_raw = pm.Normal("g_start_raw", 0.0, 1.0, shape=start_meter)
        g_start = pm.Deterministic("g_start", g_start_raw - g_start_raw.mean())
        g_other_raw = pm.Normal("g_other_raw", 0.0, 1.0, shape=end_meter)
        g_other = pm.Deterministic("g_other", g_other_raw - g_other_raw.mean())

        sigma_0 = pm.HalfNormal("sigma_0", sigma=0.5)
        sigma_sw = pm.HalfNormal("sigma_sw", sigma=0.5)

        w = pm.math.sigmoid((n - tau) / s)
        mu = baseline + (1 - w) * g_start[pos_start] + w * g_other[pos_other]
        sigma = pt.sqrt(sigma_0**2 + sigma_sw**2 * 4 * w * (1 - w))

        pm.Normal("log_v_obs", mu=mu, sigma=sigma, observed=log_v)

    return model


def build_spontaneous_trial_model(n, log_v, start_meter, n_pulses):
    """Single spontaneous trial: broad prior on tau (no cue)."""
    return build_cued_trial_model(n, log_v, start_meter, switch_beat=None, n_pulses=n_pulses,
                                  tau_prior_sd=None)


def extract_posterior_draws(idatas_dict, meters_dict, condition, var_names=("tau", "s", "sigma_sw", "sigma_0")):
    """Long-format: one row per (trial, draw), tagging condition/meter/converged."""
    rows = []
    for trial, idata in idatas_dict.items():
        rhat = az.rhat(idata, var_names=["tau", "s", "sigma_0", "sigma_sw"])
        max_rhat = float(max(rhat[v].values for v in ["tau", "s", "sigma_0", "sigma_sw"]))
        draws = {v: idata.posterior[v].values.flatten() for v in var_names}
        n_draws = len(draws[var_names[0]])
        row = {"trial": trial, "condition": condition, "meter": meters_dict[trial],
               "draw": np.arange(n_draws), "max_rhat": max_rhat, "converged": max_rhat < 1.05}
        row.update(draws)
        rows.append(pd.DataFrame(row))
    return pd.concat(rows, ignore_index=True)


def hdi(samples, cred=0.94):
    samples = np.sort(samples)
    n = len(samples)
    interval_idx = int(np.floor(cred * n))
    n_intervals = n - interval_idx
    widths = samples[interval_idx:] - samples[:n_intervals]
    min_idx = np.argmin(widths)
    return samples[min_idx], samples[min_idx + interval_idx]


def group_mean_mc(df, group_col, group_val, param, n_mc=4000, rng=None):
    """Paired Monte Carlo resample of the group's mean."""
    rng = rng if rng is not None else np.random.default_rng(0)
    sub = df[df[group_col] == group_val]
    trial_draws = [g[param].values for _, g in sub.groupby("trial")]
    mc_means = np.empty(n_mc)
    for i in range(n_mc):
        mc_means[i] = np.mean([rng.choice(td) for td in trial_draws])
    return mc_means


def compare_groups(df, group_col, group_a, group_b, params, rng):
    rows = []
    for param in params:
        a_mc = group_mean_mc(df, group_col, group_a, param, rng=rng)
        b_mc = group_mean_mc(df, group_col, group_b, param, rng=rng)
        diff_mc = a_mc - b_mc
        lo, hi = hdi(diff_mc)
        rows.append({
            "comparison": f"{group_a} - {group_b}", "parameter": param,
            f"{group_a}_mean": a_mc.mean(), f"{group_b}_mean": b_mc.mean(),
            "diff_mean": diff_mc.mean(), "hdi_94_lo": lo, "hdi_94_hi": hi,
            "credible": not (lo <= 0 <= hi),
        })
    return pd.DataFrame(rows)

# %% [markdown]
# ## 2. Protected Execution Block

# %%
if __name__ == "__main__":
    # --- 1. Load and prepare data ---
    df_raw = pd.read_csv(ALIGNMENT_CSV)
    df_raw["missed_beat"] = df_raw["missed_beat"].astype(str).str.lower().eq("true")

    df = df_raw[~df_raw["missed_beat"]].copy()
    df["log_v"] = df["rms_db"] / DB_PER_NAT
    df["switch_beat"] = df["switch_time"] * df["bpm"] / 60.0

    print(f"{len(df_raw)} clicks total, {len(df)} with a matched tap (observation)")
    print(df.groupby("condition")["trial"].nunique())

    df_cued = df[df["condition"] == "cued"].copy()
    df_spontaneous = df[df["condition"] == "spontaneous"].copy()

    trials_cued = df_cued[["trial", "meter", "bpm", "switch_time", "switch_beat"]].drop_duplicates().sort_values("trial")
    trials_spontaneous = df_spontaneous[["trial", "meter", "bpm"]].drop_duplicates().sort_values("trial")

    # --- 3. Cued fit ---
    cued_results = []
    cued_idatas = {}

    print("\n--- Starting Cued Fits ---")
    for _, row in trials_cued.iterrows():
        trial = int(row["trial"])
        sub = df_cued[df_cued["trial"] == trial]
        n = sub["click_idx"].values
        log_v = sub["log_v"].values
        meter = int(row["meter"])
        switch_beat = row["switch_beat"]
        n_pulses = int(n.max()) + 1

        model = build_cued_trial_model(n, log_v, meter, switch_beat, n_pulses)
        with model:
            idata = pm.sample(1000, tune=1500, chains=4, cores=4, target_accept=0.9,
                              random_seed=20260703, progressbar=False, init="adapt_diag")
        cued_idatas[trial] = idata

        tau_samples = idata.posterior["tau"].values.flatten()
        rhat = az.rhat(idata, var_names=["tau", "s", "sigma_0", "sigma_sw"])
        max_rhat = float(max(rhat[v].values for v in ["tau", "s", "sigma_0", "sigma_sw"]))

        cued_results.append({
            "trial": trial, "meter": meter, "switch_beat": switch_beat,
            "tau_mean": tau_samples.mean(),
            "tau_lo": np.percentile(tau_samples, 3), "tau_hi": np.percentile(tau_samples, 97),
            "max_rhat": max_rhat, "converged": max_rhat < 1.05,
        })
        print(f"trial {trial:2d} (meter {meter}): tau = {tau_samples.mean():.2f} "
              f"[{np.percentile(tau_samples,3):.2f}, {np.percentile(tau_samples,97):.2f}] "
              f"vs switch_beat={switch_beat:.2f}  max_rhat={max_rhat:.3f}"
              f"{'   *** NOT CONVERGED ***' if max_rhat >= 1.05 else ''}")

    df_cued_results = pd.DataFrame(cued_results)

    # --- 4. Cued recovery check ---
    converged = df_cued_results[df_cued_results["converged"]]
    n_excluded = len(df_cued_results) - len(converged)
    if n_excluded:
        excluded_trials = df_cued_results.loc[~df_cued_results["converged"], "trial"].tolist()
        print(f"Excluding {n_excluded} non-converged trial(s) from recovery check: {excluded_trials}")

    fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
    y = np.arange(len(df_cued_results))
    is_converged = df_cued_results["converged"].values

    for mask, color, label in [(is_converged, "C0", "posterior tau, converged"),
                                (~is_converged, "C3", "posterior tau, NOT converged")]:
        if mask.sum() == 0:
            continue
        ax.errorbar(df_cued_results["tau_mean"][mask], y[mask],
                    xerr=[df_cued_results["tau_mean"][mask] - df_cued_results["tau_lo"][mask],
                          df_cued_results["tau_hi"][mask] - df_cued_results["tau_mean"][mask]],
                    fmt="o", color=color, capsize=3, label=label)

    ax.scatter(df_cued_results["switch_beat"], y, color="k", marker="x", s=60, zorder=5,
               label="experimenter switch_beat")

    ax.set_yticks(y)
    ax.set_yticklabels([f"trial {t} (m{m})" for t, m in zip(df_cued_results["trial"], df_cued_results["meter"])])
    ax.set_xlabel("tau (beats)")
    ax.set_title(f"{SUBJECT}: cued fit, posterior tau vs. cue time (switch_beat)")
    ax.legend(fontsize=8)
    plt.show()

    corr = np.corrcoef(converged["tau_mean"], converged["switch_beat"])[0, 1]
    lag = converged["tau_mean"] - converged["switch_beat"]
    print(f"corr(tau_mean, switch_beat) = {corr:.3f}  (converged trials only, n={len(converged)})")
    print(f"estimated reaction/adoption lag (tau - switch_beat): "
          f"mean={lag.mean():.2f} beats, sd={lag.std():.2f}, range=[{lag.min():.2f}, {lag.max():.2f}]")

    # --- 5. Spontaneous fit ---
    spontaneous_results = []
    spontaneous_idatas = {}

    print("\n--- Starting Spontaneous Fits ---")
    for _, row in trials_spontaneous.iterrows():
        trial = int(row["trial"])
        sub = df_spontaneous[df_spontaneous["trial"] == trial]
        n = sub["click_idx"].values
        log_v = sub["log_v"].values
        meter = int(row["meter"])
        n_pulses = int(n.max()) + 1

        model = build_spontaneous_trial_model(n, log_v, meter, n_pulses)
        with model:
            idata = pm.sample(1000, tune=1500, chains=4, cores=4, target_accept=0.9,
                              random_seed=20260703, progressbar=False, init="adapt_diag")
        spontaneous_idatas[trial] = idata

        tau_samples = idata.posterior["tau"].values.flatten()
        rhat = az.rhat(idata, var_names=["tau", "s", "sigma_0", "sigma_sw"])
        max_rhat = float(max(rhat[v].values for v in ["tau", "s", "sigma_0", "sigma_sw"]))

        bpm = row["bpm"]
        tau_lo, tau_hi = np.percentile(tau_samples, [3, 97])
        spontaneous_results.append({
            "trial": trial, "meter": meter, "n_pulses": n_pulses, "bpm": bpm,
            "tau_mean": tau_samples.mean(),
            "tau_lo": tau_lo, "tau_hi": tau_hi, "tau_ci_width": tau_hi - tau_lo,
            "tau_mean_s": tau_samples.mean() * 60 / bpm,
            "max_rhat": max_rhat, "converged": max_rhat < 1.05,
        })
        print(f"trial {trial:2d} (meter {meter}): tau = {tau_samples.mean():.2f} "
              f"[{tau_lo:.2f}, {tau_hi:.2f}] beats (width={tau_hi-tau_lo:.1f})  max_rhat={max_rhat:.3f}"
              f"{'   *** NOT CONVERGED ***' if max_rhat >= 1.05 else ''}")

    df_spontaneous_results = pd.DataFrame(spontaneous_results)

    # --- 6. Spontaneous switch-time estimates ---
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")

    y = np.arange(len(df_spontaneous_results))
    axes[0].errorbar(df_spontaneous_results["tau_mean"], y,
                     xerr=[df_spontaneous_results["tau_mean"] - df_spontaneous_results["tau_lo"],
                           df_spontaneous_results["tau_hi"] - df_spontaneous_results["tau_mean"]],
                     fmt="o", color="C2", capsize=3)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([f"trial {t} (m{m})" for t, m in
                              zip(df_spontaneous_results["trial"], df_spontaneous_results["meter"])])
    axes[0].set_xlabel("tau (beats, estimated self-switch time)")
    axes[0].set_title("Spontaneous: estimated switch time")

    axes[1].bar([f"t{t}" for t in df_spontaneous_results["trial"]], df_spontaneous_results["tau_ci_width"],
                color="C3")
    axes[1].set_ylabel("tau 94% CI width (beats)")
    axes[1].set_title("Switch-time uncertainty per trial\n(wide = no clear switch found)")
    axes[1].tick_params(axis="x", labelrotation=90, labelsize=7)

    fig.suptitle(f"{SUBJECT}: spontaneous fit", fontsize=11)
    plt.show()

    # --- 7. Comparisons ---
    cued_meters = dict(zip(trials_cued["trial"], trials_cued["meter"]))
    spontaneous_meters = dict(zip(trials_spontaneous["trial"], trials_spontaneous["meter"]))

    draws_cued = extract_posterior_draws(cued_idatas, cued_meters, "cued")
    draws_spontaneous = extract_posterior_draws(spontaneous_idatas, spontaneous_meters, "spontaneous")
    df_posterior_draws = pd.concat([draws_cued, draws_spontaneous], ignore_index=True)

    n_excluded_draws = df_posterior_draws.loc[~df_posterior_draws["converged"], "trial"].unique()
    print(f"{df_posterior_draws['trial'].nunique()} trials, "
          f"{len(n_excluded_draws)} excluded from comparisons below (non-converged): "
          f"{sorted(n_excluded_draws.tolist())}")

    df_converged_draws = df_posterior_draws[df_posterior_draws["converged"]]
    rng = np.random.default_rng(42)
    params_to_check = ["tau", "s", "sigma_sw", "sigma_0"]

    condition_comparison = compare_groups(df_converged_draws, "condition", "cued", "spontaneous",
                                           params_to_check, rng)
    meter_comparison = compare_groups(df_converged_draws, "meter", 2, 3, params_to_check, rng)
    df_group_comparisons = pd.concat([condition_comparison, meter_comparison], ignore_index=True)

    pd.set_option("display.width", 160)
    print("\n--- Group Comparisons ---")
    print(df_group_comparisons.round(3).to_string(index=False))

    # --- 8. Save results ---
    df_cued_results.to_csv(f"{OUT_DIR}/{SUBJECT}_cued_tau_fit.csv", index=False)
    df_spontaneous_results.to_csv(f"{OUT_DIR}/{SUBJECT}_spontaneous_tau_fit.csv", index=False)
    df_posterior_draws.to_csv(f"{OUT_DIR}/{SUBJECT}_posterior_draws.csv", index=False)
    df_group_comparisons.to_csv(f"{OUT_DIR}/{SUBJECT}_group_comparisons.csv", index=False)

    print("\nSaved:")
    print(f" - {OUT_DIR}/{SUBJECT}_cued_tau_fit.csv")
    print(f" - {OUT_DIR}/{SUBJECT}_spontaneous_tau_fit.csv")
    print(f" - {OUT_DIR}/{SUBJECT}_posterior_draws.csv")
    print(f" - {OUT_DIR}/{SUBJECT}_group_comparisons.csv")