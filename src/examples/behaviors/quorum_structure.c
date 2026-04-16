#include "quorum_structure.h"

void set_quorum_vars(const uint32_t Expiring_time,const uint8_t Min_quorum_length){
    expiring_ticks_quorum = Expiring_time;
    min_quorum_length = Min_quorum_length;
}

void sort_q(quorum_a **Array[]){
    true_quorum_items = 0;
    if(expiring_ticks_quorum > 0){
        for (uint8_t i = 0; i < buffer_length-1; i++){
            for (uint8_t j = i+1; j < buffer_length; j++){
                if(((*Array)[i] == NULL && (*Array)[j] != NULL)){
                    quorum_a *flag = (*Array)[i];
                    (*Array)[i] = (*Array)[j];
                    (*Array)[j] = flag;
                }
                else if(((*Array)[i] != NULL && (*Array)[j] != NULL) && (*Array)[i]->counter > (*Array)[j]->counter){
                    quorum_a *flag = (*Array)[i];
                    (*Array)[i] = (*Array)[j];
                    (*Array)[j] = flag;
                }
            }
        }
    }
    else{
        uint8_t write = 0;
        for (uint8_t read = 0; read < buffer_length; read++){
            if((*Array)[read] != NULL){
                if(write != read) (*Array)[write] = (*Array)[read];
                write++;
            }
        }
        for (uint8_t i = write; i < buffer_length; i++) (*Array)[i] = NULL;
    }

    uint8_t seen[256] = {0};
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if((*Array)[i] == NULL){
            continue;
        }
        uint8_t agent_id = (*Array)[i]->agent_id;
        if(seen[agent_id] == 0){
            seen[agent_id] = 1;
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

void print_q(quorum_a **Array[],uint8_t id){
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if((*Array)[i]!=NULL) printf("id:%d,%d\tQ__%d++%d++%d\n",id,num_quorum_items,(*Array)[i]->agent_id,(*Array)[i]->counter,(*Array)[i]->delivered);
        else printf("NULL\n");
    }
}

void increment_quorum_counter(quorum_a **Array[]){
    for (uint8_t i = 0; i < num_quorum_items; i++) (*Array)[i]->counter = (*Array)[i]->counter+1;
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

void destroy_quorum_memory(quorum_a **Array[],quorum_a **Myquorum){
    for(uint8_t i=0;i<buffer_length;i++) if((*Array)[i]!=NULL) free((*Array)[i]);
    free(*Array);
    num_quorum_items = 0;
    if(*Myquorum != NULL){
        while(1){
            if((*Myquorum)->next != NULL){
                *Myquorum = (*Myquorum)->next;
                free((*Myquorum)->prev);
                (*Myquorum)->prev = NULL;
            }
            else{
                free(*Myquorum);
                break;
            }
        }
        *Myquorum=NULL;
    }
}

uint8_t update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state, const uint32_t expiring_time, const uint8_t Msg_n_hops, const uint8_t Gossip){
    (void)Prev;
    if(id_aware){
        quorum_a *cursor = *Myquorum;
        while(cursor != NULL){
            if(cursor->agent_id == Agent_id){
                if(received_state != cursor->agent_state &&(!Gossip || Msg_n_hops <= cursor->msg_n_hops)){
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

uint16_t select_message_by_fifo(quorum_a **Array[],const uint8_t check_4_hops){
    if(num_quorum_items == 0) return 0b1111111111111111;
    uint8_t start = priority_sampling_k;
    if(start >= num_quorum_items) return 0b1111111111111111;

    if(expiring_ticks_quorum == 0){
        for(uint8_t i = start; i < num_quorum_items; i++){
            if((*Array)[i] == NULL) continue;
            if(check_4_hops == 0){
                if((*Array)[i]->delivered == 0) return i;
            }
            else{
                if((*Array)[i]->delivered == 0 && (*Array)[i]->msg_n_hops > 0) return i;
            }
        }
    }
    else{
        for(uint8_t i = num_quorum_items; i > start; i--){
            uint8_t idx = (uint8_t)(i - 1);
            if((*Array)[idx] == NULL) continue;
            if(check_4_hops == 0){
                if((*Array)[idx]->delivered == 0) return idx;
            }
            else{
                if((*Array)[idx]->delivered == 0 && (*Array)[idx]->msg_n_hops > 0) return idx;
            }
        }
    }
    return 0b1111111111111111;
}
