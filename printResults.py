import BestNresults as BNres

N_run='first'
percentages_by_leaf = False
evaluation = ['position','commitment']

bestNresults = BNres.Results()

results,bases,N_agents,branches,depth,k,r,max_steps,date = bestNresults.extract_data()
bestNresults.plot_percentages_on_leaf(results,bases,N_agents,branches,depth,k,r,max_steps)
for evalit in evaluation:
    data = bestNresults.plot_weibulls(results,bases,N_agents,branches,depth,k,r,max_steps,date,evalit)
    bestNresults.write_percentages(data,bases,N_agents,branches,depth,k,r,max_steps,date,evalit,percentages_by_leaf)

qresults,qbases,qN_agents,qbranches,qdepth,qk,qr,qmax_steps = bestNresults.extract_k_quorum_data()
bestNresults.do_something_quorum(qresults,qbases,qN_agents,qbranches,qdepth,qk,qr,qmax_steps)
bestNresults.print_single_run_quorum(qresults,qbases,qN_agents,qbranches,qdepth,qk,qr,qmax_steps,N_run)


# bestNresults.plot_pareto_diagram()
# ARK_data_positions = bestNresults.sort_ark_positions_by_node()
# bestNresults.plot_positions_distribution(ARK_data_positions)
# KILO_data_positions = bestNresults.sort_kilo_positions_by_node()
# bestNresults.plot_positions_distribution(KILO_data_positions)