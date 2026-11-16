import os, csv, logging, re, fcntl
import numpy as np
from pathlib import Path
from scipy.stats import t as t_dist

PROC_DIR = "proc_data"
# Settings already in proc_data, one per line: <setting>\t<number of runs>
DONE_LIST = "processed_settings.txt"


def mean_ci95(per_run: np.ndarray):
    """Mean over runs (axis 0) and half-width of its 95% confidence interval (Student t).

    Same method as the Python model (quorum_sensing_Best_of_N/data_extractor.py).
    NaN values (e.g. a group with no agents in that run) are left out step by step;
    the half-width is NaN where fewer than two runs have a value.
    """
    per_run = np.asarray(per_run, dtype=np.float64)
    n = np.sum(~np.isnan(per_run), axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, np.nansum(per_run, axis=0) / np.maximum(n, 1), np.nan)
        dev = np.where(np.isnan(per_run), 0.0, per_run - mean)
        std = np.sqrt(np.sum(dev ** 2, axis=0) / np.maximum(n - 1, 1))
        half = np.where(n >= 2, t_dist.ppf(0.975, np.maximum(n - 1, 1)) * std / np.sqrt(np.maximum(n, 1)), np.nan)
    return mean, half


def _as_list(values: np.ndarray) -> list:
    return [None if np.isnan(v) else round(float(v), 4) for v in values]


def done_settings(proc_dir: str = PROC_DIR) -> dict:
    """{setting: number of runs} of the settings already written to proc_data."""
    path = os.path.join(os.path.abspath(""), proc_dir, DONE_LIST)
    done = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) == 2 and parts[1].isdigit():
                    done[parts[0]] = int(parts[1])
    return done


def mark_done(setting: str, num_runs: int, proc_dir: str = PROC_DIR) -> None:
    output_path = os.path.join(os.path.abspath(""), proc_dir)
    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, DONE_LIST), "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(f"{setting}\t{num_runs}\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)

class Results:
    ticks_per_sec = 10
    setting = ""     # relative path of the raw folder, unique for every tested setting
    hop_count = 0
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    FILE_RE = re.compile(r"agent#(?P<agent>\d+).*?(?:seed|run)#(?P<run>\d+)")

##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem=elem.split('_')
                if selem[0]=="results": self.bases.append(os.path.join(self.base, elem))
            
##########################################################################################################
    def _norm_idx(self, raw_id: int, size: int, name: str) -> int:
        # Accetta sia indici 0-based che 1-based
        if name == "agent": return raw_id
        elif name == "run": return raw_id - 1
        raise ValueError(f"{name} id fuori range: {raw_id} (size={size})")

##########################################################################################################
    @staticmethod
    def _option_counts(state_int: np.ndarray, n_options: int) -> np.ndarray:
        # Agents in each option per run and step: shape (n_runs, n_options, n_steps).
        # Built one option at a time to avoid a (runs, options, agents, steps) temporary.
        n_runs, _, n_steps = state_int.shape
        counts = np.empty((n_runs, n_options, n_steps), dtype=np.float64)
        for o in range(n_options):
            counts[:, o, :] = (state_int == o).sum(axis=1)
        return counts

##########################################################################################################
    def compute_average_cohesion_through_run(self, data: np.ndarray, n_options: int):
        if data.ndim != 3:
            raise ValueError(f"Input atteso 3D (n_runs,n_agents,steps), trovato ndim={data.ndim}")
        
        n_runs, n_agents, n_steps = data.shape
        data_int = data.astype(np.int32, copy=False)
        valid_mask = (data_int >= 0) & (data_int < n_options)
        
        # Agenti validi totali per run e step (n_runs, n_steps)
        valid_agents = valid_mask.sum(axis=1).astype(np.float64)
        valid_agents_safe = np.where(valid_agents > 0.0, valid_agents, 1.0)

        # Contiamo gli agenti per singola opzione, shape: (n_runs, n_options, n_steps)
        counts_per_opt = self._option_counts(data_int, n_options)

        # Correzione Broadcasting: espandiamo il denominatore
        cohesion_per_opt = counts_per_opt / valid_agents_safe[:, None, :]

        # Determiniamo l'indice dell'opzione maggioritaria step-by-step
        winner_idx = np.argmax(counts_per_opt, axis=1) # (n_runs, n_steps)
        r_idx = np.arange(n_runs)[:, None]
        s_idx = np.arange(n_steps)[None, :]

        # Coesione dell'opzione vincitrice
        winner_cohesion = cohesion_per_opt[r_idx, winner_idx, s_idx]

        # Coesione cumulativa di tutte le altre opzioni
        if n_options > 1:
            others_cohesion = np.sum(cohesion_per_opt, axis=1) - winner_cohesion
        else:
            others_cohesion = np.zeros_like(winner_cohesion)

        final_means = []
        final_cis = []

        # option_id = 0 logico (Maggioranza), option_id = 1 logico (Resto)
        # One value per run and step: mean and 95% CI across runs
        for group in [winner_cohesion, others_cohesion]:
            mean, half = mean_ci95(group)
            final_means.append(_as_list(mean))
            final_cis.append(_as_list(half))

        return final_means, final_cis

##########################################################################################################
    def extract_data(self,ticks_per_sec:int,path:str,exp_length:int,variation_time:float,spat_corr:int,communication:int,
                       adaptive_com:int,comm_type:str,id_aware:int,priority_k:int,n_agents:int,msg_exp_time:int,msg_hops:int,n_options:int,
                       eta:float,eta_stop:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float) -> None:
        max_steps = exp_length * ticks_per_sec
        info_vec    = path.split('/')
        arenaS  = ""
        for iv in info_vec:
            if iv.startswith("results_"):
                arenaS = iv.split("_")[-1]
                break

        files = sorted(Path(path).glob("*.tsv"))
        if not files:
            raise ValueError(f"Nessun file .tsv trovato in {path}")
        if len(files) % n_agents != 0:
            raise ValueError(f"Numero file non multiplo di n_agents ({n_agents}) in {path}: {len(files)}")
        num_runs = int(len(files) / n_agents)
        expected_files = num_runs * n_agents
        if len(files) != expected_files:
            raise ValueError(f"Attesi {expected_files} file, trovati {len(files)}")

        shape = (num_runs, n_agents, max_steps)

        # 4 matrici [run][agent][time]
        state_m = np.full(shape, 0, dtype=np.int16)
        msgs_m = np.full(shape, 0, dtype=np.int32)
        quorum_m = np.full(shape, 0.0, dtype=np.float32)
        ctrl_m = np.full(shape, 0.0, dtype=np.float32)

        loaded = np.zeros((num_runs, n_agents), dtype=bool)
        agents_loaded_per_run = np.zeros(num_runs, dtype=np.int16)

        for fp in files:
            m = self.FILE_RE.search(fp.stem)
            if not m:
                raise ValueError(f"Nome file non valido: {fp.name}")

            ag = self._norm_idx(int(m.group("agent")), n_agents, "agent")
            rn = self._norm_idx(int(m.group("run")), num_runs, "run")

            if loaded[rn, ag]:
                raise ValueError(f"Duplicato run/agent: run={rn}, agent={ag}, file={fp.name}")

            sampled = np.loadtxt(fp, delimiter="\t", ndmin=2)
            if sampled.shape[1] != 4:
                raise ValueError(f"{fp.name}: colonne trovate={sampled.shape[1]}, attese=4")
            n_rows = sampled.shape[0]

            # Padding iniziale automatico se le righe sono meno
            start = max_steps - n_rows
            state_m[rn, ag, start:] = sampled[:, 0].astype(np.int16)
            msgs_m[rn, ag, start:] = sampled[:, 1].astype(np.int32)
            quorum_m[rn, ag, start:] = sampled[:, 2].astype(np.float32)
            ctrl_m[rn, ag, start:] = sampled[:, 3].astype(np.float32)

            loaded[rn, ag] = True
            agents_loaded_per_run[rn] += 1

        incomplete_runs = np.where(agents_loaded_per_run != n_agents)[0]
        if incomplete_runs.size:
            raise ValueError(f"Run incomplete: {incomplete_runs.tolist()}")
        
        invalid_state_mask = (state_m < 0) | (state_m >= n_options)
        if np.any(invalid_state_mask):
            invalid_values = np.unique(state_m[invalid_state_mask]).tolist()
            non_temp_invalid = [v for v in invalid_values if v != 255]
            if non_temp_invalid:
                raise ValueError(f"Stati non validi trovati (attesi 0..{n_options-1}): {non_temp_invalid}")
            temp_count = int(np.count_nonzero(state_m == 255))
            print(f"[WARN] Ignoro {temp_count} campioni con stato temporaneo 255")

        # Metriche dipendenti dall'opzione (0=Dominante, 1=Altre)
        cohesion_mean, cohesion_std = self.compute_average_cohesion_through_run(state_m, n_options)
        quorum_mean, quorum_std = self.compute_average_metric_through_run(quorum_m, state_m, n_options, is_quorum=True)
        ctrl_mean, ctrl_std = self.compute_average_metric_through_run(ctrl_m, state_m, n_options, is_quorum=False)
        
        for state_id in range(len(cohesion_mean)):
            self.dump_resume_per_opt_csv(
                data_in=cohesion_mean[state_id], data_std=cohesion_std[state_id], exp_length=exp_length,
                communication=communication, adaptive_com=adaptive_com, comm_type=comm_type, id_aware=id_aware,
                priority_k=priority_k, n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops,
                variation_time=variation_time, spat_corr=spat_corr, n_options=n_options, eta=eta,
                eta_stop=eta_stop, init_distr=init_distr, function=function, vote_msg=vote_msg,
                ctrl_par=ctrl_par, num_runs=num_runs, arenaS=arenaS, option_id=state_id,
                data_type="cohesion"
            )

            self.dump_resume_per_opt_csv(
                data_in=quorum_mean[state_id], data_std=quorum_std[state_id],
                exp_length=exp_length, communication=communication, adaptive_com=adaptive_com,
                comm_type=comm_type, id_aware=id_aware, priority_k=priority_k,
                n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops,
                variation_time=variation_time, spat_corr=spat_corr, n_options=n_options,
                eta=eta, eta_stop=eta_stop, init_distr=init_distr, function=function,
                vote_msg=vote_msg, ctrl_par=ctrl_par, num_runs=num_runs, arenaS=arenaS,
                option_id=state_id, data_type="quorum"
            )

            self.dump_resume_per_opt_csv(
                data_in=ctrl_mean[state_id], data_std=ctrl_std[state_id],
                exp_length=exp_length, communication=communication, adaptive_com=adaptive_com,
                comm_type=comm_type, id_aware=id_aware, priority_k=priority_k,
                n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops,
                variation_time=variation_time, spat_corr=spat_corr, n_options=n_options,
                eta=eta, eta_stop=eta_stop, init_distr=init_distr, function=function,
                vote_msg=vote_msg, ctrl_par=ctrl_par, num_runs=num_runs, arenaS=arenaS,
                option_id=state_id, data_type="ctrl"
            )
        
        msgs_mean, msgs_std = self.compute_overall_average_through_run(msgs_m)
        self.dump_resume_csv(
            data_in=msgs_mean, data_std=msgs_std, exp_length=exp_length, communication=communication,
            adaptive_com=adaptive_com, comm_type=comm_type, id_aware=id_aware, priority_k=priority_k,
            n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops, variation_time=variation_time,
            spat_corr=spat_corr, n_options=n_options, eta=eta, eta_stop=eta_stop,
            init_distr=init_distr, function=function, vote_msg=vote_msg, ctrl_par=ctrl_par,
            num_runs=num_runs, arenaS=arenaS, data_type="msgs" )
        if self.setting:
            mark_done(self.setting, num_runs)
        
##########################################################################################################
    def compute_average_metric_through_run(self, metric_data: np.ndarray, state_data: np.ndarray, n_options: int, is_quorum: bool = False):
        if metric_data.ndim != 3 or state_data.ndim != 3:
            raise ValueError("Input expected to be 3D (n_runs, n_agents, steps)")
        
        n_runs, n_agents, n_steps = metric_data.shape
        state_data_int = state_data.astype(np.int32, copy=False)

        # 1-2. Agents, metric sum and squared-metric sum per option: shape (n_runs, n_options, n_steps).
        # One option at a time, to avoid (runs, options, agents, steps) temporaries.
        counts_per_opt = self._option_counts(state_data_int, n_options)
        metric_sq = metric_data**2
        metric_sums_per_opt = np.empty((n_runs, n_options, n_steps), dtype=metric_data.dtype)
        metric_sq_sums_per_opt = np.empty((n_runs, n_options, n_steps), dtype=metric_sq.dtype)
        for o in range(n_options):
            opt_mask = state_data_int == o
            metric_sums_per_opt[:, o, :] = np.sum(np.where(opt_mask, metric_data, 0.0), axis=1)
            metric_sq_sums_per_opt[:, o, :] = np.sum(np.where(opt_mask, metric_sq, 0.0), axis=1)

        # 3. Determiniamo dinamicamente l'indice dell'opzione vincitrice step by step
        winner_idx = np.argmax(counts_per_opt, axis=1)
        r_idx = np.arange(n_runs)[:, None]
        s_idx = np.arange(n_steps)[None, :]

        # --- VINCITORE (option_id = 0 logico) ---
        winner_counts = counts_per_opt[r_idx, winner_idx, s_idx]
        winner_sums = metric_sums_per_opt[r_idx, winner_idx, s_idx]
        winner_sq_sums = metric_sq_sums_per_opt[r_idx, winner_idx, s_idx]

        # --- ALTRE OPZIONI (option_id = 1 logico) ---
        if n_options > 1:
            others_counts = np.sum(counts_per_opt, axis=1) - winner_counts
            others_sums = np.sum(metric_sums_per_opt, axis=1) - winner_sums
            others_sq_sums = np.sum(metric_sq_sums_per_opt, axis=1) - winner_sq_sums
        else:
            others_counts = np.zeros_like(winner_counts)
            others_sums = np.zeros_like(winner_sums)
            others_sq_sums = np.zeros_like(winner_sq_sums)

        final_means = []
        final_cis = []
        # Mean over the agents of the group inside each run, then mean and 95% CI across runs.
        # A run with no agent in the group has no value at that step (NaN, left out).
        for group_counts, group_sums in [(winner_counts, winner_sums), (others_counts, others_sums)]:
            with np.errstate(invalid="ignore", divide="ignore"):
                per_run = np.where(group_counts > 0, group_sums / np.where(group_counts > 0, group_counts, 1.0), np.nan)
            mean, half = mean_ci95(per_run)
            final_means.append(_as_list(mean))
            final_cis.append(_as_list(half))

        return final_means, final_cis
    
##########################################################################################################
    def compute_overall_average_through_run(self, data: np.ndarray):
        if data.ndim != 3:
            raise ValueError(f"Input expected 3D (n_runs, n_agents, steps), found ndim={data.ndim}")
        n_runs, n_agents, n_steps = data.shape
        max_msgs = max(1.0, float(n_agents - 1))
        
        sum_per_run = np.sum(data, axis=1) # shape: (n_runs, n_steps)
        avg_per_run = sum_per_run / n_agents
        
        # Normalizziamo per numero massimo di messaggi
        norm_avg_per_run = avg_per_run / max_msgs
        
        mean, half = mean_ci95(norm_avg_per_run)
        return _as_list(mean), _as_list(half)
    
##########################################################################################################
    def dump_resume_per_opt_csv(self, data_in, data_std, option_id: int, **kwargs):
        self.dump_resume_csv(data_in, data_std, option_id=option_id, **kwargs)

##########################################################################################################
    def dump_resume_csv(self,data_in,data_std,exp_length:int,communication:int,
                       adaptive_com:int,comm_type:str,id_aware:int,priority_k:int,n_agents:int,msg_exp_time:int,msg_hops:int,variation_time:float,spat_corr:int,n_options:int,
                       eta:float,eta_stop:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float,num_runs:int,arenaS:str,data_type:str,option_id=None):
        # data_std is the half-width of the 95% CI across runs of data_in (column 'ci95').
        # Every setting is a column, so the rows of different settings never mix after merging.
        name_fields=["communication","hop_count","adaptive_com","comm_type","id_aware","priority_k","msg_exp_time","msg_hops","variation_time","spat_corr","n_options","n_agents","exp_length","arena","eta","eta_stop","init_distr","function","vote_msg","control_par","n_runs","setting"]
        values=[communication,self.hop_count,adaptive_com,comm_type,id_aware,priority_k,msg_exp_time,msg_hops,variation_time,spat_corr,n_options,n_agents,exp_length,arenaS,eta,eta_stop,init_distr,function,vote_msg,ctrl_par,num_runs,self.setting]
        name_fields.append("option_id")
        values.append("" if option_id is None else option_id)  # empty for metrics not split by option (msgs)
        name_fields += ["data", "ci95"]
        values += [data_in, data_std]

        output_path = os.path.join(os.path.abspath(""), PROC_DIR, data_type)
        os.makedirs(output_path, exist_ok=True)
        file_name = f"{data_type}_resume_time#{exp_length}_agents#{n_agents}_options#{n_options}_spatcorr#{spat_corr}_runs#{num_runs}_arena#{arenaS}.csv"
        file_path = os.path.join(output_path, file_name)
        # Several processes append to the same file: lock it, and write the header only into an empty file
        with open(file_path, mode='a', newline='\n') as fw:
            fcntl.flock(fw, fcntl.LOCK_EX)
            try:
                fw.seek(0, os.SEEK_END)
                fwriter = csv.writer(fw, delimiter='\t')
                if fw.tell() == 0:
                    fwriter.writerow(name_fields)
                fwriter.writerow(values)
                fw.flush()
            finally:
                fcntl.flock(fw, fcntl.LOCK_UN)
