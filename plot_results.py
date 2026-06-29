import os, re, logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from scipy import stats
from pathlib import Path
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 18})

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

EXCLUDED_FILENAME_KEYS = {
    "cohesion_adaptive_com", "adaptive_com", "agents", "arena", "comm_type", 
    "id_aware", "msg_hops", "priority_k", "runs", "spatcorr", "time", "variation_time"
}

def metadata_from_filename(file_name: str) -> dict:
    stem = Path(file_name).stem
    metadata = {}
    if "resume_" in stem:
        metadata_section = stem.split("resume_", 1)[1]
    elif "results_processed_" in stem:
        metadata_section = stem.split("results_processed_", 1)[1]
        metadata_section = metadata_section.split("_residence_data")[0]
    else:
        return {}

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
        mapped_key = key_translation.get(col_name, col_name)
        parsed_value = _cast_metadata_value(col_value)
        metadata[mapped_key] = parsed_value
    return metadata

def load_pickles_with_file_meta(proc_dir: str, file_meta_keys: set) -> list:
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
                
            runs_match = re.search(r'_runs#(\d+)', file_path.name)
            if runs_match:
                file_df['runs'] = int(runs_match.group(1))
                
            arena_match = re.search(r'_arena#([^_\.]+)', file_path.name)
            if arena_match:
                arena_val = arena_match.group(1)
                file_df['arena'] = int(arena_val) if arena_val.isdigit() else arena_val
                
            metadata = metadata_from_filename(file_path.name)
            df_meta = {k: v for k, v in metadata.items() if k not in file_meta_keys}
            file_meta = {k: v for k, v in metadata.items() if k in file_meta_keys}
            for col_name, col_value in df_meta.items():
                if col_name not in ['runs', 'arena'] or col_name not in file_df.columns:
                    file_df[col_name] = col_value
            datasets.append((file_df, file_meta))
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
    return datasets


##################################################################################
# 4. STANDARD PLOTTING
##################################################################################

def plot_condensed_hybrid_cohesion(argos_df: pd.DataFrame, pyth_df: pd.DataFrame, quorum_df: pd.DataFrame = None,ctrl_df: pd.DataFrame = None,msgs_df: pd.DataFrame = None,omit_m: list = [15], omit_labels: list = None,enable_python: bool = True) -> int:
    if omit_m is None: omit_m = []
    if omit_labels is None: omit_labels = []

    if not enable_python:
        pyth_df = pd.DataFrame()

    all_runs = set()
    for df_src in [argos_df, pyth_df, quorum_df, ctrl_df, msgs_df]:
        if df_src is not None and not df_src.empty and 'runs' in df_src.columns:
            all_runs.update(df_src['runs'].dropna().unique())
            
    runs_list = sorted(list(all_runs)) if all_runs else [None]

    output_path = Path(os.path.abspath("")) / "proc_data" / "images" / "cohesion_hybrid_condensed"
    output_path.mkdir(parents=True, exist_ok=True)
    image_count = 0

    for current_run in runs_list:
        
        def filter_by_run(df):
            if df is None or df.empty: return df
            if 'runs' in df.columns and current_run is not None:
                return df[df['runs'] == current_run].copy()
            return df.copy()

        cur_argos = filter_by_run(argos_df)
        cur_pyth = filter_by_run(pyth_df)
        cur_quorum = filter_by_run(quorum_df)
        cur_ctrl = filter_by_run(ctrl_df)
        cur_msgs = filter_by_run(msgs_df)

        dfs_to_clean = [cur_argos, cur_pyth, cur_quorum, cur_ctrl, cur_msgs]
        for df in dfs_to_clean:
            if df is not None and not df.empty and 'init_distr' in df.columns:
                df['init_distr'] = df['init_distr'].apply(
                    lambda x: float(re.sub(r'[a-zA-Z]', '', str(x))) if pd.notnull(x) and str(x).strip() != '' else x
                )

        if not cur_argos.empty and 'option_id' in cur_argos.columns: 
            cur_argos = cur_argos[cur_argos['option_id'] == 0]
        if cur_quorum is not None and not cur_quorum.empty and 'option_id' in cur_quorum.columns: 
            cur_quorum = cur_quorum[cur_quorum['option_id'] == 0]
        if cur_ctrl is not None and not cur_ctrl.empty and 'option_id' in cur_ctrl.columns: 
            cur_ctrl = cur_ctrl[cur_ctrl['option_id'] == 0]
        if cur_msgs is not None and not cur_msgs.empty and 'option_id' in cur_msgs.columns: 
            cur_msgs = cur_msgs[cur_msgs['option_id'] == 0]

        py_group_cols = ['function', 'control_par', 'vote_msg', 'eta', 'init_distr', 'communication', 'options', 'n_options', 'n_opts', 'N']
        if not cur_pyth.empty:
            cur_pyth['data_arr'] = cur_pyth['data'].apply(m_array_from_cell) 
            py_group_cols_exist = [c for c in py_group_cols if c in cur_pyth.columns]
            
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
            
            pyth_agg = cur_pyth.groupby(py_group_cols_exist, dropna=False).apply(process_python_config, include_groups=False).reset_index()
        else:
            pyth_agg = pd.DataFrame()

        def get_mask(df, target_eta, target_func, target_ctrl, target_vote):
            if df is None or df.empty:
                return pd.Series(False, index=[] if df is None else df.index)
            mask = pd.Series(True, index=df.index)
            
            if 'eta' in df.columns: mask &= np.isclose(pd.to_numeric(df['eta'], errors='coerce'), target_eta, atol=1e-2)
            else: return pd.Series(False, index=df.index)
                
            if 'function' in df.columns: mask &= df['function'].astype(str).str.strip().str.lower() == target_func.lower()
            if 'control_par' in df.columns: mask &= np.isclose(pd.to_numeric(df['control_par'], errors='coerce'), target_ctrl, atol=1e-3)
            if 'vote_msg' in df.columns: mask &= pd.to_numeric(df['vote_msg'], errors='coerce') == target_vote
                
            return mask

        all_configs = [
            {'label': r'$r=0.8$', 'func': 'static', 'ctrl': 0.8},
            {'label': r'r(q)=q', 'func': 'linear', 'ctrl': 0.0},
            {'label': r'$p(q,0.5)$', 'func': 'polynomial', 'ctrl': 0.5},
            {'label': r'$p(q,0.7)$', 'func': 'polynomial', 'ctrl': 0.7}
        ]
        all_m_values = [3, 5, 9, 15]

        base_configs = [c for c in all_configs if c['label'] not in omit_labels]
        m_values = [m for m in all_m_values if m not in omit_m]

        if not base_configs or not m_values:
            print("Error: Grid is empty due to omitted values.")
            return 0

        if 'communication' in cur_argos.columns:
            unique_comms = sorted(cur_argos['communication'].dropna().astype(int).unique().tolist())
        else:
            unique_comms = [0]
            
        num_comms = len(unique_comms)
        cmap_vir = plt.get_cmap('viridis')
        norm = mcolors.Normalize(vmin=0, vmax=num_comms if num_comms > 0 else 1)
        comm_colors = {val: cmap_vir(norm(i)) for i, val in enumerate(unique_comms)}
        comm_labels = {0: 'IDB', 1: r'$h-IDR_i$', 2: r'$IDR_f$'}
            
        pyth_color = 'tab:gray' 
        for df in [cur_argos, cur_quorum, cur_ctrl, cur_msgs, pyth_agg]:
            if df is not None and not df.empty and 'eta' in df.columns:
                df.loc[:, 'eta'] = pd.to_numeric(df['eta'], errors='coerce').round(3)
                
        for n_opts in [2, 5]:
            eta_main = 0.5 if n_opts == 2 else 0.8
            eta_inset = 0.4 if n_opts == 2 else 0.7
            
            active_configs = [c for c in base_configs]
            valid_panels = []
            
            for c_conf in active_configs:
                for m_val in m_values:
                    a_main = cur_argos[get_mask(cur_argos, eta_main, c_conf['func'], c_conf['ctrl'], m_val)]
                    q_main = cur_quorum[get_mask(cur_quorum, eta_main, c_conf['func'], c_conf['ctrl'], m_val)] if cur_quorum is not None else None
                    c_main = cur_ctrl[get_mask(cur_ctrl, eta_main, c_conf['func'], c_conf['ctrl'], m_val)] if cur_ctrl is not None else None
                    m_main = cur_msgs[get_mask(cur_msgs, eta_main, c_conf['func'], c_conf['ctrl'], m_val)] if cur_msgs is not None else None
                    p_main = pyth_agg[get_mask(pyth_agg, eta_main, c_conf['func'], c_conf['ctrl'], m_val)] if not pyth_agg.empty else pd.DataFrame()

                    a_inset = cur_argos[get_mask(cur_argos, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)]
                    q_inset = cur_quorum[get_mask(cur_quorum, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)] if cur_quorum is not None else None
                    c_inset = cur_ctrl[get_mask(cur_ctrl, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)] if cur_ctrl is not None else None
                    m_inset = cur_msgs[get_mask(cur_msgs, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)] if cur_msgs is not None else None
                    p_inset = pyth_agg[get_mask(pyth_agg, eta_inset, c_conf['func'], c_conf['ctrl'], m_val)] if not pyth_agg.empty else pd.DataFrame()

                    if not (a_main.empty and p_main.empty and a_inset.empty and p_inset.empty):
                        valid_panels.append({
                            'c_conf': c_conf, 'm_val': m_val,
                            'a_main': a_main, 'q_main': q_main, 'c_main': c_main, 'm_main': m_main, 'p_main': p_main,
                            'a_inset': a_inset, 'q_inset': q_inset, 'c_inset': c_inset, 'm_inset': m_inset, 'p_inset': p_inset
                        })
                        
            n_panels = len(valid_panels)
            if n_panels == 0:
                continue
                
            n_cols = min(n_panels, len(m_values))
            n_rows = int(np.ceil(n_panels / n_cols))
            sem_0x = True if (n_rows > 1) else False
            sem_0y = True if (n_cols > 1) else False
            sem_0 = True if sem_0x or sem_0y else False
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows), squeeze=sem_0, sharex=sem_0x, sharey=sem_0y)
            axes_flat = axes.flatten()
            
            has_data = True
            
            for i, panel in enumerate(valid_panels):
                ax = axes_flat[i]
                c_conf = panel['c_conf']
                m_val = panel['m_val']
                
                a_main = panel['a_main']
                q_main = panel['q_main']
                c_main = panel['c_main']
                m_main = panel['m_main']
                p_main = panel['p_main']
                
                a_inset = panel['a_inset']
                q_inset = panel['q_inset']
                c_inset = panel['c_inset']
                m_inset = panel['m_inset']
                p_inset = panel['p_inset']
                    
                max_x = 0
                final_opt0_val = 0.5 
                
                if not a_main.empty:
                    end_vals = []
                    for _, row in a_main.iterrows():
                        arr = m_array_from_cell(row['data'])
                        if len(arr) > 0: end_vals.append(arr[-1])
                    if end_vals: final_opt0_val = np.mean(end_vals)
                
                # Check if there is any data to plot in the inset
                has_inset_data = any(
                    df is not None and not df.empty 
                    for df in [a_inset, q_inset, c_inset, m_inset, p_inset]
                )
                
                if has_inset_data:
                    inset_loc = [0.275, 0.05, 0.45, 0.5] if final_opt0_val > 0.5 else [0.275, 0.45, 0.45, 0.5]
                    ax_in = ax.inset_axes(inset_loc)
                    ax_in.grid(alpha=0.2)
                else:
                    ax_in = None
                
                def plot_target(a_df, q_df, c_df, msg_df, p_df, target_ax):
                    nonlocal max_x
                    datasets = [
                        ('cohesion', a_df, '-'), 
                        ('quorum', q_df, ':'), 
                        ('ctrl', c_df, '-.'),
                        ('msgs', msg_df, '--')
                    ]
                    
                    for d_name, d_df, d_style in datasets:
                        if d_df is None or d_df.empty: continue
                        for _, row in d_df.iterrows():
                            try:
                                y = m_array_from_cell(row['data'])
                                s = m_array_from_cell(row['std'])
                                n_runs = int(row.get('runs', 1))
                            except Exception: continue
                            
                            n_steps = min(len(y), len(s))
                            if n_steps == 0 or n_runs < 2: continue 
                            max_x = max(max_x, n_steps)
                            c_color = 'black'
                            x_arr = np.arange(n_steps)
                            if d_name == 'cohesion':
                                target_ax.plot(x_arr, y[:n_steps], color=c_color, linestyle=d_style, linewidth=2)
                                t_crit = stats.t.ppf(0.975, df=n_runs - 1)
                                ci_margin = t_crit * (s[:n_steps] / np.sqrt(n_runs))
                                target_ax.fill_between(
                                    x_arr, 
                                    y[:n_steps] - ci_margin, 
                                    y[:n_steps] + ci_margin, 
                                    facecolor=c_color, 
                                    alpha=0.25
                                )
                            elif d_name == 'msgs':
                                target_ax.plot(x_arr, y[:n_steps], color=c_color, linestyle=d_style, linewidth=2)
                    merged_box = []
                    if p_df is not None and not p_df.empty:
                        for _, row in p_df.iterrows():
                            if 'box_data' in row and len(row['box_data']) > 0:
                                merged_box.extend(row['box_data'])
                    return merged_box

                box_main = plot_target(a_main, q_main, c_main, m_main, p_main, ax)
                
                if has_inset_data:
                    box_inset = plot_target(a_inset, q_inset, c_inset, m_inset, p_inset, ax_in)
                else:
                    box_inset = []

                box_width = max(1, max_x * 0.05)
                box_pos = max_x + box_width * 1.5
                
                plot_targets_list = [(box_main, ax)]
                if has_inset_data:
                    plot_targets_list.append((box_inset, ax_in))
                
                for merged_box, target_ax in plot_targets_list:
                    if merged_box and enable_python:
                        bp = target_ax.boxplot(merged_box, positions=[box_pos], widths=box_width, patch_artist=True, showfliers=False)
                        for patch in bp['boxes']:
                            patch.set_facecolor(pyth_color)
                            patch.set_alpha(0.7)
                        for median in bp['medians']:
                            median.set_color('black')
                            
                y_ticks = np.linspace(0, 1.0, 5)     
                ax.set_xlim(left=0, right=box_pos + box_width * 2)
                ax.set_ylim(-0.03, 1.03)
                ax.set_yticks(y_ticks)
                
                # 1. Define steps in data-space (accounting for the *0.1 label factor)
                major_step = 9000  # Labelled as multiples of 900
                minor_step = 3000  # Spaced as multiples of 300
                
                major_line_ticks = np.arange(0, max_x + 1, major_step)
                all_major_ticks = list(major_line_ticks) + [box_pos]
                all_major_labels = [str(int(t * 0.1)) for t in major_line_ticks] + [""]
                
                minor_ticks = np.arange(0, max_x + 1, minor_step)
                
                # 2. Apply to main axis
                ax.set_xticks(all_major_ticks)
                ax.set_xticklabels(all_major_labels)
                ax.set_xticks(minor_ticks, minor=True)
                ax.grid(which='major', ls="--", alpha=0.4)
                ax.grid(which='minor', ls="--", alpha=0.4)
                
                # 3. Apply to inset axis
                if has_inset_data:
                    ax_in.set_xlim(ax.get_xlim())
                    ax_in.set_xticks(all_major_ticks)
                    ax_in.set_xticks(minor_ticks, minor=True)
                    ax_in.set_ylim(-0.03, 1.03)
                    ax_in.set_yticks(y_ticks)
                    ax_in.tick_params(axis='both', which='both', labelbottom=False, labelleft=False, bottom=True, left=True, length=2)
                
                # Apply title and axes on borders only
                row_idx = i // n_cols
                col_idx = i % n_cols
                
                # if col_idx == 0: 
                #     ax.set_ylabel(r"$\rho^*$")
                
                if row_idx == 0: 
                    ax.set_title(rf"$m={m_val}$")
                    
                if col_idx == n_cols - 1 or i == n_panels - 1: 
                    ax.text(1.05, 0.5, c_conf['label'], transform=ax.transAxes, ha='left', va='center', rotation=270)
                    
                if row_idx == n_rows - 1 or (i + n_cols >= n_panels): 
                    ax.set_xlabel("T")
                
            # Suppress missing subpanels from layout division
            for j in range(n_panels, len(axes_flat)):
                axes_flat[j].set_visible(False)

            if not has_data:
                plt.close(fig)
                continue
                
            # legend_elements = [
            #     Line2D([0], [0], color=comm_colors[k], ls='none', marker='s', markersize=6, label=f"{comm_labels.get(k, 'Unknown')}") 
            #     for k in unique_comms
            # ]
            legend_elements = [Line2D([0], [0], color='black', ls='-', lw=4, label=r'$\rho^*$')]
            
            if cur_msgs is not None and not cur_msgs.empty:
                legend_elements.append(Line2D([0], [0], color='black', ls='--', lw=4, label=r'$\|\mathcal{B}\|$'))
            if enable_python:
                legend_elements.append(Patch(facecolor=pyth_color, edgecolor='black', alpha=0.7, label='agent-based'))
            
            fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.96, .015), ncol=len(legend_elements))
                
            fig.tight_layout()
            
            runs_suffix = f"_runs{int(current_run)}" if current_run is not None else ""
            fig.savefig(output_path / f"condensed_hybrid_opts{n_opts}{runs_suffix}.pdf", dpi=150, bbox_inches="tight")
            plt.close(fig)
            image_count += 1
            
    return image_count


##################################################################################
# 6. MAIN EXECUTION
##################################################################################

def count_configuration_overlaps():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    file_meta_keys = {'options'}
    
    coh_sets = load_pickles_with_file_meta("./proc_data/cohesion", file_meta_keys)
    pyth_sets = load_pickles_with_file_meta("../quorum_sensing_Best_of_N/compressed_data_argos_comp", file_meta_keys)
    
    coh_drop_cols = [
        'adaptive_com', 'comm_type', 'id_aware', 'priority_k', 
        'msg_exp_time', 'msg_hops', 'variation_time', 'eta_stop',
        'time', 'arena', 'agents', 'spatcorr', 'options'
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

    for df, meta in coh_sets:
        if not df.empty:
            df_clean = df.drop(columns=[c for c in coh_drop_cols if c in df.columns])
            if 'option_id' in df_clean.columns:
                df_clean = df_clean[df_clean['option_id'] != -1]
            argos_clean_list.append(df_clean)

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

    argos_master = pd.concat(argos_clean_list, ignore_index=True)
    pyth_master = pd.concat(pyth_clean_list, ignore_index=True)

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
    quorum_sets = load_pickles_with_file_meta("./proc_data/quorum", file_meta_keys)
    ctrl_sets = load_pickles_with_file_meta("./proc_data/ctrl", file_meta_keys)
    msgs_sets = load_pickles_with_file_meta("./proc_data/msgs", file_meta_keys)
    pyth_sets = load_pickles_with_file_meta("../../quorum_sensing_Best_of_N/compressed_data_argos_comp_dec", file_meta_keys) 

    argos_drop_cols = [
        'adaptive_com', 'comm_type', 'id_aware', 'priority_k', 
        'msg_exp_time', 'msg_hops', 'variation_time', 'eta_stop',
        'time', 'arena', 'agents', 'spatcorr', 'options'
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

    def process_argos_sets(datasets):
        clean_list = []
        for df, meta in datasets:
            if not df.empty:
                df = df.drop(columns=[c for c in argos_drop_cols if c in df.columns])
                if 'option_id' in df.columns:
                    df = df[df['option_id'] != -1]
                clean_list.append(df)
        return pd.concat(clean_list, ignore_index=True) if clean_list else pd.DataFrame()

    argos_df = process_argos_sets(coh_sets)
    quorum_df = process_argos_sets(quorum_sets)
    ctrl_df = process_argos_sets(ctrl_sets)
    msgs_df = process_argos_sets(msgs_sets)

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

    enable_python_flag = not pyth_df.empty

    if not argos_df.empty:
        total_imgs += plot_condensed_hybrid_cohesion(
            argos_df=argos_df, 
            pyth_df=pyth_df, 
            quorum_df=quorum_df, 
            ctrl_df=ctrl_df, 
            msgs_df=msgs_df,
            enable_python=enable_python_flag
        )

    print(f"\nExecution finished. Total images saved: {total_imgs}")

if __name__ == "__main__":
    main()
