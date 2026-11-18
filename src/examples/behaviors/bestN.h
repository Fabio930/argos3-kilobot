/* Kilobot control software for the simple ALF experment : bestN
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 *
 * One behavior for every experiment variant. The variant is chosen in the
 * .argos file (<hierarchicStruct communication/dynamic/confined>) and sent
 * by the ALF during the init handshake (see bestN_protocol.h):
 *  - communication: ID-aware buffer (one entry per sender) or anonymous
 *    circular buffer (Parker replica)
 *  - dynamic:  the robot flips its committed state following a schedule
 *  - confined: the robot picks waypoints only in its own half of the arena
 */
#ifndef BESTN_H
#define BESTN_H

#include "kilolib.h"
#include "bestN_protocol.h"
#include "tree_structure.c"
#include "quorum_structure.c"
#include "distribution_functions.c"

#define PI 3.14159265358979323846
FILE *fp;

/* Enum for messages type */
typedef enum{
  ARK_BROADCAST_MSG = 0,
  ARK_INDIVIDUAL_MSG = 1,
  KILO_BROADCAST_MSG = 255,
  KILO_IDENTIFICATION = 120
}received_message_type;

/* Enum for motion */
typedef enum{
    FORWARD = 0,
    TURN_LEFT = 1,
    TURN_RIGHT = 2,
    STOP = 3,
}motion_t;

/* Enum for boolean flags */
typedef enum{
    false = 0,
    true = 1,
}bool;

/* struct for the robot states */
typedef enum{
    uncommitted = 0,
    committed = 1,
}state_t;

uint64_t delta_elapsed = 0;
uint64_t ticks_elapsed = 0;

/* struct for the robot position */
typedef struct position{
    float position_x,position_y;
}position_t;

/* current motion type */
motion_t current_motion_type = STOP;
motion_t prev_motion_type = STOP;

/* goal position */
position_t goal_position={0,0};
uint32_t reaching_goal_ticks;
uint32_t expiring_dist;
uint8_t avoid_tmmts;

float goal_ticks_sec = TICKS_PER_SEC * 1.3;

/* position and angle given from ARK */
position_t gps_position={0,0};
float gps_angle;
float RotSpeed = 45.0;

/* current state */
state_t my_state;
uint8_t msg_n_hops = 0;

uint32_t turning_ticks = 0;
uint32_t last_motion_ticks = 0;

/* Variables for Smart Arena messages */
uint8_t sa_id = 0;
uint8_t sa_type = 0;
uint16_t sa_payload = 0;

/* experiment variant, received with the CONFIG message */
bool anonymous_comm = false;
bool dynamic_env = false;
bool confined_env = false;
uint8_t k_sampling = 0;

/* init handshake */
bool init_received_config = false;
bool init_received_state = false;
bool init_received_arena = false;
bool init_received_variation = false;
bool experiment_started = false;

/* arena in the robot frame (meters) */
float arena_width = 0;
float arena_height = 0;
float arena_midline = -1;

/* state variation schedule (dynamic environment) */
uint16_t variation_start_sec = 0;
uint16_t variation_end_sec = 0;
uint16_t variation_seed = 0;
uint8_t variation_num_flips = 0;
uint32_t variation_rng_state = 0;
uint32_t state_change_ticks[MAX_STATE_CHANGES];
uint8_t next_state_change = 0;

/* counters for broadcast a message */
const uint16_t broadcasting_ticks = 16;
uint32_t last_broadcast_ticks = 0;
uint8_t broadcasting_flag = 0;

/* Flag for decision to send a word */
bool sending_msg = false;
message_t my_message;

/* lists for decision handling */
uint8_t received_id;
uint8_t received_committed;

/* map of the environment */
arena_a *the_arena = NULL;

uint64_t num_own_info=0;
uint64_t num_other_info=0;
uint16_t selected_msg_indx = QUORUM_NOT_FOUND;

#define FIFO_MSG_SIZE 128

/* Struttura per il singolo elemento della coda */
typedef struct {
    uint8_t agent_id;
    uint8_t msg_n_hops;
    uint8_t agent_state;
} fifo_msg_t;

/* Struttura per il buffer circolare della FIFO */
typedef struct {
    fifo_msg_t buffer[FIFO_MSG_SIZE];
    uint8_t head;
    uint8_t tail;
    uint8_t count;
} fifo_msg_buffer_t;

/* Istanza globale della coda di rebroadcast (ID-aware, policy 2) */
fifo_msg_buffer_t rebroadcast_fifo;
char log_title[30];
uint8_t led = RGB(0,0,0);

/*-------------------------------------------------------------------*/
/*              Function for setting the motor speed                 */
/*-------------------------------------------------------------------*/
void set_motion( motion_t new_motion_type);

/*-------------------------------------------------------------------*/
/*              Send current kb status to the swarm                  */
/*-------------------------------------------------------------------*/
message_t *message_tx();

/*-------------------------------------------------------------------*/
/*          Callback function for successful transmission            */
/*-------------------------------------------------------------------*/
void message_tx_success();

/*-------------------------------------------------------------------*/
/*                      Broadcasting functions                       */
/*-------------------------------------------------------------------*/
void talk();

void talk_id_aware();

void talk_anonymous();

void broadcast();

void anonymous_rebroadcast();

/*-------------------------------------------------------------------*/
/*             Rebroadcasting & FIFO Functions (ID-aware)            */
/*-------------------------------------------------------------------*/
void rnd_rebroadcast();

uint8_t fifo_rebroadcast(uint8_t agent_id, uint8_t agent_state, uint8_t msg_hops, uint8_t agent_idx);

void fifo_msg_init(fifo_msg_buffer_t* fifo);

uint8_t fifo_msg_enqueue(fifo_msg_buffer_t* fifo, uint8_t agent_id, uint8_t Msg_n_hops, uint8_t agent_state);

uint8_t fifo_msg_remove(fifo_msg_buffer_t* fifo, uint8_t agent_id);

uint8_t fifo_msg_move_to_tail(fifo_msg_buffer_t* fifo, uint8_t agent_id, uint8_t msg_hops, uint8_t agent_state);

uint8_t fifo_msg_peek(fifo_msg_buffer_t* fifo, uint8_t* agent_id);

uint8_t fifo_msg_dequeue(fifo_msg_buffer_t* fifo);

uint16_t select_a_random_message();

float random_in_range(float min, float max);

/*-----------------------------------------------------------------------------------*/
/* Function implementing the uncorrelated random walk with the random waypoint model */
/*-----------------------------------------------------------------------------------*/
void select_new_point(bool force);

/*-------------------------------------------------------------------*/
/*                   Parse ALF and kilobot messages                  */
/*-------------------------------------------------------------------*/
void parse_alf_message(uint8_t data[9]);

void update_messages(const uint8_t Msg_n_hops);

void parse_kilo_message(uint8_t data[9]);

void message_rx(message_t *msg, distance_measurement_t *d);

/*-------------------------------------------------------------------*/
/*                   Environment set up                              */
/*-------------------------------------------------------------------*/
void set_waypoint_area();

bool init_completed();

/*-------------------------------------------------------------------*/
/*                  Dynamic environment                              */
/*-------------------------------------------------------------------*/
uint16_t variation_rng_next();

void build_state_change_schedule();

void apply_state_changes();

void set_state(uint8_t state);

/*-------------------------------------------------------------------*/
/*                      Compute angle to Goal                        */
/*-------------------------------------------------------------------*/
void NormalizeAngle(float* angle);

float AngleToGoal();

/*-------------------------------------------------------------------*/
/*                      Random way point model                       */
/*-------------------------------------------------------------------*/
void random_way_point_model();

/*-------------------------------------------------------------------*/
/*                          Logging                                  */
/*-------------------------------------------------------------------*/
void log_buffer_ids();

void log_step();

/*-------------------------------------------------------------------*/
/*                          Init function                            */
/*-------------------------------------------------------------------*/
void setup();

/*-------------------------------------------------------------------*/
/*                             loop                                  */
/*-------------------------------------------------------------------*/
void loop();

/*-------------------------------------------------------------------*/
/*                             main                                  */
/*-------------------------------------------------------------------*/
uint8_t main();

/*-------------------------------------------------------------------*/
/*                             exit                                  */
/*-------------------------------------------------------------------*/
void deallocate_memory();

#endif
