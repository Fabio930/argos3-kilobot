import numpy as np
import os, csv, math
import matplotlib as mpl
import seaborn as sns
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "msgs_data" or elem == "proc_data":
                self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def plot_messages(self,data):
        dict_park, dict_adam, dict_our = {},{},{}
        for k in data.keys():
            if k[1]=='P':
                dict_park.update({(k[0],k[3],k[4]):data.get(k)})
            else:
                if int(k[2])==0:
                    dict_adam.update({(k[0],k[3],k[4]):data.get(k)})
                else:
                    dict_our.update({(k[0],k[3],k[4]):data.get(k)})
        self.print_messages([dict_park,dict_adam,dict_our])
##########################################################################################################
    def read_msgs_csv(self,path):
        data = {}
        lc = 0
        with open(path,newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if lc == 0:
                    lc = 1
                else:
                    keys = []
                    array_val=[]
                    for val in row:
                        split_val = val.split('\t')
                        if len(split_val)==1:
                            tval = val  
                            if ']' in val:
                                tval = ''
                                for c in val:
                                    if c != ']':
                                        tval+=c
                            array_val.append(float(tval))
                            if ']' in val:
                                data.update({(keys[0],keys[1],keys[2],keys[3],keys[4]):array_val})
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
                                    keys.append(tval)
        return data

##########################################################################################################
    def read_recovery_csv(self,path,algo,arena):
        data = {}
        lc = 0
        with open(path,newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if lc == 0:
                    lc = 1
                else:
                    for val in row:
                        split_val = val.split('\t')
                        data.update({(algo,arena,split_val[0],split_val[1],split_val[2],split_val[3],split_val[4],split_val[5],split_val[6]):(split_val[7],split_val[8])})                        
        return data

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
        states, times, messages_b, messages_r = {},{},{},{}
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
            elif k[-1] == "broadcast_msg":
                messages_b.update({k[:-1]:data.get(k)})
            elif k[-1] == "rebroadcast_msg":
                messages_r.update({k[:-1]:data.get(k)})
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time), states, times, (messages_b, messages_r)
        
##########################################################################################################
    def plot_recovery(self,data_in):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park, dict_adms, dict_our              = {},{},{}
        ground_T, threshlds, jolly                  = [],[],[]
        algo, arena, time, comm, agents, buf_dim    = [],[],[],[],[],[]
        p_k, o_k                                    = [],[]
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in arena: arena.append(k0[1])
                if k0[2] not in time: time.append(k0[2])
                if k0[3] not in comm: comm.append(k0[3])
                if k0[4] not in agents: agents.append(k0[4])
                if k0[5] not in buf_dim: buf_dim.append(k0[5])
                if k0[6] not in ground_T: ground_T.append(k0[6])
                if k0[7] not in threshlds: threshlds.append(k0[7])
                if k0[8] not in jolly: jolly.append(k0[8])
        for i in range(len(data_in)):
            for a in algo:
                for a_s in arena:
                    for et in time:
                        for c in comm:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for m_t in jolly:
                                        for gt in ground_T:
                                            tmp = []
                                            for thr in threshlds:
                                                s_data = data_in[i].get((a,a_s,et,c,n_a,m_b_d,gt,thr,m_t))
                                                if s_data != None:
                                                    if (a=='P' and m_b_d not in p_k) or (a=='O' and m_b_d not in o_k):
                                                        p_k.append(m_b_d) if a=='P' else o_k.append(m_b_d)
                                                    value =round(float(s_data[0]),3)
                                                    tmp.append(value)
                                                else:
                                                    if (a=='P' and ((a_s=='bigA' and ((n_a=='25' and (m_b_d=='11' or m_b_d=='15' or m_b_d=='17' or m_b_d=='19' or m_b_d=='21')) or
                                                                    (n_a=='100' and (m_b_d=='41' or m_b_d=='56' or m_b_d=='65' or m_b_d=='74' or m_b_d=='83')))) or
                                                                    (a_s=='smallA' and (n_a=='25' and (m_b_d=='19' or m_b_d=='22' or m_b_d=='23' or m_b_d=='23.01' or m_b_d=='24'))))) or (a=='O' and m_b_d in ['60','120','180','300','600']):
                                                        if (a=='P' and m_b_d not in p_k) or (a=='O' and m_b_d not in o_k):
                                                            p_k.append(m_b_d) if a=='P' else o_k.append(m_b_d)
                                            tmp = np.array(tmp)
                                            if a=='P' and int(c)==0 and m_b_d in p_k:
                                                if len(tmp)>0 and ((a_s=='bigA' and ((n_a=='25' and (m_b_d=='11' or m_b_d=='15' or m_b_d=='17' or m_b_d=='19' or m_b_d=='21')) or
                                                                        (n_a=='100' and (m_b_d=='41' or m_b_d=='56' or m_b_d=='65' or m_b_d=='74' or m_b_d=='83')))) or
                                                                        (a_s=='smallA' and (n_a=='25' and (m_b_d=='19' or m_b_d=='22' or m_b_d=='23' or m_b_d=='23.01' or m_b_d=='24')))):
                                                    dict_park.update({(a_s,n_a,m_b_d,m_t,gt):tmp})
                                            if a=='O' and m_b_d in o_k:
                                                if len(tmp)>0:
                                                    if int(c)==0:
                                                        dict_adms.update({(a_s,n_a,m_b_d,m_t,gt):tmp})
                                                    else:
                                                        dict_our.update({(a_s,n_a,m_b_d,m_t,gt):tmp})
        # self.print_lines_recovery(path,[dict_park,dict_adms,dict_our],'avg_recovery_lines',[ground_T,threshlds],[buf_dim,jolly],[arena,agents])
        self.print_box_recovery_by_gt(path,[dict_park,dict_adms,dict_our],'recovery_box_gt',[ground_T,threshlds],[buf_dim,jolly],[arena,agents])
        
##########################################################################################################
    def print_box_recovery_by_gt(self,save_path,data,filename,gt_thr,buf_dims,aa):
        plt.rcParams.update({"font.size":40})
        cm              = plt.get_cmap('viridis') 
        typo            = [0,1,2,3,4,5,6,7]
        cNorm           = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap       = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        anonymous       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        handles_r       = [anonymous,id_broad,id_rebroad]
        colors_box      = [scalarMap.to_rgba(typo[0]),scalarMap.to_rgba(typo[3]),scalarMap.to_rgba(typo[6])]
        dict_park, dict_adms, dict_our = data[0], data[1], data[2]
        park_plotting = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        adam_plotting = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        ours_plotting = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        for m_t in range(len(buf_dims[1])):
            for gt in range(len(gt_thr[0])):
                for a_s in aa[0]:
                    row,col = 0,0
                    for n_a in aa[1]:
                        if a_s == "smallA":
                            row = 1
                        else:
                            if n_a == "25":
                                row = 0
                            else:
                                row = 2
                        for m_b_d in buf_dims[0]:
                            park_data  = np.array(dict_park.get((a_s,n_a,m_b_d,buf_dims[1][m_t],gt_thr[0][gt])))
                            adams_data = np.array(dict_adms.get((a_s,n_a,m_b_d,buf_dims[1][m_t],gt_thr[0][gt])))
                            our_data   = np.array(dict_our.get((a_s,n_a,m_b_d,buf_dims[1][m_t],gt_thr[0][gt])))
                            if m_b_d == '60':
                                col = 0
                            elif m_b_d == '120':
                                col = 1
                            elif m_b_d == '180':
                                col = 2
                            elif m_b_d == '300':
                                col = 3
                            elif m_b_d == '600':
                                col = 4
                            else:
                                if a_s=='bigA' and n_a=='25':
                                    if m_b_d == '11':
                                        col = 0
                                    elif m_b_d == '15':
                                        col = 1
                                    elif m_b_d == '17':
                                        col = 2
                                    elif m_b_d == '19':
                                        col = 3
                                    elif m_b_d == '21':
                                        col = 4
                                elif a_s=='bigA' and n_a=='100':
                                    if m_b_d == '41':
                                        col = 0
                                    elif m_b_d == '56':
                                        col = 1
                                    elif m_b_d == '65':
                                        col = 2
                                    elif m_b_d == '74':
                                        col = 3
                                    elif m_b_d == '83':
                                        col = 4
                                elif a_s=='smallA':
                                    if m_b_d == '19':
                                        col = 0
                                    elif m_b_d == '22':
                                        col = 1
                                    elif m_b_d == '23':
                                        col = 2
                                    elif m_b_d == '23.01':
                                        col = 3
                                    elif m_b_d == '24':
                                        col = 4
                            if park_data.any() != None:
                                for i in range(len(park_data)):
                                    park_plotting[row][col][gt][i*(m_t+1)] =  park_data[i]
                            if adams_data.any() != None:
                                for i in range(len(adams_data)):
                                    adam_plotting[row][col][gt][i*(m_t+1)] =  adams_data[i]
                            if our_data.any() != None:
                                for i in range(len(our_data)):
                                    ours_plotting[row][col][gt][i*(m_t+1)] =  our_data[i]
        fig, ax = plt.subplots(nrows=3, ncols=5,figsize=(88,76))
        positions = range(1,len(gt_thr[0])*4,4)
        for i in range(3):
            for j in range(5):
                park = park_plotting[i][j]
                park_print = [[-1]]*len(gt_thr[0])
                for k in range(len(park)):
                    flag = []
                    for z in range(len(park[k])):
                        if park[k][z]!=-1:
                            flag.append(park[k][z])
                    park_print[k] = flag                    
                adam = adam_plotting[i][j]
                adam_print = [[-1]]*len(gt_thr[0])
                for k in range(len(adam)):
                    flag = []
                    for z in range(len(adam[k])):
                        if adam[k][z]!=-1:
                            flag.append(adam[k][z])
                    adam_print[k] = flag

                ours = ours_plotting[i][j]
                ours_print = [[-1]]*len(gt_thr[0])
                for k in range(len(ours)):
                    flag = []
                    for z in range(len(ours[k])):
                        if ours[k][z]!=-1:
                            flag.append(ours[k][z])
                    ours_print[k] = flag
                bpp = ax[i][j].boxplot(park_print,positions=positions,widths=0.5,patch_artist=True)
                bpa = ax[i][j].boxplot(adam_print,positions=[p+1 for p in positions],widths=0.5,patch_artist=True)
                bpo = ax[i][j].boxplot(ours_print,positions=[p+2 for p in positions],widths=0.5,patch_artist=True)
                for bplot, color in zip((bpp, bpa, bpo), colors_box):
                    for patch in bplot['boxes']:
                        patch.set_facecolor(color)
                ax[i][j].set_xticks([p + 1 for p in positions])
                ax[i][j].set_xticklabels(gt_thr[0])
                ax[i][j].set_ylim(0,901)
        fig.tight_layout()
        fig_path = save_path+filename+".png"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
        return

##########################################################################################################
    def print_lines_recovery(self,save_path,data,filename,gt_thr,buf_dims,aa):
        plt.rcParams.update({"font.size":36})
        cm              = plt.get_cmap('viridis') 
        typo            = [0,1,2,3,4,5,6,7]
        cNorm           = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap       = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        anonymous       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        handles_r   = [anonymous,id_broad,id_rebroad]
        dict_park, dict_adms, dict_our = data[0], data[1], data[2]
        for m_t in buf_dims[1]:
            for gt in range(len(gt_thr[0])):
                save = [False]*3
                fig, ax = plt.subplots(nrows=3, ncols=5,figsize=(28,18))
                col, row = 0, 0
                for a_s in aa[0]:
                    for n_a in aa[1]:
                        if a_s == "smallA":
                            row = 1
                        else:
                            if n_a == "25":
                                row = 0
                            else:
                                row = 2
                        for m_b_d in buf_dims[0]:
                            park_data  = np.array(dict_park.get((a_s,n_a,m_b_d,m_t,gt_thr[0][gt])))
                            adams_data = np.array(dict_adms.get((a_s,n_a,m_b_d,m_t,gt_thr[0][gt])))
                            our_data   = np.array(dict_our.get((a_s,n_a,m_b_d,m_t,gt_thr[0][gt])))
                            if m_b_d == '60':
                                col = 0
                            elif m_b_d == '120':
                                col = 1
                            elif m_b_d == '180':
                                col = 2
                            elif m_b_d == '300':
                                col = 3
                            elif m_b_d == '600':
                                col = 4
                            else:
                                if a_s=='bigA' and n_a=='25':
                                    if m_b_d == '11':
                                        col = 0
                                    elif m_b_d == '15':
                                        col = 1
                                    elif m_b_d == '17':
                                        col = 2
                                    elif m_b_d == '19':
                                        col = 3
                                    elif m_b_d == '21':
                                        col = 4
                                elif a_s=='bigA' and n_a=='100':
                                    if m_b_d == '41':
                                        col = 0
                                    elif m_b_d == '56':
                                        col = 1
                                    elif m_b_d == '65':
                                        col = 2
                                    elif m_b_d == '74':
                                        col = 3
                                    elif m_b_d == '83':
                                        col = 4
                                elif a_s=='smallA':
                                    if m_b_d == '19':
                                        col = 0
                                    elif m_b_d == '22':
                                        col = 1
                                    elif m_b_d == '23':
                                        col = 2
                                    elif m_b_d == '23.01':
                                        col = 3
                                    elif m_b_d == '24':
                                        col = 4
                            if park_data.any() != None:
                                save[0] = True
                                ax[row][col].plot(park_data,color=scalarMap.to_rgba(typo[0]),lw=6)
                            if adams_data.any() != None:
                                save[1] = True
                                ax[row][col].plot(adams_data,color=scalarMap.to_rgba(typo[3]),lw=6)
                            if our_data.any() != None:
                                save[2] = True
                                ax[row][col].plot(our_data,color=scalarMap.to_rgba(typo[6]),lw=6)
                fig.tight_layout()
                fig_path = save_path+filename+"_G#"+str(gt_thr[0][gt])+"_bufrng#"+str(m_t)+".png"
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3, loc='upper right',framealpha=0.7,borderaxespad=0)
                if np.array(save).any() != False: fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)        
        return

##########################################################################################################
    def plot_active(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_avg,dict_adms_avg,dict_our_avg    = {},{},{}
        dict_park_tmed,dict_adms_tmed,dict_our_tmed = {},{},{}
        ground_T, threshlds , jolly                 = [],[],[]
        algo,arena,runs,time,comm,agents,buf_dim    = [],[],[],[],[],[],[]
        p_k,o_k                                     = [],[]
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
            a='P' if (i==2 or i==3) else 'O'
            for a_s in arena:
                for n_r in runs:
                    for et in time:
                        for c in comm:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for m_t in jolly:
                                        vals            = []
                                        times_median    = []
                                        for gt in ground_T:
                                            tmp         = []
                                            tmp_tmed    = []
                                            for thr in threshlds:
                                                s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t))
                                                t_data = times[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t))
                                                if s_data != None:
                                                    if ((i==2 or i==3) and m_t not in p_k) or ((i==0 or i==1) and m_t not in o_k):
                                                        p_k.append(m_t) if (i==2 or i==3) else o_k.append(m_t)
                                                    tmp.append(round(self.extract_median(s_data[0],len(s_data[0])),2))
                                                    tmp_tmed.append(round(self.extract_median(t_data[0],len(s_data[0])),2))
                                            if len(vals)==0:
                                                vals            = np.array([tmp])
                                                times_median    = np.array([tmp_tmed])
                                            else:
                                                vals            = np.append(vals,[tmp],axis=0)
                                                times_median    = np.append(times_median,[tmp_tmed],axis=0)
                                        if a=='P' and int(c)==0 and m_t in p_k:
                                            if len(vals[0])>0 and ((a_s=='bigA' and ((n_a=='25' and (m_t=='11' or m_t=='15' or m_t=='17' or m_t=='19' or m_t=='21')) or (n_a=='100' and (m_t=='41' or m_t=='56' or m_t=='65' or m_t=='74' or m_t=='83')))) or (a_s=='smallA' and (n_a=='25' and (m_t=='19' or m_t=='22' or m_t=='23' or m_t=='23.01' or m_t=='24')))):
                                                dict_park_avg.update({(a_s,n_a,m_t):vals})
                                                dict_park_tmed.update({(a_s,n_a,m_t):times_median})
                                        if a=='O' and m_t in o_k:
                                            if len(vals[0])>0:
                                                if int(c)==0:
                                                    dict_adms_avg.update({(a_s,n_a,m_t):vals})
                                                    dict_adms_tmed.update({(a_s,n_a,m_t):times_median})
                                                else:
                                                    dict_our_avg.update({(a_s,n_a,m_t):vals})
                                                    dict_our_tmed.update({(a_s,n_a,m_t):times_median})
        self.print_borders(path,'avg','median',ground_T,threshlds,[dict_park_avg,dict_adms_avg,dict_our_avg],[dict_park_tmed,dict_adms_tmed,dict_our_tmed],[p_k,o_k],[arena,agents])
        
##########################################################################################################
    def print_messages(self,data_in):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5,6,7]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        anonymous         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        
        handles_r   = [anonymous,id_broad,id_rebroad]
        fig, ax     = plt.subplots(nrows=3, ncols=5,figsize=(28,18))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in dict_adam.keys():
            tmp =[]
            res = dict_adam.get(k)
            norm = int(k[1])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam.update({k:tmp})
        for k in dict_park.keys():
            tmp =[]
            res = dict_park.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_park.update({k:tmp})
        for k in dict_our.keys():
            tmp =[]
            res = dict_our.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_our.update({k:tmp})
        for k in dict_park.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
                if k[2] == '11':
                    col = 0
                elif k[2] == '15':
                    col = 1
                elif k[2] == '17':
                    col = 2
                elif k[2] == '19':
                    col = 3
                elif k[2] == '21':
                    col = 4
            elif k[0]=='big' and k[1]=='100':
                row = 2
                if k[2] == '41':
                    col = 0
                elif k[2] == '56':
                    col = 1
                elif k[2] == '65':
                    col = 2
                elif k[2] == '74':
                    col = 3
                elif k[2] == '83':
                    col = 4
            elif k[0]=='small':
                row = 1
                if k[2] == '19':
                    col = 0
                elif k[2] == '22':
                    col = 1
                elif k[2] == '23':
                    col = 2
                elif k[2] == '23.01':
                    col = 3
                elif k[2] == '24':
                    col = 4
            ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6)
        for k in dict_adam.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '180':
                    col = 2
                elif k[2] == '300':
                    col = 3
                elif k[2] == '600':
                    col = 4
            elif k[0]=='big' and k[1]=='100':
                row = 2
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '180':
                    col = 2
                elif k[2] == '300':
                    col = 3
                elif k[2] == '600':
                    col = 4
            elif k[0]=='small':
                row = 1
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '180':
                    col = 2
                elif k[2] == '300':
                    col = 3
                elif k[2] == '600':
                    col = 4
            ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[3]),lw=6)
        for k in dict_our.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '180':
                    col = 2
                elif k[2] == '300':
                    col = 3
                elif k[2] == '600':
                    col = 4
            elif k[0]=='big' and k[1]=='100':
                row = 2
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '180':
                    col = 2
                elif k[2] == '300':
                    col = 3
                elif k[2] == '600':
                    col = 4
            elif k[0]=='small':
                row = 1
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '180':
                    col = 2
                elif k[2] == '300':
                    col = 3
                elif k[2] == '600':
                    col = 4
            ax[row][col].plot(dict_our.get(k),color=scalarMap.to_rgba(typo[6]),lw=6)
        for x in range(2):
            for y in range(5):
                ax[x][y].set_xticks(np.arange(0,901,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,5):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(5):
            ax[2][y].set_xticks(np.arange(0,901,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        axt0=ax[0][0].twiny()
        axt1=ax[0][1].twiny()
        axt2=ax[0][2].twiny()
        axt3=ax[0][3].twiny()
        axt4=ax[0][4].twiny()
        labels = [item.get_text() for item in axt0.get_xticklabels()]
        empty_string_labels = ['']*len(labels)
        axt0.set_xticklabels(empty_string_labels)
        axt1.set_xticklabels(empty_string_labels)
        axt2.set_xticklabels(empty_string_labels)
        axt3.set_xticklabels(empty_string_labels)
        axt4.set_xticklabels(empty_string_labels)
        axt0.set_xlabel(r"$T_m = 60\, s$")
        axt1.set_xlabel(r"$T_m = 120\, s$")
        axt2.set_xlabel(r"$T_m = 180\, s$")
        axt3.set_xlabel(r"$T_m = 300\, s$")
        axt4.set_xlabel(r"$T_m = 600\, s$")
        ayt0=ax[0][4].twinx()
        ayt1=ax[1][4].twinx()
        ayt2=ax[2][4].twinx()
        labels = [item.get_text() for item in axt0.get_yticklabels()]
        empty_string_labels = ['']*len(labels)
        ayt0.set_yticklabels(empty_string_labels)
        ayt1.set_yticklabels(empty_string_labels)
        ayt2.set_yticklabels(empty_string_labels)
        ayt0.set_ylabel("LD25")
        ayt1.set_ylabel("HD25")
        ayt2.set_ylabel("HD100")
        ax[0][0].set_ylabel(r"$M$")
        ax[1][0].set_ylabel(r"$M$")
        ax[2][0].set_ylabel(r"$M$")
        ax[2][0].set_xlabel(r"$T\, (s)$")
        ax[2][1].set_xlabel(r"$T\, (s)$")
        ax[2][2].set_xlabel(r"$T\, (s)$")
        ax[2][3].set_xlabel(r"$T\, (s)$")
        ax[2][4].set_xlabel(r"$T\, (s)$")
        for x in range(3):
            for y in range(5):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,900)
                if x==0 or x==1:
                    ax[x][y].set_ylim(0,1)
                else:
                    ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/messages.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
##########################################################################################################
    def print_borders(self,path,_type,t_type,ground_T,threshlds,data_in,times_in,keys,more_k):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5,6,7]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        tdict_park,tdict_adam,tdict_our = times_in[0], times_in[1], times_in[2]
        p_k, po_k = keys[0],keys[1]
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = np.sort(o_k)
        arena = more_k[0]
        vals8p = [[0]*len(threshlds)]*len(o_k)
        vals2p = [[0]*len(threshlds)]*len(o_k)
        vals8a = [[0]*len(threshlds)]*len(o_k)
        vals2a = [[0]*len(threshlds)]*len(o_k)
        vals8o = [[0]*len(threshlds)]*len(o_k)
        vals2o = [[0]*len(threshlds)]*len(o_k)

        tvalsp = [[0]*len(threshlds)]*len(o_k)
        tvalsa = [[0]*len(threshlds)]*len(o_k)
        tvalso = [[0]*len(threshlds)]*len(o_k)

        low_bound   = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label=r"$\hat{Q} = 0.2$")
        high_bound  = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label=r"$\hat{Q} = 0.8$")
        anonymous   = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad    = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')

        handles_c   = [high_bound,low_bound]
        handles_r   = [anonymous,id_broad,id_rebroad]
        fig, ax     = plt.subplots(nrows=3, ncols=5,figsize=(40,22))
        tfig, tax   = plt.subplots(nrows=3, ncols=5,figsize=(28,18))
        str_threshlds = []
        void_str_threshlds = []
        svoid_str_threshlds = []
        str_threshlds_y = []
        void_str_threshlds_y = []
        svoid_str_threshlds_y = []
        void_str_gt = []
        void_str_tim = []
        for a in arena:
            if a=="smallA":
                agents = ["25"]
            else:
                agents = more_k[1]
            for ag in agents:
                row = 1  if a=="smallA" else 0
                p_k = [str(11),str(15),str(17),str(19),str(21)]
                if row ==1: p_k = [str(19),str(22),str(23),str(23.01),str(24)]
                if int(ag)==100:
                    p_k = [str(41),str(56),str(65),str(74),str(83)]
                    row = 2
                for k in range(len(o_k)):
                    for th in range(len(threshlds)):
                        p_vals2,a_vals2,o_vals2 = [np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_vals8,a_vals8,o_vals8 = [np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt2,a_gt2,o_gt2       = [np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt8,a_gt8,o_gt8       = [np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_valst,a_valst,o_valst = np.nan,np.nan,np.nan
                        for pt in range(len(ground_T)):
                            pval    = dict_park.get((a,ag,p_k[k]))[pt][th]
                            aval    = dict_adam.get((a,ag,str(o_k[k])))[pt][th]
                            oval    = dict_our.get((a,ag,str(o_k[k])))[pt][th]
                            tpval   = tdict_park.get((a,ag,p_k[k]))[pt][th]
                            taval   = tdict_adam.get((a,ag,str(o_k[k])))[pt][th]
                            toval   = tdict_our.get((a,ag,str(o_k[k])))[pt][th]
                            if pval>=0.8:
                                if ground_T[pt]-threshlds[th] >=0.1 and ground_T[pt]-threshlds[th] <=0.2 and p_valst is np.nan:
                                    p_valst = np.log10(tpval)
                                if p_vals8[1] is np.nan or pval<p_vals8[1]:
                                    p_vals8[1]  = pval
                                    p_gt8[1]    = ground_T[pt]
                            elif pval<=0.2:
                                if p_vals2[0] is np.nan or pval>=p_vals2[0]:
                                    p_vals2[0]  = pval
                                    p_gt2[0]    = ground_T[pt]
                            else:
                                if p_vals8[0] is np.nan or pval>p_vals8[0]:
                                    p_vals8[0]  = pval
                                    p_gt8[0]    = ground_T[pt]
                                if p_vals2[1] is np.nan or pval<p_vals2[1]:
                                    p_vals2[1]  = pval
                                    p_gt2[1]    = ground_T[pt]
                            if oval>=0.8:
                                if ground_T[pt]-threshlds[th] >=0.1 and ground_T[pt]-threshlds[th] <=0.2 and o_valst is np.nan:
                                    o_valst = np.log10(toval)
                                if o_vals8[1] is np.nan or oval<o_vals8[1]:
                                    o_vals8[1]  = oval
                                    o_gt8[1]    = ground_T[pt]
                            elif oval<=0.2:
                                if o_vals2[0] is np.nan or oval>=o_vals2[0]:
                                    o_vals2[0]  = oval
                                    o_gt2[0]    = ground_T[pt]
                            else:
                                if o_vals8[0] is np.nan or oval>o_vals8[0]:
                                    o_vals8[0]  = oval
                                    o_gt8[0]    = ground_T[pt]
                                if o_vals2[1] is np.nan or oval<o_vals2[1]:
                                    o_vals2[1]  = oval
                                    o_gt2[1]    = ground_T[pt]
                            if aval>=0.8:
                                if ground_T[pt]-threshlds[th] >=0.1 and ground_T[pt]-threshlds[th] <=0.2 and a_valst is np.nan:
                                    a_valst = np.log10(taval)
                                if a_vals8[1] is np.nan or aval<a_vals8[1]:
                                    a_vals8[1]  = aval
                                    a_gt8[1]    = ground_T[pt]
                            elif aval<=0.2:
                                if a_vals2[0] is np.nan or aval>=a_vals2[0]:
                                    a_vals2[0]  = aval
                                    a_gt2[0]    = ground_T[pt]
                            else:
                                if a_vals8[0] is np.nan or aval>a_vals8[0]:
                                    a_vals8[0]  = aval
                                    a_gt8[0]    = ground_T[pt]
                                if a_vals2[1] is np.nan or aval<a_vals2[1]:
                                    a_vals2[1]  = aval
                                    a_gt2[1]    = ground_T[pt]
                        if p_vals8[0] is np.nan:
                            p_vals8[0] = p_vals8[1]
                            p_gt8[0] = p_gt8[1]
                        elif p_vals8[1] is np.nan:
                            p_vals8[1] = p_vals8[0]
                            p_gt8[1] = p_gt8[0]
                        if p_vals2[0] is np.nan:
                            p_vals2[0] = p_vals2[1]
                            p_gt2[0] = p_gt2[1]
                        elif p_vals2[1] is np.nan:
                            p_vals2[1] = p_vals2[0]
                            p_gt2[1] = p_gt2[0]
                        if o_vals8[0] is np.nan:
                            o_vals8[0] = o_vals8[1]
                            o_gt8[0] = o_gt8[1]
                        elif o_vals8[1] is np.nan:
                            o_vals8[1] = o_vals8[0]
                            o_gt8[1] = o_gt8[0]
                        if o_vals2[0] is np.nan:
                            o_vals2[0] = o_vals2[1]
                            o_gt2[0] = o_gt2[1]
                        elif o_vals2[1] is np.nan:
                            o_vals2[1] = o_vals2[0]
                            o_gt2[1] = o_gt2[0]
                        if a_vals8[0] is np.nan:
                            a_vals8[0] = a_vals8[1]
                            a_gt8[0] = a_gt8[1]
                        elif a_vals8[1] is np.nan:
                            a_vals8[1] = a_vals8[0]
                            a_gt8[1] = a_gt8[0]
                        if a_vals2[0] is np.nan:
                            a_vals2[0] = a_vals2[1]
                            a_gt2[0] = a_gt2[1]
                        elif a_vals2[1] is np.nan:
                            a_vals2[1] = a_vals2[0]
                            a_gt2[1] = a_gt2[0]
                        vals2p[k][th] = np.round(np.interp([0.2],p_vals2,p_gt2,left=np.nan)[0],3)
                        vals2a[k][th] = np.round(np.interp([0.2],a_vals2,a_gt2,left=np.nan)[0],3)
                        vals2o[k][th] = np.round(np.interp([0.2],o_vals2,o_gt2,left=np.nan)[0],3)
                        vals8p[k][th] = np.round(np.interp([0.8],p_vals8,p_gt8,right=np.nan)[0],3)
                        vals8a[k][th] = np.round(np.interp([0.8],a_vals8,a_gt8,right=np.nan)[0],3) 
                        vals8o[k][th] = np.round(np.interp([0.8],o_vals8,o_gt8,right=np.nan)[0],3)
                        tvalsp[k][th] = p_valst
                        tvalsa[k][th] = a_valst
                        tvalso[k][th] = o_valst
                    ax[row][k].plot(vals2p[k],color=scalarMap.to_rgba(typo[0]),lw=6,ls='--')
                    ax[row][k].plot(vals8p[k],color=scalarMap.to_rgba(typo[0]),lw=6,ls='-')
                    ax[row][k].plot(vals2a[k],color=scalarMap.to_rgba(typo[3]),lw=6,ls='--')
                    ax[row][k].plot(vals8a[k],color=scalarMap.to_rgba(typo[3]),lw=6,ls='-')
                    ax[row][k].plot(vals2o[k],color=scalarMap.to_rgba(typo[6]),lw=6,ls='--')
                    ax[row][k].plot(vals8o[k],color=scalarMap.to_rgba(typo[6]),lw=6,ls='-')
                    ax[row][k].plot(np.arange(0.5,1.01,0.01),color='black',lw=5,ls=':')
                    tax[row][k].plot(tvalsp[k],color=scalarMap.to_rgba(typo[0]),lw=6)
                    tax[row][k].plot(tvalsa[k],color=scalarMap.to_rgba(typo[3]),lw=6)
                    tax[row][k].plot(tvalso[k],color=scalarMap.to_rgba(typo[6]),lw=6)
                    if len(str_threshlds)==0:
                        for x in threshlds:
                            if np.round(np.round(x,1)-np.round(x%10,2),2) == 0.0:
                                str_threshlds.append(str(x))
                                void_str_threshlds.append('')
                                svoid_str_threshlds.append('')
                            else:
                                void_str_threshlds.append('')
                        for x in threshlds:
                            if x>.9: break
                            if np.round(np.round(x,1)-np.round(x%10,2),2) == 0.0:
                                str_threshlds_y.append(str(x))
                                void_str_threshlds_y.append('')
                                svoid_str_threshlds_y.append('')
                            else:
                                void_str_threshlds_y.append('')
                        for x in range(5,11,1):
                            void_str_gt.append('')
                        for x in range(0,31,5):
                            void_str_tim.append('')
                    ax[row][k].set_xlim(0.5,1)
                    tax[row][k].set_xlim(0.5,0.9)
                    ax[row][k].set_ylim(0.5,1)
                    tax[row][k].set_ylim(0.5,1)
                    if row==0:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,41,10),labels=svoid_str_threshlds_y)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,41,1),labels=void_str_threshlds_y,minor=True)
                        axt = ax[row][k].twiny()
                        taxt = tax[row][k].twiny()
                        labels = [item.get_text() for item in axt.get_xticklabels()]
                        empty_string_labels = ['']*len(labels)
                        axt.set_xticklabels(empty_string_labels)
                        taxt.set_xticklabels(empty_string_labels)
                        if k==0:
                            axt.set_xlabel(r"$T_m = 60\, s$")
                            taxt.set_xlabel(r"$T_m = 60\, s$")
                        elif k==1:
                            axt.set_xlabel(r"$T_m = 120\, s$")
                            taxt.set_xlabel(r"$T_m = 120\, s$")
                        elif k==2:
                            axt.set_xlabel(r"$T_m = 180\, s$")
                            taxt.set_xlabel(r"$T_m = 180\, s$")
                        elif k==3:
                            axt.set_xlabel(r"$T_m = 300\, s$")
                            taxt.set_xlabel(r"$T_m = 300\, s$")
                        elif k==4:
                            axt.set_xlabel(r"$T_m = 600\, s$")
                            taxt.set_xlabel(r"$T_m = 600\, s$")
                    elif row==2:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,41,10),labels=str_threshlds_y)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,41,1),labels=void_str_threshlds_y,minor=True)
                        if k==0:
                            ax[row][k].set_xlabel(r"$\tau$")
                            tax[row][k].set_xlabel(r"$\tau$")
                        elif k==1:
                            ax[row][k].set_xlabel(r"$\tau$")
                            tax[row][k].set_xlabel(r"$\tau$")
                        elif k==2:
                            ax[row][k].set_xlabel(r"$\tau$")
                            tax[row][k].set_xlabel(r"$\tau$")
                        elif k==3:
                            ax[row][k].set_xlabel(r"$\tau$")
                            tax[row][k].set_xlabel(r"$\tau$")
                        elif k==4:
                            ax[row][k].set_xlabel(r"$\tau$")
                            tax[row][k].set_xlabel(r"$\tau$")
                    else:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,41,10),labels=svoid_str_threshlds_y)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,41,1),labels=void_str_threshlds_y,minor=True)
                    if k==0:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1))
                        tax[row][k].set_yticks(np.arange(0,3.1,.5))
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_yticks(np.arange(0,3.1,.1),labels=['' for x in range(0,31,1)],minor=True)
                        if row==0:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$log_{10}(T_c)\, (s)$")
                        elif row==1:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$log_{10}(T_c)\, (s)$")
                        elif row==2:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$log_{10}(T_c)\, (s)$")
                    elif k==4:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
                        tax[row][k].set_yticks(np.arange(0,3.1,.5),labels=void_str_tim)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_yticks(np.arange(0,3.1,.1),labels=['' for x in range(0,31,1)],minor=True)
                        axt = ax[row][k].twinx()
                        taxt = tax[row][k].twinx()
                        labels = [item.get_text() for item in axt.get_yticklabels()]
                        empty_string_labels = ['']*len(labels)
                        axt.set_yticklabels(empty_string_labels)
                        taxt.set_yticklabels(empty_string_labels)
                        if row==0:
                            axt.set_ylabel("LD25")
                            taxt.set_ylabel("LD25")
                        elif row==1:
                            axt.set_ylabel("HD25")
                            taxt.set_ylabel("HD25")
                        elif row==2:
                            axt.set_ylabel("HD100")
                            taxt.set_ylabel("HD100")
                    else:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
                        tax[row][k].set_yticks(np.arange(0,3.1,.5),labels=void_str_tim)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_yticks(np.arange(0,3.1,.1),labels=['' for x in range(0,31,1)],minor=True)
                    ax[row][k].grid(which='major')
                    tax[row][k].grid(which='major')

        fig.tight_layout()
        tfig.tight_layout()
        fig_path = path+_type+"_activation.pdf"
        tfig_path = path+t_type+"_time.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_c,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        tfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3,loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        tfig.savefig(tfig_path, bbox_inches='tight')
        plt.close(fig)
        plt.close(tfig)

##########################################################################################################
    def extract_median(self,array,max_time):
        mt = int(max_time)
        median = max_time
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0:
            if sortd_arr[(len(sortd_arr)//2)]!=mt: median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            if sortd_arr[math.ceil(len(sortd_arr)/2)]!=mt: median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median