import os, sys
import numpy as np

class Results:
    min_buff_dim = 5
    ticks_per_sec = 10
    x_limit = 100
    limit = 0.8
        
##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem=elem.split('_')
                if selem[0] in ("Oresults", "Presults", "Psresults"):
                    self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    @staticmethod
    def ci95(run_values):
        # CI 95% della media tra le run: run_values ha forma (runs, ticks)
        n = run_values.shape[0]
        if n < 2:
            return np.zeros(run_values.shape[1])
        return 1.96 * (np.std(run_values, axis=0, ddof=1) / np.sqrt(n))

##########################################################################################################
    def _group_run_means(self, data, states):
        """
        Medie per run su tutti gli agenti, sui committed e sugli uncommitted (stato finale).
        data: (runs, agents, ticks). Le somme sugli agenti sono intere; le medie tra run si accumulano
        lungo l'asse 0 nello stesso ordine della versione originale, quindi i valori arrotondati coincidono.
        """
        data = np.asarray(data)
        st = np.asarray(states)
        committed_count = self.count_committed_agents(st)
        n_agents = data.shape[1]
        comm_mask = (st == 1)[:, :, None]
        uncomm_mask = (st == 0)[:, :, None]
        tot_run = data.sum(axis=1, dtype=np.int64) / n_agents
        comm_run = np.where(comm_mask, data, 0).sum(axis=1, dtype=np.int64) / committed_count
        uncomm_run = np.where(uncomm_mask, data, 0).sum(axis=1, dtype=np.int64) / (n_agents - committed_count)
        return tot_run, comm_run, uncomm_run

##########################################################################################################
    def compute_avg_msgs(self,messages,states):
        print("--- Computing avg buffer dimension ---")
        messages = np.asarray(messages)
        runs, n_agents = messages.shape[0], messages.shape[1]
        tot_run, comm_run, uncomm_run = self._group_run_means(messages, states)
        tot_avg = np.round(messages.sum(axis=(0, 1), dtype=np.int64) / (runs * n_agents), 3).tolist()
        comm_avg = np.round(np.add.reduce(comm_run, axis=0) / runs, 3).tolist()
        uncomm_avg = np.round(np.add.reduce(uncomm_run, axis=0) / runs, 3).tolist()
        cis = [np.round(self.ci95(x), 3).tolist() for x in (tot_run, comm_run, uncomm_run)]
        return tot_avg, comm_avg, uncomm_avg, cis

##########################################################################################################
    def _read_log(self, path):
        """
        Legge un file quorum_log (stato, quorum, messaggi, x, y separati da tab) tenendo una riga ogni
        ticks_per_sec. Conversione in blocco; per formati inattesi si usa il parsing riga per riga.
        Restituisce state, quorum, msgs (int) e x (float, -1 se assente).
        """
        with open(path, 'rb') as f:
            lines = f.read().split(b'\n')
        if lines and lines[-1] == b'':
            lines.pop()
        sampled = lines[self.ticks_per_sec - 1 :: self.ticks_per_sec]
        sampled = [l for l in sampled if l.count(b'\t') >= 2]
        if not sampled:
            z = np.zeros(0, dtype=np.int64)
            return z, z, z, np.zeros(0)
        ncols = sampled[0].count(b'\t') + 1
        flat = np.fromstring(b'\t'.join(sampled).replace(b'\t', b' '), dtype=float, sep=' ')
        if flat.size == len(sampled) * ncols and all(l.count(b'\t') == ncols - 1 for l in (sampled[0], sampled[-1])):
            m = flat.reshape(len(sampled), ncols)
            x = m[:, 3] if ncols > 4 else np.full(len(sampled), -1.0)
            if ncols <= 4: print("positional values not found")
            return m[:, 0].astype(np.int64), m[:, 1].astype(np.int64), m[:, 2].astype(np.int64), x
        st, q, ms, x = [], [], [], []
        missing = False
        for line in sampled:
            parts = line.decode().split('\t')
            st.append(int(parts[0])); q.append(int(parts[1])); ms.append(int(parts[2]))
            try:
                x.append(float(parts[3]) if len(parts) > 4 else -1.0)
                missing |= len(parts) <= 4
            except ValueError:
                x.append(-1.0); missing = True
        if missing: print("positional values not found")
        return np.array(st), np.array(q), np.array(ms), np.array(x, dtype=float)

##########################################################################################################
    def extract_k_data(self,base,max_steps,communication,n_agents,threshold,GT,msg_hops,msg_exp_time,k_sampling,sub_path):
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        # (runs, agents, ticks); i tick mancanti in testa valgono 0 (posizioni -1)
        states = np.zeros((num_runs, n_agents, max_steps), dtype=np.int16)
        quorums = np.zeros((num_runs, n_agents, max_steps), dtype=np.int16)
        messages = np.zeros((num_runs, n_agents, max_steps), dtype=np.int32)
        positions = np.full((num_runs, n_agents, max_steps), -1.0)
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem = elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    seed = int(selem[0].split('#')[-1])
                    agent_id = int(selem[0].split('_')[2].split('#')[-1])
                    st, q, ms, x = self._read_log(os.path.join(sub_path, elem))
                    n = len(ms)
                    if n > max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",n)
                        sys.exit(0)
                    off = max_steps - n
                    states[seed-1, agent_id, off:] = st
                    quorums[seed-1, agent_id, off:] = q
                    messages[seed-1, agent_id, off:] = ms
                    positions[seed-1, agent_id, off:] = x
        algo    = ""
        arenaS  = ""
        info_vec    = sub_path.split('/')
        for iv in info_vec:
            if "results_loop" in iv:
                if iv.startswith("Ps"):
                    algo = "Ps"
                else:
                    algo = iv[0]
            elif "ArenaType" in iv:
                arenaS      = iv.split('#')[-1]

        statescpy = states[:, :, -1]
        avg_messages,commit_avg_msgs,uncommit_avg_msgs,msgs_ci = self.compute_avg_msgs(messages,statescpy)
        self.dump_msgs("messages_resume.csv", [arenaS, algo, threshold, GT, communication, n_agents, msg_exp_time, msg_hops, k_sampling, avg_messages, commit_avg_msgs, uncommit_avg_msgs], msgs_ci)
        self.dump_times(algo,0,quorums,base,sub_path,self.min_buff_dim,msg_exp_time,n_agents,self.limit)
        self.dump_quorum(algo,0,quorums,statescpy,base,sub_path,self.min_buff_dim,msg_exp_time)
        # avg_distance = self.compute_frontier_avg_distance(positions,arenaS,GT)
        # self.dump_distance("distance_resume.csv",[arenaS, algo, threshold, GT, communication, n_agents, msg_exp_time, msg_hops, k_sampling, avg_distance])
        del states, quorums, messages, positions, statescpy

##########################################################################################################
    def compute_frontier_avg_distance(self,positions,arena_size,gt):
        front = np.round(float(arena_size.split(';')[0].replace('_','.'))*float(gt),3)
        distances = np.abs(np.asarray(positions, dtype=float) - front)
        return np.round(distances.sum(axis=(0, 1)) / (distances.shape[0] * distances.shape[1]), 3).tolist()

##########################################################################################################
    def dump_distance(self, file_name, data):
        header = ["ArenaSize", "algo", "threshold", "GT", "broadcast", "n_agents", "buff_dim", "msg_hops", "k_sampling", "type", "data"]
        out_dir = os.path.join(os.path.abspath(""), "pos_data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        write_header = not os.path.exists(out_path)
        row = [data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],"tot_average",data[-1]]
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            fw.write("\t".join(map(str, row)) + "\n")

##########################################################################################################
    def dump_msgs(self, file_name, data, cis=None):
        header = ["ArenaSize", "algo", "threshold", "GT", "broadcast", "n_agents", "buff_dim", "msg_hops", "k_sampling", "type", "data", "ci_95"]
        out_dir = os.path.join(os.path.abspath(""), "msgs_data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        write_header = not os.path.exists(out_path)
        cis = cis if cis is not None else ["-", "-", "-"]
        rows = [
            [data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],"tot_average",data[-3],cis[0]],
            [data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],"commit_average",data[-2],cis[1]],
            [data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],"uncommit_average",data[-1],cis[2]],
        ]
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            for row in rows:
                fw.write("\t".join(map(str, row)) + "\n")

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,data_in,data_std,base,path,MINS,MSG_EXP_TIME,n_runs):    
        static_fields=["MinBuffDim"]
        static_values=[MINS]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        tmp_b = base.split('/')
        tmp_p = path.split('/')
        # l'arena si prende dall'elemento ArenaType# del percorso (prima: tmp_p[6], valido solo per una profondita' fissa)
        arena_dir = next((i for i in tmp_p if i.startswith("ArenaType#")), tmp_p[6])
        arena_tag = arena_dir.split('#')[1].replace('_',',')
        if algo == 'O':
            file_name = "Oaverage_resume_r#"+str(n_runs)+"_a#"+arena_tag+".csv"
        elif algo == 'Ps':
            file_name = "Psaverage_resume_r#"+str(n_runs)+"_a#"+arena_tag+".csv"
        else:
            file_name = "Paverage_resume_r#"+str(n_runs)+"_a#"+arena_tag+".csv"
        if not os.path.exists(os.path.abspath("")+"/proc_data/"+file_name):
            write_header = 1
        for i in tmp_p:
            if i not in tmp_b:
                tmp = i.split("#")
                name_fields.append(tmp[0])
                values.append(tmp[1])
        for i in range(len(static_fields)):
            name_fields.append(static_fields[i])
            values.append(static_values[i])
        name_fields.append("type")
        name_fields.append("data")
        name_fields.append("ci_95")
        if indx+bias==-1:
            values.append("times")
        elif indx+bias==0:
            values.append("swarm_state")
        elif indx+bias==1:
            values.append("committed_state")
        elif indx+bias==2:
            values.append("uncommitted_state")
        elif indx+bias==3:
            values.append("broadcast_msg")
        elif indx+bias==4:
            values.append("rebroadcast_msg")
        values.append(data_in)
        values.append(data_std)
        out_path = os.path.abspath("")+"/proc_data/"+file_name
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header == 1:
                fw.write("\t".join(name_fields) + "\n")
            fw.write("\t".join(map(str, values)) + "\n")

##########################################################################################################
    def dump_msg_freq(self,algo,bias,data_in,dMR,BASE,PATH,MSG_EXP_TIME,n_agents):
        for l in range(len(data_in.get(0))):
            multi_run_data = data_in.get(0)[l]
            if multi_run_data is not None:
                flag2 = [-1 for _ in range(len(multi_run_data[0][0]))]
                for i in range(len([multi_run_data[0]])):
                    flag1 = [-1 for _ in range(len(multi_run_data[0][0]))]
                    for j in range(len(multi_run_data)):
                        for z in range(len(multi_run_data[j][i])):
                            if flag1[z]==-1:
                                flag1[z]=float(multi_run_data[j][i][z])
                            else:
                                flag1[z]=flag1[z]+float(multi_run_data[j][i][z])
                    for j in range(len(flag1)):
                        flag1[j]=flag1[j]/len(multi_run_data)
                        if flag2[j]==-1:
                            flag2[j]=flag1[j]
                        else:
                            flag2[j]=flag1[j]+flag2[j]
                for i in range(len(flag2)):
                    flag2[i]=flag2[i]/len(multi_run_data[0])
                self.dump_resume_csv(algo,l,bias,np.round(flag2,2).tolist(),"-",BASE,PATH,"-",MSG_EXP_TIME,dMR)
        
##########################################################################################################
    def count_committed_agents(self,data):
        counts = (np.asarray(data) == 1).sum(axis=1)
        if counts.size and np.any(counts != counts[0]):
            print("ERROR! Number of committed agents change through iterations ---EXIT---")
            exit(1)
        return int(counts[0]) if counts.size else -1

##########################################################################################################
    def dump_quorum(self,algo,bias,q_data,s_data,BASE,PATH,MINS,MSG_EXP_TIME):
        # medie su tutti gli agenti, sui committed e sugli uncommitted, con CI 95% tra le run
        q = np.asarray(q_data)
        runs = q.shape[0]
        tot_run, comm_run, uncomm_run = self._group_run_means(q, s_data)
        for indx, run_vals in ((0, tot_run), (1, comm_run), (2, uncomm_run)):
            mean = np.add.reduce(run_vals, axis=0) / runs
            self.dump_resume_csv(algo,indx,bias,np.round(mean,2).tolist(),np.round(self.ci95(run_vals),3).tolist(),BASE,PATH,MINS,MSG_EXP_TIME,runs)

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,MINS,MSG_EXP_TIME,n_agents,limit):
        q = np.asarray(data_in)
        ticks = q.shape[2]
        reached = q.sum(axis=1) >= limit * q.shape[1]
        # primo tick in cui almeno limit*agenti sono in quorum, ticks se mai
        times = np.where(reached.any(axis=1), reached.argmax(axis=1), ticks)
        self.dump_resume_csv(algo,-1,bias,sorted(times.tolist()),'-',BASE,PATH,MINS,MSG_EXP_TIME,len(q))

