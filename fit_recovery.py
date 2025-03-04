import csv_results as CSVres
import os, csv
import sys
import logging
import gc
import time
import psutil
from multiprocessing import Process, Manager

processed_keys = []
memory_needed = (32 * 1024) * 0.2  # 25% of 32GB in MB
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
    retry_count = 50

    while retry_count > 0:
        try:
            # Check available memory before processing
            available_memory = psutil.virtual_memory().available / (1024 * 1024)  # in MB
            if available_memory < memory_needed:  # Adjust this threshold based on your needs
                raise MemoryError("Not enough memory available to process the file")
            if tuple(tot_recovery[0].keys())[0] not in processed_keys:
                logging.info(f"Processing {tuple(tot_recovery[0].keys())[0]} : START")
                csv_res.store_recovery(csv_res.fit_recovery_raw_data(tot_recovery))
                logging.info(f"Processing {tuple(tot_recovery[0].keys())[0]} : END")
            else:
                logging.info(f"Skipping {tuple(tot_recovery[0].keys())[0]} : Already processed")
            break
        except MemoryError as e:
            logging.error(f"MemoryError processing {tuple(tot_recovery[0].keys())[0]}:{e}")
            retry_count -= 1
            if retry_count > 0:
                logging.info(f"Retrying {tuple(tot_recovery[0].keys())[0]} ({retry_count}) after MemoryError")
                time.sleep(600)  # Delay before retrying
            else:
                logging.error(f"Failed due to MemoryError {tuple(tot_recovery[0].keys())[0]}")
            gc.collect()
            break
        except KeyError as e:
            logging.error(f"KeyError processing {tuple(tot_recovery[0].keys())[0]}:{e}")
            gc.collect()
            break
        except Exception as e:
            logging.error(f"Error processing {tuple(tot_recovery[0].keys())[0]}:{e}")
            logging.debug(f"Exception details: {e}", exc_info=True)
            gc.collect()
            break

def main():
    setup_logging()
    csv_res = CSVres.Data()
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
                queue.put([{i:data.get(i)}])
    for file_path in rec_path:
        logging.info(f"Reading {file_path} : START")
        with open(file_path, 'r') as file:
            read = csv.reader(file)
            data = {tuple(rows[:9]): rows[9:] for rows in read}
        logging.info(f"Reading {file_path} : END")
        for i in data.keys():
            if i not in processed_keys:
                processed_keys.append(i)
    del csv_res
    gc.collect()
            
    active_processes = []

    while not queue.empty() or active_processes:

        # Calculate the memory used by each process
        memory_used_by_processes = []
        for p in active_processes:
            try:
                proc = psutil.Process(p.pid)
                memory_used_by_processes.append(proc.memory_info().rss / (1024 * 1024))
            except psutil.NoSuchProcess:
                active_processes.remove(p)
        
        max_memory_used = max(memory_used_by_processes, default=128)  # use default value of 128 MB

        # Launch the next process only if the available memory is larger than the biggest memory occupied
        available_memory = psutil.virtual_memory().available / (1024 * 1024)
        if available_memory > max_memory_used:
            task = queue.get()
            p = Process(target=process_file, args=(task,))
            p.start()
            active_processes.append(p)
        else:
            # Requeue the task if there's not enough memory
            queue.put(task)
            break
        for p in active_processes:
            if not p.is_alive():
                p.join()
                active_processes.remove(p)
        logging.info(f"Active processes: {len(active_processes)}")
        time.sleep(1)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()