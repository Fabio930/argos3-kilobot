import csv_results as CSVres
import os
import numpy as np

##################################################################################
def main():
    csv_res = CSVres.Data()
    limit = 0.8
    for base in csv_res.bases:
        tot_st = []
        for file in sorted(os.listdir(base)):
            if "images" not in file:
                file_path=os.path.join(base, file)
                no_ext_file = file.split('.')[0]
                sets = no_ext_file.split('_')
                algo = sets[0][0]
                for s in sets:
                    val = s.split('#')
                    if len(val)>1:
                        if val[0]=='r':
                            n_runs=val[1]
                        elif val[0]=='a':
                            arena=val[1]
                data = csv_res.read_csv(file_path,algo,n_runs,arena)
                keys, states, times, buffers, messages_counts = csv_res.divide_data(data)     
                # csv_res.o_plot_heatmaps(keys,(states,times,buffers),limit) if algo=='O' else csv_res.p_plot_heatmaps(keys,(states,times,buffers),limit)
                if len(tot_st)==0:
                    tot_st = [states]
                else:
                    tot_st = np.append(tot_st,[states],axis=0)
        csv_res.plot_active(tot_st)
##################################################################################
if __name__ == "__main__":
    main()