import data_extractor as dex
import os
import sys
import logging
import signal
import gc
import time
import psutil
from multiprocessing import Pool, cpu_count, TimeoutError

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(message)s',
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

# Signal handler for stuck processes
def signal_handler(signum, frame):
    raise TimeoutError("Task timed out")

# Process folder with retries and memory management
def process_folder(base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type, results, retry_count=3):
    try:
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(5400)  # Set alarm for 5400 seconds for each task
        logging.info(f"{agents_path}\tStarted")

        # Memory usage logging
        process = psutil.Process(os.getpid())
        logging.info(f"Memory usage before processing {agents_path}: {process.memory_info().rss / (1024 * 1024)} MB")

        results.extract_k_data(base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type)

        gc.collect()
        # Memory usage logging
        logging.info(f"Memory usage after processing {agents_path}: {process.memory_info().rss / (1024 * 1024)} MB")

        signal.alarm(0)  # Disable the alarm after successful completion

        # Garbage collection after task completion
        logging.info("Garbage collection completed")

    except TimeoutError as e:
        logging.error(f"Timeout processing {agents_path}: {e}")
        if retry_count > 0:
            logging.info(f"Retrying {agents_path} ({3 - retry_count + 1}/3)")
            gc.collect()  # Explicit garbage collection before retrying
            time.sleep(300)  # Delay before retrying
            process_folder(base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type, results, retry_count - 1)
        else:
            logging.error(f"Failed {agents_path} after 3 retries")
            return str(e)
    except MemoryError as e:
        logging.error(f"MemoryError processing {agents_path}: {e}")
        if retry_count > 0:
            logging.info(f"Retrying {agents_path} ({3 - retry_count + 1}/3) after MemoryError")
            gc.collect()  # Explicit garbage collection before retrying
            time.sleep(300)  # Delay before retrying
            process_folder(base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type, results, retry_count - 1)
        else:
            logging.error(f"Failed {agents_path} after 3 retries due to MemoryError")
            return str(e)
    except Exception as e:
        logging.error(f"Error processing {agents_path}: {e}")
        return str(e)
    return "Success"

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
                                                tasks.append((base, agents_path, exp_length, communication, n_agents, threshold, delta_str, data_type, results))

    logging.info("Pooling")
    pool = Pool(cpu_count())

    async_results = []
    for task in tasks:
        async_result = pool.apply_async(process_folder, args=task, callback=task_done, error_callback=task_error)
        async_results.append(async_result)

    pool.close()

    # Wait for all tasks to complete or timeout
    for async_result in async_results:
        try:
            async_result.get()  # Remove global timeout, handled within the process
        except TimeoutError:
            logging.error("Task timed out")
        except Exception as e:
            logging.error(f"Task failed with exception: {e}")

    pool.join()
    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
