#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

uint32_t expiring_ticks_quorum = 10000;
uint8_t min_quorum_length;
float quorum_scaling_factor;
uint8_t num_quorum_items = 0;

typedef struct quorum_structure{
    uint16_t counter;
    uint8_t agent_id;
    uint8_t delivered;
    uint8_t agent_state;
    struct quorum_structure *next,*prev;
}quorum_a;

void set_quorum_vars(const uint32_t Expiring_time,const uint8_t Min_quorum_length,const uint8_t Quorum_scaling_factor);

void sort_q(quorum_a **Array[]);

void init_array_qrm(quorum_a **Array[]);

void print_q(quorum_a **Array[]);

void increment_quorum_counter(quorum_a **Array[]);

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum);

void destroy_quorum_memory(quorum_a **Array[],quorum_a **Myquorum);

quorum_a* select_a_random_message(quorum_a **Array[]);

uint8_t update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const uint8_t Agent_id,const uint8_t received_state);
