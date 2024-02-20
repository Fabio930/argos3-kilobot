# usage python3 light_print_results.py -d data -f files -t ticks
# if -d is declared then must specify which data to print: all, quorum or freq(uency)
# if -t is declared then must specify which is the log frequency, default value is 31
import data_extractor as dex
import os, sys

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
    max_buff_dim = 0
    print("\n--- Check max buffer dimension ---")
    for base in results.bases:
        for adir in sorted(os.listdir(base),reverse=True):
            if '.' not in adir and '#' in adir:
                pre_apath=os.path.join(base, adir)
                for dir in sorted(os.listdir(pre_apath)):
                    if '.' not in dir and '#' in dir:
                        pre_path=os.path.join(pre_apath, dir)
                        for zdir in sorted(os.listdir(pre_path)):
                            if '.' not in zdir and '#' in zdir:
                                n_agents=int(zdir.split('#')[1]) - 1
                                if n_agents > max_buff_dim:
                                    max_buff_dim = n_agents
    for base in results.bases:
        for adir in sorted(os.listdir(base)):
            if '.' not in adir and '#' in adir:
                pre_apath=os.path.join(base, adir)
                exp_length=int(adir.split('#')[1])
                for dir in sorted(os.listdir(pre_apath)):
                    if '.' not in dir and '#' in dir:
                        pre_path=os.path.join(pre_apath, dir)
                        communication=int(dir.split('#')[1])
                        for zdir in sorted(os.listdir(pre_path)):
                            if '.' not in zdir and '#' in zdir:
                                n_agents=int(zdir.split('#')[1])
                                dtemp=os.path.join(pre_path, zdir)
                                results.extract_k_data(base,dtemp,exp_length,communication,n_agents,max_buff_dim,data_type)

if __name__ == "__main__":
    main()