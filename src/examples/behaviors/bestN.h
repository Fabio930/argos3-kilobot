/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
#ifndef BESTN_H
#define BESTN_H

#include "kilolib.h"
#include "tree_structure.c"
#include "quorum_structure.c"
#include "distribution_functions.c"

#define PI 3.14159265358979323846
FILE *fp;

/* divided by 10 */
typedef enum{
    ARENA_X = 10,
    ARENA_Y = 10
}arena_size;

/* Enum for messages type */
typedef enum{
  ARK_BROADCAST_MSG = 0,
  ARK_INDIVIDUAL_MSG = 1,
  KILO_BROADCAST_MSG = 255,
  KILO_IDENTIFICATION = 120
}received_message_type;

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

/* struct for the robot states */
typedef enum{
    uncommitted = 0,
    committed = 1,
}state_t;

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
float quorum_ticks_sec = TICKS_PER_SEC * 2;

/* position and angle given from ARK */
position_t gps_position={0,0};
float gps_angle;
float RotSpeed = 45.0;

/* current state */
state_t my_state;

uint32_t turning_ticks = 0;
uint32_t last_motion_ticks = 0;

/* Variables for Smart Arena messages */
uint8_t sa_id = 0;
uint8_t sa_type = 0;
uint16_t sa_payload = 0;

bool init_received_A = false;
bool init_received_B = false;
bool init_received_C = false;

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

quorum_a *rnd_msg = NULL;
quorum_a *quorum_list = NULL;
quorum_a **quorum_array;
float quorum_percentage;
bool quorum_reached = false;

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

void broadcast();

void rebroadcast();

/*-------------------------------------------------------------------*/
/*           Bunch of funtions for handling the quorum               */
/*-------------------------------------------------------------------*/
uint8_t check_quorum_trigger(quorum_a **Array[]);

void check_quorum(quorum_a **Array[]);

/*-----------------------------------------------------------------------------------*/
/*          sample a value, update the map, decide if change residence node          */
/*-----------------------------------------------------------------------------------*/
void check_quorum_and_prepare_messages();

float random_in_range(float min, float max);

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
void update_messages();

/*-------------------------------------------------------------------*/
/*                      Parse smart messages                         */
/*-------------------------------------------------------------------*/
void parse_kilo_message(uint8_t data[9]);

void parse_smart_arena_broadcast(uint8_t data[9]);

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

#endif