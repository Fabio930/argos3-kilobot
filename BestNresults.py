import numpy as np
import os, csv
import matplotlib.lines as mlines
import matplotlib.colors as colors
import matplotlib.cm as cmx
from scipy.special import gamma
from matplotlib import pyplot as plt
from lifelines import KaplanMeierFitter
from lifelines import WeibullFitter

class Results:

##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in os.listdir(self.base):
            if '.' not in elem:
                selem=elem.split('_')
                if selem[0]=="results":
                    self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def get_mean_and_std(self, wf:WeibullFitter):
        # get the Weibull shape and scale parameter 
        scale, shape = wf.summary.loc['lambda_','coef'], wf.summary.loc['rho_','coef']

        # calculate the mean time
        mean = scale*gamma(1 + 1/shape)

        # calculate the standard deviation
        std = np.sqrt(scale*(2)*gamma(1 + 2.0/shape) - mean*2)
        
        return [mean, std]

##########################################################################################################
    def extract_data(self):
        COMMUNICATION=[]
        BASES=[]
        COMMIT_PERC=[]
        Q_LEN=[]
        N_AGENTS=[]
        SCALING=[]
        MAX_STEPS=[]
        results = {}
        dateToStore = ""
        for base in self.bases:
            if base not in BASES:
                BASES.append(base)
            for dir in os.listdir(base):
                if '.' not in dir and '#' in dir:
                    pre_path=os.path.join(base, dir)
                    communication=int(dir.split('#')[1])
                    if communication not in COMMUNICATION:
                        COMMUNICATION.append(int(communication))
                    for zdir in os.listdir(pre_path):
                        if '.' not in zdir and '#' in zdir:
                            n_agents=int(zdir.split('#')[1])
                            if n_agents not in N_AGENTS:
                                N_AGENTS.append(int(n_agents))
                            dtemp=os.path.join(pre_path, zdir)
                            for sdir in os.listdir(dtemp):
                                if '.' not in sdir and '#' in sdir:
                                    commit_perc=float(sdir.split('#')[1].replace("_","."))
                                    if commit_perc not in COMMIT_PERC:
                                        COMMIT_PERC.append(float(commit_perc))
                                    stemp=os.path.join(dtemp, sdir)
                                    for ssdir in os.listdir(stemp):
                                        if '.' not in ssdir and '#' in ssdir:
                                            q_len=float(ssdir.split('#')[1].replace("_","."))
                                            if q_len not in Q_LEN:
                                                Q_LEN.append(float(q_len))
                                            path_temp=os.path.join(stemp, ssdir)
                                            for folder in os.listdir(path_temp):
                                                if '.' not in folder:
                                                    params = folder.split('#')
                                                    scaling , max_steps = float(params[1].replace("_",".")) , int(params[3])-1
                                                    if scaling not in SCALING:
                                                        SCALING.append(float(scaling))
                                                    if max_steps not in MAX_STEPS:
                                                        MAX_STEPS.append(int(max_steps))
                                                    sub_path=os.path.join(path_temp,folder)
                                                    unordered_commitments = np.array([[[]]])
                                                    unordered_posX = np.array([[[]]])
                                                    unordered_posY = np.array([[[]]])
                                                    unordered_seeds = np.array([])
                                                    for elem in os.listdir(sub_path):
                                                        #==================================================================
                                                        if '.' in elem:
                                                            selem=elem.split('.')
                                                            if selem[-1]=="tsv" and selem[0].split('_')[-1]=="LOG":
                                                                date = selem[0].split('__')[0]
                                                                dmy=date.split('_')[0]
                                                                hms=date.split('_')[-1]
                                                                day=int(dmy.split('-')[0])
                                                                month=int(dmy.split('-')[1])
                                                                year=int(dmy.split('-')[2])
                                                                hours=int(hms.split('-')[0])
                                                                minutes=int(hms.split('-')[1])
                                                                if dateToStore=="":
                                                                    dateToStore=date
                                                                else:
                                                                    dmy0=dateToStore.split('_')[0]
                                                                    hms0=dateToStore.split('_')[-1]
                                                                    day0=int(dmy0.split('-')[0])
                                                                    month0=int(dmy0.split('-')[1])
                                                                    year0=int(dmy0.split('-')[2])
                                                                    hours0=int(hms0.split('-')[0])
                                                                    minutes0=int(hms0.split('-')[1])
                                                                    if year0<=year:
                                                                        if month0<=month:
                                                                            if day0<=day:
                                                                                if hours0<=hours:   
                                                                                    if minutes0<=minutes:   
                                                                                        dateToStore=date
                                                                proceed = True
                                                                for CHECKfile in os.listdir(base+"/Rebroadcast#"+str(communication)+"/Robots#"+str(n_agents)):
                                                                    if ".csv" in CHECKfile:
                                                                        temp_str=CHECKfile.split('.')[0]
                                                                        Mdmy=temp_str.split('_')[2]
                                                                        Mhms=temp_str.split('_')[-1]
                                                                        Mday=int(Mdmy.split('-')[0])
                                                                        Mmonth=int(Mdmy.split('-')[1])
                                                                        Myear=int(Mdmy.split('-')[2])
                                                                        Mhours=int(Mhms.split('-')[0])
                                                                        Mminutes=int(Mhms.split('-')[1])
                                                                        if year<=Myear:
                                                                            if month<=Mmonth:
                                                                                if day<=Mday:
                                                                                    if hours<=Mhours:   
                                                                                        if minutes<=Mminutes:   
                                                                                            proceed = False
                                                                                            break
                                                                #==================================================================
                                                                if proceed:
                                                                    seed=-1
                                                                    agents_commitments = np.array([[0]])
                                                                    agents_posX = np.array([[-1]])
                                                                    agents_posY = np.array([[-1]])
                                                                    for n in range(1,n_agents):
                                                                        agents_commitments = np.append(agents_commitments,[[0]],1)
                                                                        agents_posX = np.append(agents_posX,[[-1]],1)
                                                                        agents_posY = np.append(agents_posY,[[-1]],1)
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        s=0
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                com_arr=[]
                                                                                posX_arr=[]
                                                                                posY_arr=[]
                                                                                val = val.split('\t')
                                                                                if s==0:
                                                                                    seed=int(val[0])
                                                                                    s+=1
                                                                                elif s>0:
                                                                                    for i in range(1,len(val)):
                                                                                        if i%3==1:
                                                                                            posX_arr.append(float(val[i]))
                                                                                        elif i%3==2:
                                                                                            posY_arr.append(float(val[i]))
                                                                                        elif i%3==0:
                                                                                            com_arr.append(int(val[i]))
                                                                                    agents_commitments = np.append(agents_commitments,[com_arr],0)
                                                                                    agents_posX = np.append(agents_posX,[posX_arr],0)
                                                                                    agents_posY = np.append(agents_posY,[posY_arr],0)
                                                                    if np.size(unordered_commitments)==0:
                                                                        unordered_commitments = np.array([agents_commitments])
                                                                        unordered_seeds = np.array([seed])
                                                                        unordered_posX = np.array([agents_posX])
                                                                        unordered_posY = np.array([agents_posY])
                                                                    else:
                                                                        unordered_commitments = np.append(unordered_commitments,[agents_commitments],0)
                                                                        unordered_seeds = np.append(unordered_seeds,seed)
                                                                        unordered_posX = np.append(unordered_posX,[agents_posX],0)
                                                                        unordered_posY = np.append(unordered_posY,[agents_posY],0)
                                                    results.update({(base,communication,n_agents,max_steps,commit_perc,q_len,scaling):(unordered_commitments,list(unordered_seeds),unordered_posX,unordered_posY)})
        return results,BASES,COMMUNICATION,N_AGENTS,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS,dateToStore

##########################################################################################################
##########################################################################################################
    def extract_k_quorum_data(self,position="all"):
        COMMUNICATION=[]
        BASES=[]
        COMMIT_PERC=[]
        Q_LEN=[]
        N_AGENTS=[]
        SCALING=[]
        MAX_STEPS=[]
        results = {}
        for base in self.bases:
            if base not in BASES:
                BASES.append(base)
            for dir in os.listdir(base):
                if '.' not in dir and '#' in dir:
                    pre_path=os.path.join(base, dir)
                    communication=int(dir.split('#')[1])
                    if communication not in COMMUNICATION:
                        COMMUNICATION.append(int(communication))
                    for zdir in os.listdir(pre_path):
                        if '.' not in zdir and '#' in zdir:
                            n_agents=int(zdir.split('#')[1])
                            if n_agents not in N_AGENTS:
                                N_AGENTS.append(int(n_agents))
                            dtemp=os.path.join(pre_path, zdir)
                            for sdir in os.listdir(dtemp):
                                if '.' not in sdir and '#' in sdir:
                                    commit_perc=float(sdir.split('#')[1].replace("_","."))
                                    if commit_perc not in COMMIT_PERC:
                                        COMMIT_PERC.append(float(commit_perc))
                                    stemp=os.path.join(dtemp, sdir)
                                    for ssdir in os.listdir(stemp):
                                        if '.' not in ssdir and '#' in ssdir:
                                            q_len=float(ssdir.split('#')[1].replace("_","."))
                                            if q_len not in Q_LEN:
                                                Q_LEN.append(float(q_len))
                                            path_temp=os.path.join(stemp, ssdir)
                                            for folder in os.listdir(path_temp):
                                                if '.' not in folder:
                                                    params = folder.split('#')
                                                    scaling , max_steps = float(params[1].replace("_",".")) , int(params[3])-1
                                                    if scaling not in SCALING:
                                                        SCALING.append(float(scaling))
                                                    if max_steps not in MAX_STEPS:
                                                        MAX_STEPS.append(int(max_steps))
                                                    sub_path=os.path.join(path_temp,folder)
                                                    dim = len(os.listdir(sub_path))//2
                                                    bigM_0 = [np.array([])] * dim if position=="all" else np.array([])
                                                    bigM_1 = [np.array([])] * dim if position=="all" else np.array([])
                                                    bigM_2 = [np.array([])] * dim if position=="all" else np.array([])
                                                    for elem in os.listdir(sub_path):
                                                        if '.' in elem:
                                                            selem=elem.split('.')
                                                            if position == "all":
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_2 = [np.array([],dtype=float)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                state = (int)(val[1])
                                                                                ql = (int)(val[2])
                                                                                qv = (float)(val[3])
                                                                                M_0[id] = np.append(M_0[id],state)
                                                                                M_1[id] = np.append(M_1[id],ql)
                                                                                M_2[id] = np.append(M_2[id],qv)
                                                                    bigM_0[seed-1] = M_0
                                                                    bigM_1[seed-1] = M_1
                                                                    bigM_2[seed-1] = M_2
                                                            elif position == "first":
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]=="1":
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_2 = [np.array([],dtype=float)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                state = (int)(val[1])
                                                                                ql = (int)(val[2])
                                                                                qv = (float)(val[3])
                                                                                M_0[id] = np.append(M_0[id],state)
                                                                                M_1[id] = np.append(M_1[id],ql)
                                                                                M_2[id] = np.append(M_2[id],qv)
                                                                    bigM_0 = M_0
                                                                    bigM_1 = M_1
                                                                    bigM_2 = M_2
                                                            elif position == "last":
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]==str(len(os.listdir(sub_path))//2):
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_2 = [np.array([],dtype=float)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                state = (int)(val[1])
                                                                                ql = (int)(val[2])
                                                                                qv = (float)(val[3])
                                                                                M_0[id] = np.append(M_0[id],state)
                                                                                M_1[id] = np.append(M_1[id],ql)
                                                                                M_2[id] = np.append(M_2[id],qv)
                                                                    bigM_0 = M_0
                                                                    bigM_1 = M_1
                                                                    bigM_2 = M_2
                                                            elif position == "rand":
                                                                p = np.random.choice(np.arange(len(os.listdir(sub_path))//2))
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]==p:
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    M_2 = [np.array([],dtype=float)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                state = (int)(val[1])
                                                                                ql = (int)(val[2])
                                                                                qv = (float)(val[3])
                                                                                M_0[id] = np.append(M_0[id],state)
                                                                                M_1[id] = np.append(M_1[id],ql)
                                                                                M_2[id] = np.append(M_2[id],qv)
                                                                    bigM_0 = M_0
                                                                    bigM_1 = M_1
                                                                    bigM_2 = M_2
                                                        results.update({(base,communication,n_agents,max_steps,commit_perc,q_len,scaling):(bigM_0,bigM_1,bigM_2)})
        return results,BASES,COMMUNICATION,N_AGENTS,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS
    
##########################################################################################################
    def print_mean_quorum_value(self,data_in,BASES,COMMUNICATION,N_AGENTS,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS):
        N_AGENTS,COMMUNICATION,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS = np.sort(N_AGENTS),np.sort(COMMUNICATION),np.sort(COMMIT_PERC),np.sort(Q_LEN),np.sort(SCALING),np.sort(MAX_STEPS)
        for base in BASES:
            for A in COMMUNICATION:
                for S in N_AGENTS:
                    for B in MAX_STEPS:
                        for D in COMMIT_PERC:
                            for k in Q_LEN:
                                we_will_print=False
                                to_print = [[]]*len(data_in.get((base,A,S,B,D,k,SCALING[0])))
                                legend = [[]]*len(data_in.get((base,A,S,B,D,k,SCALING[0])))
                                for r in SCALING:
                                    for l in range(len(data_in.get((base,A,S,B,D,k,r)))):
                                        if (data_in.get((base,A,S,B,D,k,r)))[l] is not None:
                                            # print(base,A,S,B,D,k,r,"\n")
                                            we_will_print=True
                                            bigM = (data_in.get((base,A,S,B,D,k,r)))[l]
                                            flag2=[-1]*len(bigM[0][0])
                                            flag3=[flag2]*(len(bigM)+1)
                                            tmp=[flag2]*len(bigM)
                                            for i in range(len(bigM)):
                                                flag1=[-1]*len(bigM[i][0])
                                                for j in range(len(bigM[i])):
                                                    for z in range(len(bigM[i][j])):
                                                        if flag1[z]==-1:
                                                            flag1[z]=bigM[i][j][z]
                                                        else:
                                                            flag1[z]=flag1[z]+bigM[i][j][z]
                                                for z in range(len(flag1)):
                                                    flag1[z]=flag1[z]/len(bigM[i])
                                                    if flag2[z]==-1:
                                                        flag2[z]=flag1[z]
                                                    else:
                                                        flag2[z]=flag1[z]+flag2[z]
                                                tmp[i] = np.round(flag1,2).tolist()
                                            for i in range(len(flag2)):
                                                flag2[i]=flag2[i]/len(bigM)
                                            for i in range(len(flag3)):
                                                flag3[i] = np.round(flag2,2).tolist() if i==0 else tmp[i-1]
                                            if len(to_print[l])==0:
                                                to_print[l] = [flag3]
                                                legend[l] = ["Scaling: "+str(r)]
                                            else:
                                                to_print[l] = np.append(to_print[l],[flag3],0)
                                                legend[l] = np.append(legend[l],"Scaling: "+str(r))
                                if we_will_print:
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
                                                    the_plot, = plt.plot(to_print[l][i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[l][i])
                                                    handls = np.append(handls,the_plot)
                                                else:
                                                    plt.plot(to_print[l][i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.3)
                                        plt.grid(True,linestyle=':')
                                        plt.xlabel("simulation ticks")

                                        if not os.path.exists(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images"):
                                            os.mkdir(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images")
                                        if not os.path.exists(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum"):
                                            os.mkdir(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum")
                                        
                                        if l==0:
                                            plt.ylabel("mean swarm state")
                                            fig_path=base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum/CONFIGs__COMM#"+str(A)+"_"+"ROB#"+str(S)+"_"+"STEPS#"+str(B)+"_"+"cOMM%#"+str(D)+"_"+"qLEN#"+str(k).replace(".","-")+".png"
                                            plt.yticks(np.arange(0,1.05,0.05))
                                        elif l==1:
                                            plt.ylabel("mean quorum length")
                                            fig_path=base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum/CONFIGql__COMM#"+str(A)+"_"+"ROB#"+str(S)+"_"+"STEPS#"+str(B)+"_"+"cOMM%#"+str(D)+"_"+"qLEN#"+str(k).replace(".","-")+".png"
                                            plt.yticks(np.arange(0,S+0.5,0.5))
                                        elif l==2:
                                            plt.ylabel("mean quorum level")
                                            fig_path=base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum/CONFIGqv__COMM#"+str(A)+"_"+"ROB#"+str(S)+"_"+"STEPS#"+str(B)+"_"+"cOMM%#"+str(D)+"_"+"qLEN#"+str(k).replace(".","-")+".png"
                                            plt.yticks(np.arange(0,1.05,0.05))
                                        plt.legend(handles=handls.tolist(),loc='best')
                                        plt.tight_layout()
                                        plt.savefig(fig_path)
                                        # plt.show(fig)
                                        plt.close(fig)

##########################################################################################################
    def print_single_run_quorum(self,data_in,BASES,COMMUNICATION,N_AGENTS,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS,position='first',taken='all'):
        N_AGENTS,COMMUNICATION,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS = np.sort(N_AGENTS),np.sort(COMMUNICATION),np.sort(COMMIT_PERC),np.sort(Q_LEN),np.sort(SCALING),np.sort(MAX_STEPS)
        for base in BASES:
            for A in COMMUNICATION:
                for S in N_AGENTS:
                    for B in MAX_STEPS:
                        for D in COMMIT_PERC:
                            for k in Q_LEN:
                                we_will_print = False
                                to_print = []
                                legend = []
                                for r in SCALING:
                                    if data_in.get((base,A,S,B,D,k,r))[2] is not None:
                                        we_will_print=True
                                        run = bigM = data_in.get((base,A,S,B,D,k,r))[2]
                                        if taken=='all':
                                            p = 0
                                            if position=='rand': p = np.random.choice(np.arange(len(bigM)))
                                            elif position=='last': p = len(bigM)-1
                                            run = bigM[p]
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
                                        if len(to_print)==0:
                                            to_print = [flag]
                                            legend = ["R: "+str(r)]
                                        else:
                                            to_print = np.append(to_print,[flag],0)
                                            legend = np.append(legend,"R: "+str(r))
                                if we_will_print:
                                    handls=[]
                                    values = range(len(to_print))
                                    fig, ax = plt.subplots(figsize=(12,6))
                                    cm = plt.get_cmap('viridis') 
                                    cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
                                    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
                                    for i in range(len(to_print)):
                                        for j in range(len(to_print[i])):
                                            if j==0:
                                                the_plot, = plt.plot(to_print[i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[i],alpha=i*.1)
                                                handls = np.append(handls,the_plot)
                                            else:
                                                plt.plot(to_print[i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.5)
                                    plt.grid(True,linestyle=':')
                                    plt.ylabel("mean quorum level")
                                    plt.xlabel("simulation ticks")
                                    plt.tight_layout()
                                    if not os.path.exists(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images"):
                                        os.mkdir(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images")
                                    if not os.path.exists(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum"):
                                        os.mkdir(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum")
                                    fig_path=base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/images/quorum/CONFIGq__COMM#"+str(A)+"_"+"ROB#"+str(S)+"_"+"STEPS#"+str(B)+"_"+"cOMM%#"+str(D)+"_"+"qLEN#"+str(k).replace(".","-")+".png"
                                    plt.yticks(np.arange(0,1.05,0.05))
                                    plt.legend(handles=handls.tolist(),loc='best')
                                    plt.savefig(fig_path)
                                    # plt.show(fig)
                                    plt.close(fig)

##########################################################################################################
##########################################################################################################
    def plot_weibulls(self,data_in,BASES,COMMUNICATION,N_AGENTS,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS,date,POSorCOM='commitment'):
        N_AGENTS,COMMUNICATION,COMMIT_PERC,Q_LEN,SCALING,MAX_STEPS = np.sort(N_AGENTS),np.sort(COMMUNICATION),np.sort(COMMIT_PERC),np.sort(Q_LEN),np.sort(SCALING),np.sort(MAX_STEPS)
        data={}
        times={}
        for base in BASES:
            for A in COMMUNICATION:
                for S in N_AGENTS:
                    if not os.path.exists(base+"/Rebroadcast#"+str(A)+"/Robots#"+str(S)+"/resume_"+POSorCOM+"_"+date+".csv"):
                        for B in MAX_STEPS:
                            for D in COMMIT_PERC:
                                for k in Q_LEN:
                                    for r in SCALING:
                                        if data_in.get((base,A,S,B,D,k,r)) is not None:
                                            states=data_in.get((base,A,S,B,D,k,r))[2]
                                            seeds=data_in.get((base,A,S,B,D,k,r))[3]
                                            stored_times = [S+1]*len(states)
                                            stored_eval_data = [[0]*A]*len(states)
                                            # ===============================================
                                            # extract data for weibulls plotting
                                            for c in range(len(states)): 
                                                semc = 0
                                                timec = S+1
                                                eval_to_store = [0]*A
                                                for l in range(len(states[c])):
                                                    if semc==0:
                                                        for e in range(int(len(states[c][l]))):
                                                            if states[c][l][e] in leafs:
                                                                sum = 1
                                                                for ce in range(len(states[c][l])):
                                                                    if e!=ce and states[c][l][e]==states[c][l][ce]: # derive weibulls and % over position
                                                                        sum += 1
                                                                if sum >= len(states[c][l])*.9:
                                                                    semc = 1
                                                                    timec = l+1
                                                                    eval_to_store = states[c][l]
                                                                    break
                                                    if semc==1: break
                                                stored_times[c] = timec
                                                stored_eval_data[c] = list(eval_to_store)
                                                # print(best_leafs[c],'\n',stored_times[c],'\t',stored_commitments[c],'\t',stored_distances[c],'\t',leafs,'\n\n')
                                            data.update({(base,A,S,B,D,k,r):(stored_times,stored_eval_data,list(seeds))})
                                # for k in Q_LEN:
                                #     fig, ax = plt.subplots(figsize=(12,6))
                                #     values = range(len(R))
                                #     cm = plt.get_cmap('viridis') 
                                #     cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
                                #     scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
                                #     gottaPrint=False
                                #     indx = 0
                                #     for r in SCALING:
                                #         if data.get((base,A,S,B,D,k,r)) is not None:
                                #             gottaPrint=True
                                #             sorted_times = np.sort(data.get((base,A,S,B,D,k,r))[0],axis=None,kind='stable')
                                #             censored=[]
                                #             for j in range(len(sorted_times)):
                                #                 if sorted_times[j]==S+1:
                                #                     censored.append(0)
                                #                 else:
                                #                     censored.append(1)
                                #             kmf = KaplanMeierFitter()
                                #             kmf.fit(sorted_times,censored,label="R:"+str(r)+" KM")
                                #             ci = kmf.confidence_interval_cumulative_density_
                                #             ts = ci.index
                                #             low,high = np.transpose(ci.values)
                                #             plt.fill_between(ts,low,high,color="gray",alpha=0.2)
                                #             kmf.cumulative_density_.plot(ax=ax,linestyle="solid",color=scalarMap.to_rgba(values[indx]))
                                #             sorted_times,censored = np.insert(sorted_times,0,1),np.insert(censored,0,0)
                                #             we = WeibullFitter()
                                #             we.fit(sorted_times,censored,label="R:"+str(r)+" Weibull")
                                #             ci = we.confidence_interval_cumulative_density_
                                #             ts = ci.index
                                #             low,high = np.transpose(ci.values)
                                #             plt.fill_between(ts,low,high,color="gray",alpha=0.2)
                                #             we.cumulative_density_.plot(ax=ax,linestyle="dashed",color=scalarMap.to_rgba(values[indx]))
                                #             values=self.get_mean_and_std(we)
                                #             times.update({(base,A,S,B,D,k,r):[values[0],values[1]]})
                                #             indx+=1
                                #     if gottaPrint:
                                #         plt.grid(True,linestyle=':')
                                #         plt.ylabel("consensus cumulative density")
                                #         plt.xlabel("Seconds")
                                #         plt.xlim((0,S+50))
                                #         plt.ylim((-0.05,1.05))
                                #         plt.tight_layout()
                                #         if not os.path.exists(base+"/Robots#"+str(A)+"/images"):
                                #             os.mkdir(base+"/Robots#"+str(A)+"/images")
                                #         if not os.path.exists(base+"/Robots#"+str(A)+"/images/"+POSorCOM):
                                #             os.mkdir(base+"/Robots#"+str(A)+"/images/"+POSorCOM)
                                #         if not os.path.exists(base+"/Robots#"+str(A)+"/images/"+POSorCOM+"/Weibulls"):
                                #             os.mkdir(base+"/Robots#"+str(A)+"/images/"+POSorCOM+"/Weibulls")
                                #         fig_path=base+"/Robots#"+str(A)+"/images/"+POSorCOM+"/Weibulls/CONFIGw_"+POSorCOM+"__A#"+str(A)+"_"+"S#"+str(S)+"_"+"B#"+str(B)+"_"+"D#"+str(D)+"_"+"K#"+str(k).replace(".","-")+"__"+date+".png"
                                #         plt.savefig(fig_path)
                                #     # plt.show(fig)
                                #     plt.close(fig)
        return (data,times)

##########################################################################################################