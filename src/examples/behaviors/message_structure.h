#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

uint16_t expiring_ticks_messages = 10000;
uint8_t num_messages = 0;

typedef struct message_structure{
    uint16_t counter;
    uint8_t agent_id, agent_node, agent_leaf;
    float leaf_utility;
    struct message_structure *next,*prev;
}message_a;

void set_expiring_ticks_message(const uint16_t Expiring_time);

void sort_m(message_a **Array[]);

void init_array_msg(message_a **Array[]);

void print_m(message_a **Array[]);

void increment_messages_counter(message_a **Array[]);

void erase_expired_messages(message_a **Array[],message_a **Mymessage);

void erase_messages(message_a **Array[],message_a **Mymessage);

void destroy_messages_memory(message_a **Array[],message_a **Mymessage);

uint8_t update_m(message_a **Array[], message_a **Mymessage,message_a **Prev,const uint8_t Agent_id,const uint8_t Agent_node, const uint8_t Agent_leaf, const float Leaf_utility);

uint16_t get_counter_from_id(message_a **Array[],const uint8_t Agent_id);

message_a *select_a_random_msg(message_a **Array[]);
