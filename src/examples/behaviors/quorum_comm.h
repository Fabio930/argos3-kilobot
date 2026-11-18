/* Robot-to-robot communication protocol shared by every BestN experiment.
 * This file (and quorum_comm.c, quorum_structure.c/.h) is identical in
 * quorum_analysis and QS_social_interaction_modulation: change it in both branches.
 *
 * Message between robots (3 bytes): [0] originator ID, [1] hops travelled, [2] state.
 *
 * ID-aware model   (communication = id)
 *   - buffer: one entry per sender (quorum_update_by_id), entries expire after an
 *     exponential time of mean expiring_s seconds, never if expiring_s == 0
 *   - hop_count = 0: a known sender is updated when its state changed
 *     hop_count = 1: a known sender is updated when the new message travelled at most
 *     as many hops as the stored one, even with the same state (the timer restarts)
 *   - rebroadcast 0: own state only
 *                 1: with probability 0.5 relay a random buffer entry (at most
 *                    msgs_n_hops times each, unlimited if msgs_n_hops == 0)
 *                 2: with probability 0.5 relay the next sender of a FIFO queue; the
 *                    state and hops sent are the current ones in the buffer and the
 *                    queue drops senders that left the buffer
 * Anonymous model  (communication = anonymous, Parker replica)
 *   - buffer of queue_lenght entries, every message is appended, when full the entry
 *     closest to expiry (or the oldest if expiring_s == 0) is replaced; expired
 *     entries are not deleted
 *   - robots never rebroadcast: they always send their own state
 *   - the quorum ignores the first k_sampling entries of the buffer
 */
#ifndef QUORUM_COMM_H
#define QUORUM_COMM_H

#include <stdint.h>
#include "quorum_structure.h"

#define COMM_FIFO_SIZE 128

typedef struct {
    uint8_t agent_id;
    uint8_t msg_n_hops;
    uint8_t agent_state;
} comm_fifo_item_t;

typedef struct {
    comm_fifo_item_t buffer[COMM_FIFO_SIZE];
    uint8_t head;
    uint8_t tail;
    uint8_t count;
} comm_fifo_t;

extern uint8_t comm_anonymous;
extern uint8_t comm_rebroadcast;
extern uint8_t comm_msgs_n_hops;
extern uint8_t comm_hop_count;
extern uint8_t comm_k_sampling;
extern uint16_t comm_expiring_s;
extern comm_fifo_t comm_fifo;
extern uint64_t comm_own_sent;
extern uint64_t comm_relayed;

/* Configure the protocol (call once, when the parameters arrive from the ALF).
 * Anonymous robots never rebroadcast and ignore msgs_n_hops and hop_count;
 * ID-aware robots ignore queue_lenght and k_sampling. */
void comm_configure(uint8_t anonymous, uint8_t rebroadcast, uint16_t expiring_s, uint8_t msgs_n_hops,
                    uint8_t hop_count, uint8_t queue_lenght, uint8_t k_sampling, uint32_t ticks_per_sec);

/* A message from another robot: originator ID, state, hops travelled. */
void comm_receive(uint8_t sender_id, uint8_t state, uint8_t hops);

/* Once per control step: ages the buffer, drops expired entries, cleans the FIFO queue. */
void comm_tick(uint64_t delta_ticks);

/* Fills data[0..2] with the next message to send. Returns 1 for the robot's own
 * state, 2 for a relayed message. */
uint8_t comm_talk(uint8_t my_id, uint8_t my_state, uint8_t data[3]);

/* Quorum test on the buffer (k_sampling applies to the anonymous model only). */
uint8_t comm_quorum(uint8_t my_state);

/* Index of the first buffer entry used for quorum and voting. */
uint8_t comm_first_sample();

/* Number of distinct senders in the buffer. */
uint8_t comm_distinct_ids();

#endif
