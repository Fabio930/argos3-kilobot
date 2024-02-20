import numpy as np
import os, csv, math, sys

class Results:
    thresholds = {}
    ground_truth = [.52,.56,.60,.64,.68,.72,.76,.8,.84,.88,.92,.96,1.0]
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
        for gt in range(len(self.ground_truth)):
            _thresholds=np.arange(50,int(self.ground_truth[gt]*100)+1,1)
            f_thresholds = []
            for t in range(len(_thresholds)): f_thresholds.append(round(float(_thresholds[t])*.01,2))
            self.thresholds.update({self.ground_truth[gt]:f_thresholds})


#########################################################################################################
    def compute_quorum_vars_on_ground_truth(self,m1,states):
        print("-- Computing agents' states")
        out = {}
        max_compl = len(states)*len(states[0])*len(states[0][0])*len(m1[0][0])*len(m1[0][0][0])
        compl = 0
        for i in range(len(states)):
            tmp_dim_0 = [np.array([])]*len(m1[0])
            tmp_ones_0 = [np.array([])]*len(m1[0])
            for j in range(len(states[i])):
                tmp_dim_1 = [np.array([])]*len(m1)
                tmp_ones_1 = [np.array([])]*len(m1)
                for k in range(len(states[i][j])):
                    tmp_dim_2 = []
                    tmp_ones_2 = []
                    for t in range(len(m1[k][j])):
                        dim = 1
                        ones = states[i][j][k]
                        for z in range(len(m1[k][j][t])):
                            if(m1[k][j][t][z] == -1):
                                compl += len(m1[0][0][0])-z
                                sys.stdout.write("- Computing ... %s%%\r" %(round((compl/max_compl)*100,3)))
                                sys.stdout.flush()
                                break
                            dim += 1
                            ones += states[i][j][m1[k][j][t][z]]
                            compl += 1
                            sys.stdout.write("- Computing ... %s%%\r" %(round((compl/max_compl)*100,3)))
                            sys.stdout.flush()
                        tmp_dim_2.append(dim)
                        tmp_ones_2.append(ones)
                    tmp_dim_1[k] = tmp_dim_2
                    tmp_ones_1[k] = tmp_ones_2
                tmp_dim_0[j] = tmp_dim_1
                tmp_ones_0[j] = tmp_ones_1
            out[self.ground_truth[i]] = (tmp_dim_0,tmp_ones_0)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return out
    
#########################################################################################################
    def compute_quorum(self,m1,m2,minus,threshold,):
        out = np.copy(m1)
        for i in range(len(m1)):
            for j in range(len(m1[i])):
                for k in range(len(m1[i][j])):
                    out[i][j][k] = 1 if m1[i][j][k]-1 >= minus and m2[i][j][k] >= threshold * m1[i][j][k] else 0
        return out
        
##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,max_buff_size,data_type="all"):
        for pre_folder in sorted(os.listdir(path_temp)):
            if '.' not in pre_folder:
                pre_params = pre_folder.split('#')
                msg_exp_time = int(pre_params[-1])
                sub_path = os.path.join(path_temp,pre_folder)
                msgs_results = {}
                act_results = {}
                num_runs = int(len(os.listdir(sub_path))/n_agents)
                p = np.random.choice(np.arange(num_runs))
                msgs_bigM_1 = [np.array([])] * n_agents
                act_bigM_1 = [np.array([])] * n_agents
                act_bigM_2 = [np.array([])] * n_agents
                msgs_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
                act_M_1 = [np.array([],dtype=int)]*num_runs
                act_M_2 = [np.array([],dtype=int)]*num_runs
                # assign randomly the state to agents at each run
                print(sub_path)
                print("--- Assigning states ---")
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
                                        log_count = 0
                                        msgs = []
                                        broadcast_c = 0
                                        re_broadcast_c = 0
                                        for val in row:                                            
                                            if val.count('\t')==0:
                                                msgs.append(int(val))
                                            else:
                                                val = val.split('\t')
                                                if val[0] != '': msgs.append(int(val[0]))
                                                broadcast_c = val[1]
                                                re_broadcast_c = val[2]
                                        act_M_1[seed-1] = np.append(act_M_1[seed-1],broadcast_c)
                                        act_M_2[seed-1] = np.append(act_M_2[seed-1],re_broadcast_c)
                                        if len(msgs) < max_buff_size:
                                            for i in range(max_buff_size-len(msgs)): msgs.append(-1)
                                        if len(msgs_M_1[seed-1]) == 0:
                                            msgs_M_1[seed-1] = [msgs]
                                        else :
                                            msgs_M_1[seed-1] = np.append(msgs_M_1[seed-1],[msgs],axis=0)
                            if len(msgs_M_1[seed-1])!=max_steps: print(seed,len(msgs_M_1[seed-1]),len(msgs_M_1[seed-1][-1]))
                            if seed == num_runs:
                                msgs_bigM_1[agent_id] = msgs_M_1
                                act_bigM_1[agent_id] = act_M_1
                                act_bigM_2[agent_id] = act_M_2
                                msgs_M_1 = [np.array([],dtype=int)]*num_runs
                                act_M_1 = [np.array([],dtype=int)]*num_runs
                                act_M_2 = [np.array([],dtype=int)]*num_runs
                results = self.compute_quorum_vars_on_ground_truth(msgs_bigM_1,states_by_gt)
                max_compl = len(self.ground_truth)*len(self.min_buff_dim)
                compl = 0
                for gt in range(len(self.ground_truth)):
                    for minus in self.min_buff_dim:
                        for thr in self.thresholds.get(self.ground_truth[gt]):
                            compl += 1/len(self.thresholds.get(self.ground_truth[gt]))
                            msgs_results[(self.ground_truth[gt],minus,thr)] = (self.compute_quorum(results.get(self.ground_truth[gt])[0],results.get(self.ground_truth[gt])[1],minus,thr),results.get(self.ground_truth[gt])[0])
                            sys.stdout.write("- Rolling ground truth and threshold ... %s%%\r" %(round((compl/max_compl)*100,3)))
                            sys.stdout.flush()
                sys.stdout.write("\n")
                sys.stdout.flush()         
                act_results[0] = (act_bigM_1,act_bigM_2)
                self.ground_truth,self.min_buff_dim = np.sort(self.ground_truth),np.sort(self.min_buff_dim)
                if data_type=="all" or data_type=="quorum":
                    self.dump_times(0,msgs_results,base,path_temp,self.ground_truth,self.min_buff_dim,msg_exp_time,self.limit)
                    self.dump_quorum_and_buffer(0,msgs_results,base,path_temp,self.ground_truth,self.min_buff_dim,msg_exp_time)
                if (data_type=="all" or data_type=="freq"):
                    self.dump_msg_freq(2,act_results,msgs_results,base,path_temp,msg_exp_time)
                print("")

##########################################################################################################
    def dump_resume_csv(self,indx,bias,data_in,data_std,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,n_runs):    
        static_fields=["CommittedPerc","Threshold","MinBuffDim","MsgExpTime"]
        static_values=[COMMIT,THRESHOLD,MINS,MSG_EXP_TIME]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        file_name = "Oaverage_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
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
            values.append("quorum_length")
        elif indx+bias==2:
            values.append("broadcast_msg")
        elif indx+bias==3:
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
    def dump_msg_freq(self,bias,data_in,ddata,BASE,PATH,MSG_EXP_TIME):
        print("-- Dumping messages frequency")
        dMR = (ddata.get((self.ground_truth[0],self.min_buff_dim[0],self.thresholds.get(self.ground_truth[0])[0])))[0]
        for l in range(len(data_in.get(0))):
            multi_run_data = data_in.get(0)[l]
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
            self.dump_resume_csv(l,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,"-","-","-",MSG_EXP_TIME,len(dMR))
        
##########################################################################################################
    def dump_quorum_and_buffer(self,bias,data_in,BASE,PATH,COMMIT,MINS,MSG_EXP_TIME):
        print("-- Dumping average quorum data")
        for m in range(len(MINS)):
            for r in COMMIT:
                for t in range(len(self.thresholds.get(r))):
                    for l in range(len(data_in.get((r,MINS[m],self.thresholds.get(r)[t])))):
                        if data_in.get((r,MINS[m],self.thresholds.get(r)[t]))[l] is not None:
                            multi_run_data = (data_in.get((r,MINS[m],self.thresholds.get(r)[t])))[l]
                            flag2=[-1]*len(multi_run_data[0][0])
                            for i in range(len(multi_run_data)):
                                flag1=[-1]*len(multi_run_data[i][0])
                                for j in range(len(multi_run_data[i])):
                                    for z in range(len(multi_run_data[i][j])):
                                        if flag1[z]==-1:
                                            flag1[z]=multi_run_data[i][j][z]
                                        else:
                                            flag1[z]=flag1[z]+multi_run_data[i][j][z]
                                for j in range(len(flag1)):
                                    flag1[j]=flag1[j]/len(multi_run_data[i])
                                    if flag2[j]==-1:
                                        flag2[j]=flag1[j]
                                    else:
                                        flag2[j]=flag1[j]+flag2[j]
                            for i in range(len(flag2)):
                                flag2[i]=flag2[i]/len(multi_run_data)
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
                            self.dump_resume_csv(l,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,r,self.thresholds.get(r)[t],MINS[m],MSG_EXP_TIME,len(multi_run_data))

##########################################################################################################
    def dump_times(self,bias,data_in,BASE,PATH,COMMIT,MINS,MSG_EXP_TIME,limit):
        print("-- Dumping arrival times")
        for m in range(len(MINS)):
            for r in COMMIT:
                for t in range(len(self.thresholds.get(r))):
                    multi_run_data = (data_in.get((r,MINS[m],self.thresholds.get(r)[t])))[0]
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
                    self.dump_resume_csv(-1,bias,times,'-',BASE,PATH,r,self.thresholds.get(r)[t],MINS[m],MSG_EXP_TIME,len(multi_run_data))

##########################################################################################################
    def extract_median(self,array):
        median = 0
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median