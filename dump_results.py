import os, sys, logging, gc, psutil
import pandas as pd
import data_extractor as dex
from multiprocessing import Pool

# Configurazione Logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def check_inputs():
    ticks = 10
    if len(sys.argv) > 1:
        for i in range(len(sys.argv)):
            if sys.argv[i] == '-t':
                try:
                    ticks = int(sys.argv[i + 1])
                except:
                    logging.error("Il parametro -t deve essere un intero positivo.")
                    sys.exit(1)
    return ticks

def get_processed_keys():
    """
    Scansiona i file elaborati per identificare cosa è già stato fatto.
    Ritorna un set di tuple (chiavi univoche).
    """
    done_keys = set()
    msgs_path = "./msgs_data/messages_resume.csv"
    proc_dir = "./proc_data/"
    
    # 1. Controllo dal file dei messaggi
    if os.path.exists(msgs_path):
        try:
            df = pd.read_csv(msgs_path, sep="\t" if "\t" in open(msgs_path).readline() else ",")
            key_cols = ['ArenaSize', 'algo', 'threshold', 'GT', 'broadcast', 'n_agents', 'buff_dim', 'msg_hops', 'k_sampling']
            # chiave normalizzata che include k_sampling (costruita per colonne, senza iterrows)
            done_keys.update(zip(df['ArenaSize'].astype(str), df['algo'].astype(str), df['threshold'].astype(float),
                                 df['GT'].astype(float), df['broadcast'].astype(int), df['n_agents'].astype(int),
                                 df['buff_dim'].astype(int), df['msg_hops'].astype(int), df['k_sampling'].astype(int)))
        except Exception as e:
            logging.warning(f"Errore lettura {msgs_path}: {e}")

    # 2. Controllo incrociato con i file in proc_data (opzionale ma consigliato)
    # Se un esperimento è in messages_resume ma manca il relativo file in proc_data, 
    # potresti volerlo ricalcolare. Qui aggiungiamo logica se necessario.
    
    return done_keys

def process_folder(task):
    base, exp_length, communication, n_agents, threshold, delta_str, msg_hops, msg_exp_time, k_sampling, k_samp_path, ticks_per_sec = task
    results = dex.Results()
    results.ticks_per_sec = ticks_per_sec
    try:
        results.extract_k_data(base, exp_length, communication, n_agents, threshold, delta_str, msg_hops, msg_exp_time, k_sampling, k_samp_path)
    except (Exception, SystemExit) as e:
        # anche SystemExit: un worker del Pool che esce perde il task e blocca l'attesa dei risultati
        logging.error(f"Errore critico su {k_samp_path}: {e!r}")
    finally:
        del results
        gc.collect()
    return k_samp_path

def main():
    setup_logging()
    ticks_per_sec = check_inputs()
    
    logging.info("Analisi dati processati esistenti...")
    done_keys = get_processed_keys()
    
    tasks = []
    tasks_count = 0

    # Scansione Gerarchica dei dati grezzi (Raw Data)
    results_obj = dex.Results()
    for base in results_obj.bases:
        
        if "Oresults" in base:
            algo = "O"
        elif "Psresults" in base:
            algo = "Ps"
        else:
            algo = "P"
            
        if not os.path.exists(base): continue
        
        for exp_l_dir in sorted(os.listdir(base)):
            if '#' not in exp_l_dir: continue
            exp_l_path = os.path.join(base, exp_l_dir)
            exp_length = int(exp_l_dir.split('#')[1])
            
            for arena_dir in sorted(os.listdir(exp_l_path)):
                if '#' not in arena_dir: continue
                arena_size = arena_dir.split('#')[1]
                arena_path = os.path.join(exp_l_path, arena_dir)
                
                for comm_dir in sorted(os.listdir(arena_path)):
                    if '#' not in comm_dir: continue
                    communication = int(comm_dir.split('#')[1])
                    comm_path = os.path.join(arena_path, comm_dir)
                    
                    for agents_dir in sorted(os.listdir(comm_path)):
                        if '#' not in agents_dir: continue
                        n_agents = int(agents_dir.split('#')[1])
                        agents_path = os.path.join(comm_path, agents_dir)
                        
                        for thr_dir in sorted(os.listdir(agents_path)):
                            if '#' not in thr_dir: continue
                            threshold = float(thr_dir.split('#')[1].replace('_', '.'))
                            thr_path = os.path.join(agents_path, thr_dir)
                            
                            for Dgt_dir in sorted(os.listdir(thr_path)):
                                if '#' not in Dgt_dir: continue
                                delta_str = Dgt_dir.split('#')[1].replace('_', '.')
                                Dgt_path = os.path.join(thr_path, Dgt_dir)
                                
                                for msg_hop_dir in sorted(os.listdir(Dgt_path)):
                                    if '#' not in msg_hop_dir: continue
                                    msg_hops = int(msg_hop_dir.split('#')[-1])
                                    msg_hop_path = os.path.join(Dgt_path, msg_hop_dir)
                                    
                                    for msg_exp_dir in sorted(os.listdir(msg_hop_path)):
                                        if '#' not in msg_exp_dir: continue
                                        msg_exp_time = int(msg_exp_dir.split('#')[-1])
                                        msg_exp_path = os.path.join(msg_hop_path, msg_exp_dir)
                                        
                                        # il livello KSampling# e' opzionale: se manca, i .tsv stanno direttamente
                                        # in MsgExpTime# e k_sampling vale 0
                                        entries = sorted(os.listdir(msg_exp_path))
                                        k_entries = [(int(d.split('#')[-1]), os.path.join(msg_exp_path, d))
                                                     for d in entries if d.startswith("KSampling#") and os.path.isdir(os.path.join(msg_exp_path, d))]
                                        if not k_entries and any(d.endswith(".tsv") for d in entries):
                                            k_entries = [(0, msg_exp_path)]
                                        for k_sampling, k_samp_path in k_entries:
                                            
                                            # Identificatore univoco del task aggiornato
                                            current_key = (str(arena_size), str(algo), float(threshold), 
                                                           float(delta_str), int(communication), int(n_agents), 
                                                           int(msg_exp_time), int(msg_hops), int(k_sampling))
                                            
                                            if current_key not in done_keys:
                                                tasks.append((base, exp_length, communication, n_agents, 
                                                           threshold, delta_str, msg_hops, msg_exp_time, 
                                                           k_sampling, k_samp_path, ticks_per_sec))
                                                tasks_count += 1
                                            else:
                                                logging.debug(f"Saltato: {current_key}")

    logging.info(f"Task totali da elaborare: {tasks_count}")

    if not tasks:
        logging.info("Nessun task da elaborare.")
        return

    # Pool di processi: ogni worker elabora una cartella alla volta, senza attese tra un avvio e l'altro.
    # Memoria per task: ~ runs x agenti x tick x 16 byte (stati, quorum, messaggi, posizioni) piu' margine.
    max_agents = max(t[3] for t in tasks)
    est_task_mb = max(256, 100 * max_agents * 900 * 16 / (1024 ** 2) * 3)
    available_mb = psutil.virtual_memory().available / (1024 ** 2)
    n_workers = max(1, min(os.cpu_count() or 1, int((available_mb - 2048) // est_task_mb), len(tasks)))
    tasks.sort(key=lambda t: -t[3])  # i task con piu' agenti partono per primi
    logging.info(f"Avvio di {len(tasks)} task su {n_workers} worker")
    with Pool(processes=n_workers, maxtasksperchild=10) as pool:
        for done, path in enumerate(pool.imap_unordered(process_folder, tasks), start=1):
            logging.info(f"[{done}/{len(tasks)}] completato {path}")

    logging.info("Elaborazione completata con successo.")

if __name__ == "__main__":
    main()