#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

uint32_t expiring_ticks_quorum = 600;
uint8_t min_quorum_length = 5;
float quorum_threshold;
uint8_t true_quorum_items;
uint8_t num_quorum_items;
uint8_t quorum_reached = 0;
uint8_t buffer_lenght;

typedef struct quorum_structure{
    uint32_t counter;
    uint8_t agent_id;
    uint8_t delivered;
    uint8_t agent_state;
    struct quorum_structure *next,*prev;
}quorum_a;

void set_quorum_vars(const uint32_t Expiring_time);

void set_quorum_threshold(const uint8_t Quorum_threshold);

void sort_q(quorum_a **Array[]);

void init_array_qrm(quorum_a **Array[], uint8_t N);

void print_q(quorum_a **Array[], uint8_t id);

void increment_quorum_counter(quorum_a **Array[]);

void decrement_quorum_counter(quorum_a **Array[]);

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum);

void destroy_quorum_memory(quorum_a **Array[],quorum_a **Myquorum);

uint16_t select_a_random_message();

uint16_t select_message_by_fifo(quorum_a **Array[]);

uint8_t update_circular_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state, const uint32_t expiring_time);

uint8_t update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state, const uint32_t expiring_time);
