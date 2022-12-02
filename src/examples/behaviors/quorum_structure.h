#ifndef QUORUM_STRCUCT_H
#define QUORUM_STRCUCT_H

int expiring_ticks_quorum=20000;
unsigned int min_quorum_length=10;
float quorum_scaling_factor=.9;
unsigned int num_quorum_items=0;
unsigned int free_space_q = 0;

typedef struct quorum_structure{
    unsigned int agent_id, agent_node, counter;
    struct quorum_structure *next,*prev;
}quorum_a;

void set_expiring_ticks_quorum_item(const int Expiring_time){
    expiring_ticks_quorum=Expiring_time;
}

void sort_q(quorum_a **Array[]){
    for (int i = 0; i < num_quorum_items-1; i++){
        for (int j = i+1; j < num_quorum_items; j++){
            if((*Array)[i]->counter > (*Array)[j]->counter){
                quorum_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

void fill_array_q(quorum_a **Array[],quorum_a** List){
    *Array=(quorum_a*)malloc(num_quorum_items*sizeof(quorum_a));
    quorum_a *current_item = *List;
    for(int i=0;i<num_quorum_items;i++){
        (*Array)[i] = current_item;
        current_item = current_item->next;
    }
    sort_q(Array);
}

void print_q(quorum_a **Array[]){
    for (int i = 0; i < num_quorum_items; i++) printf("Q__%d++%d\n",(*Array)[i]->agent_id,(*Array)[i]->counter);
}

void increment_quorum_counter(quorum_a **Array[]){
    for (int i = 0; i < num_quorum_items; i++) (*Array)[i]->counter = (*Array)[i]->counter+1;
}

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum){
    for(int i=num_quorum_items-1;i>=0;i--){
        if((*Array)[i]->counter>=expiring_ticks_quorum){
            if((*Array)[i]->next == NULL && (*Array)[i]->prev == NULL){
                free((*Array)[i]);
                free(*Array);
                *Myquorum=NULL;
            }
            else if((*Array)[i]->next != NULL && (*Array)[i]->prev == NULL){
                quorum_a *temp=(*Array)[i]->next;
                temp->prev=NULL;
                free((*Array)[i]);
                (*Array)[i]=NULL;
                *Myquorum=temp;
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

void erase_quorum_list(quorum_a **Array[],quorum_a **Myquorum){
    if(num_quorum_items>0){
        for(int i=0;i<num_quorum_items;i++) free((*Array)[i]);
        free(*Array);
        num_quorum_items = 0;
        *Myquorum=NULL;
    }
}

int update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const int Agent_id,const int Agent_node,const int Counter){
    int out;
    out=1;
    if(*Myquorum!=NULL){
        if((*Myquorum)->agent_id==Agent_id){
            out=0;
            (*Myquorum)->agent_node = Agent_node;
            (*Myquorum)->counter = Counter;
        }
        if(out==1) out=update_q(Array,&((*Myquorum)->next),Myquorum,Agent_id,Agent_node,Counter);
    }
    else{
        (*Myquorum)=(quorum_a*)malloc(sizeof(quorum_a));
        (*Myquorum)->agent_id=Agent_id;
        (*Myquorum)->agent_node=Agent_node;
        (*Myquorum)->counter=Counter;
        if(num_quorum_items > 0) free_space_q=1;
        num_quorum_items++;
        if (Prev!=NULL && *Prev!=NULL){
            (*Myquorum)->prev=*Prev;
            (*Prev)->next=*Myquorum;
        }
        else (*Myquorum)->prev=NULL;
        (*Myquorum)->next=NULL;
    }
    if(Prev==NULL){
        if(free_space_q==1){
            free(*Array);
            free_space_q = 0;
        }
        fill_array_q(Array,Myquorum);
    }
    return out;
}

#endif