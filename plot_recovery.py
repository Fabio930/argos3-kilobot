import csv_results as CSVres
import os

##################################################################################
# adjust the main function to plot the recovery data
##################################################################################
def main():
    csv_res = CSVres.Data()
    for base in csv_res.bases:
        if base.split('/')[-1] == "rec_data":
            for file in sorted(os.listdir(base)):
                if "images" not in file and file.split('_')[0][0] != '.':
                    file_path=os.path.join(base, file)
                    if "recovery_data" in file:
                        data = csv_res.read_fitted_recovery_csv(file_path)
                        csv_res.plot_recovery(data) # plot the recovery data
                            
##################################################################################
if __name__ == "__main__":
    main()