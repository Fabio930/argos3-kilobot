import os, csv, sys, logging, gc, time, psutil
import csv_results as CSVres
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
        csv_res.store_recovery(csv_res.fit_recovery_raw_data(tot_recovery))
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
    gc.collect()
    logging.info(f"Starting {queue.qsize()} tasks")

    # Active processes dictionary
    active_processes = {}
    iteration = 0

    while len(active_processes) > 0 or queue.qsize() > 0:
        iteration += 1

        to_remove = []
        # Calculate the memory used by each process
        active_keys = active_processes.keys()
        available_memory = psutil.virtual_memory().available / (1024 * 1024)
        for key in active_keys:
            try:
                proc = psutil.Process(key)
                if proc.status() == psutil.STATUS_DEAD or proc.status() == psutil.STATUS_ZOMBIE:
                    process = active_processes.get(key)
                    process[0].terminate()
                    process[0].join()
                    if process[0].is_alive():
                        logging.warning(f"Process {key} could not be terminated properly.")
                    else:
                        to_remove.append(key)
            except psutil.NoSuchProcess:
                to_remove.append(key)
                logging.info(f"Process {key} for task {list(process[1][0].keys())[0]} not found")
        cpu_usage = psutil.cpu_percent(percpu=True)
        idle_cpus = sum(1 for usage in cpu_usage if usage < .5)  # Consider CPU idle if usage is less than 50%
        # Kill the last process and put it back in the queue
        if available_memory < 1024 and len(active_processes) > 0:
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
                        logging.info(f"Process {last_pid} for task {list(last_process[1][0].keys())[0]} terminated due to low memory")
                        # Requeue the task
                        queue.put(last_process[1])
                        break
        for key in to_remove:
            process = active_processes.pop(key)
            logging.info(f"Process {key} for task {list(process[1][0].keys())[0]} joined and removed from active processes")
        if queue.qsize() > 0 and idle_cpus > 0 and available_memory > 3072:
            try:
                task = queue.get(block=False)
                p = Process(target=process_file, args=(task,))
                p.start()
                active_processes.update({p.pid:(p,task)})
                logging.info(f"Started process {p.pid} for task {list(task[0].keys())[0]}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                logging.debug(f"Exception details: {e}", exc_info=True)
        if iteration % 3000 == 0 or len(to_remove) > 0:
            logging.info(f"Active processes: {list(active_keys)}, processes waiting: {queue.qsize()}, available_memory: {available_memory:.2f} MB\n")
            gc.collect()
        time.sleep(.1)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()