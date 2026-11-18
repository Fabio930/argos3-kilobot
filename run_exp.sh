#!/bin/bash
# One launcher for every experiment variant (replaces runbatch.sh, run_seg.sh and run.sh).
# batch runs from the repository root (results in results_loop_runs_<variant>/ there),
# single writes the robot logs in the current folder.
#
#   ./run_exp.sh batch  <variant>                  full batch of the variant (loop_runs.sh)
#   ./run_exp.sh single <variant> [key=value ...]  one run with the GUI
#
# <variant>: id_static anon_static id_dynamic anon_dynamic id_confined anon_confined
#
# single-run keys (default in brackets, some depend on the variant):
#   robots [25]  committed [0.8, dynamic/confined 0.68]  arena_x [1.0]  arena_y [1.0]  (walkable area, m)
#   rebroadcast [id 2, anonymous 0 (fixed)]  exp [id 300, anonymous 0] (s)  hops [0]  hop_count [0]  threshold [0.8]
#   queue [robots-1]  k [0]  (anonymous)
#   start [300]  end [0]  next [0.92]  (dynamic, seconds / share)
#   time [0 = unlimited]  seed [1]  gui [1]
# e.g.  ./run_exp.sh single anon_confined robots=100 committed=0.76 arena_x=2.0 arena_y=0.5
#
# The build is always refreshed first (SKIP_BUILD=1 to skip it).

set -e
mode=$1
variant=$2
variants="id_static anon_static id_dynamic anon_dynamic id_confined anon_confined"

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
[[ -n "$mode" && " $variants " == *" $variant "* ]] || usage

repo=$(cd "$(dirname "$0")" && pwd)
batch_dir=src/examples/experiments/batch
template=$repo/$batch_dir/kilobot_ALF_BestN.argos

case "$mode" in
batch)
    cd "$repo"
    exec "$batch_dir/loop_runs.sh" "$batch_dir" kilobot_ALF_BestN.argos "$variant"
    ;;
single)
    shift 2
    ;;
*)
    usage
    ;;
esac

if [[ "$SKIP_BUILD" != "1" ]]; then
    make -C "$repo/build" -j"$(nproc)" > /dev/null
fi

calc() { LC_ALL=C awk "BEGIN { printf \"%.4f\", $1 }"; }

# defaults
comm=id; dynamic=false; confined=false
case "$variant" in anon_*) comm=anonymous;; esac
case "$variant" in *_dynamic) dynamic=true;; *_confined) confined=true;; esac
robots=25; arena_x=1.0; arena_y=1.0; hops=0; hop_count=0; threshold=0.8; k=0; queue=""
start=300; end=0; next=0.92; time=0; seed=1; gui=1
if [[ $comm == id ]]; then rebroadcast=2; exp=300; else rebroadcast=0; exp=0; fi
if [[ $dynamic == true || $confined == true ]]; then committed=0.68; else committed=0.8; fi

for kv in "$@"; do
    key=${kv%%=*}; val=${kv#*=}
    case "$key" in
        robots|committed|arena_x|arena_y|rebroadcast|exp|hops|hop_count|threshold|queue|k|start|end|next|time|seed|gui)
            printf -v "$key" '%s' "$val";;
        *) echo "Error: unknown key '$key'" 1>&2; usage;;
    esac
done
[[ -n "$queue" ]] || queue=$((robots - 1))

middle=0
[[ $confined == true ]] && middle=$(calc "$arena_x * ($committed - 0.5)")
wr=$(calc "$arena_x + 0.10")
hr=$(calc "$arena_y + 0.10")

config="config_single_${variant}.argos"
sed -e "s|__COMMUNICATION__|$comm|g" \
    -e "s|__DYNAMIC__|$dynamic|g" \
    -e "s|__CONFINED__|$confined|g" \
    -e "s|__BROADCAST_POLICY__|$rebroadcast|g" \
    -e "s|__MSG_HOPS__|$hops|g" \
    -e "s|__HOP_COUNT__|$hop_count|g" \
    -e "s|__MSG_EXPIRING_SECONDS__|$exp|g" \
    -e "s|__COMMITTED_PERC__|$committed|g" \
    -e "s|__THRESHOLD__|$threshold|g" \
    -e "s|__QUORUM_BUFFER_DIM__|$queue|g" \
    -e "s|__K_SAMPLING__|$k|g" \
    -e "s|__VARIATION_START_TIME__|$start|g" \
    -e "s|__VARIATION_END_TIME__|$end|g" \
    -e "s|__GT_AFTER_VAR__|$next|g" \
    -e "s|__MIDDLE_X_AREA__|$middle|g" \
    -e "s|__ARENA_X__|$wr|g" \
    -e "s|__ARENA_Y__|$hr|g" \
    -e "s|__MID_X_TOP__|$(calc "$wr / 2")|g" \
    -e "s|__MID_X_BOT__|$(calc "-$wr / 2")|g" \
    -e "s|__MID_Y_TOP__|$(calc "$hr / 2")|g" \
    -e "s|__MID_Y_BOT__|$(calc "-$hr / 2")|g" \
    -e "s|__AGENT_DIST_X_MIN__|$(calc "-$arena_x / 2")|g" \
    -e "s|__AGENT_DIST_X_MAX__|$(calc "$arena_x / 2")|g" \
    -e "s|__AGENT_DIST_Y_MIN__|$(calc "-$arena_y / 2")|g" \
    -e "s|__AGENT_DIST_Y_MAX__|$(calc "$arena_y / 2")|g" \
    -e "s|__NUMROBOTS__|$robots|g" \
    -e "s|__SEED__|$seed|g" \
    -e "s|__TIME_EXPERIMENT__|$time|g" \
    -e "s|__KILOLOG__|log.tsv|g" \
    -e "s|\"build/|\"$repo/build/|g" \
    "$template" > "$config"

if [[ "$gui" == "1" ]]; then
    camera_z=$(calc "($wr > $hr ? $wr : $hr) * 0.9")
    visualization="    <visualization>\n        <qt-opengl>\n            <camera>\n                <placements>\n                    <placement index=\"0\" position=\"0,0,$camera_z\" up=\"0,1,0\" look_at=\"0,0,0\" lens_focal_length=\"20\" />\n                </placements>\n            </camera>\n        </qt-opengl>\n    </visualization>"
    sed -i "s|</argos-configuration>|$visualization\n</argos-configuration>|" "$config"
fi

rm -f quorum_log_agent#*.tsv
echo "Running $variant -- $config ($*)"
status=0
argos3 -c "./$config" || status=$?
rm -f "$config"
exit $status
