#ifndef BESTN_H
#define BESTN_H

#include <stdint.h>
#include <math.h>
#include "kilolib.h"
#include "tree_structure.c"
#include "quorum_structure.c"
#include "distribution_functions.c"
#include "quorum_comm.c"

#define PI 3.14159265358979323846

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

/* communication parameters from the ALF handshake, applied with comm_configure()
 * once all of them arrived (protocol in quorum_comm.h) */
uint8_t cfg_rebroadcast = 0;
uint16_t cfg_expiring_s = 0;
uint8_t cfg_id_aware = 1;
uint8_t cfg_hop_count = 0;
uint8_t cfg_k_sampling = 0;
uint8_t cfg_queue_lenght = 1;
bool comm_ready = false;

bool sending_msg = false;
message_t my_message;

arena_a *the_arena = NULL;

char log_title[30];
uint8_t led = RGB(0,0,0);

control_type control_mode = f_static;
uint8_t voting_msgs = 0;
uint8_t control_parameter_q = 0;

uint8_t control_parameter = 0;
uint8_t control_value = 0;
uint8_t quorum_value = 0;

bool init_control_received = false;
uint8_t gps_max_x_q = 105;
uint8_t gps_max_y_q = 105;
uint8_t gps_floor_color = 0;

void decision();
void set_motion( motion_t new_motion_type);
message_t *message_tx();
void message_tx_success();
void talk();
float random_in_range(float min, float max);
uint8_t compute_quorum_value();
uint8_t compute_r_threshold(uint8_t quorum_value);
uint8_t majority_vote();
void select_new_point(bool force);
void parse_smart_arena_message(uint8_t data[9], uint8_t kb_index);
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

static float clamp01(float value){
    if(value < 0.0f){
        return 0.0f;
    }
    if(value > 1.0f){
        return 1.0f;
    }
    return value;
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

#endif