import lwBestNresults as BNres
import os

bestNresults = BNres.Results()

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
                            print("Opening folder Rebroadcast",communication,"with",n_agents,"Agents")
                            bestNresults.extract_k_quorum_data(dtemp,exp_length,communication,n_agents)