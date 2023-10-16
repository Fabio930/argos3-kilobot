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
echo "$CONFIGURATION_FILE" | egrep "^$SHARED_DIR" &> /dev/null || exit 1

#######################################
### experiment_length is in seconds ###
#######################################
experiment_length="2701"
RUNS=1
rebroadcast="0"
msg_expiring_sec="300"
numrobots="20"
# minimum_quorum_length="10 20"
# quorum_scaling_factor=".6 .7"
committed_percentage=".5 .6 .7 .8"

strToReplace="."
replace="_"

for par0 in $rebroadcast; do
    dir=$res_dir/"Rebroadcast#"$par0
    if [[ ! -e $dir ]]; then
        mkdir $dir
    fi
    for par1 in $numrobots; do
        dir1=$dir/"Robots#"$par1
        if [[ ! -e $dir1 ]]; then
            mkdir $dir1
        fi
        for par2 in $msg_expiring_sec; do
            dir2=$dir1/"MsgExpDist#"$par2
            if [[ ! -e $dir2 ]]; then
                mkdir $dir2
            fi
        #     for par3 in $quorum_scaling_factor; do
        #         par3BIS=${par3//$strToReplace/$replace}
        #         dir3=$dir2/"Scaling#"$par3BIS
        #         if [[ ! -e $dir3 ]]; then
        #             mkdir $dir3
        #         fi
            for par4 in $committed_percentage; do
                par4BIS=${par4//$strToReplace/$replace}
                dir4=$dir2/"CommitPerc#"$par4BIS"#S#"$experiment_length
                if [[ ! -e $dir4 ]]; then
                    mkdir $dir4
                fi
                for it in $(seq 1 $RUNS); do
                    config=`printf 'config_rebroad%d_nrobots%d_msgExpDist%d_CommitPerc%s_run%d.argos' $par0 $par1 $par2 $par4 $it`
                    cp $base_config $config
                    sed -i "s|__BROADCAST_POLICY__|$par0|g" $config
                    sed -i "s|__NUMROBOTS__|$par1|g" $config
                    sed -i "s|_MSG_EXPIRING_SECONDS_|$par2|g" $config
                    sed -i "s|__COMMITTED_PERCENTAGE__|$par4|g" $config
                    sed -i "s|__SEED__|$it|g" $config
                    sed -i "s|__TIMEEXPERIMENT__|$experiment_length|g" $config
                    dt=$(date '+%d-%m-%Y_%H-%M-%S')
                    kilo_file="${dt}__run#${it}.tsv"
                    sed -i "s|__KILOLOG__|$kilo_file|g" $config
                    echo "Running next configuration Rebroadcast $par0 Robots $par1 MsgExpiringTime $par2 CommittedPercentage $par4 File $kilo_file"
                    argos3 -c './'$config
                    rename="quorum_log_$kilo_file"
                    mv "quorum_log.tsv" $rename
                    rm -rf "quorum_log.tsv"
                    mv $rename $dir4
                done
            done
        #     done
        done
    done
done

rm *.argos