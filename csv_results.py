import os, logging, re, json
import numpy as np
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib import pyplot as plt
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})

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
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "proc_data" or elem == "msgs_data":
                self.bases.append(os.path.join(self.base, elem))
        self.plot_config = self._load_plot_config()
        self.protocols = self.plot_config.get("protocols", [])
        self.protocols_by_id = {p.get("id"): p for p in self.protocols if p.get("id") is not None}

##########################################################################################################
    def _default_plot_config(self):
        return {
            "protocols": [
                {"id": "P.0", "label": r"$AN$", "color": "red"},
                {"id": "P.1.0", "label": r"$AN_{t}$", "color": "viridis:0"},
                {"id": "P.1.1", "label": r"$AN_{t}^{1}$", "color": "orange"},
                {"id": "O.0.0", "label": r"$ID+B$", "color": "viridis:1"},
                {"id": "O.2.0", "label": r"$ID+R_{f}$", "color": "viridis:2"},
                {"id": "O.1.1", "label": r"$ID+R_{1}$", "color": "viridis:3"},
                {"id": "O.1.0", "label": r"$ID+R_{\\infty}$", "color": "viridis:4"},
            ],
            "plots": {
                "active": {"exclude_protocols": [], "exclude_tm": []},
                "messages": {"exclude_protocols": [], "exclude_tm": []},
            },
        }

##########################################################################################################
    def _merge_plot_config(self, base_cfg, user_cfg):
        cfg = dict(base_cfg)
        cfg["plots"] = dict(base_cfg.get("plots", {}))
        if isinstance(user_cfg, dict):
            if "protocols" in user_cfg:
                cfg["protocols"] = user_cfg.get("protocols") or []
            if "plots" in user_cfg and isinstance(user_cfg.get("plots"), dict):
                for plot_name, plot_cfg in user_cfg["plots"].items():
                    if plot_name not in cfg["plots"]:
                        cfg["plots"][plot_name] = {}
                    if isinstance(plot_cfg, dict):
                        cfg["plots"][plot_name].update(plot_cfg)
        return cfg

##########################################################################################################
    def _load_plot_config(self):
        cfg = self._default_plot_config()
        path = os.path.join(self.base, "plot_config.json")
        if not os.path.exists(path):
            return cfg
        try:
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            return self._merge_plot_config(cfg, user_cfg)
        except Exception as exc:
            logging.warning("Failed to load plot_config.json (%s). Using defaults.", exc)
            return cfg

##########################################################################################################
    def apply_plot_overrides(self, plot_names, exclude_protocols=None, exclude_tm=None):
        if not plot_names:
            return
        for plot_name in plot_names:
            plot_cfg = self.plot_config.setdefault("plots", {}).setdefault(plot_name, {})
            if exclude_protocols is not None:
                plot_cfg["exclude_protocols"] = exclude_protocols
            if exclude_tm is not None:
                plot_cfg["exclude_tm"] = exclude_tm

##########################################################################################################
    def _normalize_tm(self, val):
        if isinstance(val, bool):
            return None
        if isinstance(val, np.integer):
            return int(val)
        if isinstance(val, np.floating) and float(val).is_integer():
            return int(val)
        if isinstance(val, (int, float)):
            if isinstance(val, float) and not val.is_integer():
                return None
            return int(val)
        if isinstance(val, str):
            s = val.strip()
            if s.isdigit():
                return int(s)
        return None

##########################################################################################################
    def _plot_tm_values(self, plot_name, values):
        plot_cfg = self.plot_config.get("plots", {}).get(plot_name, {})
        exclude = plot_cfg.get("exclude_tm") or []
        exclude_set = set()
        for v in exclude:
            norm = self._normalize_tm(v)
            if norm is not None:
                exclude_set.add(norm)
        out = []
        for v in values:
            nv = self._normalize_tm(v)
            if nv is None or nv in exclude_set:
                continue
            out.append(nv if isinstance(v, (int, np.integer, np.floating)) else v)
        return out

##########################################################################################################
    def _protocol_matches(self, protocol, selector):
        if protocol is None or selector is None:
            return False
        sel = str(selector).strip()
        return sel == protocol.get("id") or sel == protocol.get("label")

##########################################################################################################
    def _protocol_enabled(self, plot_name, protocol_id):
        protocol = self.protocols_by_id.get(protocol_id)
        plot_cfg = self.plot_config.get("plots", {}).get(plot_name, {})
        exclude = plot_cfg.get("exclude_protocols") or []
        if any(self._protocol_matches(protocol, sel) for sel in exclude):
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
    def read_msgs_csv(self,path):
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header:
                return data
            header_cols = header.rstrip('\n').split('\t')
            try:
                data_idx = header_cols.index("data")
            except ValueError:
                data_idx = max(len(header_cols) - 1, 0)
            for line in f:
                line = line.strip('\n')
                if not line:
                    continue
                cols = line.split('\t')
                if len(cols) <= data_idx:
                    continue
                keys = cols[:data_idx]
                array_val = self._parse_float_list(cols[data_idx])
                if len(keys) >= 9:
                    data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5],keys[6],keys[7],keys[8]):array_val})
        return data #,labels

##########################################################################################################
    def read_csv(self,path,algo,n_runs):
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header:
                return data
            keys = header.rstrip('\n').split('\t')
            use_legacy_idx = len(keys) > 11
            type_idx = 9 if use_legacy_idx else max(len(keys) - 3, 0)
            data_idx = 10 if use_legacy_idx else max(len(keys) - 2, 0)
            std_idx = 11 if use_legacy_idx else max(len(keys) - 1, 0)
            for line in f:
                line = line.strip('\n')
                if not line:
                    continue
                cols = line.split('\t')
                if len(cols) <= max(type_idx, data_idx, std_idx, 7):
                    continue
                array_val = self._parse_float_list(cols[data_idx])
                std_val = self._parse_float_list(cols[std_idx], allow_dash=True)
                data.update({(algo,n_runs,cols[0],cols[1],cols[2],cols[3],cols[4],cols[5],cols[6],cols[7],cols[type_idx]):(array_val,std_val)})
        return data

##########################################################################################################
    def divide_data(self,data):
        states, comm_states, uncomm_states, times = {},{},{},{}
        algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, msg_hops, msg_time    = [],[],[],[],[],[],[],[],[],[]
        for k in data.keys():
            for i in range(len(k)-1):
                if i == 0 and k[i] not in algorithm: algorithm.append(k[i])
                elif i == 1 and k[i] not in n_runs: n_runs.append(k[i])
                elif i == 2 and k[i] not in exp_time: exp_time.append(k[i])
                elif i == 3 and k[i] not in arena_size: arena_size.append(k[i])
                elif i == 4 and k[i] not in communication: communication.append(k[i])
                elif i == 5 and k[i] not in n_agents: n_agents.append(k[i])
                elif i == 6 and k[i] not in thrlds: thrlds.append(k[i])
                elif i == 7 and k[i] not in gt: gt.append(k[i])
                elif i == 8 and k[i] not in msg_hops: msg_hops.append(k[i])
                elif i == 9 and k[i] not in msg_time: msg_time.append(k[i])
            if k[-1] == "times":
                times.update({k[:-1]:data.get(k)})
            elif k[-1] == "swarm_state":
                states.update({k[:-1]:data.get(k)})
            elif k[-1] == "committed_state":
                comm_states.update({k[:-1]:data.get(k)})
            elif k[-1] == "uncommitted_state":
                uncomm_states.update({k[:-1]:data.get(k)})
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, msg_hops, msg_time), states, times, (comm_states,uncomm_states)
    
##########################################################################################################
    def plot_by_commit_w_gt_thr(self,data_in):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_state_comm_sq,dict_adms_state_comm_sq,dict_fifo_state_comm_sq,dict_rnd_state_comm_sq,dict_inf_rnd_state_comm_sq,dict_adp_rnd_state_comm_sq               = {},{},{},{},{},{}
        dict_park_state_uncomm_sq,dict_adms_state_uncomm_sq,dict_fifo_state_uncomm_sq,dict_rnd_state_uncomm_sq,dict_inf_rnd_state_uncomm_sq,dict_adp_rnd_state_uncomm_sq     = {},{},{},{},{},{}
        dict_park_state_comm_rt,dict_adms_state_comm_rt,dict_fifo_state_comm_rt,dict_rnd_state_comm_rt,dict_inf_rnd_state_comm_rt,dict_adp_rnd_state_comm_rt               = {},{},{},{},{},{}
        dict_park_state_uncomm_rt,dict_adms_state_uncomm_rt,dict_fifo_state_uncomm_rt,dict_rnd_state_uncomm_rt,dict_inf_rnd_state_uncomm_rt,dict_adp_rnd_state_uncomm_rt     = {},{},{},{},{},{}
        ground_T, threshlds , msg_time                                                                                                          = [],[],[]
        algo,arena,runs,time,comm,agents,msg_hop                                                                                                = [],[],[],[],[],[],[]
        o_k                                                                                                                                     = []
        for i in range(len(data_in)):
            da_K = data_in[i][0].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in runs: runs.append(k0[1])
                if k0[2] not in time: time.append(k0[2])
                if k0[3] not in arena: arena.append(k0[3])
                if k0[4] not in comm: comm.append(k0[4])
                if k0[5] not in agents: agents.append(k0[5])
                if k0[6] not in threshlds: threshlds.append(k0[6])
                if k0[7] not in ground_T: ground_T.append(k0[7])
                if k0[8] not in msg_hop: msg_hop.append(k0[8])
                if k0[9] not in msg_time: msg_time.append(k0[9])
        for i in range(len(data_in)):
            for a in algo:
                for n_r in runs:
                    for et in time:
                        for a_s in arena:
                            for c in comm:
                                for n_a in agents:
                                    for thr in threshlds:
                                        for gt in ground_T:
                                            for m_h in msg_hop:
                                                for m_t in msg_time:
                                                    comm_data = data_in[i][0].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    uncomm_data = data_in[i][1].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    if comm_data != None:
                                                        if m_t not in o_k: o_k.append(m_t)
                                                        if a=='P' and int(c)==0 and m_t in o_k:
                                                            if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                dict_park_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                dict_park_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                            else:
                                                                dict_park_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                dict_park_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                        if a=='O' and m_t in o_k:
                                                            if int(c)==0:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_adms_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_adms_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                else:
                                                                    dict_adms_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_adms_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                            elif int(c)==1:
                                                                if m_h=="1":
                                                                    if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                        dict_rnd_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                        dict_rnd_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                    else:
                                                                        dict_rnd_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                        dict_rnd_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                elif m_h=="a31":
                                                                    if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                        dict_adp_rnd_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                        dict_adp_rnd_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                    else:
                                                                        dict_adp_rnd_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                        dict_adp_rnd_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                else:
                                                                    if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                        dict_inf_rnd_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                        dict_inf_rnd_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                    else:
                                                                        dict_inf_rnd_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                        dict_inf_rnd_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                            elif int(c)==2:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_fifo_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_fifo_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                else:
                                                                    dict_fifo_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_fifo_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
        self.print_evolutions_by_commit(path,ground_T,threshlds,[dict_park_state_comm_sq,dict_adms_state_comm_sq,dict_fifo_state_comm_sq,dict_rnd_state_comm_sq,dict_inf_rnd_state_comm_sq,dict_adp_rnd_state_comm_sq],[dict_park_state_uncomm_sq,dict_adms_state_uncomm_sq,dict_fifo_state_uncomm_sq,dict_rnd_state_uncomm_sq,dict_inf_rnd_state_uncomm_sq,dict_adp_rnd_state_uncomm_sq],[dict_park_state_comm_rt,dict_adms_state_comm_rt,dict_fifo_state_comm_rt,dict_rnd_state_comm_rt,dict_inf_rnd_state_comm_rt,dict_adp_rnd_state_comm_rt],[dict_park_state_uncomm_rt,dict_adms_state_uncomm_rt,dict_fifo_state_uncomm_rt,dict_rnd_state_uncomm_rt,dict_inf_rnd_state_uncomm_rt,dict_adp_rnd_state_uncomm_rt],o_k,[["0_500;0_500","1_000;1_000","1_000;0_250","2_000;0_500"],agents],msg_hop)

##########################################################################################################
    def plot_active_w_gt_thr(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_state_sq,dict_adms_state_sq,dict_fifo_state_sq,dict_rnd_state_sq,dict_inf_rnd_state_sq,dict_adp_rnd_state_sq    = {},{},{},{},{},{}
        dict_park_time_sq,dict_adms_time_sq,dict_fifo_time_sq,dict_rnd_time_sq,dict_inf_rnd_time_sq,dict_adp_rnd_time_sq         = {},{},{},{},{},{}
        dict_park_state_rt,dict_adms_state_rt,dict_fifo_state_rt,dict_rnd_state_rt,dict_inf_rnd_state_rt,dict_adp_rnd_state_rt    = {},{},{},{},{},{}
        dict_park_time_rt,dict_adms_time_rt,dict_fifo_time_rt,dict_rnd_time_rt,dict_inf_rnd_time_rt,dict_adp_rnd_time_rt         = {},{},{},{},{},{}
        ground_T, threshlds , msg_time                                                                      = [],[],[]
        algo,arena,runs,time,comm,agents,msg_hop                                                            = [],[],[],[],[],[],[]
        o_k                                                                                                 = []
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in runs: runs.append(k0[1])
                if k0[2] not in time: time.append(k0[2])
                if k0[3] not in arena: arena.append(k0[3])
                if k0[4] not in comm: comm.append(k0[4])
                if k0[5] not in agents: agents.append(k0[5])
                if k0[6] not in threshlds: threshlds.append(k0[6])
                if k0[7] not in ground_T: ground_T.append(k0[7])
                if k0[8] not in msg_hop: msg_hop.append(k0[8])
                if k0[9] not in msg_time: msg_time.append(k0[9])
        for i in range(len(data_in)):
            for a in algo:
                for n_r in runs:
                    for et in time:
                        for a_s in arena:
                            for c in comm:
                                for n_a in agents:
                                    for thr in threshlds:
                                        for gt in ground_T:
                                            for m_h in msg_hop:
                                                for m_t in msg_time:
                                                    s_data = data_in[i].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    t_data = times[i].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    if s_data != None:
                                                        if m_t not in o_k: o_k.append(m_t)
                                                        
                                                        if a=='P' and int(c)==0 and m_t in o_k:
                                                            if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                dict_park_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                dict_park_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            else:
                                                                dict_park_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                dict_park_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            
                                                        if a=='O' and m_t in o_k:
                                                            if int(c)==0:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_adms_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_adms_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                else:
                                                                    dict_adms_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_adms_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            elif int(c)==1:
                                                                if m_h=="1":
                                                                    if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                        dict_rnd_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                        dict_rnd_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                    else:
                                                                        dict_rnd_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                        dict_rnd_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                elif m_h=="a31":
                                                                    if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                        dict_adp_rnd_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                        dict_adp_rnd_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                    else:
                                                                        dict_adp_rnd_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                        dict_adp_rnd_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                else:
                                                                    if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                        dict_inf_rnd_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                        dict_inf_rnd_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                    else:
                                                                        dict_inf_rnd_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                        dict_inf_rnd_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            elif int(c)==2:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_fifo_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_fifo_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                else:
                                                                    dict_fifo_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_fifo_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
        self.print_evolutions(path,ground_T,threshlds,[dict_park_state_sq,dict_adms_state_sq,dict_fifo_state_sq,dict_rnd_state_sq,dict_inf_rnd_state_sq,dict_adp_rnd_state_sq],[dict_park_time_sq,dict_adms_time_sq,dict_fifo_time_sq,dict_rnd_time_sq,dict_inf_rnd_time_sq,dict_adp_rnd_time_sq],[dict_park_state_rt,dict_adms_state_rt,dict_fifo_state_rt,dict_rnd_state_rt,dict_inf_rnd_state_rt,dict_adp_rnd_state_rt],[dict_park_time_rt,dict_adms_time_rt,dict_fifo_time_rt,dict_rnd_time_rt,dict_inf_rnd_time_rt,dict_adp_rnd_time_rt],o_k,[["0_500;0_500","1_000;1_000","1_000;0_250","2_000;0_500"],agents],msg_hop)

##########################################################################################################
    def plot_messages(self,data):
        dict_park_square, dict_adam_square, dict_fifo_square,dict_rnd_square,dict_inf_rnd_square,dict_adapt_rnd_square                                      = {},{},{},{},{},{}
        dict_park_rect, dict_adam_rect, dict_fifo_rect,dict_rnd_rect,dict_inf_rnd_rect,dict_adapt_rnd_rect                                                  = {},{},{},{},{},{}
        com_dict_park_square, com_dict_adam_square, com_dict_fifo_square,com_dict_rnd_square,com_dict_inf_rnd_square,com_dict_adapt_rnd_square              = {},{},{},{},{},{}
        com_dict_park_rect, com_dict_adam_rect, com_dict_fifo_rect,com_dict_rnd_rect,com_dict_inf_rnd_rect,com_dict_adapt_rnd_rect                          = {},{},{},{},{},{}
        uncom_dict_park_square, uncom_dict_adam_square, uncom_dict_fifo_square,uncom_dict_rnd_square,uncom_dict_inf_rnd_square,uncom_dict_adapt_rnd_square  = {},{},{},{},{},{}
        uncom_dict_park_rect, uncom_dict_adam_rect, uncom_dict_fifo_rect,uncom_dict_rnd_rect,uncom_dict_inf_rnd_rect,uncom_dict_adapt_rnd_rect              = {},{},{},{},{},{}
        arena,algo,thr,gt,comm,agents,buffer,m_hop,group = [],[],[],[],[],[],[],[],[]
        da_K = data.keys()
        for k0 in da_K:
            if k0[0] not in arena: arena.append(k0[0])
            if k0[1] not in algo: algo.append(k0[1])
            if k0[2] not in thr: thr.append(k0[2])
            if k0[3] not in gt: gt.append(k0[3])
            if k0[4] not in comm: comm.append(k0[4])
            if k0[5] not in agents: agents.append(k0[5])
            if k0[6] not in buffer: buffer.append(k0[6])
            if k0[7] not in m_hop: m_hop.append(k0[7])
            if k0[8] not in group: group.append(k0[8])
        for a in arena:
            for al in algo:
                for t in thr:
                    for g in gt:
                        for c in comm:
                            for ag in agents:
                                for b in buffer:
                                    for mh in m_hop:
                                        for gp in group:
                                            s_data = data.get((a,al,t,g,c,ag,b,mh,gp))
                                            if s_data != None:
                                                if al=='P' and int(c)==0:
                                                    if a.split(';')[0] == a.split(';')[1]:
                                                        if gp == "commit_average":
                                                            com_dict_park_square.update({(a,t,g,ag,b):s_data})
                                                        elif gp == "uncommit_average":
                                                            uncom_dict_park_square.update({(a,t,g,ag,b):s_data})
                                                        else:
                                                            dict_park_square.update({(a,t,g,ag,b):s_data})
                                                    else:
                                                        if gp == "commit_average":
                                                            com_dict_park_rect.update({(a,t,g,ag,b):s_data})
                                                        elif gp == "uncommit_average":
                                                            uncom_dict_park_rect.update({(a,t,g,ag,b):s_data})
                                                        else:
                                                            dict_park_rect.update({(a,t,g,ag,b):s_data})
                                                if al=='O':
                                                    if int(c)==0:
                                                        if a.split(';')[0] == a.split(';')[1]:
                                                            if gp == "commit_average":
                                                                com_dict_adam_square.update({(a,t,g,ag,b):s_data})
                                                            elif gp == "uncommit_average":
                                                                uncom_dict_adam_square.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                dict_adam_square.update({(a,t,g,ag,b):s_data})
                                                        else:
                                                            if gp == "commit_average":
                                                                com_dict_adam_rect.update({(a,t,g,ag,b):s_data})
                                                            elif gp == "uncommit_average":
                                                                uncom_dict_adam_rect.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                dict_adam_rect.update({(a,t,g,ag,b):s_data})
                                                    elif int(c)==1:
                                                        if mh=="1":
                                                            if a.split(';')[0] == a.split(';')[1]:
                                                                if gp == "commit_average":
                                                                    com_dict_rnd_square.update({(a,t,g,ag,b):s_data})
                                                                elif gp == "uncommit_average":
                                                                    uncom_dict_rnd_square.update({(a,t,g,ag,b):s_data})
                                                                else:
                                                                    dict_rnd_square.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                if gp == "commit_average":
                                                                    com_dict_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                                elif gp == "uncommit_average":
                                                                    uncom_dict_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                                else:
                                                                    dict_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                        elif mh=="0":
                                                            if a.split(';')[0] == a.split(';')[1]:
                                                                if gp == "commit_average":
                                                                    com_dict_inf_rnd_square.update({(a,t,g,ag,b):s_data})
                                                                elif gp == "uncommit_average":
                                                                    uncom_dict_inf_rnd_square.update({(a,t,g,ag,b):s_data})
                                                                else:
                                                                    dict_inf_rnd_square.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                if gp == "commit_average":
                                                                    com_dict_inf_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                                elif gp == "uncommit_average":
                                                                    uncom_dict_inf_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                                else:
                                                                    dict_inf_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                        else:
                                                            if a.split(';')[0] == a.split(';')[1]:
                                                                if gp == "commit_average":
                                                                    com_dict_adapt_rnd_square.update({(a,t,g,ag,b):s_data})
                                                                elif gp == "uncommit_average":
                                                                    uncom_dict_adapt_rnd_square.update({(a,t,g,ag,b):s_data})
                                                                else:
                                                                    dict_adapt_rnd_square.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                if gp == "commit_average":
                                                                    com_dict_adapt_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                                elif gp == "uncommit_average":
                                                                    uncom_dict_adapt_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                                else:
                                                                    dict_adapt_rnd_rect.update({(a,t,g,ag,b):s_data})
                                                    elif int(c)==2:
                                                        if a.split(';')[0] == a.split(';')[1]:
                                                            if gp == "commit_average":
                                                                com_dict_fifo_square.update({(a,t,g,ag,b):s_data})
                                                            elif gp == "uncommit_average":
                                                                uncom_dict_fifo_square.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                dict_fifo_square.update({(a,t,g,ag,b):s_data})
                                                        else:
                                                            if gp == "commit_average":
                                                                com_dict_fifo_rect.update({(a,t,g,ag,b):s_data})
                                                            elif gp == "uncommit_average":
                                                                uncom_dict_fifo_rect.update({(a,t,g,ag,b):s_data})
                                                            else:
                                                                dict_fifo_rect.update({(a,t,g,ag,b):s_data})
        self.print_messages("tot_average",[dict_park_square,dict_adam_square,dict_fifo_square,dict_rnd_square,dict_inf_rnd_square,dict_adapt_rnd_square],[dict_park_rect,dict_adam_rect,dict_fifo_rect,dict_rnd_rect,dict_inf_rnd_rect,dict_adapt_rnd_rect],[arena,thr,gt,agents,buffer])
        self.print_dif_messages("dif_commit_average",[com_dict_park_square,com_dict_adam_square,com_dict_fifo_square,com_dict_rnd_square,com_dict_inf_rnd_square,com_dict_adapt_rnd_square],[uncom_dict_park_square,uncom_dict_adam_square,uncom_dict_fifo_square,uncom_dict_rnd_square,uncom_dict_inf_rnd_square,uncom_dict_adapt_rnd_square],[com_dict_park_rect,com_dict_adam_rect,com_dict_fifo_rect,com_dict_rnd_rect,com_dict_inf_rnd_rect,com_dict_adapt_rnd_rect],[uncom_dict_park_rect,uncom_dict_adam_rect,uncom_dict_fifo_rect,uncom_dict_rnd_rect,uncom_dict_inf_rnd_rect,uncom_dict_adapt_rnd_rect],[arena,thr,gt,agents,buffer])

##########################################################################################################
    def print_evolutions_by_commit(self,path,ground_T,threshlds,data_comm_sq,data_uncomm_sq,data_comm_rt,data_uncomm_rt,keys,more_k,msg_hop):
        typo        = [0,1,2,3,4,5]
        cNorm       = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap   = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        o_k         = keys
        dict_park_comm_sq,dict_adam_comm_sq,dict_fifo_comm_sq,dict_rnd_comm_sq,dict_inf_rnd_comm_sq,dict_adp_rnd_comm_sq              = data_comm_sq[0], data_comm_sq[1], data_comm_sq[2], data_comm_sq[3], data_comm_sq[4], data_comm_sq[5]
        dict_park_uncomm_sq,dict_adam_uncomm_sq,dict_fifo_uncomm_sq,dict_rnd_uncomm_sq,dict_inf_rnd_uncomm_sq,dict_adp_rnd_uncomm_sq  = data_uncomm_sq[0], data_uncomm_sq[1], data_uncomm_sq[2], data_uncomm_sq[3], data_uncomm_sq[4], data_uncomm_sq[5]
        dict_park_comm_rt,dict_adam_comm_rt,dict_fifo_comm_rt,dict_rnd_comm_rt,dict_inf_rnd_comm_rt,dict_adp_rnd_comm_rt              = data_comm_rt[0], data_comm_rt[1], data_comm_rt[2], data_comm_rt[3], data_comm_rt[4], data_comm_rt[5]
        dict_park_uncomm_rt,dict_adam_uncomm_rt,dict_fifo_uncomm_rt,dict_rnd_uncomm_rt,dict_inf_rnd_uncomm_rt,dict_adp_rnd_uncomm_rt  = data_uncomm_rt[0], data_uncomm_rt[1], data_uncomm_rt[2], data_uncomm_rt[3], data_uncomm_rt[4], data_uncomm_rt[5]
        o_k = sorted({int(x) for x in o_k})
        o_k = self._plot_tm_values("active", o_k)
        if not o_k:
            return
        ncols = len(o_k)
        arena           = more_k[0]
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        large_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='-', linewidth=10, label="LI")
        small_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=10, label="SI")
        handles_r       = []
        for pid in protocols_order:
            if not self._protocol_enabled("active", pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=protocol_colors.get(pid, "black"),
                    marker='_',
                    linestyle='None',
                    markeredgewidth=18,
                    markersize=18,
                    label=protocol.get("label", pid) if protocol else pid,
                )
            )
        handles_l       = [large_intrfc,small_intrfc]
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        for gt in ground_T:
            for thr in threshlds:
                cfig, cax = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
                ufig, uax = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
                for m_h in msg_hop:
                    for a in arena:
                        if a=="0_500;0_500" or a=="1_000;0_250":
                            agents = ["25"]
                        else:
                            agents = more_k[1]
                        for ag in agents:
                            if int(ag) == 25:
                                if a == "0_500;0_500" or a == "1_000;0_250": row=1
                                elif a =="1_000;1_000" or a =="2_000;0_500": row=0
                            elif int(ag) == 100: row=2
                            for k in range(len(o_k)):
                                if self._protocol_enabled("active", "P.1.0") and dict_park_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_park_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.0.0") and dict_adam_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_adam_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.2.0") and dict_fifo_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_fifo_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.1.1") and dict_rnd_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_rnd_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.1.0") and dict_inf_rnd_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_inf_rnd_comm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls='-')
                                if self._protocol_enabled("active", "P.1.0") and dict_park_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_park_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.0.0") and dict_adam_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_adam_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.2.0") and dict_fifo_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_fifo_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.1.1") and dict_rnd_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_rnd_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.1.0") and dict_inf_rnd_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    cax[row][k].plot(dict_inf_rnd_comm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls='--')
                                cax[row][k].set_xlim(0,901)
                                cax[row][k].set_ylim(-0.03,1.03)
                                if self._protocol_enabled("active", "P.1.0") and dict_park_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_park_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.0.0") and dict_adam_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_adam_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.2.0") and dict_fifo_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_fifo_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.1.1") and dict_rnd_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_rnd_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.1.0") and dict_inf_rnd_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_inf_rnd_uncomm_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls='-')
                                if self._protocol_enabled("active", "P.1.0") and dict_park_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_park_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.0.0") and dict_adam_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_adam_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.2.0") and dict_fifo_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_fifo_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.1.1") and dict_rnd_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_rnd_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.1.0") and dict_inf_rnd_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    uax[row][k].plot(dict_inf_rnd_uncomm_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls='--')
                                uax[row][k].set_xlim(0,901)
                                uax[row][k].set_ylim(-0.03,1.03)
                                if len(real_x_ticks)==0:
                                    for x in range(0,901,50):
                                        if x%300 == 0:
                                            svoid_x_ticks.append('')
                                            void_x_ticks.append('')
                                            real_x_ticks.append(str(int(np.round(x,0))))
                                        else:
                                            void_x_ticks.append('')
                                    for _ in range(0,11,1):
                                        void_y_ticks.append('')
                                if row == 0:
                                    cax[row][k].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                                    cax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    caxt = cax[row][k].twiny()
                                    uax[row][k].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                                    uax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    uaxt = uax[row][k].twiny()
                                    labels = [item.get_text() for item in caxt.get_xticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    caxt.set_xticklabels(empty_string_labels)
                                    uaxt.set_xticklabels(empty_string_labels)
                                    caxt.set_xlabel(rf"$T_m = {int(o_k[k])}\, s$")
                                    uaxt.set_xlabel(rf"$T_m = {int(o_k[k])}\, s$")
                                elif row==2:
                                    cax[row][k].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
                                    cax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    uax[row][k].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
                                    uax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    cax[row][k].set_xlabel(r"$T\,  s$")
                                    uax[row][k].set_xlabel(r"$T\,  s$")
                                else:
                                    cax[row][k].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                                    cax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    uax[row][k].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                                    uax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    cax[row][k].set_yticks(np.arange(0,1.01,.1))
                                    uax[row][k].set_yticks(np.arange(0,1.01,.1))
                                    cax[row][k].set_ylabel(r"$Q(G,\tau)$")
                                    uax[row][k].set_ylabel(r"$Q(G,\tau)$")
                                elif k==ncols-1:
                                    cax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    caxt = cax[row][k].twinx()
                                    uax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    uaxt = uax[row][k].twinx()
                                    labels = [item.get_text() for item in caxt.get_yticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    caxt.set_yticklabels(empty_string_labels)
                                    uaxt.set_yticklabels(empty_string_labels)
                                    if row==0:
                                        caxt.set_ylabel("LD25")
                                        uaxt.set_ylabel("LD25")
                                    elif row==1:
                                        caxt.set_ylabel("HD25")
                                        uaxt.set_ylabel("HD25")
                                    elif row==2:
                                        caxt.set_ylabel("HD100")
                                        uaxt.set_ylabel("HD100")
                                else:
                                    cax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    uax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                cax[row][k].grid(True,which='major')
                                uax[row][k].grid(True,which='major')
                cfig.tight_layout()
                ufig.tight_layout()
                cfig_path = path+"T"+thr+"_G"+gt+"_activation_committed.pdf"
                ufig_path = path+"T"+thr+"_G"+gt+"_activation_uncommitted.pdf"
                legend_cols = len(handles_r + handles_l) if (handles_r or handles_l) else 1
                cfig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=legend_cols,loc='upper right',framealpha=0.7,borderaxespad=0)
                ufig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=legend_cols,loc='upper right',framealpha=0.7,borderaxespad=0)
                cfig.savefig(cfig_path, bbox_inches='tight')
                ufig.savefig(ufig_path, bbox_inches='tight')
                plt.close(cfig)
                plt.close(ufig)

##########################################################################################################
    def print_evolutions(self,path,ground_T,threshlds,data_in_sq,times_in_sq,data_in_rt,times_in_rt,keys,more_k,msg_hop):
        typo        = [0,1,2,3,4,5]
        cNorm       = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap   = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        o_k         = keys
        dict_park_sq,dict_adam_sq,dict_fifo_sq,dict_rnd_sq,dict_inf_rnd_sq,dict_adp_rnd_sq = data_in_sq[0], data_in_sq[1], data_in_sq[2], data_in_sq[3], data_in_sq[4], data_in_sq[5]
        dict_park_rt,dict_adam_rt,dict_fifo_rt,dict_rnd_rt,dict_inf_rnd_rt,dict_adp_rnd_rt = data_in_rt[0], data_in_rt[1], data_in_rt[2], data_in_rt[3], data_in_rt[4], data_in_rt[5]
        o_k = sorted({int(x) for x in o_k})
        o_k = self._plot_tm_values("active", o_k)
        if not o_k:
            return
        ncols = len(o_k)
        arena           = more_k[0]
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        large_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='-', linewidth=10, label="LI")
        small_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=10, label="SI")
        handles_r       = []
        for pid in protocols_order:
            if not self._protocol_enabled("active", pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=protocol_colors.get(pid, "black"),
                    marker='_',
                    linestyle='None',
                    markeredgewidth=18,
                    markersize=18,
                    label=protocol.get("label", pid) if protocol else pid,
                )
            )
        handles_l       = [large_intrfc,small_intrfc]
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        for gt in ground_T:
            for thr in threshlds:
                fig, ax = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
                for m_h in msg_hop:
                    for a in arena:
                        if a=="0_500;0_500" or a=="1_000;0_250":
                            agents = ["25"]
                        else:
                            agents = more_k[1]
                        for ag in agents:
                            if int(ag) == 25:
                                if a == "0_500;0_500" or a == "1_000;0_250": row=1
                                elif a =="1_000;1_000" or a =="2_000;0_500": row=0
                            elif int(ag) == 100: row=2
                            for k in range(len(o_k)):
                                if self._protocol_enabled("active", "P.1.0") and dict_park_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_park_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.0.0") and dict_adam_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_adam_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.2.0") and dict_fifo_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_fifo_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.1.1") and dict_rnd_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_rnd_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls='-')
                                if self._protocol_enabled("active", "O.1.0") and dict_inf_rnd_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_inf_rnd_sq.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls='-')
                                if self._protocol_enabled("active", "P.1.0") and dict_park_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_park_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.0.0") and dict_adam_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_adam_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.2.0") and dict_fifo_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_fifo_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.1.1") and dict_rnd_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_rnd_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls='--')
                                if self._protocol_enabled("active", "O.1.0") and dict_inf_rnd_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)) != None:
                                    ax[row][k].plot(dict_inf_rnd_rt.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls='--')
                                ax[row][k].set_xlim(0,901)
                                ax[row][k].set_ylim(-0.03,1.03)
                                if len(real_x_ticks)==0:
                                    for x in range(0,901,50):
                                        if x%300 == 0:
                                            svoid_x_ticks.append('')
                                            void_x_ticks.append('')
                                            real_x_ticks.append(str(int(np.round(x,0))))
                                        else:
                                            void_x_ticks.append('')
                                    for y in range(0,11,1):
                                        void_y_ticks.append('')
                                if row == 0:
                                    ax[row][k].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                                    ax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    axt = ax[row][k].twiny()
                                    labels = [item.get_text() for item in axt.get_xticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    axt.set_xticklabels(empty_string_labels)
                                    axt.set_xlabel(rf"$T_m = {int(o_k[k])}\, s$")
                                elif row==2:
                                    ax[row][k].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
                                    ax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                else:
                                    ax[row][k].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                                    ax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    ax[row][k].set_yticks(np.arange(0,1.01,.1))
                                    ax[row][k].set_ylabel(r"$Q(G,\tau)$")
                                elif k==ncols-1:
                                    ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    axt = ax[row][k].twinx()
                                    labels = [item.get_text() for item in axt.get_yticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    axt.set_yticklabels(empty_string_labels)
                                    if row==0:
                                        axt.set_ylabel("LD25")
                                    elif row==1:
                                        axt.set_ylabel("HD25")
                                    elif row==2:
                                        axt.set_ylabel("HD100")
                                else:
                                    ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                ax[row][k].grid(True,which='major')
                fig.tight_layout()
                fig_path = path+"T"+thr+"_G"+gt+"_activation.pdf"
                legend_cols = len(handles_r + handles_l) if (handles_r or handles_l) else 1
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=legend_cols,loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_messages(self,c_type,data_in_sq,data_in_rt,keys):
        typo        = [0,1,2,3,4,5]
        cNorm       = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap   = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        arena,thr,gt,agents,buffer = keys
        dict_park_sq,dict_adam_sq,dict_fifo_sq,dict_rnd_sq,dict_inf_rnd_sq, dict_adpt_rnd_sq = data_in_sq[0], data_in_sq[1], data_in_sq[2], data_in_sq[3], data_in_sq[4], data_in_sq[5]
        dict_park_rt,dict_adam_rt,dict_fifo_rt,dict_rnd_rt,dict_inf_rnd_rt, dict_adpt_rnd_rt = data_in_rt[0], data_in_rt[1], data_in_rt[2], data_in_rt[3], data_in_rt[4], data_in_rt[5]
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        large_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='-', linewidth=10, label="LI")
        small_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=10, label="SI")
        minbuflab       = mlines.Line2D([], [], color="black", marker='None', linestyle=':', linewidth=10, label=r"$min\|\mathcal{B}\|$")
        void_x_ticks    = []
        svoid_x_ticks   = []
        real_x_ticks    = []
        columns = sorted({int(b) for b in buffer})
        columns = self._plot_tm_values("messages", columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        handles_r       = []
        for pid in protocols_order:
            if not self._protocol_enabled("messages", pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=protocol_colors.get(pid, "black"),
                    marker='_',
                    linestyle='None',
                    markeredgewidth=18,
                    markersize=18,
                    label=protocol.get("label", pid) if protocol else pid,
                )
            )
        handles_l       = [large_intrfc,small_intrfc, minbuflab]
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in dict_adam_sq.keys():
            tmp =[]
            res = dict_adam_sq.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam_sq.update({k:tmp})
        for k in dict_park_sq.keys():
            tmp =[]
            res = dict_park_sq.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_park_sq.update({k:tmp})
        for k in dict_fifo_sq.keys():
            tmp =[]
            res = dict_fifo_sq.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_fifo_sq.update({k:tmp})
        for k in dict_rnd_sq.keys():
            tmp =[]
            res = dict_rnd_sq.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_rnd_sq.update({k:tmp})
        for k in dict_inf_rnd_sq.keys():
            tmp =[]
            res = dict_inf_rnd_sq.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_inf_rnd_sq.update({k:tmp})
        for k in dict_adam_rt.keys():
            tmp =[]
            res = dict_adam_rt.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam_rt.update({k:tmp})
        for k in dict_park_rt.keys():
            tmp =[]
            res = dict_park_rt.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_park_rt.update({k:tmp})
        for k in dict_fifo_rt.keys():
            tmp =[]
            res = dict_fifo_rt.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_fifo_rt.update({k:tmp})
        for k in dict_rnd_rt.keys():
            tmp =[]
            res = dict_rnd_rt.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_rnd_rt.update({k:tmp})
        for k in dict_inf_rnd_rt.keys():
            tmp =[]
            res = dict_inf_rnd_rt.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_inf_rnd_rt.update({k:tmp})
        for t in thr:
            for g in gt:
                fig, ax = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
                for a in arena:
                    for ag in agents:
                        row = -1
                        if int(ag) == 25:
                            if a == "0_500;0_500" or a == "1_000;0_250": row=1
                            elif a =="1_000;1_000" or a =="2_000;0_500": row=0
                        elif int(ag) == 100: row=2
                        for b in buffer:
                            col = col_index.get(str(int(b)))
                            if row!=-1 and col is not None:
                                min_buf = []
                                val = 5/(int(ag)-1)
                                for _ in range(900):
                                    min_buf.append(val)
                                ax[row][col].plot(min_buf,color="black",lw=4,ls=":")
                                ls = '-'
                                if self._protocol_enabled("messages", "P.1.0") and dict_park_sq.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_park_sq.get((a,t,g,ag,b)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.0.0") and dict_adam_sq.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_adam_sq.get((a,t,g,ag,b)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.2.0") and dict_fifo_sq.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_fifo_sq.get((a,t,g,ag,b)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.1") and dict_rnd_sq.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_rnd_sq.get((a,t,g,ag,b)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.0") and dict_inf_rnd_sq.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_inf_rnd_sq.get((a,t,g,ag,b)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls=ls)
                                ls ='--'
                                if self._protocol_enabled("messages", "P.1.0") and dict_park_rt.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_park_rt.get((a,t,g,ag,b)),color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.0.0") and dict_adam_rt.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_adam_rt.get((a,t,g,ag,b)),color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.2.0") and dict_fifo_rt.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_fifo_rt.get((a,t,g,ag,b)),color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.1") and dict_rnd_rt.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_rnd_rt.get((a,t,g,ag,b)),color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.0") and dict_inf_rnd_rt.get((a,t,g,ag,b)) != None:
                                    ax[row][col].plot(dict_inf_rnd_rt.get((a,t,g,ag,b)),color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls=ls)
                for y in range(ncols):
                    ax[2][y].grid(True)
                    ax[2][y].set_xlim(0,900)
                    ax[2][y].set_ylim(-0.03,1.03)
                    ax[2][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
                    ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                for x in range(2):
                    for y in range(ncols):
                        ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                        ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                        ax[x][y].grid(True)
                        ax[x][y].set_xlim(0,900)
                        ax[x][y].set_ylim(-0.03,1.03)
                for x in range(3):
                    for y in range(1,ncols):
                        labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                        empty_string_labels = ['']*len(labels)
                        ax[x][y].set_yticklabels(empty_string_labels)
                for idx, col_val in enumerate(columns):
                    axt=ax[0][idx].twiny()
                    labels = [item.get_text() for item in axt.get_xticklabels()]
                    empty_string_labels = ['']*len(labels)
                    axt.set_xticklabels(empty_string_labels)
                    axt.set_xlabel(rf"$T_m = {int(col_val)}\, s$")
                last_col = ncols - 1
                ayt0=ax[0][last_col].twinx()
                ayt1=ax[1][last_col].twinx()
                ayt2=ax[2][last_col].twinx()
                labels = [item.get_text() for item in ayt0.get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ayt0.set_yticklabels(empty_string_labels)
                ayt1.set_yticklabels(empty_string_labels)
                ayt2.set_yticklabels(empty_string_labels)
                ayt0.set_ylabel("LD25")
                ayt1.set_ylabel("HD25")
                ayt2.set_ylabel("HD100")
                ax[0][0].set_ylabel(r"$M$")
                ax[1][0].set_ylabel(r"$M$")
                ax[2][0].set_ylabel(r"$M$")
                for y in range(ncols):
                    ax[2][y].set_xlabel(r"$T\, (s)$")
                fig.tight_layout()
                if not os.path.exists(self.base+"/msgs_data/images/"):
                    os.mkdir(self.base+"/msgs_data/images/")
                fig_path = self.base+"/msgs_data/images/"+str(g).replace(".","_")+"_"+c_type+"_messages.pdf"
                legend_cols = len(handles_r + handles_l) if (handles_r or handles_l) else 1
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=legend_cols, loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_dif_messages(self,c_type,comm_data_in_sq,uncomm_data_in_sq,comm_data_in_rt,uncomm_data_in_rt,keys):
        typo        = [0,1,2,3,4,5]
        cNorm       = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap   = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        arena,thr,gt,agents,buffer  = keys
        comm_dict_park_sq,comm_dict_adam_sq,comm_dict_fifo_sq,comm_dict_rnd_sq,comm_dict_inf_rnd_sq,comm_dict_adp_rnd_sq              = comm_data_in_sq[0], comm_data_in_sq[1], comm_data_in_sq[2], comm_data_in_sq[3], comm_data_in_sq[4], comm_data_in_sq[5]
        uncomm_dict_park_sq,uncomm_dict_adam_sq,uncomm_dict_fifo_sq,uncomm_dict_rnd_sq,uncomm_dict_inf_rnd_sq,uncomm_dict_adp_rnd_sq  = uncomm_data_in_sq[0], uncomm_data_in_sq[1], uncomm_data_in_sq[2], uncomm_data_in_sq[3], uncomm_data_in_sq[4], uncomm_data_in_sq[5]
        comm_dict_park_rt,comm_dict_adam_rt,comm_dict_fifo_rt,comm_dict_rnd_rt,comm_dict_inf_rnd_rt,comm_dict_adp_rnd_rt              = comm_data_in_rt[0], comm_data_in_rt[1], comm_data_in_rt[2], comm_data_in_rt[3], comm_data_in_rt[4], comm_data_in_rt[5]
        uncomm_dict_park_rt,uncomm_dict_adam_rt,uncomm_dict_fifo_rt,uncomm_dict_rnd_rt,uncomm_dict_inf_rnd_rt,uncomm_dict_adp_rnd_rt  = uncomm_data_in_rt[0], uncomm_data_in_rt[1], uncomm_data_in_rt[2], uncomm_data_in_rt[3], uncomm_data_in_rt[4], uncomm_data_in_rt[5]
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        large_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='-', linewidth=10, label="LI")
        small_intrfc    = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=10, label="SI")
        void_x_ticks    = []
        svoid_x_ticks   = []
        real_x_ticks    = []
        columns = sorted({int(b) for b in buffer})
        columns = self._plot_tm_values("messages", columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        handles_r       = []
        for pid in protocols_order:
            if not self._protocol_enabled("messages", pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=protocol_colors.get(pid, "black"),
                    marker='_',
                    linestyle='None',
                    markeredgewidth=18,
                    markersize=18,
                    label=protocol.get("label", pid) if protocol else pid,
                )
            )
        handles_l       = [large_intrfc,small_intrfc]
        fig, ax         = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for t in thr:
            for g in gt:
                fig, ax = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
                for a in arena:
                    for ag in agents:
                        row = -1
                        if int(ag) == 25:
                            if a == "0_500;0_500" or a == "1_000;0_250": row=1
                            elif a =="1_000;1_000" or a =="2_000;0_500": row=0
                        elif int(ag) == 100: row=2
                        for b in buffer:
                            col = col_index.get(str(int(b)))
                            if row!=-1 and col is not None:
                                ls = '-'
                                if self._protocol_enabled("messages", "P.1.0") and comm_dict_park_sq.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_park_sq.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_park_sq.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.0.0") and comm_dict_adam_sq.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_adam_sq.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_adam_sq.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.2.0") and comm_dict_fifo_sq.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_fifo_sq.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_fifo_sq.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.1") and comm_dict_rnd_sq.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_rnd_sq.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_rnd_sq.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.0") and comm_dict_inf_rnd_sq.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_inf_rnd_sq.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_inf_rnd_sq.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls=ls)
                                ls = '--'
                                if self._protocol_enabled("messages", "P.1.0") and comm_dict_park_rt.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_park_rt.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_park_rt.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("P.1.0", scalarMap.to_rgba(typo[0])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.0.0") and comm_dict_adam_rt.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_adam_rt.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_adam_rt.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.0.0", scalarMap.to_rgba(typo[1])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.2.0") and comm_dict_fifo_rt.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_fifo_rt.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_fifo_rt.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.2.0", scalarMap.to_rgba(typo[2])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.1") and comm_dict_rnd_rt.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_rnd_rt.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_rnd_rt.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.1.1", scalarMap.to_rgba(typo[3])),lw=6,ls=ls)
                                if self._protocol_enabled("messages", "O.1.0") and comm_dict_inf_rnd_rt.get((a,t,g,ag,b)) != None:
                                    comm_flag   = comm_dict_inf_rnd_rt.get((a,t,g,ag,b))
                                    uncomm_flag = uncomm_dict_inf_rnd_rt.get((a,t,g,ag,b))
                                    flag = []
                                    for i in range(len(comm_flag)):
                                        denom = comm_flag[i] + uncomm_flag[i]
                                        if denom != 0:
                                            flag.append((comm_flag[i]-uncomm_flag[i]) / denom)
                                        else:
                                            flag.append(0)
                                    ax[row][col].plot(flag,color=protocol_colors.get("O.1.0", scalarMap.to_rgba(typo[4])),lw=6,ls=ls)
                for y in range(ncols):
                    ax[2][y].grid(True)
                    ax[2][y].set_xlim(0,900)
                    ax[2][y].set_ylim(-0.03,0.63)
                    ax[2][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
                    ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                for x in range(2):
                    for y in range(ncols):
                        ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                        ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                        ax[x][y].grid(True)
                        ax[x][y].set_xlim(0,900)
                        ax[x][y].set_ylim(-0.03,0.63)
                for x in range(3):
                    for y in range(1,ncols):
                        labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                        empty_string_labels = ['']*len(labels)
                        ax[x][y].set_yticklabels(empty_string_labels)
                for idx, col_val in enumerate(columns):
                    axt=ax[0][idx].twiny()
                    labels = [item.get_text() for item in axt.get_xticklabels()]
                    empty_string_labels = ['']*len(labels)
                    axt.set_xticklabels(empty_string_labels)
                    axt.set_xlabel(rf"$T_m = {int(col_val)}\, s$")
                last_col = ncols - 1
                ayt0=ax[0][last_col].twinx()
                ayt1=ax[1][last_col].twinx()
                ayt2=ax[2][last_col].twinx()
                labels = [item.get_text() for item in ayt0.get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ayt0.set_yticklabels(empty_string_labels)
                ayt1.set_yticklabels(empty_string_labels)
                ayt2.set_yticklabels(empty_string_labels)
                ayt0.set_ylabel("LD25")
                ayt1.set_ylabel("HD25")
                ayt2.set_ylabel("HD100")
                ax[0][0].set_ylabel(r"$\Delta M$")
                ax[1][0].set_ylabel(r"$\Delta M$")
                ax[2][0].set_ylabel(r"$\Delta M$")
                for y in range(ncols):
                    ax[2][y].set_xlabel(r"$T\, (s)$")
                fig.tight_layout()
                if not os.path.exists(self.base+"/msgs_data/images/"):
                    os.mkdir(self.base+"/msgs_data/images/")
                fig_path = self.base+"/msgs_data/images/"+str(g).replace(".","_")+"_"+c_type+"_messages.pdf"
                legend_cols = len(handles_r + handles_l) if (handles_r or handles_l) else 1
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=legend_cols, loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)
    
