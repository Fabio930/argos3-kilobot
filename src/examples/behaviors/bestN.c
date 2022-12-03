/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) fabio.oddi@diag.uniroma1.it
 */

#include "kilolib.h"
#include <stdlib.h>
#include<stdio.h>
#include "tree_structure.h"
#include "message_structure.h"
#include "quorum_structure.h"

#define PI 3.14159265358979323846
/* used only for noisy data generation */
const float DBL_MIN = 0.15;
typedef enum{
    MAX_UTILITY = 10,
    NOISE = 1
}signal;

/* divided by 10 */
typedef enum{
    ARENA_X = 5,
    ARENA_Y = 5
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
  MSG_C = 2
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
    int current_node,commitment_node,current_level;
}state_t;

/* struct for the robot position */
typedef struct position{
    float position_x,position_y;
}position_t;

/* offsets of map axes*/
float offset_x, offset_y;

/* current motion type */
motion_t current_motion_type = STOP;

/* goal position */
position_t goal_position={0,0};

/* position and angle given from ARK */
position_t gps_position={0,0};
int gps_angle=-1;
float RotSpeed=38.0;
float min_dist;
uint32_t lastWaypointTime;
uint32_t maxWaypointTime=3600;//3600; // about 2 minutes

/* current state */
state_t my_state={0,0,0};

unsigned int turning_ticks = 0;
unsigned int straight_ticks = 0;
const uint8_t max_turning_ticks = 160; /* constant to allow a maximum rotation of 180 degrees with \omega=\pi/5 */
const uint16_t max_straight_ticks = 320; /* set the \tau_m period to 2.5 s: n_m = \tau_m/\delta_t = 2.5/(1/32) */
uint32_t last_motion_ticks = 0;

/* Variables for Smart Arena messages */
int sa_id = -1;
int sa_type = 0;
int sa_payload = 0;

bool init_received_A=false;
bool init_received_B=false;

/* counters for broadcast a message */
const uint16_t broadcasting_ticks = 3;
uint32_t last_broadcast_ticks = 0;
bool last_sensing=false;

/* Flag for decision to send a word */
bool sending_msg = false;
int sending_type = MSG_A;
message_t my_message;

/* lists for decision handling */
unsigned int received_id;
unsigned int received_level;
unsigned int received_committed;
unsigned int received_leaf;
float received_utility;
bool ARK_sem_talking=false;

// float control_parameter_gain=3;
float control_parameter=3;
float gain_h;
float gain_k;

/* used only for noisy data generation */
int last_sample_id=-1;
unsigned int last_sample_level;
unsigned int last_sample_committed;
float last_sample_utility=-1;

/* map of the environment */
tree_a *the_tree=NULL;
tree_a *tree_array[];
unsigned int leafs_id[16];

message_a *messages_list=NULL;
message_a *messages_array[];

quorum_a *quorum_list=NULL;
message_a *quorum_array[];

bool light = true;


/*-------------------------------------------------------------------*/
/*                                                                   */
/*-------------------------------------------------------------------*/
int get_leaf_vec_id_in(const int Leaf_id){
    return leafs_id[Leaf_id];
}

/*-------------------------------------------------------------------*/
/* Function for setting the motor speed                              */
/*-------------------------------------------------------------------*/
void set_motion( motion_t new_motion_type){
    bool calibrated = true;
    if(current_motion_type != new_motion_type){
        switch( new_motion_type ) {
        case FORWARD:
            spinup_motors();
            if(calibrated) set_motors(kilo_straight_left,kilo_straight_right);
            else set_motors(70,70);
            break;
        case TURN_LEFT:
            spinup_motors();
            if(calibrated) set_motors(kilo_turn_left,0);
            else set_motors(70,0);
            break;
        case TURN_RIGHT:
            spinup_motors();
            if(calibrated) set_motors(0,kilo_turn_right);
            else set_motors(0,70);
            break;
        case STOP:
        default:
            set_motors(0,0);
        }
        current_motion_type = new_motion_type;
    }
}

/*-------------------------------------------------------------------*/
/* Function to sample a random number from a Gaussian distribution   */
/*-------------------------------------------------------------------*/
float generate_gaussian_noise(float mu, float std_dev){
    const float epsilon = DBL_MIN;
    const float two_pi = 2.0*PI;
    float u1;
    do{
        u1 = rand() * (1.0 / RAND_MAX);
    }while(u1<=epsilon);
    float z0 = sqrt(-2.0 * log(u1)) * cos(two_pi * u1);
    return z0 * std_dev + mu;
}

bool bot_isin_node(tree_a **Node){
    if(((*Node)!=NULL)&&(gps_position.position_x >= (*Node)->tlX && gps_position.position_x <= (*Node)->brX)&&(gps_position.position_y >= (*Node)->tlY && gps_position.position_y <= (*Node)->brY)) return true;
    return false;
}

/*-------------------------------------------------------------------*/
/* Send current kb status to the swarm                               */
/*-------------------------------------------------------------------*/
message_t *message_tx(){    
    if (sending_msg) return &my_message;
    return 0;
}

/*-------------------------------------------------------------------*/
/* Callback function for successful transmission                     */
/*-------------------------------------------------------------------*/
void message_tx_success(){
    sending_msg = false;
}

/*-------------------------------------------------------------------*/
/* Function to broadcast a message                                        */
/*-------------------------------------------------------------------*/
void broadcast(){
    if (!sending_msg && kilo_ticks > last_broadcast_ticks + broadcasting_ticks){
        sa_type=0;
        for (int i = 0; i < 9; ++i) my_message.data[i]=0;
        int utility_to_send;
        switch (sending_type){
            case MSG_A:
                utility_to_send = (int)(last_sample_utility*10);
                my_message.data[0] = kilo_uid << 2 | sa_type;
                my_message.data[1] = last_sample_committed << 7 | utility_to_send;
                my_message.data[2] = last_sample_id << 4 | last_sample_level << 2;
                break;
        }
        my_message.crc = message_crc(&my_message);
        last_broadcast_ticks = kilo_ticks;
        sending_msg = true;
    }
}

unsigned int check_quorum_trigger(quorum_a **Array[]){
    unsigned int out=0;
    for(int i=0;i<num_quorum_items;i++){
        int msg_src=msg_received_from(&tree_array,my_state.current_node,(*Array)[i]->agent_node);
        if(msg_src==THISNODE || msg_src==SUBTREE) out++;
    }
    return out;
}

void check_quorum(quorum_a **Array){
    unsigned int counter = check_quorum_trigger(Array);
    if(counter>=num_quorum_items*quorum_scaling_factor) my_state.commitment_node=my_state.current_node;
}

void update_quorum_list(tree_a **Current_node,message_a **Mymessage,const int Msg_switch){
    if(my_state.commitment_node==my_state.current_node && Msg_switch!=SIBLINGTREE) update_q(&quorum_array,&quorum_list,NULL,(*Mymessage)->agent_id,(*Mymessage)->agent_node,0);
    else if(my_state.commitment_node==(*Current_node)->parent->id) update_q(&quorum_array,&quorum_list,NULL,(*Mymessage)->agent_id,(*Mymessage)->agent_node,0);
}

/*-----------------------------------------------------------------------------------*/
/* sample a value, update the map, decide if change residence node                   */
/*-----------------------------------------------------------------------------------*/
void sample_and_decide(tree_a **leaf){
    tree_a *current_node = get_node(&tree_array,my_state.current_node);
    // select a random message
    int message_switch=-1;
    message_a *rnd_msg = select_a_random_msg(&messages_array);
    if(rnd_msg!=NULL){
        message_switch=msg_received_from(&tree_array,my_state.current_node,rnd_msg->agent_node);
        update_quorum_list(&current_node,&rnd_msg,message_switch);
    }
    if(quorum_list!=NULL){
        if(num_quorum_items>=min_quorum_length) check_quorum(&quorum_array);
        else if(num_quorum_items<min_quorum_length*.8 && current_node->parent!=NULL) my_state.commitment_node=current_node->parent->id; 
    }

    // decide to commit or abandon
    float commitment = 0;
    float recruitment = 0;
    float abandonment = 0;
    float cross_inhibition = 0;
    tree_a *over_node=NULL;
    tree_a *c=current_node->children;
    last_sensing = true;
    float random_sample = generate_gaussian_noise((*leaf)->gt_utility,NOISE);
    bottom_up_utility_update(&tree_array,(*leaf)->id,random_sample);
    last_sample_utility = get_utility((*leaf)->node_filter);
    if(last_sample_utility > 10) last_sample_utility=10;
    else if(last_sample_utility < 0) last_sample_utility=0;
    if(c!=NULL){
        for(int i=0;i<branches;i++){
            over_node=c+i;
            if(bot_isin_node(&over_node)) break;
            over_node=NULL;
        }
        if(over_node!=NULL && my_state.current_node==my_state.commitment_node){
            if(over_node->node_filter->utility < 0) commitment = 0;
            else if(over_node->node_filter->utility < MAX_UTILITY) commitment = over_node->node_filter->utility/MAX_UTILITY;
            else commitment = 1;
        }
    }
    if(current_node->parent!=NULL && my_state.commitment_node==current_node->parent->id){
        if(current_node->node_filter->utility<=0) abandonment=1;
        else abandonment = 1/(1 + current_node->node_filter->utility);
    }
    int agent_node_flag;
    switch (message_switch){
        case SUBTREE:
            if(my_state.current_node==my_state.commitment_node){
                bottom_up_utility_update(&tree_array,rnd_msg->agent_leaf,rnd_msg->leaf_utility);
                float utility_flag = get_node(&tree_array,rnd_msg->agent_node)->node_filter->utility;
                if(utility_flag<=0) recruitment = 0;
                else if(utility_flag<MAX_UTILITY) recruitment = utility_flag/MAX_UTILITY;
                else recruitment = 1;
                agent_node_flag = get_nearest_node(&tree_array,my_state.current_node,rnd_msg->agent_node);
            }
            break;
        case SIBLINGTREE:
            if(current_node->parent->id==my_state.commitment_node){
                bottom_up_utility_update(&tree_array,rnd_msg->agent_leaf,rnd_msg->leaf_utility);
                float utility_flag = get_node(&tree_array,rnd_msg->agent_node)->node_filter->utility;
                if(utility_flag<=0) cross_inhibition = 0;
                else if(utility_flag<MAX_UTILITY) cross_inhibition = utility_flag/MAX_UTILITY;
                else cross_inhibition = 1;
            }
            break;
    }
    commitment = commitment * gain_k;
    abandonment = abandonment * gain_k;
    recruitment = recruitment * gain_h;
    cross_inhibition = cross_inhibition * gain_h;
    float p = (rand()%1000)*.001;
    if(p<commitment) my_state.current_node = over_node->id;
    else if(p<commitment+recruitment) my_state.current_node = agent_node_flag;
    else if(p<commitment+cross_inhibition) my_state.current_node = current_node->parent->id;
    else if(p<(commitment+recruitment+cross_inhibition+abandonment)*.667) my_state.current_node = current_node->parent->id;
    erase_messages(&messages_array,&messages_list);
    my_state.current_level = get_node(&tree_array,my_state.current_node)->depth;
}

int random_in_range(int min, int max){
   return min + (rand()%(max-min));
}

/*-----------------------------------------------------------------------------------*/
/* Function implementing the uncorrelated random walk with the random waypoint model */
/*-----------------------------------------------------------------------------------*/
void select_new_point(bool force){
    /* if the robot arrived to the destination, a new goal is selected and a noisy sample is taken from the correspective leaf*/
    if (force || ((abs((int)((gps_position.position_x-goal_position.position_x)*100))*.01<.015) && (abs((int)((gps_position.position_y-goal_position.position_y)*100))*.01<.015))){
        tree_a *leaf=NULL;
        if(!force){
            for(unsigned int l=0;l<num_leafs;l++){
                leaf = get_node(&tree_array,leafs_id[l]);
                last_sample_id = l;
                if(bot_isin_node(&leaf)) break;
            }
            if(leaf==NULL){
                last_sample_utility = -1;
                last_sample_id = -1;
                gps_angle = -1;
                printf("ERROR____Agent:%d___NOT_ON_LEAF__\n",kilo_uid);
            }
            else{
                last_sample_level = get_node(&tree_array,my_state.current_node)->depth;
                if(my_state.commitment_node==my_state.current_node){
                    last_sample_committed=1;
                    if(last_sample_level==4){
                        last_sample_level = last_sample_level - 1;
                        last_sample_committed = 0;
                    }
                }
                else{   
                    last_sample_level = last_sample_level - 1;
                    last_sample_committed = 0;
                }
                sample_and_decide(&leaf);
            }
        }
        lastWaypointTime = kilo_ticks;
        tree_a *actual_node = get_node(&tree_array,my_state.current_node);
        float flag;
        flag=abs((int)((actual_node->brX-actual_node->tlX)*100))*.0025;
        min_dist=abs((int)((actual_node->brY-actual_node->tlY)*100))*.0025;
        if(flag>min_dist) min_dist=flag;
        do{
            goal_position.position_x=(float)(random_in_range((int)((actual_node->tlX)*100),(int)((actual_node->brX)*100)))*.01;
            goal_position.position_y=(float)(random_in_range((int)((actual_node->tlY)*100),(int)((actual_node->brY)*100)))*.01;
            float dif_x,dif_y;
            dif_x = abs((int)((gps_position.position_x-goal_position.position_x)*100))*.01;
            dif_y = abs((int)((gps_position.position_y-goal_position.position_y)*100))*.01;
            if (dif_x >= min_dist || dif_y >= min_dist ) break;
        }while(true);
    }
}

/*-------------------------------------------------------------------*/
/* Parse smart messages                            */
/*-------------------------------------------------------------------*/
void parse_smart_arena_message(uint8_t data[9], uint8_t kb_index){
    // index of first element in the 3 sub-blocks of data
    uint8_t shift = kb_index * 3;
    sa_type = data[shift] & 0b00000011;
    sa_payload = ((uint16_t)data[shift + 1] << 8) | data[shift + 2];
    switch(sa_type){
        case MSG_B:
            gps_position.position_x = (sa_payload >> 10) * 0.02;
            gps_position.position_y = ((uint8_t)sa_payload >> 2) * 0.02;
            gps_angle = (((sa_payload >> 8) & 0b00000011) << 2 | ((uint8_t)sa_payload & 0b00000011)) * 24;
            break;
    }
}

int derive_agent_node(const unsigned int Received_committed, const unsigned int Received_leaf, const unsigned int Received_level){
    tree_a *leaf=get_node(&tree_array,Received_leaf);
    unsigned int level;
    if(received_committed) level = Received_level;
    else level = Received_level + 1;
    if(level==leaf->depth) return leaf->id;
    while(true){
        if(leaf->parent!=NULL){
            leaf=leaf->parent;
            if(level==leaf->depth) return leaf->id;
        }
        else break;
    }
    return -1;
}

/*-------------------------------------------------------------------*/
/* Check and save incoming data                                      */
/*-------------------------------------------------------------------*/
void update_messages(){
    int received_node=derive_agent_node(received_committed,received_leaf,received_level);
    update(&messages_array,&messages_list,NULL,received_id,received_node,received_leaf,received_utility);
}

/*-------------------------------------------------------------------*/
/* Parse smart messages                                              */
/*-------------------------------------------------------------------*/
void parse_kilo_message(uint8_t data[9]){
    // Agents wait for 3 messages by the same teammate
    // if the chain is broken the agent forgets partial data
    sa_id = (data[0] & 0b11111100) >> 2;
    sa_type = data[0] & 0b00000011;
    sa_payload = (uint16_t)data[1] << 8 | data[2];
    int counter_check, temp_leaf;
    switch(sa_type){
        case MSG_A:
            counter_check = get_counter_from_id(&messages_array, sa_id);
            if((counter_check==-1 || counter_check > 5*broadcasting_ticks)){
                received_id = sa_id;
                received_utility = ((uint8_t)(sa_payload >> 8)) & 0b01111111;
                received_committed = (((uint8_t)(sa_payload >> 8)) & 0b10000000) >> 7;
                temp_leaf = (((uint8_t)sa_payload) & 0b11110000) >> 4;
                received_leaf = get_leaf_vec_id_in(temp_leaf);
                received_level = (((uint8_t)sa_payload) & 0b00001100) >> 2;
                update_messages();
            }
            break;
    }
}

void parse_smart_arena_broadcast(uint8_t data[9]){   
    sa_type = data[0] & 0b00000011;
    switch (sa_type){
        case MSG_A:
            if(!init_received_A){   
                set_color(RGB(3,3,0));
                float k = data[1]*.01;
                int best_leaf_id = (data[0] >> 2)+1;
                int depth = (data[2] >> 2)+1;
                int branches = (data[2] & 0b00000011)+1;
                complete_tree(&tree_array,&the_tree,depth,branches,&leafs_id,best_leaf_id,MAX_UTILITY,k);
                offset_x=(ARENA_X*.1)/2;
                offset_y=(ARENA_Y*.1)/2;
                goal_position.position_x=offset_x;
                goal_position.position_y=offset_y;
                set_vertices(&the_tree,(ARENA_X*.1),(ARENA_Y*.1));
                int expiring_dist = (ARENA_X*.1)*100;
                if((ARENA_Y*.1)>offset_x) expiring_dist=(ARENA_Y*.1)*100;
                set_expiring_ticks_message(expiring_dist*TICKS_PER_SEC);
                set_expiring_ticks_quorum_item(expiring_dist*TICKS_PER_SEC*2);
                init_received_A=true;
            }
            break;
        case MSG_B:
            if(!init_received_B && init_received_A){   
                int id1 = (data[0] & 0b11111100) >> 2;
                int id2 = (data[3] & 0b11111100) >> 2;
                int id3 = (data[6] & 0b11111100) >> 2;
                if (id1 == kilo_uid) parse_smart_arena_message(data, 0);
                else if (id2 == kilo_uid) parse_smart_arena_message(data, 1);
                else if (id3 == kilo_uid) parse_smart_arena_message(data, 2);
                select_new_point(true);
                set_motion(FORWARD);
                init_received_B=true;
                set_color(RGB(0,0,0));
            }
            break;
    }
}

/*-------------------------------------------------------------------*/
/* Callback function for message reception                           */
/*-------------------------------------------------------------------*/
void message_rx(message_t *msg, distance_measurement_t *d){
    sa_id = -1;
    sa_type = 0;
    sa_payload = 0;
    int id1;
    int id2;
    int id3;
    switch (msg->type){
        case ARK_BROADCAST_MSG:
            parse_smart_arena_broadcast(msg->data);
            break;
        case ARK_INDIVIDUAL_MSG:
            id1 = (msg->data[0] & 0b11111100) >> 2;
            id2 = (msg->data[3] & 0b11111100) >> 2;
            id3 = (msg->data[6] & 0b11111100) >> 2;
            if (id1 == kilo_uid) parse_smart_arena_message(msg->data, 0);
            else if (id2 == kilo_uid) parse_smart_arena_message(msg->data, 1);
            else if (id3 == kilo_uid) parse_smart_arena_message(msg->data, 2);
            break;
        case KILO_BROADCAST_MSG:
            parse_kilo_message(msg->data);
            break;
        case KILO_IDENTIFICATION:
            id1 = (msg->data[0] & 0b11111100) >> 2;
            if (id1 == kilo_uid) set_color(RGB(0,0,3));
            else set_color(RGB(3,0,0));
            break;
    }
}

/*-------------------------------------------------------------------*/
/* Compute angle to Goal                                             */
/*-------------------------------------------------------------------*/
void NormalizeAngle(int* angle){
    while(*angle>180){
        *angle=*angle-360;
    }
    while(*angle<-180){
        *angle=*angle+360;
    }
}
int AngleToGoal(){
    int angletogoal=(atan2(gps_position.position_y-goal_position.position_y,gps_position.position_x-goal_position.position_x)/PI)*180 - (gps_angle - 180);
    NormalizeAngle(&angletogoal);
    return angletogoal;
}

/*-------------------------------------------------------------------*/
/* Function implementing the uncorrelated random walk                */
/*-------------------------------------------------------------------*/
void random_walk(){
    switch( current_motion_type ) {
    case TURN_LEFT:
        if(kilo_ticks > last_motion_ticks + turning_ticks){
            /* start moving forward */
            last_motion_ticks = kilo_ticks;  // fixed time FORWARD
            set_motion(FORWARD);
            straight_ticks = rand()%max_straight_ticks + 1;
        }
    case TURN_RIGHT:
        if(kilo_ticks > last_motion_ticks + turning_ticks){
            /* start moving forward */
            last_motion_ticks = kilo_ticks;  // fixed time FORWARD
            set_motion(FORWARD);
            straight_ticks = rand()%max_straight_ticks + 1;
        }
        break;
    case FORWARD:
        if(kilo_ticks > last_motion_ticks + straight_ticks){
            /* perform a radnom turn */
            last_motion_ticks = kilo_ticks;
            turning_ticks = rand()%max_turning_ticks + 1;
            if(rand()%2){
                set_motion(TURN_LEFT);
            }
            else{
                set_motion(TURN_RIGHT);
            }
        }
        break;
    case STOP:
    default:
        set_motion(STOP);
    }
}

void random_way_point_model(){   
    if(gps_angle!=-1){
        int angleToGoal = AngleToGoal();
        if(fabs(angleToGoal) <= 24){
            set_motion(FORWARD);
            last_motion_ticks = kilo_ticks;
        }
        else{
            if(angleToGoal>0){
                set_motion(TURN_LEFT);
                last_motion_ticks = kilo_ticks;
                turning_ticks=(unsigned int) ( fabs(angleToGoal)/RotSpeed*32.0 );
            }
            else{
                set_motion(TURN_RIGHT);
                last_motion_ticks = kilo_ticks;
                turning_ticks=(unsigned int) ( fabs(angleToGoal)/RotSpeed*32.0 );
            }
        }
        select_new_point(false);
        switch(current_motion_type){
            case TURN_LEFT:
                if(kilo_ticks > last_motion_ticks + turning_ticks){
                    /* start moving forward */
                    last_motion_ticks = kilo_ticks;  // fixed time FORWARD
                    set_motion(FORWARD);
                }
                break;
            case TURN_RIGHT:
                if(kilo_ticks > last_motion_ticks + turning_ticks){
                    /* start moving forward */
                    last_motion_ticks = kilo_ticks;  // fixed time FORWARD
                    set_motion(FORWARD);
                }
                break;
            case FORWARD:
                break;
            case STOP:
            default:
                set_motion(STOP);
        }
    }
    else if(init_received_B){
        set_motion(FORWARD);
        random_walk();
    }
}

/*-------------------------------------------------------------------*/
/* Init function                                                     */
/*-------------------------------------------------------------------*/
void setup(){
    /* Initialise LED and motors */
    set_color(RGB(0,0,0));
    set_motors(0,0);

    /* Initialise state and message type*/
    my_state.current_node=0;
    my_state.commitment_node=0;
    my_message.type=KILO_BROADCAST_MSG;
    gain_h = control_parameter/(1+control_parameter);
    gain_k = 1 / (1+control_parameter);

    /* Initialise random seed */
    uint8_t seed = rand_hard();
    rand_seed(seed);
    seed = rand_hard();
    srand(seed);

    /* Initialise motion variables */
    last_motion_ticks=rand()%max_straight_ticks;
    set_motion(STOP);
}

/*-------------------------------------------------------------------*/
/* Main loop                                                         */
/*-------------------------------------------------------------------*/
void loop(){
    printf("_________ID_%d____N_MSG_%d_________\n",kilo_uid,num_messages);
    message_a *flag = messages_list;
    for (int i = 0; i < num_messages; i++){
        flag = flag->next;
    }
    // print_m(&messages_array);
    switch (my_state.current_level){
    case 0:
        set_color(RGB(3,0,0));
        break;
    case 1:
        set_color(RGB(0,3,0));
        break;
    case 2:
        set_color(RGB(0,0,3));
        break;
    case 3:
        set_color(RGB(3,3,0));
        break;
    case 4:
        set_color(RGB(0,3,3));
        break;
    
    default:
        break;
    }
    if(my_state.commitment_node==my_state.current_node){
        if(light) light = false;
        else{
            set_color(RGB(0,0,0));
            light = true;
        }
    }
    else light = true;
    increment_messages_counter(&messages_array);
    increment_quorum_counter(&quorum_array);
    erase_expired_messages(&messages_array,&messages_list);
    erase_expired_items(&quorum_array,&quorum_list);
    random_way_point_model();
    if(last_sensing) broadcast();
}

int main(){
    kilo_init();
    
    // register message transmission callback
    kilo_message_tx = message_tx;

    // register tranmsission success callback
    kilo_message_tx_success = message_tx_success;

    // register message reception callback
    kilo_message_rx = message_rx;

    kilo_start(setup, loop);
    
    erase_tree(&tree_array,&the_tree);
    erase_messages(&messages_array,&messages_list);
    erase_quorum_list(&quorum_array,&quorum_list);
    return 0;
}
