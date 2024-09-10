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
            if elem == "proc_data" or elem == "msgs_data" or elem == "pos_data":
                self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def plot_pos(self,data):
        dict_park_square, dict_adam_square, dict_our_square = {},{},{}
        dict_park_rect, dict_adam_rect, dict_our_rect       = {},{},{}
        for k in data.keys():
            if k[1]=='P':
                if k[0].split(';')[0] == k[0].split(';')[1]:
                    dict_park_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                else:
                    dict_park_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
            else:
                if int(k[4])==0:
                    if k[0].split(';')[0] == k[0].split(';')[1]:
                        dict_adam_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    else:
                        dict_adam_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                else:
                    if k[0].split(';')[0] == k[0].split(';')[1]:
                        dict_our_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    else:
                        dict_our_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
        self.print_pos("tot_average_distance",[dict_park_square,dict_adam_square,dict_our_square],[dict_park_rect,dict_adam_rect,dict_our_rect])

##########################################################################################################
    def plot_messages(self,data):
        dict_park_square, dict_adam_square, dict_our_square = {},{},{}
        dict_park_rect, dict_adam_rect, dict_our_rect = {},{},{}
        com_dict_park_square, com_dict_adam_square, com_dict_our_square = {},{},{}
        com_dict_park_rect, com_dict_adam_rect, com_dict_our_rect = {},{},{}
        uncom_dict_park_square, uncom_dict_adam_square, uncom_dict_our_square = {},{},{}
        uncom_dict_park_rect, uncom_dict_adam_rect, uncom_dict_our_rect = {},{},{}
        for k in data.keys():
            if k[1]=='P':
                if k[0].split(';')[0] == k[0].split(';')[1]:
                    if k[7] == "commit_average":
                        com_dict_park_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    elif k[7] == "uncommit_average":
                        uncom_dict_park_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    else:
                        dict_park_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                else:
                    if k[7] == "commit_average":
                        com_dict_park_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    elif k[7] == "uncommit_average":
                        uncom_dict_park_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    else:
                        dict_park_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
            else:
                if int(k[4])==0:
                    if k[0].split(';')[0] == k[0].split(';')[1]:
                        if k[7] == "commit_average":
                            com_dict_adam_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        elif k[7] == "uncommit_average":
                            uncom_dict_adam_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        else:
                            dict_adam_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    else:
                        if k[7] == "commit_average":
                            com_dict_adam_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        elif k[7] == "uncommit_average":
                            uncom_dict_adam_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        else:
                            dict_adam_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                else:
                    if k[0].split(';')[0] == k[0].split(';')[1]:
                        if k[7] == "commit_average":
                            com_dict_our_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        elif k[7] == "uncommit_average":
                            uncom_dict_our_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        else:
                            dict_our_square.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                    else:
                        if k[7] == "commit_average":
                            com_dict_our_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        elif k[7] == "uncommit_average":
                            uncom_dict_our_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
                        else:
                            dict_our_rect.update({(k[0],k[2],k[3],k[5],k[6]):data.get(k)})
        self.print_messages("tot_average",[dict_park_square,dict_adam_square,dict_our_square],0)
        self.print_messages("tot_average",[dict_park_rect,dict_adam_rect,dict_our_rect],1)
        self.print_dif_messages("dif_commit_average",[com_dict_park_square,com_dict_adam_square,com_dict_our_square],[uncom_dict_park_square,uncom_dict_adam_square,uncom_dict_our_square],0)
        self.print_dif_messages("dif_commit_average",[com_dict_park_rect,com_dict_adam_rect,com_dict_our_rect],[uncom_dict_park_rect,uncom_dict_adam_rect,uncom_dict_our_rect],1)

##########################################################################################################
    def read_pos_csv(self,path):
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
                                data.update({(algo,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7]),data_val.get(keys[9])):(data_val.get(keys[10]),data_val.get(keys[11]))})
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
                                data.update({(algo,n_runs,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7]),data_val.get(keys[9])):(data_val.get(keys[10]),data_val.get(keys[11]))})
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
        states, comm_states, uncomm_states, times, messages_b, messages_r = {},{},{},{},{},{}
        algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, msg_hops, msg_time = [],[],[],[],[],[],[],[],[],[]
        for k in data.keys():
            for i in range(len(k)-1):
                if i == 0 and k[i] not in algorithm: algorithm.append(k[i])
                elif i == 1 and k[i] not in n_runs: n_runs.append(k[i])
                elif i == 2 and k[i] not in exp_time: exp_time.append(k[i])
                elif i == 3 and k[i] not in arena_size: arena_size.append(k[i])
                elif i == 4 and k[i] not in communication: communication.append(k[i])
                elif i == 5 and k[i] not in n_agents: n_agents.append(k[i])
                elif i == 6 and k[i] not in thrlds: thrlds.append(k[i])
                elif i == 7 and k[i] not in gt: gt.append(k[i])
                elif i == 8 and k[i] not in msg_hops: msg_hops.append(k[i])
                elif i == 9 and k[i] not in msg_time: msg_time.append(k[i])
            if k[-1] == "times":
                times.update({k[:-1]:data.get(k)})
            elif k[-1] == "swarm_state":
                states.update({k[:-1]:data.get(k)})
            elif k[-1] == "committed_state":
                comm_states.update({k[:-1]:data.get(k)})
            elif k[-1] == "uncommitted_state":
                uncomm_states.update({k[:-1]:data.get(k)})
            elif k[-1] == "broadcast_msg":
                messages_b.update({k[:-1]:data.get(k)})
            elif k[-1] == "rebroadcast_msg":
                messages_r.update({k[:-1]:data.get(k)})
        return (algorithm, arena_size, n_runs, exp_time, communication, n_agents, gt, thrlds, msg_hops, msg_time), states, times, (messages_b, messages_r), (comm_states,uncomm_states)
    
##########################################################################################################
    def plot_by_commit_w_gt_thr(self,data_in):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_state_comm_sq,dict_adms_state_comm_sq,dict_our_state_comm_sq           = {},{},{}
        dict_park_state_uncomm_sq,dict_adms_state_uncomm_sq,dict_our_state_uncomm_sq     = {},{},{}
        dict_park_state_comm_rt,dict_adms_state_comm_rt,dict_our_state_comm_rt           = {},{},{}
        dict_park_state_uncomm_rt,dict_adms_state_uncomm_rt,dict_our_state_uncomm_rt     = {},{},{}
        ground_T, threshlds , msg_time                                          = [],[],[]
        algo,arena,runs,time,comm,agents,msg_hop                                = [],[],[],[],[],[],[]
        p_k,o_k                                                                 = [],[]
        for i in range(len(data_in)):
            da_K = data_in[i][0].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in runs: runs.append(k0[1])
                if k0[2] not in time: time.append(k0[2])
                if k0[3] not in arena: arena.append(k0[3])
                if k0[4] not in comm: comm.append(k0[4])
                if k0[5] not in agents: agents.append(k0[5])
                if k0[6] not in threshlds: threshlds.append(k0[6])
                if k0[7] not in ground_T: ground_T.append(k0[7])
                if k0[8] not in msg_hop: msg_hop.append(k0[8])
                if k0[9] not in msg_time: msg_time.append(k0[9])
        for i in range(len(data_in)):
            for a in algo:
                for n_r in runs:
                    for et in time:
                        for a_s in arena:
                            for c in comm:
                                for n_a in agents:
                                    for thr in threshlds:
                                        for gt in ground_T:
                                            for m_h in msg_hop:
                                                for m_t in msg_time:
                                                    comm_data = data_in[i][0].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    uncomm_data = data_in[i][1].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    if comm_data != None:
                                                        if (a=='P' and m_t not in p_k) or (a=='O' and m_t not in o_k):
                                                            p_k.append(m_t) if a=='P' else o_k.append(m_t)
                                                        if a=='P' and int(c)==0 and m_t in p_k:
                                                            if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                dict_park_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                dict_park_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                            else:
                                                                dict_park_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                dict_park_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                        if a=='O' and m_t in o_k:
                                                            if int(c)==0:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_adms_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_adms_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                else:
                                                                    dict_adms_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_adms_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                            else:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_our_state_comm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_our_state_uncomm_sq.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
                                                                else:
                                                                    dict_our_state_comm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):comm_data[0]})
                                                                    dict_our_state_uncomm_rt.update({(a_s,n_a,m_t,m_h,gt,thr):uncomm_data[0]})
        self.print_evolutions_by_commit(path,ground_T,threshlds,[dict_park_state_comm_sq,dict_adms_state_comm_sq,dict_our_state_comm_sq],[dict_park_state_uncomm_sq,dict_adms_state_uncomm_sq,dict_our_state_uncomm_sq],[p_k,o_k],[["0_500;0_500","1_000;1_000"],agents],msg_hop,"square")
        self.print_evolutions_by_commit(path,ground_T,threshlds,[dict_park_state_comm_rt,dict_adms_state_comm_rt,dict_our_state_comm_rt],[dict_park_state_uncomm_rt,dict_adms_state_uncomm_rt,dict_our_state_uncomm_rt],[p_k,o_k],[["1_000;0_250","2_000;0_500"],agents],msg_hop,"rectangular")

##########################################################################################################
    def plot_active_w_gt_thr(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_state_sq,dict_adms_state_sq,dict_our_state_sq  = {},{},{}
        dict_park_time_sq,dict_adms_time_sq,dict_our_time_sq     = {},{},{}
        dict_park_state_rt,dict_adms_state_rt,dict_our_state_rt  = {},{},{}
        dict_park_time_rt,dict_adms_time_rt,dict_our_time_rt     = {},{},{}
        ground_T, threshlds , msg_time                  = [],[],[]
        algo,arena,runs,time,comm,agents,msg_hop        = [],[],[],[],[],[],[]
        p_k,o_k                                         = [],[]
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0] not in algo: algo.append(k0[0])
                if k0[1] not in runs: runs.append(k0[1])
                if k0[2] not in time: time.append(k0[2])
                if k0[3] not in arena: arena.append(k0[3])
                if k0[4] not in comm: comm.append(k0[4])
                if k0[5] not in agents: agents.append(k0[5])
                if k0[6] not in threshlds: threshlds.append(k0[6])
                if k0[7] not in ground_T: ground_T.append(k0[7])
                if k0[8] not in msg_hop: msg_hop.append(k0[8])
                if k0[9] not in msg_time: msg_time.append(k0[9])
        for i in range(len(data_in)):
            for a in algo:
                for n_r in runs:
                    for et in time:
                        for a_s in arena:
                            for c in comm:
                                for n_a in agents:
                                    for thr in threshlds:
                                        for gt in ground_T:
                                            for m_h in msg_hop:
                                                for m_t in msg_time:
                                                    s_data = data_in[i].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    t_data = times[i].get((a,n_r,et,a_s,c,n_a,thr,gt,m_h,m_t))
                                                    if s_data != None:
                                                        if (a=='P' and m_t not in p_k) or (a=='O' and m_t not in o_k):
                                                            p_k.append(m_t) if a=='P' else o_k.append(m_t)
                                                        
                                                        if a=='P' and int(c)==0 and m_t in p_k:
                                                            if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                dict_park_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                dict_park_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            else:
                                                                dict_park_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                dict_park_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            
                                                        if a=='O' and m_t in o_k:
                                                            if int(c)==0:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_adms_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_adms_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                else:
                                                                    dict_adms_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_adms_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                            else:
                                                                if a_s.split(';')[0] == a_s.split(';')[1]:
                                                                    dict_our_state_sq.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_our_time_sq.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
                                                                else:
                                                                    dict_our_state_rt.update({(a_s,n_a,m_t,m_h,gt,thr):s_data[0]})
                                                                    dict_our_time_rt.update({(a_s,n_a,m_t,m_h,gt,thr):t_data[0]})
        self.print_evolutions(path,ground_T,threshlds,[dict_park_state_sq,dict_adms_state_sq,dict_our_state_sq],[dict_park_time_sq,dict_adms_time_sq,dict_our_time_sq],[p_k,o_k],[["0_500;0_500","1_000;1_000"],agents],msg_hop,"square")
        self.print_evolutions(path,ground_T,threshlds,[dict_park_state_rt,dict_adms_state_rt,dict_our_state_rt],[dict_park_time_rt,dict_adms_time_rt,dict_our_time_rt],[p_k,o_k],[["1_000;0_250","2_000;0_500"],agents],msg_hop,"rectangular")

##########################################################################################################
    def print_evolutions_by_commit(self,path,ground_T,threshlds,data_comm,data_uncomm,keys,more_k,msg_hop,arena_type):
        plt.rcParams.update({"font.size":36})
        cm                                                  = plt.get_cmap('viridis') 
        typo                                                = [0,1,2,3,4,5,6,7]
        cNorm                                               = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap                                           = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park_comm,dict_adam_comm,dict_our_comm         = data_comm[0], data_comm[1], data_comm[2]
        dict_park_uncomm,dict_adam_uncomm,dict_our_uncomm   = data_uncomm[0], data_uncomm[1], data_uncomm[2]
        p_k, o_k                                            = keys[0],keys[1]
        for x in range(len(o_k)):
            o_k[x] = int(o_k[x])
        o_k             = np.sort(o_k)
        arena           = more_k[0]
        red             = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        handles_r       = [red,blue,green]
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        for m_h in msg_hop:
            for gt in ground_T:
                for thr in threshlds:
                    cfig, cax = plt.subplots(nrows=3, ncols=4,figsize=(36,20))
                    ufig, uax = plt.subplots(nrows=3, ncols=4,figsize=(36,20))
                    for a in arena:
                        if a=="0_500;0_500" or a=="1_000;0_250":
                            agents = ["25"]
                        else:
                            agents = more_k[1]
                        for ag in agents:
                            if ag=="25":
                                if a=="0_500;0_500" or a=="1_000;0_250":
                                    row = 1
                                    if a=="0_500;0_500":
                                        if gt=="0_56": p_k=["13","15","18","19"]
                                        elif gt=="0_68": p_k=["14","16","19","20"]
                                        elif gt=="0_80": p_k=["15","18","20","22"]
                                    elif a=="1_000;0_250":
                                        if gt=="0_56": p_k=["10","11","12","13"]
                                        elif gt=="0_68": p_k=["11","12","14","14_01"]
                                        elif gt=="0_80": p_k=["13","15","16","17"]
                                else:
                                    row = 0
                                    if a=="1_000;1_000":
                                        if gt=="0_56": p_k=["7","9","11","12"]
                                        elif gt=="0_68": p_k=["7","9","12","13"]
                                        elif gt=="0_80": p_k=["7","10","14","15"]
                                    elif a=="2_000;0_500":
                                        if gt=="0_56": p_k=["6","8","10","11"]
                                        elif gt=="0_68": p_k=["6","8","11","12"]
                                        elif gt=="0_80": p_k=["7","9","12","14"]
                            else:
                                row = 2
                                if a=="1_000;1_000":
                                    if gt=="0_56": p_k=["28","36","45","49"]
                                    elif gt=="0_68": p_k=["29","38","48","53"]
                                    elif gt=="0_80": p_k=["31","42","56","62"]
                                elif a=="2_000;0_500":
                                    if gt=="0_56": p_k=["27","34","42","45"]
                                    elif gt=="0_68": p_k=["27","36","45","49"]
                                    elif gt=="0_80": p_k=["28","38","51","56"]
                            for k in range(len(o_k)):
                                cax[row][k].plot(dict_park_comm.get((a,ag,p_k[k],m_h,gt,thr)),color=scalarMap.to_rgba(typo[0]),lw=6)
                                cax[row][k].plot(dict_adam_comm.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=scalarMap.to_rgba(typo[3]),lw=6)
                                cax[row][k].plot(dict_our_comm.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=scalarMap.to_rgba(typo[6]),lw=6)
                                cax[row][k].set_xlim(0,901)
                                cax[row][k].set_ylim(0,1)
                                uax[row][k].plot(dict_park_uncomm.get((a,ag,p_k[k],m_h,gt,thr)),color=scalarMap.to_rgba(typo[0]),lw=6)
                                uax[row][k].plot(dict_adam_uncomm.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=scalarMap.to_rgba(typo[3]),lw=6)
                                uax[row][k].plot(dict_our_uncomm.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=scalarMap.to_rgba(typo[6]),lw=6)
                                uax[row][k].set_xlim(0,901)
                                uax[row][k].set_ylim(0,1)
                                if len(real_x_ticks)==0:
                                    for x in range(0,901,50):
                                        if x%150 == 0:
                                            svoid_x_ticks.append('')
                                            void_x_ticks.append('')
                                            real_x_ticks.append(str(int(np.round(x,0))))
                                        else:
                                            void_x_ticks.append('')
                                    for y in range(0,11,1):
                                        void_y_ticks.append('')
                                if row == 0:
                                    cax[row][k].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                                    cax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    caxt = cax[row][k].twiny()
                                    uax[row][k].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                                    uax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    uaxt = uax[row][k].twiny()
                                    labels = [item.get_text() for item in caxt.get_xticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    caxt.set_xticklabels(empty_string_labels)
                                    uaxt.set_xticklabels(empty_string_labels)
                                    if k==0:
                                        caxt.set_xlabel(r"$T_m = 60\, s$")
                                        uaxt.set_xlabel(r"$T_m = 60\, s$")
                                    elif k==1:
                                        caxt.set_xlabel(r"$T_m = 120\, s$")
                                        uaxt.set_xlabel(r"$T_m = 120\, s$")
                                    elif k==2:
                                        caxt.set_xlabel(r"$T_m = 300\, s$")
                                        uaxt.set_xlabel(r"$T_m = 300\, s$")
                                    elif k==3:
                                        caxt.set_xlabel(r"$T_m = 600\, s$")
                                        uaxt.set_xlabel(r"$T_m = 600\, s$")
                                elif row==2:
                                    cax[row][k].set_xticks(np.arange(0,901,150),labels=real_x_ticks)
                                    cax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    uax[row][k].set_xticks(np.arange(0,901,150),labels=real_x_ticks)
                                    uax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    if k==0:
                                        cax[row][k].set_xlabel(r"$T\,  s$")
                                        uax[row][k].set_xlabel(r"$T\,  s$")
                                    elif k==1:
                                        cax[row][k].set_xlabel(r"$T\,  s$")
                                        uax[row][k].set_xlabel(r"$T\,  s$")
                                    elif k==2:
                                        cax[row][k].set_xlabel(r"$T\,  s$")
                                        uax[row][k].set_xlabel(r"$T\,  s$")
                                    elif k==3:
                                        cax[row][k].set_xlabel(r"$T\,  s$")
                                        uax[row][k].set_xlabel(r"$T\,  s$")
                                else:
                                    cax[row][k].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                                    cax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    uax[row][k].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                                    uax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    cax[row][k].set_yticks(np.arange(0,1.01,.1))
                                    uax[row][k].set_yticks(np.arange(0,1.01,.1))
                                    if row==0:
                                        cax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                        uax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                    elif row==1:
                                        cax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                        uax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                    elif row==2:
                                        cax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                        uax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif k==3:
                                    cax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    caxt = cax[row][k].twinx()
                                    uax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    uaxt = uax[row][k].twinx()
                                    labels = [item.get_text() for item in caxt.get_yticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    caxt.set_yticklabels(empty_string_labels)
                                    uaxt.set_yticklabels(empty_string_labels)
                                    if row==0:
                                        caxt.set_ylabel("LD25")
                                        uaxt.set_ylabel("LD25")
                                    elif row==1:
                                        caxt.set_ylabel("HD25")
                                        uaxt.set_ylabel("HD25")
                                    elif row==2:
                                        caxt.set_ylabel("HD100")
                                        uaxt.set_ylabel("HD100")
                                else:
                                    cax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                    uax[row][k].set_yticks(np.arange(0,1.01,.1),labels=void_y_ticks)
                                cax[row][k].grid(which='major')
                                uax[row][k].grid(which='major')
                    cfig.tight_layout()
                    ufig.tight_layout()
                    cfig_path = path+"mH#"+m_h+"_T#"+thr+"_G#"+gt+"_"+arena_type+"Arena_activation_committed.pdf"
                    ufig_path = path+"mH#"+m_h+"_T#"+thr+"_G#"+gt+"_"+arena_type+"Arena_activation_uncommitted.pdf"
                    cfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3,loc='upper right',framealpha=0.7,borderaxespad=0)
                    ufig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3,loc='upper right',framealpha=0.7,borderaxespad=0)
                    cfig.savefig(cfig_path, bbox_inches='tight')
                    ufig.savefig(ufig_path, bbox_inches='tight')
                    plt.close(cfig)
                    plt.close(ufig)

##########################################################################################################
    def print_evolutions(self,path,ground_T,threshlds,data_in,times_in,keys,more_k,msg_hop,arena_type):
        plt.rcParams.update({"font.size":36})
        cm                              = plt.get_cmap('viridis') 
        typo                            = [0,1,2,3,4,5,6,7]
        cNorm                           = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap                       = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_our    = data_in[0], data_in[1], data_in[2]
        p_k, o_k                        = keys[0],keys[1]
        for x in range(len(o_k)):
            o_k[x] = int(o_k[x])
        o_k             = np.sort(o_k)
        arena           = more_k[0]
        red             = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        handles_r       = [red,blue,green]
        svoid_x_ticks   = []
        void_x_ticks    = []
        void_y_ticks    = []
        real_x_ticks    = []
        for m_h in msg_hop:
            for gt in ground_T:
                for thr in threshlds:
                    fig, ax = plt.subplots(nrows=3, ncols=4,figsize=(36,20))
                    for a in arena:
                        if a=="0_500;0_500" or a=="1_000;0_250":
                            agents = ["25"]
                        else:
                            agents = more_k[1]
                        for ag in agents:
                            if ag=="25":
                                if a=="0_500;0_500" or a=="1_000;0_250":
                                    row = 1
                                    if a=="0_500;0_500":
                                        if gt=="0_56": p_k=["13","15","18","19"]
                                        elif gt=="0_68": p_k=["14","16","19","20"]
                                        elif gt=="0_80": p_k=["15","18","20","22"]
                                    elif a=="1_000;0_250":
                                        if gt=="0_56": p_k=["10","11","12","13"]
                                        elif gt=="0_68": p_k=["11","12","14","14_01"]
                                        elif gt=="0_80": p_k=["13","15","16","17"]
                                else:
                                    row = 0
                                    if a=="1_000;1_000":
                                        if gt=="0_56": p_k=["7","9","11","12"]
                                        elif gt=="0_68": p_k=["7","9","12","13"]
                                        elif gt=="0_80": p_k=["7","10","14","15"]
                                    elif a=="2_000;0_500":
                                        if gt=="0_56": p_k=["6","8","10","11"]
                                        elif gt=="0_68": p_k=["6","8","11","12"]
                                        elif gt=="0_80": p_k=["7","9","12","14"]
                            else:
                                row = 2
                                if a=="1_000;1_000":
                                    if gt=="0_56": p_k=["28","36","45","49"]
                                    elif gt=="0_68": p_k=["29","38","48","53"]
                                    elif gt=="0_80": p_k=["31","42","56","62"]
                                elif a=="2_000;0_500":
                                    if gt=="0_56": p_k=["27","34","42","45"]
                                    elif gt=="0_68": p_k=["27","36","45","49"]
                                    elif gt=="0_80": p_k=["28","38","51","56"]
                            for k in range(len(o_k)):
                                ax[row][k].plot(dict_park.get((a,ag,p_k[k],m_h,gt,thr)),color=scalarMap.to_rgba(typo[0]),lw=6)
                                ax[row][k].plot(dict_adam.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=scalarMap.to_rgba(typo[3]),lw=6)
                                ax[row][k].plot(dict_our.get((a,ag,str(o_k[k]),m_h,gt,thr)),color=scalarMap.to_rgba(typo[6]),lw=6)
                                ax[row][k].set_xlim(0,901)
                                ax[row][k].set_ylim(0,1)
                                if len(real_x_ticks)==0:
                                    for x in range(0,901,50):
                                        if x%150 == 0:
                                            svoid_x_ticks.append('')
                                            void_x_ticks.append('')
                                            real_x_ticks.append(str(int(np.round(x,0))))
                                        else:
                                            void_x_ticks.append('')
                                    for y in range(0,11,1):
                                        void_y_ticks.append('')
                                if row == 0:
                                    ax[row][k].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                                    ax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    axt = ax[row][k].twiny()
                                    labels = [item.get_text() for item in axt.get_xticklabels()]
                                    empty_string_labels = ['']*len(labels)
                                    axt.set_xticklabels(empty_string_labels)
                                    if k==0:
                                        axt.set_xlabel(r"$T_m = 60\, s$")
                                    elif k==1:
                                        axt.set_xlabel(r"$T_m = 120\, s$")
                                    elif k==2:
                                        axt.set_xlabel(r"$T_m = 300\, s$")
                                    elif k==3:
                                        axt.set_xlabel(r"$T_m = 600\, s$")
                                elif row==2:
                                    ax[row][k].set_xticks(np.arange(0,901,150),labels=real_x_ticks)
                                    ax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                    if k==0:
                                        ax[row][k].set_xlabel(r"$T\,  s$")
                                    elif k==1:
                                        ax[row][k].set_xlabel(r"$T\,  s$")
                                    elif k==2:
                                        ax[row][k].set_xlabel(r"$T\,  s$")
                                    elif k==3:
                                        ax[row][k].set_xlabel(r"$T\,  s$")
                                else:
                                    ax[row][k].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                                    ax[row][k].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
                                if k==0:
                                    ax[row][k].set_yticks(np.arange(0,1.01,.1))
                                    if row==0:
                                        ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                    elif row==1:
                                        ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                    elif row==2:
                                        ax[row][k].set_ylabel(r"$\hat{Q}(G,\tau)$")
                                elif k==3:
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
                    fig_path = path+"mH#"+m_h+"_T#"+thr+"_G#"+gt+"_"+arena_type+"Arena_activation.pdf"
                    fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=3,loc='upper right',framealpha=0.7,borderaxespad=0)
                    fig.savefig(fig_path, bbox_inches='tight')
                    plt.close(fig)

##########################################################################################################
    def print_messages(self,c_type,data_in,a_type):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5,6,7]
        arena_type = "square"
        if a_type==1: arena_type = "rectangular"
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_our = data_in[0], data_in[1], data_in[2]
        red         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        solid       = mlines.Line2D([], [], color="black", marker="None", linestyle="-", linewidth=10, label='GT=0.56')
        dashed      = mlines.Line2D([], [], color="black", marker="None", linestyle="--", linewidth=10, label='GT=0.68')
        dotted      = mlines.Line2D([], [], color="black", marker="None", linestyle=":", linewidth=10, label='GT=0.80')
        void_x_ticks = []
        svoid_x_ticks = []
        real_x_ticks = []
        handles_r   = [red,blue,green]
        handles_l   = [solid,dashed,dotted]
        fig, ax     = plt.subplots(nrows=3, ncols=4,figsize=(36,20))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%150 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in dict_adam.keys():
            tmp =[]
            res = dict_adam.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_adam.update({k:tmp})
        for k in dict_park.keys():
            tmp =[]
            res = dict_park.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_park.update({k:tmp})
        for k in dict_our.keys():
            tmp =[]
            res = dict_our.get(k)
            norm = int(k[3])-1
            for xi in range(len(res)):
                tmp.append(res[xi]/norm)
            dict_our.update({k:tmp})
        for k in dict_park.keys():
            row = 0
            col = 0
            if k[3]=="25":
                if k[0]=="0_500;0_500":
                    row=1
                    if k[2]=="0.56":
                        if k[4] == "13": col=0
                        elif k[4] == "15": col=1
                        elif k[4] == "18": col=2
                        elif k[4] == "19": col=3
                    elif k[2]=="0.68":
                        if k[4] == "14": col=0
                        elif k[4] == "16": col=1
                        elif k[4] == "19": col=2
                        elif k[4] == "20": col=3
                    elif k[2]=="0.80":
                        if k[4] == "15": col=0
                        elif k[4] == "18": col=1
                        elif k[4] == "20": col=2
                        elif k[4] == "22": col=3
                elif k[0]=="1_000;0_250":
                    row=1
                    if k[2]=="0.56":
                        if k[4] == "10": col=0
                        elif k[4] == "11": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "13": col=3
                    elif k[2]=="0.68":
                        if k[4] == "11": col=0
                        elif k[4] == "12": col=1
                        elif k[4] == "14": col=2
                        elif k[4] == "14_01": col=3
                    elif k[2]=="0.80":
                        if k[4] == "13": col=0
                        elif k[4] == "15": col=1
                        elif k[4] == "16": col=2
                        elif k[4] == "17": col=3
                elif k[0]=="1_000;1_000":
                    row=0
                    if k[2]=="0.56":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "11": col=2
                        elif k[4] == "12": col=3
                    elif k[2]=="0.68":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "13": col=3
                    elif k[2]=="0.80":
                        if k[4] == "7": col=0
                        elif k[4] == "10": col=1
                        elif k[4] == "14": col=2
                        elif k[4] == "15": col=3
                elif k[0]=="2_000;0_500":
                    row=0
                    if k[2]=="0.56":
                        if k[4] == "6": col=0
                        elif k[4] == "8": col=1
                        elif k[4] == "10": col=2
                        elif k[4] == "11": col=3
                    elif k[2]=="0.68":
                        if k[4] == "6": col=0
                        elif k[4] == "8": col=1
                        elif k[4] == "11": col=2
                        elif k[4] == "12": col=3
                    elif k[2]=="0.80":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "14": col=3
            elif k[3]=="100":
                if k[0]=="1_000;1_000":
                    row = 2
                    if k[2]=="0.56":
                        if k[4] == "28": col=0
                        elif k[4] == "36": col=1
                        elif k[4] == "45": col=2
                        elif k[4] == "49": col=3
                    elif k[2]=="0.68":
                        if k[4] == "29": col=0
                        elif k[4] == "38": col=1
                        elif k[4] == "48": col=2
                        elif k[4] == "53": col=3
                    elif k[2]=="0.80":
                        if k[4] == "31": col=0
                        elif k[4] == "42": col=1
                        elif k[4] == "56": col=2
                        elif k[4] == "62": col=3
                elif k[0]=="2_000;0_500":
                    row = 2
                    if k[2]=="0.56":
                        if k[4] == "27": col=0
                        elif k[4] == "34": col=1
                        elif k[4] == "42": col=2
                        elif k[4] == "45": col=3
                    elif k[2]=="0.68":
                        if k[4] == "27": col=0
                        elif k[4] == "36": col=1
                        elif k[4] == "45": col=2
                        elif k[4] == "49": col=3
                    elif k[2]=="0.80":
                        if k[4] == "28": col=0
                        elif k[4] == "38": col=1
                        elif k[4] == "51": col=2
                        elif k[4] == "56": col=3
            if k[2]=="0.56": ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6)
            elif k[2]=="0.68": ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6,ls="--")
            elif k[2]=="0.80": ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6,ls=":")
        for k in dict_adam.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            if k[2]=="0.56": ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[3]),lw=6)
            elif k[2]=="0.68": ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[3]),lw=6,ls="--")
            elif k[2]=="0.80": ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[3]),lw=6,ls=":")
        for k in dict_our.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            if k[2]=="0.56": ax[row][col].plot(dict_our.get(k),color=scalarMap.to_rgba(typo[6]),lw=6)
            elif k[2]=="0.68": ax[row][col].plot(dict_our.get(k),color=scalarMap.to_rgba(typo[6]),lw=6,ls="--")
            elif k[2]=="0.80": ax[row][col].plot(dict_our.get(k),color=scalarMap.to_rgba(typo[6]),lw=6,ls=":")
        for x in range(2):
            for y in range(4):
                ax[x][y].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,4):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(4):
            ax[2][y].set_xticks(np.arange(0,901,150),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)

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
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/"+c_type+"_"+arena_type+"Arena_messages.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=6, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

##########################################################################################################
    def print_dif_messages(self,c_type,comm_data_in,uncomm_data_in,a_type):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5,6,7]
        arena_type = "square" if a_type==0 else "rectangular"        
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        comm_dict_park,comm_dict_adam,comm_dict_our         = comm_data_in[0], comm_data_in[1], comm_data_in[2]
        uncomm_dict_park,uncomm_dict_adam,uncomm_dict_our   = uncomm_data_in[0], uncomm_data_in[1], uncomm_data_in[2]
        red         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        solid       = mlines.Line2D([], [], color="black", marker="None", linestyle="-", linewidth=10, label='GT=0.56')
        dashed      = mlines.Line2D([], [], color="black", marker="None", linestyle="--", linewidth=10, label='GT=0.68')
        dotted      = mlines.Line2D([], [], color="black", marker="None", linestyle=":", linewidth=10, label='GT=0.80')
        void_x_ticks = []
        svoid_x_ticks = []
        real_x_ticks = []
        handles_r   = [red,blue,green]
        handles_l   = [solid,dashed,dotted]
        fig, ax     = plt.subplots(nrows=3, ncols=4,figsize=(36,20))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%150 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in comm_dict_adam.keys():
            uncom_tmp,com_tmp = [],[]
            norm = int(k[3])-1
            com_res = comm_dict_adam.get(k)
            uncom_res = uncomm_dict_adam.get(k)
            for xi in range(len(com_res)):
                uncom_tmp.append(uncom_res[xi]/norm)
                com_tmp.append(com_res[xi]/norm)
            comm_dict_adam.update({k:com_tmp})
            uncomm_dict_adam.update({k:uncom_tmp})
        for k in comm_dict_park.keys():
            uncom_tmp,com_tmp = [],[]
            norm = int(k[3])-1
            com_res = comm_dict_park.get(k)
            uncom_res = uncomm_dict_park.get(k)
            for xi in range(len(com_res)):
                uncom_tmp.append(uncom_res[xi]/norm)
                com_tmp.append(com_res[xi]/norm)
            comm_dict_park.update({k:com_tmp})
            uncomm_dict_park.update({k:uncom_tmp})
        for k in comm_dict_our.keys():
            uncom_tmp,com_tmp = [],[]
            norm = int(k[3])-1
            com_res = comm_dict_our.get(k)
            uncom_res = uncomm_dict_our.get(k)
            for xi in range(len(com_res)):
                uncom_tmp.append(uncom_res[xi]/norm)
                com_tmp.append(com_res[xi]/norm)
            comm_dict_our.update({k:com_tmp})
            uncomm_dict_our.update({k:uncom_tmp})
        for k in comm_dict_park.keys():
            row = 0
            col = 0
            if k[3]=="25":
                if k[0]=="0_500;0_500":
                    row=1
                    if k[2]=="0.56":
                        if k[4] == "13": col=0
                        elif k[4] == "15": col=1
                        elif k[4] == "18": col=2
                        elif k[4] == "19": col=3
                    elif k[2]=="0.68":
                        if k[4] == "14": col=0
                        elif k[4] == "16": col=1
                        elif k[4] == "19": col=2
                        elif k[4] == "20": col=3
                    elif k[2]=="0.80":
                        if k[4] == "15": col=0
                        elif k[4] == "18": col=1
                        elif k[4] == "20": col=2
                        elif k[4] == "22": col=3
                elif k[0]=="1_000;0_250":
                    row=1
                    if k[2]=="0.56":
                        if k[4] == "10": col=0
                        elif k[4] == "11": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "13": col=3
                    elif k[2]=="0.68":
                        if k[4] == "11": col=0
                        elif k[4] == "12": col=1
                        elif k[4] == "14": col=2
                        elif k[4] == "14_01": col=3
                    elif k[2]=="0.80":
                        if k[4] == "13": col=0
                        elif k[4] == "15": col=1
                        elif k[4] == "16": col=2
                        elif k[4] == "17": col=3
                elif k[0]=="1_000;1_000":
                    row=0
                    if k[2]=="0.56":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "11": col=2
                        elif k[4] == "12": col=3
                    elif k[2]=="0.68":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "13": col=3
                    elif k[2]=="0.80":
                        if k[4] == "7": col=0
                        elif k[4] == "10": col=1
                        elif k[4] == "14": col=2
                        elif k[4] == "15": col=3
                elif k[0]=="2_000;0_500":
                    row=0
                    if k[2]=="0.56":
                        if k[4] == "6": col=0
                        elif k[4] == "8": col=1
                        elif k[4] == "10": col=2
                        elif k[4] == "11": col=3
                    elif k[2]=="0.68":
                        if k[4] == "6": col=0
                        elif k[4] == "8": col=1
                        elif k[4] == "11": col=2
                        elif k[4] == "12": col=3
                    elif k[2]=="0.80":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "14": col=3
            elif k[3]=="100":
                if k[0]=="1_000;1_000":
                    row = 2
                    if k[2]=="0.56":
                        if k[4] == "28": col=0
                        elif k[4] == "36": col=1
                        elif k[4] == "45": col=2
                        elif k[4] == "49": col=3
                    elif k[2]=="0.68":
                        if k[4] == "29": col=0
                        elif k[4] == "38": col=1
                        elif k[4] == "48": col=2
                        elif k[4] == "53": col=3
                    elif k[2]=="0.80":
                        if k[4] == "31": col=0
                        elif k[4] == "42": col=1
                        elif k[4] == "56": col=2
                        elif k[4] == "62": col=3
                elif k[0]=="2_000;0_500":
                    row = 2
                    if k[2]=="0.56":
                        if k[4] == "27": col=0
                        elif k[4] == "34": col=1
                        elif k[4] == "42": col=2
                        elif k[4] == "45": col=3
                    elif k[2]=="0.68":
                        if k[4] == "27": col=0
                        elif k[4] == "36": col=1
                        elif k[4] == "45": col=2
                        elif k[4] == "49": col=3
                    elif k[2]=="0.80":
                        if k[4] == "28": col=0
                        elif k[4] == "38": col=1
                        elif k[4] == "51": col=2
                        elif k[4] == "56": col=3
            comm_flag   = comm_dict_park.get(k)
            uncomm_flag = uncomm_dict_park.get(k)
            flag = []
            for i in range(len(comm_flag)):
                flag.append(comm_flag[i]-uncomm_flag[i])
            if k[2]=="0.56": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[0]),lw=6)
            elif k[2]=="0.68": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[0]),lw=6,ls="--")
            elif k[2]=="0.80": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[0]),lw=6,ls=":")
        for k in comm_dict_adam.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            comm_flag   = comm_dict_adam.get(k)
            uncomm_flag = uncomm_dict_adam.get(k)
            flag = []
            for i in range(len(comm_flag)):
                flag.append(comm_flag[i]-uncomm_flag[i])
            if k[2]=="0.56": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[3]),lw=6)
            elif k[2]=="0.68": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[3]),lw=6,ls="--")
            elif k[2]=="0.80": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[3]),lw=6,ls=":")
        for k in comm_dict_our.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            comm_flag   = comm_dict_our.get(k)
            uncomm_flag = uncomm_dict_our.get(k)
            flag = []
            for i in range(len(comm_flag)):
                flag.append(comm_flag[i]-uncomm_flag[i])
            if k[2]=="0.56": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[6]),lw=6)
            elif k[2]=="0.68": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[6]),lw=6,ls="--")
            elif k[2]=="0.80": ax[row][col].plot(flag,color=scalarMap.to_rgba(typo[6]),lw=6,ls=":")
        for x in range(2):
            for y in range(4):
                ax[x][y].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,4):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(4):
            ax[2][y].set_xticks(np.arange(0,901,150),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
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
                ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/"+c_type+"_"+arena_type+"Arena_messages.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=6, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
##########################################################################################################
    def print_pos(self,c_type,square_data_in,rect_data_in):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5,6,7]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        square_dict_park,square_dict_adam,square_dict_our   = square_data_in[0], square_data_in[1], square_data_in[2]
        rect_dict_park,rect_dict_adam,rect_dict_our         = rect_data_in[0], rect_data_in[1], rect_data_in[2]
        red         = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        blue        = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        green       = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[6]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R')
        solid       = mlines.Line2D([], [], color="black", marker="None", linestyle="-", linewidth=10, label='large interface')
        dashed      = mlines.Line2D([], [], color="black", marker="None", linestyle="--", linewidth=10, label='small interface')
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r   = [red,blue,green]
        handles_l   = [solid,dashed]
        fig, ax     = plt.subplots(nrows=3, ncols=4,figsize=(36,20))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%150 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in square_dict_park.keys():
            row = 0
            col = 0
            if k[3]=="25":
                if k[0]=="0_500;0_500":
                    row=1
                    if k[2]=="0.56":
                        if k[4] == "13": col=0
                        elif k[4] == "15": col=1
                        elif k[4] == "18": col=2
                        elif k[4] == "19": col=3
                    elif k[2]=="0.68":
                        if k[4] == "14": col=0
                        elif k[4] == "16": col=1
                        elif k[4] == "19": col=2
                        elif k[4] == "20": col=3
                    elif k[2]=="0.80":
                        if k[4] == "15": col=0
                        elif k[4] == "18": col=1
                        elif k[4] == "20": col=2
                        elif k[4] == "22": col=3
                elif k[0]=="1_000;1_000":
                    row=0
                    if k[2]=="0.56":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "11": col=2
                        elif k[4] == "12": col=3
                    elif k[2]=="0.68":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "13": col=3
                    elif k[2]=="0.80":
                        if k[4] == "7": col=0
                        elif k[4] == "10": col=1
                        elif k[4] == "14": col=2
                        elif k[4] == "15": col=3
            elif k[3]=="100":
                if k[0]=="1_000;1_000":
                    row = 2
                    if k[2]=="0.56":
                        if k[4] == "28": col=0
                        elif k[4] == "36": col=1
                        elif k[4] == "45": col=2
                        elif k[4] == "49": col=3
                    elif k[2]=="0.68":
                        if k[4] == "29": col=0
                        elif k[4] == "38": col=1
                        elif k[4] == "48": col=2
                        elif k[4] == "53": col=3
                    elif k[2]=="0.80":
                        if k[4] == "31": col=0
                        elif k[4] == "42": col=1
                        elif k[4] == "56": col=2
                        elif k[4] == "62": col=3
            elif k[2]=="0.80": ax[row][col].plot(square_dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6,ls="-")
        for k in rect_dict_park.keys():
            row = 0
            col = 0
            if k[3]=="25":
                if k[0]=="1_000;0_250":
                    row=1
                    if k[2]=="0.56":
                        if k[4] == "10": col=0
                        elif k[4] == "11": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "13": col=3
                    elif k[2]=="0.68":
                        if k[4] == "11": col=0
                        elif k[4] == "12": col=1
                        elif k[4] == "14": col=2
                        elif k[4] == "14_01": col=3
                    elif k[2]=="0.80":
                        if k[4] == "13": col=0
                        elif k[4] == "15": col=1
                        elif k[4] == "16": col=2
                        elif k[4] == "17": col=3
                elif k[0]=="2_000;0_500":
                    row=0
                    if k[2]=="0.56":
                        if k[4] == "6": col=0
                        elif k[4] == "8": col=1
                        elif k[4] == "10": col=2
                        elif k[4] == "11": col=3
                    elif k[2]=="0.68":
                        if k[4] == "6": col=0
                        elif k[4] == "8": col=1
                        elif k[4] == "11": col=2
                        elif k[4] == "12": col=3
                    elif k[2]=="0.80":
                        if k[4] == "7": col=0
                        elif k[4] == "9": col=1
                        elif k[4] == "12": col=2
                        elif k[4] == "14": col=3
            elif k[3]=="100":
                if k[0]=="2_000;0_500":
                    row = 2
                    if k[2]=="0.56":
                        if k[4] == "27": col=0
                        elif k[4] == "34": col=1
                        elif k[4] == "42": col=2
                        elif k[4] == "45": col=3
                    elif k[2]=="0.68":
                        if k[4] == "27": col=0
                        elif k[4] == "36": col=1
                        elif k[4] == "45": col=2
                        elif k[4] == "49": col=3
                    elif k[2]=="0.80":
                        if k[4] == "28": col=0
                        elif k[4] == "38": col=1
                        elif k[4] == "51": col=2
                        elif k[4] == "56": col=3
            elif k[2]=="0.80": ax[row][col].plot(rect_dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6,ls="--")
        for k in square_dict_adam.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            if k[2]=="0.80": ax[row][col].plot(square_dict_adam.get(k),color=scalarMap.to_rgba(typo[3]),lw=6,ls="-")
        for k in rect_dict_adam.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            if k[2]=="0.80": ax[row][col].plot(rect_dict_adam.get(k),color=scalarMap.to_rgba(typo[3]),lw=6,ls="--")
        for k in square_dict_our.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            if k[2]=="0.80": ax[row][col].plot(square_dict_our.get(k),color=scalarMap.to_rgba(typo[6]),lw=6,ls="-")
        for k in rect_dict_our.keys():
            row = 0
            col = 0
            if (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='25':
                row = 0
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="1_000;1_000" or k[0]=="2_000;0_500") and k[3]=='100':
                row = 2
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            elif (k[0]=="0_500;0_500" or k[0]=="1_000;0_250"):
                row = 1
                if k[4] == '60':
                    col = 0
                elif k[4] == '120':
                    col = 1
                elif k[4] == '300':
                    col = 2
                elif k[4] == '600':
                    col = 3
            if k[2]=="0.80": ax[row][col].plot(rect_dict_our.get(k),color=scalarMap.to_rgba(typo[6]),lw=6,ls="--")
        for x in range(2):
            for y in range(4):
                ax[x][y].set_xticks(np.arange(0,901,150),labels=svoid_x_ticks)
                ax[x][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
        for x in range(3):
            for y in range(1,4):
                labels = [item.get_text() for item in ax[x][y].get_yticklabels()]
                empty_string_labels = ['']*len(labels)
                ax[x][y].set_yticklabels(empty_string_labels)
        for y in range(4):
            ax[2][y].set_xticks(np.arange(0,901,150),labels=real_x_ticks)
            ax[2][y].set_xticks(np.arange(0,901,50),labels=void_x_ticks,minor=True)
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
        ax[0][0].set_ylabel(r"$D\, (m)$")
        ax[1][0].set_ylabel(r"$D\, (m)$")
        ax[2][0].set_ylabel(r"$D\, (m)$")
        ax[2][0].set_xlabel(r"$T\, (s)$")
        ax[2][1].set_xlabel(r"$T\, (s)$")
        ax[2][2].set_xlabel(r"$T\, (s)$")
        ax[2][3].set_xlabel(r"$T\, (s)$")
        for x in range(3):
            for y in range(4):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,900)
                ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/pos_data/images/"):
            os.mkdir(self.base+"/pos_data/images/")
        fig_path = self.base+"/pos_data/images/"+c_type+".pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_l,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
##########################################################################################################
    def extract_median(self,array,max_time):
        mt = int(max_time)
        median = max_time
        sortd_arr = np.sort(array)
        if len(sortd_arr)%2 == 0 and sortd_arr[(len(sortd_arr)//2)]!=mt:
            median = (sortd_arr[(len(sortd_arr)//2) -1] + sortd_arr[(len(sortd_arr)//2)]) * .5
        else:
            if sortd_arr[math.ceil(len(sortd_arr)/2)]!=mt: median = sortd_arr[math.floor(len(sortd_arr)/2)]
        return median