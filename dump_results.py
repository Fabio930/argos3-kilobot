import data_extractor as dex
import os
import sys
import logging
import gc
import time
import psutil
from multiprocessing import Process, Manager, Queue

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
    base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type, ticks_per_sec, msg_exp_time, sub_path = task
    retry_count = 50

    while retry_count > 0:
        try:
            # Memory usage logging
            process = psutil.Process(os.getpid())
            logging.info(f"Memory usage before processing {sub_path}: {process.memory_info().rss / (1024 * 1024)} MB")

            results = dex.Results()
            results.ticks_per_sec = ticks_per_sec
            results.extract_k_data(base, agents_path, exp_length, communication, n_agents, threshold, delta_str, msg_exp_time, sub_path, data_type)
            gc.collect()
            # Memory usage logging
            logging.info(f"Memory usage after processing {sub_path}: {process.memory_info().rss / (1024 * 1024)} MB")

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
        for exp_l_dir in sorted(os.listdir(base)):
            if '.' not in exp_l_dir and '#' in exp_l_dir:
                exp_l_path = os.path.join(base, exp_l_dir)
                exp_length = int(exp_l_dir.split('#')[1])
                for thr_dir in sorted(os.listdir(exp_l_path)):
                    if '.' not in thr_dir and '#' in thr_dir:
                        thr_path = os.path.join(exp_l_path, thr_dir)
                        threshold = float(thr_dir.split('#')[1].replace('_', '.'))
                        for Dgt_dir in sorted(os.listdir(thr_path)):
                            if '.' not in Dgt_dir and '#' in Dgt_dir:
                                Dgt_path = os.path.join(thr_path, Dgt_dir)
                                delta_str = Dgt_dir.split('#')[1].replace('_', '.')
                                for comm_dir in sorted(os.listdir(Dgt_path)):
                                    if '.' not in comm_dir and '#' in comm_dir:
                                        comm_path = os.path.join(Dgt_path, comm_dir)
                                        communication = int(comm_dir.split('#')[1])
                                        for agents_dir in sorted(os.listdir(comm_path)):
                                            if '.' not in agents_dir and '#' in agents_dir:
                                                n_agents = int(agents_dir.split('#')[1])
                                                agents_path = os.path.join(comm_path, agents_dir)
                                                for pre_folder in sorted(os.listdir(agents_path)):
                                                    if '.' not in pre_folder:
                                                        msg_exp_time = int(pre_folder.split('#')[-1])
                                                        sub_path = os.path.join(agents_path, pre_folder)
                                                        tasks.append((base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type, ticks_per_sec, msg_exp_time, sub_path))

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    for task in tasks:
        queue.put(task)

    active_processes = []
    total_memory = psutil.virtual_memory().total / (1024 * 1024)  # Total memory in MB
    memory_per_process_25 = 335545 / 1024 # Memory used by each process with 25 agents
    memory_per_process_100 = 838861 / 1024 # Memory used by each process with 100 agents

    while not queue.empty() or active_processes:
        # Calculate total memory used by active processes
        total_memory_used = sum(memory_per_process_25 if n_agents == 25 else memory_per_process_100 for p, n_agents in active_processes)

        # Launch new processes if there is room
        while total_memory_used + min(memory_per_process_25, memory_per_process_100) <= total_memory and not queue.empty():
            task = queue.get()
            n_agents = task[4]
            required_memory = memory_per_process_25 if n_agents == 25 else memory_per_process_100
            if total_memory_used + required_memory < total_memory:
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
