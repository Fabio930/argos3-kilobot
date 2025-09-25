import os, sys, logging, gc, time, psutil
import data_extractor as dex
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
    if len(sys.argv) > 3:
        logging.error("Too many arguments --EXIT--")
        exit()
    if len(sys.argv) > 1:
        for i in range(len(sys.argv)):
            if sys.argv[i] == '-t':
                if i + 1 >= len(sys.argv):
                    logging.error("BAD format input --EXIT--")
                    exit()
                try:
                    ticks = int(sys.argv[i + 1])
                except:
                    logging.error("BAD format input\n-t must be followed by a positive integer --EXIT--")
                    exit()
            else:
                logging.error("BAD format input\n-t must be followed by a positive integer --EXIT--")
                exit()
    if ticks <= 0:
        logging.error("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks

# Process folder with retries and memory management
def process_folder(task):
    base, dtemp, exp_length, n_agents, communication, msg_exp_time,msg_hops, sub_path,ticks_per_sec,states = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_k_data(base, dtemp, exp_length, communication, n_agents, msg_exp_time, msg_hops, sub_path, states)
    except KeyError as e:
        logging.error(f"KeyError processing {sub_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {sub_path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results, base, dtemp, exp_length, n_agents, communication, msg_exp_time, msg_hops, sub_path, ticks_per_sec,states

def main():
    setup_logging()
    ticks_per_sec = check_inputs()

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    states_by_gt = {25:dex.Results().assign_states(25,100),100:dex.Results().assign_states(25,100)}
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
                                                if n_agents==25:
                                                    queue.put((base, dtemp, exp_length, n_agents, communication, msg_exp_time,msg_hops,path,ticks_per_sec,states_by_gt.get(n_agents)))

    gc.collect()
    logging.info(f"Starting {queue.qsize()} tasks")

    # Active processes dictionary
    active_processes = {}
    iteration = 0
    h_counter = 0

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
                logging.info(f"Process {key} for task {process[1][-3]} not found")
        cpu_usage = psutil.cpu_percent(percpu=True)
        idle_cpus = sum(1 for usage in cpu_usage if usage < 50)  # Consider CPU idle if usage is less than 50%
        # Kill the last process and put it back in the queue
        if available_memory < 2048 and len(active_processes) > 0:
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
                        logging.info(f"Process {last_pid} for task {last_process[1][-3]} terminated due to low memory")
                        # Requeue the task
                        queue.put(last_process[1])
                        break
        for key in to_remove:
            process = active_processes.pop(key)
            if process[1][3] == 100: h_counter -= 4
            elif process[1][3] == 25: h_counter -= 1
            logging.info(f"Process {key} for task {process[1][-3]} joined and removed from active processes")
        if queue.qsize() > 0 and idle_cpus > 0 and available_memory > 6072:
            try:
                task = queue.get(block=False)
                start = True
                if task[3] == 100:
                    if h_counter < 12 : h_counter += 4
                    else:
                        queue.put(task)
                        start = False
                elif task[3] == 25:
                    if h_counter < 15 : h_counter += 1
                    else:
                        queue.put(task)
                        start = False
                if start:
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
        time.sleep(.5)  # Avoid busy-waiting

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
