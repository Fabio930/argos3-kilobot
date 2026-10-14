import os, sys, logging, psutil
import data_extractor as dex
from multiprocessing import Pool

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# Check command line inputs
# -t <ticks>  : ticks per second (default 10)
# --p11       : compute only P.1.1 (P results, MsgExpTime > 0, X in [1, n/5, 2n/5])
def check_inputs():
    ticks = 10
    only_p11 = False
    args = sys.argv[1:]
    if len(args) > 3:
        logging.error("Too many arguments --EXIT--")
        exit()
    i = 0
    while i < len(args):
        if args[i] == '-t':
            if i + 1 >= len(args):
                logging.error("BAD format input --EXIT--")
                exit()
            try:
                ticks = int(args[i + 1])
            except:
                logging.error("BAD format input\n-t must be followed by a positive integer --EXIT--")
                exit()
            i += 2
        elif args[i] == '--p11':
            only_p11 = True
            i += 1
        else:
            logging.error("BAD format input\nusage: [-t <positive integer>] [--p11] --EXIT--")
            exit()
    if ticks <= 0:
        logging.error("BAD format -t input type\nmust input a positive integer greater than zero --EXIT--")
        exit()
    return ticks, only_p11

# Number of rightmost valid messages hidden from the buffers for P.1.1
def p11_buf_cuts(n_agents):
    return sorted({1, n_agents // 5, 2 * n_agents // 5})

# Process folder with retries and memory management
def process_folder(task):
    base, dtemp, exp_length, n_agents, communication, msg_exp_time,msg_hops, buf_cut, sub_path,ticks_per_sec,states = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_k_data(base, dtemp, exp_length, communication, n_agents, msg_exp_time, msg_hops, sub_path, states, buf_cut)
    except KeyError as e:
        logging.error(f"KeyError processing {sub_path}: {e}")
    except Exception as e:
        logging.error(f"Error processing {sub_path}: {e}")
        logging.debug(f"Exception details: {e}", exc_info=True)
    finally:
        del results
    return sub_path, buf_cut

def main():
    setup_logging()
    ticks_per_sec, only_p11 = check_inputs()

    tasks = []

    states_by_gt = {25:dex.Results().assign_states(25,100),100:dex.Results().assign_states(100,100)}
    for base in dex.Results().bases:
        if only_p11 and not os.path.basename(base).lower().startswith("presults"): continue
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
                                        # T_m = 0 resta solo per P.0
                                        if only_p11 and msg_exp_time == 0: continue
                                        buf_cuts = p11_buf_cuts(n_agents) if only_p11 else [0]
                                        sub_path = os.path.join(dtemp,pre_folder)
                                        for folder in sorted(os.listdir(sub_path)):
                                            if '.' not in folder:
                                                msg_hops = int(folder.split('#')[-1])
                                                path = os.path.join(sub_path,folder)
                                                for buf_cut in buf_cuts:
                                                    tasks.append((base, dtemp, exp_length, n_agents, communication, msg_exp_time,msg_hops,buf_cut,path,ticks_per_sec,states_by_gt.get(n_agents)))

    if not tasks:
        logging.info("No tasks found")
        return
    logging.info(f"Starting {len(tasks)} tasks")

    # Memoria di picco stimata per task (misurata: ~2.4 GB con 100 agenti x 100 run), scala con agenti^2.
    def task_mb(n_agents):
        return max(512, 2600 * (n_agents / 100) ** 2)

    # I task si raggruppano per numero di agenti: ogni gruppo usa tanti worker quanti ne stanno in memoria.
    # I gruppi piu' pesanti partono per primi.
    done = 0
    for n_agents in sorted({t[3] for t in tasks}, reverse=True):
        group = [t for t in tasks if t[3] == n_agents]
        available_mb = psutil.virtual_memory().available / (1024 * 1024)
        n_workers = max(1, min(os.cpu_count() or 1, int((available_mb - 2048) // task_mb(n_agents)), len(group)))
        logging.info(f"{len(group)} tasks with {n_agents} agents on {n_workers} workers")
        with Pool(processes=n_workers, maxtasksperchild=1) as pool:
            for sub_path, buf_cut in pool.imap_unordered(process_folder, group):
                done += 1
                logging.info(f"[{done}/{len(tasks)}] completed {sub_path}" + (f" (X={buf_cut})" if buf_cut else ""))

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
