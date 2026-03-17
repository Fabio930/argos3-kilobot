import numpy as np
import os, csv, logging, json
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})
class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "proc_data" or elem == "msgs_data":
                self.bases.append(os.path.join(self.base, elem))
        self.plot_config = self._load_plot_config()
        self.protocols = self.plot_config.get("protocols", [])
        self.protocols_by_key = {p.get("key"): p for p in self.protocols if p.get("key") is not None}

##########################################################################################################
    def _default_plot_config(self):
        return {
            "protocols": [
                {"key": "AN", "id": 0, "label": r"$AN$", "color": "red", "legend": False},
                {"key": "AN_t", "id": 1, "label": r"$AN_{t}$", "color": "viridis:0", "legend": True},
                {"key": "ID+B", "id": 2, "label": r"$ID+B$", "color": "viridis:1", "legend": True},
                {"key": "ID+R_f", "id": 3, "label": r"$ID+R_{f}$", "color": "viridis:2", "legend": True},
                {"key": "ID+R_1", "id": 4, "label": r"$ID+R_{1}$", "color": "viridis:3", "legend": True},
                {"key": "ID+R_inf", "id": 5, "label": r"$ID+R_{\\infty}$", "color": "viridis:4", "legend": True},
                {"key": "ID+R_a", "id": 6, "label": r"$ID+R_{a}$", "color": "viridis:5", "legend": True},
            ],
            "plots": {
                "activation": {
                    "exclude_protocols": [],
                    "columns": [60, 120, 180, 300, 600],
                },
                "messages": {
                    "exclude_protocols": [],
                    "columns": [60, 120, 180, 300, 600],
                },
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
    def _plot_columns(self, plot_name, default_cols):
        plot_cfg = self.plot_config.get("plots", {}).get(plot_name, {})
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
    def _protocol_enabled(self, plot_name, protocol_key):
        protocol = self.protocols_by_key.get(protocol_key)
        plot_cfg = self.plot_config.get("plots", {}).get(plot_name, {})
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

        # helper used when the same logical configuration appears with different msg_hops
        def add_or_merge(dct, key, series):
            """store a new time series or average with an existing one"""
            if key in dct:
                old = dct[key]
                if len(old) == len(series):
                    dct[key] = [(x + y) / 2 for x, y in zip(old, series)]
                else:
                    # mismatched lengths are unexpected; prefer the new one
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
        # self.print_evolutions_anonymous(path,ground_T,threshlds,[dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state,dict_park_state_real],[dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time,dict_park_time_real],o_k,[arena,agents])

##########################################################################################################
    def print_evolutions(self,path,ground_T,threshlds,data_in,times_in,keys,more_k):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adapt, dict_park_real = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5],data_in[6]
        o_k = [int(x) for x in keys]
        o_k = sorted(set(o_k))
        columns = self._plot_columns("activation", o_k)
        columns = [c for c in columns if c in o_k]
        if not columns:
            columns = o_k
        col_index = {c: i for i, c in enumerate(columns)}
        ncols = len(columns)
        arena   = more_k[0]
        protocol_colors = {p.get("key"): self._protocol_color(p, scalarMap) for p in self.protocols}
        handles_r = []
        for p in self.protocols:
            if not p.get("legend", True):
                continue
            if not self._protocol_enabled("activation", p.get("key")):
                continue
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=self._protocol_color(p, scalarMap),
                    marker='_',
                    linestyle='None',
                    markeredgewidth=18,
                    markersize=18,
                    label=p.get("label", p.get("key")),
                )
            )
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        for gt in ground_T:
            for thr in threshlds:
                fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
                for a in arena:
                    if a=="smallA":
                        row = 1
                        agents = ["25"]
                    else:
                        row = 0
                        agents = more_k[1]
                    for ag in agents:
                        if int(ag)==100: row = 2
                        for col_val in columns:
                            col = col_index[col_val]
                            key = (a,ag,str(col_val),gt,thr)
                            if self._protocol_enabled("activation", "AN") and dict_park_real.get(key) != None:
                                ax[row][col].plot(dict_park_real.get(key),color=protocol_colors.get("AN","red"),lw=6)
                            if self._protocol_enabled("activation", "AN_t") and dict_park.get(key) != None:
                                ax[row][col].plot(dict_park.get(key),color=protocol_colors.get("AN_t",scalarMap.to_rgba(typo[0])),lw=6)
                            if self._protocol_enabled("activation", "ID+B") and dict_adam.get(key) != None:
                                ax[row][col].plot(dict_adam.get(key),color=protocol_colors.get("ID+B",scalarMap.to_rgba(typo[1])),lw=6)
                            if self._protocol_enabled("activation", "ID+R_f") and dict_fifo.get(key) != None:
                                ax[row][col].plot(dict_fifo.get(key),color=protocol_colors.get("ID+R_f",scalarMap.to_rgba(typo[2])),lw=6)
                            if self._protocol_enabled("activation", "ID+R_1") and dict_rnd.get(key) != None:
                                ax[row][col].plot(dict_rnd.get(key),color=protocol_colors.get("ID+R_1",scalarMap.to_rgba(typo[3])),lw=6)
                            if self._protocol_enabled("activation", "ID+R_inf") and dict_rnd_inf.get(key) != None:
                                ax[row][col].plot(dict_rnd_inf.get(key),color=protocol_colors.get("ID+R_inf",scalarMap.to_rgba(typo[4])),lw=6)
                            if self._protocol_enabled("activation", "ID+R_a") and dict_rnd_adapt.get(key) != None:
                                ax[row][col].plot(dict_rnd_adapt.get(key),color=protocol_colors.get("ID+R_a",scalarMap.to_rgba(typo[5])),lw=6)
                            ax[row][col].set_xlim(0,1201)
                            ax[row][col].set_ylim(-0.03,1.03)
                            if len(real_x_ticks)==0:
                                for x in range(0,1201,50):
                                    if x%300 == 0:
                                        svoid_x_ticks.append('')
                                        void_x_ticks.append('')
                                        real_x_ticks.append(str(int(np.round(x,0))))
                                    else:
                                        void_x_ticks.append('')
                                for y in range(0,11,1):
                                    void_y_ticks.append('')
                            if row == 0:
                                ax[row][col].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][col].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                axt = ax[row][col].twiny()
                                labels = [item.get_text() for item in axt.get_xticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_xticklabels(empty_string_labels)
                                axt.set_xlabel(rf"$T_m = {int(col_val)}\, s$")
                            elif row==2:
                                ax[row][col].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
                                ax[row][col].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                ax[row][col].set_xlabel(r"$T\,  s$")
                            else:
                                ax[row][col].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][col].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                            if col == 0:
                                ax[row][col].set_yticks(np.arange(0,1.01,.1))
                                ax[row][col].set_ylabel(r"$Q(G,\tau)$")
                            else:
                                ax[row][col].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                            if col == (ncols - 1):
                                axt = ax[row][col].twinx()
                                labels = [item.get_text() for item in axt.get_yticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_yticklabels(empty_string_labels)
                                if row==0:
                                    axt.set_ylabel("LD25")
                                elif row==1:
                                    axt.set_ylabel("HD25")
                                elif row==2:
                                    axt.set_ylabel("HD100")
                            ax[row][col].grid(which='major')
                fig.tight_layout()
                fig_path = path+thr+"_"+gt.replace(';','_')+"_activation.pdf"
                if handles_r:
                    fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=len(handles_r),loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_evolutions_anonymous(self,path,ground_T,threshlds,data_in,times_in,keys,more_k):
        # Plots only anonymous protocols (AN_t and AN real) for msg_exp_time 60 and 0.
        # 3 rows (LD25, smallA, HD100) and 2 columns: left shows High->Low transitions, right Low->High.
        typo = [0]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,_,_,_,_,_, dict_park_real = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5], data_in[6]
        arena = more_k[0]
        agents_list = more_k[1]

        # choose ground truth for H2L and L2H explicitly to avoid mis‑detection
        gt_h2l = None
        gt_l2h = None
        if len(ground_T) >= 2:
            # assume higher value corresponds to high->low, lower to low->high
            try:
                sorted_gt = sorted(ground_T, key=lambda x: float(x))
                gt_l2h = sorted_gt[0]
                gt_h2l = sorted_gt[-1]
            except Exception:
                # non-numeric values: fall back to first/second
                gt_l2h = ground_T[0]
                gt_h2l = ground_T[1]
        elif ground_T:
            # only one value available; use it for both sides
            gt_l2h = gt_h2l = ground_T[0]
        # earlier logic ensured keys exist but we can optionally keep trend detection as sanity
        # if a chosen gt has no data, nothing will plot in that column

        if not os.path.exists(self.base+"/proc_data/images/"):
            os.makedirs(self.base+"/proc_data/images/", exist_ok=True)

        for thr in threshlds:
            fig, ax = plt.subplots(nrows=3, ncols=2, figsize=(19,16))
            # rows mapping same as other methods
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

                    # left column: high->low
                    if gt_h2l is not None:
                        # AN_t at msg_exp_time=60
                        s = dict_park.get((a,ag,"60",gt_h2l,thr))
                        if s is not None:
                            ax[row][0].plot(s, color=scalarMap.to_rgba(typo[0]), lw=4)
                        # AN real (originally msg_exp_time 0 stored as "60") in red
                        sr = dict_park_real.get((a,ag,"60",gt_h2l,thr))
                        if sr is not None:
                            ax[row][0].plot(sr, color="red", lw=4)

                    # right column: low->high
                    if gt_l2h is not None:
                        s = dict_park.get((a,ag,"60",gt_l2h,thr))
                        if s is not None:
                            ax[row][1].plot(s, color=scalarMap.to_rgba(typo[0]), lw=4)
                        sr = dict_park_real.get((a,ag,"60",gt_l2h,thr))
                        if sr is not None:
                            ax[row][1].plot(sr, color="red", lw=4)

            # formatting ticks/labels
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
                    # ensure y ticks from 0 to 1 every 0.1
                    ax[r][c].set_yticks(np.arange(0,1.01,0.1))
                    if c==0:
                        ax[r][c].set_ylabel(r"$Q(G,\tau)$")
                    # grid
                    ax[r][c].grid(True)

            # add row labels (LD25, HD25, HD100) on the right column using twin y axes
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

            # top twin labels for columns
            axt0 = ax[0][0].twiny()
            axt1 = ax[0][1].twiny()
            labels0 = [item.get_text() for item in axt0.get_xticklabels()]
            empty0 = ['']*len(labels0)
            axt0.set_xticklabels(empty0)
            axt1.set_xticklabels(empty0)
            axt0.set_xlabel(r"$G_{i}=0.92,G_{f}=0.68$")
            axt1.set_xlabel(r"$G_{i}=0.68,G_{f}=0.92$")

            # bottom row x labels
            for c in range(2):
                ax[2][c].set_xticks(np.arange(0,1201,300), labels=real_x_ticks)
                ax[2][c].set_xticks(np.arange(0,1201,50), labels=void_x_ticks, minor=True)
                ax[2][c].set_xlabel(r"$T\, (s)$")

            fig.tight_layout()
            fig_path = self.base+"/proc_data/images/"+thr+"_anonymous_60_0_activation.pdf"
            # create legend: AN_t and AN (red)
            an_t = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$AN_{t}$")
            an_r = mlines.Line2D([], [], color="red", marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$AN$")
            fig.legend(bbox_to_anchor=(1, 0), handles=[an_r, an_t], ncols=2, loc='upper right', framealpha=0.7, borderaxespad=0)
            fig.savefig(fig_path, bbox_inches='tight')
            plt.close(fig)

##########################################################################################################
    def print_messages(self,data_in):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adpt,dict_park_real = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5], data_in[6]
        protocol_colors = {p.get("key"): self._protocol_color(p, scalarMap) for p in self.protocols}
        handles_r = []
        for p in self.protocols:
            if not p.get("legend", True):
                continue
            if not self._protocol_enabled("messages", p.get("key")):
                continue
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=self._protocol_color(p, scalarMap),
                    marker='_',
                    linestyle='None',
                    markeredgewidth=18,
                    markersize=18,
                    label=p.get("label", p.get("key")),
                )
            )
        svoid_x_ticks   = []
        void_x_ticks    = []
        real_x_ticks    = []
        all_cols = set()
        for dct in (dict_park_real, dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adpt):
            for k in dct.keys():
                try:
                    all_cols.add(int(k[5]))
                except Exception:
                    continue
        default_cols = sorted(all_cols) if all_cols else [60, 120, 180, 300, 600]
        columns = self._plot_columns("messages", default_cols)
        columns = [c for c in columns if c in default_cols]
        if not columns:
            columns = default_cols
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)

        if len(real_x_ticks)==0:
            for x in range(0,1201,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
        for k in dict_park_real.keys():
            tmp =[]
            res = dict_park_real.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_park_real.update({k:tmp})
        for k in dict_park.keys():
            tmp =[]
            res = dict_park.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_park.update({k:tmp})
        for k in dict_adam.keys():
            tmp =[]
            res = dict_adam.get(k)
            norm = int(k[4])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam.update({k:tmp})
        for k in dict_fifo.keys():
            tmp =[]
            res = dict_fifo.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_fifo.update({k:tmp})
        for k in dict_rnd.keys():
            tmp =[]
            res = dict_rnd.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd.update({k:tmp})
        for k in dict_rnd_inf.keys():
            tmp =[]
            res = dict_rnd_inf.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_inf.update({k:tmp})
        for k in dict_rnd_adpt.keys():
            tmp =[]
            res = dict_rnd_adpt.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_adpt.update({k:tmp})
        for k in dict_park_real.keys():
            if not self._protocol_enabled("messages", "AN"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            min_buf = []
            val = 5/(int(k[4])-1)
            for i in range(1200):
                min_buf.append(val)
            ax[row][col].plot(min_buf,color="black",lw=4,ls="--")
            ax[row][col].plot(dict_park_real.get(k),color=protocol_colors.get("AN","red"),lw=6)
        for k in dict_park.keys():
            if not self._protocol_enabled("messages", "AN_t"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            ax[row][col].plot(dict_park.get(k),color=protocol_colors.get("AN_t",scalarMap.to_rgba(typo[0])),lw=6)
        for k in dict_adam.keys():
            if not self._protocol_enabled("messages", "ID+B"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            ax[row][col].plot(dict_adam.get(k),color=protocol_colors.get("ID+B",scalarMap.to_rgba(typo[1])),lw=6)
        for k in dict_fifo.keys():
            if not self._protocol_enabled("messages", "ID+R_f"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            ax[row][col].plot(dict_fifo.get(k),color=protocol_colors.get("ID+R_f",scalarMap.to_rgba(typo[2])),lw=6)
        for k in dict_rnd.keys():
            if not self._protocol_enabled("messages", "ID+R_1"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd.get(k),color=protocol_colors.get("ID+R_1",scalarMap.to_rgba(typo[3])),lw=6)
        for k in dict_rnd_inf.keys():
            if not self._protocol_enabled("messages", "ID+R_inf"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd_inf.get(k),color=protocol_colors.get("ID+R_inf",scalarMap.to_rgba(typo[4])),lw=6)
        for k in dict_rnd_adpt.keys():
            if not self._protocol_enabled("messages", "ID+R_a"):
                continue
            if k[5] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[5])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd_adpt.get(k),color=protocol_colors.get("ID+R_a",scalarMap.to_rgba(typo[5])),lw=6)
        for x in range(2):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,ncols):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(ncols):
            ax[2][y].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)

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
        for x in range(3):
            for y in range(ncols):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,1201)
                ax[x][y].set_ylim(-0.03,1.03)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/messages.pdf"
        if handles_r:
            fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=len(handles_r), loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
