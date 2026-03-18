import os, logging, argparse, json
import csv_results as CSVres
import numpy as np

logging.getLogger('matplotlib').setLevel(logging.WARNING)

##################################################################################
def _collect_proc_data(csv_res, proc_path, exclude_protocols=None):
    if not os.path.isdir(proc_path):
        return [], []
    tot_st = []
    tot_times = []
    for file in sorted(os.listdir(proc_path)):
        if "images" in file:
            continue
        n_runs = 0
        arena = ""
        file_path = os.path.join(proc_path, file)
        no_ext_file = file.split('.')[0]
        sets = no_ext_file.split('_')
        algo = sets[0][0] if len(sets[0]) > 1 and (sets[0][1] == "a" or sets[0][1] == "r") else sets[0][0:2]
        for s in sets:
            val = s.split('#')
            if len(val) > 1:
                if val[0] == 'r':
                    n_runs = val[1]
                elif val[0] == 'a':
                    arena = val[1]
        data = csv_res.read_csv(file_path, algo, n_runs, arena)
        _, states, times = csv_res.divide_data(data)
        if exclude_protocols:
            states = {k: v for k, v in states.items() if k[0] not in exclude_protocols}
            times = {k: v for k, v in times.items() if k[0] not in exclude_protocols}
        if len(tot_st) == 0:
            tot_st = [states]
            tot_times = [times]
        else:
            tot_st = np.append(tot_st, [states], axis=0)
            tot_times = np.append(tot_times, [times], axis=0)
    return tot_st, tot_times

##################################################################################
def _collect_msgs_data(csv_res, msgs_path):
    if not os.path.isdir(msgs_path):
        return []
    data_list = []
    for file in sorted(os.listdir(msgs_path)):
        if "images" in file:
            continue
        file_path = os.path.join(msgs_path, file)
        data_list.append(csv_res.read_msgs_csv(file_path))
    return data_list

##################################################################################
def _plot_proc_data(csv_res, tot_st, tot_times, mode):
    if len(tot_st) == 0:
        return
    if mode == 'diff':
        csv_res.plot_active_w_gt_thr_diff(tot_st, tot_times)
    else:
        csv_res.plot_active_w_gt_thr(tot_st, tot_times)

##################################################################################
def _plot_msgs_data(csv_res, data_list, mode):
    if not data_list:
        return
    if mode == 'diff':
        csv_res.plot_messages_diff(data_list)
    else:
        for data in data_list:
            csv_res.plot_messages(data)

##################################################################################
def main():
    parser = argparse.ArgumentParser(description='Plot ARGoS kilobot experiment results')
    parser.add_argument('--mode', choices=['default', 'diff'], default='default', help='Plot mode to use')
    args = parser.parse_args()
    mode = args.mode

    csv_res = CSVres.Data()

    if mode == 'diff':
        json_path = os.path.join(csv_res.base, 'diff_plot_config.json')
        if not os.path.exists(json_path):
            logging.error('diff mode: config %s not found', json_path)
            return
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
        except Exception as e:
            logging.error('diff mode: unable to read %s (%s)', json_path, e)
            return

        # Collezioniamo i dati in dizionari usando il nome della root come chiave
        dict_proc_st = {}
        dict_proc_times = {}
        dict_msgs = {}

        for folder in cfg.get('folders', []):
            root = folder.get('root')
            if not root:
                continue
            
            # Identifichiamo il nome della root (es. 'exp_01')
            root_name = os.path.basename(root.rstrip(os.sep))
            root_path = os.path.abspath(os.path.join(csv_res.base, root)) if not os.path.isabs(root) else root
            
            # Proc Data
            proc_st, proc_times = _collect_proc_data(csv_res, os.path.join(root_path, 'proc_data'))
            if len(proc_st) > 0:
                dict_proc_st[root_name] = proc_st
                dict_proc_times[root_name] = proc_times

            # Msgs Data
            msgs = _collect_msgs_data(csv_res, os.path.join(root_path, 'msgs_data'))
            if msgs:
                dict_msgs[root_name] = msgs

        # Passiamo i dizionari alle funzioni di plot
        _plot_proc_data(csv_res, dict_proc_st, dict_proc_times, mode)
        _plot_msgs_data(csv_res, dict_msgs, mode)

    else:
        # Porzione originale invariata per il default mode
        for base in csv_res.bases:
            if os.path.basename(base) == 'proc_data':
                proc_st, proc_times = _collect_proc_data(csv_res, base)
                _plot_proc_data(csv_res, proc_st, proc_times, mode)
            elif os.path.basename(base) == 'msgs_data':
                msgs = _collect_msgs_data(csv_res, base)
                _plot_msgs_data(csv_res, msgs, mode)

##################################################################################
if __name__ == "__main__":
    main()