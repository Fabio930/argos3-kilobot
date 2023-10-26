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
                    ##########################################################################################################
                    qresults,qcommit,qmax_steps,qmins,qexptime = bestNresults.extract_k_quorum_data(dtemp,n_agents)
                    bestNresults.print_median_time(qresults,base,communication,n_agents,qcommit,qmax_steps,qmins,qexptime)
                    bestNresults.print_mean_quorum_value(qresults,base,communication,n_agents,qcommit,qmax_steps,qmins,qexptime)
                    bestNresults.print_single_run_quorum(qresults,base,communication,n_agents,qcommit,qmax_steps,qmins,qexptime)
                    ##########################################################################################################
                    del qresults
                    del qcommit
                    del qmax_steps
                    del qexptime
                    gc.collect()