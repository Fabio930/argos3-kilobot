import csv_results as CSVres
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

# Process file with retries and memory management
def process_file(task):
    file_path = task
    retry_count = 50

    while retry_count > 0:
        try:
            # Check available memory before processing
            available_memory = psutil.virtual_memory().available / (1024 * 1024)  # in MB
            if available_memory < 1000:  # Adjust this threshold based on your needs
                raise MemoryError("Not enough memory available to process the file")

            csv_res = CSVres.Data()
            tot_recovery = []
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
            logging.info(f"Processing {file_path} : START")
            data = csv_res.read_recovery_csv(file_path, algo, arena)
            tot_recovery.append(data)
            if len(tot_recovery) > 0:
                csv_res.store_recovery(csv_res.fit_recovery_raw_data(tot_recovery))
            logging.info(f"Processing {file_path} : END")
            break
        except MemoryError as e:
            logging.error(f"MemoryError processing {file_path}: {e}")
            retry_count -= 1
            if retry_count > 0:
                logging.info(f"Retrying {file_path} ({retry_count}) after MemoryError")
                time.sleep(600)  # Delay before retrying
            else:
                logging.error(f"Failed {file_path} due to MemoryError")
            gc.collect()
        except KeyError as e:
            logging.error(f"KeyError processing {file_path}: {e}")
            logging.debug(f"Data structure: {data}")
            gc.collect()
            break
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
            logging.debug(f"Exception details: {e}", exc_info=True)
            gc.collect()
            break

def main():
    setup_logging()

    csv_res = CSVres.Data()
    file_paths = []
    for base in csv_res.bases:
        if base.split('/')[-1] == "proc_data":
            files = [os.path.join(base, file) for file in sorted(os.listdir(base))]
            file_paths.extend(files)

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    for file_path in file_paths:
        file = os.path.basename(file_path)
        if "recovery_data_raw" in file:
            queue.put(file_path)

    active_processes = []
    total_memory = psutil.virtual_memory().available / (1024 * 1024)  # Available memory in MB
    memory_per_process = 1000  # Adjust this value based on your memory usage per process

    while not queue.empty() or active_processes:
        # Calculate total memory used by active processes
        total_memory_used = sum(memory_per_process for p in active_processes)

        # Launch new processes if there is room
        while total_memory_used + memory_per_process <= total_memory and not queue.empty():
            task = queue.get()
            if total_memory_used + memory_per_process <= total_memory:
                p = Process(target=process_file, args=(task,))
                p.start()
                active_processes.append(p)
                total_memory_used += memory_per_process
            else:
                # Requeue the task if there's not enough memory
                queue.put(task)
                break

        # Check for completed processes
        for p in active_processes:
            if not p.is_alive():
                p.join()
                active_processes.remove(p)
                total_memory_used -= memory_per_process

        time.sleep(1)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()