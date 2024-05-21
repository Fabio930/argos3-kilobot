import numpy as np
import os, csv, math, sys

class Results:
    min_buff_dim = [5]
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
                if selem[0]=="Oresults":
                    self.bases.append(os.path.join(self.base, elem))

#########################################################################################################
    def compute_quorum_dim(self,msgs_states):
        tmp_dim_0 = [np.array([])]*len(msgs_states[0])
        tmp_ones_0 = [np.array([])]*len(msgs_states[0])
        for i in range(len(msgs_states[0])):
            tmp_dim_1 = [np.array([])]*len(msgs_states)
            tmp_ones_1 = [np.array([])]*len(msgs_states)
            for j in range(len(msgs_states)):
                tmp_dim_2 = []
                tmp_ones_2 = []
                for t in range(len(msgs_states[j][i])):
                    dim = 0
                    ones = 0
                    for z in range(len(msgs_states[j][i][t])):
                        if(msgs_states[j][i][t][z] == -1):
                            break
                        dim += 1
                        ones += msgs_states[j][i][t][z]
                    tmp_dim_2.append(dim)
                    tmp_ones_2.append(ones)
                tmp_dim_1[j] = tmp_dim_2
                tmp_ones_1[j] = tmp_ones_2
            tmp_dim_0[i] = tmp_dim_1
            tmp_ones_0[i] = tmp_ones_1
        return (tmp_dim_0,tmp_ones_0)
    
#########################################################################################################
    def compute_quorum(self,m1,m2,minus,threshold):
        out = np.copy(m1)
        for i in range(len(m1)):
            for j in range(len(m1[i])):
                for k in range(len(m1[i][j])):
                    out[i][j][k] = 1 if m1[i][j][k] >= minus and m2[i][j][k] >= threshold * m1[i][j][k] else 0
        return out
        
##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,threshold,delta,data_type="all"):
        max_buff_size = n_agents - 1
        for pre_folder in sorted(os.listdir(path_temp)):
            if '.' not in pre_folder:
                pre_params = pre_folder.split('#')
                msg_exp_time = int(pre_params[-1])
                sub_path = os.path.join(path_temp,pre_folder)
                act_results = {}
                num_runs = int(len(os.listdir(sub_path))/n_agents)
                states_bigM_1 = [np.array([])] * n_agents
                msgs_id_bigM_1 = [np.array([])] * n_agents
                msgs_state_bigM_1 = [np.array([])] * n_agents
                act_bigM_1 = [np.array([])] * n_agents
                act_bigM_2 = [np.array([])] * n_agents
                msgs_id_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
                msgs_state_M_1 = [np.array([],dtype=int)]*num_runs
                states_M_1 = [np.array([],dtype=int)]*num_runs
                act_M_1 = [np.array([],dtype=int)]*num_runs
                act_M_2 = [np.array([],dtype=int)]*num_runs
                # assign randomly the state to agents at each run
                print("--- Path ---")
                print(sub_path,"\n")
                print("--- Extract data ---")
                a_ = 0
                prev_id = -1
                for elem in sorted(os.listdir(sub_path)):
                    if '.' in elem:
                        selem=elem.split('.')
                        if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                            a_+=1
                            seed = int(selem[0].split('#')[-1])
                            agent_id = int(selem[0].split('__')[0].split('#')[-1])
                            if prev_id != agent_id:
                                a_ = 0
                            if a_ == 0:
                                print("- Reading files of agent",agent_id)
                                prev_id = agent_id
                            with open(os.path.join(sub_path, elem), newline='') as f:
                                reader = csv.reader(f)
                                log_count = 0
                                for row in reader:
                                    log_count += 1
                                    if log_count % self.ticks_per_sec == 0:
                                        msgs_id = []
                                        msgs_state = []
                                        state = -1
                                        broadcast_c = 0
                                        re_broadcast_c = 0
                                        sem = 0
                                        for val in row:
                                            if val.count('\t')==0:
                                                if sem == 1: msgs_state.append(int(val))
                                                elif sem == 2: msgs_id.append(int(val))
                                            else:
                                                val = val.split('\t')
                                                if sem == 0:
                                                    if log_count<=30:
                                                        sem = 0
                                                        state = int(val[0])
                                                        broadcast_c = int(val[1])
                                                        re_broadcast_c = int(val[2])
                                                    else:
                                                        if len(val) == 5:
                                                            sem = 0
                                                            state = int(val[0])
                                                            msgs_state.append(int(val[1]))
                                                            msgs_id.append(int(val[2]))
                                                            broadcast_c = int(val[3])
                                                            re_broadcast_c = int(val[4])
                                                        elif len(val) == 3:
                                                            state = int(val[0])
                                                            broadcast_c = int(val[1])
                                                            re_broadcast_c = int(val[2])
                                                        else:
                                                            sem = 1
                                                            state = int(val[0])
                                                            msgs_state.append(int(val[1]))
                                                elif sem == 1:
                                                    sem = 2
                                                    msgs_state.append(int(val[0]))
                                                    msgs_id.append(int(val[1]))
                                                else:
                                                    sem = 0
                                                    msgs_id.append(int(val[0]))
                                                    broadcast_c = int(val[1])
                                                    re_broadcast_c = int(val[2])
                                        states_M_1[seed-1] = np.append(states_M_1[seed-1],state)
                                        act_M_1[seed-1] = np.append(act_M_1[seed-1],broadcast_c)
                                        act_M_2[seed-1] = np.append(act_M_2[seed-1],re_broadcast_c)
                                        if len(msgs_id) < max_buff_size:
                                            for i in range(max_buff_size-len(msgs_id)):
                                                msgs_state.append(-1)
                                                msgs_id.append(-1)
                                        if len(msgs_id_M_1[seed-1]) == 0:
                                            msgs_state_M_1[seed-1] = [msgs_state]
                                            msgs_id_M_1[seed-1] = [msgs_id]
                                        else :
                                            msgs_state_M_1[seed-1] = np.append(msgs_state_M_1[seed-1],[msgs_state],axis=0)
                                            msgs_id_M_1[seed-1] = np.append(msgs_id_M_1[seed-1],[msgs_id],axis=0)
                            if len(msgs_id_M_1[seed-1])!=max_steps: print(seed,len(msgs_id_M_1[seed-1]),len(msgs_id_M_1[seed-1][-1]))
                            if seed == num_runs:
                                msgs_state_bigM_1[agent_id] = msgs_state_M_1
                                msgs_id_bigM_1[agent_id] = msgs_id_M_1
                                states_bigM_1[agent_id] = states_M_1
                                act_bigM_1[agent_id] = act_M_1
                                act_bigM_2[agent_id] = act_M_2

                                msgs_state_M_1 = [np.array([],dtype=int)]*num_runs
                                msgs_id_M_1 = [np.array([],dtype=int)]*num_runs
                                states_M_1 = [np.array([],dtype=int)]*num_runs
                                act_M_1 = [np.array([],dtype=int)]*num_runs
                                act_M_2 = [np.array([],dtype=int)]*num_runs
                if data_type=="all" or data_type=="quorum":
                    results = self.compute_quorum_dim(msgs_state_bigM_1)
                    for mbd in self.min_buff_dim:
                        quorum_results = {}
                        states = self.compute_quorum(results[0],results[1],mbd,threshold)
                        quorum_results[(threshold+delta,mbd,threshold)] = (states,results[0])
                        self.dump_times(0,quorum_results,base,path_temp,threshold,threshold+delta,mbd,msg_exp_time,n_agents,self.limit)
                        self.dump_quorum_and_buffer(0,quorum_results,base,path_temp,threshold,threshold+delta,mbd,msg_exp_time,n_agents)
                                
                act_results[0] = (act_bigM_1,act_bigM_2)
                if (data_type=="all" or data_type=="freq"):
                    self.dump_msg_freq(2,act_results,len(act_M_1),base,path_temp,msg_exp_time,n_agents)

##########################################################################################################
    def dump_resume_csv(self,indx,bias,value,data_in,data_std,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,n_runs,n_agents):    
        static_fields=["CommittedPerc","Threshold","MinBuffDim","MsgExpTime"]
        static_values=[COMMIT,THRESHOLD,MINS,MSG_EXP_TIME]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        file_name = "Oaverage_resume_r#"+str(n_runs)+"_a#"+str(n_agents)+".csv"
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
            values.append("quorum_length")
        elif indx+bias==2:
            values.append("broadcast_msg")
        elif indx+bias==3:
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
    def dump_msg_freq(self,bias,data_in,dMR,BASE,PATH,MSG_EXP_TIME,n_agents):
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
                ###################################################
                fstd2=[[-1]*len(multi_run_data[0][0])]*len(multi_run_data[0])
                fstd3=[-1]*len(multi_run_data[0][0])
                for i in range(len(multi_run_data[0])):
                    fstd1=[-1]*len(multi_run_data[0][0])
                    for z in range(len(multi_run_data[0][0])): # per ogni tick
                        std_tmp = []
                        for j in range(len(multi_run_data)): # per ogni agente
                            std_tmp.append(float(multi_run_data[j][i][z]))
                        fstd1[z]=np.std(std_tmp)
                    fstd2[i] = fstd1
                for z in range(len(fstd3)):
                    median_array = []
                    for i in range(len(fstd2)):
                        median_array.append(fstd2[i][z])
                    fstd3[z]=self.extract_median(median_array)
                self.dump_resume_csv(l,bias,'-',np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,"-","-","-",MSG_EXP_TIME,dMR,n_agents)
        
##########################################################################################################
    def dump_quorum_and_buffer(self,bias,data_in,BASE,PATH,THR,COMMIT,MINS,MSG_EXP_TIME,n_agents):
        if data_in.get((COMMIT,MINS,THR)) is not None:
            for l in range(len(data_in.get((COMMIT,MINS,THR)))):
                if data_in.get((COMMIT,MINS,THR))[l] is not None:
                    mean_val = 0
                    multi_run_data = (data_in.get((COMMIT,MINS,THR)))[l]
                    flag2=[-1]*len(multi_run_data[0][0])
                    for i in range(len(multi_run_data)):
                        flag1=[-1]*len(multi_run_data[i][0])
                        flagmv=[-1]*len(multi_run_data[i])
                        for j in range(len(multi_run_data[i])):
                            for z in range(len(multi_run_data[i][j])):
                                if flag1[z]==-1:
                                    flag1[z]=multi_run_data[i][j][z]
                                else:
                                    flag1[z]=flag1[z]+multi_run_data[i][j][z]
                                if flagmv[j]==-1:
                                    flagmv[j]=multi_run_data[i][j][z]
                                else:
                                    flagmv[j]=flagmv[j]+multi_run_data[i][j][z]
                            flagmv[j] = flagmv[j]/len(multi_run_data[i][j])
                        for j in flagmv:
                            mean_val+=j
                        for j in range(len(flag1)):
                            flag1[j]=flag1[j]/len(multi_run_data[i])
                            if flag2[j]==-1:
                                flag2[j]=flag1[j]
                            else:
                                flag2[j]=flag1[j]+flag2[j]
                    for i in range(len(flag2)):
                        flag2[i]=flag2[i]/len(multi_run_data)
                    mean_val = mean_val/len(multi_run_data)
                    ###################################################
                    fstd2=[[-1]*len(multi_run_data[0][0])]*len(multi_run_data)
                    fstd3=[-1]*len(multi_run_data[0][0])
                    for i in range(len(multi_run_data)):
                        fstd1=[-1]*len(multi_run_data[i][0])
                        for z in range(len(multi_run_data[i][0])): # per ogni tick
                            std_tmp = []
                            for j in range(len(multi_run_data[i])): # per ogni agente
                                std_tmp.append(float(multi_run_data[i][j][z]))
                            fstd1[z]=np.std(std_tmp)
                        fstd2[i]=fstd1
                    for z in range(len(fstd3)):
                        median_array = []
                        for i in range(len(fstd2)):
                            median_array.append(fstd2[i][z])
                        fstd3[z]=self.extract_median(median_array)
                    ###################################################
                    if l==0:
                        self.dump_resume_csv(l,bias,np.round(mean_val,2),np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,len(multi_run_data),n_agents)
                    else:
                        self.dump_resume_csv(l,bias,'-',np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,len(multi_run_data),n_agents)

##########################################################################################################
    def dump_times(self,bias,data_in,BASE,PATH,THR,COMMIT,MINS,MSG_EXP_TIME,n_agents,limit):
        if data_in.get((COMMIT,MINS,THR)) is not None:
            multi_run_data = (data_in.get((COMMIT,MINS,THR)))[0]
            times = [len(multi_run_data[0][0])] * len(multi_run_data)
            for i in range(len(multi_run_data)): # per ogni run
                for z in range(len(multi_run_data[i][0])): # per ogni tick
                    sum = 0
                    for j in range(len(multi_run_data[i])): # per ogni agente
                        sum += multi_run_data[i][j][z]
                    if sum >= limit * len(multi_run_data[i]):
                        times[i] = z
                        break
            times = sorted(times)
            self.dump_resume_csv(-1,bias,'-',times,'-',BASE,PATH,COMMIT,THR,MINS,MSG_EXP_TIME,len(multi_run_data),n_agents)

##########################################################################################################
    def extract_median(self,array):
        median = 0
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median