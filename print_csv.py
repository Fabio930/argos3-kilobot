# usage python3 light_print_results.py -f files -t ticks
# if -f is declared then must specify which files to print: all, first, last or rand(om)
# if -t is declared then must specify which is the log frequency, default value is 31
import csv_results as CSVres
import os, sys

def main():
    csv_res = CSVres.Data()
    for base in csv_res.bases:
        for adir in sorted(os.listdir(base)):
            pre_path=os.path.join(base, adir)
            if 'proc_data' in adir:
                for file in sorted(os.listdir(pre_path)):
                    n_runs=file.split('.')[0].split('#')[-1]
                    csv_path=os.path.join(pre_path, file)
                    data = csv_res.read_csv(csv_path,n_runs)
                    csv_res.print_hetmap(data)               

if __name__ == "__main__":
    main()