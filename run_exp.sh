#!/bin/bash
# Launcher for the bestN experiments of this branch (QS_social_interaction_modulation).
# batch runs from the repository root (results in results_loop_runs_<arena_label>/ there),
# single writes the robot logs in the current folder.
#
#   ./run_exp.sh batch  [arena_label]       full batch (loop_runs.sh), arena_label [bigA]
#   ./run_exp.sh single [key=value ...]     one run with the GUI
#
# single-run keys (default in brackets):
#   robots [100]  id_aware [1]  rebroadcast [2]  hop_count [0]  hops [0]  timeout [10] (s)
#   k [0]  queue [robots-1]  options [5]  init_distr [0.2]  eta_init [0.8]  eta_stop [eta_init]
#   var_time [0]  spat_corr [1]  control [polynomial: static|linear|polynomial]  voting [5]
#   control_par [0.6]  time [0 = unlimited]  seed [1]  gui [1]
# e.g.  ./run_exp.sh single options=2 eta_init=0.5 init_distr=0.5 control=static control_par=0.8
#
# The build is always refreshed first (SKIP_BUILD=1 to skip it).

set -e
mode=$1

usage() { sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

repo=$(cd "$(dirname "$0")" && pwd)
batch_dir=src/examples/experiments/batch
template=$repo/$batch_dir/kilobot_ALF_BestN.argos

build() {
    if [[ "$SKIP_BUILD" != "1" ]]; then
        make -C "$repo/build" -j"$(nproc)" > /dev/null
    fi
}

case "$mode" in
batch)
    [[ $# -le 2 ]] || usage
    cd "$repo"
    build
    exec "$batch_dir/loop_runs.sh" "$batch_dir/" kilobot_ALF_BestN.argos ${2:+"$2"}
    ;;
single)
    shift
    ;;
*)
    usage
    ;;
esac

build

# defaults (those of src/examples/experiments/kilobot_ALF_BestN.argos)
robots=100; id_aware=1; rebroadcast=2; hop_count=0; hops=0; timeout=10; k=0; queue=""
options=5; init_distr=0.2; eta_init=0.8; eta_stop=""; var_time=0; spat_corr=1
control=polynomial; voting=5; control_par=0.6; time=0; seed=1; gui=1

for kv in "$@"; do
    key=${kv%%=*}; val=${kv#*=}
    case "$key" in
        robots|id_aware|rebroadcast|hop_count|hops|timeout|k|queue|options|init_distr|eta_init|eta_stop|var_time|spat_corr|control|voting|control_par|time|seed|gui)
            printf -v "$key" '%s' "$val";;
        *) echo "Error: unknown key '$key'" 1>&2; usage;;
    esac
done
[[ -n "$queue" ]] || queue=$((robots - 1))
[[ -n "$eta_stop" ]] || eta_stop=$eta_init
case "$control" in static|linear|polynomial) ;; *) echo "Error: control must be static, linear or polynomial" 1>&2; exit 1;; esac

config="config_single_bestN.argos"
sed -e "s|__ID_AWARE__|$id_aware|g" \
    -e "s|__BROADCAST_POLICY__|$rebroadcast|g" \
    -e "s|__hop_count__|$hop_count|g" \
    -e "s|__MSGS_HOPS__|$hops|g" \
    -e "s|__MSG_EXPIRING_SECONDS__|$timeout|g" \
    -e "s|__PRIORITY_K__|$k|g" \
    -e "s|__QUEUE_LENGHT__|$queue|g" \
    -e "s|__N_OPTIONS__|$options|g" \
    -e "s|__INIT_DISTR__|$init_distr|g" \
    -e "s|__ETA_INIT__|$eta_init|g" \
    -e "s|__ETA_STOP__|$eta_stop|g" \
    -e "s|__VAR_TIME__|$var_time|g" \
    -e "s|__OPTS_SPTIL_CORR__|$spat_corr|g" \
    -e "s|__CONTROL_TYPE__|$control|g" \
    -e "s|__VOTING_MSGS__|$voting|g" \
    -e "s|__CONTROL_PARAMETER__|$control_par|g" \
    -e "s|__NUMROBOTS__|$robots|g" \
    -e "s|__SEED__|$seed|g" \
    -e "s|__TIME_EXPERIMENT__|$time|g" \
    -e "s|__KILOLOG__|log.tsv|g" \
    -e "s|\"build/|\"$repo/build/|g" \
    "$template" > "$config"

if [[ "$gui" == "1" ]]; then
    visualization="    <visualization>\n        <qt-opengl>\n            <camera>\n                <placements>\n                    <placement index=\"0\" position=\"0,0,1\" up=\"0,1,0\" look_at=\"0,0,0\" lens_focal_length=\"23\" />\n                </placements>\n            </camera>\n        </qt-opengl>\n    </visualization>"
    sed -i "s|</argos-configuration>|$visualization\n</argos-configuration>|" "$config"
fi

rm -f quorum_log_agent#*.tsv
echo "Running bestN -- $config ($*)"
status=0
argos3 -c "./$config" || status=$?
rm -f "$config"
exit $status
