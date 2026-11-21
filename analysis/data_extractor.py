import os, csv, logging, re, fcntl
import numpy as np
import pandas as pd
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

        # Files of each run; a run is read, reduced to its series and dropped before the next one,
        # so memory holds one run (agents x steps), not all of them
        files_by_run = {}
        for fp in files:
            m = self.FILE_RE.search(fp.stem)
            if not m:
                raise ValueError(f"Nome file non valido: {fp.name}")
            ag = self._norm_idx(int(m.group("agent")), n_agents, "agent")
            rn = self._norm_idx(int(m.group("run")), num_runs, "run")
            if ag in files_by_run.setdefault(rn, {}):
                raise ValueError(f"Duplicato run/agent: run={rn}, agent={ag}, file={fp.name}")
            files_by_run[rn][ag] = fp
        incomplete_runs = [rn for rn in range(num_runs) if len(files_by_run.get(rn, {})) != n_agents]
        if incomplete_runs:
            raise ValueError(f"Run incomplete: {incomplete_runs}")

        # One series per run: (num_runs, max_steps) for every metric and group (0=Dominante, 1=Altre)
        series = {k: np.full((num_runs, max_steps), np.nan) for k in
                  ("cohesion_0", "cohesion_1", "quorum_0", "quorum_1", "ctrl_0", "ctrl_1", "msgs")}
        temp_count = 0
        for rn in range(num_runs):
            state_r = np.zeros((n_agents, max_steps), dtype=np.int16)
            msgs_r = np.zeros((n_agents, max_steps), dtype=np.float64)
            quorum_r = np.zeros((n_agents, max_steps), dtype=np.float64)
            ctrl_r = np.zeros((n_agents, max_steps), dtype=np.float64)
            for ag, fp in files_by_run[rn].items():
                # C parser: same values as np.loadtxt, about 15 times faster on these logs
                sampled = pd.read_csv(fp, sep="\t", header=None, skipinitialspace=True,
                                      dtype=np.float64, engine="c").to_numpy()
                if sampled.shape[1] != 4:
                    raise ValueError(f"{fp.name}: colonne trovate={sampled.shape[1]}, attese=4")
                if sampled.shape[0] > max_steps:
                    raise ValueError(f"{fp.name}: {sampled.shape[0]} righe, attese al massimo {max_steps}")
                # Padding iniziale automatico se le righe sono meno
                start = max_steps - sampled.shape[0]
                state_r[ag, start:] = sampled[:, 0].astype(np.int16)
                msgs_r[ag, start:] = sampled[:, 1]
                quorum_r[ag, start:] = sampled[:, 2].astype(np.float32)
                ctrl_r[ag, start:] = sampled[:, 3].astype(np.float32)
            invalid = (state_r < 0) | (state_r >= n_options)
            if np.any(invalid):
                non_temp_invalid = [v for v in np.unique(state_r[invalid]).tolist() if v != 255]
                if non_temp_invalid:
                    raise ValueError(f"Stati non validi trovati (attesi 0..{n_options-1}): {non_temp_invalid}")
                temp_count += int(np.count_nonzero(state_r == 255))
            for key, values in self.run_series(state_r, msgs_r, quorum_r, ctrl_r, n_options).items():
                series[key][rn] = values
        if temp_count:
            print(f"[WARN] Ignoro {temp_count} campioni con stato temporaneo 255")

        # Mean and 95% CI across runs
        stats_ = {k: mean_ci95(v) for k, v in series.items()}
        def mc(key):
            mean, half = stats_[key]
            return _as_list(mean), _as_list(half)
        cohesion_mean, cohesion_std = zip(mc("cohesion_0"), mc("cohesion_1"))
        quorum_mean, quorum_std = zip(mc("quorum_0"), mc("quorum_1"))
        ctrl_mean, ctrl_std = zip(mc("ctrl_0"), mc("ctrl_1"))
        # The *_std names hold the half-width of the 95% CI (column 'ci95')

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
        
        msgs_mean, msgs_std = mc("msgs")
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
    @staticmethod
    def run_series(state: np.ndarray, msgs: np.ndarray, quorum: np.ndarray, ctrl: np.ndarray, n_options: int) -> dict:
        """Series of one run (inputs: agents x steps).

        cohesion_0 / cohesion_1  fraction of the committed agents on the most chosen option / on the others
        quorum_* / ctrl_*        mean over the agents of that group (NaN at steps where the group is empty)
        msgs                     mean buffer size over all agents, normalised by n_agents - 1
        """
        n_agents, n_steps = state.shape
        state_int = state.astype(np.int32, copy=False)
        counts = np.empty((n_options, n_steps), dtype=np.float64)
        q_sums = np.empty((n_options, n_steps), dtype=np.float64)
        c_sums = np.empty((n_options, n_steps), dtype=np.float64)
        for o in range(n_options):
            mask = state_int == o
            counts[o] = mask.sum(axis=0)
            q_sums[o] = np.where(mask, quorum, 0.0).sum(axis=0)
            c_sums[o] = np.where(mask, ctrl, 0.0).sum(axis=0)
        valid = counts.sum(axis=0)
        valid_safe = np.where(valid > 0, valid, 1.0)
        winner = np.argmax(counts, axis=0)
        steps = np.arange(n_steps)

        out = {}
        win_coh = counts[winner, steps] / valid_safe
        out["cohesion_0"] = win_coh
        out["cohesion_1"] = (counts.sum(axis=0) / valid_safe - win_coh) if n_options > 1 else np.zeros(n_steps)
        for name, sums in (("quorum", q_sums), ("ctrl", c_sums)):
            win_n, win_s = counts[winner, steps], sums[winner, steps]
            oth_n = counts.sum(axis=0) - win_n if n_options > 1 else np.zeros(n_steps)
            oth_s = sums.sum(axis=0) - win_s if n_options > 1 else np.zeros(n_steps)
            with np.errstate(invalid="ignore", divide="ignore"):
                out[f"{name}_0"] = np.where(win_n > 0, win_s / np.where(win_n > 0, win_n, 1.0), np.nan)
                out[f"{name}_1"] = np.where(oth_n > 0, oth_s / np.where(oth_n > 0, oth_n, 1.0), np.nan)
        out["msgs"] = msgs.sum(axis=0) / n_agents / max(1.0, float(n_agents - 1))
        return out

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
