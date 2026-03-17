import csv_results as CSVres
import os
import numpy as np
import argparse

##################################################################################
def main():
    parser = argparse.ArgumentParser(description="Plot results with optional protocol/Tm exclusions.")
    parser.add_argument("--exclude-protocols", default="", help="Comma-separated protocol IDs to exclude (e.g. P.0,O.2.0)")
    parser.add_argument("--exclude-tm", default="", help="Comma-separated Tm values to exclude (e.g. 60,120)")
    args = parser.parse_args()
    exclude_protocols = [s.strip() for s in args.exclude_protocols.split(",") if s.strip()]
    exclude_tm = [s.strip() for s in args.exclude_tm.split(",") if s.strip()]

    csv_res = CSVres.Data()
    if exclude_protocols or exclude_tm:
        csv_res.apply_plot_overrides(
            ["active", "messages", "decisions"],
            exclude_protocols=exclude_protocols or None,
            exclude_tm=exclude_tm or None,
        )
    for base in csv_res.bases:
        if base.split('/')[-1] == "proc_data":
            tot_st          = []
            tot_times       = []
            for file in sorted(os.listdir(base)):
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
            if len(tot_st) > 0: csv_res.plot_active(tot_st,tot_times)
        if base.split('/')[-1] == "msgs_data":
            for file in sorted(os.listdir(base)):
                if "images" not in file:
                    file_path=os.path.join(base, file)
                    data = csv_res.read_msgs_csv(file_path)
                    csv_res.plot_messages(data)
        if base.split('/')[-1] == "dec_data":
            for file in sorted(os.listdir(base)):
                if "images" not in file:
                    file_path=os.path.join(base, file)
                    data = csv_res.read_msgs_csv(file_path)
                    csv_res.plot_decisions(data)

##################################################################################
if __name__ == "__main__":
    main()
