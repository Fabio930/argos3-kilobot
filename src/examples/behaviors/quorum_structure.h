/* Quorum buffer shared by the ID-aware and the anonymous communication models.
 *
 * The buffer is a plain array of entries (no linked list), so insertion,
 * eviction and expiry can never leave dangling pointers behind.
 *
 *  - ID-aware  (quorum_analysis):   one entry per sender ID, entries expire
 *    when their counter reaches 0, array kept sorted by descending counter.
 *  - anonymous (Parker_replica):    every received message is appended, the
 *    buffer holds at most buffer_lenght entries; when it is full the entry at
 *    index 0 is evicted. With expiring_ticks_quorum > 0 the array is kept
 *    sorted by ascending counter (index 0 = closest to expiry), with
 *    expiring_ticks_quorum == 0 it is a pure FIFO (index 0 = oldest).
 */
#ifndef QUORUM_STRUCTURE_H
#define QUORUM_STRUCTURE_H

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

#define QUORUM_CAPACITY 255
#define QUORUM_NOT_FOUND 0xFFFF

typedef struct quorum_structure{
    uint32_t counter;
    uint8_t agent_id;
    uint8_t delivered;
    uint8_t agent_state;
    uint8_t msg_n_hops;
}quorum_a;

extern quorum_a quorum_buf[QUORUM_CAPACITY];
extern uint8_t num_quorum_items;
extern uint8_t buffer_lenght;
extern uint8_t quorum_anonymous;
extern uint32_t expiring_ticks_quorum;
extern uint8_t min_quorum_length;
extern float quorum_threshold;
extern uint8_t quorum_reached;

/* Configure the buffer: capacity is clamped to [1, QUORUM_CAPACITY]. */
void quorum_init(uint8_t capacity, uint32_t expiring_ticks, uint8_t anonymous);

void quorum_clear();

void set_quorum_threshold(const uint8_t Quorum_threshold_percent);

/* ID-aware insertion.
 * returns 0: sender already known, nothing changed
 *         1: new sender appended
 *         2: known sender changed state (counter, state, hops and delivered refreshed)
 * A state change is accepted only if the new information travelled at most
 * as many hops as the stored one. */
uint8_t quorum_update_by_id(const uint8_t Agent_id, const uint8_t received_state, const uint32_t expiring_time, const uint8_t Msg_n_hops);

/* Anonymous insertion: always appends, evicting index 0 when full. Returns 1. */
uint8_t quorum_push_anonymous(const uint8_t Agent_id, const uint8_t received_state, const uint32_t expiring_time);

void quorum_remove_at(uint8_t idx);

void quorum_sort();

void quorum_decrement(uint64_t ticks);

/* Removes every entry whose counter reached 0 (ID-aware model only). */
void quorum_erase_expired();

uint16_t quorum_find_by_id(const uint8_t agent_id);

/* First entry never rebroadcast: oldest first in FIFO mode, otherwise the
 * last array position first (anonymous rebroadcast policy 2). */
uint16_t quorum_select_undelivered();

uint8_t quorum_distinct_ids();

/* Quorum test: ignores the first k_sampling entries of the array. */
uint8_t quorum_check(const uint8_t my_state, const uint8_t k_sampling);

#endif
