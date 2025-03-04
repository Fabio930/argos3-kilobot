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
    base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time,msg_hops, sub_path, ticks_per_sec = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        logging.info(f"Processing {sub_path} : START")
        results.extract_k_data(base, dtemp, exp_length, communication, n_agents, msg_exp_time, msg_hops, sub_path, data_type)
        logging.info(f"Processing {sub_path} : END")

    except KeyError as e:
        logging.error(f"KeyError processing {sub_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {sub_path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results, base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time, msg_hops, sub_path, ticks_per_sec
        gc.collect()

def main():
    setup_logging()
    ticks_per_sec, data_type = check_inputs()

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    for base in dex.Results().bases:
        for adir in sorted(os.listdir(base)):
            if '.' not in adir and '#' in adir:
                pre_apath = os.path.join(base, adir)
                exp_length = int(adir.split('#')[1])
                for dir in sorted(os.listdir(pre_apath)):
                    if '.' not in dir and '#' in dir:
                        communication = int(dir.split('#')[1])
                        pre_path = os.path.join(pre_apath, dir)
                        for zdir in sorted(os.listdir(pre_path)):
                            if '.' not in zdir and '#' in zdir:
                                n_agents = int(zdir.split('#')[1])
                                dtemp = os.path.join(pre_path, zdir)
                                for pre_folder in sorted(os.listdir(dtemp)):
                                    if '.' not in pre_folder:
                                        msg_exp_time = int(pre_folder.split('#')[-1])
                                        sub_path = os.path.join(dtemp,pre_folder)
                                        for folder in sorted(os.listdir(sub_path)):
                                            if '.' not in folder:
                                                msg_hops = int(folder.split('#')[-1])
                                                path = os.path.join(sub_path,folder)
                                                queue.put((base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time,msg_hops,path,ticks_per_sec))

    active_processes = []
    process_tasks = []  # List to keep track of tasks associated with each active process

    while not queue.empty() or len(active_processes) > 0:

        memory_used_by_processes = []
        # Calculate the memory used by each process
        to_remove = []
        for p in active_processes:
            try:
                proc = psutil.Process(p.pid)
                memory_used_by_processes.append(proc.memory_info().rss / (1024 * 1024))
            except psutil.NoSuchProcess:
                to_remove.append(active_processes.index(p))
        for index in to_remove:
            active_processes.pop(index)
            process_tasks.pop(index)
        
        max_memory_used = max(memory_used_by_processes, default=0)
        # Launch the next process only if the available memory is larger than the biggest memory occupied
        available_memory = psutil.virtual_memory().available / (1024 * 1024)
        cpu_usage = psutil.cpu_percent(percpu=True)
        idle_cpus = sum(1 for usage in cpu_usage if usage < 50)  # Consider CPU idle if usage is less than 50%

        # Kill the last process and put it back in the queue
        if available_memory < 30 and active_processes:
            last_process = active_processes.pop()
            last_task = process_tasks.pop()
            last_process.terminate()
            last_process.join()
            logging.info(f"Terminated process {last_process.pid} due to low memory")
            # Requeue the task
            queue.put(last_task)

        if available_memory > max_memory_used and len(active_processes) < idle_cpus:
            task = queue.get()
            p = Process(target=process_folder, args=(task,))
            p.start()
            active_processes.append(p)
            process_tasks.append(task)  # Track the task associated with this process
        to_remove = []
        for p in active_processes:
            if not p.is_alive():
                to_remove.append(active_processes.index(p))
                p.join()
        for index in to_remove:
            active_processes.pop(index)
            process_tasks.pop(index)
        gc.collect()
        logging.info(f"Active processes: {len(active_processes)}, processes waiting: {queue.qsize()}, available_memory: {available_memory:.2f} MB")
        time.sleep(.5)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
