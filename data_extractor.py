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
    def compute_average_selection_through_run(self, data: np.ndarray, n_options: int):
        """
        data shape: (n_runs, n_agents, steps)
        Ritorna due liste:
        - medie per stato nel tempo (len = n_options + 1)
        - std per stato nel tempo (len = n_options + 1)
        """
        if data.ndim != 3:
            raise ValueError(f"Input atteso 3D (n_runs,n_agents,steps), trovato ndim={data.ndim}")
        if n_options < 1:
            raise ValueError(f"n_options deve essere >= 1, trovato {n_options}")

        _, n_agents, _ = data.shape
        n_states = n_options + 1  # include lo stato 0 (nessuna scelta)

        data_int = data.astype(np.int32, copy=False)
        if np.any(data_int < 0) or np.any(data_int > n_options):
            raise ValueError(f"Valori stato fuori range [0,{n_options}]")

        # Conteggio agenti per stato ad ogni step, per ogni run
        # shape: (n_runs, n_states, steps)
        state_values = np.arange(n_states, dtype=np.int32)[:, None, None]
        counts = (data_int[:, None, :, :] == state_values[None, :, :, :]).sum(axis=2).astype(np.float64)

        # Normalizzazione sul numero di agenti
        counts_norm = counts / float(n_agents)

        # Andamento medio e std tra run (per ogni stato e step)
        mean_over_runs = counts_norm.mean(axis=0)
        std_over_runs = counts_norm.std(axis=0)

        data_in = [np.around(mean_over_runs[s], decimals=6).tolist() for s in range(n_states)]
        data_std = [np.around(std_over_runs[s], decimals=6).tolist() for s in range(n_states)]
        return data_in, data_std

##########################################################################################################
    def extract_data(self,ticks_per_sec:int,path:str,exp_length:int,communication:int,
                       adaptive_com:int,n_agents:int,msg_exp_time:int,msg_hops:int,n_options:int,
                       eta:float,function:str,vote_msg:int,ctrl_par:float) -> None:
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
        state_mean, state_std = self.compute_average_selection_through_run(state_m, n_options)

        for state_id in range(n_options + 1):
            self.dump_resume_csv(
                data_in=state_mean[state_id],
                data_std=state_std[state_id],
                exp_length=exp_length,
                communication=communication,
                adaptive_com=adaptive_com,
                n_agents=n_agents,
                msg_exp_time=msg_exp_time,
                msg_hops=msg_hops,
                n_options=n_options,
                eta=eta,
                function=function,
                vote_msg=vote_msg,
                ctrl_par=ctrl_par,
                num_runs=num_runs,
                arenaS=arenaS,
                option_id=state_id,
                data_type="state"
            )

##########################################################################################################
    def dump_resume_csv(self,data_in,data_std,exp_length:int,communication:int,
                       adaptive_com:int,n_agents:int,msg_exp_time:int,msg_hops:int,n_options:int,
                       eta:float,function:str,vote_msg:int,ctrl_par:float,num_runs:int,arenaS:str,option_id:int,data_type:str):    
        static_fields=["communication","adaptive_com","msg_exp_time","msg_hops","eta","function","vote_msg","control_par"]
        static_values=[communication,adaptive_com,msg_exp_time,msg_hops,eta,function,vote_msg,ctrl_par]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        file_name = f"{data_type}_resume_time#{exp_length}_agents#{n_agents}_options#{n_options}_runs#{num_runs}_arena#{arenaS}.csv"
        if not os.path.exists(os.path.abspath("")+"/proc_data/"+file_name):
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
        fw = open(os.path.abspath("")+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()
