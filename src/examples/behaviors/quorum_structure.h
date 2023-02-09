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

void set_expiring_ticks_quorum_item(const int Expiring_time);

void sort_q(quorum_a **Array[]);

void init_array_qrm(quorum_a **Array[]);

void print_q(quorum_a **Array[]);

void increment_quorum_counter(quorum_a **Array[]);

void erase_expired_items(quorum_a **Array[],quorum_a **Myquorum);

void destroy_quorum_memory(quorum_a **Array[],quorum_a **Myquorum);

int update_q(quorum_a **Array[],quorum_a **Myquorum,quorum_a **Prev,const int Agent_id,const int Agent_node);
