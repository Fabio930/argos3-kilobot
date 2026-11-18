#! /bin/bash
#
# Batch runner for every experiment variant (run it from the repository root):
#
#   VARIANT=<variant> ./src/examples/experiments/batch/loop_runs.sh src/examples/experiments/batch kilobot_ALF_BestN.argos
#   ./src/examples/experiments/batch/loop_runs.sh src/examples/experiments/batch kilobot_ALF_BestN.argos <variant>
#
# <variant>:  id_static     (ex quorum_analysis)            anon_static    (ex Parker_replica)
#             id_dynamic    (ex quorum_analysis_dynamic)    anon_dynamic   (ex Parker_replica_dynamic)
#             id_confined   (ex quorum_analysis_segregation) anon_confined (ex Parker_replica_segregation)
#
# Each variant has its own block of sweep values below (the values of the original branch) and
# writes to results_loop_runs_<variant>/ with the directory layout of the original branch, so the
# scripts in analysis/<static|dynamic|segregation>/ read it (rename the folder with the prefix
# they expect, e.g. Oresults_* for ID-aware and Presults_* / Psresults_* for anonymous runs).
# Directories that already contain results are skipped, so an interrupted batch can be resumed.
#
# RUNS=<n> overrides the number of runs per configuration, SKIP_BUILD=1 skips the build check.

if [ "$#" -lt 2 ]; then
    echo "Usage: loop_runs.sh (from the repository root) <base_config_dir> <base_config_file_name> [variant]"
    exit 1
fi

VARIANT=${3:-$VARIANT}
case "$VARIANT" in
    id_static|anon_static|id_dynamic|anon_dynamic|id_confined|anon_confined) ;;
    *)  echo "Error: set VARIANT to one of id_static anon_static id_dynamic anon_dynamic id_confined anon_confined" 1>&2
        exit 1;;
esac

wdir=`pwd`
base_config=$1$2
if [ ! -e $base_config ]; then
    base_config=$wdir/$1/$2
    if [ ! -e $base_config ]; then
        echo "Error: missing configuration file '$base_config'" 1>&2
        exit 1
    fi
fi

# never run a batch on stale binaries
if [[ "$SKIP_BUILD" != "1" ]]; then
    if ! make -C "$wdir/build" -j"$(nproc)" > /dev/null; then
        echo "Error: build failed, fix it before running the batch" 1>&2
        exit 1
    fi
fi

res_dir=$wdir/"results_loop_runs_"$VARIANT
mkdir -p "$res_dir"

########################################################
### parameters shared by the run function (P_*)      ###
### experiment length and variation times in seconds ###
########################################################
P_COMM="id"; P_DYN="false"; P_CONF="false"
P_REBROAD=0; P_HOPS=0; P_EXP=0; P_COMMITTED=1; P_THR=0.8
P_QUEUE=1; P_K=0; P_VSTART=0; P_VEND=0; P_GT_AFTER=0; P_MIDDLE=0
P_INNER_X=1.0; P_INNER_Y=1.0; P_ROBOTS=25; P_TIME=900

calc() { LC_ALL=C awk "BEGIN { printf \"%.4f\", $1 }"; }

# committed robots on the left: the committed area is committed_percentage of the arena,
# so the density is the same in both areas. Returns the world x of the midline.
middle_x_area() {  # <inner_x> <committed_percentage>
    calc "$1 * ($2 - 0.5)"
}

# Runs RUNS seeds of the current P_* configuration and stores the logs in <target_dir>
run_seeds() {
    local target_dir=$1
    local label=$2
    mkdir -p "$target_dir"
    if find "$target_dir" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
        echo "Skipping non-empty results directory: $target_dir"
        return
    fi
    local wr=$(calc "$P_INNER_X + 0.10")
    local hr=$(calc "$P_INNER_Y + 0.10")
    local last_id=$((P_ROBOTS - 1))
    for i in $(seq 1 $RUNS); do
        local kilo_file="run#${i}.tsv"
        local config="config_${VARIANT}_${label}_run${i}.argos"
        sed -e "s|__COMMUNICATION__|$P_COMM|g" \
            -e "s|__DYNAMIC__|$P_DYN|g" \
            -e "s|__CONFINED__|$P_CONF|g" \
            -e "s|__BROADCAST_POLICY__|$P_REBROAD|g" \
            -e "s|__MSG_HOPS__|$P_HOPS|g" \
            -e "s|__MSG_EXPIRING_SECONDS__|$P_EXP|g" \
            -e "s|__COMMITTED_PERC__|$P_COMMITTED|g" \
            -e "s|__THRESHOLD__|$P_THR|g" \
            -e "s|__QUORUM_BUFFER_DIM__|$P_QUEUE|g" \
            -e "s|__K_SAMPLING__|$P_K|g" \
            -e "s|__VARIATION_START_TIME__|$P_VSTART|g" \
            -e "s|__VARIATION_END_TIME__|$P_VEND|g" \
            -e "s|__GT_AFTER_VAR__|$P_GT_AFTER|g" \
            -e "s|__MIDDLE_X_AREA__|$P_MIDDLE|g" \
            -e "s|__ARENA_X__|$wr|g" \
            -e "s|__ARENA_Y__|$hr|g" \
            -e "s|__MID_X_TOP__|$(calc "$wr / 2")|g" \
            -e "s|__MID_X_BOT__|$(calc "-$wr / 2")|g" \
            -e "s|__MID_Y_TOP__|$(calc "$hr / 2")|g" \
            -e "s|__MID_Y_BOT__|$(calc "-$hr / 2")|g" \
            -e "s|__AGENT_DIST_X_MIN__|$(calc "-$P_INNER_X / 2")|g" \
            -e "s|__AGENT_DIST_X_MAX__|$(calc "$P_INNER_X / 2")|g" \
            -e "s|__AGENT_DIST_Y_MIN__|$(calc "-$P_INNER_Y / 2")|g" \
            -e "s|__AGENT_DIST_Y_MAX__|$(calc "$P_INNER_Y / 2")|g" \
            -e "s|__NUMROBOTS__|$P_ROBOTS|g" \
            -e "s|__SEED__|$i|g" \
            -e "s|__TIME_EXPERIMENT__|$P_TIME|g" \
            -e "s|__KILOLOG__|$kilo_file|g" \
            "$base_config" > "$config"
        echo "Running next configuration -- $config"
        argos3 -c "./$config"
        for j in $(seq 0 $last_id); do
            mv "quorum_log_agent#$j.tsv" "$target_dir/quorum_log_agent#${j}_${kilo_file}"
        done
        rm -f "$config"
    done
}

dot2us() { echo "${1//./_}"; }

case "$VARIANT" in

########################################################################################
id_static)  # ex quorum_analysis
    experiment_length="900"; RUNS=${RUNS:-100}
    rebroadcast="1"; msg_expiring_sec="600"; numrobots="25"
    P_COMM="id"; P_COMMITTED=1; P_INNER_X=0.5; P_INNER_Y=0.5
    for P_TIME in $experiment_length; do
        for P_ROBOTS in $numrobots; do
            for P_REBROAD in $rebroadcast; do
                if [[ $P_REBROAD == "1" ]]; then messages_hops="0 1"; else messages_hops="0"; fi
                for P_EXP in $msg_expiring_sec; do
                    for P_HOPS in $messages_hops; do
                        dir=$res_dir/"ExperimentLength#$P_TIME/Rebroadcast#$P_REBROAD/Robots#$P_ROBOTS/MsgExpTime#$P_EXP/MsgHops#$P_HOPS"
                        run_seeds "$dir" "nrobots${P_ROBOTS}_rebroad${P_REBROAD}_hops${P_HOPS}_MsgExpTime${P_EXP}"
                    done
                done
            done
        done
    done;;

########################################################################################
anon_static)  # ex Parker_replica
    experiment_length="900"; RUNS=${RUNS:-100}
    rebroadcast="0"; numrobots="25 100"; msg_expiring_seconds="0 60 120 180 300 600"
    P_COMM="anonymous"; P_COMMITTED=1; P_INNER_X=1.0; P_INNER_Y=1.0; P_HOPS=0; P_K=0
    for P_TIME in $experiment_length; do
        for P_REBROAD in $rebroadcast; do
            for P_ROBOTS in $numrobots; do
                P_QUEUE=$((P_ROBOTS - 1))
                for P_EXP in $msg_expiring_seconds; do
                    dir=$res_dir/"ExperimentLength#$P_TIME/Rebroadcast#$P_REBROAD/Robots#$P_ROBOTS/MsgExpTime#$P_EXP/MsgHops#0"
                    run_seeds "$dir" "nrobots${P_ROBOTS}_rebroad${P_REBROAD}_MsgExpTime${P_EXP}"
                done
            done
        done
    done;;

########################################################################################
id_dynamic)  # ex quorum_analysis_dynamic
    experiment_length="1200"; RUNS=${RUNS:-100}
    P_VSTART=600; P_VEND=0
    rebroadcast="1 2"; msg_expiring_sec="60 120 180 300 600"; numrobots="25"
    threshold="0.8"; delta="0.68;0.92 0.92;0.68"
    P_COMM="id"; P_DYN="true"; P_INNER_X=0.5; P_INNER_Y=0.5
    for P_TIME in $experiment_length; do
        for P_ROBOTS in $numrobots; do
            for P_THR in $threshold; do
                for dlt_par in $delta; do
                    IFS=';' read -r P_COMMITTED P_GT_AFTER <<< "$dlt_par"
                    for P_REBROAD in $rebroadcast; do
                        if [[ $P_REBROAD == "1" ]]; then msg_hops="0 1"; else msg_hops="0"; fi
                        for P_HOPS in $msg_hops; do
                            for P_EXP in $msg_expiring_sec; do
                                dir=$res_dir/"ExperimentLength#$P_TIME/Threshold#$(dot2us $P_THR)/GT#$(dot2us $P_COMMITTED);$(dot2us $P_GT_AFTER)/Rebroadcast#$P_REBROAD/Robots#$P_ROBOTS/MsgExpTime#$P_EXP/MsgHops#$P_HOPS"
                                run_seeds "$dir" "nrobots${P_ROBOTS}_rebroad${P_REBROAD}_MsgHop${P_HOPS}_MsgExpTime${P_EXP}_Thr${P_THR}_Gt${P_COMMITTED}-${P_GT_AFTER}"
                            done
                        done
                    done
                done
            done
        done
    done;;

########################################################################################
anon_dynamic)  # ex Parker_replica_dynamic
    experiment_length="1200"; RUNS=${RUNS:-100}
    P_VSTART=600; P_VEND=0
    rebroadcast="0"; numrobots="25 100"; msg_expiring_seconds="60 180 600"
    threshold="0.8"; delta="0.68;0.92 0.92;0.68"
    P_COMM="anonymous"; P_DYN="true"; P_INNER_X=1.0; P_INNER_Y=1.0; P_HOPS=0
    for P_TIME in $experiment_length; do
        for P_THR in $threshold; do
            for dlt_par in $delta; do
                IFS=';' read -r P_COMMITTED P_GT_AFTER <<< "$dlt_par"
                for P_REBROAD in $rebroadcast; do
                    for P_ROBOTS in $numrobots; do
                        P_QUEUE=$((P_ROBOTS - 1))
                        if [ $P_ROBOTS -eq 25 ]; then k_sampling="1 4 9"; else k_sampling="1 19 39"; fi
                        for P_EXP in $msg_expiring_seconds; do
                            for P_K in $k_sampling; do
                                dir=$res_dir/"ExperimentLength#$P_TIME/Threshold#$(dot2us $P_THR)/GT#$(dot2us $P_COMMITTED);$(dot2us $P_GT_AFTER)/Rebroadcast#$P_REBROAD/Robots#$P_ROBOTS/MsgExpTime#$P_EXP/KSampling#$P_K/MsgHops#0"
                                run_seeds "$dir" "nrobots${P_ROBOTS}_rebroad${P_REBROAD}_MsgExpTime${P_EXP}_Thr${P_THR}_Gt${P_COMMITTED}-${P_GT_AFTER}_Ksamp${P_K}"
                            done
                        done
                    done
                done
            done
        done
    done;;

########################################################################################
id_confined)  # ex quorum_analysis_segregation
    experiment_length="900"; RUNS=${RUNS:-100}
    numrobots="25"; rebroadcast="2"; messages_hops="0"; msg_expiring_sec="60 120 180 300 600"
    threshold="0.80"; committed_percentage="0.68 0.76 0.84"
    arena_x_side=(0.500 1.000); arena_y_side=(0.500 0.250)
    P_COMM="id"; P_CONF="true"
    for P_TIME in $experiment_length; do
        for ap in "${!arena_x_side[@]}"; do
            P_INNER_X=${arena_x_side[$ap]}; P_INNER_Y=${arena_y_side[$ap]}
            for P_REBROAD in $rebroadcast; do
                for P_ROBOTS in $numrobots; do
                    for P_THR in $threshold; do
                        for P_COMMITTED in $committed_percentage; do
                            P_MIDDLE=$(middle_x_area $P_INNER_X $P_COMMITTED)
                            for P_HOPS in $messages_hops; do
                                for P_EXP in $msg_expiring_sec; do
                                    dir=$res_dir/"ExperimentLength#$P_TIME/ArenaType#$(dot2us $P_INNER_X);$(dot2us $P_INNER_Y)/Rebroadcast#$P_REBROAD/Robots#$P_ROBOTS/Threshold#$(dot2us $P_THR)/GT#$(dot2us $P_COMMITTED)/MsgHop#$P_HOPS/MsgExpTime#$P_EXP"
                                    run_seeds "$dir" "arenaX${P_INNER_X}_Y${P_INNER_Y}_nrobots${P_ROBOTS}_rebroad${P_REBROAD}_MsgExpTime${P_EXP}_Thr${P_THR}_GT${P_COMMITTED}"
                                done
                            done
                        done
                    done
                done
            done
        done
    done;;

########################################################################################
anon_confined)  # ex Parker_replica_segregation
    experiment_length="900"; RUNS=${RUNS:-100}
    rebroadcast="0"; numrobots="25 100"; k_sampling="0"
    threshold="0.80"; committed_percentage="0.68 0.76 0.84"
    msg_expiring_seconds="0"; messages_hops="0"
    arena_x_side=(1.000 2.000); arena_y_side=(1.000 0.500)
    P_COMM="anonymous"; P_CONF="true"
    for P_TIME in $experiment_length; do
        for ap in "${!arena_x_side[@]}"; do
            P_INNER_X=${arena_x_side[$ap]}; P_INNER_Y=${arena_y_side[$ap]}
            for P_ROBOTS in $numrobots; do
                P_QUEUE=$((P_ROBOTS - 1))
                for P_REBROAD in $rebroadcast; do
                    for P_THR in $threshold; do
                        for P_COMMITTED in $committed_percentage; do
                            P_MIDDLE=$(middle_x_area $P_INNER_X $P_COMMITTED)
                            for P_HOPS in $messages_hops; do
                                for P_EXP in $msg_expiring_seconds; do
                                    for P_K in $k_sampling; do
                                        dir=$res_dir/"ExperimentLength#$P_TIME/ArenaType#$(dot2us $P_INNER_X);$(dot2us $P_INNER_Y)/Rebroadcast#$P_REBROAD/Robots#$P_ROBOTS/Threshold#$(dot2us $P_THR)/GT#$(dot2us $P_COMMITTED)/MsgHop#$P_HOPS/MsgExpTime#$P_EXP/KSampling#$P_K"
                                        run_seeds "$dir" "arenaX${P_INNER_X}_Y${P_INNER_Y}_nrobots${P_ROBOTS}_rebroad${P_REBROAD}_MsgExpTime${P_EXP}_Thr${P_THR}_GT${P_COMMITTED}_Ksamp${P_K}"
                                    done
                                done
                            done
                        done
                    done
                done
            done
        done
    done;;
esac
