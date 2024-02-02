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
experiment_length="900"
RUNS=100
rebroadcast="0"
numrobots="25"

strToReplace="."
replace="_"
for par in $experiment_length; do
    dir=$res_dir/"ExperimentLength#"$par
    for par0 in $rebroadcast; do
        dir0=$dir/"Rebroadcast#"$par0
        for par1 in $numrobots; do
            dir1=$dir0/"Robots#"$par1
            last_id=`expr $par1 - 1`
            if [ $par1 -eq 25 ]; then
                buffer_dim="10 24"
            elif [ $par1 -eq 100 ]; then
                buffer_dim="10 99"
            fi
            for par2 in $buffer_dim; do
                dir2=$dir1/"BufferDim#"$par2
                if [[ ! -e $dir ]]; then
                    mkdir $dir
                fi
                if [[ ! -e $dir0 ]]; then
                    mkdir $dir0
                fi
                if [[ ! -e $dir1 ]]; then
                    mkdir $dir1
                fi
                if [[ ! -e $dir2 ]]; then
                    mkdir $dir2
                fi
                for it in $(seq 1 $RUNS); do
                    config=`printf 'config_rebroad%d_nrobots%d_bufferDim%d_run%d.argos' $par0 $par1 $par2 $it`
                    cp $base_config $config
                    sed -i "s|__BROADCAST_POLICY__|$par0|g" $config
                    sed -i "s|__NUMROBOTS__|$par1|g" $config
                    sed -i "s|__QUORUM_BUFFER_DIM__|$par2|g" $config
                    sed -i "s|__SEED__|$it|g" $config
                    sed -i "s|__TIME_EXPERIMENT__|$experiment_length|g" $config
                    dt=$(date '+%d-%m-%Y_%H-%M-%S')
                    kilo_file="${dt}__run#${it}.tsv"
                    sed -i "s|__KILOLOG__|$kilo_file|g" $config
                    echo "Running next configuration -- $config"
                    argos3 -c './'$config
                    for ik in $(seq 0 $last_id); do
                        rename="quorum_log_agent#$ik"__"$kilo_file"
                        mv "quorum_log_agent#$ik.tsv" $rename
                        mv $rename $dir2
                    done
                    rm *.argos
                done
            done
        done
    done
done