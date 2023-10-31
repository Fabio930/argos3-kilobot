import lwBestNresults as BNres
import os, gc

bestNresults = BNres.Results()

for base in bestNresults.bases:
    for dir in sorted(os.listdir(base)):
        if '.' not in dir and '#' in dir:
            pre_path=os.path.join(base, dir)
            communication=int(dir.split('#')[1])
            for zdir in sorted(os.listdir(pre_path)):
                if '.' not in zdir and '#' in zdir:
                    n_agents=int(zdir.split('#')[1])
                    dtemp=os.path.join(pre_path, zdir)
                    print("Opening folder Rebroadcast",communication,"with",n_agents,"Agents")
                    bestNresults.extract_k_quorum_data(dtemp,n_agents)