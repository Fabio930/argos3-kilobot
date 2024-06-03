#! /bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: loop_runs.sh (from src folder) <base_config_dir> <base_config_file_name>"
    exit 11
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

base_dir=`dirname $base_config`
echo base_dir $base_dir
echo "$CONFIGURATION_FILE" | egrep "^$SHARED_DIR" &> /dev/null || exit 1

#######################################
### experiment_length is in seconds ###
#######################################
experiment_length="1801"
RUNS=100
numrobots="20"
kappa="0.75"
branches="2"
depth="2 4"
control_param="1 3"

for agents_par in $numrobots; do
    agents_dir=$res_dir/"Robots#"$agents_par
    if [[ ! -e $agents_dir ]]; then
        mkdir $agents_dir
    fi
    for branches_par in $branches; do
        branches_dir=$agents_dir/"Branches#"$branches_par
        if [[ ! -e $branches_dir ]]; then
            mkdir $branches_dir
        fi
        for depth_par in $depth; do
            depth_dir=$branches_dir/"Depth#"$depth_par
            if [[ ! -e $depth_dir ]]; then
                mkdir $depth_dir
            fi
            for k_par in $kappa; do
                k_par_bis=${k_par//./_}
                k_dir=$depth_dir/"K#"$k_par_bis
                if [[ ! -e $k_dir ]]; then
                    mkdir $k_dir
                fi
                for ctrl_par in $control_param; do
                    ctrl_dir=$k_dir/"R#"$ctrl_par"_S#"$experiment_length
                    if [[ ! -e $ctrl_dir ]]; then
                        mkdir $ctrl_dir
                    fi
                    for i in $(seq 1 $RUNS); do
                        config=`printf 'config_nrob%d_branches%d_depth%d_K%s_R%d_run%d.argos' $agents_par $branches_par $depth_par $k_par $ctrl_par $i`
                        echo config $config
                        cp $base_config $config
                        sed -i "s|__NUMROBOTS__|$agents_par|g" $config
                        sed -i "s|__BRANCHES__|$branches_par|g" $config
                        sed -i "s|__DEPTH__|$depth_par|g" $config
                        sed -i "s|__K__|$k_par|g" $config
                        sed -i "s|__R__|$ctrl_par|g" $config
                        sed -i "s|__SEED__|$i|g" $config
                        sed -i "s|__TIMEEXPERIMENT__|$experiment_length|g" $config
                        dt=$(date '+%d-%m-%Y_%H-%M-%S')
                        kilo_file="${dt}__run#${i}_LOG.tsv"
                        sed -i "s|__KILOLOG__|$kilo_file|g" $config
                        echo "Running next configuration Robots $agents_par Branches $branches_par Depth $depth_par K $k_par R $ctrl_par File $kilo_file"
                        echo "argos3 -c $1$config"
                        argos3 -c './'$config
                        mv $kilo_file $ctrl_dir
                        rename="quorum_log_${i}.tsv"
                        mv "quorum_log.tsv" $rename
                        rm -rf "quorum_log.tsv"
                        mv $rename $ctrl_dir
                    done
                done
            done

        done
    done
done

rm *.argos