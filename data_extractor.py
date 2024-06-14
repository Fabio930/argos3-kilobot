import numpy as np
import os, csv, math, sys

class Results:
    thresholds = {}
    ground_truth = [.52, .56, .60, .64, .68, .72, .76, .80, .84, .88, .92, .96, 1.0]
    min_buff_dim = 5
    ticks_per_sec = 10
    x_limit = 100
    limit = 0.8

    def __init__(self):
        self.bases = []
        self.base = os.path.abspath("")
        for elem in sorted(os.listdir(self.base)):
            if '.' not in elem:
                selem = elem.split('_')
                if selem[0] in ["Oresults", "Presults"]:
                    self.bases.append(os.path.join(self.base, elem))
        _thresholds = np.arange(50, 101) * 0.01
        for gt in self.ground_truth:
            self.thresholds[gt] = np.round(_thresholds, 2)

    def compute_quorum_vars_on_ground_truth(self, algo, m1, states, buf_lim, gt, gt_dim):
        print(f"--- Processing data {gt}/{gt_dim} ---")
        perc = 0
        compl = np.prod([len(states), len(states[0]), len(m1[0][0])])
        tmp_dim_0 = [[[] for _ in range(len(m1[0]))] for _ in range(len(states))]
        tmp_ones_0 = [[[] for _ in range(len(m1[0]))] for _ in range(len(states))]

        for i, state_row in enumerate(states):
            for j, state in enumerate(state_row):
                for t, m1_elem in enumerate(m1[j][i]):
                    dim = 1
                    ones = state
                    sys.stdout.write(f"\rProgress: {np.round((perc / compl) * 100, 3)}%")
                    sys.stdout.flush()
                    if algo == 'O':
                        for z, val in enumerate(m1_elem):
                            if val == -1:
                                break
                            dim += 1
                            ones += states[i][val]
                    else:
                        tmp = m1_elem[m1_elem != -1]
                        start = max(0, len(tmp) - buf_lim)
                        for z in tmp[start:]:
                            dim += 1
                            ones += states[i][z]
                    perc += 1
                    tmp_dim_0[i][j].append(dim)
                    tmp_ones_0[i][j].append(ones)
        print("\n")
        return tmp_dim_0, tmp_ones_0

    def compute_quorum(self, m1, m2, minus, threshold):
        perc = 0
        compl = np.prod(m1.shape)
        out = np.zeros_like(m1)

        for i in range(len(m1)):
            for j in range(len(m1[i])):
                for k in range(len(m1[i][j])):
                    sys.stdout.write(f"\rComputing results for threshold: {threshold} Progress: {np.round((perc / compl) * 100, 3)}%")
                    sys.stdout.flush()
                    perc += 1
                    out[i][j][k] = 1 if m1[i][j][k] - 1 >= minus and m2[i][j][k] >= threshold * m1[i][j][k] else 0
        return out

    def compute_meaningful_msgs(self, data, limit, algo, buf, buf_dim):
        print(f"--- Computing avg buffer dimension {buf}/{buf_dim} ---")
        perc = 0
        compl = np.prod([len(data), len(data[0]), len(data[0][0])])
        data_partial = []

        for ag in data:
            runs = []
            for rn in ag:
                tmp = [0] * len(rn[0])
                for tk, row in enumerate(rn):
                    sys.stdout.write(f"\rProgress: {np.round((perc / compl) * 100, 3)}%")
                    sys.stdout.flush()
                    flag = set()
                    for el in row:
                        if algo == 'P' and el >= limit:
                            break
                        if el not in flag and el != -1:
                            flag.add(el)
                            tmp[tk] += 1
                    perc += 1
                runs.append(tmp)
            data_partial.append(runs)

        msgs_summation = np.sum(data_partial, axis=(0, 1))
        msgs_summation = np.round(msgs_summation / len(data_partial) / len(data_partial[0]), 3)
        print("\n")
        return msgs_summation

    def extract_k_data(self, base, path_temp, max_steps, communication, n_agents, data_type="all"):
        max_buff_size = n_agents - 1
        for pre_folder in sorted(os.listdir(path_temp)):
            if '.' not in pre_folder:
                pre_params = pre_folder.split('#')
                msg_exp_time = int(pre_params[-1])
                sub_path = os.path.join(path_temp, pre_folder)
                act_results = {}
                num_runs = len(os.listdir(sub_path)) // n_agents
                msgs_bigM_1 = [None] * n_agents
                act_bigM_1 = [None] * n_agents
                act_bigM_2 = [None] * n_agents

                print(sub_path)
                print("--- Assign states ---")
                states_by_gt = [[] for _ in self.ground_truth]
                for gt, commit in enumerate(self.ground_truth):
                    runs_states = []
                    num_committed = math.ceil(n_agents * commit)
                    for _ in range(num_runs):
                        agents_state = np.random.choice([0, 1], size=n_agents, p=[1 - commit, commit])
                        runs_states.append(agents_state)
                    states_by_gt[gt] = runs_states

                print("--- Extract data ---")
                prev_id = -1
                for elem in sorted(os.listdir(sub_path)):
                    if '.' in elem:
                        selem = elem.split('.')
                        if selem[-1] == "tsv" and selem[0].split('_')[0] == "quorum":
                            seed = int(selem[0].split('#')[-1])
                            agent_id = int(selem[0].split('__')[0].split('#')[-1])
                            if prev_id != agent_id:
                                a_ = 0
                            if a_ == 0:
                                print("- Reading files of agent", agent_id)
                                prev_id = agent_id
                            with open(os.path.join(sub_path, elem), newline='') as f:
                                reader = csv.reader(f, delimiter='\t')
                                for log_count, row in enumerate(reader):
                                    if log_count % self.ticks_per_sec == 0:
                                        msgs = [int(val.split('\t')[0]) if '\t' in val else int(val) for val in row]
                                        broadcast_c, re_broadcast_c = map(int, row[-1].split('\t')[1:])
                                        if len(msgs) < max_buff_size:
                                            msgs.extend([-1] * (max_buff_size - len(msgs)))
                                        act_bigM_1[agent_id].append(broadcast_c)
                                        act_bigM_2[agent_id].append(re_broadcast_c)
                                        msgs_bigM_1[agent_id].append(msgs)
                            if len(msgs_bigM_1[agent_id]) != max_steps:
                                print(seed, len(msgs_bigM_1[agent_id]), len(msgs_bigM_1[agent_id][-1]))
                            if seed == num_runs:
                                msgs_bigM_1[agent_id] = np.array(msgs_bigM_1)
                                act_bigM_1[agent_id] = np.array(act_bigM_1)
                                act_bigM_2[agent_id] = np.array(act_bigM_2)

                if data_type == "all" or data_type == "quorum":
                    self.process_quorum_data(base, path_temp, msgs_bigM_1, states_by_gt, communication, n_agents, sub_path, msg_exp_time)

                act_results[0] = (act_bigM_1, act_bigM_2)
                if data_type == "all" or data_type == "freq":
                    self.dump_msg_freq(algo, 2, act_results, len(act_bigM_1), base, path_temp, msg_exp_time)
                print("--- Results saved ---\n")

    def process_quorum_data(self, base, path_temp, msgs_bigM_1, states_by_gt, communication, n_agents, sub_path, msg_exp_time):
        info_vec = sub_path.split('/')
        t_messages = sub_path.split('#')[-1]
        algo = info_vec[4].split('_')[0][0]
        arenaS = info_vec[4].split('_')[-1][:-1]
        BUFFERS = self.get_buffers(arenaS, n_agents)

        for buf in BUFFERS:
            messages = self.compute_meaningful_msgs(msgs_bigM_1, buf, algo, len(BUFFERS), len(BUFFERS))
            self.write_msgs_data("messages_resume.csv", [arenaS, algo, communication, n_agents, buf, messages])
            for gt in self.ground_truth:
                results = self.compute_quorum_vars_on_ground_truth(algo, msgs_bigM_1, states_by_gt[gt], buf, gt + 1,len(self.ground_truth))
                for thr in self.thresholds[gt]:
                    quorum_results = {}
                    states = self.compute_quorum(results[0], results[1], self.min_buff_dim, thr)
                    quorum_results[(gt, self.min_buff_dim, thr)] = (states, results[0])
                    self.dump_times(algo, 0, quorum_results, base, path_temp, gt, self.min_buff_dim, buf, self.limit)
                    self.dump_quorum_and_buffer(algo, 0, quorum_results, base, path_temp, gt, self.min_buff_dim, buf)
                print("\n")

    def get_buffers(self, arena_size, n_agents):
        if arena_size == 'small':
            return [20, 22, 23, 23.01, 24]
        elif arena_size == 'big':
            if n_agents == 25:
                return [11, 15, 17, 19, 21]
            elif n_agents == 100:
                return [41, 56, 65, 74, 83]
        return []

    def write_msgs_data(self, file_name, data):
        header = ["ArenaSize", "algo", "broadcast", "n_agents", "buff_dim", "data"]
        file_path = os.path.join(os.path.abspath(""), "msgs_data", file_name)
        write_header = not os.path.exists(file_path)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(header)
            fwriter.writerow(data)

    def dump_resume_csv(self, algo, indx, bias, value, data_in, data_std, base, path, COMMIT, THRESHOLD, MINS, MSG_EXP_TIME, n_runs):
        static_fields = ["CommittedPerc", "Threshold", "MinBuffDim", "MsgExpTime"]
        static_values = [COMMIT, THRESHOLD, MINS, MSG_EXP_TIME]
        file_name = f"{algo}average_resume_r#{n_runs}_a#{base.split('_')[-1]}.csv"
        file_path = os.path.join(os.path.abspath(""), "proc_data", file_name)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        write_header = not os.path.exists(file_path)
        
        name_fields, values = self.prepare_csv_fields(static_fields, static_values, base, path, indx, bias, value, data_in, data_std)
        
        with open(file_path, mode='a', newline='\n') as fw:
            fwriter = csv.writer(fw, delimiter='\t')
            if write_header:
                fwriter.writerow(name_fields)
            fwriter.writerow(values)

    def prepare_csv_fields(self, static_fields, static_values, base, path, indx, bias, value, data_in, data_std):
        tmp_b = base.split('/')
        tmp_p = path.split('/')
        name_fields = []
        values = []

        for i in tmp_p:
            if i not in tmp_b:
                tmp = i.split("#")
                name_fields.append(tmp[0])
                values.append(tmp[1])
        
        for field, val in zip(static_fields, static_values):
            name_fields.append(field)
            values.append(val)

        name_fields.extend(["type", "mean_value", "data", "std"])
        if indx + bias == -1:
            values.append("times")
        elif indx + bias == 0:
            values.append("swarm_state")
        elif indx + bias == 1:
            values.append("quorum_length")
        elif indx + bias == 2:
            values.append("broadcast_msg")
        elif indx + bias == 3:
            values.append("rebroadcast_msg")

        values.extend([value, data_in, data_std])
        return name_fields, values

    def dump_msg_freq(self, algo, bias, data_in, dMR, BASE, PATH, MSG_EXP_TIME):
        if algo == 'O':
            for l, multi_run_data in enumerate(data_in.get(0)):
                if multi_run_data is not None:
                    flag2 = np.mean(multi_run_data, axis=0).tolist()
                    fstd3 = [np.std([multi_run_data[j][i][z] for j in range(len(multi_run_data))]) for i in range(len(multi_run_data[0])) for z in range(len(multi_run_data[0][0]))]
                    self.dump_resume_csv(algo, l, bias, '-', np.round(flag2, 2).tolist(), np.round(fstd3, 3).tolist(), BASE, PATH, "-", "-", "-", MSG_EXP_TIME, dMR)

    def dump_quorum_and_buffer(self, algo, bias, data_in, BASE, PATH, COMMIT, MINS, MSG_EXP_TIME):
        for t in self.thresholds[COMMIT]:
            if data_in.get((COMMIT, MINS, t)) is not None:
                for l, multi_run_data in enumerate(data_in.get((COMMIT, MINS, t))):
                    if multi_run_data is not None:
                        mean_val = np.mean(multi_run_data, axis=(0, 1)).tolist()
                        flag2 = np.mean(multi_run_data, axis=0).tolist()
                        fstd3 = [np.std([multi_run_data[j][i][z] for j in range(len(multi_run_data))]) for i in range(len(multi_run_data[0])) for z in range(len(multi_run_data[0][0]))]
                        if l == 0:
                            self.dump_resume_csv(algo, l, bias, np.round(mean_val, 2), np.round(flag2, 2).tolist(), np.round(fstd3, 3).tolist(), BASE, PATH, COMMIT, t, MINS, MSG_EXP_TIME, len(multi_run_data))
                        else:
                            self.dump_resume_csv(algo, l, bias, '-', np.round(flag2, 2).tolist(), np.round(fstd3, 3).tolist(), BASE, PATH, COMMIT, t, MINS, MSG_EXP_TIME, len(multi_run_data))

    def dump_times(self, algo, bias, data_in, BASE, PATH, COMMIT, MINS, MSG_EXP_TIME, limit):
        for t in self.thresholds[COMMIT]:
            if data_in.get((COMMIT, MINS, t)) is not None:
                multi_run_data = data_in.get((COMMIT, MINS, t))[0]
                times = [len(multi_run_data[0][0])] * len(multi_run_data)
                for i, run_data in enumerate(multi_run_data):
                    for z, tick_data in enumerate(run_data[0]):
                        if sum(run_data[j][z] for j in range(len(run_data))) >= limit * len(run_data):
                            times[i] = z
                            break
                self.dump_resume_csv(algo, -1, bias, '-', sorted(times), '-', BASE, PATH, COMMIT, t, MINS, MSG_EXP_TIME, len(multi_run_data))

    def extract_median(self, array):
        sortd_arr = np.sort(array)
        if len(sortd_arr) % 2 == 0:
            median = (sortd_arr[len(sortd_arr) // 2 - 1] + sortd_arr[len(sortd_arr) // 2]) * 0.5
        else:
            median = sortd_arr[len(sortd_arr) // 2]
        return median