import numpy as np
import os, csv, math
import seaborn as sns
import matplotlib as mpl
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
plt.rcParams.update({"font.size":18})

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

class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "proc_data_part":
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
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7])):(data_val.get(keys[9]),data_val.get(keys[10]),data_val.get(keys[8]))})
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
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7])):(data_val.get(keys[9]),data_val.get(keys[10]),data_val.get(keys[8]))})
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
        if not os.path.exists(self.base+"/proc_data_part/o_images"):
            os.mkdir(self.base+"/proc_data_part/o_images")
        if not os.path.exists(self.base+"/proc_data_part/p_images"):
            os.mkdir(self.base+"/proc_data_part/p_images")
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
    def plot_active(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data_part/c_images/"):
            os.mkdir(self.base+"/proc_data_part/c_images/")
        path = self.base+"/proc_data_part/c_images/"
        dict_park_avg,dict_adms_avg,dict_our_avg = {},{},{}
        dict_park_max,dict_adms_max,dict_our_max = {},{},{}
        dict_park_fin,dict_adms_fin,dict_our_fin = {},{},{}
        ground_T, threshlds , jolly= [], [],[]
        algo,arena,runs,time,comm,agents,buf_dim = [],[],[],[],[],[],[]
        p_k,o_k = [],[]
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if float(k0[6]) not in ground_T: ground_T.append(float(k0[6]))
                if float(k0[7]) not in threshlds: threshlds.append(float(k0[7]))
                if k0[9]not in jolly: jolly.append(k0[9])
                if k0[0]not in algo: algo.append(k0[0])
                if k0[1]not in arena: arena.append(k0[1])
                if k0[2]not in runs: runs.append(k0[2])
                if k0[3]not in time: time.append(k0[3])
                if k0[4]not in comm: comm.append(k0[4])
                if k0[5]not in agents: agents.append(k0[5])
                if k0[8]not in buf_dim: buf_dim.append(k0[8])
        for i in range(len(data_in)):
            a='P' if i==1 else 'O'
            for a_s in arena:
                for n_r in runs:
                    for et in time:
                        for c in comm:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for m_t in jolly:
                                        vals = []
                                        vals_m = []
                                        vals_r = []
                                        for gt in ground_T:
                                            tmp = []
                                            t_max = []
                                            reg = []
                                            for thr in threshlds:
                                                s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t))
                                                if s_data != None:
                                                    if (i==1 and m_t not in p_k) or (i==0 and m_t not in o_k):
                                                        p_k.append(m_t) if i==1 else o_k.append(m_t)
                                                    tmp.append(round(float(s_data[2])/int(n_a),2))
                                                    t_max.append(round(np.max(s_data[0]),2))
                                                    reg.append(round(np.median(s_data[0][-30:]),2))

                                            if len(vals)==0:
                                                vals = np.array([tmp])
                                                vals_m = np.array([t_max])
                                                vals_r = np.array([reg])
                                            else:
                                                vals = np.append(vals,[tmp],axis=0)
                                                vals_m = np.append(vals_m,[t_max],axis=0)
                                                vals_r = np.append(vals_r,[reg],axis=0)
                                        if a=='P' and int(c)==0 and m_t in p_k:
                                            dict_park_avg.update({m_t:vals})
                                            dict_park_max.update({m_t:vals_m})
                                            dict_park_fin.update({m_t:vals_r})
                                        if a=='O' and m_t in o_k:
                                            if int(c)==0:
                                                dict_adms_avg.update({m_t:vals})
                                                dict_adms_max.update({m_t:vals_m})
                                                dict_adms_fin.update({m_t:vals_r})
                                            else:
                                                dict_our_avg.update({m_t:vals})
                                                dict_our_max.update({m_t:vals_m})
                                                dict_our_fin.update({m_t:vals_r})
        self.print_borders_l(path,'avg',ground_T,threshlds,[dict_park_avg,dict_adms_avg,dict_our_avg],[p_k,o_k])
        self.print_borders_l(path,'max',ground_T,threshlds,[dict_park_max,dict_adms_max,dict_our_max],[p_k,o_k])
        self.print_borders_l(path,'reg',ground_T,threshlds,[dict_park_fin,dict_adms_fin,dict_our_fin],[p_k,o_k])


##########################################################################################################
    def print_borders_r(self,path,_type,ground_T,threshlds,data_in,keys):
        cmap = mpl.colormaps["viridis"]
        cNorm  = colors.Normalize(vmin=ground_T[0], vmax=ground_T[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cmap)
    
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        p_k, o_k = keys[0],keys[1]
        fig, ax = plt.subplots(figsize=(12,6))
        for pt in range(len(ground_T)):
            P_val = dict_park.get(p_k[0])[pt]
            A_val = dict_adam.get(o_k[0])[pt]
            O_val = dict_our.get(o_k[0])[pt]
            ax.plot(P_val,ls='--',c=scalarMap.to_rgba(ground_T[pt]))
            ax.plot(A_val,ls=':',c=scalarMap.to_rgba(ground_T[pt]))
            ax.plot(O_val,ls='-',c=scalarMap.to_rgba(ground_T[pt]))
        ax.set_xticks(np.arange(len(threshlds)),labels=np.array(threshlds,dtype=str))
        ax.set_yticks(np.arange(0,1.01,.1))
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Norm "+_type+" activation")
        plt.grid(True)
        fig.tight_layout()
        fig_path = path+"_"+_type+"_trial.png"
        plt.savefig(fig_path)
        # plt.show()
        plt.close()

##########################################################################################################
    def print_borders_l(self,path,_type,ground_T,threshlds,data_in,keys):
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        p_k, o_k = keys[0],keys[1]
        colors_map = ['r','b','g','y']
        vals8p = [[0]*len(threshlds)]*len(o_k)
        vals2p = [[0]*len(threshlds)]*len(o_k)
        vals8a = [[0]*len(threshlds)]*len(o_k)
        vals2a = [[0]*len(threshlds)]*len(o_k)
        vals8o = [[0]*len(threshlds)]*len(o_k)
        vals2o = [[0]*len(threshlds)]*len(o_k)

        dots = mlines.Line2D([], [], color='black', marker='o', linestyle='None', markeredgewidth=6, markersize=6, label='P = 0.2')
        triangles = mlines.Line2D([], [], color='black', marker='^', linestyle='None', markeredgewidth=6, markersize=6, label='P = 0.8')
        red = mlines.Line2D([], [], color='r', marker='_', linestyle='None', markeredgewidth=12, markersize=12, label='shorter buffer')
        blue = mlines.Line2D([], [], color='b', marker='_', linestyle='None', markeredgewidth=12, markersize=12, label='short buffer')
        green = mlines.Line2D([], [], color='g', marker='_', linestyle='None', markeredgewidth=12, markersize=12, label='large buffer')
        yellow = mlines.Line2D([], [], color='y', marker='_', linestyle='None', markeredgewidth=12, markersize=12, label='larger buffer')
        dashed = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label='Parker')
        dotted = mlines.Line2D([], [], color='black', marker='None', linestyle=':', linewidth=4, label='Broadcast')
        solid = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label='R-Broadcast')

        void = mlines.Line2D([], [], linestyle='None')

        handles_l = [dashed,dotted,solid,void]
        handles_c = [triangles,dots,void,void]
        handles_r = [red,blue,green,yellow]
        fig, ax = plt.subplots(figsize=(12,6))
        for k in range(len(o_k)):
            for th in range(len(threshlds)):
                p_vals2,a_vals2,o_vals2 = [np.nan]*2,[np.nan]*2,[np.nan]*2
                p_vals8,a_vals8,o_vals8 = [np.nan]*2,[np.nan]*2,[np.nan]*2
                p_gt2,a_gt2,o_gt2 = [np.nan]*2,[np.nan]*2,[np.nan]*2
                p_gt8,a_gt8,o_gt8 = [np.nan]*2,[np.nan]*2,[np.nan]*2
                for pt in range(len(ground_T)):
                    P_val,A_val,O_val = dict_park.get(p_k[0])[pt][th],dict_adam.get(o_k[0])[pt][th],dict_our.get(o_k[0])[pt][th]
                    pval,aval,oval = P_val,A_val,O_val
                    if pval>=0.8:
                        if p_vals8[1] is np.nan or pval<=p_vals8[1]:
                            p_vals8[1] = pval
                            p_gt8[1] = ground_T[pt]
                    elif pval<=0.2:
                        if p_vals2[0]is np.nan or pval>=p_vals2[0]:
                            p_vals2[0] = pval
                            p_gt2[0] = ground_T[pt]
                    else:
                        if p_vals8[0]is np.nan or pval>=p_vals8[0]:
                            p_vals8[0] = pval
                            p_gt8[0] = ground_T[pt]
                        if p_vals2[1]is np.nan or pval<=p_vals2[1]:
                            p_vals2[1] = pval
                            p_gt2[1] = ground_T[pt]
                    if oval>=0.8:
                        if o_vals8[1]is np.nan or oval<=o_vals8[1]:
                            o_vals8[1] = oval
                            o_gt8[1] = ground_T[pt]
                    elif oval<=0.2:
                        if o_vals2[0]is np.nan or oval>=o_vals2[0]:
                            o_vals2[0] = oval
                            o_gt2[0] = ground_T[pt]
                    else:
                        if o_vals8[0]is np.nan or oval>=o_vals8[0]:
                            o_vals8[0] = oval
                            o_gt8[0] = ground_T[pt]
                        if o_vals2[1]is np.nan or oval<=o_vals2[1]:
                            o_vals2[1] = oval
                            o_gt2[1] = ground_T[pt]
                    if aval>=0.8:
                        if a_vals8[1]is np.nan or aval<=a_vals8[1]:
                            a_vals8[1] = aval
                            a_gt8[1] = ground_T[pt]
                    elif aval<=0.2:
                        if a_vals2[0]is np.nan or aval>=a_vals2[0]:
                            a_vals2[0] = aval
                            a_gt2[0] = ground_T[pt]
                    else:
                        if a_vals8[0]is np.nan or aval>=a_vals8[0]:
                            a_vals8[0] = aval
                            a_gt8[0] = ground_T[pt]
                        if a_vals2[1]is np.nan or aval<=a_vals2[1]:
                            a_vals2[1] = aval
                            a_gt2[1] = ground_T[pt]
                vals2p[k][th] = np.round(np.interp([0.2],p_vals2,p_gt2,left=np.nan)[0],3)
                vals2a[k][th] = np.round(np.interp([0.2],a_vals2,a_gt2,left=np.nan)[0],3)
                vals2o[k][th] = np.round(np.interp([0.2],o_vals2,o_gt2,left=np.nan)[0],3)
                vals8p[k][th] = np.round(np.interp([0.8],p_vals8,p_gt8,right=np.nan)[0],3)
                vals8a[k][th] = np.round(np.interp([0.8],a_vals8,a_gt8,right=np.nan)[0],3) 
                vals8o[k][th] = np.round(np.interp([0.8],o_vals8,o_gt8,right=np.nan)[0],3) 
            ax.plot(vals2p[k],color=colors_map[k],marker='o',ls='--')
            ax.plot(vals8p[k],color=colors_map[k],marker='^',ls='--')
            ax.plot(vals2a[k],color=colors_map[k],marker='o',ls=':')
            ax.plot(vals8a[k],color=colors_map[k],marker='^',ls=':')
            ax.plot(vals2o[k],color=colors_map[k],marker='o')
            ax.plot(vals8o[k],color=colors_map[k],marker='^')
        str_threshlds = []
        for x in threshlds:

            if np.round(np.round(x,1)-np.round(x%10,2),2) == 0.0:
                str_threshlds.append(str(x))
            else:
                str_threshlds.append('')
        ax.set_xticks(np.arange(len(str_threshlds)),labels=str_threshlds)
        ax.set_yticks(np.arange(.5,1.01,.1))
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Ground Truth")
        fig.tight_layout()
        fig_path = path+"_"+_type+"_trial.png"
        plt.grid(True)
        plt.legend(handles=handles_r+handles_l+handles_c, ncol=3,loc='upper left',framealpha=.4)
        plt.savefig(fig_path)
        # plt.show()
        plt.close()                  
##########################################################################################################
    def p_plot_heatmaps(self,keys,data_in,limit):
        print("-- Printing Heatmaps")
        if not os.path.exists(self.base+"/proc_data_part/p_images/grids/"):
            os.mkdir(self.base+"/proc_data_part/p_images/grids/")
        path = self.base+"/proc_data_part/p_images/grids/"
        states = data_in[0]
        times = data_in[1]
        buffers = data_in[2]
        for algo in keys[0]:
            for a_s in keys[1]:
                for n_r in keys[2]:
                    for et in keys[3]:
                        for c in keys[4]:
                            for n_a in keys[5]:
                                MET = [10, 13, 21, 24] if int(n_a) == 25 else [10, 32, 78, 99]
                                for m_b_d in keys[8]:
                                    for m_t in keys[9]:
                                        if int(m_t) in MET:
                                            heatmap_t = []
                                            heatmap_a = []
                                            heatmap_m = []
                                            heatmap_r = []
                                            _GT = keys[6]
                                            GT = [-1]*len(_GT)
                                            for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                            for gt in GT:
                                                list_a = [-1]*len(keys[7])
                                                list_t = [-1]*len(keys[7])
                                                list_m = [-1]*len(keys[7])
                                                list_r = [-1]*len(keys[7])
                                                for thr in range(len(keys[7])):
                                                    t_data = times.get((algo,a_s,n_r,et,c,n_a,gt,keys[7][thr],m_b_d,m_t))
                                                    s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,keys[7][thr],m_b_d,m_t))
                                                    if s_data != None:
                                                        if float(s_data[0][-1])>=limit:
                                                            list_t[thr] = round(self.extract_median(t_data[0],et),1)
                                                        list_a[thr] = round(float(s_data[2])/int(n_a),2) if float(s_data[2])>=0 else 0
                                                        list_m[thr] = round(np.max(np.array(s_data[0],dtype=float)),2)
                                                        list_r[thr] = round(np.median(np.array(s_data[0][-30:],dtype=float)),2)
                                                if len(heatmap_t)==0:
                                                    heatmap_t = np.array([list_t])
                                                    heatmap_a = np.array([list_a])
                                                    heatmap_m = np.array([list_m])
                                                    heatmap_r = np.array([list_r])
                                                else:
                                                    heatmap_t = np.append(heatmap_t,[list_t],axis=0)
                                                    heatmap_a = np.append(heatmap_a,[list_a],axis=0)
                                                    heatmap_m = np.append(heatmap_m,[list_m],axis=0)
                                                    heatmap_r = np.append(heatmap_r,[list_r],axis=0)
                                            t_mask = np.logical_and(heatmap_t>=-1,heatmap_t<=-1)
                                            t_cmap = mpl.colormaps["viridis_r"].with_extremes(bad='black', under='w', over='k')
                                            a_mask = np.logical_and(heatmap_a>=-1,heatmap_a<=-1)
                                            a_cmap = mpl.colormaps["viridis"].with_extremes(bad='black', under='w', over='k')

                                            t_fig, t_ax = plt.subplots(figsize=(24,6))
                                            t_im = sns.heatmap(heatmap_t,robust=True, cmap=t_cmap, mask=t_mask, vmin=1, vmax=100,cbar=True)
                                            # Show all ticks and label them with the respective list entries
                                            t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                            t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                            t_ax.set_xlabel("# buffer thresholds")
                                            t_ax.set_ylabel("committed percentage")
                                            # Loop over data dimensions and create text annotations.
                                            for i in range(len(GT)):
                                                for j in range(len(keys[7][:-1])):
                                                    text = t_ax.text(j, i, heatmap_t[i, j], ha="left", va="top", color="black")# if t_mask[i, j]!=1 else t_ax.text(j, i, heatmap_t[i, j], ha="left", va="top", color="black")
                                            t_ax.set_title("median time to sense quorum")
                                            t_fig.tight_layout()
                                            fig_path = path+"hmp_time__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_maxBuff#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                            plt.savefig(fig_path)
                                            # plt.show()

                                            t_fig, t_ax = plt.subplots(figsize=(24,6))
                                            t_im = sns.heatmap(heatmap_a,robust=True, cmap=a_cmap, mask=a_mask, vmin=0, vmax=1,cbar=True)
                                            # Show all ticks and label them with the respective list entries
                                            t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                            t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                            t_ax.set_xlabel("# buffer thresholds")
                                            t_ax.set_ylabel("committed percentage")
                                            # Loop over data dimensions and create text annotations.
                                            for i in range(len(GT)):
                                                for j in range(len(keys[7][:-1])):
                                                    text = t_ax.text(j, i, heatmap_a[i, j], ha="left", va="top", color="black")
                                            t_ax.set_title("avg activation")
                                            t_fig.tight_layout()
                                            fig_path = path+"hmp_avg_act__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                            plt.savefig(fig_path)
                                            # plt.show()

                                            t_fig, t_ax = plt.subplots(figsize=(24,6))
                                            t_im = sns.heatmap(heatmap_m,robust=True, cmap=a_cmap, mask=a_mask, vmin=0, vmax=1,cbar=True)
                                            # Show all ticks and label them with the respective list entries
                                            t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                            t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                            t_ax.set_xlabel("# buffer thresholds")
                                            t_ax.set_ylabel("committed percentage")
                                            # Loop over data dimensions and create text annotations.
                                            for i in range(len(GT)):
                                                for j in range(len(keys[7][:-1])):
                                                    text = t_ax.text(j, i, heatmap_m[i, j], ha="left", va="top", color="black")
                                            t_ax.set_title("max activation")
                                            t_fig.tight_layout()
                                            fig_path = path+"hmp_max_act__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                            plt.savefig(fig_path)
                                            # plt.show()

                                            t_fig, t_ax = plt.subplots(figsize=(24,6))
                                            t_im = sns.heatmap(heatmap_r,robust=True, cmap=a_cmap, mask=a_mask, vmin=0, vmax=1,cbar=True)
                                            # Show all ticks and label them with the respective list entries
                                            t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                            t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                            t_ax.set_xlabel("# buffer thresholds")
                                            t_ax.set_ylabel("committed percentage")
                                            # Loop over data dimensions and create text annotations.
                                            for i in range(len(GT)):
                                                for j in range(len(keys[7][:-1])):
                                                    text = t_ax.text(j, i, heatmap_r[i, j], ha="left", va="top", color="black")
                                            t_ax.set_title("reg activation")
                                            t_fig.tight_layout()
                                            fig_path = path+"hmp_reg_act__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                            plt.savefig(fig_path)
                                            # plt.show()

                                    heatmap_p = []
                                    _GT = keys[6]
                                    GT = [-1]*len(_GT)
                                    for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                    for gt in GT:
                                        list_p = [-1]*len(MET)
                                        for m_t in range(len(MET)):
                                            for thr in range(len(keys[7])):
                                                s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,keys[7][thr],m_b_d,str(MET[m_t])))
                                                if s_data != None:
                                                    if float(s_data[0][-1])>=limit and (float(keys[7][thr])/float(gt))>list_p[m_t]:
                                                        list_p[m_t] = round(float(keys[7][thr])/float(gt),2)
                                        if len(heatmap_p)==0:
                                            heatmap_p = np.array([list_p])
                                        else:
                                            heatmap_p = np.append(heatmap_p,[list_p],axis=0)
                                    p_mask = np.logical_and(heatmap_p>=-1,heatmap_p<=-1)
                                    p_cmap = mpl.colormaps["viridis"].with_extremes(bad='black', under='w', over='k')

                                    p_fig, p_ax = plt.subplots(figsize=(12,6))
                                    p_im = sns.heatmap(heatmap_p,robust=True, cmap=p_cmap, mask=p_mask, vmin=.75, vmax=1,cbar=True)
                                    # Show all ticks and label them with the respective list entries
                                    p_ax.set_xticks(np.arange(len(MET)), labels=MET)
                                    p_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                    p_ax.set_xlabel("buffer dimension")
                                    p_ax.set_ylabel("committed percentage")
                                    # Loop over data dimensions and create text annotations.
                                    for i in range(len(GT)):
                                        for j in range(len(MET)):
                                            text = p_ax.text(j, i, heatmap_p[i, j], ha="left", va="top", color="black")# if p_mask[i, j]!=1 else p_ax.text(j, i, heatmap_p[i, j], ha="left", va="top", color="black")
                                    p_ax.set_title("normalized MAX threshold to sense quorum")
                                    p_fig.tight_layout()
                                    fig_path = path+"hmp_thr__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                    plt.savefig(fig_path)
                                    # plt.show()
        
        return 0

##########################################################################################################
    def o_plot_heatmaps(self,keys,data_in,limit):
        print("-- Printing Heatmaps")
        if not os.path.exists(self.base+"/proc_data_part/o_images/grids/"):
            os.mkdir(self.base+"/proc_data_part/o_images/grids/")
        path = self.base+"/proc_data_part/o_images/grids/"
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
                                        heatmap_a = []
                                        heatmap_m = []
                                        heatmap_r = []
                                        _GT = keys[6][:-1]
                                        GT = [-1]*len(_GT)
                                        for g in range(len(_GT)): GT[g]=_GT[len(_GT)-1-g]
                                        for gt in GT:
                                            THR = keys[7][:-1]
                                            list_a = [-1]*len(THR)
                                            list_t = [-1]*len(THR)
                                            list_m = [-1]*len(THR)
                                            list_r = [-1]*len(THR)
                                            for thr in range(len(THR)):
                                                t_data = times.get((algo,a_s,n_r,et,c,n_a,gt,THR[thr],m_b_d,m_t))
                                                s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,THR[thr],m_b_d,m_t))
                                                if s_data != None:
                                                    if float(s_data[0][-1])>=limit:
                                                        list_t[thr] = round(self.extract_median(t_data[0],et),1)
                                                    list_a[thr] = round(float(s_data[2])/int(n_a),2) if float(s_data[2])>=0 else 0
                                                    list_m[thr] = round(np.max(np.array(s_data[0],dtype=float)),2)
                                                    list_r[thr] = round(np.median(np.array(s_data[0][-30:],dtype=float)),2)
                                            if len(heatmap_t)==0:
                                                heatmap_t = np.array([list_t])
                                                heatmap_a = np.array([list_a])
                                                heatmap_m = np.array([list_m])
                                                heatmap_r = np.array([list_r])
                                            else:
                                                heatmap_t = np.append(heatmap_t,[list_t],axis=0)
                                                heatmap_a = np.append(heatmap_a,[list_a],axis=0)
                                                heatmap_m = np.append(heatmap_m,[list_m],axis=0)
                                                heatmap_r = np.append(heatmap_r,[list_r],axis=0)

                                        t_mask = np.logical_and(heatmap_t>=-1,heatmap_t<=-1)
                                        t_cmap = mpl.colormaps["viridis_r"].with_extremes(bad='black', under='w', over='k')
                                        a_mask = np.logical_and(heatmap_a>=-1,heatmap_a<=-1)
                                        a_cmap = mpl.colormaps["viridis"].with_extremes(bad='black', under='w', over='k')

                                        t_fig, t_ax = plt.subplots(figsize=(24,6))
                                        t_im = sns.heatmap(heatmap_t,robust=True, cmap=t_cmap, mask=t_mask, vmin=1, vmax=100,cbar=True)
                                        # Show all ticks and label them with the respective list entries
                                        t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                        t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                        t_ax.set_xlabel("# buffer thresholds")
                                        t_ax.set_ylabel("committed percentage")
                                        # Loop over data dimensions and create text annotations.
                                        for i in range(len(GT)):
                                            for j in range(len(keys[7][:-1])):
                                                text = t_ax.text(j, i, heatmap_t[i, j], ha="left", va="top", color="black")# if t_mask[i, j]!=1 else t_ax.text(j, i, heatmap_t[i, j], ha="left", va="top", color="black")
                                        t_ax.set_title("median time to sense quorum")
                                        t_fig.tight_layout()
                                        fig_path = path+"hmp_time__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                        plt.savefig(fig_path)
                                        # plt.show()

                                        t_fig, t_ax = plt.subplots(figsize=(24,6))
                                        t_im = sns.heatmap(heatmap_a,robust=True, cmap=a_cmap, mask=a_mask, vmin=0, vmax=1,cbar=True)
                                        # Show all ticks and label them with the respective list entries
                                        t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                        t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                        t_ax.set_xlabel("# buffer thresholds")
                                        t_ax.set_ylabel("committed percentage")
                                        # Loop over data dimensions and create text annotations.
                                        for i in range(len(GT)):
                                            for j in range(len(keys[7][:-1])):
                                                text = t_ax.text(j, i, heatmap_a[i, j], ha="left", va="top", color="black")
                                        t_ax.set_title("avg activation")
                                        t_fig.tight_layout()
                                        fig_path = path+"hmp_avg_act__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                        plt.savefig(fig_path)
                                        # plt.show()

                                        t_fig, t_ax = plt.subplots(figsize=(24,6))
                                        t_im = sns.heatmap(heatmap_m,robust=True, cmap=a_cmap, mask=a_mask, vmin=0, vmax=1,cbar=True)
                                        # Show all ticks and label them with the respective list entries
                                        t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                        t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                        t_ax.set_xlabel("# buffer thresholds")
                                        t_ax.set_ylabel("committed percentage")
                                        # Loop over data dimensions and create text annotations.
                                        for i in range(len(GT)):
                                            for j in range(len(keys[7][:-1])):
                                                text = t_ax.text(j, i, heatmap_m[i, j], ha="left", va="top", color="black")
                                        t_ax.set_title("max activation")
                                        t_fig.tight_layout()
                                        fig_path = path+"hmp_max_act__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
                                        plt.savefig(fig_path)
                                        # plt.show()

                                        t_fig, t_ax = plt.subplots(figsize=(24,6))
                                        t_im = sns.heatmap(heatmap_r,robust=True, cmap=a_cmap, mask=a_mask, vmin=0, vmax=1,cbar=True)
                                        # Show all ticks and label them with the respective list entries
                                        t_ax.set_xticks(np.arange(len(keys[7][:-1])), labels=keys[7][:-1])
                                        t_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                        t_ax.set_xlabel("# buffer thresholds")
                                        t_ax.set_ylabel("committed percentage")
                                        # Loop over data dimensions and create text annotations.
                                        for i in range(len(GT)):
                                            for j in range(len(keys[7][:-1])):
                                                text = t_ax.text(j, i, heatmap_r[i, j], ha="left", va="top", color="black")
                                        t_ax.set_title("reg activation")
                                        t_fig.tight_layout()
                                        fig_path = path+"hmp_reg_act__CONF__alg#"+algo+"_Asize#"+a_s+"_runs#"+n_r+"_t#"+et+"_com#"+c+"_rbts#"+n_a+"_msg#"+m_t+"_minBuf#"+m_b_d+"_l#"+str(limit)+".png"
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
                                                s_data = states.get((algo,a_s,n_r,et,c,n_a,gt,THR[thr],m_b_d,str(MET[m_t])))
                                                if s_data != None:
                                                    if float(s_data[0][-1])>=limit and (float(THR[thr])/float(gt))>list_p[m_t]:
                                                        list_p[m_t] = round(float(THR[thr])/float(gt),2)
                                        if len(heatmap_p)==0:
                                            heatmap_p = np.array([list_p])
                                        else:
                                            heatmap_p = np.append(heatmap_p,[list_p],axis=0)
                                    p_mask = np.logical_and(heatmap_p>=-1,heatmap_p<=-1)
                                    p_cmap = mpl.colormaps["viridis"].with_extremes(bad='black', under='w', over='k')

                                    p_fig, p_ax = plt.subplots(figsize=(12,6))
                                    p_im = sns.heatmap(heatmap_p,robust=True, cmap=p_cmap, mask=p_mask, vmin=.75, vmax=1,cbar=True)
                                    # Show all ticks and label them with the respective list entries
                                    p_ax.set_xticks(np.arange(len(MET)), labels=MET)
                                    p_ax.set_yticks(np.arange(len(GT)), labels=GT)
                                    p_ax.set_xlabel("msgs expiring time")
                                    p_ax.set_ylabel("committed percentage")
                                    # Loop over data dimensions and create text annotations.
                                    for i in range(len(GT)):
                                        for j in range(len(MET)):
                                            text = p_ax.text(j, i, heatmap_p[i, j], ha="left", va="top", color="black")# if p_mask[i, j]!=1 else p_ax.text(j, i, heatmap_p[i, j], ha="left", va="top", color="black")
                                    p_ax.set_title("normalized MAX threshold to sense quorum")
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