#include "quorum_structure.h"

quorum_a quorum_buf[QUORUM_CAPACITY];
uint8_t num_quorum_items = 0;
uint8_t buffer_lenght = QUORUM_CAPACITY;
uint8_t quorum_anonymous = 0;
uint32_t expiring_ticks_quorum = 10000;
uint8_t min_quorum_length = 5;
float quorum_threshold = 0.8;
uint8_t quorum_reached = 0;

void quorum_init(uint8_t capacity, uint32_t expiring_ticks, uint8_t anonymous){
    if(capacity == 0) capacity = 1;   /* capacity is a uint8_t: at most QUORUM_CAPACITY */
    buffer_lenght = capacity;
    expiring_ticks_quorum = expiring_ticks;
    quorum_anonymous = anonymous ? 1 : 0;
    quorum_clear();
}

void quorum_clear(){
    num_quorum_items = 0;
    quorum_reached = 0;
}

void set_quorum_threshold(const uint8_t Quorum_threshold_percent){
    quorum_threshold = Quorum_threshold_percent*.01;
}

static void quorum_append(const uint8_t Agent_id, const uint8_t received_state, const uint32_t expiring_time, const uint8_t Msg_n_hops){
    quorum_a *item = &quorum_buf[num_quorum_items];
    item->agent_id = Agent_id;
    item->counter = expiring_time;
    item->agent_state = received_state;
    item->delivered = 0;
    item->msg_n_hops = Msg_n_hops;
    num_quorum_items++;
}

void quorum_remove_at(uint8_t idx){
    if(idx >= num_quorum_items) return;
    for(uint8_t i = idx; i + 1 < num_quorum_items; i++) quorum_buf[i] = quorum_buf[i+1];
    num_quorum_items--;
}

uint8_t quorum_update_by_id(const uint8_t Agent_id, const uint8_t received_state, const uint32_t expiring_time, const uint8_t Msg_n_hops){
    for(uint8_t i = 0; i < num_quorum_items; i++){
        quorum_a *item = &quorum_buf[i];
        if(item->agent_id != Agent_id) continue;
        if(received_state != item->agent_state && Msg_n_hops <= item->msg_n_hops){
            item->counter = expiring_time;
            item->agent_state = received_state;
            item->delivered = 0;
            item->msg_n_hops = Msg_n_hops;
            return 2;
        }
        return 0;
    }
    if(num_quorum_items >= buffer_lenght) return 0;
    quorum_append(Agent_id,received_state,expiring_time,Msg_n_hops);
    return 1;
}

uint8_t quorum_push_anonymous(const uint8_t Agent_id, const uint8_t received_state, const uint32_t expiring_time){
    if(num_quorum_items >= buffer_lenght) quorum_remove_at(0);
    quorum_append(Agent_id,received_state,expiring_time,0);
    return 1;
}

static void quorum_swap(uint8_t i, uint8_t j){
    quorum_a tmp = quorum_buf[i];
    quorum_buf[i] = quorum_buf[j];
    quorum_buf[j] = tmp;
}

void quorum_sort(){
    if(num_quorum_items < 2) return;
    if(!quorum_anonymous){
        /* descending counter: expired entries end up at the tail */
        for(uint8_t i = 0; i < num_quorum_items-1; i++)
            for(uint8_t j = i+1; j < num_quorum_items; j++)
                if(quorum_buf[i].counter < quorum_buf[j].counter) quorum_swap(i,j);
    }
    else if(expiring_ticks_quorum > 0){
        /* ascending counter: index 0 is the next to be evicted */
        for(uint8_t i = 0; i < num_quorum_items-1; i++)
            for(uint8_t j = i+1; j < num_quorum_items; j++)
                if(quorum_buf[i].counter > quorum_buf[j].counter) quorum_swap(i,j);
    }
    /* anonymous FIFO: insertion order is kept */
}

void quorum_decrement(uint64_t ticks){
    for(uint8_t i = 0; i < num_quorum_items; i++){
        if(quorum_buf[i].counter > ticks) quorum_buf[i].counter -= ticks;
        else quorum_buf[i].counter = 0;
    }
}

void quorum_erase_expired(){
    uint8_t write = 0;
    for(uint8_t read = 0; read < num_quorum_items; read++){
        if(quorum_buf[read].counter == 0) continue;
        if(write != read) quorum_buf[write] = quorum_buf[read];
        write++;
    }
    num_quorum_items = write;
}

uint16_t quorum_find_by_id(const uint8_t agent_id){
    for(uint8_t i = 0; i < num_quorum_items; i++)
        if(quorum_buf[i].agent_id == agent_id) return i;
    return QUORUM_NOT_FOUND;
}

uint16_t quorum_select_undelivered(){
    if(num_quorum_items == 0) return QUORUM_NOT_FOUND;
    if(quorum_anonymous && expiring_ticks_quorum == 0){
        for(uint8_t i = 0; i < num_quorum_items; i++)
            if(quorum_buf[i].delivered == 0) return i;
    }
    else{
        for(int16_t i = num_quorum_items-1; i >= 0; i--)
            if(quorum_buf[i].delivered == 0) return (uint16_t)i;
    }
    return QUORUM_NOT_FOUND;
}

uint8_t quorum_distinct_ids(){
    uint8_t seen[32] = {0};
    uint8_t count = 0;
    for(uint8_t i = 0; i < num_quorum_items; i++){
        uint8_t id = quorum_buf[i].agent_id;
        if(!(seen[id >> 3] & (1 << (id & 7)))){
            seen[id >> 3] |= (uint8_t)(1 << (id & 7));
            count++;
        }
    }
    return count;
}

uint8_t quorum_check(const uint8_t my_state, const uint8_t k_sampling){
    uint16_t committed = my_state;
    uint16_t valid_items = 0;
    uint8_t start_idx = (num_quorum_items > k_sampling) ? k_sampling : num_quorum_items;
    for(uint8_t i = start_idx; i < num_quorum_items; i++){
        committed += quorum_buf[i].agent_state;
        valid_items++;
    }
    quorum_reached = (valid_items >= min_quorum_length && committed >= (valid_items + 1)*quorum_threshold) ? 1 : 0;
    return quorum_reached;
}
