import numpy as np
import os, csv, math
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from lifelines import WeibullFitter
from scipy.special import gamma
class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "msgs_data" or elem == "proc_data" or elem == "rec_data":
                self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def wb_get_mean_and_std(self, wf:WeibullFitter):
        # get the Weibull shape and scale parameter 
        scale, shape = wf.summary.loc['lambda_','coef'], wf.summary.loc['rho_','coef']

        # calculate the mean time
        mean = scale*gamma(1 + 1/shape)
        # calculate the standard deviation
        variance = (scale ** 2) * (gamma(1 + 2 / shape) - (gamma(1 + 1 / shape)) ** 2)
        std = np.sqrt(variance)
        
        return [mean, std]
    
##########################################################################################################
    def fit_recovery(self,algo,n_agents,buf_dim,data_in):
        buff_starts     = data_in[0]
        durations       = data_in[1]
        event_observed  = data_in[2]

        durations_by_buffer = self.divide_event_by_buffer(buf_dim,algo,n_agents,buff_starts,durations,event_observed)
        durations_by_buffer = self.sort_arrays_in_dict(durations_by_buffer)
        adapted_durations = self.adapt_dict_to_weibull_est(durations_by_buffer)
        wf = WeibullFitter()
        estimates = {}
        for k in adapted_durations.keys():
            a_data = adapted_durations.get(k)[0]
            a_censoring = adapted_durations.get(k)[1]
            if len(a_data)>10:
                wf.fit(a_data, event_observed=a_censoring,label="wf "+k)
                estimates.update({k:self.wb_get_mean_and_std(wf)})
        return estimates

##########################################################################################################
    def fit_recovery_raw_data(self,data_in):
        fitted_data = {}
        for i in range(len(data_in)):
            for k in data_in[i].keys():
                estimates = self.fit_recovery(k[0],k[4],k[5],data_in[i].get(k))
                for z in estimates.keys():
                    fitted_data.update({(k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7],k[8],z):estimates.get(z)})
        return fitted_data
    
##########################################################################################################
    def divide_event_by_buffer(self,limit_buf,algo,n_agents,buffer,durations,event_observed):
        max_dim = float(n_agents) - 1
        if algo=='P': max_dim = float(limit_buf)
        durations_by_buffer = {"33": [[], []], "66": [[], []], "100": [[], []]}
        for i in range(len(buffer)):
            dimension = float(buffer[i])
            if dimension<=max_dim*0.33:
                tmp = durations_by_buffer.get("33")
                tmp[0].append(durations[i])
                tmp[1].append(event_observed[i])
                durations_by_buffer.update({"33":tmp})
            elif dimension>max_dim*0.33 and dimension<=max_dim*0.66:
                tmp = durations_by_buffer.get("66")
                tmp[0].append(durations[i])
                tmp[1].append(event_observed[i])
                durations_by_buffer.update({"66":tmp})
            elif dimension>max_dim*0.66:
                tmp = durations_by_buffer.get("100")
                tmp[0].append(durations[i])
                tmp[1].append(event_observed[i])
                durations_by_buffer.update({"100":tmp})
        return durations_by_buffer

##########################################################################################################
    def adapt_dict_to_weibull_est(self,data):
        out = {}
        for k in data.keys():
            durations = data.get(k)[0]
            event_observed = data.get(k)[1]
            if len(durations)>0:
                if durations[0] > 0: durations,event_observed = np.insert(durations,0,0),np.insert(event_observed,0,0)
                durations = list(durations)
                event_observed = list(event_observed)
                for i in range(len(durations)):
                    if durations[i] == 0: durations[i] = .00000001
            out.update({k:[durations,event_observed]})
        return out
    
##########################################################################################################
    def sort_arrays_in_dict(self,data_to_sort):
        out = {}
        for k in data_to_sort.keys():
            durations = data_to_sort.get(k)[0]
            event_obseerved = data_to_sort.get(k)[1]
            for i in range(len(durations)):
                for j in range(len(durations)):
                    if durations[j]<durations[i] and i<j:
                        tmp = durations[i]
                        durations[i] = durations[j]
                        durations[j] = tmp
                        tmp = event_obseerved[i]
                        event_obseerved[i] = event_obseerved[j]
                        event_obseerved[j] = tmp
            out.update({k:[durations,event_obseerved]})
        return out

##########################################################################################################
    def plot_messages(self,data):
        dict_park, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{}
        for k in data.keys():
            if k[1]=='P':
                dict_park.update({(k[0],k[3],k[4]):data.get(k)})
            else:
                if k[2]=="0":
                    dict_adam.update({(k[0],k[3],k[4]):data.get(k)})
                elif k[2]=="2":
                    dict_fifo.update({(k[0],k[3],k[4]):data.get(k)})
                else:
                    if k[5] == "1":
                        dict_rnd.update({(k[0],k[3],k[4]):data.get(k)})
                    else:
                        dict_rnd_inf.update({(k[0],k[3],k[4]):data.get(k)})
        self.print_messages([dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf])

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
                                data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
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
    def read_recovery_csv(self,path,algo,arena): # fix similar to read csv but with 3 arrays as last values
        keys = []
        data = {}
        lc = 0
        with open(path,newline='\n',) as f:
            reader = csv.reader(f)
            for row in reader:
                change = 0
                if lc == 0:
                    lc = 1
                    for val in row:
                        keys=val.split('\t')
                else:
                    buffer_start_dim,durations,event_observed = [],[],[]
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
                            if change==0:
                                buffer_start_dim.append(int(tval))
                            elif change == 1:
                                durations.append(int(tval))
                            else:
                                event_observed.append(int(tval))
                            if ']' in val:
                                data_val.update({keys[-3]:buffer_start_dim})
                                data_val.update({keys[-2]:durations})
                                data_val.update({keys[-1]:event_observed})
                                data.update({(algo,arena,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6])):(data_val.get(keys[7]),data_val.get(keys[8]),data_val.get(keys[9]))})
                        elif len(split_val)==2:
                            lval = ""
                            rval = ""
                            for c in split_val[0]:
                                if c != ']':
                                    lval += c
                            for c in split_val[1]:
                                if c != '[':
                                    rval += c
                            if change == 0:
                                change = 1
                                buffer_start_dim.append(int(lval))
                                durations.append(int(rval))
                            elif change == 1:
                                change = 2
                                durations.append(int(lval))
                                event_observed.append(int(rval))
                        else:
                            for k in range(len(split_val)):
                                tval = split_val[k]
                                if '[' in split_val[k]:
                                    tval = ''
                                    for c in split_val[k]:
                                        if c != '[' and c != ']':
                                            tval+=c
                                    if change==0:
                                        if ']' in split_val[k]:
                                            change = 1
                                        buffer_start_dim.append(int(tval))
                                    elif change == 1:
                                        if ']' in split_val[k]:
                                            change = 2
                                        durations.append(int(tval))
                                    else:
                                        event_observed.append(int(tval))
                                else:
                                    data_val.update({keys[k]:tval})
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
    def read_fitted_recovery_csv(self,file_path:str) -> dict:
        data = {}
        with open(file_path, newline='') as f:
            reader = csv.reader(f)
            next(reader)  # Skip the header row
            for row in reader:
                key = tuple(row[:10])
                value = tuple(row[10:])
                data[key] = value
        return data


##########################################################################################################
    def plot_recovery(self,data_in):
        if not os.path.exists(self.base+"/rec_data/images/"):
            os.mkdir(self.base+"/rec_data/images/")
        path = self.base+"/rec_data/images/"
        dict_park, dict_adms, dict_fifo, dict_rnd, dict_rnd_inf = {},{},{},{},{}
        ground_T, threshlds, msg_hops, jolly                    = [],[],[],[]
        algo, arena, time, comm, agents, buf_dim                = [],[],[],[],[],[]
        p_k, o_k                                                = [],[]
        da_K = data_in.keys()
        for k0 in da_K:
            if k0[0] not in algo: algo.append(k0[0])
            if k0[1] not in arena: arena.append(k0[1])
            if k0[2] not in time: time.append(k0[2])
            if k0[3] not in comm: comm.append(k0[3])
            if k0[4] not in agents: agents.append(k0[4])
            if k0[5] not in buf_dim: buf_dim.append(k0[5])
            if k0[6] not in msg_hops: msg_hops.append(k0[6])
            if k0[7] not in ground_T: ground_T.append(k0[7])
            if k0[8] not in threshlds: threshlds.append(k0[8])
            if k0[9] not in jolly: jolly.append(k0[9])
        for a in algo:
            for a_s in arena:
                for et in time:
                    for c in comm:
                        for m_h in msg_hops:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for gt in ground_T:
                                        for jl in jolly:
                                            tmp = []
                                            for thr in threshlds:
                                                s_data = data_in.get((a,a_s,et,c,n_a,m_b_d,m_h,gt,thr,jl))
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
                                                    dict_park.update({(a_s,n_a,m_b_d,gt,jl):tmp})
                                            if a=='O' and m_b_d in o_k:
                                                if len(tmp)>0:
                                                    if int(c)==0:
                                                        dict_adms.update({(a_s,n_a,m_b_d,gt,jl):tmp})
                                                    elif int(c)==2:
                                                        dict_fifo.update({(a_s,n_a,m_b_d,gt,jl):tmp})
                                                    else:
                                                        if int(m_h)==1:
                                                            dict_rnd.update({(a_s,n_a,m_b_d,gt,jl):tmp})
                                                        else:
                                                            dict_rnd_inf.update({(a_s,n_a,m_b_d,gt,jl):tmp})
        self.print_box_recovery_by_gt(path,[dict_park,dict_adms,dict_fifo,dict_rnd,dict_rnd_inf],'recovery_box_gt.pdf',[ground_T,threshlds],[buf_dim,jolly],[arena,agents])

##########################################################################################################
    def store_recovery(self,data_in):
        if not os.path.exists(self.base+"/rec_data/"):
            os.mkdir(self.base+"/rec_data/")
        path = self.base+"/rec_data/"
        ground_T, threshlds, msg_hops, jolly        = [],[],[],[]
        algo, arena, time, comm, agents, buf_dim    = [],[],[],[],[],[]
        da_K = data_in.keys()
        for k0 in da_K:
            if k0[0] not in algo: algo.append(k0[0])
            if k0[1] not in arena: arena.append(k0[1])
            if k0[2] not in time: time.append(k0[2])
            if k0[3] not in comm: comm.append(k0[3])
            if k0[4] not in agents: agents.append(k0[4])
            if k0[5] not in buf_dim: buf_dim.append(k0[5])
            if k0[6] not in msg_hops: msg_hops.append(k0[6])
            if k0[7] not in ground_T: ground_T.append(k0[7])
            if k0[8] not in threshlds: threshlds.append(k0[8])
            if k0[9] not in jolly: jolly.append(k0[9])
        for a in algo:
            for a_s in arena:
                for et in time:
                    for c in comm:
                        for m_h in msg_hops:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for gt in ground_T:
                                        for jl in jolly:
                                            for thr in threshlds:
                                                s_data = data_in.get((a,a_s,et,c,n_a,m_b_d,m_h,gt,thr,jl))
                                                if s_data != None:
                                                    with open(path + 'recovery_data.csv', mode='a', newline='\n') as file:
                                                        writer = csv.writer(file)
                                                        if file.tell() == 0:
                                                            writer.writerow(['Algorithm', 'Arena', 'Time', 'Broadcast', 'Agents', 'Buffer_Dim', 'Msg_Hops', 'Ground_T', 'Threshold', 'Buffer_Perc', 'Mean', 'Std'])
                                                        writer.writerow([a, a_s, et, c, n_a, m_b_d, m_h, gt, thr, jl, s_data[0], s_data[1]])

##########################################################################################################
    def print_box_recovery_by_gt(self,save_path,data,filename,gt_thr,buf_dims,aa):
        plt.rcParams.update({"font.size":40})
        cm                  = plt.get_cmap('viridis') 
        typo                = [0,1,2,3,4,5]
        cNorm               = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap           = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        anonymous           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad_fifo     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R fifo')
        id_rebroad_rnd      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R rnd')
        id_rebroad_rnd_inf  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R rnd inf')
        handles_r           = [anonymous,id_broad,id_rebroad_fifo,id_rebroad_rnd,id_rebroad_rnd_inf]
        colors_box          = [scalarMap.to_rgba(typo[0]),scalarMap.to_rgba(typo[1]),scalarMap.to_rgba(typo[2]),scalarMap.to_rgba(typo[3]),scalarMap.to_rgba(typo[4])]
        dict_park, dict_adms, dict_fifo, dict_rnd, dict_rnd_inf = data[0], data[1], data[2], data[3], data[4]
        park_plotting       = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        adam_plotting       = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        fifo_plotting       = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        rnd_plotting        = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
        rnd_inf_plotting    = np.array([[[[-1]*len(buf_dims[1])*len(gt_thr[1])]*len(gt_thr[0])]*5]*3)
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
                            park_data       = np.array(dict_park.get((a_s,n_a,m_b_d,gt_thr[0][gt],buf_dims[1][m_t])))
                            adams_data      = np.array(dict_adms.get((a_s,n_a,m_b_d,gt_thr[0][gt],buf_dims[1][m_t])))
                            fifo_data       = np.array(dict_fifo.get((a_s,n_a,m_b_d,gt_thr[0][gt],buf_dims[1][m_t])))
                            rnd_data        = np.array(dict_rnd.get((a_s,n_a,m_b_d,gt_thr[0][gt],buf_dims[1][m_t])))
                            rnd_inf_data    = np.array(dict_rnd_inf.get((a_s,n_a,m_b_d,gt_thr[0][gt],buf_dims[1][m_t])))
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
                                    park_plotting[row][col][gt][i] =  park_data[i]
                            if adams_data.any() != None:
                                for i in range(len(adams_data)):
                                    adam_plotting[row][col][gt][i] =  adams_data[i]
                            if fifo_data.any() != None:
                                for i in range(len(fifo_data)):
                                    fifo_plotting[row][col][gt][i] =  fifo_data[i]
                            if rnd_data.any() != None:
                                for i in range(len(rnd_data)):
                                    rnd_plotting[row][col][gt][i] =  rnd_data[i]
                            if rnd_inf_data.any() != None:
                                for i in range(len(rnd_inf_data)):
                                    rnd_inf_plotting[row][col][gt][i] =  rnd_inf_data[i]
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
                fifo = fifo_plotting[i][j]
                fifo_print = [[-1]]*len(gt_thr[0])
                for k in range(len(fifo)):
                    flag = []
                    for z in range(len(fifo[k])):
                        if fifo[k][z]!=-1:
                            flag.append(fifo[k][z])
                    fifo_print[k] = flag
                rnd = rnd_plotting[i][j]
                rnd_print = [[-1]]*len(gt_thr[0])
                for k in range(len(rnd)):
                    flag = []
                    for z in range(len(rnd[k])):
                        if rnd[k][z]!=-1:
                            flag.append(rnd[k][z])
                    rnd_print[k] = flag
                rnd_inf = rnd_inf_plotting[i][j]
                rnd_inf_print = [[-1]]*len(gt_thr[0])
                for k in range(len(rnd_inf)):
                    flag = []
                    for z in range(len(rnd_inf[k])):
                        if rnd_inf[k][z]!=-1:
                            flag.append(rnd_inf[k][z])
                    rnd_inf_print[k] = flag
                bpp     = ax[i][j].boxplot(park_print,positions=positions,widths=0.5,patch_artist=True)
                bpa     = ax[i][j].boxplot(adam_print,positions=[p+1 for p in positions],widths=0.5,patch_artist=True)
                bpf     = ax[i][j].boxplot(fifo_print,positions=[p+2 for p in positions],widths=0.5,patch_artist=True)
                bpr     = ax[i][j].boxplot(rnd_print,positions=[p+3 for p in positions],widths=0.5,patch_artist=True)
                bpri    = ax[i][j].boxplot(rnd_inf_print,positions=[p+4 for p in positions],widths=0.5,patch_artist=True)
                for bplot, color in zip((bpp, bpa, bpf, bpr, bpri), colors_box):
                    for patch in bplot['boxes']:
                        patch.set_facecolor(color)
                ax[i][j].set_xticks([p + 1 for p in positions])
                ax[i][j].set_xticklabels(gt_thr[0])
                ax[i][j].set_ylim(0,901)
        fig.tight_layout()
        fig_path = save_path+filename
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
        return

##########################################################################################################
    def plot_buffer_opts(self,no_actions,insertions,updates):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd   = {},{},{}
        dict_rnd_inf_no_act_fr,dict_rnd_inf_ins_fr,dict_rnd_inf_upd_fr   = {},{},{}
        jolly, msg_hop                      = [],[]
        algo,arena,runs,time,comm,agents    = [],[],[],[],[],[]
        for i in range(len(no_actions)):
            da_K = no_actions[i].keys()
            for k0 in da_K:
                if k0[0]not in algo: algo.append(k0[0])
                if k0[1]not in arena: arena.append(k0[1])
                if k0[2]not in runs: runs.append(k0[2])
                if k0[3]not in time: time.append(k0[3])
                if k0[4]not in comm: comm.append(k0[4])
                if k0[5]not in agents: agents.append(k0[5])
                if k0[9]not in jolly: jolly.append(k0[9])
                if k0[10]not in msg_hop: msg_hop.append(k0[10])
        for i in range(len(no_actions)):
            for a in ('O'):
                for a_s in arena:
                    for n_r in runs:
                        for et in time:
                            for c in comm:
                                for n_a in agents:
                                    for m_t in jolly:
                                        for m_h in msg_hop:
                                            n_data = no_actions[i].get((a,a_s,n_r,et,c,n_a,'-','-','-',m_t,m_h))
                                            if n_data != None and c=="1" and m_h=="0":
                                                n_data = n_data[0]
                                                i_data = insertions[i].get((a,a_s,n_r,et,c,n_a,'-','-','-',m_t,m_h))[0]
                                                u_data = updates[i].get((a,a_s,n_r,et,c,n_a,'-','-','-',m_t,m_h))[0]
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

        self.print_buff_opts(path,[dict_rnd_inf_no_act,dict_rnd_inf_ins,dict_rnd_inf_upd],"buff_sum_opts.pdf",500)
        self.print_buff_opts(path,[dict_rnd_inf_no_act_fr,dict_rnd_inf_ins_fr,dict_rnd_inf_upd_fr],"buff_step_opts.pdf",7.5)
    
        return

##########################################################################################################
    def plot_active(self,data_in,times):
        if not os.path.exists(self.base+"/proc_data/images/"):
            os.mkdir(self.base+"/proc_data/images/")
        path = self.base+"/proc_data/images/"
        dict_park_avg,dict_adms_avg,dict_fifo_avg,dict_rnd_avg,dict_rnd_inf_avg         = {},{},{},{},{}
        dict_park_tmed,dict_adms_tmed,dict_fifo_tmed,dict_rnd_tmed,dict_rnd_inf_tmed    = {},{},{},{},{}
        ground_T, threshlds , jolly, msg_hop        = [],[],[],[]
        algo,arena,runs,time,comm,agents,buf_dim    = [],[],[],[],[],[],[]
        p_k,o_k                                     = [],[]
        for i in range(len(data_in)):
            da_K = data_in[i].keys()
            for k0 in da_K:
                if k0[0]not in algo: algo.append(k0[0])
                if k0[1]not in arena: arena.append(k0[1])
                if k0[2]not in runs: runs.append(k0[2])
                if k0[3]not in time: time.append(k0[3])
                if k0[4]not in comm: comm.append(k0[4])
                if k0[5]not in agents: agents.append(k0[5])
                if float(k0[6]) not in ground_T: ground_T.append(float(k0[6]))
                if float(k0[7]) not in threshlds: threshlds.append(float(k0[7]))
                if k0[8]not in buf_dim: buf_dim.append(k0[8])
                if k0[9]not in jolly: jolly.append(k0[9])
                if k0[10]not in msg_hop: msg_hop.append(k0[10])
        for i in range(len(data_in)):
            for a in algo:
                for a_s in arena:
                    for n_r in runs:
                        for et in time:
                            for c in comm:
                                for n_a in agents:
                                    for m_b_d in buf_dim:
                                        for m_t in jolly:
                                            for m_h in msg_hop:
                                                vals            = []
                                                times_median    = []
                                                for gt in ground_T:
                                                    tmp         = []
                                                    tmp_tmed    = []
                                                    for thr in threshlds:
                                                        s_data = data_in[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h))
                                                        t_data = times[i].get((a,a_s,n_r,et,c,n_a,str(gt),str(thr),m_b_d,m_t,m_h))
                                                        if s_data != None:
                                                            if (a=='P' and m_t not in p_k) or (a=='O' and m_t not in o_k):
                                                                p_k.append(m_t) if (a=='P') else o_k.append(m_t)
                                                            tmp.append(round(self.extract_median(s_data[0],len(s_data[0])),2))
                                                            tmp_tmed.append(round(self.extract_median(t_data[0],len(s_data[0])),2))
                                                    if len(vals)==0:
                                                        vals            = np.array([tmp])
                                                        times_median    = np.array([tmp_tmed])
                                                    else:
                                                        vals            = np.append(vals,[tmp],axis=0)
                                                        times_median    = np.append(times_median,[tmp_tmed],axis=0)
                                                if a=='P' and int(c)==0 and m_t in p_k:
                                                    if len(vals[0])>0 and ((a_s=='bigA' and ((n_a=='25' and (m_t=='11' or m_t=='15' or m_t=='17' or m_t=='19' or m_t=='21')) or 
                                                                                            (n_a=='100' and (m_t=='41' or m_t=='56' or m_t=='65' or m_t=='74' or m_t=='83')))) or 
                                                                                            (a_s=='smallA' and (n_a=='25' and (m_t=='19' or m_t=='22' or m_t=='23' or m_t=='23.01' or m_t=='24')))):
                                                        dict_park_avg.update({(a_s,n_a,m_t):vals})
                                                        dict_park_tmed.update({(a_s,n_a,m_t):times_median})
                                                if a=='O' and m_t in o_k:
                                                    if len(vals[0])>0:
                                                        if int(c)==0:
                                                            dict_adms_avg.update({(a_s,n_a,m_t):vals})
                                                            dict_adms_tmed.update({(a_s,n_a,m_t):times_median})
                                                        elif int(c)==2:
                                                            dict_fifo_avg.update({(a_s,n_a,m_t):vals})
                                                            dict_fifo_tmed.update({(a_s,n_a,m_t):times_median})
                                                        else:
                                                            if int(m_h)==1:
                                                                dict_rnd_avg.update({(a_s,n_a,m_t):vals})
                                                                dict_rnd_tmed.update({(a_s,n_a,m_t):times_median})
                                                            else:
                                                                dict_rnd_inf_avg.update({(a_s,n_a,m_t):vals})
                                                                dict_rnd_inf_tmed.update({(a_s,n_a,m_t):times_median})
        self.print_borders(path,'avg','median',ground_T,threshlds,[dict_park_avg,dict_adms_avg,dict_fifo_avg,dict_rnd_avg,dict_rnd_inf_avg],[dict_park_tmed,dict_adms_tmed,dict_fifo_tmed,dict_rnd_tmed,dict_rnd_inf_tmed],[p_k,o_k],[arena,agents])
        
##########################################################################################################
    def print_messages(self,data_in):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo, dict_rnd, dict_rnd_inf = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4]
        anonymous           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad_fifo     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R fifo')
        id_rebroad_rnd      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R rnd')
        id_rebroad_rnd_inf  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R rnd inf')
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        
        handles_r   = [anonymous,id_broad,id_rebroad_fifo,id_rebroad_rnd,id_rebroad_rnd_inf]
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
        for k in dict_fifo.keys():
            tmp =[]
            res = dict_fifo.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_fifo.update({k:tmp})
        for k in dict_rnd.keys():
            tmp =[]
            res = dict_rnd.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd.update({k:tmp})
        for k in dict_rnd_inf.keys():
            tmp =[]
            res = dict_rnd_inf.get(k)
            norm = int(k[1])-1
            for xi in res:
                tmp.append(xi/norm)
            dict_rnd_inf.update({k:tmp})
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
            elif k[0]=='big' and k[1]=='100':
                row = 2
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
            ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[1]),lw=6)
        for k in dict_fifo.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
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
            ax[row][col].plot(dict_fifo.get(k),color=scalarMap.to_rgba(typo[2]),lw=6)
        for k in dict_rnd.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
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
            ax[row][col].plot(dict_rnd.get(k),color=scalarMap.to_rgba(typo[3]),lw=6)
        for k in dict_rnd_inf.keys():
            row = 0
            col = 0
            if k[0]=='big' and k[1]=='25':
                row = 0
            elif k[0]=='big' and k[1]=='100':
                row = 2
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
            ax[row][col].plot(dict_rnd_inf.get(k),color=scalarMap.to_rgba(typo[4]),lw=6)
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
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)

##########################################################################################################
    def print_buff_opts(self,path,data_in,fig_name,y_lim):
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
        fig, ax     = plt.subplots(nrows=3, ncols=5,figsize=(28,18))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
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
            elif k[2] == '120':
                col = 1
            elif k[2] == '180':
                col = 2
            elif k[2] == '300':
                col = 3
            elif k[2] == '600':
                col = 4
            ax[row][col].plot(dict_no_act.get(k),color=scalarMap.to_rgba(typo[0]),lw=3)
            ax[row][col].plot(dict_ins.get(k),color=scalarMap.to_rgba(typo[1]),lw=3)
            ax[row][col].plot(dict_upd.get(k),color=scalarMap.to_rgba(typo[2]),lw=3)
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
        ax[0][0].set_ylabel("#")
        ax[1][0].set_ylabel("#")
        ax[2][0].set_ylabel("#")
        ax[2][0].set_xlabel(r"$T\, (s)$")
        ax[2][1].set_xlabel(r"$T\, (s)$")
        ax[2][2].set_xlabel(r"$T\, (s)$")
        ax[2][3].set_xlabel(r"$T\, (s)$")
        ax[2][4].set_xlabel(r"$T\, (s)$")
        for x in range(3):
            for y in range(5):
                ax[x][y].grid(True)
                ax[x][y].set_xlim(0,900)
                ax[x][y].set_ylim(0,y_lim)
        fig.tight_layout()
        fig_path = path+fig_name
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5, loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        plt.close(fig)
    
##########################################################################################################
    def print_borders(self,path,_type,t_type,ground_T,threshlds,data_in,times_in,keys,more_k):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4]
        tdict_park,tdict_adam,tdict_fifo,tdict_rnd,tdict_rnd_inf = times_in[0], times_in[1], times_in[2], times_in[3], times_in[4]
        p_k, po_k = keys[0],keys[1]
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = np.sort(o_k)
        arena = more_k[0]
        vals8p  = [[0]*len(threshlds)]*len(o_k)
        vals2p  = [[0]*len(threshlds)]*len(o_k)
        vals8a  = [[0]*len(threshlds)]*len(o_k)
        vals2a  = [[0]*len(threshlds)]*len(o_k)
        vals8f  = [[0]*len(threshlds)]*len(o_k)
        vals2f  = [[0]*len(threshlds)]*len(o_k)
        vals8r  = [[0]*len(threshlds)]*len(o_k)
        vals2r  = [[0]*len(threshlds)]*len(o_k)
        vals8ri = [[0]*len(threshlds)]*len(o_k)
        vals2ri = [[0]*len(threshlds)]*len(o_k)

        tvalsp  = [[0]*len(threshlds)]*len(o_k)
        tvalsa  = [[0]*len(threshlds)]*len(o_k)
        tvalsf  = [[0]*len(threshlds)]*len(o_k)
        tvalsr  = [[0]*len(threshlds)]*len(o_k)
        tvalsri = [[0]*len(threshlds)]*len(o_k)

        low_bound           = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label=r"$\hat{Q} = 0.2$")
        high_bound          = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label=r"$\hat{Q} = 0.8$")
        anonymous           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='Anonymous')
        id_broad            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+B')
        id_rebroad_fifo     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R fifo')
        id_rebroad_rnd      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R rnd')
        id_rebroad_rnd_inf  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label='ID+R rnd inf')

        handles_c   = [high_bound,low_bound]
        handles_r   = [anonymous,id_broad,id_rebroad_fifo,id_rebroad_rnd,id_rebroad_rnd_inf]
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
                        p_vals2,a_vals2,f_vals2,r_vals2,ri_vals2 = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_vals8,a_vals8,f_vals8,r_vals8,ri_vals8 = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt2,a_gt2,f_gt2,r_gt2,ri_gt2           = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt8,a_gt8,f_gt8,r_gt8,ri_gt8           = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_valst,a_valst,f_valst,r_valst,ri_valst = np.nan,np.nan,np.nan,np.nan,np.nan
                        for pt in range(len(ground_T)):
                            pval    = dict_park.get((a,ag,p_k[k]))[pt][th]
                            aval    = dict_adam.get((a,ag,str(o_k[k])))[pt][th]
                            fval    = dict_fifo.get((a,ag,str(o_k[k])))[pt][th]
                            rval    = dict_rnd.get((a,ag,str(o_k[k])))[pt][th]
                            rival   = dict_rnd_inf.get((a,ag,str(o_k[k])))[pt][th]
                            tpval   = tdict_park.get((a,ag,p_k[k]))[pt][th]
                            taval   = tdict_adam.get((a,ag,str(o_k[k])))[pt][th]
                            tfval   = tdict_fifo.get((a,ag,str(o_k[k])))[pt][th]
                            trval   = tdict_rnd.get((a,ag,str(o_k[k])))[pt][th]
                            trival  = tdict_rnd_inf.get((a,ag,str(o_k[k])))[pt][th]
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
                            if fval>=0.8:
                                if ground_T[pt]-threshlds[th] >=0.1 and ground_T[pt]-threshlds[th] <=0.2 and f_valst is np.nan:
                                    f_valst = np.log10(tfval)
                                if f_vals8[1] is np.nan or fval<f_vals8[1]:
                                    f_vals8[1]  = fval
                                    f_gt8[1]    = ground_T[pt]
                            elif fval<=0.2:
                                if f_vals2[0] is np.nan or fval>=f_vals2[0]:
                                    f_vals2[0]  = fval
                                    f_gt2[0]    = ground_T[pt]
                            else:
                                if f_vals8[0] is np.nan or fval>f_vals8[0]:
                                    f_vals8[0]  = fval
                                    f_gt8[0]    = ground_T[pt]
                                if f_vals2[1] is np.nan or fval<f_vals2[1]:
                                    f_vals2[1]  = fval
                                    f_gt2[1]    = ground_T[pt]
                            if rval>=0.8:
                                if ground_T[pt]-threshlds[th] >=0.1 and ground_T[pt]-threshlds[th] <=0.2 and r_valst is np.nan:
                                    r_valst = np.log10(trval)
                                if r_vals8[1] is np.nan or rval<r_vals8[1]:
                                    r_vals8[1]  = rval
                                    r_gt8[1]    = ground_T[pt]
                            elif rval<=0.2:
                                if r_vals2[0] is np.nan or rval>=r_vals2[0]:
                                    r_vals2[0]  = rval
                                    r_gt2[0]    = ground_T[pt]
                            else:
                                if r_vals8[0] is np.nan or rval>r_vals8[0]:
                                    r_vals8[0]  = rval
                                    r_gt8[0]    = ground_T[pt]
                                if r_vals2[1] is np.nan or rval<r_vals2[1]:
                                    r_vals2[1]  = rval
                                    r_gt2[1]    = ground_T[pt]
                            if rival>=0.8:
                                if ground_T[pt]-threshlds[th] >=0.1 and ground_T[pt]-threshlds[th] <=0.2 and ri_valst is np.nan:
                                    ri_valst = np.log10(trival)
                                if ri_vals8[1] is np.nan or rival<ri_vals8[1]:
                                    ri_vals8[1]  = rival
                                    ri_gt8[1]    = ground_T[pt]
                            elif rival<=0.2:
                                if ri_vals2[0] is np.nan or rival>=ri_vals2[0]:
                                    ri_vals2[0]  = rival
                                    ri_gt2[0]    = ground_T[pt]
                            else:
                                if ri_vals8[0] is np.nan or rival>ri_vals8[0]:
                                    ri_vals8[0]  = rival
                                    ri_gt8[0]    = ground_T[pt]
                                if ri_vals2[1] is np.nan or rival<ri_vals2[1]:
                                    ri_vals2[1]  = rival
                                    ri_gt2[1]    = ground_T[pt]
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
                        if f_vals8[0] is np.nan:
                            f_vals8[0] = f_vals8[1]
                            f_gt8[0] = f_gt8[1]
                        elif f_vals8[1] is np.nan:
                            f_vals8[1] = f_vals8[0]
                            f_gt8[1] = f_gt8[0]
                        if f_vals2[0] is np.nan:
                            f_vals2[0] = f_vals2[1]
                            f_gt2[0] = f_gt2[1]
                        elif f_vals2[1] is np.nan:
                            f_vals2[1] = f_vals2[0]
                            f_gt2[1] = f_gt2[0]
                        if r_vals8[0] is np.nan:
                            r_vals8[0] = r_vals8[1]
                            r_gt8[0] = r_gt8[1]
                        elif r_vals8[1] is np.nan:
                            r_vals8[1] = r_vals8[0]
                            r_gt8[1] = r_gt8[0]
                        if r_vals2[0] is np.nan:
                            r_vals2[0] = r_vals2[1]
                            r_gt2[0] = r_gt2[1]
                        elif r_vals2[1] is np.nan:
                            r_vals2[1] = r_vals2[0]
                            r_gt2[1] = r_gt2[0]
                        if ri_vals8[0] is np.nan:
                            ri_vals8[0] = ri_vals8[1]
                            ri_gt8[0] = ri_gt8[1]
                        elif ri_vals8[1] is np.nan:
                            ri_vals8[1] = ri_vals8[0]
                            ri_gt8[1] = ri_gt8[0]
                        if ri_vals2[0] is np.nan:
                            ri_vals2[0] = ri_vals2[1]
                            ri_gt2[0] = ri_gt2[1]
                        elif ri_vals2[1] is np.nan:
                            ri_vals2[1] = ri_vals2[0]
                            ri_gt2[1] = ri_gt2[0]

                        vals2p[k][th] = np.round(np.interp([0.2],p_vals2,p_gt2,left=np.nan)[0],3)
                        vals2a[k][th] = np.round(np.interp([0.2],a_vals2,a_gt2,left=np.nan)[0],3)
                        vals2f[k][th] = np.round(np.interp([0.2],f_vals2,f_gt2,left=np.nan)[0],3)
                        vals2r[k][th] = np.round(np.interp([0.2],r_vals2,r_gt2,left=np.nan)[0],3)
                        vals2ri[k][th] = np.round(np.interp([0.2],ri_vals2,ri_gt2,left=np.nan)[0],3)
                        vals8p[k][th] = np.round(np.interp([0.8],p_vals8,p_gt8,right=np.nan)[0],3)
                        vals8a[k][th] = np.round(np.interp([0.8],a_vals8,a_gt8,right=np.nan)[0],3) 
                        vals8f[k][th] = np.round(np.interp([0.8],f_vals8,f_gt8,right=np.nan)[0],3)
                        vals8r[k][th] = np.round(np.interp([0.8],r_vals8,r_gt8,right=np.nan)[0],3)
                        vals8ri[k][th] = np.round(np.interp([0.8],ri_vals8,ri_gt8,right=np.nan)[0],3)
                        tvalsp[k][th] = p_valst
                        tvalsa[k][th] = a_valst
                        tvalsf[k][th] = f_valst
                        tvalsr[k][th] = r_valst
                        tvalsri[k][th] = ri_valst
                    ax[row][k].plot(vals2p[k],color=scalarMap.to_rgba(typo[0]),lw=6,ls='--')
                    ax[row][k].plot(vals8p[k],color=scalarMap.to_rgba(typo[0]),lw=6,ls='-')
                    ax[row][k].plot(vals2a[k],color=scalarMap.to_rgba(typo[1]),lw=6,ls='--')
                    ax[row][k].plot(vals8a[k],color=scalarMap.to_rgba(typo[1]),lw=6,ls='-')
                    ax[row][k].plot(vals2f[k],color=scalarMap.to_rgba(typo[2]),lw=6,ls='--')
                    ax[row][k].plot(vals8f[k],color=scalarMap.to_rgba(typo[2]),lw=6,ls='-')
                    ax[row][k].plot(vals2r[k],color=scalarMap.to_rgba(typo[3]),lw=6,ls='--')
                    ax[row][k].plot(vals8r[k],color=scalarMap.to_rgba(typo[3]),lw=6,ls='-')
                    ax[row][k].plot(vals2ri[k],color=scalarMap.to_rgba(typo[4]),lw=6,ls='--')
                    ax[row][k].plot(vals8ri[k],color=scalarMap.to_rgba(typo[4]),lw=6,ls='-')
                    ax[row][k].plot(np.arange(0.5,1.01,0.01),color='black',lw=5,ls=':')
                    tax[row][k].plot(tvalsp[k],color=scalarMap.to_rgba(typo[0]),lw=6)
                    tax[row][k].plot(tvalsa[k],color=scalarMap.to_rgba(typo[1]),lw=6)
                    tax[row][k].plot(tvalsf[k],color=scalarMap.to_rgba(typo[2]),lw=6)
                    tax[row][k].plot(tvalsr[k],color=scalarMap.to_rgba(typo[3]),lw=6)
                    tax[row][k].plot(tvalsri[k],color=scalarMap.to_rgba(typo[4]),lw=6)
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
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_c,ncols=7, loc='upper right',framealpha=0.7,borderaxespad=0)
        tfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=5,loc='upper right',framealpha=0.7,borderaxespad=0)
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