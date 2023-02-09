#ifndef QUORUM_STRCUCT_H
#define QUORUM_STRCUCT_H
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

int expiring_ticks_quorum = 10000;
unsigned int min_quorum_length = 3;
float quorum_scaling_factor = 1;
unsigned int num_quorum_items = 0;

typedef struct quorum_structure{
    unsigned int agent_id, agent_node, counter;
    struct quorum_structure *next,*prev;
}quorum_a;

void set_expiring_ticks_quorum_item(const int Expiring_time){
    expiring_ticks_quorum = Expiring_time;
}

void sort_q(quorum_a **Array[]){
    for (int i = 0; i < num_quorum_items-1; i++){
        for (int j = i+1; j < num_quorum_items; j++){
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
    for(int i=0;i<64;i++) (*Array)[i] = NULL;
}

void print_q(quorum_a **Array[]){
    for (int i = 0; i < num_quorum_items; i++){
        if((*Array)[i]!=NULL) printf("Q__%d++%d\n",(*Array)[i]->agent_id,(*Array)[i]->counter);
        else printf("NULL\n");
    }
}

void increment_quorum_counter(quorum_a **Array[]){
    for (int i = 0; i < num_quorum_items; i++) (*Array)[i]->counter = (*Array)[i]->counter+1;
}

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum){
    for(int i=num_quorum_items-1;i>=0;i--){
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
    for(int i=0;i<num_quorum_items;i++) if((*Array)[i]!=NULL) free((*Array)[i]);
    free(*Array);
    num_quorum_items = 0;
    *Myquorum=NULL;
}

int update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const int Agent_id,const int Agent_node){
    int out;
    out=1;
    if(*Myquorum!=NULL){
        if((*Myquorum)->agent_id==Agent_id){
            out=0;
            (*Myquorum)->agent_node = Agent_node;
            (*Myquorum)->counter = 0;
        }
        if(out==1) out=update_q(Array,&((*Myquorum)->next),Myquorum,Agent_id,Agent_node);
    }
    else{
        (*Myquorum)=(quorum_a*)malloc(sizeof(quorum_a));
        (*Myquorum)->agent_id=Agent_id;
        (*Myquorum)->agent_node=Agent_node;
        (*Myquorum)->counter=0;
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

#endif