
import numpy as np
import os, csv
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit
import scipy.special as sc

#####################################################
def weib_cdf(x,alpha,gamma):
    return (1-np.exp(-np.power(x/alpha,gamma)))

#####################################################
def weibull_plot(array,base,agents,steps,branches,depth,check,step=int(300)):
    col=0
    for i in array:
        if i is not None:
            col+=1
    if col!=0:
        fig, ax = plt.subplots(figsize=(14, 8))
        for i in range(len(array)):
            if array[i] is not None:
                flag=[]
                for j in range(len(array[i][2])):
                    if j==0:
                        flag.append(array[i][2][j])
                    else:
                        while flag[-1]<array[i][2][j]-1:
                            flag.append(flag[-1]+1)
                        flag.append(array[i][2][j])
                y_weib=weib_cdf(flag,array[i][3][0],array[i][3][1])
                ax.plot(flag,y_weib,linewidth=1.5,linestyle='--',label="Weibull Distribution",color=plt.cm.tab10(i) if len(array)<=10 else plt.cm.tab20(i))
                ax.plot(array[i][2],array[i][4],linewidth=2,label="K-M, (r:k)"+str(array[i][7][0])+":"+str(array[i][7][1]),color=plt.cm.tab10(i) if len(array)<=10 else plt.cm.tab20(i))
        if col>1:
            plt.legend(loc="best",borderaxespad=0,ncol=int(col/2))
        else:
            plt.legend(loc="best",borderaxespad=0)
        ax.set_yticks(np.arange(0,1.1,.05))
        plt.grid(True,linestyle=':')
        plt.ylim(-.05,1.05)
        ax.set_xticks(np.arange(0,steps+step,step))
        plt.xlabel("Number of steps")
        plt.ylabel("Synchronisation probability")
        plt.tight_layout()
        fig_path=base+"/images_"+str(check)+"/CONFIG__A#"+str(agents)+"_"+"S#"+str(steps)+"_"+"B#"+str(branches)+"_"+"D#"+str(depth)+"__weibulls.png"
        plt.savefig(fig_path)
        # plt.show()
        plt.close(fig)
        
##########################################################################################################################################################
##########################################################################################################################################################

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
                pre_path=os.path.join(base, dir)
                if '.' not in pre_path and dir.split('#')[0]=="Robots":
                    n_agents=int(dir.split('#')[1])
                    if n_agents not in N_AGENTS:
                        N_AGENTS.append(int(n_agents))
                    for dir in os.listdir(pre_path):
                        if '.' not in dir:
                            branches=int(dir.split('#')[1])
                            if branches not in BRACHES:
                                BRACHES.append(int(branches))
                            dtemp=os.path.join(pre_path, dir)
                            for sdir in os.listdir(dtemp):
                                if '.' not in sdir:
                                    depth=int(sdir.split('#')[1])
                                    if depth not in DEPTH:
                                        DEPTH.append(int(depth))
                                    stemp=os.path.join(dtemp, sdir)
                                    for ssdir in os.listdir(stemp):
                                        if '.' not in ssdir:
                                            k=float(ssdir.split('#')[1].replace("_","."))
                                            if k not in K:
                                                K.append(float(k))
                                            path_temp=os.path.join(stemp, ssdir)
                                            for folder in os.listdir(path_temp):
                                                if '.' not in folder:
                                                    # pre_params = folder.split('__') # not considering different dates 
                                                    # params = pre_params[-1].split('_')
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
                                                                                    # for i in range(6,len(val)):
                                                                                    for i in range(2,len(val)):
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
    def plot_weibulls(self,data,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS):
        N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS = np.sort(N_AGENTS),np.sort(BRACHES),np.sort(DEPTH),np.sort(K),np.sort(R),np.sort(MAX_STEPS)
        data_loc={}
        data_com={}
        times_loc={}
        times_com={}
        for base in BASES:
            for A in N_AGENTS:
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
                            for r in R:
                                for k in K:
                                    if data.get((base,A,S,B,D,k,r)) is not None:
                                        locations=data.get((base,A,S,B,D,k,r))[0]
                                        commitments=data.get((base,A,S,B,D,k,r))[1]
                                        distances=data.get((base,A,S,B,D,k,r))[2]
                                        seeds=data.get((base,A,S,B,D,k,r))[3]
                                        best_leafs=data.get((base,A,S,B,D,k,r))[4]
                                        leafs=data.get((base,A,S,B,D,k,r))[5]
                                        stored_times_com = [S+1]*len(commitments)
                                        stored_distances_com = [[-1]*A]*len(commitments)
                                        stored_commitments_com = [[0]*A]*len(commitments)
                                        stored_locations_com = [[0]*A]*len(commitments)
                                        stored_times_loc = [S+1]*len(commitments)
                                        stored_distances_loc = [[-1]*A]*len(commitments)
                                        stored_commitments_loc = [[0]*A]*len(commitments)
                                        stored_locations_loc = [[0]*A]*len(commitments)
                                        for c in range(len(commitments)):
                                            semc = 0
                                            seml = 0
                                            timec = S+1
                                            timel = S+1
                                            distances_to_store_com = [-1]*A
                                            commitments_to_store_com = [0]*A
                                            locations_to_store_com = [0]*A
                                            distances_to_store_loc = [-1]*A
                                            commitments_to_store_loc = [0]*A
                                            locations_to_store_loc = [0]*A
                                            for l in range(len(commitments[c])):
                                                if semc==0:
                                                    for e in range(int(len(commitments[c][l])*.33)):
                                                        if commitments[c][l][e] in leafs:
                                                            sum = 0
                                                            for ce in range(len(commitments[c][l])):
                                                                if e!=ce and commitments[c][l][e]==commitments[c][l][ce]:
                                                                    sum += 1
                                                            if sum >= len(commitments[c][l])*.9:
                                                                semc = 1
                                                                timec = l+1
                                                                distances_to_store_com = distances[c][l]
                                                                commitments_to_store_com = commitments[c][l]
                                                                locations_to_store_com = locations[c][l]
                                                                break
                                                if seml==0:
                                                    for e in range(int(len(locations[c][l])*.33)):
                                                        if locations[c][l][e] in leafs:
                                                            sum = 0
                                                            for ce in range(len(locations[c][l])):
                                                                if e!=ce and locations[c][l][e]==locations[c][l][ce]:
                                                                    sum += 1
                                                            if sum >= len(locations[c][l])*.9:
                                                                seml = 1
                                                                timel = l+1
                                                                distances_to_store_loc = distances[c][l]
                                                                commitments_to_store_loc = commitments[c][l]
                                                                locations_to_store_loc = locations[c][l]
                                                                break

                                                if semc==1 and seml==1: break
                                            stored_times_com[c] = timec
                                            stored_distances_com[c] = list(distances_to_store_com)
                                            stored_commitments_com[c] = list(commitments_to_store_com)
                                            stored_locations_com[c] = list(locations_to_store_com)
                                            stored_times_loc[c] = timel
                                            stored_distances_loc[c] = list(distances_to_store_loc)
                                            stored_commitments_loc[c] = list(commitments_to_store_loc)
                                            stored_locations_loc[c] = list(locations_to_store_loc)
                                        data_com.update({(base,A,S,B,D,k,r):(stored_times_com,stored_locations_com,stored_commitments_com,stored_distances_com,seeds,best_leafs,leafs)})
                                        data_loc.update({(base,A,S,B,D,k,r):(stored_times_loc,stored_locations_loc,stored_commitments_loc,stored_distances_loc,seeds,best_leafs,leafs)})
                            plot_arr_com=[None]*len(K)*len(R)
                            plot_arr_com_index=0
                            plot_arr_loc=[None]*len(K)*len(R)
                            plot_arr_loc_index=0
                            wMAX_loc = 0
                            wMAX_com = 0
                            for r in R:
                                for k in K:
                                    if data_com.get((base,A,S,B,D,k,r)) is not None:
                                        sorted_times = np.sort(data_com.get((base,A,S,B,D,k,r))[0],axis=None,kind='stable')
                                        sorted_times = np.insert(sorted_times,0,0)
                                        censored=[]
                                        for j in range(len(sorted_times)):
                                            if sorted_times[j]==S+1:
                                                s=0
                                                for c in censored:
                                                    if c != 0: s+=c
                                                censored.append(s+1)
                                            else:
                                                censored.append(0)
                                        ones=0
                                        for c in censored:
                                            if c>=1: ones+=1
                                        if ones>.9*(len(sorted_times)-1):
                                            print("COMMITMENTS--key(#agents,Msteps,branches,depth,r,k): ("+str(A)+","+str(S)+","+str(B)+","+str(D)+","+str(r)+","+str(k)+"), NOT enough entries for mean and std")
                                        else:
                                            for x in range(len(sorted_times)):
                                                if sorted_times[x]==S+1: sorted_times[x]=S+1
                                            flag=[0]*len(sorted_times)
                                            for st in range(len(sorted_times)):
                                                tmp=len(sorted_times)-st+1
                                                if tmp>0:
                                                    for sst in range(st+1,len(sorted_times)):
                                                        if sorted_times[sst]==sorted_times[st]:
                                                            tmp-=1
                                                        else:
                                                            flag[st]=tmp
                                                            break
                                            RT=[1]
                                            for f in range(1,len(flag)):
                                                if flag[f]==0:
                                                    RT.append(RT[-1])
                                                else:
                                                    RT.append(RT[-1]*((flag[f]-1)/(flag[f]+censored[f])))
                                            FT=[]
                                            for rt in RT:
                                                FT.append(1-rt)
                                            step = 1
                                            pre=0.1
                                            lim=step
                                            a=1
                                            if sorted_times[-1]>wMAX_com:
                                                wMAX_com=sorted_times[-1]
                                            while a>.05:
                                                popt_weibull,_ = curve_fit(weib_cdf,xdata=sorted_times,ydata=FT,bounds=(pre,lim),method='trf')
                                                mean = sc.gamma(1+(1./popt_weibull[1]))*popt_weibull[0]
                                                std_dev = np.sqrt(popt_weibull[0]**2 * sc.gamma(1+(2./popt_weibull[1])) - mean**2)
                                                plot_arr_com[plot_arr_com_index]=[mean,std_dev,sorted_times,popt_weibull,FT,'test',ones,(r,k)]
                                                y_weib=weib_cdf(plot_arr_com[plot_arr_com_index][2],plot_arr_com[plot_arr_com_index][3][0],plot_arr_com[plot_arr_com_index][3][1])
                                                err=0
                                                for ft in range(len(FT)):
                                                    if y_weib[ft]-FT[ft]>err:
                                                        err=y_weib[ft]-FT[ft]
                                                a=err
                                                pre=lim
                                                lim=lim+step
                                            print("COMMITMENTS--key(#agents,Msteps,branches,depth,r,k): ("+str(A)+","+str(S)+","+str(B)+","+str(D)+","+str(r)+","+str(k)+"), removed: "+str(ones)+", mean: "+str(mean)+", std: "+str(std_dev))
                                            times_com.update({(base,A,S,B,D,k,r):[plot_arr_com[plot_arr_com_index][0],plot_arr_com[plot_arr_com_index][1],y_weib[-1]]})
                                            plot_arr_com_index+=1
                                    if data_loc.get((base,A,S,B,D,k,r)) is not None:
                                        sorted_times = np.sort(data_loc.get((base,A,S,B,D,k,r))[0],axis=None,kind='stable')
                                        sorted_times = np.insert(sorted_times,0,0)
                                        censored=[]
                                        for j in range(len(sorted_times)):
                                            if sorted_times[j]==S+1:
                                                s=0
                                                for c in censored:
                                                    if c != 0: s+=c
                                                censored.append(s+1)
                                            else:
                                                censored.append(0)
                                        ones=0
                                        for c in censored:
                                            if c>=1: ones+=1
                                        if ones>.9*(len(sorted_times)-1):
                                            print("LOCATIONS--key(#agents,Msteps,branches,depth,r,k): ("+str(A)+","+str(S)+","+str(B)+","+str(D)+","+str(r)+","+str(k)+"), NOT enough entries for mean and std")
                                        else:
                                            for x in range(len(sorted_times)):
                                                if sorted_times[x]==S+1: sorted_times[x]=S+1
                                            flag=[0]*len(sorted_times)
                                            for st in range(len(sorted_times)):
                                                tmp=len(sorted_times)-st+1
                                                if tmp>0:
                                                    for sst in range(st+1,len(sorted_times)):
                                                        if sorted_times[sst]==sorted_times[st]:
                                                            tmp-=1
                                                        else:
                                                            flag[st]=tmp
                                                            break
                                            RT=[1]
                                            for f in range(1,len(flag)):
                                                if flag[f]==0:
                                                    RT.append(RT[-1])
                                                else:
                                                    RT.append(RT[-1]*((flag[f]-1)/(flag[f]+censored[f])))
                                            FT=[]
                                            for rt in RT:
                                                FT.append(1-rt)
                                            step = 1
                                            pre=0.1
                                            lim=step
                                            a=1
                                            if sorted_times[-1]>wMAX_loc:
                                                wMAX_loc=sorted_times[-1]
                                            while a>.05:
                                                popt_weibull,_ = curve_fit(weib_cdf,xdata=sorted_times,ydata=FT,bounds=(pre,lim),method='trf')
                                                mean = sc.gamma(1+(1./popt_weibull[1]))*popt_weibull[0]
                                                std_dev = np.sqrt(popt_weibull[0]**2 * sc.gamma(1+(2./popt_weibull[1])) - mean**2)
                                                plot_arr_loc[plot_arr_loc_index]=[mean,std_dev,sorted_times,popt_weibull,FT,'test',ones,(r,k)]
                                                y_weib=weib_cdf(plot_arr_loc[plot_arr_loc_index][2],plot_arr_loc[plot_arr_loc_index][3][0],plot_arr_loc[plot_arr_loc_index][3][1])
                                                err=0
                                                for ft in range(len(FT)):
                                                    if y_weib[ft]-FT[ft]>err:
                                                        err=y_weib[ft]-FT[ft]
                                                a=err
                                                pre=lim
                                                lim=lim+step
                                            print("LOCATIONS--key(#agents,Msteps,branches,depth,r,k): ("+str(A)+","+str(S)+","+str(B)+","+str(D)+","+str(r)+","+str(k)+"), removed: "+str(ones)+", mean: "+str(mean)+", std: "+str(std_dev))
                                            times_loc.update({(base,A,S,B,D,k,r):[plot_arr_loc[plot_arr_loc_index][0],plot_arr_loc[plot_arr_loc_index][1],y_weib[-1]]})
                                            plot_arr_loc_index+=1
                            if plot_arr_com_index>0: self.print_data_weib("com",plot_arr_com,base,A,S,B,D)
                            if plot_arr_loc_index>0: self.print_data_weib("loc",plot_arr_loc,base,A,S,B,D)
        return (data_com,times_com,"com"),(data_loc,times_loc,"loc"),(BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS)

    ##########################################################################################################
    def write_percentages(self,data,BASES,N_AGENTS,BRACHES,DEPTH,K,R,MAX_STEPS):
        data_0,data_1,data_2 = data[0],data[1], data[2]
        for base in BASES:
            for A in N_AGENTS:
                for S in MAX_STEPS:
                    for B in BRACHES:
                        for D in DEPTH:
                            for r in R:
                                for k in K:
                                    if data_0.get((base,A,S,B,D,k,r)) is not None and data_1.get((base,A,S,B,D,k,r)) is not None:
                                        type="unknown"
                                        if D==1:
                                            type="flat"
                                        elif B==2:
                                            type="binary"
                                        elif B==4:
                                            type="quad"
                                        success=0
                                        sync=0
                                        times=data_0.get((base,A,S,B,D,k,r))[0]
                                        locations=data_0.get((base,A,S,B,D,k,r))[1]
                                        commitments=data_0.get((base,A,S,B,D,k,r))[2]
                                        distances=data_0.get((base,A,S,B,D,k,r))[3]
                                        best_leafs=data_0.get((base,A,S,B,D,k,r))[4]
                                        leafs=data_0.get((base,A,S,B,D,k,r))[5]
                                        
                                        mean=data_1.get((base,A,S,B,D,k,r))[0]
                                        std=data_1.get((base,A,S,B,D,k,r))[1]
                                        sync_est=data_1.get((base,A,S,B,D,k,r))[2]
                                        sync=0
                                        for t in range(len(times)):
                                            if times[t]<=S:
                                                check_4_succes=0
                                                sync+=1
                                                for d in distances[t]:
                                                    if d==0:
                                                        check_4_succes+=1
                                                if check_4_succes>=len(distances[t])*.9:
                                                    success+=1
                                        success=success/len(times)
                                        sync=sync/len(times)
                                        is_new = True
                                        if os.path.exists(base+"/resume_"+data_2+".csv"):
                                            is_new=False
                                        fieldnames = ["max_steps","agents","k","r","options","type","sync_est","sync","success","mean","std"]
                                        with open(base+"/resume_"+data_2+".csv","a") as f:
                                            writer = csv.DictWriter(f,fieldnames=fieldnames,dialect='unix',delimiter="\t")
                                            if is_new:
                                                writer.writeheader()
                                            writer.writerow({"max_steps":S,"agents":A,"k":k,"r":r,"options":pow(B,D),"type":type,"sync_est":round(sync_est,3),"sync":round(sync,3),"success":round(success,3),"mean":round(mean,3),"std":round(std,3)})
                                        

    ##########################################################################################################
    def print_data_weib(self,check,p_arr,base,agents,steps,branches,depth):
        mean_y=[]
        std_e=[]
        x=[]
        for p in range(len(p_arr)):
            if p_arr[p] is not None:
                mean_y.append(round(p_arr[p][0],2))
                std_e.append(round(p_arr[p][1],2))
                x.append(str(p_arr[p][7][0])+":"+str(p_arr[p][7][1]))
        fig,ax = plt.subplots(figsize=(10,5))
        ax.errorbar(x, mean_y, std_e, linestyle='None',fmt='-', marker='o')
        ax.set_xlabel('r:k')
        ax.set_ylabel('steps')
        plt.grid(True,linestyle=':')
        plt.tight_layout()
        if not os.path.exists(base+"/images_"+check):
            os.mkdir(base+"/images_"+check)
        fig_path=base+"/images_"+check+"/CONFIG__A#"+str(agents)+"_"+"S#"+str(steps)+"_"+"B#"+str(branches)+"_"+"D#"+str(depth)+"__mean_and_std.png"
        plt.savefig(fig_path)
        # plt.show()
        plt.close()
        weibull_plot(p_arr,base,agents,steps,branches,depth,check)
