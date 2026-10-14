import os, sys, logging, argparse
import csv_results as CSVres
from multiprocessing import Pool

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

WEIB_IMAGES = False

# Fit di un gruppo di chiavi: il worker restituisce i risultati, la scrittura la fa il processo principale
def process_chunk(chunk):
    csv_res = CSVres.Data()
    csv_res.weib_images = WEIB_IMAGES
    fitted = {}
    for key, runs_data in chunk:
        try:
            fitted.update(csv_res.fit_recovery_raw_data([{key: runs_data}]))
        except Exception as e:
            logging.error(f"Error processing {key}:{e}")
            logging.debug(f"Exception details: {e}", exc_info=True)
    return fitted, len(chunk)

def _init_worker(weib_images):
    global WEIB_IMAGES
    WEIB_IMAGES = weib_images

def main():
    parser = argparse.ArgumentParser(description="Weibull fit of the raw recovery data.")
    parser.add_argument("--weib-images", action="store_true", help="Salva in weib_images/ i grafici Weibull vs Kaplan-Meier della run 1 di ogni configurazione (lento)")
    args = parser.parse_args()
    setup_logging()
    csv_res = CSVres.Data()
    processed_keys = set()
    file_paths = []
    rec_path = []
    for base in csv_res.bases:
        if base.split('/')[-1] == "proc_data":
            files = [os.path.join(base, file) for file in sorted(os.listdir(base))]
            file_paths.extend(files)
        elif base.split('/')[-1] == "rec_data":
            files = [os.path.join(base, file) for file in sorted(os.listdir(base))]
            rec_path.extend(files)

    # chiavi gia' presenti in recovery_data.csv: non vengono rifittate
    for file_path in rec_path:
        if "images" not in file_path:
            logging.info(f"Reading {file_path} : START")
            with open(file_path, 'r', buffering=1024 * 1024) as file:
                header = file.readline()
                if header:
                    for line in file:
                        line = line.strip('\n')
                        if not line:
                            continue
                        row = line.split(',')
                        if len(row) >= 10:
                            processed_keys.add(tuple(row[:10]))
            logging.info(f"Reading {file_path} : END")

    tasks = []
    for file_path in file_paths:
        file = os.path.basename(file_path)
        if "recovery_data_raw" in file:
            arena = ''
            no_ext_file = file.split('.')[0]
            sets = no_ext_file.split('_')
            algo = sets[0][:2] if sets[0].lower().startswith("ps") else sets[0][0]
            for s in sets:
                val = s.split('#')
                if len(val) > 1 and val[0] == 'a':
                    arena = val[1]
            logging.info(f"Reading {file_path} : START")
            data = csv_res.read_recovery_csv(file_path, algo, arena)
            logging.info(f"Reading {file_path} : END")
            tasks.extend((k, v) for k, v in data.items() if k not in processed_keys)
            del data

    if not tasks:
        logging.info("No new configurations to fit")
        return

    # gruppi di chiavi per ridurre l'overhead di comunicazione tra processi
    n_workers = max(1, min(os.cpu_count() or 1, len(tasks)))
    chunk_size = max(1, min(25, len(tasks) // (n_workers * 4) or 1))
    chunks = [tasks[i:i + chunk_size] for i in range(0, len(tasks), chunk_size)]
    logging.info(f"Starting {len(tasks)} fits on {n_workers} workers ({len(chunks)} chunks)")

    done = 0
    with Pool(processes=n_workers, initializer=_init_worker, initargs=(args.weib_images,)) as pool:
        for fitted, n in pool.imap_unordered(process_chunk, chunks):
            csv_res.store_recovery(fitted)
            done += n
            logging.info(f"[{done}/{len(tasks)}] fitted")

    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
