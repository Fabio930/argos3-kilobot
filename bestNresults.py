import numpy as np
import os, csv, math
import matplotlib.colors as colors
import matplotlib.cm as cmx
from matplotlib import pyplot as plt

class Results:
    thresholds = [0.4,0.5,0.55,0.6,0.7]
    ticks_per_sec = 31
    x_limit = 100
    
##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem=elem.split('_')
                if selem[0]=="results":
                    self.bases.append(os.path.join(self.base, elem))

#########################################################################################################
    def compute_states(self,m1,m2,minus,threshold,position):
        out = np.copy(m1)
        if position == "all":
            for i in range(len(m1)):
                for j in range(len(m1[i])):
                    for k in range(len(m1[i][j])):
                        out[i][j][k] = 1 if m1[i][j][k]-1 >= minus and m2[i][j][k] >= threshold * m1[i][j][k] else 0
        else:
            for i in range(len(m1)):
                for j in range(len(m1[i])):
                    out[i][j] = 1 if m1[i][j]-1 >= minus and m2[i][j] >= threshold * m1[i][j] else 0

        return out
    
##########################################################################################################
    def extract_k_quorum_data(self,base,path_temp,max_steps,communication,n_agents,position="all",data_type="all"):
        MINS = [5]
        for i in range(10,n_agents,10):
            MINS.append(i) 
        COMMIT=[]
        for pre_folder in sorted(os.listdir(path_temp)):
            if '.' not in pre_folder:
                pre_params = pre_folder.split('#')
                msg_exp_time = int(pre_params[-1])
                pre_path_temp=os.path.join(path_temp,pre_folder)
                q_results = {}
                m_results = {}
                for folder in sorted(os.listdir(pre_path_temp)):
                    if '.' not in folder:
                        params = folder.split('#')
                        commit = float(params[1].replace("_","."))
                        print("\nExtracting KILO data for",msg_exp_time,"Expiring messages",commit,"Committed percentage and",max_steps,"Time steps")
                        if commit not in COMMIT:
                            COMMIT.append(float(commit))
                        sub_path=os.path.join(pre_path_temp,folder)
                        p = np.random.choice(np.arange(len(os.listdir(sub_path))))
                        dim = len(os.listdir(sub_path))
                        q_bigM_1 = [np.array([])] * dim if position=="all" else np.array([])
                        q_bigM_2 = [np.array([])] * dim if position=="all" else np.array([])
                        m_bigM_1 = [np.array([])] * dim if position=="all" else np.array([])
                        m_bigM_2 = [np.array([])] * dim if position=="all" else np.array([])
                        m_bigM_3 = [np.array([])] * dim if position=="all" else np.array([])
                        for elem in sorted(os.listdir(sub_path)):
                            if '.' in elem:
                                q_M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                q_M_2 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                m_M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                m_M_2 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                m_M_3 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                selem=elem.split('.')
                                if position == "all":
                                    if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                                        seed = (int)(selem[0].split('#')[-1])
                                        print("Reading file",seed)
                                        with open(os.path.join(sub_path, elem), newline='') as f:
                                            reader = csv.reader(f)
                                            log_count = 0
                                            for row in reader:
                                                for val in row:
                                                    val = val.split('\t')
                                                    agent_id = (int)(val[0])
                                                    if log_count % self.ticks_per_sec == 0:
                                                        q_M_1[agent_id] = np.append(q_M_1[agent_id],(int)(val[2])+1)
                                                        q_M_2[agent_id] = np.append(q_M_2[agent_id],(int)(val[3])+(int)(val[1]))
                                                        if communication != 0:
                                                            m_M_1[agent_id] = np.append(m_M_1[agent_id],(int)(val[4]))
                                                            m_M_2[agent_id] = np.append(m_M_2[agent_id],(int)(val[5]))
                                                            m_M_3[agent_id] = np.append(m_M_3[agent_id],(int)(val[6]))
                                                    if agent_id == n_agents - 1: log_count+=1
                                        q_bigM_1[seed-1] = q_M_1
                                        q_bigM_2[seed-1] = q_M_2
                                        m_bigM_1[seed-1] = m_M_1
                                        m_bigM_2[seed-1] = m_M_2
                                        m_bigM_3[seed-1] = m_M_3
                                elif position == "first":
                                    if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('#')[-1]=="1":
                                        seed = (int)(selem[0].split('#')[-1])
                                        print("Reading file",seed)
                                        with open(os.path.join(sub_path, elem), newline='') as f:
                                            reader = csv.reader(f)
                                            log_count = 0
                                            for row in reader:
                                                for val in row:
                                                    val = val.split('\t')
                                                    agent_id = (int)(val[0])
                                                    if log_count % self.ticks_per_sec == 0:
                                                        q_M_1[agent_id] = np.append(q_M_1[agent_id],(int)(val[2])+1)
                                                        q_M_2[agent_id] = np.append(q_M_2[agent_id],(int)(val[3])+(int)(val[1]))
                                                        if communication != 0:
                                                            m_M_1[agent_id] = np.append(m_M_1[agent_id],(int)(val[4]))
                                                            m_M_2[agent_id] = np.append(m_M_2[agent_id],(int)(val[5]))
                                                            m_M_3[agent_id] = np.append(m_M_3[agent_id],(int)(val[6]))
                                                    if agent_id == n_agents - 1: log_count+=1
                                        q_bigM_1 = q_M_1
                                        q_bigM_2 = q_M_2
                                        m_bigM_1 = m_M_1
                                        m_bigM_2 = m_M_2
                                        m_bigM_3 = m_M_3
                                elif position == "last":
                                    if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('#')[-1]==str(len(os.listdir(sub_path))):
                                        seed = (int)(selem[0].split('#')[-1])
                                        print("Reading file",seed)
                                        with open(os.path.join(sub_path, elem), newline='') as f:
                                            reader = csv.reader(f)
                                            log_count = 0
                                            for row in reader:
                                                for val in row:
                                                    val = val.split('\t')
                                                    agent_id = (int)(val[0])
                                                    if log_count % self.ticks_per_sec == 0:
                                                        q_M_1[agent_id] = np.append(q_M_1[agent_id],(int)(val[2])+1)
                                                        q_M_2[agent_id] = np.append(q_M_2[agent_id],(int)(val[3])+(int)(val[1]))
                                                        if communication != 0:
                                                            m_M_1[agent_id] = np.append(m_M_1[agent_id],(int)(val[4]))
                                                            m_M_2[agent_id] = np.append(m_M_2[agent_id],(int)(val[5]))
                                                            m_M_3[agent_id] = np.append(m_M_3[agent_id],(int)(val[6]))
                                                    if agent_id == n_agents - 1: log_count+=1
                                        q_bigM_1 = q_M_1
                                        q_bigM_2 = q_M_2
                                        m_bigM_1 = m_M_1
                                        m_bigM_2 = m_M_2
                                        m_bigM_3 = m_M_3
                                elif position == "rand":
                                    if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('#')[-1]==str(p):
                                        seed = (int)(selem[0].split('#')[-1])
                                        print("Reading file",seed)
                                        with open(os.path.join(sub_path, elem), newline='') as f:
                                            reader = csv.reader(f)
                                            log_count = 0
                                            for row in reader:
                                                for val in row:
                                                    val = val.split('\t')
                                                    agent_id = (int)(val[0])
                                                    if log_count % self.ticks_per_sec == 0:
                                                        q_M_1[agent_id] = np.append(q_M_1[agent_id],(int)(val[2])+1)
                                                        q_M_2[agent_id] = np.append(q_M_2[agent_id],(int)(val[3])+(int)(val[1]))
                                                        if communication != 0:
                                                            m_M_1[agent_id] = np.append(m_M_1[agent_id],(int)(val[4]))
                                                            m_M_2[agent_id] = np.append(m_M_2[agent_id],(int)(val[5]))
                                                            m_M_3[agent_id] = np.append(m_M_3[agent_id],(int)(val[6]))
                                                    if agent_id == n_agents - 1: log_count+=1
                                        q_bigM_1 = q_M_1
                                        q_bigM_2 = q_M_2
                                        m_bigM_1 = m_M_1
                                        m_bigM_2 = m_M_2
                                        m_bigM_3 = m_M_3
                        for minus in MINS:
                            for thr in self.thresholds:
                                q_results[(commit,minus,thr)] = (self.compute_states(q_bigM_1,q_bigM_2,minus,thr,position),q_bigM_1,q_bigM_2)
                        m_results[commit] = (m_bigM_1,m_bigM_2,m_bigM_3)
                COMMIT,MINS = np.sort(COMMIT),np.sort(MINS)
                if data_type=="all" or data_type=="quorum":
                    if position=="all":
                        self.print_median_time(q_results,base,path_temp,COMMIT,MINS,msg_exp_time)
                        self.print_mean_quorum_value(q_results,base,path_temp,n_agents,COMMIT,MINS,msg_exp_time)
                    self.print_single_run_quorum(q_results,base,path_temp,n_agents,COMMIT,MINS,msg_exp_time)
                if (data_type=="all" or data_type=="freq") and communication > 0:
                    if position == "all":
                        self.print_msg_freq(m_results,base,path_temp,COMMIT,msg_exp_time)
                        self.print_focused_meg_freq(m_results,base,path_temp,COMMIT,msg_exp_time,self.x_limit)
        print("DONE\n")
        
##########################################################################################################
    def print_resume_csv(self,indx,data_in,base,path,COMMIT,THRESHOLD,MINS,MSG_EXP_TIME,n_runs):    
        static_fields=["CommittedPerc","Threshold","MinBuffDim","MsgExpTime"]
        static_values=[COMMIT,THRESHOLD,MINS,MSG_EXP_TIME]
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
        if indx==-1:
            values.append("times")
        elif indx==0:
            values.append("swarm_state")
        elif indx==1:
            values.append("quorum_length")
        elif indx==2:
            values.append("quorum_value")
        elif indx==3:
            values.append("avg_msg_action")
        elif indx==4:
            values.append("broadcast_msg")
        elif indx==5:
            values.append("rebroadcast_msg")
        values.append(data_in)
        fw = open(base+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()

##########################################################################################################
    def print_focused_meg_freq(self,data_in,BASE,PATH,COMMIT,MSG_EXP_TIME,x_limit):
        print("Printing focus messages frequency")
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
        if not os.path.exists(BASE+"/images/messages"):
            os.mkdir(BASE+"/images/messages")
        to_print = [[]]*len(data_in.get(COMMIT[0]))
        legend = [[]]*len(data_in.get(COMMIT[0]))
        for c in COMMIT:
            for l in range(len(data_in.get(c))):
                multi_run_data = data_in.get(c)[l]
                flag2 = [-1]*x_limit
                flag3 = [flag2]*(len(multi_run_data)+1) 
                tmp = [flag2]*len(multi_run_data)
                for i in range(len(multi_run_data)):
                    flag1 = [-1]*x_limit
                    for j in range(len(multi_run_data[i])):
                        for z in range(x_limit):
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
                for i in range(len(flag3)):
                    flag3[i] = np.round(flag2,2).tolist() if i==0 else tmp[i-1]
                if len(to_print[l])==0:
                    to_print[l] = [flag3]
                    if l==1: legend[l] = "message type: broadcast"
                    else: legend[l] = "message type: re-broadcast"
                else:    
                    to_print[l] = np.append(to_print[l],[flag3],0)
        handls = []
        values = range(2)
        fig, ax = plt.subplots(figsize=(12,6))
        cm = plt.get_cmap('viridis')
        cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        for i in range(len(to_print[0])):
            for j in range(len(to_print[0][i])):
                for l in range(1,len(to_print)):
                    if j==0:
                        the_plot, = plt.plot(to_print[l][i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[l-1]),label=legend[l])
                        handls = np.append(handls,the_plot)
                    else:
                        plt.plot(to_print[l][i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[l-1]),alpha=.3)
        plt.legend(handles=handls.tolist(),loc='lower right')
        plt.grid(True,linestyle=':')
        plt.xlabel("simulation time (secs)")
        plt.ylabel("average # of msgs")
        fig_path=BASE+"/images/messages/CONFIGfom__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
        plt.tight_layout()
        plt.savefig(fig_path)
        # plt.show()
        plt.close(fig)
        
##########################################################################################################
    def print_msg_freq(self,data_in,BASE,PATH,COMMIT,MSG_EXP_TIME):
        print("Printing messages frequency")
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
        if not os.path.exists(BASE+"/images/messages"):
            os.mkdir(BASE+"/images/messages")
        to_print = [[]]*len(data_in.get(COMMIT[0]))
        for c in COMMIT:
            for l in range(len(data_in.get(c))):
                multi_run_data = data_in.get(c)[l]
                flag2 = [-1]*len(multi_run_data[0][0])
                flag3 = [flag2]*(len(multi_run_data)+1)
                tmp = [flag2]*len(multi_run_data)
                for i in range(len(multi_run_data)):
                    flag1 = [-1]*len(multi_run_data[i][0])
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
                for i in range(len(flag3)):
                    flag3[i] = np.round(flag2,2).tolist() if i==0 else tmp[i-1]
                if len(to_print[l])==0:
                    to_print[l] = [flag3]
                else:
                    to_print[l] = np.append(to_print[l],[flag3],0)
                self.print_resume_csv(l+3,flag3[0],BASE,PATH,c,"-","-",MSG_EXP_TIME,len(multi_run_data))
        for l in range(len(to_print)):
            handls=[]
            values = range(len(to_print[l]))
            fig, ax = plt.subplots(figsize=(12,6))
            cm = plt.get_cmap('viridis') 
            cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
            scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
            for i in range(len(to_print[l])):
                for j in range(len(to_print[l][i])):
                    if j==0:
                        the_plot, = plt.plot(to_print[l][i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]))
                        handls = np.append(handls,the_plot)
                    else:
                        plt.plot(to_print[l][i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.3)
            plt.grid(True,linestyle=':')
            plt.xlabel("simulation time (secs)")
            
            if l==0:
                plt.ylabel("average swarm msg action")
                fig_path=BASE+"/images/messages/CONFIGf__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
                plt.yticks(np.arange(0,1.1,0.1))
            elif l==1:
                plt.ylabel("average # of broadcast msgs")
                fig_path=BASE+"/images/messages/CONFIGbm__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
                plt.yticks(np.arange(0,4100,100))
            elif l==2:
                plt.ylabel("average # of rebroadcast msgs")
                fig_path=BASE+"/images/messages/CONFIGrm__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
                plt.yticks(np.arange(0,110,10))
            plt.tight_layout()
            plt.savefig(fig_path)
            # plt.show()
            plt.close(fig)
        
##########################################################################################################
    def print_mean_quorum_value(self,data_in,BASE,PATH,N_AGENTS,COMMIT,MINS,MSG_EXP_TIME):
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
                to_print = [[]]*len(data_in.get((COMMIT[0],MINS[m],self.thresholds[t])))
                legend = [[]]*len(data_in.get((COMMIT[0],MINS[m],self.thresholds[t])))
                for r in COMMIT:
                    for l in range(len(data_in.get((r,MINS[m],self.thresholds[t])))):
                        if (print_only_state or l==0) and (data_in.get((r,MINS[m],self.thresholds[t])))[l] is not None:
                            we_will_print=True
                            multi_run_data = (data_in.get((r,MINS[m],self.thresholds[t])))[l]
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
                            self.print_resume_csv(l,flag3[0],BASE,PATH,r,self.thresholds[t],MINS[m],MSG_EXP_TIME,len(multi_run_data))
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
                                        plt.plot(to_print[l][i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.3)
                            plt.grid(True,linestyle=':')
                            plt.xlabel("simulation time (secs)")
                            
                            if l==0:
                                plt.ylabel("average swarm state")
                                fig_path=BASE+"/images/state/CONFIGs__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+"_MINl#"+str(MINS[m])+"_THR#"+str(self.thresholds[t]).replace(".","-")+".png"
                                plt.yticks(np.arange(0,1.05,0.05))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            elif l==1:
                                plt.ylabel("average quorum length")
                                fig_path=BASE+"/images/quorum/CONFIGql__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                            elif l==2:
                                plt.ylabel("average quorum level")
                                fig_path=BASE+"/images/quorum/CONFIGqv__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            plt.tight_layout()
                            plt.savefig(fig_path)
                            # plt.show()
                            plt.close(fig)
                print_only_state = False

##########################################################################################################
    def print_single_run_quorum(self,data_in,BASE,PATH,N_AGENTS,COMMIT,MINS,MSG_EXP_TIME,position='first',taken="all"):
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
                to_print = [[]]*len(data_in.get((COMMIT[0],MINS[0],self.thresholds[0])))
                legend = [[]]*len(data_in.get((COMMIT[0],MINS[0],self.thresholds[0])))
                p,P = 0,0
                for r in COMMIT:
                    if P==0 and position!='first' and taken=="all":
                        P = 1
                        if position=='rand': p = np.random.choice(np.arange(len(data_in.get((r,MINS[m],self.thresholds[t]))[0])))
                        elif position=='last': p = len(data_in.get((r,MINS[m],self.thresholds[t]))[0])-1
                    for l in range(len(data_in.get((r,MINS[m],self.thresholds[t])))):
                        if(print_only_state or l==0) and  data_in.get((r,MINS[m],self.thresholds[t]))[l] is not None:
                            we_will_print=True
                            run = data_in.get((r,MINS[m],self.thresholds[t]))[l][p]
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
                                fig_path=BASE+"/images/single_runs/state/srCONFIGs__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+"_MINl#"+str(MINS[m])+"_THR#"+str(self.thresholds[t]).replace(".","-")+"_Nrun#"+str(p)+".png"
                                plt.yticks(np.arange(0,1.05,0.05))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            elif l==1:
                                plt.ylabel("average quorum length")
                                fig_path=BASE+"/images/single_runs/quorum/srCONFIGql__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+"_Nrun#"+str(p)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                            elif l==2:
                                plt.ylabel("average quorum level")
                                fig_path=BASE+"/images/single_runs/quorum/srCONFIGqv__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+"_Nrun#"+str(p)+".png"
                                plt.yticks(np.arange(0,N_AGENTS+1,1))
                                plt.legend(handles=handls.tolist(),loc='lower right')
                            plt.tight_layout()
                            plt.savefig(fig_path)
                            # plt.show()
                            plt.close(fig)
                print_only_state = False

##########################################################################################################
    def print_median_time(self,data_in,BASE,PATH,COMMIT,MINS,MSG_EXP_TIME):
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
                    self.print_resume_csv(-1,times,BASE,PATH,r,self.thresholds[t],MINS[m],MSG_EXP_TIME,len(times))
                    median = len(multi_run_data[0][0])
                    if ylim == 0: ylim = median
                    if times[len(times)//2] < median:
                        if len(times)%2 == 0:
                            indx = int(len(times)*0.5)
                            median = (times[indx] + times[indx-1])*0.5
                        else:
                            median = times[int(math.floor(len(times)*0.5))]
                    median_times[(MINS[m],self.thresholds[t],r)] = round(median,3)
        printing_dict = {}
        sets = []
        for r in COMMIT:
            values = []
            for m in range(len(MINS)):
                for t in range(len(self.thresholds)):
                    set_item = "min dim "+str(MINS[m])+"_ thr "+str(self.thresholds[t])
                    if set_item not in sets: sets.append(set_item)
                    values.append(median_times[(MINS[m],self.thresholds[t],r)])
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
        fig_path=BASE+"/images/times/CONFIGt__"+mid_string+"MsgExpTime#"+str(MSG_EXP_TIME)+".png"
        plt.savefig(fig_path)
        # plt.show()
        plt.close(fig)
