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
    base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time,msg_hops, sub_path,algo,arenaS,buf,ticks_per_sec = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_k_data_fifo(base, dtemp, exp_length, communication, n_agents, msg_exp_time, msg_hops, sub_path,algo,arenaS,buf, data_type)
    except KeyError as e:
        logging.error(f"KeyError processing {sub_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {sub_path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results, base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time, msg_hops, sub_path, ticks_per_sec

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
                                        _msg_exp_time = int(pre_folder.split('#')[-1])
                                        sub_path = os.path.join(dtemp,pre_folder)
                                        for folder in sorted(os.listdir(sub_path)):
                                            if '.' not in folder:
                                                msg_hops = int(folder.split('#')[-1])
                                                path = os.path.join(sub_path,folder)
                                                info_vec    = sub_path.split('/')
                                                algo    = ""
                                                arenaS  = ""
                                                for iv in info_vec:
                                                    if "results_loop" in iv:
                                                        algo        = iv[0]
                                                        arenaS      = iv.split('_')[-1][:-1]
                                                        break
                                                BUFFERS = [19,21,22,23,24]
                                                msg_exp_time = 60
                                                if arenaS=='big':
                                                    if n_agents==25:
                                                        BUFFERS=[11,15,17,19,21]
                                                    elif n_agents==100:
                                                        BUFFERS=[41,56,65,74,83]
                                                for buf in range(len(BUFFERS)):
                                                    if buf==1: msg_exp_time=120
                                                    elif buf==2: msg_exp_time=180
                                                    elif buf==3: msg_exp_time=300
                                                    elif buf==4: msg_exp_time=600
                                                    queue.put((base, dtemp, exp_length, n_agents, communication, data_type, msg_exp_time,msg_hops,path,algo,arenaS,BUFFERS[buf],ticks_per_sec))

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
                logging.info(f"Process {key} for task {process[1]} not found")
        cpu_usage = psutil.cpu_percent(percpu=True)
        idle_cpus = sum(1 for usage in cpu_usage if usage < 50)  # Consider CPU idle if usage is less than 50%
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
                        logging.info(f"Process {last_pid} for task {last_process[1]} terminated due to low memory")
                        # Requeue the task
                        queue.put(last_process[1])
                        break
        for key in to_remove:
            process = active_processes.pop(key)
            if process[1][3] == 100: h_counter -= 4
            elif process[1][3] == 25: h_counter -= 1
            logging.info(f"Process {key} for task {process[1]} joined and removed from active processes")
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
                    logging.info(f"Started process {p.pid} for task {task}")
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
