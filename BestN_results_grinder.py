import numpy as np
import os, csv
from scipy.special import gamma
from matplotlib import pyplot as plt
from lifelines import KaplanMeierFitter
from lifelines import WeibullFitter

class Grinder:

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
                                                    unordered_distances = np.array([[[]]]) # distance is from 0 to depth --> if == 0 -> optimal decision, if != 0 -> check that commitment is in leaf, otherwise there is no decision
                                                    unordered_Bleafs = np.array([])
                                                    unordered_seeds = np.array([])
                                                    for elem in os.listdir(sub_path):
                                                        if '.' in elem:
                                                            selem=elem.split('.')
                                                            # date = selem[0].split('__')[0]
                                                            if selem[-1]=="tsv" and selem[0].split('_')[-1]=="LOG":
                                                                seed=-1
                                                                best_leaf=-1
                                                                agents_commitments = np.array([[0]])
                                                                agents_locations = np.array([[0]])
                                                                agents_distances = np.array([[depth]])
                                                                for n in range(1,n_agents):
                                                                    agents_commitments = np.append(agents_commitments,[[0]],1)
                                                                    agents_locations = np.append(agents_locations,[[0]],1)
                                                                    agents_distances = np.append(agents_distances,[[depth]],1)
                                                                with open(os.path.join(sub_path, elem), newline='') as f:
                                                                    s=0
                                                                    reader = csv.reader(f)
                                                                    for row in reader:
                                                                        for val in row:
                                                                            com_arr=[]
                                                                            loc_arr=[]
                                                                            dist_arr=[]
                                                                            val = val.split('\t')
                                                                            if s==0:
                                                                                seed=int(val[0])
                                                                                best_leaf=int(val[1])
                                                                                # aggiunti angoli della best leaf dopo id...fai dopo aver sistemato
                                                                                if len(leafs)==0:
                                                                                    for i in range(6,len(val)):
                                                                                        leafs.append(int(val[i]))
                                                                                s+=1
                                                                            elif s>0:
                                                                                for i in range(1,len(val)):
                                                                                    if i%5==3:
                                                                                        loc_arr.append(int(val[i]))
                                                                                    if i%5==4:
                                                                                        com_arr.append(int(val[i]))
                                                                                    elif i%5==0:
                                                                                        dist_arr.append(int(val[i]))
                                                                                agents_commitments = np.append(agents_commitments,[com_arr],0)
                                                                                agents_locations = np.append(agents_locations,[loc_arr],0)
                                                                                agents_distances = np.append(agents_distances,[dist_arr],0)
                                                                if np.size(unordered_commitments)==0:
                                                                    unordered_commitments = np.array([agents_commitments])
                                                                    unordered_locations = np.array([agents_locations])
                                                                    unordered_distances = np.array([agents_distances])
                                                                    unordered_Bleafs = np.array([best_leaf])
                                                                    unordered_seeds = np.array([seed])
                                                                else:
                                                                    unordered_commitments = np.append(unordered_commitments,[agents_commitments],0)
                                                                    unordered_locations = np.append(unordered_locations,[agents_locations],0)
                                                                    unordered_distances = np.append(unordered_distances,[agents_distances],0)
                                                                    unordered_Bleafs = np.append(unordered_Bleafs,best_leaf)
                                                                    unordered_seeds = np.append(unordered_seeds,seed)
                                                    results.update({(base,n_agents,max_steps,branches,depth,k,r):(unordered_locations,unordered_commitments,unordered_distances,list(unordered_seeds),list(unordered_Bleafs),leafs)})
        return results,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS
    
    ##########################################################################################################
    def plot_weibulls(self,data_in,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS):
        c_map = plt.cm.get_cmap('viridis')
        N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS = np.sort(N_AGENTS),np.sort(BRACHES),np.sort(DEPTH),np.sort(K),np.sort(R),np.sort(MAX_STEPS)
        data={}
        times={}
        for base in BASES:
            for A in N_AGENTS:
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
                            for k in K:
                                for r in R:
                                    if data_in.get((base,A,S,B,D,k,r)) is not None:
                                        locations=data_in.get((base,A,S,B,D,k,r))[0]
                                        commitments=data_in.get((base,A,S,B,D,k,r))[1]
                                        distances=data_in.get((base,A,S,B,D,k,r))[2]
                                        seeds=data_in.get((base,A,S,B,D,k,r))[3]
                                        best_leafs=data_in.get((base,A,S,B,D,k,r))[4]
                                        leafs=data_in.get((base,A,S,B,D,k,r))[5]
                                        stored_times = [S+1]*len(commitments)
                                        stored_distances = [[-1]*A]*len(commitments)
                                        stored_commitments = [[0]*A]*len(commitments)
                                        stored_locations = [[0]*A]*len(commitments)
                                        for c in range(len(commitments)):
                                            semc = 0
                                            timec = S+1
                                            distances_to_store = [-1]*A
                                            commitments_to_store = [0]*A
                                            locations_to_store = [0]*A
                                            for l in range(len(commitments[c])):
                                                if semc==0:
                                                    for e in range(int(len(commitments[c][l]))):
                                                        if commitments[c][l][e] in leafs:
                                                            sum = 1
                                                            for ce in range(len(commitments[c][l])):
                                                                if e!=ce and commitments[c][l][e]==commitments[c][l][ce]:
                                                                    sum += 1
                                                            if sum >= len(commitments[c][l])*.9:
                                                                semc = 1
                                                                timec = l+1
                                                                distances_to_store = distances[c][l]
                                                                commitments_to_store = commitments[c][l]
                                                                locations_to_store = locations[c][l]
                                                                break
                                                if semc==1: break
                                            stored_times[c] = timec
                                            stored_distances[c] = list(distances_to_store)
                                            stored_commitments[c] = list(commitments_to_store)
                                            stored_locations[c] = list(locations_to_store)
                                            # print(best_leafs[c],'\n',stored_times[c],'\t',stored_commitments[c],'\t',stored_distances[c],'\t',leafs,'\n\n')
                                        data.update({(base,A,S,B,D,k,r):(stored_times,stored_locations,stored_commitments,stored_distances,list(seeds),list(best_leafs),list(leafs))})
                            for k in K:
                                x = 0
                                fig, ax = plt.subplots(figsize=(12, 6))
                                for r in R:
                                    if data.get((base,A,S,B,D,k,r)) is not None:
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
                                        kmf.cumulative_density_.plot(ax=ax,linestyle="solid",color=c_map(round(x/len(R),1)))
                                        sorted_times,censored = np.insert(sorted_times,0,1),np.insert(censored,0,0)
                                        we = WeibullFitter()
                                        we.fit(sorted_times,censored,label="R:"+str(r)+" Weibull")
                                        ci = we.confidence_interval_cumulative_density_
                                        ts = ci.index
                                        low,high = np.transpose(ci.values)
                                        plt.fill_between(ts,low,high,color="gray",alpha=0.2)
                                        we.cumulative_density_.plot(ax=ax,linestyle="dashed",color=c_map(round(x/len(R),1)))
                                        x += 1
                                        if we.median_survival_time_>S+1:
                                            times.update({(base,A,S,B,D,k,r):[-1,-1]})
                                        else:
                                            values=self.get_mean_and_std(we)
                                            times.update({(base,A,S,B,D,k,r):[values[0],values[1]]})
                                plt.grid(True,linestyle=':')
                                plt.ylabel("consensus cumulative density")
                                plt.xlabel("Seconds")
                                plt.xlim((0,S+50))
                                plt.ylim((-0.05,1.05))
                                plt.tight_layout()
                                if not os.path.exists(base+"/Robots#"+str(A)+"/images"):
                                    os.mkdir(base+"/Robots#"+str(A)+"/images")
                                fig_path=base+"/Robots#"+str(A)+"/images/CONFIGc__A#"+str(A)+"_"+"S#"+str(S)+"_"+"B#"+str(B)+"_"+"D#"+str(D)+"_"+"K#"+str(k).replace(".","-")+"__estimates.png"
                                plt.savefig(fig_path)
                                # plt.show(fig)
                                plt.close(fig)
        return (data,times),(BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS)

    ##########################################################################################################
    def write_percentages(self,data,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS):
        data_0,data_1 = data[0],data[1]
        for base in BASES:
            for A in N_AGENTS:
                if os.path.exists(base+"/Robots#"+str(A)+"/resume.csv"):
                    os.remove(base+"/Robots#"+str(A)+"/resume.csv")
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
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
                                        dist_0=0
                                        dist_1=0
                                        dist_2=0
                                        no_decision=0
                                        times=data_0.get((base,A,S,B,D,k,r))[0]
                                        locations=data_0.get((base,A,S,B,D,k,r))[1]
                                        commitments=data_0.get((base,A,S,B,D,k,r))[2]
                                        distances=data_0.get((base,A,S,B,D,k,r))[3]
                                        seeds=data_0.get((base,A,S,B,D,k,r))[4]
                                        best_leafs=data_0.get((base,A,S,B,D,k,r))[5]
                                        leafs=data_0.get((base,A,S,B,D,k,r))[6]
                                        mean=data_1.get((base,A,S,B,D,k,r))[0]
                                        std=data_1.get((base,A,S,B,D,k,r))[1]
                                        for t in range(len(times)):
                                            # print(best_leafs[t],'\n',times[t],'\t',commitments[t],'\t',distances[t],'\t',leafs[t],'\n\n')
                                            if times[t]<=S:
                                                check_4_succes=0
                                                for d in range(len(distances[t])):
                                                    if distances[t][d]==0 and commitments[t][d]==best_leafs[t]:
                                                        check_4_succes+=1
                                                if check_4_succes>=len(distances[t])*.9:
                                                    dist_0+=1
                                                else:
                                                    check_4_succes=0
                                                    for d in range(len(distances[t])):
                                                        if distances[t][d]==1 and commitments[t][d] in leafs:
                                                            check_4_succes+=1
                                                    if check_4_succes>=len(distances[t])*.9:
                                                        dist_1+=1
                                                    else:
                                                        check_4_succes=0
                                                        for d in range(len(distances[t])):
                                                            if distances[t][d]==2 and commitments[t][d] in leafs:
                                                                check_4_succes+=1
                                                        if check_4_succes>=len(distances[t])*.9:
                                                            dist_2+=1
                                                        else:
                                                            no_decision+=1
                                            else:
                                                no_decision+=1
                                        dist_0_val=round(dist_0/len(times),3)
                                        dist_1_val=round(dist_1/len(times),3)
                                        dist_2_val=round(dist_2/len(times),3)
                                        no_decision_val=round(no_decision/len(times),3)
                                        mean_val=round(mean,3)
                                        std_val=round(std,3)
                                    else:
                                        SEMprint=False
                                    if SEMprint:
                                        is_new = True
                                        if os.path.exists(base+"/Robots#"+str(A)+"/resume.csv"):
                                            is_new=False
                                        fieldnames = ["max_steps","agents","k","r","options","type","mean","std","dist_0","dist_1","dist_2","no_decision"]
                                        with open(base+"/Robots#"+str(A)+"/resume.csv","a") as f:
                                            writer = csv.DictWriter(f,fieldnames=fieldnames,dialect='unix',delimiter="\t")
                                            if is_new:
                                                writer.writeheader()
                                            writer.writerow({"max_steps":S,"agents":A,"k":k,"r":r,"options":pow(B,D),"type":type,"mean":mean_val,"std":std_val,"dist_0":dist_0_val,"dist_1":dist_1_val,"dist_2":dist_2_val,"no_decision":no_decision_val})