import numpy as np
import os, csv, logging, json, re, colorsys
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib.patches import Rectangle
from matplotlib.legend_handler import HandlerBase

logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})

class GradientHandler(HandlerBase):
    def __init__(self, cmap, **kw):
        super().__init__(**kw)
        self.cmap = cmap

    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        artists = []
        n = 6
        for i in range(n):
            color = self.cmap((i+1) / (n - 1))
            x = xdescent + (i / n) * width
            w = width / n + 0.5 
            rect = Rectangle([x, ydescent], w, height, facecolor=color, edgecolor='none', transform=trans)
            artists.append(rect)
        return artists

class Data:

    def __init__(self, mode="default") -> None:
        self.mode = mode
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
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(r',\s*([\]}])', r'\1', content)
        return json.loads(content)

    def _load_diff_bases(self):
        self.bases_diff = []
        self.diff_plot_config = {}
        if self.mode == "diff_short":
            json_path = os.path.join(self.base, "diff_short_plot_config.json")
        else:
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
            logging.warning("Failed to load diff configs (%s). bases_diff will be empty.", exc)

##########################################################################################################
    def _default_plot_config(self):
        return {
            "protocols": [
                {"key": "P.0", "id": 0, "label": r"$AN$", "color": "red", "legend": False},
                {"key": "P.1.0", "id": 1, "label": r"$AN_{t}$", "color": "viridis:0", "legend": True},
                {"key": "P.1.1", "id": 2, "label": r"$AN_{t}^{k}$", "color": "orange", "legend": True},
                {"key": "O.0", "id": 3, "label": r"$ID+B$", "color": "viridis:1", "legend": True},
                {"key": "O.2.0", "id": 4, "label": r"$ID+R_{f}$", "color": "viridis:2", "legend": True},
                {"key": "O.1.1", "id": 5, "label": r"$ID+R_{k}$", "color": "viridis:3", "legend": True},
                {"key": "O.1.0", "id": 6, "label": r"$ID+R_{\infty}$", "color": "viridis:4", "legend": True},
                {"key": "O.1.a", "id": 7, "label": r"$ID+R_{a}$", "color": "viridis:5", "legend": True}
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
        if self.mode == "short":
            path = os.path.join(self.base, "short_plot_config.json")
        elif self.mode == "diff":
            path = os.path.join(self.base, "diff_plot_config.json")
        elif self.mode == "diff_short":
            path = os.path.join(self.base, "diff_short_plot_config.json")
        else:
            path = os.path.join(self.base, "plot_config.json")
            
        if not os.path.exists(path):
            return cfg
        try:
            user_cfg = self._read_json_robust(path)
            return self._merge_plot_config(cfg, user_cfg)
        except Exception as exc:
            logging.warning("Failed to load %s (%s). Using defaults.", path, exc)
            return cfg

##########################################################################################################
    def apply_plot_overrides(self, targets, exclude_protocols=None, exclude_tm=None):
        if "plots" not in self.plot_config:
            self.plot_config["plots"] = {}
            
        if exclude_protocols is not None:
            existing = self.plot_config["plots"].get("exclude_protocols", [])
            self.plot_config["plots"]["exclude_protocols"] = list(set(existing + exclude_protocols))
            
        if exclude_tm is not None:
            existing = self.plot_config["plots"].get("exclude_tm", [])
            try:
                new_tm = [int(x) for x in exclude_tm if str(x).strip().isdigit()]
                self.plot_config["plots"]["exclude_tm"] = list(set(existing + new_tm))
            except ValueError:
                pass

##########################################################################################################
    def _plot_columns(self, default_cols):
        plot_cfg = self.plot_config.get("plots", {})
        cols = plot_cfg.get("columns")
        exclude_tm = plot_cfg.get("exclude_tm", [])
        
        exclude_tm_ints = [int(x) for x in exclude_tm if str(x).strip().isdigit()]
        out = []
        
        if not cols:
            out = list(default_cols)
        else:
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
                    out = filtered

        if not out:
            out = list(default_cols)

        return [c for c in out if c not in exclude_tm_ints]

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

    def _protocol_color_with_k(self, p_key, k_samp, n_agents, ps_k_dict, scalarMap):
        if p_key == "P.1.1":
            p = self.protocols_by_key.get(p_key)
            base_color = self._protocol_color(p, scalarMap) if p else colors.to_rgb("orange")
            k_list = sorted(list(ps_k_dict.get(str(n_agents), set())))
            if not k_list:
                return base_color
            try:
                idx = k_list.index(float(k_samp))
            except ValueError:
                idx = 0
            n = len(k_list)
            if n <= 1:
                return base_color
            
            rgb = colors.to_rgb(base_color)
            h, l, s = colorsys.rgb_to_hls(*rgb)
            
            max_l = 0.85
            if l >= max_l: 
                max_l = min(0.95, l + 0.15)
            new_l = l + (max_l - l) * (idx / (n - 1))
            rgb_new = colorsys.hls_to_rgb(h, new_l, s)
            return tuple(min(1.0, max(0.0, c)) for c in rgb_new)
            
        p = self.protocols_by_key.get(p_key)
        return self._protocol_color(p, scalarMap)

##########################################################################################################
    def _identify_protocol_key_from_vars(self, algo, comm, msg_time, msg_hops):
        if algo == 'P':
            return "P.0" if int(msg_time) == 0 else "P.1.0"
        if algo == 'Ps':
            return "P.1.1"
        if algo == 'O':
            c = int(comm)
            if c == 0: return "O.0"
            if c == 2: return "O.2.0"
            hops = str(msg_hops)
            if hops == "0": return "O.1.0"
            if hops == "31": return "O.1.a"
            return "O.1.1"
        return None

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
            # Ensure the canvas has computed the layout and limits
            ax.figure.canvas.draw_idle()
        except Exception:
            pass

        for line in ax.lines:
            xdata = line.get_xdata()
            ydata = line.get_ydata()
            
            # Filter out NaN values
            valid = ~(np.isnan(xdata) | np.isnan(ydata))
            if not np.any(valid):
                continue
                
            xy = np.column_stack((xdata[valid], ydata[valid]))
            
            try:
                # Transform data coordinates to axes coordinates [0, 1]
                disp_xy = line.get_transform().transform(xy)
                ax_xy = ax.transAxes.inverted().transform(disp_xy)
                
                ls = line.get_linestyle()
                if ls not in ['None', 'none', '', ' ', False, None]:
                    # Calculate cumulative distance between consecutive points
                    diffs = np.diff(ax_xy, axis=0)
                    dists = np.linalg.norm(diffs, axis=1)
                    cum_dists = np.insert(np.cumsum(dists), 0, 0)
                    total_length = cum_dists[-1]
                    
                    if total_length > 0:
                        # Resample uniformly based on physical arc length
                        step_size = 0.01 # Generates a point every 1% of axes space
                        num_uniform_pts = int(total_length / step_size) + 1
                        uniform_dists = np.linspace(0, total_length, num_uniform_pts)
                        
                        # Interpolate X and Y independently based on cumulative distance
                        x_interp = np.interp(uniform_dists, cum_dists, ax_xy[:, 0])
                        y_interp = np.interp(uniform_dists, cum_dists, ax_xy[:, 1])
                        points_axes.append(np.column_stack((x_interp, y_interp)))
                    else:
                        points_axes.append(ax_xy)
                else:
                    # If it's a scatter-like line (no connecting segments), keep raw points
                    points_axes.append(ax_xy)
            except Exception:
                pass

        if not points_axes:
            return candidates["top_left"]
            
        # Aggregate all points and evaluate bounding boxes
        all_points_axes = np.vstack(points_axes)
        x_ax, y_ax = all_points_axes[:, 0], all_points_axes[:, 1]
        
        for key, box in candidates.items():
            x0, y0, w, h = box
            in_box = (x_ax >= x0) & (x_ax <= x0 + w) & (y_ax >= y0) & (y_ax <= y0 + h)
            counts[key] = np.sum(in_box)
            
        best_position_key = min(counts, key=counts.get)
        return candidates[best_position_key]

##########################################################################################################
    def _extract_short_data(self, tot_st, tot_msgs):
        msgs_dict = {}
        st_dict = {}
        ps_k_dict = {}
        
        for k, res in tot_msgs.items():
            if k[3] == "0.68;0.92":
                arena, algo, thr, gt, comm, msg_hops, agents, k_samp, tm = k
                p_key = self._identify_protocol_key_from_vars(algo, comm, tm, msg_hops)
                if p_key:
                    if p_key == "P.1.1":
                        if agents not in ps_k_dict: ps_k_dict[agents] = set()
                        ps_k_dict[agents].add(float(k_samp))
                    msgs_dict[(p_key, arena, str(agents), str(tm), str(k_samp))] = res
                    
        for states in tot_st:
            for k, res in states.items():
                algo, arena, thr, gt, comm, agents, tm, msg_hops, k_samp = k[0], k[1], k[4], k[5], k[6], k[7], k[9], k[10], k[11]
                p_key = self._identify_protocol_key_from_vars(algo, comm, tm, msg_hops)
                if p_key:
                    if p_key == "P.1.1":
                        if agents not in ps_k_dict: ps_k_dict[agents] = set()
                        ps_k_dict[agents].add(float(k_samp))
                    s_key = (p_key, arena, str(agents), str(tm), gt, thr, str(k_samp))
                    if s_key not in st_dict:
                        st_dict[s_key] = []
                    st_dict[s_key].append(res[0])
                    
        for s_key, lst in st_dict.items():
            min_len = min(len(x) for x in lst)
            arr = np.array([x[:min_len] for x in lst])
            st_dict[s_key] = np.mean(arr, axis=0).tolist()
            
        return msgs_dict, st_dict, ps_k_dict

##########################################################################################################
    def plot_diff_short(self, dict_st_in, dict_msgs):
        if not os.path.exists(self.base + "/compressed_data/images/"):
            os.makedirs(self.base + "/compressed_data/images/", exist_ok=True)
        path = self.base + "/compressed_data/images/"
        
        diff_protocols = self.diff_plot_config.get("protocols", self.protocols)
        diff_protocols_by_key = {p.get("key"): p for p in diff_protocols if p.get("key") is not None}
        
        # 1. Aggregate State Data
        dict_states_aggregated = {}
        ps_k_dict = {}
        threshlds, ground_T = set(), set()
        
        for root_name, data_list in dict_st_in.items():
            dict_states_aggregated[root_name] = {}
            for data_in in data_list: 
                for k0, s_data in data_in.items():
                    algo, arena, thr, gt, comm, ag, tm, hops, k_samp = k0[0], k0[1], k0[4], k0[5], k0[6], k0[7], k0[9], k0[10], k0[11]
                    threshlds.add(thr)
                    ground_T.add(gt)
                    p_key = self._identify_protocol_key_from_vars(algo, comm, tm, hops)
                    if not p_key: continue
                    if p_key == "P.1.1":
                        if ag not in ps_k_dict: ps_k_dict[ag] = set()
                        ps_k_dict[ag].add(float(k_samp))
                    key = (p_key, arena, ag, tm, gt, thr, str(k_samp))
                    dict_states_aggregated[root_name][key] = s_data[0]

        # 2. Aggregate Message Data
        dict_msgs_aggregated = {}
        for root_name, msgs_dct in dict_msgs.items():
            dict_msgs_aggregated[root_name] = {}
            for k, res in msgs_dct.items():
                if k[3] == "0.68;0.92":
                    arena, algo, thr, gt, comm, msg_hops, agents, k_samp, tm = k
                    p_key = self._identify_protocol_key_from_vars(algo, comm, tm, msg_hops)
                    if p_key == "P.1.1":
                        if agents not in ps_k_dict: ps_k_dict[agents] = set()
                        ps_k_dict[agents].add(float(k_samp))
                    key = (p_key, arena, agents, tm, str(k_samp))
                    dict_msgs_aggregated[root_name][key] = res

        threshlds = sorted(list(threshlds))
        gt_list = sorted(list(ground_T))
        gt_068_092 = next((g for g in gt_list if "0.68" in g and "0.92" in g and g.startswith("0.68")), gt_list[0] if len(gt_list) > 0 else None)
        gt_092_068 = next((g for g in gt_list if "0.92" in g and "0.68" in g and g.startswith("0.92")), gt_list[-1] if len(gt_list) > 1 else None)
        
        plot_cfg = self.plot_config.get("plots", {})
        raw_columns = plot_cfg.get("columns", [60, 120, 180, 300, 600])
        main_tm_list = [str(c) for c in self._plot_columns(raw_columns)]
        
        insert_raw = plot_cfg.get("insert", [])
        insert_tm_list = []
        for v in insert_raw:
            try: insert_tm_list.append(str(int(v)))
            except ValueError: pass
        
        combined_tm = sorted(list(set(main_tm_list) | set(insert_tm_list)))
        if not combined_tm:
            return

        cNorm = colors.Normalize(vmin=0, vmax=5)
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        cols_config = [
            {"label": "LD25", "msg_arena": "big", "st_arena": "bigA", "agents": "25"},
            {"label": "HD25", "msg_arena": "small", "st_arena": "smallA", "agents": "25"},
            {"label": "HD100", "msg_arena": "big", "st_arena": "bigA", "agents": "100"}
        ]
        
        for thr in threshlds:
            # Create the 3x3 layout (Row 0: Messages, Row 1 & 2: States)
            fig, ax = plt.subplots(3, 3, figsize=(24, 18), constrained_layout=True, squeeze=False)
            inset_axes_dict = {}
            used_protocols = set()
            used_roots = {}
            
            for col_idx, col_cfg in enumerate(cols_config):
                ax[0][col_idx].set_title(col_cfg["label"])
                min_buf_drawn = False
                
                # --- MESSAGES LOGIC (ROW 0) ---
                for root_name, msgs_dct in dict_msgs_aggregated.items():
                    folder_cfg = self._get_diff_folder_cfg(root_name)
                    l_style = folder_cfg.get("line_style", "-")
                    l_label = folder_cfg.get("label", str(root_name) if root_name else "default")
                    
                    for key, res in msgs_dct.items():
                        p_key, msg_arena, msg_agents, msg_tm, k_samp = key
                        if msg_arena != col_cfg["msg_arena"] or msg_agents != col_cfg["agents"]: continue
                        
                        is_p0 = (p_key == "P.0")
                        is_main = str(msg_tm) in main_tm_list or is_p0
                        is_insert = str(msg_tm) in insert_tm_list or (is_p0 and insert_tm_list)
                        
                        if not (is_main or is_insert): continue
                        
                        if p_key and self._protocol_enabled_diff(p_key, root_name, diff_protocols_by_key):
                            used_protocols.add(p_key)
                            if root_name not in used_roots: used_roots[root_name] = (l_label, l_style)
                            
                            try:
                                norm = int(msg_agents) - 1
                                if norm <= 0: norm = 1
                                norm_data = [xi / norm for xi in res]
                            except: continue
                            
                            c = self._protocol_color_with_k(p_key, k_samp, msg_agents, ps_k_dict, scalarMap)
                            targets = []
                            
                            if is_main:
                                targets.append(ax[0][col_idx])
                                if not min_buf_drawn:
                                    ax[0][col_idx].plot([5/norm]*1200, color="black", lw=4, ls=":")
                                    min_buf_drawn = True
                                    
                            if is_insert:
                                if (0, col_idx) not in inset_axes_dict:
                                    best_box = [0.62, 0.03, 0.35, 0.35]
                                    ins_ax = ax[0][col_idx].inset_axes(best_box)
                                    ins_ax.set_xlim(0, 1201)
                                    ins_ax.set_ylim(-0.03, 1.03)
                                    ins_ax.set_xticks([0, 300, 600, 900, 1200])
                                    ins_ax.tick_params(labelbottom=False, labelleft=False)
                                    ins_ax.grid(True, ls=':', color='silver')
                                    ins_ax.plot([5 / norm] * 1200, color="black", ls=':', lw=3)
                                    inset_axes_dict[(0, col_idx)] = ins_ax
                                targets.append(inset_axes_dict[(0, col_idx)])
                            
                            for t_ax in targets:
                                t_ax.plot(norm_data, color=c, lw=4, linestyle=l_style, alpha=0.9)

                # --- STATE LOGIC (ROWS 1 and 2) ---
                for row_idx, gt_val in enumerate([gt_068_092, gt_092_068], start=1):
                    if not gt_val: continue
                    for root_name, st_dct in dict_states_aggregated.items():
                        folder_cfg = self._get_diff_folder_cfg(root_name)
                        l_style = folder_cfg.get("line_style", "-")
                        l_label = folder_cfg.get("label", str(root_name) if root_name else "default")
                        
                        for key, s_data in st_dct.items():
                            p_key, st_arena, st_agents, st_tm, st_gt, st_thr, k_samp = key
                            if st_arena != col_cfg["st_arena"] or st_agents != col_cfg["agents"]: continue
                            if st_gt != gt_val or st_thr != thr: continue
                            
                            is_p0 = (p_key == "P.0")
                            is_main = str(st_tm) in main_tm_list or is_p0
                            is_insert = str(st_tm) in insert_tm_list or (is_p0 and insert_tm_list)
                            
                            if not (is_main or is_insert): continue
                            
                            if p_key and self._protocol_enabled_diff(p_key, root_name, diff_protocols_by_key):
                                used_protocols.add(p_key)
                                if root_name not in used_roots: used_roots[root_name] = (l_label, l_style)
                                
                                c = self._protocol_color_with_k(p_key, k_samp, st_agents, ps_k_dict, scalarMap)
                                targets = []
                                
                                if is_main:
                                    targets.append(ax[row_idx][col_idx])
                                    
                                if is_insert:
                                    if (row_idx, col_idx) not in inset_axes_dict:
                                        best_box = self.find_emptiest_inset_position(ax[row_idx][col_idx]) if row_idx<2 else [1.0 - 0.35 - 0.03, 1.0 - 0.35 - 0.03, 0.35, 0.35]
                                        ins_ax = ax[row_idx][col_idx].inset_axes(best_box)
                                        ins_ax.set_xlim(0, 1201)
                                        ins_ax.set_ylim(-0.03, 1.03)
                                        ins_ax.set_xticks([0, 300, 600, 900, 1200])
                                        ins_ax.tick_params(labelbottom=False, labelleft=False)
                                        ins_ax.grid(True, ls=':', color='silver')
                                        inset_axes_dict[(row_idx, col_idx)] = ins_ax
                                    targets.append(inset_axes_dict[(row_idx, col_idx)])
                                    
                                for t_ax in targets:
                                    t_ax.plot(s_data, color=c, lw=4, linestyle=l_style, alpha=0.9)

            # --- APPLY STYLE ---
            for i in range(3):
                for j in range(3):
                    ax[i][j].grid(True)
                    ax[i][j].set_xlim(0, 1201)
                    ax[i][j].set_ylim(-0.03, 1.03)
                    ax[i][j].set_xticks([0, 300, 600, 900, 1200])
                    if i < 2: ax[i][j].set_xticklabels([])
                    else: ax[i][j].set_xlabel(r"$T$")
                    if j > 0: ax[i][j].set_yticklabels([])
            
            ax[0][0].set_ylabel(r"$M$")
            ax[1][0].set_ylabel(r"$Q(G,\tau)$")
            ax[2][0].set_ylabel(r"$Q(G,\tau)$")
            
            # Add GT info as labels to the rightmost axes
            if gt_068_092:
                ax_right1 = ax[1][2].twinx()
                ax_right1.set_yticks([])
                lab1 = str(gt_068_092).split(";")[0]+"."+str(gt_068_092).split(";")[1]+r' \rightarrow '+str(gt_068_092).split(";")[2]+"."+str(gt_068_092).split(";")[3]
                ax_right1.set_ylabel(r"$G: " + lab1 + r"$", rotation=270, labelpad=30)
                
            if gt_092_068:
                ax_right2 = ax[2][2].twinx()
                ax_right2.set_yticks([])
                lab2 = str(gt_092_068).split(";")[0]+"."+str(gt_092_068).split(";")[1]+r' \rightarrow '+str(gt_092_068).split(";")[2]+"."+str(gt_092_068).split(";")[3]
                ax_right2.set_ylabel(r"$G: " + lab2 + r"$", rotation=270, labelpad=30)
                
            # Build Combined Legend Handles
            handles_r = []
            handles_r.append(mlines.Line2D([], [], color="black", linestyle=':', linewidth=4, label=r"$\min|\mathcal{B}|$"))
            for r_name, (r_label, r_style) in used_roots.items():
                handles_r.append(mlines.Line2D([], [], color='black', linestyle=r_style, lw=3, label=r_label))
            
            for p in diff_protocols:
                pk = p.get("key")
                if pk in used_protocols and p.get("legend", True):
                    lbl = p.get("label", pk)
                    handles_r.append(mlines.Line2D([], [], color=self._protocol_color(p, scalarMap), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=lbl))
            
            handler_map = {Rectangle: GradientHandler(plt.cm.Greys_r)}
            fig.legend(handles=handles_r, handler_map=handler_map, loc='lower center', bbox_to_anchor=(0.6, -0.05), framealpha=0.7, fontsize=24, ncol=7)
            
            # Save the final consolidated file
            fig.savefig(f"{path}{thr}_diff_short_grid.pdf", bbox_inches='tight')
            plt.close(fig)

##########################################################################################################
    def plot_short(self, tot_st, tot_msgs):
        if not os.path.exists(self.base + "/compressed_data/images/"):
            os.makedirs(self.base + "/compressed_data/images/", exist_ok=True)
        path = self.base + "/compressed_data/images/"
        
        msgs_dict, st_dict, ps_k_dict = self._extract_short_data(tot_st, tot_msgs)
        
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
            if p_key in ("P.0", "P.1.1"):
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
            fig, ax = plt.subplots(2, 3, figsize=(24, 12), constrained_layout=True, squeeze=False)
            inset_axes_dict = {}
            
            for col_idx, col_cfg in enumerate(cols_config):
                ax[0][col_idx].set_title(col_cfg["label"])
                min_buf_drawn = False
                
                # --- STATE LOGIC ---
                for row_idx, gt_val in enumerate([gt_068_092, gt_092_068], start=0):
                    if not gt_val: continue
                    for p in self.protocols:
                        p_key = p.get("key")
                        if not self._protocol_enabled(p_key): continue
                        
                        unique_k_samps = set(k[6] for k in st_dict.keys() if k[0] == p_key and k[1] == col_cfg["st_arena"] and k[2] == col_cfg["agents"])
                        if not unique_k_samps: unique_k_samps = ["0"]
                        unique_k_samps = sorted(list(unique_k_samps), key=lambda x: float(x))

                        for k_samp in unique_k_samps:
                            base_color = self._protocol_color_with_k(p_key, k_samp, col_cfg["agents"], ps_k_dict, scalarMap)
                            is_p0 = (p_key == "P.0")
                            tms_to_iterate = ["60"] if is_p0 else combined_tm
                            
                            for tm in tms_to_iterate:
                                if is_p0:
                                    is_main = True
                                    is_insert = bool(insert_tm_list)
                                else:
                                    is_main = tm in main_tm_list
                                    is_insert = tm in insert_tm_list
                                    if not (is_main or is_insert): continue
                                
                                s_data = st_dict.get((p_key, col_cfg["st_arena"], col_cfg["agents"], str(tm), gt_val, thr, k_samp))
                                if not s_data and is_p0:
                                    s_data = st_dict.get((p_key, col_cfg["st_arena"], col_cfg["agents"], "60", gt_val, thr, k_samp))
                                    if not s_data:
                                        s_data = st_dict.get((p_key, col_cfg["st_arena"], col_cfg["agents"], "0", gt_val, thr, k_samp))
                                
                                if s_data is not None:
                                    c = tm_color(base_color, tm, p_key)
                                    targets = []
                                    if is_main:
                                        targets.append(ax[row_idx][col_idx])
                                    if is_insert:
                                        if (row_idx, col_idx) not in inset_axes_dict:
                                            if row_idx == 1:
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
                                    
            for i in range(2):
                for j in range(3):
                    ax[i][j].grid(True)
                    ax[i][j].set_xlim(0, 1201)
                    ax[i][j].set_ylim(-0.03, 1.03)
                    ax[i][j].set_xticks([0, 300, 600, 900, 1200])
                    if i < 1:
                        ax[i][j].set_xticklabels([])
                    else:
                        ax[i][j].set_xlabel(r"$T$")
                    if j > 0:
                        ax[i][j].set_yticklabels([])
            
            ax[0][0].set_ylabel(r"$Q(G,\tau)$")
            ax[1][0].set_ylabel(r"$Q(G,\tau)$")
            
            ax_right1 = ax[0][2].twinx()
            ax_right1.set_yticks([])
            lab1 = str(gt_068_092).split(";")[0]+"."+str(gt_068_092).split(";")[1]+r' \rightarrow '+str(gt_068_092).split(";")[2]+"."+str(gt_068_092).split(";")[3]
            ax_right1.set_ylabel(r"$G: " + lab1 + r"$", rotation=270, labelpad=30)
            
            ax_right2 = ax[1][2].twinx()
            ax_right2.set_yticks([])
            lab2 = str(gt_092_068).split(";")[0]+"."+str(gt_092_068).split(";")[1]+r' \rightarrow '+str(gt_092_068).split(";")[2]+"."+str(gt_092_068).split(";")[3]
            ax_right2.set_ylabel(r"$G: " + lab2 + r"$", rotation=270, labelpad=30)
            
            handles_l = []
            handles_r = []

            for p in self.protocols:
                p_key = p.get("key")
                if self._protocol_enabled(p_key) and p.get("legend", True):
                    color = self._protocol_color(p, scalarMap)
                    handles_r.append(mlines.Line2D([], [], color=color, marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", p_key)))
                    
            legend_elements = handles_l + handles_r
            handler_map = {Rectangle: GradientHandler(plt.cm.Greys_r)}
            
            fig.legend(handles=legend_elements, handler_map=handler_map, loc='lower center', bbox_to_anchor=(0.68, -0.08), framealpha=0.7, fontsize=24, ncol=7)
            fig.savefig(f"{path}{thr}_short_grid.pdf", bbox_inches='tight')
            plt.close(fig)

##########################################################################################################
    def _apply_plot_style(self, ax, nrows, rows, is_messages=False):
        for x in range(nrows):
            for y in range(3):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0, 1201)
                ax[x][y].set_ylim(-0.03, 1.03)
                if y == 0:
                    ax[x][y].set_ylabel(r"$M$" if is_messages else r"$Q(G,\tau)$")
                else:
                    ax[x][y].set_yticklabels([])
                if x == nrows - 1:
                    ax[x][y].set_xlabel(r"$T$")
                    ax[x][y].set_xticks([0, 300, 600, 900, 1200])
                    ax[x][y].set_xticklabels(["0", "300", "600", "900", "1200"])
                else:
                    ax[x][y].set_xticklabels([])
                if y == 2:
                    axt = ax[x][y].twinx()
                    axt.set_yticks([])
                    axt.set_ylabel(rf"$T_m = {int(rows[x])}\, s$", rotation=270, labelpad=30)
        labels = ["LD25", "HD25", "HD100"]
        for col in range(3):
            ax_right = ax[0][col].twiny()
            ax_right.set_xticks([])
            ax_right.set_xlabel(labels[col])

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
        
        ps_k_dict = {}
        for msgs_dct in dict_msgs.values():
            for k in msgs_dct.keys():
                if k[3] == "0.68;0.92":
                    arena, algo, thr, gt, comm, msg_hops, agents, k_samp, tm = k
                    p_key = self._identify_protocol_key_from_vars(algo, comm, tm, msg_hops)
                    if p_key == "P.1.1":
                        if agents not in ps_k_dict: ps_k_dict[agents] = set()
                        ps_k_dict[agents].add(float(k_samp))

        all_cols = set()
        for msgs_dct in dict_msgs.values():
            for k in msgs_dct.keys():
                if k[3] == "0.68;0.92":
                    try: all_cols.add(int(k[-1]))
                    except: continue
        
        columns = self._plot_columns(sorted(list(all_cols)))
        col_index = {str(c): i for i, c in enumerate(columns)}
        nrows = len(columns)

        svoid_x_ticks, void_x_ticks, real_x_ticks = [], [], []
        for x in range(0, 1201, 50):
            if x % 300 == 0:
                svoid_x_ticks.append(''); void_x_ticks.append('')
                real_x_ticks.append(str(int(np.round(x, 0))))
            else:
                void_x_ticks.append('')

        fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6.0 * nrows), squeeze=False, layout="constrained")
        min_buf_line = np.zeros((nrows, 3), int)
        used_protocols = set()
        used_roots = {}

        items_to_plot = []
        for root_name, msgs_dct in dict_msgs.items():
            folder_cfg = self._get_diff_folder_cfg(root_name)
            l_style = folder_cfg.get("line_style", "-")
            l_label = folder_cfg.get("label", str(root_name) if root_name else "default")
            
            for k, res in msgs_dct.items():
                if k[3] != "0.68;0.92": continue
                if str(k[-1]) not in col_index: continue
                items_to_plot.append((root_name, k, res, l_style, l_label))
                
        # Z-order sorting
        items_to_plot.sort(key=lambda x: float(x[1][7]))

        for root_name, k, res, l_style, l_label in items_to_plot:
            arena, algo, thr, gt, comm, msg_hops, agents, k_samp, tm = k
            p_key = self._identify_protocol_key_from_vars(algo, comm, tm, msg_hops)

            if p_key and self._protocol_enabled_diff(p_key, root_name, diff_protocols_by_key):
                used_protocols.add(p_key)
                if root_name not in used_roots:
                    used_roots[root_name] = (l_label, l_style)

                try:
                    norm = int(agents) - 1
                    if norm <= 0: norm = 1
                    norm_data = [xi / norm for xi in res]
                except: continue
                
                col = 0
                if arena == 'big' and str(agents) == '25': col = 0
                elif arena == 'small': col = 1
                elif arena == 'big' and str(agents) == '100': col = 2
                
                row = col_index[str(tm)]
                color = self._protocol_color_with_k(p_key, k_samp, agents, ps_k_dict, scalarMap)

                if min_buf_line[row][col] == 0:
                    ax[row][col].plot([5/norm]*1200, color="black", lw=4, ls=":")
                    min_buf_line[row][col] = 1
                ax[row][col].plot(norm_data, color=color, lw=6, linestyle=l_style)

        # Apply standardized style inline (mirrors print_messages logic)
        for x in range(nrows-1):
            for y in range(3):
                ax[x][y].set_xticks(np.arange(0, 1201, 300), labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0, 1201, 50), labels=void_x_ticks, minor=True)
        
        for x in range(nrows):
            for y in range(1,3):
                ax[x][y].set_yticklabels([''] * len(ax[x][y].get_yticklabels()))
                
        for idx, row_val in enumerate(columns):
            axt = ax[idx][2].twinx()
            axt.set_yticklabels([''] * len(axt.get_yticklabels()))
            axt.set_ylabel(rf"$T_m = {int(row_val)}\, s$",rotation=270,labelpad=30)
            ax[idx][0].set_ylabel(r"$M$")

        for r, lab in enumerate(["LD25", "HD25", "HD100"]):
            ayt = ax[0][r].twiny()
            ayt.set_xticklabels([''] * len(ayt.get_xticklabels()))
            ayt.set_xlabel(lab)

        for y in range(3):
            ax[nrows-1][y].set_xlabel(r"$T$")
            for x in range(nrows):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0, 1201)
                ax[x][y].set_ylim(-0.03, 1.03)

        handles_r = []
        handles_r.append(mlines.Line2D([], [], color="black", linestyle=':', linewidth=4, label=r"$\min|\mathcal{B}|$"))
        for r_name, (r_label, r_style) in used_roots.items():
            handles_r.append(mlines.Line2D([], [], color='black', linestyle=r_style, lw=3, label=r_label))
        for p in diff_protocols:
            pk = p.get("key")
            if pk in used_protocols and p.get("legend", True):
                lbl = p.get("label", pk)
                handles_r.append(mlines.Line2D([], [], color=self._protocol_color(p, scalarMap), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=lbl))
        
        if handles_r:
            handler_map = {Rectangle: GradientHandler(plt.cm.Greys_r)}
            fig.legend(handles=handles_r, handler_map=handler_map, ncols=7, loc='upper center', bbox_to_anchor=(0.6, -0.005), framealpha=0.7, fontsize=24)

        fig.savefig(path + "messages_diff.pdf", bbox_inches='tight')
        plt.close(fig)

##########################################################################################################
    def plot_messages(self, data):
        dict_msgs = {}
        ps_k_dict = {}
        
        for k, res in data.items():
            if k[3] == "0.68;0.92":
                arena, algo, thr, gt, comm, msg_hops, agents, k_samp, tm = k
                p_key = self._identify_protocol_key_from_vars(algo, comm, tm, msg_hops)
                if not p_key: continue
                if p_key == "P.1.1":
                    if agents not in ps_k_dict: ps_k_dict[agents] = set()
                    ps_k_dict[agents].add(float(k_samp))
                key = (p_key, arena, agents, tm, str(k_samp))
                dict_msgs[key] = res

        self.print_messages(dict_msgs, ps_k_dict)

##########################################################################################################
    def print_evolutions_diff(self, path, ground_T, threshlds, dict_states, o_k, more_k, ps_k_dict):
        diff_protocols = self.diff_plot_config.get("protocols", self.protocols)
        diff_protocols_by_key = {p.get("key"): p for p in diff_protocols if p.get("key") is not None}

        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        columns = self._plot_columns(o_k)
        col_index = {str(c): i for i, c in enumerate(columns)}
        nrows = len(columns)

        for gt in ground_T:
            for thr in threshlds:
                fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6.0 * nrows), squeeze=False, layout="constrained")
                
                used_protocol_keys = set()
                used_roots = {}

                items_to_plot = []
                for root_name, dict_st_root in dict_states.items():
                    folder_cfg = self._get_diff_folder_cfg(root_name)
                    l_style = folder_cfg.get("line_style", "-")
                    l_label = folder_cfg.get("label", str(root_name) if root_name else "default")
                    
                    for key, s_data in dict_st_root.items():
                        p_key, k_arena, k_agents, k_tm, k_gt, k_thr, k_samp = key
                        if k_gt != gt or k_thr != thr:
                            continue
                        items_to_plot.append((root_name, key, s_data, l_style, l_label))
                        
                # Z-order sorting
                items_to_plot.sort(key=lambda x: float(x[1][6]))

                for root_name, key, s_data, l_style, l_label in items_to_plot:
                    p_key, k_arena, k_agents, k_tm, k_gt, k_thr, k_samp = key
                    
                    col = 0
                    if k_arena == "smallA": col = 1
                    elif k_agents == "100": col = 2
                    
                    if str(k_tm) not in col_index: continue
                    row = col_index[str(k_tm)]

                    if self._protocol_enabled_diff(p_key, root_name, diff_protocols_by_key):
                        color = self._protocol_color_with_k(p_key, k_samp, k_agents, ps_k_dict, scalarMap)
                        ax[row][col].plot(s_data, color=color, lw=4, linestyle=l_style)
                        
                        used_protocol_keys.add(p_key)
                        if root_name not in used_roots:
                            used_roots[root_name] = (l_label, l_style)

                self._apply_plot_style(ax, nrows, columns, is_messages=False)
                
                handles_r = []
                
                for r_name, (r_label, r_style) in used_roots.items():
                    handles_r.append(mlines.Line2D([], [], color='black', linestyle=r_style, lw=2, label=r_label))
                for p in diff_protocols:
                    pk = p.get("key")
                    if pk in used_protocol_keys and p.get("legend", True):
                        handles_r.append(mlines.Line2D([], [], color=self._protocol_color(p, scalarMap), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", pk)))

                if handles_r:
                    handler_map = {Rectangle: GradientHandler(plt.cm.Greys_r)}
                    fig.legend(handles=handles_r, handler_map=handler_map, ncols=6, loc='upper center', bbox_to_anchor=(0.66, 0.005), framealpha=0.7, fontsize=24)
                
                fig.savefig(f"{path}{thr}_{gt.replace(';','_')}_diff_activation.pdf", bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def plot_active_w_gt_thr_diff(self, dict_st_in, dict_times):
        if not os.path.exists(self.base + "/proc_data/images/"):
            os.makedirs(self.base + "/proc_data/images/", exist_ok=True)
        path = self.base + "/proc_data/images/"
        
        ground_T, threshlds, o_k = set(), set(), set()
        arenas, agents = set(), set()
        ps_k_dict = {}
        dict_states_aggregated = {}
        
        for root_name, data_list in dict_st_in.items():
            dict_states_aggregated[root_name] = {}
            for data_in in data_list: 
                for k0, s_data in data_in.items():
                    algo, arena, thr, gt, comm, ag, tm, hops, k_samp = k0[0], k0[1], k0[4], k0[5], k0[6], k0[7], k0[9], k0[10], k0[11]
                    arenas.add(arena)
                    threshlds.add(thr)
                    ground_T.add(gt)
                    agents.add(ag)
                    if int(tm) != 0: o_k.add(int(tm))
                    
                    p_key = self._identify_protocol_key_from_vars(algo, comm, tm, hops)
                    if not p_key: continue
                    if p_key == "P.1.1":
                        if ag not in ps_k_dict: ps_k_dict[ag] = set()
                        ps_k_dict[ag].add(float(k_samp))
                        
                    key = (p_key, arena, ag, tm, gt, thr, str(k_samp))
                    dict_states_aggregated[root_name][key] = s_data[0]

        ground_T = sorted(list(ground_T))
        threshlds = sorted(list(threshlds))
        o_k = sorted(list(o_k))
        more_k = [sorted(list(arenas)), sorted(list(agents))]

        self.print_evolutions_diff(path, ground_T, threshlds, dict_states_aggregated, o_k, more_k, ps_k_dict)

##########################################################################################################
    def read_msgs_csv(self, path):
        data = {}
        with open(path, newline='') as f:
            reader = csv.reader(f, delimiter='\t')
            headers = next(reader)
            for row in reader:
                if not row: continue
                data_val = dict(zip(headers, row[:-1])) 
                val = row[-1].replace('[', '').replace(']', '')
                array_val = [float(x) for x in val.split(',')] if val else []
                
                key_tuple = (
                    data_val.get("ArenaSize", "big"),
                    data_val.get("algo", "P"),
                    data_val.get("threshold", "0.8"),
                    data_val.get("delta_GT", "0.68;0.92"),
                    data_val.get("broadcast", "1"),
                    data_val.get("msg_hops", "0"),
                    data_val.get("n_agents", "25"),
                    data_val.get("k_sampling", "0"),
                    data_val.get("buff_dim", "60")  
                )
                data[key_tuple] = array_val
        return data

##########################################################################################################
    def read_csv(self, path, algo, n_runs, arena):
        data = {}
        with open(path, newline='') as f:
            reader = csv.reader(f, delimiter='\t')
            headers = next(reader)
            for row in reader:
                if not row: continue
                data_val = {}
                array_val = []
                std_val = []
                for i, h in enumerate(headers):
                    if i >= len(row): continue
                    val = row[i]
                    if h == 'data':
                        val = val.replace('[', '').replace(']', '')
                        array_val = [float(x) for x in val.split(',')] if val else []
                    elif h == 'std':
                        if val == '-':
                            std_val = [-1.0] * len(array_val)
                        else:
                            val = val.replace('[', '').replace(']', '')
                            std_val = [float(x) for x in val.split(',')] if val else []
                    else:
                        data_val[h] = val
                        
                key_tuple = (
                    algo,
                    arena,
                    str(n_runs),
                    data_val.get("ExperimentLength", "1200"),
                    data_val.get("Threshold", "0.8"),
                    data_val.get("GT", "0.68;0.92").replace('_', ';'), 
                    data_val.get("Rebroadcast", "1"),
                    data_val.get("Robots", "25"),
                    data_val.get("MinBuffDim", "5"),
                    data_val.get("MsgExpTime", "60"),
                    data_val.get("MsgHops", "0"),
                    data_val.get("KSampling", "0"),
                    data_val.get("type", "swarm_state")
                )
                data[key_tuple] = (array_val, std_val)
        return data

##########################################################################################################
    def divide_data(self, data):
        states, times = {}, {}
        algorithm, arena_size, n_runs, exp_time, thrlds, gt, communication, n_agents, min_buff_dim, msg_time, msg_hops, k_sampling = [],[],[],[],[],[],[],[],[],[],[],[]
        
        for k in data.keys():
            algo, arena, runs, et, thr, gt_val, comm, agents, buf_dim, tm, hops, k_samp, dtype = k
            if algo not in algorithm: algorithm.append(algo)
            if arena not in arena_size: arena_size.append(arena)
            if runs not in n_runs: n_runs.append(runs)
            if et not in exp_time: exp_time.append(et)
            if thr not in thrlds: thrlds.append(thr)
            if gt_val not in gt: gt.append(gt_val)
            if comm not in communication: communication.append(comm)
            if agents not in n_agents: n_agents.append(agents)
            if buf_dim not in min_buff_dim: min_buff_dim.append(buf_dim)
            if tm not in msg_time: msg_time.append(tm)
            if hops not in msg_hops: msg_hops.append(hops)
            if k_samp not in k_sampling: k_sampling.append(k_samp)
            
            if dtype == "times":
                times[k[:-1]] = data[k]
            elif dtype == "swarm_state":
                states[k[:-1]] = data[k]
        
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops, k_sampling), states, times
    
##########################################################################################################
    def plot_active_w_gt_thr(self, data_in, times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.makedirs(self.base+"/proc_data/images/", exist_ok=True)
        path = self.base+"/proc_data/images/"
        
        dict_states = {}
        dict_times = {}
        ps_k_dict = {}
        ground_T, threshlds, o_k = set(), set(), set()
        arenas, agents = set(), set()

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
            for k0, s_data in data_in[i].items():
                t_data = times[i].get(k0)
                algo, arena, thr, gt, comm, ag, tm, hops, k_samp = k0[0], k0[1], k0[4], k0[5], k0[6], k0[7], k0[9], k0[10], k0[11]
                
                arenas.add(arena)
                threshlds.add(thr)
                ground_T.add(gt)
                agents.add(ag)
                if int(tm) != 0: o_k.add(int(tm))
                
                p_key = self._identify_protocol_key_from_vars(algo, comm, tm, hops)
                if not p_key: continue
                
                if p_key == "P.1.1":
                    if ag not in ps_k_dict: ps_k_dict[ag] = set()
                    ps_k_dict[ag].add(float(k_samp))
                
                key = (p_key, arena, ag, tm, gt, thr, str(k_samp))
                add_or_merge(dict_states, key, s_data[0])
                if t_data:
                    add_or_merge(dict_times, key, t_data[0])

        ground_T = sorted(list(ground_T))
        threshlds = sorted(list(threshlds))
        o_k = sorted(list(o_k))
        more_k = [sorted(list(arenas)), sorted(list(agents))]

        self.print_evolutions(path, ground_T, threshlds, dict_states, dict_times, o_k, more_k, ps_k_dict)

##########################################################################################################
    def print_evolutions(self, path, ground_T, threshlds, dict_states, times_in, keys, more_k, ps_k_dict):
        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        o_k = sorted(set([int(x) for x in keys]))
        rows = self._plot_columns(o_k)
        row_index = {str(c): i for i, c in enumerate(rows)}
        nrows = len(rows)
        arena = more_k[0]
        agents_list = more_k[1]

        for gt in ground_T:
            for thr in threshlds:
                fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6*nrows), squeeze=False, layout="constrained")
                used_protocols = set()

                for a in arena:
                    for ag in agents_list:
                        col = 1 if a == "smallA" else (2 if int(ag) == 100 else 0)
                        
                        items_to_plot = []
                        for key, s_data in dict_states.items():
                            p_key, k_arena, k_agents, k_tm, k_gt, k_thr, k_samp = key
                            if k_arena != a or k_agents != ag or k_gt != gt or k_thr != thr:
                                continue
                            items_to_plot.append((key, s_data))
                            
                        # Z-order sorting
                        items_to_plot.sort(key=lambda x: float(x[0][6]))
                        
                        for key, s_data in items_to_plot:
                            p_key, k_arena, k_agents, k_tm, k_gt, k_thr, k_samp = key
                            if not self._protocol_enabled(p_key): continue
                            
                            if p_key == "P.0":
                                for row in range(nrows):
                                    color = self._protocol_color_with_k(p_key, k_samp, ag, ps_k_dict, scalarMap)
                                    ax[row][col].plot(s_data, color=color, lw=6)
                                    used_protocols.add(p_key)
                            else:
                                if str(k_tm) not in row_index: continue
                                row = row_index[str(k_tm)]
                                color = self._protocol_color_with_k(p_key, k_samp, ag, ps_k_dict, scalarMap)
                                ax[row][col].plot(s_data, color=color, lw=6)
                                used_protocols.add(p_key)

                self._apply_plot_style(ax, nrows, rows, is_messages=False)

                handles_r = []
                for p in self.protocols:
                    pk = p.get("key")
                    if pk in used_protocols and p.get("legend", True):
                        handles_r.append(mlines.Line2D([], [], color=self._protocol_color(p, scalarMap), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", pk)))

                if handles_r:
                    fig.legend(handles=handles_r, ncols=6, loc='upper center', bbox_to_anchor=(0.68, 0.0), framealpha=0.7, fontsize=24)
                
                fig.savefig(f"{path}{thr}_{gt.replace(';','_')}_activation.pdf", bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_messages(self, dict_msgs, ps_k_dict):
        typo = [0, 1, 2, 3, 4, 5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        used_protocols = set()
        all_cols = set()
        for k in dict_msgs.keys():
            try: all_cols.add(int(k[3]))
            except Exception: continue
        
        default_rows = sorted(all_cols) if all_cols else [60, 120, 180, 300, 600]
        rows = self._plot_columns(default_rows)
        rows = [c for c in rows if c in default_rows]
        if not rows:
            rows = default_rows
        
        row_index = {str(c): i for i, c in enumerate(rows)}
        nrows = len(rows)

        svoid_x_ticks, void_x_ticks, real_x_ticks = [], [], []
        for x in range(0, 1201, 50):
            if x % 300 == 0:
                svoid_x_ticks.append(''); void_x_ticks.append('')
                real_x_ticks.append(str(int(np.round(x, 0))))
            else:
                void_x_ticks.append('')

        size_per_plot = 6.0
        min_buf_line = np.zeros((nrows,3), int)
        fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, size_per_plot * nrows), squeeze=False, layout="constrained")

        items_to_plot = []
        for key, raw_data in dict_msgs.items():
            items_to_plot.append((key, raw_data))
            
        # Z-order sorting
        items_to_plot.sort(key=lambda x: float(x[0][4]))

        for key, raw_data in items_to_plot:
            p_key, arena, agents, tm, k_samp = key
            if not self._protocol_enabled(p_key): continue
            
            if arena == 'big' and agents == '25': col = 0
            elif arena == 'small' and agents == '25': col = 1
            elif arena == 'big' and agents == '100': col = 2
            else: continue
            
            norm = int(agents) - 1
            if norm <= 0: norm = 1
            data = [xi / norm for xi in raw_data]
            
            color = self._protocol_color_with_k(p_key, k_samp, agents, ps_k_dict, scalarMap)
            used_protocols.add(p_key)

            if p_key == "P.0":
                for row in range(nrows):
                    if min_buf_line[row][col] == 0:
                        val = 5 / norm
                        ax[row][col].plot([val]*1200, color="black", lw=4, ls=":")
                        min_buf_line[row][col] = 1
                    ax[row][col].plot(data, color=color, lw=6)
            else:
                if str(tm) not in row_index: continue
                row = row_index[str(tm)]
                if min_buf_line[row][col] == 0:
                    val = 5 / norm
                    ax[row][col].plot([val]*1200, color="black", lw=4, ls=":")
                    min_buf_line[row][col] = 1
                ax[row][col].plot(data, color=color, lw=6)

        for x in range(nrows-1):
            for y in range(3):
                ax[x][y].set_xticks(np.arange(0, 1201, 300), labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0, 1201, 50), labels=void_x_ticks, minor=True)
        
        for x in range(nrows):
            for y in range(1,3):
                ax[x][y].set_yticklabels([''] * len(ax[x][y].get_yticklabels()))
                
        for idx, row_val in enumerate(rows):
            axt = ax[idx][2].twinx()
            axt.set_yticklabels([''] * len(axt.get_yticklabels()))
            axt.set_ylabel(rf"$T_m = {int(row_val)}\, s$",rotation=270,labelpad=30)
            ax[idx][0].set_ylabel(r"$M$")

        for r, lab in enumerate(["LD25", "HD25", "HD100"]):
            ayt = ax[0][r].twiny()
            ayt.set_xticklabels([''] * len(ayt.get_xticklabels()))
            ayt.set_xlabel(lab)

        for y in range(3):
            ax[nrows-1][y].set_xlabel(r"$T$")
            for x in range(nrows):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0, 1201)
                ax[x][y].set_ylim(-0.03, 1.03)

        handles_r = []

        for p in self.protocols:
            pk = p.get("key")
            if pk in used_protocols and p.get("legend", True):
                handles_r.append(mlines.Line2D([], [], color=self._protocol_color(p, scalarMap), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=p.get("label", pk)))

        if handles_r:
            handler_map = {Rectangle: GradientHandler(plt.cm.Greys_r)}
            fig.legend(handles=handles_r, handler_map=handler_map, ncols=6, loc='upper center', bbox_to_anchor=(0.66, 0.0), framealpha=0.7, fontsize=24)

        dest_dir = os.path.join(self.base, "msgs_data", "images")
        if not os.path.exists(dest_dir): os.makedirs(dest_dir)
        fig.savefig(os.path.join(dest_dir, "messages.pdf"), bbox_inches='tight')
        plt.close(fig)