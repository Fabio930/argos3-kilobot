#include "quorum_structure.h"

void set_msg_life(const uint32_t Expiring_time){
    expiring_ticks_quorum = Expiring_time;
}

void set_quorum_threshold(const uint8_t Quorum_threshold){
    quorum_threshold = Quorum_threshold*.01;
}

void sort_q(quorum_a **Array[]){
    for (uint8_t i = 0; i < num_quorum_items-1; i++){
        for (uint8_t j = i+1; j < num_quorum_items; j++){
            if(((*Array)[i] == NULL && (*Array)[j] != NULL) || (*Array)[i]->counter < (*Array)[j]->counter){
                quorum_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

void init_array_qrm(quorum_a **Array[]){
    *Array = (quorum_a**)malloc(128*sizeof(quorum_a*));
    for(uint8_t i=0;i<128;i++) (*Array)[i] = NULL;
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

void decrement_quorum_counter(quorum_a **Array[]){
    for (uint8_t i = 0; i < num_quorum_items; i++) (*Array)[i]->counter = (*Array)[i]->counter-1;
}

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum){
    for(int8_t i=num_quorum_items-1;i>=0;i--){
        if((*Array)[i]->counter<=0){
            if((*Array)[i]->next == NULL && (*Array)[i]->prev == NULL){
                free((*Array)[i]);
                (*Array)[i] = NULL;
                *Myquorum=NULL;
            }
            else if((*Array)[i]->next != NULL && (*Array)[i]->prev == NULL){
                *Myquorum = (*Array)[i]->next;
                (*Myquorum)->prev=NULL;
                free((*Array)[i]);
                (*Array)[i]=NULL;
            }
            else if((*Array)[i]->next == NULL && (*Array)[i]->prev != NULL){
                (*Array)[i]->prev->next=NULL;
                free((*Array)[i]);
                (*Array)[i]=NULL;
            }
            else{
                (*Array)[i]->next->prev = (*Array)[i]->prev;
                (*Array)[i]->prev->next = (*Array)[i]->next;
                free((*Array)[i]);
                (*Array)[i]=NULL;
            }
            num_quorum_items--;
        }
        else break;
    }
}

void destroy_quorum_memory(quorum_a **Array[],quorum_a **Myquorum){
    for(uint8_t i=0;i<128;i++) if((*Array)[i]!=NULL) free((*Array)[i]);
    free(*Array);
    num_quorum_items = 0;
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

uint8_t update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state, const uint32_t expiring_time, const uint8_t Msg_n_hops){
    uint8_t out;
    out=1;
    if(*Myquorum!=NULL){
        if((*Myquorum)->agent_id==Agent_id){
            out=0;
            if((*Myquorum)->agent_state!=received_state){
                out=2;
                (*Myquorum)->counter=expiring_time;
                (*Myquorum)->agent_state=received_state;
                (*Myquorum)->delivered=0;
                (*Myquorum)->msg_n_hops=Msg_n_hops;
            }
        }
        if(out==1) out=update_q(Array,&((*Myquorum)->next),Myquorum,Agent_id,received_state,expiring_time,Msg_n_hops);
    }
    else{
        (*Myquorum)=(quorum_a*)malloc(sizeof(quorum_a));
        (*Myquorum)->agent_id=Agent_id;
        (*Myquorum)->counter=expiring_time;
        (*Myquorum)->agent_state=received_state;
        (*Myquorum)->delivered=0;
        (*Myquorum)->msg_n_hops=Msg_n_hops;
        num_quorum_items++;
        if (Prev!=NULL && *Prev!=NULL){
            (*Myquorum)->prev=*Prev;
            (*Prev)->next=*Myquorum;
        }
        else (*Myquorum)->prev=NULL;
        (*Myquorum)->next=NULL;
        (*Array)[num_quorum_items-1] = *Myquorum;
    }
    return out;
}

uint16_t select_a_random_message(){
    if(num_quorum_items>0)return rand_hard()%num_quorum_items;
    else return 0b1111111111111111;
}

uint16_t select_message_by_fifo(quorum_a **Array[],const uint8_t check_4_hops){
    if(num_quorum_items>0){
        for(uint8_t i=num_quorum_items-1;i>=0;i--){
            switch (check_4_hops){
                case 0:
                    if((*Array)[i]->delivered == 0) return i;
                    break;
                default:
                    if((*Array)[i]->delivered == 0 && (*Array)[i]->msg_n_hops > 0) return i;
                    break;
            }
            if(i==0) break;
        }
    }
    return 0b1111111111111111;
}