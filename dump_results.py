import os, sys, logging, gc, time, psutil
import pandas as pd
import data_extractor as dex
from pathlib import Path
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
        logging.error("BAD format -t input type\nmust input a positive integer --EXIT--")
        exit()
    return ticks

# Process folder with retries and memory management
def process_folder(task):
    ticks_per_sec,path,exp_length,communication,adaptive_com,n_agents,msg_exp_time,msg_hops,n_options,eta,init_distr,function,vote_msg,ctrl_par = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_data(ticks_per_sec,path,exp_length,communication,adaptive_com,n_agents,msg_exp_time,msg_hops,n_options,eta,init_distr,function,vote_msg,ctrl_par)
    except KeyError as e:
        logging.error(f"KeyError processing {path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results, ticks_per_sec,path,exp_length,communication,adaptive_com,n_agents,msg_exp_time,msg_hops,n_options,eta,init_distr,function,vote_msg,ctrl_par

def convert_csv_results_to_pickle(output_dir="proc_data"):
    output_path = Path(os.path.abspath("")) / output_dir
    if not output_path.exists():
        logging.info(f"No CSV conversion needed: {output_path} does not exist.")
        return

    csv_files = sorted(output_path.rglob("*.csv"))
    if not csv_files:
        logging.info(f"No CSV files found in {output_path}.")
        return

    converted = 0
    failed = 0
    for csv_file in csv_files:
        pkl_file = csv_file.with_suffix(".pkl")
        try:
            df = pd.read_csv(csv_file, sep="\t")
            df.to_pickle(pkl_file)
            os.remove(csv_file)
            converted += 1
            logging.info(f"Converted {csv_file} -> {pkl_file} and removed CSV.")
        except Exception as e:
            failed += 1
            logging.error(f"Error converting {csv_file}: {e}")
            logging.debug(f"Exception details: {e}", exc_info=True)

    logging.info(f"CSV to PKL conversion completed. Converted={converted}, Failed={failed}.")

def main():
    setup_logging()
    ticks_per_sec = check_inputs()

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()

    for base in dex.Results().bases:
        for exp_len_dir in sorted(os.listdir(base)):
            if '#' in exp_len_dir:
                exp_len_path = os.path.join(base, exp_len_dir)
                exp_length = int(exp_len_dir.split('#')[1])
                for comm_dir in sorted(os.listdir(exp_len_path)):
                    if '#' in comm_dir:
                        comm_path = os.path.join(exp_len_path, comm_dir)
                        communication = int(comm_dir.split('#')[1])
                        for adpt_dir in sorted(os.listdir(comm_path)):
                            if '#' in adpt_dir:
                                adpt_path = os.path.join(comm_path, adpt_dir)
                                adaptive_com = int(adpt_dir.split('#')[1])
                                for agents_dir in sorted(os.listdir(adpt_path)):
                                    if '#' in agents_dir:
                                        agents_path = os.path.join(adpt_path, agents_dir)
                                        n_agents = int(agents_dir.split('#')[1])
                                        for msg_exp_time_dir in sorted(os.listdir(agents_path)):
                                            if '#' in msg_exp_time_dir:
                                                msg_exp_time_path = os.path.join(agents_path,msg_exp_time_dir)
                                                msg_exp_time = int(msg_exp_time_dir.split('#')[-1])
                                                for hops_dir in sorted(os.listdir(msg_exp_time_path)):
                                                    if '#' in hops_dir:
                                                        hops_path = os.path.join(msg_exp_time_path,hops_dir)
                                                        msg_hops = int(hops_dir.split('#')[-1])
                                                        for options_dir in sorted(os.listdir(hops_path)):
                                                            if '#' in options_dir:
                                                                options_path = os.path.join(hops_path,options_dir)
                                                                n_options = int(options_dir.split('#')[-1])
                                                                for eta_dir in sorted(os.listdir(options_path)):
                                                                    if '#' in eta_dir:
                                                                        eta_path = os.path.join(options_path,eta_dir)
                                                                        eta = float(eta_dir.split('#')[-1])
                                                                        for init_dir in sorted(os.listdir(eta_path)):
                                                                            if '#' in init_dir:
                                                                                init_path = os.path.join(eta_path,init_dir)
                                                                                init_distr = float(init_dir.split('#')[-1])
                                                                                for functn_dir in sorted(os.listdir(init_path)):
                                                                                    if '#' in functn_dir:
                                                                                        functn_path = os.path.join(init_path,functn_dir)
                                                                                        function = str(functn_dir.split('#')[-1])
                                                                                        for vote_msg_dir in sorted(os.listdir(functn_path)):
                                                                                            if '#' in vote_msg_dir:
                                                                                                vote_msg_path = os.path.join(functn_path,vote_msg_dir)
                                                                                                vote_msg = int(vote_msg_dir.split('#')[-1])
                                                                                                for ctrl_par_dir in sorted(os.listdir(vote_msg_path)):
                                                                                                    if '#' in ctrl_par_dir:
                                                                                                        ctrl_par_path = os.path.join(vote_msg_path,ctrl_par_dir)
                                                                                                        ctrl_par = float(ctrl_par_dir.split('#')[-1])
                                                                                                        queue.put((ticks_per_sec,ctrl_par_path,exp_length,communication,adaptive_com,n_agents,msg_exp_time,msg_hops,n_options,eta,init_distr,function,vote_msg,ctrl_par))

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
                logging.info(f"Process {key} for task {process[1][1]} not found")
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
                        logging.info(f"Process {last_pid} for task {last_process[1][1]} terminated due to low memory")
                        # Requeue the task
                        queue.put(last_process[1])
                        break
        for key in to_remove:
            process = active_processes.pop(key)
            if process[1][3] == 100: h_counter -= 1
            elif process[1][3] == 25: h_counter -= 1
            logging.info(f"Process {key} for task {process[1][1]} joined and removed from active processes")
        if queue.qsize() > 0 and idle_cpus > 0 and available_memory > 6072:
            try:
                task = queue.get(block=False)
                start = True
                if task[3] == 100:
                    if h_counter < 15 : h_counter += 1
                    else:
                        queue.put(task)
                        start = False
                elif task[3] == 25:
                    if h_counter < 18 : h_counter += 1
                    else:
                        queue.put(task)
                        start = False
                if start:
                    p = Process(target=process_folder, args=(task,))
                    p.start()
                    active_processes.update({p.pid:(p,task)})
                    logging.info(f"Started process {p.pid} for task {task[1]}")
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                logging.debug(f"Exception details: {e}", exc_info=True)
        if iteration % 300 == 0 or len(to_remove) > 0:
            logging.info(f"Active processes: {list(active_keys)}, processes waiting: {queue.qsize()}, available_memory: {available_memory:.2f} MB")
            gc.collect()
        time.sleep(.5)  # Avoid busy-waiting

    logging.info("All tasks completed.")
    convert_csv_results_to_pickle()

if __name__ == "__main__":
    main()
