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
RUNS=20
numrobots="15 40"
experiment_length="1800"
msg_frequency="124"
rebroadcast="0"
committed_percentage=".5 .6 .7"

strToReplace="."
replace="_"
for par in $experiment_length; do
    dir=$res_dir/"ExperimentLength#"$par
    for par00 in $msg_frequency; do
        dir00=$dir/"MsgFreq#"$par00
        for par0 in $rebroadcast; do
            dir0=$dir00/"Rebroadcast#"$par0
            for par1 in $numrobots; do
                dir1=$dir0/"Robots#"$par1
                if [ $par1 -eq 15 ]; then
                    buffer_dim="10"
                elif [ $par1 -eq 40 ]; then
                    buffer_dim="28"
                else
                    buffer_dim="42"
                fi
                for par2 in $buffer_dim; do
                    dir2=$dir1/"BufferDim#"$par2
                    for par3 in $committed_percentage; do
                        par3BIS=${par3//$strToReplace/$replace}
                        dir3=$dir2/"CommitPerc#"$par3BIS
                        if [[ ! -e $dir ]]; then
                            mkdir $dir
                        fi
                        if [[ ! -e $dir00 ]]; then
                            mkdir $dir00
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
                        if [[ ! -e $dir3 ]]; then
                            mkdir $dir3
                        fi
                        for it in $(seq 1 $RUNS); do
                            config=`printf 'config_msgFreq%s_rebroad%d_nrobots%d_bufferDim%d_CommitPerc%s_run%d.argos' $par00 $par0 $par1 $par2 $par3 $it`
                            cp $base_config $config
                            sed -i "s|__BROADCAST_POLICY__|$par0|g" $config
                            sed -i "s|__NUMROBOTS__|$par1|g" $config
                            sed -i "s|__QUORUM_BUFFER_DIM__|$par2|g" $config
                            sed -i "s|__COMMITTED_PERCENTAGE__|$par3|g" $config
                            sed -i "s|__TIME_FOR_A_MSG__|$par00|g" $config
                            sed -i "s|__SEED__|$it|g" $config
                            sed -i "s|__TIME_EXPERIMENT__|$experiment_length|g" $config
                            dt=$(date '+%d-%m-%Y_%H-%M-%S')
                            kilo_file="${dt}__run#${it}.tsv"
                            sed -i "s|__KILOLOG__|$kilo_file|g" $config
                            echo "Running next configuration -- MsgFreq $par00 Rebroadcast $par0 Robots $par1 BufferDim $par2 CommittedPercentage $par3 File $kilo_file"
                            argos3 -c './'$config
                            rename="quorum_log_$kilo_file"
                            mv "quorum_log.tsv" $rename
                            mv $rename $dir3
                            rm *.argos
                        done
                    done
                done
            done
        done
    done
done
