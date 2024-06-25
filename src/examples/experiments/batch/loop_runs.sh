#! /bin/bash

# Function to calculate the number of robots and areas
calculate_areas() {
    local N=$1
    local X=$2
    local arena_width=$3
    local arena_height=$4

    # Calculate the number of robots in state 1 and state 0
    local N1=$(echo "$N * $X" | bc)
    local N0=$(echo "$N * (1 - $X)" | bc)

    # Calculate the total area of the arena
    local total_area=$(echo "$arena_width * $arena_height" | bc)

    # Calculate the areas for state 1 and state 0 with constant density
    local area1=$(echo "$total_area * $X" | bc)
    local area0=$(echo "$total_area * (1 - $X)" | bc)

    echo "$N1 $N0 $area1 $area0"
}

# Function to calculate the dimensions and coordinates of each area
calculate_dimensions_and_coordinates() {
    local area=$1
    local arena_width=$2
    local arena_height=$3

    # The height of the area is equal to the height of the entire arena
    local height=$arena_height

    # Calculate the width of the area
    local width=$(echo "scale=2; $area / $height" | bc)

    # Calculate the x-coordinates for the area's corners assuming origin at center
    local x_min=$(echo "scale=2; -$arena_width / 2" | bc)
    local x_max=$(echo "scale=2; $width - $arena_width / 2" | bc)

    echo "$width $height $x_min $x_max"
}

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
rebroadcast="0 2"
msg_expiring_sec="60 120 300 600"
numrobots="25"
threshold="0.8"
committed_percentage="0.56 0.68 0.80"
messages_hops="0"
# small arena dimensions
arena_x_side="0.500 1.000"
arena_y_side="0.500 0.250"
# big arena dimensions
# arena_x_side="1.000 2.000"
# arena_y_side="1.000 0.500"

# Convert the space-separated strings into arrays
arena_x_side_array=($arena_x_side)
arena_y_side_array=($arena_y_side)

# Loop over the indices of the arrays
for exp_len_par in $experiment_length; do
    exp_len_dir=$res_dir/"ExperimentLength#"$exp_len_par
    if [[ ! -e $exp_len_dir ]]; then
        mkdir $exp_len_dir
    fi
    for ap in "${!arena_x_side_array[@]}"; do
        arena_x_par=${arena_x_side_array[$ap]}
        arena_y_par=${arena_y_side_array[$ap]}
        arena_x_par=${arena_x_par//./_}
        arena_y_par=${arena_y_par//./_}
        arena_dir=$exp_len_dir/"ArenaType#${arena_x_par};${arena_y_par}"
        arena_x_par=${arena_x_par//_/.}
        arena_y_par=${arena_y_par//_/.}
        if [[ ! -e $arena_dir ]]; then
            mkdir $arena_dir
        fi
        for agents_par in $numrobots; do
            for comm_par in $rebroadcast; do
                comm_dir=$arena_dir/"Rebroadcast#"$comm_par
                if [[ ! -e $comm_dir ]]; then
                    mkdir $comm_dir
                fi
                agents_dir=$comm_dir/"Robots#"$agents_par
                if [[ ! -e $agents_dir ]]; then
                    mkdir $agents_dir
                fi
                last_id=`expr $agents_par - 1`
                for thr_par in $threshold; do
                    thr_par=${thr_par//./_}
                    thr_dir=$agents_dir/"Threshold#"$thr_par
                    if [[ ! -e $thr_dir ]]; then
                        mkdir $thr_dir
                    fi
                    thr_par=${thr_par//_/.}
                    for committed_par in $committed_percentage; do
                        committed_par=${committed_par//./_}
                        committed_dir=$thr_dir/"GT#"$committed_par
                        committed_par=${committed_par//_/.}
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

                                read N1 N0 area1 area0 < <(calculate_areas $agents_par $committed_par $arena_x_par $arena_y_par)
                                read width1 height1 x_min1 x_max1 < <(calculate_dimensions_and_coordinates $area1 $arena_x_par $arena_y_par)
                                read width0 height0 x_min0 x_max0 < <(calculate_dimensions_and_coordinates $area0 $arena_x_par $arena_y_par)
                                D=0.10
                                Hd=0.50
                                distXmax=$(echo "$arena_x_par * 0.50" | bc)
                                distXmin=$(echo "$distXmax * -1" | bc)
                                distYmax=$(echo "$arena_y_par * 0.50" | bc)
                                distYmin=$(echo "$distYmax * -1" | bc)
                                Wr=$(echo "$arena_x_par + $D" | bc)
                                Hr=$(echo "$arena_y_par + $D" | bc)
                                midXtop=$(echo "$Wr * $Hd" | bc)
                                midXbot=$(echo "$Wr * $Hd" | bc)
                                midYtop=$(echo "$Hr * $Hd" | bc)
                                midYbot=$(echo "$Hr * $Hd" | bc)
                                midXbot=$(echo "$midXbot - $Wr" | bc)
                                midYbot=$(echo "$midYbot - $Hr" | bc)
                                for i in $(seq 1 $RUNS); do
                                    config=`printf 'config_arenaX%s_Y%s_nrobots%s_rebroad%s_MsgExpTime%s_Thr%s_GT%s_run%s.argos' $arena_x_par $arena_y_par $agents_par $comm_par $msgs_par $thr_par $committed_par $i`
                                    cp $base_config $config
                                    sed -i "s|__TIME_EXPERIMENT__|$exp_len_par|g" $config
                                    sed -i "s|__SEED__|$i|g" $config
                                    sed -i "s|__KILOLOG__|$kilo_file|g" $config
                                    sed -i "s|__BROADCAST_POLICY__|$comm_par|g" $config
                                    sed -i "s|__MSG_HOPS__|$msgs_hop_par|g" $config
                                    sed -i "s|__MSG_EXPIRING_SECONDS__|$msgs_par|g" $config
                                    sed -i "s|__THRESHOLD__|$thr_par|g" $config
                                    sed -i "s|__COMMITTED_PERC__|$committed_par|g" $config
                                    sed -i "s|__MIDDLE_X_AREA__|$x_max1|g" $config
                                    sed -i "s|__ARENA_X__|$Wr|g" $config
                                    sed -i "s|__ARENA_Y__|$Hr|g" $config
                                    sed -i "s|__MID_X_TOP__|$midXtop|g" $config
                                    sed -i "s|__MID_X_BOT__|$midXbot|g" $config
                                    sed -i "s|__MID_Y_TOP__|$midYtop|g" $config
                                    sed -i "s|__MID_Y_BOT__|$midYbot|g" $config
                                    sed -i "s|__AGENT_DIST_X_MIN__|$distXmin|g" $config
                                    sed -i "s|__AGENT_DIST_Y_MIN__|$distYmin|g" $config
                                    sed -i "s|__AGENT_DIST_X_MAX__|$distXmax|g" $config
                                    sed -i "s|__AGENT_DIST_Y_MAX__|$distYmax|g" $config
                                    sed -i "s|__NUMROBOTS__|$agents_par|g" $config
                                    dt=$(date '+%d-%m-%Y_%H-%M-%S')
                                    kilo_file="${dt}__run#${i}.tsv"
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
    done
done