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

echo "$CONFIGURATION_FILE" | egrep "^$SHARED_DIR" &> /dev/null || exit 1

#######################################
### experiment_length is in seconds ###
#######################################
experiment_length="600"
RUNS=30
rebroadcast="0 2"
msg_expiring_sec="60 120 300 600"
numrobots="25"
committed_percentage="0.5"
messages_hops="0"

for exp_len_par in $experiment_length; do
    exp_len_dir=$res_dir/"ExperimentLength#"$exp_len_par
    if [[ ! -e $exp_len_dir ]]; then
        mkdir $exp_len_dir
    fi
    for comm_par in $rebroadcast; do
        comm_dir=$exp_len_dir/"Rebroadcast#"$comm_par
        if [[ ! -e $comm_dir ]]; then
            mkdir $comm_dir
        fi
        for agents_par in $numrobots; do
            agents_dir=$comm_dir/"Robots#"$agents_par
            if [[ ! -e $agents_dir ]]; then
                mkdir $agents_dir
            fi
            last_id=`expr $agents_par - 1`
            for committed_par in $committed_percentage; do
                committed_dir=$agents_dir/"Committed#"$committed_par
                if [[ ! -e $committed_dir ]]; then
                    mkdir $committed_dir
                fi
                for msgs_hop_par in $messages_hops; do
                    msgs_hop_dir=$committed_dir/"MsgHop#"$msgs_hop_par
                    if [[ ! -e $msgs_hop_dir ]]; then
                        mkdir $msgs_hop_dir
                    fi
                    for msgs_par in $msg_expiring_sec; do
                        msgs_dir=$msgs_hop_dir/"MsgExpTime#"$msgs_par
                        if [[ ! -e $msgs_dir ]]; then
                            mkdir $msgs_dir
                        fi
                        for i in $(seq 1 $RUNS); do
                            config=`printf 'config_rebroad%d_nrobots%d_MsgExpTime%d_run%d.argos' $comm_par $agents_par $msgs_par $i`
                            cp $base_config $config
                            sed -i "s|__BROADCAST_POLICY__|$comm_par|g" $config
                            sed -i "s|__NUMROBOTS__|$agents_par|g" $config
                            sed -i "s|__COMMITTED_PERC__|$committed_par|g" $config
                            sed -i "s|__MSG_HOPS__|$msgs_hop_par|g" $config
                            sed -i "s|__MSG_EXPIRING_SECONDS__|$msgs_par|g" $config
                            sed -i "s|__SEED__|$i|g" $config
                            sed -i "s|__TIME_EXPERIMENT__|$exp_len_par|g" $config
                            dt=$(date '+%d-%m-%Y_%H-%M-%S')
                            kilo_file="${dt}__run#${i}.tsv"
                            sed -i "s|__KILOLOG__|$kilo_file|g" $config
                            echo "Running next configuration -- $config"
                            argos3 -c './'$config
                            for j in $(seq 0 $last_id); do
                                rename="quorum_log_agent#$j"__"$kilo_file"
                                mv "quorum_log_agent#$j.tsv" $rename
                                mv $rename $msgs_dir
                            done
                            rm *.argos
                        done
                    done
                done
            done
        done
    done
done