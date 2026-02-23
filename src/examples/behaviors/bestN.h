/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */

#ifndef BESTN_H
#define BESTN_H

#include <stdint.h>
#include "kilolib.h"
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
uint8_t my_state;
uint8_t msg_n_hops;

uint32_t turning_ticks = 0;
uint32_t last_motion_ticks = 0;

/* Variables for Smart Arena messages */
uint8_t sa_id = 0;
uint8_t sa_type = 0;
uint16_t sa_payload = 0;

bool init_received_A = false;
bool init_received_B = false;
bool init_received_C = false;
bool init_struct_received = false;
bool init_grid_received = false;
bool init_map_received = false;
bool init_bounds_x_received = false;
bool init_bounds_y_received = false;

/* counters for broadcast a message */
const uint16_t broadcasting_ticks = 16;
uint32_t last_broadcast_ticks = 0;
uint8_t broadcasting_flag = 0;
uint8_t adaptive_comm = 0;
uint32_t adaptive_broadcast_until_ticks = 0;

/* Flag for decision to send a word */
bool sending_msg = false;
message_t my_message;

/* lists for decision handling */
uint8_t received_id;
uint8_t received_committed;

/* map of the environment */
arena_a *the_arena = NULL;

uint16_t selected_msg_indx = 0b1111111111111111;
quorum_a *quorum_list = NULL;
quorum_a **quorum_array;

// uint8_t quorum_reached = 0;
char log_title[30];
uint8_t led = RGB(0,0,0);

/* local copy of floor map for debug */
uint8_t grid_rows = 0;
uint8_t grid_cols = 0;
uint8_t eta_q = 0;
uint8_t map_options = 1;
uint16_t map_seed = 1;
uint8_t seed_hi = 0;
uint8_t seed_lo = 1;
control_type control_mode = f_static;
uint8_t voting_msgs = 0;
uint8_t control_parameter_q = 0;
float control_parameter = 0.0f;
float control_value = 0.0f;
float quorum_value = 0.0f;
bool init_control_received = false;
uint8_t gps_min_x_q = 5;
uint8_t gps_max_x_q = 105;
uint8_t gps_min_y_q = 5;
uint8_t gps_max_y_q = 105;
uint8_t *floor_colors = NULL;

void decision();
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

void broadcast();

void rebroadcast();

/*-----------------------------------------------------------------------------------*/
/*          sample a value, update the map, decide if change residence node          */
/*-----------------------------------------------------------------------------------*/

float random_in_range(float min, float max);
float compute_quorum_value();
float compute_r_threshold(float quorum_value);
int majority_vote();

/*-----------------------------------------------------------------------------------*/
/* Function implementing the uncorrelated random walk with the random waypoint model */
/*-----------------------------------------------------------------------------------*/
void select_new_point(bool force);

/*-------------------------------------------------------------------*/
/*                   Parse smart messages                            */
/*-------------------------------------------------------------------*/
void parse_smart_arena_message(uint8_t data[9], uint8_t kb_index);

/*-------------------------------------------------------------------*/
/*                   Check and save incoming data                    */
/*-------------------------------------------------------------------*/
void update_messages(const uint8_t Msg_n_hops);

/*-------------------------------------------------------------------*/
/*                      Parse smart messages                         */
/*-------------------------------------------------------------------*/
void parse_kilo_message(uint8_t data[9]);

void parse_smart_arena_broadcast(uint8_t data[9]);
void setup_floor_colors();
uint8_t floor_color_id_at_position(float x, float y);
uint8_t floor_color_value_at_position(float x, float y);
uint8_t led_from_color_value(uint8_t color_value);
uint8_t led_from_color_id(uint8_t color_id);
void update_debug_led();

/*-------------------------------------------------------------------*/
/*              Callback function for message reception              */
/*-------------------------------------------------------------------*/
void message_rx(message_t *msg, distance_measurement_t *d);

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
