import BestNresults as BNres
import os, gc

N_run='rand'
bestNresults = BNres.Results()

COMMUNICATION=[]
BASES=[]
SCALING=[]
Q_LEN=[]
N_AGENTS=[]
for base in bestNresults.bases:
    if base not in BASES:
        BASES.append(base)
    for dir in os.listdir(base):
        if '.' not in dir and '#' in dir:
            pre_path=os.path.join(base, dir)
            communication=int(dir.split('#')[1])
            if communication not in COMMUNICATION:
                COMMUNICATION.append(int(communication))
            for zdir in os.listdir(pre_path):
                if '.' not in zdir and '#' in zdir:
                    n_agents=int(zdir.split('#')[1])
                    if n_agents not in N_AGENTS:
                        N_AGENTS.append(int(n_agents))
                    dtemp=os.path.join(pre_path, zdir)
                    for sdir in os.listdir(dtemp):
                        if '.' not in sdir and '#' in sdir:
                            q_len=int(sdir.split('#')[1])
                            if q_len not in Q_LEN:
                                Q_LEN.append(float(q_len))
                            stemp=os.path.join(dtemp, sdir)
                            for ssdir in os.listdir(stemp):
                                if '.' not in ssdir and '#' in ssdir:
                                    scaling=float(ssdir.split('#')[1].replace("_","."))
                                    if scaling not in SCALING:
                                        SCALING.append(float(scaling))
                                    path_temp=os.path.join(stemp, ssdir)
                                ##########################################################################################################
                                    # results,scaling,max_steps,date = bestNresults.extract_data(path_temp,base,communication,n_agents)
                                    qresults,qcommit,qmax_steps = bestNresults.extract_k_quorum_data(path_temp,n_agents)
                                    bestNresults.print_mean_quorum_value(qresults,base,communication,n_agents,scaling,q_len,qcommit,qmax_steps)
                                    bestNresults.print_single_run_quorum(qresults,base,communication,n_agents,scaling,q_len,qcommit,qmax_steps,N_run)
                                    # bestNresults.plot_weibulls(qresults,base,communication,n_agents,scaling,q_len,qscaling,qmax_steps)
                                ##########################################################################################################
                                    del qresults
                                    del qcommit
                                    del qmax_steps
                                    gc.collect()