import numpy as np
import os, csv, math
import seaborn as sns
import matplotlib as mpl
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
            if elem == "proc_data":
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
    def plot_active(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/c_images/"):
            os.mkdir(self.base+"/proc_data/c_images/")
        path = self.base+"/proc_data/c_images/"
        dict_park_avg,dict_adms_avg,dict_our_avg    = {},{},{}
        dict_park_max,dict_adms_max,dict_our_max    = {},{},{}
        dict_park_fin,dict_adms_fin,dict_our_fin    = {},{},{}
        dict_park_tmin,dict_adms_tmin,dict_our_tmin = {},{},{}
        dict_park_tmax,dict_adms_tmax,dict_our_tmax = {},{},{}
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
                                        vals_m          = []
                                        vals_r          = []
                                        times_min       = []
                                        times_max       = []
                                        times_median    = []
                                        for gt in ground_T:
                                            tmp         = []
                                            t_max       = []
                                            reg         = []
                                            tmp_tmin    = []
                                            tmp_tmax    = []
                                            tmp_tmed    = []
                                            for thr in threshlds:
                                                s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t))
                                                t_data = times[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t))
                                                if s_data != None:
                                                    if ((i==2 or i==3) and m_t not in p_k) or ((i==0 or i==1) and m_t not in o_k):
                                                        p_k.append(m_t) if (i==2 or i==3) else o_k.append(m_t)
                                                    tmp.append(np.round(float(s_data[2])/int(n_a),2))
                                                    t_max.append(np.round(np.max(s_data[0]),2))
                                                    reg.append(np.round(np.median(s_data[0][-30:]),2))
                                                    tmp_tmin.append(np.round(np.min(t_data[0]),2))
                                                    tmp_tmax.append(np.round(np.max(t_data[0]),2))
                                                    tmp_tmed.append(np.round(np.median(t_data[0][:]),2))
                                            if len(vals)==0:
                                                vals            = np.array([tmp])
                                                vals_m          = np.array([t_max])
                                                vals_r          = np.array([reg])
                                                times_min       = np.array([tmp_tmin])
                                                times_max       = np.array([tmp_tmax])
                                                times_median    = np.array([tmp_tmed])
                                            else:
                                                vals            = np.append(vals,[tmp],axis=0)
                                                vals_m          = np.append(vals_m,[t_max],axis=0)
                                                vals_r          = np.append(vals_r,[reg],axis=0)
                                                times_min       = np.append(times_min,[tmp_tmin],axis=0)
                                                times_max       = np.append(times_max,[tmp_tmax],axis=0)
                                                times_median    = np.append(times_median,[tmp_tmed],axis=0)
                                        if a=='P' and int(c)==0 and m_t in p_k:
                                            if len(vals[0])>0 and ((a_s=='bigA' and ((n_a=='25' and (m_t=='10' or m_t=='13' or m_t=='21' or m_t=='24')) or (n_a=='100' and (m_t=='10' or m_t=='32' or m_t=='78' or m_t=='99')))) or (a_s=='smallA' and (n_a=='25' and (m_t=='10' or m_t=='13' or m_t=='21' or m_t=='24')))):
                                                dict_park_avg.update({(a_s,n_a,m_t):vals})
                                                dict_park_max.update({(a_s,n_a,m_t):vals_m})
                                                dict_park_fin.update({(a_s,n_a,m_t):vals_r})
                                                dict_park_tmin.update({(a_s,n_a,m_t):times_min})
                                                dict_park_tmax.update({(a_s,n_a,m_t):times_max})
                                                dict_park_tmed.update({(a_s,n_a,m_t):times_median})
                                        if a=='O' and m_t in o_k:
                                            if len(vals[0])>0:
                                                if int(c)==0:
                                                    dict_adms_avg.update({(a_s,n_a,m_t):vals})
                                                    dict_adms_max.update({(a_s,n_a,m_t):vals_m})
                                                    dict_adms_fin.update({(a_s,n_a,m_t):vals_r})
                                                    dict_adms_tmin.update({(a_s,n_a,m_t):times_min})
                                                    dict_adms_tmax.update({(a_s,n_a,m_t):times_max})
                                                    dict_adms_tmed.update({(a_s,n_a,m_t):times_median})
                                                else:
                                                    dict_our_avg.update({(a_s,n_a,m_t):vals})
                                                    dict_our_max.update({(a_s,n_a,m_t):vals_m})
                                                    dict_our_fin.update({(a_s,n_a,m_t):vals_r})
                                                    dict_our_tmin.update({(a_s,n_a,m_t):times_min})
                                                    dict_our_tmax.update({(a_s,n_a,m_t):times_max})
                                                    dict_our_tmed.update({(a_s,n_a,m_t):times_median})
        self.print_borders(path,'avg','min',ground_T,threshlds,[dict_park_avg,dict_adms_avg,dict_our_avg],[dict_park_tmin,dict_adms_tmin,dict_our_tmin],[p_k,o_k],[arena,agents])
        self.print_borders(path,'max','max',ground_T,threshlds,[dict_park_max,dict_adms_max,dict_our_max],[dict_park_tmax,dict_adms_tmax,dict_our_tmax],[p_k,o_k],[arena,agents])
        self.print_borders(path,'reg','median',ground_T,threshlds,[dict_park_fin,dict_adms_fin,dict_our_fin],[dict_park_tmed,dict_adms_tmed,dict_our_tmed],[p_k,o_k],[arena,agents])
        
##########################################################################################################
    def print_messages(self,data_in):
        plt.rcParams.update({"font.size":26})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        red         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')

        handles_r   = [red,blue,green]
        fig, ax     = plt.subplots(nrows=3, ncols=4,figsize=(28,20))
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
            sign = []
            if k[0]=='big' and k[1]=='25':
                row = 0
                if k[2] == '10':
                    col = 0
                elif k[2] == '13':
                    col = 1
                elif k[2] == '21':
                    col = 2
                elif k[2] == '24':
                    col = 3
            elif k[0]=='big' and k[1]=='100':
                row = 2
                if k[2] == '10':
                    col = 0
                elif k[2] == '32':
                    col = 1
                elif k[2] == '78':
                    col = 2
                elif k[2] == '99':
                    col = 3
            elif k[0]=='small':
                row = 1
                if k[2] == '10':
                    col = 0
                elif k[2] == '13':
                    col = 1
                elif k[2] == '21':
                    col = 2
                elif k[2] == '24':
                    col = 3
            for xi in range(0,900):
                sign.append(int(k[2])/int(k[1]))
            ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6)
            # ax[row][col].plot(sign,color="black",lw=6,ls="--")
        for k in dict_adam.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '300':
                    col = 2
                elif k[2] == '600':
                    col = 3
            elif k[0]=='big' and k[1]=='100':
                row = 2
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '300':
                    col = 2
                elif k[2] == '600':
                    col = 3
            elif k[0]=='small':
                row = 1
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '300':
                    col = 2
                elif k[2] == '600':
                    col = 3
            ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[1]),lw=6)
        for k in dict_our.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '300':
                    col = 2
                elif k[2] == '600':
                    col = 3
            elif k[0]=='big' and k[1]=='100':
                row = 2
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '300':
                    col = 2
                elif k[2] == '600':
                    col = 3
            elif k[0]=='small':
                row = 1
                if k[2] == '60':
                    col = 0
                elif k[2] == '120':
                    col = 1
                elif k[2] == '300':
                    col = 2
                elif k[2] == '600':
                    col = 3
            ax[row][col].plot(dict_our.get(k),color=scalarMap.to_rgba(typo[2]),lw=6)
        
        for x in range(2):
            for y in range(4):
                labels = [item.get_text() for item in ax[x][y].get_xticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_xticklabels(empty_string_labels)
        for x in range(3):
            for y in range(1,4):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        axt0=ax[0][0].twiny()
        axt1=ax[0][1].twiny()
        axt2=ax[0][2].twiny()
        axt3=ax[0][3].twiny()
        labels = [item.get_text() for item in axt0.get_xticklabels()]
        empty_string_labels = ['']*len(labels)
        axt0.set_xticklabels(empty_string_labels)
        axt1.set_xticklabels(empty_string_labels)
        axt2.set_xticklabels(empty_string_labels)
        axt3.set_xticklabels(empty_string_labels)
        axt0.set_xlabel(r"$T_m = 60\, s$")
        axt1.set_xlabel(r"$T_m = 120\, s$")
        axt2.set_xlabel(r"$T_m = 300\, s$")
        axt3.set_xlabel(r"$T_m = 600\, s$")
        ayt0=ax[0][3].twinx()
        ayt1=ax[1][3].twinx()
        ayt2=ax[2][3].twinx()
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
        for x in range(3):
            for y in range(4):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,900)
                if x==0 or x==1:
                    ax[x][y].set_ylim(0,1)
                else:
                    ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/c_images/"):
            os.mkdir(self.base+"/msgs_data/c_images/")
        fig_path = self.base+"/msgs_data/c_images/messages.png"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
##########################################################################################################
    def print_borders(self,path,_type,t_type,ground_T,threshlds,data_in,times_in,keys,more_k):
        plt.rcParams.update({"font.size":26})
        cm = plt.get_cmap('viridis') 
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        tdict_park,tdict_adam,tdict_our = times_in[0], times_in[1], times_in[2]
        p_k, o_k = keys[0],keys[1]
        arena = more_k[0]
        typo = [0,1,2,3]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        vals8p = [[0]*len(threshlds)]*len(o_k)
        vals2p = [[0]*len(threshlds)]*len(o_k)
        vals8a = [[0]*len(threshlds)]*len(o_k)
        vals2a = [[0]*len(threshlds)]*len(o_k)
        vals8o = [[0]*len(threshlds)]*len(o_k)
        vals2o = [[0]*len(threshlds)]*len(o_k)

        tvalsp = [[0]*len(threshlds)]*len(o_k)
        tvalsa = [[0]*len(threshlds)]*len(o_k)
        tvalso = [[0]*len(threshlds)]*len(o_k)

        dots        = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label='P = 0.2')
        triangles   = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label='P = 0.8')
        red         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        void        = mlines.Line2D([], [], linestyle='None')

        handles_c   = [triangles,dots]
        handles_r   = [red,blue,green]
        fig, ax     = plt.subplots(nrows=3, ncols=4,figsize=(28,20))
        tfig, tax   = plt.subplots(nrows=3, ncols=4,figsize=(28,20))
        str_threshlds = []
        void_str_threshlds = []
        svoid_str_threshlds = []
        void_str_gt = []
        void_str_tim = []
        for a in arena:
            if a=="smallA":
                agents = ["25"]
            else:
                agents = more_k[1]
            for ag in agents:
                row = 1  if a=="smallA" else 0
                p_k = [str(10),str(13),str(21),str(24)]
                if int(ag)==100:
                    p_k = [str(10),str(32),str(78),str(99)]
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
                            aval    = dict_adam.get((a,ag,o_k[k]))[pt][th]
                            oval    = dict_our.get((a,ag,o_k[k]))[pt][th]
                            tpval   = tdict_park.get((a,ag,p_k[k]))[pt][th]
                            taval   = tdict_adam.get((a,ag,o_k[k]))[pt][th]
                            toval   = tdict_our.get((a,ag,o_k[k]))[pt][th]
                            if pval>=0.8:
                                if p_vals8[1] is np.nan or pval<p_vals8[1]:
                                    p_valst     = tpval
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
                                if o_vals8[1] is np.nan or oval<o_vals8[1]:
                                    o_valst     = toval
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
                                if a_vals8[1] is np.nan or aval<a_vals8[1]:
                                    a_valst     = taval
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
                    ax[row][k].plot(vals2a[k],color=scalarMap.to_rgba(typo[1]),lw=6,ls='--')
                    ax[row][k].plot(vals8a[k],color=scalarMap.to_rgba(typo[1]),lw=6,ls='-')
                    ax[row][k].plot(vals2o[k],color=scalarMap.to_rgba(typo[2]),lw=6,ls='--')
                    ax[row][k].plot(vals8o[k],color=scalarMap.to_rgba(typo[2]),lw=6,ls='-')
                    ax[row][k].plot(np.arange(0.5,1.01,0.01),color='black',lw=5,ls=':')
                    tax[row][k].plot(tvalsp[k],color=scalarMap.to_rgba(typo[0]),lw=6)
                    tax[row][k].plot(tvalsa[k],color=scalarMap.to_rgba(typo[1]),lw=6)
                    tax[row][k].plot(tvalso[k],color=scalarMap.to_rgba(typo[2]),lw=6)
                    if len(str_threshlds)==0:
                        for x in threshlds:
                            if np.round(np.round(x,1)-np.round(x%10,2),2) == 0.0:
                                str_threshlds.append(str(x))
                                void_str_threshlds.append('')
                                svoid_str_threshlds.append('')
                            else:
                                void_str_threshlds.append('')
                        for x in range(5,11,1):
                            void_str_gt.append('')
                        for x in range(0,601,100):
                            void_str_tim.append('')
                    ax[row][k].set_xlim(0.5,1)
                    tax[row][k].set_xlim(0.5,1)
                    ax[row][k].set_ylim(0.5,1)
                    tax[row][k].set_ylim(0.5,1)
                    if row==0:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
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
                            axt.set_xlabel(r"$T_m = 300\, s$")
                            taxt.set_xlabel(r"$T_m = 300\, s$")
                        elif k==3:
                            axt.set_xlabel(r"$T_m = 600\, s$")
                            taxt.set_xlabel(r"$T_m = 600\, s$")
                    elif row==2:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,51,10),labels=str_threshlds)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
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
                    else:
                        ax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        tax[row][k].set_xticks(np.arange(0,51,10),labels=svoid_str_threshlds)
                        ax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_xticks(np.arange(0,51,1),labels=void_str_threshlds,minor=True)
                    if k==0:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1))
                        tax[row][k].set_yticks(np.arange(0,601,100))
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_yticks(np.arange(0,601,25),labels=['' for x in range(0,601,25)],minor=True)
                        if row==0:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$T_c\, (s)$")
                        elif row==1:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$T_c\, (s)$")
                        elif row==2:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$T_c\, (s)$")
                    elif k==3:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
                        tax[row][k].set_yticks(np.arange(0,601,100),labels=void_str_tim)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_yticks(np.arange(0,601,25),labels=['' for x in range(0,601,25)],minor=True)
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
                        tax[row][k].set_yticks(np.arange(0,601,100),labels=void_str_tim)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        tax[row][k].set_yticks(np.arange(0,601,25),labels=['' for x in range(0,601,25)],minor=True)
                    ax[row][k].grid(which='major')
                    tax[row][k].grid(which='major')

        fig.tight_layout()
        tfig.tight_layout()
        fig_path = path+_type+"_activation.png"
        tfig_path = path+t_type+"_time.png"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_c,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        tfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3,loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        tfig.savefig(tfig_path, bbox_inches='tight')
        plt.close(fig)
        plt.close(tfig)

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
                                                            list_t[thr] = np.round(self.extract_median(t_data[0],et),1)
                                                        list_a[thr] = np.round(float(s_data[2])/int(n_a),2) if float(s_data[2])>=0 else 0
                                                        list_m[thr] = np.round(np.max(np.array(s_data[0],dtype=float)),2)
                                                        list_r[thr] = np.round(np.median(np.array(s_data[0][-30:],dtype=float)),2)
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
                                            plt.close()

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
                                            plt.close()

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
                                            plt.close()

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
                                            plt.close()

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
                                                        list_p[m_t] = np.round(float(keys[7][thr])/float(gt),2)
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
                                    plt.close()        
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
                                                        list_t[thr] = np.round(self.extract_median(t_data[0],et),1)
                                                    list_a[thr] = np.round(float(s_data[2])/int(n_a),2) if float(s_data[2])>=0 else 0
                                                    list_m[thr] = np.round(np.max(np.array(s_data[0],dtype=float)),2)
                                                    list_r[thr] = np.round(np.median(np.array(s_data[0][-30:],dtype=float)),2)
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
                                        plt.close()

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
                                        plt.close()

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
                                        plt.close()

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
                                        plt.close()

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
                                                        list_p[m_t] = np.round(float(THR[thr])/float(gt),2)
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
                                    plt.close()
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