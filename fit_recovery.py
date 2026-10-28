import os, sys, logging, argparse
import csv_results as CSVres
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

WEIB_IMAGES = False
CHUNK_SIZE = 10

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

    raw_files = []
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
            raw_files.append((file_path, algo, arena))

    # i file RAW vengono letti in streaming: una configurazione alla volta, a gruppi verso i worker,
    # con un numero limitato di gruppi in coda per tenere bassa la RAM
    def iter_chunks(chunk_size=CHUNK_SIZE):
        chunk = []
        for file_path, algo, arena in raw_files:
            logging.info(f"Reading {file_path} : START")
            for key, runs_data in csv_res.iter_recovery_csv(file_path, algo, arena, processed_keys):
                chunk.append((key, runs_data))
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
            logging.info(f"Reading {file_path} : END")
        if chunk:
            yield chunk

    n_workers = max(1, os.cpu_count() or 1)
    max_pending = n_workers * 2
    logging.info(f"Starting fits on {n_workers} workers")

    done = 0
    pending = set()

    def collect(finished):
        nonlocal done
        for fut in finished:
            fitted, n = fut.result()
            csv_res.store_recovery(fitted)
            done += n
            logging.info(f"[{done}] fitted")

    with ProcessPoolExecutor(max_workers=n_workers, initializer=_init_worker, initargs=(args.weib_images,)) as pool:
        for chunk in iter_chunks():
            if len(pending) >= max_pending:
                finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                collect(finished)
            pending.add(pool.submit(process_chunk, chunk))
        finished, _ = wait(pending)
        collect(finished)

    if done == 0:
        logging.info("No new configurations to fit")
        return
    logging.info("All tasks completed.")

if __name__ == "__main__":
    main()
