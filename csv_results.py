import os, logging, re, json, colorsys
import numpy as np
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.legend_handler import HandlerBase

logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})

class HandlerKGrad(HandlerBase):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        n_steps = 5
        cmap = colors.LinearSegmentedColormap.from_list("grey_grad", ["#404040", "#D0D0D0"])
        artists = []
        step_width = width / n_steps
        for i in range(n_steps):
            color = cmap(i / (n_steps - 1))
            r = Rectangle((xdescent + i * step_width, ydescent), step_width, height, facecolor=color, edgecolor=color, transform=trans)
            artists.append(r)
        return artists

class Data:
    _FLOAT_RE = re.compile(r"(?i)(?:[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?|[-+]?inf|nan)")
    _NP_FLOAT_RE = re.compile(r"(?i)np\.float\d*\(([^)]+)\)")

##########################################################################################################
    @staticmethod
    def _parse_float_list(raw, allow_dash=False):
        raw = raw.strip()
        if allow_dash and raw == "-":
            return [-1.0]
        if "np.float" in raw:
            raw = Data._NP_FLOAT_RE.sub(r"\1", raw)
        if raw and raw[0] == "[" and raw[-1] == "]":
            raw = raw[1:-1]
        if "[" in raw or "]" in raw:
            raw = raw.replace("[", "").replace("]", "")
        if not raw:
            return []
        return [float(x) for x in Data._FLOAT_RE.findall(raw)]

##########################################################################################################
    def __init__(self, use_short=False) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "proc_data" or elem == "msgs_data":
                self.bases.append(os.path.join(self.base, elem))
        self.plot_config = self._load_plot_config(use_short)
        self.protocols = self.plot_config.get("protocols", [])
        self.protocols_by_id = {p.get("id"): p for p in self.protocols if p.get("id") is not None}
        self.k_samps_per_agent = {}

##########################################################################################################
    def _default_plot_config(self):
        return {
            "protocols": [
                {"id": "P.0", "label": r"$AN$", "color": "red"},
                {"id": "P.1.0", "label": r"$AN_{t}$", "color": "viridis:0"},
                {"id": "P.1.1", "label": r"$AN_{t}^{k}$", "color": "orange"},
                {"id": "O.0.0", "label": r"$ID+B$", "color": "viridis:1"},
                {"id": "O.2.0", "label": r"$ID+R_{f}$", "color": "viridis:2"},
                {"id": "O.1.1", "label": r"$ID+R_{1}$", "color": "viridis:3"},
                {"id": "O.1.0", "label": r"$ID+R_{\infty}$", "color": "viridis:4"},
            ],
            "plots": {"exclude_protocols": [], "exclude_tm": []},
        }

##########################################################################################################
    def _merge_plot_config(self, base_cfg, user_cfg):
        cfg = dict(base_cfg)
        cfg["plots"] = dict(base_cfg.get("plots", {}))
        if isinstance(user_cfg, dict):
            if "protocols" in user_cfg:
                cfg["protocols"] = user_cfg.get("protocols") or []
            if "plots" in user_cfg and isinstance(user_cfg.get("plots"), dict):
                cfg["plots"].update(user_cfg.get("plots"))
        return cfg

##########################################################################################################
    def _load_plot_config(self, use_short):
        cfg = self._default_plot_config()
        path = os.path.join(self.base, "plot_config.json")
        short_path = os.path.join(self.base, "short_plot_config.json")
        
        # ORA CARICA LO SHORT SOLO SE RICHIESTO ESPRESSAMENTE
        actual_path = short_path if use_short and os.path.exists(short_path) else path
        
        if not os.path.exists(actual_path):
            return cfg
        try:
            with open(actual_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Pulizia automatica di virgole di troppo per evitare crash del parser JSON
                content = re.sub(r',\s*}', '}', content)
                content = re.sub(r',\s*\]', ']', content)
                user_cfg = json.loads(content)
            return self._merge_plot_config(cfg, user_cfg)
        except Exception as exc:
            print(f"ATTENZIONE: Fallimento nel parsing del config ({actual_path}): {exc}")
            return cfg

##########################################################################################################
    def apply_plot_overrides(self, plot_names, exclude_protocols=None, exclude_tm=None):
        if not plot_names: return
        plot_cfg = self.plot_config.setdefault("plots", {})
        if exclude_protocols is not None:
            plot_cfg["exclude_protocols"] = exclude_protocols
        if exclude_tm is not None:
            plot_cfg["exclude_tm"] = exclude_tm

##########################################################################################################
    def _normalize_tm(self, val):
        if isinstance(val, bool): return None
        if isinstance(val, (int, np.integer)): return int(val)
        if isinstance(val, (float, np.floating)):
            if float(val).is_integer(): return int(val)
            return None
        if isinstance(val, str):
            try:
                f = float(val.strip())
                if f.is_integer(): return int(f)
            except ValueError:
                pass
        return None

##########################################################################################################
    def _plot_tm_values(self, values):
        plot_cfg = self.plot_config.get("plots", {})
        exclude = plot_cfg.get("exclude_tm") or []
        exclude_set = {self._normalize_tm(v) for v in exclude if self._normalize_tm(v) is not None}
        out = []
        for v in values:
            nv = self._normalize_tm(v)
            if nv is None or nv in exclude_set:
                continue
            out.append(nv)
        return out

##########################################################################################################
    def _protocol_matches(self, protocol, selector):
        if protocol is None or selector is None: return False
        sel = str(selector).strip()
        return sel == protocol.get("id") or sel == protocol.get("label")

##########################################################################################################
    def _protocol_enabled(self, protocol_id):
        protocol = self.protocols_by_id.get(protocol_id)
        plot_cfg = self.plot_config.get("plots", {})
        exclude = plot_cfg.get("exclude_protocols") or []
        return not any(self._protocol_matches(protocol, sel) for sel in exclude)

##########################################################################################################
    def _protocol_color(self, protocol, scalarMap):
        if protocol is None: return "black"
        color = protocol.get("color")
        if isinstance(color, str) and color.startswith("viridis:"):
            try: return scalarMap.to_rgba(int(color.split(":", 1)[1]))
            except Exception: return "black"
        return color if color else "black"

##########################################################################################################
    def _get_p11_color(self, k_val, ag):
        k_list = sorted(list(self.k_samps_per_agent.get(str(ag), [])))
        if not k_list or len(k_list) <= 1:
            return "orange"
        idx = k_list.index(k_val)
        cmap = colors.LinearSegmentedColormap.from_list("or_grad", ["#FF9100", "#FDCF72"])
        return cmap(idx / (len(k_list) - 1))

##########################################################################################################
    def _get_lines_to_plot(self, target_dict, pid, base_key, ag, protocol_colors):
        lines = []
        subdict = target_dict.get(pid, {})
        matches = [(k[-1], v) for k, v in subdict.items() if k[:-1] == base_key]
        matches.sort(key=lambda x: x[0])
        for k_val, data in matches:
            color = self._get_p11_color(k_val, ag) if pid == "P.1.1" else protocol_colors.get(pid, "black")
            lines.append((data, color))
        return lines

##########################################################################################################
    def _get_protocol_id(self, a, c, m_h):
        c_int = int(c)
        if a == 'P' and c_int == 0: return "P.1.0"
        if a == 'O':
            if c_int == 0: return "O.0.0"
            if c_int == 1:
                if m_h == "1": return "O.1.1"
                if m_h == "a31": return "adp_rnd"
                return "O.1.0"
            if c_int == 2: return "O.2.0"
        if a == 'Ps' and c_int == 0: return "P.1.1" 
        return None

##########################################################################################################
    def _get_row(self, arena, ag):
        ag = int(ag)
        if ag == 25:
            if arena in ["0_500;0_500", "1_000;0_250"]: return 1
            if arena in ["1_000;1_000", "2_000;0_500"]: return 0
        elif ag == 100:
            return 2
        return 0

##########################################################################################################
    def _cast_proc_key(self, k):
        return (
            str(k[0]),                  # a (algo)
            str(k[1]),                  # n_r
            str(k[2]),                  # et
            str(k[3]),                  # a_s (arena)
            int(float(k[4])),           # c (communication)
            int(float(k[5])),           # n_a (agents)
            float(k[6]),                # thr
            float(k[7]),                # gt
            str(k[8]),                  # m_h
            int(float(k[9])),           # m_t (tm)
            int(float(k[10]))           # k_samp
        )

##########################################################################################################
    def _cast_msg_key(self, k):
        return (
            str(k[0]),                  # a (arena)
            str(k[1]),                  # al (algo)
            float(k[2]),                # t (thr)
            float(k[3]),                # g (gt)
            int(float(k[4])),           # c (comm)
            int(float(k[5])),           # ag (agents)
            int(float(k[6])),           # b (tm)
            str(k[7]),                  # mh (msg_hop)
            int(float(k[8])),           # k_samp
            str(k[9])                   # gp (type)
        )

##########################################################################################################
    def read_msgs_csv(self, path):
        """PARSING DINAMICO INTELLIGENTE PER I MESSAGGI"""
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header: return data
            keys = header.rstrip('\n').split('\t')
            
            def get_idx(names, default=-1):
                for n in names:
                    if n in keys: return keys.index(n)
                return default
            
            idx_arena = get_idx(["ArenaSize", "Arena"], 0)
            idx_algo = get_idx(["algo"], 1)
            idx_thr = get_idx(["threshold", "Thr"], 2)
            idx_gt = get_idx(["GT", "Gt"], 3)
            idx_comm = get_idx(["broadcast", "Comm"], 4)
            idx_ag = get_idx(["n_agents", "Agents"], 5)
            # In old versions, buff_dim was used for Tm!
            idx_tm = get_idx(["buff_dim", "MsgExpTime", "msg_exp_time"], 6)
            idx_mh = get_idx(["msg_hops", "MsgH"], 7)
            idx_ks = get_idx(["k_sampling", "KSamp", "KSampling"], -1)
            idx_type = get_idx(["type"], 8)
            idx_data = get_idx(["data"], max(len(keys)-1, 0))

            for line in f:
                line = line.strip('\n')
                if not line: continue
                cols = line.split('\t')
                if len(cols) <= idx_data: continue
                
                c_arena = cols[idx_arena]
                c_algo = cols[idx_algo]
                c_thr = cols[idx_thr]
                c_gt = cols[idx_gt]
                c_comm = cols[idx_comm]
                c_ag = cols[idx_ag]
                c_tm = cols[idx_tm]
                c_mh = cols[idx_mh]
                c_ks = cols[idx_ks] if idx_ks != -1 and idx_ks < len(cols) else "0"
                c_type = cols[idx_type]
                
                key = (c_arena, c_algo, c_thr, c_gt, c_comm, c_ag, c_tm, c_mh, c_ks, c_type)
                data[key] = self._parse_float_list(cols[idx_data])
        return data

##########################################################################################################
    def read_csv(self, path, algo, n_runs):
        """PARSING DINAMICO INTELLIGENTE PER AVERAGE RESUME"""
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header: return data
            keys = header.rstrip('\n').split('\t')
            
            def get_idx(names, default=-1):
                for n in names:
                    if n in keys: return keys.index(n)
                return default
                
            idx_expl = get_idx(["ExpL", "exp_length"], 0)
            idx_arena = get_idx(["Arena", "ArenaSize"], 1)
            idx_comm = get_idx(["Comm", "communication"], 2)
            idx_ag = get_idx(["Agents", "n_agents"], 3)
            idx_thr = get_idx(["Thr", "threshold"], 4)
            idx_gt = get_idx(["Gt", "GT"], 5)
            idx_mh = get_idx(["MsgH", "msg_hops"], 6)
            idx_tm = get_idx(["MsgExpTime", "MsgExp"], 7)
            idx_ks = get_idx(["KSampling", "KSamp", "k_sampling"], -1)
            
            idx_type = get_idx(["type"], max(len(keys)-3, 0))
            idx_data = get_idx(["data"], max(len(keys)-2, 0))
            idx_std = get_idx(["std"], max(len(keys)-1, 0))

            for line in f:
                line = line.strip('\n')
                if not line: continue
                cols = line.split('\t')
                if len(cols) <= max(idx_type, idx_data, idx_std): continue
                
                c_expl = cols[idx_expl]
                c_arena = cols[idx_arena]
                c_comm = cols[idx_comm]
                c_ag = cols[idx_ag]
                c_thr = cols[idx_thr]
                c_gt = cols[idx_gt]
                c_mh = cols[idx_mh]
                c_tm = cols[idx_tm]
                c_ks = cols[idx_ks] if idx_ks != -1 and idx_ks < len(cols) else "0"
                c_type = cols[idx_type]
                
                key = (algo, n_runs, c_expl, c_arena, c_comm, c_ag, c_thr, c_gt, c_mh, c_tm, c_ks, c_type)
                data[key] = (self._parse_float_list(cols[idx_data]), self._parse_float_list(cols[idx_std], allow_dash=True))
        return data

##########################################################################################################
    def divide_data(self, data):
        states, comm_states, uncomm_states, times = {}, {}, {}, {}
        unique_vals = [set() for _ in range(11)]
        for k, v in data.items():
            for i in range(11): unique_vals[i].add(k[i])
            if k[-1] == "times": times[k[:-1]] = v
            elif k[-1] == "swarm_state": states[k[:-1]] = v
            elif k[-1] == "committed_state": comm_states[k[:-1]] = v
            elif k[-1] == "uncommitted_state": uncomm_states[k[:-1]] = v
        return tuple(list(s) for s in unique_vals), states, times, (comm_states, uncomm_states)

##########################################################################################################
    def plot_by_commit_w_gt_thr(self, data_in):
        path = os.path.join(self.base, "proc_data", "images") + "/"
        os.makedirs(path, exist_ok=True)
        
        sq_c, sq_u, rt_c, rt_u = {}, {}, {}, {}
        for d in [sq_c, sq_u, rt_c, rt_u]:
            for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]: d[pid] = {}

        ground_T, threshlds, msg_time, msg_hop = set(), set(), set(), set()
        arena, agents = set(), set()

        for comm_data_dict, uncomm_data_dict in data_in:
            for raw_k, comm_data in comm_data_dict.items():
                uncomm_data = uncomm_data_dict.get(raw_k)
                if not comm_data or not uncomm_data: continue
                
                a, n_r, et, a_s, c, n_a, thr, gt, m_h, m_t, k_val = self._cast_proc_key(raw_k)
                
                ground_T.add(gt); threshlds.add(thr); msg_time.add(m_t); msg_hop.add(m_h)
                arena.add(a_s); agents.add(n_a)

                pid = self._get_protocol_id(a, c, m_h)
                if pid:
                    if pid == "P.1.1":
                        if str(n_a) not in self.k_samps_per_agent: self.k_samps_per_agent[str(n_a)] = set()
                        self.k_samps_per_agent[str(n_a)].add(k_val)
                    is_sq = (a_s.split(';')[0] == a_s.split(';')[1])
                    (sq_c if is_sq else rt_c)[pid][(a_s, n_a, m_t, m_h, gt, thr, k_val)] = comm_data[0]
                    (sq_u if is_sq else rt_u)[pid][(a_s, n_a, m_t, m_h, gt, thr, k_val)] = uncomm_data[0]

        more_k = [["0_500;0_500","1_000;1_000","1_000;0_250","2_000;0_500"], sorted(list(agents))]
        self.print_evolutions_by_commit(path, sorted(list(ground_T)), sorted(list(threshlds)), 
                                        sq_c, sq_u, rt_c, rt_u, list(msg_time), more_k, sorted(list(msg_hop)))

##########################################################################################################
    def plot_active_w_gt_thr(self, data_in, times):
        path = os.path.join(self.base, "proc_data", "images") + "/"
        os.makedirs(path, exist_ok=True)

        sq_d, sq_t, rt_d, rt_t = {}, {}, {}, {}
        for d in [sq_d, sq_t, rt_d, rt_t]:
            for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]: d[pid] = {}

        ground_T, threshlds, msg_time, msg_hop = set(), set(), set(), set()
        arena, agents = set(), set()

        for idx, s_data_dict in enumerate(data_in):
            for raw_k, s_data in s_data_dict.items():
                t_data = times[idx].get(raw_k)
                if not s_data or not t_data: continue
                
                a, n_r, et, a_s, c, n_a, thr, gt, m_h, m_t, k_val = self._cast_proc_key(raw_k)

                ground_T.add(gt); threshlds.add(thr); msg_time.add(m_t); msg_hop.add(m_h)
                arena.add(a_s); agents.add(n_a)

                pid = self._get_protocol_id(a, c, m_h)
                if pid:
                    if pid == "P.1.1":
                        if str(n_a) not in self.k_samps_per_agent: self.k_samps_per_agent[str(n_a)] = set()
                        self.k_samps_per_agent[str(n_a)].add(k_val)
                    is_sq = (a_s.split(';')[0] == a_s.split(';')[1])
                    (sq_d if is_sq else rt_d)[pid][(a_s, n_a, m_t, m_h, gt, thr, k_val)] = s_data[0]
                    (sq_t if is_sq else rt_t)[pid][(a_s, n_a, m_t, m_h, gt, thr, k_val)] = t_data[0]

        more_k = [["0_500;0_500","1_000;1_000","1_000;0_250","2_000;0_500"], sorted(list(agents))]
        self.print_evolutions(path, sorted(list(ground_T)), sorted(list(threshlds)), 
                              sq_d, sq_t, rt_d, rt_t, list(msg_time), more_k, sorted(list(msg_hop)))

##########################################################################################################
    def plot_messages(self, data):
        sq_tot, rt_tot, sq_com, rt_com, sq_unc, rt_unc = [ {pid: {} for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]} for _ in range(6) ]
        arena, thr, gt, agents, buffer = set(), set(), set(), set(), set()

        for raw_k, s_data in data.items():
            a, al, t, g, c, ag, b, mh, k_val, gp = self._cast_msg_key(raw_k)
            
            arena.add(a); thr.add(t); gt.add(g); agents.add(ag); buffer.add(b)
            
            pid = self._get_protocol_id(al, c, mh)
            if pid:
                if pid == "P.1.1":
                    if str(ag) not in self.k_samps_per_agent: self.k_samps_per_agent[str(ag)] = set()
                    self.k_samps_per_agent[str(ag)].add(k_val)
                is_sq = (a.split(';')[0] == a.split(';')[1])
                target = sq_com if gp == "commit_average" and is_sq else \
                         rt_com if gp == "commit_average" and not is_sq else \
                         sq_unc if gp == "uncommit_average" and is_sq else \
                         rt_unc if gp == "uncommit_average" and not is_sq else \
                         sq_tot if is_sq else rt_tot
                target[pid][(a, t, g, ag, b, k_val)] = s_data

        keys_list = [sorted(list(x)) for x in (arena, thr, gt, agents, buffer)]
        self.print_messages("tot_average", sq_tot, rt_tot, keys_list)
        self.print_dif_messages("dif_commit_average", sq_com, sq_unc, rt_com, rt_unc, keys_list)

##########################################################################################################
    def print_evolutions_by_commit(self, path, ground_T, threshlds, sq_c, sq_u, rt_c, rt_u, keys, more_k, msg_hop):
        typo = [0,1,2,3,4,5]
        scalarMap = cmx.ScalarMappable(norm=colors.Normalize(vmin=typo[0], vmax=typo[-1]), cmap=plt.get_cmap('viridis'))
        
        o_k = self._plot_tm_values(sorted(list(keys)))
        if not o_k: return
        nrows = len(o_k) # Number of Tm values
        
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        handles_r = [mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=self.protocols_by_id[pid].get("label", pid)) for pid in protocols_order if self._protocol_enabled(pid)]
        handles_l = [mlines.Line2D([], [], color="black", linestyle='-', linewidth=6, label="LI"), mlines.Line2D([], [], color="black", linestyle='--', linewidth=6, label="SI")]
        
        handler_map = {}
        if self._protocol_enabled("P.1.1"):
            grad_rect_k = Rectangle((0, 0), 1, 1, label=r"$k$-sampling")
            handles_l.append(grad_rect_k)
            handler_map[grad_rect_k] = HandlerKGrad()
        legend_elements = handles_l + handles_r
        legend_cols = len(legend_elements) if len(legend_elements) < 6 else int(np.ceil(len(legend_elements)/2.0))
        
        real_x_ticks = [str(int(np.round(x,0))) if x%300==0 else '' for x in range(0,901,50)]
        svoid_x_ticks = ['' for x in range(0,901,50)]
        void_x_ticks = ['' for x in range(0,901,50)]
        void_y_ticks = ['' for _ in range(0,11,1)]

        for gt in ground_T:
            for thr in threshlds:
                cfig, cax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6*nrows), squeeze=False)
                ufig, uax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6*nrows), squeeze=False)
                for m_h in msg_hop:
                    for a in more_k[0]:
                        agents_list = [25] if a in ["0_500;0_500", "1_000;0_250"] else more_k[1]
                        for ag in agents_list:
                            col = self._get_row(a, ag) # Column corresponds to Scenario
                            for k_idx, tm in enumerate(o_k): # Row corresponds to Tm
                                for pid in protocols_order + ["adp_rnd"]:
                                    if pid != "adp_rnd" and not self._protocol_enabled(pid): continue
                                    
                                    base_key = (a, ag, tm, m_h, gt, thr)
                                    
                                    for target_ax, sq_dict, rt_dict in [(cax, sq_c, rt_c), (uax, sq_u, rt_u)]:
                                        lines_sq = self._get_lines_to_plot(sq_dict, pid, base_key, ag, protocol_colors)
                                        lines_rt = self._get_lines_to_plot(rt_dict, pid, base_key, ag, protocol_colors)
                                        
                                        for data, color in lines_sq: target_ax[k_idx][col].plot(data, color=color, lw=6, ls='-')
                                        for data, color in lines_rt: target_ax[k_idx][col].plot(data, color=color, lw=6, ls='--')

                                    cax[k_idx][col].set_xlim(0, 901); uax[k_idx][col].set_xlim(0, 901)
                                    cax[k_idx][col].set_ylim(-0.03, 1.03); uax[k_idx][col].set_ylim(-0.03, 1.03)

                                    if k_idx == 0: # Top Row: Show Scenario labels
                                        caxt, uaxt = cax[k_idx][col].twiny(), uax[k_idx][col].twiny()
                                        caxt.set_xticklabels(['']*len(caxt.get_xticklabels())); uaxt.set_xticklabels(['']*len(uaxt.get_xticklabels()))
                                        lbl = "LD25" if col == 0 else "HD25" if col == 1 else "HD100"
                                        caxt.set_xlabel(lbl); uaxt.set_xlabel(lbl)
                                    
                                    if k_idx == nrows - 1: # Bottom Row: Show X-axis labels
                                        cax[k_idx][col].set_xticks(np.arange(0,901,300), labels=real_x_ticks[::6]); cax[k_idx][col].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                                        uax[k_idx][col].set_xticks(np.arange(0,901,300), labels=real_x_ticks[::6]); uax[k_idx][col].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                                        cax[k_idx][col].set_xlabel(r"$T$"); uax[k_idx][col].set_xlabel(r"$T$")
                                    else:
                                        cax[k_idx][col].set_xticks(np.arange(0,901,300), labels=svoid_x_ticks[::6]); cax[k_idx][col].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                                        uax[k_idx][col].set_xticks(np.arange(0,901,300), labels=svoid_x_ticks[::6]); uax[k_idx][col].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                                    
                                    if col == 0: # Left Column: Show Y-axis labels
                                        cax[k_idx][col].set_yticks(np.arange(0,1.01,.1)); uax[k_idx][col].set_yticks(np.arange(0,1.01,.1))
                                        cax[k_idx][col].set_ylabel(r"$Q(G,\tau)$"); uax[k_idx][col].set_ylabel(r"$Q(G,\tau)$")
                                    
                                    elif col == 2: # Right Column: Show Tm labels
                                        cax[k_idx][col].set_yticks(np.arange(0,1.01,.1), labels=void_y_ticks); uax[k_idx][col].set_yticks(np.arange(0,1.01,.1), labels=void_y_ticks)
                                        caxt, uaxt = cax[k_idx][col].twinx(), uax[k_idx][col].twinx()
                                        caxt.set_yticklabels(['']*len(caxt.get_yticklabels())); uaxt.set_yticklabels(['']*len(uaxt.get_yticklabels()))
                                        caxt.set_ylabel(rf"$T_m = {tm}\, s$",rotation=270,labelpad=30); uaxt.set_ylabel(rf"$T_m = {tm}\, s$",rotation=270,labelpad=30)
                                    else:
                                        cax[k_idx][col].set_yticks(np.arange(0,1.01,.1), labels=void_y_ticks); uax[k_idx][col].set_yticks(np.arange(0,1.01,.1), labels=void_y_ticks)
                                    
                                    cax[k_idx][col].grid(True, which='major'); uax[k_idx][col].grid(True, which='major')

                cfig.tight_layout(); ufig.tight_layout()
                cfig.legend(bbox_to_anchor=(0.96, 0), handles=legend_elements, handler_map=handler_map, ncols=7, loc='upper right', framealpha=0.7, borderaxespad=0)
                ufig.legend(bbox_to_anchor=(0.96, 0), handles=legend_elements, handler_map=handler_map, ncols=7, loc='upper right', framealpha=0.7, borderaxespad=0)
                cfig.savefig(path + f"T{thr}_G{gt}_activation_committed.pdf", bbox_inches='tight')
                ufig.savefig(path + f"T{thr}_G{gt}_activation_uncommitted.pdf", bbox_inches='tight')
                plt.close(cfig); plt.close(ufig)

##########################################################################################################
    def print_evolutions(self, path, ground_T, threshlds, sq_d, sq_t, rt_d, rt_t, keys, more_k, msg_hop):
        typo = [0,1,2,3,4,5]
        scalarMap = cmx.ScalarMappable(norm=colors.Normalize(vmin=typo[0], vmax=typo[-1]), cmap=plt.get_cmap('viridis'))
        
        o_k = self._plot_tm_values(sorted(list(keys)))
        if not o_k: return
        nrows = len(o_k)

        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        handles_r = [mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=self.protocols_by_id[pid].get("label", pid)) for pid in protocols_order if self._protocol_enabled(pid)]
        handles_l = [mlines.Line2D([], [], color="black", linestyle='-', linewidth=6, label="LI"), mlines.Line2D([], [], color="black", linestyle='--', linewidth=6, label="SI")]
        
        handler_map = {}
        if self._protocol_enabled("P.1.1"):
            grad_rect_k = Rectangle((0, 0), 1, 1, label=r"$k$-sampling")
            handles_l.append(grad_rect_k)
            handler_map[grad_rect_k] = HandlerKGrad()
        legend_elements = handles_l + handles_r
        legend_cols = len(legend_elements) if len(legend_elements) < 6 else int(np.ceil(len(legend_elements)/2.0))
        
        real_x_ticks = [str(int(np.round(x,0))) if x%300==0 else '' for x in range(0,901,50)]
        svoid_x_ticks = ['' for x in range(0,901,50)]
        void_x_ticks = ['' for x in range(0,901,50)]
        void_y_ticks = ['' for _ in range(0,11,1)]

        for gt in ground_T:
            for thr in threshlds:
                fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6*nrows), squeeze=False)
                for m_h in msg_hop:
                    for a in more_k[0]:
                        agents_list = [25] if a in ["0_500;0_500", "1_000;0_250"] else more_k[1]
                        for ag in agents_list:
                            col = self._get_row(a, ag)
                            for k_idx, tm in enumerate(o_k):
                                for pid in protocols_order + ["adp_rnd"]:
                                    if pid != "adp_rnd" and not self._protocol_enabled(pid): continue
                                    
                                    base_key = (a, ag, tm, m_h, gt, thr)
                                    lines_sq = self._get_lines_to_plot(sq_d, pid, base_key, ag, protocol_colors)
                                    lines_rt = self._get_lines_to_plot(rt_d, pid, base_key, ag, protocol_colors)

                                    for data, color in lines_sq: ax[k_idx][col].plot(data, color=color, lw=6, ls='-')
                                    for data, color in lines_rt: ax[k_idx][col].plot(data, color=color, lw=6, ls='--')

                                ax[k_idx][col].set_xlim(0, 901); ax[k_idx][col].set_ylim(-0.03, 1.03)

                                if k_idx == 0:
                                    axt = ax[k_idx][col].twiny()
                                    axt.set_xticklabels(['']*len(axt.get_xticklabels()))
                                    axt.set_xlabel("LD25" if col == 0 else "HD25" if col == 1 else "HD100")
                                if k_idx == nrows - 1:
                                    ax[k_idx][col].set_xticks(np.arange(0,901,300), labels=real_x_ticks[::6])
                                    ax[k_idx][col].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                                    ax[k_idx][col].set_xlabel(r"$T$")
                                else:
                                    ax[k_idx][col].set_xticks(np.arange(0,901,300), labels=svoid_x_ticks[::6])
                                    ax[k_idx][col].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                                
                                if col == 0:
                                    ax[k_idx][col].set_yticks(np.arange(0,1.01,.1))
                                    ax[k_idx][col].set_ylabel(r"$Q(G,\tau)$")
                                elif col == 2:
                                    ax[k_idx][col].set_yticks(np.arange(0,1.01,.1), labels=void_y_ticks)
                                    axt = ax[k_idx][col].twinx()
                                    axt.set_yticklabels(['']*len(axt.get_yticklabels()))
                                    axt.set_ylabel(rf"$T_m = {tm}\, s$",rotation=270,labelpad=30)
                                else:
                                    ax[k_idx][col].set_yticks(np.arange(0,1.01,.1), labels=void_y_ticks)
                                ax[k_idx][col].grid(True, which='major')

                fig.tight_layout()
                fig.legend(bbox_to_anchor=(0.96, 0), handles=legend_elements, handler_map=handler_map, ncols=7, loc='upper right', framealpha=0.7, borderaxespad=0)
                fig.savefig(path + f"T{thr}_G{gt}_activation.pdf", bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_messages(self, c_type, sq_d, rt_d, keys):
        arena, thr, gt, agents, buffer = keys
        rows_tm = self._plot_tm_values(sorted(list(buffer)))
        if not rows_tm: return
        row_index = {c: i for i, c in enumerate(rows_tm)}
        nrows = len(rows_tm)

        scalarMap = cmx.ScalarMappable(norm=colors.Normalize(vmin=0, vmax=5), cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        handles_r = [mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=self.protocols_by_id[pid].get("label", pid)) for pid in protocols_order if self._protocol_enabled(pid)]
        handles_l = [mlines.Line2D([], [], color="black", linestyle='-', linewidth=6, label="LI"), mlines.Line2D([], [], color="black", linestyle='--', linewidth=6, label="SI"), mlines.Line2D([], [], color="black", linestyle=':', linewidth=6, label=r"$min|\mathcal{B}|$")]

        handler_map = {}
        if self._protocol_enabled("P.1.1"):
            grad_rect_k = Rectangle((0, 0), 1, 1, label=r"$k$-sampling")
            handles_l.append(grad_rect_k)
            handler_map[grad_rect_k] = HandlerKGrad()
        legend_elements = handles_l + handles_r
        legend_cols = len(legend_elements) if len(legend_elements) < 6 else int(np.ceil(len(legend_elements)/2.0))

        for d_target in [sq_d, rt_d]:
            for pid, subdict in d_target.items():
                for k in list(subdict.keys()):
                    norm = int(k[3]) - 1
                    if norm > 0: subdict[k] = [x/norm for x in subdict[k]]

        real_x_ticks = [str(int(np.round(x,0))) if x%300==0 else '' for x in range(0,901,50)]
        svoid_x_ticks = ['' for x in range(0,901,50)]
        void_x_ticks = ['' for x in range(0,901,50)]

        for t in thr:
            for g in gt:
                fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6*nrows), squeeze=False)
                for a in arena:
                    for ag in agents:
                        col = self._get_row(a, ag)
                        for b in buffer:
                            row = row_index.get(b)
                            if row is not None:
                                ax[row][col].plot([5/(int(ag)-1)] * 900, color="black", lw=4, ls=":")
                                for pid in protocols_order + ["adp_rnd"]:
                                    if pid != "adp_rnd" and not self._protocol_enabled(pid): continue
                                    
                                    base_key = (a, t, g, ag, b)
                                    lines_sq = self._get_lines_to_plot(sq_d, pid, base_key, ag, protocol_colors)
                                    lines_rt = self._get_lines_to_plot(rt_d, pid, base_key, ag, protocol_colors)

                                    for data, color in lines_sq: ax[row][col].plot(data, color=color, lw=6, ls='-')
                                    for data, color in lines_rt: ax[row][col].plot(data, color=color, lw=6, ls='--')

                for x in range(nrows):
                    for y in range(3):
                        ax[x][y].grid(True)
                        ax[x][y].set_xlim(0,900)
                        ax[x][y].set_ylim(-0.03,1.03)
                        ax[x][y].set_xticks(np.arange(0,901,300), labels=real_x_ticks[::6] if x==nrows-1 else svoid_x_ticks[::6])
                        ax[x][y].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                        if y > 0:
                            ax[x][y].set_yticklabels(['']*len(ax[x][y].get_yticklabels()))
                
                for idx in range(3):
                    axt = ax[0][idx].twiny()
                    axt.set_xticklabels(['']*len(axt.get_xticklabels()))
                    axt.set_xlabel("LD25" if idx == 0 else "HD25" if idx == 1 else "HD100")
                
                for r_idx, tm_val in enumerate(rows_tm):
                    ayt = ax[r_idx][2].twinx()
                    ayt.set_yticklabels(['']*len(ayt.get_yticklabels()))
                    ayt.set_ylabel(rf"$T_m = {tm_val}\, s$",rotation=270,labelpad=30)
                    ax[r_idx][0].set_ylabel(r"$M$")
                for y in range(3): ax[nrows-1][y].set_xlabel(r"$T\, s$")

                fig.tight_layout()
                path = os.path.join(self.base, "msgs_data", "images") + "/"
                os.makedirs(path, exist_ok=True)
                fig.legend(bbox_to_anchor=(0.96, 0), handles=legend_elements, handler_map=handler_map, ncols=4, loc='upper right', framealpha=0.7, borderaxespad=0)
                fig.savefig(path + f"{str(g).replace('.','_')}_{c_type}_messages.pdf", bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_dif_messages(self, c_type, sq_c, sq_u, rt_c, rt_u, keys):
        arena, thr, gt, agents, buffer = keys
        rows_tm = self._plot_tm_values(sorted(list(buffer)))
        if not rows_tm: return
        row_index = {c: i for i, c in enumerate(rows_tm)}
        nrows = len(rows_tm)

        scalarMap = cmx.ScalarMappable(norm=colors.Normalize(vmin=0, vmax=5), cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        handles_r = [mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=self.protocols_by_id[pid].get("label", pid)) for pid in protocols_order if self._protocol_enabled(pid)]
        handles_l = [mlines.Line2D([], [], color="black", linestyle='-', linewidth=6, label="LI"), mlines.Line2D([], [], color="black", linestyle='--', linewidth=6, label="SI")]

        handler_map = {}
        if self._protocol_enabled("P.1.1"):
            grad_rect_k = Rectangle((0, 0), 1, 1, label=r"$k$-sampling")
            handles_l.append(grad_rect_k)
            handler_map[grad_rect_k] = HandlerKGrad()
        legend_elements = handles_l + handles_r
        legend_cols = len(legend_elements) if len(legend_elements) < 6 else int(np.ceil(len(legend_elements)/2.0))

        real_x_ticks = [str(int(np.round(x,0))) if x%300==0 else '' for x in range(0,901,50)]
        svoid_x_ticks = ['' for x in range(0,901,50)]
        void_x_ticks = ['' for x in range(0,901,50)]

        for t in thr:
            for g in gt:
                fig, ax = plt.subplots(nrows=nrows, ncols=3, figsize=(24, 6*nrows), squeeze=False)
                for a in arena:
                    for ag in agents:
                        col = self._get_row(a, ag)
                        for b in buffer:
                            row = row_index.get(b)
                            if row is not None:
                                for pid in protocols_order + ["adp_rnd"]:
                                    if pid != "adp_rnd" and not self._protocol_enabled(pid): continue
                                    
                                    base_key = (a, t, g, ag, b)
                                    sc_lines = self._get_lines_to_plot(sq_c, pid, base_key, ag, protocol_colors)
                                    su_lines = self._get_lines_to_plot(sq_u, pid, base_key, ag, protocol_colors)
                                    rc_lines = self._get_lines_to_plot(rt_c, pid, base_key, ag, protocol_colors)
                                    ru_lines = self._get_lines_to_plot(rt_u, pid, base_key, ag, protocol_colors)
                                    
                                    for (c_data, c_color), (u_data, _) in zip(sc_lines, su_lines):
                                        flag = [(c_v-u_v)/(c_v+u_v) if (c_v+u_v)!=0 else 0 for c_v, u_v in zip(c_data, u_data)]
                                        ax[row][col].plot(flag, color=c_color, lw=6, ls='--')
                                        
                                    for (c_data, c_color), (u_data, _) in zip(rc_lines, ru_lines):
                                        flag = [(c_v-u_v)/(c_v+u_v) if (c_v+u_v)!=0 else 0 for c_v, u_v in zip(c_data, u_data)]
                                        ax[row][col].plot(flag, color=c_color, lw=6, ls='-')

                for x in range(nrows):
                    for y in range(3):
                        ax[x][y].grid(True)
                        ax[x][y].set_xlim(0,900)
                        ax[x][y].set_ylim(-0.03,0.73)
                        ax[x][y].set_xticks(np.arange(0,901,300), labels=real_x_ticks[::6] if x==nrows-1 else svoid_x_ticks[::6])
                        ax[x][y].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                        if y > 0:
                            ax[x][y].set_yticklabels(['']*len(ax[x][y].get_yticklabels()))
                
                for idx in range(3):
                    axt = ax[0][idx].twiny()
                    axt.set_xticklabels(['']*len(axt.get_xticklabels()))
                    axt.set_xlabel("LD25" if idx == 0 else "HD25" if idx == 1 else "HD100")
                
                for r_idx, tm_val in enumerate(rows_tm):
                    ayt = ax[r_idx][2].twinx()
                    ayt.set_yticklabels(['']*len(ayt.get_yticklabels()))
                    ayt.set_ylabel(rf"$T_m = {tm_val}\, s$",rotation=270,labelpad=30)
                    ax[r_idx][0].set_ylabel(r"$\Delta M$")
                for y in range(3): ax[nrows-1][y].set_xlabel(r"$T\, s$")

                fig.tight_layout()
                path = os.path.join(self.base, "msgs_data", "images") + "/"
                os.makedirs(path, exist_ok=True)
                fig.legend(bbox_to_anchor=(0.96, 0), handles=legend_elements, handler_map=handler_map, ncols=7, loc='upper right', framealpha=0.7, borderaxespad=0)
                fig.savefig(path + f"{str(g).replace('.','_')}_{c_type}_messages.pdf", bbox_inches='tight')
                plt.close(fig)
                
##########################################################################################################
    def plot_short(self, msgs_data, proc_data, mode="combined"):
        path = os.path.join(self.base, "short_data", "images") + "/"
        os.makedirs(path, exist_ok=True)
        
        sq_tot, rt_tot = {pid: {} for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]}, {pid: {} for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]}
        arena, thr, gt, agents, buffer, msg_hop = set(), set(), set(), set(), set(), set()

        for raw_k, s_data in msgs_data.items():
            a, al, t_val, g_val, c, ag, b_val, mh, k_val, gp = self._cast_msg_key(raw_k)
            if g_val > 1: g_val = round(g_val / 100.0, 2)
            if t_val > 1: t_val = round(t_val / 100.0, 2)
            
            arena.add(a); thr.add(t_val); gt.add(g_val); agents.add(ag); buffer.add(b_val); msg_hop.add(mh)
            pid = self._get_protocol_id(al, c, mh)
            if pid:
                if pid == "P.1.1":
                    if str(ag) not in self.k_samps_per_agent: self.k_samps_per_agent[str(ag)] = set()
                    self.k_samps_per_agent[str(ag)].add(k_val)

        sq_act, rt_act = {pid: {} for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]}, {pid: {} for pid in list(self.protocols_by_id.keys()) + ["adp_rnd"]}
        for s_data_dict in proc_data:
            for raw_k, s_data in s_data_dict.items():
                a_al, n_r, et, a_s, c, n_a, t_val, g_val, m_h, b_val, k_val = self._cast_proc_key(raw_k)
                
                if g_val > 1: g_val = round(g_val / 100.0, 2)
                if t_val > 1: t_val = round(t_val / 100.0, 2)
                
                arena.add(a_s); thr.add(t_val); gt.add(g_val); agents.add(n_a); buffer.add(b_val); msg_hop.add(m_h)
                pid = self._get_protocol_id(a_al, c, m_h)
                if pid:
                    if pid == "P.1.1":
                        if str(n_a) not in self.k_samps_per_agent: self.k_samps_per_agent[str(n_a)] = set()
                        self.k_samps_per_agent[str(n_a)].add(k_val)
                    is_sq = (a_s.split(';')[0] == a_s.split(';')[1])
                    (sq_act if is_sq else rt_act)[pid][(a_s, t_val, g_val, n_a, b_val, m_h, k_val)] = s_data[0]

        raw_all_tm = sorted(list(buffer))
        main_tm_list = self._plot_tm_values(raw_all_tm)
        plot_cfg = self.plot_config.get("plots", {})
        exclude_set = {self._normalize_tm(v) for v in plot_cfg.get("exclude_tm", []) if self._normalize_tm(v) is not None}
        insert_raw = plot_cfg.get("insert", [])
        
        insert_tm_list = [self._normalize_tm(v) for v in insert_raw if self._normalize_tm(v) is not None and self._normalize_tm(v) in raw_all_tm and self._normalize_tm(v) in exclude_set]
        
        if not main_tm_list and not insert_tm_list:
            return

        combined_tm = sorted(list(set(main_tm_list) | set(insert_tm_list)))
        use_gradient = len(main_tm_list) > 1 and not insert_tm_list

        scalarMap = cmx.ScalarMappable(norm=colors.Normalize(vmin=0, vmax=5), cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        tm_norm = colors.LogNorm(vmin=min(combined_tm), vmax=max(combined_tm)) if use_gradient else None

        def get_tm_color(pid, tm_val, k_val=None, ag=None):
            if pid == 'P.1.1' and k_val is not None and ag is not None:
                return self._get_p11_color(k_val, ag)
            base_color = protocol_colors.get(pid, 'gray')
            if not use_gradient: return base_color
            if pid == 'P.0': return base_color
            rgb_base = colors.to_rgb(base_color)
            h, l, s = colorsys.rgb_to_hls(*rgb_base)
            norm_val = tm_norm(tm_val)
            if tm_val <= 0: norm_val = tm_norm(max(combined_tm))
            if np.ma.is_masked(norm_val): norm_val = 0.0
            if tm_val == max(combined_tm):
                new_l, new_s = l, s
            else:
                diff = (1.0 - float(norm_val))
                new_l = max(l, min(0.85, l + (diff * 0.4))) 
                new_s = s * (1.0 - (diff * 0.3))
            return np.clip(colorsys.hls_to_rgb(h, new_l, new_s), 0, 1)

        real_x_ticks = [str(int(np.round(x,0))) if x%300==0 else '' for x in range(0,901,50)]
        svoid_x_ticks = ['' for x in range(0,901,50)]
        void_x_ticks = ['' for x in range(0,901,50)]

        gt_sorted = sorted(list(gt))
        thr_sorted = sorted(list(thr))
        msg_hop_sorted = sorted(list(msg_hop))

        interfaces_to_plot = ["LI", "SI"] if mode == "split_interface" else ["both"]

        for interface in interfaces_to_plot:
            n_rows = len(gt_sorted)
            fig, ax = plt.subplots(nrows=n_rows, ncols=3, figsize=(24, 6 * n_rows), squeeze=False, constrained_layout=True)
            inset_axes_dict = {}
            
            handles_r = [mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='s', linestyle='None', markersize=14, label=self.protocols_by_id[pid].get("label", pid)) for pid in protocols_order if self._protocol_enabled(pid)]
            
            handles_l = []
            if interface == "both":
                handles_l.extend([
                    mlines.Line2D([], [], color="black", linestyle='-', linewidth=4, label="LI"), 
                    mlines.Line2D([], [], color="black", linestyle='--', linewidth=4, label="SI")
                ])
            
            for r_idx, g in enumerate(gt_sorted):
                for t in thr_sorted:
                    for mh in msg_hop_sorted:
                        for a in arena:
                            is_sq_arena = (a.split(';')[0] == a.split(';')[1])
                            
                            # Fixed Logic: Correctly filter out the opposite interface
                            if interface == "SI" and is_sq_arena:
                                continue
                            if interface == "LI" and not is_sq_arena:
                                continue
                                
                            for ag in agents:
                                col = self._get_row(a, ag)
                                
                                for tm_val in combined_tm:
                                    is_main = tm_val in main_tm_list
                                    is_insert = tm_val in insert_tm_list
                                    
                                    for pid in protocols_order + ["adp_rnd"]:
                                        if pid != "adp_rnd" and not self._protocol_enabled(pid): continue
                                        is_p0 = (pid == 'P.0')
                                        
                                        if not (is_main or is_insert or is_p0): continue
                                        
                                        base_key = (a, t, g, ag, tm_val, mh)
                                        
                                        source_dict = sq_act if is_sq_arena else rt_act
                                        matches = [(k_tup[-1], v) for k_tup, v in source_dict.get(pid, {}).items() if k_tup[:-1] == base_key]
                                        matches.sort(key=lambda x: x[0]) 
                                        
                                        for k_val, _ in matches:
                                            color = get_tm_color(pid, tm_val, k_val, ag)
                                            data_key = base_key + (k_val,)
                                            
                                            v_sq_a = sq_act.get(pid, {}).get(data_key)
                                            v_rt_a = rt_act.get(pid, {}).get(data_key)
                                            
                                            targets = []
                                            if is_main or is_p0:
                                                targets.append(ax[r_idx][col])
                                            if is_insert or is_p0:
                                                if (r_idx, col) not in inset_axes_dict:
                                                    if g >= 0.8:
                                                        best_box = [0.62, 0.03, 0.35, 0.35]
                                                    else:
                                                        best_box = [0.62, 0.62, 0.35, 0.35]
                                                    
                                                    ins_ax = ax[r_idx][col].inset_axes(best_box)
                                                    ins_ax.set_xlim(0, 901)
                                                    ins_ax.set_ylim(-0.03, 1.03)
                                                    ins_ax.set_yticks([0.0, 0.5, 1.0])
                                                    ins_ax.axhline(0.5, color='dimgray', ls=':', lw=1.5)
                                                    ins_ax.axhline(1.0, color='dimgray', ls=':', lw=1.5)
                                                    ins_ax.set_xticks([0, 300, 600, 900])
                                                    ins_ax.tick_params(labelbottom=False, labelleft=False)
                                                    ins_ax.grid(True, ls=':', color='silver')
                                                    inset_axes_dict[(r_idx, col)] = ins_ax
                                                    
                                                targets.append(inset_axes_dict[(r_idx, col)])
                                                
                                            # Fixed Logic: Strictly assign '-' to squared and '--' to rectangular
                                            for t_ax in targets:
                                                if is_sq_arena and v_sq_a is not None:
                                                    t_ax.plot(v_sq_a, color=color, lw=6, ls='-')
                                                elif not is_sq_arena and v_rt_a is not None:
                                                    t_ax.plot(v_rt_a, color=color, lw=6, ls='--' if mode =='combined' else '-')

            for x in range(n_rows):
                for y in range(3):
                    ax[x][y].grid(True)
                    ax[x][y].set_xlim(0, 900)
                    ax[x][y].set_ylim(-0.03, 1.03)
                    
                    ax[x][y].set_xticks(np.arange(0,901,300), labels=real_x_ticks[::6] if x == (n_rows - 1) else svoid_x_ticks[::6])
                    ax[x][y].set_xticks(np.arange(0,901,50), labels=void_x_ticks, minor=True)
                    
                    if y > 0: 
                        ax[x][y].set_yticklabels(['']*len(ax[x][y].get_yticklabels()))
            
                ax[x][0].set_ylabel(r"$Q(G,\tau)$")
                
                ayt = ax[x][2].twinx()
                ayt.set_yticklabels(['']*len(ayt.get_yticklabels()))
                ayt.set_ylabel(rf"$G = {gt_sorted[x]}$", rotation=270, labelpad=35)
                    
            ax[0][0].set_title("LD25", pad=20)
            ax[0][1].set_title("HD25", pad=20)
            ax[0][2].set_title("HD100", pad=20)
            
            for y in range(3): 
                ax[n_rows - 1][y].set_xlabel(r"$T$")

            legend_elements = []
            handler_map = {}
            if use_gradient:
                class HandlerGradient(HandlerBase):
                    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
                        n_steps = 5
                        cmap = colors.LinearSegmentedColormap.from_list("grey_grad", [ "#E0E0E0","#2D2D2D"])
                        artists = []
                        step_width = width / n_steps
                        for i in range(n_steps):
                            color = cmap(i / n_steps)
                            r = Rectangle((xdescent + i * step_width, ydescent), step_width, height, facecolor=color, edgecolor=color, transform=trans)
                            artists.append(r)
                        return artists
                grad_rect = Rectangle((0, 0), 1, 1, label=r"$T_m$")
                legend_elements.append(grad_rect)
                handler_map[grad_rect] = HandlerGradient()
                
            if self._protocol_enabled("P.1.1"):
                grad_rect_k = Rectangle((0, 0), 1, 1, label=r"$k$-sampling")
                handles_l.append(grad_rect_k)
                handler_map[grad_rect_k] = HandlerKGrad()
                
            legend_elements.extend(handles_l+handles_r)
            
            n_cols_leg = 7 if mode=="combined" else 5
            x_pad = 0.11 if mode=="combined" else 0.31
            fig.legend(handles=legend_elements, handler_map=handler_map, loc='lower left', bbox_to_anchor=(x_pad, -0.06), ncol=n_cols_leg, frameon=True, edgecolor='0.8')
                
            prefix = "" if interface == "both" else f"{interface}_"
            fig.savefig(path + f"{prefix}short_all_G.pdf", bbox_inches='tight')
            plt.close(fig)