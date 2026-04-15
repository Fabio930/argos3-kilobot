import sys, os, csv, logging, re, json, colorsys
import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.cm as cm
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
class GradientHandler(HandlerBase):
    def __init__(self, cmap):
        self.cmap = cmap
        super().__init__()
        
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        n_steps = 5  
        artists = []
        step_width = width / n_steps
        for i in range(n_steps):
            color = self.cmap(i / (n_steps - 1) if n_steps > 1 else 1)
            r = Rectangle((xdescent + i * step_width, ydescent), step_width - 1.5, height, 
                          facecolor=color, edgecolor='none', transform=trans)
            artists.append(r)
        return artists

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
    
###################################################
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

    def event_axis_limits(self, max_val):
        top_int = int(np.ceil(max_val)) if max_val and max_val > 0 else 1
        desired_ticks = 10
        step = max(1, int(np.ceil(top_int / desired_ticks)))
        top_rounded = int(np.ceil(top_int / step) * step)
        extra = max(1, int(0.05 * top_rounded))
        top_plot = top_rounded + extra
        ymin_plot = -0.03 * top_plot
        yticks = np.arange(0, top_rounded + step, step, dtype=int)
        return ymin_plot, top_plot, yticks

    def time_axis_limits(self, max_val):
        ymin_plot = 0.95
        if max_val <= ymin_plot:
            log_max = 1
        else:
            log_max = int(np.ceil(np.log10(max_val)))
        log_ticks = np.logspace(0, log_max, log_max + 1)
        top_plot = 10 ** log_max
        return ymin_plot, top_plot, log_ticks

###################################################
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
    def apply_plot_overrides(self, plot_names, exclude_protocols=None, exclude_tm=None, insert=None):
        if not plot_names:
            return
        plot_cfg = self.plot_config.setdefault("plots", {})
        if exclude_protocols is not None:
            plot_cfg["exclude_protocols"] = exclude_protocols
        if exclude_tm is not None:
            plot_cfg["exclude_tm"] = exclude_tm
        if insert is not None:
            plot_cfg["insert"] = insert

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
    def _get_valid_insert_tm(self):
            plot_cfg = self.plot_config.get("plots", {})
            exclude_raw = plot_cfg.get("exclude_tm", [])
            insert_raw = plot_cfg.get("insert", [])
            
            exclude_set = set()
            for v in exclude_raw:
                norm = self._normalize_tm(v)
                if norm is not None:
                    exclude_set.add(norm)
                    
            valid_insert = []
            for v in insert_raw:
                nv = self._normalize_tm(v)
                if nv is not None and nv in exclude_set:
                    valid_insert.append(nv)
                    
            return sorted(list(set(valid_insert)))

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
            max_buff_size = k[6] if len(k) > 6 else str(max(0, n_agents - 1))
            is_priority_sampling = algo == 'ps' or (algo == 'p' and buff_dim == max(0, n_agents - 2))

            if is_priority_sampling and buff_dim > 0:
                dict_park_t1.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[0]})
                std_dict_park_t1.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[1]})
            elif k[1]=='P' and int(k[4]) > 0:
                dict_park.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[0]})
                std_dict_park.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[1]})
            elif k[1]=='P' and int(k[4]) == 0:
                dict_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):data.get(k)[0]})
                std_dict_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):data.get(k)[1]})
            if k[1]=='O':
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[0]})
                    std_dict_adam.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[1]})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[0]})
                    std_dict_fifo.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[1]})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[0]})
                        std_dict_rnd.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[1]})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[0]})
                        std_dict_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):data.get(k)[1]})
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
        messages_dict.update({"O.1.1":dict_rnd})
        stds_dict.update({"O.1.1":std_dict_rnd})
        messages_dict.update({"O.1.0":dict_rnd_inf})
        stds_dict.update({"O.1.0":std_dict_rnd_inf})

        return messages_dict,stds_dict


###################################################
    def plot_decisions(self,data):
        decisions_dict = {}
        dict_park, dict_park_t1, dict_park_real_fifo, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{},{},{}
        for k in data.keys():
            algo = str(k[1]).strip().lower()
            n_agents = int(k[3]) if len(k) > 3 else 0
            buf_dim = int(k[4]) if len(k) > 4 else 0
            max_buff_size = k[6] if len(k) > 6 else str(max(0, n_agents - 1))
            is_priority_sampling = algo == 'ps' or (algo == 'p' and buf_dim == max(0, n_agents - 2))

            if is_priority_sampling and buf_dim > 0:
                dict_park_t1.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
            elif is_priority_sampling and buf_dim == 0:
                dict_park_real_fifo.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
            elif k[1]=='P' and int(k[4]) > 0:
                dict_park.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
            elif k[1]=='P' and int(k[4]) == 0:
                dict_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):data.get(k)})
            else:
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):data.get(k)})
        decisions_dict.update({"P.0":dict_park_real_fifo})
        decisions_dict.update({"P.1.0":dict_park})
        decisions_dict.update({"P.1.1":dict_park_t1})
        decisions_dict.update({"O.0.0":dict_adam})
        decisions_dict.update({"O.2.0":dict_fifo})
        decisions_dict.update({"O.1.1":dict_rnd})
        decisions_dict.update({"O.1.0":dict_rnd_inf})
        self.print_decisions(decisions_dict)

###################################################
    def read_msgs_csv(self, path):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            header_idx = {name: i for i, name in enumerate(header)}
            data_idx = header_idx.get("data", len(header) - 1)
            arena_idx = header_idx.get("arena_size", 0)
            algo_idx = header_idx.get("algo", 1)
            broadcast_idx = header_idx.get("broadcast", 2)
            n_agents_idx = header_idx.get("n_agents", 3)
            buff_idx = header_idx.get("buff_dim", 4)
            msg_hops_idx = header_idx.get("msg_hops", 5)
            eff_idx = header_idx.get("buff_dim_eff", header_idx.get("max_buff_size"))
            parse_float = self._parse_float_list 
            for row in reader:
                if len(row) <= data_idx:
                    continue
                algo_val = row[algo_idx] if len(row) > algo_idx else ""
                buff_val = row[buff_idx] if len(row) > buff_idx else ""
                n_agents_val = row[n_agents_idx] if len(row) > n_agents_idx else ""
                eff_val = None
                if eff_idx is not None and len(row) > eff_idx:
                    eff_val = row[eff_idx]
                elif eff_idx is None and len(row) > len(header):
                    eff_val = row[-1]
                max_buff_val = eff_val
                if max_buff_val in (None, "", "-", "nan"):
                    try:
                        max_buff_val = str(int(float(n_agents_val)) - 1)
                    except Exception:
                        max_buff_val = ""
                        
                key = (
                    row[arena_idx] if len(row) > arena_idx else "",
                    algo_val,
                    row[broadcast_idx] if len(row) > broadcast_idx else "",
                    n_agents_val,
                    buff_val,
                    row[msg_hops_idx] if len(row) > msg_hops_idx else "",
                    max_buff_val,
                )
                data[key] = (parse_float(row[data_idx]), [])
        return data
    
###################################################
    def read_msgs_csv_w_std(self, path):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            header_idx = {name: i for i, name in enumerate(header)}
            data_idx = header_idx.get("data", len(header) - 2)
            std_idx = header_idx.get("std", data_idx + 1)
            arena_idx = header_idx.get("arena_size", 0)
            algo_idx = header_idx.get("algo", 1)
            broadcast_idx = header_idx.get("broadcast", 2)
            n_agents_idx = header_idx.get("n_agents", 3)
            buff_idx = header_idx.get("buff_dim", 4)
            msg_hops_idx = header_idx.get("msg_hops", 5)
            eff_idx = header_idx.get("buff_dim_eff", header_idx.get("max_buff_size"))
            parse_float = self._parse_float_list
            for row in reader:
                if len(row) <= max(data_idx, std_idx):
                    continue
                algo_val = row[algo_idx] if len(row) > algo_idx else ""
                buff_val = row[buff_idx] if len(row) > buff_idx else ""
                n_agents_val = row[n_agents_idx] if len(row) > n_agents_idx else ""
                eff_val = None
                if eff_idx is not None and len(row) > eff_idx:
                    eff_val = row[eff_idx]
                elif eff_idx is None and len(row) > len(header):
                    eff_val = row[-1]
                max_buff_val = eff_val
                if max_buff_val in (None, "", "-", "nan"):
                    try:
                        max_buff_val = str(int(float(n_agents_val)) - 1)
                    except Exception:
                        max_buff_val = ""
                        
                key = (
                    row[arena_idx] if len(row) > arena_idx else "",
                    algo_val,
                    row[broadcast_idx] if len(row) > broadcast_idx else "",
                    n_agents_val,
                    buff_val,
                    row[msg_hops_idx] if len(row) > msg_hops_idx else "",
                    max_buff_val,
                )
                data[key] = (
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
            
            header_idx = {name: i for i, name in enumerate(header)}
            t_idx = header_idx.get("type", len(header) - 3)
            d_idx = header_idx.get("data", t_idx + 1)
            s_idx = header_idx.get("std", t_idx + 2)
            
            exp_len_idx = header_idx.get("ExperimentLength", 0)
            rebroad_idx = header_idx.get("Rebroadcast", 1)
            robots_idx = header_idx.get("Robots", 2)
            comm_perc_idx = header_idx.get("committed_perc", 3)
            thr_idx = header_idx.get("threshold", 4)
            min_buf_idx = header_idx.get("min_buff_dim", 5)
            msg_exp_idx = header_idx.get("msg_exp_time", 6)
            msg_hops_idx = header_idx.get("msg_hops", 7)
            eff_idx = header_idx.get("buff_dim_eff", header_idx.get("max_buff_size"))
            
            parse_float = self._parse_float_list
            for row in reader:
                if len(row) <= s_idx:
                    continue
                
                exp_time = row[exp_len_idx] if len(row) > exp_len_idx else ""
                comm = row[rebroad_idx] if len(row) > rebroad_idx else ""
                n_agents = row[robots_idx] if len(row) > robots_idx else ""
                gt = row[comm_perc_idx] if len(row) > comm_perc_idx else ""
                thrlds = row[thr_idx] if len(row) > thr_idx else ""
                min_buff_dim = row[min_buf_idx] if len(row) > min_buf_idx else ""
                msg_time = row[msg_exp_idx] if len(row) > msg_exp_idx else ""
                msg_hops = row[msg_hops_idx] if len(row) > msg_hops_idx else ""
                
                eff_val = None
                if eff_idx is not None and len(row) > eff_idx:
                    eff_val = row[eff_idx]
                
                max_buff_val = eff_val
                if max_buff_val in (None, "", "-", "nan"):
                    try:
                        max_buff_val = str(int(float(n_agents)) - 1)
                    except Exception:
                        max_buff_val = ""
                        
                tipo = row[t_idx] if len(row) > t_idx else ""

                key = (algo, arena, n_runs, exp_time, comm, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops, max_buff_val, tipo)
                
                data[key] = (
                    parse_float(row[d_idx]),
                    parse_float(row[s_idx], allow_dash=True)
                )
        return data

###################################################
    def divide_data(self,data):
        states, times = {},{}
        algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops, max_buff_size = [],[],[],[],[],[],[],[],[],[],[],[]
        for k in data.keys():
            if k[0] not in algorithm: algorithm.append(k[0])
            if k[1] not in arena_size: arena_size.append(k[1])
            if k[2] not in n_runs: n_runs.append(k[2])
            if k[3] not in exp_time: exp_time.append(k[3])
            if k[4] not in communication: communication.append(k[4])
            if k[5] not in n_agents: n_agents.append(k[5])
            if k[6] not in gt: gt.append(k[6])
            if k[7] not in thrlds: thrlds.append(k[7])
            if k[8] not in min_buff_dim: min_buff_dim.append(k[8])
            if k[9] not in msg_time: msg_time.append(k[9])
            if k[10] not in msg_hops: msg_hops.append(k[10])
            if k[11] not in max_buff_size: max_buff_size.append(k[11])
            
            tipo = k[12]
            if tipo == "times":
                times.update({k[:-1]:data.get(k)})
            elif tipo == "swarm_state":
                states.update({k[:-1]:data.get(k)})
                
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops, max_buff_size), states, times
                
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
        
        images_dir = os.path.join(self.base, "rec_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cm.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        
        variant_map = {}
        for p in self.protocols:
            pid = p.get("id")
            if pid: variant_map[pid] = (p.get("label", pid), self._protocol_color(p, scalarMap))
        
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        rows = []
        
        for key, value in data_in.items():
            mean, std, events = float(value[0]), float(value[1]), float(value[2])
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k[:10]
            
            mbs = buf
            
            alg_lower = str(alg).strip().lower()
            if alg_lower == 'ps':
                variant_key = 'P.1.1'
            elif alg_lower == 'p':
                variant_key = 'P.1.1' if int(buf) == max(0, int(agents) - 2) else ('P.1.0' if int(msgs) > 0 else 'P.0')
            else:
                variant_key = f"{alg}.{int(broadcast)}.{int(hops)}"

            if not self._protocol_enabled(variant_key): continue
            
            label, color = variant_map.get(variant_key, ('UNK', 'black'))
            rows.append({
                'Arena': str(arena), 'Agents': int(agents), 'Msgs_exp_time': int(msgs),
                'Error': abs(float(gt) - float(th)), 'Events': events / (100 * int(agents)),
                'Time': mean, 'VariantKey': variant_key, 'Label': label, 'Color': color, 'MBS': mbs
            })
            
        df = pd.DataFrame(rows)
        if not df.empty:
            df.loc[df['Label'].isin([r'$AN$']), 'Msgs_exp_time'] = 60
            df = df[df['Msgs_exp_time'] != 0]
        
        grid = [("bigA", 25), ("smallA", 25), ("bigA", 100)]
        row_labels = ["LD25", "HD25", "HD100"]
        
        if df.empty: return
        msg_list = self._plot_tm_values(sorted(df['Msgs_exp_time'].unique()))
        if not msg_list: return
        
        if 60 in msg_list:
            msg_list = [60] + [m for m in msg_list if m != 60]
        col_labels = [f"$T_m$={m}" for m in msg_list]
        
        mbs_global_map = {}
        for ag in df['Agents'].unique():
            mbs_vals = df[(df['VariantKey'] == 'P.1.1') & (df['Agents'] == ag)]['MBS'].unique()
            mbs_global_map[ag] = sorted(list(mbs_vals), key=lambda x: float(x))

        def save_box(subset, threshold_str, entry, global_max):
            if subset.empty: return
            
            nrows, ncols = len(msg_list), len(grid)
            fig, axes = plt.subplots(nrows, ncols, figsize=(ncols*8, nrows*8), squeeze=False, sharex=True, sharey=True)
            
            for i, tm_val in enumerate(msg_list):
                for j, (arena_type, ag_num) in enumerate(grid):
                    ax = axes[i, j]
                    
                    # Strict .loc filtering to avoid empty fragments
                    mask_base = (subset['Arena'] == arena_type) & (subset['Agents'] == ag_num)
                    base_cell = subset.loc[mask_base]
                    pos_idx = 1
                    tick_labels, tick_pos = [], []

                    for pid in protocols_order:
                        if not self._protocol_enabled(pid): continue
                        
                        target_tm = 60 if pid == 'P.0' else tm_val
                        mask_p = (base_cell['VariantKey'] == pid) & (base_cell['Msgs_exp_time'] == target_tm)
                        p_cell = base_cell.loc[mask_p]
                        
                        base_color = variant_map[pid][1]
                        width = 0.3
                        
                        if pid == "P.1.1":
                            mbs_list = mbs_global_map.get(ag_num, [])
                            n_mbs_total = len(mbs_list)
                            
                            if n_mbs_total > 0:
                                for m_idx, val_mbs in enumerate(mbs_list):
                                    d = p_cell.loc[p_cell['MBS'] == val_mbs, entry].dropna().astype(float).values
                                    if len(d) > 0:
                                        ratio = (m_idx + 1) / n_mbs_total
                                        h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(base_color))
                                        c_val = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0-ratio)*0.4))), s*(1.0-((1.0-ratio)*0.3)))
                                        
                                        offset = (m_idx - (n_mbs_total - 1) / 2.0) * width
                                        ax.boxplot(d, positions=[pos_idx + offset], widths=width, patch_artist=True,
                                                   boxprops=dict(facecolor=c_val), medianprops=dict(color='gray'))
                            else:
                                d = p_cell[entry].dropna().astype(float).values
                                if len(d) > 0:
                                    ax.boxplot(d, positions=[pos_idx], widths=width, patch_artist=True,
                                               boxprops=dict(facecolor=base_color), medianprops=dict(color='gray'))
                        else:
                            d = p_cell[entry].dropna().astype(float).values
                            if len(d) > 0:
                                ax.boxplot(d, positions=[pos_idx], widths=width, patch_artist=True,
                                           boxprops=dict(facecolor=base_color), medianprops=dict(color='gray'))
                        
                        tick_pos.append(pos_idx)
                        tick_labels.append(variant_map[pid][0])
                        pos_idx += 1
                    
                    # Force X-limits to guarantee boxes are visible within bounds
                    ax.set_xlim(0.5, pos_idx - 0.5)
                    
                    ax.set_xticks(tick_pos)
                    ax.set_xticklabels(tick_labels, rotation=45)
                    ax.grid(True, ls=':')
                    
                    if entry == "Time": 
                        ax.set_yscale('log')
                        ax.set_ylim(self.time_axis_limits(global_max)[:2])
                    else:
                        ax.set_ylim(self.event_axis_limits(global_max)[:2])
                        
                    if i == 0: 
                        ax.set_title(row_labels[j], fontsize=plt.rcParams.get("font.size", 30))
                    
                    if j == 0:
                        row_label_left = r"$E_{r}$" if entry == "Events" else r"$T_{r}$"
                        ax.set_ylabel(row_label_left, fontsize=28)
                    
                    if j == ncols - 1:
                        ax.annotate(f"$T_m$={tm_val} s", xy=(1.03, 0.5), xycoords='axes fraction',
                                    rotation=270, ha='left', va='center', fontsize=plt.rcParams.get("font.size", 30))

            # cmap_grey = colors.LinearSegmentedColormap.from_list('custom_grey', ['#2D2D2D','#E0E0E0'])
            # gradient = [Rectangle((0,0), 1, 1, label="K-sampling")]
            # legend_elements = [Line2D([0], [0], color=v[1], marker='s', linestyle='None', markersize=16, label=v[0]) for k, v in variant_map.items() if self._protocol_enabled(k)]
            
            # fig.legend(handles=gradient+legend_elements, loc='lower center', ncol=4, 
            #            bbox_to_anchor=(0.7, 0.0), handler_map={Rectangle: GradientHandler(cmap_grey)})
            
            fig.tight_layout(rect=[0, 0.05, 1, 0.98])
            fig.savefig(os.path.join(images_dir, f"box_recovery_{threshold_str}_{entry}.pdf"), bbox_inches='tight')
            plt.close(fig)

        if df.empty: return
        time_max = df["Time"].max()
        event_max = df["Events"].max()
        
        df_le = df[df['Error'] <= 0.05]
        if not df_le.empty:
            save_box(df_le, "0.05_le", 'Events', event_max)
            save_box(df_le, "0.05_le", 'Time', time_max)
            
        df_gt = df[df['Error'] > 0.05]
        if not df_gt.empty:
            save_box(df_gt, "0.05_gt", 'Events', event_max)
            save_box(df_gt, "0.05_gt", 'Time', time_max)

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
    def plot_recovery_short(self, data_in, side_by_side: bool = True):
        plt.rcParams.update({"font.size": 24})
        images_dir = os.path.join(self.base, "compressed_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cm.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        
        variant_map = {p.get("id"): (p.get("label", p.get("id")), self._protocol_color(p, scalarMap)) 
                       for p in self.protocols if p.get("id")}
        
        protocols_order = [p.get("id") for p in self.protocols if p.get("id") and self._protocol_enabled(p.get("id"))]

        rows = []
        for key, value in data_in.items():
            mean, std, events = float(value[0]), float(value[1]), float(value[2])
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k[:10]
            
            mbs = buf
            
            alg_lower = str(alg).strip().lower()
            if alg_lower == 'ps':
                variant_key = 'P.1.1'
            elif alg_lower == 'p':
                variant_key = 'P.1.1' if int(buf) == max(0, int(agents) - 2) else ('P.1.0' if int(msgs) > 0 else 'P.0')
            else:
                variant_key = f"{alg}.{int(broadcast)}.{int(hops)}"

            if not self._protocol_enabled(variant_key): continue
            
            rows.append({
                'Arena': arena, 'Agents': int(agents), 'Msgs_exp_time': int(msgs),
                'Error': abs(float(gt) - float(th)), 'Events': events / (100 * int(agents)),
                'Time': mean, 'VariantKey': variant_key, 'Label': variant_map[variant_key][0], 
                'Color': variant_map[variant_key][1], 'MBS': mbs
            })

        df = pd.DataFrame(rows)
        if df.empty: return
        
        df.loc[df['VariantKey'] == 'P.0', 'Msgs_exp_time'] = 60
        
        mbs_global_map = {}
        for ag in df['Agents'].unique():
            mbs_vals = df[(df['VariantKey'] == 'P.1.1') & (df['Agents'] == ag)]['MBS'].unique()
            mbs_global_map[ag] = sorted(list(mbs_vals), key=lambda x: float(x))

        real_tm_vals = sorted([m for m in df[df['VariantKey'] != 'P.0']['Msgs_exp_time'].unique() if m > 0])
        main_tm_list = self._plot_tm_values(real_tm_vals)
        insert_tm_list = self._get_valid_insert_tm()
        
        combined_tm = sorted(list(set(main_tm_list) | set(insert_tm_list)))
        active_labels = [variant_map[pid][0] for pid in protocols_order]
        densities = [("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)]

        def save_short(subset, suffix, side_by_side_mode: bool):
            if subset.empty: return
            fig, axes = plt.subplots(2, 3, figsize=(24, 14))
            event_max = subset["Events"].max()
            time_max = subset["Time"].max()

            for col_idx, (dens_label, arena, ag) in enumerate(densities):
                cell = subset[(subset['Arena'] == arena) & (subset['Agents'] == ag)]

                for row_idx, entry in enumerate(["Events", "Time"]):
                    ax = axes[row_idx, col_idx]
                    if row_idx == 0: ax.set_title(dens_label)

                    n_tm_total = len(combined_tm)
                    width_tm = 0.6
                    
                    def draw_pass(target_ax, target_type):
                        for k, pid in enumerate(protocols_order):
                            is_p0 = (pid == 'P.0')
                            
                            if is_p0:
                                tms = [main_tm_list[0]] if target_type == "main" and main_tm_list else []
                                if target_type == "inset" and insert_tm_list: tms = [insert_tm_list[0]]
                            else:
                                tms = main_tm_list if target_type == "main" else insert_tm_list

                            for tm_val in tms:
                                if is_p0:
                                    p_data = cell[cell['VariantKey'] == pid]
                                    tm_off = 0
                                else:
                                    p_data = cell[(cell['VariantKey'] == pid) & (cell['Msgs_exp_time'] == tm_val)]
                                    t_idx = main_tm_list.index(tm_val) if target_type == "main" else insert_tm_list.index(tm_val)
                                    tm_off = (t_idx - (n_tm_total - 1) / 2.0) * width_tm
                                
                                if p_data.empty: continue
                                final_base_pos = (k + 1) + tm_off

                                if pid == "P.1.1":
                                    mbs_list = mbs_global_map.get(ag, [])
                                    n_mbs_total = len(mbs_list)
                                    if n_mbs_total > 0:
                                        sub_w_mbs = width_tm
                                        for m_idx, val_mbs in enumerate(mbs_list):
                                            d_mbs_row = p_data[p_data['MBS'] == val_mbs]
                                            ratio = (m_idx + 1) / n_mbs_total
                                            h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(variant_map[pid][1]))
                                            c_val = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0-ratio)*0.4))), s*(1.0-((1.0-ratio)*0.3)))
                                            m_off = (m_idx - (n_mbs_total - 1) / 2.0) * sub_w_mbs *.8
                                            if not d_mbs_row.empty:
                                                self._draw_boxes_internal(target_ax, d_mbs_row, entry, final_base_pos + m_off, sub_w_mbs, c_val, side_by_side_mode)
                                    else:
                                        self._draw_boxes_internal(target_ax, p_data, entry, final_base_pos, width_tm, variant_map[pid][1], side_by_side_mode)
                                else:
                                    self._draw_boxes_internal(target_ax, p_data, entry, final_base_pos, width_tm, variant_map[pid][1], side_by_side_mode)

                    draw_pass(ax, "main")

                    ax.set_xticks(range(1, len(active_labels) + 1))
                    if row_idx == 1: ax.set_xticklabels(active_labels, rotation=45)
                    else: ax.set_xticklabels([])
                    
                    if row_idx == 0: ax.set_ylim(self.event_axis_limits(event_max)[:2])
                    else: ax.set_yscale('log'); ax.set_ylim(self.time_axis_limits(time_max)[:2])
                    
                    if col_idx == 0: ax.set_ylabel(r"$E_{r}$" if row_idx == 0 else r"$T_{r}$", fontsize=28)
                    if col_idx > 0: ax.set_yticklabels([])
                    ax.set_axisbelow(True)
                    ax.grid(True, ls=':', zorder=0)

                    if insert_tm_list:
                        best_box = self.find_emptiest_inset_position(ax)
                        ins = ax.inset_axes(best_box)
                        
                        draw_pass(ins, "inset")
                        
                        ins.set_xscale(ax.get_xscale())
                        ins.set_xlim(ax.get_xlim())
                        ins.set_xticks(ax.get_xticks())
                        ins.set_xticklabels([])
                        
                        ins.set_yticks(ax.get_yticks())
                        if row_idx == 1: ins.set_yscale(ax.get_yscale())
                        ins.set_ylim(ax.get_ylim())
                        ins.set_yticklabels([])
                        
                        # ins.set_axisbelow(True)
                        ins.grid(True, ls=':', color='silver', zorder=0)

            legend_elements = []
            
            # if side_by_side_mode:
            #     legend_elements.append(Patch(facecolor='white', edgecolor='black', label=r'$|G-\tau| \leq 0.05$'))
            #     legend_elements.append(Patch(facecolor='white', edgecolor='black', hatch='///', label=r'$|G-\tau| > 0.05$'))
            # legend_elements.append(Rectangle((0,0),1,1, label="k-sampling"))
                
            # for pid in protocols_order:
            #     legend_elements.append(Line2D([0], [0], color=variant_map[pid][1], marker='s', linestyle='None', markersize=14, label=variant_map[pid][0]))
            
            # fig.legend(handles=legend_elements, loc='lower center', ncol=6, 
            #            bbox_to_anchor=(0.66, -0.04), handler_map=None) #{Rectangle: GradientHandler(plt.get_cmap("Greys_r"))})
            
            fig.tight_layout()
            fig.savefig(os.path.join(images_dir, f"box_short_{suffix}.pdf"), bbox_inches='tight')
            plt.close(fig)

        if side_by_side: save_short(df, "sidebyside", True)
        else:
            save_short(df[df['Error'] <= 0.05], "le05", False)
            save_short(df[df['Error'] > 0.05], "gt05", False)


###################################################
    def plot_recovery_pareto(self, data_in, side_by_side_mode: bool=True):
        plt.rcParams.update({"font.size": 24})
        images_dir = os.path.join(self.base, "compressed_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cm.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        
        variant_map = {p.get("id"): (p.get("label", p.get("id")), self._protocol_color(p, scalarMap)) 
                       for p in self.protocols if p.get("id")}
        
        protocols_order = [p.get("id") for p in self.protocols if p.get("id") and self._protocol_enabled(p.get("id"))]

        rows = []
        for key, value in data_in.items():
            mean, std, events = float(value[0]), float(value[1]), float(value[2])
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k[:10]
            
            mbs = buf
            
            alg_lower = str(alg).strip().lower()
            if alg_lower == 'ps':
                variant_key = 'P.1.1'
            elif alg_lower == 'p':
                variant_key = 'P.1.1' if int(buf) == max(0, int(agents) - 2) else ('P.1.0' if int(msgs) > 0 else 'P.0')
            else:
                variant_key = f"{alg}.{int(broadcast)}.{int(hops)}"

            if not self._protocol_enabled(variant_key): continue
            
            rows.append({
                'Arena': arena, 'Agents': int(agents), 'Msgs_exp_time': int(msgs),
                'Error': abs(float(gt) - float(th)), 'Events': events / (100 * int(agents)),
                'Time': mean, 'VariantKey': variant_key, 'Label': variant_map[variant_key][0], 
                'Color': variant_map[variant_key][1], 'MBS': mbs
            })

        df = pd.DataFrame(rows)
        if df.empty: return
        
        df.loc[df['VariantKey'] == 'P.0', 'Msgs_exp_time'] = 60
        
        mbs_global_map = {}
        for ag in df['Agents'].unique():
            mbs_vals = df[(df['VariantKey'] == 'P.1.1') & (df['Agents'] == ag)]['MBS'].unique()
            mbs_global_map[ag] = sorted(list(mbs_vals), key=lambda x: float(x))

        real_tm_vals = sorted([m for m in df[df['VariantKey'] != 'P.0']['Msgs_exp_time'].unique() if m > 0])
        main_tm_list = self._plot_tm_values(real_tm_vals)
        insert_tm_list = self._get_valid_insert_tm()
        
        combined_tm = sorted(list(set(main_tm_list) | set(insert_tm_list)))
        active_labels = [variant_map[pid][0] for pid in protocols_order]
        densities = [("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)]

        def save_short(subset, suffix, side_by_side_mode: bool):
            if subset.empty: return
            fig, axes = plt.subplots(1, 3, figsize=(24, 14))
            event_max = subset["Events"].max()
            time_max = subset["Time"].max()

            for col_idx, (dens_label, arena, ag) in enumerate(densities):
                cell = subset[(subset['Arena'] == arena) & (subset['Agents'] == ag)]

                ax = axes[col_idx]
                ax.set_title(dens_label)

                n_tm_total = len(combined_tm)
                width_tm = 0.6
                
                def draw_pass(target_ax, target_type):
                    for k, pid in enumerate(protocols_order):
                        is_p0 = (pid == 'P.0')
                        
                        if is_p0:
                            tms = [main_tm_list[0]] if target_type == "main" and main_tm_list else []
                            if target_type == "inset" and insert_tm_list: tms = [insert_tm_list[0]]
                        else:
                            tms = main_tm_list if target_type == "main" else insert_tm_list

                        for tm_val in tms:
                            if is_p0:
                                p_data = cell[cell['VariantKey'] == pid]
                                tm_off = 0
                            else:
                                p_data = cell[(cell['VariantKey'] == pid) & (cell['Msgs_exp_time'] == tm_val)]
                                t_idx = main_tm_list.index(tm_val) if target_type == "main" else insert_tm_list.index(tm_val)
                                tm_off = (t_idx - (n_tm_total - 1) / 2.0) * width_tm
                            
                            if p_data.empty: continue
                            final_base_pos = (k + 1) + tm_off

                            if pid == "P.1.1":
                                mbs_list = mbs_global_map.get(ag, [])
                                n_mbs_total = len(mbs_list)
                                if n_mbs_total > 0:
                                    sub_w_mbs = width_tm
                                    for m_idx, val_mbs in enumerate(mbs_list):
                                        d_mbs_row = p_data[p_data['MBS'] == val_mbs]
                                        ratio = (m_idx + 1) / n_mbs_total
                                        h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(variant_map[pid][1]))
                                        c_val = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0-ratio)*0.4))), s*(1.0-((1.0-ratio)*0.3)))
                                        m_off = (m_idx - (n_mbs_total - 1) / 2.0) * sub_w_mbs *.8
                                        if not d_mbs_row.empty:
                                            self._draw_scatter_internal(target_ax, d_mbs_row, c_val,target_type)
                                else:
                                    self._draw_scatter_internal(target_ax, p_data, variant_map[pid][1],target_type)
                            else:
                                self._draw_scatter_internal(target_ax, p_data, variant_map[pid][1],target_type)

                ax.set_ylim(1,500)
                ax.set_yscale('log')
                draw_pass(ax, "main")

                
                
                if col_idx == 0: ax.set_ylabel(r"$T_{r}$" if col_idx == 0 else '', fontsize=28)
                ax.set_xlabel(r"$E_{r}$",fontsize=28)
                
                ax.set_axisbelow(True)
                ax.grid(True, ls=':', zorder=0)

                if insert_tm_list:
                    best_box = self.find_emptiest_inset_position(ax)
                    ins = ax.inset_axes(best_box)
                    
                    draw_pass(ins, "inset")
                    
                    ins.set_xscale(ax.get_xscale())
                    ins.set_xticks(ax.get_xticks())
                    ins.set_xticklabels([])
                    # ins.set_xlim(ax.get_xlim())
                    
                    ins.set_yscale(ax.get_yscale())
                    ins.set_yticks(ax.get_yticks())
                    ins.set_yticklabels([])
                    ins.set_ylim(1,1000)
                    
                    ins.set_axisbelow(True)
                    ins.grid(True, ls=':', color='silver', zorder=0)

            legend_elements = []
            # if main_tm_list: 
            #     legend_elements.append(Line2D([], [], color='none',marker='none', label=rf'Main $T_m={main_tm_list[0]}$'))
            # if insert_tm_list: 
            #     legend_elements.append(Line2D([], [], color='none',marker='none', label=rf'Inset $T_m={insert_tm_list[0]}$'))
            
            # if side_by_side_mode:
            #     legend_elements.append(Patch(facecolor='white', edgecolor='black', label=r'$|G-\tau| \leq 0.05$'))
            #     legend_elements.append(Patch(facecolor='white', edgecolor='black', hatch='///', label=r'$|G-\tau| > 0.05$'))
            # legend_elements.append(Rectangle((0,0),1,1, label="k-sampling"))
                
            for pid in protocols_order:
                legend_elements.append(Line2D([0], [0], color=variant_map[pid][1], marker='s', linestyle='None', markersize=14, label=variant_map[pid][0]))
            
            fig.legend(handles=legend_elements, loc='lower center', ncol=6, 
                       bbox_to_anchor=(0.76, -0.04), handler_map={Rectangle: GradientHandler(plt.get_cmap("Greys_r"))})
            
            fig.tight_layout()
            fig.savefig(os.path.join(images_dir, f"pareto_{suffix}.pdf"), bbox_inches='tight')
            plt.close(fig)

        save_short(df, "sidebyside", True)

###################################################
    def _draw_boxes_internal(self, ax, data, entry, pos, width, color, side_by_side):
        if side_by_side:
            d_le = data[data['Error'] <= 0.05][entry].values
            d_gt = data[data['Error'] > 0.05][entry].values
            bw = width * 0.4
            if len(d_le) > 0:
                ax.boxplot(d_le, positions=[pos - bw/2], widths=bw*0.8, patch_artist=True, 
                           boxprops=dict(facecolor=color), medianprops=dict(color='gray'), notch=False)
            if len(d_gt) > 0:
                ax.boxplot(d_gt, positions=[pos + bw/2], widths=bw*0.8, patch_artist=True, 
                           boxprops=dict(facecolor=color, hatch='///'), medianprops=dict(color='gray'), notch=False)
        else:
            d = data[entry].values
            if len(d) > 0:
                ax.boxplot(d, positions=[pos], widths=width*0.8, patch_artist=True, 
                           boxprops=dict(facecolor=color), medianprops=dict(color='gray'), notch=False)
                
###################################################
    def _draw_scatter_internal(self, ax, data, color,target_type):
        sc_size = 400 if target_type == 'main' else 100
        d_le = data[data['Error'] <= 0.05]['Events'].values
        # d_gt = data[data['Error'] > 0.05]['Events'].values
        t_le = data[data['Error'] <= 0.05]['Time'].values
        # t_gt = data[data['Error'] > 0.05]['Time'].values
        if len(d_le) > 0:
            ax.scatter(d_le,t_le,marker='o',s=sc_size,alpha=0.2,c=color)
        # if len(d_gt) > 0:
        #     ax.scatter(d_gt,t_gt,marker='s',c=color)
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
        ground_T, threshlds , msg_time, msg_hop, max_buff = [],[],[],[],[]
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
                if len(k0)>11 and k0[11]not in max_buff: max_buff.append(k0[11])
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
                                                for m_b_s in max_buff:
                                                    vals            = []
                                                    times_median    = []
                                                    for gt in ground_T:
                                                        tmp         = []
                                                        tmp_tmed    = []
                                                        for thr in threshlds:
                                                            s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h,m_b_s))
                                                            t_data = times[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h,m_b_s))
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
                                                            dict_park_t1_avg.update({(a_s,n_a,m_t,m_b_s):vals})
                                                            dict_park_t1_tmed.update({(a_s,n_a,m_t,m_b_s):times_median})
                                                    elif a.strip().lower() == 'p' and int(c)==0 and m_t in o_k and int(m_t) > 0:
                                                        if len(vals[0])>0:
                                                            dict_park_avg.update({(a_s,n_a,m_t,m_b_s):vals})
                                                            dict_park_tmed.update({(a_s,n_a,m_t,m_b_s):times_median})
                                                    if a=='P' and int(c)==0 and m_t in o_k and int(m_t) == 0:
                                                        if len(vals[0])>0:
                                                            dict_park_avg_real_fifo.update({(a_s,n_a,"60",m_b_s):vals})
                                                            dict_park_tmed_real_fifo.update({(a_s,n_a,"60",m_b_s):times_median})
                                                    if a=='O' and m_t in o_k:
                                                        if len(vals[0])>0:
                                                            if int(c)==0:
                                                                dict_adms_avg.update({(a_s,n_a,m_t,m_b_s):vals})
                                                                dict_adms_tmed.update({(a_s,n_a,m_t,m_b_s):times_median})
                                                            elif int(c)==2:
                                                                dict_fifo_avg.update({(a_s,n_a,m_t,m_b_s):vals})
                                                                dict_fifo_tmed.update({(a_s,n_a,m_t,m_b_s):times_median})
                                                            else:
                                                                if int(m_h)==1:
                                                                    dict_rnd_avg.update({(a_s,n_a,m_t,m_b_s):vals})
                                                                    dict_rnd_tmed.update({(a_s,n_a,m_t,m_b_s):times_median})
                                                                else:
                                                                    dict_rnd_inf_avg.update({(a_s,n_a,m_t,m_b_s):vals})
                                                                    dict_rnd_inf_tmed.update({(a_s,n_a,m_t,m_b_s):times_median})
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
        states_dict.update({"O.1.1":dict_rnd_avg})
        times_dict.update({"O.1.1":dict_rnd_tmed})
        states_dict.update({"O.1.0":dict_rnd_inf_avg})
        times_dict.update({"O.1.0":dict_rnd_inf_tmed})
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
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=4, label=r'$min|\mathcal{B}|$')
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_l = []
        handles_r = []
        l_list = []
        r_list = []
        
        all_cols = set()
        p11_present = False
        all_agents = set()
        mbs_per_agent = {}
        
        for dk in data_in.keys():
            if dk == "P.1.1" or dk.startswith("P.1.1"): p11_present = True
            dicts = data_in.get(dk)
            for k in dicts.keys():
                try:
                    all_cols.add(int(k[2]))
                    ag_val = int(k[1])
                    all_agents.add(ag_val)
                    if dk == "P.1.1" or dk.startswith("P.1.1"):
                        if len(k) > 3 and k[3] != "":
                            if ag_val not in mbs_per_agent: mbs_per_agent[ag_val] = set()
                            mbs_per_agent[ag_val].add(float(k[3]))
                except Exception:
                    continue
                    
        mbs_sorted = {ag: sorted(list(mbs_per_agent[ag])) for ag in mbs_per_agent}
                    
        for pid in protocols_order:
            if not self._protocol_enabled( pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=protocol_colors.get(pid, "black"),
                    marker='s',
                    linestyle='None',
                    markeredgewidth=0,
                    markersize=16,
                )
            )
            r_list.append(protocol.get("label", pid) if protocol else pid)
                
        handles_l.append(min_dim)
        l_list.append(r'$min|\mathcal{B}|$')
        
        rows = [60, 120, 180, 300, 600]
        rows = self._plot_tm_values( rows)
        if not rows:
            return
        col_index = {str(c): i for i, c in enumerate(rows)}
        nrows = len(rows)
        
        fig, ax = plt.subplots(nrows=nrows, ncols=3,figsize=(24,nrows*7),sharex=True,sharey=True, squeeze=False)
        
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
            for z in range(nrows):
                den = 100 if k==2 else 25
                val_min_buf = 5 / den
                ax[z][k].plot([val_min_buf for _ in range(901)],color="black",ls='--',lw=3)
                
        for dk in data_in.keys():
            dict_dk = data_in.get(dk)
            for k in dict_dk.keys():
                if not self._protocol_enabled( dk):
                    continue
                
                if dk != 'P.0' and k[2] not in col_index:
                    continue
                    
                col = 0
                if k[0]=='big' and k[1]=='25':
                    col = 0
                elif k[0]=='big' and k[1]=='100':
                    col = 2
                elif k[0]=='small':
                    col = 1
                    
                c_val = protocol_colors.get(dk,"gray")
                is_p11 = (dk == "P.1.1" or dk.startswith("P.1.1"))
                if is_p11 and len(k) > 3:
                    try:
                        m_b_s = k[3]
                        ag_val = int(k[1])
                        if m_b_s != "" and ag_val in mbs_sorted and len(mbs_sorted[ag_val]) > 0:
                            val = float(m_b_s)
                            N_vals = len(mbs_sorted[ag_val])
                            idx = mbs_sorted[ag_val].index(val)
                            ratio = (idx + 1) / N_vals
                        else:
                            ratio = 1.0
                            
                        ratio = max(0.0, min(1.0, ratio))
                        
                        rgb_base = colors.to_rgb(c_val)
                        h_c, l_c, s_c = colorsys.rgb_to_hls(*rgb_base)
                        diff = 1.0 - ratio
                        new_l = max(l_c, min(0.85, l_c + (diff * 0.4)))
                        new_s = s_c * (1.0 - (diff * 0.3))
                        raw_rgb = colorsys.hls_to_rgb(h_c, new_l, new_s)
                        c_val = tuple(np.clip(raw_rgb, 0, 1))
                    except Exception:
                        pass
                
                if dk == 'P.0':
                    for r_idx in range(nrows):
                        ax[r_idx][col].plot(dict_dk.get(k),color=c_val,lw=6)
                else:
                    row = col_index.get(k[2])
                    if row is not None:
                        ax[row][col].plot(dict_dk.get(k),color=c_val,lw=6)
                
        for x in range(nrows):
            for y in range(2):
                ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                
        for y in range(3):
            ax[4][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
            ax[4][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
            
        for idx, col_val in enumerate(["LD25","HD25","HD100"]):
            axt=ax[0][idx].twiny()
            axt.tick_params(labeltop=False, labelbottom=False)
            axt.set_xlabel(f"{col_val}")
            
        last_col = 2
        ayt0=ax[0][last_col].twinx()
        ayt1=ax[1][last_col].twinx()
        ayt2=ax[2][last_col].twinx()
        ayt3=ax[3][last_col].twinx()
        ayt4=ax[4][last_col].twinx()
        
        ayt0.tick_params(labelright=False)
        ayt1.tick_params(labelright=False)
        ayt2.tick_params(labelright=False)
        ayt3.tick_params(labelright=False)
        ayt4.tick_params(labelright=False)
        ays=[ayt0,ayt1,ayt2,ayt3,ayt4]
        for idx, row_val in enumerate(rows):
            ays[idx].set_ylabel(rf"$T_m = {row_val}\, s$",rotation=270,labelpad=30)

        ax[0][0].set_ylabel(r"$M$")
        ax[1][0].set_ylabel(r"$M$")
        ax[2][0].set_ylabel(r"$M$")
        ax[3][0].set_ylabel(r"$M$")
        ax[4][0].set_ylabel(r"$M$")
        for y in range(3):
            ax[4][y].set_xlabel(r"$T$")
        for x in range(nrows):
            for y in range(3):
                ax[x][y].grid(True,ls=':')
                ax[x][y].set_xlim(0,900)
                ax[x][y].set_ylim(-0.03,1.03)

        fig.tight_layout()
                
        # if p11_present:
        #     cmap_grey = colors.LinearSegmentedColormap.from_list('custom_grey', ['#2D2D2D','#E0E0E0'])
        #     grad_rect = Rectangle((0, 0), 1, 1)
        #     handles_l.append(grad_rect)
        #     l_list.append("k-sampling")
        #     handler_map = {Rectangle: GradientHandler(cmap_grey)}
        # else:
        handler_map = None

        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        if handles_r:
            fig.legend(handles_l+handles_r, l_list+r_list, bbox_to_anchor=(0.96, 0.01), ncols=7, loc='upper right',framealpha=0.7,borderaxespad=0, handler_map=handler_map)
            
        fig_path = self.base+"/msgs_data/images/messages.pdf"
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
###################################################
    def print_decisions(self,data_in):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=6, label=r'$min|\mathcal{B}|$')
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r = []
        l_list = []
        
        all_cols = set()
        p11_present = False
        all_agents = set()
        mbs_per_agent = {}
        
        for dk in data_in.keys():
            if dk == "P.1.1" or dk.startswith("P.1.1"): p11_present = True
            dct = data_in.get(dk)
            for k in dct.keys():
                try:
                    all_cols.add(int(k[2]))
                    ag_val = int(k[1])
                    all_agents.add(ag_val)
                    if dk == "P.1.1" or dk.startswith("P.1.1"):
                        if len(k) > 3 and k[3] != "":
                            if ag_val not in mbs_per_agent: mbs_per_agent[ag_val] = set()
                            mbs_per_agent[ag_val].add(float(k[3]))
                except Exception:
                    continue
                    
        mbs_sorted = {ag: sorted(list(mbs_per_agent[ag])) for ag in mbs_per_agent}
                    
        for pid in protocols_order:
            if not self._protocol_enabled( pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(
                mlines.Line2D(
                    [], [],
                    color=protocol_colors.get(pid, "black"),
                    marker='s',
                    linestyle='None',
                    markeredgewidth=0,
                    markersize=16,
                )
            )
            l_list.append(protocol.get("label", pid) if protocol else pid)
                
        handles_r.append(min_dim)
        l_list.append(r'$min|\mathcal{B}|$')
        
        columns = [60, 120, 180, 300, 600]
        columns = self._plot_tm_values( columns)
        if not columns:
            return
        col_index = {str(c): i for i, c in enumerate(columns)}
        ncols = len(columns)
        
        fig, ax     = plt.subplots(nrows=3, ncols=ncols,figsize=(5.2*ncols + ncols*1.5,5.2*ncols), squeeze=False)
        
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
                
                if dk != 'P.0' and k[2] not in col_index:
                    continue
                    
                row = 0
                if k[0]=='big' and k[1]=='25':
                    row = 0
                elif k[0]=='big' and k[1]=='100':
                    row = 2
                elif k[0]=='small':
                    row = 1
                    
                c_val = protocol_colors.get(dk,"gray")
                is_p11 = (dk == "P.1.1" or dk.startswith("P.1.1"))
                if is_p11 and len(k) > 3:
                    try:
                        m_b_s = k[3]
                        ag_val = int(k[1])
                        if m_b_s != "" and ag_val in mbs_sorted and len(mbs_sorted[ag_val]) > 0:
                            val = float(m_b_s)
                            N_vals = len(mbs_sorted[ag_val])
                            idx = mbs_sorted[ag_val].index(val)
                            ratio = (idx + 1) / N_vals
                        else:
                            ratio = 1.0
                            
                        ratio = max(0.0, min(1.0, ratio))
                        
                        rgb_base = colors.to_rgb(c_val)
                        h_c, l_c, s_c = colorsys.rgb_to_hls(*rgb_base)
                        diff = 1.0 - ratio
                        new_l = max(l_c, min(0.85, l_c + (diff * 0.4)))
                        new_s = s_c * (1.0 - (diff * 0.3))
                        raw_rgb = colorsys.hls_to_rgb(h_c, new_l, new_s)
                        c_val = tuple(np.clip(raw_rgb, 0, 1))
                    except Exception:
                        pass
                
                if dk == 'P.0':
                    for c_idx in range(ncols):
                        ax[row][c_idx].plot(dct.get(k),color=c_val,lw=6)
                else:
                    col = col_index.get(k[2])
                    if col is not None:
                        ax[row][col].plot(dct.get(k),color=c_val,lw=6)
                
        for x in range(2):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                
        for x in range(3):
            for y in range(1,ncols):
                ax[x][y].tick_params(labelleft=False)
                
        for y in range(ncols):
            ax[2][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
            
        for idx, col_val in enumerate(columns):
            axt=ax[0][idx].twiny()
            axt.tick_params(labeltop=False, labelbottom=False)
            axt.set_xlabel(rf"$T_m = {int(col_val)}\, s$")
            
        last_col = ncols - 1
        ayt0=ax[0][last_col].twinx()
        ayt1=ax[1][last_col].twinx()
        ayt2=ax[2][last_col].twinx()
        
        ayt0.tick_params(labelright=False)
        ayt1.tick_params(labelright=False)
        ayt2.tick_params(labelright=False)
        
        ayt0.set_ylabel("LD25")
        ayt1.set_ylabel("HD25")
        ayt2.set_ylabel("HD100")
        ax[0][0].set_ylabel(r"$D$")
        ax[1][0].set_ylabel(r"$D$")
        ax[2][0].set_ylabel(r"$D$")
        for y in range(ncols):
            ax[2][y].set_xlabel(r"$T$")
        for x in range(3):
            for y in range(ncols):
                ax[x][y].grid(True,ls=':')
                ax[x][y].set_xlim(0,900)
                if x==0 or x==1:
                    ax[x][y].set_ylim(-0.03,1.03)
                else:
                    ax[x][y].set_ylim(-0.03,1.03)

        fig.tight_layout()
                    
        if p11_present:
            cmap_grey = colors.LinearSegmentedColormap.from_list('custom_grey', ['#2D2D2D','#E0E0E0'])
            grad_rect = Rectangle((0, 0), 1, 1)
            handles_r.append(grad_rect)
            l_list.append("k-sampling")
            handler_map = {Rectangle: GradientHandler(cmap_grey)}
        else:
            handler_map = None
            
        if not os.path.exists(self.base+"/dec_data/images/"):
            os.mkdir(self.base+"/dec_data/images/")
        fig_path = self.base+"/dec_data/images/decisions.pdf"
        if handles_r:
            fig.legend(handles_r, l_list, bbox_to_anchor=(1, 0), ncols=len(handles_r), loc='upper right',framealpha=0.7,borderaxespad=0, handler_map=handler_map)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

###################################################
    def print_borders(self,path,_type,t_type,ground_T,threshlds,data_in,times_in,keys,more_k):
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        po_k = keys
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = sorted(set(o_k))
        o_k = self._plot_tm_values( o_k)
        if not o_k:
            return
        nrows = len(o_k)
        arena = more_k[0]
        
        low_bound           = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label=r"$\hat{Q} = 0.2$")
        high_bound          = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label=r"$\hat{Q} = 0.8$")
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        handles_c   = [high_bound,low_bound]
        handles_r = []
        l_list_r = []
        handles_l = []
        l_list_l = []
        
        p11_present = False
        for dk in data_in.keys():
            if dk == "P.1.1" or dk.startswith("P.1.1"): p11_present = True
                
        for pid in protocols_order:
            if not self._protocol_enabled( pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='s', linestyle='None', markeredgewidth=0, markersize=16))
            l_list_r.append(protocol.get("label", pid) if protocol else pid)
                
        border_font = plt.rcParams.get("font.size", 20) + 4
        
        fig, ax     = plt.subplots(nrows=nrows, ncols=3,figsize=(26,8*nrows), sharex=False, squeeze=False)
        tfig, tax   = plt.subplots(nrows=nrows, ncols=3,figsize=(24,7*nrows), sharex=False, squeeze=False)
        
        attributes_row_col = np.zeros((nrows,3))

        for a in arena:
            agents_list = ["25"] if a=="smallA" else more_k[1]
            for ag in agents_list:
                col = 1 if a=="smallA" else (2 if int(ag)==100 else 0)
                
                raw_mbs = set()
                for dk in data_in.keys():
                    for k_key in data_in.get(dk).keys():
                        if k_key[0] == a and str(k_key[1]) == str(ag):
                            if len(k_key) > 3: raw_mbs.add(k_key[3])
                if not raw_mbs: raw_mbs.add("")
                sorted_valid_mbs = sorted([float(x) for x in raw_mbs if x != ""])
                N_mbs = len(sorted_valid_mbs)
                    
                for m_b_s in raw_mbs:
                    for k in range(len(o_k)):
                        for dk in data_in.keys():
                            vals_v2, vals_v8, gts_v2, gts_v8 = [], [], [], []
                            times_v = []
                            
                            x_plot = np.array(threshlds)
                            if np.max(x_plot) > 1.0: x_plot = x_plot / np.max(x_plot)
                            
                            search_tm = "60" if dk == 'P.0' else str(o_k[k])

                            for th in range(len(threshlds)):
                                vals2, vals8, gt2, gt8 = [np.nan]*2, [np.nan]*2, [np.nan]*2, [np.nan]*2
                                valst, lim_valst = np.nan, np.nan
                                
                                d_series = data_in.get(dk).get((a,ag,search_tm, m_b_s))
                                t_series = times_in.get(dk).get((a,ag,search_tm, m_b_s))
                                
                                if d_series is not None:
                                    for pt in range(len(ground_T)):
                                        val = d_series[pt][th]
                                        tval = t_series[pt][th]
                                        if val is not None:
                                            if val>=0.8:
                                                if ground_T[pt]-threshlds[th] >= 0.09 and (valst is np.nan or ground_T[pt]-threshlds[th]<lim_valst):
                                                    valst, lim_valst = tval, ground_T[pt]-threshlds[th]
                                                if ground_T[pt]-threshlds[th] >= 0 and (vals8[1] is np.nan or val<vals8[1]):
                                                    vals8[1], gt8[1] = val, ground_T[pt]
                                            elif val<=0.2:
                                                if ground_T[pt]-threshlds[th] <= 0 and (vals2[0] is np.nan or val>=vals2[0]):
                                                    vals2[0], gt2[0] = val, ground_T[pt]
                                            else:
                                                if vals8[0] is np.nan or val>vals8[0]: vals8[0], gt8[0] = val, ground_T[pt]
                                                if vals2[1] is np.nan or val<vals2[1]: vals2[1], gt2[1] = val, ground_T[pt]
                                                
                                if vals8[0] is np.nan: vals8[0], gt8[0] = vals8[1], gt8[1]
                                elif vals8[1] is np.nan: vals8[1], gt8[1] = vals8[0], gt8[0]
                                if vals2[0] is np.nan: vals2[0], gt2[0] = vals2[1], gt2[1]
                                elif vals2[1] is np.nan: vals2[1], gt2[1] = vals2[0], gt2[0]
                                
                                vals_v2.append(np.around(np.interp([0.2], vals2, gt2, left=np.nan), 3))
                                vals_v8.append(np.around(np.interp([0.8], vals8, gt8, right=np.nan), 3))
                                times_v.append(valst)

                            if m_b_s == list(raw_mbs)[0]:
                                ax[k][col].plot(np.arange(0.5, 1.01, 0.01), np.arange(0.5, 1.01, 0.01), color='black', lw=2, ls=':')
                                
                            if self._protocol_enabled(dk):
                                c_val = protocol_colors.get(dk, "gray")
                                if (dk == "P.1.1" or dk.startswith("P.1.1")) and m_b_s != "" and N_mbs > 0:
                                    idx_mbs = sorted_valid_mbs.index(float(m_b_s))
                                    ratio = max(0.0, min(1.0, (idx_mbs + 1) / N_mbs))
                                    h_c, l_c, s_c = colorsys.rgb_to_hls(*colors.to_rgb(c_val))
                                    c_val = colorsys.hls_to_rgb(h_c, max(l_c, min(0.85, l_c + ((1.0-ratio) * 0.4))), s_c * (1.0 - ((1.0-ratio) * 0.3)))

                                ax[k][col].plot(x_plot, vals_v2, color=c_val, lw=6, ls='--')
                                ax[k][col].plot(x_plot, vals_v8, color=c_val, lw=6, ls='-')
                                tax[k][col].plot(x_plot, times_v, color=c_val, lw=6)

                            if attributes_row_col[k][col] == 0:
                                attributes_row_col[k][col] = 1
                                self._borders_attributes(ax, tax, col, k, o_k, border_font, nrows)

        fig.tight_layout()
        tfig.tight_layout()
                
        handler_map = None
        # if p11_present:
        #     cmap_grey = colors.LinearSegmentedColormap.from_list('custom_grey', ['#2D2D2D','#E0E0E0'])
        #     handles_l.append(Rectangle((0, 0), 1, 1))
        #     l_list_l.append("k-sampling")
        #     handler_map = {Rectangle: GradientHandler(cmap_grey)}

        fig.legend(handles_c+handles_r, [r"$\hat{Q} = 0.8$", r"$\hat{Q} = 0.2$"]+l_list_r, bbox_to_anchor=(0.96, 0), ncols=4, loc='upper right', framealpha=0.7, borderaxespad=0)
        tfig.legend(handles_l+handles_r, l_list_l+l_list_r, bbox_to_anchor=(0.96, 0), ncols=6, loc='upper right', framealpha=0.7, borderaxespad=0)
        
        fig.savefig(path+_type+"_activation.pdf", bbox_inches='tight')
        tfig.savefig(path+t_type+"_time.pdf", bbox_inches='tight')
        plt.close(fig); plt.close(tfig)
        # self.plot_protocol_tables(path, o_k, ground_T, threshlds, prot_tables_vals_dict)

###################################################
    def _borders_attributes(self, ax, tax, col, k, o_k, border_font, nrows):
        from matplotlib.ticker import FixedLocator

        for a_curr in [ax[k][col], tax[k][col]]:
            a_curr.set_xlim(0.5, 1.0)
            a_curr.tick_params(axis='both', which='major', labelsize=border_font)

        ax[k][col].set_ylim(0.5, 1.0)
        if col==0: tax[k][col].set_ylim(0, 201)
        elif col==1: tax[k][col].set_ylim(0, 51)
        elif col==2: tax[k][col].set_ylim(0, 101)

        if col == 0:
            ax[k][col].set_ylabel(r"$G$", fontsize=border_font)
            tax[k][col].set_ylabel(r"$T_c$", fontsize=border_font)
            ax[k][col].yaxis.set_tick_params(labelleft=True)
        else:
            # tax[k][col].yaxis.set_tick_params(labelleft=False)
            ax[k][col].yaxis.set_tick_params(labelleft=False)
        tax[k][col].yaxis.set_tick_params(labelleft=True)

        ticks_pos = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        
        if k == 4:
            for a_curr in [ax[k][col], tax[k][col]]:
                a_curr.xaxis.set_major_locator(FixedLocator(ticks_pos))
                a_curr.set_xticklabels([f"{x:.1f}" for x in ticks_pos], fontsize=border_font)
                a_curr.set_xlabel(r"$\tau$", fontsize=border_font)
        else:
            for a_curr in [ax[k][col], tax[k][col]]:
                a_curr.xaxis.set_major_locator(FixedLocator(ticks_pos))
                a_curr.set_xticklabels([]) 

        if k == 0:
            axt = ax[k][col].twiny()
            taxt = tax[k][col].twiny()
            axt.set_xlim(0.5, 1.0)
            taxt.set_xlim(0.5, 1.0)
            axt.set_xticks([])
            taxt.set_xticks([])
            label_top = "LD25" if col == 0 else ("HD25" if col == 1 else "HD100")
            axt.set_xlabel(label_top, fontsize=border_font, labelpad=15)
            taxt.set_xlabel(label_top, fontsize=border_font, labelpad=15)

        if col == 2:
            for a_curr in [ax[k][col], tax[k][col]]:
                a_right = a_curr.twinx()
                a_right.set_yticks([])
                a_right.set_ylabel(rf"$T_m = {int(o_k[k])}\, s$", fontsize=border_font, rotation=270, labelpad=35)

        ax[k][col].grid(True, which='major', ls=':', alpha=0.6)
        tax[k][col].grid(True, which='major', ls=':', alpha=0.6)

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
        
        ground_T, threshlds, dk_tot_states, dk_tot_times, o_k, [arena, agents], dk_tot_msgs, dk_stds_dict = self._group_tables(tot_states_in, tot_times_in, tot_msgs_in)
        
        typo = [0,1,2,3,4,5]
        cNorm = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        
        raw_all_tm = sorted([int(x) for x in o_k if x is not None and int(x) > 0])
        main_tm_list = self._plot_tm_values(raw_all_tm)
        insert_tm_list = self._get_valid_insert_tm()
        
        if not main_tm_list and not insert_tm_list:
            return

        if insert_tm_list:
            use_gradient = False
        else:
            use_gradient = len(main_tm_list) > 1
            
        tm_set = set(int(x) for x in main_tm_list)
        insert_tm_set = set(int(x) for x in insert_tm_list)
        combined_tm = sorted(list(tm_set | insert_tm_set))
        
        fig, ax = plt.subplots(3, 3, figsize=(28, 22), constrained_layout=True, squeeze=False, gridspec_kw={'height_ratios': [1, 1.4, 1]})
        
        min_buf_plotted = np.zeros(3)
        mid_act_plotted = np.zeros(3)
        max_time = 0
        ref_x = np.arange(0.5, 1.01, 0.01)
        
        inset_axes_dict = {}

        mbs_per_agent = {}
        for dk_key in dk_tot_msgs.keys():
            dicts = dk_tot_msgs.get(dk_key)
            for k in dicts.keys():
                ag_val = int(k[1])
                if ag_val not in mbs_per_agent: mbs_per_agent[ag_val] = set()
                if len(k) > 3 and k[3] != "": mbs_per_agent[ag_val].add(float(k[3]))
        mbs_sorted_map = {ag: sorted(list(mbs_per_agent[ag])) for ag in mbs_per_agent}

        for dk in dk_tot_msgs.keys():
            if not self._protocol_enabled(dk):
                continue
            
            tot_msgs = dk_tot_msgs.get(dk)
            tot_states = dk_tot_states.get(dk)
            tot_times = dk_tot_times.get(dk)
            base_color = protocol_colors.get(dk, 'gray')
            is_p0 = (dk == 'P.0')

            for key, msg_series in tot_msgs.items():
                current_tm = int(key[2])
                if not (current_tm in combined_tm or is_p0): continue
                
                num_agents = int(key[1])
                col_idx = 2 if num_agents == 100 else 1 if key[0] == "small" and num_agents == 25 else 0
                
                c_val = base_color
                if (dk == "P.1.1" or dk.startswith("P.1.1")) and len(key) > 3 and key[3] != "":
                    val_mbs = float(key[3])
                    mbs_list = mbs_sorted_map.get(num_agents, [])
                    if mbs_list:
                        ratio = (mbs_list.index(val_mbs) + 1) / len(mbs_list)
                        h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(base_color))
                        c_val = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0-ratio)*0.4))), s*(1.0-((1.0-ratio)*0.3)))

                destinations = []
                if is_p0:
                    destinations.extend(["main", "inset"])
                elif current_tm in tm_set: 
                    destinations.append("main")
                elif current_tm in insert_tm_set: 
                    destinations.append("inset")

                for dest_type in destinations:
                    if dest_type == "main":
                        target_ax = ax[0][col_idx]
                    else:
                        if (0, col_idx) not in inset_axes_dict:
                            ins = ax[0][col_idx].inset_axes([0.62, 0.03, 0.35, 0.35])
                            ins.set_xlim(0, 901); ins.set_ylim(-0.01, 1.01)
                            ins.tick_params(labelbottom=False, labelleft=False)
                            ins.grid(True, ls=':', color='silver')
                            
                            ins.plot([5 / (num_agents - 1) for _ in range(901)], color="black", ls='-.', lw=3)
                            
                            inset_axes_dict[(0, col_idx)] = ins
                        target_ax = inset_axes_dict[(0, col_idx)]

                    target_ax.plot(np.array(msg_series) / (num_agents - 1), color=c_val, lw=4, alpha=0.75)

                if min_buf_plotted[col_idx] == 0:
                    min_buf_plotted[col_idx] = 1
                    ax[0][col_idx].plot([5 / (num_agents - 1) for _ in range(901)], color="black", ls='-.', lw=3)

            for key, state_series in tot_states.items():
                current_tm = int(key[2])
                if not (current_tm in combined_tm or is_p0): continue
                
                num_agents = int(key[1])
                col_idx = 2 if num_agents == 100 else 1 if key[0] == "smallA" and num_agents == 25 else 0
                time_series = tot_times.get(key)
                
                v2, v8, vt = [], [], []
                for th in range(len(threshlds)):
                    vals2, vals8, gt2, gt8 = [np.nan]*2, [np.nan]*2, [np.nan]*2, [np.nan]*2
                    valst, lim_valst = np.nan, np.nan
                    for pt in range(len(ground_T)):
                        val, tval = state_series[pt][th], time_series[pt][th]
                        if val is not None:
                            if val >= 0.8:
                                if ground_T[pt]-threshlds[th] >= 0.09 and (valst is np.nan or ground_T[pt]-threshlds[th]<lim_valst):
                                    valst, lim_valst = tval, ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >= 0 and (vals8[1] is np.nan or val<vals8[1]):
                                    vals8[1], gt8[1] = val, ground_T[pt]
                            elif val <= 0.2:
                                if ground_T[pt]-threshlds[th] <= 0 and (vals2[0] is np.nan or val>=vals2[0]):
                                    vals2[0], gt2[0] = val, ground_T[pt]
                            else:
                                if vals8[0] is np.nan or val>vals8[0]: vals8[0], gt8[0] = val, ground_T[pt]
                                if vals2[1] is np.nan or val<vals2[1]: vals2[1], gt2[1] = val, ground_T[pt]
                    if vals8[0] is np.nan: vals8[0], gt8[0] = vals8[1], gt8[1]
                    elif vals8[1] is np.nan: vals8[1], gt8[1] = vals8[0], gt8[0]
                    if vals2[0] is np.nan: vals2[0], gt2[0] = vals2[1], gt2[1]
                    elif vals2[1] is np.nan: vals2[1], gt2[1] = vals2[0], gt2[0]
                    v2.append(np.interp([0.2], vals2, gt2, left=np.nan)[0])
                    v8.append(np.interp([0.8], vals8, gt8, right=np.nan)[0])
                    vt.append(valst)
                    if not np.isnan(valst) and valst > max_time: max_time = valst

                c_val = base_color
                if (dk == "P.1.1" or dk.startswith("P.1.1")) and len(key) > 3 and key[3] != "":
                    mbs_list = mbs_sorted_map.get(num_agents, [])
                    if mbs_list:
                        ratio = (mbs_list.index(float(key[3])) + 1) / len(mbs_list)
                        h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(base_color))
                        c_val = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0-ratio)*0.4))), s*(1.0-((1.0-ratio)*0.3)))

                destinations = []
                if is_p0: destinations.extend(["main", "inset"])
                elif current_tm in tm_set: destinations.append("main")
                elif current_tm in insert_tm_set: destinations.append("inset")

                for target_type in destinations:
                    for r_idx, data_to_plot in [(2, vt), (1, v2), (1, v8)]:
                        if target_type == "main":
                            curr_ax = ax[r_idx][col_idx]
                        else:
                            if (r_idx, col_idx) not in inset_axes_dict:
                                if r_idx == 2:
                                    y_pos = 0.62
                                    best_box = [0.62, y_pos, 0.35, 0.35]
                                else:
                                    best_box = self.find_emptiest_inset_position(ax[r_idx][col_idx])
                                
                                ins = ax[r_idx][col_idx].inset_axes(best_box)
                                ins.set_xlim(0.5, 1); ins.tick_params(labelbottom=False, labelleft=False)
                                ins.grid(True, ls=':', color='silver')
                                if r_idx == 1: 
                                    ins.set_ylim(0.5, 1); ins.plot(ref_x, ref_x, color='black', lw=2, ls=':')
                                inset_axes_dict[(r_idx, col_idx)] = ins
                            curr_ax = inset_axes_dict[(r_idx, col_idx)]
                        
                        ls = '--' if data_to_plot == v2 else '-'
                        curr_ax.plot(threshlds, data_to_plot, color=c_val, lw=4, ls=ls, alpha=0.75)
                
                if mid_act_plotted[col_idx] == 0:
                    mid_act_plotted[col_idx] = 1
                    ax[1][col_idx].plot(ref_x, ref_x, color='black', lw=3, ls=':')
        self._finalize_compressed_plot(fig, ax, path, protocol_colors, threshlds, max_time, use_gradient, main_tm_list, insert_tm_list, inset_axes_dict)
        
###################################################
    def _finalize_compressed_plot(self, fig, ax, path, protocol_colors, tau_ticks, max_time, use_gradient, main_tm_list, insert_tm_list, inset_axes_dict=None):
        import os
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MultipleLocator, FormatStrFormatter
        from matplotlib.lines import Line2D
        from matplotlib.patches import Rectangle
        from matplotlib.legend_handler import HandlerBase
        
        if inset_axes_dict is None:
            inset_axes_dict = {}
            
        column_titles = ["LD25","HD25","HD100"]
        
        for i in range(3):
            for j in range(3):
                curr = ax[i][j]
                if i == 0:
                    curr.set_title(column_titles[j], pad=20)
                    curr.set_xlim(0, 901); curr.set_xticks([0, 300, 600, 900])
                    curr.set_ylim(-0.01, 1.01); curr.set_xlabel(r"$T$")
                    if j == 0: ax[i][0].text(0.5, 0.25, r'$min|\mathcal{B}|$', transform=ax[i][0].transAxes, fontsize=plt.get("font.size"), ha='center', va='center', color='black')
                elif i == 1:
                    curr.set_xlim(0.5, 1); curr.set_ylim(0.5, 1)
                    curr.xaxis.set_major_locator(MultipleLocator(0.1))
                    curr.xaxis.set_major_formatter(FormatStrFormatter('%.1f'))
                    curr.set_xticklabels([])
                    if j == 0:
                        ax[i][0].text(0.6, 0.9, r'$\hat{Q}=0.8$', transform=ax[i][0].transAxes, fontsize=plt.get("font.size"), ha='center', va='center', color='black')
                        ax[i][0].text(0.9, 0.5, r'$\hat{Q}=0.2$', transform=ax[i][0].transAxes, fontsize=plt.get("font.size"), ha='center', va='center', color='black')
                elif i == 2:
                    curr.set_xlim(0.5, 1); curr.set_ylim(0, max_time + 10)
                    curr.xaxis.set_major_locator(MultipleLocator(0.1))
                    curr.set_xlabel(r"$\tau$")
                
                curr.grid(True, ls=':', which='major')
                if j > 0: curr.set_yticklabels([])
                if (i, j) in inset_axes_dict:
                    ins_ax = inset_axes_dict[(i, j)]
                    
                    
                    if i == 0:
                        ins_ax.set_xticks([0, 300, 600, 900])
                    else:
                        ins_ax.xaxis.set_major_locator(MultipleLocator(0.1))
                    
                    ins_ax.set_yticks(curr.get_yticks())
                    
                    ins_ax.tick_params(
                        labelbottom=False, labeltop=False, 
                        labelleft=False, labelright=False
                    )
                    ins_ax.set_xlim(curr.get_xlim())
                    ins_ax.set_ylim(curr.get_ylim())

        ax[0][0].set_ylabel(r"$M$"); ax[1][0].set_ylabel(r"$G$"); ax[2][0].set_ylabel(r"$T_c$")
        
        legend_elements = []
        # if main_tm_list: 
        #     legend_elements.append(Line2D([], [], color='none', marker='none', label=rf'Main $T_m={main_tm_list[0]}$'))
        # if insert_tm_list: 
        #     legend_elements.append(Line2D([], [], color='none', marker='none', label=rf'Inset $T_m={insert_tm_list[0]}$'))
        
        # legend_elements.append(Line2D([0], [0], color='black', lw=4, ls='--', label=r'$\hat{Q}=0.2$'))
        # legend_elements.append(Line2D([0], [0], color='black', lw=4, ls='-', label=r'$\hat{Q}=0.8$'))
        # legend_elements.append(Line2D([], [], color="black", lw=4, ls='-.', label=r'$min|\mathcal{B}|$'))
        handler_map = {}
        # grad_rect = Rectangle((0, 0), 1, 1, label="k-sampling")
        # legend_elements.append(grad_rect)
        # try:
        #     handler_map[Rectangle] = GradientHandler(plt.get_cmap("Greys_r"))
        # except NameError:
        #     pass
        
        for p in self.protocols:
            p_id = p.get("id")
            if self._protocol_enabled(p_id):
                legend_elements.append(Line2D([0], [0], color=protocol_colors[p_id], marker='s', linestyle='None', markersize=16, label=p.get("label", p_id)))
                    
        # if use_gradient:
        #     grad_rect = Rectangle((0, 0), 1, 1, label=r"$T_m$")
        #     legend_elements.append(grad_rect)
        #     try:
        #         handler_map[Rectangle] = GradientHandler(plt.get_cmap("Greys"))
        #     except NameError:
        #         pass 

        fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 0), ncol=7, frameon=True, edgecolor='0.8')
        fig.savefig(os.path.join(path, "compressed_summary.pdf"), bbox_inches='tight', dpi=300)
        plt.close(fig)

###################################################
    def find_emptiest_inset_position(self, ax, width=0.35, height=0.35, margin=0.03):
        """
        Calculates the emptiest quadrant in the given axis to place an inset.
        Evaluates the top-left, top-right, bottom-left, and bottom-right corners.
        Fully compatible with lines, boxplots (patches), and scatter points (collections),
        respecting both linear and logarithmic axis scales.
        """
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
                offsets = np.asarray(collection.get_offsets())
                if offsets.size > 0:
                    transform = collection.get_offset_transform() if hasattr(collection, "get_offset_transform") else collection.get_transform()
                    disp_offsets = transform.transform(offsets)
                    ax_offsets = ax.transAxes.inverted().transform(disp_offsets)
                    points_axes.append(ax_offsets)
            except Exception:
                pass

        if not points_axes:
            return candidates["top_right"]
            
        all_points_axes = np.vstack(points_axes)
        x_ax, y_ax = all_points_axes[:, 0], all_points_axes[:, 1]
        
        for key, box in candidates.items():
            x0, y0, w, h = box
            in_box = (x_ax >= x0) & (x_ax <= x0 + w) & (y_ax >= y0) & (y_ax <= y0 + h)
            counts[key] += np.sum(in_box)
            
        best_position_key = min(counts, key=counts.get)
        
        return candidates[best_position_key]