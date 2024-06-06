# usage python3 light_print_results.py -d data -f files -t ticks
# if -d is declared then must specify which data to print: all, quorum or freq(uency)
# if -t is declared then must specify which is the log frequency, default value is 31
import data_extractor as dex
import os, sys
import numpy as np

def check_inputs():
    ticks = 10
    data_type = "all"
    if len(sys.argv)>7:
        print("Too many arguments --EXIT--")
        exit()
    if len(sys.argv)>1:
        for i in range(len(sys.argv)):
            if sys.argv[i]=='-d':
                if i+1 >= len(sys.argv):
                    print("BAD format input --EXIT--")
                    exit()
                data_type = str(sys.argv[i+1])
            elif sys.argv[i]=='-t':
                if i+1 >= len(sys.argv):
                    print("BAD format input --EXIT--")
                    exit()
                try:
                    ticks = int(sys.argv[i+1])
                except:
                    print("BAD format input\n-t must be followed by a positve integer --EXIT--")
                    exit()
    if data_type!="all" and data_type!="quorum" and data_type!="freq":
        print("BAD format -d input type\nallowed entries are: all, quorum or freq --EXIT--")
        exit()
    if ticks <= 0:
        print("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks,data_type

def main():
    results = dex.Results()
    results.ticks_per_sec, data_type = check_inputs()
    for base in results.bases:
        for exp_l_dir in sorted(os.listdir(base)):
            if '.' not in exp_l_dir and '#' in exp_l_dir:
                exp_l_path = os.path.join(base, exp_l_dir)
                exp_length = int(exp_l_dir.split('#')[1])
                for thr_dir in sorted(os.listdir(exp_l_path)):
                    if '.' not in thr_dir and '#' in thr_dir:
                        thr_path = os.path.join(exp_l_path, thr_dir)
                        threshold = float(thr_dir.split('#')[1].replace('_','.'))
                        for Dgt_dir in sorted(os.listdir(thr_path)):
                            Dgt_path = os.path.join(thr_path,Dgt_dir)
                            delta_str = Dgt_dir.split('#')[1].replace('_','.')
                            for comm_dir in sorted(os.listdir(Dgt_path)):
                                if '.' not in comm_dir and '#' in comm_dir:
                                    comm_path = os.path.join(Dgt_path, comm_dir)
                                    communication = int(comm_dir.split('#')[1])
                                    for agents_dir in sorted(os.listdir(comm_path)):
                                        if '.' not in agents_dir and '#' in agents_dir:
                                            n_agents = int(agents_dir.split('#')[1])
                                            agents_path = os.path.join(comm_path, agents_dir)
                                            results.extract_k_data(base,agents_path,exp_length,communication,n_agents,threshold,delta_str,data_type)

if __name__ == "__main__":
    main()