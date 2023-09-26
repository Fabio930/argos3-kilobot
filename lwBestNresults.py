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
        for elem in sorted(os.listdir(self.base)):
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
##########################################################################################################
    def extract_k_quorum_data(self,path_temp,n_agents,position="all"):
        COMMIT=[]
        MAX_STEPS=[]
        results = {}
        for folder in sorted(os.listdir(path_temp)):
            if '.' not in folder:
                params = folder.split('#')
                commit , max_steps = float(params[1].replace("_",".")) , int(params[3])-1
                print("Extracting KILO data for",commit,"Committed percentage and",max_steps,"Time steps")
                if commit not in COMMIT:
                    COMMIT.append(int(commit))
                if max_steps not in MAX_STEPS:
                    MAX_STEPS.append(int(max_steps))
                sub_path=os.path.join(path_temp,folder)
                dim = len(os.listdir(sub_path))
                bigM_0 = [np.array([])] * dim if position=="all" else np.array([])
                bigM_1 = [np.array([])] * dim if position=="all" else np.array([])
                bigM_2 = [np.array([])] * dim if position=="all" else np.array([])
                for elem in sorted(os.listdir(sub_path)):
                    if '.' in elem:
                        selem=elem.split('.')
                        if position == "all":
                            if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                                seed = (int)(selem[0].split('#')[-1])
                                print("Reading file",seed)
                                M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_2 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                with open(os.path.join(sub_path, elem), newline='') as f:
                                    reader = csv.reader(f)
                                    for row in reader:
                                        for val in row:
                                            val = val.split('\t')
                                            id = (int)(val[0])
                                            M_0[id] = np.append(M_0[id],(int)(val[1]))
                                            M_1[id] = np.append(M_1[id],(int)(val[2]))
                                            M_2[id] = np.append(M_2[id],(int)(val[3]))
                                bigM_0[seed-1] = M_0
                                bigM_1[seed-1] = M_1
                                bigM_2[seed-1] = M_2
                        elif position == "first":
                            if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]=="1":
                                seed = (int)(selem[0].split('_')[-1])
                                M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_2 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                with open(os.path.join(sub_path, elem), newline='') as f:
                                    reader = csv.reader(f)
                                    for row in reader:
                                        for val in row:
                                            val = val.split('\t')
                                            id = (int)(val[0])
                                            M_0[id] = np.append(M_0[id],(int)(val[1]))
                                            M_1[id] = np.append(M_1[id],(int)(val[2]))
                                            M_2[id] = np.append(M_2[id],(int)(val[3]))
                                bigM_0 = M_0
                                bigM_1 = M_1
                                bigM_2 = M_2
                        elif position == "last":
                            if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]==str(len(os.listdir(sub_path))):
                                seed = (int)(selem[0].split('_')[-1])
                                M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_2 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                with open(os.path.join(sub_path, elem), newline='') as f:
                                    reader = csv.reader(f)
                                    for row in reader:
                                        for val in row:
                                            val = val.split('\t')
                                            id = (int)(val[0])
                                            M_0[id] = np.append(M_0[id],(int)(val[1]))
                                            M_1[id] = np.append(M_1[id],(int)(val[2]))
                                            M_2[id] = np.append(M_2[id],(int)(val[3]))
                                bigM_0 = M_0
                                bigM_1 = M_1
                                bigM_2 = M_2
                        elif position == "rand":
                            p = np.random.choice(np.arange(len(os.listdir(sub_path))))
                            if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]==p:
                                seed = (int)(selem[0].split('_')[-1])
                                M_0 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_1 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                M_2 = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                with open(os.path.join(sub_path, elem), newline='') as f:
                                    reader = csv.reader(f)
                                    for row in reader:
                                        for val in row:
                                            val = val.split('\t')
                                            id = (int)(val[0])
                                            M_0[id] = np.append(M_0[id],(int)(val[1]))
                                            M_1[id] = np.append(M_1[id],(int)(val[2]))
                                            M_2[id] = np.append(M_2[id],(int)(val[3]))
                                bigM_0 = M_0
                                bigM_1 = M_1
                                bigM_2 = M_2
                    results.update({(max_steps,commit):(bigM_0,bigM_1,bigM_2)})
                print("")
        print("DONE\n")
        return results,COMMIT,MAX_STEPS
    
##########################################################################################################
    def print_mean_quorum_value(self,data_in,BASE,COMMUNICATION,N_AGENTS,COMMIT,MAX_STEPS):
        print("Printing quorum data")
        COMMIT,MAX_STEPS = np.sort(COMMIT),np.sort(MAX_STEPS)
        for s in MAX_STEPS:
            we_will_print=False
            to_print = [[]]*len(data_in.get((s,COMMIT[0])))
            legend = [[]]*len(data_in.get((s,COMMIT[0])))
            for r in COMMIT:
                for l in range(len(data_in.get((s,r)))):
                    if (data_in.get((s,r)))[l] is not None:
                        # print(s,r,"\n")
                        we_will_print=True
                        bigM = (data_in.get((s,r)))[l]
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
                            legend[l] = ["Gound Truth: "+str(r)]
                        else:
                            to_print[l] = np.append(to_print[l],[flag3],0)
                            legend[l] = np.append(legend[l],"Gound Truth: "+str(r))
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
                    plt.xlabel("kilo ticks")

                    if not os.path.exists(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images"):
                        os.mkdir(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images")
                    if not os.path.exists(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum"):
                        os.mkdir(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum")
                    
                    if l==0:
                        plt.ylabel("mean swarm state")
                        fig_path=BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum/CONFIGs__COMM#"+str(COMMUNICATION)+"_"+"ROB#"+str(N_AGENTS)+"_"+"STEPS#"+str(s).replace(".","-")+".png"
                        plt.yticks(np.arange(0,1.05,0.05))
                    elif l==1:
                        plt.ylabel("mean quorum length")
                        fig_path=BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum/CONFIGql__COMM#"+str(COMMUNICATION)+"_"+"ROB#"+str(N_AGENTS)+"_"+"STEPS#"+str(s).replace(".","-")+".png"
                        plt.yticks(np.arange(0,N_AGENTS+1,1))
                    elif l==2:
                        plt.ylabel("mean quorum level")
                        fig_path=BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum/CONFIGqv__COMM#"+str(COMMUNICATION)+"_"+"ROB#"+str(N_AGENTS)+"_"+"STEPS#"+str(s).replace(".","-")+".png"
                        plt.yticks(np.arange(0,1.05,0.05))
                    plt.legend(handles=handls.tolist(),loc='best')
                    plt.tight_layout()
                    plt.savefig(fig_path)
                    # plt.show(fig)
                    plt.close(fig)
        print("DONE")
##########################################################################################################

    def print_single_run_quorum(self,data_in,BASE,COMMUNICATION,N_AGENTS,COMMIT,MAX_STEPS,position='first',taken="all"):
        print("Printing single run quorum data")
        COMMIT,MAX_STEPS = np.sort(COMMIT),np.sort(MAX_STEPS)
        for s in MAX_STEPS:
            we_will_print = False
            to_print = [[]]*len(data_in.get((s,COMMIT[0])))
            legend = [[]]*len(data_in.get((s,COMMIT[0])))
            p = 0
            P = 0
            for r in COMMIT:
                if P==0 and position!='first' and taken=="all":
                    P = 1
                    if position=='rand': p = np.random.choice(np.arange(len(data_in.get((s,r))[0])))
                    elif position=='last': p = len(data_in.get((s,r))[0])-1
                for l in range(len(data_in.get((s,r)))):
                    if data_in.get((s,r))[l] is not None:
                        we_will_print=True
                        run = data_in.get((s,r))[l][p]
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
                    plt.xlabel("kilo ticks")
                    if not os.path.exists(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images"):
                        os.mkdir(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images")
                    if not os.path.exists(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum"):
                        os.mkdir(BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum")
                    
                    if l==0:
                        plt.ylabel("mean swarm state")
                        fig_path=BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum/srCONFIGs__COMM#"+str(COMMUNICATION)+"_"+"ROB#"+str(N_AGENTS)+"_"+"STEPS#"+str(s)+"_Nrun#"+str(p)+".png"
                        plt.yticks(np.arange(0,1.05,0.05))
                    elif l==1:
                        plt.ylabel("mean quorum length")
                        fig_path=BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum/srCONFIGql__COMM#"+str(COMMUNICATION)+"_"+"ROB#"+str(N_AGENTS)+"_"+"STEPS#"+str(s)+"_Nrun#"+str(p)+".png"
                        plt.yticks(np.arange(0,N_AGENTS+1,1))
                    elif l==2:
                        plt.ylabel("mean quorum level")
                        fig_path=BASE+"/Rebroadcast#"+str(COMMUNICATION)+"/Robots#"+str(N_AGENTS)+"/images/quorum/srCONFIGqv__COMM#"+str(COMMUNICATION)+"_"+"ROB#"+str(N_AGENTS)+"_"+"STEPS#"+str(s)+"_Nrun#"+str(p)+".png"
                        plt.yticks(np.arange(0,1.05,0.05))
                    plt.legend(handles=handls.tolist(),loc='best')
                    plt.tight_layout()
                    plt.savefig(fig_path)
                    # plt.show(fig)
                    plt.close(fig)
        print("DONE")