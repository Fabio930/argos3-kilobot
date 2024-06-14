import data_extractor as dex
import os
import sys
from multiprocessing import Pool, cpu_count

def check_inputs():
    ticks = 10
    data_type = "all"
    if len(sys.argv) > 7:
        print("Too many arguments --EXIT--")
        exit()
    if len(sys.argv) > 1:
        for i in range(len(sys.argv)):
            if sys.argv[i] == '-d':
                if i + 1 >= len(sys.argv):
                    print("BAD format input --EXIT--")
                    exit()
                data_type = str(sys.argv[i + 1])
            elif sys.argv[i] == '-t':
                if i + 1 >= len(sys.argv):
                    print("BAD format input --EXIT--")
                    exit()
                try:
                    ticks = int(sys.argv[i + 1])
                except:
                    print("BAD format input\n-t must be followed by a positive integer --EXIT--")
                    exit()
    if data_type != "all" and data_type != "quorum" and data_type != "freq":
        print("BAD format -d input type\nallowed entries are: all, quorum or freq --EXIT--")
        exit()
    if ticks <= 0:
        print("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks, data_type

def process_folder(args):
    print(dtemp+"\tStarted")
    base, dtemp, exp_length, n_agents, communication, data_type, results = args
    results.extract_k_data(base, dtemp, exp_length, communication, n_agents, data_type)
    print(dtemp+"\tCompleted")

def main():
    results = dex.Results()
    results.ticks_per_sec, data_type = check_inputs()

    tasks = []
    for base in results.bases:
        for adir in sorted(os.listdir(base)):
            if '.' not in adir and '#' in adir:
                pre_apath = os.path.join(base, adir)
                exp_length = int(adir.split('#')[1])
                for dir in sorted(os.listdir(pre_apath)):
                    if '.' not in dir and '#' in dir:
                        communication = int(dir.split('#')[1])
                        pre_path = os.path.join(pre_apath, dir)
                        for zdir in sorted(os.listdir(pre_path)):
                            if '.' not in zdir and '#' in zdir:
                                n_agents = int(zdir.split('#')[1])
                                dtemp = os.path.join(pre_path, zdir)
                                tasks.append((base, dtemp, exp_length, n_agents, communication, data_type, results))
    print("Pooling")
    with Pool(cpu_count()) as pool:
        pool.map(process_folder, tasks)

if __name__ == "__main__":
    main()
