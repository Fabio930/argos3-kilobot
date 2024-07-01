import data_extractor as dex
import os
import sys
import logging

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

def main():
    setup_logging()
    ticks_per_sec, data_type = check_inputs()
    for base in dex.Results().bases:
        for exp_l_dir in sorted(os.listdir(base)):
            if '.' not in exp_l_dir and '#' in exp_l_dir:
                exp_l_path = os.path.join(base, exp_l_dir)
                exp_length = int(exp_l_dir.split('#')[1])
                for arena_dir in sorted(os.listdir(exp_l_path)):
                    if '.' not in arena_dir and '#' in arena_dir:
                        arena_path = os.path.join(exp_l_path, arena_dir)
                        dim_x = float(arena_dir.split('#')[1].split(';')[0].replace('_', '.'))
                        dim_y = float(arena_dir.split('#')[1].split(';')[1].replace('_', '.'))
                        for comm_dir in sorted(os.listdir(arena_path)):
                            if '.' not in comm_dir and '#' in comm_dir:
                                comm_path = os.path.join(arena_path, comm_dir)
                                communication = int(comm_dir.split('#')[1])
                                for agents_dir in sorted(os.listdir(comm_path)):
                                    if '.' not in agents_dir and '#' in agents_dir:
                                        n_agents = int(agents_dir.split('#')[1])
                                        agents_path = os.path.join(comm_path, agents_dir)
                                        for thr_dir in sorted(os.listdir(agents_path)):
                                            if '.' not in thr_dir and '#' in thr_dir:
                                                thr_path = os.path.join(agents_path, thr_dir)
                                                threshold = float(thr_dir.split('#')[1].replace('_', '.'))
                                                for Dgt_dir in sorted(os.listdir(thr_path)):
                                                    if '.' not in Dgt_dir and '#' in Dgt_dir:
                                                        Dgt_path = os.path.join(thr_path, Dgt_dir)
                                                        delta_str = Dgt_dir.split('#')[1].replace('_', '.')
                                                        for msg_hop_dir in sorted(os.listdir(Dgt_path)):
                                                            if '.' not in msg_hop_dir and '#' in msg_hop_dir:
                                                                msg_hops = int(msg_hop_dir.split('#')[-1])
                                                                msg_hop_path = os.path.join(Dgt_path, msg_hop_dir)
                                                                for msg_exp_dir in sorted(os.listdir(msg_hop_path)):
                                                                    if '.' not in msg_exp_dir and '#' in msg_exp_dir:
                                                                        msg_exp_time = int(msg_exp_dir.split('#')[-1])
                                                                        msg_exp_path = os.path.join(msg_hop_path, msg_exp_dir)
                                                                        results = dex.Results()
                                                                        results.ticks_per_sec = ticks_per_sec
                                                                        results.extract_k_data(base, exp_length, communication, n_agents, threshold, delta_str, msg_exp_time, msg_exp_path, data_type)

if __name__ == "__main__":
    main()
