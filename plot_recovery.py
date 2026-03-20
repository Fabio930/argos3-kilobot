import csv_results as CSVres
import os
import argparse

##################################################################################
# adjust the main function to plot the recovery data
##################################################################################
def main():
    parser = argparse.ArgumentParser(description="Plot recovery data with optional protocol/Tm exclusions.")
    parser.add_argument("--exclude-protocols", default="", help="Comma-separated protocol IDs to exclude (e.g. P.0,O.2.0)")
    parser.add_argument("--exclude-tm", default="", help="Comma-separated Tm values to exclude (e.g. 60,120)")
    args = parser.parse_args()
    exclude_protocols = [s.strip() for s in args.exclude_protocols.split(",") if s.strip()]
    exclude_tm = [s.strip() for s in args.exclude_tm.split(",") if s.strip()]

    csv_res = CSVres.Data()
    if exclude_protocols or exclude_tm:
        csv_res.apply_plot_overrides(
            ["recovery"],
            exclude_protocols=exclude_protocols or None,
            exclude_tm=exclude_tm or None,
        )
    for base in csv_res.bases:
        if base.split('/')[-1] == "rec_data":
            for file in sorted(os.listdir(base)):
                if "images" not in file and file.split('_')[0][0] != '.':
                    file_path=os.path.join(base, file)
                    if "recovery_data" in file:
                        data = csv_res.read_fitted_recovery_csv(file_path)
                        csv_res.plot_recovery(data)
                            
##################################################################################
if __name__ == "__main__":
    main()
