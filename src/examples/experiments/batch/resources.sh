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
MIN_FREE_GB=${MIN_FREE_GB:-20}            # free disk below this: proc_data is merged into ARCHIVE_DIR, then the batch stops
# External disk for proc_data when the main disk runs out of space. It must be mounted when
# the batch starts (check_archive_disk). Not set: the folder ARCHIVE_SUBDIR on the disk with
# filesystem UUID ARCHIVE_UUID (the 2 TB disk labelled HDD_2TB), wherever it is mounted.
# Empty: no external disk, proc_data is never moved.
ARCHIVE_UUID=${ARCHIVE_UUID:-9b8e83f3-4392-489f-b119-f6dd9fe534bf}
ARCHIVE_SUBDIR=${ARCHIVE_SUBDIR:-argos3-kilobot_proc_data}
if [[ -z "${ARCHIVE_DIR+set}" ]]; then
    archive_mount=$(findmnt -rn -S "UUID=$ARCHIVE_UUID" -o TARGET 2>/dev/null | head -n 1)
    if [[ -z "$archive_mount" ]]; then
        # Mount point left by udisks under any user's /media (or /run/media) folder
        archive_mount=$(ls -d /media/*/"$ARCHIVE_UUID" /run/media/*/"$ARCHIVE_UUID" 2>/dev/null | head -n 1)
    fi
    # Not mounted: check_archive_disk stops the batch with this path in the message
    ARCHIVE_DIR=${archive_mount:-/media/$USER/$ARCHIVE_UUID}/$ARCHIVE_SUBDIR
    unset archive_mount
fi

available_ram_mb() {
    awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo
}

# Free space in GB on the filesystem of the batch folder
free_disk_gb() {
    df -P -BG "$wdir" | awk 'NR == 2 {print int($4)}'
}

# Check, before any run, that the external disk of ARCHIVE_DIR is mounted and writable.
# Exits if it is not: without it the batch would stop as soon as the main disk fills up.
check_archive_disk() {
    if [[ -z "$ARCHIVE_DIR" ]]; then
        echo "[$(date '+%F %T')] ARCHIVE_DIR empty: no external disk, proc_data stays on this disk"
        return 0
    fi
    # First existing folder of the path: on the main disk if the external one is not mounted
    local probe="$ARCHIVE_DIR"
    while [[ ! -e "$probe" ]]; do
        probe=$(dirname "$probe")
    done
    if [[ $(stat -c %d "$probe") == $(stat -c %d "$wdir") ]]; then
        echo "Error: external disk for ARCHIVE_DIR '$ARCHIVE_DIR' not mounted ('$probe' is on the same disk as $wdir)" 1>&2
        echo "       Mount it, or run with ARCHIVE_DIR= to go on without it" 1>&2
        exit 1
    fi
    local test_file="$ARCHIVE_DIR/.write_test_$$"
    if ! mkdir -p "$ARCHIVE_DIR" 2>/dev/null || ! touch "$test_file" 2>/dev/null; then
        echo "Error: ARCHIVE_DIR '$ARCHIVE_DIR' is not writable" 1>&2
        exit 1
    fi
    rm -f "$test_file"
    echo "[$(date '+%F %T')] External disk OK: $ARCHIVE_DIR (mounted on $(findmnt -n -o TARGET -T "$ARCHIVE_DIR"), $(df -P -BG "$ARCHIVE_DIR" | awk 'NR == 2 {print int($4)}') GB free)"

    # proc_data left as a symlink to the external disk by an older version of this script:
    # back to a local folder, whose data are merged there from now on
    local src="$wdir/proc_data"
    if [[ -L "$src" ]]; then
        local target
        target=$(readlink -f "$src")
        if ! rm "$src" || ! mkdir -p "$src"; then
            echo "Error: cannot replace the proc_data symlink with a folder" 1>&2
            exit 1
        fi
        [[ -f "$target/processed_settings.txt" ]] && cp "$target/processed_settings.txt" "$src/"
        touch "$src/.offloaded"
        echo "[$(date '+%F %T')] proc_data was a symlink to $target: now a local folder merged into $ARCHIVE_DIR/proc_data"
    fi
    merge_archive_done_list
}

# Settings already on the external disk go into the local processed_settings.txt (union, local
# lines first), so they are skipped even if the local list was lost or another batch moved them there
merge_archive_done_list() {
    local ext="$ARCHIVE_DIR/proc_data/processed_settings.txt" loc="$wdir/proc_data/processed_settings.txt"
    [[ -f "$ext" ]] || return 0
    local before=0 after files=()
    if [[ -f "$loc" ]]; then
        before=$(grep -c . "$loc")
        files+=("$loc")
    fi
    files+=("$ext")
    if ! mkdir -p "$wdir/proc_data" || ! awk 'NF && !seen[$0]++' "${files[@]}" > "$loc.tmp" || ! mv "$loc.tmp" "$loc"; then
        rm -f "$loc.tmp"
        echo "Error: cannot merge $ext into $loc" 1>&2
        exit 1
    fi
    after=$(grep -c . "$loc")
    if (( after > before )); then
        echo "[$(date '+%F %T')] $(( after - before )) settings already on the external disk added to $loc: they will be skipped"
    fi
}

# Merge the local proc_data into ARCHIVE_DIR/proc_data (files with the same name are merged,
# see analysis/merge_proc_data.py). Called with no job running (the dumps append to its CSV files).
# proc_data/.offloaded records that its data now live on the external disk: at the end of the
# batch the files left are merged there too (finalize_offload). Returns 1 if not possible.
offload_proc_data() {
    local src="$wdir/proc_data" dst="$ARCHIVE_DIR/proc_data"
    if [[ -z "$ARCHIVE_DIR" || ! -d "$src" ]]; then
        return 1
    fi
    local need_kb free_kb
    need_kb=$(du -sk "$src" | cut -f1)
    free_kb=$(df -P -k "$ARCHIVE_DIR" | awk 'NR == 2 {print $4}')
    if (( free_kb < need_kb + 1048576 )); then
        echo "[$(date '+%F %T')] Not enough space on the external disk ($(( free_kb / 1024 )) MB free, $(( need_kb / 1024 )) MB to move): proc_data not moved" 1>&2
        return 1
    fi
    echo "[$(date '+%F %T')] Merging proc_data into $dst ($(( need_kb / 1024 )) MB)"
    touch "$src/.offloaded"
    if ! "$PY" "$wdir/analysis/merge_proc_data.py" "$src" "$dst"; then
        echo "[$(date '+%F %T')] Merge of proc_data into $dst failed: the files not merged are still in $src" 1>&2
        return 1
    fi
    echo "[$(date '+%F %T')] proc_data merged into $dst ($(free_disk_gb) GB free here)"
}

# Stop the batch (after the jobs still running) if a setting could not be processed, or if the
# disk stays below MIN_FREE_GB even after moving proc_data away: runs would only fail from here on.
check_batch_health() {
    if [[ -e "$work_root/dump_failed" ]]; then
        wait
        # If proc_data was moved to the external disk, what was written since goes there too
        declare -F finalize_offload > /dev/null && finalize_offload
        echo "[$(date '+%F %T')] Batch stopped: processing failed for:" 1>&2
        cat "$work_root/dump_failed" 1>&2
        exit 1
    fi
    if (( $(free_disk_gb) < MIN_FREE_GB )); then
        # The dumps in the background free the raw logs of their setting: wait for them first
        wait
        if (( $(free_disk_gb) < MIN_FREE_GB )); then
            if [[ -n "$ARCHIVE_DIR" ]] && ! offload_proc_data; then
                echo "[$(date '+%F %T')] Batch stopped: proc_data could not be moved to the external disk" 1>&2
                exit 1
            fi
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
echo "[$(date '+%F %T')] Disk: stop below $MIN_FREE_GB GB free${ARCHIVE_DIR:+, proc_data merged into $ARCHIVE_DIR/proc_data first}"

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
