import csv_results as CSVres
import os
import numpy as np
import argparse

##################################################################################
def main():
    parser = argparse.ArgumentParser(description="Plot results with optional protocol/Tm exclusions.")
    parser.add_argument("--exclude-protocols", default="", help="Comma-separated protocol IDs to exclude (e.g. P.0,O.2.0)")
    parser.add_argument("--exclude-tm", default="", help="Comma-separated Tm values to exclude (e.g. 60,120)")
    parser.add_argument("--insert", default="", help="Comma-separated Tm values to insert in inset panel (e.g. 600)")
    parser.add_argument("--short", default="", help="Use 's' command")
    args = parser.parse_args()
    
    exclude_protocols = [s.strip() for s in args.exclude_protocols.split(",") if s.strip()]
    exclude_tm = [s.strip() for s in args.exclude_tm.split(",") if s.strip()]
    insert_tm = [s.strip() for s in args.insert.split(",") if s.strip()]
    short = [s.strip() for s in args.short.split(",") if s.strip()]
    use_short = "s" in short

    def _select_files(base_dir):
        selected = []
        for file in sorted(os.listdir(base_dir)):
            if "images" not in file and not file.startswith('.'):
                selected.append(file)
        return selected

    csv_res = CSVres.Data()
    if use_short:
        csv_res._assign_config("short_plot_config.json")
        
    # Aggiornata la condizione e la chiamata a funzione
    if exclude_protocols or exclude_tm or insert_tm:
        csv_res.apply_plot_overrides(
            ["active", "messages", "decisions"],
            exclude_protocols=exclude_protocols or None,
            exclude_tm=exclude_tm or None,
            insert=insert_tm or None,
        )
        
    if use_short:
        tot_st          = []
        tot_times       = []
        tot_msgs        = None
        for base in csv_res.bases:
            if base.split('/')[-1] == "proc_data":
                for file in _select_files(base):
                    n_runs=0
                    arena=''
                    if "images" not in file and file.split('_')[0][0] != '.':
                        file_path=os.path.join(base, file)
                        no_ext_file = file.split('.')[0]
                        sets = no_ext_file.split('_')
                        algo = sets[0][0] if sets[0][1] == "a" or sets[0][1] == "r" else sets[0][0:2]
                        if "resume" in file:
                            for s in sets:
                                val = s.split('#')
                                if len(val)>1:
                                    if val[0]=='r':
                                        n_runs=val[1]
                                    elif val[0]=='a':
                                        arena=val[1]
                            data = csv_res.read_csv(file_path,algo,n_runs,arena)
                            keys, states, times = csv_res.divide_data(data)
                            if len(tot_st)==0:
                                tot_st      = [states]
                                tot_times   = [times]
                            else:
                                tot_st      = np.append(tot_st,[states],axis=0)
                                tot_times   = np.append(tot_times,[times],axis=0)
            if base.split('/')[-1] == "msgs_data":
                for file in _select_files(base):
                    if "images" not in file:
                        file_path=os.path.join(base, file)
                        tot_msgs = csv_res.read_msgs_csv(file_path)
        csv_res.plot_compressed_table(tot_st,tot_times,tot_msgs)
    else:
        for base in csv_res.bases:
            if base.split('/')[-1] == "proc_data":
                tot_st          = []
                tot_times       = []
                for file in _select_files(base):
                    n_runs=0
                    arena=''
                    if "images" not in file and file.split('_')[0][0] != '.':
                        file_path=os.path.join(base, file)
                        no_ext_file = file.split('.')[0]
                        sets = no_ext_file.split('_')
                        algo = sets[0][0] if sets[0][1] == "a" or sets[0][1] == "r" else sets[0][0:2]
                        if "resume" in file:
                            for s in sets:
                                val = s.split('#')
                                if len(val)>1:
                                    if val[0]=='r':
                                        n_runs=val[1]
                                    elif val[0]=='a':
                                        arena=val[1]
                            data = csv_res.read_csv(file_path,algo,n_runs,arena)
                            keys, states, times = csv_res.divide_data(data)
                            if len(tot_st)==0:
                                tot_st      = [states]
                                tot_times   = [times]
                            else:
                                tot_st      = np.append(tot_st,[states],axis=0)
                                tot_times   = np.append(tot_times,[times],axis=0)
                if len(tot_st) > 0:
                    path,ground_T,threshlds,states_dict,times_dict,o_k,[arena,agents] = csv_res.plot_active(tot_st,tot_times)
                    csv_res.print_borders(path,'avg','median',ground_T,threshlds,states_dict,times_dict,o_k,[arena,agents])
            if base.split('/')[-1] == "msgs_data":
                for file in _select_files(base):
                    if "images" not in file:
                        file_path=os.path.join(base, file)
                        tot_msgs = csv_res.read_msgs_csv(file_path)
                        messages_dict,stds_dict = csv_res.plot_messages(tot_msgs)
                        csv_res.print_messages(messages_dict,stds_dict)
            # if base.split('/')[-1] == "dec_data":
            #     for file in sorted(os.listdir(base)):
            #         if "images" not in file:
            #             file_path=os.path.join(base, file)
            #             tot_dec = csv_res.read_msgs_csv(file_path)
            #             csv_res.plot_decisions(tot_dec)

##################################################################################
if __name__ == "__main__":
    main()
