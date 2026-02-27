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
experiment_length="1000"
RUNS=3
numrobots="100"
rebroadcast="0 1"
adaptive_comm="0"
msgs_n_hops="0"
msgs_timeout="300"
options="2 5"
eta2="0.4 0.5"
init_distr="0.5"
control="polynomial"
voting_msgs="3 5 7 9 15"
control_parameter_list="0.7 0.8"

for exp_len_par in $experiment_length; do
    exp_len_dir=$res_dir/"ExperimentLength#"$exp_len_par
    if [[ ! -e $exp_len_dir ]]; then
        mkdir $exp_len_dir
    fi
    for agents_par in $numrobots; do
        for comm_par in $rebroadcast; do
            comm_dir=$exp_len_dir/"Rebroadcast#"$comm_par
            if [[ ! -e $comm_dir ]]; then
                mkdir $comm_dir
            fi
            if [[ $comm_par == "1" ]]; then
                adaptive_set=$adaptive_comm
            else
                adaptive_set="0"
            fi
            for adaptive_par in $adaptive_set; do
                adaptive_dir=$comm_dir/"Adaptive#"$adaptive_par
                if [[ ! -e $adaptive_dir ]]; then
                    mkdir $adaptive_dir
                fi
                agents_dir=$adaptive_dir/"Robots#"$agents_par
                if [[ ! -e $agents_dir ]]; then
                    mkdir $agents_dir
                fi
                last_id=`expr $agents_par - 1`
                for msgs_par in $msgs_timeout; do
                    msgs_dir=$agents_dir/"MsgExpTime#"$msgs_par
                    if [[ ! -e $msgs_dir ]]; then
                        mkdir $msgs_dir
                    fi
                    for msgs_hop_par in $msgs_n_hops; do
                        msgs_hop_dir=$msgs_dir/"MsgHops#"$msgs_hop_par
                        if [[ ! -e $msgs_hop_dir ]]; then
                            mkdir $msgs_hop_dir
                        fi
                        for options_par in $options; do
                            options_dir=$msgs_hop_dir/"Options#"$options_par
                            if [[ ! -e $options_dir ]]; then
                                mkdir $options_dir
                            fi
                            if [[ $options_par == "2" ]]; then
                                eta="0.4 0.5"
                                init_distr="0.5"
                            else
                                eta="0.7 0.8"
                                init_distr="0.2"
                            fi
                            for eta_par in $eta; do
                                eta_dir=$options_dir/"Eta#"$eta_par
                                if [[ ! -e $eta_dir ]]; then
                                    mkdir $eta_dir
                                fi
                                for init_par in $init_distr; do
                                    init_dir=$eta_dir/"InitDistr#"$init_par
                                    if [[ ! -e $init_dir ]]; then
                                        mkdir $init_dir
                                    fi
                                    for control_par in $control; do
                                        control_dir=$init_dir/"Control#"$control_par
                                        if [[ ! -e $control_dir ]]; then
                                            mkdir $control_dir
                                        fi
                                        if [[ $control_par == "static" ]]; then
                                            control_parameter="0.8"
                                        else
                                            control_parameter=$control_parameter_list
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
                                                for i in $(seq 1 $RUNS); do
                                                    kilo_file="run#${i}.tsv"
                                                    config=`printf 'config_nrobots%d_rebroad%d_adap%d_MsgExpTime%d_MsgHop%d_Opt%d_Eta%s_InitDistr%s_Ctrl%s_Vote%d_CPar%s_run%d.argos' $agents_par $comm_par $adaptive_par $msgs_par $msgs_hop_par $options_par $eta_par $init_par $control_par $voting_msgs_par $control_parameter_par $i`
                                                    cp $base_config $config
                                                    sed -i "s|__BROADCAST_POLICY__|$comm_par|g" $config
                                                    sed -i "s|__ADAPTIVE_COMM__|$adaptive_par|g" $config
                                                    sed -i "s|__NUMROBOTS__|$agents_par|g" $config
                                                    sed -i "s|__MSG_EXPIRING_SECONDS__|$msgs_par|g" $config
                                                    sed -i "s|__SEED__|$i|g" $config
                                                    sed -i "s|__TIME_EXPERIMENT__|$exp_len_par|g" $config
                                                    sed -i "s|__MSGS_HOPS__|$msgs_hop_par|g" $config
                                                    sed -i "s|__N_OPTIONS__|$options_par|g" $config
                                                    sed -i "s|__ETA__|$eta_par|g" $config
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
