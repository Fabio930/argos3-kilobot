import os
import argparse
import csv_results as CSVres

##################################################################################
def main():
    parser = argparse.ArgumentParser(description="Plot results with optional protocol/Tm exclusions.")
    parser.add_argument("--exclude-protocols", default="", help="Comma-separated protocol IDs to exclude (e.g. P.0,O.2.0)")
    parser.add_argument("--exclude-tm", default="", help="Comma-separated Tm values to exclude (e.g. 60,120)")
    
    parser.add_argument("--short", nargs='?', const="combined", default=False, 
                        help="Usa '--short' per uniti (3x3), oppure '--short split_interface' per dividere LI e SI.")
    args = parser.parse_args()
    
    exclude_protocols = [s.strip() for s in args.exclude_protocols.split(",") if s.strip()]
    exclude_tm = [s.strip() for s in args.exclude_tm.split(",") if s.strip()]

    csv_res = CSVres.Data(use_short=bool(args.short))
    
    # Applichiamo le regole di esclusione in modo globale
    if exclude_protocols or exclude_tm:
        csv_res.apply_plot_overrides(
            ["all"],
            exclude_protocols=exclude_protocols or None,
            exclude_tm=exclude_tm or None,
        )
    tot_st      = []
    tot_times   = []
    tot_stbc    = []
    tot_msgs    = {}
    
    for base in csv_res.bases:
        folder = os.path.basename(base)
        
        if folder == "proc_data":
            for file in sorted(os.listdir(base)):
                n_runs = 0
                if "images" not in file:
                    file_path = os.path.join(base, file)
                    no_ext_file = file.split('.')[0]
                    sets = no_ext_file.split('_')
                    algo = sets[0][0]
                    if sets[0].startswith("Ps"):
                        algo = "Ps"
                    
                    for s in sets:
                        val = s.split('#')
                        if len(val) > 1 and val[0] == 'r':
                            n_runs = val[1]
                                
                    data = csv_res.read_csv(file_path, algo, n_runs)
                    keys, states, times, states_by_commit = csv_res.divide_data(data)     
                    
                    tot_st.append(states)
                    tot_stbc.append(states_by_commit)
                    tot_times.append(times)
                    
        elif folder == "msgs_data":
            for file in sorted(os.listdir(base)):
                if "images" not in file:
                    file_path = os.path.join(base, file)
                    tot_msgs.update(csv_res.read_msgs_csv(file_path))

    if args.short:
        print(f"Esecuzione modalità SHORT (opzione: {args.short})...")
        if tot_st and tot_msgs:
            csv_res.plot_short(tot_msgs, tot_st, mode=args.short)
        else:
            print("Attenzione: per la modalità short servono dati sia da proc_data che da msgs_data.")
    else:
        print("Esecuzione modalità STANDARD (grafici separati)...")
        if tot_st:
            csv_res.plot_active_w_gt_thr(tot_st, tot_times)
            csv_res.plot_by_commit_w_gt_thr(tot_stbc)
            
        if tot_msgs:
            csv_res.plot_messages(tot_msgs)

##################################################################################
if __name__ == "__main__":
    main()