import numpy as np
import os, csv, math, gc
import logging
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
    def compute_quorum_vars_on_ground_truth(self,algo,m1,states,buf_lim,gt,gt_dim):
        print(f"--- Processing data {gt}/{gt_dim} ---")
        buf_lim = int(buf_lim)
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
                    tmp=np.delete(m1[j][i][t], np.where(m1[j][i][t] == -1))
                    start = 0
                    if algo=='P' and len(tmp) > buf_lim: start = len(tmp) - buf_lim
                    for z in range(start,len(tmp)):
                        dim += 1
                        ones += states[i][m1[j][i][t][z]]
                    tmp_dim_2.append(dim)
                    tmp_ones_2.append(ones)
                tmp_dim_1[j]    = tmp_dim_2
                tmp_ones_1[j]   = tmp_ones_2
            tmp_dim_0[i]        = tmp_dim_1
            tmp_ones_0[i]       = tmp_ones_1
        return (tmp_dim_0,tmp_ones_0)
    
#########################################################################################################
    def compute_quorum(self,m1,m2,minus,threshold):
        out = np.copy(m1)
        for i in range(len(m1)):
            for j in range(len(m1[i])):
                for k in range(len(m1[i][j])):
                    out[i][j][k] = 1 if m1[i][j][k]-1 >= minus and m2[i][j][k] >= threshold * m1[i][j][k] else 0
        return out

##########################################################################################################
    def compute_meaningful_msgs(self,data,limit,algo,buf,buf_dim):
        print(f"--- Computing avg buffer dimension {buf}/{buf_dim} ---")
        data_partial = np.array([])
        for ag in range(len(data)):
            runs = np.array([])
            for rn in range(len(data[ag])):
                tmp = [0]*len(data[0][0])
                for tk in range(len(data[ag][rn])):
                    flag = []
                    for el in range(len(data[ag][rn][tk])):
                        if algo == 'P' and el >= limit: break
                        elif data[ag][rn][tk][el] not in flag and data[ag][rn][tk][el]!=-1:
                            flag.append(data[ag][rn][tk][el])
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
        for tk in range(len(msgs_summation)):
            msgs_summation[tk] = msgs_summation[tk]/len(data_partial)
            msgs_summation[tk] = np.round(msgs_summation[tk]/len(data_partial[0]),3)
        return msgs_summation
    
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
    
##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,msg_hops,sub_path,data_type="all"):
        max_buff_size = n_agents - 1
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        msgs_bigM_1 = [np.array([])] * n_agents
        act_bigM_1 = [np.array([])] * n_agents
        act_bigM_2 = [np.array([])] * n_agents
        buff_neglects_bigM = [np.array([])] * n_agents
        buff_insertin_bigM = [np.array([])] * n_agents
        buff_updates_bigM = [np.array([])] * n_agents
        msgs_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
        act_M_1 = [np.array([],dtype=int)]*num_runs
        act_M_2 = [np.array([],dtype=int)]*num_runs
        buff_neglects  = [np.array([],dtype=int)]*num_runs
        buff_insertin  = [np.array([],dtype=int)]*num_runs
        buff_updates  = [np.array([],dtype=int)]*num_runs
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
                            broadcast_c = 0
                            re_broadcast_c = 0 
                            buf_neglect = 0
                            buf_insert = 0
                            buf_update = 0
                            if log_count % self.ticks_per_sec == 0:
                                msgs = []
                                if data_type in ("all","freq"):
                                    for val in row:                                            
                                        if val.count('\t')!=0:
                                            val = val.split('\t')
                                            broadcast_c = int(val[1])
                                            re_broadcast_c = int(val[2])
                                            if len(val)>3:
                                                buf_neglect = int(val[3])
                                                buf_insert = int(val[4])
                                                buf_update = int(val[5])
                                    act_M_1[seed-1] = np.append(act_M_1[seed-1],broadcast_c)
                                    act_M_2[seed-1] = np.append(act_M_2[seed-1],re_broadcast_c)
                                    buff_neglects[seed-1] = np.append(buff_neglects[seed-1],buf_neglect)
                                    buff_insertin[seed-1] = np.append(buff_insertin[seed-1],buf_insert)
                                    buff_updates[seed-1] = np.append(buff_updates[seed-1],buf_update)
                                if data_type in ("all","quorum"):
                                    for val in row:                                            
                                        if val.count('\t')==0:
                                            if val!='-' : msgs.append(int(val))
                                        else:
                                            val = val.split('\t')
                                            if val[0] != '': msgs.append(int(val[0]))
                                    if len(msgs) < max_buff_size:
                                        for i in range(max_buff_size-len(msgs)): msgs.append(-1)
                                    if len(msgs_M_1[seed-1]) == 0:
                                        msgs_M_1[seed-1] = [msgs]
                                    else :
                                        msgs_M_1[seed-1] = np.append(msgs_M_1[seed-1],[msgs],axis=0)
                    if data_type in ("all","quorum") and len(msgs_M_1[seed-1])!=max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(msgs_M_1[seed-1]))
                    elif data_type in ("freq") and len(act_M_1[seed-1])!=max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(act_M_1[seed-1]))
                    if agents_count[agent_id]==num_runs:
                        if data_type in ("all","freq"):
                            act_bigM_1[agent_id] = act_M_1
                            act_bigM_2[agent_id] = act_M_2
                            act_M_1 = [np.array([],dtype=int)]*num_runs
                            act_M_2 = [np.array([],dtype=int)]*num_runs
                            buff_neglects_bigM[agent_id] = buff_neglects
                            buff_insertin_bigM[agent_id] = buff_insertin
                            buff_updates_bigM[agent_id] = buff_updates
                            buff_neglects = [np.array([],dtype=int)]*num_runs
                            buff_insertin = [np.array([],dtype=int)]*num_runs
                            buff_updates = [np.array([],dtype=int)]*num_runs
                        if data_type in ("all","quorum"):
                            msgs_bigM_1[agent_id] = msgs_M_1
                            msgs_M_1 = [np.array([],dtype=int)]*num_runs
        info_vec    = sub_path.split('/')
        algo        = info_vec[4].split('_')[0][0]
        if data_type in ("all","quorum"):
            states_by_gt = self.assign_states(n_agents,num_runs)
            arenaS   = info_vec[4].split('_')[-1][:-1]
            BUFFERS = []
            if arenaS=='small':
                BUFFERS = [19,22,23,23.01,24]
            elif arenaS=='big':
                if n_agents==25:
                    BUFFERS=[11,15,17,19,21]
                elif n_agents==100:
                    BUFFERS=[41,56,65,74,83]
            if algo=='P':
                for buf in range(len(BUFFERS)):
                    messages = self.compute_meaningful_msgs(msgs_bigM_1,BUFFERS[buf],algo,buf+1,len(BUFFERS))
                    self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,BUFFERS[buf],msg_hops,messages])
                    for gt in range(len(self.ground_truth)):
                        results = self.compute_quorum_vars_on_ground_truth(algo,msgs_bigM_1,states_by_gt[gt],BUFFERS[buf],gt+1,len(self.ground_truth))
                        for thr in self.thresholds.get(self.ground_truth[gt]):
                            quorums = self.compute_quorum(results[0],results[1],self.min_buff_dim,thr)
                            self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,BUFFERS[buf],msg_hops,self.limit)
                            self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,BUFFERS[buf],msg_hops)
                            self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,BUFFERS[buf],msg_hops,self.ground_truth[gt],thr,quorums,msgs_bigM_1)
                            del quorums
                        del results
            else:
                messages = self.compute_meaningful_msgs(msgs_bigM_1,msg_exp_time,algo,1,1)
                self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,msg_hops,messages])
                for gt in range(len(self.ground_truth)):
                    results = self.compute_quorum_vars_on_ground_truth(algo,msgs_bigM_1,states_by_gt[gt],0,gt+1,len(self.ground_truth))
                    for thr in self.thresholds.get(self.ground_truth[gt]):
                        quorums = self.compute_quorum(results[0],results[1],self.min_buff_dim,thr)
                        self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops,self.limit)
                        self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,msg_hops)
                        self.compute_recovery(algo,num_runs,arenaS,communication,n_agents,msg_exp_time,msg_hops,self.ground_truth[gt],thr,quorums,msgs_bigM_1)
                        del quorums
                    del results
            del msgs_M_1,msgs_bigM_1,messages
        if data_type in ("all","freq"):
            act_results = (act_bigM_1,act_bigM_2)
            self.dump_sumof(algo,1,act_results,len(act_M_1),base,path_temp,msg_exp_time,msg_hops)
            act_results = (buff_neglects_bigM,buff_insertin_bigM,buff_updates_bigM)
            self.dump_sumof(algo,3,act_results,len(buff_insertin),base,path_temp,msg_exp_time,msg_hops)
            del act_results
        del num_runs,act_bigM_1,act_bigM_2,act_M_1,act_M_2,buff_insertin,buff_neglects,buff_updates,buff_insertin_bigM,buff_neglects_bigM,buff_updates_bigM
        gc.collect()
                
##########################################################################################################
    def compute_recovery(self,algo,runs,arenaS,communication,n_agents,buf_dim,msg_hops,gt,thr,quorums,buffers):
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
            'msg_hops': msg_hops,
            'ground_truth': gt,
            'threshold': thr
        }
        t_starts, t_ends, b_starts = [], [], []
        starts_cens, ends_cens, = [], []
        limit_buf = int(buf_dim)
        for i in range(len(quorums)):
            for j in range(len(quorums[i])):
                sem = 0
                for t in range(1,len(quorums[i][j])):
                    tmp = []
                    st = 0
                    bf = np.delete(buffers[j][i][t], np.where(buffers[j][i][t] == -1))
                    if algo=='P':
                        if len(bf)>limit_buf:
                            st = len(bf)-limit_buf
                        for z in range(st,len(bf)):
                            if bf[z] not in tmp:
                                tmp.append(bf[z])
                    else: tmp = bf
                    b = len(tmp)
                    if quorums[i][j][t] != quorums[i][j][t-1]:
                        if sem == 0 and b >= self.min_buff_dim and ((gt < thr and quorums[i][j][t] == 1) or (gt >= thr and quorums[i][j][t] == 0)):
                            sem = 1
                            t_starts.append(t+1)
                            b_starts.append(b)
                            starts_cens.append(1)
                        elif sem == 1 and ((gt < thr and quorums[i][j][t] == 0) or (gt >= thr and quorums[i][j][t] == 1)):
                            sem = 0
                            t_ends.append(t+1)
                            ends_cens.append(1)
                    else:
                        if sem == 0 and b >= self.min_buff_dim and ((gt < thr and quorums[i][j][t] == 1) or (gt >= thr and quorums[i][j][t] == 0)):
                            sem = 1
                            t_starts.append(t+1)
                            b_starts.append(b)
                            starts_cens.append(1)
                if sem == 1:
                    t_ends.append(len(quorums[i][j])+1)
                    ends_cens.append(0)
        if len(t_starts) > 0:
            durations,event_observed = [],[]
            for i in range(len(t_starts)):
                durations.append(t_ends[i]-t_starts[i])
                event_observed.append(starts_cens[i]*ends_cens[i])
            self.dump_recovery_raw(external_data,[b_starts,durations,event_observed])


##########################################################################################################
    def dump_recovery_raw(self,external_data,data):
        header = ["experiment_length","broadcast", "n_agents", "buff_dim", "msg_hops", "ground_truth", "threshold", "buff_starts", "durations", "events"]
        filename = os.path.abspath("")+"/proc_data"
        if not os.path.exists(filename):
            os.mkdir(filename)
        filename += "/"+external_data['algorithm']+"recovery_data_raw_r#"+str(external_data['runs'])+"_a#"+external_data['arena']+"A.csv"
        write_header = not os.path.exists(filename)
        with open(filename, mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow([external_data['experiment_length'],external_data['rebroadcast'],external_data['n_agents'],external_data['buff_dim'],external_data['msg_hops'],external_data['ground_truth'],external_data['threshold'],
                                data[0],data[1],data[2]])

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
    def dump_sumof(self,algo,bias,data_in,dMR,BASE,PATH,MSG_EXP_TIME,msg_hops):
        for l in range(len(data_in)):
            multi_run_data = data_in[l]
            flag2 = [-1]*len(multi_run_data[0][0])
            for i in range(len(multi_run_data[0])):
                flag1 = [-1]*len(multi_run_data[0][0])
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
            self.dump_resume_csv(algo,l,bias,np.round(flag2,2).tolist(),"-",BASE,PATH,"-","-","-",MSG_EXP_TIME,msg_hops,dMR)
    
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
            fstd3[z]=self.extract_median(median_array)
        self.dump_resume_csv(algo,0,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,len(data_in))

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,limit):
        times = [len(data_in[0][0])] * len(data_in)
        for i in range(len(data_in)): # per ogni run
            for z in range(len(data_in[i][0])): # per ogni tick
                sum = 0
                for j in range(len(data_in[i])): # per ogni agente
                    sum += data_in[i][j][z]
                if sum >= limit * len(data_in[i]):
                    times[i] = z
                    break
        times = sorted(times)
        self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,msg_hops,len(data_in))

##########################################################################################################
    def extract_median(self,array):
        median = 0
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median