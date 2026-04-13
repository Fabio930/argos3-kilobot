import os, sys, logging, gc, time, psutil
import pandas as pd
import data_extractor as dex
from multiprocessing import Process, Manager

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
            for _, row in df.iterrows():
                # Creiamo una chiave normalizzata che include k_sampling
                key = (str(row['ArenaSize']), str(row['algo']), float(row['threshold']), 
                       float(row['GT']), int(row['broadcast']), int(row['n_agents']), 
                       int(row['buff_dim']), int(row['msg_hops']), int(row['k_sampling']))
                done_keys.add(key)
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
    except Exception as e:
        logging.error(f"Errore critico su {k_samp_path}: {e}")
    finally:
        del results
        gc.collect()

def main():
    setup_logging()
    ticks_per_sec = check_inputs()
    
    logging.info("Analisi dati processati esistenti...")
    done_keys = get_processed_keys()
    
    manager = Manager()
    queue = manager.Queue()
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
                                        
                                        for k_samp_dir in sorted(os.listdir(msg_exp_path)):
                                            if '#' not in k_samp_dir: continue
                                            k_sampling = int(k_samp_dir.split('#')[-1])
                                            k_samp_path = os.path.join(msg_exp_path, k_samp_dir)
                                            
                                            # Identificatore univoco del task aggiornato
                                            current_key = (str(arena_size), str(algo), float(threshold), 
                                                           float(delta_str), int(communication), int(n_agents), 
                                                           int(msg_exp_time), int(msg_hops), int(k_sampling))
                                            
                                            if current_key not in done_keys:
                                                queue.put((base, exp_length, communication, n_agents, 
                                                           threshold, delta_str, msg_hops, msg_exp_time, 
                                                           k_sampling, k_samp_path, ticks_per_sec))
                                                tasks_count += 1
                                            else:
                                                logging.debug(f"Saltato: {current_key}")

    logging.info(f"Task totali da elaborare: {tasks_count}")

    # Gestione Processi e Memoria (Logic Loop)
    active_processes = {}
    while active_processes or queue.qsize() > 0:
        available_mem = psutil.virtual_memory().available / (1024**2)
        cpu_usage = psutil.cpu_percent(percpu=True)
        idle_cpus = sum(1 for u in cpu_usage if u < 60)

        # Pulizia processi terminati
        finished = []
        for pid, (p, task) in active_processes.items():
            if not p.is_alive():
                p.join()
                finished.append(pid)
        for pid in finished:
            active_processes.pop(pid)

        # Avvio nuovi task se c'è risorse
        if queue.qsize() > 0 and idle_cpus > 0 and available_mem > 4000:
            task = queue.get()
            p = Process(target=process_folder, args=(task,))
            p.start()
            active_processes[p.pid] = (p, task)
            logging.info(f"Avviato PID {p.pid} - Task rimanenti: {queue.qsize()}")

        # Salvaguardia memoria: se scende troppo, non avviare e logga
        if available_mem < 2000:
            logging.warning(f"Memoria RAM critica ({available_mem:.0f}MB). Attesa rilascio...")
            time.sleep(5)

        time.sleep(1)

    logging.info("Elaborazione completata con successo.")

if __name__ == "__main__":
    main()