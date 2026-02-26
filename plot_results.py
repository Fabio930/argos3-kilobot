import os, ast, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.lines import Line2D

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

def _safe_filename_from_params(values: dict) -> str:
    """
    Generates a safe filename using ONLY experimental parameters.
    Prevents 'File name too long' errors by ignoring data columns.
    """
    # Define which keys are actually parameters we want in the filename
    allowed_params = {
        "communication", "adaptive_com", "msg_exp_time", "msg_hops", 
        "eta", "control_par", "agents", "options", "arena", "runs", "time"
    }
    
    safe_parts = []
    # Use priority order for a consistent look
    priority_order = [
        "communication", "adaptive_com", "msg_exp_time", "msg_hops", 
        "eta", "control_par", "agents", "options", "arena", "runs", "time"
    ]
    
    for key in priority_order:
        if key in values and key in allowed_params:
            val = values[key]
            # Avoid placing entire lists/arrays in the filename
            if not isinstance(val, (list, np.ndarray, pd.Series)):
                clean = f"{key}#{val}".replace("/", "-").replace(" ", "").replace(":", "-")
                safe_parts.append(clean)
                
    return "_".join(safe_parts) if safe_parts else "plot"

def metadata_from_filename(file_name: str) -> dict:
    """Extracts metadata dictionary from a pickle filename."""
    stem = Path(file_name).stem
    if "resume_" not in stem: return {}
    metadata = {}
    metadata_section = stem.split("resume_", 1)[1]
    parts = metadata_section.split("_")
    for part in parts:
        if "#" not in part: continue
        col_name, col_value = part.split("#", 1)
        metadata[col_name] = _cast_metadata_value(col_value)
    return metadata

def load_pickles_to_single_df(proc_dir: str) -> pd.DataFrame:
    """Loads all .pkl files into a single DataFrame with integrated metadata."""
    base_path = Path(os.path.abspath("")) / proc_dir
    if not base_path.exists(): return pd.DataFrame()
    all_files = sorted(base_path.glob("*resume_*.pkl"))
    dataframes = []
    for file_path in all_files:
        try:
            file_df = pd.read_pickle(file_path)
            if not isinstance(file_df, pd.DataFrame): file_df = pd.DataFrame(file_df)
            metadata = metadata_from_filename(file_path.name)
            for col_name, col_value in metadata.items():
                file_df[col_name] = col_value
            dataframes.append(file_df)
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
    return pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()

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
# 4. PARETO PLOTTING ENGINE
##################################################################################

def plot_pareto_base(merged_df, x_col, x_err_col, y_col, y_err_col, x_label, y_label, sub_folder):
    """Generic Pareto plotter logic."""
    output_path = Path(os.path.abspath("")) / "proc_data" / "pareto" / sub_folder
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Identify constant metadata columns for grouping
    plot_vars = {"eta", "coh_f", "coh_s", "val_f", "val_s", "vote_msg", "function"}
    # Remove any unwanted columns derived from merge (data_x, data_y etc)
    grouping_cols = [c for c in merged_df.columns if c not in plot_vars and "data" not in c and "std" not in c and c != "control_par"]
    
    image_count = 0
    markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'h']
    
    for group_key, base_df in merged_df.groupby(grouping_cols, dropna=False):
        # Create metadata dict for filename
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
            
            # Use the new safe filename function
            curr_meta = {**base_meta, "control_par": ctrl}
            filename = f"pareto_{_safe_filename_from_params(curr_meta)}.png"
            fig.savefig(output_path / filename, dpi=150, bbox_inches="tight")
            plt.close(fig); image_count += 1
            
    return image_count

def plot_cohesion_accuracy_pareto(coh_df, acc_df):
    """Prepares Cohesion vs Accuracy data."""
    c = coh_df[coh_df["option_id"] == 1].copy()
    c[["coh_f", "coh_s"]] = c.apply(lambda r: pd.Series([np.mean(m_array_from_cell(r["data"])[-100:]), np.mean(m_array_from_cell(r["std"])[-100:])]), axis=1)
    
    a = acc_df.copy()
    a["val_f"] = a["data"].apply(lambda x: np.mean(m_array_from_cell(x)))
    
    ignore_cols = {"data", "std", "coh_f", "coh_s", "val_f", "val_s", "option_id"}
    merge_cols = [col for col in (set(c.columns) & set(a.columns)) if col not in ignore_cols]
    
    merged = pd.merge(c, a, on=merge_cols)
    return plot_pareto_base(merged, "val_f", None, "coh_f", "coh_s", "Accuracy (%)", "Final Cohesion (Avg last 100)", "cohesion_accuracy")

def plot_cohesion_time_pareto(coh_df, time_df):
    """Prepares Cohesion vs Time data."""
    c = coh_df[coh_df["option_id"] == 1].copy()
    c[["coh_f", "coh_s"]] = c.apply(lambda r: pd.Series([np.mean(m_array_from_cell(r["data"])[-100:]), np.mean(m_array_from_cell(r["std"])[-100:])]), axis=1)
    
    t = time_df.copy()
    t[["val_f", "val_s"]] = t["data"].apply(lambda x: pd.Series([np.median(m_array_from_cell(x)), np.std(m_array_from_cell(x))]))
    
    ignore_cols = {"data", "std", "coh_f", "coh_s", "val_f", "val_s", "option_id"}
    merge_cols = [col for col in (set(c.columns) & set(t.columns)) if col not in ignore_cols]
    
    merged = pd.merge(c, t, on=merge_cols)
    return plot_pareto_base(merged, "val_f", "val_s", "coh_f", "coh_s", "Median Exit Time (Ticks)", "Final Cohesion (Avg last 100)", "cohesion_time")

##################################################################################
# 5. MAIN EXECUTION
##################################################################################

def main():
    total_imgs = 0
    df_coh = load_pickles_to_single_df("proc_data/cohesion")
    df_acc = load_pickles_to_single_df("proc_data/accuracy")
    df_time = load_pickles_to_single_df("proc_data/time")
    # if not df_coh.empty:
    #     total_imgs += plot_cohesion_df(df_coh)
    # if not df_acc.empty:
    #     total_imgs += plot_accuracy_df(df_acc)
    # if not df_time.empty:
    #     imagtotal_imgses += plot_time_df(df_time)

    if not df_coh.empty and not df_acc.empty:
        print("Generating Pareto: Cohesion vs Accuracy...")
        total_imgs += plot_cohesion_accuracy_pareto(df_coh, df_acc)
        
    if not df_coh.empty and not df_time.empty:
        print("Generating Pareto: Cohesion vs Time...")
        total_imgs += plot_cohesion_time_pareto(df_coh, df_time)

    print(f"\nExecution finished. Total Pareto images saved: {total_imgs}")

if __name__ == "__main__":
    main()