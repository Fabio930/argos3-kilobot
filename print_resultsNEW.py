# usage python3 light_print_results.py -d data -f files -t ticks
# if -d is declared then must specify which data to print: all, quorum or freq(uency)
# if -f is declared then must specify which files to print: all, first, last or rand(om)
# if -t is declared then must specify which is the log frequency, default value is 31
import bestNresultsNEW as BNres
import os, sys

def check_inputs():
    ticks = 31
    data_type = "all"
    files_to_elaborate = "all"
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
            elif sys.argv[i]=='-f':
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
    if data_type!="all" and data_type!="quorum" and data_type!="freq":
        print("BAD format -d input type\nallowed entries are: all, quorum or freq --EXIT--")
        exit()
    if files_to_elaborate!="all" and files_to_elaborate!="first" and files_to_elaborate!="last" and files_to_elaborate!="rand":
        print("BAD format -f input type\nallowed entries are: all, first, last or rand --EXIT--")
        exit()
    if ticks <= 0:
        print("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks,data_type,files_to_elaborate

def main():
    bestNresults = BNres.Results()
    bestNresults.ticks_per_sec, data_type, files_to_elaborate = check_inputs()
    for base in bestNresults.bases:
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
                                print("\nOpening folder",dtemp)
                                bestNresults.extract_k_quorum_data(dtemp,exp_length,communication,n_agents,files_to_elaborate,data_type)

if __name__ == "__main__":
    main()