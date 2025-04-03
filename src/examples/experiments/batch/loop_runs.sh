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
experiment_length="1200"
variation_time="600"
RUNS=100
rebroadcast="0"
numrobots="25 100"
msg_expiring_seconds="60 300 600"
threshold="0.8"
delta="0.68;0.92 0.92;0.68"

for exp_len_par in $experiment_length; do
    exp_len_dir=$res_dir/"ExperimentLength#"$exp_len_par
    if [[ ! -e $exp_len_dir ]]; then
        mkdir $exp_len_dir
    fi
    for agents_par in $numrobots; do
        for thr_par in $threshold; do
            thr_par=${thr_par//./_}
            thr_dir=$exp_len_dir/"Threshold#"$thr_par
            if [[ ! -e $thr_dir ]]; then
                mkdir $thr_dir
            fi
            thr_par=${thr_par//_/.}
            for dlt_par in $delta; do
                IFS=';' read -r gt_before gt_after <<< "$dlt_par"
                gt_before=${gt_before//./_}
                gt_after=${gt_after//./_}
                dlt_dir=$thr_dir/"GT#"$gt_before";"$gt_after
                if [[ ! -e $dlt_dir ]]; then
                    mkdir $dlt_dir
                fi

                gt_before=${gt_before//_/.}
                gt_after=${gt_after//_/.}
                for comm_par in $rebroadcast; do
                    comm_dir=$dlt_dir/"Rebroadcast#"$comm_par
                    if [[ ! -e $comm_dir ]]; then
                        mkdir $comm_dir
                    fi
                    agents_dir=$comm_dir/"Robots#"$agents_par
                    if [[ ! -e $agents_dir ]]; then
                        mkdir $agents_dir
                    fi
                    last_id=`expr $agents_par - 1`
                    if [ $agents_par -eq 25 ]; then
                        # buffer_dim="19 23 24" # small arena 25
                        buffer_dim="11 19 22" # big arena 25
                    elif [ $agents_par -eq 100 ]; then
                        buffer_dim="41 76 85"
                    fi
                    buffer_dim_array=($buffer_dim)
                    dim_b_idx=0
                    for msgs_par in $msg_expiring_seconds; do
                        msgs_dir=$agents_dir/"MsgExpTime#"$msgs_par
                        if [[ ! -e $msgs_dir ]]; then
                            mkdir $msgs_dir
                        fi
                        buff_par=${buffer_dim_array[dim_b_idx]}
                        hops_dir=$msgs_dir/"MsgHops#0"
                        if [[ ! -e $hops_dir ]]; then
                            mkdir $hops_dir
                        fi
                        for i in $(seq 1 $RUNS); do
                            config=`printf 'config_nrobots%s_rebroad%d_MsgExpTime%s_Thr%s_Gt%s_run%s.argos' $agents_par $comm_par $msgs_par $thr_par $dlt_par $i`
                            cp $base_config $config
                            sed -i "s|__BROADCAST_POLICY__|$comm_par|g" $config
                            sed -i "s|__NUMROBOTS__|$agents_par|g" $config
                            sed -i "s|__QUORUM_BUFFER_DIM__|$buff_par|g" $config
                            sed -i "s|__MSG_EXPIRING_SECONDS__|$msgs_par|g" $config
                            sed -i "s|__SEED__|$i|g" $config
                            sed -i "s|__TIME_EXPERIMENT__|$exp_len_par|g" $config
                            sed -i "s|__VARIATION_TIME__|$variation_time|g" $config
                            sed -i "s|__THRESHOLD__|$thr_par|g" $config
                            sed -i "s|__GT_BEFORE_VAR__|$gt_before|g" $config
                            sed -i "s|__GT_AFTER_VAR__|$gt_after|g" $config
                            sed -i "s|__KILOLOG__|$kilo_file|g" $config
                            kilo_file="run#${i}.tsv"
                            echo "Running next configuration -- $config"
                            argos3 -c './'$config
                            for j in $(seq 0 $last_id); do
                                rename="quorum_log_agent#$j"_"$kilo_file"
                                mv "quorum_log_agent#$j.tsv" $rename
                                mv $rename $hops_dir
                            done
                            rm *.argos
                        done
                        dim_b_idx=$((dim_b_idx + 1))
                    done
                done
            done
        done
    done
done