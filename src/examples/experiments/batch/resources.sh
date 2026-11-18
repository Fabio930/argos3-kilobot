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

available_ram_mb() {
    awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo
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

# Wait until a new job can start: fewer than MAX_JOBS running and enough free RAM for it.
# With no job running, one always starts, so the batch can never get stuck.
wait_for_free_slot() {
    local running
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
