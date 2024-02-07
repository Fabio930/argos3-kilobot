import numpy as np
import os, csv, math
import matplotlib.colors as colors
import matplotlib.cm as cmx
from matplotlib import pyplot as plt

class Results:
    thresholds = [0.72, 0.76]
    ground_truth = [0.72,0.76,0.8]
    min_buff_dim = [5]
    ticks_per_sec = 10
    x_limit = 100
##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem=elem.split('_')
                if selem[0]=="Presults":
                    self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def compute_quorum_vars_on_ground_truth(self,m1,states):
        out = {}
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
                        dim = 0
                        ones = 0
                        for z in range(len(m1[k][j][t])):
                            if(m1[k][j][t][z] == -1): break
                            dim += 1
                            ones += states[i][j][m1[k][j][t][z]]
                        tmp_dim_2.append(dim)
                        tmp_ones_2.append(ones)
                    tmp_dim_1[k] = tmp_dim_2
                    tmp_ones_1[k] = tmp_ones_2
                tmp_dim_0[j] = tmp_dim_1
                tmp_ones_0[j] = tmp_ones_1
            out[self.ground_truth[i]] = (tmp_dim_0,tmp_ones_0)
        return out
    
#########################################################################################################
    def compute_quorum(self,m1,m2,minus,threshold):
        out = np.copy(m1)
        for i in range(len(m1)):
            for j in range(len(m1[i])):
                for k in range(len(m1[i][j])):
                    out[i][j][k] = 1 if m1[i][j][k] >= minus and m2[i][j][k] >= threshold * (1 + m1[i][j][k]) else 0
        return out

##########################################################################################################
    def extract_k_quorum_data(self,base,path_temp,max_steps,n_agents,max_buff_size,position="all"): 
        for pre_folder in sorted(os.listdir(path_temp)):
            if '.' not in pre_folder:
                pre_params = pre_folder.split('#')
                buffer_dim = int(pre_params[-1])
                sub_path=os.path.join(path_temp,pre_folder)
                msgs_results = {}
                num_runs = int(len(os.listdir(sub_path))/n_agents)
                p = np.random.choice(np.arange(num_runs))
                msgs_bigM_1 = [np.array([])] * n_agents if position=="all" else np.array([])
                msgs_M_1 = [np.array([],dtype=int)]*num_runs # x num_samples
                # assign randomly the state to agents at each run
                print("--- Assigning states ---\n",sub_path,'\n')
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
                print("--- Extract data ---\n")
                a_ = 0
                prev_id = -1
                for elem in sorted(os.listdir(sub_path)):
                    if '.' in elem:
                        selem=elem.split('.')
                        if position == "all":
                            if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                                a_+=1
                                seed = int(selem[0].split('#')[-1])
                                agent_id = int(selem[0].split('__')[0].split('#')[-1])
                                if prev_id != agent_id:
                                    a_ = 0
                                if a_ == 0:
                                    print("Reading files of agent",agent_id)
                                    prev_id = agent_id
                                
                                with open(os.path.join(sub_path, elem), newline='') as f:
                                    reader = csv.reader(f)
                                    log_count = 0
                                    for row in reader:
                                        log_count += 1
                                        if log_count % self.ticks_per_sec == 0:
                                            log_count = 0
                                            msgs = []
                                            for val in row:
                                                if val.count('\t')==0 and val.count('-')==0:
                                                    msgs.append(int(val))
                                            if len(msgs) < max_buff_size:
                                                for i in range(max_buff_size-len(msgs)): msgs.append(-1)
                                            if len(msgs_M_1[seed-1]) == 0:
                                                msgs_M_1[seed-1] = [msgs]
                                            else :
                                                msgs_M_1[seed-1] = np.append(msgs_M_1[seed-1],[msgs],axis=0)
                                if len(msgs_M_1[seed-1])!=max_steps: print(seed,len(msgs_M_1[seed-1]),len(msgs_M_1[seed-1][-1]))
                                if seed == num_runs:
                                    msgs_bigM_1[agent_id] = msgs_M_1
                                    msgs_M_1 = [np.array([],dtype=int)]*num_runs
                results = self.compute_quorum_vars_on_ground_truth(msgs_bigM_1,states_by_gt)
                for gt in range(len(self.ground_truth)):
                    for minus in self.min_buff_dim:
                        for thr in self.thresholds:
                            msgs_results[(self.ground_truth[gt],minus,thr)] = (self.compute_quorum(results.get(self.ground_truth[gt])[0],results.get(self.ground_truth[gt])[1],minus,thr),results.get(self.ground_truth[gt])[0],results.get(self.ground_truth[gt])[1])
                self.print_median_time(msgs_results,base,path_temp,self.ground_truth,self.min_buff_dim,buffer_dim)
                self.print_mean_quorum_value(msgs_results,base,path_temp,n_agents,self.ground_truth,self.min_buff_dim,buffer_dim)
                # self.print_single_run_quorum(msgs_results,base,path_temp,n_agents,self.ground_truth,self.min_buff_dim,buffer_dim)
        print("DONE\n")

##########################################################################################################
    def print_resume_csv(self,indx,data_in,base,path,COMMIT,THRESHOLD,MINS,BUFFER_DIM,n_runs):
        static_fields=["CommittedPerc","Threshold","MinBuffDim","MaxBuffDim"]
        static_values=[COMMIT,THRESHOLD,MINS,BUFFER_DIM]
        if not os.path.exists(base+"/proc_data"):
            os.mkdir(base+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        file_name = "average_resume_r#"+str(n_runs)+".csv"
        if not os.path.exists(base+"/proc_data/"+file_name):
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
        if indx==0:
            values.append("swarm_state")
        elif indx==1:
            values.append("quorum_length")
        elif indx==2:
            values.append("quorum_value")
        elif indx==3:
            values.append("times")
        values.append(data_in)
        fw = open(base+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()

##########################################################################################################
    def print_mean_quorum_value(self,data_in,BASE,PATH,N_AGENTS,COMMIT,MINS,BUFFER_DIM):
        print("Printing average quorum data")
        tmp_b = BASE.split('/')
        tmp_p = PATH.split('/')
        name_fields = []
        mid_string=""
        for i in tmp_p:
            if i not in tmp_b:
                name_fields.append(i)
        for label in name_fields:
            mid_string += label+"_"
        if not os.path.exists(BASE+"/images"):
            os.mkdir(BASE+"/images")
        if not os.path.exists(BASE+"/images/quorum"):
            os.mkdir(BASE+"/images/quorum")
        if not os.path.exists(BASE+"/images/state"):
            os.mkdir(BASE+"/images/state")
        print_only_state = True
        for m in range(len(MINS)):
            for t in range(len(self.thresholds)):
                we_will_print=False
                to_print = [[]]*(len(data_in.get((COMMIT[0],MINS[m],self.thresholds[t])))-1)
                legend = [[]]*(len(data_in.get((COMMIT[0],MINS[m],self.thresholds[t])))-1)
                support_print = []
                support_legend = []
                for r in COMMIT:
                    for l in range(len(data_in.get((r,MINS[m],self.thresholds[t])))-1):
                        if (print_only_state or l==0) and (data_in.get((r,MINS[m],self.thresholds[t])))[l] is not None:
                            we_will_print=True
                            multi_run_data = (data_in.get((r,MINS[m],self.thresholds[t])))[l]
                            support_buffer = (data_in.get((r,MINS[m],self.thresholds[t])))[2]
                            if l==1:
                                flag2=[-1]*len(support_buffer[0][0])
                                flag3=[flag2]*(len(support_buffer)+1)
                                tmp=[flag2]*len(support_buffer)
                                for i in range(len(support_buffer)):
                                    flag1=[-1]*len(support_buffer[i][0])
                                    for j in range(len(support_buffer[i])):
                                        for z in range(len(support_buffer[i][j])):
                                            if flag1[z]==-1:
                                                flag1[z]=support_buffer[i][j][z]
                                            else:
                                                flag1[z]=flag1[z]+support_buffer[i][j][z]
                                    for j in range(len(flag1)):
                                        flag1[j]=flag1[j]/len(support_buffer[i])
                                        if flag2[j]==-1:
                                            flag2[j]=flag1[j]
                                        else:
                                            flag2[j]=flag1[j]+flag2[j]
                                    tmp[i] = np.round(flag1,2).tolist()
                                for i in range(len(flag2)):
                                    flag2[i]=flag2[i]/len(support_buffer)
                                for i in range(len(flag3)):
                                    flag3[i] = np.round(flag2,2).tolist() if i==0 else tmp[i-1]
                                support_print = [flag3]
                                support_legend = ["Not repeated messages"]
                            flag2=[-1]*len(multi_run_data[0][0])
                            flag3=[flag2]*(len(multi_run_data)+1)
                            tmp=[flag2]*len(multi_run_data)
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
                                tmp[i] = np.round(flag1,2).tolist()
                            for i in range(len(flag2)):
                                flag2[i]=flag2[i]/len(multi_run_data)
                            for i in range(len(flag3)):
                                flag3[i] = np.round(flag2,2).tolist() if i==0 else tmp[i-1]
                            if len(to_print[l])==0:
                                to_print[l] = [flag3]
                                legend[l] = ["Gound Truth: "+str(r)]
                            else:
                                to_print[l] = np.append(to_print[l],[flag3],0)
                                legend[l] = np.append(legend[l],"Gound Truth: "+str(r))
                            self.print_resume_csv(l,flag3[0],BASE,PATH,r,self.thresholds[t],MINS[m],BUFFER_DIM,len(multi_run_data))
                if we_will_print:
                    for l in range(len(to_print)):
                        if (print_only_state or l==0):
                            handls=[]
                            values = range(len(to_print[l]))
                            fig, ax = plt.subplots(figsize=(12,6))
                            cm = plt.get_cmap('viridis') 
                            cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
                            scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
                            for i in range(len(to_print[l])):
                                for j in range(len(to_print[l][i])):
                                    if j==0:
                                        if l==1 and i==0:
                                            the_plot, = plt.plot(support_print[i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[0]),label=support_legend[i])
                                            handls = np.append(handls,the_plot) 
                                        if l==1:
                                            the_plot, = plt.plot(to_print[l][i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[2]),label="Message buffer")
                                        else:  
                                            the_plot, = plt.plot(to_print[l][i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[l][i])
                                        if l==1:
                                            if i==0:
                                                handls = np.append(handls,the_plot)
                                        else:
                                            handls = np.append(handls,the_plot)
                                    else:
                                        if l==1 and i==0:
                                            plt.plot(support_print[i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.3)
                                        plt.plot(to_print[l][i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.3)
                            plt.grid(True,linestyle=':')
                            plt.xlabel("simulation time (secs)")
                            if l==0:
                                plt.ylabel("average swarm state")
                                fig_path=BASE+"/images/state/CONFIGs__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+"_MinListDim#"+str(MINS[m])+"_THR#"+str(self.thresholds[t]).replace(".","-")+".png"
                                plt.yticks(np.arange(0,1.05,0.05))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            elif l==1:
                                plt.ylabel("average quorum length")
                                fig_path=BASE+"/images/quorum/CONFIGql__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            elif l==2:
                                plt.ylabel("average quorum level")
                                fig_path=BASE+"/images/quorum/CONFIGqv__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            plt.tight_layout()
                            plt.savefig(fig_path)
                            # plt.show()
                            plt.close(fig)
                print_only_state = False

##########################################################################################################
    def print_single_run_quorum(self,data_in,BASE,PATH,N_AGENTS,COMMIT,MINS,BUFFER_DIM,position='first',taken="all"):
        print("Printing single run quorum data")
        tmp_b = BASE.split('/')
        tmp_p = PATH.split('/')
        name_fields = []
        mid_string=""
        for i in tmp_p:
            if i not in tmp_b:
                name_fields.append(i)
        for label in name_fields:
            mid_string += label+"_"
        if not os.path.exists(BASE+"/images"):
            os.mkdir(BASE+"/images")
        if not os.path.exists(BASE+"/images/single_runs"):
            os.mkdir(BASE+"/images/single_runs")
        if not os.path.exists(BASE+"/images/single_runs/quorum"):
            os.mkdir(BASE+"/images/single_runs/quorum")
        if not os.path.exists(BASE+"/images/single_runs/state"):
            os.mkdir(BASE+"/images/single_runs/state")
        print_only_state = True
        for m in range(len(MINS)):
            for t in range(len(self.thresholds)):
                we_will_print = False
                to_print = [[]]*(len(data_in.get((COMMIT[0],MINS[0],self.thresholds[0])))-1)
                legend = [[]]*(len(data_in.get((COMMIT[0],MINS[0],self.thresholds[0])))-1)
                p,P = 0,0
                for r in COMMIT:
                    if P==0 and position!='first' and taken=="all":
                        P = 1
                        if position=='rand': p = np.random.choice(np.arange(len(data_in.get((r,MINS[0],self.thresholds[t]))[0])))
                        elif position=='last': p = len(data_in.get((r,MINS[0],self.thresholds[t]))[0])-1
                    for l in range(len(data_in.get((r,MINS[0],self.thresholds[t])))-1):
                        if(print_only_state or l==0) and  data_in.get((r,MINS[0],self.thresholds[t]))[l] is not None:
                            we_will_print=True
                            run = data_in.get((r,MINS[0],self.thresholds[t]))[l][p]
                            mean = [-1]*len(run[0])
                            flag = [mean]*(len(run)+1)
                            for i in range(len(run)):
                                flag[i+1] = run[i]
                                for j in range(len(run[i])):
                                    if mean[j] == -1:
                                        mean[j] = run[i][j]
                                    else:
                                        mean[j] = mean[j]+run[i][j]
                            for z in range(len(mean)):
                                mean[z] = mean[z]/len(run)
                            flag[0] = np.round(mean,2).tolist()
                            if len(to_print[l])==0:
                                to_print[l] = [flag]
                                legend[l] = ["Ground Truth: "+str(r)]
                            else:
                                to_print[l] = np.append(to_print[l],[flag],0)
                                legend[l] = np.append(legend[l],"Ground Truth: "+str(r))
                if we_will_print:
                    for l in range(len(to_print)):
                        if (print_only_state or l==0):
                            handls=[]
                            values = range(len(to_print[l]))
                            fig, ax = plt.subplots(figsize=(12,6))
                            cm = plt.get_cmap('viridis') 
                            cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
                            scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
                            for i in range(len(to_print[l])):
                                for j in range(len(to_print[l][i])):
                                    if j==0:
                                        the_plot, = plt.plot(to_print[l][i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[l][i])
                                        handls = np.append(handls,the_plot)
                                    else:
                                        plt.plot(to_print[l][i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.5)
                            plt.grid(True,linestyle=':')
                            plt.xlabel("simulation time (secs)")
                            if l==0:
                                plt.ylabel("average swarm state")
                                fig_path=BASE+"/images/single_runs/state/srCONFIGs__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+"_MinListDim#"+str(MINS[m])+"_THR#"+str(self.thresholds[t]).replace(".","-")+"_Nrun#"+str(p)+".png"
                                plt.yticks(np.arange(0,1.05,0.05))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            elif l==1:
                                plt.ylabel("average quorum length")
                                fig_path=BASE+"/images/single_runs/quorum/srCONFIGql__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+"_Nrun#"+str(p)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                            elif l==2:
                                plt.ylabel("average quorum level")
                                fig_path=BASE+"/images/single_runs/quorum/srCONFIGqv__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+"_Nrun#"+str(p)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            plt.tight_layout()
                            plt.savefig(fig_path)
                            # plt.show()
                            plt.close(fig)
                print_only_state = False

##########################################################################################################
    def print_median_time(self,data_in,BASE,PATH,COMMIT,MINS,BUFFER_DIM):
        print("\nPrinting median arrival times")
        tmp_b = BASE.split('/')
        tmp_p = PATH.split('/')
        name_fields = []
        mid_string=""
        for i in tmp_p:
            if i not in tmp_b:
                name_fields.append(i)
        for label in name_fields:
            mid_string += label+"_"
        median_times = {}
        if not os.path.exists(BASE+"/images"):
            os.mkdir(BASE+"/images")
        if not os.path.exists(BASE+"/images/times"):
            os.mkdir(BASE+"/images/times")
        ylim = 0
        for m in range(len(MINS)):
            for t in range(len(self.thresholds)):
                for r in COMMIT:
                    multi_run_data = (data_in.get((r,MINS[m],self.thresholds[t])))[0]
                    times = [len(multi_run_data[0][0])] * len(multi_run_data)
                    for i in range(len(multi_run_data)): # per ogni run
                        for z in range(len(multi_run_data[i][0])): # per ogni tick
                            sum = 0
                            for j in range(len(multi_run_data[i])): # per ogni agente
                                sum += multi_run_data[i][j][z]
                            if sum >= 0.9 * len(multi_run_data[i]):
                                times[i] = z
                                break
                    times = sorted(times)
                    self.print_resume_csv(3,times,BASE,PATH,r,self.thresholds[t],MINS[m],BUFFER_DIM,len(times))
                    median = len(multi_run_data[0][0])
                    if ylim == 0: ylim = median
                    if times[len(times)//2] < median:
                        if len(times)%2 == 0:
                            indx = int(len(times)*0.5)
                            median = (times[indx] + times[indx-1])*0.5
                        else:
                            median = times[int(math.floor(len(times)*0.5))]
                    median_times[(self.thresholds[t],MINS[m],r)] = round(median,3)
        printing_dict = {}
        sets = []
        for m in range(len(MINS)):
            for r in COMMIT:
                values = []
                for t in range(len(self.thresholds)):
                    set_item = str(self.thresholds[t])
                    if set_item not in sets: sets.append(set_item)
                    values.append(median_times[(self.thresholds[t],MINS[m],r)])
                printing_dict["ground truth "+str(r)] = values
            x = np.arange(len(sets))
            width = 0.25
            multiplier = 0
            fig, ax = plt.subplots(figsize=(12,6))
            for attribute, measurement in printing_dict.items():
                rects = ax.bar(x + (width*multiplier),measurement,width, label=attribute)
                ax.bar_label(rects,padding=3)
                multiplier += 1
            ax.set_ylabel("median arrival time (sec)")
            ax.set_ylim(0,ylim)
            ax.set_xlabel("configurations")
            ax.set_xticks(x + width,sets)
            plt.legend(loc='upper right')
            plt.tight_layout()
            fig_path=BASE+"/images/times/CONFIGt__"+mid_string+"BufferDim#"+str(BUFFER_DIM)+"_MinListDim#"+str(MINS[m])+".png"
            plt.savefig(fig_path)
            # plt.show()
            plt.close(fig)
