import csv_results as CSVres
import os, csv
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

# Process file with retries and memory management
def process_file(task):
    csv_res = CSVres.Data()
    tot_recovery = task
    try:
        logging.info(f"Processing {tuple(tot_recovery[0].keys())[0]} : START")
        csv_res.store_recovery(csv_res.fit_recovery_raw_data(tot_recovery))
        logging.info(f"Processing {tuple(tot_recovery[0].keys())[0]} : END")
    except KeyError as e:
        logging.error(f"KeyError processing {tuple(tot_recovery[0].keys())[0]}:{e}")
    except Exception as e:
        logging.error(f"Error processing {tuple(tot_recovery[0].keys())[0]}:{e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del csv_res,tot_recovery
        gc.collect()


def main():
    setup_logging()
    csv_res = CSVres.Data()
    processed_keys = []
    file_paths = []
    rec_path = []
    for base in csv_res.bases:
        if base.split('/')[-1] == "proc_data":
            files = [os.path.join(base, file) for file in sorted(os.listdir(base))]
            file_paths.extend(files)
        elif base.split('/')[-1] == "rec_data":
            files = [os.path.join(base, file) for file in sorted(os.listdir(base))]
            rec_path.extend(files)
    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    for file_path in rec_path:
        logging.info(f"Reading {file_path} : START")
        with open(file_path, 'r') as file:
            read = csv.reader(file)
            data = {tuple(rows[:9]): rows[9:] for rows in read}
        logging.info(f"Reading {file_path} : END")
        for i in data.keys():
            if i not in processed_keys:
                processed_keys.append(i)
    for file_path in file_paths:
        file = os.path.basename(file_path)
        if "recovery_data_raw" in file:
            arena = ''
            file = os.path.basename(file_path)
            no_ext_file = file.split('.')[0]
            sets = no_ext_file.split('_')
            algo = sets[0][0]
            for s in sets:
                val = s.split('#')
                if len(val) > 1:
                    if val[0] == 'r':
                        n_runs = val[1]
                    elif val[0] == 'a':
                        arena = val[1]
            logging.info(f"Reading {file_path} : START")
            data = csv_res.read_recovery_csv(file_path, algo, arena)
            logging.info(f"Reading {file_path} : END")
            for i in data.keys():
                if i not in processed_keys:
                    queue.put([{i:data.get(i)}])
    del csv_res,processed_keys,file_paths,rec_path
            
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
                if active_processes.index(p) not in to_remove: to_remove.append(active_processes.index(p))
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
            if active_processes.index(last_process) not in to_remove: to_remove.append(active_processes.index(last_process))
            logging.info(f"Terminated process {last_process.pid} due to low memory")
            # Requeue the task
            queue.put(last_task)

        if available_memory > max_memory_used and len(active_processes) < idle_cpus:
            task = queue.get()
            p = Process(target=process_file, args=(task,))
            p.start()
            active_processes.append(p)
            process_tasks.append(task)  # Track the task associated with this process
        for p in active_processes:
            if not p.is_alive():
                if active_processes.index(p) not in to_remove: to_remove.append(active_processes.index(p))
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