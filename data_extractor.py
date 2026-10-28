import os, math, logging
import numpy as np
class Results:
    thresholds      = {}
    ground_truth    = [.52,.56,.60,.64,.68,.72,.76,.8,.84,.88,.92,.96,1.0]
    min_buff_dim    = 5
    ticks_per_sec   = 10
    limit           = 0.8
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem = elem.split('_')
                if selem and selem[0].lower() in ("oresults", "presults", "psresults"):
                    self.bases.append(os.path.join(self.base, elem))
        for gt in range(len(self.ground_truth)):
            _thresholds=np.arange(50,101,1)
            f_thresholds = []
            for t in range(len(_thresholds)): f_thresholds.append(round(float(_thresholds[t])*.01,2))
            self.thresholds.update({self.ground_truth[gt]:f_thresholds})
            
##########################################################################################################
    def compute_quorum_vars_all(self, m1, states_all):
        """
        Dimensione dei buffer e numero di agenti in stato 1 visti da ogni agente, per tutti i G insieme.
        m1: array (agents, runs, ticks, buf) con -1 come padding in coda.
        states_all: (n_gt, runs, agents). Restituisce dims (runs, agents, ticks) e ones (n_gt, runs, agents, ticks).
        L'istogramma degli ID di ogni buffer non dipende da G: si calcola una volta per run e si moltiplica
        per gli stati di tutti i G (equivale a sommare states[id] sugli elementi validi del buffer).
        """
        agents, runs, ticks, _ = m1.shape
        n_gt = states_all.shape[0]
        dims = np.empty((runs, agents, ticks), dtype=np.int16)
        ones = np.empty((n_gt, runs, agents, ticks), dtype=np.int16)
        cells = agents * ticks
        cell_idx = np.arange(cells, dtype=np.int64)[:, None]
        for i in range(runs):
            rows = m1[:, i].reshape(cells, -1)
            valid = rows != -1
            cnt = valid.sum(axis=1)
            dims[i] = (1 + cnt).reshape(agents, ticks)
            flat = (cell_idx * agents + rows)[valid]
            hist = np.bincount(flat, minlength=cells * agents).reshape(cells, agents).astype(np.float32)
            # (cells, agents) @ (agents, n_gt) -> agenti in stato 1 nel buffer, per ogni G
            # (float32 per usare BLAS: con valori < 2^24 il risultato e' esatto)
            seen = np.rint(hist @ states_all[:, i, :].T.astype(np.float32)).astype(np.int16)
            ones[:, i] = seen.T.reshape(n_gt, agents, ticks) + states_all[:, i, :, None].astype(np.int16)
        return dims, ones

##########################################################################################################
    def compute_quorum_vars_on_ground_truth(self,m1,states,buf_lim,gt,gt_dim,compound=None):
        print(f"--- Processing data {gt}/{gt_dim} ---") if compound==None else print(f"--- Processing data {gt}/{gt_dim} - arena#{compound[0]}_nAgents#{compound[1]}_tm#{compound[2]} ---")
        dims, ones = self.compute_quorum_vars_all(np.asarray(m1), np.asarray(states)[None])
        return dims.astype(int), ones[0].astype(int)

##########################################################################################################
    def compute_quorum(self,m1,m2,threshold,base_mask=None,m1_float=None):
        # base_mask (m1-1 >= min_buff_dim) e m1_float possono essere precalcolati: non dipendono dalla soglia
        m1_arr = np.asarray(m1)
        if base_mask is None: base_mask = (m1_arr - 1 >= self.min_buff_dim)
        if m1_float is None: m1_float = m1_arr.astype(float)
        return (base_mask & (np.asarray(m2, dtype=float) >= threshold * m1_float)).view(np.int8)

##########################################################################################################
    def compute_recovery(self,algo,runs,arenaS,communication,n_agents,buf_dim,msg_hops,gt,thr,quorums,buffers,msg_exp_time,base_mask=None):
        # if gt < thr compute the steps in which the agents have the wrong state "1" and the buffer lenght
        # if gt >= thr compute the steps in which the agents have the wrong state "0" and the buffer lenght
        # Vettorializzato su run e agenti: gli intervalli si trovano con un solo diff sull'asse del tempo.
        q_arr = np.asarray(quorums)
        b_arr = np.asarray(buffers)
        ticks = q_arr.shape[2]
        if base_mask is None: base_mask = (b_arr - 1 >= self.min_buff_dim)
        cond = base_mask & ((q_arr == 1) if gt < thr else (q_arr == 0))
        if not cond.any():
            return
        # inizio intervallo: vero ora e falso al tick prima; fine: vero ora e falso al tick dopo
        starts = cond.copy()
        starts[..., 1:] &= ~cond[..., :-1]
        ends = cond.copy()
        ends[..., :-1] &= ~cond[..., 1:]
        f_s = np.flatnonzero(starts)
        t_s = f_s % ticks
        ra = f_s // ticks
        r_s, a_s = ra // q_arr.shape[1], ra % q_arr.shape[1]
        end_idx = np.flatnonzero(ends) % ticks + 1
        b_start = b_arr[r_s, a_s, t_s].astype(np.int64) - 1
        durations = end_idx - t_s
        events = (end_idx != ticks).astype(np.int64)
        bounds = np.searchsorted(r_s, np.arange(q_arr.shape[0] + 1))
        prefix = [ticks, communication, n_agents, buf_dim, msg_exp_time, msg_hops, gt, thr]
        rows = []
        for i in range(q_arr.shape[0]):
            lo, hi = bounds[i], bounds[i + 1]
            if hi > lo:
                rows.append(prefix + [i + 1, b_start[lo:hi].tolist(), durations[lo:hi].tolist(), events[lo:hi].tolist()])
        self.dump_recovery_raw({'algorithm': algo, 'runs': runs, 'arena': arenaS}, rows)

##########################################################################################################
    def compute_meaningfulMsgs_decidinAgents(self,data,buf_limit):
        data = np.asarray(data)
        n_agents, n_runs, ticks = data.shape[0], data.shape[1], data.shape[2]
        run_msgs_means = np.zeros((n_runs, ticks), dtype=float)
        run_decisions_means = np.zeros((n_runs, ticks), dtype=float)
        idx = np.arange(data.shape[3])
        for rn in range(n_runs):
            run_data = data[:, rn]
            valid_mask = run_data != -1
            cnt = valid_mask.sum(axis=2)
            decisions_mask = cnt >= self.min_buff_dim
            run_decisions_means[rn] = decisions_mask.mean(axis=0)
            start = cnt - buf_limit
            mask = (idx < cnt[..., None]) & (idx >= start[..., None])
            masked = np.where(mask, run_data, -1)
            sorted_rows = np.sort(masked, axis=2)
            if sorted_rows.shape[2] > 1:
                diff = (sorted_rows[...,1:] != sorted_rows[...,:-1]) & (sorted_rows[...,1:] != -1)
                uniq = diff.sum(axis=2) + (sorted_rows[...,0] != -1)
            else:
                uniq = (sorted_rows[...,0] != -1).astype(int)
            run_msgs_means[rn] = uniq.mean(axis=0)
        msgs_summation = np.round(run_msgs_means.mean(axis=0), 3).tolist()
        msgs_ci = np.round(1.96 * (run_msgs_means.std(axis=0, ddof=1) / np.sqrt(n_runs)), 3).tolist()
        decisions_summation = np.round(run_decisions_means.mean(axis=0), 3).tolist()
        decisions_ci = np.round(1.96 * (run_decisions_means.std(axis=0, ddof=1) / np.sqrt(n_runs)), 3).tolist()
        return msgs_summation, decisions_summation, msgs_ci, decisions_ci

##########################################################################################################
    def _read_buffers(self, path, max_steps, full_buff_size, max_buff_size, buf_cut):
        """
        Legge un file quorum_log: una riga ogni ticks_per_sec, ognuna con gli ID nel buffer separati da virgole.
        Restituisce (max_steps, max_buff_size) int16 con -1 come padding (in coda alla riga e in testa al file).
        Le righe campionate vengono convertite in blocco; per formati inattesi si usa il parsing riga per riga.
        """
        with open(path, 'rb') as f:
            raw = f.read()
        lines = raw.split(b'\n')
        if lines and lines[-1] == b'':
            lines.pop()
        sampled = lines[self.ticks_per_sec - 1 :: self.ticks_per_sec]
        n_rows = len(sampled)
        if n_rows > max_steps:
            return None, n_rows
        out = np.full((max_steps, max_buff_size), -1, dtype=np.int16)
        if n_rows == 0:
            return out, 0
        body = b','.join(l for l in sampled if l)
        counts = np.fromiter((l.count(b',') + 1 if l else 0 for l in sampled), dtype=np.int64, count=n_rows)
        simple = b'-' not in body and b'\t' not in body and b',,' not in body and b'\r' not in body
        vals = np.fromstring(body, dtype=np.int64, sep=',') if simple and body else np.zeros(0, dtype=np.int64)
        if not simple or vals.size != counts.sum():
            # formato non standard: parsing riga per riga come nella versione originale
            rows = []
            for line in sampled:
                v = [int(x.split(b'\t', 1)[0]) for x in line.split(b',') if x and x != b'-']
                rows.append(v)
            counts = np.array([len(v) for v in rows], dtype=np.int64)
            vals = np.array([x for v in rows for x in v], dtype=np.int64)
        # i messaggi oltre full_buff_size (n_agents-1) si scartano da sinistra,
        # poi per P.1.1 si oscurano i buf_cut messaggi piu' a destra
        skip_n = np.maximum(counts - full_buff_size, 0)
        keep_n = np.minimum(np.maximum(np.minimum(counts, full_buff_size) - buf_cut, 0), max_buff_size)
        row_of = np.repeat(np.arange(n_rows), counts)
        col_of = np.arange(vals.size) - np.repeat(np.cumsum(counts) - counts, counts) - np.repeat(skip_n, counts)
        sel = (col_of >= 0) & (col_of < np.repeat(keep_n, counts))
        offset = max_steps - n_rows
        out[offset + row_of[sel], col_of[sel]] = vals[sel]
        return out, n_rows

##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,msg_hops,sub_path,states,buf_cut=0):
        # buf_cut > 0 -> P.1.1: si oscurano buf_cut messaggi validi di ogni buffer, a destra
        x = 1
        full_buff_size = n_agents - x
        max_buff_size = full_buff_size - buf_cut
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        info_vec = sub_path.split('/')
        algo = ""
        arenaS = ""
        for iv in info_vec:
            iv_lower = iv.lower()
            if "results_loop" in iv_lower:
                algo = iv[:2] if iv_lower.startswith("ps") else iv[0]
                arenaS = iv.split('_')[-1][:-1]
                break
        # buffer di tutti gli agenti e run: (agents, runs, ticks, buf), int16 per contenere la memoria
        msgs_bigM = np.full((n_agents, num_runs, max_steps, max_buff_size), -1, dtype=np.int16)
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem=elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    agent_id = int(selem[0].split('_')[2].split('#')[-1])
                    seed = int(selem[0].split('_')[3].split('#')[-1])
                    mat, n_rows = self._read_buffers(os.path.join(sub_path, elem), max_steps, full_buff_size, max_buff_size, buf_cut)
                    if mat is None:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",n_rows)
                        exit(0)
                    msgs_bigM[agent_id, seed-1] = mat
        messages, decisions, msg_ci, dec_ci = self.compute_meaningfulMsgs_decidinAgents(msgs_bigM, max_buff_size)
        algo_lower = str(algo).strip().lower()
        buff_dim_eff = max_buff_size if (algo_lower == "ps" or buf_cut > 0) else "-"
        if algo_lower=='p' and buf_cut == 0 and msg_exp_time == 0:
            encounters_mean, encounters_ci = self.compute_unique_encounters_over_deltaT(msgs_bigM, n_agents, max_steps)
            self.dump_encounters("encounters_resume.csv", [
                arenaS, algo, communication, n_agents, msg_exp_time, msg_hops, 
                encounters_mean, encounters_ci, buff_dim_eff
            ])
        self.dump_decisions("decisions_resume.csv", [arenaS, algo, communication, n_agents, msg_exp_time, msg_hops, decisions, dec_ci, buff_dim_eff])
        self.dump_msgs("messages_resume.csv", [arenaS, algo, communication, n_agents, msg_exp_time, msg_hops, messages, msg_ci, buff_dim_eff])

        # dimensioni dei buffer e agenti a 1 per tutti i G; le maschere che non dipendono da (G, tau) si calcolano una volta
        dims, ones_all = self.compute_quorum_vars_all(msgs_bigM, np.asarray(states))
        del msgs_bigM
        base_mask = (dims - 1 >= self.min_buff_dim)
        dims_f = dims.astype(float)
        for gt in range(len(self.ground_truth)):
            print(f"--- Processing data {gt+1}/{len(self.ground_truth)} ---")
            ones_f = ones_all[gt].astype(float)
            for thr in self.thresholds.get(self.ground_truth[gt]):
                quorums = self.compute_quorum(dims,ones_f,thr,base_mask,dims_f)
                self.dump_times(algo,0,quorums,dims,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,max_buff_size,base_mask)
                self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,max_buff_size)
                self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,max_buff_size,msg_hops,self.ground_truth[gt],thr,quorums,dims,msg_exp_time,base_mask)

##########################################################################################################
    def compute_unique_encounters_over_deltaT(self, msgs_bigM, n_agents, ticks):
        """
        Per ogni dT: frazione media di altri agenti incontrati (presenti nel buffer) in una finestra di dT+1 tick.
        Per ogni (agente i, tick s, agente j) sia g il tempo dal tick s al primo incontro con j (s compreso):
        la coppia conta in tutte le finestre che partono in s con g <= dT <= ticks-1-s. Le somme su tutti i dT
        si ottengono con un array di differenze, in O(ticks * n^2) invece di O(ticks^2 * n^2).
        """
        msgs_bigM = np.asarray(msgs_bigM)
        num_runs = msgs_bigM.shape[1]
        prop_runs = np.zeros((num_runs, ticks), dtype=float)
        starts_per_dT = n_agents * (ticks - np.arange(ticks))
        for rn in range(num_runs):
            run_data = msgs_bigM[:, rn]
            B = np.zeros((n_agents, ticks, n_agents), dtype=bool)
            valid_mask = run_data != -1
            ag_idx, tick_idx, buff_idx = np.where(valid_mask)
            valid_ids = run_data[ag_idx, tick_idx, buff_idx]
            valid_id_mask = (valid_ids >= 0) & (valid_ids < n_agents) & (valid_ids != ag_idx)
            B[ag_idx[valid_id_mask], tick_idx[valid_id_mask], valid_ids[valid_id_mask]] = True
            # primo incontro a partire da ogni tick (ticks = mai)
            nxt = np.where(B, np.arange(ticks)[None, :, None], ticks)
            nxt = np.minimum.accumulate(nxt[:, ::-1, :], axis=1)[:, ::-1, :]
            s_idx = np.broadcast_to(np.arange(ticks)[None, :, None], nxt.shape)
            found = nxt < ticks
            gap = (nxt - s_idx)[found]
            diff = np.bincount(gap, minlength=ticks + 1)[:ticks + 1].astype(np.int64)
            diff -= np.bincount(ticks - s_idx[found], minlength=ticks + 1)[:ticks + 1]
            total = np.cumsum(diff)[:ticks]
            prop_runs[rn] = total / starts_per_dT / (n_agents - 1)
        encounters_mean = np.round(prop_runs.mean(axis=0), 4).tolist()
        encounters_ci = np.round(1.96 * (prop_runs.std(axis=0, ddof=1) / np.sqrt(num_runs)), 4).tolist()
        
        return encounters_mean, encounters_ci

##########################################################################################################
    def dump_encounters(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "msg_exp_time", "msg_hops", "data", "ci_95", "max_buff_size"]
        out_dir = os.path.join(os.path.abspath(""), "encounters_data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        
        write_header = not os.path.exists(out_path)
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            fw.write("\t".join(map(str, data)) + "\n")

##########################################################################################################
    def dump_recovery_raw(self,external_data,rows):
        # rows: righe gia' pronte (una per run), scritte con una sola apertura del file
        if not rows: return
        header = ["experiment_length","broadcast", "n_agents", "buff_dim", "msg_exp_time", "msg_hops", "ground_truth", "threshold", "run_id", "buff_starts", "durations", "events"]
        filename = os.path.abspath("")+"/proc_data"
        os.makedirs(filename, exist_ok=True)
        filename += "/"+external_data['algorithm']+"recovery_data_raw_r#"+str(external_data['runs'])+"_a#"+external_data['arena']+"A.csv"
        write_header = not os.path.exists(filename)
        with open(filename, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            fw.write("".join("\t".join(map(str, row)) + "\n" for row in rows))

##########################################################################################################
    def dump_decisions(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "msg_hops", "data", "ci_95", "buff_dim_eff"]
        out_dir = os.path.join(os.path.abspath(""), "dec_data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        write_header = not os.path.exists(out_path)
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            fw.write("\t".join(map(str, data)) + "\n")

##########################################################################################################
    def dump_msgs(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "msg_hops", "data", "ci_95", "max_buff_size"]
        out_dir = os.path.join(os.path.abspath(""), "msgs_data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        write_header = not os.path.exists(out_path)
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            fw.write("\t".join(map(str, data)) + "\n")

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,data_in,data_ci,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,msg_hops,n_runs,max_buff_size):    
        static_fields=["committed_perc","threshold","min_buff_dim","msg_exp_time","msg_hops","max_buff_size"]
        static_values=[COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,msg_hops,max_buff_size]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        file_name = f"{algo}average_resume_r#{n_runs}_a#{base.split('_')[-1]}.csv"
        if not os.path.exists(os.path.abspath("")+"/proc_data/"+file_name):
            write_header = 1
        tmp_b = base.split('/')
        tmp_p = path.split('/')
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
            values.append("broadcast_msg")
        elif indx+bias==2:
            values.append("rebroadcast_msg")
        elif indx+bias==3:
            values.append("do_nothing_buffer")
        elif indx+bias==4:
            values.append("insert_buffer")
        elif indx+bias==5:
            values.append("update_buffer")
        values.append(data_in)
        values.append(data_ci)
        out_path = os.path.abspath("")+"/proc_data/"+file_name
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header == 1:
                fw.write("\t".join(name_fields) + "\n")
            fw.write("\t".join(map(str, values)) + "\n")

##########################################################################################################
    def dump_quorum(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,max_buff_size):
        data_arr = np.asarray(data_in, dtype=float)
        run_means = data_arr.mean(axis=1)
        flag2 = run_means.mean(axis=0)
        runs_count = data_arr.shape[0]
        fci_95 = 1.96 * (run_means.std(axis=0, ddof=1) / np.sqrt(runs_count))
        self.dump_resume_csv(
            algo,0,bias,
            np.around(flag2,decimals=2).tolist(),
            np.around(fci_95,decimals=3).tolist(),
            BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,runs_count,max_buff_size
        )

##########################################################################################################
    def dump_times(self,algo,bias,quorums,buffers,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,max_buff_size,base_mask=None):
        q_arr = np.asarray(quorums)
        runs, agents, ticks = q_arr.shape
        actual_g = round(float(COMMIT), 2)
        tau = round(float(THR), 2)
        if tau <= actual_g:
            count = q_arr.sum(axis=1)
        else:
            if base_mask is None: base_mask = (np.asarray(buffers) - 1 >= MINS)
            count = (base_mask & (q_arr == 0)).sum(axis=1)
        reached = count >= 0.8 * agents
        # primo tick in cui si raggiunge l'80% degli agenti, ticks+100 se mai (dato censurato)
        times = np.where(reached.any(axis=1), reached.argmax(axis=1), ticks + 100)
        self.dump_resume_csv(algo,-1,bias,sorted(times.tolist()),'-',BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,runs,max_buff_size)

##########################################################################################################
    def assign_states(self, n_agents, num_runs):
        states_by_gt = np.zeros((len(self.ground_truth), num_runs, n_agents), dtype=int)
        for gt_idx, gt_value in enumerate(self.ground_truth):
            num_committed = math.ceil(n_agents * gt_value)
            for run_idx in range(num_runs):
                committed_indices = np.random.choice(n_agents, num_committed, replace=False)
                states_by_gt[gt_idx, run_idx, committed_indices] = 1
        return states_by_gt
