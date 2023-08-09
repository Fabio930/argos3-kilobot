import BestNresults as BNres

N_run='first'
bestNresults = BNres.Results()

# results,bases,communication,N_agents,commit_perc,q_len,scaling,max_steps,date = bestNresults.extract_data()
qresults,qbases,qcommunication,qN_agents,qcommit_perc,qq_len,qscaling,qmax_steps = bestNresults.extract_k_quorum_data()

bestNresults.print_mean_quorum_value(qresults,qbases,qcommunication,qN_agents,qcommit_perc,qq_len,qscaling,qmax_steps)
# bestNresults.print_single_run_quorum(qresults,qbases,qcommunication,qN_agents,qcommit_perc,qq_len,qscaling,qmax_steps,N_run,N_run)