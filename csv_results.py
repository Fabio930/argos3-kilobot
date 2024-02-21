import numpy as np
import os, csv, math
import seaborn as sns
import matplotlib as mpl
from matplotlib import pyplot as plt

class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "proc_data":
                self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def read_csv(self,path,algo,n_runs,arena):
        lc = 0
        keys = []
        data = {}
        with open(path, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                change = 0
                if lc == 0:
                    for val in row:
                        keys=val.split('\t')
                else:
                    array_val = []
                    std_val = []
                    data_val = {}
                    for val in row:
                        split_val = val.split('\t')
                        if len(split_val)==1:
                            tval = val  
                            if ']' in val:
                                tval = ''
                                for c in val:
                                    if c != ']':
                                        tval+=c
                            array_val.append(float(tval)) if change==0 else std_val.append(float(tval))
                            if ']' in val:
                                data_val.update({keys[-2]:array_val})
                                data_val.update({keys[-1]:std_val})
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7])):(data_val.get(keys[8]),data_val.get(keys[9]))})
                        elif len(split_val)==2:
                            lval = ""
                            rval = ""
                            change = 1
                            for c in split_val[0]:
                                if c != ']':
                                    lval += c
                            for c in split_val[1]:
                                if c != '[':
                                    rval += c
                            if rval == '-':
                                rval = -1
                            array_val.append(float(lval))
                            std_val.append(float(rval))
                            if rval == -1:
                                data_val.update({keys[-2]:array_val})
                                data_val.update({keys[-1]:std_val})
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7])):(data_val.get(keys[8]),data_val.get(keys[9]))})
                        else:
                            for k in range(len(split_val)):
                                tval = split_val[k]
                                if '[' in split_val[k]:
                                    tval = ''
                                    for c in split_val[k]:
                                        if c != '[':
                                            tval+=c
                                    array_val.append(float(tval))
                                else:
                                    data_val.update({keys[k]:tval})
                lc += 1
        return data

##########################################################################################################
    def divide_data(self,data):
        if not os.path.exists(self.base+"/proc_data/o_images"):
            os.mkdir(self.base+"/proc_data/o_images")
        if not os.path.exists(self.base+"/proc_data/p_images"):
            os.mkdir(self.base+"/proc_data/p_images")
        states, times, buffer, messages_b, messages_r = {},{},{},{},{}
        algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time = [],[],[],[],[],[],[],[],[],[]
        for k in data.keys():
            for i in range(len(k)-1):
                if i == 0 and k[i] not in algorithm: algorithm.append(k[i])
                elif i == 1 and k[i] not in arena_size: arena_size.append(k[i])
                elif i == 2 and k[i] not in n_runs: n_runs.append(k[i])
                elif i == 3 and k[i] not in exp_time: exp_time.append(k[i])
                elif i == 4 and k[i] not in communication: communication.append(k[i])
                elif i == 5 and k[i] not in n_agents: n_agents.append(k[i])
                elif i == 6 and k[i] not in gt: gt.append(k[i])
                elif i == 7 and k[i] not in thrlds: thrlds.append(k[i])
                elif i == 8 and k[i] not in min_buff_dim: min_buff_dim.append(k[i])
                elif i == 9 and k[i] not in msg_time: msg_time.append(k[i])
            if k[-1] == "times":
                times.update({k[:-1]:data.get(k)})
            elif k[-1] == "swarm_state":
                states.update({k[:-1]:data.get(k)})
            elif k[-1] == "quorum_length":
                buffer.update({k[:-1]:data.get(k)})
            elif k[-1] == "broadcast_msg":
                messages_b.update({k[:-1]:data.get(k)})
            elif k[-1] == "rebroadcast_msg":
                messages_r.update({k[:-1]:data.get(k)})
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time), states, times, buffer, (messages_b, messages_r)
    
##########################################################################################################
    def p_plot_heatmaps(self,keys,data_in,limit):
        print("-- Printing Heatmaps")
        if not os.path.exists(self.base+"/proc_data/p_images/grids/"):
            os.mkdir(self.base+"/proc_data/p_images/grids/")
        path = self.base+"/proc_data/p_images/grids/"
        states = data_in[0]
        times = data_in[1]
        buffers = data_in[2]
        for algo in keys[0]:
            for a_s in keys[1]:
                for n_r in keys[2]:
                    for et in keys[3]:
                        for c in keys[4]:
                            for n_a in keys[5]:
                                for m_b_d in keys[8]:
                                    for m_t in keys[9]:
                                        heatmap_t = []
                                        _GT = keys[6]
                                        GT = [-1]*len(_GT)
                                        for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                        for gt in GT:
                                            list_t = [-1]*len(keys[7])
                                            for thr in range(len(keys[7])):
                                                if float(keys[7][thr])<=float(gt):
                                                    t_data = times.get((algo,a_s,n_r,et,c,n_a,gt,keys[7][thr],m_b_d,m_t))
                                                    s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,keys[7][thr],m_b_d,m_t))
                                                    if s_data != None:
                                                        for p in range(len(s_data[0])):
                                                            if float(s_data[0][p])>=limit:
                                                                list_t[thr] = round(self.extract_median(t_data[0],et),1)
                                                                break
                                            if len(heatmap_t)==0:
                                                heatmap_t = np.array([list_t])
                                            else:
                                                heatmap_t = np.append(heatmap_t,[list_t],axis=0)
                                        t_mask = np.logical_and(heatmap_t>=-1,heatmap_t<=-1)
                                        t_cmap = mpl.colormaps["viridis_r"].with_extremes(bad='white', under='w', over='k')

                                        t_fig, t_ax = plt.subplots(figsize=(24,6))
                                        t_im = sns.heatmap(heatmap_t,robust=True, cmap=t_cmap, mask=t_mask, vmin=1, vmax=int(et),cbar=True)
                                        # Show all ticks and label them with the respective list entries
                                        t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                        t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                        t_ax.set_xlabel("# buffer thresholds")
                                        t_ax.set_ylabel("committed percentage")
                                        # Loop over data dimensions and create text annotations.
                                        for i in range(len(GT)):
                                            for j in range(len(keys[7][:-1])):
                                                text = t_ax.text(j, i, heatmap_t[i, j], ha="left", va="top", color="w")
                                        t_ax.set_title("median time to sense quorum")
                                        t_fig.tight_layout()
                                        fig_path = path+"hmp_time__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_maxBuff#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                        plt.savefig(fig_path)
                                        # plt.show()
                                    heatmap_p = []
                                    _GT = keys[6]
                                    GT = [-1]*len(_GT)
                                    for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                    for gt in GT:
                                        list_p = [-1]*len(keys[9])
                                        MET = []
                                        for i in keys[9]:
                                            MET.append(int(i))
                                        MET = np.sort(MET)
                                        for m_t in range(len(MET)):
                                            for thr in range(len(keys[7])):
                                                if float(keys[7][thr])<=float(gt):
                                                    s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,keys[7][thr],m_b_d,str(MET[m_t])))
                                                    if s_data != None:
                                                        for p in range(len(s_data[0])):
                                                            if float(s_data[0][p])>=limit and (float(keys[7][thr])/float(gt))>list_p[m_t]:
                                                                list_p[m_t] = round(float(keys[7][thr])/float(gt),2)
                                        if len(heatmap_p)==0:
                                            heatmap_p = np.array([list_p])
                                        else:
                                            heatmap_p = np.append(heatmap_p,[list_p],axis=0)
                                    p_mask = np.logical_and(heatmap_p>=-1,heatmap_p<=-1)
                                    p_cmap = mpl.colormaps["viridis"].with_extremes(bad='white', under='w', over='k')

                                    p_fig, p_ax = plt.subplots(figsize=(24,6))
                                    p_im = sns.heatmap(heatmap_p,robust=True, cmap=p_cmap, mask=p_mask, vmin=.8, vmax=1,cbar=True)
                                    # Show all ticks and label them with the respective list entries
                                    p_ax.set_xticks(np.arange(len(MET)), labels=MET)
                                    p_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                    p_ax.set_xlabel("buffer dimension")
                                    p_ax.set_ylabel("committed percentage")
                                    # Loop over data dimensions and create text annotations.
                                    for i in range(len(GT)):
                                        for j in range(len(MET)):
                                            text = p_ax.text(j, i, heatmap_p[i, j], ha="left", va="top", color="w")
                                    p_ax.set_title("maximum threshold to sense quorum")
                                    p_fig.tight_layout()
                                    fig_path = path+"hmp_thr__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                    plt.savefig(fig_path)
                                    # plt.show()
        
        return 0

##########################################################################################################
    def o_plot_heatmaps(self,keys,data_in,limit):
        print("-- Printing Heatmaps")
        if not os.path.exists(self.base+"/proc_data/o_images/grids/"):
            os.mkdir(self.base+"/proc_data/o_images/grids/")
        path = self.base+"/proc_data/o_images/grids/"
        states = data_in[0]
        times = data_in[1]
        buffers = data_in[2]
        for algo in keys[0]:
            for a_s in keys[1]:
                for n_r in keys[2]:
                    for et in keys[3]:
                        for c in keys[4]:
                            for n_a in keys[5]:
                                MBD = keys[8][:-1]
                                for m_b_d in MBD:
                                    for m_t in keys[9]:
                                        heatmap_t = []
                                        _GT = keys[6][:-1]
                                        GT = [-1]*len(_GT)
                                        for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                        for gt in GT:
                                            THR = keys[7][:-1]
                                            list_t = [-1]*len(THR)
                                            for thr in range(len(THR)):
                                                if float(THR[thr])<=float(gt):
                                                    t_data = times.get((algo,a_s,n_r,et,c,n_a,gt,THR[thr],m_b_d,m_t))
                                                    s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,THR[thr],m_b_d,m_t))
                                                    if s_data != None:
                                                        for p in range(len(s_data[0])):
                                                            if float(s_data[0][p])>=limit:
                                                                list_t[thr] = round(self.extract_median(t_data[0],et),1)
                                                                break
                                            if len(heatmap_t)==0:
                                                heatmap_t = np.array([list_t])
                                            else:
                                                heatmap_t = np.append(heatmap_t,[list_t],axis=0)
                                        t_mask = np.logical_and(heatmap_t>=-1,heatmap_t<=-1)
                                        t_cmap = mpl.colormaps["viridis_r"].with_extremes(bad='white', under='w', over='k')

                                        t_fig, t_ax = plt.subplots(figsize=(24,6))
                                        t_im = sns.heatmap(heatmap_t,robust=True, cmap=t_cmap, mask=t_mask, vmin=1, vmax=int(et),cbar=True)
                                        # Show all ticks and label them with the respective list entries
                                        t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                        t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                        t_ax.set_xlabel("# buffer thresholds")
                                        t_ax.set_ylabel("committed percentage")
                                        # Loop over data dimensions and create text annotations.
                                        for i in range(len(GT)):
                                            for j in range(len(keys[7][:-1])):
                                                text = t_ax.text(j, i, heatmap_t[i, j], ha="left", va="top", color="w")
                                        t_ax.set_title("median time to sense quorum")
                                        t_fig.tight_layout()
                                        fig_path = path+"hmp_time__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                        plt.savefig(fig_path)
                                        # plt.show()
                                    heatmap_p = []
                                    _GT = keys[6][:-1]
                                    GT = [-1]*len(_GT)
                                    for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                    for gt in GT:
                                        list_p = [-1]*len(keys[9])
                                        MET = []
                                        for i in keys[9]:
                                            MET.append(int(i))
                                        MET = np.sort(MET)
                                        for m_t in range(len(MET)):
                                            THR = keys[7][:-1]
                                            for thr in range(len(THR)):
                                                if float(THR[thr])<=float(gt):
                                                    s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,THR[thr],m_b_d,str(MET[m_t])))
                                                    if s_data != None:
                                                        for p in range(len(s_data[0])):
                                                            if float(s_data[0][p])>=limit and (float(THR[thr])/float(gt))>list_p[m_t]:
                                                                list_p[m_t] = round(float(THR[thr])/float(gt),2)
                                        if len(heatmap_p)==0:
                                            heatmap_p = np.array([list_p])
                                        else:
                                            heatmap_p = np.append(heatmap_p,[list_p],axis=0)
                                    p_mask = np.logical_and(heatmap_p>=-1,heatmap_p<=-1)
                                    p_cmap = mpl.colormaps["viridis"].with_extremes(bad='white', under='w', over='k')

                                    p_fig, p_ax = plt.subplots(figsize=(24,6))
                                    p_im = sns.heatmap(heatmap_p,robust=True, cmap=p_cmap, mask=p_mask, vmin=.8, vmax=1,cbar=True)
                                    # Show all ticks and label them with the respective list entries
                                    p_ax.set_xticks(np.arange(len(MET)), labels=MET)
                                    p_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                    p_ax.set_xlabel("msgs expiring time")
                                    p_ax.set_ylabel("committed percentage")
                                    # Loop over data dimensions and create text annotations.
                                    for i in range(len(GT)):
                                        for j in range(len(MET)):
                                            text = p_ax.text(j, i, heatmap_p[i, j], ha="left", va="top", color="w")
                                    p_ax.set_title("maximum threshold to sense quorum")
                                    p_fig.tight_layout()
                                    fig_path = path+"hmp_thr__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                    plt.savefig(fig_path)
                                    # plt.show()
        return 0

##########################################################################################################
    def extract_median(self,array,max_time):
        mt = int(max_time)
        median = -1
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0 and sortd_arr[(len(sortd_arr)//2)]!=mt:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            if sortd_arr[math.ceil(len(sortd_arr)/2)]!=mt: median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median