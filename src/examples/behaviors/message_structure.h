#ifndef MESSAGE_STRCUCT_H
#define MESSAGE_STRCUCT_H
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

int expiring_ticks_messages = 10000;
unsigned int num_messages = 0;

typedef struct message_structure{
    unsigned int counter;
    int agent_id, agent_node, agent_leaf;
    float leaf_utility;
    struct message_structure *next,*prev;
}message_a;

void set_expiring_ticks_message(const int Expiring_time){
    expiring_ticks_messages = Expiring_time;
}

void sort_m(message_a **Array[]){
    for (int i = 0; i < num_messages-1; i++){
        for (int j = i+1; j < num_messages; j++){
            if((*Array)[i]->counter > (*Array)[j]->counter){
                message_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

void init_array_msg(message_a **Array[]){
    *Array = (message_a**)malloc(64*sizeof(message_a*));
    for(int i=0;i<64;i++) (*Array)[i] = NULL;
}

void print_m(message_a **Array[]){
    for (int i = 0; i < num_messages; i++){
        if((*Array)[i]!=NULL) printf("M__%d++%d\n",(*Array)[i]->agent_id,(*Array)[i]->counter);
        else printf("NULL\n");
    }
}

void increment_messages_counter(message_a **Array[]){
    for (int i = 0; i < num_messages; i++) (*Array)[i]->counter = (*Array)[i]->counter+1;
}

void erase_expired_messages(message_a **Array[],message_a **Mymessage){
    for(int i=num_messages-1;i>=0;i--){
        if((*Array)[i]->counter>=expiring_ticks_messages){
            if((*Array)[i]->next == NULL && (*Array)[i]->prev == NULL){
                free((*Array)[i]);
                (*Array)[i] = NULL;
                *Mymessage = NULL;
            }
            else if((*Array)[i]->next != NULL && (*Array)[i]->prev == NULL){
                *Mymessage = (*Array)[i]->next;
                (*Mymessage)->prev = NULL;
                free((*Array)[i]);
                (*Array)[i] = NULL;
            }
            else if((*Array)[i]->next == NULL && (*Array)[i]->prev != NULL){
                (*Array)[i]->prev->next = NULL;
                free((*Array)[i]);
                (*Array)[i] = NULL;
            }
            else{
                (*Array)[i]->next->prev = (*Array)[i]->prev;
                (*Array)[i]->prev->next = (*Array)[i]->next;
                free((*Array)[i]);
                (*Array)[i] = NULL;
            }
            num_messages--;
        }
        else break;
    }
}

void erase_messages(message_a **Array[],message_a **Mymessage){
    for(int i=0;i<num_messages;i++){
        free((*Array)[i]);
        (*Array)[i] = NULL;
    }
    num_messages = 0;
    *Mymessage=NULL;
}

void destroy_messages_memory(message_a **Array[],message_a **Mymessage){
    for(int i=0;i<num_messages;i++) if((*Array)[i]!=NULL) free((*Array)[i]);
    free(*Array);
    num_messages = 0;
    *Mymessage=NULL;
}

int update_m(message_a **Array[], message_a **Mymessage,message_a **Prev,const int Agent_id,const int Agent_node, const int Agent_leaf, const float Leaf_utility){
    int out;
    out=1;
    if(*Mymessage!=NULL){
        if((*Mymessage)->agent_id==Agent_id){
            out=0;
            (*Mymessage)->agent_node = Agent_node;
            (*Mymessage)->agent_leaf = Agent_leaf;
            (*Mymessage)->leaf_utility = Leaf_utility;
            (*Mymessage)->counter = 0;
        }
        if(out==1) out=update_m(Array,&((*Mymessage)->next),Mymessage,Agent_id,Agent_node,Agent_leaf,Leaf_utility);
    }
    else{
        (*Mymessage)=(message_a*)malloc(sizeof(message_a));
        (*Mymessage)->agent_id=Agent_id;
        (*Mymessage)->agent_node=Agent_node;
        (*Mymessage)->agent_leaf=Agent_leaf;
        (*Mymessage)->counter=0;
        (*Mymessage)->leaf_utility=Leaf_utility;
        num_messages++;
        if (Prev!=NULL && *Prev!=NULL){
            (*Mymessage)->prev=*Prev;
            (*Prev)->next=*Mymessage;
        }
        else (*Mymessage)->prev=NULL;
        (*Mymessage)->next=NULL;
        (*Array)[num_messages-1] = *Mymessage;
    }
    return out;
}

int get_counter_from_id(message_a **Array[],const int Agent_id){
    for(int i=0;i<num_messages;i++) if((*Array)[i]->agent_id==Agent_id) return (*Array)[i]->counter;
    return -1;
}

message_a *select_a_random_msg(message_a **Array[]){
    if(num_messages>1) return (*Array)[rand()%(num_messages-1)];
    else if(num_messages==1) return (*Array)[0];
    else return NULL;
}

#endif