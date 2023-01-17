#! /bin/bash

# in ARGoS folder run the following:
# ./src/examples/experiments/batch/loop_runs.sh /src/examples/experiments/batch kilobot_ALF_BestN.argos

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

#################################
# experiment_length is in seconds
#################################
experiment_length="36"
RUNS=10
numrobots="20"
kappa="0.75 0.85 1.0"
depth="1 2"
branches="2"
control_param="1 3 5"

for nrob in $numrobots; do
    dir=$res_dir/"Robots#"$nrob
    if [[ ! -e $dir ]]; then
        mkdir $dir
    fi
    for par1 in $branches; do
        dir1=$dir/"Branches#"$par1
        if [[ ! -e $dir1 ]]; then
            mkdir $dir1
        fi
        for par2 in $depth; do
            dir2=$dir1/"Depth#"$par2
            if [[ ! -e $dir2 ]]; then
                mkdir $dir2
            fi
            for par3 in $kappa; do
                strToReplace="."
                replace="_"
                par3BIS=${par3//$strToReplace/$replace}
                dir3=$dir2/"K#"$par3BIS
                if [[ ! -e $dir3 ]]; then
                    mkdir $dir3
                fi
                for par4 in $control_param; do
                    dir4=$dir3/"R#"$par4"_S#"$experiment_length
                    if [[ ! -e $dir4 ]]; then
                        mkdir $dir4
                    fi
                    for it in $(seq 1 $RUNS); do
                        config=`printf 'config_nrob%d_branches%d_depth%d_K%d_R%d_run%d.argos' $nrob $par1 $par2 $par3 $par4 $it`
                        echo config $config
                        cp $base_config $config
                        sed -i "s|__NUMROBOTS__|$nrob|g" $config
                        sed -i "s|__BRANCHES__|$par1|g" $config
                        sed -i "s|__DEPTH__|$par2|g" $config
                        sed -i "s|__K__|$par3|g" $config
                        sed -i "s|__R__|$par4|g" $config
                        sed -i "s|__SEED__|$it|g" $config
                        sed -i "s|__TIMEEXPERIMENT__|$experiment_length|g" $config
                        dt=$(date '+%d-%m-%Y_%H-%M-%S')
                        kilo_file="${dt}__run#${it}_LOG.tsv"
                        sed -i "s|__KILOLOG__|$kilo_file|g" $config
                        echo "Running next configuration Robots $nrob Branches $par1 Depth $par2 K $par3 R $par4 File $kilo_file"
                        echo "argos3 -c $1$config"
                        argos3 -c './'$config
                        mv $kilo_file $dir4
                    done
                done
            done
        done
        # depth="1"
    done
done

rm *.argos