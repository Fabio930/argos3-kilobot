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
            
#########################################################################################################
    def compute_quorum_vars_on_ground_truth(self,m1,states,buf_lim,gt,gt_dim,compound=None):
        print(f"--- Processing data {gt}/{gt_dim} ---") if compound==None else print(f"--- Processing data {gt}/{gt_dim} - arena#{compound[0]}_nAgents#{compound[1]}_tm#{compound[2]} ---")
        states_arr = np.asarray(states)
        runs = states_arr.shape[0]
        agents = states_arr.shape[1]
        sample_mat = np.asarray(m1[0][0])
        ticks = sample_mat.shape[0]
        tmp_dim_0 = np.empty((runs, agents, ticks), dtype=int)
        tmp_ones_0 = np.empty((runs, agents, ticks), dtype=int)
        idx = np.arange(sample_mat.shape[1])
        for i in range(runs):
            states_i = states_arr[i]
            for j in range(agents):
                rows = np.asarray(m1[j][i])
                valid_mask = rows != -1
                cnt = valid_mask.sum(axis=1)
                dims = 1 + np.minimum(cnt, buf_lim)
                start = cnt - buf_lim
                mask = (idx < cnt[:, None]) & (idx >= start[:, None])
                safe_rows = np.where(rows < 0, 0, rows)
                ones_sum = (states_i[safe_rows] * mask).sum(axis=1)
                tmp_dim_0[i, j, :] = dims
                tmp_ones_0[i, j, :] = states_i[j] + ones_sum
        return (tmp_dim_0,tmp_ones_0)

#########################################################################################################   
    def compute_quorum(self,m1,m2,threshold):
        m1_arr = np.asarray(m1)
        m2_arr = np.asarray(m2)
        cond = (m1_arr - 1 >= self.min_buff_dim) & (m2_arr.astype(float) >= threshold * m1_arr)
        out = np.zeros_like(m1_arr, dtype=int)
        out[cond] = 1
        return out
 
##########################################################################################################
    def compute_recovery(self,algo,runs,arenaS,communication,n_agents,buf_dim,msg_hops,gt,thr,quorums,buffers,msg_exp_time):
        # if gt < thr compute the steps in which the agents have the wrong state "1" and the buffer lenght
        # if gt >= thr compute the steps in which the agents have the wrong state "0" and the buffer lenght
        external_data = {
            'algorithm': algo,
            'runs': runs,
            'arena' : arenaS,
            'experiment_length' : len(quorums[0][0]),
            'rebroadcast': communication,
            'n_agents': n_agents,
            'buff_dim': buf_dim,
            'msg_exp_time': msg_exp_time,
            'msg_hops': msg_hops,
            'ground_truth': gt,
            'threshold': thr
        }
        q_arr = np.asarray(quorums)
        b_arr = np.asarray(buffers)
        wrong_is_one = gt < thr
        for i in range(q_arr.shape[0]):
            t_starts, t_ends, b_starts = [], [], []
            ends_cens = []
            censored = 0
            for j in range(q_arr.shape[1]):
                b = b_arr[i, j] - 1
                q = q_arr[i, j]
                if wrong_is_one:
                    cond = (b >= self.min_buff_dim) & (q == 1)
                else:
                    cond = (b >= self.min_buff_dim) & (q == 0)
                if not np.any(cond):
                    continue
                cond_i = cond.astype(np.int8)
                start_idx = np.flatnonzero(np.diff(cond_i, prepend=0) == 1)
                last_true_idx = np.flatnonzero(np.diff(cond_i, append=0) == -1)
                end_idx = last_true_idx + 1
                if start_idx.size == 0:
                    continue
                t_starts.extend((start_idx + 1).tolist())
                t_ends.extend((end_idx + 1).tolist())
                b_starts.extend(b[start_idx].tolist())
                cens_mask = end_idx == cond_i.shape[0]
                if np.any(cens_mask):
                    censored += int(np.count_nonzero(cens_mask))
                ends_cens.extend((~cens_mask).astype(int).tolist())
            if len(t_starts) > 0:
                durations = [x - y for x, y in zip(t_ends, t_starts)]
                external_data['current_run'] = i + 1
                self.dump_recovery_raw(external_data,[b_starts,durations,ends_cens])

##########################################################################################################
    def compute_meaningfulMsgs_decidinAgents(self,data,buf_limit):
        n_agents = len(data)
        n_runs = len(data[0])
        ticks = len(data[0][0])
        run_msgs_means = np.zeros((n_runs, ticks), dtype=float)
        run_decisions_means = np.zeros((n_runs, ticks), dtype=float)
        idx = None
        for rn in range(n_runs):
            run_data = np.stack([data[ag][rn] for ag in range(n_agents)], axis=0)
            if idx is None:
                idx = np.arange(run_data.shape[2])
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
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,msg_hops,sub_path,states):
        x = 1
        max_buff_size = n_agents - x
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        msgs_bigM = [np.array([])] * n_agents
        msgs_M = [None] * num_runs
        agents_count = [0] * n_agents
        info_vec = sub_path.split('/')
        algo = ""
        arenaS = ""
        for iv in info_vec:
            iv_lower = iv.lower()
            if "results_loop" in iv_lower:
                algo = iv[:2] if iv_lower.startswith("ps") else iv[0]
                arenaS = iv.split('_')[-1][:-1]
                break
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem=elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    agent_id = int(selem[0].split('_')[2].split('#')[-1])
                    seed = int(selem[0].split('_')[3].split('#')[-1])
                    agents_count[agent_id] += 1
                    with open(os.path.join(sub_path, elem), 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    sampled_lines = lines[self.ticks_per_sec - 1 :: self.ticks_per_sec]
                    msgs_list = []
                    for line in sampled_lines:
                        vals = [
                            int(v.split('\t', 1)[0]) 
                            for v in line.rstrip('\n').split(',') 
                            if v and v != '-'
                        ]
                        v_len = len(vals)
                        if v_len < max_buff_size:
                            vals.extend([-1] * (max_buff_size - v_len))
                        elif v_len > max_buff_size:
                            vals = vals[:max_buff_size]
                        msgs_list.append(vals)
                    msgs_M[seed-1] = np.asarray(msgs_list, dtype=int)
                    if msgs_M[seed-1].shape[0] < max_steps:
                        padded = np.full((max_steps, max_buff_size), -1, dtype=int)
                        if msgs_M[seed-1].shape[0] > 0:
                            padded[-msgs_M[seed-1].shape[0]:] = msgs_M[seed-1]
                        msgs_M[seed-1] = padded
                    elif msgs_M[seed-1].shape[0] > max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(msgs_M[seed-1]))
                        exit(0)
                    if agents_count[agent_id]==num_runs:
                        msgs_bigM[agent_id] = msgs_M
                        msgs_M = [None] * num_runs
        messages, decisions, msg_ci, dec_ci = self.compute_meaningfulMsgs_decidinAgents(msgs_bigM, max_buff_size)
        algo_lower = str(algo).strip().lower()
        buff_dim_eff = max_buff_size if algo_lower == "ps" else "-"
        self.dump_decisions("decisions_resume.csv", [arenaS, algo, communication, n_agents, msg_exp_time, msg_hops, decisions, dec_ci, buff_dim_eff])
        self.dump_msgs("messages_resume.csv", [arenaS, algo, communication, n_agents, msg_exp_time, msg_hops, messages, msg_ci, buff_dim_eff])
        
        for gt in range(len(self.ground_truth)):
            results = self.compute_quorum_vars_on_ground_truth(msgs_bigM,states[gt],max_buff_size,gt+1,len(self.ground_truth))
            for thr in self.thresholds.get(self.ground_truth[gt]):
                quorums = self.compute_quorum(results[0],results[1],thr)
                self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,max_buff_size)
                self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,max_buff_size)
                self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,max_buff_size,msg_hops,self.ground_truth[gt],thr,quorums,results[0],msg_exp_time)
##########################################################################################################
    def dump_recovery_raw(self,external_data,data):
        header = ["experiment_length","broadcast", "n_agents", "buff_dim", "msg_exp_time", "msg_hops", "ground_truth", "threshold", "run_id", "buff_starts", "durations", "events"]
        filename = os.path.abspath("")+"/proc_data"
        if not os.path.exists(filename):
            os.mkdir(filename)
        filename += "/"+external_data['algorithm']+"recovery_data_raw_r#"+str(external_data['runs'])+"_a#"+external_data['arena']+"A.csv"
        write_header = not os.path.exists(filename)
        with open(filename, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            row = [
                external_data['experiment_length'],
                external_data['rebroadcast'],
                external_data['n_agents'],
                external_data['buff_dim'],
                external_data['msg_exp_time'],
                external_data['msg_hops'],
                external_data['ground_truth'],
                external_data['threshold'],
                external_data['current_run'],
                data[0],
                data[1],
                data[2],
            ]
            fw.write("\t".join(map(str, row)) + "\n")

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
    def dump_times(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,max_buff_size):
        data_arr = np.asarray(data_in, dtype=float)
        runs = data_arr.shape[0]
        ticks = data_arr.shape[2]
        sums = data_arr.sum(axis=1)
        cond = sums >= (self.limit * data_arr.shape[1])
        any_true = cond.any(axis=1)
        first_idx = cond.argmax(axis=1)
        times = np.where(any_true, first_idx, ticks).tolist()
        times = sorted(times)
        self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,len(data_in),max_buff_size)

##########################################################################################################
    def assign_states(self, n_agents, num_runs):
        states_by_gt = np.zeros((len(self.ground_truth), num_runs, n_agents), dtype=int)
        for gt_idx, gt_value in enumerate(self.ground_truth):
            num_committed = math.ceil(n_agents * gt_value)
            for run_idx in range(num_runs):
                committed_indices = np.random.choice(n_agents, num_committed, replace=False)
                states_by_gt[gt_idx, run_idx, committed_indices] = 1
        return states_by_gt
