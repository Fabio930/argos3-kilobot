import os, sys, logging, gc, time, psutil, argparse
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
    parser = argparse.ArgumentParser(description="Process the ARGoS kilobot logs into proc_data.")
    parser.add_argument("-t", type=int, default=10, help="ARGoS ticks per second (default 10)")
    parser.add_argument("--leaf", default=None,
                        help="process only this setting folder, in this process, without merging into the Pickle files")
    args = parser.parse_args()
    if args.t <= 0:
        parser.error("-t must be a positive integer")
    return args

# Process folder with retries and memory management
def process_folder(task):
    ticks_per_sec,path,exp_length,variation_time,spat_corr,communication,adaptive_com,comm_type,id_aware,priority_k,n_agents,msg_exp_time,msg_hops,n_options,eta,eta_stop,init_distr,function,vote_msg,ctrl_par,setting,hop_count = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    results.setting = setting
    results.hop_count = hop_count
    try:
        results.extract_data(ticks_per_sec,path,exp_length,variation_time,spat_corr,communication,adaptive_com,comm_type,id_aware,priority_k,n_agents,msg_exp_time,msg_hops,n_options,eta,eta_stop,init_distr,function,vote_msg,ctrl_par)
    except KeyError as e:
        logging.error(f"KeyError processing {path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results, task

def merge_csv_results_into_pickle(output_dir="proc_data"):
    """Move the rows of the new CSV files into the Pickle file with the same name.

    Rows already in the Pickle file are kept; a setting processed again replaces
    its old rows (same 'setting' and 'option_id'), so nothing is overwritten or duplicated.
    """
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
            new_df = pd.read_csv(csv_file, sep="\t")
            if pkl_file.exists():
                old_df = pd.read_pickle(pkl_file)
                df = pd.concat([old_df, new_df], ignore_index=True)
            else:
                df = new_df
            if "setting" in df.columns:
                keys = ["setting"] + (["option_id"] if "option_id" in df.columns else [])
                has_key = df["setting"].notna()
                keyed = df[has_key].drop_duplicates(subset=keys, keep="last")
                df = pd.concat([df[~has_key], keyed], ignore_index=True)
            tmp_file = pkl_file.with_suffix(".pkl.tmp")
            df.to_pickle(tmp_file)
            os.replace(tmp_file, pkl_file)
            os.remove(csv_file)
            converted += 1
            logging.info(f"Merged {csv_file} into {pkl_file} ({len(df)} rows) and removed CSV.")
        except Exception as e:
            failed += 1
            logging.error(f"Error converting {csv_file}: {e}")
            logging.debug(f"Exception details: {e}", exc_info=True)

    logging.info(f"CSV to PKL merge completed. Merged={converted}, Failed={failed}.")

prefix_map = {
    "ExperimentLength": ("exp_length", int),
    "VariationTime": ("variation_time", int),
    "SpatCorr": ("spat_corr", float),
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

def task_for_leaf(base, leaf, ticks_per_sec, done=None):
    """Task tuple for process_folder from the settings in the folder path, or None to skip it."""
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
        return None

    comm_type = meta["comm_type"]
    id_aware = 0 if comm_type == "anon" else 1
    # Same rule as loop_runs.sh: hop count only with rebroadcast 1
    hop_count = 1 if (id_aware and meta["communication"] == 1) else 0
    setting = str(Path(os.path.basename(base)) / Path(leaf).relative_to(base))
    n_runs = len(list(Path(leaf).glob("*.tsv"))) // max(1, meta["n_agents"])
    if done is not None and done.get(setting) == n_runs:
        logging.info(f"Already processed ({n_runs} runs): {setting}")
        return None

    return (ticks_per_sec, leaf, meta["exp_length"], meta["variation_time"], meta["spat_corr"],
            meta["communication"], meta["adaptive_com"], comm_type, id_aware, meta["priority_k"],
            meta["n_agents"], meta["msg_exp_time"], meta["msg_hops"], meta["n_options"], meta["eta"],
            meta["eta_stop"], meta["init_distr"], meta["function"], meta["vote_msg"], meta["ctrl_par"],
            setting, hop_count)

def process_leaf(leaf, ticks_per_sec):
    """Process one setting folder in this process. Returns 0 if it is now in proc_data."""
    leaf = os.path.abspath(leaf)
    base = next((str(p) for p in [Path(leaf)] + list(Path(leaf).parents) if p.name.startswith("results_")), None)
    if base is None:
        logging.error(f"{leaf} is not inside a results_* folder")
        return 1
    task = task_for_leaf(base, leaf, ticks_per_sec)
    if task is None:
        return 1
    setting, n_agents = task[20], task[10]
    n_runs = len(list(Path(leaf).glob("*.tsv"))) // max(1, n_agents)
    process_folder(task)
    if dex.done_settings().get(setting) != n_runs:
        logging.error(f"Processing failed: {setting}")
        return 1
    return 0

def main():
    setup_logging()
    args = check_inputs()
    ticks_per_sec = args.t
    if args.leaf is not None:
        # One setting, called by loop_runs.sh as soon as all its runs are there
        sys.exit(process_leaf(args.leaf, ticks_per_sec))

    # Using a manager to handle the queue
    manager = Manager()
    queue = manager.Queue()


    # Rows left in CSV files by an interrupted run go into the Pickle files first
    merge_csv_results_into_pickle()
    done = dex.done_settings()

    for base in dex.Results().bases:
        leaf_dirs = set()
        for root, _dirs, files in os.walk(base):
            if any(f.endswith(".tsv") for f in files):
                leaf_dirs.add(root)

        for leaf in sorted(leaf_dirs):
            task = task_for_leaf(base, leaf, ticks_per_sec, done)
            if task is not None:
                queue.put(task)

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
            if process[1][10] == 100: h_counter -= 4
            elif process[1][10] == 25: h_counter -= 1
            logging.info(f"Process {key} for task {process[1][1]} joined and removed from active processes")
        if queue.qsize() > 0 and idle_cpus > 0 and available_memory > 8072:
            try:
                task = queue.get(block=False)
                start = True
                if task[10] == 100:
                    if h_counter < 15 : h_counter += 4
                    else:
                        queue.put(task)
                        start = False
                elif task[10] == 25:
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
    merge_csv_results_into_pickle()

if __name__ == "__main__":
    main()
