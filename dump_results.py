# usage python3 light_print_results.py -f files -t ticks
# if -f is declared then must specify which files to print: all, first, last or rand(om)
# if -t is declared then must specify which is the log frequency, default value is 31
import data_extractor as BNres
import os, sys

def check_inputs():
    ticks = 10
    files_to_elaborate = "all"
    if len(sys.argv)>5:
        print("Too many arguments --EXIT--")
        exit()
    if len(sys.argv)>1:
        for i in range(len(sys.argv)):
            if sys.argv[i]=='-f':
                if i+1 >= len(sys.argv):
                    print("BAD format input --EXIT--")
                    exit()
                files_to_elaborate = str(sys.argv[i+1])
            elif sys.argv[i]=='-t':
                if i+1 >= len(sys.argv):
                    print("BAD format input --EXIT--")
                    exit()
                try:
                    ticks = int(sys.argv[i+1])
                except:
                    print("BAD format input\n-t must be followed by a positve integer --EXIT--")
                    exit()
    if files_to_elaborate!="all" and files_to_elaborate!="first" and files_to_elaborate!="last" and files_to_elaborate!="rand":
        print("BAD format -f input type\nallowed entries are: all, first, last or rand --EXIT--")
        exit()
    if ticks <= 0:
        print("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks,files_to_elaborate

def main():
    bestNresults = BNres.Results()
    bestNresults.ticks_per_sec, files_to_elaborate = check_inputs()
    max_buff_dim = 0
    print("\n--- Check max buffer dimension ---\n")
    for base in bestNresults.bases:
        for adir in sorted(os.listdir(base),reverse=True):
            if '.' not in adir and '#' in adir:
                pre_path=os.path.join(base, adir)
                for zdir in sorted(os.listdir(pre_path)):
                    if '.' not in zdir and '#' in zdir:
                        dtemp=os.path.join(pre_path, zdir)
                        for zzdir in sorted(os.listdir(dtemp)):
                            if '.' not in zzdir and '#' in zzdir:
                                n_agents=int(zzdir.split('#')[1])
                                if n_agents >= max_buff_dim:
                                    max_buff_dim = n_agents
    for base in bestNresults.bases:
        for adir in sorted(os.listdir(base)):
            if '.' not in adir and '#' in adir:
                exp_length=int(adir.split('#')[1])
                pre_path=os.path.join(base, adir)
                for zdir in sorted(os.listdir(pre_path)):
                    if '.' not in zdir and '#' in zdir:
                        communication=int(zdir.split('#')[1])
                        dtemp=os.path.join(pre_path, zdir)
                        for zzdir in sorted(os.listdir(dtemp)):
                            if '.' not in zzdir and '#' in zzdir:
                                n_agents=int(zzdir.split('#')[1])
                                ddtemp=os.path.join(dtemp, zzdir)
                                print("Opening folder",ddtemp)
                                bestNresults.extract_k_data(base,ddtemp,exp_length,n_agents,max_buff_dim,files_to_elaborate)

if __name__ == "__main__":
    main()