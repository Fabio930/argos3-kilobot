import os, csv, math, logging
import numpy as np
import pandas as pd
import matplotlib.colors as colors
import matplotlib.cm as cmx
import matplotlib.lines as mlines
from matplotlib import pyplot as plt
from lifelines import WeibullFitter,KaplanMeierFitter
from scipy.special import gamma
from tsmoothie.smoother import *
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
class Data:

##########################################################################################################
    def __init__(self) -> None:
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if elem == "msgs_data" or elem == "proc_data" or elem == "rec_data" or elem=="diagnostics_states_chunks":
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
    def fit_recovery(self,algo,arena,n_agents,buf_dim,gt,thr,comunication,msg_hops,data_in):
        buff_starts     = data_in[0]
        durations       = data_in[1]
        event_observed  = data_in[2]
        if not os.path.exists(self.base+"/weib_images/"):
            os.mkdir(self.base+"/weib_images/")
        path = self.base+"/weib_images/"

        durations_by_buffer = self.dull_division(buff_starts,durations,event_observed)
        # durations_by_buffer = self.divide_event_by_buffer(buf_dim,buff_starts,durations,event_observed)
        durations_by_buffer = self.sort_arrays_in_dict(durations_by_buffer)
        adapted_durations = self.adapt_dict_to_weibull_est(durations_by_buffer)
        wf = WeibullFitter()
        kmf = KaplanMeierFitter()
        estimates = {}
        for k in adapted_durations.keys():
            a_data = adapted_durations.get(k)[0]
            a_censoring = adapted_durations.get(k)[1]
            if len(a_data)>100:
                wf.fit(a_data, event_observed=a_censoring,label="wf "+k)
                kmf.fit(a_data, event_observed=a_censoring,label="kmf "+k)
                fig, ax = plt.subplots(figsize=(10,8))
                ax.plot(wf.cumulative_density_)
                ax.plot(kmf.cumulative_density_)
                fig.tight_layout()
                fig.savefig(path+algo+'_'+comunication+'_'+msg_hops+'_'+n_agents+'_'+arena+'_'+buf_dim+'_'+gt+'_'+thr+'_'+k+'.png')
                estimates.update({k:[self.wb_get_mean_and_std(wf),len(durations_by_buffer.get(k)[1])]})
        return estimates

##########################################################################################################
    def fit_recovery_raw_data(self,data_in):
        fitted_data = {}
        for i in range(len(data_in)):
            for k in data_in[i].keys():
                estimates = self.fit_recovery(k[0],k[1],k[4],k[5],k[8],k[9],k[3],k[7],data_in[i].get(k))
                for z in estimates.keys():
                    fitted_data.update({(k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7],k[8],k[9],z):estimates.get(z)})
        return fitted_data
    
##########################################################################################################
    def dull_division(self,buffer,durations,event_observed):
        durations_by_buffer = {"all": [[], []]}
        for i in range(len(buffer)):
            tmp = durations_by_buffer.get("all")
            tmp[0].append(durations[i])
            tmp[1].append(event_observed[i])
            durations_by_buffer.update({"all":tmp})
        return durations_by_buffer
    
##########################################################################
    def divide_event_by_buffer(self,limit_buf,buffer,durations,event_observed):
        min_dim = 5
        max_dim = float(limit_buf)
        diff = max_dim - min_dim
        durations_by_buffer = {"33": [[], []], "66": [[], []], "100": [[], []]}
        for i in range(len(buffer)):
            dimension = float(buffer[i])
            if dimension<=diff*0.33 + min_dim:
                tmp = durations_by_buffer.get("33")
                tmp[0].append(durations[i])
                tmp[1].append(event_observed[i])
                durations_by_buffer.update({"33":tmp})
            elif dimension>diff*0.33 + min_dim and dimension<=diff*0.66 + min_dim:
                tmp = durations_by_buffer.get("66")
                tmp[0].append(durations[i])
                tmp[1].append(event_observed[i])
                durations_by_buffer.update({"66":tmp})
            elif dimension>diff*0.66 + min_dim:
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
            event_observed = data_to_sort.get(k)[1]
            for i in range(len(durations)):
                for j in range(len(durations)):
                    if durations[j]<durations[i] and i<j:
                        tmp = durations[i]
                        durations[i] = durations[j]
                        durations[j] = tmp
                        tmp = event_observed[i]
                        event_observed[i] = event_observed[j]
                        event_observed[j] = tmp
            out.update({k:[durations,event_observed]})
        return out

##########################################################################################################
    def plot_messages(self,data):
        dict_park, dict_park_real_fifo, dict_adam, dict_fifo,dict_rnd,dict_rnd_inf = {},{},{},{},{},{}
        for k in data.keys():
            if k[1]=='P':
                dict_park.update({(k[0],k[3],k[4]):data.get(k)})
            elif k[1]=='Pf':
                dict_park_real_fifo.update({(k[0],k[3],k[4]):data.get(k)})
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
        self.print_messages([dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_park_real_fifo])

##########################################################################################################
    def plot_messages_homogeneity(self,data):
        max_dict_park, max_dict_park_real_fifo, max_dict_adam, max_dict_fifo, max_dict_rnd, max_dict_rnd_inf = {},{},{},{},{},{}
        min_dict_park, min_dict_park_real_fifo, min_dict_adam, min_dict_fifo, min_dict_rnd, min_dict_rnd_inf = {},{},{},{},{},{}
        median_max_dict_park, median_max_dict_park_real_fifo, median_max_dict_adam, median_max_dict_fifo, median_max_dict_rnd, median_max_dict_rnd_inf = {},{},{},{},{},{}
        median_min_dict_park, median_min_dict_park_real_fifo, median_min_dict_adam, median_min_dict_fifo, median_min_dict_rnd, median_min_dict_rnd_inf = {},{},{},{},{},{}
        agents_dict_park, agents_dict_park_real_fifo, agents_dict_adam, agents_dict_fifo, agents_dict_rnd, agents_dict_rnd_inf = {},{},{},{},{},{}
        agents_90_dict_park, agents_90_dict_park_real_fifo, agents_90_dict_adam, agents_90_dict_fifo, agents_90_dict_rnd, agents_90_dict_rnd_inf = {},{},{},{},{},{}
        for k in data[0].keys():
            if k[1]=='P':
                max_dict_park.update({(k[0],k[3],k[4]):data[0].get(k)})
                min_dict_park.update({(k[0],k[3],k[4]):data[1].get(k)})
                median_max_dict_park.update({(k[0],k[3],k[4]):data[2].get(k)})
                median_min_dict_park.update({(k[0],k[3],k[4]):data[3].get(k)})
                agents_dict_park.update({(k[0],k[3],k[4]):data[4].get(k)})
                agents_90_dict_park.update({(k[0],k[3],k[4]):data[5].get(k)})
            elif k[1]=='Pf':
                max_dict_park_real_fifo.update({(k[0],k[3],k[4]):data[0].get(k)})
                min_dict_park_real_fifo.update({(k[0],k[3],k[4]):data[1].get(k)})
                median_max_dict_park_real_fifo.update({(k[0],k[3],k[4]):data[2].get(k)})
                median_min_dict_park_real_fifo.update({(k[0],k[3],k[4]):data[3].get(k)})
                agents_dict_park_real_fifo.update({(k[0],k[3],k[4]):data[4].get(k)})
                agents_90_dict_park_real_fifo.update({(k[0],k[3],k[4]):data[5].get(k)})
            else:
                if k[2]=="0":
                    max_dict_adam.update({(k[0],k[3],k[4]):data[0].get(k)})
                    min_dict_adam.update({(k[0],k[3],k[4]):data[1].get(k)})
                    median_max_dict_adam.update({(k[0],k[3],k[4]):data[2].get(k)})
                    median_min_dict_adam.update({(k[0],k[3],k[4]):data[3].get(k)})
                    agents_dict_adam.update({(k[0],k[3],k[4]):data[4].get(k)})
                    agents_90_dict_adam.update({(k[0],k[3],k[4]):data[5].get(k)})
                elif k[2]=="2":
                    max_dict_fifo.update({(k[0],k[3],k[4]):data[0].get(k)})
                    min_dict_fifo.update({(k[0],k[3],k[4]):data[1].get(k)})
                    median_max_dict_fifo.update({(k[0],k[3],k[4]):data[2].get(k)})
                    median_min_dict_fifo.update({(k[0],k[3],k[4]):data[3].get(k)})
                    agents_dict_fifo.update({(k[0],k[3],k[4]):data[4].get(k)})
                    agents_90_dict_fifo.update({(k[0],k[3],k[4]):data[5].get(k)})
                else:
                    if k[5] == "1":
                        max_dict_rnd.update({(k[0],k[3],k[4]):data[0].get(k)})
                        min_dict_rnd.update({(k[0],k[3],k[4]):data[1].get(k)})
                        median_max_dict_rnd.update({(k[0],k[3],k[4]):data[2].get(k)})
                        median_min_dict_rnd.update({(k[0],k[3],k[4]):data[3].get(k)})
                        agents_dict_rnd.update({(k[0],k[3],k[4]):data[4].get(k)})
                        agents_90_dict_rnd.update({(k[0],k[3],k[4]):data[5].get(k)})
                    else:
                        max_dict_rnd_inf.update({(k[0],k[3],k[4]):data[0].get(k)})
                        min_dict_rnd_inf.update({(k[0],k[3],k[4]):data[1].get(k)})
                        median_max_dict_rnd_inf.update({(k[0],k[3],k[4]):data[2].get(k)})
                        median_min_dict_rnd_inf.update({(k[0],k[3],k[4]):data[3].get(k)})
                        agents_dict_rnd_inf.update({(k[0],k[3],k[4]):data[4].get(k)})
                        agents_90_dict_rnd_inf.update({(k[0],k[3],k[4]):data[5].get(k)})
        self.print_messages_homogeneity([max_dict_park,max_dict_adam,max_dict_fifo,max_dict_rnd,max_dict_rnd_inf,max_dict_park_real_fifo],
                                        [min_dict_park, min_dict_park_real_fifo, min_dict_adam, min_dict_fifo, min_dict_rnd, min_dict_rnd_inf],
                                        [median_max_dict_park, median_max_dict_park_real_fifo, median_max_dict_adam, median_max_dict_fifo, median_max_dict_rnd, median_max_dict_rnd_inf],
                                        [median_min_dict_park, median_min_dict_park_real_fifo, median_min_dict_adam, median_min_dict_fifo, median_min_dict_rnd, median_min_dict_rnd_inf],
                                        [agents_dict_park, agents_dict_park_real_fifo, agents_dict_adam, agents_dict_fifo, agents_dict_rnd, agents_dict_rnd_inf],
                                        [agents_90_dict_park, agents_90_dict_park_real_fifo, agents_90_dict_adam, agents_90_dict_fifo, agents_90_dict_rnd, agents_90_dict_rnd_inf])

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
    def read_msgs_homogeneity_csv(self,path):
        max_data, min_data, median_max_data, median_min_data, agents, agents_90 = {},{},{},{},{},{}
        lc,data_type = 0,0
        with open(path,newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                if lc == 0: lc = 1
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
                                if data_type == 0:
                                    max_data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
                                    data_type = 1
                                elif data_type == 1:
                                    min_data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
                                    data_type = 2
                                elif data_type == 2:
                                    median_max_data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
                                    data_type = 3
                                elif data_type == 3:
                                    median_min_data.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
                                    data_type = 4
                                elif data_type == 4:
                                    agents.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
                                    data_type = 5
                                elif data_type == 5:
                                    agents_90.update({(keys[0],keys[1],keys[2],keys[3],keys[4],keys[5]):array_val})
                                    data_type = 0
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
        return max_data, min_data, median_max_data, median_min_data, agents, agents_90

##########################################################################################################
    def read_recovery_csv(self,path,algo,arena):
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
                                data.update({(algo,arena,data_val.get(keys[0]),data_val.get(keys[1]),data_val.get(keys[2]),data_val.get(keys[3]),data_val.get(keys[4]),data_val.get(keys[5]),data_val.get(keys[6]),data_val.get(keys[7])):(data_val.get(keys[8]),data_val.get(keys[9]),data_val.get(keys[10]))})
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
    def plot_recovery(self, data_in):
        # Impostazioni generali
        plt.rcParams.update({"font.size": 18})
        images_dir = os.path.join(self.base, "rec_data", "images")
        os.makedirs(images_dir, exist_ok=True)

        # Mappa varianti -> label e colore
        cm = plt.get_cmap('viridis')
        norm = colors.Normalize(vmin=0, vmax=5)
        scalarMap = cmx.ScalarMappable(norm=norm, cmap=cm)
        variant_map = {
            'Pf': (r'$AN$', 'red'),
            'P': (r'$AN_{t}$', scalarMap.to_rgba(0)),
            'O.0.0': (r'$ID+B$', scalarMap.to_rgba(1)),
            'O.2.0': (r'$ID+R_{f}$', scalarMap.to_rgba(2)),
            'O.1.1': (r'$ID+R_{1}$', scalarMap.to_rgba(3)),
            'O.1.0': (r'$ID+R_{\infty}$', scalarMap.to_rgba(4)),
        }

        # Ricostruzione DataFrame
        rows = []
        for key, (mean, std, events) in data_in.items():
            # Assicura trattazione come stringhe e cast
            k = [str(x) for x in key]
            alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = k
            broadcast = int(float(broadcast)); hops = int(float(hops))
            agents = int(float(agents)); msgs = int(float(msgs))
            gt = float(gt); th = float(th)
            variant_key = f"{alg}.{broadcast}.{hops}" if alg == 'O' else alg
            label, color = variant_map.get(variant_key, ('UNK', 'black'))
            rows.append({
                'Arena': arena,
                'Agents': agents,
                'Msgs_exp_time': msgs,
                'Error': abs(gt - th),
                'Events': int(events)/(100*agents),
                'Time': float(mean),
                'VariantKey': variant_key,
                'Label': label,
                'Color': color
            })
        df = pd.DataFrame(rows)

        # Griglia righe/colonne
        grid = [("bigA",25), ("smallA",25), ("bigA",100)]
        row_labels = ["LD25", "HD25", "HD100"]
        msg_list = sorted(df['Msgs_exp_time'].unique())
        col_labels = [f"$T_m$={m}" for m in msg_list]
        labels = [v[0] for v in variant_map.values()]

        def save_box(subset, suffix, entry):
            fig, axes = plt.subplots(3, len(msg_list), figsize=(28,18), sharey=True,sharex=True)
            for i, (arena, ag) in enumerate(grid):
                for j, m in enumerate(msg_list):
                    ax = axes[i,j]
                    cell = subset[(subset['Arena']==arena)&(subset['Agents']==ag)&(subset['Msgs_exp_time']==m)]
                    data = [cell[cell['Label']==lbl][entry].values for lbl in labels]
                    # Plot only if non-empty
                    if any(len(d)>0 for d in data):
                        bp = ax.boxplot(data, labels=labels, patch_artist=True)
                        for patch, lbl in zip(bp['boxes'], labels):
                            c = dict(variant_map.values())[lbl]
                            patch.set_facecolor(c)
                    # Label colonna/riga
                    if i == 0:
                        ax.set_title(col_labels[j])
                    if entry=="Time":
                        ax.set_ylim(0,20)
                    else:
                        ax.set_ylim(-0.03,1.03)
                # Rilascia label riga a destra
                if entry=="Time":
                    axes[i,0].annotate(r"$T_{r}$", xy=(-.2, 0.5), xycoords='axes fraction', fontsize=36,
                                     ha='left', va='center', rotation=90)
                else:
                    axes[i,0].annotate(r"$E_{r}$", xy=(-.2, 0.5), xycoords='axes fraction', fontsize=36,
                                     ha='left', va='center', rotation=90)
    
                axes[i,-1].annotate(row_labels[i], xy=(1.05, 0.5), xycoords='axes fraction', fontsize=36,
                                     ha='left', va='center', rotation=90)
            # Legenda
            handles = [mlines.Line2D([],[],color=color,marker='.',linestyle='None',markersize=24,label=label)
                       for label, color in variant_map.values()]
                
            # fig.legend(handles=handles, ncol=len(handles), loc='lower center')
            fig.tight_layout(rect=[0,0.05,1,0.95])
            fig.savefig(os.path.join(images_dir, f"box_{suffix}.png"))
            plt.close(fig)
        save_box(df, 'all_events','Events')
        save_box(df, 'all_time','Time')
        save_box(df[df['Error']<=0.05], 'le05_events','Events')
        save_box(df[df['Error']<=0.05], 'le05_time','Time')
        save_box(df[df['Error']>0.05], 'gt05_events','Events')
        save_box(df[df['Error']>0.05], 'gt05_time','Time')

        # Istogrammi 2D per variante
        xbins = np.linspace(0, df['Error'].max(), 20)
        ybins = np.arange(0.00,1.1,0.05)
        for key_var, (label, color) in variant_map.items():
            fig, axes = plt.subplots(3, len(msg_list), figsize=(28,18), sharex=True, sharey=True)
            h = None
            for i, (arena, ag) in enumerate(grid):
                for j, m in enumerate(msg_list):
                    ax = axes[i,j]
                    cell = df[(df['VariantKey']==key_var)&(df['Arena']==arena)&(df['Agents']==ag)&(df['Msgs_exp_time']==m)]
                    if not cell.empty:
                        h = ax.hist2d(cell['Error'], cell['Events'], bins=[xbins,ybins], cmap='viridis')
                    if i == 0:
                        ax.set_title(col_labels[j])
                axes[i,-1].annotate(row_labels[i], xy=(1.05, 0.5), xycoords='axes fraction', fontsize=36,
                                     ha='left', va='center', rotation=270)
            # Add colorbar if any data
            if h is not None:
                fig.colorbar(h[3], ax=axes.ravel().tolist(), label='Count')
            fig.savefig(os.path.join(images_dir, f"hist2d_{key_var}.png"))
            plt.close(fig)
        # Istogrammi 2D per variante
        xbins = np.linspace(0, df['Error'].max(), 20)
        ybins = np.arange(0,21,1)
        for key_var, (label, color) in variant_map.items():
            fig, axes = plt.subplots(3, len(msg_list), figsize=(28,18), sharex=True, sharey=True)
            h = None
            for i, (arena, ag) in enumerate(grid):
                for j, m in enumerate(msg_list):
                    ax = axes[i,j]
                    cell = df[(df['VariantKey']==key_var)&(df['Arena']==arena)&(df['Agents']==ag)&(df['Msgs_exp_time']==m)]
                    if not cell.empty:
                        h = ax.hist2d(cell['Error'], cell['Time'], bins=[xbins,ybins], cmap='viridis')
                    if i == 0:
                        ax.set_title(col_labels[j])
                axes[i,-1].annotate(row_labels[i], xy=(1.05, 0.5), xycoords='axes fraction', fontsize=36,
                                     ha='left', va='center', rotation=270)
            # Add colorbar if any data
            if h is not None:
                fig.colorbar(h[3], ax=axes.ravel().tolist(), label='Count')
            # fig.tight_layout(rect=[0,0.05,1,0.95])
            fig.savefig(os.path.join(images_dir, f"Thist2d_{key_var}.png"))
            plt.close(fig)

##########################################################################################################
    def plot_recovery_old(self,data_in):
        if not os.path.exists(self.base+"/rec_data/images/"):
            os.mkdir(self.base+"/rec_data/images/")
        path = self.base+"/rec_data/images/"
        means_dict_park, means_dict_park_real_fifo, means_dict_adms, means_dict_fifo, means_dict_rnd, means_dict_rnd_inf = {},{},{},{},{},{}
        stds_dict_park, stds_dict_park_real_fifo, stds_dict_adms, stds_dict_fifo, stds_dict_rnd, stds_dict_rnd_inf = {},{},{},{},{},{}
        events_dict_park, events_dict_park_real_fifo, events_dict_adms, events_dict_fifo, events_dict_rnd, events_dict_rnd_inf = {},{},{},{},{},{}
        ground_T, threshlds, msg_hops, jolly                    = [],[],[],[]
        algo, arena, time, comm, agents, buf_dim, msg_time      = [],[],[],[],[],[],[]
        o_k                                                     = []
        da_K = data_in.keys()
        for k0 in da_K:
            if k0[0] not in algo: algo.append(k0[0])
            if k0[1] not in arena: arena.append(k0[1])
            if k0[2] not in time: time.append(k0[2])
            if k0[3] not in comm: comm.append(k0[3])
            if k0[4] not in agents: agents.append(k0[4])
            if k0[5] not in buf_dim: buf_dim.append(k0[5])
            if k0[6] not in msg_time: msg_time.append(k0[6])
            if k0[7] not in msg_hops: msg_hops.append(k0[7])
            if k0[8] not in ground_T: ground_T.append(k0[8])
            if k0[9] not in threshlds: threshlds.append(k0[9])
            if k0[10] not in jolly: jolly.append(k0[10])
        for a in algo:
            for a_s in arena:
                for et in time:
                    for c in comm:
                        for m_h in msg_hops:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for mt in msg_time:
                                        for gt in ground_T:
                                            for jl in jolly:
                                                for thr in threshlds:
                                                    s_data = data_in.get((a,a_s,et,c,n_a,m_b_d,mt,m_h,gt,thr,jl))
                                                    if s_data != None:
                                                        if m_b_d not in o_k: o_k.append(m_b_d)
                                                        value = np.round(float(s_data[0]),3)
                                                        std = np.round(float(s_data[1]),3)
                                                        episodes = int(s_data[2])
                                                        if a=='P' and int(c)==0:
                                                            means_dict_park.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):value})
                                                            stds_dict_park.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):std})
                                                            events_dict_park.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):episodes})
                                                        if a=='Pf' and int(c)==0:
                                                            means_dict_park_real_fifo.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):value})
                                                            stds_dict_park_real_fifo.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):std})
                                                            events_dict_park_real_fifo.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):episodes})
                                                        if a=='O':
                                                            if int(c)==0:
                                                                means_dict_adms.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):value})
                                                                stds_dict_adms.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):std})
                                                                events_dict_adms.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):episodes})
                                                            elif int(c)==2:
                                                                means_dict_fifo.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):value})
                                                                stds_dict_fifo.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):std})
                                                                events_dict_fifo.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):episodes})
                                                            else:
                                                                if int(m_h)==1:
                                                                    means_dict_rnd.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):value})
                                                                    stds_dict_rnd.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):std})
                                                                    events_dict_rnd.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):episodes})
                                                                else:
                                                                    means_dict_rnd_inf.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):value})                                                
                                                                    stds_dict_rnd_inf.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):std})                                                
                                                                    events_dict_rnd_inf.update({(a_s,n_a,m_b_d,mt,gt,thr,jl):episodes})                                                
        self.print_box_recovery_by_bufferSize(path,[means_dict_park,means_dict_adms,means_dict_fifo,means_dict_rnd,means_dict_rnd_inf,means_dict_park_real_fifo],'recovery_box_buffer_size_means.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        self.print_box_recovery_by_bufferSize(path,[means_dict_park,means_dict_adms,means_dict_fifo,means_dict_rnd,means_dict_rnd_inf,means_dict_park_real_fifo],'easy_recovery_box_buffer_size_means.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        self.print_box_recovery_by_bufferSize(path,[means_dict_park,means_dict_adms,means_dict_fifo,means_dict_rnd,means_dict_rnd_inf,means_dict_park_real_fifo],'hard_recovery_box_buffer_size_means.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        # self.print_box_recovery_by_bufferSize(path,[stds_dict_park,stds_dict_adms,stds_dict_fifo,stds_dict_rnd,stds_dict_rnd_inf,stds_dict_park_real_fifo],'recovery_box_buffer_size_stds.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        # self.print_box_recovery_by_bufferSize(path,[stds_dict_park,stds_dict_adms,stds_dict_fifo,stds_dict_rnd,stds_dict_rnd_inf,stds_dict_park_real_fifo],'easy_recovery_box_buffer_size_stds.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        # self.print_box_recovery_by_bufferSize(path,[stds_dict_park,stds_dict_adms,stds_dict_fifo,stds_dict_rnd,stds_dict_rnd_inf,stds_dict_park_real_fifo],'hard_recovery_box_buffer_size_stds.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        self.print_box_recovery_by_bufferSize(path,[events_dict_park,events_dict_adms,events_dict_fifo,events_dict_rnd,events_dict_rnd_inf,events_dict_park_real_fifo],'recovery_box_buffer_size_events.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        self.print_box_recovery_by_bufferSize(path,[events_dict_park,events_dict_adms,events_dict_fifo,events_dict_rnd,events_dict_rnd_inf,events_dict_park_real_fifo],'easy_recovery_box_buffer_size_events.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])
        self.print_box_recovery_by_bufferSize(path,[events_dict_park,events_dict_adms,events_dict_fifo,events_dict_rnd,events_dict_rnd_inf,events_dict_park_real_fifo],'hard_recovery_box_buffer_size_events.pdf',[ground_T,threshlds],[buf_dim,jolly,msg_time],[arena,agents])

##########################################################################################################
    def store_recovery(self,data_in):
        if not os.path.exists(self.base+"/rec_data/"):
            os.mkdir(self.base+"/rec_data/")
        path = self.base+"/rec_data/"
        ground_T, threshlds, msg_hops, jolly        = [],[],[],[]
        algo, arena, time, comm, agents, buf_dim ,msgs_time   = [],[],[],[],[],[],[]
        da_K = data_in.keys()
        for k0 in da_K:
            if k0[0] not in algo: algo.append(k0[0])
            if k0[1] not in arena: arena.append(k0[1])
            if k0[2] not in time: time.append(k0[2])
            if k0[3] not in comm: comm.append(k0[3])
            if k0[4] not in agents: agents.append(k0[4])
            if k0[5] not in buf_dim: buf_dim.append(k0[5])
            if k0[6] not in msgs_time: msgs_time.append(k0[6])
            if k0[7] not in msg_hops: msg_hops.append(k0[7])
            if k0[8] not in ground_T: ground_T.append(k0[8])
            if k0[9] not in threshlds: threshlds.append(k0[9])
            if k0[10] not in jolly: jolly.append(k0[10])
        for a in algo:
            for a_s in arena:
                for et in time:
                    for c in comm:
                        for m_h in msg_hops:
                            for n_a in agents:
                                for m_b_d in buf_dim:
                                    for met in msgs_time:
                                        for gt in ground_T:
                                            for thr in threshlds:
                                                for jl in jolly:
                                                    s_data = data_in.get((a,a_s,et,c,n_a,m_b_d,met,m_h,gt,thr,jl))
                                                    if s_data != None:
                                                        with open(path + 'recovery_data.csv', mode='a', newline='\n') as file:
                                                            writer = csv.writer(file)
                                                            if file.tell() == 0:
                                                                writer.writerow(['Algorithm', 'Arena', 'Time', 'Broadcast', 'Agents', 'Buffer_Dim','Msgs_exp_time','Msg_Hops', 'Ground_T', 'Threshold', 'Mean', 'Std', 'Events'])
                                                            writer.writerow([a, a_s, et, c, n_a, m_b_d,met, m_h, gt, thr, s_data[0][0], s_data[0][1], s_data[1]])

##########################################################################################################
    def print_box_recovery_by_bufferSize(self,save_path,data,filename,gt_thr,buf_dims,aa):
        plt.rcParams.update({"font.size":36})
        cm                  = plt.get_cmap('viridis') 
        typo                = [0,1,2,3,4,5]
        cNorm               = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap           = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        anonymous_real_fifo = mlines.Line2D([], [], color="red", marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$AN$')
        anonymous           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$AN_{t}$')
        id_broad            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+B$')
        id_rebroad_fifo     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{f}$')
        id_rebroad_rnd      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        id_rebroad_rnd_inf  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')
        handles_r           = [id_rebroad_fifo,id_rebroad_rnd,id_rebroad_rnd_inf]
        colors_box          = [scalarMap.to_rgba(typo[2]),scalarMap.to_rgba(typo[3]),scalarMap.to_rgba(typo[4])]
        dict_park, dict_adms, dict_fifo, dict_rnd, dict_rnd_inf,dict_park_real_fifo = data[0], data[1], data[2], data[3], data[4], data[5]
        # park_real_fifo_plotting = np.array([[[[-1]*len(gt_thr[0])*len(gt_thr[1])]*len(buf_dims[1])]*5]*3)
        # park_plotting       = np.array([[[[-1]*len(gt_thr[0])*len(gt_thr[1])]*len(buf_dims[1])]*5]*3)
        # adam_plotting       = np.array([[[[-1]*len(gt_thr[0])*len(gt_thr[1])]*len(buf_dims[1])]*5]*3)
        fifo_plotting       = np.array([[[[-1]*len(gt_thr[0])*len(gt_thr[1])]*len(buf_dims[1])]*5]*3)
        rnd_plotting        = np.array([[[[-1]*len(gt_thr[0])*len(gt_thr[1])]*len(buf_dims[1])]*5]*3)
        rnd_inf_plotting    = np.array([[[[-1]*len(gt_thr[0])*len(gt_thr[1])]*len(buf_dims[1])]*5]*3)
        for gt in range(len(gt_thr[0])):
            for buff_perc in range(len(buf_dims[1])):
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
                        for mt in buf_dims[2]:
                            park_data_real_fifo = np.array([])
                            park_data       = np.array([])
                            adams_data      = np.array([])
                            fifo_data       = np.array([])
                            rnd_data        = np.array([])
                            rnd_inf_data    = np.array([])
                            for m_b_d in buf_dims[0]:
                                for thr in range(len(gt_thr[1])):
                                    store = True
                                    if filename.split('_')[0] == "easy" and abs(float(gt_thr[0][gt]) - float(gt_thr[1][thr])) <= 0.05 : store=False
                                    elif filename.split('_')[0] == "hard" and abs(float(gt_thr[0][gt]) - float(gt_thr[1][thr])) > 0.05 : store=False
                                    if store:
                                        # entry = dict_park_real_fifo.get((a_s,n_a,m_b_d,mt,gt_thr[0][gt],gt_thr[1][thr],buf_dims[1][buff_perc]))
                                        # if entry != None: park_data_real_fifo = np.append(park_data_real_fifo,entry)
                                        # entry = dict_park.get((a_s,n_a,m_b_d,mt,gt_thr[0][gt],gt_thr[1][thr],buf_dims[1][buff_perc]))
                                        # if entry != None: park_data = np.append(park_data,entry)
                                        # entry = dict_adms.get((a_s,n_a,m_b_d,mt,gt_thr[0][gt],gt_thr[1][thr],buf_dims[1][buff_perc]))
                                        # if entry != None: adams_data = np.append(adams_data,entry)
                                        entry = dict_fifo.get((a_s,n_a,m_b_d,mt,gt_thr[0][gt],gt_thr[1][thr],buf_dims[1][buff_perc]))
                                        if entry != None: fifo_data = np.append(fifo_data,entry)
                                        entry = dict_rnd.get((a_s,n_a,m_b_d,mt,gt_thr[0][gt],gt_thr[1][thr],buf_dims[1][buff_perc]))
                                        if entry != None: rnd_data = np.append(rnd_data,entry)
                                        entry = dict_rnd_inf.get((a_s,n_a,m_b_d,mt,gt_thr[0][gt],gt_thr[1][thr],buf_dims[1][buff_perc]))
                                        if entry != None: rnd_inf_data = np.append(rnd_inf_data,entry)
                            if mt == '60':
                                col = 0
                            elif mt == '120':
                                col = 1
                            elif mt == '180':
                                col = 2
                            elif mt == '300':
                                col = 3
                            elif mt == '600':
                                col = 4
                            # if park_data_real_fifo.any() != None:
                            #     for i in range(len(park_data_real_fifo)): park_real_fifo_plotting[row][col][buff_perc][i] = park_data_real_fifo[i]
                            # if park_data.any() != None:
                            #     for i in range(len(park_data)): park_plotting[row][col][buff_perc][i] = park_data[i]
                            # if adams_data.any() != None:
                            #     for i in range(len(adams_data)): adam_plotting[row][col][buff_perc][i] = adams_data[i]
                            if fifo_data.any() != None:
                                for i in range(len(fifo_data)): fifo_plotting[row][col][buff_perc][i] = fifo_data[i]
                            if rnd_data.any() != None:
                                for i in range(len(rnd_data)): rnd_plotting[row][col][buff_perc][i] = rnd_data[i]
                            if rnd_inf_data.any() != None:
                                for i in range(len(rnd_inf_data)): rnd_inf_plotting[row][col][buff_perc][i] = rnd_inf_data[i]
        fig, ax = plt.subplots(nrows=3, ncols=5,figsize=(28,18),sharex=True,sharey=True)
        positions = np.arange(0,len(buf_dims[1])*3,3)
        for i in range(3):
            for j in range(5):
                # park_real = park_real_fifo_plotting[i][j]
                # park_real_print = [np.array([])]*len(buf_dims[1])
                # for k in range(len(park_real)):
                #     flag = []
                #     for z in range(len(park_real[k])):
                #         if park_real[k][z]>0:
                #             flag.append(park_real[k][z]) if "events" not in filename else flag.append((park_real[k][z]*.01)/25) if i!=2 else flag.append((park_real[k][z]*.01)/100)
                #     for e in flag:
                #         park_real_print[k] = np.append(park_real_print[k],e)
                # park = park_plotting[i][j]
                # park_print = [np.array([])]*len(buf_dims[1])
                # for k in range(len(park)):
                #     flag = []
                #     for z in range(len(park[k])):
                #         if park[k][z]>0:
                #             flag.append(park[k][z]) if "events" not in filename else flag.append((park[k][z]*.01)/25) if i!=2 else flag.append((park[k][z]*.01)/100)
                #     for e in flag:
                #         park_print[k] = np.append(park_print[k],e)
                # adam = adam_plotting[i][j]
                # adam_print = [np.array([])]*len(buf_dims[1])
                # for k in range(len(adam)):
                #     flag = []
                #     for z in range(len(adam[k])):
                #         if adam[k][z]>0:
                #             flag.append(adam[k][z]) if "events" not in filename else flag.append((adam[k][z]*.01)/25) if i!=2 else flag.append((adam[k][z]*.01)/100)
                #     for e in flag:
                #         adam_print[k] = np.append(adam_print[k],e)
                fifo = fifo_plotting[i][j]
                fifo_print = [np.array([])]*len(buf_dims[1])
                for k in range(len(fifo)):
                    flag = []
                    for z in range(len(fifo[k])):
                        if fifo[k][z]>0:
                            flag.append(fifo[k][z]) if "events" not in filename else flag.append((fifo[k][z]*.01)/25) if i!=2 else flag.append((fifo[k][z]*.01)/100)
                    for e in flag:
                        fifo_print[k] = np.append(fifo_print[k],e)
                rnd = rnd_plotting[i][j]
                rnd_print = [np.array([])]*len(buf_dims[1])
                for k in range(len(rnd)):
                    flag = []
                    for z in range(len(rnd[k])):
                        if rnd[k][z]>0:
                            flag.append(rnd[k][z]) if "events" not in filename else flag.append((rnd[k][z]*.01)/25) if i!=2 else flag.append((rnd[k][z]*.01)/100)
                    for e in flag:
                        rnd_print[k] = np.append(rnd_print[k],e)
                rnd_inf = rnd_inf_plotting[i][j]
                rnd_inf_print = [np.array([])]*len(buf_dims[1])
                for k in range(len(rnd_inf)):
                    flag = []
                    for z in range(len(rnd_inf[k])):
                        if rnd_inf[k][z]>0:
                            flag.append(rnd_inf[k][z]) if "events" not in filename else flag.append((rnd_inf[k][z]*.01)/25) if i!=2 else flag.append((rnd_inf[k][z]*.01)/100)
                    for e in flag:
                        rnd_inf_print[k] = np.append(rnd_inf_print[k],e)
                # bppr     = ax[i][j].boxplot(park_real_print,positions=[p for p in positions],widths=0.5,patch_artist=True)
                # bpp     = ax[i][j].boxplot(park_print,positions=[p for p in positions],widths=0.5,patch_artist=True)
                # bpa     = ax[i][j].boxplot(adam_print,positions=[p+1 for p in positions],widths=0.5,patch_artist=True)
                bpf     = ax[i][j].boxplot(fifo_print,positions=[p for p in positions],widths=0.5,patch_artist=True)
                bpr     = ax[i][j].boxplot(rnd_print,positions=[p+1 for p in positions],widths=0.5,patch_artist=True)
                bpri    = ax[i][j].boxplot(rnd_inf_print,positions=[p+2 for p in positions],widths=0.5,patch_artist=True)
                if "events" not in filename:
                    ax[i][j].set_yscale('log')
                    ax[i][j].set_ylim(1e0, 1e4)
                    ax[i][j].yaxis.set_tick_params(labelleft=True) if j == 0 else ax[i][j].yaxis.set_tick_params(labelleft=False)
                else: ax[i][j].set_ylim(0,5) if "easy" in filename else ax[i][j].set_ylim(0,10)
                # for bplot, color in zip((bpp, bpa, bpf, bpr, bpri), colors_box):
                for bplot, color in zip((bpf,bpr,bpri), colors_box):
                    for patch in bplot['boxes']:
                        patch.set_facecolor(color)
                ax[i][j].set_xticks([p + 1 for p in positions])
                ax[i][j].set_xticklabels(buf_dims[1])
        ax[0][0].set_title(r"$T_m = 60\, s$")
        ax[0][1].set_title(r"$T_m = 120\, s$")
        ax[0][2].set_title(r"$T_m = 180\, s$")
        ax[0][3].set_title(r"$T_m = 300\, s$")
        ax[0][4].set_title(r"$T_m = 600\, s$")
        ayt0=ax[0][4].twinx()
        ayt0.set_yticks([])
        ayt1=ax[1][4].twinx()
        ayt1.set_yticks([])
        ayt2=ax[2][4].twinx()
        ayt2.set_yticks([])
        ayt0.set_ylabel("LD25")
        ayt1.set_ylabel("HD25")
        ayt2.set_ylabel("HD100")
        ax[0][0].set_ylabel(r"$T_r$") if "events" not in filename else ax[0][0].set_ylabel("#")
        ax[1][0].set_ylabel(r"$T_r$") if "events" not in filename else ax[1][0].set_ylabel("#")
        ax[2][0].set_ylabel(r"$T_r$") if "events" not in filename else ax[2][0].set_ylabel("#")

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
        dict_park_avg_real_fifo,dict_park_avg,dict_adms_avg,dict_fifo_avg,dict_rnd_avg,dict_rnd_inf_avg         = {},{},{},{},{},{}
        dict_park_tmed_real_fifo,dict_park_tmed,dict_adms_tmed,dict_fifo_tmed,dict_rnd_tmed,dict_rnd_inf_tmed    = {},{},{},{},{},{}
        ground_T, threshlds , jolly, msg_hop        = [],[],[],[]
        algo,arena,runs,time,comm,agents,buf_dim    = [],[],[],[],[],[],[]
        o_k                                         = []
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
                                                            if m_t not in o_k: o_k.append(m_t)
                                                            tmp.append(round(self.extract_median(s_data[0],len(s_data[0])),2))
                                                            tmp_tmed.append(round(self.extract_median(t_data[0],len(s_data[0])),2))
                                                    if len(vals)==0:
                                                        vals            = np.array([tmp])
                                                        times_median    = np.array([tmp_tmed])
                                                    else:
                                                        vals            = np.append(vals,[tmp],axis=0)
                                                        times_median    = np.append(times_median,[tmp_tmed],axis=0)
                                                if a=='P' and int(c)==0 and m_t in o_k:
                                                    if len(vals[0])>0:
                                                        dict_park_avg.update({(a_s,n_a,m_t):vals})
                                                        dict_park_tmed.update({(a_s,n_a,m_t):times_median})
                                                if a=='Pf' and int(c)==0 and m_t in o_k:
                                                    if len(vals[0])>0:
                                                        dict_park_avg_real_fifo.update({(a_s,n_a,m_t):vals})
                                                        dict_park_tmed_real_fifo.update({(a_s,n_a,m_t):times_median})
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
        self.print_borders(path,'avg','median',ground_T,threshlds,[dict_park_avg,dict_adms_avg,dict_fifo_avg,dict_rnd_avg,dict_rnd_inf_avg,dict_park_avg_real_fifo],[dict_park_tmed,dict_adms_tmed,dict_fifo_tmed,dict_rnd_tmed,dict_rnd_inf_tmed,dict_park_tmed_real_fifo],o_k,[arena,agents])
        
##########################################################################################################
    def print_messages(self,data_in):
        plt.rcParams.update({"font.size":36})
        cm = plt.get_cmap('viridis') 
        typo = [0,1,2,3,4,5]
        cNorm  = colors.Normalize(vmin=typo[0], vmax=typo[-1])
        scalarMap = cmx.ScalarMappable(norm=cNorm, cmap=cm)
        dict_park,dict_adam,dict_fifo, dict_rnd, dict_rnd_inf,dict_park_real_fifo = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        anonymous_real_fifo = mlines.Line2D([], [], color="red", marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$AN$')
        anonymous           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$AN_{t}$')
        id_broad            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+B$')
        id_rebroad_fifo     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{f}$')
        id_rebroad_rnd      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        id_rebroad_rnd_inf  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r   = [id_rebroad_fifo,id_rebroad_rnd,id_rebroad_rnd_inf]
        fig, ax     = plt.subplots(nrows=3, ncols=5,figsize=(28,18))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        # for k in dict_park_real_fifo.keys():
        #     tmp =[]
        #     res = dict_park_real_fifo.get(k)
        #     norm = int(k[1])-1
        #     for xi in res:
        #         tmp.append(xi/norm)
        #     dict_park_real_fifo.update({k:tmp})
        # for k in dict_park.keys():
        #     tmp =[]
        #     res = dict_park.get(k)
        #     norm = int(k[1])-1
        #     for xi in res:
        #         tmp.append(xi/norm)
        #     dict_park.update({k:tmp})
        # for k in dict_adam.keys():
        #     tmp =[]
        #     res = dict_adam.get(k)
        #     norm = int(k[1])-1
        #     for xi in range(len(res)):
        #         tmp.append(res[xi]/norm)
        #     dict_adam.update({k:tmp})
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
        # for k in dict_park_real_fifo.keys():
        #     row = 0
        #     col = 0
        #     if k[0]=='big' and k[1]=='25':
        #         row = 0
        #     elif k[0]=='big' and k[1]=='100':
        #         row = 2
        #     elif k[0]=='small':
        #         row = 1
        #     if k[2] == '60':
        #         col = 0
        #     elif k[2] == '120':
        #         col = 1
        #     elif k[2] == '180':
        #         col = 2
        #     elif k[2] == '300':
        #         col = 3
        #     elif k[2] == '600':
        #         col = 4
        #     ax[row][col].plot(dict_park_real_fifo.get(k),color="red",lw=6)
        # for k in dict_park.keys():
        #     row = 0
        #     col = 0
        #     if k[0]=='big' and k[1]=='25':
        #         row = 0
        #     elif k[0]=='big' and k[1]=='100':
        #         row = 2
        #     elif k[0]=='small':
        #         row = 1
        #     if k[2] == '60':
        #         col = 0
        #     elif k[2] == '120':
        #         col = 1
        #     elif k[2] == '180':
        #         col = 2
        #     elif k[2] == '300':
        #         col = 3
        #     elif k[2] == '600':
        #         col = 4
        #     ax[row][col].plot(dict_park.get(k),color=scalarMap.to_rgba(typo[0]),lw=6)
        # for k in dict_adam.keys():
        #     row = 0
        #     col = 0
        #     if k[0]=='big' and k[1]=='25':
        #         row = 0
        #     elif k[0]=='big' and k[1]=='100':
        #         row = 2
        #     elif k[0]=='small':
        #         row = 1
        #     if k[2] == '60':
        #         col = 0
        #     elif k[2] == '120':
        #         col = 1
        #     elif k[2] == '180':
        #         col = 2
        #     elif k[2] == '300':
        #         col = 3
        #     elif k[2] == '600':
        #         col = 4
        #     ax[row][col].plot(dict_adam.get(k),color=scalarMap.to_rgba(typo[1]),lw=6)
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
    def print_messages_homogeneity(self,max_data_in,min_data_in,median_max_data,median_min_data,agents_data,agents_90_data):
        plt.rcParams.update({"font.size":36})
        max_dict_park, min_dict_park, median_max_dict_park, median_min_dict_park, agents, agents_90 = max_data_in[0], min_data_in[0] ,median_max_data[0] ,median_min_data[0], agents_data[0], agents_90_data[0]
        max_rep         = mlines.Line2D([], [], color="red", marker="None", linestyle='-', linewidth=6, label="abs max")
        median_max_rep  = mlines.Line2D([], [], color="red", marker="None", linestyle='--', linewidth=6, label="median max")
        median_min_rep  = mlines.Line2D([], [], color="black", marker="None", linestyle='--', linewidth=6, label="median min")
        agents_lab      = mlines.Line2D([], [], color="green", marker="None", linestyle='-', linewidth=6, label="agents")
        real_x_ticks = []
        void_x_ticks = []
        svoid_x_ticks = []
        handles_r   = [max_rep,median_max_rep,median_min_rep,agents_lab]
        fig, ax     = plt.subplots(nrows=3, ncols=5,figsize=(28,18))
        if len(real_x_ticks)==0:
            for x in range(0,901,50):
                if x%300 == 0:
                    svoid_x_ticks.append('')
                    void_x_ticks.append('')
                    real_x_ticks.append(str(int(np.round(x,0))))
                else:
                    void_x_ticks.append('')
        for k in agents.keys():
            tmp =[]
            res = agents.get(k)
            norm = int(k[1])
            for xi in res:
                tmp.append(xi/norm)
            agents.update({k:tmp})
        for k in max_dict_park.keys():
            tmp =[]
            res = max_dict_park.get(k)
            BUFFERS = [19,21,22,23,24]
            buf = 0
            if k[0]=='big':
                if int(k[1])==25:
                    BUFFERS=[11,15,17,19,21]
                elif int(k[1])==100:
                    BUFFERS=[41,56,65,74,83]
            if int(k[2])==120:
                buf = 1
            elif int(k[2])==180:
                buf = 2
            elif int(k[2])==300:
                buf = 3
            elif int(k[2])==600:
                buf = 4
            norm = BUFFERS[buf]
            for xi in res:
                tmp.append(xi/norm)
            max_dict_park.update({k:tmp})
        for k in median_max_dict_park.keys():
            tmp =[]
            res = median_max_dict_park.get(k)
            BUFFERS = [19,21,22,23,24]
            buf = 0
            if k[0]=='big':
                if int(k[1])==25:
                    BUFFERS=[11,15,17,19,21]
                elif int(k[1])==100:
                    BUFFERS=[41,56,65,74,83]
            if int(k[2])==120:
                buf = 1
            elif int(k[2])==180:
                buf = 2
            elif int(k[2])==300:
                buf = 3
            elif int(k[2])==600:
                buf = 4
            norm = BUFFERS[buf]
            for xi in res:
                tmp.append(xi/norm)
            median_max_dict_park.update({k:tmp})
        for k in median_min_dict_park.keys():
            tmp =[]
            res = median_min_dict_park.get(k)
            BUFFERS = [19,21,22,23,24]
            buf = 0
            if k[0]=='big':
                if int(k[1])==25:
                    BUFFERS=[11,15,17,19,21]
                elif int(k[1])==100:
                    BUFFERS=[41,56,65,74,83]
            if int(k[2])==120:
                buf = 1
            elif int(k[2])==180:
                buf = 2
            elif int(k[2])==300:
                buf = 3
            elif int(k[2])==600:
                buf = 4
            norm = BUFFERS[buf]
            for xi in res:
                tmp.append(xi/norm)
            median_min_dict_park.update({k:tmp})
        for k in max_dict_park.keys():
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
            ax[row][col].plot(max_dict_park.get(k),color="red",ls="-",lw=6)
        for k in median_max_dict_park.keys():
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
            ax[row][col].plot(median_max_dict_park.get(k),color="red",ls="--",lw=6)
        for k in median_min_dict_park.keys():
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
            ax[row][col].plot(median_min_dict_park.get(k),color="black",ls="--",lw=6)
        for k in agents.keys():
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
            ax[row][col].plot(agents.get(k),color="green",ls="-",lw=6)
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
                ax[x][y].set_ylim(0,1)
        fig.tight_layout()
        if not os.path.exists(self.base+"/msgs_data/images/"):
            os.mkdir(self.base+"/msgs_data/images/")
        fig_path = self.base+"/msgs_data/images/messages_homogeneity.pdf"
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
        dict_park,dict_adam,dict_fifo,dict_rnd,dict_rnd_inf,dict_park_real_fifo = data_in[0], data_in[1], data_in[2], data_in[3], data_in[4], data_in[5]
        tdict_park,tdict_adam,tdict_fifo,tdict_rnd,tdict_rnd_inf,tdict_park_real_fifo = times_in[0], times_in[1], times_in[2], times_in[3], times_in[4], times_in[5]
        po_k = keys
        o_k = []
        for x in range(len(po_k)):
            o_k.append(int(po_k[x]))
        o_k = np.sort(o_k)
        arena = more_k[0]

        low_bound           = mlines.Line2D([], [], color='black', marker='None', linestyle='--', linewidth=4, label=r"$\hat{Q} = 0.2$")
        high_bound          = mlines.Line2D([], [], color='black', marker='None', linestyle='-', linewidth=4, label=r"$\hat{Q} = 0.8$")
        anonymous_real_fifo = mlines.Line2D([], [], color="red", marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$AN$')
        anonymous           = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[0]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$AN_{t}$')
        id_broad            = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[1]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+B$')
        id_rebroad_fifo     = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[2]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{f}$')
        id_rebroad_rnd      = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[3]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{1}$')
        id_rebroad_rnd_inf  = mlines.Line2D([], [], color=scalarMap.to_rgba(typo[4]), marker='_', linestyle='None', markeredgewidth=18, markersize=18, label=r'$ID+R_{\infty}$')

        handles_c   = [high_bound,low_bound]
        handles_r   = [anonymous_real_fifo,anonymous,id_broad,id_rebroad_fifo,id_rebroad_rnd,id_rebroad_rnd_inf]
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
        vals_dict = {}
        for a in arena:
            if a=="smallA":
                agents = ["25"]
            else:
                agents = more_k[1]
            for ag in agents:
                row = 1  if a=="smallA" else 0
                if int(ag)==100: row = 2
                vals8p  = [[0]*len(threshlds)]*len(o_k)
                vals2p  = [[0]*len(threshlds)]*len(o_k)
                vals8pr  = [[0]*len(threshlds)]*len(o_k)
                vals2pr  = [[0]*len(threshlds)]*len(o_k)
                vals8a  = [[0]*len(threshlds)]*len(o_k)
                vals2a  = [[0]*len(threshlds)]*len(o_k)
                vals8f  = [[0]*len(threshlds)]*len(o_k)
                vals2f  = [[0]*len(threshlds)]*len(o_k)
                vals8r  = [[0]*len(threshlds)]*len(o_k)
                vals2r  = [[0]*len(threshlds)]*len(o_k)
                vals8ri = [[0]*len(threshlds)]*len(o_k)
                vals2ri = [[0]*len(threshlds)]*len(o_k)
                flag_vals8p  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals2p  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals8pr  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals2pr  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals8a  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals2a  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals8f  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals2f  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals8r  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals2r  = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals8ri = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)
                flag_vals2ri = [[[0,0],[0,0]]*len(threshlds)]*len(o_k)

                tvalsp  = [[0]*len(threshlds)]*len(o_k)
                tvalspr  = [[0]*len(threshlds)]*len(o_k)
                tvalsa  = [[0]*len(threshlds)]*len(o_k)
                tvalsf  = [[0]*len(threshlds)]*len(o_k)
                tvalsr  = [[0]*len(threshlds)]*len(o_k)
                tvalsri = [[0]*len(threshlds)]*len(o_k)
                for k in range(len(o_k)):
                    for th in range(len(threshlds)):
                        p_vals2,pr_vals2,a_vals2,f_vals2,r_vals2,ri_vals2 = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_vals8,pr_vals8,a_vals8,f_vals8,r_vals8,ri_vals8 = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt2,pr_gt2,a_gt2,f_gt2,r_gt2,ri_gt2             = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_gt8,pr_gt8,a_gt8,f_gt8,r_gt8,ri_gt8             = [np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2,[np.nan]*2
                        p_valst,pr_valst,a_valst,f_valst,r_valst,ri_valst = np.nan,np.nan,np.nan,np.nan,np.nan,np.nan
                        lim_p_valst,lim_pr_valst,lim_a_valst,lim_f_valst,lim_r_valst,lim_ri_valst = np.nan,np.nan,np.nan,np.nan,np.nan,np.nan
                        for pt in range(len(ground_T)):
                            pval    = dict_park.get((a,ag,str(o_k[k])))[pt][th]
                            prval   = dict_park_real_fifo.get((a,ag,str(o_k[k])))[pt][th]
                            aval    = dict_adam.get((a,ag,str(o_k[k])))[pt][th]
                            fval    = dict_fifo.get((a,ag,str(o_k[k])))[pt][th]
                            rval    = dict_rnd.get((a,ag,str(o_k[k])))[pt][th]
                            rival   = dict_rnd_inf.get((a,ag,str(o_k[k])))[pt][th]
                            tpval   = tdict_park.get((a,ag,str(o_k[k])))[pt][th]
                            trpval  = tdict_park_real_fifo.get((a,ag,str(o_k[k])))[pt][th]
                            taval   = tdict_adam.get((a,ag,str(o_k[k])))[pt][th]
                            tfval   = tdict_fifo.get((a,ag,str(o_k[k])))[pt][th]
                            trval   = tdict_rnd.get((a,ag,str(o_k[k])))[pt][th]
                            trival  = tdict_rnd_inf.get((a,ag,str(o_k[k])))[pt][th]
                            if pval>=0.8:
                                temp_tval = tpval
                                if ground_T[pt]-threshlds[th] >= 0.09 and (p_valst is np.nan or ground_T[pt]-threshlds[th]<lim_p_valst):
                                    p_valst = temp_tval
                                    lim_p_valst = ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >=0 and (p_vals8[1] is np.nan or pval<p_vals8[1]):
                                    p_vals8[1]  = pval
                                    p_gt8[1]    = ground_T[pt]
                            elif pval<=0.2:
                                if ground_T[pt]-threshlds[th] <=0 and (p_vals2[0] is np.nan or pval>=p_vals2[0]):
                                    p_vals2[0]  = pval
                                    p_gt2[0]    = ground_T[pt]
                            else:
                                if p_vals8[0] is np.nan or pval>p_vals8[0]:
                                    p_vals8[0]  = pval
                                    p_gt8[0]    = ground_T[pt]
                                if p_vals2[1] is np.nan or pval<p_vals2[1]:
                                    p_vals2[1]  = pval
                                    p_gt2[1]    = ground_T[pt]
                            if prval>=0.8:
                                temp_tval = trpval
                                if ground_T[pt]-threshlds[th] >= 0.09 and (pr_valst is np.nan or ground_T[pt]-threshlds[th]<lim_pr_valst):
                                    pr_valst = temp_tval
                                    lim_pr_valst = ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >=0 and (pr_vals8[1] is np.nan or prval<pr_vals8[1]):
                                    pr_vals8[1]  = prval
                                    pr_gt8[1]    = ground_T[pt]
                            elif prval<=0.2:
                                if ground_T[pt]-threshlds[th] <=0 and (pr_vals2[0] is np.nan or prval>=pr_vals2[0]):
                                    pr_vals2[0]  = prval
                                    pr_gt2[0]    = ground_T[pt]
                            else:
                                if pr_vals8[0] is np.nan or prval>pr_vals8[0]:
                                    pr_vals8[0]  = prval
                                    pr_gt8[0]    = ground_T[pt]
                                if pr_vals2[1] is np.nan or prval<pr_vals2[1]:
                                    pr_vals2[1]  = prval
                                    pr_gt2[1]    = ground_T[pt]
                            if aval>=0.8:
                                temp_aval = taval
                                if ground_T[pt]-threshlds[th] >= 0.09 and (a_valst is np.nan or ground_T[pt]-threshlds[th]<lim_a_valst):
                                    a_valst = temp_aval
                                    lim_a_valst = ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >=0 and (a_vals8[1] is np.nan or aval<a_vals8[1]):
                                    a_vals8[1]  = aval
                                    a_gt8[1]    = ground_T[pt]
                            elif aval<=0.2:
                                if ground_T[pt]-threshlds[th] <=0 and (a_vals2[0] is np.nan or aval>=a_vals2[0]):
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
                                temp_fval = tfval
                                if ground_T[pt]-threshlds[th] >= 0.09 and (f_valst is np.nan or ground_T[pt]-threshlds[th]<lim_f_valst):
                                    f_valst = temp_fval
                                    lim_f_valst = ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >=0 and (f_vals8[1] is np.nan or fval<f_vals8[1]):
                                    f_vals8[1]  = fval
                                    f_gt8[1]    = ground_T[pt]
                            elif fval<=0.2:
                                if ground_T[pt]-threshlds[th] <=0 and (f_vals2[0] is np.nan or fval>=f_vals2[0]):
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
                                temp_rval = trval
                                if ground_T[pt]-threshlds[th] >= 0.09 and (r_valst is np.nan or ground_T[pt]-threshlds[th]<lim_r_valst):
                                    r_valst = temp_rval
                                    lim_r_valst = ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >=0 and (r_vals8[1] is np.nan or rval<r_vals8[1]):
                                    r_vals8[1]  = rval
                                    r_gt8[1]    = ground_T[pt]
                            elif rval<=0.2:
                                if ground_T[pt]-threshlds[th] <=0 and (r_vals2[0] is np.nan or rval>=r_vals2[0]):
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
                                temp_rival = trival
                                if ground_T[pt]-threshlds[th] >= 0.09 and (ri_valst is np.nan or ground_T[pt]-threshlds[th]<lim_ri_valst):
                                    ri_valst = temp_rival
                                    lim_ri_valst = ground_T[pt]-threshlds[th]
                                if ground_T[pt]-threshlds[th] >=0 and (ri_vals8[1] is np.nan or rival<ri_vals8[1]):
                                    ri_vals8[1]  = rival
                                    ri_gt8[1]    = ground_T[pt]
                            elif rival<=0.2:
                                if ground_T[pt]-threshlds[th] <=0 and (ri_vals2[0] is np.nan or rival>=ri_vals2[0]):
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
                        if pr_vals8[0] is np.nan:
                            pr_vals8[0] = pr_vals8[1]
                            pr_gt8[0] = pr_gt8[1]
                        elif pr_vals8[1] is np.nan:
                            pr_vals8[1] = pr_vals8[0]
                            pr_gt8[1] = pr_gt8[0]
                        if pr_vals2[0] is np.nan:
                            pr_vals2[0] = pr_vals2[1]
                            pr_gt2[0] = pr_gt2[1]
                        elif pr_vals2[1] is np.nan:
                            pr_vals2[1] = pr_vals2[0]
                            pr_gt2[1] = pr_gt2[0]
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
                        vals2pr[k][th] = np.round(np.interp([0.2],pr_vals2,pr_gt2,left=np.nan)[0],3)
                        vals2a[k][th] = np.round(np.interp([0.2],a_vals2,a_gt2,left=np.nan)[0],3)
                        vals2f[k][th] = np.round(np.interp([0.2],f_vals2,f_gt2,left=np.nan)[0],3)
                        vals2r[k][th] = np.round(np.interp([0.2],r_vals2,r_gt2,left=np.nan)[0],3)
                        vals2ri[k][th] = np.round(np.interp([0.2],ri_vals2,ri_gt2,left=np.nan)[0],3)
                        vals8p[k][th] = np.round(np.interp([0.8],p_vals8,p_gt8,right=np.nan)[0],3)
                        vals8pr[k][th] = np.round(np.interp([0.8],pr_vals8,pr_gt8,right=np.nan)[0],3)
                        vals8a[k][th] = np.round(np.interp([0.8],a_vals8,a_gt8,right=np.nan)[0],3) 
                        vals8f[k][th] = np.round(np.interp([0.8],f_vals8,f_gt8,right=np.nan)[0],3)
                        vals8r[k][th] = np.round(np.interp([0.8],r_vals8,r_gt8,right=np.nan)[0],3)
                        vals8ri[k][th] = np.round(np.interp([0.8],ri_vals8,ri_gt8,right=np.nan)[0],3)
                        flag_vals2p[k][th] = [p_vals2,p_gt2]
                        flag_vals2pr[k][th] = [pr_vals2,pr_gt2]
                        flag_vals2a[k][th] = [a_vals2,a_gt2]
                        flag_vals2f[k][th] = [f_vals2,f_gt2]
                        flag_vals2r[k][th] = [r_vals2,r_gt2]
                        flag_vals2ri[k][th] = [ri_vals2,ri_gt2]
                        flag_vals8p[k][th] = [p_vals8,p_gt8]
                        flag_vals8pr[k][th] = [pr_vals8,pr_gt8]
                        flag_vals8a[k][th] = [a_vals8,a_gt8]
                        flag_vals8f[k][th] = [f_vals8,f_gt8]
                        flag_vals8r[k][th] = [r_vals8,r_gt8]
                        flag_vals8ri[k][th] = [ri_vals8,ri_gt8]
                        tvalsp[k][th] = p_valst
                        tvalspr[k][th] = pr_valst
                        tvalsa[k][th] = a_valst
                        tvalsf[k][th] = f_valst
                        tvalsr[k][th] = r_valst
                        tvalsri[k][th] = ri_valst

                        key= (a,ag)
                        vals_dict[key] = {
                            "vals2p": flag_vals2p, "vals8p": flag_vals8p,
                            "vals2pr": flag_vals2pr, "vals8pr": flag_vals8pr,
                            "vals2a": flag_vals2a, "vals8a": flag_vals8a,
                            "vals2f": flag_vals2f, "vals8f": flag_vals8f,
                            "vals2r": flag_vals2r, "vals8r": flag_vals8r,
                            "vals2ri": flag_vals2ri, "vals8ri": flag_vals8ri,
                        }
                    ax[row][k].plot(np.arange(0.5,1.01,0.01),color='black',lw=5,ls=':')
                    ax[row][k].plot(vals2pr[k],color="red",lw=6,ls='--')
                    ax[row][k].plot(vals8pr[k],color="red",lw=6,ls='-')
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

                    tax[row][k].plot(tvalspr[k],color="red",lw=6)
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
                        for x in range(0,61,5):
                            void_str_tim.append('')
                    ax[row][k].set_xlim(0.5,1)
                    tax[row][k].set_xlim(0.5,0.9)
                    ax[row][k].set_ylim(0.5,1)
                    tax[row][k].set_yscale('log')
                    tax[row][k].set_ylim(1e0, 1e3)
                    tax[row][k].yaxis.set_tick_params(labelleft=True) if k == 0 else tax[row][k].yaxis.set_tick_params(labelleft=False)
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
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                        if row==0:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$T_c$")
                        elif row==1:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$T_c$")
                        elif row==2:
                            ax[row][k].set_ylabel(r"$G$")
                            tax[row][k].set_ylabel(r"$T_c$")
                    elif k==4:
                        ax[row][k].set_yticks(np.arange(.5,1.01,.1),labels=void_str_gt)
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
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
                        ax[row][k].set_yticks(np.arange(.5,1.01,.01),labels=void_str_threshlds,minor=True)
                    ax[row][k].grid(which='major')
                    tax[row][k].grid(which='major')

        fig.tight_layout()
        tfig.tight_layout()
        fig_path = path+_type+"_activation.pdf"
        tfig_path = path+t_type+"_time.pdf"
        fig.legend(bbox_to_anchor=(1, 0),handles=handles_r+handles_c,ncols=8, loc='upper right',framealpha=0.7,borderaxespad=0)
        tfig.legend(bbox_to_anchor=(1, 0),handles=handles_r,ncols=6,loc='upper right',framealpha=0.7,borderaxespad=0)
        fig.savefig(fig_path, bbox_inches='tight')
        tfig.savefig(tfig_path, bbox_inches='tight')
        plt.close(fig)
        plt.close(tfig)

        self.plot_protocol_tables(path, o_k, ground_T, threshlds, vals_dict)

##########################################################################################################
    def plot_protocol_tables(self, save_path, o_k, ground_T, threshlds, vals_dict):
        """
        Genera una tabella unica per ogni valore di o_k e protocollo, con valori v2 (rosso) e v8 (verde) nella stessa cella.
        """
        protocols = [
            ("anonymous_real_fifo", "pr"),
            ("anonymous", "p"),
            ("id_broad", "a"),
            ("id_rebroad_fifo", "f"),
            ("id_rebroad_rnd", "r"),
            ("id_rebroad_rnd_inf", "ri"),
        ]

        for (a, ag), proto_dict in vals_dict.items():
            for idx, ok_val in enumerate(o_k):
                fig, axes = plt.subplots(len(protocols), 1, figsize=(28, 84))
                if len(protocols) == 1:
                    axes = [axes]
                for p_idx, (title, suffix) in enumerate(protocols):
                    vals2 = proto_dict[f"vals2{suffix}"]
                    vals8 = proto_dict[f"vals8{suffix}"]
                    gt_unique = sorted(set(ground_T))[::-1]
                    cell_text = [[] for _ in gt_unique]
                    for j, thr in enumerate(threshlds):
                        for gt_idx, gt in enumerate(gt_unique):
                            v2_txt = ""
                            v8_txt = ""
                            # Cerca il valore v2
                            if gt in vals2[idx][j][1]:
                                pos = vals2[idx][j][1].index(gt)
                                v2 = vals2[idx][j][0][pos]
                                v2_txt = f"{v2:.2f}"
                            # Cerca il valore v8
                            if gt in vals8[idx][j][1]:
                                pos = vals8[idx][j][1].index(gt)
                                v8 = vals8[idx][j][0][pos]
                                v8_txt = f"{v8:.2f}"
                            # Unisci i valori nella stessa cella
                            if v2_txt and v8_txt:
                                if float(v2_txt) != float(v8_txt):
                                    cell_text[gt_idx].append("ERR")
                                else:
                                    cell_text[gt_idx].append(f"{v2_txt}_B")
                            elif v2_txt:
                                cell_text[gt_idx].append(f"{v2_txt}_L")
                            elif v8_txt:
                                cell_text[gt_idx].append(f"{v8_txt}_H")
                            else:
                                cell_text[gt_idx].append("")
                    table = axes[p_idx].table(
                        cellText=cell_text,
                        colLabels=[f"{t:.2f}" for t in threshlds],
                        rowLabels=[f"{gt:.2f}" for gt in gt_unique],
                        loc='center',
                        cellLoc='center'
                    )
                    axes[p_idx].set_title(f"{title} ({a}, {ag})")
                    axes[p_idx].axis('off')
                    table.auto_set_font_size(False)
                    table.set_fontsize(18)
                    table.scale(2.5, 4.0)
                    # Colora le celle: rosso se v2 presente, verde se v8 presente
                    for (i, j), cell in table.get_celld().items():
                        if i == 0 or j == -1:
                            continue
                        if i > 0 and j >= 0:
                            txt = cell.get_text().get_text()
                            if "_" in txt:
                                if txt.split('_')[-1] == "B":
                                    cell.get_text().set_text(txt.split("_B")[0])
                                    cell.set_facecolor("#ffae00")  # arancione
                                elif txt.split('_')[-1] == "L":
                                    cell.get_text().set_text(txt.split("_L")[0])
                                    cell.set_facecolor('#ffcccc')  # rosso
                                elif txt.split('_')[-1] == "H":
                                    cell.get_text().set_text(txt.split("_H")[0])
                                    cell.set_facecolor('#ccffcc')  # verde
                fig.tight_layout()
                fig.savefig(f"{save_path}protocol_tables_{a}_{ag}_buffer_{ok_val}.png", bbox_inches='tight')
                plt.close(fig)
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