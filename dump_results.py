import data_extractor as dex
import os
import sys
import logging
import gc
import time
import psutil
from multiprocessing import Process, Manager

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# Check command line inputs
def check_inputs():
    ticks = 10
    data_type = "all"
    if len(sys.argv) > 7:
        logging.error("Too many arguments --EXIT--")
        exit()
    if len(sys.argv) > 1:
        for i in range(len(sys.argv)):
            if sys.argv[i] == '-d':
                if i + 1 >= len(sys.argv):
                    logging.error("BAD format input --EXIT--")
                    exit()
                data_type = str(sys.argv[i + 1])
            elif sys.argv[i] == '-t':
                if i + 1 >= len(sys.argv):
                    logging.error("BAD format input --EXIT--")
                    exit()
                try:
                    ticks = int(sys.argv[i + 1])
                except:
                    logging.error("BAD format input\n-t must be followed by a positive integer --EXIT--")
                    exit()
    if data_type not in {"all", "quorum", "freq"}:
        logging.error("BAD format -d input type\nallowed entries are: all, quorum or freq --EXIT--")
        exit()
    if ticks <= 0:
        logging.error("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks, data_type

# Process folder with retries and memory management
def process_folder(task):
    base, exp_length, communication, n_agents, threshold, delta_str, msg_hops, msg_exp_time, msg_exp_path, data_type, ticks_per_sec = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_k_data(base, exp_length, communication, n_agents, threshold, delta_str, msg_hops, msg_exp_time, msg_exp_path, data_type)
    except KeyError as e:
        logging.error(f"KeyError processing {msg_exp_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {msg_exp_path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results,base, exp_length, communication, n_agents, threshold, delta_str, msg_hops, msg_exp_time, msg_exp_path, data_type, ticks_per_sec
def main():
    setup_logging()
    ticks_per_sec, data_type = check_inputs()

    manager = Manager()
    queue = manager.Queue()

    for base in dex.Results().bases:
        for exp_l_dir in sorted(os.listdir(base)):
            if '.' not in exp_l_dir and '#' in exp_l_dir:
                exp_l_path = os.path.join(base, exp_l_dir)
                exp_length = int(exp_l_dir.split('#')[1])
                for arena_dir in sorted(os.listdir(exp_l_path)):
                    if '.' not in arena_dir and '#' in arena_dir:
                        arena_path = os.path.join(exp_l_path, arena_dir)
                        for comm_dir in sorted(os.listdir(arena_path)):
                            if '.' not in comm_dir and '#' in comm_dir:
                                comm_path = os.path.join(arena_path, comm_dir)
                                communication = int(comm_dir.split('#')[1])
                                for agents_dir in sorted(os.listdir(comm_path)):
                                    if '.' not in agents_dir and '#' in agents_dir:
                                        n_agents = int(agents_dir.split('#')[1])
                                        agents_path = os.path.join(comm_path, agents_dir)
                                        for thr_dir in sorted(os.listdir(agents_path)):
                                            if '.' not in thr_dir and '#' in thr_dir:
                                                thr_path = os.path.join(agents_path, thr_dir)
                                                threshold = float(thr_dir.split('#')[1].replace('_', '.'))
                                                for Dgt_dir in sorted(os.listdir(thr_path)):
                                                    if '.' not in Dgt_dir and '#' in Dgt_dir:
                                                        Dgt_path = os.path.join(thr_path, Dgt_dir)
                                                        delta_str = Dgt_dir.split('#')[1].replace('_', '.')
                                                        for msg_hop_dir in sorted(os.listdir(Dgt_path)):
                                                            if '.' not in msg_hop_dir and '#' in msg_hop_dir:
                                                                msg_hops = msg_hop_dir.split('#')[-1]
                                                                msg_hop_path = os.path.join(Dgt_path, msg_hop_dir)
                                                                for msg_exp_dir in sorted(os.listdir(msg_hop_path)):
                                                                    if '.' not in msg_exp_dir and '#' in msg_exp_dir:
                                                                        msg_exp_time = int(msg_exp_dir.split('#')[-1])
                                                                        msg_exp_path = os.path.join(msg_hop_path, msg_exp_dir)
                                                                        queue.put((base, exp_length, communication, n_agents, threshold, delta_str, msg_hops, msg_exp_time, msg_exp_path, data_type, ticks_per_sec))

    gc.collect()
    logging.info(f"Starting {queue.qsize()} tasks")

    # Active processes dictionary
    active_processes = {}
    iteration = 0

    while len(active_processes) > 0 or queue.qsize() > 0:
        iteration += 1

        memory_used_by_processes = []
        to_remove = []
        # Calculate the memory used by each process
        active_keys = active_processes.keys()
        available_memory = psutil.virtual_memory().available / (1024 * 1024)
        for key in active_keys:
            try:
                proc = psutil.Process(key)
                memory_info = proc.memory_info().rss / (1024 * 1024)
                memory_used_by_processes.append(memory_info)
                if proc.status() != psutil.STATUS_RUNNING and proc.status() != psutil.STATUS_DISK_SLEEP:
                    process = active_processes.get(key)
                    process[0].terminate()
                    process[0].join()
                    if process[0].is_alive():
                        logging.warning(f"Process {key} could not be terminated properly.")
                    else:
                        to_remove.append(key)
            except psutil.NoSuchProcess:
                to_remove.append(key)
                logging.info(f"Process {key} for task {process[1][-3]} not found")
        max_memory_used = max(memory_used_by_processes, default=0)
        cpu_usage = psutil.cpu_percent(percpu=True)
        idle_cpus = sum(1 for usage in cpu_usage if usage < 50)  # Consider CPU idle if usage is less than 50%
        # Kill the last process and put it back in the queue
        if available_memory <= 1024 and len(active_processes) > 0:
            for i in range(1, len(active_keys) + 1):
                last_pid = list(active_keys)[-i]
                if last_pid not in to_remove:
                    last_process = active_processes.get(last_pid)
                    last_process[0].terminate()
                    last_process[0].join()
                    if last_process[0].is_alive():
                        logging.warning(f"Process {key} could not be terminated properly.")
                    else:
                        to_remove.append(last_pid)
                        logging.info(f"Process {last_pid} for task {last_process[1][-2]} terminated due to low memory")
                        # Requeue the task
                        queue.put(last_process[1])
                        break
        for key in to_remove:
            process = active_processes.pop(key)
            logging.info(f"Process {key} for task {process[1][-3]} joined and removed from active processes")
        if queue.qsize() > 0 and idle_cpus > 0 and available_memory > 3072:
            try:
                task = queue.get(block=False)
                p = Process(target=process_folder, args=(task,))
                p.start()
                active_processes.update({p.pid:(p,task)})
                logging.info(f"Started process {p.pid} for task {task[-3]}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                logging.debug(f"Exception details: {e}", exc_info=True)
        if iteration % 300 == 0 or len(to_remove) > 0:
            logging.info(f"Active processes: {list(active_keys)}, processes waiting: {queue.qsize()}, available_memory: {available_memory:.2f} MB")
            gc.collect()
        time.sleep(1)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
