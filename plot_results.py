import os, re, logging
from typing import Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 16})

##################################################################################
# 1. DATA PARSING AND CONVERSION
##################################################################################

def _cast_metadata_value(raw_value: str):
    """Casts string values extracted from filenames to correct Python types."""
    if raw_value == "": return raw_value
    try: return int(raw_value)
    except ValueError:
        try: return float(raw_value)
        except ValueError: return raw_value

def m_array_from_cell(cell_value) -> np.ndarray:
    """Converts cell content into float NumPy arrays. Handles scalars and strings."""
    if isinstance(cell_value, (float, int, np.number)):
        return np.array([float(cell_value)], dtype=float)
    if isinstance(cell_value, np.ndarray):
        return cell_value.astype(float, copy=False)
    if isinstance(cell_value, (list, tuple)):
        return np.asarray(cell_value, dtype=float)
    if isinstance(cell_value, str):
        clean = cell_value.replace('[', '').replace(']', '').strip()
        parts = re.split(r'[\s,]+', clean)
        return np.array([float(p) for p in parts if p], dtype=float)
    raise ValueError(f"Unsupported data type in cell: {type(cell_value).__name__}")

##################################################################################
# 2. FILENAME AND METADATA MANAGEMENT
##################################################################################

# Keys to explicitly remove from generated filenames
EXCLUDED_FILENAME_KEYS = {
    "cohesion_adaptive_com", "adaptive_com", "agents", "arena", "comm_type", 
    "id_aware", "msg_hops", "priority_k", "runs", "spatcorr", "time", "variation_time"
}

def _safe_filename_from_params(values: dict) -> str:
    """
    Generates a safe filename using ONLY experimental parameters.
    Prevents 'File name too long' errors by ignoring data columns and excluded keys.
    """
    allowed_params = {
        "communication", "msg_exp_time", "eta", "eta_stop", "control_par", "options"
    }
    
    safe_parts = []
    priority_order = [
        "communication", "msg_exp_time", "eta", "eta_stop", "control_par", "options"
    ]
    
    for key in priority_order:
        if key in values and key in allowed_params and key not in EXCLUDED_FILENAME_KEYS:
            val = values[key]
            if not isinstance(val, (list, np.ndarray, pd.Series)):
                clean = f"{key}#{val}".replace("/", "-").replace(" ", "").replace(":", "-")
                safe_parts.append(clean)
                
    return "_".join(safe_parts) if safe_parts else "plot"


def _safe_filename_from_metadata(values: dict) -> str:
    """Generates a safe filename using all scalar metadata key/value pairs, excluding filtered keys."""
    safe_parts = []
    for key in sorted(values.keys()):
        if key in EXCLUDED_FILENAME_KEYS:
            continue
            
        val = values[key]
        if isinstance(val, (list, tuple, np.ndarray, pd.Series, dict, set)):
            continue
            
        clean = f"{key}#{val}".replace("/", "-").replace(" ", "").replace(":", "-")
        safe_parts.append(clean)
        
    return "_".join(safe_parts) if safe_parts else "plot"

def metadata_from_filename(file_name: str) -> dict:
    """Extracts metadata dictionary from a pickle filename and aligns keys."""
    stem = Path(file_name).stem
    metadata = {}
    
    if "resume_" in stem:
        metadata_section = stem.split("resume_", 1)[1]
    elif "results_processed_" in stem:
        metadata_section = stem.split("results_processed_", 1)[1]
        # Clean up the trailing identifiers in Python filenames
        metadata_section = metadata_section.split("_residence_data")[0]
    else:
        return {}

    # Define the bijective mapping T: K_{python} -> K_{argos}
    key_translation = {
        "o": "options",
        "r_shape": "function",
        "msg_per_step": "vote_msg",
        "sigmd_par": "control_par",
    }

    parts = metadata_section.split("_")
    for part in parts:
        if "#" not in part: continue
        col_name, col_value = part.split("#", 1)
        
        # Translate the key to match ARGoS standards
        mapped_key = key_translation.get(col_name, col_name)
        parsed_value = _cast_metadata_value(col_value)
            
        metadata[mapped_key] = parsed_value
        
    return metadata

def load_pickles_with_file_meta(proc_dir: str, file_meta_keys: set) -> list:
    """Loads all .pkl files and returns list of (df, file_meta) tuples."""
    base_path = Path(os.path.abspath("")) / proc_dir
    if not base_path.exists():
        return []
    all_files = sorted(base_path.glob("*resume_*.pkl"))+sorted(base_path.glob("*results_processed_*.pkl"))
    datasets = []
    for file_path in all_files:
        try:
            file_df = pd.read_pickle(file_path)
            if not isinstance(file_df, pd.DataFrame):
                file_df = pd.DataFrame(file_df)
            metadata = metadata_from_filename(file_path.name)
            df_meta = {k: v for k, v in metadata.items() if k not in file_meta_keys}
            file_meta = {k: v for k, v in metadata.items() if k in file_meta_keys}
            for col_name, col_value in df_meta.items():
                file_df[col_name] = col_value
            datasets.append((file_df, file_meta))
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
    return datasets

##################################################################################
# 3. VISUALIZATION UTILS
##################################################################################

def _function_colormap(function_names):
    """Maps each function name to a specific Colormap."""
    cmap_cycle = ["Blues", "Oranges", "Greens", "Purples", "Reds", "Greys", "YlGnBu", "YlOrBr"]
    mapping = {}
    for idx, fn in enumerate(sorted(function_names)):
        mapping[fn] = plt.get_cmap(cmap_cycle[idx % len(cmap_cycle)])
    return mapping

##################################################################################
# 4. STANDARD PLOTTING
##################################################################################

def _iter_groups(df: pd.DataFrame, grouping_cols: list):
    """Yields (key_dict, group_df) even when no grouping columns are available."""
    if not grouping_cols:
        yield {}, df
        return

    for group_key, group_df in df.groupby(grouping_cols, dropna=False):
        if isinstance(group_key, tuple):
            yield dict(zip(grouping_cols, group_key)), group_df
        else:
            yield {grouping_cols[0]: group_key}, group_df


def _vote_color_map(vote_values):
    """Stable color mapping keyed by vote_msg."""
    cmap = plt.get_cmap("tab10")
    return {vote: cmap(idx % 10) for idx, vote in enumerate(sorted(vote_values))}


def plot_cohesion_df(result_df: pd.DataFrame, file_meta: Optional[dict] = None) -> int:
    """
    Cohesion line plots with std shadow.
    Combines 'static' (control_par=0.8) and 'polynomial' (dynamic control_par) on the same plot.
    """
    required_cols = {"option_id", "vote_msg", "data", "std", "function", "control_par"}
    missing = required_cols.difference(result_df.columns)
    if missing:
        raise ValueError(f"plot_cohesion_df missing required columns: {sorted(missing)}")

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "cohesion"
    output_path.mkdir(parents=True, exist_ok=True)

    exclude_cols = {"option_id", "vote_msg", "function", "data", "std", "control_par"}
    grouping_cols = [c for c in result_df.columns if c not in exclude_cols]
    image_count = 0

    function_cmaps = {
        "static": plt.get_cmap("Reds"),
        "polynomial": plt.get_cmap("Blues"),
        "linear": plt.get_cmap("Greens")
    }

    file_meta = file_meta or {}
    for group_meta, gdf in _iter_groups(result_df, grouping_cols):
        
        poly_df = gdf[gdf["function"] == "polynomial"]
        if poly_df.empty:
            poly_ctrl_vals = [None]
        else:
            poly_ctrl_vals = sorted(poly_df["control_par"].dropna().unique().tolist())

        for ctrl_val in poly_ctrl_vals:
            if ctrl_val is not None:
                mask_poly = (gdf["function"] == "polynomial") & (np.isclose(gdf["control_par"].astype(float), float(ctrl_val)))
                mask_static = (gdf["function"] == "static") & (np.isclose(gdf["control_par"].astype(float), 0.8))
                mask_linear = (gdf["function"] == "linear") & (np.isclose(gdf["control_par"].astype(float), 0.0))
                
                plot_df = gdf[mask_poly | mask_static | mask_linear]
                curr_meta = {**group_meta, **file_meta, "control_par": ctrl_val}
            else:
                plot_df = gdf
                curr_meta = {**group_meta, **file_meta}

            option_1_df = plot_df[plot_df["option_id"] == 0]
            option_2_df = plot_df[plot_df["option_id"] == 1]
            
            if option_1_df.empty and option_2_df.empty:
                continue

            fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
            panel_data = [(1, option_1_df, axes[0]), (2, option_2_df, axes[1])]

            for option_id, opt_df, ax in panel_data:
                if opt_df.empty:
                    ax.set_title(f"Option {option_id} (no data)")
                    ax.set_xlabel("step")
                    ax.grid(alpha=0.25)
                    continue

                for function_name in sorted(opt_df["function"].astype(str).unique().tolist()):
                    fn_df = opt_df[opt_df["function"].astype(str) == function_name]
                    votes = sorted(fn_df["vote_msg"].dropna().unique().tolist())
                    
                    cmap = function_cmaps.get(function_name, plt.get_cmap("Greys"))
                    vote_shades = np.linspace(0.45, 0.9, max(1, len(votes)))
                    vote_to_color = {v: cmap(vote_shades[idx]) for idx, v in enumerate(votes)}

                    for _, row in fn_df.iterrows():
                        data_arr = m_array_from_cell(row["data"])
                        std_arr = m_array_from_cell(row["std"])
                        n_steps = min(len(data_arr), len(std_arr))
                        if n_steps == 0:
                            continue

                        x = np.arange(n_steps)
                        y = data_arr[:n_steps]
                        s = std_arr[:n_steps]
                        vote = row["vote_msg"]
                        color = vote_to_color.get(vote, cmap(0.7))
                        label = f"f:{function_name} | m:{vote}"

                        ax.plot(x, y, color=color, linewidth=2.0, label=label)
                        # ax.fill_between(x, y - s, y + s, color=color, alpha=0.18)
                        
                ax.set_ylim(-0.03, 1.03)
                ax.set_title(f"Option {option_id}")
                ax.set_xlabel("step")
                ax.grid(alpha=0.25)
                handles, labels = ax.get_legend_handles_labels()
                polynomial_group = []
                static_group = []
                linear_group = []

                # Now you have three separate lists
                if handles:
                    uniq = dict(zip(labels, handles))
                    # Sort the labels alphanumerically
                    sorted_labels = sorted(uniq.keys())
                    for label in sorted_labels:
                        if "polynomial" in label:
                            polynomial_group.append(label)
                        elif "static" in label:
                            static_group.append(label)
                        elif "linear" in label:
                            linear_group.append(label)
                    polynomial_group = sorted(polynomial_group, key=lambda x: int(x.split("m:")[-1]))
                    static_group = sorted(static_group, key=lambda x: int(x.split("m:")[-1]))
                    linear_group = sorted(linear_group, key=lambda x: int(x.split("m:")[-1]))
                    sorted_handles = [uniq[lbl] for lbl in static_group]+[uniq[lbl] for lbl in linear_group]+[uniq[lbl] for lbl in polynomial_group]
                    sorted_labels = static_group + linear_group + polynomial_group
                    ax.legend(sorted_handles, sorted_labels, loc="best", frameon=False, fontsize=plt.rcParams.get("font.size"))

            axes[0].set_ylabel("cohesion")
            
            title_suffix = f" (Poly ctrl={ctrl_val}, Static ctrl=0.8, Linear)" if ctrl_val is not None else ""
            fig.suptitle(f"Cohesion{title_suffix}")

            file_name = f"cohesion_{_safe_filename_from_metadata(curr_meta)}.png"
            fig.tight_layout()
            fig.savefig(output_path / file_name, dpi=150, bbox_inches="tight")
            plt.close(fig)
            image_count += 1

    return image_count

def plot_hybrid_cohesion(argos_df: pd.DataFrame, pyth_df: pd.DataFrame) -> int:
    """
    Plots ARGoS timelines and Python Box Plots for the final time step.
    Grouping base: ['control_par', 'eta', 'init_distr']
    Dynamically aggregates Python options:
    - If eta == (N-1)/N: Option 0 is the max, Option 1 is the sum of the rest.
    - Otherwise: Option 0 is statically option 0, Option 1 is the sum of the rest.
    """
    # --- 0. SANITIZE INIT_DISTR ---
    # Strip alphabetic characters from init_distr to ensure correct numeric grouping and calculation
    for df in [argos_df, pyth_df]:
        if not df.empty and 'init_distr' in df.columns:
            df['init_distr'] = df['init_distr'].apply(
                lambda x: float(re.sub(r'[a-zA-Z]', '', str(x))) if pd.notnull(x) and str(x).strip() != '' else x
            )

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "cohesion_hybrid"
    output_path.mkdir(parents=True, exist_ok=True)
    image_count = 0
    
    eta_mapping = {
        0.4: [0.4],
        0.5: [0.5],
        0.7: [0.7],
        0.8: [0.8]
    }
    
    # --- 1. DYNAMIC PYTHON AGGREGATION ---
    py_group_cols = ['function', 'control_par', 'vote_msg', 'eta', 'init_distr', 'communication']
    if not pyth_df.empty:
        pyth_df['data_arr'] = pyth_df['data'].apply(m_array_from_cell) 
        py_group_cols_exist = [c for c in py_group_cols if c in pyth_df.columns]
        
        def process_python_config(group):
            options = sorted(group['option_id'].unique())
            
            # Extract final 10-step mean for each run, aligned by option
            opt_data = {}
            for opt in options:
                opt_rows = group[group['option_id'] == opt]
                vals = []
                for d in opt_rows['data_arr']:
                    if len(d) >= 10:
                        vals.append(np.mean(d[-10:]))
                    elif len(d) > 0:
                        vals.append(np.mean(d)) 
                opt_data[opt] = np.array(vals)
                
            # Align run lengths
            min_runs = min([len(v) for v in opt_data.values()]) if opt_data else 0
            if min_runs == 0:
                return pd.DataFrame()
                
            for opt in options:
                opt_data[opt] = opt_data[opt][:min_runs]
                
            stacked = np.stack([opt_data[opt] for opt in options]) 
            
            # Safely calculate N and check symmetry condition
            try:
                if 'init_distr' in group.columns:
                    init_d = float(group['init_distr'].iloc[0])
                    N = int(round(1.0 / init_d))
                else:
                    N = 2
            except Exception:
                N = 2
                
            eta_val = float(group['eta'].iloc[0]) if 'eta' in group.columns else 0.5
            is_symmetric = np.isclose(eta_val, (N - 1.0) / N, atol=1e-3)
            
            if is_symmetric:
                winning_indices = np.argmax(stacked, axis=0)
                run_indices = np.arange(min_runs)
                opt0_vals = stacked[winning_indices, run_indices]
                
                if len(options) > 1:
                    opt1_vals = np.sum(stacked, axis=0) - opt0_vals
                else:
                    opt1_vals = np.array([])
            else:
                opt0_vals = opt_data[0] if 0 in opt_data else np.zeros(min_runs)
                others = [opt_data[opt] for opt in options if opt > 0]
                if others:
                    opt1_vals = np.sum(np.stack(others), axis=0) 
                else:
                    opt1_vals = np.array([])
                    
            res = []
            if len(opt0_vals) > 0:
                res.append({'option_id': 0, 'box_data': opt0_vals})
            if len(opt1_vals) > 0:
                res.append({'option_id': 1, 'box_data': opt1_vals})
                
            return pd.DataFrame(res)
        
        pyth_agg = pyth_df.groupby(py_group_cols_exist, dropna=False).apply(process_python_config).reset_index()
    else:
        pyth_agg = pd.DataFrame()

    base_group_cols = ['control_par', 'eta', 'init_distr']
    base_group_cols = [c for c in base_group_cols if c in argos_df.columns]
    
    function_cmaps = {
        "static": plt.get_cmap("Reds"),
        "polynomial": plt.get_cmap("Blues"),
        "linear": plt.get_cmap("Greens")
    }
    
    comm_styles = {0: '-', 1: '--', 2: ':'}
    comm_labels = {0: 'IDB', 1: r'$h-IDR_i$', 2: r'$IDR_f$'}
    
    # --- 2. MAIN PLOTTING LOOP ---
    for group_vals, argos_group in argos_df.groupby(base_group_cols, dropna=False):
        group_dict = dict(zip(base_group_cols, group_vals)) if isinstance(group_vals, tuple) else {base_group_cols[0]: group_vals}
        
        pyth_group = pyth_agg
        for k, v in group_dict.items():
            if not pyth_group.empty and k in pyth_group.columns:
                col_numeric = pd.to_numeric(pyth_group[k], errors='coerce').fillna(-999)
                
                if k == 'eta':
                    base_eta = float(v)
                    allowed_etas = [base_eta]
                    for map_k, map_v in eta_mapping.items():
                        if np.isclose(base_eta, map_k, atol=1e-3):
                            allowed_etas.extend(map_v)
                            break
                            
                    mask = pd.Series(False, index=pyth_group.index)
                    for allowed_eta in allowed_etas:
                        mask = mask | np.isclose(col_numeric, float(allowed_eta), atol=1e-3)
                    pyth_group = pyth_group[mask]
                else:
                    if isinstance(v, (float, np.floating, int, np.integer)):
                        pyth_group = pyth_group[np.isclose(col_numeric, float(v), atol=1e-3)]
                    else:
                        pyth_group = pyth_group[pyth_group[k].astype(str) == str(v)]
        
        fig, axes = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
        legend_lines = {}
        comms_in_plot = set()
        has_python = False
        
        for option_id, ax in zip([0, 1], axes):
            if option_id == 0:
                argos_opt = argos_group[argos_group['option_id'] == 0]
                pyth_opt = pyth_group[pyth_group['option_id'] == 0] if not pyth_group.empty else pd.DataFrame()
            else:
                argos_opt = argos_group[argos_group['option_id'] == 1]
                pyth_opt = pyth_group[pyth_group['option_id'] == 1] if not pyth_group.empty else pd.DataFrame()
            
            if argos_opt.empty and pyth_opt.empty:
                ax.grid(alpha=0.25)
                continue
                
            max_x = 0
            boxes_to_draw = []
            box_colors = []
            box_votes = []
            
            funcs_argos = argos_opt['function'].unique() if 'function' in argos_opt.columns else []
            funcs_pyth = pyth_opt['function'].unique() if 'function' in pyth_opt.columns else []
            funcs = sorted(set(funcs_argos).union(set(funcs_pyth)))
            
            for f_name in funcs:
                cmap = function_cmaps.get(str(f_name), plt.get_cmap("Greys"))
                votes_a = argos_opt[argos_opt['function'] == f_name]['vote_msg'].unique() if 'function' in argos_opt.columns else []
                votes_p = pyth_opt[pyth_opt['function'] == f_name]['vote_msg'].unique() if 'function' in pyth_opt.columns else []
                votes = sorted(set(votes_a).union(set(votes_p)))
                
                vote_shades = np.linspace(0.45, 0.9, max(1, len(votes)))
                vote_colors = {v: cmap(vote_shades[idx]) for idx, v in enumerate(votes)}
                
                for vote in votes:
                    color = vote_colors[vote]
                    label_key = f"{f_name} | m={vote}"
                    if label_key not in legend_lines:
                        legend_lines[label_key] = Line2D([], [], color=color, linewidth=2.0, label=label_key)
                    
                    if not argos_opt.empty and 'function' in argos_opt.columns and 'vote_msg' in argos_opt.columns:
                        a_mask = (argos_opt['function'].astype(str) == str(f_name)) & (argos_opt['vote_msg'] == vote)
                        for _, row in argos_opt[a_mask].iterrows():
                            try:
                                data_arr = m_array_from_cell(row['data'])
                                std_arr = m_array_from_cell(row['std'])
                            except Exception: 
                                continue
                                
                            n_steps = min(len(data_arr), len(std_arr))
                            if n_steps == 0: continue
                            max_x = max(max_x, n_steps)
                            
                            x, y, s = np.arange(n_steps), data_arr[:n_steps], std_arr[:n_steps]
                            comm = int(row.get('communication', 0))
                            comms_in_plot.add(comm)
                            ls = comm_styles.get(comm, '-')
                            
                            ax.plot(x, y, color=color, linestyle=ls, linewidth=2.0)
                            # ax.fill_between(x, y-s, y+s, facecolor=color, alpha=0.15)
                            
                    if not pyth_opt.empty and 'function' in pyth_opt.columns and 'vote_msg' in pyth_opt.columns:
                        p_mask = (pyth_opt['function'].astype(str) == str(f_name)) & \
                                 np.isclose(pd.to_numeric(pyth_opt['vote_msg'], errors='coerce').fillna(-999), float(vote), atol=1e-3)
                        
                        matching_pyth = pyth_opt[p_mask]
                        
                        if not matching_pyth.empty:
                            merged_box_data = []
                            for _, row in matching_pyth.iterrows():
                                if 'box_data' in row and len(row['box_data']) > 0:
                                    merged_box_data.extend(row['box_data'])
                            
                            if merged_box_data:
                                boxes_to_draw.append(np.array(merged_box_data))
                                box_colors.append(color)
                                box_votes.append(vote)
                                has_python = True
                                
            if boxes_to_draw:
                if max_x == 0: max_x = 100
                box_width = max(1, max_x * 0.03)
                box_positions = [] 
                
                for i, (b_data, b_color) in enumerate(zip(boxes_to_draw, box_colors)):
                    pos = max_x + box_width * (i*1.3 + 1.5)
                    box_positions.append(pos)
                    bp = ax.boxplot(b_data, positions=[pos], widths=box_width, patch_artist=True, showfliers=False)
                    for patch in bp['boxes']:
                        patch.set_facecolor(b_color)
                        patch.set_alpha(0.65)
                    for median in bp['medians']:
                        median.set_color('black')
                
                current_ticks = ax.get_xticks()
                valid_step_ticks = [t for t in current_ticks if 0 <= t <= max_x]
                all_ticks = valid_step_ticks + box_positions
                all_labels = [str(int(t)) for t in valid_step_ticks] + [str(v) for v in box_votes]
                ax.set_xticks(all_ticks)
                ax.set_xticklabels(all_labels)
                ax.set_xlim(left=0, right=box_positions[-1] + box_width * 2)
                        
            ax.set_ylim(-0.03, 1.03)
            ax.set_xlabel("step / vote_msg") 
            ax.grid(alpha=0.25)
            
        axes[0].set_ylabel(r"$\rho^*$")
        axes[1].set_ylabel(r"$\bar{\rho}^*$")
        
        handles = sorted(list(legend_lines.values()), key=lambda x: int(x.get_label().split("m=")[-1]))
        for c_val in sorted(comms_in_plot):
            handles.append(Line2D([], [], color='black', linestyle=comm_styles.get(c_val, '-'), label=f"ARGoS: {comm_labels.get(c_val, 'Unknown')}"))
        if has_python:
            handles.append(Patch(facecolor='gray', edgecolor='black', alpha=0.6, label='Python BoxPlot'))
            
        axes[1].legend(handles=handles, loc="best", frameon=False, fontsize=plt.rcParams.get("font.size"))
        
        title_parts = [f"{k}={v}" for k, v in group_dict.items()]
        fig.suptitle(f"Cohesion | {' | '.join(title_parts)}")
        
        safe_str = "_".join(title_parts).replace(".", "_").replace(" ", "")
        fig.tight_layout()
        fig.savefig(output_path / f"hybrid_cohesion_{safe_str}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        image_count += 1
        
    return image_count

def plot_condensed_hybrid_cohesion(argos_df: pd.DataFrame, pyth_df: pd.DataFrame, omit_m: list = [15], omit_labels: list = None) -> int:
    """
    Condensed Grid Layout for Hybrid Cohesion Plots.
    - Grid is transposed: configurations are rows, m values are columns.
    - Allows omitting specific m values via `omit_m` (e.g., [9, 15]).
    - Allows omitting specific configurations via `omit_labels` (e.g., ['Linear']).
    - Generates exactly 2 images: one for n_options=2, one for n_options=5.
    - option_id=1 is completely removed from the final plots. We only plot option_id=0.
    - Main panels use eta=0.5 (for opts=2) or eta=0.8 (for opts=5).
    - Insets use eta=0.4 (for opts=2) or eta=0.7 (for opts=5).
    - Filters entirely by eta value to guarantee data is found.
    """
    
    if omit_m is None:
        omit_m = []
    if omit_labels is None:
        omit_labels = []

    # 1. Sanitize init_distr
    for df in [argos_df, pyth_df]:
        if not df.empty and 'init_distr' in df.columns:
            df['init_distr'] = df['init_distr'].apply(
                lambda x: float(re.sub(r'[a-zA-Z]', '', str(x))) if pd.notnull(x) and str(x).strip() != '' else x
            )

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "cohesion_hybrid_condensed"
    output_path.mkdir(parents=True, exist_ok=True)
    image_count = 0
    
    if not argos_df.empty:
        argos_df = argos_df[argos_df['option_id'] == 0].copy()
    if not pyth_df.empty:
        pyth_df = pyth_df.copy()

    # 2. Dynamic Python Aggregation
    py_group_cols = ['function', 'control_par', 'vote_msg', 'eta', 'init_distr', 'communication', 'options', 'n_options', 'n_opts', 'N']
    if not pyth_df.empty:
        pyth_df['data_arr'] = pyth_df['data'].apply(m_array_from_cell) 
        py_group_cols_exist = [c for c in py_group_cols if c in pyth_df.columns]
        
        def process_python_config(group):
            opts = sorted(group['option_id'].unique())
            opt_data = {}
            for opt in opts:
                opt_rows = group[group['option_id'] == opt]
                vals = []
                for d in opt_rows['data_arr']:
                    if len(d) >= 10: vals.append(np.mean(d[-10:]))
                    elif len(d) > 0: vals.append(np.mean(d)) 
                opt_data[opt] = np.array(vals)
                
            min_runs = min([len(v) for v in opt_data.values()]) if opt_data else 0
            if min_runs == 0: return pd.DataFrame()
            for opt in opts: opt_data[opt] = opt_data[opt][:min_runs]
                
            stacked = np.stack([opt_data[opt] for opt in opts]) 
            
            try:
                init_d = float(group['init_distr'].iloc[0]) if 'init_distr' in group.columns else 0.5
                N = int(round(1.0 / init_d)) if init_d > 0 else 2
            except Exception:
                N = 2
                
            eta_val = float(group['eta'].iloc[0]) if 'eta' in group.columns else 0.5
            is_symmetric = np.isclose(eta_val, (N - 1.0) / N, atol=1e-3)
            
            if is_symmetric:
                winning_indices = np.argmax(stacked, axis=0)
                run_indices = np.arange(min_runs)
                opt0_vals = stacked[winning_indices, run_indices]
            else:
                opt0_vals = opt_data[0] if 0 in opt_data else np.zeros(min_runs)
                    
            res = []
            if len(opt0_vals) > 0: 
                res.append({'option_id': 0, 'box_data': opt0_vals})
            return pd.DataFrame(res)
        
        pyth_agg = pyth_df.groupby(py_group_cols_exist, dropna=False).apply(process_python_config, include_groups=False).reset_index()
    else:
        pyth_agg = pd.DataFrame()

    def get_mask(df, target_eta, target_func, target_ctrl, target_vote):
        if df.empty:
            return pd.Series(False, index=df.index)
        mask = pd.Series(True, index=df.index)
        
        if 'eta' in df.columns:
            mask &= np.isclose(pd.to_numeric(df['eta'], errors='coerce'), target_eta, atol=1e-2)
        else:
            return pd.Series(False, index=df.index)
            
        if 'function' in df.columns:
            mask &= df['function'].astype(str).str.strip().str.lower() == target_func.lower()
            
        if 'control_par' in df.columns:
            mask &= np.isclose(pd.to_numeric(df['control_par'], errors='coerce'), target_ctrl, atol=1e-3)
            
        if 'vote_msg' in df.columns:
            mask &= pd.to_numeric(df['vote_msg'], errors='coerce') == target_vote
            
        return mask

    # 3. Grid Configurations & Filtering
    all_configs = [
        {'label': r'Static ($r=0.8$)', 'func': 'static', 'ctrl': 0.8},
        {'label': 'Linear', 'func': 'linear', 'ctrl': 0.0},
        {'label': r'Poly ($X_0=0.5$)', 'func': 'polynomial', 'ctrl': 0.5},
        {'label': r'Poly ($X_0=0.7$)', 'func': 'polynomial', 'ctrl': 0.7}
    ]
    all_m_values = [3, 5, 9, 15]

    configs = [c for c in all_configs if c['label'] not in omit_labels]
    m_values = [m for m in all_m_values if m not in omit_m]

    if not configs or not m_values:
        print("Error: Grid is empty due to omitted values.")
        return 0

    if 'communication' in argos_df.columns:
        unique_comms = sorted(argos_df['communication'].dropna().astype(int).unique().tolist())
    else:
        unique_comms = [0]
        
    num_comms = len(unique_comms)
    cmap_vir = plt.get_cmap('viridis')
    norm = mcolors.Normalize(vmin=0, vmax=num_comms if num_comms > 0 else 1)
    comm_colors = {val: cmap_vir(norm(i)) for i, val in enumerate(unique_comms)}
    
    comm_styles = {0: '-', 1: '-', 2: '-'}
    comm_labels = {0: 'IDB', 1: r'$h-IDR_i$', 2: r'$IDR_f$'}
    for val in unique_comms:
        if val not in comm_styles: comm_styles[val] = '-'
        if val not in comm_labels: comm_labels[val] = f'Comm {val}'
        
    pyth_color = 'tab:gray' 

    # 4. Main Plotting Loop (configs as rows, m as columns)
    for n_opts in [2, 5]:
        eta_main = 0.5 if n_opts == 2 else 0.8
        eta_inset = 0.4 if n_opts == 2 else 0.7
        
        # Squeeze=False ensures axes is always a 2D array, even if row/col length is 1
        fig, axes = plt.subplots(len(configs), len(m_values), figsize=(16, 12), sharex='col', sharey='row', squeeze=False)
        has_data = False
        
        # Iterate over configs for rows and m_values for columns
        for r_idx, c_conf in enumerate(configs):
            for c_idx, m_val in enumerate(m_values):
                ax = axes[r_idx, c_idx]
                
                # Filter data for this cell (Main Eta)
                mask_a_main = get_mask(argos_df, eta_main, c_conf['func'], c_conf['ctrl'], m_val)
                a_main = argos_df[mask_a_main]
                mask_p_main = get_mask(pyth_agg, eta_main, c_conf['func'], c_conf['ctrl'], m_val)
                p_main = pyth_agg[mask_p_main] if not pyth_agg.empty else pd.DataFrame()

                # Filter data for this cell (Inset Eta)
                mask_a_inset = get_mask(argos_df, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)
                a_inset = argos_df[mask_a_inset]
                mask_p_inset = get_mask(pyth_agg, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)
                p_inset = pyth_agg[mask_p_inset] if not pyth_agg.empty else pd.DataFrame()

                if a_main.empty and p_main.empty and a_inset.empty and p_inset.empty:
                    ax.grid(alpha=0.25)
                    continue
                    
                has_data = True
                max_x = 0
                final_opt0_val = 0.5 
                
                if not a_main.empty:
                    end_vals = []
                    for _, row in a_main.iterrows():
                        arr = m_array_from_cell(row['data'])
                        if len(arr) > 0: end_vals.append(arr[-1])
                    if end_vals: final_opt0_val = np.mean(end_vals)
                
                inset_loc = [0.35, 0.05, 0.45, 0.4] if final_opt0_val > 0.5 else [0.35, 0.55, 0.45, 0.4]
                ax_in = ax.inset_axes(inset_loc)
                ax_in.grid(alpha=0.2)
                
                def plot_target(a_df, p_df, target_ax):
                    nonlocal max_x
                    for _, row in a_df.iterrows():
                        try:
                            y = m_array_from_cell(row['data'])
                            s = m_array_from_cell(row['std'])
                        except Exception: continue
                        
                        n_steps = min(len(y), len(s))
                        if n_steps == 0: continue
                        max_x = max(max_x, n_steps)
                        
                        comm = int(row.get('communication', 0))
                        c_color = comm_colors.get(comm, 'black')
                        c_style = comm_styles.get(comm, '-')
                        
                        x_arr = np.arange(n_steps)
                        target_ax.plot(x_arr, y[:n_steps], color=c_color, linestyle=c_style, linewidth=1.5)
                        target_ax.fill_between(x_arr, y[:n_steps]-s[:n_steps], y[:n_steps]+s[:n_steps], facecolor=c_color, alpha=0.15)
                    
                    merged_box = []
                    if not p_df.empty:
                        for _, row in p_df.iterrows():
                            if 'box_data' in row and len(row['box_data']) > 0:
                                merged_box.extend(row['box_data'])
                    return merged_box

                box_main = plot_target(a_main, p_main, ax)
                box_inset = plot_target(a_inset, p_inset, ax_in)

                box_width = max(1, max_x * 0.05)
                box_pos = max_x + box_width * 1.5
                
                for merged_box, target_ax in [(box_main, ax), (box_inset, ax_in)]:
                    if merged_box:
                        bp = target_ax.boxplot(merged_box, positions=[box_pos], widths=box_width, patch_artist=True, showfliers=False)
                        for patch in bp['boxes']:
                            patch.set_facecolor(pyth_color)
                            patch.set_alpha(0.7)
                        for median in bp['medians']:
                            median.set_color('black')
                            
                ax.set_xlim(left=0, right=box_pos + box_width * 2)
                ax.set_ylim(-0.03, 1.03)
                
                line_ticks = np.arange(0, max_x + 1, 1500)
                all_ticks = list(line_ticks) + [box_pos]
                all_labels = [str(int(t*.1)) for t in line_ticks] + [""]
                
                ax.set_xticks(all_ticks)
                ax.set_xticklabels(all_labels)
                
                ax_in.set_xlim(ax.get_xlim())
                ax_in.set_ylim(ax.get_ylim())
                ax_in.set_xticks(all_ticks)
                ax_in.tick_params(labelbottom=False, labelleft=False, labeltop=False, labelright=False)
                
                ax.grid(alpha=0.25)
                
                # Axes Labels
                if c_idx == 0:
                    ax.set_ylabel(r"$\rho^*$")
                if r_idx == 0:
                    ax.text(0.5, 1.125, rf"$m={m_val}$", transform=ax.transAxes, ha='center', va='top')
                if c_idx == len(m_values) - 1:
                    ax.text(1.05, 0.5, c_conf['label'], transform=ax.transAxes, ha='left', va='center', rotation=270)
                if r_idx == len(configs) - 1:
                    ax.set_xlabel("T")

        if not has_data:
            plt.close(fig)
            continue
            
        legend_elements = [
            Line2D([0], [0], color=comm_colors[k], ls='None', marker='s', markersize=8, label=f"{comm_labels.get(k, 'Unknown')}") 
            for k in unique_comms
        ]
        legend_elements.append(Patch(facecolor=pyth_color, edgecolor='black', alpha=0.7, label='agent-based'))
        
        fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.96, .015), ncol=len(unique_comms)+1)
        
        fig.tight_layout()
        fig.savefig(output_path / f"condensed_hybrid_opts{n_opts}.pdf", dpi=150, bbox_inches="tight")
        plt.close(fig)
        image_count += 1
        
    return image_count

def plot_accuracy_df(result_df: pd.DataFrame, file_meta: Optional[dict] = None) -> int:
    """Accuracy bar plot with eta on x-axis.
    Combines 'static' (control_par=0.8) and 'polynomial' (dynamic control_par) on the same plot.
    """
    required_cols = {"eta", "vote_msg", "data", "function", "control_par"}
    missing = required_cols.difference(result_df.columns)
    if missing:
        raise ValueError(f"plot_accuracy_df missing required columns: {sorted(missing)}")

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "accuracy"
    output_path.mkdir(parents=True, exist_ok=True)

    exclude_cols = {"eta", "vote_msg", "function", "data", "std", "control_par"}
    grouping_cols = [c for c in result_df.columns if c not in exclude_cols]
    image_count = 0

    function_cmaps = {
        "static": plt.get_cmap("Reds"),
        "polynomial": plt.get_cmap("Blues")
    }

    file_meta = file_meta or {}
    for group_meta, gdf in _iter_groups(result_df, grouping_cols):
        
        poly_df = gdf[gdf["function"] == "polynomial"]
        if poly_df.empty:
            poly_ctrl_vals = [None]
        else:
            poly_ctrl_vals = sorted(poly_df["control_par"].dropna().unique().tolist())

        for ctrl_val in poly_ctrl_vals:
            if ctrl_val is not None:
                mask_poly = (gdf["function"] == "polynomial") & (np.isclose(gdf["control_par"].astype(float), float(ctrl_val)))
                mask_static = (gdf["function"] == "static") & (np.isclose(gdf["control_par"].astype(float), 0.8))
                
                work = gdf[mask_poly | mask_static].copy()
                curr_meta = {**group_meta, **file_meta, "control_par": ctrl_val}
            else:
                work = gdf.copy()
                curr_meta = {**group_meta, **file_meta}

            if work.empty:
                continue

            work["metric"] = work["data"].apply(lambda x: float(np.mean(m_array_from_cell(x))))
            if "function" not in work.columns:
                work["function"] = ""
                
            agg = work.groupby(["eta", "vote_msg", "function"], dropna=False)["metric"].agg(["mean", "std"]).reset_index()
            if agg.empty:
                continue

            eta_values = np.array(sorted(agg["eta"].dropna().unique().tolist()), dtype=float)
            if eta_values.size == 0:
                continue

            funcs = sorted(agg["function"].dropna().unique().tolist())
            pairs = agg[["function", "vote_msg"]].drop_duplicates().apply(tuple, axis=1).tolist()
            pairs.sort()
            total_series = len(pairs)

            if eta_values.size > 1:
                min_gap = float(np.min(np.diff(eta_values)))
            else:
                min_gap = 0.1
            cluster_w = min_gap * 0.8
            bar_w = cluster_w / max(1, total_series)

            pair_colors = {}
            for f in funcs:
                votes_for_f = sorted(agg[agg["function"] == f]["vote_msg"].dropna().unique().tolist())
                cmap = function_cmaps.get(f, plt.get_cmap("Greys"))
                shades = np.linspace(0.45, 0.9, max(1, len(votes_for_f)))
                for idx, v in enumerate(votes_for_f):
                    pair_colors[(f, v)] = cmap(shades[idx])

            fig, ax = plt.subplots(figsize=(11, 6))
            for j, (f, v) in enumerate(pairs):
                sub = agg[(agg["function"] == f) & (agg["vote_msg"] == v)]
                means = sub.set_index("eta")["mean"].reindex(eta_values).to_numpy(dtype=float)
                stds = sub.set_index("eta")["std"].reindex(eta_values).to_numpy(dtype=float)
                stds = np.nan_to_num(stds, nan=0.0)

                pos = eta_values - (cluster_w / 2.0) + (j + 0.5) * bar_w
                ax.bar(pos, means, width=bar_w, yerr=stds, capsize=3,
                       label=f"{f} m:{v}", color=pair_colors.get((f, v), "gray"), alpha=0.85)

            ax.set_xticks(eta_values)
            ax.set_xticklabels([str(e) for e in eta_values])
            ax.set_xlim(eta_values.min() - cluster_w * 0.6, eta_values.max() + cluster_w * 0.6)
            ax.set_xlabel(r"$\eta$")
            ax.set_ylabel("accuracy (%)")
            ax.set_ylim(-0.03,103)
            
            title_suffix = f" (Poly ctrl={ctrl_val}, Static ctrl=0.8)" if ctrl_val is not None else ""
            ax.set_title(f"Accuracy by eta{title_suffix}")
            ax.grid(axis="y", alpha=0.25)
            
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                uniq = dict(zip(labels, handles))
                # Sort the labels alphanumerically
                sorted_labels = sorted(uniq.keys())
                sorted_handles = [uniq[lbl] for lbl in sorted_labels]
                ax.legend(sorted_handles, sorted_labels, frameon=False, loc="best")

            file_name = f"accuracy_{_safe_filename_from_params(curr_meta)}.png"
            fig.tight_layout()
            fig.savefig(output_path / file_name, dpi=150, bbox_inches="tight")
            plt.close(fig)
            image_count += 1

    return image_count


def plot_time_df(result_df: pd.DataFrame, file_meta: Optional[dict] = None) -> int:
    """Time box plot with eta on x-axis.
    Combines 'static' (control_par=0.8) and 'polynomial' (dynamic control_par) on the same plot.
    """
    required_cols = {"eta", "vote_msg", "data", "function", "control_par"}
    missing = required_cols.difference(result_df.columns)
    if missing:
        raise ValueError(f"plot_time_df missing required columns: {sorted(missing)}")

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "time"
    output_path.mkdir(parents=True, exist_ok=True)

    exclude_cols = {"eta", "vote_msg", "function", "data", "std", "control_par"}
    grouping_cols = [c for c in result_df.columns if c not in exclude_cols]
    image_count = 0

    function_cmaps = {
        "static": plt.get_cmap("Reds"),
        "polynomial": plt.get_cmap("Blues")
    }

    file_meta = file_meta or {}
    for group_meta, base_gdf in _iter_groups(result_df, grouping_cols):
        
        poly_df = base_gdf[base_gdf["function"] == "polynomial"]
        if poly_df.empty:
            poly_ctrl_vals = [None]
        else:
            poly_ctrl_vals = sorted(poly_df["control_par"].dropna().unique().tolist())

        for ctrl_val in poly_ctrl_vals:
            if ctrl_val is not None:
                mask_poly = (base_gdf["function"] == "polynomial") & (np.isclose(base_gdf["control_par"].astype(float), float(ctrl_val)))
                mask_static = (base_gdf["function"] == "static") & (np.isclose(base_gdf["control_par"].astype(float), 0.8))
                
                gdf = base_gdf[mask_poly | mask_static].copy()
                curr_meta = {**group_meta, **file_meta, "control_par": ctrl_val}
            else:
                gdf = base_gdf.copy()
                curr_meta = {**group_meta, **file_meta}

            if gdf.empty:
                continue

            eta_values = np.array(sorted(gdf["eta"].dropna().unique().tolist()), dtype=float)
            if eta_values.size == 0:
                continue

            if "function" not in gdf.columns:
                gdf["function"] = ""

            funcs = sorted(gdf["function"].dropna().unique().tolist())
            pairs = gdf[["function", "vote_msg"]].drop_duplicates().apply(tuple, axis=1).tolist()
            pairs.sort()
            total_series = len(pairs)

            if eta_values.size > 1:
                min_gap = float(np.min(np.diff(eta_values)))
            else:
                min_gap = 0.1
            cluster_w = min_gap * 0.7
            box_w = cluster_w / max(1, total_series)

            pair_colors = {}
            for f in funcs:
                votes_for_f = sorted(gdf[gdf["function"] == f]["vote_msg"].dropna().unique().tolist())
                cmap = function_cmaps.get(f, plt.get_cmap("Greys"))
                shades = np.linspace(0.45, 0.9, max(1, len(votes_for_f)))
                for idx, v in enumerate(votes_for_f):
                    pair_colors[(f, v)] = cmap(shades[idx])

            fig, ax = plt.subplots(figsize=(11, 6))
            has_boxes = False

            for j, (f, v) in enumerate(pairs):
                series_data = []
                positions = []
                for eta in eta_values:
                    subset = gdf[
                        np.isclose(gdf["eta"].astype(float), eta)
                        & (gdf["vote_msg"] == v)
                        & (gdf["function"] == f)
                    ]
                    merged = []
                    for cell in subset["data"].tolist():
                        merged.extend(m_array_from_cell(cell).tolist())
                    if not merged:
                        continue
                    series_data.append(merged)
                    positions.append(float(eta - (cluster_w / 2.0) + (j + 0.5) * box_w))

                if not series_data:
                    continue

                bp = ax.boxplot(
                    series_data,
                    positions=positions,
                    widths=box_w * 0.9,
                    patch_artist=True,
                    manage_ticks=False,
                    showfliers=False,
                )
                for patch in bp["boxes"]:
                    patch.set_facecolor(pair_colors.get((f, v), "gray"))
                    patch.set_alpha(0.55)
                for median in bp["medians"]:
                    median.set_color("black")
                    median.set_linewidth(1.3)
                has_boxes = True

            if not has_boxes:
                plt.close(fig)
                continue

            ax.set_xticks(eta_values)
            ax.set_xticklabels([str(e) for e in eta_values])
            ax.set_xlim(eta_values.min() - cluster_w * 0.6, eta_values.max() + cluster_w * 0.6)
            ax.set_xlabel(r"$\eta$")
            ax.set_ylabel("exit time (ticks)")
            
            title_suffix = f" (Poly ctrl={ctrl_val}, Static ctrl=0.8)" if ctrl_val is not None else ""
            ax.set_title(f"Exit Time by eta{title_suffix}")
            ax.set_ylim(1,10000)
            ax.set_yscale("log")
            ax.grid(axis="y", alpha=0.25)

            # Sort the legend items alphanumerically before plotting
            legend_items = [
                Line2D([0], [0], color=pair_colors[p], lw=0, marker='o', markersize=8, label=f"{p[0]} m:{p[1]}")
                for p in pair_colors
            ]
            legend_items.sort(key=lambda x: x.get_label())

            if legend_items:
                ax.legend(handles=legend_items, frameon=False, loc="best")

            file_name = f"time_{_safe_filename_from_params(curr_meta)}.png"
            fig.tight_layout()
            fig.savefig(output_path / file_name, dpi=150, bbox_inches="tight")
            plt.close(fig)
            image_count += 1

    return image_count

##################################################################################
# 5. PARETO PLOTTING ENGINE
##################################################################################

def plot_pareto_base(merged_df, x_col, x_err_col, y_col, y_err_col, x_label, y_label, sub_folder, file_meta: Optional[dict] = None):
    """Generic Pareto plotter logic."""
    output_path = Path(os.path.abspath("")) / "proc_data" / "pareto" / sub_folder
    output_path.mkdir(parents=True, exist_ok=True)
    
    plot_vars = {"eta", "coh_f", "coh_s", "val_f", "val_s", "vote_msg", "function"}
    grouping_cols = [c for c in merged_df.columns if c not in plot_vars and "data" not in c and "std" not in c and c != "control_par"]
    
    image_count = 0
    markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h']
    
    file_meta = file_meta or {}
    for group_key, base_df in merged_df.groupby(grouping_cols, dropna=False):
        base_meta = dict(zip(grouping_cols, group_key)) if isinstance(group_key, tuple) else {grouping_cols[0]: group_key}
        
        for ctrl in sorted(base_df["control_par"].unique()):
            df = base_df[np.isclose(base_df["control_par"], ctrl)]
            fig, ax = plt.subplots(figsize=(11, 7))
            
            funcs = sorted(df["function"].unique())
            f_cmaps = _function_colormap(funcs)
            etas = sorted(df["eta"].unique())
            eta_m = {e: markers[idx % len(markers)] for idx, e in enumerate(etas)}

            legend_elements = []
            for f in funcs:
                cmap = f_cmaps[f]
                votes = sorted(df[df["function"] == f]["vote_msg"].unique())
                for i, v in enumerate(votes):
                    color = cmap(np.linspace(0.4, 0.9, len(votes))[i])
                    legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=f"{f} (m:{v})"))
            
            legend_elements.append(Line2D([0], [0], color='w', label="")) 
            for e in etas:
                legend_elements.append(Line2D([0], [0], marker=eta_m[e], color='w', markerfacecolor='gray', markersize=10, label=fr"$\eta$ = {e}"))

            for f in funcs:
                cmap = f_cmaps[f]
                f_df = df[df["function"] == f]
                votes = sorted(f_df["vote_msg"].unique())
                for i, v in enumerate(votes):
                    color = cmap(np.linspace(0.4, 0.9, len(votes))[i])
                    v_df = f_df[f_df["vote_msg"] == v]
                    for e in etas:
                        r = v_df[v_df["eta"] == e]
                        if not r.empty:
                            ax.errorbar(r[x_col], r[y_col], 
                                        xerr=r[x_err_col] if x_err_col and x_err_col in r.columns else None, 
                                        yerr=r[y_err_col], fmt=eta_m[e], color=color, markersize=8, capsize=3, alpha=0.8)

            ax.set_xlabel(x_label); ax.set_ylabel(y_label)
            ax.set_title(f"Pareto Trade-off | {sub_folder.replace('_', ' ').title()} | ctrl={ctrl}")
            ax.grid(alpha=0.3)
            ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1), frameon=False)
            ax.set_ylim(-0.03,1.03)
            ax.set_xlim(-0.03,103)
            if "time" in str(output_path):
                ax.set_xlim(1,15000)
                ax.set_xscale("log")
            
            curr_meta = {**base_meta, **file_meta, "control_par": ctrl}
            filename = f"pareto_{_safe_filename_from_params(curr_meta)}.png"
            fig.savefig(output_path / filename, dpi=150, bbox_inches="tight")
            plt.close(fig); image_count += 1
            
    return image_count

def plot_cohesion_accuracy_pareto(coh_df, acc_df, file_meta: Optional[dict] = None):
    """Prepares Cohesion vs Accuracy data."""
    c = coh_df[coh_df["option_id"] == 0].copy()
    c[["coh_f", "coh_s"]] = c.apply(lambda r: pd.Series([np.mean(m_array_from_cell(r["data"])[-100:]), np.mean(m_array_from_cell(r["std"])[-100:])]), axis=1)
    
    a = acc_df.copy()
    a["val_f"] = a["data"].apply(lambda x: np.mean(m_array_from_cell(x)))
    
    ignore_cols = {"data", "std", "coh_f", "coh_s", "val_f", "val_s", "option_id"}
    merge_cols = [col for col in (set(c.columns) & set(a.columns)) if col not in ignore_cols]
    
    merged = pd.merge(c, a, on=merge_cols)
    return plot_pareto_base(merged, "val_f", None, "coh_f", "coh_s", "Accuracy (%)", "Final Cohesion (Avg last 100)", "cohesion_accuracy", file_meta=file_meta)

def plot_cohesion_time_pareto(coh_df, time_df, file_meta: Optional[dict] = None):
    """Prepares Cohesion vs Time data."""
    c = coh_df[coh_df["option_id"] == 0].copy()
    c[["coh_f", "coh_s"]] = c.apply(lambda r: pd.Series([np.mean(m_array_from_cell(r["data"])[-100:]), np.mean(m_array_from_cell(r["std"])[-100:])]), axis=1)
    
    t = time_df.copy()
    t[["val_f", "val_s"]] = t["data"].apply(lambda x: pd.Series([np.median(m_array_from_cell(x)), np.std(m_array_from_cell(x))]))
    
    ignore_cols = {"data", "std", "coh_f", "coh_s", "val_f", "val_s", "option_id"}
    merge_cols = [col for col in (set(c.columns) & set(t.columns)) if col not in ignore_cols]
    
    merged = pd.merge(c, t, on=merge_cols)
    return plot_pareto_base(merged, "val_f", "val_s", "coh_f", "coh_s", "Median Exit Time (Ticks)", "Final Cohesion (Avg last 100)", "cohesion_time", file_meta=file_meta)

##################################################################################
# 6. MAIN EXECUTION
##################################################################################

def count_configuration_overlaps():
    """Conta i match esatti tra le configurazioni escludendo le colonne di dati e ID opzione/run."""
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    file_meta_keys = {'options'}
    
    coh_sets = load_pickles_with_file_meta("./proc_data/cohesion", file_meta_keys)
    pyth_sets = load_pickles_with_file_meta("../quorum_sensing_Best_of_N/compressed_data_argos_comp", file_meta_keys)
    
    
    coh_drop_cols = [
        'adaptive_com', 'comm_type', 'id_aware', 'priority_k', 
        'msg_exp_time', 'msg_hops', 'variation_time', 'eta_stop',
        'time',  'runs', 'arena', 'agents', 'spatcorr', 'options'
    ]
    pyth_drop_cols = [
        'dir_sw', 'exp_length', 'rec_time', 'n_agents', 'vote_model', 
        'min_qrm_buf', 'msg_time_exp', 'epsilon', 'r_cmpt', 'r_step', 
        '_m', 'source_file', 'rType', 'directSwitch', 'steps', 'rt',
        'options', 'n_options'
    ]

    pyth_rename_map = {
        'r_shape': 'function',
        'sigmd_par': 'control_par',
        'msg_per_step': 'vote_msg'
    }

    argos_clean_list = []
    pyth_clean_list = []

    # --- 1. PULIZIA ARGOS ---
    for df, meta in coh_sets:
        if not df.empty:
            df_clean = df.drop(columns=[c for c in coh_drop_cols if c in df.columns])
            if 'option_id' in df_clean.columns:
                df_clean = df_clean[df_clean['option_id'] != -1]
            argos_clean_list.append(df_clean)

    # --- 2. PULIZIA PYTHON ---
    for df, meta in pyth_sets:
        if not df.empty:
            df_clean = df.drop(columns=[c for c in pyth_drop_cols if c in df.columns])
            df_clean = df_clean.rename(columns=pyth_rename_map)
            
            if 'option_id' in df_clean.columns:
                df_clean = df_clean[df_clean['option_id'] != -1]
            
            if 'function' in df_clean.columns:
                df_clean['function'] = df_clean['function'].replace({'poly3': 'polynomial', 'direct': 'linear'})
            if 'r_type' in df_clean.columns:
                df_clean.loc[df_clean['r_type'] == 'static', 'function'] = 'static'
                df_clean = df_clean.drop(columns=['r_type', 'r_value'], errors='ignore')

            if 'static_v' in df_clean.columns:
                static_mask = df_clean['function'] == 'static'
                df_clean.loc[static_mask, 'control_par'] = df_clean.loc[static_mask, 'static_v']
                df_clean = df_clean.drop(columns=['static_v'])
                
            pyth_clean_list.append(df_clean)

    if not argos_clean_list or not pyth_clean_list:
        print("Errore: Impossibile trovare dati validi da confrontare.")
        return

    # --- 3. CREAZIONE MATRICI MASTER ---
    argos_master = pd.concat(argos_clean_list, ignore_index=True)
    pyth_master = pd.concat(pyth_clean_list, ignore_index=True)

    # --- 4. DEFINIZIONE CHIAVI DI OVERLAP DINAMICHE ---
    common_cols = set(argos_master.columns).intersection(set(pyth_master.columns))
    exclude_cols = {'data', 'std', 'run_id'}
    overlap_keys = list(common_cols - exclude_cols)
    overlap_keys.sort() 

    for col in overlap_keys:
        argos_master[col] = pd.to_numeric(argos_master[col], errors='ignore')
        pyth_master[col] = pd.to_numeric(pyth_master[col], errors='ignore')

    argos_configs = argos_master[overlap_keys].drop_duplicates()
    pyth_configs = pyth_master[overlap_keys].drop_duplicates()

    overlap_df = pd.merge(argos_configs, pyth_configs, on=overlap_keys, how='inner')
    sort_cols = [c for c in ['options', 'function', 'eta', 'vote_msg', 'control_par'] if c in overlap_df.columns]
    if sort_cols:
        overlap_df = overlap_df.sort_values(by=sort_cols).reset_index(drop=True)

    print("\n" + "="*90)
    print(f" CHIAVI UTILIZZATE PER IL MATCH: {overlap_keys}")
    print("="*90)
    print(f" -> Configurazioni uniche totali in ARGoS  : {len(argos_configs)}")
    print(f" -> Configurazioni uniche totali in Python : {len(pyth_configs)}")
    print(f" -> MATCH ESATTI TROVATI                   : {len(overlap_df)}")
    print("="*90)
    
    if not overlap_df.empty:
        print("\nElenco delle configurazioni sovrapposte:")
        print(overlap_df)
    print("="*90 + "\n")

def main():
    total_imgs = 0
    
    file_meta_keys = {"eta", "options", "communication", "function"}
    
    coh_sets = load_pickles_with_file_meta("./proc_data/cohesion", file_meta_keys)
    pyth_sets = load_pickles_with_file_meta("../quorum_sensing_Best_of_N/compressed_data_argos_comp", file_meta_keys)
    
    if not coh_sets or not pyth_sets:
        print("Error: One or both directories failed to load files. Check your paths!")
        return

    coh_drop_cols = [
        'adaptive_com', 'comm_type', 'id_aware', 'priority_k', 
        'msg_exp_time', 'msg_hops', 'variation_time', 'eta_stop',
        'time',  'runs', 'arena', 'agents', 'spatcorr', 'options'
    ]
    pyth_drop_cols = [
        'dir_sw', 'exp_length', 'rec_time', 'n_agents', 'vote_model', 
        'min_qrm_buf', 'msg_time_exp', 'epsilon', 'r_cmpt', 'r_step', 
        '_m', 'source_file', 'rType', 'directSwitch', 'steps', 'rt',
        'options', 'n_options'
    ]

    pyth_rename_map = {
        'r_shape': 'function',
        'sigmd_par': 'control_par',
        'msg_per_step': 'vote_msg'
    }

    argos_list = []
    for df, meta in coh_sets:
        if not df.empty:
            df = df.drop(columns=[c for c in coh_drop_cols if c in df.columns])
            if 'option_id' in df.columns:
                df = df[df['option_id'] != -1]
            argos_list.append(df)
            
    argos_df = pd.concat(argos_list, ignore_index=True) if argos_list else pd.DataFrame()

    pyth_list = []
    for df, meta in pyth_sets:
        if not df.empty:
            df = df.drop(columns=[c for c in pyth_drop_cols if c in df.columns])
            df = df.rename(columns=pyth_rename_map)
            
            if 'option_id' in df.columns:
                df = df[df['option_id'] != -1]
            
            if 'function' in df.columns:
                df['function'] = df['function'].replace({'poly3': 'polynomial', 'direct': 'linear'})
            if 'r_type' in df.columns:
                df.loc[df['r_type'] == 'static', 'function'] = 'static'
                df = df.drop(columns=['r_type', 'r_value'], errors='ignore')

            if 'static_v' in df.columns:
                static_mask = df['function'] == 'static'
                df.loc[static_mask, 'control_par'] = df.loc[static_mask, 'static_v']
                df = df.drop(columns=['static_v'])
                
            df['communication'] = 0
            pyth_list.append(df)
            
    pyth_df = pd.concat(pyth_list, ignore_index=True) if pyth_list else pd.DataFrame()

    if not argos_df.empty:
        # total_imgs += plot_hybrid_cohesion(argos_df, pyth_df)
        total_imgs += plot_condensed_hybrid_cohesion(argos_df, pyth_df)
        
    print(f"\nHybrid plot finished with {total_imgs} images")

    # total_imgs = 0
    # file_meta_keys = {"spatcorr"}
    # coh_sets = load_pickles_with_file_meta("proc_data/cohesion", file_meta_keys)
    # acc_sets = load_pickles_with_file_meta("proc_data/accuracy", file_meta_keys)
    # time_sets = load_pickles_with_file_meta("proc_data/time", file_meta_keys)
    # for df_coh, meta in coh_sets:
    #     if not df_coh.empty:
    #         total_imgs += plot_cohesion_df(df_coh, file_meta=meta)
    # for df_acc, meta in acc_sets:
    #     if not df_acc.empty:
    #         total_imgs += plot_accuracy_df(df_acc, file_meta=meta)
    # for df_time, meta in time_sets:
    #     if not df_time.empty:
    #         total_imgs += plot_time_df(df_time, file_meta=meta)

    # if not df_coh.empty and not df_acc.empty:
    #     print("Generating Pareto: Cohesion vs Accuracy...")
    #     total_imgs += plot_cohesion_accuracy_pareto(df_coh, df_acc)
        
    # if not df_coh.empty and not df_time.empty:
    #     print("Generating Pareto: Cohesion vs Time...")
    #     total_imgs += plot_cohesion_time_pareto(df_coh, df_time)

    print(f"\nExecution finished. Total images saved: {total_imgs}")

if __name__ == "__main__":
    main()
