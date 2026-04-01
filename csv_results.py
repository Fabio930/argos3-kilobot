import numpy as np
import os, csv, logging, json, re, colorsys
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib.ticker import MultipleLocator
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})
class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.bases_diff = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "proc_data" or elem == "msgs_data":
                self.bases.append(os.path.join(self.base, elem))
        self._load_diff_bases()
        self.plot_config = self._load_plot_config()
        self.protocols = self.plot_config.get("protocols", [])
        self.protocols_by_key = {p.get("key"): p for p in self.protocols if p.get("key") is not None}

    def _read_json_robust(self, path):
        """Reads JSON safely by stripping illegal trailing commas."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r',\s*([\]}])', r'\1', content)
        return json.loads(content)

    def _load_diff_bases(self):
        self.bases_diff = []
        self.diff_plot_config = {}
        json_path = os.path.join(self.base, "diff_plot_config.json")
        if not os.path.exists(json_path):
            return
        try:
            cfg = self._read_json_robust(json_path)
            self.diff_plot_config = cfg
            for folder in cfg.get("folders", []):
                root = folder.get("root")
                if not root:
                    continue
                root_name = os.path.basename(root.rstrip(os.sep))
                root_path = os.path.abspath(os.path.join(self.base, root)) if not os.path.isabs(root) else root
                self.bases_diff.append({
                    "root_name": root_name,
                    "root": root_path,
                    "proc_data": os.path.join(root_path, "proc_data"),
                    "msgs_data": os.path.join(root_path, "msgs_data"),
                    "exclude_protocols": folder.get("exclude_protocols", []),
                    "plots": folder.get("plots", {}),
                    "label": folder.get("label"),
                    "line_style": folder.get("line_style"),
                })
        except Exception as exc:
            logging.warning("Failed to load diff_plot_config.json (%s). bases_diff will be empty.", exc)

##########################################################################################################
    def _default_plot_config(self):
        return {
            "protocols": [
                {"key": "AN", "id": 0, "label": r"$AN$", "color": "red", "legend": False},
                {"key": "AN_t", "id": 1, "label": r"$AN_{t}$", "color": "viridis:0", "legend": True},
                {"key": "ID+B", "id": 2, "label": r"$ID+B$", "color": "viridis:1", "legend": True},
                {"key": "ID+R_f", "id": 3, "label": r"$ID+R_{f}$", "color": "viridis:2", "legend": True},
                {"key": "ID+R_1", "id": 4, "label": r"$ID+R_{1}$", "color": "viridis:3", "legend": True},
                {"key": "ID+R_inf", "id": 5, "label": r"$ID+R_{\infty}$", "color": "viridis:4", "legend": True},
                {"key": "ID+R_a", "id": 6, "label": r"$ID+R_{a}$", "color": "viridis:5", "legend": True},
            ],
            "plots": { "exclude_protocols": [], "columns": [60, 120, 180, 300, 600] },
        }

##########################################################################################################
    def _merge_plot_config(self, base_cfg, user_cfg):
        cfg = dict(base_cfg)
        cfg["plots"] = dict(base_cfg.get("plots", {}))
        if isinstance(user_cfg, dict):
            if "protocols" in user_cfg:
                cfg["protocols"] = user_cfg.get("protocols") or []
            if "plots" in user_cfg and isinstance(user_cfg.get("plots"), dict):
                cfg["plots"].update(user_cfg["plots"])
        return cfg

##########################################################################################################
    def _load_plot_config(self):
        cfg = self._default_plot_config()
        path = os.path.join(self.base, "plot_config.json")
        if not os.path.exists(path):
            return cfg
        try:
            user_cfg = self._read_json_robust(path)
            return self._merge_plot_config(cfg, user_cfg)
        except Exception as exc:
            logging.warning("Failed to load plot_config.json (%s). Using defaults.", exc)
            return cfg

##########################################################################################################
    def _plot_columns(self, default_cols):
        plot_cfg = self.plot_config.get("plots", {})
        cols = plot_cfg.get("columns")
        if not cols:
            return list(default_cols)
        out = []
        for c in cols:
            if isinstance(c, bool):
                continue
            if isinstance(c, (int, float)):
                if isinstance(c, float) and not c.is_integer():
                    continue
                out.append(int(c))
            elif isinstance(c, str):
                s = c.strip()
                if s.isdigit():
                    out.append(int(s))
        if default_cols:
            filtered = [c for c in out if c in default_cols]
            if filtered:
                return filtered
        return out if out else list(default_cols)

##########################################################################################################
    def _protocol_matches(self, protocol, selector):
        if protocol is None:
            return False
        if isinstance(selector, bool):
            return False
        if isinstance(selector, int):
            return protocol.get("id") == selector
        if isinstance(selector, float) and selector.is_integer():
            return protocol.get("id") == int(selector)
        if isinstance(selector, str):
            s = selector.strip()
            if s.isdigit():
                return protocol.get("id") == int(s)
            return s == protocol.get("key") or s == protocol.get("label")
        return False

##########################################################################################################
    def _protocol_enabled(self, protocol_key):
        protocol = self.protocols_by_key.get(protocol_key)
        plot_cfg = self.plot_config.get("plots", {})
        exclude = plot_cfg.get("exclude_protocols") or []
        if exclude and any(self._protocol_matches(protocol, sel) for sel in exclude):
            return False
        return True

##########################################################################################################
    def _protocol_color(self, protocol, scalarMap):
        if protocol is None:
            return "black"
        color = protocol.get("color")
        if isinstance(color, str) and color.startswith("viridis:"):
            try:
                idx = int(color.split(":", 1)[1])
                return scalarMap.to_rgba(idx)
            except Exception:
                return "black"
        return color if color else "black"

##########################################################################################################
    def _get_diff_folder_cfg(self, dict_key):
        for folder_cfg in self.bases_diff:
            if folder_cfg.get("root_name") == dict_key or folder_cfg.get("label") == dict_key:
                return folder_cfg
        return {}

##########################################################################################################
    def _protocol_enabled_diff(self, protocol_key, root_name, diff_protocols_by_key=None):
        folder_cfg = self._get_diff_folder_cfg(root_name)
        if folder_cfg and "exclude_protocols" in folder_cfg:
            exclude = folder_cfg.get("exclude_protocols", [])
            if diff_protocols_by_key is None:
                diff_protocols_by_key = self.protocols_by_key
            protocol = diff_protocols_by_key.get(protocol_key)
            if any(self._protocol_matches(protocol, sel) for sel in exclude):
                return False
            return True
        return self._protocol_enabled(protocol_key)
    
##########################################################################################################
    def find_emptiest_inset_position(self, ax, width=0.35, height=0.35, margin=0.03):
        candidates = {
            "top_left": [margin, 1.0 - height - margin, width, height],
            "top_right": [1.0 - width - margin, 1.0 - height - margin, width, height],
            "bottom_left": [margin, margin, width, height],
            "bottom_right": [1.0 - width - margin, margin, width, height]
        }
        counts = {key: 0 for key in candidates}
        points_axes = []
        try:
            ax.figure.canvas.draw_idle()
        except Exception:
            pass

        for line in ax.lines:
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            valid = ~(np.isnan(xdata) | np.isnan(ydata))
            if np.any(valid):
                xy = np.column_stack((xdata[valid], ydata[valid]))
                try:
                    disp_xy = line.get_transform().transform(xy)
                    ax_xy = ax.transAxes.inverted().transform(disp_xy)
                    ls = line.get_linestyle()
                    if ls not in ['None', 'none', '', ' ', False, None]:
                        interpolated_points = []
                        for i in range(len(ax_xy) - 1):
                            p1, p2 = ax_xy[i], ax_xy[i+1]
                            num_pts = max(2, int(np.linalg.norm(p2 - p1) * 30))
                            x_interp = np.linspace(p1[0], p2[0], num_pts)
                            y_interp = np.linspace(p1[1], p2[1], num_pts)
                            interpolated_points.append(np.column_stack((x_interp, y_interp)))
                        if interpolated_points:
                            points_axes.append(np.vstack(interpolated_points))
                        else:
                            points_axes.append(ax_xy)
                    else:
                        points_axes.append(ax_xy)
                except Exception:
                    pass

        for patch in ax.patches:
            try:
                verts = patch.get_path().vertices
                disp_verts = patch.get_transform().transform(verts)
                ax_verts = ax.transAxes.inverted().transform(disp_verts)
                xmin, ymin = np.min(ax_verts, axis=0)
                xmax, ymax = np.max(ax_verts, axis=0)
                xx, yy = np.meshgrid(np.linspace(xmin, xmax, 10), np.linspace(ymin, ymax, 10))
                grid_points = np.column_stack((xx.ravel(), yy.ravel()))
                points_axes.append(grid_points)
            except Exception:
                pass

        for collection in ax.collections:
            try:
                offsets = collection.get_offsets()
                if len(offsets) > 0:
                    disp_offsets = collection.get_transform().transform(offsets)
                    ax_offsets = ax.transAxes.inverted().transform(disp_offsets)
                    points_axes.append(ax_offsets)
            except Exception:
                pass

        if not points_axes:
            return candidates["top_left"]
            
        all_points_axes = np.vstack(points_axes)
        x_ax, y_ax = all_points_axes[:, 0], all_points_axes[:, 1]
        
        for key, box in candidates.items():
            x0, y0, w, h = box
            in_box = (x_ax >= x0) & (x_ax <= x0 + w) & (y_ax >= y0) & (y_ax <= y0 + h)
            counts[key] += np.sum(in_box)
            
        best_position_key = min(counts, key=counts.get)
        return candidates[best_position_key]

##########################################################################################################
    def _extract_short_data(self, tot_st, tot_msgs):
        msgs_dict = {}
        st_dict = {}
        
        for k, res in tot_msgs.items():
            if k[3] == "0.68;0.92":
                p_key = self._identify_protocol_key_msgs(k)
                if p_key:
                    arena = k[0]
                    agents = k[6]
                    tm = k[7]
                    msgs_dict[(p_key, arena, str(agents), str(tm))] = res
                    
        for states in tot_st:
            for k, res in states.items():
                p_key = self._identify_protocol_key(k)
                if p_key:
                    arena = k[1]
                    thr = k[4]
                    gt = k[5]
                    agents = k[7]
                    tm = k[9]
                    s_key = (p_key, arena, str(agents), str(tm), gt, thr)
                    if s_key not in st_dict:
                        st_dict[s_key] = []
                    st_dict[s_key].append(res[0])
                    
        for s_key, lst in st_dict.items():
            min_len = min(len(x) for x in lst)
            arr = np.array([x[:min_len] for x in lst])
            st_dict[s_key] = np.mean(arr, axis=0).tolist()
            
        return msgs_dict, st_dict

##########################################################################################################
    def plot_short(self, tot_st, tot_msgs):
        if not os.path.exists(self.base + "/compressed_data/images/"):
            os.makedirs(self.base + "/compressed_data/images/", exist_ok=True)
        path = self.base + "/compressed_data/images/"
        
        msgs_dict, st_dict = self._extract_short_data(tot_st, tot_msgs)
        
        plot_cfg = self.plot_config.get("plots", {})
        raw_columns = plot_cfg.get("columns", [60, 120, 180, 300, 600])
        main_tm_list = self._plot_columns(raw_columns)
        
        insert_raw = plot_cfg.get("insert", [])
        insert_tm_list = []
        for v in insert_raw:
            try: insert_tm_list.append(int(v))
            except ValueError: pass
            
        use_gradient = len(main_tm_list) > 1 and not insert_tm_list
        combined_tm = sorted(list(set(main_tm_list) | set(insert_tm_list)))
        if not combined_tm:
            return
            
        if use_gradient:
            tm_norm = colors.LogNorm(vmin=min(combined_tm), vmax=max(combined_tm))
        else:
            tm_norm = None
            
        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        def tm_color(base_color, current_tm, p_key):
            if p_key == "AN":
                return colors.to_rgb(base_color)
            rgb_base = colors.to_rgb(base_color)
            if not use_gradient:
                return np.clip(rgb_base, 0, 1)
            h, l, s = colorsys.rgb_to_hls(*rgb_base)
            norm_val = tm_norm(current_tm)
            if current_tm <= 0:
                norm_val = tm_norm(max(combined_tm))
            if np.ma.is_masked(norm_val):
                norm_val = 0.0
            if current_tm == max(combined_tm):
                new_l, new_s = l, s
            else:
                diff = (1.0 - float(norm_val))
                new_l = max(l, min(0.85, l + (diff * 0.4)))
                new_s = s * (1.0 - (diff * 0.3))
            raw_rgb = colorsys.hls_to_rgb(h, new_l, new_s)
            return np.clip(raw_rgb, 0, 1)

        threshlds = sorted(list(set(k[5] for k in st_dict.keys())))
        gt_list = sorted(list(set(k[4] for k in st_dict.keys())))
        
        gt_068_092 = next((g for g in gt_list if "0.68" in g and "0.92" in g and g.startswith("0.68")), gt_list[0] if len(gt_list) > 0 else None)
        gt_092_068 = next((g for g in gt_list if "0.92" in g and "0.68" in g and g.startswith("0.92")), gt_list[-1] if len(gt_list) > 1 else None)
        
        cols_config = [
            {"label": "LD25", "msg_arena": "big", "st_arena": "bigA", "agents": "25"},
            {"label": "HD25", "msg_arena": "small", "st_arena": "smallA", "agents": "25"},
            {"label": "HD100", "msg_arena": "big", "st_arena": "bigA", "agents": "100"}
        ]
        
        for thr in threshlds:
            fig, ax = plt.subplots(3, 3, figsize=(24, 18), constrained_layout=True, squeeze=False)
            inset_axes_dict = {}
            
            for col_idx, col_cfg in enumerate(cols_config):
                ax[0][col_idx].set_title(col_cfg["label"])
                min_buf_drawn = False
                
                # --- MESSAGES LOGIC ---
                for p in self.protocols:
                    p_key = p.get("key")
                    if not self._protocol_enabled(p_key): continue
                    base_color = self._protocol_color(p, scalarMap)
                    
                    is_p0 = (p_key == "AN")
                    tms_to_iterate = ["60"] if is_p0 else combined_tm
                    
                    for tm in tms_to_iterate:
                        if is_p0:
                            is_main = True
                            is_insert = bool(insert_tm_list)
                        else:
                            is_main = tm in main_tm_list
                            is_insert = tm in insert_tm_list
                            if not (is_main or is_insert): continue
                        
                        m_data = msgs_dict.get((p_key, col_cfg["msg_arena"], col_cfg["agents"], str(tm)))
                        if not m_data and is_p0:
                            m_data = msgs_dict.get((p_key, col_cfg["msg_arena"], col_cfg["agents"], "60"))
                            if not m_data:
                                m_data = msgs_dict.get((p_key, col_cfg["msg_arena"], col_cfg["agents"], "0"))
                            
                        if m_data:
                            c = tm_color(base_color, tm, p_key)
                            y_data = np.array(m_data) / (int(col_cfg["agents"]) - 1)
                            targets = []
                            
                            if is_main:
                                targets.append(ax[0][col_idx])
                                if not min_buf_drawn:
                                    ax[0][col_idx].plot([5 / (int(col_cfg["agents"]) - 1)] * 1200, color="black", ls='--', lw=3)
                                    min_buf_drawn = True
                            
                            if is_insert:
                                if (0, col_idx) not in inset_axes_dict:
                                    # ROW 0: FORCED TOP-RIGHT
                                    best_box = [0.62, 0.62, 0.35, 0.35]
                                    ins_ax = ax[0][col_idx].inset_axes(best_box)
                                    ins_ax.set_xlim(0, 1201)
                                    ins_ax.set_ylim(-0.03, 1.03)
                                    ins_ax.set_xticks([0, 300, 600, 900, 1200])
                                    ins_ax.tick_params(labelbottom=False, labelleft=False)
                                    ins_ax.grid(True, ls=':', color='silver')
                                    ins_ax.plot([5 / (int(col_cfg["agents"]) - 1)] * 1200, color="black", ls='--', lw=2)
                                    inset_axes_dict[(0, col_idx)] = ins_ax
                                targets.append(inset_axes_dict[(0, col_idx)])
                                
                            for t_ax in targets:
                                t_ax.plot(y_data, color=c, lw=4, alpha=0.9)
                
                # --- STATE LOGIC ---
                for row_idx, gt_val in enumerate([gt_068_092, gt_092_068], start=1):
                    if not gt_val: continue
                    for p in self.protocols:
                        p_key = p.get("key")
                        if not self._protocol_enabled(p_key): continue
                        base_color = self._protocol_color(p, scalarMap)
                        
                        is_p0 = (p_key == "AN")
                        tms_to_iterate = ["60"] if is_p0 else combined_tm
                        
                        for tm in tms_to_iterate:
                            if is_p0:
                                is_main = True
                                is_insert = bool(insert_tm_list)
                            else:
                                is_main = tm in main_tm_list
                                is_insert = tm in insert_tm_list
                                if not (is_main or is_insert): continue
                            
                            s_data = st_dict.get((p_key, col_cfg["st_arena"], col_cfg["agents"], str(tm), gt_val, thr))
                            if not s_data and is_p0:
                                s_data = st_dict.get((p_key, col_cfg["st_arena"], col_cfg["agents"], "60", gt_val, thr))
                                if not s_data:
                                    s_data = st_dict.get((p_key, col_cfg["st_arena"], col_cfg["agents"], "0", gt_val, thr))
                                
                            if s_data is not None:
                                c = tm_color(base_color, tm, p_key)
                                targets = []
                                if is_main:
                                    targets.append(ax[row_idx][col_idx])
                                if is_insert:
                                    if (row_idx, col_idx) not in inset_axes_dict:
                                        # ROW 2: FORCED TOP-RIGHT, ROW 1: DYNAMIC
                                        if row_idx == 2:
                                            best_box = [0.62, 0.62, 0.35, 0.35]
                                        else:
                                            best_box = self.find_emptiest_inset_position(ax[row_idx][col_idx])
                                        ins_ax = ax[row_idx][col_idx].inset_axes(best_box)
                                        ins_ax.set_xlim(0, 1201)
                                        ins_ax.set_ylim(-0.03, 1.03)
                                        ins_ax.set_xticks([0, 300, 600, 900, 1200])
                                        ins_ax.tick_params(labelbottom=False, labelleft=False)
                                        ins_ax.grid(True, ls=':', color='silver')
                                        inset_axes_dict[(row_idx, col_idx)] = ins_ax
                                    targets.append(inset_axes_dict[(row_idx, col_idx)])
                                
                                for t_ax in targets:
                                    t_ax.plot(s_data, color=c, lw=4, alpha=0.9)
                                    
            for i in range(3):
                for j in range(3):
                    ax[i][j].grid(True)
                    ax[i][j].set_xlim(0, 1201)
                    ax[i][j].set_ylim(-0.03, 1.03)
                    ax[i][j].set_xticks([0, 300, 600, 900, 1200])
                    if i < 2:
                        ax[i][j].set_xticklabels([])
                    else:
                        ax[i][j].set_xlabel(r"$T\, (s)$")
                    if j > 0:
                        ax[i][j].set_yticklabels([])
            
            ax[0][0].set_ylabel(r"$M$")
            ax[1][0].set_ylabel(r"$Q(G,\tau)$")
            ax[2][0].set_ylabel(r"$Q(G,\tau)$")
            
            ax_right1 = ax[1][2].twinx()
            ax_right1.set_yticks([])
            lab1 = str(gt_068_092).replace('_','.').replace(';', r' \rightarrow ')
            ax_right1.set_ylabel(r"$G: " + lab1 + r"$", rotation=270, labelpad=30)
            
            ax_right2 = ax[2][2].twinx()
            ax_right2.set_yticks([])
            lab2 = str(gt_092_068).replace('_','.').replace(';', r' \rightarrow ')
            ax_right2.set_ylabel(r"$G: " + lab2 + r"$", rotation=270, labelpad=30)
            
            handles_r = []
            if main_tm_list:
                main_str = ", ".join(map(str, main_tm_list))
                handles_r.append(mlines.Line2D([], [], marker='', linestyle='', label="Main: $T_m=" + main_str + "$"))
            
            if insert_tm_list:
                handles_r.append(mlines.Line2D([], [], marker='', linestyle='', label="Inset: $T_m=" + str(insert_tm_list[0]) + "$"))

            for p in self.protocols:
                p_key = p.get("key")
                if self._protocol_enabled(p_key) and p.get("legend", True):
                    color = self._protocol_color(p, scalarMap)
                    handles_r.append(mlines.Line2D([], [], color=color, marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", p_key)))
                    
            fig.legend(handles=handles_r, loc='upper center', bbox_to_anchor=(0.5, 0.0), framealpha=0.7, fontsize=24, ncol=4)
            fig.savefig(f"{path}{thr}_short_grid.pdf", bbox_inches='tight')
            plt.close(fig)

##########################################################################################################
    def plot_messages_diff(self, dict_msgs):
        if not os.path.exists(self.base + "/msgs_data/images/"):
            os.makedirs(self.base + "/msgs_data/images/", exist_ok=True)
        path = self.base + "/msgs_data/images/"

        diff_protocols = self.diff_plot_config.get("protocols", self.protocols)
        diff_protocols_by_key = {p.get("key"): p for p in diff_protocols if p.get("key") is not None}

        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("key"): self._protocol_color(p, scalarMap) for p in diff_protocols}

        all_cols = set()
        for list_of_dicts in dict_msgs.values():
            for dct in list_of_dicts:
                for k in dct.keys():
                    if k[3] == "0.68;0.92":
                        try: all_cols.add(int(k[-1]))
                        except: continue
        
        columns = self._plot_columns(sorted(list(all_cols)))
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)

        svoid_x_ticks, void_x_ticks, real_x_ticks = [], [], []
        for x in range(0, 1201, 50):
            if x % 300 == 0:
                svoid_x_ticks.append(''); void_x_ticks.append('')
                real_x_ticks.append(str(int(np.round(x, 0))))
            else:
                void_x_ticks.append('')

        fig, ax = plt.subplots(nrows=3, ncols=ncols, figsize=(6.0 * ncols, 18), squeeze=False, layout="constrained")
        min_buf_line = np.zeros((3, ncols), int)
        used_protocols = set()
        used_roots = {}

        for root_name, list_of_dicts in dict_msgs.items():
            folder_cfg = self._get_diff_folder_cfg(root_name)
            l_style = folder_cfg.get("line_style", "-")
            l_label = folder_cfg.get("label", str(root_name) if root_name else "default")
            
            for dct in list_of_dicts:
                for k, res in dct.items():
                    if k[3] != "0.68;0.92": continue
                    if str(k[-1]) not in col_index: continue
                    
                    p_key = None
                    if k[1] == 'P':
                        p_key = "AN" if k[7] == "0" else "AN_t"
                    else:
                        try:
                            val_proto = int(k[4])
                            if val_proto == 0: p_key = "ID+B"
                            elif val_proto == 2: p_key = "ID+R_f"
                            else:
                                if k[5] == "0": p_key = "ID+R_inf"
                                elif k[5] == "31": p_key = "ID+R_a"
                                else: p_key = "ID+R_1"
                        except: continue

                    if p_key and self._protocol_enabled_diff(p_key, root_name, diff_protocols_by_key):
                        used_protocols.add(p_key)
                        if root_name not in used_roots:
                            used_roots[root_name] = (l_label, l_style)

                        try:
                            norm = int(k[6]) - 1
                            if norm <= 0: norm = 1
                            norm_data = [xi / norm for xi in res]
                        except: continue
                        
                        row = 0
                        if k[0] == 'big' and str(k[6]) == '25': row = 0
                        elif k[0] == 'big' and str(k[6]) == '100': row = 2
                        elif k[0] == 'small': row = 1
                        
                        col = col_index[str(k[-1])]
                        color = protocol_colors.get(p_key, "red")

                        if min_buf_line[row][col] == 0:
                            ax[row][col].plot([5/norm]*1200, color="black", lw=4, ls="--")
                            min_buf_line[row][col] = 1
                        ax[row][col].plot(norm_data, color=color, lw=6, linestyle=l_style)

        self._apply_messages_style(ax, ncols, columns, svoid_x_ticks, void_x_ticks, real_x_ticks)

        handles_r = []
        for p in diff_protocols:
            pk = p.get("key")
            if pk in used_protocols and p.get("legend", True):
                lbl = p.get("label", pk)
                handles_r.append(mlines.Line2D([], [], color=protocol_colors.get(pk), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=lbl))
        
        for r_name, (r_label, r_style) in used_roots.items():
            handles_r.append(mlines.Line2D([], [], color='black', linestyle=r_style, lw=2, label=r_label))

        if handles_r:
            fig.legend(handles=handles_r, ncols=min(len(handles_r), 6), loc='upper center', bbox_to_anchor=(0.5, 0.0), framealpha=0.7, fontsize=24)

        fig.savefig(path + "messages_diff.pdf", bbox_inches='tight')
        plt.close(fig)

    def _apply_messages_style(self, ax, ncols, columns, svoid, void, real):
        for x in range(3):
            ax[x][0].set_ylabel(r"$M$")
            for y in range(ncols):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0, 1201)
                ax[x][y].set_ylim(-0.03, 1.03)
                if x < 2:
                    ax[x][y].set_xticks(np.arange(0, 1201, 300), labels=svoid)
                else:
                    ax[x][y].set_xticks(np.arange(0, 1201, 300), labels=real)
                    ax[x][y].set_xlabel(r"$T\, (s)$")
                ax[x][y].set_xticks(np.arange(0, 1201, 50), labels=void, minor=True)
                if y > 0: ax[x][y].set_yticklabels([])

        labels_side = ["LD25", "HD25", "HD100"]
        for y in range(ncols):
            axt = ax[0][y].twiny()
            axt.set_xticklabels([])
            axt.set_xlabel(rf"$T_m = {int(columns[y])}\, s$")
        for r in range(3):
            ayt = ax[r][ncols-1].twinx()
            ayt.set_yticklabels([])
            ayt.set_ylabel(labels_side[r], labelpad=20)

##########################################################################################################
    def plot_messages(self,data):
        dict_park_real, dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adpt = {},{},{},{},{},{},{}
        for k in data.keys():
            if(k[3]=="0.68;0.92"):
                if k[1]=='P' and k[7]!="0":
                    dict_park.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                elif k[1]=='P' and k[7]=="0":
                    dict_park_real.update({(k[0],k[2],k[3],k[5],k[6],"60"):data.get(k)})
                else:
                    if int(k[4])==0:
                        dict_adam.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                    elif int(k[4])==2:
                        dict_fifo.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                    else:
                        if k[5]=="0":
                            dict_rnd_inf.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                        elif k[5]=="31":
                            dict_rnd_adpt.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                        else:
                            dict_rnd.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})

        self.print_messages([dict_park,dict_adam,dict_fifo, dict_rnd, dict_rnd_inf,dict_rnd_adpt,dict_park_real])

##########################################################################################################
    def _identify_protocol_key(self, k):
        algo, c, m_t, m_h = k[0], int(k[6]), int(k[9]), k[10]
        if algo == 'P':
            return "AN" if m_t == 0 else "AN_t"
        if algo == 'O':
            if c == 0: return "ID+B"
            if c == 2: return "ID+R_f"
            if m_h == "1": return "ID+R_1"
            if m_h == "31": return "ID+R_a"
            return "ID+R_inf"
        return None

    def _get_scalar_map_msgs(self):
        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        return cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis')), typo

##########################################################################################################
    # FIX: Corretto l'ordine per interpretare perfettamente i dati "O" dai messaggi
    def _identify_protocol_key_msgs(self, k):
        algo = k[1]
        if algo == 'P':
            real_an = str(k[7])
            return "AN" if real_an == "0" else "AN_t"
        if algo == 'O':
            try:
                val_proto = int(k[4])
                if val_proto == 0: return "ID+B"
                if val_proto == 2: return "ID+R_f"
                hops = str(k[5])
                if hops == "0": return "ID+R_inf"
                if hops == "31": return "ID+R_a"
                return "ID+R_1"
            except Exception:
                return None
        return None
    
    def _apply_plot_style(self, ax, ncols, columns, is_messages=False):
        for x in range(3):
            for y in range(ncols):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0, 1201)
                ax[x][y].set_ylim(-0.03, 1.03)
                if y == 0:
                    ax[x][y].set_ylabel(r"$M$" if is_messages else r"$Q(G,\tau)$")
                else:
                    ax[x][y].set_yticklabels([])
                if x == 2:
                    ax[x][y].set_xlabel(r"$T\, (s)$")
                    ax[x][y].set_xticks([0, 300, 600, 900, 1200])
                    ax[x][y].set_xticklabels(["0", "300", "600", "900", "1200"])
                else:
                    ax[x][y].set_xticklabels([])
                if x == 0:
                    axt = ax[x][y].twiny()
                    axt.set_xticks([])
                    axt.set_xlabel(rf"$T_m = {int(columns[y])}\, s$")
        labels = ["LD25", "HD25", "HD100"]
        for row in range(3):
            ax_right = ax[row][ncols-1].twinx()
            ax_right.set_yticks([])
            ax_right.set_ylabel(labels[row], rotation=270, labelpad=40)

##########################################################################################################
    def print_evolutions_diff(self, path, ground_T, threshlds, dict_st, dict_times, o_k, more_k):
        diff_protocols = self.diff_plot_config.get("protocols", self.protocols)
        diff_protocols_by_key = {p.get("key"): p for p in diff_protocols if p.get("key") is not None}

        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        columns = self._plot_columns(o_k)
        col_index = {c: i for i, c in enumerate(columns)}
        ncols = len(columns)

        for gt in ground_T:
            for thr in threshlds:
                fig, ax = plt.subplots(nrows=3, ncols=ncols, figsize=(6.0 * ncols, 18), squeeze=False, layout="constrained")
                
                used_protocol_keys = set()
                used_roots = {}

                for root_name, data_list in dict_st.items():
                    folder_cfg = self._get_diff_folder_cfg(root_name)
                    l_style = folder_cfg.get("line_style", "-")
                    l_label = folder_cfg.get("label", str(root_name) if root_name else "default")
                    
                    for data_in in data_list:
                        for k, s_data in data_in.items():
                            if k[4] != thr or k[5] != gt:
                                continue
                            
                            row = 0
                            if k[1] == "smallA": row = 1
                            elif k[7] == "100": row = 2
                            
                            try:
                                m_t = int(k[9])
                                if m_t not in col_index: continue
                                col = col_index[m_t]
                            except: continue

                            p_key = self._identify_protocol_key(k)
                            if p_key and self._protocol_enabled_diff(p_key, root_name, diff_protocols_by_key):
                                p_cfg = diff_protocols_by_key.get(p_key, {})
                                color = self._protocol_color(p_cfg, scalarMap)
                                ax[row][col].plot(s_data[0], color=color, lw=4, linestyle=l_style)
                                
                                used_protocol_keys.add(p_key)
                                if root_name not in used_roots:
                                    used_roots[root_name] = (l_label, l_style)

                self._apply_plot_style(ax, ncols, columns, is_messages=False)
                
                handles_r = []
                for p in diff_protocols:
                    pk = p.get("key")
                    if pk in used_protocol_keys and p.get("legend", True):
                        handles_r.append(mlines.Line2D([], [], color=self._protocol_color(p, scalarMap), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", pk)))
                
                for r_name, (r_label, r_style) in used_roots.items():
                    handles_r.append(mlines.Line2D([], [], color='black', linestyle=r_style, lw=2, label=r_label))

                if handles_r:
                    leg_cols = min(len(handles_r), max(4, ncols))
                    fig.legend(handles=handles_r, ncols=leg_cols, loc='upper center', bbox_to_anchor=(0.5, 0.0), framealpha=0.7, fontsize=24)
                
                fig.savefig(f"{path}{thr}_{gt.replace(';','_')}_diff_activation.pdf", bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def plot_active_w_gt_thr_diff(self, dict_st, dict_times):
        if not os.path.exists(self.base + "/proc_data/images/"):
            os.makedirs(self.base + "/proc_data/images/", exist_ok=True)
        path = self.base + "/proc_data/images/"
        
        ground_T, threshlds, o_k = set(), set(), set()
        arenas, agents = set(), set()
        
        for root_name, data_list in dict_st.items():
            for data_in in data_list: 
                for k in data_in.keys():
                    arenas.add(k[1])
                    threshlds.add(k[4])
                    ground_T.add(k[5])
                    agents.add(k[7])
                    if int(k[9]) != 0:
                        o_k.add(int(k[9]))

        ground_T = sorted(list(ground_T))
        threshlds = sorted(list(threshlds))
        o_k = sorted(list(o_k))
        more_k = [sorted(list(arenas)), sorted(list(agents))]

        self.print_evolutions_diff(path, ground_T, threshlds, dict_st, dict_times, o_k, more_k)

##########################################################################################################
    def read_msgs_csv(self,path):
        data = {}
        lc = 0
        with open(path,newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if lc == 0:
                    lc = 1
                else:
                    keys = []
                    array_val=[]
                    for val in row:
                        split_val = val.split('\t')
                        if len(split_val)==1:
                            tval = val  
                            if ']' in val:
                                tval = ''
                                for c in val:
                                    if c != ']':
                                        tval+=c
                            array_val.append(float(tval))
                            if ']' in val:
                                data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5],keys[6],keys[7]):array_val})
                        else:
                            for k in range(len(split_val)):
                                tval = split_val[k]
                                if '[' in split_val[k]:
                                    tval = ''
                                    for c in split_val[k]:
                                        if c != '[':
                                            tval+=c
                                    array_val.append(float(tval))
                                else:
                                    keys.append(tval)
        return data

##########################################################################################################
    def read_csv(self,path,algo,n_runs,arena):
        lc = 0
        keys = []
        data = {}
        with open(path, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                change = 0
                if lc == 0:
                    lc = 1
                    for val in row:
                        keys=val.split('\t')
                else:
                    array_val = []
                    std_val = []
                    data_val = {}
                    for val in row:
                        split_val = val.split('\t')
                        if len(split_val)==1:
                            tval = val  
                            if ']' in val:
                                tval = ''
                                for c in val:
                                    if c != ']':
                                        tval+=c
                            array_val.append(float(tval)) if change==0 else std_val.append(float(tval))
                            if ']' in val:
                                data_val.update({keys[-2]:array_val})
                                data_val.update({keys[-1]:std_val})
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7]),data_val.get(keys[8])):(data_val.get(keys[9]),data_val.get(keys[10]))})
                        elif len(split_val)==2:
                            lval = ""
                            rval = ""
                            change = 1
                            for c in split_val[0]:
                                if c != ']':
                                    lval += c
                            for c in split_val[1]:
                                if c != '[':
                                    rval += c
                            if rval == '-':
                                rval = -1
                            array_val.append(float(lval))
                            std_val.append(float(rval))
                            if rval == -1:
                                data_val.update({keys[-2]:array_val})
                                data_val.update({keys[-1]:std_val})
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7]),data_val.get(keys[8])):(data_val.get(keys[9]),data_val.get(keys[10]))})
                        else:
                            for k in range(len(split_val)):
                                tval = split_val[k]
                                if '[' in split_val[k]:
                                    tval = ''
                                    for c in split_val[k]:
                                        if c != '[':
                                            tval+=c
                                    array_val.append(float(tval))
                                else:
                                    data_val.update({keys[k]:tval})
        return data

##########################################################################################################
    def divide_data(self,data):
        states, times = {},{}
        algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops = [],[],[],[],[],[],[],[],[],[],[]
        for k in data.keys():
            for i in range(len(k)-1):
                if i == 0 and k[i] not in algorithm: algorithm.append(k[i])
                elif i == 1 and k[i] not in arena_size: arena_size.append(k[i])
                elif i == 2 and k[i] not in n_runs: n_runs.append(k[i])
                elif i == 3 and k[i] not in exp_time: exp_time.append(k[i])
                elif i == 4 and k[i] not in communication: communication.append(k[i])
                elif i == 5 and k[i] not in n_agents: n_agents.append(k[i])
                elif i == 6 and k[i] not in gt: gt.append(k[i])
                elif i == 7 and k[i] not in thrlds: thrlds.append(k[i])
                elif i == 8 and k[i] not in min_buff_dim: min_buff_dim.append(k[i])
                elif i == 9 and k[i] not in msg_time: msg_time.append(k[i])
                elif i == 10 and k[i] not in msg_hops: msg_hops.append(k[i])
            if k[-1] == "times":
                times.update({k[:-1]:data.get(k)})
            elif k[-1] == "swarm_state":
                states.update({k[:-1]:data.get(k)})
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time,msg_hops), states, times
    
##########################################################################################################
    def plot_active_w_gt_thr(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state, dict_park_state_real  = {},{},{},{},{},{},{}
        dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time, dict_park_time_real        = {},{},{},{},{},{},{}
        ground_T, threshlds , jolly, msg_hops                                               = [],[],[],[]
        algo,arena,runs,time,comm,agents,buf_dim                                            = [],[],[],[],[],[],[]
        o_k                                                                                 = []

        def add_or_merge(dct, key, series):
            if key in dct:
                old = dct[key]
                if len(old) == len(series):
                    dct[key] = [(x + y) / 2 for x, y in zip(old, series)]
                else:
                    dct[key] = series
            else:
                dct[key] = series

        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in arena: arena.append(k0[1])
                if k0[2] not in runs: runs.append(k0[2])
                if k0[3] not in time: time.append(k0[3])
                if k0[4] not in threshlds: threshlds.append(k0[4])
                if k0[5] not in ground_T: ground_T.append(k0[5])
                if k0[6] not in comm: comm.append(k0[6])
                if k0[7] not in agents: agents.append(k0[7])
                if k0[8] not in buf_dim: buf_dim.append(k0[8])
                if k0[9] not in jolly: jolly.append(k0[9])
                if k0[10] not in msg_hops: msg_hops.append(k0[10])
        for i in range(len(data_in)):
            for a in algo:
                for a_s in arena:
                    for n_r in runs:
                        for et in time:
                            for c in comm:
                                for n_a in agents:
                                    for m_b_d in buf_dim:
                                        for m_h in msg_hops:
                                            for m_t in jolly:
                                                for gt in ground_T:
                                                    for thr in threshlds:
                                                        s_data = data_in[i].get((a,a_s,n_r,et,thr,gt,c,n_a,m_b_d,m_t,m_h))
                                                        t_data = times[i].get((a,a_s,n_r,et,thr,gt,c,n_a,m_b_d,m_t,m_h))
                                                        if s_data != None:
                                                            if int(m_t) !=0 and m_t not in o_k: o_k.append(m_t)
                                                            
                                                            if a=='P' and int(c)==0 and int(m_t)!=0:
                                                                key = (a_s,n_a,m_t,gt,thr)
                                                                add_or_merge(dict_park_state, key, s_data[0])
                                                                add_or_merge(dict_park_time, key, t_data[0])
                                                            elif a=='P' and int(c)==0 and int(m_t)==0:
                                                                key = (a_s,n_a,"60",gt,thr)
                                                                add_or_merge(dict_park_state_real, key, s_data[0])
                                                                add_or_merge(dict_park_time_real, key, t_data[0])
                                                            elif a=='O':
                                                                key = (a_s,n_a,m_t,gt,thr)
                                                                if int(c)==0:
                                                                    add_or_merge(dict_adms_state, key, s_data[0])
                                                                    add_or_merge(dict_adms_time, key, t_data[0])
                                                                elif int(c)==2:
                                                                    add_or_merge(dict_fifo_state, key, s_data[0])
                                                                    add_or_merge(dict_fifo_time, key, t_data[0])
                                                                else:
                                                                    if m_h=="1":
                                                                        add_or_merge(dict_rnd_state, key, s_data[0])
                                                                        add_or_merge(dict_rnd_time, key, t_data[0])
                                                                    elif m_h=="31":
                                                                        add_or_merge(dict_rnd_adapt_state, key, s_data[0])
                                                                        add_or_merge(dict_rnd_adapt_time, key, t_data[0])
                                                                    else:
                                                                        add_or_merge(dict_rnd_inf_state, key, s_data[0])
                                                                        add_or_merge(dict_rnd_inf_time, key, t_data[0])
        self.print_evolutions(path,ground_T,threshlds,[dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state,dict_park_state_real],[dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time,dict_park_time_real],o_k,[arena,agents])

##########################################################################################################
    def print_evolutions(self, path, ground_T, threshlds, data_in, times_in, keys, more_k):
        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adapt, dict_park_real = data_in
        
        o_k = sorted(set([int(x) for x in keys]))
        columns = self._plot_columns(o_k)
        col_index = {c: i for i, c in enumerate(columns)}
        ncols = len(columns)
        arena = more_k[0]
        protocol_colors = {p.get("key"): self._protocol_color(p, scalarMap) for p in self.protocols}

        for gt in ground_T:
            for thr in threshlds:
                fig, ax = plt.subplots(nrows=3, ncols=ncols, figsize=(6.0 * ncols, 18), squeeze=False, layout="constrained")
                used_protocols = set()

                for a in arena:
                    agents = more_k[1]
                    for ag in agents:
                        row = 1 if a == "smallA" else (2 if int(ag) == 100 else 0)
                        for col_val in columns:
                            col = col_index[col_val]
                            key = (a, ag, str(col_val), gt, thr)
                            
                            mapping = [
                                ("AN", dict_park_real), ("AN_t", dict_park), ("ID+B", dict_adam),
                                ("ID+R_f", dict_fifo), ("ID+R_1", dict_rnd), 
                                ("ID+R_inf", dict_rnd_inf), ("ID+R_a", dict_rnd_adapt)
                            ]

                            for p_key, d_src in mapping:
                                if self._protocol_enabled(p_key) and d_src.get(key) is not None:
                                    ax[row][col].plot(d_src.get(key), color=protocol_colors.get(p_key, "red"), lw=6)
                                    used_protocols.add(p_key)

                self._apply_plot_style(ax, ncols, columns, is_messages=False)

                handles_r = []
                for p in self.protocols:
                    pk = p.get("key")
                    if pk in used_protocols and p.get("legend", True):
                        handles_r.append(mlines.Line2D([], [], color=protocol_colors.get(pk), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", pk)))

                if handles_r:
                    fig.legend(handles=handles_r, ncols=min(len(handles_r), ncols), loc='upper center', bbox_to_anchor=(0.5, 0.0), framealpha=0.7, fontsize=24)
                
                fig.savefig(f"{path}{thr}_{gt.replace(';','_')}_activation.pdf", bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_evolutions_anonymous(self,path,ground_T,threshlds,data_in,times_in,keys,more_k):
        typo = [0]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,_,_,_,_,_, dict_park_real = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5], data_in[6]
        arena = more_k[0]
        agents_list = more_k[1]
        gt_h2l = None
        gt_l2h = None
        if len(ground_T) >= 2:
            try:
                sorted_gt = sorted(ground_T, key=lambda x: float(x))
                gt_l2h = sorted_gt[0]
                gt_h2l = sorted_gt[-1]
            except Exception:
                gt_l2h = ground_T[0]
                gt_h2l = ground_T[1]
        elif ground_T:
            gt_l2h = gt_h2l = ground_T[0]
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.makedirs(self.base+"/proc_data/images/", exist_ok=True)

        for thr in threshlds:
            fig, ax = plt.subplots(nrows=3, ncols=2, figsize=(19,16), squeeze=False, layout="constrained")
            for a in arena:
                if a=="smallA":
                    row_base = 1
                    agents = ["25"]
                else:
                    row_base = 0
                    agents = agents_list
                for ag in agents:
                    row = row_base
                    if int(ag) == 100:
                        row = 2

                    if gt_h2l is not None:
                        s = dict_park.get((a,ag,"60",gt_h2l,thr))
                        if s is not None:
                            ax[row][0].plot(s, color=scalarMap.to_rgba(typo[0]), lw=4)
                        sr = dict_park_real.get((a,ag,"60",gt_h2l,thr))
                        if sr is not None:
                            ax[row][0].plot(sr, color="red", lw=4)

                    if gt_l2h is not None:
                        s = dict_park.get((a,ag,"60",gt_l2h,thr))
                        if s is not None:
                            ax[row][1].plot(s, color=scalarMap.to_rgba(typo[0]), lw=4)
                        sr = dict_park_real.get((a,ag,"60",gt_l2h,thr))
                        if sr is not None:
                            ax[row][1].plot(sr, color="red", lw=4)

            svoid_x_ticks = []
            void_x_ticks = []
            real_x_ticks = []
            for x in range(0,1201,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')

            for r in range(3):
                for c in range(2):
                    ax[r][c].set_xlim(0,1201)
                    ax[r][c].set_ylim(-0.03,1.03)
                    ax[r][c].set_xticks(np.arange(0,1201,300), labels=svoid_x_ticks)
                    ax[r][c].set_xticks(np.arange(0,1201,50), labels=void_x_ticks, minor=True)
                    ax[r][c].set_yticks(np.arange(0,1.01,0.1))
                    if c==0:
                        ax[r][c].set_ylabel(r"$Q(G,\tau)$")
                    ax[r][c].grid(True)

            ayt0 = ax[0][1].twinx()
            ayt1 = ax[1][1].twinx()
            ayt2 = ax[2][1].twinx()
            labels = [item.get_text() for item in ayt0.get_yticklabels()]
            empty_string_labels = [''] * len(labels)
            ayt0.set_yticklabels(empty_string_labels)
            ayt1.set_yticklabels(empty_string_labels)
            ayt2.set_yticklabels(empty_string_labels)
            ayt0.set_ylabel("LD25")
            ayt1.set_ylabel("HD25")
            ayt2.set_ylabel("HD100")

            axt0 = ax[0][0].twiny()
            axt1 = ax[0][1].twiny()
            labels0 = [item.get_text() for item in axt0.get_xticklabels()]
            empty0 = ['']*len(labels0)
            axt0.set_xticklabels(empty0)
            axt1.set_xticklabels(empty0)
            axt0.set_xlabel(r"$G_{i}=0.92,G_{f}=0.68$")
            axt1.set_xlabel(r"$G_{i}=0.68,G_{f}=0.92$")

            for c in range(2):
                ax[2][c].set_xticks(np.arange(0,1201,300), labels=real_x_ticks)
                ax[2][c].set_xticks(np.arange(0,1201,50), labels=void_x_ticks, minor=True)
                ax[2][c].set_xlabel(r"$T\, (s)$")

            fig.tight_layout()
            fig_path = self.base+"/proc_data/images/"+thr+"_anonymous_60_0_activation.pdf"
            an_t = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$AN_{t}$")
            an_r = mlines.Line2D([], [], color="red", marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$AN$")
            fig.legend(bbox_to_anchor=(1, 0), handles=[an_r, an_t], ncols=2, loc='upper right', framealpha=0.7, borderaxespad=0)
            fig.savefig(fig_path, bbox_inches='tight')
            plt.close(fig)

##########################################################################################################
    def print_messages(self, data_in):
        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adpt, dict_park_real = data_in
        
        protocol_colors = {p.get("key"): self._protocol_color(p, scalarMap) for p in self.protocols}
        used_protocols = set()

        all_cols = set()
        for dct in (dict_park_real, dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adpt):
            for k in dct.keys():
                try: all_cols.add(int(k[5]))
                except Exception: continue
        
        default_cols = sorted(all_cols) if all_cols else [60, 120, 180, 300, 600]
        columns = self._plot_columns(default_cols)
        columns = [c for c in columns if c in default_cols]
        if not columns:
            columns = default_cols
        
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)

        svoid_x_ticks, void_x_ticks, real_x_ticks = [], [], []
        for x in range(0, 1201, 50):
            if x % 300 == 0:
                svoid_x_ticks.append(''); void_x_ticks.append('')
                real_x_ticks.append(str(int(np.round(x, 0))))
            else:
                void_x_ticks.append('')

        size_per_plot = 6.0
        min_buf_line = np.zeros((3, ncols), int)
        fig, ax = plt.subplots(nrows=3, ncols=ncols, figsize=(size_per_plot * ncols, size_per_plot * 3), squeeze=False, layout="constrained")

        dicts_to_norm = [dict_park_real, dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adpt]
        for dct in dicts_to_norm:
            for k in dct.keys():
                norm = int(k[4]) - 1
                dct[k] = [xi / norm for xi in dct[k]]

        plot_map = [
            ("AN", dict_park_real), ("AN_t", dict_park), ("ID+B", dict_adam),
            ("ID+R_f", dict_fifo), ("ID+R_1", dict_rnd), 
            ("ID+R_inf", dict_rnd_inf), ("ID+R_a", dict_rnd_adpt)
        ]

        for p_key, dct in plot_map:
            if not self._protocol_enabled(p_key): continue
            
            for k, data in dct.items():
                if k[5] not in col_index: continue
                
                if k[0] == 'big' and k[4] == '25': row = 0
                elif k[0] == 'big' and k[4] == '100': row = 2
                elif k[0] == 'small': row = 1
                else: continue
                
                col = col_index[k[5]]
                
                if min_buf_line[row][col] == 0:
                    val = 5 / (int(k[4]) - 1)
                    ax[row][col].plot([val]*1200, color="black", lw=4, ls="--")
                    min_buf_line[row][col] = 1
                
                ax[row][col].plot(data, color=protocol_colors.get(p_key, "red"), lw=6)
                used_protocols.add(p_key)

        for x in range(2):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0, 1201, 300), labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0, 1201, 50), labels=void_x_ticks, minor=True)
        
        for x in range(3):
            for y in range(1, ncols):
                ax[x][y].set_yticklabels([''] * len(ax[x][y].get_yticklabels()))
        
        for y in range(ncols):
            ax[2][y].set_xticks(np.arange(0, 1201, 300), labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0, 1201, 50), labels=void_x_ticks, minor=True)

        for idx, col_val in enumerate(columns):
            axt = ax[0][idx].twiny()
            axt.set_xticklabels([''] * len(axt.get_xticklabels()))
            axt.set_xlabel(rf"$T_m = {int(col_val)}\, s$")

        last_col = ncols - 1
        for r, lab in enumerate(["LD25", "HD25", "HD100"]):
            ayt = ax[r][last_col].twinx()
            ayt.set_yticklabels([''] * len(ayt.get_yticklabels()))
            ayt.set_ylabel(lab)
            ax[r][0].set_ylabel(r"$M$")

        for y in range(ncols): ax[2][y].set_xlabel(r"$T\, (s)$")
        for x in range(3):
            for y in range(ncols):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0, 1201)
                ax[x][y].set_ylim(-0.03, 1.03)

        handles_r = []
        for p in self.protocols:
            pk = p.get("key")
            if pk in used_protocols and p.get("legend", True):
                handles_r.append(mlines.Line2D([], [], color=protocol_colors.get(pk), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", pk)))

        if handles_r:
            leg_cols = min(len(handles_r), max(2, ncols))
            fig.legend(handles=handles_r, ncols=leg_cols, loc='upper center', bbox_to_anchor=(0.5, 0.0), framealpha=0.7, fontsize=24)

        dest_dir = os.path.join(self.base, "msgs_data", "images")
        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
        fig.savefig(os.path.join(dest_dir, "messages.pdf"), bbox_inches='tight')
        plt.close(fig)