#include "quorum_comm.h"

uint8_t comm_anonymous = 0;
uint8_t comm_rebroadcast = 0;
uint8_t comm_msgs_n_hops = 0;
uint8_t comm_hop_count = 0;
uint8_t comm_k_sampling = 0;
uint16_t comm_expiring_s = 0;
comm_fifo_t comm_fifo;
uint64_t comm_own_sent = 0;
uint64_t comm_relayed = 0;

static uint8_t comm_sat_inc(const uint8_t value){
    return (value == UINT8_MAX) ? UINT8_MAX : (uint8_t)(value + 1);
}

/*-------------------------------------------------------------------*/
/*              FIFO queue of senders to relay (policy 2)            */
/*-------------------------------------------------------------------*/

static void comm_fifo_init(){
    comm_fifo.head = 0;
    comm_fifo.tail = 0;
    comm_fifo.count = 0;
}

static uint8_t comm_fifo_index(uint8_t offset){
    return (uint8_t)((comm_fifo.head + offset) % COMM_FIFO_SIZE);
}

/* Puts the sender at the tail: appended if new, moved to the tail if already queued. */
static void comm_fifo_push(uint8_t agent_id, uint8_t agent_state, uint8_t msg_n_hops){
    int16_t found = -1;
    for(uint8_t i = 0; i < comm_fifo.count; i++){
        if(comm_fifo.buffer[comm_fifo_index(i)].agent_id == agent_id){
            found = i;
            break;
        }
    }
    if(found >= 0){
        for(uint8_t i = (uint8_t)found; i + 1 < comm_fifo.count; i++)
            comm_fifo.buffer[comm_fifo_index(i)] = comm_fifo.buffer[comm_fifo_index(i + 1)];
        comm_fifo.tail = comm_fifo_index(comm_fifo.count - 1);
        comm_fifo.count--;
    }
    else if(comm_fifo.count >= COMM_FIFO_SIZE){
        comm_fifo.head = comm_fifo_index(1);
        comm_fifo.count--;
    }
    comm_fifo.buffer[comm_fifo.tail].agent_id = agent_id;
    comm_fifo.buffer[comm_fifo.tail].agent_state = agent_state;
    comm_fifo.buffer[comm_fifo.tail].msg_n_hops = msg_n_hops;
    comm_fifo.tail = (uint8_t)((comm_fifo.tail + 1) % COMM_FIFO_SIZE);
    comm_fifo.count++;
}

/* Drops the queued senders that are no longer in the buffer, keeping the order. */
static void comm_fifo_sync(){
    if(comm_fifo.count == 0) return;
    uint8_t present[32] = {0};
    for(uint8_t i = 0; i < num_quorum_items; i++){
        uint8_t id = quorum_buf[i].agent_id;
        present[id >> 3] |= (uint8_t)(1 << (id & 7));
    }
    uint8_t kept = 0;
    for(uint8_t i = 0; i < comm_fifo.count; i++){
        comm_fifo_item_t item = comm_fifo.buffer[comm_fifo_index(i)];
        if(present[item.agent_id >> 3] & (1 << (item.agent_id & 7))){
            comm_fifo.buffer[comm_fifo_index(kept)] = item;
            kept++;
        }
    }
    comm_fifo.count = kept;
    comm_fifo.tail = comm_fifo_index(kept);
}

/*-------------------------------------------------------------------*/
/*                           Protocol                                */
/*-------------------------------------------------------------------*/

void comm_configure(uint8_t anonymous, uint8_t rebroadcast, uint16_t expiring_s, uint8_t msgs_n_hops,
                    uint8_t hop_count, uint8_t queue_lenght, uint8_t k_sampling, uint32_t ticks_per_sec){
    comm_anonymous = anonymous ? 1 : 0;
    comm_expiring_s = expiring_s;
    if(comm_anonymous){
        comm_rebroadcast = 0;
        comm_msgs_n_hops = 0;
        comm_hop_count = 0;
        comm_k_sampling = k_sampling;
        quorum_init(queue_lenght, (uint32_t)expiring_s * ticks_per_sec, 1);
    }
    else{
        comm_rebroadcast = (rebroadcast <= 2) ? rebroadcast : 0;
        comm_msgs_n_hops = msgs_n_hops;
        comm_hop_count = hop_count ? 1 : 0;
        comm_k_sampling = 0;
        quorum_init(QUORUM_CAPACITY, (uint32_t)expiring_s * ticks_per_sec, 0);
    }
    comm_fifo_init();
    comm_own_sent = 0;
    comm_relayed = 0;
}

void comm_receive(uint8_t sender_id, uint8_t state, uint8_t hops){
    uint32_t expiring_time = 0;
    if(expiring_ticks_quorum > 0) expiring_time = (uint32_t)exponential_distribution(expiring_ticks_quorum);
    if(comm_anonymous){
        quorum_push_anonymous(sender_id, state, expiring_time);
    }
    else{
        uint8_t result = quorum_update_by_id(sender_id, state, expiring_time, hops, comm_hop_count);
        if(comm_rebroadcast == 2 && result != 0) comm_fifo_push(sender_id, state, hops);
    }
    quorum_sort();
}

void comm_tick(uint64_t delta_ticks){
    quorum_decrement(delta_ticks);
    if(!comm_anonymous){
        quorum_erase_expired();
        if(comm_rebroadcast == 2) comm_fifo_sync();
    }
}

static uint8_t comm_own(uint8_t my_id, uint8_t my_state, uint8_t data[3]){
    data[0] = my_id;
    data[1] = 0;            /* a robot's own state always travels with 0 hops */
    data[2] = my_state;
    comm_own_sent++;
    return 1;
}

static uint8_t comm_relay(uint8_t idx, uint8_t data[3]){
    quorum_a *item = &quorum_buf[idx];
    uint8_t hops = comm_sat_inc(item->msg_n_hops);
    item->delivered = comm_sat_inc(item->delivered);
    item->msg_n_hops = hops;
    data[0] = item->agent_id;
    data[1] = hops;
    data[2] = item->agent_state;
    comm_relayed++;
    return 2;
}

uint8_t comm_talk(uint8_t my_id, uint8_t my_state, uint8_t data[3]){
    if(comm_anonymous || comm_rebroadcast == 0) return comm_own(my_id, my_state, data);
    if(rand_hard() >= 128) return comm_own(my_id, my_state, data);     /* relay with probability 0.5 */
    if(comm_rebroadcast == 1){
        if(num_quorum_items == 0) return comm_own(my_id, my_state, data);
        uint8_t idx = rand_soft() % num_quorum_items;
        if(comm_msgs_n_hops > 0 && quorum_buf[idx].delivered >= comm_msgs_n_hops) return comm_own(my_id, my_state, data);
        return comm_relay(idx, data);
    }
    /* policy 2: next queued sender still in the buffer, with its current state */
    while(comm_fifo.count > 0){
        uint8_t agent_id = comm_fifo.buffer[comm_fifo.head].agent_id;
        comm_fifo.head = comm_fifo_index(1);
        comm_fifo.count--;
        uint16_t idx = quorum_find_by_id(agent_id);
        if(idx != QUORUM_NOT_FOUND) return comm_relay((uint8_t)idx, data);
    }
    return comm_own(my_id, my_state, data);
}

uint8_t comm_first_sample(){
    if(!comm_anonymous) return 0;
    return (num_quorum_items > comm_k_sampling) ? comm_k_sampling : num_quorum_items;
}

uint8_t comm_quorum(uint8_t my_state){
    return quorum_check(my_state, comm_anonymous ? comm_k_sampling : 0);
}

uint8_t comm_distinct_ids(){
    return quorum_distinct_ids();
}
