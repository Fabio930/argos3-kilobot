#!/bin/bash
# Parallel ARGoS runs for loop_runs.sh, sized on this machine's CPUs and RAM.
# Source it, then call wait_for_free_slot before starting each background job.
#
# One run (100 kilobots, 2700 s) was measured at 1.14 cores and 253 MB at its peak
# (ARGoS + the 100 robot processes). The job count uses those peaks rounded up, so a full
# machine never has to share CPUs between runs. Some CPUs and RAM are always left free
# for the user. Every value can be overridden from the environment, e.g. MAX_JOBS=1 for a
# sequential batch.
#
# Running in parallel does not change the results: the simulated time is logical and the
# robot processes are synchronised at every tick (a seed run alone and among N parallel
# runs gives byte-identical logs).

RESERVED_CPUS=${RESERVED_CPUS:-2}         # CPUs never used by the batch
RESERVED_RAM_MB=${RESERVED_RAM_MB:-4096}  # RAM always left free
JOB_CPU_CENTICORES=${JOB_CPU_CENTICORES:-120}  # peak CPU of one run, in hundredths of a core
JOB_RAM_MB=${JOB_RAM_MB:-512}             # peak RAM of one run (measured 253 MB) plus margin
JOB_NICE=${JOB_NICE:-10}                  # priority of the jobs: higher is lower priority
RUN_TIMEOUT=${RUN_TIMEOUT:-5m}            # a run still going after this is stuck and killed (normal: max ~95 s
                                          # with 100 robots and 2700 s: raise it for longer or bigger runs)
RUN_RETRIES=${RUN_RETRIES:-1}             # attempts after a timeout before giving up on a run
MIN_FREE_GB=${MIN_FREE_GB:-20}            # free disk below this: proc_data is moved to ARCHIVE_DIR, then the batch stops
# Secondary disk for proc_data when the main disk runs out of space (empty: never move it)
ARCHIVE_DIR=${ARCHIVE_DIR-/media/admin/503618a1-b61d-4abf-b741-79275b0a8754/argos3-kilobot_proc_data}

available_ram_mb() {
    awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo
}

# Free space in GB on the filesystem of the batch folder
free_disk_gb() {
    df -P -BG "$wdir" | awk 'NR == 2 {print int($4)}'
}

# Move proc_data to ARCHIVE_DIR and leave a symlink in its place, so every script still finds it
# at proc_data/. Called with no job running (the dumps append to its CSV files). Returns 1 if not possible.
relocate_proc_data() {
    local src="$wdir/proc_data"
    if [[ -z "$ARCHIVE_DIR" || -L "$src" || ! -d "$src" ]]; then
        return 1
    fi
    if ! mkdir -p "$ARCHIVE_DIR" 2>/dev/null || [[ ! -w "$ARCHIVE_DIR" ]]; then
        echo "[$(date '+%F %T')] ARCHIVE_DIR '$ARCHIVE_DIR' not writable (disk not mounted?): proc_data not moved" 1>&2
        return 1
    fi
    local dst="$ARCHIVE_DIR/proc_data"
    if [[ -e "$dst" ]]; then
        echo "[$(date '+%F %T')] '$dst' already exists: proc_data not moved" 1>&2
        return 1
    fi
    echo "[$(date '+%F %T')] Low disk space: moving proc_data to $dst"
    if cp -a "$src" "$dst" && diff -rq "$src" "$dst" > /dev/null; then
        mv "$src" "$src.old" && ln -s "$dst" "$src" && rm -rf "$src.old"
        echo "[$(date '+%F %T')] proc_data moved: $src -> $dst ($(free_disk_gb) GB free)"
        return 0
    fi
    rm -rf "$dst"
    echo "[$(date '+%F %T')] Copy of proc_data to $dst failed: proc_data not moved" 1>&2
    return 1
}

# Stop the batch (after the jobs still running) if a setting could not be processed, or if the
# disk stays below MIN_FREE_GB even after moving proc_data away: runs would only fail from here on.
check_batch_health() {
    if [[ -e "$work_root/dump_failed" ]]; then
        wait
        echo "[$(date '+%F %T')] Batch stopped: processing failed for:" 1>&2
        cat "$work_root/dump_failed" 1>&2
        exit 1
    fi
    if (( $(free_disk_gb) < MIN_FREE_GB )); then
        # The dumps in the background free the raw logs of their setting: wait for them first
        wait
        if (( $(free_disk_gb) < MIN_FREE_GB )); then
            relocate_proc_data
        fi
        if (( $(free_disk_gb) < MIN_FREE_GB )); then
            echo "[$(date '+%F %T')] Batch stopped: only $(free_disk_gb) GB free (MIN_FREE_GB=$MIN_FREE_GB)" 1>&2
            exit 1
        fi
    fi
}

CPUS=$(nproc)
TOTAL_RAM_MB=$(awk '/^MemTotal:/ {print int($2 / 1024)}' /proc/meminfo)
jobs_by_cpu=$(( (CPUS - RESERVED_CPUS) * 100 / JOB_CPU_CENTICORES ))
jobs_by_ram=$(( (TOTAL_RAM_MB - RESERVED_RAM_MB) / JOB_RAM_MB ))
if [[ -z "${MAX_JOBS:-}" ]]; then
    MAX_JOBS=$(( jobs_by_cpu < jobs_by_ram ? jobs_by_cpu : jobs_by_ram ))
fi
(( MAX_JOBS < 1 )) && MAX_JOBS=1
echo "[$(date '+%F %T')] Machine: $CPUS CPUs, $TOTAL_RAM_MB MB RAM. Up to $MAX_JOBS parallel ARGoS runs ($RESERVED_CPUS CPUs and $RESERVED_RAM_MB MB RAM kept free), run timeout $RUN_TIMEOUT"
echo "[$(date '+%F %T')] Disk: stop below $MIN_FREE_GB GB free${ARCHIVE_DIR:+, proc_data moved to $ARCHIVE_DIR first}"

# Wait until a new job can start: fewer than MAX_JOBS running and enough free RAM for it.
# With no job running, one always starts, so the batch can never get stuck.
wait_for_free_slot() {
    local running
    check_batch_health
    while true; do
        running=$(jobs -rp | wc -l)
        if (( running == 0 )); then
            return
        fi
        if (( running < MAX_JOBS && $(available_ram_mb) >= RESERVED_RAM_MB + JOB_RAM_MB )); then
            return
        fi
        sleep 0.5
    done
}
