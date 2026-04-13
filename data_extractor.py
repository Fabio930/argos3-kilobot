import os, csv, gc, sys, re
import numpy as np
from pathlib import Path

class Results:
    min_buff_dim = 5
    ticks_per_sec = 10
    x_limit = 100
    limit = 0.8
    FILE_RE = re.compile(r"agent#(?P<agent>\d+).*?run#(?P<run>\d+)")
        
##########################################################################################################
    def __init__(self):
        self.bases=[]
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem=elem.split('_')
                if selem[0] in ("Oresults","Presults", "Psresults") and selem[-1] in ("smallA","bigA"):
                    self.bases.append(os.path.join(self.base, elem))

##########################################################################################################
    def _norm_idx(self, raw_id: int, size: int, name: str) -> int:
        # Accept both 0-based and 1-based indices
        if 0 <= raw_id < size:
            return raw_id
        if 1 <= raw_id <= size:
            return raw_id - 1
        raise ValueError(f"{name} id out of range: {raw_id} (size={size})")
    
##########################################################################################################
    def compute_avg_msgs(self,data):
        print("--- Computing avg buffer dimension ---")
        if isinstance(data, np.ndarray):
            if data.size == 0:
                return []
            return np.mean(data, axis=(0,1)).tolist()
        out = [0]*len(data[0][0])
        for i in range(len(data)):
            for j in range(len(data[i])):
                for t in range(len(data[i][j])):
                    out[t]+=data[i][j][t]
        for t in range(len(out)):
            out[t] = out[t]/(len(data)*len(data[0]))
        return out
    
##########################################################################################################
    def extract_k_data(self,base,path_temp,max_steps,communication,n_agents,threshold,delta,msg_exp_time,msg_hops,k_sampling,sub_path):
        files = [fp for fp in sorted(Path(sub_path).glob("*.tsv")) if self.FILE_RE.search(fp.stem)]
        num_runs = int(len(files)/n_agents)
        state_m = np.zeros((num_runs, n_agents, max_steps), dtype=np.int16)
        quorum_m = np.zeros((num_runs, n_agents, max_steps), dtype=np.int16)
        msgs_m = np.zeros((num_runs, n_agents, max_steps), dtype=np.int32)
        loaded = np.zeros((num_runs, n_agents), dtype=bool)

        for fp in files:
            m = self.FILE_RE.search(fp.stem)
            if not m:
                continue
            agent_raw = int(m.group("agent"))
            run_raw = int(m.group("run"))
            agent_id = self._norm_idx(agent_raw, n_agents, "agent")
            seed = self._norm_idx(run_raw, num_runs, "run")

            sampled = np.loadtxt(fp, delimiter="\t", ndmin=2)
            if sampled.ndim == 1:
                sampled = sampled.reshape(1, -1)
            if sampled.shape[1] < 3:
                print(fp, "bad columns:", sampled.shape[1])
                sys.exit(0)
            if self.ticks_per_sec > 1:
                sampled = sampled[self.ticks_per_sec-1::self.ticks_per_sec]
            n_rows = sampled.shape[0]
            if n_rows > max_steps:
                print(sub_path,'\n',"run:",run_raw,"agent:",agent_raw,"tot lines:",n_rows)
                sys.exit(0)
            start = max_steps - n_rows
            if n_rows > 0:
                state_m[seed, agent_id, start:] = sampled[:,0].astype(np.int16, copy=False)
                quorum_m[seed, agent_id, start:] = sampled[:,1].astype(np.int16, copy=False)
                msgs_m[seed, agent_id, start:] = sampled[:,2].astype(np.int32, copy=False)
            loaded[seed, agent_id] = True
        algo    = ""
        arenaS  = ""
        info_vec    = sub_path.split('/')
        for iv in info_vec:
            if "results_loop" in iv:
                if iv.startswith("Psresults"):
                    algo = "Ps"
                elif iv.startswith("Presults"):
                    algo = "P"
                elif iv.startswith("Oresults"):
                    algo = "O"
                else:
                    algo = iv.split("results")[0]
                arenaS      = iv.split('_')[-1][:-1]
                break
        t_messages  = info_vec[-3].split('#')[-1]
        messages    = self.compute_avg_msgs(msgs_m)
        self.dump_msgs("messages_resume.csv", [arenaS, algo, threshold, delta, communication, msg_hops, n_agents, k_sampling, t_messages, messages])
        states = quorum_m
        self.dump_times(algo,0,states,base,path_temp,threshold,delta,self.min_buff_dim,msg_exp_time,msg_hops,k_sampling,n_agents,self.limit)
        self.dump_quorum(algo,0,states,base,path_temp,threshold,delta,self.min_buff_dim,msg_exp_time,msg_hops,k_sampling,n_agents)
        del state_m,quorum_m,msgs_m,loaded,messages,states
        gc.collect()

##########################################################################################################
    def dump_msgs(self, file_name, data):
        header = ["ArenaSize", "algo", "threshold", "delta_GT", "broadcast","msg_hops", "n_agents", "k_sampling", "buff_dim", "data"]
        write_header = not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data", file_name))
        
        if not os.path.exists(os.path.join(os.path.abspath(""), "msgs_data")):
            os.mkdir(os.path.join(os.path.abspath(""), "msgs_data"))
        
        with open(os.path.join(os.path.abspath(""), "msgs_data", file_name), mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow(data)

##########################################################################################################
    def dump_resume_csv(self,algo,indx,bias,data_in,data_std,base,path,MINS,MSG_EXP_TIME,msg_hops,k_sampling,n_runs):    
        static_fields=["MinBuffDim","MsgExpTime","MsgHops","KSampling"]
        static_values=[MINS,MSG_EXP_TIME,msg_hops,k_sampling]
        if not os.path.exists(os.path.abspath("")+"/proc_data"):
            os.mkdir(os.path.abspath("")+"/proc_data")
        write_header = 0
        name_fields = []
        values = []
        if algo == 'O':
            file_name = "Oaverage_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
        elif algo == 'P':
            file_name = "Paverage_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
        elif algo == 'Ps':
            file_name = "Psaverage_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
        else:
            file_name = str(algo)+"average_resume_r#"+str(n_runs)+"_a#"+base.split('_')[-1]+".csv"
            
        if not os.path.exists(os.path.abspath("")+"/proc_data/"+file_name):
            write_header = 1
        tmp_b = base.split('/')
        tmp_p = path.split('/')
        for i in tmp_p:
            if i not in tmp_b:
                tmp = i.split("#")
                name_fields.append(tmp[0])
                values.append(tmp[1])
        for i in range(len(static_fields)):
            name_fields.append(static_fields[i])
            values.append(static_values[i])
        name_fields.append("type")
        name_fields.append("data")
        name_fields.append("std")
        if indx+bias==-1:
            values.append("times")
        elif indx+bias==0:
            values.append("swarm_state")
        elif indx+bias==1:
            values.append("broadcast_msg")
        elif indx+bias==2:
            values.append("rebroadcast_msg")
        elif indx+bias==3:
            values.append("do_nothing_buffer")
        elif indx+bias==4:
            values.append("insert_buffer")
        elif indx+bias==5:
            values.append("update_buffer")
        values.append(data_in)
        values.append(data_std)
        fw = open(os.path.abspath("")+"/proc_data/"+file_name,mode='a',newline='\n')
        fwriter = csv.writer(fw,delimiter='\t')
        if write_header == 1:
            fwriter.writerow(name_fields)
        fwriter.writerow(values)
        fw.close()

##########################################################################################################
    def dump_sumof(self,algo,bias,data_in,dMR,BASE,PATH,MSG_EXP_TIME,msg_hops,k_sampling):
        for l in range(len(data_in)):
            multi_run_data = data_in[l]
            flag2 = [-1]*len(multi_run_data[0][0])
            for i in range(len(multi_run_data[0])):
                flag1 = [-1]*len(multi_run_data[0][0])
                for j in range(len(multi_run_data)):
                    for z in range(len(multi_run_data[j][i])):
                        if flag1[z]==-1:
                            flag1[z]=float(multi_run_data[j][i][z])
                        else:
                            flag1[z]=flag1[z]+float(multi_run_data[j][i][z])
                for j in range(len(flag1)):
                    flag1[j]=flag1[j]/len(multi_run_data)
                    if flag2[j]==-1:
                        flag2[j]=flag1[j]
                    else:
                        flag2[j]=flag1[j]+flag2[j]
            for i in range(len(flag2)):
                flag2[i]=flag2[i]/len(multi_run_data[0])
            self.dump_resume_csv(algo,l,bias,np.round(flag2,2).tolist(),"-",BASE,PATH,"-",MSG_EXP_TIME,msg_hops,k_sampling,dMR)

##########################################################################################################
    def dump_quorum(self,algo,bias,data_in,BASE,PATH,THR,COMMIT,MINS,MSG_EXP_TIME,msg_hops,k_sampling,n_agents):
        if isinstance(data_in, np.ndarray):
            if data_in.size == 0:
                return
            flag2 = np.mean(data_in, axis=(0,1))
            std_per_run = np.std(data_in, axis=1)
            fstd3 = np.median(std_per_run, axis=0)
            self.dump_resume_csv(algo,0,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,MINS,MSG_EXP_TIME,msg_hops,k_sampling,len(data_in))
            return
        flag2=[-1]*len(data_in[0][0])
        for i in range(len(data_in)):
            flag1=[-1]*len(data_in[i][0])
            for j in range(len(data_in[i])):
                for z in range(len(data_in[i][j])):
                    if flag1[z]==-1:
                        flag1[z]=data_in[i][j][z]
                    else:
                        flag1[z]=flag1[z]+data_in[i][j][z]
            for j in range(len(flag1)):
                flag1[j]=flag1[j]/len(data_in[i])
                if flag2[j]==-1:
                    flag2[j]=flag1[j]
                else:
                    flag2[j]=flag1[j]+flag2[j]
        for i in range(len(flag2)):
            flag2[i]=flag2[i]/len(data_in)
        fstd2=[[-1]*len(data_in[0][0])]*len(data_in)
        fstd3=[-1]*len(data_in[0][0])
        for i in range(len(data_in)):
            fstd1=[-1]*len(data_in[i][0])
            for z in range(len(data_in[i][0])): # per ogni tick
                std_tmp = []
                for j in range(len(data_in[i])): # per ogni agente
                    std_tmp.append(float(data_in[i][j][z]))
                fstd1[z]=np.std(std_tmp)
            fstd2[i]=fstd1
        for z in range(len(fstd3)):
            median_array = []
            for i in range(len(fstd2)):
                median_array.append(fstd2[i][z])
            fstd3[z]=np.median(median_array)
        self.dump_resume_csv(algo,0,bias,np.round(flag2,2).tolist(),np.round(fstd3,3).tolist(),BASE,PATH,MINS,MSG_EXP_TIME,msg_hops,k_sampling,len(data_in))

##########################################################################################################
    def dump_times(self,algo,bias,data_in,BASE,PATH,THR,COMMIT,MINS,MSG_EXP_TIME,msg_hops,k_sampling,n_agents,limit):
        if isinstance(data_in, np.ndarray):
            if data_in.size == 0:
                return
            n_steps = data_in.shape[2]
            sums = np.sum(data_in, axis=1)
            thresh = limit * data_in.shape[1]
            mask = sums >= thresh
            times = np.where(mask.any(axis=1), mask.argmax(axis=1), n_steps).tolist()
            times = sorted(times)
            self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,MINS,MSG_EXP_TIME,msg_hops,k_sampling,len(data_in))
            return
        times = [len(data_in[0][0])] * len(data_in)
        for i in range(len(data_in)): # per ogni run
            for z in range(len(data_in[i][0])): # per ogni tick
                sum = 0
                for j in range(len(data_in[i])): # per ogni agente
                    sum += data_in[i][j][z]
                if sum >= limit * len(data_in[i]):
                    times[i] = z
                    break
        times = sorted(times)
        self.dump_resume_csv(algo,-1,bias,times,'-',BASE,PATH,MINS,MSG_EXP_TIME,msg_hops,k_sampling,len(data_in))