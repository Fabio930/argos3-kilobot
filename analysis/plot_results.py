"""Condensed hybrid plots: ARGoS time series next to the boxplot of the agent-based (Python) model.

One figure for every tested ARGoS setting that the panels do not show, saved as
proc_data/images/cohesion_hybrid_condensed/options_<n>/corr_<c>/rebroadcast_<r>_hop_<h>/
timeout_<s>s_python_mt<m>[_arena<a>][_runs<k>].png/.pdf (the folders tell the settings apart,
the figures have no title). Inside a figure, rows are the
control functions and columns the number of voting messages m; the inset shows
the second eta of that number of options.

The Python boxplot of a panel is built from the runs of the same setting:
message_timeout matched through MSG_TIME_MAP, quorum minimum 5, same initial
distribution, same control function and value, same m. When the ARGoS eta is
not in the Python grid, the two Python eta values around it (+-0.02) are
averaged run by run. Python has no space, so the same box goes into the panels
of every spatial correlation.

Usage: python3 plot_results.py [--python-data DIR]
Reading the Python Parquet files needs pyarrow (e.g. the venv of quorum_sensing_Best_of_N).
"""
import argparse, json, os, re, logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 18})

# ARGoS mean message lifetime (s) -> Python message_timeout (decisions); a decision every 5.1 s
MSG_TIME_MAP = {14: 3, 29: 6, 59: 12, 120: 24, 242: 48}
PY_QUORUM_MIN = 5            # min_quorum_length of the kilobots (bestN.c)
PY_ETA_HALF_STEP = 0.02      # Python eta grid step is 0.04
ETAS_BY_OPTIONS = {2: (0.5, 0.4), 5: (0.8, 0.7)}   # (main panel, inset)
ALL_M_VALUES = [3, 5, 9, 15]
DEFAULT_CONFIG = "plot_config.json"
# What to plot. A missing key or null means "every value in the data".
#   options, spatial_correlation, rebroadcast, msg_timeout: which figures
#   m: columns; static_r, linear, polynomial_x0: rows (static on top, then linear, then
#   polynomial, values ascending)
CONFIG_KEYS = {"options", "spatial_correlation", "rebroadcast", "msg_timeout", "m", "static_r", "linear", "polynomial_x0"}

def load_plot_config(path: str) -> dict:
    """Read the plot selection; with no file every setting in the data is plotted."""
    if path and not os.path.exists(path) and not os.path.isabs(path):
        # not in the working directory: use the copy next to this script
        here = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        if os.path.exists(here):
            path = here
    if not path or not os.path.exists(path):
        logging.info(f"No plot config {path}: plotting every setting")
        return {}
    with open(path) as f:
        cfg = json.load(f)
    unknown = set(cfg) - CONFIG_KEYS - {k for k in cfg if k.startswith("_")}
    if unknown:
        raise ValueError(f"Unknown keys in {path}: {sorted(unknown)} (allowed: {sorted(CONFIG_KEYS)})")
    return cfg

def _wanted(values, selection) -> list:
    """Values present in the data, kept by the config selection (None = all), ascending."""
    present = sorted({round(float(v), 3) for v in values if pd.notnull(v)})
    if selection is None:
        return present
    chosen = {round(float(v), 3) for v in selection}
    return [v for v in present if v in chosen]

def row_configs(coh: pd.DataFrame, cfg: dict) -> list:
    """Rows of a figure: static r ascending, then linear, then polynomial x0 ascending."""
    rows = []
    static = coh.loc[coh['function'] == 'static', 'control_par']
    for v in _wanted(static, cfg.get("static_r")):
        rows.append({'label': rf'$r={v:g}$', 'func': 'static', 'ctrl': v})
    if cfg.get("linear", True) and (coh['function'] == 'linear').any():
        rows.append({'label': r'$r(q)=q$', 'func': 'linear', 'ctrl': 0.0})
    poly = coh.loc[coh['function'] == 'polynomial', 'control_par']
    for v in _wanted(poly, cfg.get("polynomial_x0")):
        rows.append({'label': rf'$p(q,{v:g})$', 'func': 'polynomial', 'ctrl': v})
    return rows
# Settings of an ARGoS row that get a figure of their own
FIGURE_KEYS = ['n_options', 'spat_corr', 'communication', 'hop_count', 'msg_exp_time', 'arena', 'n_runs']

##################################################################################
# 1. DATA PARSING AND CONVERSION
##################################################################################

def _cast_metadata_value(raw_value: str):
    if raw_value == "": return raw_value
    try: return int(raw_value)
    except ValueError:
        try: return float(raw_value)
        except ValueError: return raw_value

def m_array_from_cell(cell_value) -> np.ndarray:
    if cell_value is None:
        return np.array([], dtype=float)
    if isinstance(cell_value, (float, int, np.number)):
        return np.array([float(cell_value)], dtype=float)
    if isinstance(cell_value, np.ndarray):
        return cell_value.astype(float, copy=False)
    if isinstance(cell_value, (list, tuple)):
        return np.asarray([np.nan if v is None else v for v in cell_value], dtype=float)
    if isinstance(cell_value, str):
        clean = cell_value.replace('[', ' ').replace(']', ' ').replace(',', ' ').replace('None', 'nan')
        return np.fromstring(clean, dtype=float, sep=' ')
    raise ValueError(f"Unsupported data type in cell: {type(cell_value).__name__}")

def _last_value(cell) -> float:
    """Last value of a serialized series ("[0.1, 0.2, 0.3]" -> 0.3)."""
    if isinstance(cell, str):
        tail = cell.rsplit(',', 1)[-1].strip(' []')
        try:
            return float(tail)
        except ValueError:
            arr = m_array_from_cell(cell)
            return float(arr[-1]) if arr.size else np.nan
    arr = m_array_from_cell(cell)
    return float(arr[-1]) if arr.size else np.nan

##################################################################################
# 2. ARGOS DATA
##################################################################################

# File name field -> column (only used where the rows themselves lack the column)
FILENAME_KEYS = {"options": "n_options", "spatcorr": "spat_corr", "runs": "n_runs",
                 "arena": "arena", "time": "exp_length", "agents": "n_agents"}

def metadata_from_filename(file_name: str) -> dict:
    stem = Path(file_name).stem
    if "resume_" not in stem:
        return {}
    metadata = {}
    for part in stem.split("resume_", 1)[1].split("_"):
        if "#" not in part: continue
        key, value = part.split("#", 1)
        if key in FILENAME_KEYS:
            metadata[FILENAME_KEYS[key]] = _cast_metadata_value(value)
    return metadata

def load_argos_metric(metric: str, proc_dir: str = "proc_data") -> pd.DataFrame:
    """All rows of one ARGoS metric, every setting as a column."""
    base_path = Path(os.path.abspath("")) / proc_dir / metric
    frames = []
    for file_path in sorted(base_path.glob("*resume_*.pkl")):
        try:
            df = pd.read_pickle(file_path)
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)
            for col, value in metadata_from_filename(file_path.name).items():
                if col not in df.columns:
                    df[col] = value
            frames.append(df)
        except ModuleNotFoundError as e:
            logging.error(f"Cannot load {file_path.name} ({e}): it was written with another numpy version. "
                          f"Run dump_results.py and plot_results.py with the same interpreter.")
        except Exception as e:
            logging.error(f"Error loading {file_path.name}: {e}")
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)

    # Files written before hop_count/ci95 were stored
    if 'hop_count' not in df.columns:
        df['hop_count'] = np.where(pd.to_numeric(df['communication'], errors='coerce') == 1, 1, 0)
    df['hop_count'] = pd.to_numeric(df['hop_count'], errors='coerce').fillna(0).astype(int)
    if 'option_id' not in df.columns:
        df['option_id'] = np.nan
    df['option_id'] = pd.to_numeric(df['option_id'], errors='coerce')
    df['data'] = [m_array_from_cell(v) for v in df['data']]
    if 'ci95' in df.columns:
        df['ci95'] = [m_array_from_cell(v) for v in df['ci95']]
    elif 'std' in df.columns:
        # Old files: std across runs -> half-width of the 95% CI
        n = pd.to_numeric(df['n_runs'], errors='coerce').fillna(1).astype(int).clip(lower=2)
        df['ci95'] = [stats.t.ppf(0.975, k - 1) * m_array_from_cell(s) / np.sqrt(k) for s, k in zip(df['std'], n)]
    else:
        df['ci95'] = [np.full(len(d), np.nan) for d in df['data']]
    for col in ['n_options', 'spat_corr', 'communication', 'msg_exp_time', 'n_runs', 'eta', 'control_par', 'vote_msg', 'init_distr']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df['eta'] = df['eta'].round(3)
    df['function'] = df['function'].astype(str).str.strip().str.lower()
    if 'arena' not in df.columns:
        df['arena'] = ''
    df['arena'] = df['arena'].fillna('').astype(str)
    return df

##################################################################################
# 3. PYTHON (AGENT-BASED) DATA
##################################################################################

PY_COLUMNS = ['run_id', 'r_type', 'init_distr', 'n_options', 'eta', 'min_qrm_buf', 'msg_time_exp',
              'msg_per_step', 'sigmd_par', 'r_value', 'r_shape', 'option_id', 'data']

def _python_eta_candidates(eta: float) -> list:
    return [round(eta, 3), round(eta - PY_ETA_HALF_STEP, 3), round(eta + PY_ETA_HALF_STEP, 3)]

def load_python_final_values(python_dir: str, argos_df: pd.DataFrame) -> pd.DataFrame:
    """Final residence value per run of the Python settings that can match an ARGoS panel.

    Reads the residence Parquet files in streaming, keeping only the rows that can
    match (quorum minimum, m, eta), and reduces every series to its last value.
    """
    files = sorted(Path(python_dir).glob("results_processed_*_residence_data.parquet"))
    if not files:
        logging.warning(f"No Python residence Parquet files in {python_dir}: plots without boxplots")
        return pd.DataFrame()
    try:
        import pyarrow.dataset as ds
    except ImportError:
        logging.error("pyarrow is needed for the Python data: run with the venv of quorum_sensing_Best_of_N")
        return pd.DataFrame()

    etas = sorted({e for eta in argos_df['eta'].dropna().unique() for e in _python_eta_candidates(float(eta))})
    eta_filter = None
    for e in etas:
        cond = (ds.field('eta') >= e - 1e-6) & (ds.field('eta') <= e + 1e-6)
        eta_filter = cond if eta_filter is None else (eta_filter | cond)

    frames = []
    for f in files:
        dataset = ds.dataset(str(f), format="parquet")
        cols = [c for c in PY_COLUMNS if c in dataset.schema.names]
        expr = (ds.field('min_qrm_buf') == PY_QUORUM_MIN) & ds.field('msg_per_step').isin(ALL_M_VALUES)
        if eta_filter is not None:
            expr = expr & eta_filter
        for batch in dataset.to_batches(columns=cols, filter=expr):
            chunk = batch.to_pandas()
            if chunk.empty:
                continue
            chunk['value'] = [_last_value(v) for v in chunk['data']]
            frames.append(chunk.drop(columns=['data']))
    if not frames:
        return pd.DataFrame()
    py = pd.concat(frames, ignore_index=True)

    init = py['init_distr'].astype(str).str.strip()
    py['init_mode'] = init.str.extract(r'([A-Za-z]*)$', expand=False).fillna('')
    py['init_value'] = pd.to_numeric(init.str.replace(r'[A-Za-z]+$', '', regex=True), errors='coerce')
    shape = py['r_shape'].astype(str)
    py['function'] = np.where(py['r_type'].astype(str) == 'static', 'static',
                              np.where(shape.str.contains('poly'), 'polynomial',
                                       np.where(shape == 'direct', 'linear', shape)))
    py['control_par'] = np.where(py['function'] == 'static', py['r_value'],
                                 np.where(py['function'] == 'polynomial', py['sigmd_par'], 0.0))
    py['eta'] = pd.to_numeric(py['eta'], errors='coerce').round(3)
    py['control_par'] = pd.to_numeric(py['control_par'], errors='coerce').round(3)
    return py

class PythonBoxes:
    """Per-run Python values for an ARGoS panel, cached by setting."""

    def __init__(self, py: pd.DataFrame):
        self.py = py
        self.cache = {}
        if py is None or py.empty:
            self.groups = {}
            return
        keys = ['n_options', 'init_value', 'msg_time_exp', 'msg_per_step', 'function', 'control_par', 'eta']
        # Initialization 'a' (or none): the one used by the ARGoS arena
        sel = py[py['init_mode'].isin(['a', ''])]
        self.groups = {self._key(*k): g for k, g in sel.groupby(keys)}

    @staticmethod
    def _key(n_opts, init, mt, m, func, ctrl, eta):
        return (int(n_opts), round(float(init), 3), int(mt), int(m), str(func), round(float(ctrl), 3), round(float(eta), 3))

    def _per_run(self, n_opts, init, mt, m, func, ctrl, eta, eta_target):
        group = self.groups.get(self._key(n_opts, init, mt, m, func, ctrl, eta))
        if group is None:
            return None
        # One value per run: the best option, or the winning option when every option is equal
        by_run = group.pivot_table(index='run_id', columns='option_id', values='value', aggfunc='last')
        by_run = by_run[[c for c in by_run.columns if c != -1]]
        if by_run.empty:
            return None
        symmetric = np.isclose(eta_target, (n_opts - 1.0) / n_opts, atol=1e-3)
        if symmetric:
            return by_run.max(axis=1)
        return by_run[0] if 0 in by_run.columns else None

    def box(self, n_opts, init, argos_msg_time, m, func, ctrl, eta_target):
        mt = MSG_TIME_MAP.get(int(argos_msg_time)) if pd.notnull(argos_msg_time) else None
        if mt is None or not self.groups:
            return np.array([])
        cache_key = (n_opts, init, mt, m, func, ctrl, eta_target)
        if cache_key in self.cache:
            return self.cache[cache_key]
        exact = self._per_run(n_opts, init, mt, m, func, ctrl, eta_target, eta_target)
        if exact is not None:
            values = exact.dropna().to_numpy()
        else:
            # ARGoS eta not in the Python grid: average of the two eta values around it, run by run
            lo = self._per_run(n_opts, init, mt, m, func, ctrl, eta_target - PY_ETA_HALF_STEP, eta_target)
            hi = self._per_run(n_opts, init, mt, m, func, ctrl, eta_target + PY_ETA_HALF_STEP, eta_target)
            if lo is None or hi is None:
                values = np.array([])
            else:
                both = pd.concat([lo, hi], axis=1, join='inner').dropna()
                values = both.mean(axis=1).to_numpy()
        self.cache[cache_key] = values
        return values

##################################################################################
# 4. PLOTTING
##################################################################################

def _figure_path(setting: dict) -> Path:
    """Folder and file name of a figure: one folder level per setting not shown in the panels.

    options_<n>/corr_<c>/rebroadcast_<r>_hop_<h>/timeout_<s>s_python_mt<m>[_arena<a>][_runs<k>]
    """
    rb, hop = int(setting['communication']), int(setting['hop_count'])
    folder = (Path(f"options_{int(setting['n_options'])}") / f"corr_{setting['spat_corr']:g}"
              / f"rebroadcast_{rb}_hop_{hop}")
    mt = int(setting['msg_exp_time'])
    name = f"timeout_{mt}s" + (f"_python_mt{MSG_TIME_MAP[mt]}" if mt in MSG_TIME_MAP else "")
    if setting.get('arena'):
        name += f"_arena{setting['arena']}"
    if pd.notnull(setting.get('n_runs')):
        name += f"_runs{int(setting['n_runs'])}"
    return folder / name

def _select(df, eta, func, ctrl, m):
    if df is None or df.empty:
        return pd.DataFrame()
    mask = (np.isclose(df['eta'], eta, atol=1e-3)
            & (df['function'] == func)
            & np.isclose(df['control_par'], ctrl, atol=1e-3)
            & (df['vote_msg'] == m))
    return df[mask]

def plot_setting(setting: dict, coh: pd.DataFrame, msgs: pd.DataFrame, boxes: PythonBoxes,
                 output_path: Path, cfg: dict) -> int:
    """One figure for one ARGoS setting (coh/msgs already restricted to it)."""
    n_opts = int(setting['n_options'])
    eta_main, eta_inset = ETAS_BY_OPTIONS.get(n_opts, (None, None))
    if eta_main is None:
        logging.warning(f"No eta pair for {n_opts} options, setting skipped")
        return 0
    configs = row_configs(coh, cfg)
    m_values = [int(m) for m in _wanted(coh['vote_msg'], cfg.get("m"))]
    pyth_color = 'tab:gray'

    panels = []
    for conf in configs:
        for m in m_values:
            p = {'conf': conf, 'm': m}
            for which, eta in (('main', eta_main), ('inset', eta_inset)):
                a = _select(coh, eta, conf['func'], conf['ctrl'], m)
                p[f'a_{which}'] = a
                p[f'msg_{which}'] = _select(msgs, eta, conf['func'], conf['ctrl'], m)
                init = a['init_distr'].iloc[0] if not a.empty and 'init_distr' in a.columns else np.nan
                p[f'p_{which}'] = (boxes.box(n_opts, init, setting['msg_exp_time'], m, conf['func'], conf['ctrl'], eta)
                                   if pd.notnull(init) else np.array([]))
            if not (p['a_main'].empty and p['a_inset'].empty):
                panels.append(p)
    if not panels:
        return 0

    # Fixed grid: one row per control function, one column per m (cells without data stay empty)
    row_labels = [c['label'] for c in configs if any(p['conf'] is c for p in panels)]
    col_values = [m for m in m_values if any(p['m'] == m for p in panels)]
    n_rows, n_cols = len(row_labels), len(col_values)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows + 0.8), squeeze=False,
                             sharex=True, sharey=True)
    used = np.zeros((n_rows, n_cols), dtype=bool)
    any_box = False
    any_msgs = False

    for p in panels:
        row_idx = row_labels.index(p['conf']['label'])
        col_idx = col_values.index(p['m'])
        used[row_idx, col_idx] = True
        ax = axes[row_idx, col_idx]
        max_x = 0
        final_opt0 = 0.5
        if not p['a_main'].empty:
            ends = [d[~np.isnan(d)][-1] for d in p['a_main']['data'] if np.any(~np.isnan(d))]
            if ends: final_opt0 = float(np.mean(ends))
        has_inset = not p['a_inset'].empty or len(p['p_inset']) > 0
        ax_in = None
        if has_inset:
            ax_in = ax.inset_axes([0.275, 0.05, 0.45, 0.5] if final_opt0 > 0.5 else [0.275, 0.45, 0.45, 0.5])
            ax_in.grid(alpha=0.2)

        def draw(a_df, msg_df, target_ax):
            nonlocal max_x, any_msgs
            for _, row in a_df.iterrows():
                y, ci = row['data'], row['ci95']
                n = min(len(y), len(ci))
                if n == 0: continue
                x = np.arange(n)
                max_x = max(max_x, n)
                target_ax.plot(x, y[:n], color='black', linestyle='-', linewidth=2)
                if np.any(~np.isnan(ci[:n])):
                    target_ax.fill_between(x, y[:n] - ci[:n], y[:n] + ci[:n], facecolor='black', alpha=0.25)
            for _, row in msg_df.iterrows():
                y = row['data']
                if len(y) == 0: continue
                max_x = max(max_x, len(y))
                target_ax.plot(np.arange(len(y)), y, color='black', linestyle=(0, (5, 5)), linewidth=2)
                any_msgs = True

        draw(p['a_main'], p['msg_main'], ax)
        if ax_in is not None:
            draw(p['a_inset'], p['msg_inset'], ax_in)

        box_width = max(1, max_x * 0.05)
        box_pos = max_x + box_width * 1.5
        for values, target_ax in [(p['p_main'], ax), (p['p_inset'], ax_in)]:
            if target_ax is None or len(values) == 0:
                continue
            bp = target_ax.boxplot(values, positions=[box_pos], widths=box_width, patch_artist=True, showfliers=False)
            for patch in bp['boxes']:
                patch.set_facecolor(pyth_color)
                patch.set_alpha(0.7)
            for median in bp['medians']:
                median.set_color('black')
            any_box = True

        y_ticks = np.linspace(0, 1.0, 5)
        ax.set_xlim(left=0, right=box_pos + box_width * 2)
        ax.set_ylim(-0.03, 1.03)
        ax.set_yticks(y_ticks)
        # x in ARGoS ticks (10 per second): labels in seconds
        major_step, minor_step = 9000, 3000
        major = np.arange(0, max_x + 1, major_step)
        ax.set_xticks(list(major) + [box_pos])
        ax.set_xticklabels([str(int(t * 0.1)) for t in major] + [""])
        ax.set_xticks(np.arange(0, max_x + 1, minor_step), minor=True)
        ax.grid(which='major', ls="--", alpha=0.4)
        ax.grid(which='minor', ls="--", alpha=0.4)
        if ax_in is not None:
            ax_in.set_xlim(ax.get_xlim())
            ax_in.set_xticks(list(major) + [box_pos])
            ax_in.set_xticks(np.arange(0, max_x + 1, minor_step), minor=True)
            ax_in.set_ylim(-0.03, 1.03)
            ax_in.set_yticks(y_ticks)
            ax_in.tick_params(axis='both', which='both', labelbottom=False, labelleft=False, bottom=True, left=True, length=2)

        if row_idx == 0:
            ax.set_title(rf"$m={p['m']}$")
        if col_idx == n_cols - 1:
            ax.text(1.05, 0.5, p['conf']['label'], transform=ax.transAxes, ha='left', va='center', rotation=270)
        if row_idx == n_rows - 1:
            ax.set_xlabel("T (s)")

    for r in range(n_rows):
        for c in range(n_cols):
            if not used[r, c]:
                axes[r, c].set_visible(False)

    legend = [Line2D([0], [0], color='black', ls='-', lw=4, label=r'$\rho^*$')]
    if any_msgs:
        legend.append(Line2D([0], [0], color='black', ls='--', lw=4, label=r'$\|\mathcal{B}\|$'))
    if any_box:
        legend.append(Patch(facecolor=pyth_color, edgecolor='black', alpha=0.7, label='agent-based'))
    fig.legend(handles=legend, loc='upper right', bbox_to_anchor=(0.96, .015), ncol=len(legend))
    fig.tight_layout()
    target = output_path / _figure_path(setting)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target.with_suffix(".pdf"), dpi=300, bbox_inches="tight")
    fig.savefig(target.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    return 1

def plot_condensed_hybrid(coh: pd.DataFrame, msgs: pd.DataFrame, boxes: PythonBoxes, cfg: dict) -> int:
    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "cohesion_hybrid_condensed"
    output_path.mkdir(parents=True, exist_ok=True)
    # The dominant option (option_id 0) is the plotted density
    coh = coh[coh['option_id'] == 0]
    # Figures chosen in the config
    for key, col in (("options", "n_options"), ("spatial_correlation", "spat_corr"),
                     ("rebroadcast", "communication"), ("msg_timeout", "msg_exp_time")):
        if cfg.get(key) is not None:
            coh = coh[coh[col].round(3).isin({round(float(v), 3) for v in cfg[key]})]
    keys = [k for k in FIGURE_KEYS if k in coh.columns]
    count = 0
    for values, group in coh.groupby(keys, dropna=False):
        setting = dict(zip(keys, values))
        msg_mask = pd.Series(True, index=msgs.index) if not msgs.empty else None
        if not msgs.empty:
            for k in keys:
                if k in msgs.columns:
                    msg_mask &= (msgs[k] == setting[k]) | (msgs[k].isna() & pd.isna(setting[k]))
        msg_group = msgs[msg_mask] if not msgs.empty else msgs
        count += plot_setting(setting, group, msg_group, boxes, output_path, cfg)
    return count

##################################################################################
# 5. CHECKS AND MAIN
##################################################################################

def count_configuration_overlaps(coh: pd.DataFrame, boxes: PythonBoxes) -> None:
    """Print the ARGoS panels without a matching Python setting."""
    coh = coh[coh['option_id'] == 0]
    missing = []
    total = 0
    for _, row in coh.drop_duplicates(subset=['n_options', 'init_distr', 'msg_exp_time', 'vote_msg', 'function', 'control_par', 'eta']).iterrows():
        total += 1
        values = boxes.box(int(row['n_options']), row['init_distr'], row['msg_exp_time'], int(row['vote_msg']),
                           row['function'], row['control_par'], row['eta'])
        if len(values) == 0:
            missing.append((int(row['n_options']), row['eta'], row['function'], row['control_par'], int(row['vote_msg']), row['msg_exp_time']))
    print(f"ARGoS settings: {total}, with a matching Python boxplot: {total - len(missing)}")
    for m in missing:
        print(f"  no Python data: options={m[0]} eta={m[1]} {m[2]} {m[3]} m={m[4]} timeout={m[5]}")

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--python-data", default=os.path.join("..", "quorum_sensing_Best_of_N", "compressed_data"),
                        help="folder with the Python results_processed_*_residence_data.parquet files")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"JSON file choosing the figures, rows and columns to plot (default {DEFAULT_CONFIG})")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    coh = load_argos_metric("cohesion")
    msgs = load_argos_metric("msgs")
    if coh.empty:
        print("No ARGoS cohesion data in proc_data/cohesion")
        return
    boxes = PythonBoxes(load_python_final_values(args.python_data, coh))
    count_configuration_overlaps(coh, boxes)
    total = plot_condensed_hybrid(coh, msgs, boxes, load_plot_config(args.config))
    print(f"\nExecution finished. Total images saved: {total}")

if __name__ == "__main__":
    main()
