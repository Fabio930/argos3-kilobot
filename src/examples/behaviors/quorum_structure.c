#include "quorum_structure.h"

void set_quorum_vars(const uint32_t Expiring_time,const uint8_t Min_quorum_length){
    expiring_ticks_quorum = Expiring_time;
    min_quorum_length = Min_quorum_length;
}

/* Move occupied slots to the front, keeping their order. */
static void compact_q(quorum_a **a, uint8_t len){
    uint8_t write = 0;
    for(uint8_t read = 0; read < len; read++){
        if(a[read] != NULL){
            if(write != read){
                a[write] = a[read];
                a[read] = NULL;
            }
            write++;
        }
    }
}

/*
 * Orders the buffer by counter (expiring soonest first), NULL slots last.
 * The result is identical to the original O(buffer_length^2) exchange sort:
 *  - slots after the last occupied one never move, so only that prefix is scanned;
 *  - when the occupied counters are already non-decreasing, the exchange sort only
 *    shifts items over NULL holes, which is exactly a stable compaction.
 */
void sort_q(quorum_a **Array[]){
    quorum_a **a = *Array;
    uint8_t len = buffer_length;
    while(len > 0 && a[len - 1] == NULL) len--;

    uint8_t ordered = 1;
    if(expiring_ticks_quorum > 0){
        uint32_t last = 0;
        for(uint8_t i = 0; i < len; i++){
            if(a[i] == NULL) continue;
            if(a[i]->counter < last){
                ordered = 0;
                break;
            }
            last = a[i]->counter;
        }
    }

    if(ordered){
        compact_q(a, len);
    }
    else{
        for(uint8_t i = 0; i + 1 < len; i++){
            for(uint8_t j = i + 1; j < len; j++){
                if(a[j] != NULL && (a[i] == NULL || a[i]->counter > a[j]->counter)){
                    quorum_a *tmp = a[i];
                    a[i] = a[j];
                    a[j] = tmp;
                }
            }
        }
    }

    uint8_t seen[256] = {0};
    true_quorum_items = 0;
    for(uint8_t i = 0; i < num_quorum_items; i++){
        if(a[i] == NULL) continue;
        if(seen[a[i]->agent_id] == 0){
            seen[a[i]->agent_id] = 1;
            true_quorum_items++;
        }
    }
}

static void remove_quorum_item_at_index(quorum_a **Array[], quorum_a **Myquorum, uint8_t idx){
    quorum_a *item = (*Array)[idx];
    if(item == NULL){
        return;
    }
    if(item->next == NULL && item->prev == NULL){
        free(item);
        (*Array)[idx] = NULL;
        *Myquorum = NULL;
    }
    else if(item->next != NULL && item->prev == NULL){
        *Myquorum = item->next;
        (*Myquorum)->prev = NULL;
        free(item);
        (*Array)[idx] = NULL;
    }
    else if(item->next == NULL && item->prev != NULL){
        item->prev->next = NULL;
        free(item);
        (*Array)[idx] = NULL;
    }
    else{
        item->next->prev = item->prev;
        item->prev->next = item->next;
        free(item);
        (*Array)[idx] = NULL;
    }
    if(num_quorum_items > 0){
        num_quorum_items--;
    }
}

void init_array_qrm(quorum_a **Array[], uint8_t N){
    buffer_length = (N == 0) ? 1 : N;
    *Array = (quorum_a**)malloc(buffer_length*sizeof(quorum_a*));
    for(uint8_t i=0;i<buffer_length;i++) (*Array)[i] = NULL;
    true_quorum_items = 0;
}

void decrement_quorum_counter(quorum_a **Array[], uint64_t ticks){
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if((*Array)[i]->counter>ticks) (*Array)[i]->counter = (*Array)[i]->counter-ticks;
        else (*Array)[i]->counter = 0;
    }
}

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum){
    if(expiring_ticks_quorum == 0){
        return;
    }
    while(num_quorum_items > 0){
        if((*Array)[0] == NULL){
            sort_q(Array);
            if((*Array)[0] == NULL){
                break;
            }
        }
        if((*Array)[0]->counter > 0){
            break;
        }
        remove_quorum_item_at_index(Array, Myquorum, 0);
        sort_q(Array);
    }
}

void destroy_quorum_memory(quorum_a **Array[], quorum_a **Myquorum){
    for(uint8_t i=0; i<buffer_length; i++){
        if((*Array)[i]!=NULL){
            free((*Array)[i]);
            (*Array)[i] = NULL;
        }
    }
    free(*Array);
    *Array = NULL;
    num_quorum_items = 0;
    
    *Myquorum = NULL;
}

uint8_t update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state, const uint32_t expiring_time, const uint8_t Msg_n_hops, const uint8_t hop_count){
    (void)Prev;
    if(id_aware){
        quorum_a *cursor = *Myquorum;
        while(cursor != NULL){
            if(cursor->agent_id == Agent_id){
                if((!hop_count && received_state != cursor->agent_state) ||
                (hop_count && Msg_n_hops <= cursor->msg_n_hops)){
                    cursor->counter = expiring_time;
                    cursor->agent_state = received_state;
                    cursor->delivered = 0;
                    cursor->msg_n_hops = Msg_n_hops;
                    return 2;
                }
                return 0;
            }
            cursor = cursor->next;
        }
    }

    if(num_quorum_items >= buffer_length){
        sort_q(Array);
        remove_quorum_item_at_index(Array, Myquorum, 0);
        sort_q(Array);
    }

    quorum_a *node = (quorum_a*)malloc(sizeof(quorum_a));
    node->agent_id = Agent_id;
    node->counter = expiring_time;
    node->agent_state = received_state;
    node->delivered = 0;
    node->msg_n_hops = Msg_n_hops;

    if(*Myquorum == NULL){
        node->prev = NULL;
        node->next = NULL;
        *Myquorum = node;
    }
    else{
        quorum_a *tail = *Myquorum;
        while(tail->next != NULL) tail = tail->next;
        node->prev = tail;
        node->next = NULL;
        tail->next = node;
    }

    if(num_quorum_items < buffer_length){
        (*Array)[num_quorum_items] = node;
    }
    num_quorum_items++;
    return 1;
}

uint16_t select_a_random_message(){
    if(num_quorum_items == 0) return 0b1111111111111111;
    uint8_t start = priority_sampling_k;
    if(start >= num_quorum_items) return 0b1111111111111111;
    uint8_t eligible = (uint8_t)(num_quorum_items - start);
    return (uint16_t)(start + (rand_hard() % eligible));
}
