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
    ticks_per_sec,path,exp_length,variation_time,communication,adaptive_com,comm_type,id_aware,priority_k,n_agents,msg_exp_time,msg_hops,n_options,eta,eta_stop,init_distr,function,vote_msg,ctrl_par = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_data(ticks_per_sec,path,exp_length,variation_time,communication,adaptive_com,comm_type,id_aware,priority_k,n_agents,msg_exp_time,msg_hops,n_options,eta,eta_stop,init_distr,function,vote_msg,ctrl_par)
    except KeyError as e:
        logging.error(f"KeyError processing {path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results, ticks_per_sec,path,exp_length,variation_time,communication,adaptive_com,comm_type,id_aware,priority_k,n_agents,msg_exp_time,msg_hops,n_options,eta,eta_stop,init_distr,function,vote_msg,ctrl_par

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

    prefix_map = {
        "ExperimentLength": ("exp_length", int),
        "VariationTime": ("variation_time", float),
        "Options": ("n_options", int),
        "Eta": ("eta", float),
        "EtaStop": ("eta_stop", float),
        "Robots": ("n_agents", int),
        "CommType": ("comm_type", str),
        "Rebroadcast": ("communication", int),
        "Adaptive": ("adaptive_com", int),
        "PriorityK": ("priority_k", int),
        "MsgExpTime": ("msg_exp_time", int),
        "MsgHops": ("msg_hops", int),
        "InitDistr": ("init_distr", float),
        "Control": ("function", str),
        "VotingMsgs": ("vote_msg", int),
        "ControlParameter": ("ctrl_par", float),
    }
    required_keys = {v[0] for v in prefix_map.values()}

    for base in dex.Results().bases:
        leaf_dirs = set()
        for root, _dirs, files in os.walk(base):
            if any(f.endswith(".tsv") for f in files):
                leaf_dirs.add(root)

        for leaf in sorted(leaf_dirs):
            rel_parts = Path(leaf).relative_to(base).parts
            meta = {}
            for part in rel_parts:
                if "#" not in part:
                    continue
                prefix, raw_val = part.split("#", 1)
                if prefix in prefix_map:
                    key, caster = prefix_map[prefix]
                    try:
                        meta[key] = caster(raw_val)
                    except ValueError:
                        logging.error(f"Bad value for {prefix} in {part} (path: {leaf})")
                        meta[key] = None

            missing = sorted(required_keys.difference(meta.keys()))
            if missing:
                logging.warning(f"Skipping {leaf}, missing keys: {missing}")
                continue

            comm_type = meta["comm_type"]
            id_aware = 0 if comm_type == "anon" else 1

            queue.put((
                ticks_per_sec,
                leaf,
                meta["exp_length"],
                meta["variation_time"],
                meta["communication"],
                meta["adaptive_com"],
                comm_type,
                id_aware,
                meta["priority_k"],
                meta["n_agents"],
                meta["msg_exp_time"],
                meta["msg_hops"],
                meta["n_options"],
                meta["eta"],
                meta["eta_stop"],
                meta["init_distr"],
                meta["function"],
                meta["vote_msg"],
                meta["ctrl_par"],
            ))

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
            if process[1][9] == 100: h_counter -= 1
            elif process[1][9] == 25: h_counter -= 1
            logging.info(f"Process {key} for task {process[1][1]} joined and removed from active processes")
        if queue.qsize() > 0 and idle_cpus > 0 and available_memory > 6072:
            try:
                task = queue.get(block=False)
                start = True
                if task[9] == 100:
                    if h_counter < 15 : h_counter += 1
                    else:
                        queue.put(task)
                        start = False
                elif task[9] == 25:
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
