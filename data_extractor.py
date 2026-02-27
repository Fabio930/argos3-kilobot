import os, csv, logging, re
import numpy as np
from pathlib import Path

class Results:
    min_buff_dim = 5
    ticks_per_sec = 10
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
    def compute_average_cohesion_through_run(self, data: np.ndarray, n_options: int):

        if data.ndim != 3:
            raise ValueError(f"Input atteso 3D (n_runs,n_agents,steps), trovato ndim={data.ndim}")
        
        n_runs, n_agents, n_steps = data.shape
        n_states = n_options

        data_int = data.astype(np.int32, copy=False)
        valid_mask = (data_int >= 0) & (data_int < n_states)
        valid_agents = valid_mask.sum(axis=1).astype(np.float64)  # (n_runs, n_steps)
        valid_agents = np.where(valid_agents > 0.0, valid_agents, np.nan)

        state_values = np.arange(n_states, dtype=np.int32)[:, None, None]
        counts = (
            (data_int[:, None, :, :] == state_values[None, :, :, :]) &
            valid_mask[:, None, :, :]
        ).sum(axis=2).astype(np.float64)

        counts_norm = counts / valid_agents[:, None, :]
        counts_norm = np.nan_to_num(counts_norm, nan=0.0)
        winner_counts = np.max(counts_norm, axis=1) # (n_runs, n_steps)
        
        if n_options > 1:
            other_counts = (np.sum(counts_norm, axis=1) - winner_counts) / (n_options - 1)
        else:
            other_counts = np.zeros_like(winner_counts)

        final_means = []
        final_stds = []

        # option_id = 0 -> coesione massima; option_id = 1 -> media delle altre opzioni
        for group in [winner_counts, other_counts]:
            final_means.append(np.around(group.mean(axis=0), decimals=6).tolist())
            final_stds.append(np.around(group.std(axis=0), decimals=6).tolist())

        return final_means, final_stds

##########################################################################################################
    def compute_accuracy(self, data: np.ndarray, n_options: int, eta: float, window: int = 100):
        n_runs, n_agents, n_steps = data.shape
        crit_eta = (n_options - 1) / n_options
        actual_window = min(window, n_steps)
        last_data = data[:, :, -actual_window:] # shape: (runs, agents, window)
        
        success_count = 0

        for r in range(n_runs):
            counts_per_step = []
            valid_per_step = []
            for t in range(actual_window):
                states = last_data[r, :, t].astype(np.int32)
                valid_states = states[(states >= 0) & (states < n_options)]
                valid_per_step.append(valid_states.size)
                counts_per_step.append(np.bincount(valid_states, minlength=n_options))

            counts_per_step = np.asarray(counts_per_step, dtype=np.float64)
            valid_per_step = np.asarray(valid_per_step, dtype=np.float64)
            
            avg_counts = np.mean(counts_per_step, axis=0)
            avg_valid_agents = float(np.mean(valid_per_step))
            threshold = 0.9 * avg_valid_agents
            
            is_success = False
            if avg_valid_agents <= 0:
                is_success = False
            elif eta < crit_eta:
                if avg_counts[0] >= threshold:
                    is_success = True
            elif eta > crit_eta:
                if n_options > 1 and np.any(avg_counts[1:] >= threshold):
                    is_success = True
            else:
                if np.any(avg_counts[:] >= threshold):
                    is_success = True
            
            if is_success:
                success_count += 1

        return (success_count / n_runs) * 100

    def compute_exit_time(self, data: np.ndarray, n_options: int):
        n_runs, n_agents, n_steps = data.shape
        exit_times = []

        for r in range(n_runs):
            run_data = data[r] 
            found_step = n_steps + 1
            
            for t in range(n_steps):
                states = run_data[:, t].astype(np.int32)
                valid_states = states[(states >= 0) & (states < n_options)]
                if valid_states.size == 0:
                    continue
                counts = np.bincount(valid_states, minlength=n_options)
                threshold = 0.9 * valid_states.size
                if np.any(counts[:] >= threshold):
                    found_step = t
                    break
            
            exit_times.append(found_step)

        exit_times_arr = np.array(exit_times)
        return exit_times_arr

##########################################################################################################
    def extract_data(self,ticks_per_sec:int,path:str,exp_length:int,communication:int,
                       adaptive_com:int,n_agents:int,msg_exp_time:int,msg_hops:int,n_options:int,
                       eta:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float) -> None:
        max_steps = exp_length * ticks_per_sec
        num_runs = int(len(os.listdir(path))/n_agents)
        info_vec    = path.split('/')
        arenaS  = ""
        for iv in info_vec:
            if "results_loop" in iv:
                arenaS      = iv.split('_')[-1][:-1]
                break
        shape = (num_runs, n_agents, max_steps)

        # 4 matrici [run][agent][time]
        state_m = np.full(shape, 0, dtype=np.int16)
        msgs_m = np.full(shape, 0, dtype=np.int32)
        quorum_m = np.full(shape, 0.0, dtype=np.float32)
        ctrl_m = np.full(shape, 0.0, dtype=np.float32)

        files = sorted(Path(path).glob("*.tsv"))
        expected_files = num_runs * n_agents
        if len(files) != expected_files:
            raise ValueError(f"Attesi {expected_files} file, trovati {len(files)}")

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

            sampled = np.loadtxt(fp, delimiter="\t", ndmin=2)  # attese 4 colonne numeriche
            if sampled.shape[1] != 4:
                raise ValueError(f"{fp.name}: colonne trovate={sampled.shape[1]}, attese=4")
            n_rows = sampled.shape[0]

            # Check 1: troppe righe
            if n_rows > max_steps:
                raise ValueError(f"{fp.name}: righe={n_rows} > max_steps={max_steps}")

            # Check 2: meno righe -> padding iniziale (valori default già impostati)
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

        cohesion_mean, cohesion_std = self.compute_average_cohesion_through_run(state_m, n_options)

        for state_id in range(len(cohesion_mean)):
            self.dump_resume_per_opt_csv(
                data_in=cohesion_mean[state_id],
                data_std=cohesion_std[state_id],
                exp_length=exp_length,
                communication=communication,
                adaptive_com=adaptive_com,
                n_agents=n_agents,
                msg_exp_time=msg_exp_time,
                msg_hops=msg_hops,
                n_options=n_options,
                eta=eta,
                init_distr=init_distr,
                function=function,
                vote_msg=vote_msg,
                ctrl_par=ctrl_par,
                num_runs=num_runs,
                arenaS=arenaS,
                option_id=state_id,
                data_type="cohesion"
            )

        success = self.compute_accuracy(state_m, n_options,eta)
        self.dump_resume_csv(
            data_in=success,
            data_std="-",
            exp_length=exp_length,
            communication=communication,
            adaptive_com=adaptive_com,
            n_agents=n_agents,
            msg_exp_time=msg_exp_time,
            msg_hops=msg_hops,
            n_options=n_options,
            eta=eta,
            init_distr=init_distr,
            function=function,
            vote_msg=vote_msg,
            ctrl_par=ctrl_par,
            num_runs=num_runs,
            arenaS=arenaS,
            data_type="accuracy"
        )

        time_mean = self.compute_exit_time(state_m, n_options)

        self.dump_resume_csv(
            data_in=time_mean,
            data_std="-",
            exp_length=exp_length,
            communication=communication,
            adaptive_com=adaptive_com,
            n_agents=n_agents,
            msg_exp_time=msg_exp_time,
            msg_hops=msg_hops,
            n_options=n_options,
            eta=eta,
            init_distr=init_distr,
            function=function,
            vote_msg=vote_msg,
            ctrl_par=ctrl_par,
            num_runs=num_runs,
            arenaS=arenaS,
            data_type="time"
        )

##########################################################################################################
    def dump_resume_per_opt_csv(self,data_in,data_std,exp_length:int,communication:int,
                       adaptive_com:int,n_agents:int,msg_exp_time:int,msg_hops:int,n_options:int,
                       eta:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float,num_runs:int,arenaS:str,option_id:int,data_type:str):    
        static_fields=["communication","adaptive_com","msg_exp_time","msg_hops","eta","init_distr","function","vote_msg","control_par"]
        static_values=[communication,adaptive_com,msg_exp_time,msg_hops,eta,init_distr,function,vote_msg,ctrl_par]
        os.makedirs(os.path.abspath("")+f"/proc_data/{data_type}", exist_ok=True)
        output_path = os.path.abspath("")+f"/proc_data/{data_type}/"
        write_header = 0
        name_fields = []
        values = []
        file_name = f"{data_type}_resume_time#{exp_length}_agents#{n_agents}_options#{n_options}_runs#{num_runs}_arena#{arenaS}.csv"
        if not os.path.exists(output_path+file_name):
            write_header = 1
        for i in range(len(static_fields)):
            name_fields.append(static_fields[i])
            values.append(static_values[i])
        name_fields.append("option_id")
        values.append(option_id)
        name_fields.append("data")
        name_fields.append("std")
        values.append(data_in)
        values.append(data_std)
        fw = open(output_path+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()


##########################################################################################################
    def dump_resume_csv(self,data_in,data_std,exp_length:int,communication:int,
                       adaptive_com:int,n_agents:int,msg_exp_time:int,msg_hops:int,n_options:int,
                       eta:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float,num_runs:int,arenaS:str,data_type:str):    
        static_fields=["communication","adaptive_com","msg_exp_time","msg_hops","eta","init_distr","function","vote_msg","control_par"]
        static_values=[communication,adaptive_com,msg_exp_time,msg_hops,eta,init_distr,function,vote_msg,ctrl_par]
        os.makedirs(os.path.abspath("")+f"/proc_data/{data_type}", exist_ok=True)
        output_path = os.path.abspath("")+f"/proc_data/{data_type}/"
        write_header = 0
        name_fields = []
        values = []
        file_name = f"{data_type}_resume_time#{exp_length}_agents#{n_agents}_options#{n_options}_runs#{num_runs}_arena#{arenaS}.csv"
        if not os.path.exists(output_path+file_name):
            write_header = 1
        for i in range(len(static_fields)):
            name_fields.append(static_fields[i])
            values.append(static_values[i])
        name_fields.append("data")
        name_fields.append("std")
        values.append(data_in)
        values.append(data_std)
        fw = open(output_path+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()
