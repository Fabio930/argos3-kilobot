#include "quorum_structure.h"

void set_quorum_vars(const uint32_t Expiring_time,const uint8_t Min_quorum_length,const uint8_t Quorum_scaling_factor){
    expiring_ticks_quorum = Expiring_time;
    min_quorum_length = Min_quorum_length;
    quorum_scaling_factor = Quorum_scaling_factor;
}

void sort_q(quorum_a **Array[]){
    for (uint8_t i = 0; i < num_quorum_items-1; i++){
        for (uint8_t j = i+1; j < num_quorum_items; j++){
            if(((*Array)[i] == NULL && (*Array)[j] != NULL) || (*Array)[i]->counter > (*Array)[j]->counter){
                quorum_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

void init_array_qrm(quorum_a **Array[]){
    *Array = (quorum_a**)malloc(64*sizeof(quorum_a*));
    for(uint8_t i=0;i<64;i++) (*Array)[i] = NULL;
}

void print_q(quorum_a **Array[]){
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if((*Array)[i]!=NULL) printf("Q__%d++%d\n",(*Array)[i]->agent_id,(*Array)[i]->counter);
        else printf("NULL\n");
    }
}

void increment_quorum_counter(quorum_a **Array[]){
    for (uint8_t i = 0; i < num_quorum_items; i++) (*Array)[i]->counter = (*Array)[i]->counter+1;
}

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum){
    for(uint8_t i=num_quorum_items-1;i>=0;i--){
        if((*Array)[i]->counter>=expiring_ticks_quorum){
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
    for(uint8_t i=0;i<num_quorum_items;i++) if((*Array)[i]!=NULL) free((*Array)[i]);
    free(*Array);
    num_quorum_items = 0;
    *Myquorum=NULL;
}

uint8_t update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state){
    uint8_t out;
    out=1;
    if(*Myquorum!=NULL){
        if((*Myquorum)->agent_id==Agent_id){
            out=0;
            (*Myquorum)->counter = 0;
        }
        if(out==1) out=update_q(Array,&((*Myquorum)->next),Myquorum,Agent_id,received_state);
    }
    else{
        (*Myquorum)=(quorum_a*)malloc(sizeof(quorum_a));
        (*Myquorum)->agent_id=Agent_id;
        (*Myquorum)->counter=0;
        (*Myquorum)->delivered=0;
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

quorum_a* select_a_random_message(quorum_a **Array[]){
    return (*Array)[rand()%num_quorum_items];
}