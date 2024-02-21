import csv_results as CSVres
import os, sys

##################################################################################
def main():
    csv_res = CSVres.Data()
    limit = 0.8
    for base in csv_res.bases:
        for file in sorted(os.listdir(base)):
            if file != "images":
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
                keys, states, buffers, times, messages_counts = csv_res.divide_data(data)               
                csv_res.plot_hetmaps(keys,(states,times,buffers),limit)

##################################################################################
if __name__ == "__main__":
    main()