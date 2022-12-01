#ifndef MESSAGE_STRCUCT_H
#define MESSAGE_STRCUCT_H

int expiring_ticks_messages = 10000;
unsigned int num_messages = 0;

typedef struct message_structure{
    unsigned int counter;
    int agent_id, agent_node, agent_leaf;
    float leaf_utility;
    struct message_structure *next,*prev;
}message_a;

void fill_array_m(message_a **Array[],message_a** List){
    message_a *flag[num_messages];
    message_a *current_message = *List;
    for(int i=0;i<num_messages;i++){
        flag[i] = current_message;
        current_message = current_message->next;
    }
    *Array = flag;
    sort_m(Array);
}

void sort_m(message_a **Array[]){
    for (int i = 0; i < num_messages-1; i++){
        for (int j = i+1; j < num_messages; j++){
            if((*Array)[i]->counter>(*Array)[j]->counter){
                message_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

void set_expiring_ticks_message(const int Expiring_time){
    expiring_ticks_messages=Expiring_time;
}

void increment_messages_counter(message_a **Mymessage){
    if((*Mymessage)!=NULL){
        (*Mymessage)->counter=(*Mymessage)->counter+1;
        increment_messages_counter(&((*Mymessage)->next));
    }
}

void erase_expired_messages(message_a **Mymessage){
    if(*Mymessage!=NULL){
        message_a *Next=(*Mymessage)->next;
        if((*Mymessage)->counter >= expiring_ticks_messages){
            if((*Mymessage)->next == NULL && (*Mymessage)->prev == NULL){
                free(*Mymessage);
                (*Mymessage)=NULL;
                num_messages--;
            }
            else if((*Mymessage)->next != NULL && (*Mymessage)->prev == NULL){
                Next->prev = NULL;
                (*Mymessage)->next=NULL;
                free(*Mymessage);
                (*Mymessage)=Next;
                num_messages--;
            }
            else if((*Mymessage)->next == NULL && (*Mymessage)->prev != NULL){
                (*Mymessage)->prev->next=NULL;
                (*Mymessage)->prev = NULL;
                free(*Mymessage);
                (*Mymessage)=NULL;
                num_messages--;
            }
            else{
                (*Mymessage)->prev->next = Next;
                Next->prev = (*Mymessage)->prev;
                free(*Mymessage);
                (*Mymessage)=NULL;
                num_messages--;
            }
        }
        erase_expired_messages(&Next);
    }
}

void erase_messages(message_a **Mymessage){
    if((*Mymessage!=NULL)){
        if((*Mymessage)->next!=NULL){
            message_a *m=(*Mymessage)->next;
            erase_messages(&m);
            (*Mymessage)->next=NULL;
        }
        (*Mymessage)->prev=NULL;
        free(*Mymessage);
        (*Mymessage)=NULL;
    }
    num_messages = 0;
}

int update(message_a **Mymessage,message_a **Prev,const int Agent_id,const int Agent_node, const int Agent_leaf, const float Leaf_utility){
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
        if(out==1){
            message_a *flag=(*Mymessage)->next;
            out=update(&flag,Mymessage,Agent_id,Agent_node,Agent_leaf,Leaf_utility);
        }
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
    }
    return out;
}

int get_counter_from_id(message_a **Mymessage,const int Agent_id){
    int out;
    out=-1;
    if(*Mymessage!=NULL){
        if((*Mymessage)->agent_id==Agent_id){
            out=(*Mymessage)->counter;
        }
        else{
            message_a *flag=(*Mymessage)->next;
            out=get_counter_from_id(&flag,Agent_id);
        }
    }
    return out;
}

message_a *select_a_random_msg(message_a **Mymessage)
{
    message_a *out=NULL;
    if(*Mymessage!=NULL)
    {
        if(num_messages==1) return *Mymessage;
        int index = rand()%(num_messages-1);
        out = *Mymessage;
        for(int i=0;i<index;i++) out = out->next;
    }
    return out;
}

#endif