import os, csv, logging, re
import numpy as np
from pathlib import Path
import warnings

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
        data_int = data.astype(np.int32, copy=False)
        valid_mask = (data_int >= 0) & (data_int < n_options)
        
        # Agenti validi totali per run e step (n_runs, n_steps)
        valid_agents = valid_mask.sum(axis=1).astype(np.float64)
        valid_agents_safe = np.where(valid_agents > 0.0, valid_agents, 1.0)

        # Contiamo gli agenti per singola opzione
        state_values = np.arange(n_options, dtype=np.int32)[:, None, None]
        opt_mask = (data_int[:, None, :, :] == state_values[None, :, :, :]) & valid_mask[:, None, :, :]
        # Shape: (n_runs, n_options, n_steps)
        counts_per_opt = opt_mask.sum(axis=2).astype(np.float64) 

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
        final_stds = []

        # option_id = 0 logico (Maggioranza), option_id = 1 logico (Resto)
        for group in [winner_cohesion, others_cohesion]:
            final_means.append(np.around(np.mean(group, axis=0), decimals=3).tolist())
            final_stds.append(np.around(np.std(group, axis=0), decimals=3).tolist())

        return final_means, final_stds

##########################################################################################################
    def compute_accuracy(self, data: np.ndarray, n_options: int, eta: float, window: int = 100):
        n_runs, n_agents, n_steps = data.shape
        crit_eta = (n_options - 1) / n_options
        
        # Ignora se eta è uguale al valore critico
        if abs(eta - crit_eta) < 1e-5:
            return None
            
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
            
            # Soglia per dichiarare il successo (es. 90% degli agenti validi)
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
            
            if is_success:
                success_count += 1

        # Restituisce la percentuale di run che hanno avuto successo
        accuracy_percentage = (success_count / n_runs) * 100.0
        return accuracy_percentage

##########################################################################################################
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
                    idx = np.argmax(counts)
                    found_step = t
                    for tk in range(t,n_steps):
                        k_states = run_data[:, tk].astype(np.int32)
                        k_valid_states = k_states[(k_states >= 0) & (k_states < n_options)]
                        k_counts = np.bincount(k_valid_states, minlength=n_options)
                        if k_counts[idx] < threshold:
                            found_step = n_steps + 1
                            break

                    if found_step != n_steps + 1: break
            
            exit_times.append(found_step)

        exit_times_arr = np.array(exit_times)
        return exit_times_arr

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

        # Salvo l'Accuracy come valore percentuale globale (se eta != crit_eta)
        accuracy_val = self.compute_accuracy(state_m, n_options, eta)
        if accuracy_val is not None:
            # Salviamo il singolo scalare in data_in. Impostiamo "-" in data_std.
            self.dump_resume_csv(
                data_in=accuracy_val, data_std="-", exp_length=exp_length, communication=communication,
                adaptive_com=adaptive_com, comm_type=comm_type, id_aware=id_aware, priority_k=priority_k,
                n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops, variation_time=variation_time,
                spat_corr=spat_corr, n_options=n_options, eta=eta, eta_stop=eta_stop,
                init_distr=init_distr, function=function, vote_msg=vote_msg, ctrl_par=ctrl_par,
                num_runs=num_runs, arenaS=arenaS, data_type="accuracy" )

        # Salvo le metriche globali (indipendenti dall'opzione)
        time_mean = self.compute_exit_time(state_m, n_options)
        self.dump_resume_csv(
            data_in=time_mean, data_std="-", exp_length=exp_length, communication=communication,
            adaptive_com=adaptive_com, comm_type=comm_type, id_aware=id_aware, priority_k=priority_k,
            n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops, variation_time=variation_time,
            spat_corr=spat_corr, n_options=n_options, eta=eta, eta_stop=eta_stop,
            init_distr=init_distr, function=function, vote_msg=vote_msg, ctrl_par=ctrl_par,
            num_runs=num_runs, arenaS=arenaS, data_type="time" )
        
        msgs_mean, msgs_std = self.compute_overall_average_through_run(msgs_m)
        self.dump_resume_csv(
            data_in=msgs_mean, data_std=msgs_std, exp_length=exp_length, communication=communication,
            adaptive_com=adaptive_com, comm_type=comm_type, id_aware=id_aware, priority_k=priority_k,
            n_agents=n_agents, msg_exp_time=msg_exp_time, msg_hops=msg_hops, variation_time=variation_time,
            spat_corr=spat_corr, n_options=n_options, eta=eta, eta_stop=eta_stop,
            init_distr=init_distr, function=function, vote_msg=vote_msg, ctrl_par=ctrl_par,
            num_runs=num_runs, arenaS=arenaS, data_type="msgs" )
        
##########################################################################################################
    def compute_average_metric_through_run(self, metric_data: np.ndarray, state_data: np.ndarray, n_options: int, is_quorum: bool = False):
        if metric_data.ndim != 3 or state_data.ndim != 3:
            raise ValueError("Input expected to be 3D (n_runs, n_agents, steps)")
        
        n_runs, n_agents, n_steps = metric_data.shape
        state_data_int = state_data.astype(np.int32, copy=False)
        valid_mask = (state_data_int >= 0) & (state_data_int < n_options)

        # 1. Contiamo quanti agenti ci sono per ogni ID opzione, per ogni run e step
        # shape: (n_runs, n_options, n_agents, n_steps)
        state_values = np.arange(n_options, dtype=np.int32)[:, None, None]
        opt_mask = (state_data_int[:, None, :, :] == state_values[None, :, :, :]) & valid_mask[:, None, :, :]
        
        # shape: (n_runs, n_options, n_steps)
        counts_per_opt = opt_mask.sum(axis=2).astype(np.float64) 
        
        # 2. Sommiamo la metrica per ogni ID opzione
        metric_sums_per_opt = np.sum(np.where(opt_mask, metric_data[:, None, :, :], 0.0), axis=2)
        metric_sq_sums_per_opt = np.sum(np.where(opt_mask, metric_data[:, None, :, :]**2, 0.0), axis=2)

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

        groups = [
            (np.sum(winner_counts, axis=0), np.sum(winner_sums, axis=0), np.sum(winner_sq_sums, axis=0)),
            (np.sum(others_counts, axis=0), np.sum(others_sums, axis=0), np.sum(others_sq_sums, axis=0))
        ]

        # Totale agenti validi per il sistema (solo se is_quorum)
        total_valid_agents = np.sum(valid_mask, axis=(0, 1)).astype(np.float64)

        final_means = []
        final_stds = []

        for group_counts, group_sums, group_sq_sums in groups:
            if is_quorum:
                # Quorum: diviso SEMPRE per il totale agenti del sistema
                safe_div = np.where(total_valid_agents > 0, total_valid_agents, 1.0)
                mean_opt = group_sums / safe_div
                mean_sq_opt = group_sq_sums / safe_div
            else:
                # Ctrl: diviso per gli agenti in QUEL gruppo (vincitori o restanti)
                safe_div = np.where(group_counts > 0, group_counts, 1.0)
                mean_opt = group_sums / safe_div
                mean_sq_opt = group_sq_sums / safe_div
                
                mean_opt = np.where(group_counts > 0, mean_opt, 0.0)
                mean_sq_opt = np.where(group_counts > 0, mean_sq_opt, 0.0)

            # Varianza aggregata (Pooled Variance)
            variance = mean_sq_opt - (mean_opt**2)
            variance = np.where(variance > 0, variance, 0.0)
            std_opt = np.sqrt(variance)

            final_means.append(np.around(mean_opt, decimals=3).tolist())
            final_stds.append(np.around(std_opt, decimals=3).tolist())

        return final_means, final_stds
    
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
        
        final_mean = np.around(np.mean(norm_avg_per_run, axis=0), decimals=3).tolist()
        final_std = np.around(np.std(norm_avg_per_run, axis=0), decimals=3).tolist()
        return final_mean, final_std
    
##########################################################################################################
    def dump_resume_per_opt_csv(self,data_in,data_std,exp_length:int,communication:int,
                       adaptive_com:int,comm_type:str,id_aware:int,priority_k:int,n_agents:int,msg_exp_time:int,msg_hops:int,variation_time:float,spat_corr:int,n_options:int,
                       eta:float,eta_stop:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float,num_runs:int,arenaS:str,option_id:int,data_type:str):    
        static_fields=["communication","adaptive_com","comm_type","id_aware","priority_k","msg_exp_time","msg_hops","variation_time","eta","eta_stop","init_distr","function","vote_msg","control_par"]
        static_values=[communication,adaptive_com,comm_type,id_aware,priority_k,msg_exp_time,msg_hops,variation_time,eta,eta_stop,init_distr,function,vote_msg,ctrl_par]
        os.makedirs(os.path.abspath("")+f"/proc_data/{data_type}", exist_ok=True)
        output_path = os.path.abspath("")+f"/proc_data/{data_type}/"
        write_header = 0
        name_fields = []
        values = []
        file_name = f"{data_type}_resume_time#{exp_length}_agents#{n_agents}_options#{n_options}_spatcorr#{spat_corr}_runs#{num_runs}_arena#{arenaS}.csv"
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
                       adaptive_com:int,comm_type:str,id_aware:int,priority_k:int,n_agents:int,msg_exp_time:int,msg_hops:int,variation_time:float,spat_corr:int,n_options:int,
                       eta:float,eta_stop:float,init_distr:float,function:str,vote_msg:int,ctrl_par:float,num_runs:int,arenaS:str,data_type:str):    
        static_fields=["communication","adaptive_com","comm_type","id_aware","priority_k","msg_exp_time","msg_hops","variation_time","eta","eta_stop","init_distr","function","vote_msg","control_par"]
        static_values=[communication,adaptive_com,comm_type,id_aware,priority_k,msg_exp_time,msg_hops,variation_time,eta,eta_stop,init_distr,function,vote_msg,ctrl_par]
        os.makedirs(os.path.abspath("")+f"/proc_data/{data_type}", exist_ok=True)
        output_path = os.path.abspath("")+f"/proc_data/{data_type}/"
        write_header = 0
        name_fields = []
        values = []
        file_name = f"{data_type}_resume_time#{exp_length}_agents#{n_agents}_options#{n_options}_spatcorr#{spat_corr}_runs#{num_runs}_arena#{arenaS}.csv"
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