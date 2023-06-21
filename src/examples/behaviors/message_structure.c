#include "message_structure.h"

void set_expiring_ticks_message(const uint16_t Expiring_time){
    expiring_ticks_messages = Expiring_time;
}

void sort_m(message_a **Array[]){
    for(uint8_t i = 0; i < num_messages-1; i++){
        for(uint8_t j = i+1; j < num_messages; j++){
            if((*Array)[i]->agent_id < (*Array)[j]->agent_id){
                message_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

void init_array_msg(message_a **Array[]){
    *Array = (message_a**)malloc(64*sizeof(message_a*));
    for(uint8_t i=0;i<64;i++) (*Array)[i] = NULL;
}

void print_m(message_a **Array[]){
    for(uint8_t i = 0; i < num_messages; i++){
        if((*Array)[i]!=NULL) printf("M__%d\n",(*Array)[i]->agent_id);
        else printf("NULL\n");
    }
}

void erase_messages(message_a **Array[],message_a **Mymessage){
    for(uint8_t i=0;i<num_messages;i++){
        free((*Array)[i]);
        (*Array)[i] = NULL;
    }
    num_messages = 0;
    *Mymessage=NULL;
}

void destroy_messages_memory(message_a **Array[],message_a **Mymessage){
    for(uint8_t i=0;i<num_messages;i++) if((*Array)[i]!=NULL) free((*Array)[i]);
    free(*Array);
    num_messages = 0;
    *Mymessage=NULL;
}

uint8_t update_m(message_a **Array[], message_a **Mymessage,message_a **Prev,const uint8_t Agent_id,const uint8_t Agent_node, const uint8_t Agent_leaf, const float Leaf_utility){
    uint8_t out;
    out=1;
    if(*Mymessage!=NULL){
        if((*Mymessage)->agent_id==Agent_id){
            out=0;
            (*Mymessage)->agent_node = Agent_node;
            (*Mymessage)->agent_leaf = Agent_leaf;
            (*Mymessage)->leaf_utility = Leaf_utility;
        }
        if(out==1) out=update_m(Array,&((*Mymessage)->next),Mymessage,Agent_id,Agent_node,Agent_leaf,Leaf_utility);
    }
    else{
        (*Mymessage)=(message_a*)malloc(sizeof(message_a));
        (*Mymessage)->agent_id=Agent_id;
        (*Mymessage)->agent_node=Agent_node;
        (*Mymessage)->agent_leaf=Agent_leaf;
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

message_a *select_a_random_msg(message_a **Array[]){
    if(num_messages>1) return (*Array)[rand_soft()%(num_messages-1)];
    else if(num_messages==1) return (*Array)[0];
    else return NULL;
}