#! /bin/bash

if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: loop_runs.sh (from src folder) <base_config_dir> <base_config_file_name> [arena_label]"
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

# Only one batch per folder: runs, logs and proc_data would otherwise mix
exec 9>"$wdir/.batch.lock"
if ! flock -n 9; then
    echo "Error: another batch is running in $wdir" 1>&2
    exit 1
fi

# Parallel runs sized on this machine (see resources.sh)
source "$(dirname "$0")/resources.sh"
PY="${PY:-python3}"
# Settings already processed into proc_data: <setting>\t<runs>
done_list="$wdir/proc_data/processed_settings.txt"
# Every run works in a folder of its own, so runs never share log or config files
work_root="$wdir/.work"
mkdir -p "$work_root"

# One run in its own folder: logs moved to the setting folder only if all robots wrote them.
# Arguments: run number, setting folder, robots, then the sed expressions for the config.
run_job() {
    local i=$1 ctrl_par_dir=$2 robots=$3
    shift 3
    local kilo_file="run#${i}.tsv"
    local work="$work_root/$(echo "$ctrl_par_dir" | md5sum | cut -c1-16)_run${i}"
    rm -rf "$work"
    mkdir -p "$work"
    # Absolute paths to the controller and loop functions: ARGoS runs inside the work folder
    sed "$@" -e "s|__SEED__|$i|g" -e "s|__KILOLOG__|$kilo_file|g" -e "s|\"build/|\"$wdir/build/|g" "$base_config" > "$work/exp.argos"
    # A run takes about 1.5 min: one still going after RUN_TIMEOUT s is stuck. timeout kills
    # ARGoS and its robot processes (same process group), and the run is tried again up to
    # RUN_RETRIES times.
    local argos_status attempt start_s
    for (( attempt = 0; attempt <= RUN_RETRIES; attempt++ )); do
        start_s=$(date +%s)
        (cd "$work" && nice -n "$JOB_NICE" timeout --kill-after=30 "$RUN_TIMEOUT" argos3 -c exp.argos > argos.log 2>&1)
        argos_status=$?
        if [[ $argos_status -ne 124 && $argos_status -ne 137 ]]; then
            break
        fi
        echo "[$(date '+%F %T')] TIMEOUT run $i after $(( $(date +%s) - start_s )) s (attempt $(( attempt + 1 ))/$(( RUN_RETRIES + 1 ))) -- $ctrl_par_dir" 1>&2
        rm -f "$work"/quorum_log_agent#*.tsv
    done
    local missing=0
    for (( j = 0; j < robots; j++ )); do
        if [[ ! -s "$work/quorum_log_agent#$j.tsv" ]]; then
            missing=1
            break
        fi
    done
    if [[ $argos_status -ne 0 || $missing == 1 ]]; then
        # Only complete runs go into the results
        echo "[$(date '+%F %T')] Run $i failed or incomplete (exit $argos_status) -- $ctrl_par_dir: logs discarded" 1>&2
    else
        echo "[$(date '+%F %T')] Done    run $i in $(( $(date +%s) - start_s )) s -- ${ctrl_par_dir#$res_dir/}"
        for (( j = 0; j < robots; j++ )); do
            mv "$work/quorum_log_agent#$j.tsv" "$ctrl_par_dir/quorum_log_agent#${j}_${kilo_file}"
        done
    fi
    rm -rf "$work"
}

# The arena label ends the folder name: data_extractor.py reads it from there (arena#<label>)
arena_label="${3:-bigA}"
res_dir=$wdir/"results_loop_runs_${arena_label}"
if [[ ! -e $res_dir ]]; then
    mkdir $res_dir
    echo "mkdir: directory '$res_dir' "
fi

#######################################
### experiment_length is in seconds ###
#######################################
hop_count=""
msgs_n_hops="0"
eta_init=""
eta_stop=""
init_distr=""
control_parameter=""
experiment_length="2700"
variation_time="0"
RUNS=100
options="2 5"
spatial_correlation="0 1"
numrobots="100"
comm_type_set="id_aware"
rebroadcast="1 2"
# adaptive_comm was removed: the Adaptive#0 directory level is kept so the analysis scripts still work
adaptive_set="0"
priority_k_set="0"
# Mean message lifetime in seconds. A decision every 5.1 s: these give the same mean number of
# decisions per message as message_timeout 3 6 12 24 48 in the Python model
msgs_timeout="14 29 59 120 242"
control="static linear polynomial"
voting_msgs="3 5 9 15"

for exp_len_par in $experiment_length; do
    exp_len_dir=$res_dir/"ExperimentLength#"$exp_len_par
    if [[ ! -e $exp_len_dir ]]; then
        mkdir $exp_len_dir
    fi
    for var_time_par in $variation_time; do
        var_time_dir=$exp_len_dir/"VariationTime#"$var_time_par
        if [[ ! -e $var_time_dir ]]; then
            mkdir $var_time_dir
        fi
        for options_par in $options; do
            options_dir=$var_time_dir/"Options#"$options_par
            if [[ ! -e $options_dir ]]; then
                mkdir $options_dir
            fi
            if [[ $options_par == "2" ]]; then
                eta_init="0.4 0.5"
                init_distr="0.5"
            else
                eta_init="0.7 0.8"
                init_distr="0.2"
            fi
            eta_init_list=($eta_init)
            eta_stop_list=($eta_stop)
            if [[ $var_time_par != "0" && ${#eta_init_list[@]} -ne ${#eta_stop_list[@]} ]]; then
                echo "Error: eta_init/eta_stop mismatch (eta_init=${#eta_init_list[@]}, eta_stop=${#eta_stop_list[@]})" 1>&2
                exit 1
            fi
            for idx in "${!eta_init_list[@]}"; do
                eta_i_par=${eta_init_list[$idx]}
                if [[ $var_time_par == "0" ]]; then
                    eta_s_par=$eta_i_par
                else
                    eta_s_par=${eta_stop_list[$idx]}
                fi
                eta_dir=$options_dir/"Eta#"$eta_i_par
                if [[ ! -e $eta_dir ]]; then
                    mkdir $eta_dir
                fi
                eta_stop_dir=$eta_dir/"EtaStop#"$eta_s_par
                if [[ ! -e $eta_stop_dir ]]; then
                    mkdir $eta_stop_dir
                fi
                for spatial_correlation_par in $spatial_correlation; do
                    spatial_correlation_dir=$eta_stop_dir/"SpatCorr#"$spatial_correlation_par
                    if [[ ! -e $spatial_correlation_dir ]]; then
                        mkdir $spatial_correlation_dir
                    fi
                    for agents_par in $numrobots; do
                        robots_dir=$spatial_correlation_dir/"Robots#"$agents_par
                        if [[ ! -e $robots_dir ]]; then
                            mkdir $robots_dir
                        fi
                        last_id=`expr $agents_par - 1`
                        for comm_type in $comm_type_set; do
                            comm_type_dir=$robots_dir/"CommType#"$comm_type
                            if [[ ! -e $comm_type_dir ]]; then
                                mkdir $comm_type_dir
                            fi
                            if [[ $comm_type == "anon" ]]; then
                                id_aware_val=0
                                priority_k_list=$priority_k_set
                                rebroadcast_list="0"
                            else
                                id_aware_val=1
                                priority_k_list="0"
                                rebroadcast_list=$rebroadcast
                            fi
                            for comm_par in $rebroadcast_list; do
                                comm_dir=$comm_type_dir/"Rebroadcast#"$comm_par
                                if [[ ! -e $comm_dir ]]; then
                                    mkdir $comm_dir
                                fi
                                if [[ $comm_type == "anon" ]]; then
                                    hop_count="0"
                                elif [[ $comm_par == "1" ]]; then
                                    hop_count="1"
                                else
                                    hop_count="0"
                                fi
                                for adaptive_par in $adaptive_set; do
                                    if [[ $comm_type == "anon" && $adaptive_par != "0" ]]; then
                                        continue
                                    fi
                                    if [[ $comm_type != "anon" && $comm_par == "0" && $adaptive_par != "0" ]]; then
                                        continue
                                    fi
                                    adaptive_dir=$comm_dir/"Adaptive#"$adaptive_par
                                    if [[ ! -e $adaptive_dir ]]; then
                                        mkdir $adaptive_dir
                                    fi
                                    for priority_k_par in $priority_k_list; do
                                        priority_dir=$adaptive_dir/"PriorityK#"$priority_k_par
                                        if [[ ! -e $priority_dir ]]; then
                                            mkdir $priority_dir
                                        fi
                                        for msgs_par in $msgs_timeout; do
                                            msgs_dir=$priority_dir/"MsgExpTime#"$msgs_par
                                            if [[ ! -e $msgs_dir ]]; then
                                                mkdir $msgs_dir
                                            fi
                                            for msgs_hop_par in $msgs_n_hops; do
                                                msgs_hop_dir=$msgs_dir/"MsgHops#"$msgs_hop_par
                                                if [[ ! -e $msgs_hop_dir ]]; then
                                                    mkdir $msgs_hop_dir
                                                fi
                                                for init_par in $init_distr; do
                                                    init_dir=$msgs_hop_dir/"InitDistr#"$init_par
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
                                                        elif [[ $control_par == "linear" ]]; then
                                                            control_parameter="0.0"
                                                        else
                                                            # Same base values as function_parameter in the Python model
                                                            control_parameter="0.6 0.8"
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
                                                                setting_key="results_loop_runs_${arena_label}/${ctrl_par_dir#$res_dir/}"
                                                                # Processed into proc_data with all its runs: nothing left to do (its raw logs are gone)
                                                                if grep -qxF "${setting_key}	${RUNS}" "$done_list" 2>/dev/null; then
                                                                    continue
                                                                fi
                                                                run_pids=()
                                                                for i in $(seq 1 $RUNS); do
                                                                    kilo_file="run#${i}.tsv"
                                                                    # A run is done when the logs of all its robots are there
                                                                    run_done=1
                                                                    for j in $(seq 0 $last_id); do
                                                                        if [[ ! -s "$ctrl_par_dir/quorum_log_agent#${j}_${kilo_file}" ]]; then
                                                                            run_done=0
                                                                            break
                                                                        fi
                                                                    done
                                                                    if [[ $run_done == 1 ]]; then
                                                                        continue
                                                                    fi
                                                                    # Partial logs of this run (interrupted batch)
                                                                    rm -f "$ctrl_par_dir"/quorum_log_agent#*_"$kilo_file"
                                                                    wait_for_free_slot
                                                                    echo "[$(date '+%F %T')] Started run $i -- ${setting_key#results_loop_runs_${arena_label}/}"
                                                                    run_job "$i" "$ctrl_par_dir" "$agents_par" \
                                                                        -e "s|__BROADCAST_POLICY__|$comm_par|g" -e "s|__QUEUE_LENGHT__|$((agents_par - 1))|g" \
                                                                        -e "s|__ID_AWARE__|$id_aware_val|g" -e "s|__PRIORITY_K__|$priority_k_par|g" \
                                                                        -e "s|__NUMROBOTS__|$agents_par|g" -e "s|__MSG_EXPIRING_SECONDS__|$msgs_par|g" \
                                                                        -e "s|__TIME_EXPERIMENT__|$exp_len_par|g" -e "s|__MSGS_HOPS__|$msgs_hop_par|g" \
                                                                        -e "s|__hop_count__|$hop_count|g" -e "s|__N_OPTIONS__|$options_par|g" \
                                                                        -e "s|__OPTS_SPTIL_CORR__|$spatial_correlation_par|g" -e "s|__ETA_INIT__|$eta_i_par|g" \
                                                                        -e "s|__ETA_STOP__|$eta_s_par|g" -e "s|__VAR_TIME__|$var_time_par|g" \
                                                                        -e "s|__INIT_DISTR__|$init_par|g" -e "s|__CONTROL_TYPE__|$control_par|g" \
                                                                        -e "s|__VOTING_MSGS__|$voting_msgs_par|g" -e "s|__CONTROL_PARAMETER__|$control_parameter_par|g" &
                                                                    run_pids+=($!)
                                                                done
                                                                (( ${#run_pids[@]} > 0 )) && wait "${run_pids[@]}"
                                                                # All runs there: process the setting in the background while the next one runs,
                                                                # then delete its raw logs (about 4.7 GB per setting). They stay if processing fails.
                                                                n_logs=$(find "$ctrl_par_dir" -maxdepth 1 -name 'quorum_log_agent#*.tsv' | wc -l)
                                                                if (( n_logs == RUNS * agents_par )); then
                                                                    wait_for_free_slot
                                                                    (
                                                                        if nice -n "$JOB_NICE" "$PY" "$wdir/analysis/dump_results.py" --leaf "$ctrl_par_dir" > "$work_root/dump_$(echo "$ctrl_par_dir" | md5sum | cut -c1-16).log" 2>&1; then
                                                                            find "$ctrl_par_dir" -maxdepth 1 -name 'quorum_log_agent#*.tsv' -delete
                                                                            rm -f "$work_root/dump_$(echo "$ctrl_par_dir" | md5sum | cut -c1-16).log"
                                                                        else
                                                                            echo "Processing failed for $setting_key: raw logs kept (see $work_root)" 1>&2
                                                                        fi
                                                                    ) &
                                                                else
                                                                    echo "Setting incomplete ($n_logs of $(( RUNS * agents_par )) logs), not processed: $setting_key" 1>&2
                                                                fi
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
        done
    done
done

# Wait for the runs and processing still in the background
wait
echo "[$(date '+%F %T')] All simulations completed."
