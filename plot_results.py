import os
import ast
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


##################################################################################
def _cast_metadata_value(raw_value: str):
    if raw_value == "":
        return raw_value
    try:
        return int(raw_value)
    except ValueError:
        try:
            return float(raw_value)
        except ValueError:
            return raw_value


##################################################################################
def metadata_from_filename(file_name: str) -> dict:
    stem = Path(file_name).stem
    if "resume_" not in stem:
        return {}

    metadata = {}
    metadata_section = stem.split("resume_", 1)[1]
    parts = metadata_section.split("_")
    for part in parts:
        if "#" not in part:
            continue
        col_name, col_value = part.split("#", 1)
        metadata[col_name] = _cast_metadata_value(col_value)
    return metadata


##################################################################################
def load_pickles_to_single_df(proc_dir: str = "proc_data") -> pd.DataFrame:
    base_path = Path(os.path.abspath("")) / proc_dir
    if not base_path.exists():
        raise FileNotFoundError(f"Directory not found: {base_path}")

    all_files = sorted(base_path.glob("*resume_*.pkl"))
    dataframes = []
    for file_path in all_files:
        file_df = pd.read_pickle(file_path)
        if not isinstance(file_df, pd.DataFrame):
            file_df = pd.DataFrame(file_df)

        metadata = metadata_from_filename(file_path.name)
        for col_name, col_value in metadata.items():
            file_df[col_name] = col_value

        dataframes.append(file_df)

    if not dataframes:
        return pd.DataFrame()
    return pd.concat(dataframes, ignore_index=True)


##################################################################################
def _array_from_cell(cell_value) -> np.ndarray:
    if isinstance(cell_value, np.ndarray):
        return cell_value.astype(float, copy=False)
    if isinstance(cell_value, (list, tuple)):
        return np.asarray(cell_value, dtype=float)
    if isinstance(cell_value, str):
        parsed = ast.literal_eval(cell_value)
        if isinstance(parsed, (list, tuple, np.ndarray)):
            return np.asarray(parsed, dtype=float)
    raise ValueError(f"Unsupported array cell type: {type(cell_value).__name__}")


##################################################################################
def _safe_filename_from_values(values: dict) -> str:
    safe_parts = []
    for key, value in values.items():
        clean = f"{key}#{value}"
        clean = clean.replace("/", "-").replace(" ", "").replace(":", "-")
        safe_parts.append(clean)
    return "_".join(safe_parts)


##################################################################################
def _function_colormap(function_names):
    cmap_cycle = [
        "Blues",
        "Oranges",
        "Greens",
        "Purples",
        "Reds",
        "Greys",
        "YlGnBu",
        "YlOrBr",
    ]
    mapping = {}
    for idx, fn in enumerate(sorted(function_names)):
        mapping[fn] = plt.get_cmap(cmap_cycle[idx % len(cmap_cycle)])
    return mapping


##################################################################################
def plot_result_df(result_df: pd.DataFrame, output_dir: str = "proc_data/images") -> int:
    required_cols = {"option_id", "function", "data", "std"}
    missing_cols = required_cols.difference(result_df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    static_control_par = 0.8
    grouping_cols = [
        c
        for c in result_df.columns
        if c not in required_cols and c not in {"vote_msg", "control_par"}
    ]
    output_path = Path(os.path.abspath("")) / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    image_count = 0
    grouped = result_df.groupby(grouping_cols, dropna=False)

    for group_key, base_group_df in grouped:
        if isinstance(group_key, tuple):
            base_group_values = dict(zip(grouping_cols, group_key))
        else:
            base_group_values = {grouping_cols[0]: group_key}

        static_rows = base_group_df[base_group_df["function"].astype(str) == "static"].copy()
        static_rows = static_rows[
            np.isclose(pd.to_numeric(static_rows["control_par"], errors="coerce"), static_control_par)
        ]

        non_static_rows = base_group_df[base_group_df["function"].astype(str) != "static"].copy()
        non_static_control_values = sorted(
            pd.to_numeric(non_static_rows["control_par"], errors="coerce")
            .dropna()
            .unique()
            .tolist()
        )

        if non_static_control_values:
            target_control_values = non_static_control_values
        elif not static_rows.empty:
            target_control_values = [static_control_par]
        else:
            continue

        for target_control in target_control_values:
            if non_static_rows.empty:
                group_df = static_rows.copy()
            else:
                dynamic_rows = non_static_rows[
                    np.isclose(pd.to_numeric(non_static_rows["control_par"], errors="coerce"), target_control)
                ]
                group_df = pd.concat([static_rows, dynamic_rows], ignore_index=True)

            if group_df.empty:
                continue

            group_values = dict(base_group_values)
            group_values["control_par"] = target_control

            option_values = sorted(group_df["option_id"].dropna().unique().tolist())
            if not option_values:
                continue
            if "options" in group_values:
                n_panels = int(group_values["options"]) + 1
            else:
                n_panels = int(max(option_values)) + 1

            if len(option_values) > n_panels:
                logging.warning(
                    "Found %s option_id values (%s) but panels=%s. Extra options will be ignored.",
                    len(option_values),
                    option_values,
                    n_panels,
                )
            ncols = min(3, n_panels)
            nrows = int(np.ceil(n_panels / ncols))
            fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 5 * nrows), sharey=True)
            axes = np.atleast_1d(axes).ravel()

            option_set = set(option_values)
            for panel_idx in range(n_panels):
                ax = axes[panel_idx]
                option_id = panel_idx
                if option_id not in option_set:
                    ax.set_title(f"option_id={option_id} (missing)")
                    ax.axis("off")
                    continue

                option_df = group_df[group_df["option_id"] == option_id]
                function_values = sorted(option_df["function"].astype(str).unique().tolist())
                function_cmaps = _function_colormap(function_values)

                for function_name in function_values:
                    f_df = option_df[option_df["function"].astype(str) == function_name]
                    vote_values = sorted(f_df["vote_msg"].dropna().unique().tolist())
                    if not vote_values:
                        continue
                    cmap = function_cmaps[function_name]
                    color_positions = np.linspace(0.45, 0.9, len(vote_values))

                    for color_idx, vote_val in enumerate(vote_values):
                        row = f_df[f_df["vote_msg"] == vote_val].iloc[0]
                        data_arr = _array_from_cell(row["data"])
                        std_arr = _array_from_cell(row["std"])
                        n_steps = min(len(data_arr), len(std_arr))
                        x = np.arange(n_steps)
                        y = data_arr[:n_steps]
                        s = std_arr[:n_steps]

                        color = cmap(color_positions[color_idx])
                        ax.plot(
                            x,
                            y,
                            linewidth=2.0,
                            color=color,
                            label=f"{function_name} | vote_msg={vote_val}",
                        )
                        ax.fill_between(x, y - s, y + s, color=color, alpha=0.15)

                ax.set_title(f"option_id={option_id}")
                ax.set_xlabel("step")
                if panel_idx == 0:
                    ax.set_ylabel("value")
                ax.grid(alpha=0.2)

            for panel_idx in range(n_panels, len(axes)):
                axes[panel_idx].axis("off")

            title_parts = [f"{k}={v}" for k, v in group_values.items()]
            fig.suptitle(" | ".join(title_parts), fontsize=10, y=1.02)
            handles, labels = [], []
            for ax in axes:
                h, l = ax.get_legend_handles_labels()
                if h:
                    handles, labels = h, l
                    break
            if handles:
                fig.legend(handles, labels, loc="upper center", ncols=max(1, len(labels)))

            fig.tight_layout()

            image_name = _safe_filename_from_values(group_values) + ".png"
            fig.savefig(output_path / image_name, dpi=150, bbox_inches="tight")
            plt.close(fig)
            image_count += 1

    return image_count


##################################################################################
def main():
    result_df = load_pickles_to_single_df("proc_data")
    if result_df.empty:
        print("No data found to plot.")
        return

    output_file = Path(os.path.abspath("")) / "proc_data" / "all_results.pkl"
    result_df.to_pickle(output_file)

    images = plot_result_df(result_df, "proc_data/images")
    print(
        f"Rows: {len(result_df)}, Cols: {len(result_df.columns)}, "
        f"Saved DF: {output_file}, Images: {images}"
    )


##################################################################################
if __name__ == "__main__":
    main()
