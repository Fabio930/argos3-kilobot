import data_extractor as dex
import os
import sys
from multiprocessing import Pool, cpu_count
import logging
from functools import partial
import time

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

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

def process_folder(base, dtemp, exp_length, n_agents, communication, data_type, results):
    try:
        logging.info(f"{dtemp}\tStarted")
        results.extract_k_data(base, dtemp, exp_length, communication, n_agents, data_type)
        logging.info(f"{dtemp}\tCompleted")
    except Exception as e:
        logging.error(f"Error processing {dtemp}: {e}")

def task_done(result):
    logging.info(f"Task completed with result: {result}")

def task_error(e):
    logging.error(f"Task failed with error: {e}")

def main():
    setup_logging()
    results = dex.Results()
    results.ticks_per_sec, data_type = check_inputs()

    tasks = []
    for base in results.bases:
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
                                tasks.append((base, dtemp, exp_length, n_agents, communication, data_type, results))

    logging.info("Pooling")
    pool = Pool(cpu_count())
    
    for task in tasks:
        pool.apply_async(process_folder, args=task, callback=task_done, error_callback=task_error)

    pool.close()
    pool.join()
    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
