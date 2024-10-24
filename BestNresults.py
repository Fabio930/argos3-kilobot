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
        BRACHES=[]
        BASES=[]
        DEPTH=[]
        K=[]
        N_AGENTS=[]
        R=[]
        MAX_STEPS=[]
        results = {}
        dateToStore = ""
        for base in self.bases:
            if base not in BASES:
                BASES.append(base)
            for dir in os.listdir(base):
                if '.' not in dir and '#' in dir:
                    pre_path=os.path.join(base, dir)
                    n_agents=int(dir.split('#')[1])
                    if n_agents not in N_AGENTS:
                        N_AGENTS.append(int(n_agents))
                    for zdir in os.listdir(pre_path):
                        if '.' not in zdir and '#' in zdir:
                            branches=int(zdir.split('#')[1])
                            if branches not in BRACHES:
                                BRACHES.append(int(branches))
                            dtemp=os.path.join(pre_path, zdir)
                            for sdir in os.listdir(dtemp):
                                if '.' not in sdir and '#' in sdir:
                                    depth=int(sdir.split('#')[1])
                                    if depth not in DEPTH:
                                        DEPTH.append(int(depth))
                                    stemp=os.path.join(dtemp, sdir)
                                    for ssdir in os.listdir(stemp):
                                        if '.' not in ssdir and '#' in ssdir:
                                            k=float(ssdir.split('#')[1].replace("_","."))
                                            if k not in K:
                                                K.append(float(k))
                                            path_temp=os.path.join(stemp, ssdir)
                                            for folder in os.listdir(path_temp):
                                                if '.' not in folder:
                                                    params = folder.split('_')
                                                    r , max_steps = float(params[0].split('#')[1]) , int(params[1].split('#')[1])-1
                                                    if r not in R:
                                                        R.append(float(r))
                                                    if max_steps not in MAX_STEPS:
                                                        MAX_STEPS.append(int(max_steps))
                                                    sub_path=os.path.join(path_temp,folder)
                                                    leafs=[]
                                                    unordered_commitments = np.array([[[]]])
                                                    unordered_locations = np.array([[[]]])
                                                    unordered_posX = np.array([[[]]])
                                                    unordered_posY = np.array([[[]]])
                                                    unordered_distances = np.array([[[]]]) # distance is from 0 to depth --> if == 0 -> optimal decision, if != 0 -> check that commitment is in leaf, otherwise there is no decision
                                                    unordered_Bleafs = np.array([])
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
                                                                for CHECKfile in os.listdir(base+"/Robots#"+str(n_agents)):
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
                                                                    best_leaf=-1
                                                                    agents_commitments = np.array([[0]])
                                                                    agents_locations = np.array([[0]])
                                                                    agents_posX = np.array([[-1]])
                                                                    agents_posY = np.array([[-1]])
                                                                    agents_distances = np.array([[depth]])
                                                                    for n in range(1,n_agents):
                                                                        agents_commitments = np.append(agents_commitments,[[0]],1)
                                                                        agents_locations = np.append(agents_locations,[[0]],1)
                                                                        agents_posX = np.append(agents_posX,[[-1]],1)
                                                                        agents_posY = np.append(agents_posY,[[-1]],1)
                                                                        agents_distances = np.append(agents_distances,[[depth]],1)
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        s=0
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                com_arr=[]
                                                                                loc_arr=[]
                                                                                posX_arr=[]
                                                                                posY_arr=[]
                                                                                dist_arr=[]
                                                                                val = val.split('\t')
                                                                                if s==0:
                                                                                    seed=int(val[0])
                                                                                    best_leaf=int(val[1])
                                                                                    if len(leafs)==0:
                                                                                        for i in range(6,len(val)):
                                                                                            leafs.append(int(val[i]))
                                                                                    s+=1
                                                                                elif s>0:
                                                                                    for i in range(1,len(val)):
                                                                                        if i%5==1:
                                                                                            posX_arr.append(float(val[i]))
                                                                                        elif i%5==2:
                                                                                            posY_arr.append(float(val[i]))
                                                                                        elif i%5==3:
                                                                                            loc_arr.append(int(val[i]))
                                                                                        elif i%5==4:
                                                                                            com_arr.append(int(val[i]))
                                                                                        elif i%5==0:
                                                                                            dist_arr.append(int(val[i]))
                                                                                    agents_commitments = np.append(agents_commitments,[com_arr],0)
                                                                                    agents_locations = np.append(agents_locations,[loc_arr],0)
                                                                                    agents_distances = np.append(agents_distances,[dist_arr],0)
                                                                                    agents_posX = np.append(agents_posX,[posX_arr],0)
                                                                                    agents_posY = np.append(agents_posY,[posY_arr],0)
                                                                    if np.size(unordered_commitments)==0:
                                                                        unordered_commitments = np.array([agents_commitments])
                                                                        unordered_locations = np.array([agents_locations])
                                                                        unordered_distances = np.array([agents_distances])
                                                                        unordered_Bleafs = np.array([best_leaf])
                                                                        unordered_seeds = np.array([seed])
                                                                        unordered_posX = np.array([agents_posX])
                                                                        unordered_posY = np.array([agents_posY])
                                                                    else:
                                                                        unordered_commitments = np.append(unordered_commitments,[agents_commitments],0)
                                                                        unordered_locations = np.append(unordered_locations,[agents_locations],0)
                                                                        unordered_distances = np.append(unordered_distances,[agents_distances],0)
                                                                        unordered_Bleafs = np.append(unordered_Bleafs,best_leaf)
                                                                        unordered_seeds = np.append(unordered_seeds,seed)
                                                                        unordered_posX = np.append(unordered_posX,[agents_posX],0)
                                                                        unordered_posY = np.append(unordered_posY,[agents_posY],0)
                                                    results.update({(base,n_agents,max_steps,branches,depth,k,r):(unordered_locations,unordered_commitments,unordered_distances,list(unordered_seeds),list(unordered_Bleafs),leafs,unordered_posX,unordered_posY)})
        return results,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS,dateToStore

##########################################################################################################
##########################################################################################################
    def extract_k_quorum_data(self,position="all"):
        BRACHES=[]
        BASES=[]
        DEPTH=[]
        K=[]
        N_AGENTS=[]
        R=[]
        MAX_STEPS=[]
        results = {}
        for base in self.bases:
            if base not in BASES:
                BASES.append(base)
            for dir in os.listdir(base):
                if '.' not in dir and '#' in dir:
                    pre_path=os.path.join(base, dir)
                    n_agents=int(dir.split('#')[1])
                    if n_agents not in N_AGENTS:
                        N_AGENTS.append(int(n_agents))
                    for zdir in os.listdir(pre_path):
                        if '.' not in zdir and '#' in zdir:
                            branches=int(zdir.split('#')[1])
                            if branches not in BRACHES:
                                BRACHES.append(int(branches))
                            dtemp=os.path.join(pre_path, zdir)
                            for sdir in os.listdir(dtemp):
                                if '.' not in sdir and '#' in sdir:
                                    depth=int(sdir.split('#')[1])
                                    if depth not in DEPTH:
                                        DEPTH.append(int(depth))
                                    stemp=os.path.join(dtemp, sdir)
                                    for ssdir in os.listdir(stemp):
                                        if '.' not in ssdir and '#' in ssdir:
                                            k=float(ssdir.split('#')[1].replace("_","."))
                                            if k not in K:
                                                K.append(float(k))
                                            path_temp=os.path.join(stemp, ssdir)
                                            for folder in os.listdir(path_temp):
                                                if '.' not in folder:
                                                    params = folder.split('_')
                                                    r , max_steps = float(params[0].split('#')[1]) , int(params[1].split('#')[1])-1
                                                    if r not in R:
                                                        R.append(float(r))
                                                    if max_steps not in MAX_STEPS:
                                                        MAX_STEPS.append(int(max_steps))
                                                    sub_path=os.path.join(path_temp,folder)
                                                    dim = len(os.listdir(sub_path))//2
                                                    bigM = [np.array([])] * dim if position=="all" else np.array([])
                                                    for elem in os.listdir(sub_path):
                                                        if '.' in elem:
                                                            selem=elem.split('.')
                                                            if position == "all":
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum":
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                qv = (int)(val[1])
                                                                                M[id] = np.append(M[id],qv)
                                                                    bigM[seed-1] = M
                                                            elif position == "first":
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]=="1":
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                qv = (int)(val[1])
                                                                                M[id] = np.append(M[id],qv)
                                                                    bigM = M
                                                            elif position == "last":
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]==str(len(os.listdir(sub_path))//2):
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                qv = (int)(val[1])
                                                                                M[id] = np.append(M[id],qv)
                                                                    bigM = M
                                                            elif position == "rand":
                                                                p = np.random.choice(np.arange(len(os.listdir(sub_path))//2))
                                                                if selem[-1]=="tsv" and selem[0].split('_')[0]=="quorum" and selem[0].split('_')[-1]==p:
                                                                    seed = (int)(selem[0].split('_')[-1])
                                                                    M = [np.array([],dtype=int)]*n_agents # n_agents x n_samples
                                                                    with open(os.path.join(sub_path, elem), newline='') as f:
                                                                        reader = csv.reader(f)
                                                                        for row in reader:
                                                                            for val in row:
                                                                                val = val.split('\t')
                                                                                id = (int)(val[0])
                                                                                qv = (int)(val[1])
                                                                                M[id] = np.append(M[id],qv)
                                                                    bigM = M
                                                        results.update({(base,n_agents,max_steps,branches,depth,k,r):bigM})
        return results,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS
    
##########################################################################################################
    def do_something_quorum(self,data_in,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS):
        N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS = np.sort(N_AGENTS),np.sort(BRACHES),np.sort(DEPTH),np.sort(K),np.sort(R),np.sort(MAX_STEPS)
        for base in BASES:
            for A in N_AGENTS:
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
                            for k in K:
                                we_will_print=False
                                to_print = []
                                legend = []
                                for r in R:
                                    if data_in.get((base,A,S,B,D,k,r)) is not None:
                                        we_will_print=True
                                        bigM = data_in.get((base,A,S,B,D,k,r))
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
                                        if len(to_print)==0:
                                            to_print = [flag3]
                                            legend = ["R: "+str(r)]
                                        else:
                                            to_print = np.append(to_print,[flag3],0)
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
                                                the_plot, = plt.plot(to_print[i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[i])
                                                handls = np.append(handls,the_plot)
                                            else:
                                                plt.plot(to_print[i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.3)
                                    plt.grid(True,linestyle=':')
                                    plt.ylabel("mean quorum level")
                                    plt.xlabel("simulation ticks")
                                    plt.tight_layout()
                                    if not os.path.exists(base+"/Robots#"+str(A)+"/images"):
                                        os.mkdir(base+"/Robots#"+str(A)+"/images")
                                    if not os.path.exists(base+"/Robots#"+str(A)+"/images/quorum"):
                                        os.mkdir(base+"/Robots#"+str(A)+"/images/quorum")
                                    fig_path=base+"/Robots#"+str(A)+"/images/quorum/CONFIGq__A#"+str(A)+"_"+"S#"+str(S)+"_"+"B#"+str(B)+"_"+"D#"+str(D)+"_"+"K#"+str(k).replace(".","-")+".png"
                                    maxA = A
                                    plt.ylim((-.5,maxA+.5))
                                    plt.yticks(np.arange(0,maxA+1))
                                    plt.legend(handles=handls.tolist(),loc='best')
                                    plt.savefig(fig_path)
                                    # plt.show(fig)
                                    plt.close(fig)

##########################################################################################################
    def print_single_run_quorum(self,data_in,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS,position='first',taken='all'):
        N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS = np.sort(N_AGENTS),np.sort(BRACHES),np.sort(DEPTH),np.sort(K),np.sort(R),np.sort(MAX_STEPS)
        for base in BASES:
            for A in N_AGENTS:
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
                            for k in K:
                                we_will_print = False
                                to_print = []
                                legend = []
                                for r in R:
                                    if data_in.get((base,A,S,B,D,k,r)) is not None:
                                        we_will_print=True
                                        run = bigM = data_in.get((base,A,S,B,D,k,r))
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
                                                the_plot, = plt.plot(to_print[i][j],lw=1.25,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[i])
                                                handls = np.append(handls,the_plot)
                                            else:
                                                plt.plot(to_print[i][j],lw=.5,ls='-.',c=scalarMap.to_rgba(values[i]),alpha=.5)
                                    plt.grid(True,linestyle=':')
                                    plt.ylabel("mean quorum level")
                                    plt.xlabel("simulation ticks")
                                    plt.tight_layout()
                                    if not os.path.exists(base+"/Robots#"+str(A)+"/images"):
                                        os.mkdir(base+"/Robots#"+str(A)+"/images")
                                    if not os.path.exists(base+"/Robots#"+str(A)+"/images/quorum"):
                                        os.mkdir(base+"/Robots#"+str(A)+"/images/quorum")
                                    fig_path=base+"/Robots#"+str(A)+"/images/quorum/CONFIGq__"+position+"_A#"+str(A)+"_"+"S#"+str(S)+"_"+"B#"+str(B)+"_"+"D#"+str(D)+"_"+"K#"+str(k).replace(".","-")+".png"
                                    maxA = A
                                    plt.ylim((-.5,maxA+.5))
                                    plt.yticks(np.arange(0,maxA+1))
                                    plt.legend(handles=handls.tolist(),loc='best')
                                    plt.savefig(fig_path)
                                    # plt.show(fig)
                                    plt.close(fig)

##########################################################################################################
##########################################################################################################
    def plot_weibulls(self,data_in,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS,date,POSorCOM='commitment'):
        N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS = np.sort(N_AGENTS),np.sort(BRACHES),np.sort(DEPTH),np.sort(K),np.sort(R),np.sort(MAX_STEPS)
        data={}
        times={}
        for base in BASES:
            for A in N_AGENTS:
                if not os.path.exists(base+"/Robots#"+str(A)+"/resume_"+POSorCOM+"_"+date+".csv"):
                    for S in MAX_STEPS:
                        for B in BRACHES:
                            for D in DEPTH:
                                for k in K:
                                    for r in R:
                                        if data_in.get((base,A,S,B,D,k,r)) is not None:
                                            dataTOeval = data_in.get((base,A,S,B,D,k,r))[1] if POSorCOM=="commitment" else data_in.get((base,A,S,B,D,k,r))[0]
                                            distances=data_in.get((base,A,S,B,D,k,r))[2]
                                            seeds=data_in.get((base,A,S,B,D,k,r))[3]
                                            best_leafs=data_in.get((base,A,S,B,D,k,r))[4]
                                            leafs=data_in.get((base,A,S,B,D,k,r))[5]
                                            stored_times = [S+1]*len(dataTOeval)
                                            stored_distances = [[-1]*A]*len(dataTOeval)
                                            stored_eval_data = [[0]*A]*len(dataTOeval)
                                            # ===============================================
                                            # extract data for weibulls plotting
                                            for c in range(len(dataTOeval)): 
                                                semc = 0
                                                timec = S+1
                                                distances_to_store = [-1]*A
                                                eval_to_store = [0]*A
                                                for l in range(len(dataTOeval[c])):
                                                    if semc==0:
                                                        for e in range(int(len(dataTOeval[c][l]))):
                                                            if dataTOeval[c][l][e] in leafs:
                                                                sum = 1
                                                                for ce in range(len(dataTOeval[c][l])):
                                                                    if e!=ce and dataTOeval[c][l][e]==dataTOeval[c][l][ce]: # derive weibulls and % over position
                                                                        sum += 1
                                                                if sum >= len(dataTOeval[c][l])*.9:
                                                                    semc = 1
                                                                    timec = l+1
                                                                    distances_to_store = distances[c][l]
                                                                    eval_to_store = dataTOeval[c][l]
                                                                    break
                                                    if semc==1: break
                                                stored_times[c] = timec
                                                stored_distances[c] = list(distances_to_store)
                                                stored_eval_data[c] = list(eval_to_store)
                                                # print(best_leafs[c],'\n',stored_times[c],'\t',stored_commitments[c],'\t',stored_distances[c],'\t',leafs,'\n\n')
                                            data.update({(base,A,S,B,D,k,r):(stored_times,stored_eval_data,stored_distances,list(seeds),list(best_leafs),list(leafs))})
                                for k in K:
                                    fig, ax = plt.subplots(figsize=(12,6))
                                    values = range(len(R))
                                    cm = plt.get_cmap('viridis') 
                                    cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
                                    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
                                    gottaPrint=False
                                    indx = 0
                                    for r in R:
                                        if data.get((base,A,S,B,D,k,r)) is not None:
                                            gottaPrint=True
                                            sorted_times = np.sort(data.get((base,A,S,B,D,k,r))[0],axis=None,kind='stable')
                                            censored=[]
                                            for j in range(len(sorted_times)):
                                                if sorted_times[j]==S+1:
                                                    censored.append(0)
                                                else:
                                                    censored.append(1)
                                            kmf = KaplanMeierFitter()
                                            kmf.fit(sorted_times,censored,label="R:"+str(r)+" KM")
                                            ci = kmf.confidence_interval_cumulative_density_
                                            ts = ci.index
                                            low,high = np.transpose(ci.values)
                                            plt.fill_between(ts,low,high,color="gray",alpha=0.2)
                                            kmf.cumulative_density_.plot(ax=ax,linestyle="solid",color=scalarMap.to_rgba(values[indx]))
                                            sorted_times,censored = np.insert(sorted_times,0,1),np.insert(censored,0,0)
                                            we = WeibullFitter()
                                            we.fit(sorted_times,censored,label="R:"+str(r)+" Weibull")
                                            ci = we.confidence_interval_cumulative_density_
                                            ts = ci.index
                                            low,high = np.transpose(ci.values)
                                            plt.fill_between(ts,low,high,color="gray",alpha=0.2)
                                            we.cumulative_density_.plot(ax=ax,linestyle="dashed",color=scalarMap.to_rgba(values[indx]))
                                            values=self.get_mean_and_std(we)
                                            times.update({(base,A,S,B,D,k,r):[values[0],values[1]]})
                                            indx+=1
                                    if gottaPrint:
                                        plt.grid(True,linestyle=':')
                                        plt.ylabel("consensus cumulative density")
                                        plt.xlabel("Seconds")
                                        plt.xlim((0,S+50))
                                        plt.ylim((-0.05,1.05))
                                        plt.tight_layout()
                                        if not os.path.exists(base+"/Robots#"+str(A)+"/images"):
                                            os.mkdir(base+"/Robots#"+str(A)+"/images")
                                        if not os.path.exists(base+"/Robots#"+str(A)+"/images/"+POSorCOM):
                                            os.mkdir(base+"/Robots#"+str(A)+"/images/"+POSorCOM)
                                        if not os.path.exists(base+"/Robots#"+str(A)+"/images/"+POSorCOM+"/Weibulls"):
                                            os.mkdir(base+"/Robots#"+str(A)+"/images/"+POSorCOM+"/Weibulls")
                                        fig_path=base+"/Robots#"+str(A)+"/images/"+POSorCOM+"/Weibulls/CONFIGw_"+POSorCOM+"__A#"+str(A)+"_"+"S#"+str(S)+"_"+"B#"+str(B)+"_"+"D#"+str(D)+"_"+"K#"+str(k).replace(".","-")+"__"+date+".png"
                                        plt.savefig(fig_path)
                                    # plt.show(fig)
                                    plt.close(fig)
        return (data,times)

##########################################################################################################
    def plot_percentages_on_leaf(self,data_in,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS):
        N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS = np.sort(N_AGENTS),np.sort(BRACHES),np.sort(DEPTH),np.sort(K),np.sort(R),np.sort(MAX_STEPS)
        for base in BASES:
            for A in N_AGENTS:
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
                            for k in K:
                                we_will_print=False
                                to_print = []
                                legend = []
                                for r in R:
                                    if data_in.get((base,A,S,B,D,k,r)) is not None:
                                        we_will_print=True
                                        locations = data_in.get((base,A,S,B,D,k,r))[0]
                                        best_leafs=data_in.get((base,A,S,B,D,k,r))[4]
                                        leafs=data_in.get((base,A,S,B,D,k,r))[5]
                                        best_leaf_mean = [0]*len(locations[0])
                                        other_leaf_mean = [0]*len(locations[0])
                                        no_leaf_mean = [0]*len(locations[0])
                                        for nr in range(len(locations)):
                                            for ns in range(len(locations[nr])):
                                                for na in range(len(locations[nr][ns])):
                                                    if locations[nr][ns][na]==best_leafs[nr]: best_leaf_mean[ns] += 1/len(locations[nr][ns])
                                                    elif np.isin(locations[nr][ns][na],leafs) : other_leaf_mean[ns] += 1/len(locations[nr][ns])
                                                    else: no_leaf_mean[ns] += 1/len(locations[nr][ns])
                                        for ns in range(len(best_leaf_mean)):
                                            best_leaf_mean[ns]/=len(locations)
                                            other_leaf_mean[ns]/=len(locations)
                                            no_leaf_mean[ns]/=len(locations)
                                        best_leaf_mean=np.round(best_leaf_mean,3)
                                        other_leaf_mean=np.round(other_leaf_mean,3)
                                        no_leaf_mean=np.round(no_leaf_mean,3)
                                        tmpP=[0]*3
                                        tmpL=[0]*3
                                        tmpP[0]=best_leaf_mean.tolist()
                                        tmpP[1]=other_leaf_mean.tolist()
                                        tmpP[2]=no_leaf_mean.tolist()
                                        tmpL[0]="R: "+str(r)+" over_best_leaf"
                                        tmpL[1]="         over_other_leaf"
                                        tmpL[2]="         over_no_leaf"
                                        if len(to_print)==0:
                                            to_print = [tmpP]
                                            legend = [tmpL]
                                        else:
                                            to_print = np.append(to_print,[tmpP],0)
                                            legend = np.append(legend,[tmpL],0)
                                if we_will_print:
                                    values = range(len(to_print))
                                    fig, ax = plt.subplots(figsize=(12,6))
                                    cm = plt.get_cmap('viridis') 
                                    cNorm  = colors.Normalize(vmin=0, vmax=values[-1])
                                    scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
                                    for i in range(len(to_print)):
                                        for j in range(len(to_print[i])):
                                            if j==0:
                                                plt.plot(to_print[i][j],lw=1.5,ls='-',c=scalarMap.to_rgba(values[i]),label=legend[i][j])
                                            elif j==1:
                                                plt.plot(to_print[i][j],lw=1.5,ls=':',c=scalarMap.to_rgba(values[i]),label=legend[i][j])
                                            else:
                                                plt.plot(to_print[i][j],lw=1.5,ls='--',c=scalarMap.to_rgba(values[i]),label=legend[i][j])

                                    plt.grid(True,linestyle=':')
                                    plt.ylabel("mean location percentages")
                                    plt.xlabel("simulation seconds")
                                    plt.tight_layout()
                                    if not os.path.exists(base+"/Robots#"+str(A)+"/images"):
                                        os.mkdir(base+"/Robots#"+str(A)+"/images")
                                    if not os.path.exists(base+"/Robots#"+str(A)+"/images/leafs"):
                                        os.mkdir(base+"/Robots#"+str(A)+"/images/leafs")
                                    fig_path=base+"/Robots#"+str(A)+"/images/leafs/CONFIGl__A#"+str(A)+"_"+"S#"+str(S)+"_"+"B#"+str(B)+"_"+"D#"+str(D)+"_"+"K#"+str(k).replace(".","-")+".png"
                                    plt.legend(loc='best')
                                    plt.savefig(fig_path)
                                    # plt.show(fig)
                                    plt.close(fig)

##########################################################################################################
    def write_percentages(self,data,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS,date,POSorCOM='commitment',checkNodesDistr=False):
        data_0,data_1 = data[0],data[1]
        for base in BASES:
            for A in N_AGENTS:
                if not os.path.exists(base+"/Robots#"+str(A)+"/resume_"+POSorCOM+"_"+date+".csv"):
                    for S in MAX_STEPS:
                        for B in BRACHES:
                            for D in DEPTH:
                                data_to_plot={}
                                for r in R:
                                    for k in K:
                                        type="unknown"
                                        if D==1:
                                            type="flat"
                                        elif B==2:
                                            type="binary"
                                        elif B==4:
                                            type="quad"
                                        SEMprint=True
                                        if data_0.get((base,A,S,B,D,k,r)) is not None:
                                            times=data_0.get((base,A,S,B,D,k,r))[0]
                                            dataTOprint = data_0.get((base,A,S,B,D,k,r))[1]
                                            distances=data_0.get((base,A,S,B,D,k,r))[2]
                                            # seeds=data_0.get((base,A,S,B,D,k,r))[3]
                                            best_leafs=data_0.get((base,A,S,B,D,k,r))[4]
                                            leafs=data_0.get((base,A,S,B,D,k,r))[5]
                                            mean=data_1.get((base,A,S,B,D,k,r))[0]
                                            std=data_1.get((base,A,S,B,D,k,r))[1]
                                            dist_0=[0]
                                            dist_1=[0]
                                            dist_2=[0]
                                            no_decision=[0]
                                            if checkNodesDistr:
                                                dist_0=[0]*len(leafs)
                                                dist_1=[0]*len(leafs)
                                                dist_2=[0]*len(leafs)
                                                no_decision=[0]*len(leafs)
                                            for t in range(len(times)):
                                                if times[t]<=S:
                                                    check_4_succes=0
                                                    for d in range(len(distances[t])):
                                                        if distances[t][d]==0 and dataTOprint[t][d]==best_leafs[t]:
                                                            check_4_succes+=1
                                                    if check_4_succes>=len(distances[t])*.9:
                                                        if checkNodesDistr:
                                                            dist_0[np.where(leafs == best_leafs[t])[0][0]]+=1
                                                        else:
                                                            dist_0[0]+=1
                                                    else:
                                                        check_4_succes=0
                                                        for d in range(len(distances[t])):
                                                            if distances[t][d]==1 and dataTOprint[t][d] in leafs:
                                                                check_4_succes+=1
                                                        if check_4_succes>=len(distances[t])*.9:
                                                            if checkNodesDistr:
                                                                dist_1[np.where(leafs == best_leafs[t])[0][0]]+=1
                                                            else:
                                                                dist_1[0]+=1
                                                        else:
                                                            check_4_succes=0
                                                            for d in range(len(distances[t])):
                                                                if distances[t][d]==2 and dataTOprint[t][d] in leafs:
                                                                    check_4_succes+=1
                                                            if check_4_succes>=len(distances[t])*.9:
                                                                if checkNodesDistr:
                                                                    dist_2[np.where(leafs == best_leafs[t])[0][0]]+=1
                                                                else:
                                                                    dist_2[0]+=1
                                                            else:
                                                                if checkNodesDistr:
                                                                    no_decision[np.where(leafs == best_leafs[t])[0][0]]+=1
                                                                else:
                                                                    no_decision[0]+=1
                                                else:
                                                    if checkNodesDistr:
                                                        no_decision[np.where(leafs == best_leafs[t])[0][0]]+=1
                                                    else:
                                                        no_decision[0]+=1
                                            dist_0_val=[0]*len(dist_0)
                                            dist_1_val=[0]*len(dist_1)
                                            dist_2_val=[0]*len(dist_2)
                                            no_decision_val=[0]*len(no_decision)
                                            for xd in range(len(dist_0)):
                                                dist_0_val[xd]=round(dist_0[xd]/len(times),3)
                                                dist_1_val[xd]=round(dist_1[xd]/len(times),3)
                                                dist_2_val[xd]=round(dist_2[xd]/len(times),3)
                                                no_decision_val[xd]=round(no_decision[xd]/len(times),3)
                                            mean_val=round(mean,3)
                                            std_val=round(std,3)
                                        else:
                                            SEMprint=False
                                        if SEMprint:
                                            is_new = True
                                            if os.path.exists(base+"/Robots#"+str(A)+"/resume_"+POSorCOM+"_"+date+".csv"):
                                                is_new=False
                                            fieldnames = ["max_steps","agents","k","r","options","type","mean","std","leaf","dist_0","dist_1","dist_2","no_decision"]
                                            with open(base+"/Robots#"+str(A)+"/resume_"+POSorCOM+"_"+date+".csv","a") as f:
                                                writer = csv.DictWriter(f,fieldnames=fieldnames,dialect='unix',delimiter="\t")
                                                if is_new:
                                                    writer.writeheader()
                                                if not checkNodesDistr:
                                                    writer.writerow({"max_steps":S,"agents":A,"k":k,"r":r,"options":pow(B,D),"type":type,"mean":mean_val,"std":std_val,"leaf":-1,"dist_0":dist_0_val[0],"dist_1":dist_1_val[0],"dist_2":dist_2_val[0],"no_decision":no_decision_val[0]})
                                                    data_to_plot.update({(base,S,A,B,D,k,r,-1):(mean_val,std_val,dist_0_val[0],dist_1_val[0],dist_2_val[0],no_decision_val[0])})
                                                else:
                                                    for l in range(len(leafs)):
                                                        writer.writerow({"max_steps":S,"agents":A,"k":k,"r":r,"options":pow(B,D),"type":type,"mean":mean_val,"std":std_val,"leaf":leafs[l],"dist_0":dist_0_val[l],"dist_1":dist_1_val[l],"dist_2":dist_2_val[l],"no_decision":no_decision_val[l]})
                                                        data_to_plot.update({(base,S,A,B,D,k,r,leafs[l]):(mean_val,std_val,dist_0_val[l],dist_1_val[l],dist_2_val[l],no_decision_val[l])})
                                self.plot_percentages(data_to_plot,date,POSorCOM)

##########################################################################################################
    def sort_ark_positions_by_node(self):
        position_distribution={}
        for dfold in os.listdir(self.bases):
            if dfold[:3]=="LOG":
                branches=dfold.split('x')[0][-1]
                depth=dfold.split('x')[-1]
                dir_path = os.path.join(self.base,dfold)
                for elem in os.listdir(dir_path):
                    if '.' in elem and elem.split('_')[-1]=="LOGPos.tsv":
                        with open(os.path.join(dfold, elem), newline='') as f:
                            reader = csv.reader(f)
                            for row in reader:
                                for val in row:
                                    val = val.split('\t')

                                    x,y,n=-1,-1,-1
                                    for i in range(0,len(val)-1):
                                        z=i%3
                                        if i%3==0:
                                            x=float(val[i])
                                        elif i%3==1:
                                            y=float(val[i])
                                        elif i%3==2:
                                            n=int(val[i])
                                            if x!=-1.0 and y!=-1.0:
                                                xPOSvec,yPOSvec=[],[]
                                                if position_distribution.get((branches,depth,n))!=None:
                                                    xPOSvec=position_distribution.get((branches,depth,n))[0]
                                                    yPOSvec=position_distribution.get((branches,depth,n))[1]
                                                xPOSvec.append(x)
                                                yPOSvec.append(y)
                                                position_distribution.update({(branches,depth,n):(xPOSvec,yPOSvec)})    
        return position_distribution
    
##########################################################################################################
    def sort_kilo_positions_by_node(self):
        position_distribution={}
        for elem in os.listdir(self.bases):
            if '.' in elem and elem=="POStrial.tsv":
                with open(os.path.join(self.base, elem), newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        for val in row:
                            xPOSvec,yPOSvec=[],[]
                            val = val.split('\t')
                            n = val[0]
                            if position_distribution.get(n)!=None:
                                xPOSvec=position_distribution.get(n)[0]
                                yPOSvec=position_distribution.get(n)[1]
                            xPOSvec.append(float(val[1]))
                            yPOSvec.append(float(val[2]))
                            position_distribution.update({n:(xPOSvec,yPOSvec)})    
        return position_distribution
    
##########################################################################################################
    def plot_positions_distribution(self,data):
        if data==None:
            print("\nNo data available.\n")
            return
        data_keys=list(data.keys())
        X,Y=[],[]
        for dk in range(len(data_keys)):
            positions=data.get(data_keys[dk])
            for x in range(len(positions[0])):
                X.append(float(positions[0][x]))
                Y.append(float(positions[1][x]))
        fig = plt.subplots(figsize=(8,6))
        MAXx,MAXy=0,0
        minx,miny=999,999
        for x in X:
            if x>MAXx: MAXx=x
            if x<minx: minx=x
        for y in Y:
            if y>MAXy: MAXy=y
            if y<miny: miny=y
        plt.hexbin(Y,X,gridsize=(100,100),cmap='YlOrRd')
        plt.title(0)
        plt.colorbar()
        plt.ylim(minx,MAXx)
        plt.xlim(miny,MAXy)
        plt.tight_layout()
        plt.show(fig)
        plt.close()

##########################################################################################################
    def plot_percentages(self,data,date,POSorCOM='commitment'):
        bases=[]
        times=[]
        agents=[]
        branches=[]
        depth=[]
        Ks=[]
        Rs=[]
        Leafs=[]
        for key in data.keys():
            if key[0] not in bases: bases.append(key[0])
            if key[1] not in times: times.append(key[1])
            if key[2] not in agents: agents.append(key[2])
            if key[3] not in branches: branches.append(key[3])
            if key[4] not in depth: depth.append(key[4])
            if key[5] not in Ks: Ks.append(key[5])
            if key[6] not in Rs: Rs.append(key[6])
            if key[7] not in Leafs: Leafs.append(key[7])
        Ks=np.sort(Ks)
        Rs=np.sort(Rs)
        Leafs=np.sort(Leafs)
        for ba in bases:
            saving_path=ba
            if os.path.exists(saving_path):
                for a in agents:
                    saving_path1=saving_path+"/Robots#"+str(a)
                    if os.path.exists(saving_path1):
                        for b in branches:
                            saving_path2=saving_path1+"/Branches#"+str(b)
                            if os.path.exists(saving_path2):
                                for d in depth:
                                    saving_path3=saving_path2+"/Depth#"+str(d)
                                    if os.path.exists(saving_path3):
                                        for k in Ks:
                                            Sk=str(k).replace(".","_")
                                            saving_path4=saving_path3+"/K#"+Sk
                                            if os.path.exists(saving_path4):
                                                for ti in times:
                                                    for l in Leafs:
                                                        gotta_print=False
                                                        group_labels=[]
                                                        group_bars={}
                                                        for r in Rs: # arrange the arrays for plotting
                                                            data_tuple=data.get((ba,ti,a,b,d,k,r,l))
                                                            if data_tuple is not None:
                                                                gotta_print=True
                                                                group_labels.append("R:"+str(r))
                                                                arrFlag0,arrFlag1,arrFlag2,arrFlag3 = [],[],[],[]
                                                                if len(group_bars.keys())>0:
                                                                    arrFlag0=group_bars.get("distance 0")
                                                                    arrFlag1=group_bars.get("distance 1")
                                                                    arrFlag2=group_bars.get("distance 2")
                                                                    arrFlag3=group_bars.get("no decision")
                                                                arrFlag0.append(data_tuple[2])
                                                                arrFlag1.append(data_tuple[3])
                                                                arrFlag2.append(data_tuple[4])
                                                                arrFlag3.append(data_tuple[5])
                                                                group_bars.update({"distance 0":arrFlag0})
                                                                group_bars.update({"distance 1":arrFlag1})
                                                                group_bars.update({"distance 2":arrFlag2})
                                                                group_bars.update({"no decision":arrFlag3})
                                                        if gotta_print:
                                                            x = np.arange(len(group_labels))
                                                            width = 0.1
                                                            multiplier = 0
                                                            fig,ax = plt.subplots(figsize=(12,6))
                                                            for bkey,value in group_bars.items():
                                                                offset = width * multiplier
                                                                rects = ax.bar(x+offset,value,width,label=bkey)
                                                                multiplier += 1
                                                            ax.bar_label(rects)
                                                            ax.set_ylabel("percentages")
                                                            ax.set_xlabel("configurations")
                                                            ax.set_title("Distances R:"+str(a)+",B:"+str(b)+",D:"+str(d)+",K:"+str(Sk)+"leaf:"+str(l))
                                                            ax.set_xticks(x + width, group_labels)
                                                            ax.legend(loc='best')
                                                            ax.set_ylim(0,1.025)
                                                            plt.grid(True)
                                                            plt.tight_layout()
                                                            if not os.path.exists(ba+"/Robots#"+str(a)+"/images"):
                                                                os.mkdir(ba+"/Robots#"+str(a)+"/images")
                                                            if not os.path.exists(ba+"/Robots#"+str(a)+"/images/"+POSorCOM):
                                                                os.mkdir(ba+"/Robots#"+str(a)+"/images/"+POSorCOM)
                                                            if not os.path.exists(ba+"/Robots#"+str(a)+"/images/"+POSorCOM+"/percentages"):
                                                                os.mkdir(ba+"/Robots#"+str(a)+"/images/"+POSorCOM+"/percentages")
                                                            fig_path=ba+"/Robots#"+str(a)+"/images/"+POSorCOM+"/percentages/CONFIGp_"+POSorCOM+"__A#"+str(a)+"_"+"S#"+str(ti)+"_"+"B#"+str(b)+"_"+"D#"+str(d)+"_"+"K#"+str(k).replace(".","-")+"__"+date+".png"
                                                            # plt.show(fig)
                                                            plt.savefig(fig_path)
                                                            plt.close()
                                                        else: print("Nothing to plot")

##########################################################################################################
    def plot_pareto_diagram(self):
        # plt.rcParams.update({"font.size":18})
        # colors=['#5ec962', '#21918c','#3b528b','#440154']
        # par_colors=['#fde725','#21918c','#440154']
        # styles=[':', '--','-.','-']
        # alphas = np.linspace(0.3, 1, num=3)
        # for base in self.bases:
        #     for dir in os.listdir(base):
        #         if '.' not in dir and '#' in dir:
        #             results_dict={}
        #             times=[]
        #             Ks=[]
        #             Rs=[]
        #             options=[]
        #             types=[]
        #             pre_path=os.path.join(base, dir)
        #             for elem in os.listdir(pre_path):
        #                 if ".csv" in elem and elem.split('_')[0]=="resume":
        #                     resuming_file=os.path.join(pre_path,elem)
        #                     with open(resuming_file,newline="") as the_file:
        #                         the_reader = csv.reader(the_file)
        #                         sem_reader = 0
        #                         for row in the_reader:
        #                             if sem_reader==0:
        #                                 sem_reader = 1
        #                             else:
        #                                 if row[0] not in times: times.append(int(row[0]))
        #                                 if row[2] not in Ks: Ks.append(float(row[2]))
        #                                 if row[3] not in Rs: Rs.append(int(row[3]))
        #                                 if row[4] not in options: options.append(int(row[4]))
        #                                 if row[5] not in types: types.append(row[5])
        #                                 results_dict.update({(row[0],row[2],row[3],row[4],row[5]):(float(row[6]),float(row[8]))})
        #             img_folder = os.path.join(pre_path,"/images")
        #             if not os.path.exists(img_folder):
        #                 os.mkdir(img_folder)
        #             folder = os.path.join(img_folder,"/resume")
        #             if not os.path.exists(folder):
        #                 os.mkdir(folder)
        #             dots = [np.array([[None,None,None,None,None]]),np.array([[None,None,None,None,None]])]
        #             lines=[np.array([[None,None,None,None,None]]),np.array([[None,None,None,None,None]])]
        #             fig,ax = plt.subplots(figsize=(10, 9))
        #             ##########################################################################################################################
        #             #LABELS
        #             four = mlines.Line2D([], [], color='#5ec962', marker='_', linestyle='None', markeredgewidth=5, markersize=14, label='N=4')
        #             sixteen = mlines.Line2D([], [], color='#3b528b', marker='_', linestyle='None', markeredgewidth=5, markersize=14, label='N=16')
        #             flat = mlines.Line2D([], [], color='silver', marker='o', markerfacecolor='silver', linestyle='None', markeredgewidth=1.5, markersize=10, label='Flat tree')
        #             quad = mlines.Line2D([], [], color='silver', marker='s', markerfacecolor='silver', linestyle='None', markeredgewidth=1.5, markersize=10, label='Quad tree')
        #             binary = mlines.Line2D([], [], color='silver', marker='^', markerfacecolor='silver', linestyle='None', markeredgewidth=1.5, markersize=10, label='Binary tree')

        #             void = mlines.Line2D([], [], linestyle='None')

        #             r1 = mlines.Line2D([], [], color='#cfd3d7', marker='_', linestyle='None', markeredgewidth=5, markersize=14, label='r=1')
        #             r2 = mlines.Line2D([], [], color='#98a1a8', marker='_', linestyle='None', markeredgewidth=5, markersize=14, label='r=2')
        #             r3 = mlines.Line2D([], [], color='#000000', marker='_', linestyle='None', markeredgewidth=5, markersize=14, label='r=3')

        #             handles_t = [flat, quad, binary]
        #             handles_n = [void,four, sixteen]
        #             handles_r = [r1, r2, r3]
        #             plt.legend(handles=handles_n+handles_t+handles_r, ncol=3,loc='lower right',framealpha=.4)
        #             times=[]
        #             Ks=[]
        #             Rs=[]
        #             options=[]
        #             types=[]
        #             for t in times:
        #                 for o in options:
        #                     for ty in types:
        #                         for k in Ks:
        #                             for r in Rs:
        #                                 vals=results_dict.get((t,k,r,o,ty))
        #                                 i,j=-1,-1
        #                                 mark=""
        #                                 if r==1.0: j=0
        #                                 elif r==2.0: j=1
        #                                 elif r==3.0: j=2
        #                                 if o==4: i=0
        #                                 elif o==16: i=1
        #                                 if ty=="flat": mark='o'
        #                                 elif ty=="binary": mark='^'
        #                                 elif ty=="quad": mark='s'

        return
    