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
    arena_base = str(arena).strip().replace('A', '')
    if arena_base == 'big' and str(n_agents) == '100': 
        return "HD100"
    elif arena_base == 'small' and str(n_agents) == '25': 
        return "HD25"
    elif arena_base == 'big' and str(n_agents) == '25': 
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
                # Applica la divisione (n_agents - 1) su tutti i 900 valori, poi estrae la media
                norm_factor = float(ag_val_str) - 1.0
                if norm_factor > 0:
                    v_array = np.array(v) / norm_factor
                    mean_M = float(np.mean(v_array))
                else:
                    mean_M = WORST_M
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
    # 2. Accuratezza (Isolinee) e Latenza Media
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
        # Matrice per raggruppare i valori Q e T in base a (tau, gt) per l'interpolazione
        acc_matrix = {tm: {col: {pid: {} for pid in csv_res.protocols_by_id} for col in active_cols} for tm in rows}
        time_matrix = {tm: {col: {pid: {} for pid in csv_res.protocols_by_id} for col in active_cols} for tm in rows}

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
                    latencies = times.get(k, ([], []))[0]
                    # La mediana corrisponde alla logica di print_active e print_borders
                    median_Tc = np.median(latencies) if len(latencies) > 0 else WORST_TC
                    
                    if pid == 'P.0':
                        tms_to_update = rows
                    else:
                        try:
                            tms_to_update = [int(float(msg_time))] if int(float(msg_time)) in rows else []
                        except ValueError:
                            tms_to_update = []

                    for tm in tms_to_update:
                        # Raggruppamento per l'accuratezza e i tempi associati
                        if tau_f not in acc_matrix[tm][col_name][pid]:
                            acc_matrix[tm][col_name][pid][tau_f] = {}
                            time_matrix[tm][col_name][pid][tau_f] = {}
                        if gt_f not in acc_matrix[tm][col_name][pid][tau_f]:
                            acc_matrix[tm][col_name][pid][tau_f][gt_f] = []
                            time_matrix[tm][col_name][pid][tau_f][gt_f] = []
                        acc_matrix[tm][col_name][pid][tau_f][gt_f].append(mean_Q)
                        time_matrix[tm][col_name][pid][tau_f][gt_f].append(median_Tc)

        # Processamento delle matrici accumulate
        for tm in rows:
            for col in active_cols:
                for pid in csv_res.protocols_by_id.keys():
                    
                    tau_dict = acc_matrix[tm][col][pid]
                    t_dict = time_matrix[tm][col][pid]
                    if not tau_dict:
                        continue
                        
                    total_error = 0.0
                    valid_taus_count = 0
                    
                    valid_times = []
                    
                    for tau, gt_dict in tau_dict.items():
                        gts = np.array(sorted(gt_dict.keys()))
                        Qs = np.array([np.mean(gt_dict[g]) for g in gts])
                        
                        # Estrazione del tempo corrispondente alla logica del bordo
                        # In print_borders, si registra il tempo quando Q raggiunge 0.8 e (gt - tau) è minimizzato oltre 0.09
                        valst, lim_valst = np.nan, np.nan
                        
                        vals2, vals8, gt2, gt8 = [np.nan]*2, [np.nan]*2, [np.nan]*2, [np.nan]*2
                        
                        for idx in range(len(gts)):
                            val = Qs[idx]
                            current_gt = gts[idx]
                            
                            tval = np.median(t_dict[tau][current_gt])
                            
                            if val >= 0.8:
                                # Calcolo tempo associato (Replica logica print_borders)
                                if current_gt - tau >= 0.09 and (np.isnan(valst) or current_gt - tau < lim_valst):
                                    valst, lim_valst = tval, current_gt - tau
                                    
                                if current_gt - tau >= 0 and (np.isnan(vals8[1]) or val < vals8[1]):
                                    vals8[1], gt8[1] = val, current_gt
                            elif val <= 0.2:
                                if current_gt - tau <= 0 and (np.isnan(vals2[0]) or val >= vals2[0]):
                                    vals2[0], gt2[0] = val, current_gt
                            else:
                                if np.isnan(vals8[0]) or val > vals8[0]: vals8[0], gt8[0] = val, current_gt
                                if np.isnan(vals2[1]) or val < vals2[1]: vals2[1], gt2[1] = val, current_gt

                        if np.isnan(vals8[0]): vals8[0], gt8[0] = vals8[1], gt8[1]
                        elif np.isnan(vals8[1]): vals8[1], gt8[1] = vals8[0], gt8[0]
                        if np.isnan(vals2[0]): vals2[0], gt2[0] = vals2[1], gt2[1]
                        elif np.isnan(vals2[1]): vals2[1], gt2[1] = vals2[0], gt2[0]
                        
                        v2_interp = np.interp([0.2], vals2, gt2, left=np.nan)[0]
                        v8_interp = np.interp([0.8], vals8, gt8, right=np.nan)[0]
                        
                        error_v2 = abs(v2_interp - tau) if not np.isnan(v2_interp) else 0.5
                        error_v8 = abs(v8_interp - tau) if not np.isnan(v8_interp) else 0.5
                        
                        total_error += (error_v2 + error_v8)
                        valid_taus_count += 1
                        
                        # Memorizza il tempo di completamento per questa soglia
                        if not np.isnan(valst):
                            valid_times.append(valst)
                        
                    if valid_taus_count > 0:
                        mean_error = total_error / valid_taus_count
                        accuracy = max(0.0, min(1.0, 1.0 - mean_error))
                        raw_data_grid[tm][col][pid]['Acc'] = accuracy
                        
                    if valid_times:
                        raw_data_grid[tm][col][pid]['Tc'] = np.mean(valid_times)

    # 3. Resilienza (Er) e Recovery Time (Tr)
    rec_base = os.path.join(csv_res.base, "rec_data")
    tot_rec = {}
    for file in _select_files(rec_base, "recovery_data"):
        file_path = os.path.join(rec_base, file)
        tot_rec.update(csv_res.read_fitted_recovery_csv(file_path))

    for key, value in tot_rec.items():
        alg, arena, time, broadcast, agents, buf, msgs, hops, gt, th = key[:10]
        
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
                    
                # Normalise Tc: linear (1s -> 1.0, 900s -> 0.0)
                tc_val = raw_data_grid[tm][col][pid]['Tc']
                if tc_val is None:
                    raw_data_grid[tm][col][pid]['Tc'] = 0.0
                else:
                    raw_data_grid[tm][col][pid]['Tc'] = max(0.0, min(1.0, (900.0 - tc_val) / 899.0))

                # Normalise Er: logarithmic (0 errors -> 1.0, 900 errors -> 0.0)
                er_list = raw_data_grid[tm][col][pid]['Er']
                if isinstance(er_list, list) and er_list:
                    mean_er = np.mean(er_list)
                    # Use Er + 1 to avoid log10(0), max bounds become log10(901)
                    raw_data_grid[tm][col][pid]['Er'] = max(0.0, min(1.0, 1.0 - (np.log10(mean_er + 1.0) / np.log10(901.0))))
                else:
                    raw_data_grid[tm][col][pid]['Er'] = 0.0

                # Normalise Tr: logarithmic (1s -> 1.0, 900s -> 0.0)
                tr_list = raw_data_grid[tm][col][pid]['Tr']
                if isinstance(tr_list, list) and tr_list:
                    mean_tr = np.mean(tr_list)
                    if mean_tr < 1.0: 
                        mean_tr = 1.0
                    raw_data_grid[tm][col][pid]['Tr'] = max(0.0, min(1.0, 1.0 - (np.log10(mean_tr) / np.log10(900.0))))
                else:
                    raw_data_grid[tm][col][pid]['Tr'] = 0.0
    csv_res.process_and_plot_radar_grid(raw_data_grid, rows, active_cols)
    print("Radar grid synthesis successfully plotted in radar_data/images/")

if __name__ == "__main__":
    main()