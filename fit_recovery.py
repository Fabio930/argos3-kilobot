import csv_results as CSVres
import os
import numpy as np

##################################################################################
def main():
    csv_res = CSVres.Data()
    for base in csv_res.bases:
        if base.split('/')[-1] == "proc_data":
            tot_recovery    = []
            for file in sorted(os.listdir(base)):
                arena=''
                if "images" not in file and file.split('_')[0][0] != '.':
                    file_path=os.path.join(base, file)
                    no_ext_file = file.split('.')[0]
                    sets = no_ext_file.split('_')
                    algo = sets[0][0]
                    if "recovery" in file:
                        for s in sets:
                            val = s.split('#')
                            if len(val)>1:
                                if val[0]=='r':
                                    n_runs=val[1]
                                elif val[0]=='a':
                                    arena=val[1]
                        data = csv_res.read_recovery_csv(file_path,algo,arena)
                        if len(tot_recovery)==0:
                            tot_recovery = [data]
                        else:
                            tot_recovery = np.append(tot_recovery,[data],axis=0)
            if len(tot_recovery) > 0: csv_res.plot_recovery(csv_res.fit_recovery_raw_data(tot_recovery))
                            