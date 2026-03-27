import sys, os, csv, logging, re, json, colorsys
import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib import pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.legend_handler import HandlerBase
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from lifelines import WeibullFitter,KaplanMeierFitter
from scipy.special import gamma
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
plt.rcParams.update({"font.size": 30})
csv.field_size_limit(sys.maxsize)
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
    def _assign_config(self,config_name):
        self.plot_config = self._load_plot_config(config_name)

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
                {"id": "O.1.0", "label": r"$ID+R_{\infty}$", "color": "viridis:4"},
            ],
            "plots": {"exclude_protocols": [], "exclude_tm": [], "insert":[]},
        }
###################################################
    def _merge_plot_config(self, base_cfg, user_cfg):
        cfg = dict(base_cfg)
        cfg["plots"] = dict(base_cfg.get("plots", {}))
        if isinstance(user_cfg, dict):
            if "protocols" in user_cfg:
                cfg["protocols"] = user_cfg.get("protocols") or []
            if "plots" in user_cfg and isinstance(user_cfg.get("plots"), dict):
                if isinstance(user_cfg["plots"], dict):
                    cfg["plots"].update(user_cfg["plots"])
        return cfg

###################################################
    def _load_plot_config(self,config_name="plot_config.json"):
        cfg = self._default_plot_config()
        path = os.path.join(self.base, config_name)
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
        plot_cfg = self.plot_config.setdefault("plots", {})
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
    def _plot_tm_values(self, values):
        plot_cfg = self.plot_config.get("plots", {})
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
    def _protocol_enabled(self, protocol_id):
        protocol = self.protocols_by_id.get(protocol_id)
        plot_cfg = self.plot_config.get("plots", {})
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
        scale, shape = wf.summary.loc['lambda_','coef'], wf.summary.loc['rho_','coef']

        mean = scale*gamma(1 + 1/shape)
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
        messages_dict, stds_dict = {},{}
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
            if k[1]=='O':
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
        messages_dict.update({"P.0":dict_park_real_fifo})
        stds_dict.update({"P.0":std_dict_park_real_fifo})
        messages_dict.update({"P.1.0":dict_park})
        stds_dict.update({"P.1.0":std_dict_park})
        messages_dict.update({"P.1.1":dict_park_t1})
        stds_dict.update({"P.1.1":std_dict_park_t1})
        messages_dict.update({"O.0.0":dict_adam})
        stds_dict.update({"O.0.0":dict_adam})
        messages_dict.update({"O.2.0":dict_fifo})
        stds_dict.update({"O.2.0":std_dict_fifo})
        messages_dict.update({"O.1.0":dict_rnd})
        stds_dict.update({"O.1.0":std_dict_rnd})
        messages_dict.update({"O.1.1":dict_rnd_inf})
        stds_dict.update({"O.1.1":std_dict_rnd_inf})

        return messages_dict,stds_dict


###################################################
    def plot_decisions(self,data):
        decisions_dict = {}
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
        decisions_dict.update({"P.0":dict_park_real_fifo})
        decisions_dict.update({"P.1.0":dict_park})
        decisions_dict.update({"P.1.1":dict_park_t1})
        decisions_dict.update({"O.0.0":dict_adam})
        decisions_dict.update({"O.2.0":dict_fifo})
        decisions_dict.update({"O.1.0":dict_rnd})
        decisions_dict.update({"O.1.1":dict_rnd_inf})
        self.print_decisions(decisions_dict)

###################################################
    def read_msgs_csv(self, path):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            try:
                data_idx = header.index("data")
            except ValueError:
                data_idx = len(header) - 1
            parse_float = self._parse_float_list 
            for row in reader:
                if len(row) <= data_idx:
                    continue
                data[tuple(row[:6])] = (parse_float(row[data_idx]), [])
        return data
    
###################################################
    def read_msgs_csv_w_std(self, path):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            try:
                data_idx = header.index("data")
            except ValueError:
                data_idx = len(header) - 2
            try:
                std_idx = header.index("std")
            except ValueError:
                std_idx = data_idx + 1
            parse_float = self._parse_float_list
            for row in reader:
                if len(row) <= max(data_idx, std_idx):
                    continue
                data[tuple(row[:data_idx])] = (
                    parse_float(row[data_idx]), 
                    parse_float(row[std_idx], allow_dash=True)
                )
        return data

###################################################
    def read_recovery_csv(self, path, algo, arena):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            try:
                b_idx = header.index("buff_starts")
            except ValueError:
                b_idx = len(header) - 3
            d_idx = b_idx + 1
            e_idx = b_idx + 2
            key_end = min(b_idx, d_idx, e_idx)
            parse_int = self._parse_int_list
            for row in reader:
                if len(row) <= e_idx:
                    continue
                
                key = (algo, arena, *row[:key_end])
                data[key] = (
                    parse_int(row[b_idx]),
                    parse_int(row[d_idx]),
                    parse_int(row[e_idx])
                )
        return data

###################################################
    def read_csv(self, path, algo, n_runs, arena):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            try:
                t_idx = header.index("type")
            except ValueError:
                t_idx = len(header) - 3
            d_idx = t_idx + 1
            s_idx = t_idx + 2
            parse_float = self._parse_float_list
            for row in reader:
                if len(row) <= s_idx:
                    continue
                key = (algo, arena, n_runs, *row[:t_idx + 1])
                data[key] = (
                    parse_float(row[d_idx]),
                    parse_float(row[s_idx], allow_dash=True)
                )
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
    def plot_recovery(self, data_in, side_by_side: bool = True):
        images_dir = os.path.join(self.base, "rec_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cmx.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        variant_map = {}
        for p in self.protocols:
            pid = p.get("id")
            if not pid:
                continue
            variant_map[pid] = (p.get("label", pid), self._protocol_color(p, scalarMap))
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
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
                if buf == max(0, agents - 2):
                    variant_key = 'P.1.1'
                else:
                    variant_key = 'P.1.0' if msgs > 0 else 'P.0'
            elif variant_key.startswith('P.1'):
                variant_key = 'P.1.0'

            if not self._protocol_enabled( variant_key):
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
        df.loc[df['Label'].isin([r'$AN$']), 'Msgs_exp_time'] = 60
        df = df[df['Msgs_exp_time'] != 0]
        grid = [("bigA", 25), ("smallA", 25), ("bigA", 100)]
        row_labels = ["LD25", "HD25", "HD100"]
        msg_list = sorted(df['Msgs_exp_time'].unique())
        msg_list = self._plot_tm_values( msg_list)
        if not msg_list:
            return
        if 60 in msg_list:
            msg_list = [60] + [m for m in msg_list if m != 60]
        col_labels = [f"$T_m$={m}" for m in msg_list]
        labels = []
        for pid in protocols_order:
            if pid in variant_map and self._protocol_enabled( pid):
                labels.append(variant_map[pid][0])
        label_color_map = {label: color for label, color in variant_map.values()}

        def save_box(subset, suffix, entry, global_max: int):
            nrows = len(grid)
            ncols = len(msg_list)
            fig, axes = plt.subplots(
                nrows, ncols,
                figsize=(ncols*8,nrows*8),
                sharey=False, sharex=True
            )
            if nrows == 1 and ncols == 1:
                axes = np.array([[axes]])
            elif nrows == 1:
                axes = np.array([axes])
            elif ncols == 1:
                axes = np.array([[ax] for ax in axes])
            row_maxs = []
            for (arena_r, ag_r) in grid:
                max_val = None
                for m in msg_list:
                    cell = subset[
                        (subset['Arena'] == arena_r) &
                        (subset['Agents'] == ag_r) &
                        (subset['Msgs_exp_time'] == m)
                    ]
                    for lbl in labels:
                        d = cell[cell['Label'] == lbl][entry].values
                        if len(d) == 0:
                            continue
                        q1 = np.percentile(d, 25)
                        q3 = np.percentile(d, 75)
                        iqr = q3 - q1
                        whisker = np.max(d[d <= q3 + 1.5 * iqr]) if np.any(d <= q3 + 1.5 * iqr) else np.max(d)
                        outliers = d[d > q3 + 1.5 * iqr]
                        candidate = np.max(outliers) if len(outliers) > 0 else whisker
                        if max_val is None or candidate > max_val:
                            max_val = candidate
                row_maxs.append(max_val if max_val is not None else float(global_max))
            row_limits = []
            row_ticks = []
            for raw_top in row_maxs:
                if entry == "Events":
                    top_int = int(np.ceil(raw_top)) if raw_top > 0 else 1
                    desired_ticks = 10
                    step = max(1, int(np.ceil(top_int / desired_ticks)))
                    top_rounded = int(np.ceil(top_int / step) * step)
                    extra = max(1, int(0.05 * top_rounded))
                    top_plot = top_rounded + extra
                    ymin_plot = -0.03 * top_plot
                    yticks = np.arange(0, top_rounded + step, step, dtype=int)
                    row_limits.append((ymin_plot, top_plot))
                    row_ticks.append(yticks)
                else:
                    ymin_plot = 0.95
                    if raw_top <= ymin_plot:
                        log_max = 1 
                    else:
                        log_max = int(np.ceil(np.log10(raw_top)))
                    log_min = 0 
                    log_ticks = np.logspace(log_min, log_max, log_max - log_min + 1)
                    top_plot = 10 ** log_max
                    row_limits.append((ymin_plot, top_plot))
                    row_ticks.append(log_ticks)
            for i, (arena, ag) in enumerate(grid):
                plot_labels_row = labels.copy()
                for j, m in enumerate(msg_list):
                    ax = axes[i, j]
                    cell = subset[
                        (subset['Arena'] == arena) &
                        (subset['Agents'] == ag) &
                        (subset['Msgs_exp_time'] == m)
                    ]
                    if side_by_side:
                        if i == 0:
                            ax.set_title(col_labels[j])
                        cell_le = cell[cell['Error'] <= 0.05]
                        cell_gt = cell[cell['Error'] > 0.05]
                        pos = np.arange(1, len(plot_labels_row) + 1)
                        for k, lbl in enumerate(plot_labels_row):
                            d_le = cell_le[cell_le['Label'] == lbl][entry].values
                            d_gt = cell_gt[cell_gt['Label'] == lbl][entry].values
                            if len(d_le) > 0:
                                bp = ax.boxplot(
                                    d_le,
                                    positions=[pos[k] - 0.2],
                                    widths=0.35,
                                    patch_artist=True,
                                    medianprops=dict(color='orange', linewidth=2)
                                )
                                bp['boxes'][0].set_facecolor(label_color_map.get(lbl, 'black'))
                                bp['boxes'][0].set_hatch('//')
                            if len(d_gt) > 0:
                                bp = ax.boxplot(
                                    d_gt,
                                    positions=[pos[k] + 0.2],
                                    widths=0.35,
                                    patch_artist=True,
                                    medianprops=dict(color='orange', linewidth=2)
                                )
                                bp['boxes'][0].set_facecolor(label_color_map.get(lbl, 'black'))
                        ax.set_xticks(pos)
                        ax.set_xticklabels(plot_labels_row)
                    else:
                        plot_labels = plot_labels_row if j == 0 else [l for l in labels if l != r'$AN$']
                        data = []
                        lbls = []
                        for lbl in plot_labels:
                            d = cell[cell['Label'] == lbl][entry].values
                            if len(d) > 0:
                                data.append(d)
                                lbls.append(lbl)
                        if len(data) > 0:
                            bp = ax.boxplot(
                                data,
                                labels=lbls,
                                patch_artist=True,
                                medianprops=dict(color='orange', linewidth=2)
                            )
                            for patch, lbl in zip(bp['boxes'], lbls):
                                patch.set_facecolor(label_color_map.get(lbl, 'black'))
                        if i == 0:
                            ax.set_title(col_labels[j])
                    ymin_plot, top_plot = row_limits[i]
                    yticks = row_ticks[i]
                    if entry == "Time":
                        ax.set_yscale('log')
                        ax.set_ylim(ymin_plot, top_plot)
                        ax.set_yticks(yticks)
                        ax.set_yticklabels([f"$10^{{{int(np.log10(t))}}}$" for t in yticks])
                    else:
                        ax.set_yscale('linear')
                        ax.set_ylim(ymin_plot, top_plot)
                        ax.set_yticks(yticks)
                        ax.set_yticklabels([str(int(t)) for t in yticks])
                    if j > 0:
                        ax.set_yticklabels([])
                    ax.grid(True,ls=':')
                    if i != nrows - 1:
                        ax.set_xticklabels([])
                axes[i, 0].annotate(
                    r"$T_{r}$" if entry == "Time" else r"$E_{r}$",
                    xy=(-.15, 0.5),
                    xycoords='axes fraction',
                    rotation=90,
                    ha='left', va='center'
                )
                axes[i, -1].annotate(
                    row_labels[i],
                    xy=(1.05, 0.5),
                    xycoords='axes fraction',
                    rotation=90,
                    ha='left', va='center'
                )
            if side_by_side:
                legend_handles = [
                    Patch(facecolor='gray', hatch='//', label=r'$|GT - \tau| \leq 0.05$'),
                    Patch(facecolor='gray', label=r'$|GT - \tau| > 0.05$')
                ]
                fig.legend(
                    handles=legend_handles,
                    loc='lower right',
                    ncol=len(legend_handles),
                    frameon=True
                )
            fig.tight_layout(rect=[0, 0.03, 1, 0.98])
            fig.savefig(os.path.join(images_dir, f"box_{suffix}.pdf"),bbox_inches='tight')
            plt.close(fig)
        time_max = df["Time"].max()
        event_max = df["Events"].max()
        if not side_by_side:
            save_box(df[df['Error'] <= 0.05], 'le05_events', 'Events',event_max)
            save_box(df[df['Error'] <= 0.05], 'le05_time', 'Time',time_max)
            save_box(df[df['Error'] > 0.05], 'gt05_events', 'Events',event_max)
            save_box(df[df['Error'] > 0.05], 'gt05_time', 'Time',time_max)
        else:
            save_box(df, 'sidebyside_events', 'Events', event_max)
            save_box(df, 'sidebyside_time', 'Time', time_max)
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
        #                 ax.grid(True,ls=':')
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
        #             ax.grid(True,ls=':')
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
        #                 ax.grid(True,ls=':')
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
    def plot_recovery_short(self, data_in, side_by_side: bool = False):
        images_dir = os.path.join(self.base, "compressed_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cmx.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        variant_map = {}
        for p in self.protocols:
            pid = p.get("id")
            if not pid:
                continue
            variant_map[pid] = (p.get("label", pid), self._protocol_color(p, scalarMap))
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]

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
                if buf == max(0, agents - 2):
                    variant_key = 'P.1.1'
                else:
                    variant_key = 'P.1.0' if msgs > 0 else 'P.0'
            elif variant_key.startswith('P.1'):
                variant_key = 'P.1.0'

            if not self._protocol_enabled( variant_key):
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
        if df.empty:
            return
        df.loc[df['Label'].isin([r'$AN$']), 'Msgs_exp_time'] = 60
        df = df[df['Msgs_exp_time'] != 0]

        msg_list = sorted(df['Msgs_exp_time'].unique())
        msg_list = self._plot_tm_values( msg_list)
        if not msg_list:
            return
        df = df[df['Msgs_exp_time'].isin(msg_list)]
        if 60 in msg_list:
            msg_list = [60] + [m for m in msg_list if m != 60]

        labels = []
        for pid in protocols_order:
            if pid in variant_map and self._protocol_enabled( pid):
                labels.append(variant_map[pid][0])
        if not labels:
            return

        base_color_by_label = {variant_map[pid][0]: variant_map[pid][1] for pid in protocols_order if pid in variant_map}

        tm_vals = [int(m) for m in msg_list]
        if len(tm_vals) > 1:
            tm_norm = colors.LogNorm(vmin=min(tm_vals), vmax=max(tm_vals))
        else:
            tm_norm = colors.Normalize(vmin=0, vmax=1)
        tm_max = max(tm_vals) if tm_vals else 1

        def tm_color(base_color, current_tm):
            rgb_base = colors.to_rgb(base_color)
            h, l, s = colorsys.rgb_to_hls(*rgb_base)
            norm_val = tm_norm(current_tm)
            if current_tm <= 0:
                norm_val = tm_norm(tm_max)
            if np.ma.is_masked(norm_val):
                norm_val = 0.0
            if current_tm == tm_max:
                new_l, new_s = l, s
            else:
                diff = (1.0 - float(norm_val))
                new_l = max(l, min(0.85, l + (diff * 0.4)))
                new_s = s * (1.0 - (diff * 0.3))
            raw_rgb = colorsys.hls_to_rgb(h, new_l, new_s)
            return np.clip(raw_rgb, 0, 1)

        densities = [("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)]

        def event_axis_limits(max_val):
            top_int = int(np.ceil(max_val)) if max_val and max_val > 0 else 1
            desired_ticks = 10
            step = max(1, int(np.ceil(top_int / desired_ticks)))
            top_rounded = int(np.ceil(top_int / step) * step)
            extra = max(1, int(0.05 * top_rounded))
            top_plot = top_rounded + extra
            ymin_plot = -0.03 * top_plot
            yticks = np.arange(0, top_rounded + step, step, dtype=int)
            return ymin_plot, top_plot, yticks

        def time_axis_limits(max_val):
            ymin_plot = 0.95
            if max_val <= ymin_plot:
                log_max = 1
            else:
                log_max = int(np.ceil(np.log10(max_val)))
            log_ticks = np.logspace(0, log_max, log_max + 1)
            top_plot = 10 ** log_max
            return ymin_plot, top_plot, log_ticks

        def save_short(subset, suffix, side_by_side_mode: bool):
            if subset.empty:
                return
            event_max = subset["Events"].max()
            time_max = subset["Time"].max()
            fig, axes = plt.subplots(
                2, 3,
                figsize=(24, 14),
                sharex=False, sharey=False
            )
            if axes.ndim == 1:
                axes = np.array([axes])

            n_labels = len(labels)
            n_tm = len(msg_list)
            group_width = 0.8
            tm_chunk = group_width / max(1, n_tm)
            if side_by_side_mode:
                box_width = tm_chunk * 0.5
                err_offset = tm_chunk * 0.25
            else:
                box_width = tm_chunk * 0.7
                err_offset = 0

            base_positions = np.arange(1, n_labels + 1)

            for col_idx, (dens_label, arena, ag) in enumerate(densities):
                cell = subset[(subset['Arena'] == arena) & (subset['Agents'] == ag)]
                for row_idx, entry in enumerate(["Events", "Time"]):
                    ax = axes[row_idx, col_idx]
                    if row_idx == 0:
                        ax.set_title(dens_label)
                    for t_idx, tm in enumerate(msg_list):
                        tm_offset = (t_idx - (n_tm - 1) / 2.0) * tm_chunk
                        tm_positions = base_positions + tm_offset
                        for k, lbl in enumerate(labels):
                            base_color = base_color_by_label.get(lbl, 'black')
                            color = tm_color(base_color, int(tm))
                            if side_by_side_mode:
                                d_le = cell[(cell['Label'] == lbl) & (cell['Msgs_exp_time'] == tm) & (cell['Error'] <= 0.05)][entry].values
                                d_gt = cell[(cell['Label'] == lbl) & (cell['Msgs_exp_time'] == tm) & (cell['Error'] > 0.05)][entry].values
                                if len(d_le) > 0:
                                    bp = ax.boxplot(
                                        d_le,
                                        positions=[tm_positions[k] - err_offset],
                                        widths=box_width,
                                        patch_artist=True,
                                        medianprops=dict(color='orange', linewidth=2)
                                    )
                                    bp['boxes'][0].set_facecolor(color)
                                    bp['boxes'][0].set_hatch('//')
                                if len(d_gt) > 0:
                                    bp = ax.boxplot(
                                        d_gt,
                                        positions=[tm_positions[k] + err_offset],
                                        widths=box_width,
                                        patch_artist=True,
                                        medianprops=dict(color='orange', linewidth=2)
                                    )
                                    bp['boxes'][0].set_facecolor(color)
                            else:
                                d = cell[(cell['Label'] == lbl) & (cell['Msgs_exp_time'] == tm)][entry].values
                                if len(d) == 0:
                                    continue
                                bp = ax.boxplot(
                                    d,
                                    positions=[tm_positions[k]],
                                    widths=box_width,
                                    patch_artist=True,
                                    medianprops=dict(color='orange', linewidth=2)
                                )
                                bp['boxes'][0].set_facecolor(color)
                    ax.set_xticks(base_positions)
                    ax.set_xticklabels(labels if row_idx == 1 else ['' for _ in labels])
                    if row_idx == 0:
                        ymin_plot, top_plot, yticks = event_axis_limits(event_max)
                        ax.set_yscale('linear')
                        ax.set_ylim(ymin_plot, top_plot)
                        ax.set_yticks(yticks)
                        ax.set_yticklabels([str(int(t)) for t in yticks])
                        ax.set_ylabel(r"$E_{r}$" if col_idx == 0 else "")
                    else:
                        ymin_plot, top_plot, yticks = time_axis_limits(time_max)
                        ax.set_yscale('log')
                        ax.set_ylim(ymin_plot, top_plot)
                        ax.set_yticks(yticks)
                        ax.set_yticklabels([f"$10^{{{int(np.log10(t))}}}$" for t in yticks])
                        ax.set_ylabel(r"$T_{r}$" if col_idx == 0 else "")
                    if col_idx > 0:
                        ax.set_yticklabels([])
                    ax.grid(True, ls=':')
            class HandlerGradient(HandlerBase):
                def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
                    n_steps = 5
                    cmap = colors.LinearSegmentedColormap.from_list("grey_grad", ["#E0E0E0", "#2D2D2D"])
                    artists = []
                    step_width = width / n_steps
                    for i in range(n_steps):
                        color = cmap(i / n_steps)
                        r = Rectangle((xdescent + i * step_width, ydescent), step_width, height,
                                      facecolor=color, edgecolor=color, transform=trans)
                        artists.append(r)
                    return artists

            grad_rect = Rectangle((0, 0), 1, 1, label=r"$T_m$")
            if side_by_side_mode:
                legend_handles = [
                    Patch(facecolor='gray', hatch='//', label=r'$|GT - \tau| \leq 0.05$'),
                    Patch(facecolor='gray', label=r'$|GT - \tau| > 0.05$'),
                    grad_rect
                ]
            else:
                legend_handles = [grad_rect]
            fig.legend(
                handles=legend_handles,
                handler_map={grad_rect: HandlerGradient()},
                loc='lower right',
                ncol=len(legend_handles),
                frameon=True
            )
            fig.tight_layout(rect=[0, 0.05, 1, 0.98])
            fig.savefig(os.path.join(images_dir, f"box_short_{suffix}.pdf"), bbox_inches='tight')
            plt.close(fig)

        if side_by_side:
            save_short(df, "sidebyside", True)
        else:
            save_short(df[df['Error'] <= 0.05], "le05", False)
            save_short(df[df['Error'] > 0.05], "gt05", False)

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
        states_dict, times_dict = {}, {}
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
        states_dict.update({"P.0":dict_park_avg_real_fifo})
        times_dict.update({"P.0":dict_park_tmed_real_fifo})
        states_dict.update({"P.1.0":dict_park_avg})
        times_dict.update({"P.1.0":dict_park_tmed})
        states_dict.update({"P.1.1":dict_park_t1_avg})
        times_dict.update({"P.1.1":dict_park_t1_tmed})
        states_dict.update({"O.0.0":dict_adms_avg})
        times_dict.update({"O.0.0":dict_adms_tmed})
        states_dict.update({"O.2.0":dict_fifo_avg})
        times_dict.update({"O.2.0":dict_fifo_tmed})
        states_dict.update({"O.1.0":dict_rnd_avg})
        times_dict.update({"O.1.0":dict_rnd_tmed})
        states_dict.update({"O.1.1":dict_rnd_inf_avg})
        times_dict.update({"O.1.1":dict_rnd_inf_tmed})
        tmp = []
        for x in o_k:
            if int(x)!=0:
                tmp.append(x)
        o_k=tmp
        return path,ground_T,threshlds,states_dict,times_dict,o_k,[arena,agents]
        
###################################################
    def print_messages(self,data_in,data_std):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=4, label=r'$min|B|$')
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r = []
        for pid in protocols_order:
            if not self._protocol_enabled( pid):
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
        for dk in data_in.keys():
            dicts = data_in.get(dk)
            for k in dicts.keys():
                try:
                    all_cols.add(int(k[2]))
                except Exception:
                    continue
        columns = [60, 120, 180, 300, 600]
        columns = self._plot_tm_values( columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        fig, ax = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols + ncols*1.5, 5.2*ncols + ncols*0.2),sharex=True, squeeze=False, layout="constrained")
        
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x,0))))
                else:
                    void_x_ticks.append('')
        for dk in data_in.keys():
            dict_dk = data_in.get(dk)
            for k in dict_dk.keys():
                tmp = []
                res = dict_dk.get(k)
                norm = int(k[1])-1
                for xi in res:
                    tmp.append(xi/norm)
                dict_dk.update({k:tmp})
        for k in range(3):
            for z in range(ncols):
                den = 100 if k==2 else 25
                val_min_buf = 5 / den
                ax[k][z].plot([val_min_buf for _ in range(901)],color="black",ls='--',lw=3)
        for dk in data_in.keys():
            dict_dk = data_in.get(dk)
            for k in dict_dk.keys():
                if not self._protocol_enabled( dk):
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
                ax[row][col].plot(dict_dk.get(k),color=protocol_colors.get(dk,"gray"),lw=6)
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
                ax[x][y].grid(True,ls=':')
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
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=6, label=r'$min|B|$')
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r = []
        for pid in protocols_order:
            if not self._protocol_enabled( pid):
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
        for dk in data_in.keys():
            dct = data_in.get(dk)
            for k in dct.keys():
                try:
                    all_cols.add(int(k[2]))
                except Exception:
                    continue
        columns = [60, 120, 180, 300, 600]
        columns = self._plot_tm_values( columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols + ncols*1.5,5.2*ncols), squeeze=False, layout="constrained")
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x,0))))
                else:
                    void_x_ticks.append('')
        for dk in data_in.keys():
            dct = data_in.get(dk)
            for k in dct.keys():
                if not self._protocol_enabled( dk):
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
                ax[row][col].plot(dct.get(k),color=protocol_colors.get(dk,"gray"),lw=6)
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
                ax[x][y].grid(True,ls=':')
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
        po_k = keys
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = sorted(set(o_k))
        o_k = self._plot_tm_values( o_k)
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
            if not self._protocol_enabled( pid):
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
        border_font = plt.rcParams.get("font.size")
        border_font = border_font + 4 if border_font is not None else 20    
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(8*ncols + ncols*0.75,8*ncols),sharex=True, squeeze=False, layout="constrained")
        tfig, tax   = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols + ncols*1.5,5.2*ncols),sharex=True, squeeze=False, layout="constrained")
        attributes_row_col = np.zeros((3,ncols))
        str_threshlds = []
        void_str_threshlds = []
        svoid_str_threshlds = []
        str_threshlds_y = []
        void_str_threshlds_y = []
        svoid_str_threshlds_y = []
        void_str_gt = []
        void_str_tim = []
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
        prot_tables_vals_dict = {}
        for a in arena:
            if a=="smallA":
                agents = ["25"]
            else:
                agents = more_k[1]
            for ag in agents:
                row = 1  if a=="smallA" else 0
                if int(ag)==100: row = 2
                vals_dict = {}
                for dk in data_in.keys():
                    vals_dict.update({dk:([[0 for _ in range(len(threshlds))] for _ in range(len(o_k))], [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))],
                                          [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ], [ [ [[0,0],[0,0]] for _ in range(len(threshlds)) ] for _ in range(len(o_k)) ],
                                          [[0 for _ in range(len(threshlds))] for _ in range(len(o_k))])})
                for k in range(len(o_k)):
                    for dk in data_in.keys():
                        for th in range(len(threshlds)):
                            vals2, vals8, gt2, gt8= [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                            valst, lim_valst = np.nan, np.nan
                            for pt in range(len(ground_T)):
                                val    = data_in.get(dk).get((a,ag,str(o_k[k])))[pt][th] if data_in.get(dk).get((a,ag,str(o_k[k]))) is not None else None
                                tval   = times_in.get(dk).get((a,ag,str(o_k[k])))[pt][th] if times_in.get(dk).get((a,ag,str(o_k[k]))) is not None else None
                                if val is not None:
                                    if val>=0.8:
                                        temp_tval = tval
                                        if ground_T[pt]-threshlds[th]  >= 0.09 and (valst is np.nan or ground_T[pt]-threshlds[th]<lim_valst):
                                            valst = temp_tval
                                            lim_valst = ground_T[pt]-threshlds[th]
                                        if ground_T[pt]-threshlds[th] >=0 and (vals8[1] is np.nan or val<vals8[1]):
                                            vals8[1]  = val
                                            gt8[1]    = ground_T[pt]
                                    elif val<=0.2:
                                        if ground_T[pt]-threshlds[th] <=0 and (vals2[0] is np.nan or val>=vals2[0]):
                                            vals2[0]  = val
                                            gt2[0]    = ground_T[pt]
                                    else:
                                        if vals8[0] is np.nan or val>vals8[0]:
                                            vals8[0]  = val
                                            gt8[0]    = ground_T[pt]
                                        if vals2[1] is np.nan or val<vals2[1]:
                                            vals2[1]  = val
                                            gt2[1]    = ground_T[pt]
                            if vals8[0] is np.nan:
                                vals8[0] = vals8[1]
                                gt8[0] = gt8[1]
                            elif vals8[1] is np.nan:
                                vals8[1] = vals8[0]
                                gt8[1] = gt8[0]
                            if vals2[0] is np.nan:
                                vals2[0] = vals2[1]
                                gt2[0] = gt2[1]
                            elif vals2[1] is np.nan:
                                vals2[1] = vals2[0]
                                gt2[1] = gt2[0]
                            temp_vals = list(vals_dict.get(dk))
                            temp_vals[0][k][th]  = np.around(np.interp([0.2],vals2,gt2,left=np.nan),3)
                            temp_vals[1][k][th]  = np.around(np.interp([0.8],vals8,gt8,right=np.nan),3)
                            temp_vals[2][k][th]  = [vals2,gt2]
                            temp_vals[3][k][th]  = [vals8,gt8]
                            temp_vals[4][k][th]  = valst
                            vals_dict.update({dk:tuple(temp_vals)})
                        ax[row][k].plot(np.arange(0.5,1.01,0.01),color='black',lw=5,ls=':')
                        if self._protocol_enabled( dk):
                            ax[row][k].plot(vals_dict.get(dk)[0][k],color=protocol_colors.get(dk,"gray"),lw=6,ls='--')
                            ax[row][k].plot(vals_dict.get(dk)[1][k],color=protocol_colors.get(dk,"gray"),lw=6,ls='-')
                            tax[row][k].plot(vals_dict.get(dk)[4][k],color=protocol_colors.get(dk,"gray"),lw=6)
                        if attributes_row_col[row][k] == 0:
                            attributes_row_col[row][k] = 1
                            self._borders_attributes(ax,tax,row,k,svoid_str_threshlds,svoid_str_threshlds_y,void_str_threshlds,void_str_threshlds_y,
                                                        o_k,border_font,str_threshlds,str_threshlds_y,ncols,void_str_gt)
                key= (a,ag)
                prot_tables_vals_dict[key] = {
                    "vals2p": vals_dict.get("P.1.0")[0], "vals8p": vals_dict.get("P.1.0")[1],
                    "vals2pr": vals_dict.get("P.0")[0], "vals8pr": vals_dict.get("P.0")[1],
                    "vals2a": vals_dict.get("O.0.0")[0], "vals8a": vals_dict.get("O.0.0")[1],
                    "vals2f": vals_dict.get("O.2.0")[0], "vals8f": vals_dict.get("O.2.0")[1],
                    "vals2r": vals_dict.get("O.1.1")[0], "vals8r": vals_dict.get("O.1.1")[1],
                    "vals2ri": vals_dict.get("O.1.0")[0], "vals8ri": vals_dict.get("O.1.0")[1],
                }
        for axes in ax.flat:
            for label in (axes.get_xticklabels() + axes.get_yticklabels()):
                label.set_fontsize(border_font)
            if axes.get_xlabel():
                axes.set_xlabel(axes.get_xlabel(), fontsize=border_font)
            if axes.get_ylabel():
                axes.set_ylabel(axes.get_ylabel(), fontsize=border_font)
        legend = fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_c,ncols=9, loc='upper right',framealpha=0.7,borderaxespad=0)
        if legend is not None:
            for text in legend.get_texts():
                text.set_fontsize(border_font)
        fig.tight_layout()
        tfig.tight_layout()
        fig_path = path+_type+"_activation.pdf"
        tfig_path = path+t_type+"_time.pdf"
        # fig_path = path+_type+"_activation.png"
        # tfig_path = path+t_type+"_time.png"
        tfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=7,loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        tfig.savefig(tfig_path, bbox_inches='tight')
        plt.close(fig)
        plt.close(tfig)
        # self.plot_protocol_tables(path, o_k, ground_T, threshlds, prot_tables_vals_dict)

###################################################
    def _borders_attributes(self,ax,tax,row,k,svoid_str_threshlds,svoid_str_threshlds_y,void_str_threshlds,void_str_threshlds_y,
                            o_k,border_font,str_threshlds,str_threshlds_y,ncols,void_str_gt):
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
            axt.set_xlabel(rf"$T_m = {int(o_k[k])}\, s$", fontsize=border_font)
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
            if row == 0:
                axt.set_ylabel("LD25", fontsize=border_font)
                taxt.set_ylabel("LD25")
            elif row == 1:
                axt.set_ylabel("HD25", fontsize=border_font)
                taxt.set_ylabel("HD25")
            else:
                axt.set_ylabel("HD100")
                taxt.set_ylabel("HD100", fontsize=border_font)
        else:
            ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
            ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
        ax[row][k].grid(which='major',ls=':')
        tax[row][k].grid(which='major',ls=':')

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
                        ("anonymous_ps", "ps"),
                        ("id_broad", "a"),
                        ("id_rebroad_fifo", "f"),
                        ("id_rebroad_rnd", "r"),
                        ("id_rebroad_rnd_inf", "ri"),
                    ]
                else:
                    protocols = [
                        ("anonymous", "p"),
                        ("anonymous_ps", "ps"),
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
                            if gt in vals2[idx][j][1]:
                                pos = vals2[idx][j][1].index(gt)
                                v2 = vals2[idx][j][0][pos]
                                v2_txt = f"{v2:.2f}"
                            if gt in vals8[idx][j][1]:
                                pos = vals8[idx][j][1].index(gt)
                                v8 = vals8[idx][j][0][pos]
                                v8_txt = f"{v8:.2f}"
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
    def _group_tables(self, tot_states, tot_times, tot_msgs):
        _,ground_T,threshlds,states_dict,times_dict,o_k,[arena,agents] = self.plot_active(tot_states,tot_times)
        messages_dict, stds_dict = self.plot_messages(tot_msgs)
        return ground_T,threshlds,states_dict,times_dict,o_k,[arena,agents], messages_dict, stds_dict

###################################################
    def plot_compressed_table(self, tot_states_in, tot_times_in, tot_msgs_in):
        if not os.path.exists(self.base+"/compressed_data/images/"):
            os.makedirs(self.base+"/compressed_data/images/")
        path = self.base+"/compressed_data/images/"
        ground_T,threshlds,dk_tot_states,dk_tot_times,o_k,[arena,agents], dk_tot_msgs, dk_stds_dict = self._group_tables(tot_states_in, tot_times_in, tot_msgs_in)
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        all_tm = sorted([int(x) for x in o_k if x is not None and int(x) > 0])
        all_tm = self._plot_tm_values(all_tm)
        if not all_tm:
            return
        tm_set = set(int(x) for x in all_tm)
        tm_norm = colors.LogNorm(vmin=min(all_tm), vmax=max(all_tm))
        all_gt = sorted(list(ground_T))
        all_thr = sorted(list(threshlds))
        fig, ax = plt.subplots(3, 3, figsize=(24, 20), constrained_layout=True, squeeze=False,gridspec_kw={'height_ratios': [1, 1, 1.4]})
        min_buf = np.zeros(3)
        mid_act = np.zeros(3)
        to_plot_states_vals_dict = {}
        max_time = 0
        ref_x = np.arange(0.5, 1.01, 0.01)
        for dk in dk_tot_msgs.keys():
            if self._protocol_enabled( dk):
                for timer in all_tm:
                    to_plot_states_vals_dict.update({(dk,timer):([0 for _ in range(len(threshlds))], [0 for _ in range(len(threshlds))],
                                                    [ [[0,0],[0,0]] for _ in range(len(threshlds)) ], [ [[0,0],[0,0]] for _ in range(len(threshlds)) ],
                                                    [0 for _ in range(len(threshlds))])})
                tot_msgs = dk_tot_msgs.get(dk)
                tot_states = dk_tot_states.get(dk)
                tot_times = dk_tot_times.get(dk)
                base_color = protocol_colors.get(dk, 'gray')
                rgb_base = colors.to_rgb(base_color)
                h, l, s = colorsys.rgb_to_hls(*rgb_base)
                # --- ROW 0: MESSAGES ---
                for key, msg_series in tot_msgs.items():
                    try:
                        current_tm = int(key[2])
                        if current_tm not in tm_set:
                            continue
                        norm_val = tm_norm(current_tm)
                        if current_tm <= 0:
                            norm_val = tm_norm(max(all_tm))
                        if np.ma.is_masked(norm_val):
                            norm_val = 0.0
                        if current_tm == max(all_tm):
                            new_l = l
                            new_s = s
                        else:
                            diff = (1.0 - float(norm_val))
                            new_l = max(l, min(0.85, l + (diff * 0.4))) 
                            new_s = s * (1.0 - (diff * 0.3))

                        raw_rgb = colorsys.hls_to_rgb(h, new_l, new_s)
                        stepped_color = np.clip(raw_rgb, 0, 1)

                        y_data = np.array(msg_series)
                        num_agents = int(key[1])
                        col_idx = 2 if num_agents == 100 else 1 if key[0] == "small" and num_agents == 25 else 0
                        if min_buf[col_idx]==0:
                            min_buf[col_idx]=1
                            ax[0][col_idx].plot([5 / (num_agents - 1) for _ in range(901)], 
                                            color="black", ls='-.',
                                            lw=3)

                        ax[0][col_idx].plot(y_data / (num_agents - 1),color=stepped_color,lw=4,alpha=0.75)
                    except Exception as e:
                        print(f"Skipping key {key} due to error: {e}")
                        continue
                # --- ROW 1 & 2: BORDERS & TIMES ---
                for key, state_series in tot_states.items():
                    time_series = tot_times.get(key)
                    try:
                        current_tm = int(key[2])
                        if current_tm not in tm_set:
                            continue
                        norm_val = tm_norm(current_tm)
                        if current_tm <= 0 or dk=="P.0":
                            norm_val = tm_norm(max(all_tm))
                        if np.ma.is_masked(norm_val):
                            norm_val = 0.0
                        if current_tm == max(all_tm):
                            new_l = l
                            new_s = s
                        else:
                            diff = (1.0 - float(norm_val))
                            new_l = max(l, min(0.85, l + (diff * 0.4))) 
                            new_s = s * (1.0 - (diff * 0.3))

                        raw_rgb = colorsys.hls_to_rgb(h, new_l, new_s)
                        stepped_color = np.clip(raw_rgb, 0, 1)
                        for th in range(len(threshlds)):
                            vals2, vals8, gt2, gt8= [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                            valst, lim_valst = np.nan, np.nan
                            for pt in range(len(ground_T)):
                                val    = state_series[pt][th]
                                tval   = time_series[pt][th]
                                if val is not None:
                                    if val>=0.8:
                                        temp_tval = tval
                                        if ground_T[pt]-threshlds[th]  >= 0.09 and (valst is np.nan or ground_T[pt]-threshlds[th]<lim_valst):
                                            valst = temp_tval
                                            lim_valst = ground_T[pt]-threshlds[th]
                                        if ground_T[pt]-threshlds[th] >=0 and (vals8[1] is np.nan or val<vals8[1]):
                                            vals8[1]  = val
                                            gt8[1]    = ground_T[pt]
                                    elif val<=0.2:
                                        if ground_T[pt]-threshlds[th] <=0 and (vals2[0] is np.nan or val>=vals2[0]):
                                            vals2[0]  = val
                                            gt2[0]    = ground_T[pt]
                                    else:
                                        if vals8[0] is np.nan or val>vals8[0]:
                                            vals8[0]  = val
                                            gt8[0]    = ground_T[pt]
                                        if vals2[1] is np.nan or val<vals2[1]:
                                            vals2[1]  = val
                                            gt2[1]    = ground_T[pt]
                            if vals8[0] is np.nan:
                                vals8[0] = vals8[1]
                                gt8[0] = gt8[1]
                            elif vals8[1] is np.nan:
                                vals8[1] = vals8[0]
                                gt8[1] = gt8[0]
                            if vals2[0] is np.nan:
                                vals2[0] = vals2[1]
                                gt2[0] = gt2[1]
                            elif vals2[1] is np.nan:
                                vals2[1] = vals2[0]
                                gt2[1] = gt2[0]
                            temp_vals = list(to_plot_states_vals_dict.get((dk,current_tm)))
                            temp_vals[0][th]  = np.around(np.interp([0.2],vals2,gt2,left=np.nan),3)
                            temp_vals[1][th]  = np.around(np.interp([0.8],vals8,gt8,right=np.nan),3)
                            temp_vals[2][th]  = [vals2,gt2]
                            temp_vals[3][th]  = [vals8,gt8]
                            temp_vals[4][th]  = valst
                            if max_time < valst: max_time = valst
                            to_plot_states_vals_dict.update({(dk,current_tm):tuple(temp_vals)})
                        num_agents = int(key[1])
                        col_idx = 2 if num_agents == 100 else 1 if key[0] == "smallA" and num_agents == 25 else 0
                        if mid_act[col_idx] == 0:
                            mid_act[col_idx] = 1
                            ax[2][col_idx].plot(ref_x, ref_x, color='black', lw=3, ls=':')
                        ax[2][col_idx].plot(threshlds,to_plot_states_vals_dict.get((dk,current_tm))[0],color=stepped_color,lw=4,alpha=0.75,ls='--')
                        ax[2][col_idx].plot(threshlds,to_plot_states_vals_dict.get((dk,current_tm))[1],color=stepped_color,lw=4,alpha=0.75,ls='-')
                        ax[1][col_idx].plot(threshlds,to_plot_states_vals_dict.get((dk,current_tm))[4],color=stepped_color,lw=4,alpha=0.75)
                    except Exception as e:
                        print(f"Skipping key {key} due to error: {e}")
                        continue

        self._finalize_compressed_plot(fig, ax, path, protocol_colors, threshlds, max_time, inset_tm_values, msg_data_dict, all_tm, tm_norm, dk_tot_msgs.keys())

###################################################
    def _finalize_compressed_plot(self, fig, ax, path, protocol_colors,tau_ticks,max_time):
        class HandlerGradient(HandlerBase):
            def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
                n_steps = 5
                cmap = colors.LinearSegmentedColormap.from_list("grey_grad", [ "#E0E0E0","#2D2D2D"])
                artists = []
                step_width = width / n_steps
                for i in range(n_steps):
                    color = cmap(i / n_steps)
                    r = Rectangle((xdescent + i * step_width, ydescent), step_width, height, 
                                  facecolor=color, edgecolor=color, transform=trans)
                    artists.append(r)
                return artists
        column_titles = ["LD25","HD25","HD100"]
        tau_values = [float(t) for t in tau_ticks]
        for i in range(3):
            if i == 0:
                for j in range(3):
                    ax[i][j].set_title(column_titles[j], pad=20)
                    ax[i][j].set_xlim((0, 901))
                    ax[i][j].set_xticks([0, 300, 600, 900])
                    ax[i][j].set_xlabel(r"$T\, (s)$")
            for j in range(3):
                if i == 1 or i == 2:
                    ax[i][j].set_xlim((0.5, 1))
                    ax[i][j].xaxis.set_major_locator(MultipleLocator(0.1))
                    ax[i][j].xaxis.set_major_formatter(FormatStrFormatter('%.1f'))
                    ax[i][j].xaxis.set_minor_locator(MultipleLocator(0.05))
                if i == 0:
                    ax[i][j].set_ylim((-0.01, 1.01))
                elif i == 1:
                    ax[i][j].set_ylim((0, max_time + 10))
                    ax[i][j].set_xticklabels(["" for _ in ax[i][j].get_xticks()])
                elif i == 2:
                    ax[i][j].set_ylim((0.5, 1))
                    ax[i][j].set_xlabel(r"$\tau$")
                ax[i][j].grid(True, ls=':', which='major')
                ax[i][j].tick_params(axis='both', which='major')
                ax[i][j].spines['top'].set_visible(False)
                ax[i][j].spines['right'].set_visible(False)
                if j == 1 or j == 2:
                    ax[i][j].set_yticklabels(["" for _ in ax[i][j].get_yticks()])
        ax[0][0].set_ylabel(r"$M$")
        ax[1][0].set_ylabel(r"$T\, (s)$")
        ax[2][0].set_ylabel(r"$G$")
        legend_elements = []
        for p in self.protocols:
            p_id = p.get("id")
            if self._protocol_enabled( p_id):
                label = p.get("label", p_id)
                color = protocol_colors.get(p_id, 'gray')
                legend_elements.append(Line2D([0], [0], color=color, linestyle='None', 
                                              marker='s', markersize=16, label=label))
        grad_rect = Rectangle((0, 0), 1, 1, label=r"$T_m$")
        legend_elements.append(Line2D([], [], color="black", lw=4, ls='-.', label=r'$min|B|$'))
        legend_elements.append(Line2D([0], [0], color='black', lw=4, ls='--', label=r'$\hat{Q}=0.2$'))
        legend_elements.append(Line2D([0], [0], color='black', lw=4, ls='-', label=r'$\hat{Q}=0.8$'))
        legend_elements.append(grad_rect)

        fig.legend(handles=legend_elements, 
                   handler_map={grad_rect: HandlerGradient()},
                   loc='upper right',
                   bbox_to_anchor=(1, 0),
                   ncol=9, 
                   frameon=True,
                   edgecolor='0.8')

        save_name = "compressed_summary.pdf"
        plt.savefig(os.path.join(path, save_name), bbox_inches='tight', dpi=300)
        plt.close(fig)