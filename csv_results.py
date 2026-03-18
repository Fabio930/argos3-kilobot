import os, csv, logging, re, json
import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib import pyplot as plt
from lifelines import WeibullFitter,KaplanMeierFitter
from scipy.special import gamma
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})

##########################################################################################################
class Data:
    _FLOAT_RE = re.compile(r"(?i)(?:[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?|[-+]?inf|nan)")
    _INT_RE = re.compile(r"-?\d+")

###################################################
    @staticmethod
    def _parse_float_list(raw, allow_dash=False):
        raw = raw.strip()
        if allow_dash and raw == "-":
            return [-1.0]
        if raw and raw[0] == "[" and raw[-1] == "]":
            raw = raw[1:-1]
        if "[" in raw or "]" in raw:
            raw = raw.replace("[", "").replace("]", "")
        if not raw:
            return []
        return [float(x) for x in Data._FLOAT_RE.findall(raw)]

###################################################
    @staticmethod
    def _parse_int_list(raw):
        raw = raw.strip()
        if raw and raw[0] == "[" and raw[-1] == "]":
            raw = raw[1:-1]
        if "[" in raw or "]" in raw:
            raw = raw.replace("[", "").replace("]", "")
        if not raw:
            return []
        return [int(x) for x in Data._INT_RE.findall(raw)]
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "msgs_data" or elem == "proc_data" or elem == "rec_data" or elem=="dec_data":
                self.bases.append(os.path.join(self.base, elem))
        self.plot_config = self._load_plot_config()
        self.protocols = self.plot_config.get("protocols", [])
        self.protocols_by_id = {p.get("id"): p for p in self.protocols if p.get("id") is not None}

###################################################
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
                "messages": {"exclude_protocols": [], "exclude_tm": []},
                "decisions": {"exclude_protocols": [], "exclude_tm": []},
                "active": {"exclude_protocols": [], "exclude_tm": []},
                "recovery": {"exclude_protocols": [], "exclude_tm": []},
            },
        }

###################################################
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

###################################################
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

###################################################
    def apply_plot_overrides(self, plot_names, exclude_protocols=None, exclude_tm=None):
        if not plot_names:
            return
        for plot_name in plot_names:
            plot_cfg = self.plot_config.setdefault("plots", {}).setdefault(plot_name, {})
            if exclude_protocols is not None:
                plot_cfg["exclude_protocols"] = exclude_protocols
            if exclude_tm is not None:
                plot_cfg["exclude_tm"] = exclude_tm

###################################################
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

###################################################
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
            nv = self._normalize_tm(v) if not isinstance(v, int) else v
            if nv is None or nv in exclude_set:
                continue
            out.append(v)
        return out

###################################################
    def _protocol_matches(self, protocol, selector):
        if protocol is None:
            return False
        if selector is None:
            return False
        sel = str(selector).strip()
        return sel == protocol.get("id") or sel == protocol.get("label")

###################################################
    def _protocol_enabled(self, plot_name, protocol_id):
        protocol = self.protocols_by_id.get(protocol_id)
        plot_cfg = self.plot_config.get("plots", {}).get(plot_name, {})
        exclude = plot_cfg.get("exclude_protocols") or []
        if any(self._protocol_matches(protocol, sel) for sel in exclude):
            return False
        return True

###################################################
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

###################################################
    def wb_get_mean_and_std(self, wf:WeibullFitter):
        # get the Weibull shape and scale parameter 
        scale, shape = wf.summary.loc['lambda_','coef'], wf.summary.loc['rho_','coef']

        # calculate the mean time
        mean = scale*gamma(1 + 1/shape)
        # calculate the standard deviation
        variance = (scale ** 2) * (gamma(1 + 2 / shape) - (gamma(1 + 1 / shape)) ** 2)
        std = np.sqrt(variance)
        
        return [mean, std]
    
###################################################
    def fit_recovery(self,algo,arena,n_agents,buf_dim,gt,thr,comunication,msg_hops,data_in):
        buff_starts     = data_in[0]
        durations       = data_in[1]
        event_observed  = data_in[2]
        # if not os.path.exists(self.base+"/weib_images/"):
        #     os.mkdir(self.base+"/weib_images/")
        # path = self.base+"/weib_images/"

        durations_by_buffer = self.dull_division(buff_starts,durations,event_observed)
        durations_by_buffer = self.sort_arrays_in_dict(durations_by_buffer)
        adapted_durations = self.adapt_dict_to_weibull_est(durations_by_buffer)
        wf = WeibullFitter()
        kmf = KaplanMeierFitter()
        estimates = {}
        for k in adapted_durations.keys():
            a_data = adapted_durations.get(k)[0]
            a_censoring = adapted_durations.get(k)[1]
            a_buffers = adapted_durations.get(k)[2]
            if len(a_data)>100:
                wf.fit(a_data, event_observed=a_censoring,label="wf "+k)
                kmf.fit(a_data, event_observed=a_censoring,label="kmf "+k)
                # fig, ax = plt.subplots(figsize=(10,8))
                # ax.plot(wf.cumulative_density_)
                # ax.plot(kmf.cumulative_density_)
                # fig.tight_layout()
                # fig.savefig(path+algo+'_'+comunication+'_'+msg_hops+'_'+n_agents+'_'+arena+'_'+buf_dim+'_'+gt+'_'+thr+'_'+k+'.png')
                estimates.update({k:[self.wb_get_mean_and_std(wf),len(a_buffers)-1]})
        return estimates

###################################################
    def fit_recovery_raw_data(self,data_in):
        fitted_data = {}
        for i in range(len(data_in)):
            for k in data_in[i].keys():
                estimates = self.fit_recovery(k[0],k[1],k[4],k[5],k[8],k[9],k[3],k[7],data_in[i].get(k))
                for z in estimates.keys():
                    fitted_data.update({(k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7],k[8],k[9],z):estimates.get(z)})
        return fitted_data
    
###################################################
    def dull_division(self,buffer,durations,event_observed):
        return {"all": [list(durations), list(event_observed), list(buffer)]}
    
###################################################
    def adapt_dict_to_weibull_est(self,data):
        out = {}
        for k in data.keys():
            durations = data.get(k)[0]
            event_observed = data.get(k)[1]
            buffers = data.get(k)[2]
            if len(durations)>0:
                if durations[0] > 0: durations,event_observed,buffers = np.insert(durations,0,0),np.insert(event_observed,0,0),np.insert(buffers,0,0)
                durations = list(durations)
                event_observed = list(event_observed)
                buffers = list(buffers)
                for i in range(len(durations)):
                    if durations[i] == 0: durations[i] = .00000001
            out.update({k:[durations,event_observed,buffers]})
        return out
    
###################################################
    def sort_arrays_in_dict(self,data_to_sort):
        out = {}
        for k in data_to_sort.keys():
            durations = np.asarray(data_to_sort.get(k)[0])
            event_observed = np.asarray(data_to_sort.get(k)[1])
            buffers = np.asarray(data_to_sort.get(k)[2])
            if durations.size > 1:
                order = np.argsort(durations)
                durations = durations[order]
                event_observed = event_observed[order]
                buffers = buffers[order]
            out.update({k:[durations.tolist(),event_observed.tolist(),buffers.tolist()]})
        return out

###################################################
    def plot_messages(self,data):
        dict_park, dict_park_t1, dict_park_real_fifo, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{},{},{}
        std_dict_park, std_dict_park_t1, std_dict_park_real_fifo, std_dict_adam, std_dict_fifo,std_dict_rnd,std_dict_rnd_inf = {},{},{},{},{},{},{}
        for k in data.keys():
            algo = str(k[1]).strip().lower()
            n_agents = int(k[3]) if len(k) > 3 else 0
            buff_dim = int(k[4]) if len(k) > 4 else 0
            is_priority_sampling = algo == 'ps' or (algo == 'p' and buff_dim == max(0, n_agents - 2))

            if is_priority_sampling and buff_dim > 0:
                dict_park_t1.update({(k[0],k[3],k[4]):data.get(k)[0]})
                std_dict_park_t1.update({(k[0],k[3],k[4]):data.get(k)[1]})
            elif k[1]=='P' and int(k[4]) > 0:
                dict_park.update({(k[0],k[3],k[4]):data.get(k)[0]})
                std_dict_park.update({(k[0],k[3],k[4]):data.get(k)[1]})
            elif k[1]=='P' and int(k[4]) == 0:
                dict_park_real_fifo.update({(k[0],k[3],k[4]):data.get(k)[0]})
                std_dict_park_real_fifo.update({(k[0],k[3],k[4]):data.get(k)[1]})
            else:
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4]):data.get(k)[0]})
                    std_dict_adam.update({(k[0],k[3],k[4]):data.get(k)[1]})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4]):data.get(k)[0]})
                    std_dict_fifo.update({(k[0],k[3],k[4]):data.get(k)[1]})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4]):data.get(k)[0]})
                        std_dict_rnd.update({(k[0],k[3],k[4]):data.get(k)[1]})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4]):data.get(k)[0]})
                        std_dict_rnd_inf.update({(k[0],k[3],k[4]):data.get(k)[1]})

        self.print_messages([dict_park,dict_park_t1,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_park_real_fifo],[std_dict_park,std_dict_park_t1,std_dict_adam,std_dict_fifo,std_dict_rnd,std_dict_rnd_inf,std_dict_park_real_fifo])


###################################################
    def plot_decisions(self,data):
        dict_park, dict_park_t1, dict_park_real_fifo, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{},{},{}
        for k in data.keys():
            algo = str(k[1]).strip().lower()
            n_agents = int(k[3]) if len(k) > 3 else 0
            buf_dim = int(k[4]) if len(k) > 4 else 0
            is_priority_sampling = algo == 'ps' or (algo == 'p' and buf_dim == max(0, n_agents - 2))

            if is_priority_sampling and buf_dim > 0:
                dict_park_t1.update({(k[0],k[3],k[4]):data.get(k)})
            elif is_priority_sampling and buf_dim == 0:
                dict_park_real_fifo.update({(k[0],k[3],k[4]):data.get(k)})
            elif k[1]=='P' and int(k[4]) > 0:
                dict_park.update({(k[0],k[3],k[4]):data.get(k)})
            elif k[1]=='P' and int(k[4]) == 0:
                dict_park_real_fifo.update({(k[0],k[3],k[4]):data.get(k)})
            else:
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4]):data.get(k)})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4]):data.get(k)})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4]):data.get(k)})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4]):data.get(k)})
        self.print_decisions([dict_park,dict_park_t1,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_park_real_fifo])

###################################################
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
                if len(keys) >= 6:
                    data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):(array_val,[])})
        return data
    
###################################################
    def read_msgs_csv_w_std(self,path):
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header:
                return data
            header_cols = header.rstrip('\n').split('\t')
            try:
                data_idx = header_cols.index("data")
            except ValueError:
                data_idx = max(len(header_cols) - 2, 0)
            try:
                std_idx = header_cols.index("std")
            except ValueError:
                std_idx = data_idx + 1
            for line in f:
                line = line.strip('\n')
                if not line:
                    continue
                cols = line.split('\t')
                if len(cols) <= max(data_idx, std_idx):
                    continue
                keys = cols[:data_idx]
                array_val = self._parse_float_list(cols[data_idx])
                std_val = self._parse_float_list(cols[std_idx], allow_dash=True)
                if len(keys) >= 6:
                    data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):(array_val,std_val)})
        return data

###################################################
    def read_recovery_csv(self,path,algo,arena):
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header:
                return data
            header_cols = header.rstrip('\n').split('\t')
            try:
                buff_idx = header_cols.index("buff_starts")
            except ValueError:
                buff_idx = max(len(header_cols) - 3, 0)
            try:
                dur_idx = header_cols.index("durations")
            except ValueError:
                dur_idx = buff_idx + 1
            try:
                evt_idx = header_cols.index("events")
            except ValueError:
                evt_idx = buff_idx + 2
            key_end = min(buff_idx, dur_idx, evt_idx)
            for line in f:
                line = line.strip('\n')
                if not line:
                    continue
                cols = line.split('\t')
                if len(cols) <= evt_idx:
                    continue
                buffer_start_dim = self._parse_int_list(cols[buff_idx])
                durations = self._parse_int_list(cols[dur_idx])
                event_observed = self._parse_int_list(cols[evt_idx])
                key_cols = cols[:key_end]
                if len(key_cols) >= 8:
                    data.update({(algo,arena,key_cols[0],key_cols[1],key_cols[2],key_cols[3],key_cols[4],key_cols[5],key_cols[6],key_cols[7]):(buffer_start_dim,durations,event_observed)})
        return data

###################################################
    def read_csv(self,path,algo,n_runs,arena):
        data = {}
        with open(path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header:
                return data
            header_cols = header.rstrip('\n').split('\t')
            try:
                type_idx = header_cols.index("type")
            except ValueError:
                type_idx = max(len(header_cols) - 3, 0)
            try:
                data_idx = header_cols.index("data")
            except ValueError:
                data_idx = max(len(header_cols) - 2, 0)
            try:
                std_idx = header_cols.index("std")
            except ValueError:
                std_idx = max(len(header_cols) - 1, 0)
            for line in f:
                line = line.strip('\n')
                if not line:
                    continue
                cols = line.split('\t')
                if len(cols) <= max(type_idx, data_idx, std_idx):
                    continue
                array_val = self._parse_float_list(cols[data_idx])
                std_val = self._parse_float_list(cols[std_idx], allow_dash=True)
                key_cols = cols[:type_idx + 1]
                data.update({(algo,arena,n_runs,*key_cols):(array_val,std_val)})
        return data

###################################################
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
                
###################################################
    def read_fitted_recovery_csv(self,file_path:str) -> dict:
        data = {}
        with open(file_path, newline='', buffering=1024 * 1024) as f:
            header = f.readline()
            if not header:
                return data
            for line in f:
                line = line.strip('\n')
                if not line:
                    continue
                row = line.split(',')
                key = tuple(row[:10])
                value = tuple(row[10:])
                data[key] = value
        return data
    
###################################################
    def plot_recovery(self, data_in):
        # Impostazioni generali
        images_dir = os.path.join(self.base, "rec_data", "images")
        os.makedirs(images_dir, exist_ok=True)

        # Mappa varianti -> label e colore
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cmx.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        variant_map = {}
        for p in self.protocols:
            pid = p.get("id")
            if not pid:
                continue
            variant_map[pid] = (p.get("label", pid), self._protocol_color(p, scalarMap))
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]

        # Ricostruzione DataFrame
        rows = []
        for key, (mean, std, events) in data_in.items():
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k
            broadcast = int(broadcast); hops = int(hops)
            agents = int(agents); msgs = int(msgs); buf = int(buf)
            gt = float(gt); th = float(th)
            variant_key = f"{alg}.{broadcast}.{hops}"

            alg_lower = str(alg).strip().lower()
            if alg_lower == 'ps':
                variant_key = 'P.1.1'
            elif alg_lower == 'p':
                # priority-sampling-like case: recovery with buffer = n_agents - 2
                if buf == max(0, agents - 2):
                    variant_key = 'P.1.1'
                else:
                    variant_key = 'P.1.0' if msgs > 0 else 'P.0'
            elif variant_key.startswith('P.1'):
                variant_key = 'P.1.0'

            if not self._protocol_enabled("recovery", variant_key):
                continue
            label, color = variant_map.get(variant_key, ('UNK', 'black'))
            rows.append({
                'Arena': arena,
                'Agents': agents,
                'Msgs_exp_time': msgs,
                'Error': abs(gt - th),
                'Events': int(events) / (100 * agents),
                'Time': float(mean),
                'VariantKey': variant_key,
                'Label': label,
                'Color': color
            })
        df = pd.DataFrame(rows)

        # --- CORREZIONE CRITICA: prima sposto solo AN e AN_t su T_m=60, poi rimuovo T_m=0
        # AN_t^1 deve invece restare nelle colonne corrispondenti al suo Msgs_exp_time originale.
        df.loc[df['Label'].isin([r'$AN$']), 'Msgs_exp_time'] = 60
        df = df[df['Msgs_exp_time'] != 0]

        # Griglia righe/colonne
        grid = [("bigA", 25), ("smallA", 25), ("bigA", 100)]
        row_labels = ["LD25", "HD25", "HD100"]

        # Ricostruisci msg_list e metti 60 come prima colonna se presente
        msg_list = sorted(df['Msgs_exp_time'].unique())
        msg_list = self._plot_tm_values("recovery", msg_list)
        if not msg_list:
            return
        if 60 in msg_list:
            msg_list = [60] + [m for m in msg_list if m != 60]
        col_labels = [f"$T_m$={m}" for m in msg_list]

        # Etichette varianti e mappa label->colore
        labels = []
        for pid in protocols_order:
            if pid in variant_map and self._protocol_enabled("recovery", pid):
                labels.append(variant_map[pid][0])
        label_color_map = {label: color for label, color in variant_map.values()}

        # Funzione per salvare boxplot con gestione dei label/overlap
        def save_box(subset, suffix, entry, global_max:int):
            nrows = len(grid)
            ncols = len(msg_list)

            # non condividere l'asse y tra tutte le sottotrame: vogliamo limiti y
            # diversi per ogni riga. Con sharey=True tutti gli assi avrebbero lo
            # stesso limite e ciò impedisce lo zoom per riga.
            fig, axes = plt.subplots(nrows, ncols, figsize=(26, 18), sharey=True, sharex=False)

            # assicurati che axes sia array 2D
            if nrows == 1 and ncols == 1:
                axes = np.array([[axes]])
            elif nrows == 1:
                axes = np.array([axes])
            elif ncols == 1:
                axes = np.array([[ax] for ax in axes])

            # Calcola il massimo per ogni riga (considerando tutti i column/Msg presenti
            # nel `subset` passato a questa chiamata). Questo permette a ciascuna
            # riga di avere un proprio limite y basato sui dati effettivi della
            # singola invocazione di `save_box`.
            row_maxs = []
            for (arena_r, ag_r) in grid:
                row_cell = subset[(subset['Arena'] == arena_r) & (subset['Agents'] == ag_r)]
                if not row_cell.empty and row_cell[entry].count() > 0:
                    row_maxs.append(float(row_cell[entry].max()))
                else:
                    row_maxs.append(float(global_max))

            for i, (arena, ag) in enumerate(grid):
                for j, m in enumerate(msg_list):
                    ax = axes[i, j]
                    cell = subset[
                        (subset['Arena'] == arena) &
                        (subset['Agents'] == ag) &
                        (subset['Msgs_exp_time'] == m)
                    ]

                    # rimuovi AN dalle colonne successive alla prima
                    # Escludi completamente le varianti P.0 (AN) e O.2.0 (ID+R_f)
                    excluded_labels = []#[variant_map['P.0'][0],variant_map['O.2.0'][0]]
                    plot_labels = [lbl for lbl in labels if lbl not in excluded_labels]
                    # Mantieni la logica originale: rimuovi AN dalle colonne successive (ridondante se già escluso)
                    if j > 0:
                        plot_labels = [lbl for lbl in plot_labels if lbl != r'$AN$']

                    # costruisci due liste: data_nonempty e labels_nonempty (boxplot non gradisce serie vuote)
                    data_nonempty = []
                    labels_nonempty = []
                    for lbl in plot_labels:
                        d = cell[cell['Label'] == lbl][entry].values
                        if len(d) > 0:
                            data_nonempty.append(d)
                            labels_nonempty.append(lbl)

                    # disegna solo se c'è almeno una serie non vuota
                    if len(data_nonempty) > 0:
                        bp = ax.boxplot(data_nonempty, labels=labels_nonempty, patch_artist=True,medianprops=dict(color='gray', linewidth=2))
                        for patch, lbl in zip(bp['boxes'], labels_nonempty):
                            patch.set_facecolor(label_color_map.get(lbl, 'black'))
                        # migliora visibilità degli xticks: li ruotiamo (ma li mostriamo solo nella riga in basso)
                        if i == nrows - 1:
                            plt.setp(ax.get_xticklabels(), rotation=30, ha='center', fontsize=plt.rcParams.get("font.size")-5)
                    else:
                        # niente dati -> togli label asse x per evitare "vuoti" visuali
                        ax.set_xticks([])
                        ax.set_xticklabels([])

                    # Titoli colonne (solo prima riga)
                    if i == 0:
                        ax.set_title(col_labels[j])

                    # Asse y: scala lineare e limiti; calcola min/max dal subset se disponibile
                    ax.set_yscale('linear')

                    # Usa il massimo calcolato per la riga; fallback su global_max
                    raw_top = row_maxs[i] if (i < len(row_maxs)) else float(global_max)
                    try:
                        raw_top = float(raw_top)
                    except Exception:
                        raw_top = float(global_max if global_max is not None else 1.0)
                    if raw_top <= 0:
                        raw_top = 1.0

                    # Vogliamo mantenere un numero di tick costante/attorno a desired_ticks
                    # (es. ~11). Calcoliamo il passo target e scegliamo uno step "tondo"
                    # dalla serie [1,2,2.5,5,10] * 10^exp più vicino al passo target.
                    desired_ticks = 11.0
                    target_step = raw_top / desired_ticks
                    exp = np.floor(np.log10(target_step)) if target_step > 0 else 0
                    magnitude = 10.0 ** exp
                    base_candidates = np.array([1.0, 2.0, 2.5, 5.0, 10.0])
                    candidates = magnitude * base_candidates

                    # Scegli il candidato più vicino al target_step
                    diffs = np.abs(candidates - target_step)
                    best_idx = int(np.argmin(diffs))
                    best_step = candidates[best_idx]

                    # Normalizza step a intero quando possibile (per yticks interi)
                    if abs(best_step - round(best_step)) < 1e-8:
                        step = int(round(best_step))
                    else:
                        # se il passo è frazionario (molto raro per eventi), mantienilo float
                        step = float(best_step)

                    # Arrotonda il top al prossimo multiplo del passo scelto
                    top_rounded = int(np.ceil(raw_top / best_step) * best_step)

                    # Mantieni la vecchia logica di margine speciale per 60 (compatibilità)
                    top_plot = top_rounded + 1 if top_rounded == 60 else top_rounded
                    step = int(step)
                    sstep = int(max(step,top_rounded/8))
                    yticks = np.arange(0, top_rounded + step, sstep)

                    # margini: se il minimo del subset è 0, partiamo da -1 (senza label)
                    ymin = 0
                    ymin_plot = ymin - 1

                    if entry!="Time":
                        ax.set_yticks(yticks)
                        ax.set_ylim(ymin_plot, top_plot)
                    else:
                        ax.set_yscale('log')
                        ax.set_ylim(1,500)
                    plt.setp(ax.get_yticklabels(), fontsize=plt.rcParams.get("font.size") - 5)
                    ax.grid(True)

                    # nascondi xticks/label nelle righe non-bottom per evitare sovrapposizioni
                    if i != nrows - 1:
                        ax.set_xticklabels([])

                # annotazioni riga
                if entry == "Time":
                    axes[i, 0].annotate(r"$T_{r}$", xy=(-.3, 0.5), xycoords='axes fraction',
                                        fontsize=plt.rcParams.get("font.size"), ha='left', va='center', rotation=90)
                else:
                    axes[i, 0].annotate(r"$E_{r}$", xy=(-.3, 0.5), xycoords='axes fraction',
                                        fontsize=plt.rcParams.get("font.size"), ha='left', va='center', rotation=90)

                axes[i, -1].annotate(row_labels[i], xy=(1.05, 0.5), xycoords='axes fraction',
                                    fontsize=plt.rcParams.get("font.size"), ha='left', va='center', rotation=90)

            fig.tight_layout(rect=[0, 0.05, 1, 0.95])
            plt.grid(True)
            # fig.savefig(os.path.join(images_dir, f"box_{suffix}.png"))
            fig.savefig(os.path.join(images_dir, f"box_{suffix}.pdf"))
            plt.close(fig)

        # Salva i boxplot
        time_max = df["Time"].max()
        event_max = df["Events"].max()

        # save_box(df, 'all_events', 'Events',event_max)
        # save_box(df, 'all_time', 'Time',time_max)
        save_box(df[df['Error'] <= 0.05], 'le05_events', 'Events',event_max)
        save_box(df[df['Error'] <= 0.05], 'le05_time', 'Time',time_max)
        save_box(df[df['Error'] > 0.05], 'gt05_events', 'Events',event_max)
        save_box(df[df['Error'] > 0.05], 'gt05_time', 'Time',time_max)

        # # Istogrammi 2D per variante (Error vs Events)
        # xbins = np.linspace(0, 0.5, 30)
        # ybins = np.arange(0, event_max+5, 2)
        # # limite superiore arrotondato a multipli di 10 per gli eventi
        # top_event = int(np.ceil((event_max if event_max > 0 else 1) / 10.0) * 10)
        # for key_var, (label, color) in variant_map.items():
        #     columns = len(msg_list) if key_var != "P.0" else 1
        #     w_size = 30 if columns > 1 else 12
        #     x_w = 0 if columns > 1 else 5

        #     fig, axes = plt.subplots(len(grid), columns, figsize=(w_size, 18), sharex=True, sharey=True)
        #     # Flatten axes array for uniform processing
        #     if columns == 1:
        #         axes = np.array(axes).reshape(-1, 1)
        #     elif len(grid) == 1:
        #         axes = np.array(axes).reshape(1, -1)

        #     h = None
        #     for i, (arena, ag) in enumerate(grid):
        #         for j, m in enumerate(msg_list):
        #             ax = axes[i, j]
        #             cell = df[
        #                 (df['VariantKey'] == key_var) &
        #                 (df['Arena'] == arena) &
        #                 (df['Agents'] == ag) &
        #                 (df['Msgs_exp_time'] == m)
        #             ]
        #             if not cell.empty:
        #                 h = ax.hist2d(cell['Error'], cell['Events'], bins=[xbins, ybins], cmap='viridis')
        #                 ax.set_yscale('linear')
        #                 # imposta ticks a multipli di 10 e ylim basato su top_event
        #                 ax.set_ylim(0, top_event)
        #                 ax.set_yticks(np.arange(0, top_event + 1, 10))
        #                 ax.grid(True)
        #             if i == 0:
        #                 ax.set_title(col_labels[j])
        #             if i == len(grid) - 1:
        #                 ax.set_xlabel(r"$|G-\tau|$")
        #                 ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
        #                 ax.set_xticklabels(["0", "0.1", "0.2", "0.3", "0.4", "0.5"])
        #                 plt.setp(ax.get_xticklabels(), fontsize=plt.rcParams.get("font.size") - 5 - x_w)
        #             if j == 0:
        #                 ax.set_ylabel("Events")
        #                 plt.setp(ax.get_yticklabels(), fontsize=plt.rcParams.get("font.size") - 5 - x_w)
        #             ax.set_ylim(0, top_event)
        #             # assicurati che ci sia la griglia anche quando non ci sono dati
        #             ax.grid(True)
        #             if columns == 1: break
        #         axes[i, -1].annotate(row_labels[i], xy=(1.05, 0.5), xycoords='axes fraction',
        #                         fontsize=plt.rcParams.get("font.size")-x_w, ha='left', va='center', rotation=270)
        #     if h is not None:
        #         # Use divider to place the colorbar correctly
        #         fig.subplots_adjust(right=0.88) if columns > 1 else fig.subplots_adjust(right=0.75)
        #         cbar_ax = fig.add_axes([0.91, 0.1, 0.03, 0.8]) if columns > 1 else fig.add_axes([0.85, 0.1, 0.04, 0.8])
        #         fig.colorbar(h[3], cax=cbar_ax, label='#')
        #     # fig.savefig(os.path.join(images_dir, f"hist2d_{key_var}.png"))
        #     fig.savefig(os.path.join(images_dir, f"hist2d_{key_var}.pdf"))
        #     plt.close(fig)

        # # Istogrammi 2D per variante (Error vs Time)
        # xbins = np.linspace(0, 0.5, 30)
        # ybins = np.arange(0, 155, 5)
        # # limite superiore arrotondato a multipli di 50 per i tempi (ticks 0,50,100,...)
        # top_time = int(np.ceil((time_max if time_max > 0 else 1) / 50.0) * 50)
        # for key_var, (label, color) in variant_map.items():
        #     columns = len(msg_list) if key_var != "P.0" else 1
        #     w_size = 30 if columns > 1 else 12
        #     x_w = 0 if columns > 1 else 5

        #     fig, axes = plt.subplots(len(grid), columns, figsize=(w_size, 18), sharex=True, sharey=True)
        #     # Flatten axes array for uniform processing
        #     if columns == 1:
        #         axes = np.array(axes).reshape(-1, 1)
        #     elif len(grid) == 1:
        #         axes = np.array(axes).reshape(1, -1)

        #     h = None
        #     for i, (arena, ag) in enumerate(grid):
        #         for j, m in enumerate(msg_list):
        #             ax = axes[i, j]
        #             cell = df[
        #                 (df['VariantKey'] == key_var) &
        #                 (df['Arena'] == arena) &
        #                 (df['Agents'] == ag) &
        #                 (df['Msgs_exp_time'] == m)
        #             ]
        #             if not cell.empty:
        #                 h = ax.hist2d(cell['Error'], cell['Time'], bins=[xbins, ybins], cmap='viridis')
        #                 ax.set_yscale('linear')
        #                 # imposta ticks a multipli di 50 e ylim basato su top_time
        #                 ax.set_ylim(0, top_time)
        #                 ax.set_yticks(np.arange(0, top_time + 1, 50))
        #                 ax.grid(True)
        #             if i == 0:
        #                 ax.set_title(col_labels[j])
        #             if i == len(grid) - 1:
        #                 ax.set_xlabel(r"$|G-\tau|$")
        #                 ax.set_xticks([0, 0.1, 0.2, 0.3, 0.4, 0.5])
        #                 ax.set_xticklabels(["0", "0.1", "0.2", "0.3", "0.4", "0.5"])
        #                 plt.setp(ax.get_xticklabels(), fontsize=plt.rcParams.get("font.size") - 5 - x_w)
        #             if j == 0:
        #                 ax.set_ylabel("Time")
        #                 plt.setp(ax.get_yticklabels(), fontsize=plt.rcParams.get("font.size") - 5 - x_w)
        #             ax.set_ylim(0, top_time)
        #             if columns == 1: break
        #         axes[i, -1].annotate(row_labels[i], xy=(1.05, 0.5), xycoords='axes fraction',
        #                         fontsize=plt.rcParams.get("font.size")-x_w, ha='left', va='center', rotation=270)
        #     # Add colorbar aligned to the last subplot row and column
        #     if h is not None:
        #         # Use divider to place the colorbar correctly
        #         fig.subplots_adjust(right=0.88) if columns > 1 else fig.subplots_adjust(right=0.75)
        #         cbar_ax = fig.add_axes([0.91, 0.1, 0.03, 0.8]) if columns > 1 else fig.add_axes([0.85, 0.1, 0.04, 0.8])
        #         fig.colorbar(h[3], cax=cbar_ax, label='#')
        #     # fig.savefig(os.path.join(images_dir, f"Thist2d_{key_var}.png"))
        #     fig.savefig(os.path.join(images_dir, f"Thist2d_{key_var}.pdf"))
        #     plt.close(fig)

###################################################
    def store_recovery(self,data_in):
        if not os.path.exists(self.base+"/rec_data/"):
            os.mkdir(self.base+"/rec_data/")
        path = self.base+"/rec_data/"
        out_path = os.path.join(path, "recovery_data.csv")
        write_header = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
        ground_T, threshlds, msg_hops, jolly        = [],[],[],[]
        algo, arena, time, comm, agents, buf_dim ,msgs_time   = [],[],[],[],[],[],[]
        da_K = data_in.keys()
        for k0 in da_K:
            if k0[0] not in algo: algo.append(k0[0])
            if k0[1] not in arena: arena.append(k0[1])
            if k0[2] not in time: time.append(k0[2])
            if k0[3] not in comm: comm.append(k0[3])
            if k0[4] not in agents: agents.append(k0[4])
            if k0[5] not in buf_dim: buf_dim.append(k0[5])
            if k0[6] not in msgs_time: msgs_time.append(k0[6])
            if k0[7] not in msg_hops: msg_hops.append(k0[7])
            if k0[8] not in ground_T: ground_T.append(k0[8])
            if k0[9] not in threshlds: threshlds.append(k0[9])
            if k0[10] not in jolly: jolly.append(k0[10])
        rows = []
        for a in algo:
            for a_s in arena:
                for et in time:
                    for c in comm:
                        for m_h in msg_hops:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for met in msgs_time:
                                        for gt in ground_T:
                                            for thr in threshlds:
                                                for jl in jolly:
                                                    s_data = data_in.get((a,a_s,et,c,n_a,m_b_d,met,m_h,gt,thr,jl))
                                                    if s_data != None:
                                                        rows.append([a, a_s, et, c, n_a, m_b_d, met, m_h, gt, thr, s_data[0][0], s_data[0][1], s_data[1]])
        if rows:
            with open(out_path, mode='a', newline='', buffering=1024 * 1024) as file:
                writer = csv.writer(file)
                if write_header:
                    writer.writerow(['Algorithm', 'Arena', 'Time', 'Broadcast', 'Agents', 'Buffer_Dim','Msgs_exp_time','Msg_Hops', 'Ground_T', 'Threshold', 'Mean', 'Std', 'Events'])
                writer.writerows(rows)

###################################################
    def plot_active(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_avg,dict_park_t1_avg,dict_park_avg_real_fifo,dict_adms_avg,dict_fifo_avg,dict_rnd_avg,dict_rnd_inf_avg = {},{},{},{},{},{},{}
        dict_park_tmed,dict_park_t1_tmed,dict_park_tmed_real_fifo,dict_adms_tmed,dict_fifo_tmed,dict_rnd_tmed,dict_rnd_inf_tmed = {},{},{},{},{},{},{}
        ground_T, threshlds , msg_time, msg_hop        = [],[],[],[]
        algo,arena,runs,time,comm,agents,buf_dim    = [],[],[],[],[],[],[]
        o_k                                         = []
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0]not in algo: algo.append(k0[0])
                if k0[1]not in arena: arena.append(k0[1])
                if k0[2]not in runs: runs.append(k0[2])
                if k0[3]not in time: time.append(k0[3])
                if k0[4]not in comm: comm.append(k0[4])
                if k0[5]not in agents: agents.append(k0[5])
                if float(k0[6]) not in ground_T: ground_T.append(float(k0[6]))
                if float(k0[7]) not in threshlds: threshlds.append(float(k0[7]))
                if k0[8]not in buf_dim: buf_dim.append(k0[8])
                if k0[9]not in msg_time: msg_time.append(k0[9])
                if k0[10]not in msg_hop: msg_hop.append(k0[10])
        for i in range(len(data_in)):
            for a in algo:
                for a_s in arena:
                    for n_r in runs:
                        for et in time:
                            for c in comm:
                                for n_a in agents:
                                    for m_b_d in buf_dim:
                                        for m_t in msg_time:
                                            for m_h in msg_hop:
                                                vals            = []
                                                times_median    = []
                                                for gt in ground_T:
                                                    tmp         = []
                                                    tmp_tmed    = []
                                                    for thr in threshlds:
                                                        s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h))
                                                        t_data = times[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h))
                                                        if s_data != None:
                                                            if m_t not in o_k: o_k.append(m_t)
                                                            tmp.append(round(np.median(s_data[0]),2))
                                                            tmp_tmed.append(round(np.median(t_data[0]),2))
                                                    if len(vals)==0:
                                                        vals            = np.array([tmp])
                                                        times_median    = np.array([tmp_tmed])
                                                    else:
                                                        vals            = np.append(vals,[tmp],axis=0)
                                                        times_median    = np.append(times_median,[tmp_tmed],axis=0)
                                                if a.strip().lower() in ['ps'] and int(c)==0 and m_t in o_k and int(m_t) > 0:
                                                    if len(vals[0])>0:
                                                        dict_park_t1_avg.update({(a_s,n_a,m_t):vals})
                                                        dict_park_t1_tmed.update({(a_s,n_a,m_t):times_median})
                                                elif a.strip().lower() == 'p' and int(c)==0 and m_t in o_k and int(m_t) > 0:
                                                    if len(vals[0])>0:
                                                        dict_park_avg.update({(a_s,n_a,m_t):vals})
                                                        dict_park_tmed.update({(a_s,n_a,m_t):times_median})
                                                if a=='P' and int(c)==0 and m_t in o_k and int(m_t) == 0:
                                                    if len(vals[0])>0:
                                                        dict_park_avg_real_fifo.update({(a_s,n_a,"60"):vals})
                                                        dict_park_tmed_real_fifo.update({(a_s,n_a,"60"):times_median})
                                                if a=='O' and m_t in o_k:
                                                    if len(vals[0])>0:
                                                        if int(c)==0:
                                                            dict_adms_avg.update({(a_s,n_a,m_t):vals})
                                                            dict_adms_tmed.update({(a_s,n_a,m_t):times_median})
                                                        elif int(c)==2:
                                                            dict_fifo_avg.update({(a_s,n_a,m_t):vals})
                                                            dict_fifo_tmed.update({(a_s,n_a,m_t):times_median})
                                                        else:
                                                            if int(m_h)==1:
                                                                dict_rnd_avg.update({(a_s,n_a,m_t):vals})
                                                                dict_rnd_tmed.update({(a_s,n_a,m_t):times_median})
                                                            else:
                                                                dict_rnd_inf_avg.update({(a_s,n_a,m_t):vals})
                                                                dict_rnd_inf_tmed.update({(a_s,n_a,m_t):times_median})
        tmp = []
        for x in o_k:
            if int(x)!=0:
                tmp.append(x)
        o_k=tmp
        self.print_borders(path,'avg','median',ground_T,threshlds,[dict_park_avg,dict_park_t1_avg,dict_adms_avg,dict_fifo_avg,dict_rnd_avg,dict_rnd_inf_avg,dict_park_avg_real_fifo],[dict_park_tmed,dict_park_t1_tmed,dict_adms_tmed,dict_fifo_tmed,dict_rnd_tmed,dict_rnd_inf_tmed,dict_park_tmed_real_fifo],o_k,[arena,agents])
        
###################################################
    def print_messages(self,data_in,data_std):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,dict_park_t1,dict_adam,dict_fifo, dict_rnd, dict_rnd_inf,dict_park_real_fifo = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5], data_in[6]
        std_dict_park,std_dict_park_t1,std_dict_adam,std_dict_fifo, std_dict_rnd, std_dict_rnd_inf,std_dict_park_real_fifo = data_std[0], data_std[1], data_std[2], data_std[3], data_std[4], data_std[5], data_std[6]
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=6, label=r'$min|B|$')
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r = []
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
        handles_r.append(min_dim)
        all_cols = set()
        for dct in (dict_park_real_fifo, dict_park, dict_park_t1, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf):
            for k in dct.keys():
                try:
                    all_cols.add(int(k[2]))
                except Exception:
                    continue
        columns = [60, 120, 180, 300, 600]
        columns = self._plot_tm_values("messages", columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x,0))))
                else:
                    void_x_ticks.append('')
        for k in dict_park_real_fifo.keys():
            tmp = []
            res = dict_park_real_fifo.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_park_real_fifo.update({k:tmp})
        for k in dict_park.keys():
            tmp = []
            res = dict_park.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_park.update({k:tmp})
        for k in dict_park_t1.keys():
            tmp = []
            res = dict_park_t1.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_park_t1.update({k:tmp})

        for k in dict_adam.keys():
            tmp = []
            res = dict_adam.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_adam.update({k:tmp})

        for k in dict_fifo.keys():
            tmp = []
            res = dict_fifo.get(k)
            restd = std_dict_fifo.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_fifo.update({k:tmp})

        for k in dict_rnd.keys():
            tmp = []
            res = dict_rnd.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd.update({k:tmp})

        for k in dict_rnd_inf.keys():
            tmp = []
            res = dict_rnd_inf.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_inf.update({k:tmp})

        for k in dict_park_real_fifo.keys():
            if not self._protocol_enabled("messages", "P.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_park_real_fifo.get(k),color=protocol_colors.get("P.0","red"),lw=6)
        for k in dict_park.keys():
            if not self._protocol_enabled("messages", "P.1.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            min_buf = []
            val = 5/(int(k[1])-1)
            for i in range(900):
                min_buf.append(val)
            ax[row][col].plot(min_buf,color="black",lw=4,ls="--")
            ax[row][col].plot(dict_park.get(k),color=protocol_colors.get("P.1.0",scalarMap.to_rgba(typo[0])),lw=6)
        for k in dict_park_t1.keys():
            if not self._protocol_enabled("messages", "P.1.1"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_park_t1.get(k),color=protocol_colors.get("P.1.1","orange"),lw=6)
        for k in dict_adam.keys():
            if not self._protocol_enabled("messages", "O.0.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_adam.get(k),color=protocol_colors.get("O.0.0",scalarMap.to_rgba(typo[1])),lw=6)
           
        for k in dict_fifo.keys():
            if not self._protocol_enabled("messages", "O.2.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_fifo.get(k),color=protocol_colors.get("O.2.0",scalarMap.to_rgba(typo[2])),lw=6)
            
        for k in dict_rnd.keys():
            if not self._protocol_enabled("messages", "O.1.1"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd.get(k),color=protocol_colors.get("O.1.1",scalarMap.to_rgba(typo[3])),lw=6)
            
        for k in dict_rnd_inf.keys():
            if not self._protocol_enabled("messages", "O.1.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd_inf.get(k),color=protocol_colors.get("O.1.0",scalarMap.to_rgba(typo[4])),lw=6)
            
        for x in range(2):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,ncols):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(ncols):
            ax[2][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
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
                ax[x][y].set_xlim(0,900)
                ax[x][y].set_ylim(-0.03,1.03)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        if handles_r:
            fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=len(handles_r), loc='upper right',framealpha=0.7,borderaxespad=0)
        # fig_path = self.base+"/msgs_data/images/messages.png"
        # fig.savefig(fig_path, bbox_inches='tight')
        fig_path = self.base+"/msgs_data/images/messages.pdf"
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
###################################################
    def print_decisions(self,data_in):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,dict_park_t1,dict_adam,dict_fifo, dict_rnd, dict_rnd_inf,dict_park_real_fifo = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5], data_in[6]
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=6, label=r'$min|B|$')
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r = []
        for pid in protocols_order:
            if not self._protocol_enabled("decisions", pid):
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
        handles_r.append(min_dim)
        all_cols = set()
        for dct in (dict_park_real_fifo, dict_park, dict_park_t1, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf):
            for k in dct.keys():
                try:
                    all_cols.add(int(k[2]))
                except Exception:
                    continue
        columns = [60, 120, 180, 300, 600]
        columns = self._plot_tm_values("decisions", columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x,0))))
                else:
                    void_x_ticks.append('')
        for k in dict_park_real_fifo.keys():
            if not self._protocol_enabled("decisions", "P.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_park_real_fifo.get(k),color=protocol_colors.get("P.0","red"),lw=6)
        for k in dict_park.keys():
            if not self._protocol_enabled("decisions", "P.1.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            min_buf = []
            val = 5/(int(k[1])-1)
            for i in range(900):
                min_buf.append(val)
            ax[row][col].plot(min_buf,color="black",lw=4,ls="--")
            ax[row][col].plot(dict_park.get(k),color=protocol_colors.get("P.1.0",scalarMap.to_rgba(typo[0])),lw=6)
        for k in dict_park_t1.keys():
            if not self._protocol_enabled("decisions", "P.1.1"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_park_t1.get(k),color=protocol_colors.get("P.1.1","orange"),lw=6)
        for k in dict_adam.keys():
            if not self._protocol_enabled("decisions", "O.0.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_adam.get(k),color=protocol_colors.get("O.0.0",scalarMap.to_rgba(typo[1])),lw=6)
        for k in dict_fifo.keys():
            if not self._protocol_enabled("decisions", "O.2.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_fifo.get(k),color=protocol_colors.get("O.2.0",scalarMap.to_rgba(typo[2])),lw=6)
        for k in dict_rnd.keys():
            if not self._protocol_enabled("decisions", "O.1.1"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd.get(k),color=protocol_colors.get("O.1.1",scalarMap.to_rgba(typo[3])),lw=6)
        for k in dict_rnd_inf.keys():
            if not self._protocol_enabled("decisions", "O.1.0"):
                continue
            if k[2] not in col_index:
                continue
            row = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            col = col_index.get(k[2])
            if col is None:
                continue
            ax[row][col].plot(dict_rnd_inf.get(k),color=protocol_colors.get("O.1.0",scalarMap.to_rgba(typo[4])),lw=6)
        for x in range(2):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,ncols):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(ncols):
            ax[2][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
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
        ax[0][0].set_ylabel(r"$D$")
        ax[1][0].set_ylabel(r"$D$")
        ax[2][0].set_ylabel(r"$D$")
        for y in range(ncols):
            ax[2][y].set_xlabel(r"$T\, (s)$")
        for x in range(3):
            for y in range(ncols):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,900)
                if x==0 or x==1:
                    ax[x][y].set_ylim(-0.03,1.03)
                else:
                    ax[x][y].set_ylim(-0.03,1.03)
        fig.tight_layout()
        if not os.path.exists(self.base+"/dec_data/images/"):
            os.mkdir(self.base+"/dec_data/images/")
        # fig_path = self.base+"/dec_data/images/decisions.png"
        fig_path = self.base+"/dec_data/images/decisions.pdf"
        if handles_r:
            fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=len(handles_r), loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
###################################################
    def print_borders(self,path,_type,t_type,ground_T,threshlds,data_in,times_in,keys,more_k):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        dict_park,dict_park_t1,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_park_real_fifo = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5], data_in[6]
        tdict_park,tdict_park_t1,tdict_adam,tdict_fifo,tdict_rnd,tdict_rnd_inf,tdict_park_real_fifo = times_in[0], times_in[1], times_in[2], times_in[3], times_in[4], times_in[5], times_in[6]
        po_k = keys
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = sorted(set(o_k))
        o_k = self._plot_tm_values("active", o_k)
        if not o_k:
            return
        ncols = len(o_k)
        arena = more_k[0]

        low_bound           = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label=r"$\hat{Q} = 0.2$")
        high_bound          = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label=r"$\hat{Q} = 0.8$")
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]

        handles_c   = [high_bound,low_bound]
        handles_r = []
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
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(8*ncols,22), squeeze=False)
        tfig, tax   = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols,18), squeeze=False)
        str_threshlds = []
        void_str_threshlds = []
        svoid_str_threshlds = []
        str_threshlds_y = []
        void_str_threshlds_y = []
        svoid_str_threshlds_y = []
        void_str_gt = []
        void_str_tim = []
        vals_dict = {}
        for a in arena:
            if a=="smallA":
                agents = ["25"]
            else:
                agents = more_k[1]
            for ag in agents:
                row = 1  if a=="smallA" else 0
                if int(ag)==100: row = 2
                vals8p  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2p  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals8p1 = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2p1 = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals8pr = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2pr = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals8a  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2a  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals8f  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2f  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals8r  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2r  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals8ri = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                vals2ri = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                flag_vals8p  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2p  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals8p1 = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2p1 = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals8pr = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2pr = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals8a  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2a  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals8f  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2f  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals8r  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2r  = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals8ri = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]
                flag_vals2ri = [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ]

                tvalsp  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                tvalspr = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                tvalsp1 = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                tvalsa  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                tvalsf  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                tvalsr  = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                tvalsri = [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))]
                for k in range(len(o_k)):
                    for th in range(len(threshlds)):
                        p_vals2,pr_vals2,p1_vals2,a_vals2,f_vals2,r_vals2,ri_vals2 = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_vals8,pr_vals8,p1_vals8,a_vals8,f_vals8,r_vals8,ri_vals8 = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt2,pr_gt2,p1_gt2,a_gt2,f_gt2,r_gt2,ri_gt2             = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt8,pr_gt8,p1_gt8,a_gt8,f_gt8,r_gt8,ri_gt8             = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_valst,pr_valst,p1_valst,a_valst,f_valst,r_valst,ri_valst = np.nan,np.nan,np.nan,np.nan,np.nan,np.nan,np.nan
                        lim_p_valst,lim_pr_valst,lim_p1_valst,lim_a_valst,lim_f_valst,lim_r_valst,lim_ri_valst = np.nan,np.nan,np.nan,np.nan,np.nan,np.nan,np.nan
                        for pt in range(len(ground_T)):
                            pval    = dict_park.get((a,ag,str(o_k[k])))[pt][th] if dict_park.get((a,ag,str(o_k[k]))) is not None else None
                            tpval   = tdict_park.get((a,ag,str(o_k[k])))[pt][th] if dict_park.get((a,ag,str(o_k[k]))) is not None else None
                            p1val   = dict_park_t1.get((a,ag,str(o_k[k])))[pt][th] if dict_park_t1.get((a,ag,str(o_k[k]))) is not None else None
                            tp1val  = tdict_park_t1.get((a,ag,str(o_k[k])))[pt][th] if dict_park_t1.get((a,ag,str(o_k[k]))) is not None else None
                            prval   = dict_park_real_fifo.get((a,ag,str(o_k[k])))[pt][th] if dict_park_real_fifo.get((a,ag,str(o_k[k]))) is not None else None
                            trpval  = tdict_park_real_fifo.get((a,ag,str(o_k[k])))[pt][th] if dict_park_real_fifo.get((a,ag,str(o_k[k]))) is not None else None
                            aval    = dict_adam.get((a,ag,str(o_k[k])))[pt][th] if dict_adam.get((a,ag,str(o_k[k]))) is not None else None
                            taval   = tdict_adam.get((a,ag,str(o_k[k])))[pt][th] if dict_adam.get((a,ag,str(o_k[k]))) is not None else None
                            fval    = dict_fifo.get((a,ag,str(o_k[k])))[pt][th] if dict_fifo.get((a,ag,str(o_k[k]))) is not None else None
                            tfval   = tdict_fifo.get((a,ag,str(o_k[k])))[pt][th] if dict_fifo.get((a,ag,str(o_k[k]))) is not None else None
                            rval    = dict_rnd.get((a,ag,str(o_k[k])))[pt][th] if dict_rnd.get((a,ag,str(o_k[k]))) is not None else None
                            trval   = tdict_rnd.get((a,ag,str(o_k[k])))[pt][th] if dict_rnd.get((a,ag,str(o_k[k]))) is not None else None
                            rival   = dict_rnd_inf.get((a,ag,str(o_k[k])))[pt][th] if dict_rnd_inf.get((a,ag,str(o_k[k]))) is not None else None
                            trival  = tdict_rnd_inf.get((a,ag,str(o_k[k])))[pt][th] if dict_rnd_inf.get((a,ag,str(o_k[k]))) is not None else None
                            if pval is not None:
                                if pval>=0.8:
                                    temp_tval = tpval
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (p_valst is np.nan or ground_T[pt]-threshlds[th]<lim_p_valst):
                                        p_valst = temp_tval
                                        lim_p_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (p_vals8[1] is np.nan or pval<p_vals8[1]):
                                        p_vals8[1]  = pval
                                        p_gt8[1]    = ground_T[pt]
                                elif pval<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (p_vals2[0] is np.nan or pval>=p_vals2[0]):
                                        p_vals2[0]  = pval
                                        p_gt2[0]    = ground_T[pt]
                                else:
                                    if p_vals8[0] is np.nan or pval>p_vals8[0]:
                                        p_vals8[0]  = pval
                                        p_gt8[0]    = ground_T[pt]
                                    if p_vals2[1] is np.nan or pval<p_vals2[1]:
                                        p_vals2[1]  = pval
                                        p_gt2[1]    = ground_T[pt]
                            if p1val is not None:
                                if p1val>=0.8:
                                    temp_tval = tp1val
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (p1_valst is np.nan or ground_T[pt]-threshlds[th]<lim_p1_valst):
                                        p1_valst = temp_tval
                                        lim_p1_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (p1_vals8[1] is np.nan or p1val<p1_vals8[1]):
                                        p1_vals8[1]  = p1val
                                        p1_gt8[1]    = ground_T[pt]
                                elif p1val<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (p1_vals2[0] is np.nan or p1val>=p1_vals2[0]):
                                        p1_vals2[0]  = p1val
                                        p1_gt2[0]    = ground_T[pt]
                                else:
                                    if p1_vals8[0] is np.nan or p1val>p1_vals8[0]:
                                        p1_vals8[0]  = p1val
                                        p1_gt8[0]    = ground_T[pt]
                                    if p1_vals2[1] is np.nan or p1val<p1_vals2[1]:
                                        p1_vals2[1]  = p1val
                                        p1_gt2[1]    = ground_T[pt]
                            if prval is not None:
                                if prval>=0.8:
                                    temp_tval = trpval
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (pr_valst is np.nan or ground_T[pt]-threshlds[th]<lim_pr_valst):
                                        pr_valst = temp_tval
                                        lim_pr_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (pr_vals8[1] is np.nan or prval<pr_vals8[1]):
                                        pr_vals8[1]  = prval
                                        pr_gt8[1]    = ground_T[pt]
                                elif prval<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (pr_vals2[0] is np.nan or prval>=pr_vals2[0]):
                                        pr_vals2[0]  = prval
                                        pr_gt2[0]    = ground_T[pt]
                                else:
                                    if pr_vals8[0] is np.nan or prval>pr_vals8[0]:
                                        pr_vals8[0]  = prval
                                        pr_gt8[0]    = ground_T[pt]
                                    if pr_vals2[1] is np.nan or prval<pr_vals2[1]:
                                        pr_vals2[1]  = prval
                                        pr_gt2[1]    = ground_T[pt]
                            if aval is not None:
                                if aval>=0.8:
                                    temp_aval = taval
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (a_valst is np.nan or ground_T[pt]-threshlds[th]<lim_a_valst):
                                        a_valst = temp_aval
                                        lim_a_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (a_vals8[1] is np.nan or aval<a_vals8[1]):
                                        a_vals8[1]  = aval
                                        a_gt8[1]    = ground_T[pt]
                                elif aval<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (a_vals2[0] is np.nan or aval>=a_vals2[0]):
                                        a_vals2[0]  = aval
                                        a_gt2[0]    = ground_T[pt]
                                else:
                                    if a_vals8[0] is np.nan or aval>a_vals8[0]:
                                        a_vals8[0]  = aval
                                        a_gt8[0]    = ground_T[pt]
                                    if a_vals2[1] is np.nan or aval<a_vals2[1]:
                                        a_vals2[1]  = aval
                                        a_gt2[1]    = ground_T[pt]
                            if fval is not None:
                                if fval>=0.8:
                                    temp_fval = tfval
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (f_valst is np.nan or ground_T[pt]-threshlds[th]<lim_f_valst):
                                        f_valst = temp_fval
                                        lim_f_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (f_vals8[1] is np.nan or fval<f_vals8[1]):
                                        f_vals8[1]  = fval
                                        f_gt8[1]    = ground_T[pt]
                                elif fval<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (f_vals2[0] is np.nan or fval>=f_vals2[0]):
                                        f_vals2[0]  = fval
                                        f_gt2[0]    = ground_T[pt]
                                else:
                                    if f_vals8[0] is np.nan or fval>f_vals8[0]:
                                        f_vals8[0]  = fval
                                        f_gt8[0]    = ground_T[pt]
                                    if f_vals2[1] is np.nan or fval<f_vals2[1]:
                                        f_vals2[1]  = fval
                                        f_gt2[1]    = ground_T[pt]
                            if rval is not None:
                                if rval>=0.8:
                                    temp_rval = trval
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (r_valst is np.nan or ground_T[pt]-threshlds[th]<lim_r_valst):
                                        r_valst = temp_rval
                                        lim_r_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (r_vals8[1] is np.nan or rval<r_vals8[1]):
                                        r_vals8[1]  = rval
                                        r_gt8[1]    = ground_T[pt]
                                elif rval<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (r_vals2[0] is np.nan or rval>=r_vals2[0]):
                                        r_vals2[0]  = rval
                                        r_gt2[0]    = ground_T[pt]
                                else:
                                    if r_vals8[0] is np.nan or rval>r_vals8[0]:
                                        r_vals8[0]  = rval
                                        r_gt8[0]    = ground_T[pt]
                                    if r_vals2[1] is np.nan or rval<r_vals2[1]:
                                        r_vals2[1]  = rval
                                        r_gt2[1]    = ground_T[pt]
                            if rival is not None:
                                if rival>=0.8:
                                    temp_rival = trival
                                    if ground_T[pt]-threshlds[th]  >= 0.09 and (ri_valst is np.nan or ground_T[pt]-threshlds[th]<lim_ri_valst):
                                        ri_valst = temp_rival
                                        lim_ri_valst = ground_T[pt]-threshlds[th]
                                    if ground_T[pt]-threshlds[th] >=0 and (ri_vals8[1] is np.nan or rival<ri_vals8[1]):
                                        ri_vals8[1]  = rival
                                        ri_gt8[1]    = ground_T[pt]
                                elif rival<=0.2:
                                    if ground_T[pt]-threshlds[th] <=0 and (ri_vals2[0] is np.nan or rival>=ri_vals2[0]):
                                        ri_vals2[0]  = rival
                                        ri_gt2[0]    = ground_T[pt]
                                else:
                                    if ri_vals8[0] is np.nan or rival>ri_vals8[0]:
                                        ri_vals8[0]  = rival
                                        ri_gt8[0]    = ground_T[pt]
                                    if ri_vals2[1] is np.nan or rival<ri_vals2[1]:
                                        ri_vals2[1]  = rival
                                        ri_gt2[1]    = ground_T[pt]

                        if p_vals8[0] is np.nan:
                            p_vals8[0] = p_vals8[1]
                            p_gt8[0] = p_gt8[1]
                        elif p_vals8[1] is np.nan:
                            p_vals8[1] = p_vals8[0]
                            p_gt8[1] = p_gt8[0]
                        if p_vals2[0] is np.nan:
                            p_vals2[0] = p_vals2[1]
                            p_gt2[0] = p_gt2[1]
                        elif p_vals2[1] is np.nan:
                            p_vals2[1] = p_vals2[0]
                            p_gt2[1] = p_gt2[0]
                        if pr_vals8[0] is np.nan:
                            pr_vals8[0] = pr_vals8[1]
                            pr_gt8[0] = pr_gt8[1]
                        elif pr_vals8[1] is np.nan:
                            pr_vals8[1] = pr_vals8[0]
                            pr_gt8[1] = pr_gt8[0]
                        if p1_vals8[0] is np.nan:
                            p1_vals8[0] = p1_vals8[1]
                            p1_gt8[0] = p1_gt8[1]
                        elif p1_vals8[1] is np.nan:
                            p1_vals8[1] = p1_vals8[0]
                            p1_gt8[1] = p1_gt8[0]
                        if pr_vals2[0] is np.nan:
                            pr_vals2[0] = pr_vals2[1]
                            pr_gt2[0] = pr_gt2[1]
                        elif pr_vals2[1] is np.nan:
                            pr_vals2[1] = pr_vals2[0]
                            pr_gt2[1] = pr_gt2[0]
                        if p1_vals2[0] is np.nan:
                            p1_vals2[0] = p1_vals2[1]
                            p1_gt2[0] = p1_gt2[1]
                        elif p1_vals2[1] is np.nan:
                            p1_vals2[1] = p1_vals2[0]
                            p1_gt2[1] = p1_gt2[0]
                        if a_vals8[0] is np.nan:
                            a_vals8[0] = a_vals8[1]
                            a_gt8[0] = a_gt8[1]
                        elif a_vals8[1] is np.nan:
                            a_vals8[1] = a_vals8[0]
                            a_gt8[1] = a_gt8[0]
                        if a_vals2[0] is np.nan:
                            a_vals2[0] = a_vals2[1]
                            a_gt2[0] = a_gt2[1]
                        elif a_vals2[1] is np.nan:
                            a_vals2[1] = a_vals2[0]
                            a_gt2[1] = a_gt2[0]
                        if f_vals8[0] is np.nan:
                            f_vals8[0] = f_vals8[1]
                            f_gt8[0] = f_gt8[1]
                        elif f_vals8[1] is np.nan:
                            f_vals8[1] = f_vals8[0]
                            f_gt8[1] = f_gt8[0]
                        if f_vals2[0] is np.nan:
                            f_vals2[0] = f_vals2[1]
                            f_gt2[0] = f_gt2[1]
                        elif f_vals2[1] is np.nan:
                            f_vals2[1] = f_vals2[0]
                            f_gt2[1] = f_gt2[0]
                        if r_vals8[0] is np.nan:
                            r_vals8[0] = r_vals8[1]
                            r_gt8[0] = r_gt8[1]
                        elif r_vals8[1] is np.nan:
                            r_vals8[1] = r_vals8[0]
                            r_gt8[1] = r_gt8[0]
                        if r_vals2[0] is np.nan:
                            r_vals2[0] = r_vals2[1]
                            r_gt2[0] = r_gt2[1]
                        elif r_vals2[1] is np.nan:
                            r_vals2[1] = r_vals2[0]
                            r_gt2[1] = r_gt2[0]
                        if ri_vals8[0] is np.nan:
                            ri_vals8[0] = ri_vals8[1]
                            ri_gt8[0] = ri_gt8[1]
                        elif ri_vals8[1] is np.nan:
                            ri_vals8[1] = ri_vals8[0]
                            ri_gt8[1] = ri_gt8[0]
                        if ri_vals2[0] is np.nan:
                            ri_vals2[0] = ri_vals2[1]
                            ri_gt2[0] = ri_gt2[1]
                        elif ri_vals2[1] is np.nan:
                            ri_vals2[1] = ri_vals2[0]
                            ri_gt2[1] = ri_gt2[0]

                        vals2p[k][th]  = np.around(np.interp([0.2],p_vals2,p_gt2,left=np.nan),3)
                        vals2pr[k][th] = np.around(np.interp([0.2],pr_vals2,pr_gt2,left=np.nan),3)
                        vals2p1[k][th] = np.around(np.interp([0.2],p1_vals2,p1_gt2,left=np.nan),3)
                        vals2a[k][th]  = np.around(np.interp([0.2],a_vals2,a_gt2,left=np.nan),3)
                        vals2f[k][th]  = np.around(np.interp([0.2],f_vals2,f_gt2,left=np.nan),3)
                        vals2r[k][th]  = np.around(np.interp([0.2],r_vals2,r_gt2,left=np.nan),3)
                        vals2ri[k][th] = np.around(np.interp([0.2],ri_vals2,ri_gt2,left=np.nan),3)
                        vals8p[k][th]  = np.around(np.interp([0.8],p_vals8,p_gt8,right=np.nan),3)
                        vals8pr[k][th] = np.around(np.interp([0.8],pr_vals8,pr_gt8,right=np.nan),3)
                        vals8p1[k][th] = np.around(np.interp([0.8],p1_vals8,p1_gt8,right=np.nan),3)
                        vals8a[k][th]  = np.around(np.interp([0.8],a_vals8,a_gt8,right=np.nan),3)
                        vals8f[k][th]  = np.around(np.interp([0.8],f_vals8,f_gt8,right=np.nan),3)
                        vals8r[k][th]  = np.around(np.interp([0.8],r_vals8,r_gt8,right=np.nan),3)
                        vals8ri[k][th] = np.around(np.interp([0.8],ri_vals8,ri_gt8,right=np.nan),3)
                        flag_vals2p[k][th]  = [p_vals2,p_gt2]
                        flag_vals2pr[k][th] = [pr_vals2,pr_gt2]
                        flag_vals2p1[k][th] = [p1_vals2,p1_gt2]
                        flag_vals2a[k][th]  = [a_vals2,a_gt2]
                        flag_vals2f[k][th]  = [f_vals2,f_gt2]
                        flag_vals2r[k][th]  = [r_vals2,r_gt2]
                        flag_vals2ri[k][th] = [ri_vals2,ri_gt2]
                        flag_vals8p[k][th]  = [p_vals8,p_gt8]
                        flag_vals8pr[k][th] = [pr_vals8,pr_gt8]
                        flag_vals8p1[k][th] = [p1_vals8,p1_gt8]
                        flag_vals8a[k][th]  = [a_vals8,a_gt8]
                        flag_vals8f[k][th]  = [f_vals8,f_gt8]
                        flag_vals8r[k][th]  = [r_vals8,r_gt8]
                        flag_vals8ri[k][th] = [ri_vals8,ri_gt8]
                        tvalsp[k][th]  = p_valst
                        tvalspr[k][th] = pr_valst
                        tvalsp1[k][th] = p1_valst
                        tvalsa[k][th]  = a_valst
                        tvalsf[k][th]  = f_valst
                        tvalsr[k][th]  = r_valst
                        tvalsri[k][th] = ri_valst

                    ax[row][k].plot(np.arange(0.5,1.01,0.01),color='black',lw=5,ls=':')
                    if self._protocol_enabled("active", "P.0"):
                        ax[row][k].plot(vals2pr[k],color=protocol_colors.get("P.0","red"),lw=6,ls='--')
                        ax[row][k].plot(vals8pr[k],color=protocol_colors.get("P.0","red"),lw=6,ls='-')
                        tax[row][k].plot(tvalspr[k],color=protocol_colors.get("P.0","red"),lw=6)
                    if self._protocol_enabled("active", "P.1.1"):
                        ax[row][k].plot(vals2p1[k],color=protocol_colors.get("P.1.1","orange"),lw=6,ls='--')
                        ax[row][k].plot(vals8p1[k],color=protocol_colors.get("P.1.1","orange"),lw=6,ls='-')
                        tax[row][k].plot(tvalsp1[k],color=protocol_colors.get("P.1.1","orange"),lw=6)
                    if self._protocol_enabled("active", "P.1.0"):
                        ax[row][k].plot(vals2p[k],color=protocol_colors.get("P.1.0",scalarMap.to_rgba(typo[0])),lw=6,ls='--')
                        ax[row][k].plot(vals8p[k],color=protocol_colors.get("P.1.0",scalarMap.to_rgba(typo[0])),lw=6,ls='-')
                        tax[row][k].plot(tvalsp[k],color=protocol_colors.get("P.1.0",scalarMap.to_rgba(typo[0])),lw=6)
                    if self._protocol_enabled("active", "O.0.0"):
                        ax[row][k].plot(vals2a[k],color=protocol_colors.get("O.0.0",scalarMap.to_rgba(typo[1])),lw=6,ls='--')
                        ax[row][k].plot(vals8a[k],color=protocol_colors.get("O.0.0",scalarMap.to_rgba(typo[1])),lw=6,ls='-')
                        tax[row][k].plot(tvalsa[k],color=protocol_colors.get("O.0.0",scalarMap.to_rgba(typo[1])),lw=6)
                    if self._protocol_enabled("active", "O.2.0"):
                        ax[row][k].plot(vals2f[k],color=protocol_colors.get("O.2.0",scalarMap.to_rgba(typo[2])),lw=6,ls='--')
                        ax[row][k].plot(vals8f[k],color=protocol_colors.get("O.2.0",scalarMap.to_rgba(typo[2])),lw=6,ls='-')
                        tax[row][k].plot(tvalsf[k],color=protocol_colors.get("O.2.0",scalarMap.to_rgba(typo[2])),lw=6)
                    if self._protocol_enabled("active", "O.1.1"):
                        ax[row][k].plot(vals2r[k],color=protocol_colors.get("O.1.1",scalarMap.to_rgba(typo[3])),lw=6,ls='--')
                        ax[row][k].plot(vals8r[k],color=protocol_colors.get("O.1.1",scalarMap.to_rgba(typo[3])),lw=6,ls='-')
                        tax[row][k].plot(tvalsr[k],color=protocol_colors.get("O.1.1",scalarMap.to_rgba(typo[3])),lw=6)
                    if self._protocol_enabled("active", "O.1.0"):
                        ax[row][k].plot(vals2ri[k],color=protocol_colors.get("O.1.0",scalarMap.to_rgba(typo[4])),lw=6,ls='--')
                        ax[row][k].plot(vals8ri[k],color=protocol_colors.get("O.1.0",scalarMap.to_rgba(typo[4])),lw=6,ls='-')
                        tax[row][k].plot(tvalsri[k],color=protocol_colors.get("O.1.0",scalarMap.to_rgba(typo[4])),lw=6)
                    if len(str_threshlds)==0:
                        for x in threshlds:
                            if np.around(np.around(x,1)-np.around(x%10,2),2) == 0.0:
                                str_threshlds.append(str(x))
                                void_str_threshlds.append('')
                                svoid_str_threshlds.append('')
                            else:
                                void_str_threshlds.append('')
                        for x in threshlds:
                            if x>.9: break
                            if np.around(np.around(x,1)-np.around(x%10,2),2) == 0.0:
                                str_threshlds_y.append(str(x))
                                void_str_threshlds_y.append('')
                                svoid_str_threshlds_y.append('')
                            else:
                                void_str_threshlds_y.append('')
                        for x in range(5,11,1):
                            void_str_gt.append('')
                        for x in range(0,61,5):
                            void_str_tim.append('')
                    ax[row][k].set_xlim(0.5,1)
                    tax[row][k].set_xlim(0.5,0.9)
                    ax[row][k].set_ylim(0.5,1)
                    tax[row][k].set_ylim(0,201)
                    tax[row][k].yaxis.set_tick_params(labelleft=True) if k == 0 else tax[row][k].yaxis.set_tick_params(labelleft=False)
                    if row==0:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,41,10),labels=svoid_str_threshlds_y)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,41,1),labels=void_str_threshlds_y,minor=True)
                        axt = ax[row][k].twiny()
                        taxt = tax[row][k].twiny()
                        labels = [item.get_text() for item in axt.get_xticklabels()]
                        empty_string_labels = ['']*len(labels)
                        axt.set_xticklabels(empty_string_labels)
                        taxt.set_xticklabels(empty_string_labels)
                        axt.set_xlabel(rf"$T_m = {int(o_k[k])}\, s$")
                        taxt.set_xlabel(rf"$T_m = {int(o_k[k])}\, s$")
                    elif row==2:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,41,10),labels=str_threshlds_y)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,41,1),labels=void_str_threshlds_y,minor=True)
                        tax[row][k].set_ylim(0,80)
                        ax[row][k].set_xlabel(r"$\tau$")
                        tax[row][k].set_xlabel(r"$\tau$")
                    else:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,41,10),labels=svoid_str_threshlds_y)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,41,1),labels=void_str_threshlds_y,minor=True)
                        tax[row][k].set_ylim(0,40)
                    if k==0:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1))
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        ax[row][k].set_ylabel(r"$G$")
                        tax[row][k].set_ylabel(r"$T_c$")
                    elif k==ncols-1:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        axt = ax[row][k].twinx()
                        taxt = tax[row][k].twinx()
                        labels = [item.get_text() for item in axt.get_yticklabels()]
                        empty_string_labels = ['']*len(labels)
                        axt.set_yticklabels(empty_string_labels)
                        taxt.set_yticklabels(empty_string_labels)
                        axt.set_ylabel("HD100")
                        taxt.set_ylabel("HD100")
                    else:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                    ax[row][k].grid(which='major')
                    tax[row][k].grid(which='major')
                key= (a,ag)
                vals_dict[key] = {
                    "vals2p": flag_vals2p, "vals8p": flag_vals8p,
                    "vals2pr": flag_vals2pr, "vals8pr": flag_vals8pr,
                    "vals2a": flag_vals2a, "vals8a": flag_vals8a,
                    "vals2f": flag_vals2f, "vals8f": flag_vals8f,
                    "vals2r": flag_vals2r, "vals8r": flag_vals8r,
                    "vals2ri": flag_vals2ri, "vals8ri": flag_vals8ri,
                }

        fig.tight_layout()
        tfig.tight_layout()
        fig_path = path+_type+"_activation.pdf"
        tfig_path = path+t_type+"_time.pdf"
        # fig_path = path+_type+"_activation.png"
        # tfig_path = path+t_type+"_time.png"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_c,ncols=9, loc='upper right',framealpha=0.7,borderaxespad=0)
        tfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=7,loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        tfig.savefig(tfig_path, bbox_inches='tight')
        plt.close(fig)
        plt.close(tfig)
        # self.plot_protocol_tables(path, o_k, ground_T, threshlds, vals_dict)

###################################################
    def plot_protocol_tables(self, save_path, o_k, ground_T, threshlds, vals_dict):
        """
        Genera una tabella unica per ogni valore di o_k e protocollo, con valori v2 (rosso) e v8 (verde) nella stessa cella.
        """
        for (a, ag), proto_dict in vals_dict.items():
            for idx, ok_val in enumerate(o_k):
                if ok_val == 60:
                    protocols = [
                        ("anonymous_real_fifo", "pr"),
                        ("anonymous", "p"),
                        ("id_broad", "a"),
                        ("id_rebroad_fifo", "f"),
                        ("id_rebroad_rnd", "r"),
                        ("id_rebroad_rnd_inf", "ri"),
                    ]
                else:
                    protocols = [
                        ("anonymous", "p"),
                        ("id_broad", "a"),
                        ("id_rebroad_fifo", "f"),
                        ("id_rebroad_rnd", "r"),
                        ("id_rebroad_rnd_inf", "ri"),
                    ]
                fig, axes = plt.subplots(len(protocols), 1, figsize=(28, 84))
                if len(protocols) == 1:
                    axes = [axes]
                for p_idx, (title, suffix) in enumerate(protocols):
                    vals2 = proto_dict[f"vals2{suffix}"]
                    vals8 = proto_dict[f"vals8{suffix}"]
                    gt_unique = sorted(set(ground_T))[::-1]
                    cell_text = [[] for _ in gt_unique]
                    for j, thr in enumerate(threshlds):
                        for gt_idx, gt in enumerate(gt_unique):
                            v2_txt = ""
                            v8_txt = ""
                            # Cerca il valore v2
                            if gt in vals2[idx][j][1]:
                                pos = vals2[idx][j][1].index(gt)
                                v2 = vals2[idx][j][0][pos]
                                v2_txt = f"{v2:.2f}"
                            # Cerca il valore v8
                            if gt in vals8[idx][j][1]:
                                pos = vals8[idx][j][1].index(gt)
                                v8 = vals8[idx][j][0][pos]
                                v8_txt = f"{v8:.2f}"
                            # Unisci i valori nella stessa cella
                            if v2_txt and v8_txt:
                                if float(v2_txt) != float(v8_txt):
                                    cell_text[gt_idx].append("ERR")
                                else:
                                    cell_text[gt_idx].append(f"{v2_txt}_B")
                            elif v2_txt:
                                cell_text[gt_idx].append(f"{v2_txt}_L")
                            elif v8_txt:
                                cell_text[gt_idx].append(f"{v8_txt}_H")
                            else:
                                cell_text[gt_idx].append("")
                    table = axes[p_idx].table(
                        cellText=cell_text,
                        colLabels=[f"{t:.2f}" for t in threshlds],
                        rowLabels=[f"{gt:.2f}" for gt in gt_unique],
                        loc='center',
                        cellLoc='center'
                    )
                    axes[p_idx].set_title(f"{title} ({a}, {ag})")
                    axes[p_idx].axis('off')
                    table.auto_set_font_size(False)
                    table.set_fontsize(plt.rcParams.get("font.size"))
                    table.scale(2.5, 4.0)
                    # Colora le celle: rosso se v2 presente, verde se v8 presente
                    for (i, j), cell in table.get_celld().items():
                        if i == 0 or j == -1:
                            continue
                        if i > 0 and j >= 0:
                            txt = cell.get_text().get_text()
                            if "_" in txt:
                                if txt.split('_')[-1] == "B":
                                    cell.get_text().set_text(txt.split("_B")[0])
                                    cell.set_facecolor("#ffae00")  # arancione
                                elif txt.split('_')[-1] == "L":
                                    cell.get_text().set_text(txt.split("_L")[0])
                                    cell.set_facecolor('#ffcccc')  # rosso
                                elif txt.split('_')[-1] == "H":
                                    cell.get_text().set_text(txt.split("_H")[0])
                                    cell.set_facecolor('#ccffcc')  # verde
                # fig.savefig(f"{save_path}protocol_tables_{a}_{ag}_buffer_{ok_val}.png", bbox_inches='tight')
                fig.savefig(f"{save_path}protocol_tables_{a}_{ag}_buffer_{ok_val}.pdf", bbox_inches='tight')
                plt.close(fig)

###################################################
    def plot_compressed_tables(self,tot_st,tot_times,tot_msgs):
        
        return
    
###################################################
    def plot_compressed_recovery(self):
        return
