import os, csv, math, gc, logging
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
                selem=elem.split('_')
                if selem[0]=="Oresults" or selem[0]=="Presults":
                    self.bases.append(os.path.join(self.base, elem))
        for gt in range(len(self.ground_truth)):
            _thresholds=np.arange(50,101,1)
            f_thresholds = []
            for t in range(len(_thresholds)): f_thresholds.append(round(float(_thresholds[t])*.01,2))
            self.thresholds.update({self.ground_truth[gt]:f_thresholds})
            
#########################################################################################################
    def compute_quorum_vars_on_ground_truth(self,m1,states,buf_lim,gt,gt_dim,compound=None):
        print(f"--- Processing data {gt}/{gt_dim} ---") if compound==None else print(f"--- Processing data {gt}/{gt_dim} - arena#{compound[0]}_nAgents#{compound[1]}_tm#{compound[2]} ---")
        tmp_dim_0 = [np.array([])]*len(m1[0])
        tmp_ones_0 = [np.array([])]*len(m1[0])
        for i in range(len(states)):
            tmp_dim_1 = [np.array([])]*len(m1)
            tmp_ones_1 = [np.array([])]*len(m1)
            for j in range(len(states[i])):
                tmp_dim_2 = []
                tmp_ones_2 = []
                for t in range(len(m1[j][i])):
                    dim = 1
                    ones = states[i][j]
                    tmp = m1[j][i][t][m1[j][i][t] != -1]
                    for z in range(max(0,len(tmp) - buf_lim),len(tmp)):
                        dim += 1
                        ones += states[i][tmp[z]]
                    tmp_dim_2.append(dim)
                    tmp_ones_2.append(ones)
                tmp_dim_1[j]    = tmp_dim_2
                tmp_ones_1[j]   = tmp_ones_2
            tmp_dim_0[i]        = tmp_dim_1
            tmp_ones_0[i]       = tmp_ones_1
        return (tmp_dim_0,tmp_ones_0)

#########################################################################################################   
    def compute_quorum(self,m1,m2,threshold):
        out = np.copy(m1)
        for i in range(len(m1)):
            for j in range(len(m1[i])):
                for k in range(len(m1[i][j])):
                    out[i][j][k] = 1 if m1[i][j][k]-1 >= self.min_buff_dim and m2[i][j][k]/m1[i][j][k] >= threshold else 0
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
        for i in range(len(quorums)):
            for j in range(len(quorums[i])):
                sem = 0
                for t in range(len(quorums[i][j])):
                    b = buffers[i][j][t] - 1
                    q_val = quorums[i][j][t]
                    if sem == 0 and b >= self.min_buff_dim and ((gt < thr and q_val == 1) or (gt >= thr and q_val == 0)):
                        sem = 1
                        t_starts.append(t+1)
                        b_starts.append(b)
                    elif sem == 1 and (b < self.min_buff_dim or (gt < thr and q_val == 0) or (gt >= thr and q_val == 1)):
                        sem = 0
                        t_ends.append(t+1)
                        ends_cens.append(1)
                if sem == 1:
                    t_ends.append(len(quorums[i][j])+1)
                    ends_cens.append(0)
                    censored += 1
        print(f"{arenaS},{msg_exp_time},{gt},{thr} |\t events {len(ends_cens)} -- censored {censored}")                
        if len(t_starts) > 0:
            durations = [x - y for x, y in zip(t_ends, t_starts)]
            self.dump_recovery_raw(external_data,[b_starts,durations,ends_cens])

##########################################################################################################
    def compute_meaningful_msgs(self,data,buf_limit):
        data_partial = np.array([])
        for ag in range(len(data)):
            runs = np.array([])
            for rn in range(len(data[ag])):
                tmp = [0]*len(data[0][0])
                for tk in range(len(data[ag][rn])):
                    stripped_ones = data[ag][rn][tk][data[ag][rn][tk] != -1]
                    flag = []
                    for el in range(max(0,len(stripped_ones) - buf_limit),len(stripped_ones)):
                        if stripped_ones[el] not in flag:
                            flag.append(stripped_ones[el])
                            tmp[tk] += 1
                if len(runs) == 0:
                    runs = [tmp]
                else:
                    runs = np.append(runs,[tmp],axis=0)
            if len(data_partial) == 0:
                data_partial = [runs]
            else:
                data_partial = np.append(data_partial,[runs],axis=0)
        msgs_summation = [0]*len(data_partial[0][0])
        for ag in range(len(data_partial)):
            for rn in range(len(data_partial[ag])):
                for tk in range(len(data_partial[ag][rn])):
                    msgs_summation[tk] += data_partial[ag][rn][tk]
        run_ag = len(data_partial)*len(data_partial[0])
        for tk in range(len(msgs_summation)):
            msgs_summation[tk] = np.around(msgs_summation[tk]/run_ag,decimals=3)
        return msgs_summation

##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,msg_hops,sub_path,states):
        max_buff_size = n_agents - 1
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        msgs_bigM = [np.array([])] * n_agents
        msgs_M = [np.array([],dtype=int)]*num_runs # x num_samples
        agents_count = [0]*n_agents
        info_vec    = sub_path.split('/')
        algo    = ""
        arenaS  = ""
        for iv in info_vec:
            if "results_loop" in iv:
                algo        = iv[0]
                arenaS      = iv.split('_')[-1][:-1]
                break
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem=elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    agent_id = int(selem[0].split('_')[2].split('#')[-1])
                    seed = int(selem[0].split('_')[3].split('#')[-1])
                    agents_count[agent_id] += 1
                    with open(os.path.join(sub_path, elem), newline='') as f:
                        reader = csv.reader(f)
                        log_count = 0
                        for row in reader:
                            log_count += 1
                            if log_count % self.ticks_per_sec == 0:
                                msgs = []
                                for val in row:                                            
                                    if val.count('\t')==0:
                                        if val!='-' : msgs.append(int(val))
                                    else:
                                        val = val.split('\t')
                                        if val[0] != '': msgs.append(int(val[0]))
                                for _ in range(max_buff_size-len(msgs)): msgs.append(-1)
                                if len(msgs_M[seed-1]) == 0:
                                    msgs_M[seed-1] = [msgs]
                                else:
                                    msgs_M[seed-1] = np.append(msgs_M[seed-1],[msgs],axis=0)
                    if len(msgs_M[seed-1])!=max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(msgs_M[seed-1]))
                    if agents_count[agent_id]==num_runs:
                        msgs_bigM[agent_id] = msgs_M
                        msgs_M = [np.array([],dtype=int)]*num_runs
        if algo=='P':
            BUFFERS = [20,21,22,23,24]
            buf = 0
            if arenaS=='big':
                if n_agents==25:
                    BUFFERS = [24,24,24,23,24]
                elif n_agents==100:
                    BUFFERS = [99,99,99,99,99]
            if int(msg_exp_time)==120:
                buf = 1
            elif int(msg_exp_time)==180:
                buf = 2
            elif int(msg_exp_time)==300:
                buf = 3
            elif int(msg_exp_time)==600:
                buf = 4
            # messages = self.compute_meaningful_msgs(msgs_bigM,BUFFERS[buf])
            # self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,msg_hops,messages])
            for gt in range(len(self.ground_truth)):
                results = self.compute_quorum_vars_on_ground_truth(msgs_bigM,states[gt],BUFFERS[buf],gt+1,len(self.ground_truth))
                for thr in self.thresholds.get(self.ground_truth[gt]):
                    quorums = self.compute_quorum(results[0],results[1],thr)
                    # self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                    # self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                    self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,BUFFERS[buf],msg_hops,self.ground_truth[gt],thr,quorums,results[0],msg_exp_time)
                    del quorums
                del results
            # del messages
        else:
            messages = self.compute_meaningful_msgs(msgs_bigM,n_agents-1)
            self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,msg_hops,messages])
            for gt in range(len(self.ground_truth)):
                results = self.compute_quorum_vars_on_ground_truth(msgs_bigM,states[gt],n_agents-1,gt+1,len(self.ground_truth))
                for thr in self.thresholds.get(self.ground_truth[gt]):
                    quorums = self.compute_quorum(results[0],results[1],thr)
                    self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                    self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                    self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,n_agents-1,msg_hops,self.ground_truth[gt],thr,quorums,results[0],msg_exp_time)
                    del quorums
                del results
            del messages
        del msgs_M,msgs_bigM
        gc.collect()
                
##########################################################################################################
    def extract_k_data_fifo(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,msg_hops,sub_path,algo,arenaS,buf,states):
        max_buff_size = n_agents - 1
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        msgs_bigM = [np.array([])] * n_agents
        msgs_M = [np.array([],dtype=int)]*num_runs # x num_samples
        agents_count = [0]*n_agents
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem=elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    agent_id = int(selem[0].split('_')[2].split('#')[-1])
                    seed = int(selem[0].split('_')[3].split('#')[-1])
                    agents_count[agent_id] += 1
                    with open(os.path.join(sub_path, elem), newline='') as f:
                        reader = csv.reader(f)
                        log_count = 0
                        for row in reader:
                            log_count += 1
                            if log_count % self.ticks_per_sec == 0:
                                msgs = []
                                for val in row:
                                    if val.count('\t')==0:
                                        if val!='-' : msgs.append(int(val))
                                    else:
                                        val = val.split('\t')
                                        if val[0] != '': msgs.append(int(val[0]))
                                for _ in range(max_buff_size-len(msgs)): msgs.append(-1)
                                if len(msgs_M[seed-1]) == 0:
                                    msgs_M[seed-1] = [msgs]
                                else:
                                    msgs_M[seed-1] = np.append(msgs_M[seed-1],[msgs],axis=0)
                    if len(msgs_M[seed-1])!=max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(msgs_M[seed-1]))
                    if agents_count[agent_id]==num_runs:
                        msgs_bigM[agent_id] = msgs_M
                        msgs_M = [np.array([],dtype=int)]*num_runs
        if algo=='P':
            # messages = self.compute_meaningful_msgs(msgs_bigM,BUFFERS[buf])
            # self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,msg_hops,messages])
            for gt in range(len(self.ground_truth)):
                results = self.compute_quorum_vars_on_ground_truth(msgs_bigM,states[gt],buf,gt+1,len(self.ground_truth))
                for thr in self.thresholds.get(self.ground_truth[gt]):
                    quorums = self.compute_quorum(results[0],results[1],thr)
                    # self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                    # self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                    self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,buf,msg_hops,self.ground_truth[gt],thr,quorums,results[0],msg_exp_time)
                    del quorums
                del results
            # del messages
        del msgs_M,msgs_bigM
        gc.collect()

##########################################################################################################
    def dump_recovery_raw(self,external_data,data):
        header = ["experiment_length","broadcast", "n_agents", "buff_dim", "msg_exp_time", "msg_hops", "ground_truth", "threshold", "buff_starts", "durations", "events"]
        filename = os.path.abspath("")+"/proc_data"
        if not os.path.exists(filename):
            os.mkdir(filename)
        filename += "/"+external_data['algorithm']+"recovery_data_raw_r#"+str(external_data['runs'])+"_a#"+external_data['arena']+"A.csv"
        write_header = not os.path.exists(filename)
        with open(filename, mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow([external_data['experiment_length'],external_data['rebroadcast'],external_data['n_agents'],external_data['buff_dim'],external_data['msg_exp_time'],external_data['msg_hops'],external_data['ground_truth'],external_data['threshold'],
                                data[0],data[1],data[2]])

##########################################################################################################
    def dump_msgs_homogeneity(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "msg_hops", "type", "data"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "msgs_data"))
        
        with open(os.path.join(os.path.abspath(""), "msgs_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            base_data = list(data[:-1])
            stats_tuple = data[-1]
            types = ["max_count", "min_count", "median_max_count", "median_min_count", "agents_over_median", "90_agents"]
            for t, stat in zip(types, stats_tuple):
                row = base_data + [t, stat]
                fwriter.writerow(row)

##########################################################################################################
    def dump_msgs(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "msg_hops", "data"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "msgs_data"))
        
        with open(os.path.join(os.path.abspath(""), "msgs_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow(data)

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,data_in,data_std,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,msg_hops,n_runs):    
        static_fields=["committed_perc","threshold","min_buff_dim","msg_exp_time","msg_hops"]
        static_values=[COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,msg_hops]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        if algo == 'O':
            file_name = "Oaverage_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
        else:
            file_name = "Paverage_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
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
        fw = open(os.path.abspath("")+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()

##########################################################################################################
    def dump_quorum(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops):
        flag2=[-1]*len(data_in[0][0])
        for i in range(len(data_in)):
            flag1=[-1]*len(data_in[i][0])
            for j in range(len(data_in[i])):
                for z in range(len(data_in[i][j])):
                    if flag1[z]==-1:
                        flag1[z]=data_in[i][j][z]
                    else:
                        flag1[z]=flag1[z]+data_in[i][j][z]
            for j in range(len(flag1)):
                flag1[j]=flag1[j]/len(data_in[i])
                if flag2[j]==-1:
                    flag2[j]=flag1[j]
                else:
                    flag2[j]=flag1[j]+flag2[j]
        for i in range(len(flag2)):
            flag2[i]=flag2[i]/len(data_in)
        fstd2=[[-1]*len(data_in[0][0])]*len(data_in)
        fstd3=[-1]*len(data_in[0][0])
        for i in range(len(data_in)):
            fstd1=[-1]*len(data_in[i][0])
            for z in range(len(data_in[i][0])): # per ogni tick
                std_tmp = []
                for j in range(len(data_in[i])): # per ogni agente
                    std_tmp.append(float(data_in[i][j][z]))
                fstd1[z]=np.std(std_tmp)
            fstd2[i]=fstd1
        for z in range(len(fstd3)):
            median_array = []
            for i in range(len(fstd2)):
                median_array.append(fstd2[i][z])
            fstd3[z]=np.median(median_array)
        self.dump_resume_csv(algo,0,bias,np.around(flag2,decimals=2).tolist(),np.around(fstd3,decimals=3).tolist(),BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,len(data_in))

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops):
        times = [len(data_in[0][0])] * len(data_in)
        for i in range(len(data_in)): # per ogni run
            for z in range(len(data_in[i][0])): # per ogni tick
                sum = 0
                for j in range(len(data_in[i])): # per ogni agente
                    sum += data_in[i][j][z]
                if sum >= self.limit * len(data_in[i]):
                    times[i] = z
                    break
        times = sorted(times)
        self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,len(data_in))

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