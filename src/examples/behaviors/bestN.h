#ifndef BESTN_H
#define BESTN_H

#include <stdint.h>
#include <math.h>
#include "kilolib.h"
#include "tree_structure.c"
#include "quorum_structure.c"
#include "distribution_functions.c"

#define PI 3.14159265358979323846
#define FIFO_BUFFER_SIZE 128

FILE *fp;

typedef enum{
  ARK_BROADCAST_MSG = 0,
  ARK_INDIVIDUAL_MSG = 1,
  KILO_BROADCAST_MSG = 255,
  KILO_IDENTIFICATION = 120
}received_message_type;

typedef enum{
  f_static = 0,
  f_linear = 1,
  f_sigmoid = 2,
  f_polynomial = 3
}control_type;

typedef enum{
  MSG_A = 0,
  MSG_B = 1,
  MSG_C = 2,
  MSG_D = 3
}message_type;

typedef enum{
    FORWARD = 0,
    TURN_LEFT = 1,
    TURN_RIGHT = 2,
    STOP = 3,
}motion_t;

typedef enum{
    false = 0,
    true = 1,
}bool;

typedef struct position{
    float position_x,position_y;
}position_t;

typedef struct {
    uint8_t agent_id;
    uint8_t agent_state;
    uint8_t msg_n_hops;
} fifo_item_t;

typedef struct {
    fifo_item_t buffer[FIFO_BUFFER_SIZE];
    uint8_t head;
    uint8_t tail;
    uint8_t count;
} generic_fifo_t;

uint64_t delta_elapsed = 0;
uint64_t ticks_elapsed = 0;

motion_t current_motion_type = STOP;
motion_t prev_motion_type = STOP;

position_t goal_position={0,0};
uint32_t reaching_goal_ticks;
uint32_t expiring_dist;
uint8_t avoid_tmmts;

float goal_ticks_sec = TICKS_PER_SEC * 1.3;

position_t gps_position={0,0};
float gps_angle;
float RotSpeed = 45.0;

uint8_t my_state;
uint8_t msg_n_hops;

uint32_t turning_ticks = 0;
uint32_t last_motion_ticks = 0;

uint8_t sa_id = 0;
uint8_t sa_type = 0;
uint16_t sa_payload = 0;

bool init_received_A = false;
bool init_received_B = false;
bool init_received_C = false;

const uint16_t broadcasting_ticks = 16;
uint32_t last_broadcast_ticks = 0;
const uint16_t decision_ticks = TICKS_PER_SEC * 5;
uint32_t last_decision_ticks = 0;
uint8_t broadcasting_flag = 0;
uint8_t adaptive_comm = 0;
uint32_t buff_ticks_sec = TICKS_PER_SEC * .2;
uint32_t buff_ticks = 0;
uint8_t msg_n_hops_rnd = 0;
uint64_t buffer_update_rng = 0;

bool sending_msg = false;
message_t my_message;

uint8_t received_id;
uint8_t received_committed;

arena_a *the_arena = NULL;

uint16_t selected_msg_indx = 0b1111111111111111;
quorum_a *quorum_list = NULL;
quorum_a **quorum_array;

generic_fifo_t rebroadcast_fifo;
generic_fifo_t vote_fifo;

char log_title[30];
uint8_t led = RGB(0,0,0);

control_type control_mode = f_static;
uint8_t voting_msgs = 0;
uint8_t control_parameter_q = 0;

int control_parameter = 0;
int control_value = 0;
int quorum_value = 0;

bool init_control_received = false;
uint8_t gps_max_x_q = 105;
uint8_t gps_max_y_q = 105;
uint8_t gps_floor_color = 0;

void generic_fifo_init(generic_fifo_t* fifo);
void generic_fifo_update(generic_fifo_t* fifo, uint8_t agent_id, uint8_t agent_state, uint8_t msg_n_hops, uint8_t capacity, uint8_t id_aware_flag);
uint8_t generic_fifo_peek(generic_fifo_t* fifo, fifo_item_t* item_out);
uint8_t generic_fifo_dequeue(generic_fifo_t* fifo);
uint8_t fifo_rebroadcast(uint8_t agent_id, uint8_t agent_state, uint8_t msg_hops, uint8_t agent_idx);

void decision();
void set_motion( motion_t new_motion_type);
message_t *message_tx();
void message_tx_success();
void talk();
void broadcast();
void rnd_rebroadcast();
void compute_msg_hops();
float random_in_range(float min, float max);
int compute_quorum_value();
int compute_r_threshold(int quorum_value);
int majority_vote();
void select_new_point(bool force);
void parse_smart_arena_message(uint8_t data[9], uint8_t kb_index);
void update_messages(const uint8_t Msg_n_hops);
void parse_kilo_message(uint8_t data[9]);
void parse_smart_arena_broadcast(uint8_t data[9]);
uint8_t led_from_color_value(uint8_t color_value);
void update_debug_led();
void message_rx(message_t *msg, distance_measurement_t *d);
void NormalizeAngle(float* angle);
float AngleToGoal();
void random_way_point_model();
void setup();
void loop();
uint8_t main();
void deallocate_memory();

static uint8_t buffer_skip_prefix(){
    if(priority_sampling_k == 0){
        return 0;
    }
    if(priority_sampling_k >= num_quorum_items){
        return num_quorum_items;
    }
    return priority_sampling_k;
}

static uint8_t eligible_quorum_items(){
    uint8_t start = buffer_skip_prefix();
    return (num_quorum_items > start) ? (num_quorum_items - start) : 0;
}

static uint16_t find_quorum_index_by_id(const uint8_t agent_id){
    for(uint8_t i = 0; i < num_quorum_items; ++i){
        if(quorum_array[i] != NULL && quorum_array[i]->agent_id == agent_id){
            return i;
        }
    }
    return 0b1111111111111111;
}

static float clamp01(float value){
    if(value < 0.0f){
        return 0.0f;
    }
    if(value > 1.0f){
        return 1.0f;
    }
    return value;
}

static uint8_t sat_inc_u8(const uint8_t value){
    return (value == UINT8_MAX) ? UINT8_MAX : (uint8_t)(value + 1);
}

static void update_arena_from_received_bounds(){
    if(the_arena == NULL){
        return;
    }
    the_arena->tlX = 0.0f;
    the_arena->brX = gps_max_x_q * 0.01f;
    the_arena->tlY = 0.0f;
    the_arena->brY = gps_max_y_q * 0.01f;
}

static uint32_t received_arena_diagonal_cm(){
    float dx_cm = (float)gps_max_x_q;
    float dy_cm = (float)gps_max_y_q;
    if(dx_cm < 0.0f) dx_cm = 0.0f;
    if(dy_cm < 0.0f) dy_cm = 0.0f;
    return (uint32_t)sqrtf(dx_cm*dx_cm + dy_cm*dy_cm);
}

#endif