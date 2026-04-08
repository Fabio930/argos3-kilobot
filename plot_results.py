import os, logging, argparse
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
        return None
    tot_msgs = {}
    for file in sorted(os.listdir(msgs_path)):
        if "images" not in file:
            file_path = os.path.join(msgs_path, file)
            data = csv_res.read_msgs_csv(file_path)
            tot_msgs.update(data)
    return tot_msgs

##################################################################################
def _plot_proc_data(csv_res, proc_st, proc_times, mode):
    if mode == "diff":
        o_k = []
        for lst in proc_st.values():
            for states in lst:
                for k in states.keys():
                    m_t = int(k[9])
                    if m_t != 0 and m_t not in o_k:
                        o_k.append(m_t)
        csv_res.plot_active_w_gt_thr_diff(proc_st, proc_times)
    else:
        csv_res.plot_active_w_gt_thr(proc_st, proc_times)

##################################################################################
def _plot_msgs_data(csv_res, msgs, mode):
    if mode == "diff":
        csv_res.plot_messages_diff(msgs)
    else:
        csv_res.plot_messages(msgs)

##################################################################################
def main():
    parser = argparse.ArgumentParser(description="Plot results with configurable mode.")
    parser.add_argument("--mode", default="default", help="Operation mode (default, diff)")
    parser.add_argument("--short", action="store_true", help="Genera i grafici uniti in modalità short")
    parser.add_argument("--exclude-protocols", default="", help="Comma-separated protocol IDs to exclude")
    parser.add_argument("--exclude-tm", default="", help="Comma-separated Tm values to exclude")
    args = parser.parse_args()
    
    mode_arg = args.mode.strip().lower()
    mode = "short" if args.short or mode_arg == "short" else mode_arg
    
    exclude_protocols = [s.strip() for s in args.exclude_protocols.split(",") if s.strip()]
    exclude_tm = [s.strip() for s in args.exclude_tm.split(",") if s.strip()]

    csv_res = CSVres.Data(mode=mode)
    
    if exclude_protocols or exclude_tm:
        csv_res.apply_plot_overrides(
            ["all"],
            exclude_protocols=exclude_protocols or None,
            exclude_tm=exclude_tm or None,
        )
    
    if mode == "short":
        tot_st = []
        dict_msgs = {}
        
        for base in csv_res.bases:
            if os.path.basename(base) == "proc_data":
                tot_st, _ = _collect_proc_data(csv_res, base, exclude_protocols)
            elif os.path.basename(base) == "msgs_data":
                msgs = _collect_msgs_data(csv_res, base)
                if msgs:
                    dict_msgs.update(msgs)
                        
        if len(tot_st) > 0 and dict_msgs:
            csv_res.plot_short(tot_st, dict_msgs)
        else:
            print("Attenzione: per la modalità short servono dati sia da proc_data che da msgs_data.")

    elif mode == "diff":
        dict_proc_st = {}
        dict_proc_times = {}
        dict_msgs = {}
        
        for folder_cfg in csv_res.bases_diff:
            root_name = folder_cfg.get("root_name")
            proc_data_path = folder_cfg.get("proc_data")
            msgs_data_path = folder_cfg.get("msgs_data")
            
            if proc_data_path:
                proc_st, proc_times = _collect_proc_data(csv_res, proc_data_path, exclude_protocols)
                if len(proc_st) > 0:
                    dict_proc_st[root_name] = proc_st
                    dict_proc_times[root_name] = proc_times

            if msgs_data_path:
                msgs = _collect_msgs_data(csv_res, msgs_data_path)
                if msgs:
                    dict_msgs[root_name] = msgs

        if dict_proc_st:
            _plot_proc_data(csv_res, dict_proc_st, dict_proc_times, mode)
        if dict_msgs:
            _plot_msgs_data(csv_res, dict_msgs, mode)

    else:
        for base in csv_res.bases:
            if os.path.basename(base) == 'proc_data':
                proc_st, proc_times = _collect_proc_data(csv_res, base, exclude_protocols)
                if len(proc_st) > 0:
                    _plot_proc_data(csv_res, proc_st, proc_times, mode)
            elif os.path.basename(base) == 'msgs_data':
                msgs = _collect_msgs_data(csv_res, base)
                if msgs:
                    _plot_msgs_data(csv_res, msgs, mode)

if __name__ == "__main__":
    main()