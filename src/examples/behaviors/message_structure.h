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

void set_expiring_ticks_message(const int Expiring_time);

void sort_m(message_a **Array[]);

void init_array_msg(message_a **Array[]);

void print_m(message_a **Array[]);

void increment_messages_counter(message_a **Array[]);

void erase_expired_messages(message_a **Array[],message_a **Mymessage);

void erase_messages(message_a **Array[],message_a **Mymessage);

void destroy_messages_memory(message_a **Array[],message_a **Mymessage);

int update_m(message_a **Array[], message_a **Mymessage,message_a **Prev,const int Agent_id,const int Agent_node, const int Agent_leaf, const float Leaf_utility);

int get_counter_from_id(message_a **Array[],const int Agent_id);

message_a *select_a_random_msg(message_a **Array[]);
