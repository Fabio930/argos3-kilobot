import data_extractor as dex
import os
import sys
import logging
import psutil
from multiprocessing import Pool

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
    if ticks <= 0:
        logging.error("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks

# Process folder with retries and memory management
def process_folder(task):
    base, agents_path, exp_length, communication, n_agents, threshold, delta_str, ticks_per_sec, msg_exp_time, msg_hops, k_sampling, sub_path = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_k_data(base, agents_path, exp_length, communication, n_agents, threshold, delta_str, msg_exp_time, msg_hops, k_sampling, sub_path)
    except KeyError as e:
        logging.error(f"MemoryError processing {sub_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {sub_path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results
    return sub_path

def main():
    setup_logging()
    ticks_per_sec = check_inputs()

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
                                                        # il livello KSampling# e' opzionale: se manca, sotto MsgExpTime# ci sono direttamente le MsgHops# (k_sampling = 0)
                                                        k_entries = []
                                                        for k_folder in sorted(os.listdir(sub_path)):
                                                            if '.' in k_folder: continue
                                                            if k_folder.startswith("KSampling#"):
                                                                k_entries.append((int(k_folder.split('#')[-1]), os.path.join(sub_path, k_folder)))
                                                            elif k_folder.startswith("MsgHops#") and (0, sub_path) not in k_entries:
                                                                k_entries.append((0, sub_path))
                                                        for k_sampling, k_path in k_entries:
                                                                for hops_folder in sorted(os.listdir(k_path)):
                                                                    if '.' not in hops_folder and hops_folder.startswith("MsgHops#"):
                                                                        msg_hops = hops_folder.split('#')[-1]
                                                                        path = os.path.join(k_path, hops_folder)
                                                                        tasks.append((base, agents_path, exp_length, communication, n_agents, threshold, delta_str, ticks_per_sec, msg_exp_time, msg_hops, k_sampling, path))

    if not tasks:
        logging.info("No tasks found")
        return

    # Pool di processi: ogni worker elabora una cartella alla volta, senza attese tra un avvio e l'altro.
    # Il numero di worker e' limitato dalle CPU e dalla memoria disponibile (stima per il task piu' grande).
    max_agents = max(t[4] for t in tasks)
    est_task_mb = max(256, 100 * max_agents * 1200 * 6 / (1024 * 1024) * 3)
    available_mb = psutil.virtual_memory().available / (1024 * 1024)
    n_workers = max(1, min(os.cpu_count() or 1, int((available_mb - 2048) // est_task_mb), len(tasks)))
    # i task piu' pesanti (piu' agenti) partono per primi per bilanciare il carico
    tasks.sort(key=lambda t: -t[4])
    logging.info(f"Starting {len(tasks)} tasks on {n_workers} workers")

    with Pool(processes=n_workers, maxtasksperchild=20) as pool:
        for done, path in enumerate(pool.imap_unordered(process_folder, tasks), start=1):
            logging.info(f"[{done}/{len(tasks)}] completed {path}")

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()