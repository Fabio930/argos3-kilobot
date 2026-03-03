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


def _safe_filename_from_metadata(values: dict) -> str:
    """Generates a safe filename using all scalar metadata key/value pairs."""
    safe_parts = []
    for key in sorted(values.keys()):
        val = values[key]
        if isinstance(val, (list, tuple, np.ndarray, pd.Series, dict, set)):
            continue
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


def plot_cohesion_df(result_df: pd.DataFrame) -> int:
    """
    Cohesion line plots with std shadow.
    Produces one image per metadata group with two panels: option_id 0 and 1.
    """
    required_cols = {"option_id", "vote_msg", "data", "std"}
    missing = required_cols.difference(result_df.columns)
    if missing:
        raise ValueError(f"plot_cohesion_df missing required columns: {sorted(missing)}")

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "cohesion"
    output_path.mkdir(parents=True, exist_ok=True)

    exclude_cols = {"option_id", "vote_msg", "function", "data", "std"}
    grouping_cols = [c for c in result_df.columns if c not in exclude_cols]
    image_count = 0

    for group_meta, gdf in _iter_groups(result_df, grouping_cols):
        option_1_df = gdf[gdf["option_id"] == 0]
        option_2_df = gdf[gdf["option_id"] == 1]
        if option_1_df.empty and option_2_df.empty:
            continue

        function_values = sorted(gdf["function"].astype(str).unique().tolist()) if "function" in gdf.columns else []
        function_cmaps = _function_colormap(function_values)

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
                    ax.fill_between(x, y - s, y + s, color=color, alpha=0.18)

            ax.set_title(f"Option {option_id}")
            ax.set_xlabel("step")
            ax.grid(alpha=0.25)
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                uniq = dict(zip(labels, handles))
                ax.legend(uniq.values(), uniq.keys(), loc="best", frameon=False, fontsize=8)

        axes[0].set_ylabel("cohesion")
        fig.suptitle("Cohesion")

        file_name = f"cohesion_{_safe_filename_from_metadata(dict(group_meta))}.png"
        fig.tight_layout()
        fig.savefig(output_path / file_name, dpi=150, bbox_inches="tight")
        plt.close(fig)
        image_count += 1

    return image_count


def plot_accuracy_df(result_df: pd.DataFrame) -> int:
    """Accuracy bar plot with eta on x-axis.

    Colors are now chosen exactly the same way as in :func:`plot_cohesion_df`:
    each *function* gets its own base colormap and each distinct ``vote_msg``
    receives a different shade from that colormap.  This keeps the color
    classification consistent across cohesion, accuracy and time figures so
    that different functions can be compared by the number of messages used.
    """
    required_cols = {"eta", "vote_msg", "data"}
    missing = required_cols.difference(result_df.columns)
    if missing:
        raise ValueError(f"plot_accuracy_df missing required columns: {sorted(missing)}")

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "accuracy"
    output_path.mkdir(parents=True, exist_ok=True)

    exclude_cols = {"eta", "vote_msg", "function", "data", "std"}
    grouping_cols = [c for c in result_df.columns if c not in exclude_cols]
    image_count = 0

    for group_meta, gdf in _iter_groups(result_df, grouping_cols):
        work = gdf.copy()
        work["metric"] = work["data"].apply(lambda x: float(np.mean(m_array_from_cell(x))))
        # if there is no function column we still want the code to run, so
        # introduce a dummy placeholder; this keeps the grouping logic
        # uniform with the cohesion plots.
        if "function" not in work.columns:
            work["function"] = ""
        # preserve the function column so we can colour by it
        agg = work.groupby(["eta", "vote_msg", "function"], dropna=False)["metric"].agg(["mean", "std"]).reset_index()
        if agg.empty:
            continue

        eta_values = np.array(sorted(agg["eta"].dropna().unique().tolist()), dtype=float)
        if eta_values.size == 0:
            continue

        # build colour maps per function and list of (function,vote_msg) pairs
        funcs = sorted(agg["function"].dropna().unique().tolist())
        f_cmaps = _function_colormap(funcs)
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
            cmap = f_cmaps[f]
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
        ax.set_title("Accuracy by eta")
        ax.grid(axis="y", alpha=0.25)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            uniq = dict(zip(labels, handles))
            ax.legend(uniq.values(), uniq.keys(), frameon=False, loc="best")

        file_name = f"accuracy_{_safe_filename_from_params(dict(group_meta))}.png"
        fig.tight_layout()
        fig.savefig(output_path / file_name, dpi=150, bbox_inches="tight")
        plt.close(fig)
        image_count += 1

    return image_count


def plot_time_df(result_df: pd.DataFrame) -> int:
    """Time box plot with eta on x-axis.

    Uses the same colour classification as the cohesion plots: each
    ``function`` has its own colormap and each ``vote_msg`` is assigned a
    different shade.  This makes it possible to visually match bars and boxes
    across the various figure types when comparing functions with different
    message counts.
    """
    required_cols = {"eta", "vote_msg", "data"}
    missing = required_cols.difference(result_df.columns)
    if missing:
        raise ValueError(f"plot_time_df missing required columns: {sorted(missing)}")

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "time"
    output_path.mkdir(parents=True, exist_ok=True)

    exclude_cols = {"eta", "vote_msg", "function", "data", "std"}
    grouping_cols = [c for c in result_df.columns if c not in exclude_cols]
    image_count = 0

    for group_meta, gdf in _iter_groups(result_df, grouping_cols):
        eta_values = np.array(sorted(gdf["eta"].dropna().unique().tolist()), dtype=float)
        if eta_values.size == 0:
            continue

        # if function column is missing add empty placeholder so that downstream
        # routines can operate without KeyError
        if "function" not in gdf.columns:
            gdf = gdf.copy()
            gdf["function"] = ""

        # build list of (function,vote) pairs and colour map
        funcs = sorted(gdf["function"].dropna().unique().tolist())
        f_cmaps = _function_colormap(funcs)
        pairs = gdf[["function", "vote_msg"]].drop_duplicates().apply(tuple, axis=1).tolist()
        pairs.sort()
        total_series = len(pairs)

        if eta_values.size > 1:
            min_gap = float(np.min(np.diff(eta_values)))
        else:
            min_gap = 0.1
        cluster_w = min_gap * 0.7
        box_w = cluster_w / max(1, total_series)

        # compute colours for each combination
        pair_colors = {}
        for f in funcs:
            votes_for_f = sorted(gdf[gdf["function"] == f]["vote_msg"].dropna().unique().tolist())
            cmap = f_cmaps[f]
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
        ax.set_title("Exit Time by eta")
        ax.grid(axis="y", alpha=0.25)

        legend_items = [
            Line2D([0], [0], color=pair_colors[p], lw=0, marker='o', markersize=8, label=f"{p[0]} m:{p[1]}")
            for p in pair_colors
        ]
        if legend_items:
            ax.legend(handles=legend_items, frameon=False, loc="best")

        file_name = f"time_{_safe_filename_from_params(dict(group_meta))}.png"
        fig.tight_layout()
        fig.savefig(output_path / file_name, dpi=150, bbox_inches="tight")
        plt.close(fig)
        image_count += 1

    return image_count

##################################################################################
# 5. PARETO PLOTTING ENGINE
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
    c = coh_df[coh_df["option_id"] == 0].copy()
    c[["coh_f", "coh_s"]] = c.apply(lambda r: pd.Series([np.mean(m_array_from_cell(r["data"])[-100:]), np.mean(m_array_from_cell(r["std"])[-100:])]), axis=1)
    
    a = acc_df.copy()
    a["val_f"] = a["data"].apply(lambda x: np.mean(m_array_from_cell(x)))
    
    ignore_cols = {"data", "std", "coh_f", "coh_s", "val_f", "val_s", "option_id"}
    merge_cols = [col for col in (set(c.columns) & set(a.columns)) if col not in ignore_cols]
    
    merged = pd.merge(c, a, on=merge_cols)
    return plot_pareto_base(merged, "val_f", None, "coh_f", "coh_s", "Accuracy (%)", "Final Cohesion (Avg last 100)", "cohesion_accuracy")

def plot_cohesion_time_pareto(coh_df, time_df):
    """Prepares Cohesion vs Time data."""
    c = coh_df[coh_df["option_id"] == 0].copy()
    c[["coh_f", "coh_s"]] = c.apply(lambda r: pd.Series([np.mean(m_array_from_cell(r["data"])[-100:]), np.mean(m_array_from_cell(r["std"])[-100:])]), axis=1)
    
    t = time_df.copy()
    t[["val_f", "val_s"]] = t["data"].apply(lambda x: pd.Series([np.median(m_array_from_cell(x)), np.std(m_array_from_cell(x))]))
    
    ignore_cols = {"data", "std", "coh_f", "coh_s", "val_f", "val_s", "option_id"}
    merge_cols = [col for col in (set(c.columns) & set(t.columns)) if col not in ignore_cols]
    
    merged = pd.merge(c, t, on=merge_cols)
    return plot_pareto_base(merged, "val_f", "val_s", "coh_f", "coh_s", "Median Exit Time (Ticks)", "Final Cohesion (Avg last 100)", "cohesion_time")

##################################################################################
# 6. MAIN EXECUTION
##################################################################################

def main():
    total_imgs = 0
    df_coh = load_pickles_to_single_df("proc_data/cohesion")
    df_acc = load_pickles_to_single_df("proc_data/accuracy")
    df_time = load_pickles_to_single_df("proc_data/time")
    if not df_coh.empty:
        total_imgs += plot_cohesion_df(df_coh)
    if not df_acc.empty:
        total_imgs += plot_accuracy_df(df_acc)
    if not df_time.empty:
        total_imgs += plot_time_df(df_time)

    # if not df_coh.empty and not df_acc.empty:
    #     print("Generating Pareto: Cohesion vs Accuracy...")
    #     total_imgs += plot_cohesion_accuracy_pareto(df_coh, df_acc)
        
    # if not df_coh.empty and not df_time.empty:
    #     print("Generating Pareto: Cohesion vs Time...")
    #     total_imgs += plot_cohesion_time_pareto(df_coh, df_time)

    print(f"\nExecution finished. Total images saved: {total_imgs}")

if __name__ == "__main__":
    main()
