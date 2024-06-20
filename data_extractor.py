import numpy as np
import os, csv, math, gc

class Results:
    thresholds      = {}
    ground_truth    = [.52,.56,.60,.64,.68,.72,.76,.8,.84,.88,.92,.96,1.0]
    min_buff_dim    = 5
    ticks_per_sec   = 10
    x_limit         = 100
    limit           = 0.8
        
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
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,msg_exp_time,sub_path,data_type="all"):
        max_buff_size = n_agents - 1
        act_results = {}
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        msgs_bigM_1 = [np.array([])] * n_agents
        act_bigM_1 = [np.array([])] * n_agents
        act_bigM_2 = [np.array([])] * n_agents
        msgs_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
        act_M_1 = [np.array([],dtype=int)]*num_runs
        act_M_2 = [np.array([],dtype=int)]*num_runs
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
        #####################################################
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem=elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    seed = int(selem[0].split('#')[-1])
                    agent_id = int(selem[0].split('__')[0].split('#')[-1])
                    with open(os.path.join(sub_path, elem), newline='') as f:
                        reader = csv.reader(f)
                        log_count = 0
                        for row in reader:
                            log_count += 1
                            if log_count % self.ticks_per_sec == 0:
                                log_count = 0
                                msgs = []
                                broadcast_c = 0
                                re_broadcast_c = 0
                                for val in row:                                            
                                    if val.count('\t')==0:
                                        if val!='-' : msgs.append(int(val))
                                    else:
                                        val = val.split('\t')
                                        if val[0] != '': msgs.append(int(val[0]))
                                        broadcast_c = int(val[1])
                                        re_broadcast_c = int(val[2])
                                if (data_type=="all" or data_type=="freq"):
                                    act_M_1[seed-1] = np.append(act_M_1[seed-1],broadcast_c)
                                    act_M_2[seed-1] = np.append(act_M_2[seed-1],re_broadcast_c)
                                if len(msgs) < max_buff_size:
                                    for i in range(max_buff_size-len(msgs)): msgs.append(-1)
                                if len(msgs_M_1[seed-1]) == 0:
                                    msgs_M_1[seed-1] = [msgs]
                                else :
                                    msgs_M_1[seed-1] = np.append(msgs_M_1[seed-1],[msgs],axis=0)
                    if len(msgs_M_1[seed-1])!=max_steps: print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(msgs_M_1[seed-1]))
                    if seed == num_runs:
                        msgs_bigM_1[agent_id] = msgs_M_1
                        msgs_M_1 = [np.array([],dtype=int)]*num_runs
                        if (data_type=="all" or data_type=="freq"):
                            act_bigM_1[agent_id] = act_M_1
                            act_bigM_2[agent_id] = act_M_2
                            act_M_1 = [np.array([],dtype=int)]*num_runs
                            act_M_2 = [np.array([],dtype=int)]*num_runs
        if data_type=="all" or data_type=="quorum":
            info_vec     = sub_path.split('/')
            algo     = info_vec[4].split('_')[0][0]
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
                    self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,BUFFERS[buf],messages])
                    for gt in range(len(self.ground_truth)):
                        results = self.compute_quorum_vars_on_ground_truth(algo,msgs_bigM_1,states_by_gt[gt],BUFFERS[buf],gt+1,len(self.ground_truth))
                        for thr in self.thresholds.get(self.ground_truth[gt]):
                            quorums = self.compute_quorum(results[0],results[1],self.min_buff_dim,thr)
                            self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,BUFFERS[buf],self.limit)
                            self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,BUFFERS[buf])
                            recovery_res = self.compute_recovery(algo,self.ground_truth[gt],thr,quorums,msgs_bigM_1,BUFFERS[buf])
                            self.dump_recovery("recovery_resume.csv",[arenaS,algo,communication,n_agents,BUFFERS[buf],self.ground_truth[gt],thr,self.min_buff_dim,recovery_res])
                            del recovery_res, quorums
                            gc.collect()
                        del results
                        gc.collect()
            else:
                messages = self.compute_meaningful_msgs(msgs_bigM_1,msg_exp_time,algo,1,1)
                self.dump_msgs("messages_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,messages])
                for gt in range(len(self.ground_truth)):
                    results = self.compute_quorum_vars_on_ground_truth(algo,msgs_bigM_1,states_by_gt[gt],0,gt+1,len(self.ground_truth))
                    for thr in self.thresholds.get(self.ground_truth[gt]):
                        quorums = self.compute_quorum(results[0],results[1],self.min_buff_dim,thr)
                        self.dump_times(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time,self.limit)
                        self.dump_quorum(algo,0,quorums,base,path_temp,self.ground_truth[gt],thr,self.min_buff_dim,msg_exp_time)
                        recovery_res = self.compute_recovery(algo,self.ground_truth[gt],thr,quorums,msgs_bigM_1,0)
                        self.dump_recovery("recovery_resume.csv",[arenaS,algo,communication,n_agents,msg_exp_time,self.ground_truth[gt],thr,self.min_buff_dim,recovery_res])
                        del recovery_res, quorums
                        gc.collect()
                    del results
                    gc.collect()
        if (data_type=="all" or data_type=="freq"):
            act_results[0] = (act_bigM_1,act_bigM_2)
            self.dump_msg_freq(algo,1,act_results,len(act_M_1),base,path_temp,msg_exp_time)
            del act_results
            gc.collect()
        del act_results,num_runs,msgs_bigM_1,act_bigM_1,act_bigM_2,msgs_M_1,act_M_1,act_M_2
        gc.collect()
                
##########################################################################################################
    def compute_recovery(self,algo,gt,thr,quorums,buffers,limit_buf):
        # if gt < thr compute the steps in which the agents have the wrong state "1" and the buffer lenght
        # if gt >= thr compute the steps in which the agents have the wrong state "0" and the buffer lenght
        t_mins, t_maxs, b_mins, b_maxs, r_mimax = [99999]*2, [-1]*2, [99999]*2, [-1]*2, [99999,-1]
        recoveries, t_starts, t_ends, b_starts, b_ends = [], [], [], [], []
        limit_buf = int(limit_buf)
        for i in range(len(quorums)):
            for j in range(len(quorums[i])):
                recovery = 0
                sem = 0
                for t in range(1,len(quorums[i][j])):
                    if quorums[i][j][t] != quorums[i][j][t-1]:
                        if sem == 0 and ((gt < thr and quorums[i][j][t] == 1) or (gt >= thr and quorums[i][j][t] == 0)):
                            sem = 1
                            if t < t_mins[0]: t_mins[0] = t
                            elif t > t_maxs[0]: t_maxs[0] = t
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
                            if b < b_mins[0]: b_mins[0] = b
                            elif b > b_maxs[0]: b_maxs[0] = b
                            t_starts.append(t)
                            b_starts.append(b)
                            recovery +=1
                        elif sem == 1 and ((gt < thr and quorums[i][j][t] == 0) or (gt >= thr and quorums[i][j][t] == 1)):
                            sem = 0
                            if t < t_mins[1]: t_mins[1] = t
                            elif t > t_maxs[1]: t_maxs[1] = t
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
                            if b < b_mins[1]: b_mins[1] = b
                            elif b > b_maxs[1]: b_maxs[1] = b
                            t_ends.append(t)
                            b_ends.append(b)
                if recovery < r_mimax[0]: r_mimax[0] = recovery
                elif recovery > r_mimax[1]: r_mimax[1] = recovery
                recoveries.append(recovery)
        t_median = [[self.extract_median(t_starts),self.extract_median(t_ends)], t_mins, t_maxs]
        b_median = [[self.extract_median(b_starts),self.extract_median(b_ends)], b_mins, b_maxs]
        return ([self.extract_median(recoveries),r_mimax],t_median,b_median)

##########################################################################################################
    def dump_recovery(self,file_name,data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "ground_truth", "threshold", "min_buff_dim",
                  "recovey_median", "recovery_min", "recovery_max",
                  "start_time_median", "end_time_median", "start_time_min", "end_time_min", "start_time_max", "end_time_max",
                  "start_buff_median", "end_buff_median", "start_buff_min", "end_buff_min", "start_buff_max", "end_buff_max"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "proc_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "proc_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "proc_data"))
        
        with open(os.path.join(os.path.abspath(""), "proc_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow([data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],
                              data[8][0][0],data[8][0][1][0],data[8][0][1][1],
                              data[8][1][0][0],data[8][1][0][1],data[8][1][1][0],data[8][1][1][1],data[8][1][2][0],data[8][1][2][1],
                              data[8][2][0][0],data[8][2][0][1],data[8][2][1][0],data[8][2][1][1],data[8][2][2][0],data[8][2][2][1]])
            
##########################################################################################################
    def dump_msgs(self, file_name, data):
        header = ["arena_size", "algo", "broadcast", "n_agents", "buff_dim", "data"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "msgs_data"))
        
        with open(os.path.join(os.path.abspath(""), "msgs_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow(data)

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,value,data_in,data_std,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,n_runs):    
        static_fields=["committed_perc","threshold","min_buff_dim","msg_exp_time"]
        static_values=[COMMIT,THRESHOLD,MINS,MSG_EXP_TIME]
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
        name_fields.append("mean_value")
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
        values.append(value)
        values.append(data_in)
        values.append(data_std)
        fw = open(os.path.abspath("")+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()

##########################################################################################################
    def dump_msg_freq(self,algo,bias,data_in,dMR,BASE,PATH,MSG_EXP_TIME):
        for l in range(len(data_in.get(0))):
            multi_run_data = data_in.get(0)[l]
            if multi_run_data is not None:
                flag2 = [-1]*len(multi_run_data[0][0])
                for i in range(len([multi_run_data[0]])):
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
                self.dump_resume_csv(algo,l,bias,'-',np.round(flag2,2).tolist(),"-",BASE,PATH,"-","-","-",MSG_EXP_TIME,dMR)
        
##########################################################################################################
    def dump_quorum(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME):
        mean_val = 0
        flag2=[-1]*len(data_in[0][0])
        for i in range(len(data_in)):
            flag1=[-1]*len(data_in[i][0])
            flagmv=[-1]*len(data_in[i])
            for j in range(len(data_in[i])):
                for z in range(len(data_in[i][j])):
                    if flag1[z]==-1:
                        flag1[z]=data_in[i][j][z]
                    else:
                        flag1[z]=flag1[z]+data_in[i][j][z]
                    if flagmv[j]==-1:
                        flagmv[j]=data_in[i][j][z]
                    else:
                        flagmv[j]=flagmv[j]+data_in[i][j][z]
                flagmv[j] = flagmv[j]/len(data_in[i][j])
            for j in flagmv:
                mean_val+=j
            for j in range(len(flag1)):
                flag1[j]=flag1[j]/len(data_in[i])
                if flag2[j]==-1:
                    flag2[j]=flag1[j]
                else:
                    flag2[j]=flag1[j]+flag2[j]
        for i in range(len(flag2)):
            flag2[i]=flag2[i]/len(data_in)
        mean_val = mean_val/len(data_in)
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
        self.dump_resume_csv(algo,0,bias,np.round(mean_val,2),np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,len(data_in))

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,limit):
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
        self.dump_resume_csv(algo,-1,bias,'-',times,'-',BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,len(data_in))

##########################################################################################################
    def extract_median(self,array):
        median = 0
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median