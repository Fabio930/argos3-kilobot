#! /bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: loop_runs.sh (from src folder) <base_config_dir> <base_config_file_name>"
    exit 1
fi

wdir=`pwd`
base_config=$1$2
if [ ! -e $base_config ]; then
    base_config=$wdir/$1/$2
    if [ ! -e $base_config ]; then
        echo "Error: missing configuration file '$base_config'" 1>&2
        exit 1
    fi
fi

res_dir=$wdir/"results_loop_runs"
if [[ ! -e $res_dir ]]; then
    mkdir $res_dir
    echo "mkdir: directory '$res_dir' "
fi

#######################################
### experiment_length is in seconds ###
#######################################
msgs_n_hops=""
eta_init=""
eta_stop=""
init_distr=""
control_parameter=""
experiment_length="1200"
variation_time="600"
RUNS=10
options="2 5"
numrobots="25 100"
comm_type_set="id_aware"
rebroadcast="0 1"
adaptive_set="0"
priority_k_set="0"
msgs_timeout="60 180"
control="polynomial"
voting_msgs="5 9 15"

for exp_len_par in $experiment_length; do
    exp_len_dir=$res_dir/"ExperimentLength#"$exp_len_par
    if [[ ! -e $exp_len_dir ]]; then
        mkdir $exp_len_dir
    fi
    for var_time_par in $variation_time; do
        var_time_dir=$exp_len_dir/"VariationTime#"$var_time_par
        if [[ ! -e $var_time_dir ]]; then
            mkdir $var_time_dir
        fi
        for options_par in $options; do
            options_dir=$var_time_dir/"Options#"$options_par
            if [[ ! -e $options_dir ]]; then
                mkdir $options_dir
            fi
            if [[ $options_par == "2" ]]; then
                eta_init="0.4"
                eta_stop="0.5"
                init_distr="0.5"
                control_parameter="0.5"
            else
                eta_init="0.7"
                eta_stop="0.9"
                init_distr="0.2"
                control_parameter="0.7"
            fi
            eta_init_list=($eta_init)
            eta_stop_list=($eta_stop)
            if [[ $var_time_par != "0" && ${#eta_init_list[@]} -ne ${#eta_stop_list[@]} ]]; then
                echo "Error: eta_init/eta_stop mismatch (eta_init=${#eta_init_list[@]}, eta_stop=${#eta_stop_list[@]})" 1>&2
                exit 1
            fi
            for idx in "${!eta_init_list[@]}"; do
                eta_i_par=${eta_init_list[$idx]}
                if [[ $var_time_par == "0" ]]; then
                    eta_s_par=$eta_i_par
                else
                    eta_s_par=${eta_stop_list[$idx]}
                fi
                eta_dir=$options_dir/"Eta#"$eta_i_par
                if [[ ! -e $eta_dir ]]; then
                    mkdir $eta_dir
                fi
                eta_stop_dir=$eta_dir/"EtaStop#"$eta_s_par
                if [[ ! -e $eta_stop_dir ]]; then
                    mkdir $eta_stop_dir
                fi
                for agents_par in $numrobots; do
                    robots_dir=$eta_stop_dir/"Robots#"$agents_par
                    if [[ ! -e $robots_dir ]]; then
                        mkdir $robots_dir
                    fi
                    last_id=`expr $agents_par - 1`
                    for comm_type in $comm_type_set; do
                        comm_type_dir=$robots_dir/"CommType#"$comm_type
                        if [[ ! -e $comm_type_dir ]]; then
                            mkdir $comm_type_dir
                        fi
                        if [[ $comm_type == "anon" ]]; then
                            id_aware_val=0
                            priority_k_list=$priority_k_set
                            rebroadcast_list="0"
                        else
                            id_aware_val=1
                            priority_k_list="0"
                            rebroadcast_list=$rebroadcast
                        fi
                        for comm_par in $rebroadcast_list; do
                            comm_dir=$comm_type_dir/"Rebroadcast#"$comm_par
                            if [[ ! -e $comm_dir ]]; then
                                mkdir $comm_dir
                            fi
                            if [[ $comm_type == "anon" ]]; then
                                msgs_n_hops="0"
                            elif [[ $comm_par == "1" ]]; then
                                msgs_n_hops="0 1"
                            else
                                msgs_n_hops="0"
                            fi
                            for adaptive_par in $adaptive_set; do
                                if [[ $comm_type == "anon" && $adaptive_par != "0" ]]; then
                                    continue
                                fi
                                if [[ $comm_type != "anon" && $comm_par == "0" && $adaptive_par != "0" ]]; then
                                    continue
                                fi
                                adaptive_dir=$comm_dir/"Adaptive#"$adaptive_par
                                if [[ ! -e $adaptive_dir ]]; then
                                    mkdir $adaptive_dir
                                fi
                                for priority_k_par in $priority_k_list; do
                                    priority_dir=$adaptive_dir/"PriorityK#"$priority_k_par
                                    if [[ ! -e $priority_dir ]]; then
                                        mkdir $priority_dir
                                    fi
                                    for msgs_par in $msgs_timeout; do
                                        msgs_dir=$priority_dir/"MsgExpTime#"$msgs_par
                                        if [[ ! -e $msgs_dir ]]; then
                                            mkdir $msgs_dir
                                        fi
                                        for msgs_hop_par in $msgs_n_hops; do
                                            msgs_hop_dir=$msgs_dir/"MsgHops#"$msgs_hop_par
                                            if [[ ! -e $msgs_hop_dir ]]; then
                                                mkdir $msgs_hop_dir
                                            fi
                                            for init_par in $init_distr; do
                                                init_dir=$msgs_hop_dir/"InitDistr#"$init_par
                                                if [[ ! -e $init_dir ]]; then
                                                    mkdir $init_dir
                                                fi
                                                for control_par in $control; do
                                                    control_dir=$init_dir/"Control#"$control_par
                                                    if [[ ! -e $control_dir ]]; then
                                                        mkdir $control_dir
                                                    fi
                                                    for voting_msgs_par in $voting_msgs; do
                                                        voting_dir=$control_dir/"VotingMsgs#"$voting_msgs_par
                                                        if [[ ! -e $voting_dir ]]; then
                                                            mkdir $voting_dir
                                                        fi
                                                        for control_parameter_par in $control_parameter; do
                                                            ctrl_par_dir=$voting_dir/"ControlParameter#"$control_parameter_par
                                                            if [[ ! -e $ctrl_par_dir ]]; then
                                                                mkdir $ctrl_par_dir
                                                            fi
                                                            if find "$ctrl_par_dir" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
                                                                echo "Skipping non-empty results directory: $ctrl_par_dir"
                                                                continue
                                                            fi
                                                            for i in $(seq 1 $RUNS); do
                                                                kilo_file="run#${i}.tsv"
                                                                config=`printf 'config_nrobots%d_comm%s_rebroad%d_adap%d_priorityk%d_MsgExpTime%d_MsgHop%d_Opt%d_Eta%s_EtaStop%s_VarTime%s_InitDistr%s_Ctrl%s_Vote%d_CPar%s_run%d.argos' $agents_par $comm_type $comm_par $adaptive_par $priority_k_par $msgs_par $msgs_hop_par $options_par $eta_i_par $eta_s_par $var_time_par $init_par $control_par $voting_msgs_par $control_parameter_par $i`
                                                                cp $base_config $config
                                                                sed -i "s|__BROADCAST_POLICY__|$comm_par|g" $config
                                                                sed -i "s|__ADAPTIVE_COMM__|$adaptive_par|g" $config
                                                                sed -i "s|__ID_AWARE__|$id_aware_val|g" $config
                                                                sed -i "s|__PRIORITY_K__|$priority_k_par|g" $config
                                                                sed -i "s|__NUMROBOTS__|$agents_par|g" $config
                                                                sed -i "s|__MSG_EXPIRING_SECONDS__|$msgs_par|g" $config
                                                                sed -i "s|__SEED__|$i|g" $config
                                                                sed -i "s|__TIME_EXPERIMENT__|$exp_len_par|g" $config
                                                                sed -i "s|__MSGS_HOPS__|$msgs_hop_par|g" $config
                                                                sed -i "s|__N_OPTIONS__|$options_par|g" $config
                                                                sed -i "s|__ETA_INIT__|$eta_i_par|g" $config
                                                                sed -i "s|__ETA_STOP__|$eta_s_par|g" $config
                                                                sed -i "s|__VAR_TIME__|$var_time_par|g" $config
                                                                sed -i "s|__INIT_DISTR__|$init_par|g" $config
                                                                sed -i "s|__CONTROL_TYPE__|$control_par|g" $config
                                                                sed -i "s|__VOTING_MSGS__|$voting_msgs_par|g" $config
                                                                sed -i "s|__CONTROL_PARAMETER__|$control_parameter_par|g" $config
                                                                sed -i "s|__KILOLOG__|$kilo_file|g" $config
                                                                echo "Running next configuration -- $config"
                                                                argos3 -c './'$config
                                                                for j in $(seq 0 $last_id); do
                                                                    rename="quorum_log_agent#$j"_"$kilo_file"
                                                                    mv "quorum_log_agent#$j.tsv" $rename
                                                                    mv $rename $ctrl_par_dir
                                                                done
                                                                rm *.argos
                                                            done
                                                        done
                                                    done
                                                done
                                            done
                                        done
                                    done
                                done
                            done
                        done
                    done
                done
            done
        done
    done
done
