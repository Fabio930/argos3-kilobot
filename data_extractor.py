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
    def rearrange_quorum(self,data):
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
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,threshold,delta,msg_exp_time,msg_hops,sub_path,data_type="all"):
        num_runs = int(len(os.listdir(sub_path))/n_agents)
        states_bigM_1 = [np.array([])] * n_agents
        quorum_bigM_1 = [np.array([])] * n_agents
        msgs_bigM_1 = [np.array([])] * n_agents
        act_bigM_1 = [np.array([])] * n_agents
        act_bigM_2 = [np.array([])] * n_agents
        buff_neglects_bigM = [np.array([])] * n_agents
        buff_insertin_bigM = [np.array([])] * n_agents
        buff_updates_bigM = [np.array([])] * n_agents
        msgs_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
        states_M_1 = [np.array([],dtype=int)]*num_runs
        quorum_M_1 = [np.array([],dtype=int)]*num_runs
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
                    agent_id = int(selem[0].split('#')[-2].split('_')[0])
                    seed = int(selem[0].split('#')[-1])
                    agents_count[agent_id] += 1
                    with open(os.path.join(sub_path, elem), newline='') as f:
                        reader = csv.reader(f)
                        log_count = 0
                        for row in reader:
                            log_count += 1
                            if log_count % self.ticks_per_sec == 0:
                                state = -1
                                msgs = -1
                                broadcast_c = 0
                                re_broadcast_c = 0
                                buf_neglect = 0
                                buf_insert = 0
                                buf_update = 0
                                for val in row:
                                    val             = val.split('\t')
                                    state           = int(val[0])
                                    quorum          = int(val[1])
                                    msgs            = int(val[2])
                                    broadcast_c     = int(val[3])
                                    re_broadcast_c  = int(val[4])
                                    if len(val)>5:
                                        buf_neglect     = int(val[5])
                                        buf_insert      = int(val[6])
                                        buf_update      = int(val[7])
                                if data_type in ("all","quorum"):
                                    states_M_1[seed-1] = np.append(states_M_1[seed-1],state)
                                    quorum_M_1[seed-1] = np.append(quorum_M_1[seed-1],quorum)
                                    msgs_M_1[seed-1] = np.append(msgs_M_1[seed-1],msgs)
                                if data_type in ("all","freq"):
                                    act_M_1[seed-1] = np.append(act_M_1[seed-1],broadcast_c)
                                    act_M_2[seed-1] = np.append(act_M_2[seed-1],re_broadcast_c)
                                    buff_neglects[seed-1] = np.append(buff_neglects[seed-1],buf_neglect)
                                    buff_insertin[seed-1] = np.append(buff_insertin[seed-1],buf_insert)
                                    buff_updates[seed-1] = np.append(buff_updates[seed-1],buf_update)
                    if data_type in ("all","quorum") and len(msgs_M_1[seed-1])!=max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(msgs_M_1[seed-1]))
                    elif data_type in ("freq") and len(act_M_1[seed-1])!=max_steps:
                        print(sub_path,'\n',"run:",seed,"agent:",agent_id,"tot lines:",len(act_M_1[seed-1]))
                    if agents_count[agent_id]==num_runs:
                        if data_type in ("all","quorum"):
                            msgs_bigM_1[agent_id] = msgs_M_1
                            states_bigM_1[agent_id] = states_M_1
                            quorum_bigM_1[agent_id] = quorum_M_1
                            msgs_M_1 = [np.array([],dtype=int)]*num_runs
                            states_M_1 = [np.array([],dtype=int)]*num_runs
                            quorum_M_1 = [np.array([],dtype=int)]*num_runs
                        if  data_type in ("all","freq"):
                            act_bigM_1[agent_id] = act_M_1
                            act_bigM_2[agent_id] = act_M_2
                            buff_neglects_bigM[agent_id] = buff_neglects
                            buff_insertin_bigM[agent_id] = buff_insertin
                            buff_updates_bigM[agent_id] = buff_updates
                            act_M_1 = [np.array([],dtype=int)]*num_runs
                            act_M_2 = [np.array([],dtype=int)]*num_runs
                            buff_neglects = [np.array([],dtype=int)]*num_runs
                            buff_insertin = [np.array([],dtype=int)]*num_runs
                            buff_updates = [np.array([],dtype=int)]*num_runs
        algo    = ""
        arenaS  = ""
        info_vec    = sub_path.split('/')
        for iv in info_vec:
            if "results_loop" in iv:
                algo        = iv[0]
                arenaS      = iv.split('_')[-1][:-1]
                break
        if data_type in ("all","quorum"):
            t_messages  = info_vec[-2].split('#')[-1]
            messages    = self.compute_avg_msgs(msgs_bigM_1)
            self.dump_msgs("messages_resume.csv", [arenaS, algo, threshold, delta, communication, msg_hops, n_agents, t_messages, messages])
            del messages
            states = self.rearrange_quorum(quorum_bigM_1)
            self.dump_times(algo,0,states,base,path_temp,threshold,delta,self.min_buff_dim,msg_exp_time,msg_hops,n_agents,self.limit)
            self.dump_quorum(algo,0,states,base,path_temp,threshold,delta,self.min_buff_dim,msg_exp_time,msg_hops,n_agents)
            del states
        if  data_type in ("all","freq"):
            act_results = (act_bigM_1,act_bigM_2)
            self.dump_sumof(algo,1,act_results,len(act_M_1),base,path_temp,msg_exp_time,msg_hops)
            act_results = (buff_neglects_bigM,buff_insertin_bigM,buff_updates_bigM)
            self.dump_sumof(algo,3,act_results,len(buff_insertin),base,path_temp,msg_exp_time,msg_hops)
            del act_results
        del states_bigM_1,quorum_bigM_1,msgs_bigM_1,act_bigM_1,act_bigM_2,msgs_M_1,quorum_M_1,states_M_1,act_M_1,act_M_2,buff_insertin,buff_neglects,buff_updates,buff_insertin_bigM,buff_neglects_bigM,buff_updates_bigM
        gc.collect()

##########################################################################################################
    def dump_msgs(self, file_name, data):
        header = ["ArenaSize", "algo", "threshold", "delta_GT", "broadcast","msg_hops", "n_agents", "buff_dim", "data"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "msgs_data"))
        
        with open(os.path.join(os.path.abspath(""), "msgs_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow(data)

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,data_in,data_std,base,path,MINS,MSG_EXP_TIME,msg_hops,n_runs):    
        static_fields=["MinBuffDim","MsgExpTime","MsgHops"]
        static_values=[MINS,MSG_EXP_TIME,msg_hops]
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
            self.dump_resume_csv(algo,l,bias,np.round(flag2,2).tolist(),"-",BASE,PATH,"-",MSG_EXP_TIME,msg_hops,dMR)

##########################################################################################################
    def dump_quorum(self,algo,bias,data_in,BASE,PATH,THR,COMMIT,MINS,MSG_EXP_TIME,msg_hops,n_agents):
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
        self.dump_resume_csv(algo,0,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,MINS,MSG_EXP_TIME,msg_hops,len(data_in))

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,THR,COMMIT,MINS,MSG_EXP_TIME,msg_hops,n_agents,limit):
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
        self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,MINS,MSG_EXP_TIME,msg_hops,len(data_in))

##########################################################################################################
    def extract_median(self,array):
        median = 0
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median