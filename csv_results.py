import sys, os, csv, logging, re, json, colorsys
import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.cm as cm
import matplotlib.lines as mlines
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.legend_handler import HandlerBase
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from lifelines import WeibullFitter,KaplanMeierFitter
from lifelines.utils import median_survival_times
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
            if elem in ["msgs_data", "proc_data", "rec_data", "dec_data", "encounters_data"]:
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
                {"id": "P.1.1", "label": r"$AN_{t}^{K}$", "color": "orange"},
                {"id": "O.0.0", "label": r"$ID+B$", "color": "viridis:1"},
                {"id": "O.2.0", "label": r"$ID+R_{f}$", "color": "viridis:2"},
                {"id": "O.1.1", "label": r"$ID+R_{1}$", "color": "viridis:3"},
                {"id": "O.1.0", "label": r"$ID+R_{\infty}$", "color": "viridis:4"},
            ],
            "plots": {"exclude_protocols": [], "exclude_tm": [], "show_ci": True},
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
        # gli id con suffisso "|<max_buff_size>" (varianti di P.1.1) seguono il protocollo base
        protocol = self.protocols_by_id.get(str(protocol_id).split('|')[0])
        plot_cfg = self.plot_config.get("plots", {})
        exclude = plot_cfg.get("exclude_protocols") or []
        if any(self._protocol_matches(protocol, sel) for sel in exclude):
            return False
        return True

###################################################
    def _plot_cols(self, cols):
        exclude = [str(c) for c in (self.plot_config.get("plots", {}).get("exclude_cols") or [])]
        return [c for c in cols if c[0] not in exclude]

###################################################
    def _is_p11(self, algo, n_agents, max_buff_size):
        # P.1.1: algo P con buffer ridotto a n_agents-1-X (X > 0)
        alg_lower = str(algo).strip().lower()
        if alg_lower == 'ps':
            return True
        if alg_lower != 'p':
            return False
        try:
            return int(float(max_buff_size)) < int(n_agents) - 1
        except (TypeError, ValueError):
            return False

###################################################
    def _shade_color(self, base_color, ratio):
        ratio = max(0.0, min(1.0, ratio))
        h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(base_color))
        rgb = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0 - ratio) * 0.4))), s * (1.0 - ((1.0 - ratio) * 0.3)))
        return tuple(np.clip(rgb, 0, 1))

###################################################
    def _isolines(self, state_grid, time_grid, ground_T, threshlds):
        """
        Isolinee Q=0.2 e Q=0.8 (G in funzione di tau, per interpolazione lineare) e tempo di
        riconoscimento associato. Restituisce (v2, v8, vt, sel) dove sel[th] e' l'indice di G
        da cui e' preso il tempo (None se non trovato).
        """
        v2, v8, vt, sel = [], [], [], []
        for th in range(len(threshlds)):
            vals2, vals8, gt2, gt8 = [np.nan]*2, [np.nan]*2, [np.nan]*2, [np.nan]*2
            valst, lim_valst, sel_pt = np.nan, np.nan, None
            for pt in range(len(ground_T)):
                val = state_grid[pt][th]
                if val is None: continue
                diff = ground_T[pt] - threshlds[th]
                if val >= 0.8:
                    if diff >= 0.09 and (np.isnan(valst) or diff < lim_valst):
                        valst, lim_valst, sel_pt = (time_grid[pt][th] if time_grid is not None else np.nan), diff, pt
                    if diff >= 0 and (np.isnan(vals8[1]) or val < vals8[1]):
                        vals8[1], gt8[1] = val, ground_T[pt]
                elif val <= 0.2:
                    if diff <= 0 and (np.isnan(vals2[0]) or val >= vals2[0]):
                        vals2[0], gt2[0] = val, ground_T[pt]
                else:
                    if np.isnan(vals8[0]) or val > vals8[0]: vals8[0], gt8[0] = val, ground_T[pt]
                    if np.isnan(vals2[1]) or val < vals2[1]: vals2[1], gt2[1] = val, ground_T[pt]
            if np.isnan(vals8[0]): vals8[0], gt8[0] = vals8[1], gt8[1]
            elif np.isnan(vals8[1]): vals8[1], gt8[1] = vals8[0], gt8[0]
            if np.isnan(vals2[0]): vals2[0], gt2[0] = vals2[1], gt2[1]
            elif np.isnan(vals2[1]): vals2[1], gt2[1] = vals2[0], gt2[0]
            v2.append(np.interp([0.2], vals2, gt2, left=np.nan)[0])
            v8.append(np.interp([0.8], vals8, gt8, right=np.nan)[0])
            vt.append(valst)
            sel.append(sel_pt)
        return np.array(v2, dtype=float), np.array(v8, dtype=float), np.array(vt, dtype=float), sel

###################################################
    def _isoline_bands(self, ci_entry, sel, ground_T, threshlds):
        """Bande CI 95% di isolinee e tempi: (v2_lo, v2_hi, v8_lo, v8_hi, t_lo, t_hi)."""
        q_lo, q_hi, t_lo, t_hi = ci_entry
        a2, a8, _, _ = self._isolines(q_lo, None, ground_T, threshlds)
        b2, b8, _, _ = self._isolines(q_hi, None, ground_T, threshlds)
        tl = np.array([t_lo[p][th] if p is not None else np.nan for th, p in enumerate(sel)], dtype=float)
        th_ = np.array([t_hi[p][th] if p is not None else np.nan for th, p in enumerate(sel)], dtype=float)
        return np.fmin(a2, b2), np.fmax(a2, b2), np.fmin(a8, b8), np.fmax(a8, b8), tl, th_

###################################################
    def _show_ci(self):
        return bool(self.plot_config.get("plots", {}).get("show_ci", True))

    def _fill_ci(self, ax, x, lo, hi, color):
        # banda del confidence interval 95%, disattivabile con "show_ci": false nel campo plots
        if self._show_ci():
            ax.fill_between(x, lo, hi, color=color, alpha=0.2, lw=0)

###################################################
    def _median_ci(self, values, z=1.96):
        # CI 95% della mediana senza ipotesi sulla distribuzione (statistiche d'ordine)
        v = np.sort(np.asarray(values, dtype=float))
        n = len(v)
        if n == 0: return np.nan, np.nan
        lo = int(np.floor(n / 2.0 - z * np.sqrt(n) / 2.0))
        hi = int(np.ceil(n / 2.0 + z * np.sqrt(n) / 2.0)) - 1
        return float(v[max(0, lo)]), float(v[min(n - 1, hi)])

###################################################
    def _recovery_variant_key(self, alg, broadcast, agents, buf, msgs, hops):
        alg_lower = str(alg).strip().lower()
        if alg_lower == 'ps':
            return 'P.1.1'
        if alg_lower == 'p':
            # AN: algo P senza tempo di scadenza dei messaggi
            if int(msgs) == 0: return 'P.0'
            return 'P.1.1' if self._is_p11(alg, agents, buf) else 'P.1.0'
        return f"{alg}.{int(broadcast)}.{int(hops)}"

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
    def fit_recovery(self, setting_key, runs_data):
        algo, arena, time_val, comm, agents, buf_dim, msgs, hops, gt, thr = setting_key
        
        path = self.base + "/weib_images/"
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            
        wf = WeibullFitter()
        kmf = KaplanMeierFitter()
        run_means = []
        run_events = []
        
        for run_id, run_data in runs_data.items():
            buff_starts = run_data[0]
            durations = run_data[1]
            event_observed = run_data[2]
            
            durations_by_buffer = self.dull_division(buff_starts, durations, event_observed)
            durations_by_buffer = self.sort_arrays_in_dict(durations_by_buffer)
            adapted_durations = self.adapt_dict_to_weibull_est(durations_by_buffer)
            
            for k in adapted_durations.keys():
                a_data = adapted_durations.get(k)[0]
                a_censoring = adapted_durations.get(k)[1]
                a_buffers = adapted_durations.get(k)[2]
                
                if len(a_data) > 20:
                    try:
                        wf.fit(a_data, event_observed=a_censoring)
                        if run_id==1:
                            kmf.fit(a_data, event_observed=a_censoring)
                            fig, ax = plt.subplots(figsize=(10,8))
                            ax.plot(wf.cumulative_density_, label="wf "+k)
                            ax.plot(kmf.cumulative_density_, label="kmf "+k)
                            fig.tight_layout()
                            
                            filename = f"{algo}_{comm}_{hops}_{agents}_{arena}_{buf_dim}_{gt}_{thr}_run{run_id}_{k}.pdf"
                            fig.savefig(os.path.join(path, filename))
                            plt.close(fig)
                        
                        mean_val, _ = self.wb_get_mean_and_std(wf)
                        if not np.isnan(mean_val) and not np.isinf(mean_val):
                            run_means.append(mean_val)
                            run_events.append(len(a_buffers) - 1)
                    except Exception:
                        pass
                        
        estimates = {}
        if len(run_means) > 10:
            run_means_arr = np.array(run_means)
            run_events_arr = np.array(run_events)
            n_runs = len(run_means_arr)
            
            mean_of_means = run_means_arr.mean()
            ci_time = 1.96 * (run_means_arr.std(ddof=1) / np.sqrt(n_runs)) if n_runs > 1 else 0.0
            
            mean_events = run_events_arr.mean()
            ci_events = 1.96 * (run_events_arr.std(ddof=1) / np.sqrt(n_runs)) if n_runs > 1 else 0.0
            
            estimates["all"] = [[mean_of_means, ci_time], [mean_events, ci_events]]
            
        return estimates
###################################################
    def fit_recovery_raw_data(self,data_in):
        fitted_data = {}
        for i in range(len(data_in)):
            for k in data_in[i].keys():
                estimates = self.fit_recovery(k, data_in[i].get(k))
                for z in estimates.keys():
                    fitted_data.update({(*k, z): estimates.get(z)})
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
    def plot_encounters(self, data):
        encounters_dict, ci_dict = {}, {}
        dict_park, dict_park_t1, dict_park_real_fifo, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{},{},{}
        ci_park, ci_park_t1, ci_park_real_fifo, ci_adam, ci_fifo,ci_rnd,ci_rnd_inf = {},{},{},{},{},{},{}
        for k in data.keys():
            algo = str(k[1]).strip().lower()
            n_agents = int(k[3]) if len(k) > 3 else 0
            buf_dim = int(k[4]) if len(k) > 4 else 0
            max_buff_size = k[6] if len(k) > 6 else str(max(0, n_agents - 1))
            is_priority_sampling = self._is_p11(algo, n_agents, max_buff_size)
            
            mean_vals = data.get(k)[0]
            ci_vals = data.get(k)[1]

            if is_priority_sampling and buf_dim > 0:
                dict_park_t1.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                ci_park_t1.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
            elif is_priority_sampling and buf_dim == 0:
                dict_park_real_fifo.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                ci_park_real_fifo.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
            elif k[1]=='P' and int(k[4]) > 0:
                dict_park.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                ci_park.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
            elif k[1]=='P' and int(k[4]) == 0:
                dict_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):mean_vals})
                ci_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):ci_vals})
            else:
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                    ci_adam.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                    ci_fifo.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                        ci_rnd.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                        ci_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                        
        encounters_dict.update({"P.0":dict_park_real_fifo})
        ci_dict.update({"P.0":ci_park_real_fifo})
        encounters_dict.update({"P.1.0":dict_park})
        ci_dict.update({"P.1.0":ci_park})
        encounters_dict.update({"P.1.1":dict_park_t1})
        ci_dict.update({"P.1.1":ci_park_t1})
        encounters_dict.update({"O.0.0":dict_adam})
        ci_dict.update({"O.0.0":ci_adam})
        encounters_dict.update({"O.2.0":dict_fifo})
        ci_dict.update({"O.2.0":ci_fifo})
        encounters_dict.update({"O.1.1":dict_rnd})
        ci_dict.update({"O.1.1":ci_rnd})
        encounters_dict.update({"O.1.0":dict_rnd_inf})
        ci_dict.update({"O.1.0":ci_rnd_inf})
        
        return encounters_dict, ci_dict

###################################################
    def print_encounters_barplot(self, data_in, data_ci, exclude_protocols=None, exclude_rows=None, exclude_cols=None):
        if exclude_protocols is None: exclude_protocols = self.plot_config.get("plots", {}).get("exclude_protocols", [])
        if exclude_rows is None: exclude_rows = self.plot_config.get("plots", {}).get("exclude_tm", [])
        if exclude_cols is None: exclude_cols = self.plot_config.get("plots", {}).get("exclude_cols", [])

        # All possible configurations
        all_cols = ["LD25", "HD25", "HD100"]
        
        # Active configurations to plot
        active_cols = [c for c in all_cols if c not in exclude_cols]
        if not active_cols: 
            return

        # Define colours based on configuration using viridis.
        # vmax is set to len(all_cols) instead of len(all_cols) - 1 to map
        # an extra step, effectively excluding the lightest yellow colour at the end.
        cNorm = colors.Normalize(vmin=0, vmax=len(all_cols))
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        config_colors = {
            col_name: scalarMap.to_rgba(idx) for idx, col_name in enumerate(all_cols)
        }

        # Create a single panel figure
        fig, ax = plt.subplots(figsize=(10, 7))
        
        real_x_ticks, void_x_ticks, svoid_x_ticks = [], [], []
        if len(real_x_ticks) == 0:
            for x in range(0, 901, 50):
                if x % 300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x, 0))))
                else:
                    void_x_ticks.append('')
                    
        # il plot degli encounter riguarda sempre e solo P.0, indipendentemente da exclude_protocols/exclude_tm
        for dk in ['P.0']:
            dct = data_in.get(dk, {})
            
            for k in dct.keys():
                ag_val_str = str(k[1]).strip()
                arena_val = str(k[0]).strip().replace('A', '')
                
                col_name = "LD25"
                if arena_val == 'big' and ag_val_str == '100': col_name = "HD100"
                elif arena_val == 'small': col_name = "HD25"

                if col_name not in active_cols:
                    continue
                    
                c_val = config_colors.get(col_name, "black")
                y_vals = np.array(dct.get(k))
                x_vals = np.arange(len(y_vals))
                
                # Plot as a thicker line
                ax.plot(x_vals, y_vals, color=c_val, linewidth=5)
                raw_ci = (data_ci.get(dk) or {}).get(k)
                if raw_ci is not None and len(raw_ci) == len(y_vals):
                    ci_vals = np.array(raw_ci)
                    self._fill_ci(ax, x_vals, np.maximum(0, y_vals - ci_vals), np.minimum(1.0, y_vals + ci_vals), color=c_val)
                
        # Set ticks and labels for the single axis
        ax.set_xticks(np.arange(0, 901, 300), labels=real_x_ticks)
        ax.set_xticks(np.arange(0, 901, 50), labels=void_x_ticks, minor=True)
            
        ax.set_ylabel(r"C")
        ax.set_xlabel(r"$\Delta T$")
            
        ax.grid(True, ls=':')
        ax.set_xlim(0, 900)
        ax.set_ylim(-0.03, 1.03)

        fig.tight_layout()
        # Adjust layout to make room for the legend at the bottom
        fig.subplots_adjust(bottom=0.2)
                    
        out_dir = os.path.join(self.base, "encounters_data", "images")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        fig_path = os.path.join(out_dir, "encounters_lineplot.pdf")
        
        # Generate the legend with square markers on a single row below the plot
        legend_handles = []
        legend_labels = []
        for col_name in active_cols:
            c_val = config_colors.get(col_name, "black")
            legend_handles.append(
                mlines.Line2D([], [], color=c_val, marker='s', linestyle='None', 
                              markersize=12, label=col_name)
            )
            legend_labels.append(col_name)
            
        if legend_handles:
            fig.legend(legend_handles, legend_labels, loc='lower center', 
                       bbox_to_anchor=(0.74, -0.05), ncol=len(legend_handles), 
                       framealpha=0.9, borderaxespad=0)
        fig.tight_layout()
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

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
            is_priority_sampling = self._is_p11(algo, n_agents, max_buff_size)

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
        stds_dict.update({"O.0.0":std_dict_adam})
        messages_dict.update({"O.2.0":dict_fifo})
        stds_dict.update({"O.2.0":std_dict_fifo})
        messages_dict.update({"O.1.1":dict_rnd})
        stds_dict.update({"O.1.1":std_dict_rnd})
        messages_dict.update({"O.1.0":dict_rnd_inf})
        stds_dict.update({"O.1.0":std_dict_rnd_inf})

        return messages_dict,stds_dict


###################################################
    def plot_decisions(self,data):
        decisions_dict, ci_dict = {}, {}
        dict_park, dict_park_t1, dict_park_real_fifo, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{},{},{}
        ci_park, ci_park_t1, ci_park_real_fifo, ci_adam, ci_fifo,ci_rnd,ci_rnd_inf = {},{},{},{},{},{},{}
        for k in data.keys():
            algo = str(k[1]).strip().lower()
            n_agents = int(k[3]) if len(k) > 3 else 0
            buf_dim = int(k[4]) if len(k) > 4 else 0
            max_buff_size = k[6] if len(k) > 6 else str(max(0, n_agents - 1))
            is_priority_sampling = self._is_p11(algo, n_agents, max_buff_size)
            
            mean_vals = data.get(k)[0]
            ci_vals = data.get(k)[1]

            if is_priority_sampling and buf_dim > 0:
                dict_park_t1.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                ci_park_t1.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
            elif is_priority_sampling and buf_dim == 0:
                dict_park_real_fifo.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                ci_park_real_fifo.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
            elif k[1]=='P' and int(k[4]) > 0:
                dict_park.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                ci_park.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
            elif k[1]=='P' and int(k[4]) == 0:
                dict_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):mean_vals})
                ci_park_real_fifo.update({(k[0],k[3],"60",max_buff_size):ci_vals})
            else:
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                    ci_adam.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                    ci_fifo.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                        ci_rnd.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):mean_vals})
                        ci_rnd_inf.update({(k[0],k[3],k[4],max_buff_size):ci_vals})
                        
        decisions_dict.update({"P.0":dict_park_real_fifo})
        ci_dict.update({"P.0":ci_park_real_fifo})
        decisions_dict.update({"P.1.0":dict_park})
        ci_dict.update({"P.1.0":ci_park})
        decisions_dict.update({"P.1.1":dict_park_t1})
        ci_dict.update({"P.1.1":ci_park_t1})
        decisions_dict.update({"O.0.0":dict_adam})
        ci_dict.update({"O.0.0":ci_adam})
        decisions_dict.update({"O.2.0":dict_fifo})
        ci_dict.update({"O.2.0":ci_fifo})
        decisions_dict.update({"O.1.1":dict_rnd})
        ci_dict.update({"O.1.1":ci_rnd})
        decisions_dict.update({"O.1.0":dict_rnd_inf})
        ci_dict.update({"O.1.0":ci_rnd_inf})
        self.print_decisions(decisions_dict, ci_dict)

###################################################
    def read_msgs_csv(self, path):
        data = {}
        with open(path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            header = next(reader, None)
            if not header:
                return data
            header_idx = {name: i for i, name in enumerate(header)}
            data_idx = header_idx.get("data", len(header) - 2)
            # Fetch ci_95 if present, fallback to std, then data_idx + 1
            std_idx = header_idx.get("ci_95", header_idx.get("std", data_idx + 1))
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
            run_idx = header.index("run_id") if "run_id" in header else -1
            parse_int = self._parse_int_list
            for row in reader:
                if len(row) <= e_idx:
                    continue
                run_id = int(row[run_idx]) if run_idx != -1 else 0
                key_list = row[:b_idx]
                if run_idx != -1 and run_idx < b_idx:
                    key_list.pop(run_idx)
                key = (algo, arena, *key_list)
                if key not in data:
                    data[key] = {}
                data[key][run_id] = (
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
    def plot_recovery(self, data_in, side_by_side: bool = True):
        
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
        all_tms = set()
        
        for key, value in data_in.items():
            # Spacchettamento robusto: cattura sia la vecchia struttura a 3 valori che la nuova a 4
            mean_time = float(value[0])
            ci_time = float(value[1]) if len(value) > 1 else 0.0
            mean_events = float(value[2]) if len(value) > 2 else 0.0
            ci_events = float(value[3]) if len(value) > 3 else 0.0
            
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k[:10]
            
            mbs = buf
            
            variant_key = self._recovery_variant_key(alg, broadcast, agents, buf, msgs, hops)

            # i pannelli T_m disponibili dipendono da tutti i dati, non solo dai protocolli abilitati
            if int(msgs) > 0: all_tms.add(int(msgs))

            if not self._protocol_enabled(variant_key): continue
            
            label, color = variant_map.get(variant_key, ('UNK', 'black'))
            
            # I valori CI non vengono passati al DataFrame, mantenendo i grafici originali
            rows.append({
                'Arena': str(arena), 'Agents': int(agents), 'Msgs_exp_time': int(msgs),
                'Error': abs(float(gt) - float(th)), 'Events': mean_events / int(agents),
                'Time': mean_time, 
                'CI_Time': ci_time, 
                'CI_Events': ci_events / int(agents),
                'VariantKey': variant_key, 'Label': label, 'Color': color, 'MBS': mbs
            })
            
        df = pd.DataFrame(rows)
        if not df.empty:
            # AN (P.0) non ha T_m: tiene Msgs_exp_time=0 e viene mostrato come base in ogni pannello
            df = df[(df['Msgs_exp_time'] != 0) | (df['VariantKey'] == 'P.0')]
        
        cols = self._plot_cols([("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)])
        if not cols: return
        grid = [(arena, ag) for _, arena, ag in cols]
        row_labels = [lbl for lbl, _, _ in cols]
        
        if df.empty: return
        msg_list = self._plot_tm_values(sorted(all_tms))
        if not msg_list: return
        
        if 60 in msg_list:
            msg_list = [60] + [m for m in msg_list if m != 60]
        col_labels = [f"$T_m$={m}" for m in msg_list]
        
        mbs_global_map = {}
        for ag in df['Agents'].unique():
            mbs_vals = df[(df['VariantKey'] == 'P.1.1') & (df['Agents'] == ag)]['MBS'].unique()
            mbs_global_map[ag] = sorted(list(mbs_vals), key=lambda x: float(x))

        def save_box(subset, threshold_str, entry, global_max, side_by_side_mode=False):
            if subset.empty: return
            
            nrows, ncols = len(msg_list), len(grid)
            fig, axes = plt.subplots(nrows, ncols, figsize=(ncols*8, nrows*8), squeeze=False, sharex=True, sharey=True)
            
            for i, tm_val in enumerate(msg_list):
                for j, (arena_type, ag_num) in enumerate(grid):
                    ax = axes[i, j]
                    
                    mask_base = (subset['Arena'] == arena_type) & (subset['Agents'] == ag_num)
                    base_cell = subset.loc[mask_base]
                    pos_idx = 1
                    tick_labels, tick_pos = [], []

                    for pid in protocols_order:
                        if not self._protocol_enabled(pid): continue
                        
                        target_tm = 0 if pid == 'P.0' else tm_val
                        mask_p = (base_cell['VariantKey'] == pid) & (base_cell['Msgs_exp_time'] == target_tm)
                        p_cell = base_cell.loc[mask_p]
                        
                        base_color = variant_map[pid][1]
                        width = 1.2
                        
                        if pid == "P.1.1":
                            mbs_list = mbs_global_map.get(ag_num, [])
                            n_mbs_total = len(mbs_list)
                            
                            if n_mbs_total > 0:
                                for m_idx, val_mbs in enumerate(mbs_list):
                                    d_mbs_row = p_cell.loc[p_cell['MBS'] == val_mbs]
                                    d = d_mbs_row[entry].dropna().astype(float).values
                                    
                                    if len(d) > 0 or (side_by_side_mode and not d_mbs_row.empty):
                                        ratio = (m_idx + 1) / n_mbs_total
                                        h, l, s = colorsys.rgb_to_hls(*colors.to_rgb(base_color))
                                        c_val = colorsys.hls_to_rgb(h, max(l, min(0.85, l + ((1.0-ratio)*0.4))), s*(1.0-((1.0-ratio)*0.3)))
                                        
                                        offset = (m_idx - (n_mbs_total - 1) / 2.0) * width
                                        
                                        if side_by_side_mode:
                                            self._draw_boxes_internal(ax, d_mbs_row, entry, pos_idx + offset, width, c_val, side_by_side_mode)
                                        else:
                                            if len(d) > 0:
                                                ax.boxplot(d, positions=[pos_idx + offset], widths=width, patch_artist=True,
                                                           boxprops=dict(facecolor=c_val), medianprops=dict(color='gray'))
                            else:
                                d = p_cell[entry].dropna().astype(float).values
                                if len(d) > 0 or (side_by_side_mode and not p_cell.empty):
                                    if side_by_side_mode:
                                        self._draw_boxes_internal(ax, p_cell, entry, pos_idx, width, base_color, side_by_side_mode)
                                    else:
                                        if len(d) > 0:
                                            ax.boxplot(d, positions=[pos_idx], widths=width, patch_artist=True,
                                                       boxprops=dict(facecolor=base_color), medianprops=dict(color='gray'))
                        else:
                            d = p_cell[entry].dropna().astype(float).values
                            if len(d) > 0 or (side_by_side_mode and not p_cell.empty):
                                if side_by_side_mode:
                                    self._draw_boxes_internal(ax, p_cell, entry, pos_idx, width, base_color, side_by_side_mode)
                                else:
                                    if len(d) > 0:
                                        ax.boxplot(d, positions=[pos_idx], widths=width, patch_artist=True,
                                                   boxprops=dict(facecolor=base_color), medianprops=dict(color='gray'))
                        
                        tick_pos.append(pos_idx)
                        tick_labels.append(variant_map[pid][0])
                        pos_idx += 1
                    
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
                        ax.set_title(row_labels[j])
                    
                    if j == 0:
                        row_label_left = r"$E_{r}$" if entry == "Events" else r"$T_{r}$"
                        ax.set_ylabel(row_label_left)
                    
                    if j == ncols - 1:
                        ax.annotate(f"$T_m$={tm_val} s", xy=(1.03, 0.5), xycoords='axes fraction',
                                    rotation=270, ha='left', va='center')
            
            fig.tight_layout(rect=[0, 0.05, 1, 0.98])
            fig.savefig(os.path.join(images_dir, f"box_recovery_{threshold_str}_{entry}.pdf"), bbox_inches='tight')
            plt.close(fig)

        if df.empty: return
        time_max = df["Time"].max()
        event_max = df["Events"].max()
        
        if side_by_side:
            save_box(df, "sidebyside", 'Events', event_max, side_by_side_mode=True)
            save_box(df, "sidebyside", 'Time', time_max, side_by_side_mode=True)
        else:
            df_le = df[df['Error'] <= 0.05]
            if not df_le.empty:
                save_box(df_le, "0.05_le", 'Events', event_max, side_by_side_mode=False)
                save_box(df_le, "0.05_le", 'Time', time_max, side_by_side_mode=False)
                
            df_gt = df[df['Error'] > 0.05]
            if not df_gt.empty:
                save_box(df_gt, "0.05_gt", 'Events', event_max, side_by_side_mode=False)
                save_box(df_gt, "0.05_gt", 'Time', time_max, side_by_side_mode=False)

###################################################
    def plot_recovery_short(self, data_in, side_by_side: bool = True):
        images_dir = os.path.join(self.base, "compressed_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cm.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        
        variant_map = {p.get("id"): (p.get("label", p.get("id")), self._protocol_color(p, scalarMap)) 
                       for p in self.protocols if p.get("id")}
        
        protocols_order = [p.get("id") for p in self.protocols if p.get("id") and self._protocol_enabled(p.get("id"))]

        rows = []
        all_tms = set()
        for key, value in data_in.items():
            mean_time = float(value[0])
            ci_time = float(value[1]) if len(value) > 1 else 0.0
            mean_events = float(value[2]) if len(value) > 2 else 0.0
            ci_events = float(value[3]) if len(value) > 3 else 0.0
            
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k[:10]
            
            mbs = buf
            
            variant_key = self._recovery_variant_key(alg, broadcast, agents, buf, msgs, hops)

            # i T_m disponibili dipendono da tutti i dati, non solo dai protocolli abilitati
            if int(msgs) > 0: all_tms.add(int(msgs))

            if not self._protocol_enabled(variant_key): continue
            
            label, color = variant_map.get(variant_key, ('UNK', 'black'))
            
            rows.append({
                'Arena': arena, 'Agents': int(agents), 'Msgs_exp_time': int(msgs),
                'Error': abs(float(gt) - float(th)), 'Events': mean_events / int(agents),
                'Time': mean_time, 'VariantKey': variant_key, 'Label': label, 
                'Color': color, 'MBS': mbs
            })

        df = pd.DataFrame(rows)
        if df.empty: return
        
        # AN (P.0) non ha T_m: tiene Msgs_exp_time=0 e viene mostrato come base
        df = df[(df['Msgs_exp_time'] != 0) | (df['VariantKey'] == 'P.0')]
        if df.empty: return
        
        mbs_global_map = {}
        for ag in df['Agents'].unique():
            mbs_vals = df[(df['VariantKey'] == 'P.1.1') & (df['Agents'] == ag)]['MBS'].unique()
            mbs_global_map[ag] = sorted(list(mbs_vals), key=lambda x: float(x))

        main_tm_list = self._plot_tm_values(sorted(all_tms))
        insert_tm_list = self._get_valid_insert_tm()
        
        combined_tm = sorted(list(set(main_tm_list) | set(insert_tm_list)))
        active_labels = [variant_map[pid][0] for pid in protocols_order]
        densities = self._plot_cols([("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)])
        if not densities: return

        def save_short(subset, suffix, side_by_side_mode: bool):
            if subset.empty: return
            fig, axes = plt.subplots(2, len(densities), figsize=(8 * len(densities), 14), squeeze=False)
            event_max = subset["Events"].max()
            time_max = subset["Time"].max()

            for col_idx, (dens_label, arena, ag) in enumerate(densities):
                cell = subset[(subset['Arena'] == arena) & (subset['Agents'] == ag)]

                for row_idx, entry in enumerate(["Events", "Time"]):
                    ax = axes[row_idx, col_idx]
                    if row_idx == 0: ax.set_title(dens_label)

                    n_tm_total = len(combined_tm)
                    width_tm = 1.2
                    
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
                                    current_n_total = len(tms) 
                                    tm_off = (t_idx - (current_n_total - 1) / 2.0) * width_tm
                                
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
                    
                    if col_idx == 0: ax.set_ylabel(r"$E_{r}$" if row_idx == 0 else r"$T_{r}$")
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
                        
                        ins.grid(True, ls=':', color='silver', zorder=0)

            fig.tight_layout()
            fig.savefig(os.path.join(images_dir, f"box_short_{suffix}.pdf"), bbox_inches='tight')
            plt.close(fig)

        if side_by_side: save_short(df, "sidebyside", True)
        else:
            save_short(df[df['Error'] <= 0.05], "le05", False)
            save_short(df[df['Error'] > 0.05], "gt05", False)

###################################################
    def plot_recovery_pareto(self, data_in):
        images_dir = os.path.join(self.base, "compressed_data", "images")
        os.makedirs(images_dir, exist_ok=True)
        norm = colors.Normalize(vmin=0, vmax=6)
        scalarMap = cm.ScalarMappable(norm=norm, cmap=plt.get_cmap('viridis'))
        
        variant_map = {p.get("id"): (p.get("label", p.get("id")), self._protocol_color(p, scalarMap)) 
                       for p in self.protocols if p.get("id")}
        
        protocols_order = [p.get("id") for p in self.protocols if p.get("id") and self._protocol_enabled(p.get("id"))]

        marker_map = {
            'P.0': 'o',      
            'P.1.0': 's',    
            'P.1.1': 'D',    
            'O.0.0': 'P',    
            'O.2.0': '^',    
            'O.1.1': 'v',    
            'O.1.0': 'X'     
        }

        rows = []
        all_tms = set()
        all_times = []
        for key, value in data_in.items():
            mean_time = float(value[0])
            ci_time = float(value[1]) if len(value) > 1 else 0.0
            mean_events = float(value[2]) if len(value) > 2 else 0.0
            ci_events = float(value[3]) if len(value) > 3 else 0.0
            
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k[:10]
            
            mbs = buf
            
            variant_key = self._recovery_variant_key(alg, broadcast, agents, buf, msgs, hops)

            # i T_m disponibili dipendono da tutti i dati, non solo dai protocolli abilitati
            if int(msgs) > 0: all_tms.add(int(msgs))
            # limiti dell'asse y calcolati su tutti i protocolli, cosi' non cambiano con exclude_protocols
            if (int(msgs) > 0 or variant_key == 'P.0') and mean_time > 0: all_times.append(mean_time)

            if not self._protocol_enabled(variant_key): continue
            
            label, color = variant_map.get(variant_key, ('UNK', 'black'))
            
            rows.append({
                'Arena': arena, 'Agents': int(agents), 'Msgs_exp_time': int(msgs),
                'Error': abs(float(gt) - float(th)), 'Events': mean_events / int(agents),
                'Time': mean_time, 'VariantKey': variant_key, 'Label': label, 
                'Color': color, 'MBS': mbs
            })

        df = pd.DataFrame(rows)
        if df.empty: return
        
        # AN (P.0) non ha T_m: tiene Msgs_exp_time=0 e viene mostrato come base in ogni pannello
        df = df[(df['Msgs_exp_time'] != 0) | (df['VariantKey'] == 'P.0')]
        if df.empty: return
        mbs_global_map = {}
        for ag in df['Agents'].unique():
            mbs_vals = df[(df['VariantKey'] == 'P.1.1') & (df['Agents'] == ag)]['MBS'].dropna().unique()
            sorted_mbs = sorted([float(x) for x in mbs_vals if str(x).strip() != ''], reverse=True)
            mbs_global_map[ag] = sorted_mbs[:3]

        main_tm_list = self._plot_tm_values(sorted(all_tms))
        insert_tm_list = self._get_valid_insert_tm()
        
        densities = self._plot_cols([("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)])
        if not densities: return
        v_events = df[df['Events'] > 0]['Events']
        v_times = df[df['Time'] > 0]['Time']
        g_e_min = v_events.min() if not v_events.empty else 0.5
        g_e_max = df['Events'].max() if not df.empty else 100.0
        g_t_min = min(all_times) if all_times else (v_times.min() if not v_times.empty else 0.5)
        g_t_max = df['Time'].max() if not df.empty else 100.0
        pad_factor = 1
        xlim_global = (0.5, g_e_max * pad_factor +10)
        ylim_global = (g_t_min / pad_factor, 1100)

        def save_short(subset):
            if subset.empty: return
            msg_list = sorted(main_tm_list)
            if 60 in msg_list:
                msg_list = [60] + [m for m in msg_list if m != 60]
            if not msg_list: return
            nrows = len(msg_list)
            ncols = len(densities)
            fig, axes = plt.subplots(nrows, ncols, figsize=(22 * ncols / 3, 7.3 * nrows), squeeze=False, sharex=True, sharey=True)

            for i, tm_val in enumerate(msg_list):
                for j, (dens_label, arena, ag) in enumerate(densities):
                    ax = axes[i, j]
                    cell = subset[(subset['Arena'] == arena) & (subset['Agents'] == ag)]

                    ax.set_box_aspect(1)
                    ax.set_yscale('log')
                    ax.set_xscale('log')
                    ax.set_xlim(xlim_global)
                    ax.set_ylim(ylim_global)

                    def draw_pass(target_ax, target_tm, tt_type):
                        for pid in protocols_order:
                            is_p0 = (pid == 'P.0')
                            marker = marker_map.get(pid, 'o')
                            t_tm = 0 if is_p0 else target_tm
                            p_data = cell[(cell['VariantKey'] == pid) & (cell['Msgs_exp_time'] == t_tm)]
                            
                            if p_data.empty: continue
                            
                            if pid == "P.1.1":
                                mbs_list = mbs_global_map.get(ag, [])
                                s_float = pd.to_numeric(p_data['MBS'], errors='coerce')
                                cmap_k = plt.get_cmap('cool_r')
                                k_color_ts = [0.25, 0.5, 0.75]
                                
                                for m_idx, val_mbs in enumerate(mbs_list):
                                    mask = (s_float - val_mbs).abs() < 1e-3
                                    d_row = p_data[mask.fillna(False)]
                                    if not d_row.empty:
                                        c_t = k_color_ts[m_idx] if m_idx < len(k_color_ts) else 0.72
                                        self._draw_scatter_internal(target_ax, d_row, cmap_k(c_t), tt_type, marker)
                            else:
                                self._draw_scatter_internal(target_ax, p_data, variant_map[pid][1], tt_type, marker)

                    draw_pass(ax, tm_val, "main")
                    
                    if i == 0: ax.set_title(dens_label)
                    if j == 0: ax.set_ylabel(r"$T_{r}$")
                    if i == nrows - 1: ax.set_xlabel(r"$E_{r}$")
                    # if j == ncols - 1:
                    #     ax.annotate(rf"$T_m={tm_val}$ s", xy=(1.03, 0.5), xycoords='axes fraction',
                    #                 rotation=270, ha='left', va='center')

                    ax.set_axisbelow(True)
                    ax.grid(True, ls=':', zorder=0)

                    if insert_tm_list:
                        best_box = [1.0 - 0.44 - 0.03, 1.0 - 0.44 - 0.03, 0.44, 0.44]
                        ins = ax.inset_axes(best_box, sharex=ax, sharey=ax)
                        ins.autoscale(False)
                        draw_pass(ins, insert_tm_list[0], "inset")
                        ins.tick_params(labelbottom=False, labeltop=False, labelleft=False, labelright=False)
                        if i == nrows - 1: ax.tick_params(labelbottom=True)
                        if j == 0: ax.tick_params(labelleft=True)
                        ins.set_axisbelow(True)
                        ins.grid(True, ls=':', color='silver', zorder=0)

            legend_elements = []
            cmap_k = plt.get_cmap('cool_r')
            k_color_ts = [0.25, 0.5, 0.75]
            k_labels = [r"K_1", r"K_2", r"K_3"]
            
            for pid in protocols_order:
                if pid == "P.1.1":
                    base_lbl = variant_map[pid][0]
                    for m_idx in range(3):
                        c_t = k_color_ts[m_idx]
                        lbl_k = k_labels[m_idx]
                        if "^{K}" in base_lbl: lbl = base_lbl.replace("^{K}", rf"^{{{lbl_k}}}")
                        elif "^K" in base_lbl: lbl = base_lbl.replace("^K", rf"^{{{lbl_k}}}")
                        else: lbl = rf"{base_lbl} (${lbl_k}$)"
                        legend_elements.append(Line2D([0], [0], color=cmap_k(c_t), marker=marker_map.get(pid, 'D'), linestyle='None', markersize=14, label=lbl))
                else:
                    legend_elements.append(Line2D([0], [0], color=variant_map[pid][1], marker=marker_map.get(pid, 'o'), linestyle='None', markersize=14, label=variant_map[pid][0]))
            
            fig.legend(handles=legend_elements, loc='lower center', ncol=6, bbox_to_anchor=(0.62, -0.1))
            fig.tight_layout(rect=[0, 0.05, 1, 1])
            fig.savefig(os.path.join(images_dir, f"pareto_recovery.pdf"), bbox_inches='tight')
            plt.close(fig)

        save_short(df)
        # self.plot_recovery_scatter_all_tm(df, mbs_global_map, variant_map, protocols_order, marker_map, xlim_global, ylim_global, tm_values=sorted(all_tms))

###################################################
    def plot_recovery_scatter_all_tm(self, df, mbs_global_map, variant_map, protocols_order, marker_map, xlim_global, ylim_global, tm_values=None):
        images_dir = os.path.join(self.base, "compressed_data", "images")
        
        raw_tms = tm_values if tm_values is not None else [m for m in df[df['VariantKey'] != 'P.0']['Msgs_exp_time'].unique() if m > 0]
        msg_list = sorted(raw_tms)
        
        if not msg_list: return
        if 60 in msg_list:
            msg_list = [60] + [m for m in msg_list if m != 60]
            
        densities = self._plot_cols([("LD25", "bigA", 25), ("HD25", "smallA", 25), ("HD100", "bigA", 100)])
        if not densities: return
        nrows = len(msg_list)
        ncols = len(densities)
        
        # Using sharex=True to ensure uniform min/max across all columns
        fig, axes = plt.subplots(nrows, ncols, figsize=(ncols*8, nrows*8), squeeze=False, sharex=True, sharey=True)

        for i, tm_val in enumerate(msg_list):
            for j, (dens_label, arena, ag) in enumerate(densities):
                ax = axes[i, j]
                cell = df[(df['Arena'] == arena) & (df['Agents'] == ag)]
                
                for pid in protocols_order:
                    is_p0 = (pid == 'P.0')
                    target_tm = 0 if is_p0 else tm_val
                    p_data = cell[(cell['VariantKey'] == pid) & (cell['Msgs_exp_time'] == target_tm)]
                    
                    if p_data.empty: continue
                    marker = marker_map.get(pid, 'o')
                    
                    if pid == "P.1.1":
                        mbs_list = mbs_global_map.get(ag, [])
                        s_float = pd.to_numeric(p_data['MBS'], errors='coerce')
                        cmap_k = plt.get_cmap('cool_r')
                        k_color_ts = [0.25, 0.5, 0.75]
                        
                        for m_idx, val_mbs in enumerate(mbs_list):
                            mask = (s_float - val_mbs).abs() < 1e-3
                            d_row = p_data[mask.fillna(False)]
                            if not d_row.empty:
                                c_t = k_color_ts[m_idx] if m_idx < len(k_color_ts) else 0.72
                                self._draw_scatter_internal(ax, d_row, cmap_k(c_t), 'main', marker)
                    else:
                        self._draw_scatter_internal(ax, p_data, variant_map[pid][1], 'main', marker)

                ax.set_yscale('log')
                ax.set_xscale('log')
                ax.set_xlim(xlim_global)
                ax.set_ylim(ylim_global)

                ax.grid(True, ls=':', zorder=0)

                if i == 0: ax.set_title(dens_label)
                if j == 0: ax.set_ylabel(r"$T_{r}$")
                if i == nrows - 1: ax.set_xlabel(r"$E_{r}$")
                if j == ncols - 1:
                    ax.annotate(rf"$T_m={tm_val}$ s", xy=(1.03, 0.5), xycoords='axes fraction',
                                rotation=270, ha='left', va='center')

        legend_elements = []
        cmap_k = plt.get_cmap('cool_r')
        k_color_ts = [0.25, 0.5, 0.75]
        k_labels = [r"K_1", r"K_2", r"K_3"]
        
        for pid in protocols_order:
            if pid == "P.1.1":
                base_lbl = variant_map[pid][0]
                for m_idx in range(3):
                    c_t = k_color_ts[m_idx]
                    lbl_k = k_labels[m_idx]
                    if "^{K}" in base_lbl: lbl = base_lbl.replace("^{K}", rf"^{{{lbl_k}}}")
                    elif "^K" in base_lbl: lbl = base_lbl.replace("^K", rf"^{{{lbl_k}}}")
                    else: lbl = rf"{base_lbl} (${lbl_k}$)"
                    legend_elements.append(Line2D([0], [0], color=cmap_k(c_t), marker=marker_map.get(pid, 'D'), linestyle='None', markersize=14, label=lbl))
            else:
                legend_elements.append(Line2D([0], [0], color=variant_map[pid][1], marker=marker_map.get(pid, 'o'), linestyle='None', markersize=14, label=variant_map[pid][0]))
            
        fig.legend(handles=legend_elements, loc='lower center', ncol=6, bbox_to_anchor=(0.58, 0.03))
        fig.tight_layout(rect=[0, 0.05, 1, 1])
        fig.savefig(os.path.join(images_dir, f"scatter_recovery_all_tm.pdf"), bbox_inches='tight')
        plt.close(fig)
        
###################################################
    def _draw_scatter_internal(self, ax, data, color, target_type, marker_type='o'):
        sc_size = 200 if target_type == 'main' else 75
        alpha_val = 0.3 if target_type == 'main' else 0.2
        d_le = data[data['Error'] <= 0.05]['Events'].values
        t_le = data[data['Error'] <= 0.05]['Time'].values
        if len(d_le) > 0:
            # 1. Draw the scatter points with zorder=2 (above the highlighted area)
            ax.scatter(d_le, t_le, marker=marker_type, s=sc_size, alpha=alpha_val, c=[color]*len(d_le), edgecolors='none', zorder=2)
            # 2. Compute variables for the shaded area
            alpha_fill = 0.15 if target_type == 'main' else 0.05
            alpha_edge = 0.40 if target_type == 'main' else 0.20
            points = np.column_stack((d_le, t_le))
            # Prevent log(0) errors by setting a tiny lower bound for the transformation
            safe_t_le = np.where(t_le > 0, t_le, 1e-10)
            # Transform the Y-axis into logarithmic space strictly for the Hull calculation
            hull_space_points = np.column_stack((d_le, np.log10(safe_t_le)))
            # Remove duplicate points based on the transformed space to prevent Qhull geometry errors
            _, unique_indices = np.unique(hull_space_points, axis=0, return_index=True)
            if len(unique_indices) >= 3:
                from scipy.spatial import ConvexHull
                from matplotlib.patches import Polygon
                try:
                    # Calculate the hull in logarithmic space
                    unique_hull_space = hull_space_points[unique_indices]
                    hull = ConvexHull(unique_hull_space)
                    
                    # Map the hull vertices back to the ORIGINAL linear coordinates for plotting
                    original_vertices = points[unique_indices][hull.vertices]
                    
                    poly = Polygon(original_vertices, 
                                   facecolor=colors.to_rgba(color, alpha_fill), 
                                   edgecolor=colors.to_rgba(color, alpha_edge), 
                                   linewidth=2, zorder=1)
                    ax.add_patch(poly)
                except Exception:
                    # Fallback for collinear points that fail the Convex Hull calculation
                    unique_points = points[unique_indices]
                    ax.plot(unique_points[:, 0], unique_points[:, 1], color=colors.to_rgba(color, alpha_edge), linewidth=2, zorder=1)
            elif len(unique_indices) == 2:
                # Draw a simple connective line if there are only exactly two unique points
                unique_points = points[unique_indices]
                ax.plot(unique_points[:, 0], unique_points[:, 1], color=colors.to_rgba(color, alpha_edge), linewidth=2, zorder=1)

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
    def store_recovery(self,data_in):
        if not os.path.exists(self.base+"/rec_data/"):
            os.mkdir(self.base+"/rec_data/")
        path = self.base+"/rec_data/"
        out_path = os.path.join(path, "recovery_data.csv")
        write_header = not os.path.exists(out_path) or os.path.getsize(out_path) == 0
        rows = []
        for k, s_data in data_in.items():
            a, a_s, et, c, n_a, m_b_d, met, m_h, gt, thr, jl = k
            mean_time = s_data[0][0]
            ci_time = s_data[0][1]
            mean_events = s_data[1][0]
            ci_events = s_data[1][1]
            rows.append([a, a_s, et, c, n_a, m_b_d, met, m_h, gt, thr, mean_time, ci_time, mean_events, ci_events])
        if rows:
            with open(out_path, mode='a', newline='', buffering=1024 * 1024) as file:
                writer = csv.writer(file)
                if write_header:
                    writer.writerow(['Algorithm', 'Arena', 'Time', 'Broadcast', 'Agents', 'Buffer_Dim','Msgs_exp_time','Msg_Hops', 'Ground_T', 'Threshold', 'Mean_Time', 'CI_Time', 'Mean_Events', 'CI_Events'])
                writer.writerows(rows)
        
###################################################
    def print_decisions(self, data_in, data_ci, exclude_protocols=None, exclude_rows=None, exclude_cols=None):
        if exclude_protocols is None: exclude_protocols = self.plot_config.get("plots", {}).get("exclude_protocols", [])
        if exclude_rows is None: exclude_rows = self.plot_config.get("plots", {}).get("exclude_tm", [])
        if exclude_cols is None: exclude_cols = self.plot_config.get("plots", {}).get("exclude_cols", [])

        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r = []
        l_list = []
        
        all_agents = set()
        mbs_per_agent = {}
        
        for dk in data_in.keys():
            dct = data_in.get(dk)
            for k in dct.keys():
                try:
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
            if pid in exclude_protocols or not self._protocol_enabled(pid):
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
                
        rows = [60, 120, 180, 300, 600]
        rows = [r for r in rows if str(r) not in exclude_rows]
        rows = self._plot_tm_values(rows)
        if not rows:
            return
        row_index = {str(c): i for i, c in enumerate(rows)}
        nrows = len(rows)
        
        active_cols = [c for c in ["LD25", "HD25", "HD100"] if c not in exclude_cols]
        ncols = len(active_cols)
        if ncols == 0: return
        
        fig, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=(8*ncols, nrows*7), sharex=True, sharey=True, squeeze=False)
        
        if len(real_x_ticks) == 0:
            for x in range(0, 901, 50):
                if x % 300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x, 0))))
                else:
                    void_x_ticks.append('')
                    
        for dk in data_in.keys():
            if dk in exclude_protocols or not self._protocol_enabled(dk):
                continue
            dct = data_in.get(dk)
            for k in dct.keys():
                if dk != 'P.0' and k[2] not in row_index:
                    continue
                
                ag_val_str = str(k[1]).strip()
                arena_val = str(k[0]).strip().replace('A', '')
                
                col_name = "LD25"
                if arena_val == 'big' and ag_val_str == '100': col_name = "HD100"
                elif arena_val == 'small': col_name = "HD25"

                if col_name not in active_cols:
                    continue
                col = active_cols.index(col_name)
                    
                c_val = protocol_colors.get(dk, "gray")
                is_p11 = (dk == "P.1.1" or dk.startswith("P.1.1"))
                if is_p11 and len(k) > 3:
                    try:
                        m_b_s = k[3]
                        ag_val_int = int(k[1])
                        if m_b_s != "" and ag_val_int in mbs_sorted and len(mbs_sorted[ag_val_int]) > 0:
                            val = float(m_b_s)
                            N_vals = len(mbs_sorted[ag_val_int])
                            idx = mbs_sorted[ag_val_int].index(val)
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
                
                y_vals = np.array(dct.get(k))
                
                raw_ci = None
                if data_ci.get(dk) is not None:
                    raw_ci = data_ci.get(dk).get(k)
                    
                if raw_ci is None or len(raw_ci) != len(y_vals):
                    ci_vals = np.zeros_like(y_vals)
                else:
                    ci_vals = np.array(raw_ci)
                    
                x_vals = np.arange(len(y_vals))
                
                if dk == 'P.0':
                    for r_idx in range(nrows):
                        ax[r_idx][col].plot(x_vals, y_vals, color=c_val, lw=6)
                        self._fill_ci(ax[r_idx][col], x_vals, np.maximum(0, y_vals - ci_vals), np.minimum(1.0, y_vals + ci_vals), color=c_val)
                else:
                    row = row_index.get(k[2])
                    if row is not None:
                        ax[row][col].plot(x_vals, y_vals, color=c_val, lw=6)
                        self._fill_ci(ax[row][col], x_vals, np.maximum(0, y_vals - ci_vals), np.minimum(1.0, y_vals + ci_vals), color=c_val)
                
        for x in range(nrows):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0, 901, 300), labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0, 901, 50), labels=void_x_ticks, minor=True)
                
        for y in range(ncols):
            ax[nrows-1][y].set_xticks(np.arange(0, 901, 300), labels=real_x_ticks)
            ax[nrows-1][y].set_xticks(np.arange(0, 901, 50), labels=void_x_ticks, minor=True)
        for idx, col_val in enumerate(active_cols):
            axt=ax[0][idx].twiny()
            axt.tick_params(labeltop=False, labelbottom=False)
            axt.set_xlabel(f"{col_val}")   

        
        last_col = ncols - 1
        ays = []
        for idx in range(nrows):
            ayt = ax[idx][last_col].twinx()
            ayt.tick_params(labelright=False)
            ays.append(ayt)
        for idx, row_val in enumerate(rows):
            ays[idx].set_ylabel(rf"$T_m = {row_val}\, s$",rotation=270,labelpad=30)
        for x in range(nrows):
            ax[x][0].set_ylabel(r"$D$")
            
        for y in range(ncols):
            ax[nrows-1][y].set_xlabel(r"$T$")
            
        for x in range(nrows):
            for y in range(ncols):
                ax[x][y].grid(True, ls=':')
                ax[x][y].set_xlim(0, 900)
                ax[x][y].set_ylim(-0.03, 1.03)

        fig.tight_layout()
                    
        if not os.path.exists(self.base + "/dec_data/images/"):
            os.mkdir(self.base + "/dec_data/images/")
        fig_path = self.base + "/dec_data/images/decisions.pdf"
        
        if handles_r:
            fig.legend(handles_r, l_list, bbox_to_anchor=(0.96, 0.01), ncols=len(handles_r), loc='upper right', framealpha=0.7, borderaxespad=0)
            
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

###################################################

    def print_messages(self, data_in, data_std, exclude_protocols=None, exclude_rows=None, exclude_cols=None):
        if exclude_protocols is None: exclude_protocols = self.plot_config.get("plots", {}).get("exclude_protocols", [])
        if exclude_rows is None: exclude_rows = self.plot_config.get("plots", {}).get("exclude_tm", [])
        if exclude_cols is None: exclude_cols = self.plot_config.get("plots", {}).get("exclude_cols", [])

        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        min_dim = mlines.Line2D([], [], color="black", marker='None', linestyle='--', linewidth=4, label=r'$\dfrac{\mathcal{B}_{m}}{N-1}$')
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
            if pid in exclude_protocols or not self._protocol_enabled(pid):
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
        l_list.append(r'$\dfrac{\mathcal{B}_{m}}{N-1}$')
        
        rows = [60, 120, 180, 300, 600]
        rows = [r for r in rows if str(r) not in exclude_rows]
        rows = self._plot_tm_values(rows)
        if not rows:
            return
        col_index = {str(c): i for i, c in enumerate(rows)}
        nrows = len(rows)
        
        active_cols = [c for c in ["LD25", "HD25", "HD100"] if c not in exclude_cols]
        ncols = len(active_cols)
        if ncols == 0: return
        
        fig, ax = plt.subplots(nrows=nrows, ncols=ncols,figsize=(8*ncols,nrows*7),sharex=True,sharey=True, squeeze=False)
        
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.around(x,0))))
                else:
                    void_x_ticks.append('')
                    
        for k in range(ncols):
            for z in range(nrows):
                col_name = active_cols[k]
                den = 100 if col_name == "HD100" else 25
                val_min_buf = 5 / den
                ax[z][k].plot([val_min_buf for _ in range(901)],color="black",ls='--',lw=3)
                
        for dk in data_in.keys():
            if dk in exclude_protocols or not self._protocol_enabled(dk):
                continue
            dict_dk = data_in.get(dk)
            for k in dict_dk.keys():
                if dk != 'P.0' and k[2] not in col_index:
                    continue
                    
                col_name = "LD25"
                if k[0]=='big' and k[1]=='100': col_name = "HD100"
                elif k[0]=='small': col_name = "HD25"

                if col_name not in active_cols:
                    continue
                col = active_cols.index(col_name)
                    
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
                
                norm = int(k[1]) - 1
                y_vals = np.array(dict_dk.get(k)) / norm
                
                raw_ci = None
                if data_std.get(dk) is not None:
                    raw_ci = data_std.get(dk).get(k)
                    
                if raw_ci is None or len(raw_ci) != len(y_vals):
                    ci_vals = np.zeros_like(y_vals)
                else:
                    # il CI e' salvato in numero di ID: va normalizzato come la media
                    ci_vals = np.array(raw_ci) / norm
                    
                x_vals = np.arange(len(y_vals))
                if dk == 'P.0':
                    for r_idx in range(nrows):
                        ax[r_idx][col].plot(x_vals, y_vals, color=c_val, lw=6)
                        self._fill_ci(ax[r_idx][col], x_vals, np.maximum(0, y_vals - ci_vals), np.minimum(1.0, y_vals + ci_vals), color=c_val)
                else:
                    row = col_index.get(k[2])
                    if row is not None:
                        ax[row][col].plot(x_vals, y_vals, color=c_val, lw=6)
                        self._fill_ci(ax[row][col], x_vals, np.maximum(0, y_vals - ci_vals), np.minimum(1.0, y_vals + ci_vals), color=c_val)
                
        for x in range(nrows):
            for y in range(ncols):
                ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                
        for y in range(ncols):
            ax[nrows-1][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
            ax[nrows-1][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
            
        for idx, col_val in enumerate(active_cols):
            axt=ax[0][idx].twiny()
            axt.tick_params(labeltop=False, labelbottom=False)
            axt.set_xlabel(f"{col_val}")
            
        last_col = ncols - 1
        ays = []
        for idx in range(nrows):
            ayt = ax[idx][last_col].twinx()
            ayt.tick_params(labelright=False)
            ays.append(ayt)
            
        for idx, row_val in enumerate(rows):
            ays[idx].set_ylabel(rf"$T_m = {row_val}\, s$",rotation=270,labelpad=30)

        for x in range(nrows):
            ax[x][0].set_ylabel(r"$M$")
            
        for y in range(ncols):
            ax[nrows-1][y].set_xlabel(r"$T$")
            
        for x in range(nrows):
            for y in range(ncols):
                ax[x][y].grid(True,ls=':')
                ax[x][y].set_xlim(0,900)
                ax[x][y].set_ylim(-0.03,1.03)

        fig.tight_layout()
        handler_map = None

        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        if handles_r:
            fig.legend(handles_l+handles_r, l_list+r_list, bbox_to_anchor=(0.96, 0.01), ncols=7, loc='upper right',framealpha=0.7,borderaxespad=0, handler_map=handler_map)
            
        fig_path = self.base+"/msgs_data/images/messages.pdf"
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

###################################################
    def plot_active(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        pids = ["P.0", "P.1.0", "P.1.1", "O.0.0", "O.2.0", "O.1.1", "O.1.0"]
        states_dict = {pid: {} for pid in pids}
        times_dict = {pid: {} for pid in pids}
        # CI 95% per chiave: (Q_lo, Q_hi, T_lo, T_hi), letti da print_borders e plot_compressed_table
        self.active_ci = {pid: {} for pid in pids}
        def put(pid, key, vals, times_median, ci_entry):
            states_dict[pid][key] = vals
            times_dict[pid][key] = times_median
            self.active_ci[pid][key] = ci_entry
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
                                                    # CI 95%: Q da mean +/- ci per tick, tempi dal CI della mediana sulle run
                                                    vals_lo, vals_hi, t_lo, t_hi = [], [], [], []
                                                    for gt in ground_T:
                                                        tmp, tmp_tmed = [], []
                                                        tmp_lo, tmp_hi, tmp_tlo, tmp_thi = [], [], [], []
                                                        for thr in threshlds:
                                                            s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h,m_b_s))
                                                            t_data = times[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h,m_b_s))
                                                            if s_data != None:
                                                                if m_t not in o_k: o_k.append(m_t)
                                                                q_mean = np.asarray(s_data[0], dtype=float)
                                                                q_ci = np.asarray(s_data[1], dtype=float)
                                                                if q_ci.shape != q_mean.shape: q_ci = np.zeros_like(q_mean)
                                                                tmp.append(round(np.median(q_mean),2))
                                                                tmp_lo.append(round(np.median(q_mean - q_ci),2))
                                                                tmp_hi.append(round(np.median(q_mean + q_ci),2))
                                                                tmp_tmed.append(round(np.median(t_data[0]),2))
                                                                tlo, thi = self._median_ci(t_data[0])
                                                                tmp_tlo.append(tlo); tmp_thi.append(thi)
                                                        vals.append(tmp); times_median.append(tmp_tmed)
                                                        vals_lo.append(tmp_lo); vals_hi.append(tmp_hi)
                                                        t_lo.append(tmp_tlo); t_hi.append(tmp_thi)
                                                    vals, times_median = np.array(vals), np.array(times_median)
                                                    ci_entry = (np.array(vals_lo), np.array(vals_hi), np.array(t_lo), np.array(t_hi))
                                                    if len(vals[0]) == 0:
                                                        continue
                                                    if self._is_p11(a, n_a, m_b_s) and int(c)==0 and m_t in o_k and int(m_t) > 0:
                                                        put("P.1.1", (a_s,n_a,m_t,m_b_s), vals, times_median, ci_entry)
                                                    elif a.strip().lower() == 'p' and int(c)==0 and m_t in o_k and int(m_t) > 0:
                                                        put("P.1.0", (a_s,n_a,m_t,m_b_s), vals, times_median, ci_entry)
                                                    if a=='P' and int(c)==0 and m_t in o_k and int(m_t) == 0:
                                                        put("P.0", (a_s,n_a,"60",m_b_s), vals, times_median, ci_entry)
                                                    if a=='O' and m_t in o_k:
                                                        if int(c)==0:
                                                            put("O.0.0", (a_s,n_a,m_t,m_b_s), vals, times_median, ci_entry)
                                                        elif int(c)==2:
                                                            put("O.2.0", (a_s,n_a,m_t,m_b_s), vals, times_median, ci_entry)
                                                        elif int(m_h)==1:
                                                            put("O.1.1", (a_s,n_a,m_t,m_b_s), vals, times_median, ci_entry)
                                                        else:
                                                            put("O.1.0", (a_s,n_a,m_t,m_b_s), vals, times_median, ci_entry)
        tmp = []
        for x in o_k:
            if int(x)!=0:
                tmp.append(x)
        o_k=tmp
        return path,ground_T,threshlds,states_dict,times_dict,o_k,[arena,agents]

###################################################
    def print_borders(self, path, _type, t_type, ground_T, threshlds, data_in, times_in, keys, more_k, exclude_protocols=None, exclude_rows=None, exclude_cols=None):
        if exclude_protocols is None: exclude_protocols = self.plot_config.get("plots", {}).get("exclude_protocols", [])
        if exclude_rows is None: exclude_rows = self.plot_config.get("plots", {}).get("exclude_tm", [])
        if exclude_cols is None: exclude_cols = self.plot_config.get("plots", {}).get("exclude_cols", [])
        
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        po_k = [k for k in keys if str(k) not in exclude_rows]
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = sorted(set(o_k))
        o_k = self._plot_tm_values(o_k)
        if not o_k:
            return
        nrows = len(o_k)
        arena = more_k[0]
        
        low_bound           = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label="Q=0.2")
        high_bound          = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label="Q=0.8")
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        handles_c   = [high_bound,low_bound]
        handles_r = []
        l_list_r = []
        handles_l = []
        l_list_l = []
                
        for pid in protocols_order:
            if pid in exclude_protocols or not self._protocol_enabled(pid):
                continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='s', linestyle='None', markeredgewidth=0, markersize=16))
            l_list_r.append(protocol.get("label", pid) if protocol else pid)
                
        active_cols = [c for c in ["LD25", "HD25", "HD100"] if c not in exclude_cols]
        ncols = len(active_cols)
        if ncols == 0: return

        fig, ax     = plt.subplots(nrows=nrows, ncols=ncols,figsize=(8.6*ncols,8*nrows), sharex=False, squeeze=False)
        tfig, tax   = plt.subplots(nrows=nrows, ncols=ncols,figsize=(8*ncols,7*nrows), sharex=False, squeeze=False)
        
        attributes_row_col = np.zeros((nrows,ncols))

        for a in arena:
            agents_list = ["25"] if a=="smallA" else more_k[1]
            for ag in agents_list:
                col_name = "HD25" if a=="smallA" else ("HD100" if int(ag)==100 else "LD25")
                if col_name not in active_cols:
                    continue
                col = active_cols.index(col_name)
                
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
                            if dk in exclude_protocols or not self._protocol_enabled(dk):
                                continue
                            
                            x_plot = np.array(threshlds)
                            if np.max(x_plot) > 1.0: x_plot = x_plot / np.max(x_plot)
                            
                            search_tm = "60" if dk == 'P.0' else str(o_k[k])
                            d_series = data_in.get(dk).get((a,ag,search_tm, m_b_s))
                            t_series = times_in.get(dk).get((a,ag,search_tm, m_b_s))
                            if d_series is not None:
                                vals_v2, vals_v8, times_v, sel = self._isolines(d_series, t_series, ground_T, threshlds)
                            else:
                                # nessun dato: linee vuote, ma il pannello riceve comunque gli attributi
                                vals_v2 = vals_v8 = times_v = np.full(len(threshlds), np.nan)
                                sel = [None] * len(threshlds)
                            vals_v2, vals_v8 = np.around(vals_v2, 3), np.around(vals_v8, 3)
                            ci_entry = getattr(self, "active_ci", {}).get(dk, {}).get((a,ag,search_tm, m_b_s))

                            if m_b_s == list(raw_mbs)[0]:
                                ax[k][col].plot(np.arange(0.5, 1.01, 0.01), np.arange(0.5, 1.01, 0.01), color='black', lw=2, ls=':')
                                
                            c_val = protocol_colors.get(dk, "gray")
                            if (dk == "P.1.1" or dk.startswith("P.1.1")) and m_b_s != "" and N_mbs > 0:
                                idx_mbs = sorted_valid_mbs.index(float(m_b_s))
                                ratio = max(0.0, min(1.0, (idx_mbs + 1) / N_mbs))
                                h_c, l_c, s_c = colorsys.rgb_to_hls(*colors.to_rgb(c_val))
                                c_val = colorsys.hls_to_rgb(h_c, max(l_c, min(0.85, l_c + ((1.0-ratio) * 0.4))), s_c * (1.0 - ((1.0-ratio) * 0.3)))

                            ax[k][col].plot(x_plot, vals_v2, color=c_val, lw=6, ls='--')
                            ax[k][col].plot(x_plot, vals_v8, color=c_val, lw=6, ls='-')
                            tax[k][col].plot(x_plot, times_v, color=c_val, lw=6)
                            if ci_entry is not None:
                                v2_lo, v2_hi, v8_lo, v8_hi, t_lo, t_hi = self._isoline_bands(ci_entry, sel, ground_T, threshlds)
                                self._fill_ci(ax[k][col], x_plot, v2_lo, v2_hi, color=c_val)
                                self._fill_ci(ax[k][col], x_plot, v8_lo, v8_hi, color=c_val)
                                self._fill_ci(tax[k][col], x_plot, t_lo, t_hi, color=c_val)

                            if attributes_row_col[k][col] == 0:
                                attributes_row_col[k][col] = 1
                                self._borders_attributes(ax, tax, col, k, o_k, nrows, ncols, col_name)

        fig.tight_layout()
        tfig.tight_layout()
                
        fig.legend(handles_c+handles_r, ["Q=0.8", "Q=0.2"]+l_list_r, bbox_to_anchor=(0.96, 0), ncols=4, loc='upper right', framealpha=0.7, borderaxespad=0)
        tfig.legend(handles_l+handles_r, l_list_l+l_list_r, bbox_to_anchor=(0.96, 0), ncols=6, loc='upper right', framealpha=0.7, borderaxespad=0)
        
        fig.savefig(path+_type+"_activation.pdf", bbox_inches='tight')
        tfig.savefig(path+t_type+"_time.pdf", bbox_inches='tight')
        plt.close(fig); plt.close(tfig)

###################################################
    def _borders_attributes(self, ax, tax, col, k, o_k, nrows, ncols, col_name):
            from matplotlib.ticker import FixedLocator
    
            for a_curr in [ax[k][col], tax[k][col]]:
                a_curr.set_xlim(0.5, 1.0)
                a_curr.tick_params(axis='both', which='major')
    
            ax[k][col].set_ylim(0.5, 1.0)
            if col_name == "LD25": tax[k][col].set_ylim(0, 201)
            elif col_name == "HD25": tax[k][col].set_ylim(0, 51)
            elif col_name == "HD100": tax[k][col].set_ylim(0, 101)
    
            if col == 0:
                ax[k][col].set_ylabel(r"$G$")
                tax[k][col].set_ylabel(r"$T_c$")
                ax[k][col].yaxis.set_tick_params(labelleft=True)
            else:
                ax[k][col].yaxis.set_tick_params(labelleft=False)
            tax[k][col].yaxis.set_tick_params(labelleft=True)
    
            ticks_pos = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
            
            if k == nrows - 1:
                for a_curr in [ax[k][col], tax[k][col]]:
                    a_curr.xaxis.set_major_locator(FixedLocator(ticks_pos))
                    a_curr.set_xticklabels([f"{x:.1f}" for x in ticks_pos])
                    a_curr.set_xlabel(r"$\tau$")
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
                axt.set_xlabel(col_name, labelpad=15)
                taxt.set_xlabel(col_name, labelpad=15)

            if col == ncols - 1:
                for a_curr in [ax[k][col], tax[k][col]]:
                    a_right = a_curr.twinx()
                    a_right.set_yticks([])
                    a_right.set_ylabel(rf"$T_m = {int(o_k[k])}\, s$", rotation=270, labelpad=35)

            ax[k][col].grid(True, which='major', ls=':', alpha=0.6)
            tax[k][col].grid(True, which='major', ls=':', alpha=0.6)

###################################################
    def print_chronometric_function(self, tot_times_in, exclude_protocols=None, exclude_rows=None, exclude_cols=None):
        if exclude_protocols is None: exclude_protocols = self.plot_config.get("plots", {}).get("exclude_protocols", [])
        if exclude_rows is None: exclude_rows = self.plot_config.get("plots", {}).get("exclude_tm", [])
        if exclude_cols is None: exclude_cols = self.plot_config.get("plots", {}).get("exclude_cols", [])
        target_gts = ['0.8']
        raw_rows = set()
        for times_dict in tot_times_in:
            for k in times_dict.keys():
                msg_time = k[9]
                try:
                    if int(msg_time) > 0: raw_rows.add(int(msg_time))
                except Exception:
                    pass
        rows = sorted(list(raw_rows))
        rows = [r for r in rows if str(r) not in exclude_rows]
        rows = self._plot_tm_values(rows)
        if not rows: 
            return
        nrows = len(rows)
        active_cols = [c for c in ["LD25", "HD25", "HD100"] if c not in exclude_cols]
        ncols = len(active_cols)
        if ncols == 0: 
            return
        fig, ax = plt.subplots(nrows=nrows, ncols=ncols, figsize=(8.6 * ncols, 8 * nrows), sharex=False, squeeze=False)
        cNorm = colors.Normalize(vmin=0, vmax=5)
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        protocol_colors = {p.get("id"): self._protocol_color(p, scalarMap) for p in self.protocols}
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        
        gt_handles = [
            mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label="GT=0.8"),
            mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label="GT=0.5")
        ]
        
        handles_r, l_list_r = [], []
        for pid in protocols_order:
            if pid in exclude_protocols or not self._protocol_enabled(pid): continue
            protocol = self.protocols_by_id.get(pid)
            handles_r.append(mlines.Line2D([], [], color=protocol_colors.get(pid, "black"), marker='s', linestyle='None', markeredgewidth=0, markersize=16))
            l_list_r.append(protocol.get("label", pid) if protocol else pid)
        parsed_data = {r: {c: {pid: {gt: {} for gt in target_gts} for pid in protocols_order} for c in active_cols} for r in rows}
        
        for times_dict in tot_times_in:
            for k, v in times_dict.items():
                algo, arena, n_runs, exp_time, comm, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops = k[:11]
                max_buff_size = k[11] if len(k) > 11 else ""
                gt_str = str(gt)
                if gt_str not in target_gts: 
                    continue
                tau = float(thrlds)
                durations = v[0]
                if not durations: 
                    continue
                alg_lower = str(algo).strip().lower()
                if alg_lower == 'ps':
                    variant_key = 'P.1.1'
                elif alg_lower == 'p':
                    if int(msg_time) == 0: variant_key = 'P.0'
                    elif self._is_p11(algo, n_agents, max_buff_size): variant_key = 'P.1.1'
                    else: variant_key = 'P.1.0'
                else:
                    variant_key = f"{algo}.{int(comm)}.{int(msg_hops)}"
                if variant_key not in protocols_order or variant_key in exclude_protocols or not self._protocol_enabled(variant_key):
                    continue
                arena_val = str(arena).strip().replace('A', '')
                ag_val_str = str(n_agents).strip()
                col_name = "LD25"
                if arena_val == 'big' and ag_val_str == '100': col_name = "HD100"
                elif arena_val == 'small': col_name = "HD25"
                if col_name not in active_cols: 
                    continue
                if variant_key == 'P.0':
                    valid_rows = rows
                else:
                    if int(msg_time) not in rows: continue
                    valid_rows = [int(msg_time)]
                # P.1.1: una curva per ogni max_buff_size
                data_key = (variant_key, int(float(max_buff_size))) if variant_key == 'P.1.1' else variant_key
                for r in valid_rows:
                    gt_dict = parsed_data[r][col_name].setdefault(data_key, {g: {} for g in target_gts})
                    if tau not in gt_dict[gt_str]:
                        gt_dict[gt_str][tau] = []
                    gt_dict[gt_str][tau].extend(durations)
        kmf = KaplanMeierFitter()
        from matplotlib.ticker import FixedLocator, MaxNLocator
        for r_idx, r_val in enumerate(rows):
            for c_idx, c_val in enumerate(active_cols):
                curr_ax = ax[r_idx][c_idx]
                curve_keys = []
                for pid in protocols_order:
                    if pid in exclude_protocols or not self._protocol_enabled(pid): continue
                    if pid == 'P.1.1':
                        sub_keys = sorted([dk for dk in parsed_data[r_val][c_val] if isinstance(dk, tuple)], key=lambda dk: dk[1])
                        for m_idx, dk in enumerate(sub_keys):
                            curve_keys.append((dk, self._shade_color(protocol_colors.get(pid, "black"), (m_idx + 1) / len(sub_keys))))
                    else:
                        curve_keys.append((pid, protocol_colors.get(pid, "black")))
                for data_key, c_color in curve_keys:
                    for gt_val in target_gts:
                        tau_dict = parsed_data[r_val][c_val][data_key][gt_val]
                        taus = sorted(list(tau_dict.keys()))
                        fitted_times, valid_taus = [], []
                        ci_lo, ci_hi = [], []
                        for tau in taus:
                            durs = tau_dict[tau]
                            if len(durs) > 0: 
                                observed = [d <= 900 for d in durs]
                                censored_count = len(durs) - sum(observed)
                                if censored_count <= 0.25 * len(durs):
                                    try:
                                        kmf.fit(durs, event_observed=observed)
                                        fit_t = kmf.median_survival_time_
                                        if not np.isinf(fit_t) and not np.isnan(fit_t):
                                            fitted_times.append(fit_t)
                                        else:
                                            fitted_times.append(np.nan)
                                        # CI 95% della mediana di Kaplan-Meier (limite infinito -> non disegnato)
                                        med_ci = median_survival_times(kmf.confidence_interval_).values[0]
                                        ci_lo.append(med_ci[0] if np.isfinite(med_ci[0]) else np.nan)
                                        ci_hi.append(med_ci[1] if np.isfinite(med_ci[1]) else np.nan)
                                    except Exception:
                                        fitted_times.append(np.nan)
                                        ci_lo.append(np.nan); ci_hi.append(np.nan)
                                else:
                                    fitted_times.append(np.nan)
                                    ci_lo.append(np.nan); ci_hi.append(np.nan)
                                    
                                valid_taus.append(tau)
                        
                        if valid_taus:
                            ls = '-' if gt_val == '0.8' else '--'
                            curr_ax.plot(valid_taus, fitted_times, color=c_color, lw=6, ls=ls)
                            self._fill_ci(curr_ax, valid_taus, np.array(ci_lo, dtype=float), np.array(ci_hi, dtype=float), color=c_color)
                curr_ax.set_xlim(0.5, 1.0)
                curr_ax.tick_params(axis='both', which='major')
                if c_idx == 0:
                    curr_ax.set_ylabel(r"$T_c$")
                curr_ax.yaxis.set_tick_params(labelleft=True)
                ticks_pos = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
                curr_ax.xaxis.set_major_locator(FixedLocator(ticks_pos))
                if r_idx == nrows - 1:
                    curr_ax.set_xticklabels([f"{x:.1f}" for x in ticks_pos])
                    curr_ax.set_xlabel(r"$\tau$")
                else:
                    curr_ax.set_xticklabels([])
                if r_idx == 0:
                    axt = curr_ax.twiny()
                    axt.set_xlim(0.5, 1.0)
                    axt.set_xticks([])
                    axt.set_xlabel(c_val, labelpad=15)
                if c_idx == ncols - 1:
                    a_right = curr_ax.twinx()
                    a_right.set_yticks([])
                    a_right.set_ylabel(rf"$T_m = {r_val}\, s$", rotation=270, labelpad=35)
                curr_ax.grid(True, which='major', ls=':', alpha=0.6)
        for c_idx in range(ncols):
            y_max = float('-inf')
            for r_idx in range(nrows):
                if ax[r_idx][c_idx].has_data():
                    _, top = ax[r_idx][c_idx].get_ylim()
                    y_max = max(y_max, top)
            if y_max == float('-inf') or np.isnan(y_max):
                y_max = 900  # Fallback for completely empty columns
            locator = MaxNLocator(nbins=5)
            col_ticks = locator.tick_values(0, y_max)
            col_ticks = [t for t in col_ticks if t >= 0]
            for r_idx in range(nrows):
                curr_ax = ax[r_idx][c_idx]
                curr_ax.set_ylim(0, col_ticks[-1])
                curr_ax.set_yticks(col_ticks)
        fig.tight_layout()
        fig.legend(handles_r, l_list_r, bbox_to_anchor=(0.96, 0), ncols=6, loc='upper right', framealpha=0.7, borderaxespad=0)
        path = self.base + "/proc_data/images/"
        if not os.path.exists(path):
            os.makedirs(path)
        fig.savefig(os.path.join(path, "chronometric_function.pdf"), bbox_inches='tight')
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
        for dk_key, dicts in dk_tot_msgs.items():
            if dk_key == "P.1.1" or dk_key.startswith("P.1.1"):
                for k in dicts.keys():
                    ag_val = int(k[1])
                    if ag_val not in mbs_per_agent: mbs_per_agent[ag_val] = set()
                    if len(k) > 3 and k[3] != "": mbs_per_agent[ag_val].add(float(k[3]))
        mbs_sorted_map = {ag: sorted(list(mbs_per_agent[ag]), reverse=True) for ag in mbs_per_agent}

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
                col_idx = 2 if num_agents == 100 else 1 if str(key[0]).startswith("small") and num_agents == 25 else 0
                
                c_val = base_color
                if (dk == "P.1.1" or dk.startswith("P.1.1")) and len(key) > 3 and key[3] != "":
                    val_mbs = float(key[3])
                    mbs_list = mbs_sorted_map.get(num_agents, [])
                    if mbs_list:
                        diffs = [abs(val_mbs - x) for x in mbs_list]
                        if min(diffs) < 1e-3:
                            m_idx = diffs.index(min(diffs))
                            cmap_k = plt.get_cmap('cool_r')
                            k_color_ts = [0.25, 0.5, 0.75]
                            c_t = k_color_ts[m_idx] if m_idx < len(k_color_ts) else 0.72
                            c_val = cmap_k(c_t)

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
                            ins = ax[0][col_idx].inset_axes([0.52, 0.03, 0.45, 0.45])
                            ins.set_xlim(0, 901); ins.set_ylim(-0.01, 1.01)
                            ins.tick_params(labelbottom=False, labelleft=False)
                            ins.grid(True, ls=':', color='silver')
                            
                            ins.plot([5 / (num_agents - 1) for _ in range(901)], color="black", ls='-.', lw=3)
                            
                            inset_axes_dict[(0, col_idx)] = ins
                        target_ax = inset_axes_dict[(0, col_idx)]

                    y_vals = np.array(msg_series) / (num_agents - 1)
                    ci_vals = np.array(dk_stds_dict.get(dk).get(key)) / (num_agents - 1)
                    x_vals = np.arange(len(y_vals))

                    target_ax.plot(x_vals, y_vals, color=c_val, lw=6, alpha=0.75)
                    self._fill_ci(target_ax, x_vals, np.maximum(0, y_vals - ci_vals), np.minimum(1.0, y_vals + ci_vals), color=c_val)

                if min_buf_plotted[col_idx] == 0:
                    min_buf_plotted[col_idx] = 1
                    ax[0][col_idx].plot([5 / (num_agents - 1) for _ in range(901)], color="black", ls='-.', lw=3)

            for key, state_series in tot_states.items():
                current_tm = int(key[2])
                if not (current_tm in combined_tm or is_p0): continue
                
                num_agents = int(key[1])
                col_idx = 2 if num_agents == 100 else 1 if str(key[0]).startswith("small") and num_agents == 25 else 0
                time_series = tot_times.get(key)
                
                v2, v8, vt, sel = self._isolines(state_series, time_series, ground_T, threshlds)
                if np.any(~np.isnan(vt)): max_time = max(max_time, float(np.nanmax(vt)))
                ci_entry = getattr(self, "active_ci", {}).get(dk, {}).get(key)
                bands = {}
                if ci_entry is not None:
                    v2_lo, v2_hi, v8_lo, v8_hi, t_lo, t_hi = self._isoline_bands(ci_entry, sel, ground_T, threshlds)
                    bands = {'v2': (v2_lo, v2_hi), 'v8': (v8_lo, v8_hi), 'vt': (t_lo, t_hi)}

                c_val = base_color
                if (dk == "P.1.1" or dk.startswith("P.1.1")) and len(key) > 3 and key[3] != "":
                    val_mbs = float(key[3])
                    mbs_list = mbs_sorted_map.get(num_agents, [])
                    if mbs_list:
                        diffs = [abs(val_mbs - x) for x in mbs_list]
                        if min(diffs) < 1e-3:
                            m_idx = diffs.index(min(diffs))
                            cmap_k = plt.get_cmap('cool_r')
                            k_color_ts = [0.25, 0.5, 0.75]
                            c_t = k_color_ts[m_idx] if m_idx < len(k_color_ts) else 0.72
                            c_val = cmap_k(c_t)

                destinations = []
                if is_p0: destinations.extend(["main", "inset"])
                elif current_tm in tm_set: destinations.append("main")
                elif current_tm in insert_tm_set: destinations.append("inset")

                for target_type in destinations:
                    for r_idx, name, data_to_plot in [(2, 'vt', vt), (1, 'v2', v2), (1, 'v8', v8)]:
                        if target_type == "main":
                            curr_ax = ax[r_idx][col_idx]
                        else:
                            if (r_idx, col_idx) not in inset_axes_dict:
                                if r_idx == 1:
                                    best_box = [1.0 - 0.48 - 0.03, 0.03, 0.48, 0.48]
                                elif r_idx == 2:
                                    best_box = [1.0 - 0.48 - 0.03, 1.0 - 0.48 - 0.03, 0.48, 0.48]
                                else:
                                    best_box = self.find_emptiest_inset_position(ax[r_idx][col_idx], width=0.48, height=0.48)
                                
                                ins = ax[r_idx][col_idx].inset_axes(best_box)
                                ins.grid(True, ls=':', color='silver')
                                if r_idx == 1: ins.set_ylim(0.5, 1); ins.plot(ref_x, ref_x, color='black', lw=2, ls=':')
                                inset_axes_dict[(r_idx, col_idx)] = ins
                            curr_ax = inset_axes_dict[(r_idx, col_idx)]
                        
                        ls = '--' if name == 'v2' else '-'
                        curr_ax.plot(threshlds, data_to_plot, color=c_val, lw=6, ls=ls, alpha=0.75)
                        if name in bands:
                            self._fill_ci(curr_ax, threshlds, bands[name][0], bands[name][1], color=c_val)
                
                if mid_act_plotted[col_idx] == 0:
                    mid_act_plotted[col_idx] = 1
                    ax[1][col_idx].plot(ref_x, ref_x, color='black', lw=3, ls=':')
        self._finalize_compressed_plot(fig, ax, path, protocol_colors, threshlds, max_time, use_gradient, main_tm_list, insert_tm_list, inset_axes_dict)
        
###################################################
    def _finalize_compressed_plot(self, fig, ax, path, protocol_colors, tau_ticks, max_time, use_gradient, main_tm_list, insert_tm_list, inset_axes_dict=None):
        
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
                elif i == 1:
                    curr.set_xlim(0.5, 1); curr.set_ylim(0.5, 1)
                    curr.xaxis.set_major_locator(MultipleLocator(0.1))
                    curr.xaxis.set_major_formatter(FormatStrFormatter('%.1f'))
                    curr.set_xticklabels([])
                elif i == 2:
                    curr.set_xlim(0.5, 1); curr.set_ylim(0, 201)
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
                        labelleft=False if i<2 else True, labelright=False
                    )
                    ins_ax.set_xlim(curr.get_xlim())
                    ins_ax.set_ylim(curr.get_ylim()) if i<2 else ins_ax.set_ylim(0,101)

        ax[0][0].set_ylabel(r"$M$"); ax[1][0].set_ylabel(r"$G$"); ax[2][0].set_ylabel(r"$T_c$")
        
        legend_elements = []
        handler_map = {}
        
        cmap_k = plt.get_cmap('cool_r')
        k_color_ts = [0.25, 0.5, 0.75]
        k_labels = [r"K_1", r"K_2", r"K_3"]

        for p in self.protocols:
            p_id = p.get("id")
            if self._protocol_enabled(p_id):
                if p_id == "P.1.1":
                    base_lbl = p.get("label", p_id)
                    for m_idx in range(3):
                        c_t = k_color_ts[m_idx]
                        lbl_k = k_labels[m_idx]
                        if "^{K}" in base_lbl: lbl = base_lbl.replace("^{K}", rf"^{{{lbl_k}}}")
                        elif "^K" in base_lbl: lbl = base_lbl.replace("^K", rf"^{{{lbl_k}}}")
                        else: lbl = rf"{base_lbl} (${lbl_k}$)"
                        legend_elements.append(Line2D([0], [0], color=cmap_k(c_t), marker='s', linestyle='None', markersize=16, label=lbl))
                else:
                    legend_elements.append(Line2D([0], [0], color=protocol_colors[p_id], marker='s', linestyle='None', markersize=16, label=p.get("label", p_id)))

        fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0), ncol=7, frameon=True, edgecolor='0.8')
        fig.savefig(os.path.join(path, "compressed_summary.pdf"), bbox_inches='tight', dpi=300)
        plt.close(fig)

###################################################
    def find_emptiest_inset_position(self, ax, width=0.35, height=0.35, margin=0.03, grid_bins=15):
        """
        Calculates the emptiest quadrant in the given axis to place an inset.
        Evaluates the top-left, top-right, bottom-left, and bottom-right corners.
        Fully compatible with lines, boxplots (patches), and scatter points (collections).
        
        Uses a 2D histogram to evaluate spatial coverage rather than raw point counts.
        Many overlapping points will only occupy a single grid bin, whereas scattered 
        points will occupy many bins, making them a heavier penalty.
        """
        import numpy as np
        
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
                            # Create interpolated points along the line to ensure coverage
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
            
            # Isolate points that fall into the current candidate box
            in_box = (x_ax >= x0) & (x_ax <= x0 + w) & (y_ax >= y0) & (y_ax <= y0 + h)
            box_x = x_ax[in_box]
            box_y = y_ax[in_box]
            
            if len(box_x) == 0:
                counts[key] = 0
            else:
                # Create a 2D histogram of the box to calculate spatial coverage.
                # 'bins=15' splits the box into a 15x15 grid.
                H, _, _ = np.histogram2d(box_x, box_y, bins=grid_bins, range=[[x0, x0 + w], [y0, y0 + h]])
                
                # Count how many grid cells have > 0 points in them
                counts[key] = np.sum(H > 0)
            
        best_position_key = min(counts, key=counts.get)
        
        return candidates[best_position_key]
    
###################################################
    def process_and_plot_radar_grid(self, raw_data_grid, rows, active_cols):
        """
        Normalises the raw radar metrics and plots a grid of radars (rows = Tm, cols = scenarios).
        - M is reported on its absolute scale (already a fraction in [0, 1]).
        - A, Tc, Er, Tr (Er and Tr already log-transformed) are min-max normalised within each
          scenario (column), using all enabled protocols and all the Tm rows shown.
        - Tc, Er, Tr are inverted, so that lower values lie closer to the outer edge.
        - A missing value is treated as the worst one; values are mapped to [0.15, 1.0]
          so that the worst value remains visible.
        """
        # Format: (Name, higher_is_better, is_absolute)
        metrics_config = [
            ('M', True, True),
            ('Acc', True, False),
            ('Tc', False, False),
            ('Er', False, False),
            ('Tr', False, False)
        ]
        labels = ['M', 'A', r'$\bar{T}_c$', r'$\bar{E}_r$', r'$\bar{T}_r$']

        def _valid(v):
            return v is not None and not np.isnan(v)

        # 1. Min/max per column over all enabled protocols and all the rows shown
        col_min_max = {col: {m: {'min': float('inf'), 'max': float('-inf')} for m, _, _ in metrics_config} for col in active_cols}
        for tm in rows:
            for col in active_cols:
                for pid, d in raw_data_grid.get(tm, {}).get(col, {}).items():
                    if not self._protocol_enabled(pid): continue
                    for m, _, is_absolute in metrics_config:
                        v = d.get(m)
                        if is_absolute or not _valid(v): continue
                        col_min_max[col][m]['min'] = min(col_min_max[col][m]['min'], v)
                        col_min_max[col][m]['max'] = max(col_min_max[col][m]['max'], v)

        # 2. Normalise using column bounds
        norm_data_grid = {tm: {col: {} for col in active_cols} for tm in rows}
        for tm in rows:
            for col in active_cols:
                for pid, d in raw_data_grid.get(tm, {}).get(col, {}).items():
                    if not self._protocol_enabled(pid): continue
                    norm_vals = []
                    for m, higher_is_better, is_absolute in metrics_config:
                        v = d.get(m)
                        if not _valid(v):
                            norm_val = 0.0
                        elif is_absolute:
                            norm_val = max(0.0, min(1.0, v))
                            if not higher_is_better: norm_val = 1.0 - norm_val
                        else:
                            min_v = col_min_max[col][m]['min']
                            max_v = col_min_max[col][m]['max']
                            if max_v == min_v:
                                norm_val = 1.0
                            else:
                                norm_val = max(0.0, min(1.0, (v - min_v) / (max_v - min_v)))
                                if not higher_is_better: norm_val = 1.0 - norm_val
                        # Scale shift from [0.0, 1.0] to [0.15, 1.0] to keep the worst value visible
                        norm_vals.append(0.15 + (0.85 * norm_val))
                    norm_data_grid[tm][col][pid] = norm_vals

        self.print_radar_grid(norm_data_grid, labels, rows, active_cols)

    ###################################################
    def print_radar_grid(self, norm_data_grid, metrics_labels, rows, active_cols):
        num_vars = len(metrics_labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]
        
        nrows = len(rows)
        ncols = len(active_cols)
        if nrows == 0 or ncols == 0:
            return
            
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(8*ncols, 8*nrows), subplot_kw=dict(polar=True))
        
        if nrows == 1 and ncols == 1:
            axes = np.array([[axes]])
        elif nrows == 1:
            axes = axes[np.newaxis, :]
        elif ncols == 1:
            axes = axes[:, np.newaxis]
            
        cNorm = colors.Normalize(vmin=0, vmax=5)
        scalarMap = cm.ScalarMappable(norm=cNorm, cmap=plt.get_cmap('viridis'))
        
        for i, tm in enumerate(rows):
            for j, col in enumerate(active_cols):
                ax = axes[i][j]
                
                ax.set_theta_offset(np.pi / 2)
                ax.set_theta_direction(-1)
                
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(metrics_labels)
                # allontana le etichette delle metriche dal bordo del radar
                ax.tick_params(axis='x', pad=15)
                ax.set_ylim(0, 1.05)
                ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
                ax.set_yticklabels([]) 
                
                ax.grid(True, ls=':', color='silver', lw=1.5)
                
                if i == 0:
                    ax.set_title(col, size=28, pad=40)
                
                dataset = norm_data_grid.get(tm, {}).get(col, {})
                # P.1.1: una curva per ogni max_buff_size ("P.1.1|<mbs>"), sfumata come nei plot dei bordi
                p11_keys = sorted([pid for pid in dataset if str(pid).startswith("P.1.1|")], key=lambda pid: int(pid.split('|')[1]))
                for pid, values in dataset.items():
                    if not self._protocol_enabled(pid):
                        continue
                    if len(values) != num_vars:
                        continue
                        
                    protocol = self.protocols_by_id.get(str(pid).split('|')[0], {})
                    c_val = self._protocol_color(protocol, scalarMap)
                    if pid in p11_keys:
                        c_val = self._shade_color(c_val, (p11_keys.index(pid) + 1) / len(p11_keys))
                    
                    # Chiusura del loop per evitare linee spezzate
                    plot_values = values + values[:1]
                    
                    # Aggiunti i marker sui vertici per renderli chiari anche nei casi critici
                    ax.plot(angles, plot_values, color=c_val, linewidth=6, linestyle='solid')
                    
        for i, tm in enumerate(rows):
            ax_right = axes[i][-1]
            ax_right.text(1.1, 0.5, rf"$T_m = {tm}\, s$", transform=ax_right.transAxes, 
                          rotation=270, ha='center', va='center')
                          
        legend_elements = []
        protocols_order = [p.get("id") for p in self.protocols if p.get("id")]
        for pid in protocols_order:
            if not self._protocol_enabled(pid): continue
            protocol = self.protocols_by_id.get(pid, {})
            c_val = self._protocol_color(protocol, scalarMap)
            label = protocol.get("label", pid)
            legend_elements.append(Line2D([0], [0], color=c_val, marker='s', linestyle='None', markersize=16, label=label))
            
        fig.legend(handles=legend_elements, loc='lower center', ncol=min(7, len(legend_elements)), 
                   bbox_to_anchor=(0.58, 0.02 if nrows > 1 else -0.1), framealpha=0.9, borderaxespad=0)
        
        fig.tight_layout()
        fig.subplots_adjust(right=0.88, bottom=0.08 if nrows > 1 else 0.15)
        
        out_dir = os.path.join(self.base, "radar_data", "images")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        fig_path = os.path.join(out_dir, "radar_grid_synthesis.pdf")
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)