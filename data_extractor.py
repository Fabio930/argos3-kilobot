import numpy as np
import os, csv, math, gc

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
                if selem[0] in ("Oresults","Presults"):
                    self.bases.append(os.path.join(self.base, elem))
    
#########################################################################################################
    def rearrange_matrix(self,data):
        return np.transpose(data, (1,0,2))

##########################################################################################################
    def compute_avg_msgs(self,data):
        print("--- Computing avg buffer dimension ---")
        out = [0]*len(data[0][0])
        for i in range(len(data)):
            for j in range(len(data[i])):
                for t in range(len(data[i][j])):
                    out[t]+=data[i][j][t]
        for t in range(len(out)):
            out[t] = out[t]/(len(data)*len(data[0]))
        return out
    
##########################################################################################################
    def extract_k_data(self,base,max_steps,communication,n_agents,threshold,GT,msg_exp_time,sub_path,data_type="all"):
        act_results = {}
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        states_bigM_1 = [np.array([])] * n_agents
        quorum_bigM_1 = [np.array([])] * n_agents
        msgs_bigM_1 = [np.array([])] * n_agents
        act_bigM_1 = [np.array([])] * n_agents
        act_bigM_2 = [np.array([])] * n_agents
        msgs_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
        states_M_1 = [np.array([],dtype=int)]*num_runs
        quorum_M_1 = [np.array([],dtype=int)]*num_runs
        act_M_1 = [np.array([],dtype=int)]*num_runs
        act_M_2 = [np.array([],dtype=int)]*num_runs
        for elem in sorted(os.listdir(sub_path)):
            if '.' in elem:
                selem = elem.split('.')
                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                    seed = int(selem[0].split('#')[-1])
                    agent_id = int(selem[0].split('__')[0].split('#')[-1])
                    with open(os.path.join(sub_path, elem), newline='') as f:
                        reader = csv.reader(f)
                        log_count = 0
                        for row in reader:
                            log_count += 1
                            if log_count % self.ticks_per_sec == 0:
                                state           = -1
                                msgs            = -1
                                broadcast_c     = -1
                                re_broadcast_c  = -1
                                for val in row:
                                    val             = val.split('\t')
                                    state           = int(val[0])
                                    quorum          = int(val[1])
                                    msgs            = int(val[2])
                                    broadcast_c     = int(val[3])
                                    re_broadcast_c  = int(val[4])
                                states_M_1[seed-1]  = np.append(states_M_1[seed-1],state)
                                quorum_M_1[seed-1]  = np.append(quorum_M_1[seed-1],quorum)
                                msgs_M_1[seed-1]    = np.append(msgs_M_1[seed-1],msgs)
                                if (data_type=="all" or data_type=="freq"):
                                    act_M_1[seed-1] = np.append(act_M_1[seed-1],broadcast_c)
                                    act_M_2[seed-1] = np.append(act_M_2[seed-1],re_broadcast_c)
                    if len(msgs_M_1[seed-1])!=max_steps: print(sub_path,'\n',"run:",seed,"agent:",agent_id,"num lines:",len(msgs_M_1[seed-1]))
                    if seed == num_runs:
                        msgs_bigM_1[agent_id]       = msgs_M_1
                        states_bigM_1[agent_id]     = states_M_1
                        quorum_bigM_1[agent_id]     = quorum_M_1
                        msgs_M_1                    = [np.array([],dtype=int)]*num_runs
                        states_M_1                  = [np.array([],dtype=int)]*num_runs
                        quorum_M_1                  = [np.array([],dtype=int)]*num_runs
                        if (data_type=="all" or data_type=="freq"):
                            act_bigM_1[agent_id]    = act_M_1
                            act_bigM_2[agent_id]    = act_M_2
                            act_M_1                 = [np.array([],dtype=int)]*num_runs
                            act_M_2                 = [np.array([],dtype=int)]*num_runs
        if data_type in ("all","quorum"):
            info_vec    = sub_path.split('/')
            t_messages  = sub_path.split('#')[-1]
            algo        = info_vec[4].split('_')[0][0]
            arenaS      = info_vec[6].split('#')[-1]
            messages    = self.compute_avg_msgs(msgs_bigM_1)
            self.dump_msgs("messages_resume.csv", [arenaS, algo, threshold, GT, communication, n_agents, t_messages, messages])
            del messages
            gc.collect()
            quorums = self.rearrange_matrix(quorum_bigM_1)
            states = self.rearrange_matrix(states_bigM_1)
            # -----------------------------------
            statescpy = [[0]*len(states[0])]*len(states)
            for i in range(len(states)):
                for j in range(len(states[i])):
                    statescpy[i][j] = states[i][j][-1]
            # -----------------------------------
            self.dump_times(algo,0,quorums,base,sub_path,self.min_buff_dim,msg_exp_time,n_agents,self.limit)
            self.dump_quorum(algo,0,quorums,statescpy,base,sub_path,self.min_buff_dim,msg_exp_time)
            del quorums, states, statescpy
            gc.collect()
        if (data_type=="all" or data_type=="freq"):
            act_results[0] = (act_bigM_1,act_bigM_2)
            self.dump_msg_freq(algo,3,act_results,len(act_M_1),base,sub_path,msg_exp_time,n_agents)
            del act_results
            gc.collect()
        del states_bigM_1,quorum_bigM_1,msgs_bigM_1,act_bigM_1,act_bigM_2,msgs_M_1,quorum_M_1,states_M_1,act_M_1,act_M_2,
        gc.collect()

##########################################################################################################
    def dump_msgs(self, file_name, data):
        header = ["ArenaSize", "algo", "threshold", "GT", "broadcast", "n_agents", "buff_dim", "data"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "msgs_data"))
        
        with open(os.path.join(os.path.abspath(""), "msgs_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow(data)

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
        if algo == 'O':
            file_name = "Oaverage_resume_r#"+str(n_runs)+"_a#"+tmp_p[6].split('#')[1].replace('_',',')+".csv"
        else:
            file_name = "Paverage_resume_r#"+str(n_runs)+"_a#"+tmp_p[6].split('#')[1].replace('_',',')+".csv"
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
        name_fields.append("std")
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
        fw = open(os.path.abspath("")+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()

##########################################################################################################
    def dump_msg_freq(self,algo,bias,data_in,dMR,BASE,PATH,MSG_EXP_TIME,n_agents):
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
                self.dump_resume_csv(algo,l,bias,np.round(flag2,2).tolist(),"-",BASE,PATH,"-",MSG_EXP_TIME,dMR)
        
##########################################################################################################
    def count_committed_agents(self,data):
        ones = -1
        for i in range(len(data)):
            tmp = 0
            for j in range(len(data[i])):
                if data[i][j]==1:
                    tmp+=1
            if ones == -1: ones = tmp
            elif ones != tmp:
                print("ERROR! Number of committed agents change through iterations ---EXIT---")
                exit(1)
        return ones

##########################################################################################################
    def dump_quorum(self,algo,bias,q_data,s_data,BASE,PATH,MINS,MSG_EXP_TIME):
        flag2=[-1]*len(q_data[0][0])
        committed_count = self.count_committed_agents(s_data)
        comm_flag2=[-1]*len(q_data[0][0])
        uncomm_flag2=[-1]*len(q_data[0][0])
        for i in range(len(q_data)):
            flag1=[-1]*len(q_data[i][0])
            comm_flag1=[-1]*len(q_data[i][0])
            uncomm_flag1=[-1]*len(q_data[i][0])
            for j in range(len(q_data[i])):
                for z in range(len(q_data[i][j])):
                    if flag1[z]==-1:
                        flag1[z]=q_data[i][j][z]
                    else:
                        flag1[z]=flag1[z]+q_data[i][j][z]
                    if s_data[i][j]==0:
                        if uncomm_flag1[z]==-1:
                            uncomm_flag1[z]=q_data[i][j][z]
                        else:
                            uncomm_flag1[z]=uncomm_flag1[z]+q_data[i][j][z]
                    elif s_data[i][j]==1:
                        if comm_flag1[z]==-1:
                            comm_flag1[z]=q_data[i][j][z]
                        else:
                            comm_flag1[z]=comm_flag1[z]+q_data[i][j][z]
            for j in range(len(flag1)):
                flag1[j]        = flag1[j]/len(q_data[i])
                comm_flag1[j]   = comm_flag1[j]/committed_count
                uncomm_flag1[j] = uncomm_flag1[j]/(len(q_data[i])-committed_count)
                if flag2[j]==-1:
                    flag2[j]=flag1[j]
                else:
                    flag2[j]=flag1[j]+flag2[j]
                if comm_flag2[j]==-1:
                    comm_flag2[j]=comm_flag1[j]
                else:
                    comm_flag2[j]=comm_flag1[j]+comm_flag2[j]
                if uncomm_flag2[j]==-1:
                    uncomm_flag2[j]=uncomm_flag1[j]
                else:
                    uncomm_flag2[j]=uncomm_flag1[j]+uncomm_flag2[j]
        for i in range(len(flag2)):
            flag2[i]        = flag2[i]/len(q_data)
            comm_flag2[i]   = comm_flag2[i]/len(q_data)
            uncomm_flag2[i] = uncomm_flag2[i]/len(q_data)
        fstd2=[[-1]*len(q_data[0][0])]*len(q_data)
        fstd3=[-1]*len(q_data[0][0])
        for i in range(len(q_data)):
            fstd1=[-1]*len(q_data[i][0])
            for z in range(len(q_data[i][0])): # per ogni tick
                std_tmp = []
                for j in range(len(q_data[i])): # per ogni agente
                    std_tmp.append(float(q_data[i][j][z]))
                fstd1[z]=np.std(std_tmp)
            fstd2[i]=fstd1
        for z in range(len(fstd3)):
            median_array = []
            for i in range(len(fstd2)):
                median_array.append(fstd2[i][z])
            fstd3[z]=self.extract_median(median_array)
        self.dump_resume_csv(algo,0,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,MINS,MSG_EXP_TIME,len(q_data))
        self.dump_resume_csv(algo,1,bias,np.round(comm_flag2,2).tolist(),"-",BASE,PATH,MINS,MSG_EXP_TIME,len(q_data))
        self.dump_resume_csv(algo,2,bias,np.round(uncomm_flag2,2).tolist(),"-",BASE,PATH,MINS,MSG_EXP_TIME,len(q_data))

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,MINS,MSG_EXP_TIME,n_agents,limit):
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
        self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,MINS,MSG_EXP_TIME,len(data_in))

##########################################################################################################
    def extract_median(self,array):
        median = 0
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median