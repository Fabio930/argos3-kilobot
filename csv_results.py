import numpy as np
import os, csv, math
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
            if elem == "proc_data" or elem == "msgs_data":
                self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def plot_messages(self,data):
        dict_park, dict_adam, dict_fifo, dict_rnd, dict_rnd_inf, dict_rnd_adpt = {},{},{},{},{},{}
        for k in data.keys():
            if(k[3]=="0.68;0.92"):
                if k[1]=='P':
                    dict_park.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                else:
                    if int(k[4])==0:
                        dict_adam.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                    elif int(k[4])==2:
                        dict_fifo.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                    else:
                        if k[5]=="0":
                            dict_rnd_inf.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                        elif k[5]=="a31":
                            dict_rnd_adpt.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})
                        else:
                            dict_rnd.update({(k[0],k[2],k[3],k[5],k[6],k[7]):data.get(k)})

        self.print_messages([dict_park,dict_adam,dict_fifo, dict_rnd, dict_rnd_inf,dict_rnd_adpt])
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
                                data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5],keys[6],keys[7]):array_val})
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
                    lc = 1
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
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7]),data_val.get(keys[8])):(data_val.get(keys[9]),data_val.get(keys[10]))})
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
                                data.update({(algo,arena,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7]),data_val.get(keys[8])):(data_val.get(keys[9]),data_val.get(keys[10]))})
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
        return data

##########################################################################################################
    def divide_data(self,data):
        states, times, messages_b, messages_r = {},{},{},{}
        do_nothing_buff, insert_buff, update_buf = {},{},{}
        algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops = [],[],[],[],[],[],[],[],[],[],[]
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
                elif i == 10 and k[i] not in msg_hops: msg_hops.append(k[i])
            if k[-1] == "times":
                times.update({k[:-1]:data.get(k)})
            elif k[-1] == "swarm_state":
                states.update({k[:-1]:data.get(k)})
            elif k[-1] == "broadcast_msg":
                messages_b.update({k[:-1]:data.get(k)})
            elif k[-1] == "rebroadcast_msg":
                messages_r.update({k[:-1]:data.get(k)})
            elif k[-1] == "do_nothing_buffer":
                do_nothing_buff.update({k[:-1]:data.get(k)})
            elif k[-1] == "insert_buffer":
                insert_buff.update({k[:-1]:data.get(k)})
            elif k[-1] == "update_buffer":
                update_buf.update({k[:-1]:data.get(k)})
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, min_buff_dim, msg_time,msg_hops), states, times, (messages_b, messages_r), (do_nothing_buff, insert_buff, update_buf)
    

##########################################################################################################
    def plot_buffer_opts(self,no_actions,insertions,updates):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd   = {},{},{}
        dict_rnd_inf_no_act_fr,dict_rnd_inf_ins_fr,dict_rnd_inf_upd_fr   = {},{},{}
        msg_hop, msg_exp                           = [],[]
        algo,arena,runs,time,thresholds,gts,agents,com    = [],[],[],[],[],[],[],[]
        for i in range(len(no_actions)):
            da_K = no_actions[i].keys()
            for k0 in da_K:
                if k0[0]not in algo: algo.append(k0[0])
                if k0[1]not in arena: arena.append(k0[1])
                if k0[2]not in runs: runs.append(k0[2])
                if k0[3]not in time: time.append(k0[3])
                if k0[4]not in thresholds: thresholds.append(k0[4])
                if k0[5]not in gts: gts.append(k0[5])
                if k0[6]not in com: com.append(k0[6])
                if k0[7]not in agents: agents.append(k0[7])
                if k0[9]not in msg_exp: msg_exp.append(k0[9])
                if k0[10]not in msg_hop: msg_hop.append(k0[10])

        for a in algo:
            for a_s in arena:
                for n_r in runs:
                    for et in time:
                        for thr in thresholds:
                            for gt in gts:
                                for i in range(len(no_actions)):
                                    for c in com:
                                        for n_a in agents:
                                            for m_t in msg_exp:
                                                for m_h in msg_hop:
                                                    n_data = no_actions[i].get((a,a_s,n_r,et,thr,gt,c,n_a,'-',m_t,m_h))
                                                    if n_data != None and int(c)==1 and m_h=="0":
                                                        n_data = n_data[0]
                                                        i_data = insertions[i].get((a,a_s,n_r,et,thr,gt,c,n_a,'-',m_t,m_h))[0]
                                                        u_data = updates[i].get((a,a_s,n_r,et,thr,gt,c,n_a,'-',m_t,m_h))[0]
                                                        dict_rnd_inf_no_act.update({(a_s,n_a,m_t):n_data})
                                                        dict_rnd_inf_ins.update({(a_s,n_a,m_t):i_data})
                                                        dict_rnd_inf_upd.update({(a_s,n_a,m_t):u_data})
                                                        n_data_fr,i_data_fr,u_data_fr = [-1]*len(n_data),[-1]*len(n_data),[-1]*len(n_data)
                                                        for j in range(len(n_data)):
                                                            if j==0:
                                                                n_data_fr[j] = n_data[j]
                                                                i_data_fr[j] = i_data[j]
                                                                u_data_fr[j] = u_data[j]
                                                            else:
                                                                n_data_fr[j] = n_data[j] - n_data[j-1]
                                                                i_data_fr[j] = i_data[j] - i_data[j-1]
                                                                u_data_fr[j] = u_data[j] - u_data[j-1]
                                                        dict_rnd_inf_no_act_fr.update({(a_s,n_a,m_t):n_data_fr})
                                                        dict_rnd_inf_ins_fr.update({(a_s,n_a,m_t):i_data_fr})
                                                        dict_rnd_inf_upd_fr.update({(a_s,n_a,m_t):u_data_fr})

                                self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],str(gt)+"_buff_sum_opts_500_150.pdf",500,0,150)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],str(gt)+"_buff_sum_opts_150_150.pdf",150,0,150)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],str(gt)+"_buff_sum_opts_500_740.pdf",500,590,740)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],str(gt)+"_buff_sum_opts_150_740.pdf",150,590,740)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],str(gt)+"_buff_sum_opts_500_1200.pdf",500,0,1200)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],str(gt)+"_buff_sum_opts_150_1200.pdf",150,0,1200)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act_fr,dict_rnd_inf_ins_fr,dict_rnd_inf_upd_fr],str(gt)+"_buff_step_opts_150.pdf",7.5,0,150)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act_fr,dict_rnd_inf_ins_fr,dict_rnd_inf_upd_fr],str(gt)+"_buff_step_opts_740.pdf",7.5,590,740)
                                self.print_buff_opts(path,[dict_rnd_inf_no_act_fr,dict_rnd_inf_ins_fr,dict_rnd_inf_upd_fr],str(gt)+"_buff_step_opts_1200.pdf",7.5,0,1200)
    
        return

##########################################################################################################
    def plot_active_w_gt_thr(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state  = {},{},{},{},{},{}
        dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time        = {},{},{},{},{},{}
        ground_T, threshlds , jolly, msg_hops                                               = [],[],[],[]
        algo,arena,runs,time,comm,agents,buf_dim                                            = [],[],[],[],[],[],[]
        o_k                                                                                 = []
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in arena: arena.append(k0[1])
                if k0[2] not in runs: runs.append(k0[2])
                if k0[3] not in time: time.append(k0[3])
                if k0[4] not in threshlds: threshlds.append(k0[4])
                if k0[5] not in ground_T: ground_T.append(k0[5])
                if k0[6] not in comm: comm.append(k0[6])
                if k0[7] not in agents: agents.append(k0[7])
                if k0[8] not in buf_dim: buf_dim.append(k0[8])
                if k0[9] not in jolly: jolly.append(k0[9])
                if k0[10] not in msg_hops: msg_hops.append(k0[10])
        for i in range(len(data_in)):
            for a in algo:
                for a_s in arena:
                    for n_r in runs:
                        for et in time:
                            for c in comm:
                                for n_a in agents:
                                    for m_b_d in buf_dim:
                                        for m_h in msg_hops:
                                            for m_t in jolly:
                                                for gt in ground_T:
                                                    for thr in threshlds:
                                                        s_data = data_in[i].get((a,a_s,n_r,et,thr,gt,c,n_a,m_b_d,m_t,m_h))
                                                        t_data = times[i].get((a,a_s,n_r,et,thr,gt,c,n_a,m_b_d,m_t,m_h))
                                                        if s_data != None:
                                                            if m_t not in o_k: o_k.append(m_t)
                                                            
                                                            if a=='P' and int(c)==0:
                                                                dict_park_state.update({(a_s,n_a,m_t,gt,thr):s_data[0]})
                                                                dict_park_time.update({(a_s,n_a,m_t,gt,thr):t_data[0]})
                                                            if a=='O':
                                                                if int(c)==0:
                                                                    dict_adms_state.update({(a_s,n_a,m_t,gt,thr):s_data[0]})
                                                                    dict_adms_time.update({(a_s,n_a,m_t,gt,thr):t_data[0]})
                                                                elif int(c)==2:
                                                                    dict_fifo_state.update({(a_s,n_a,m_t,gt,thr):s_data[0]})
                                                                    dict_fifo_time.update({(a_s,n_a,m_t,gt,thr):t_data[0]})
                                                                else:
                                                                    if m_h=="1":
                                                                        dict_rnd_state.update({(a_s,n_a,m_t,gt,thr):s_data[0]})
                                                                        dict_rnd_time.update({(a_s,n_a,m_t,gt,thr):t_data[0]})
                                                                    elif m_h=="a31":
                                                                        dict_rnd_adapt_state.update({(a_s,n_a,m_t,gt,thr):s_data[0]})
                                                                        dict_rnd_adapt_time.update({(a_s,n_a,m_t,gt,thr):t_data[0]})
                                                                    else:
                                                                        dict_rnd_inf_state.update({(a_s,n_a,m_t,gt,thr):s_data[0]})
                                                                        dict_rnd_inf_time.update({(a_s,n_a,m_t,gt,thr):t_data[0]})
        # self.print_evolutions(path,ground_T,threshlds,[dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state],[dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time],o_k,[arena,agents])
        self.print_compare_evolutions(path,ground_T,threshlds,[dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state],[dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time],o_k,[arena,agents])
        # self.print_adaptive_evolutions(path,ground_T,threshlds,[dict_park_state,dict_adms_state,dict_fifo_state,dict_rnd_state,dict_rnd_inf_state,dict_rnd_adapt_state],[dict_park_time,dict_adms_time,dict_fifo_time,dict_rnd_time,dict_rnd_inf_time,dict_rnd_adapt_time],o_k,[arena,agents])

##########################################################################################################
    def print_evolutions(self,path,ground_T,threshlds,data_in,times_in,keys,more_k):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adapt = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        o_k = keys
        for x in range(len(o_k)):
            o_k[x] = int(o_k[x])
        o_k     = np.sort(o_k)
        arena   = more_k[0]
        park    = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$AN_{t}$")
        adam    = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$ID+B$")
        # fifo    = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{f}$')
        rnd     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        rnd_inf = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        handles_r       = [park,adam,rnd,rnd_inf]
        for gt in ground_T:
            for thr in threshlds:
                fig, ax     = plt.subplots(nrows=3, ncols=3,figsize=(36,20))
                for a in arena:
                    if a=="smallA":
                        row = 1
                        agents = ["25"]
                    else:
                        row = 0
                        agents = more_k[1]
                    for ag in agents:
                        if int(ag)==100: row = 2
                        for k in range(len(o_k)):
                            if dict_park.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_park.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[0]),lw=6)
                            if dict_adam.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_adam.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[1]),lw=6)
                            # if dict_fifo.get((a,ag,str(o_k[k]),gt,thr)) != None:
                            #     ax[row][k].plot(dict_fifo.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[2]),lw=6)
                            if dict_rnd.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_rnd.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[3]),lw=6)
                            if dict_rnd_inf.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_rnd_inf.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[4]),lw=6)
                            # if dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)) != None:
                            #     ax[row][k].plot(dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[5]),lw=6)
                            ax[row][k].set_xlim(0,1201)
                            ax[row][k].set_ylim(0,1)
                            if len(real_x_ticks)==0:
                                for x in range(0,1201,50):
                                    if x%300 == 0:
                                        svoid_x_ticks.append('')
                                        void_x_ticks.append('')
                                        real_x_ticks.append(str(int(np.round(x,0))))
                                    else:
                                        void_x_ticks.append('')
                                for y in range(0,11,1):
                                    void_y_ticks.append('')
                            if row == 0:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                axt = ax[row][k].twiny()
                                labels = [item.get_text() for item in axt.get_xticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_xticklabels(empty_string_labels)
                                if k==0:
                                    axt.set_xlabel(r"$T_m = 60\, s$")
                                elif k==1:
                                    axt.set_xlabel(r"$T_m = 300\, s$")
                                elif k==2:
                                    axt.set_xlabel(r"$T_m = 600\, s$")
                            elif row==2:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                elif k==1:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                elif k==2:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                            else:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                            if k==0:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1))
                                if row==0:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif row==1:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif row==2:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                            elif k==2:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                axt = ax[row][k].twinx()
                                labels = [item.get_text() for item in axt.get_yticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_yticklabels(empty_string_labels)
                                if row==0:
                                    axt.set_ylabel("LD25")
                                elif row==1:
                                    axt.set_ylabel("HD25")
                                elif row==2:
                                    axt.set_ylabel("HD100")
                            else:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                            ax[row][k].grid(which='major')
                fig.tight_layout()
                fig_path = path+thr+"_"+gt+"_activation.pdf"
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5,loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_compare_evolutions(self,path,ground_T,threshlds,data_in,times_in,keys,more_k):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adapt = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        o_k = keys
        for x in range(len(o_k)):
            o_k[x] = int(o_k[x])
        o_k     = np.sort(o_k)
        arena   = more_k[0]
        adam    = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$ID+B$")
        rnd     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        rnd_inf = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')
        rnd_adp = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[5]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{a}$')
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        handles_r       = [adam,rnd,rnd_inf,rnd_adp]
        for gt in ground_T:
            for thr in threshlds:
                fig, ax     = plt.subplots(nrows=3, ncols=3,figsize=(36,20))
                for a in arena:
                    if a=="smallA":
                        row = 1
                        agents = ["25"]
                    else:
                        row = 0
                        agents = more_k[1]
                    for ag in agents:
                        if int(ag)==100: row = 2
                        for k in range(len(o_k)):
                            # if dict_park.get((a,ag,str(o_k[k]),gt,thr)) != None:
                            #     ax[row][k].plot(dict_park.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[0]),lw=6)
                            if dict_adam.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_adam.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[1]),lw=6)
                            # if dict_fifo.get((a,ag,str(o_k[k]),gt,thr)) != None:
                            #     ax[row][k].plot(dict_fifo.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[2]),lw=6)
                            if dict_rnd.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_rnd.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[3]),lw=6)
                            if dict_rnd_inf.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_rnd_inf.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[4]),lw=6)
                            if dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                ax[row][k].plot(dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[5]),lw=6)
                            ax[row][k].set_xlim(0,1201)
                            ax[row][k].set_ylim(0,1)
                            if len(real_x_ticks)==0:
                                for x in range(0,1201,50):
                                    if x%300 == 0:
                                        svoid_x_ticks.append('')
                                        void_x_ticks.append('')
                                        real_x_ticks.append(str(int(np.round(x,0))))
                                    else:
                                        void_x_ticks.append('')
                                for y in range(0,11,1):
                                    void_y_ticks.append('')
                            if row == 0:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                axt = ax[row][k].twiny()
                                labels = [item.get_text() for item in axt.get_xticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_xticklabels(empty_string_labels)
                                if k==0:
                                    axt.set_xlabel(r"$T_m = 60\, s$")
                                elif k==1:
                                    axt.set_xlabel(r"$T_m = 300\, s$")
                                elif k==2:
                                    axt.set_xlabel(r"$T_m = 600\, s$")
                            elif row==2:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                elif k==1:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                elif k==2:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                            else:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                            if k==0:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1))
                                if row==0:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif row==1:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif row==2:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                            elif k==2:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                axt = ax[row][k].twinx()
                                labels = [item.get_text() for item in axt.get_yticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_yticklabels(empty_string_labels)
                                if row==0:
                                    axt.set_ylabel("LD25")
                                elif row==1:
                                    axt.set_ylabel("HD25")
                                elif row==2:
                                    axt.set_ylabel("HD100")
                            else:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                            ax[row][k].grid(which='major')
                fig.tight_layout()
                fig_path = path+thr+"_"+gt+"compare_activation.pdf"
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=4,loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_adaptive_evolutions(self,path,ground_T,threshlds,data_in,times_in,keys,more_k):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adapt = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        o_k = keys
        for x in range(len(o_k)):
            o_k[x] = int(o_k[x])
        o_k     = np.sort(o_k)
        arena   = more_k[0]
        rnd     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[5]), marker='None', linestyle='-', linewidth=10, label=r'$\Delta = 0.80$')
        rnd_inf = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[5]), marker='None', linestyle='--', linewidth=10, label=r'$\Delta = 0.52$')
        rnd_adp = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[5]), marker='None', linestyle=':', linewidth=10, label=r'$\Delta = 0.24$')
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        handles_r       = [rnd_adp,rnd_inf,rnd]
        show_grid = np.array([[0]*3]*3)
        for thr in threshlds:
            fig, ax     = plt.subplots(nrows=3, ncols=3,figsize=(36,20))
            for gt in ground_T:
                for a in arena:
                    if a=="smallA":
                        row = 1
                        agents = ["25"]
                    else:
                        row = 0
                        agents = more_k[1]
                    for ag in agents:
                        if int(ag)==100:
                            row = 2
                        for k in range(len(o_k)):
                            if dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)) != None:
                                if gt == "0_92;0_12":
                                    ax[row][k].plot(dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[5]),ls="-",lw=6)
                                elif gt == "0_92;0_40":
                                    ax[row][k].plot(dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[5]),ls="--",lw=6)
                                elif gt == "0_92;0_68":
                                    ax[row][k].plot(dict_rnd_adapt.get((a,ag,str(o_k[k]),gt,thr)),color=scalarMap.to_rgba(typo[5]),ls=":",lw=6)
                            ax[row][k].set_xlim(0,1201)
                            ax[row][k].set_ylim(0,1)
                            if len(real_x_ticks)==0:
                                for x in range(0,1201,50):
                                    if x%300 == 0:
                                        svoid_x_ticks.append('')
                                        void_x_ticks.append('')
                                        real_x_ticks.append(str(int(np.round(x,0))))
                                    else:
                                        void_x_ticks.append('')
                                for y in range(0,11,1):
                                    void_y_ticks.append('')
                            if row == 0:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                axt = ax[row][k].twiny()
                                labels = [item.get_text() for item in axt.get_xticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_xticklabels(empty_string_labels)
                                if k==0:
                                    axt.set_xlabel(r"$T_m = 60\, s$")
                                elif k==1:
                                    axt.set_xlabel(r"$T_m = 300\, s$")
                                elif k==2:
                                    axt.set_xlabel(r"$T_m = 600\, s$")
                            elif row==2:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                elif k==1:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                                elif k==2:
                                    ax[row][k].set_xlabel(r"$T\,  s$")
                            else:
                                ax[row][k].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                                ax[row][k].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
                            if k==0:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1))
                                if row==0:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif row==1:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif row==2:
                                    ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                            elif k==2:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                axt = ax[row][k].twinx()
                                labels = [item.get_text() for item in axt.get_yticklabels()]
                                empty_string_labels = ['']*len(labels)
                                axt.set_yticklabels(empty_string_labels)
                                if row==0:
                                    axt.set_ylabel("LD25")
                                elif row==1:
                                    axt.set_ylabel("HD25")
                                elif row==2:
                                    axt.set_ylabel("HD100")
                            else:
                                ax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                            if show_grid[row][k]==0:
                                show_grid[row][k]=1
                                ax[row][k].grid(which='major')
                fig.tight_layout()
                fig_path = path+"adaptive_activation.pdf"
                fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3,loc='upper right',framealpha=0.7,borderaxespad=0)
                fig.savefig(fig_path, bbox_inches='tight')
                plt.close(fig)

##########################################################################################################
    def print_compare_messages(self,data_in):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adpt = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        adam            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$ID+B$")
        rnd             = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        rnd_inf         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')
        rnd_adp         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[5]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{a}$')
        handles_r       = [adam,rnd,rnd_inf,rnd_adp]
        svoid_x_ticks   = []
        void_x_ticks    = []
        real_x_ticks    = []

        if len(real_x_ticks)==0:
            for x in range(0,1201,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        fig, ax     = plt.subplots(nrows=3, ncols=3,figsize=(36,20))
        for k in dict_adam.keys():
            tmp =[]
            res = dict_adam.get(k)
            norm = int(k[4])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam.update({k:tmp})
        for k in dict_rnd.keys():
            tmp =[]
            res = dict_rnd.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd.update({k:tmp})
        for k in dict_rnd_inf.keys():
            tmp =[]
            res = dict_rnd_inf.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_inf.update({k:tmp})
        for k in dict_rnd_adpt.keys():
            tmp =[]
            res = dict_rnd_adpt.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_adpt.update({k:tmp})
        for k in dict_adam.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[1]),lw=6)
        for k in dict_rnd.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_rnd.get(k),color=scalarMap.to_rgba(typo[3]),lw=6)
        for k in dict_rnd_inf.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_rnd_inf.get(k),color=scalarMap.to_rgba(typo[4]),lw=6)
        for k in dict_rnd_adpt.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_rnd_adpt.get(k),color=scalarMap.to_rgba(typo[5]),lw=6)
        for x in range(2):
            for y in range(3):
                ax[x][y].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,3):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(3):
            ax[2][y].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)

        axt0=ax[0][0].twiny()
        axt1=ax[0][1].twiny()
        axt2=ax[0][2].twiny()
        labels = [item.get_text() for item in axt0.get_xticklabels()]
        empty_string_labels = ['']*len(labels)
        axt0.set_xticklabels(empty_string_labels)
        axt1.set_xticklabels(empty_string_labels)
        axt2.set_xticklabels(empty_string_labels)
        axt0.set_xlabel(r"$T_m = 60\, s$")
        axt1.set_xlabel(r"$T_m = 300\, s$")
        axt2.set_xlabel(r"$T_m = 600\, s$")
        ayt0=ax[0][2].twinx()
        ayt1=ax[1][2].twinx()
        ayt2=ax[2][2].twinx()
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
        for x in range(3):
            for y in range(3):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,1201)
                if x==0 or x==1:
                    ax[x][y].set_ylim(0,1)
                else:
                    ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/compare_messages.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=4, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

##########################################################################################################
    def print_messages(self,data_in):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_rnd_adpt = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        park            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$AN_{t}$")
        adam            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r"$ID+B$")
        fifo            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{f}$')
        rnd             = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        rnd_inf         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')
        rnd_adp        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[5]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{a}$')
        handles_r       = [adam,rnd,rnd_inf,rnd_adp]
        svoid_x_ticks   = []
        void_x_ticks    = []
        real_x_ticks    = []

        if len(real_x_ticks)==0:
            for x in range(0,1201,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        fig, ax     = plt.subplots(nrows=3, ncols=3,figsize=(36,20))
        for k in dict_adam.keys():
            tmp =[]
            res = dict_adam.get(k)
            norm = int(k[4])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam.update({k:tmp})
        # for k in dict_park.keys():
        #     tmp =[]
        #     res = dict_park.get(k)
        #     norm = int(k[4])-1
        #     for xi in res:
        #         tmp.append(xi/norm)
        #     dict_park.update({k:tmp})
        # for k in dict_fifo.keys():
        #     tmp =[]
        #     res = dict_fifo.get(k)
        #     norm = int(k[4])-1
        #     for xi in res:
        #         tmp.append(xi/norm)
        #     dict_fifo.update({k:tmp})
        for k in dict_rnd.keys():
            tmp =[]
            res = dict_rnd.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd.update({k:tmp})
        for k in dict_rnd_inf.keys():
            tmp =[]
            res = dict_rnd_inf.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_inf.update({k:tmp})
        for k in dict_rnd_adpt.keys():
            tmp =[]
            res = dict_rnd_adpt.get(k)
            norm = int(k[4])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_adpt.update({k:tmp})
        # for k in dict_park.keys():
        #     row = 0
        #     col = 0
        #     if k[0]=='big' and k[4]=='25':
        #         row = 0
        #     elif k[0]=='big' and k[4]=='100':
        #         row = 2
        #     elif k[0]=='small':
        #         row = 1
        #     if k[5] == '60':
        #         col = 0
        #     elif k[5] == '300':
        #         col = 1
        #     elif k[5] == '600':
        #         col = 2
        #     ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6)
        for k in dict_adam.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[1]),lw=6)
        # for k in dict_fifo.keys():
        #     row = 0
        #     col = 0
        #     if k[0]=='big' and k[4]=='25':
        #         row = 0
        #     elif k[0]=='big' and k[4]=='100':
        #         row = 2
        #     elif k[0]=='small':
        #         row = 1
        #     if k[5] == '60':
        #         col = 0
        #     elif k[5] == '300':
        #         col = 1
        #     elif k[5] == '600':
        #         col = 2
        #     ax[row][col].plot(dict_fifo.get(k),color=scalarMap.to_rgba(typo[2]),lw=6)
        for k in dict_rnd.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_rnd.get(k),color=scalarMap.to_rgba(typo[3]),lw=6)
        for k in dict_rnd_inf.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_rnd_inf.get(k),color=scalarMap.to_rgba(typo[4]),lw=6)
        for k in dict_rnd_adpt.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[4]=='25':
                row = 0
            elif k[0]=='big' and k[4]=='100':
                row = 2
            elif k[0]=='small':
                row = 1
            if k[5] == '60':
                col = 0
            elif k[5] == '300':
                col = 1
            elif k[5] == '600':
                col = 2
            ax[row][col].plot(dict_rnd_adpt.get(k),color=scalarMap.to_rgba(typo[5]),lw=6)
        for x in range(2):
            for y in range(3):
                ax[x][y].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,3):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(3):
            ax[2][y].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)

        axt0=ax[0][0].twiny()
        axt1=ax[0][1].twiny()
        axt2=ax[0][2].twiny()
        labels = [item.get_text() for item in axt0.get_xticklabels()]
        empty_string_labels = ['']*len(labels)
        axt0.set_xticklabels(empty_string_labels)
        axt1.set_xticklabels(empty_string_labels)
        axt2.set_xticklabels(empty_string_labels)
        axt0.set_xlabel(r"$T_m = 60\, s$")
        axt1.set_xlabel(r"$T_m = 300\, s$")
        axt2.set_xlabel(r"$T_m = 600\, s$")
        ayt0=ax[0][2].twinx()
        ayt1=ax[1][2].twinx()
        ayt2=ax[2][2].twinx()
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
        for x in range(3):
            for y in range(3):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,1201)
                if x==0 or x==1:
                    ax[x][y].set_ylim(0,1)
                else:
                    ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/messages.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

##########################################################################################################
    def print_buff_opts(self,path,data_in,fig_name,y_lim,_XLIM,XLIM_):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_no_act, dict_ins, dict_upd = data_in[0], data_in[1], data_in[2]
        no_action   = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='no_action')
        insertion   = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='insertion')
        update      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='update')
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        
        handles_r   = [no_action,insertion,update]
        fig, ax     = plt.subplots(nrows=3, ncols=3,figsize=(28,18))
        if len(real_x_ticks)==0:
            for x in range(0,1201,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in dict_no_act.keys():
            row = 0
            col = 0
            if k[0]=='bigA' and k[1]=='25':
                row = 0
            elif k[0]=='bigA' and k[1]=='100':
                row = 2
            elif k[0]=='smallA':
                row = 1
            if k[2] == '60':
                col = 0
            elif k[2] == '300':
                col = 1
            elif k[2] == '600':
                col = 2
            ax[row][col].plot(dict_no_act.get(k),color=scalarMap.to_rgba(typo[0]),lw=3)
            ax[row][col].plot(dict_ins.get(k),color=scalarMap.to_rgba(typo[1]),lw=3)
            ax[row][col].plot(dict_upd.get(k),color=scalarMap.to_rgba(typo[2]),lw=3)
        for x in range(2):
            for y in range(3):
                ax[x][y].set_xticks(np.arange(0,1201,300),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,3):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(3):
            ax[2][y].set_xticks(np.arange(0,1201,300),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,1201,50),labels=void_x_ticks,minor=True)
        axt0=ax[0][0].twiny()
        axt1=ax[0][1].twiny()
        axt2=ax[0][2].twiny()
        labels = [item.get_text() for item in axt0.get_xticklabels()]
        empty_string_labels = ['']*len(labels)
        axt0.set_xticklabels(empty_string_labels)
        axt1.set_xticklabels(empty_string_labels)
        axt2.set_xticklabels(empty_string_labels)
        axt0.set_xlabel(r"$T_m = 60\, s$")
        axt1.set_xlabel(r"$T_m = 300\, s$")
        axt2.set_xlabel(r"$T_m = 600\, s$")
        ayt0=ax[0][2].twinx()
        ayt1=ax[1][2].twinx()
        ayt2=ax[2][2].twinx()
        labels = [item.get_text() for item in axt0.get_yticklabels()]
        empty_string_labels = ['']*len(labels)
        ayt0.set_yticklabels(empty_string_labels)
        ayt1.set_yticklabels(empty_string_labels)
        ayt2.set_yticklabels(empty_string_labels)
        ayt0.set_ylabel("LD25")
        ayt1.set_ylabel("HD25")
        ayt2.set_ylabel("HD100")
        ax[0][0].set_ylabel("#")
        ax[1][0].set_ylabel("#")
        ax[2][0].set_ylabel("#")
        ax[2][0].set_xlabel(r"$T\, (s)$")
        ax[2][1].set_xlabel(r"$T\, (s)$")
        ax[2][2].set_xlabel(r"$T\, (s)$")
        for x in range(3):
            for y in range(3):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(_XLIM,XLIM_)
                ax[x][y].set_ylim(0,y_lim)
        fig.tight_layout()
        fig_path = path+fig_name
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
#########################################################################################################
    def extract_median(self,array,max_time):
        mt = int(max_time)
        median = max_time
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0 and sortd_arr[(len(sortd_arr)//2)]!=mt:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            if sortd_arr[math.ceil(len(sortd_arr)/2)]!=mt: median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median