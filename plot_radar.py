import csv_results as CSVres
import os
import numpy as np
import argparse

# Fallback sicuri per garantire la chiusura del radar in caso di mancate convergenze
WORST_M = 0.0
WORST_ACC = 0.0
WORST_TC = 900.0  
WORST_ER = 1.0     
WORST_TR = 900.0

def map_col(arena, n_agents):
    """Maps raw arena and agent counts to their respective scenario columns."""
    if arena == 'bigA' and str(n_agents) == '100': 
        return "HD100"
    elif arena == 'smallA' and str(n_agents) == '25': 
        return "HD25"
    elif arena == 'bigA' and str(n_agents) == '25': 
        return "LD25"
    return None

def get_protocol_id(algo, comm, msg_hops, min_buff_dim, n_agents, msg_time):
    # Forza maiuscolo per evitare KeyError quando i protocolli 'O' vengono letti come 'o'
    alg_upper = str(algo).strip().upper()
    if alg_upper == 'PS':
        return 'P.1.1'
    elif alg_upper == 'P':
        if int(min_buff_dim) == max(0, int(n_agents) - 2):
            return 'P.1.1'
        elif int(msg_time) > 0:
            return 'P.1.0'
        else:
            return 'P.0'
    else:
        return f"{alg_upper}.{int(comm)}.{int(msg_hops)}"

def main():
    parser = argparse.ArgumentParser(description="Generate radar plot grid synthesis for QS protocols.")
    parser.add_argument("--exclude-protocols", default="", help="Comma-separated protocol IDs to exclude")
    parser.add_argument("--exclude-tm", default="", help="Comma-separated Tm values to exclude")
    parser.add_argument("--short", default="", help="Use 's' command for short plot configurations")
    args = parser.parse_args()
    
    exclude_protocols = [s.strip() for s in args.exclude_protocols.split(",") if s.strip()]
    exclude_tm = [s.strip() for s in args.exclude_tm.split(",") if s.strip()]
    use_short = "s" in [s.strip() for s in args.short.split(",") if s.strip()]

    def _select_files(base_dir, keyword=""):
        selected = []
        if not os.path.exists(base_dir): 
            return selected
        for file in sorted(os.listdir(base_dir)):
            if "images" not in file and not file.startswith('.'):
                if keyword and keyword not in file:
                    continue
                selected.append(file)
        return selected

    csv_res = CSVres.Data()
    if use_short:
        csv_res._assign_config("short_plot_config.json")
        
    if exclude_protocols or exclude_tm:
        csv_res.apply_plot_overrides(
            ["radar"],
            exclude_protocols=exclude_protocols or None,
            exclude_tm=exclude_tm or None,
        )

    active_cols = ["LD25", "HD25", "HD100"]
    rows = [60, 120, 180, 300, 600]
    if exclude_tm:
        rows = [r for r in rows if str(r) not in exclude_tm]
        
    raw_data_grid = {tm: {col: {} for col in active_cols} for tm in rows}

    for tm in rows:
        for col in active_cols:
            for pid in csv_res.protocols_by_id.keys():
                raw_data_grid[tm][col][pid] = {'M': None, 'Acc': None, 'Tc': None, 'Er': None, 'Tr': None}

    # 1. Messaggi: Diversità media dei dati trattenuti (M) bypassando map imperfetto
    msg_base = os.path.join(csv_res.base, "msgs_data")
    tot_msgs = {}
    for file in _select_files(msg_base):
        file_path = os.path.join(msg_base, file)
        tot_msgs.update(csv_res.read_msgs_csv(file_path))
        
    if tot_msgs:
        for k, v_tuple in tot_msgs.items():
            # In messages_resume.csv, il 5° elemento è buff_dim (non msg_time_raw)
            # NO, buf_dim riporta i valori di T_m -> 0 indica che il protoclllo è P.0, per trovare la dimensione da plottare
            # bisogna prendere i valorui in data e normalizzarli su i valori in n_agents (a cui bisogna prima sottrarre 1)
            arena_val, algo, broadcast, ag_val_str, buff_dim_raw, msg_hops, mbs = k
            col_name = map_col(arena_val, ag_val_str)
            if not col_name: 
                continue
                
            alg_upper = str(algo).strip().upper()
            n_agents_int = int(ag_val_str)
            b_dim_int = int(float(buff_dim_raw)) if buff_dim_raw else 0

            # Identificazione diretta dei protocolli per i messaggi
            if alg_upper == 'PS' or (alg_upper == 'P' and b_dim_int == max(0, n_agents_int - 2)):
                pid = 'P.1.1'
            elif alg_upper == 'P':
                if b_dim_int > 0:
                    pid = 'P.1.0'
                else:
                    pid = 'P.0'
            else:
                pid = f"{alg_upper}.{int(broadcast)}.{int(msg_hops)}"

            if pid not in csv_res.protocols_by_id:
                continue
                
            v = v_tuple[0]
            if len(v) > 0:
                mean_M = np.mean(v) / (float(ag_val_str) - 1)
            else:
                mean_M = WORST_M
            
            if pid in ['P.0']:
                # P.0 non dipende da Tm: propaghiamo il valore su tutte le righe del radar
                for tm in rows:
                    raw_data_grid[tm][col_name][pid]['M'] = mean_M
            else:
                try:
                    # Per gli altri (O.x.x e P.1.0), in questi CSV buff_dim funge da Tm
                    tm = int(float(buff_dim_raw))
                except ValueError:
                    continue
                if tm in rows:
                    raw_data_grid[tm][col_name][pid]['M'] = mean_M
                    
    # 2. Accuratezza Proporzionale e Latenza Media
    proc_base = os.path.join(csv_res.base, "proc_data")
    tot_st, tot_times = [], []
    for file in _select_files(proc_base, "resume"):
        file_path = os.path.join(proc_base, file)
        no_ext_file = file.split('.')[0]
        sets = no_ext_file.split('_')
        algo = sets[0][0] if sets[0][1] == "a" or sets[0][1] == "r" else sets[0][0:2]
        n_runs, arena = 0, ''
        for s in sets:
            val = s.split('#')
            if len(val) > 1:
                if val[0] == 'r': n_runs = val[1]
                elif val[0] == 'a': arena = val[1]
        data = csv_res.read_csv(file_path, algo, n_runs, arena)
        keys, states, times = csv_res.divide_data(data)
        if len(tot_st) == 0:
            tot_st = [states]
            tot_times = [times]
        else:
            tot_st = np.append(tot_st, [states], axis=0)
            tot_times = np.append(tot_times, [times], axis=0)
            
    if len(tot_st) > 0:
        # Accumulatori per mediare le distribuzioni (G, tau)
        acc_accumulator = {tm: {col: {pid: [] for pid in csv_res.protocols_by_id} for col in active_cols} for tm in rows}
        tc_accumulator = {tm: {col: {pid: [] for pid in csv_res.protocols_by_id} for col in active_cols} for tm in rows}

        for states, times in zip(tot_st, tot_times):
            for k, v in states.items():
                algo, arena, n_runs, exp_time, comm, n_agents, gt, thrlds, min_buff_dim, msg_time, msg_hops, max_buff_size = k
                col_name = map_col(arena, n_agents)
                if not col_name: continue
                
                pid = get_protocol_id(algo, comm, msg_hops, min_buff_dim, n_agents, msg_time)
                if pid not in csv_res.protocols_by_id: continue
                
                gt_f = float(gt)
                tau_f = float(thrlds)
                
                if len(v[0]) > 0:
                    mean_Q = np.mean(v[0])
                    # Calcolo esatto proporzionale richiesto
                    accuracy = mean_Q if gt_f >= tau_f else (1.0 - mean_Q)
                    
                    latencies = times.get(k, ([], []))[0]
                    valid_latencies = [l for l in latencies if l > 0]
                    mean_Tc = np.mean(valid_latencies) if valid_latencies else WORST_TC
                    
                    if pid == 'P.0':
                        for tm in rows:
                            acc_accumulator[tm][col_name][pid].append(accuracy)
                            tc_accumulator[tm][col_name][pid].append(mean_Tc)
                    else:
                        try:
                            tm = int(float(msg_time))
                        except ValueError:
                            continue
                        if tm in rows:
                            acc_accumulator[tm][col_name][pid].append(accuracy)
                            tc_accumulator[tm][col_name][pid].append(mean_Tc)

        for tm in rows:
            for col in active_cols:
                for pid in csv_res.protocols_by_id.keys():
                    acc_list = acc_accumulator[tm][col][pid]
                    tc_list = tc_accumulator[tm][col][pid]
                    if acc_list:
                        raw_data_grid[tm][col][pid]['Acc'] = np.mean(acc_list)
                    if tc_list:
                        raw_data_grid[tm][col][pid]['Tc'] = np.mean(tc_list)

    # 3. Resilienza (Er) e Recovery Time (Tr)
    rec_base = os.path.join(csv_res.base, "rec_data")
    tot_rec = {}
    for file in _select_files(rec_base, "recovery_data"):
        file_path = os.path.join(rec_base, file)
        tot_rec.update(csv_res.read_fitted_recovery_csv(file_path))

    for key, value in tot_rec.items():
        alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = key[:10]
        
        if abs(float(gt) - float(th)) > 0.05: 
            continue
            
        pid = get_protocol_id(alg, broadcast, hops, buf, agents, msgs)
        if pid not in csv_res.protocols_by_id: 
            continue
            
        col_name = map_col(arena, agents)
        if not col_name: 
            continue

        mean_time = float(value[0])
        mean_events = float(value[2]) / float(agents) if len(value) > 2 else 0.0
        
        if pid == 'P.0':
            for tm in rows:
                if raw_data_grid[tm][col_name][pid]['Er'] is None:
                    raw_data_grid[tm][col_name][pid]['Er'] = []
                    raw_data_grid[tm][col_name][pid]['Tr'] = []
                raw_data_grid[tm][col_name][pid]['Er'].append(mean_events)
                raw_data_grid[tm][col_name][pid]['Tr'].append(mean_time)
        else:
            tm = int(msgs)
            if tm in rows:
                if raw_data_grid[tm][col_name][pid]['Er'] is None:
                    raw_data_grid[tm][col_name][pid]['Er'] = []
                    raw_data_grid[tm][col_name][pid]['Tr'] = []
                raw_data_grid[tm][col_name][pid]['Er'].append(mean_events)
                raw_data_grid[tm][col_name][pid]['Tr'].append(mean_time)

    # 4. Fallbacks strutturati e normalizzazione finale
    for tm in rows:
        for col in active_cols:
            for pid in csv_res.protocols_by_id.keys():
                if raw_data_grid[tm][col][pid]['M'] is None:
                    raw_data_grid[tm][col][pid]['M'] = WORST_M
                    
                if raw_data_grid[tm][col][pid]['Acc'] is None:
                    raw_data_grid[tm][col][pid]['Acc'] = WORST_ACC
                    
                if raw_data_grid[tm][col][pid]['Tc'] is None:
                    raw_data_grid[tm][col][pid]['Tc'] = WORST_TC

                if isinstance(raw_data_grid[tm][col][pid]['Er'], list):
                    lst = raw_data_grid[tm][col][pid]['Er']
                    raw_data_grid[tm][col][pid]['Er'] = np.mean(lst) if lst else WORST_ER
                elif raw_data_grid[tm][col][pid]['Er'] is None:
                    raw_data_grid[tm][col][pid]['Er'] = WORST_ER

                if isinstance(raw_data_grid[tm][col][pid]['Tr'], list):
                    lst = raw_data_grid[tm][col][pid]['Tr']
                    raw_data_grid[tm][col][pid]['Tr'] = np.mean(lst) if lst else WORST_TR
                elif raw_data_grid[tm][col][pid]['Tr'] is None:
                    raw_data_grid[tm][col][pid]['Tr'] = WORST_TR

    csv_res.process_and_plot_radar_grid(raw_data_grid, rows, active_cols)
    print("Radar grid synthesis successfully plotted in radar_data/images/")

if __name__ == "__main__":
    main()