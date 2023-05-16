/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
#ifndef BESTN_H
#define BESTN_H

#include "kilolib.h"
#include "tree_structure.c"
#include "message_structure.c"
#include "quorum_structure.c"
#include "distribution_functions.c"

#define PI 3.14159265358979323846
/* used only for noisy data generation */
typedef enum{
    MAX_UTILITY = 10,
    NOISE = 1
}signal;

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
typedef struct state{
    uint8_t previous_node,current_node,commitment_node,current_level;
}state_t;

/* struct for the robot position */
typedef struct position{
    float position_x,position_y;
}position_t;

/* current motion type */
motion_t current_motion_type = STOP;

/* goal position */
position_t goal_position={0,0};
uint32_t reaching_goal_ticks;
uint32_t expiring_dist;

float goal_ticks_sec = TICKS_PER_SEC * 1.3;
float quorum_ticks_sec = TICKS_PER_SEC * 4;

/* position and angle given from ARK */
position_t gps_position={0,0};
float gps_angle;
float RotSpeed = 45.0;

/* current state */
state_t my_state={0,0,0,0};

uint32_t turning_ticks = 0;
uint32_t last_motion_ticks = 0;

/* Variables for Smart Arena messages */
uint8_t sa_id = 0;
uint8_t sa_type = 0;
uint16_t sa_payload = 0;

bool init_received_A = false;
bool init_received_B = false;

/* counters for broadcast a message */
const uint16_t broadcasting_ticks = 3;
uint32_t last_broadcast_ticks = 0;
bool last_sensing = false;

/* Flag for decision to send a word */
bool sending_msg = false;
message_t my_message;

/* lists for decision handling */
uint8_t received_id;
uint8_t received_level;
uint8_t received_committed;
uint8_t received_leaf;
float received_utility;

uint8_t control_gain;
float control_parameter;
float gain_h;
float gain_k;

/* used only for noisy data generation */
uint8_t last_sample_id = 0;
uint8_t last_sample_level;
uint8_t last_sample_committed;
float last_sample_utility = -1;

/* map of the environment */
tree_a *the_tree = NULL;
tree_a **tree_array;
uint8_t leafs_id[16];

message_a *messages_list = NULL;
message_a **messages_array;

quorum_a *quorum_list = NULL;
quorum_a **quorum_array;

uint8_t led = RGB(0,0,0);
/*-------------------------------------------------------------------*/
/* Function for translating the relative ID of a leaf in the true ID */
/*-------------------------------------------------------------------*/
uint8_t get_leaf_vec_id_in(const uint8_t Leaf_id);

/*-------------------------------------------------------------------*/
/*              Function for setting the motor speed                 */
/*-------------------------------------------------------------------*/
void set_motion( motion_t new_motion_type);

/*-------------------------------------------------------------------*/
/*            Check if a given point is in a given node              */
/*-------------------------------------------------------------------*/
bool pos_isin_node(const float PositionX,const float PositionY, tree_a **Node);

/*-------------------------------------------------------------------*/
/*              Send current kb status to the swarm                  */
/*-------------------------------------------------------------------*/
message_t *message_tx();

/*-------------------------------------------------------------------*/
/*          Callback function for successful transmission            */
/*-------------------------------------------------------------------*/
void message_tx_success();

/*-------------------------------------------------------------------*/
/*                 Function to broadcast a message                   */
/*-------------------------------------------------------------------*/
void broadcast();

/*-------------------------------------------------------------------*/
/*           Bunch of funtions for handling the quorum               */
/*-------------------------------------------------------------------*/
uint8_t check_quorum_trigger(quorum_a **Array[]);

void check_quorum(quorum_a **Array[]);

void update_quorum_list(tree_a **Current_node,message_a **Mymessage,const uint8_t Msg_switch);

/*-----------------------------------------------------------------------------------*/
/*          sample a value, update the map, decide if change residence node          */
/*-----------------------------------------------------------------------------------*/
void sample_and_decide(tree_a **leaf);

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
/*         derive the agent position from the data received          */
/*-------------------------------------------------------------------*/
uint8_t derive_agent_node(const uint8_t Received_committed, const uint8_t Received_leaf, const uint8_t Received_level);

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