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
    retry_count = 50

    while retry_count > 0:
        try:
            # Memory usage logging
            process = psutil.Process(os.getpid())
            logging.info(f"Processing {sub_path} : START")

            results = dex.Results()
            results.ticks_per_sec = ticks_per_sec
            results.extract_k_data(base, dtemp, exp_length, communication, n_agents, msg_exp_time, msg_hops, sub_path, data_type)
            gc.collect()
            # Memory usage logging
            logging.info(f"Processing {sub_path} : END")

            break
        except MemoryError as e:
            logging.error(f"MemoryError processing {sub_path}: {e}")
            retry_count -= 1
            if retry_count > 0:
                logging.info(f"Retrying {sub_path} ({retry_count}) after MemoryError")
                time.sleep(600)  # Delay before retrying
            else:
                logging.error(f"Failed {sub_path} due to MemoryError")
            gc.collect()
        except Exception as e:
            logging.error(f"Error processing {sub_path}: {e}")
            gc.collect()
            break

def main():
    setup_logging()
    ticks_per_sec, data_type = check_inputs()

    tasks = []
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
                                                tasks.append((base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time,msg_hops,path,ticks_per_sec))

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    for task in tasks:
        queue.put(task)

    active_processes = []
    total_memory = psutil.virtual_memory().total / (1024 * 1024)  # Total memory in MB
    memory_per_process_25 = 838861/ 1024 # Memory used by each process with 25 agents 2,5%
    memory_per_process_100 = 8053063 / 1024 # Memory used by each process with 100 agents 24%

    while not queue.empty() or active_processes:
        # Calculate total memory used by active processes
        total_memory_used = sum(memory_per_process_25 if n_agents == 25 else memory_per_process_100 for p, n_agents in active_processes)

        # Launch new processes if there is room
        while total_memory_used + min(memory_per_process_25, memory_per_process_100) <= total_memory and not queue.empty():
            task = queue.get()
            n_agents = task[4]
            required_memory = memory_per_process_25 if n_agents == 25 else memory_per_process_100
            if total_memory_used + required_memory <= total_memory:
                p = Process(target=process_folder, args=(task,))
                p.start()
                active_processes.append((p, n_agents))
                total_memory_used += required_memory
            else:
                # Requeue the task if there's not enough memory
                queue.put(task)
                break

        # Check for completed processes
        for p, n_agents in active_processes:
            if not p.is_alive():
                p.join()
                active_processes.remove((p, n_agents))
                if n_agents == 25:
                    total_memory_used -= memory_per_process_25
                elif n_agents == 100:
                    total_memory_used -= memory_per_process_100

        time.sleep(1)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
