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
        t_starts, t_ends, b_starts = [], [], []
        ends_cens = []
        censored = 0
        q_arr = np.asarray(quorums)
        b_arr = np.asarray(buffers)
        wrong_is_one = gt < thr
        for i in range(q_arr.shape[0]):
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
            self.dump_recovery_raw(external_data,[b_starts,durations,ends_cens])

##########################################################################################################
    def compute_meaningfulMsgs_decidinAgents(self,data,buf_limit):
        n_agents = len(data)
        n_runs = len(data[0])
        ticks = len(data[0][0])
        msgs_sum = np.zeros(ticks, dtype=float)
        msgs_std_sum = np.zeros(ticks, dtype=float)
        idx = None
        for rn in range(n_runs):
            run_data = np.stack([data[ag][rn] for ag in range(n_agents)], axis=0)
            if idx is None:
                idx = np.arange(run_data.shape[2])
            valid_mask = run_data != -1
            cnt = valid_mask.sum(axis=2)
            start = cnt - buf_limit
            mask = (idx < cnt[..., None]) & (idx >= start[..., None])
            masked = np.where(mask, run_data, -1)
            sorted_rows = np.sort(masked, axis=2)
            if sorted_rows.shape[2] > 1:
                diff = (sorted_rows[...,1:] != sorted_rows[...,:-1]) & (sorted_rows[...,1:] != -1)
                uniq = diff.sum(axis=2) + (sorted_rows[...,0] != -1)
            else:
                uniq = (sorted_rows[...,0] != -1).astype(int)
            msgs_sum += uniq.sum(axis=0)
            msgs_std_sum += np.std(uniq, axis=0)
        run_ag = n_agents * n_runs
        msgs_summation = np.round(msgs_sum / run_ag, 3).tolist()
        msgs_std = np.round(msgs_std_sum / n_agents, 3).tolist()
        decisions = [0.0 for _ in range(ticks)]
        return msgs_summation,decisions,msgs_std

##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,msg_hops,sub_path,states):
        x = 1
        # if n_agents == 100: x = 40
        max_buff_size = n_agents - x
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        msgs_bigM = [np.array([])] * n_agents
        msgs_M = [None] * num_runs  # x num_samples
        agents_count = [0] * n_agents
        info_vec    = sub_path.split('/')
        algo    = ""
        arenaS  = ""
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
                    with open(os.path.join(sub_path, elem), newline='', buffering=1024 * 1024) as f:
                        log_count = 0
                        msgs_list = []
                        int_cast = int
                        for line in f:
                            log_count += 1
                            if log_count % self.ticks_per_sec != 0:
                                continue
                            msgs = []
                            for val in line.rstrip('\n').split(','):
                                if '\t' in val:
                                    val = val.split('\t', 1)[0]
                                if val and val != '-':
                                    msgs.append(int_cast(val))
                            if len(msgs) < max_buff_size:
                                msgs.extend([-1] * (max_buff_size - len(msgs)))
                            elif len(msgs) > max_buff_size:
                                # Clamp oversize rows to avoid ragged arrays
                                msgs = msgs[:max_buff_size]
                            msgs_list.append(msgs)
                        msgs_arr = np.asarray(msgs_list, dtype=int)
                        msgs_M[seed-1] = msgs_arr
                    if msgs_M[seed-1].shape[0] < max_steps:
                        missing = max_steps - msgs_M[seed-1].shape[0]
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
        messages,decisions,msg_std = self.compute_meaningfulMsgs_decidinAgents(msgs_bigM,max_buff_size)
        algo_lower = str(algo).strip().lower()
        buff_dim_eff = max_buff_size if algo_lower == "ps" else "-"
        # self.dump_decisions("decisions_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,msg_hops,decisions,buff_dim_eff])
        self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,msg_hops,messages,msg_std,buff_dim_eff])
        for gt in range(len(self.ground_truth)):
            results = self.compute_quorum_vars_on_ground_truth(msgs_bigM,states[gt],max_buff_size,gt+1,len(self.ground_truth))
            for thr in self.thresholds.get(self.ground_truth[gt]):
                quorums = self.compute_quorum(results[0],results[1],thr)
                self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,max_buff_size)
                self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,max_buff_size)
                self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,max_buff_size,msg_hops,self.ground_truth[gt],thr,quorums,results[0],msg_exp_time)

##########################################################################################################
    def dump_recovery_raw(self,external_data,data):
        header = ["experiment_length","broadcast", "n_agents", "buff_dim", "msg_exp_time", "msg_hops", "ground_truth", "threshold", "buff_starts", "durations", "events"]
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
                data[0],
                data[1],
                data[2],
            ]
            fw.write("\t".join(map(str, row)) + "\n")

##########################################################################################################
    def dump_decisions(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "msg_hops", "data", "buff_dim_eff"]
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
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "msg_hops", "data", "std", "max_buff_size"]
        out_dir = os.path.join(os.path.abspath(""), "msgs_data")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        write_header = not os.path.exists(out_path)
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header:
                fw.write("\t".join(header) + "\n")
            fw.write("\t".join(map(str, data)) + "\n")

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,data_in,data_std,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,msg_hops,n_runs,max_buff_size):    
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
        name_fields.append("std")
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
        values.append(data_std)
        out_path = os.path.abspath("")+"/proc_data/"+file_name
        with open(out_path, mode='a', newline='', buffering=1024 * 1024) as fw:
            if write_header == 1:
                fw.write("\t".join(name_fields) + "\n")
            fw.write("\t".join(map(str, values)) + "\n")

##########################################################################################################
    def dump_quorum(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,max_buff_size):
        data_arr = np.asarray(data_in, dtype=float)
        flag2 = data_arr.mean(axis=1).mean(axis=0)
        fstd3 = np.median(np.std(data_arr, axis=1), axis=0)
        self.dump_resume_csv(
            algo,0,bias,
            np.around(flag2,decimals=2).tolist(),
            np.around(fstd3,decimals=3).tolist(),
            BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,len(data_in),max_buff_size
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
    def assign_states(self,n_agents,num_runs):
        # assign randomly the state to agents at each run
        states_by_gt = [np.array([])]*len(self.ground_truth)
        for gt in range(len(self.ground_truth)):
            runs_states = [np.array([])]*num_runs
            num_committed = math.ceil(n_agents*self.ground_truth[gt])
            for i in range(num_runs):
                ones = 0
                agents_state = [0]*n_agents
                while(1):
                    for j in range(n_agents):
                        if agents_state[j]==0:
                            tmp = np.random.random_integers(0,1)
                            if tmp==1:
                                if ones<num_committed:
                                    ones+=1
                                    agents_state[j] = tmp
                        if ones >= num_committed: break
                    if ones >= num_committed: break
                if len(runs_states[0]) == 0:
                    runs_states = [np.array(agents_state)]
                else:
                    runs_states = np.append(runs_states,[agents_state],axis=0)
            if len(states_by_gt[0]) == 0:
                states_by_gt = [runs_states]
            else:
                states_by_gt = np.append(states_by_gt,[runs_states],axis=0)
        return states_by_gt
