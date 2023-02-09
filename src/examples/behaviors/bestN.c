/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) fabio.oddi@diag.uniroma1.it
 */

#include "bestN.h"
/*-------------------------------------------------------------------*/
/* Function for translating the relative ID of a leaf in the true ID */
/*-------------------------------------------------------------------*/
int get_leaf_vec_id_in(const int Leaf_id){
    return leafs_id[Leaf_id];
}

/*-------------------------------------------------------------------*/
/*              Function for setting the motor speed                 */
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
/*            Check if a given point is in a given node              */
/*-------------------------------------------------------------------*/
bool pos_isin_node(const float PositionX,const float PositionY, tree_a **Node){
    if(((*Node) != NULL) && (PositionX >= (*Node)->tlX && PositionX <= (*Node)->brX)&&(PositionY >= (*Node)->tlY && PositionY <= (*Node)->brY)) return true;
    return false;
}

/*-------------------------------------------------------------------*/
/*              Send current kb status to the swarm                  */
/*-------------------------------------------------------------------*/
message_t *message_tx(){    
    if (sending_msg) return &my_message;
    return 0;
}

/*-------------------------------------------------------------------*/
/*          Callback function for successful transmission            */
/*-------------------------------------------------------------------*/
void message_tx_success(){
    sending_msg = false;
}

/*-------------------------------------------------------------------*/
/*                 Function to broadcast a message                   */
/*-------------------------------------------------------------------*/
void broadcast(){
    if (!sending_msg && kilo_ticks > last_broadcast_ticks + broadcasting_ticks){
        sa_type = 0;
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

/*-------------------------------------------------------------------*/
/*           Bunch of funtions for handling the quorum               */
/*-------------------------------------------------------------------*/
unsigned int check_quorum_trigger(quorum_a **Array[]){
    unsigned int out = 0;
    for(int i = 0;i < num_quorum_items;i++){
        int msg_src = msg_received_from(&tree_array,my_state.current_node,(*Array)[i]->agent_node);
        if(msg_src == THISNODE || msg_src == SUBTREE) out++;
    }
    return out;
}

void check_quorum(quorum_a **Array[]){
    unsigned int counter = check_quorum_trigger(Array) + 1;
    if(counter >= (num_quorum_items+1)*quorum_scaling_factor) my_state.commitment_node = my_state.current_node;
}

void update_quorum_list(tree_a **Current_node,message_a **Mymessage,const int Msg_switch){
    if(my_state.commitment_node == my_state.current_node && Msg_switch != SIBLINGTREE){
        update_q(&quorum_array,&quorum_list,NULL,(*Mymessage)->agent_id,(*Mymessage)->agent_node);
        sort_q(&quorum_array);
    }
    else if(my_state.commitment_node == (*Current_node)->parent->id){
        update_q(&quorum_array,&quorum_list,NULL,(*Mymessage)->agent_id,(*Mymessage)->agent_node);
        sort_q(&quorum_array);
    }
}

/*-----------------------------------------------------------------------------------*/
/*          sample a value, update the map, decide if change residence node          */
/*-----------------------------------------------------------------------------------*/
void sample_and_decide(tree_a **leaf){
    tree_a *current_node = get_node(&tree_array,my_state.current_node);
    // select a random message
    int message_switch = -1;
    message_a *rnd_msg = select_a_random_msg(&messages_array);
    if(rnd_msg != NULL){
        message_switch = msg_received_from(&tree_array,my_state.current_node,rnd_msg->agent_node);
        update_quorum_list(&current_node,&rnd_msg,message_switch);
    }
    if(quorum_list != NULL){
        if(num_quorum_items >= min_quorum_length) check_quorum(&quorum_array);
        else if(num_quorum_items <= min_quorum_length*.35 && current_node->parent != NULL) my_state.commitment_node=current_node->parent->id; 
    }
    int flag_num_messages=num_messages,flag_num_quorum_items=num_quorum_items;
    // decide to commit or abandon
    float commitment = 0;
    float recruitment = 0;
    float abandonment = 0;
    float cross_inhibition = 0;
    tree_a *over_node = NULL;
    tree_a *c = current_node->children;
    last_sensing = true;
    float random_sample = levy(NOISE*1.0,2) + (*leaf)->gt_utility;
    bottom_up_utility_update(&tree_array,(*leaf)->id,random_sample);
    last_sample_utility = get_utility((*leaf)->node_filter);
    if(last_sample_utility > 10) last_sample_utility=10;
    else if(last_sample_utility < 0) last_sample_utility=0;
    if(c != NULL){
        for(int i = 0;i < branches;i++){
            over_node = c+i;
            if(pos_isin_node(goal_position.position_x,goal_position.position_y,&over_node)) break;
            over_node = NULL;
        }
        if(over_node != NULL && my_state.current_node == my_state.commitment_node){
            if(over_node->node_filter->utility < 0) commitment = 0;
            else if(over_node->node_filter->utility < MAX_UTILITY) commitment = over_node->node_filter->utility/MAX_UTILITY;
            else commitment = 1;
        }
    }
    if(current_node->parent != NULL && my_state.commitment_node == current_node->parent->id){
        if(current_node->node_filter->utility <= 0) abandonment = 1;
        else abandonment = 1/(1 + current_node->node_filter->utility);
    }
    int agent_node_flag = -1;
    switch (message_switch){
        case SUBTREE:
            if(my_state.current_node == my_state.commitment_node){
                bottom_up_utility_update(&tree_array,rnd_msg->agent_leaf,rnd_msg->leaf_utility);
                float utility_flag = get_node(&tree_array,rnd_msg->agent_node)->node_filter->utility;
                if(utility_flag <= 0) recruitment = 0;
                else if(utility_flag<MAX_UTILITY) recruitment = utility_flag/MAX_UTILITY;
                else recruitment = 1;
                agent_node_flag = get_nearest_node(&tree_array,my_state.current_node,rnd_msg->agent_node);
            }
            break;
        case SIBLINGTREE:
            if(current_node->parent->id == my_state.commitment_node){
                bottom_up_utility_update(&tree_array,rnd_msg->agent_leaf,rnd_msg->leaf_utility);
                float utility_flag = get_node(&tree_array,rnd_msg->agent_node)->node_filter->utility;
                if(utility_flag <= 0) cross_inhibition = 0;
                else if(utility_flag < MAX_UTILITY) cross_inhibition = utility_flag/MAX_UTILITY;
                else cross_inhibition = 1;
            }
            break;
    }
    commitment = commitment * gain_k;
    abandonment = abandonment * gain_k;
    recruitment = recruitment * gain_h;
    cross_inhibition = cross_inhibition * gain_h;
    float p = rand() * (1.0 / RAND_MAX);
    // int action = 0;
    if(p < commitment) my_state.current_node = over_node->id;
    else if(p < commitment + recruitment) my_state.current_node = agent_node_flag;
    else if(p < commitment + cross_inhibition) my_state.current_node = current_node->parent->id;
    else if(p < (commitment + recruitment + cross_inhibition + abandonment) * 0.667) my_state.current_node = current_node->parent->id;
    erase_messages(&messages_array,&messages_list);
    // printf("A_id:%d, pn:%d, cn:%d, c:%f, a:%f, r:%f, i:%f\n",kilo_uid,my_state.current_node,my_state.commitment_node,commitment,abandonment,recruitment,cross_inhibition);
    // printf("p:%f, act:%d, msgsw:%d, #msgs:%d, #qrm:%d \n",p,action,message_switch,flag_num_messages,flag_num_quorum_items);
    // printf("rs:%f, fs:%f, lid:%d \n\n",random_sample,last_sample_utility,(*leaf)->id);
}

int random_in_range(int min, int max){return min + ((rand() * (1.0 / RAND_MAX))*(max-min));}

/*-----------------------------------------------------------------------------------*/
/* Function implementing the uncorrelated random walk with the random waypoint model */
/*-----------------------------------------------------------------------------------*/
void select_new_point(bool force){
    /* if the robot arrived to the destination, a new goal is selected and a noisy sample is taken from the respective leaf*/
    if (force || ((abs((int)((gps_position.position_x-goal_position.position_x)*100))*.01<.03) && (abs((int)((gps_position.position_y-goal_position.position_y)*100))*.01<.03))){
        tree_a *leaf = NULL;
        if(!force){
            for(unsigned int l = 0;l < num_leafs;l++){
                leaf = get_node(&tree_array,leafs_id[l]);
                last_sample_id = l;
                if(pos_isin_node(goal_position.position_x,goal_position.position_y,&leaf)) break;
            }
            last_sample_level = get_node(&tree_array,my_state.current_node)->depth;
            if(my_state.commitment_node == my_state.current_node){
                last_sample_committed = 1;
                if(last_sample_level == 4){
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
        tree_a *actual_node = get_node(&tree_array,my_state.current_node);
        my_state.current_level = actual_node->depth;
        float flag, min_dist;
        if(force){min_dist=0;}
        else{
            flag = abs((int)((actual_node->brX-actual_node->tlX)*100))*.001;
            min_dist = abs((int)((actual_node->brY-actual_node->tlY)*100))*.001;
            if(flag > min_dist) min_dist = flag;
        }
        do{
            goal_position.position_x = random_in_range((int)((actual_node->tlX)*100),(int)((actual_node->brX)*100))*.01;
            goal_position.position_y = random_in_range((int)((actual_node->tlY)*100),(int)((actual_node->brY)*100))*.01;
            float dif_x,dif_y;
            dif_x = abs((int)((gps_position.position_x-goal_position.position_x)*100))*.01;
            dif_y = abs((int)((gps_position.position_y-goal_position.position_y)*100))*.01;
            if (dif_x >= min_dist || dif_y >= min_dist ) break;
        }while(true);
        printf("A_id:%d, gx:%f, gy:%f\n",kilo_uid,goal_position.position_x,goal_position.position_y);
    }
}

/*-------------------------------------------------------------------*/
/*                   Parse smart messages                            */
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

/*-------------------------------------------------------------------*/
/*         derive the agent position from the data received          */
/*-------------------------------------------------------------------*/
int derive_agent_node(const unsigned int Received_committed, const unsigned int Received_leaf, const unsigned int Received_level){
    tree_a *leaf = get_node(&tree_array,Received_leaf);
    unsigned int level;
    if(received_committed) level = Received_level;
    else level = Received_level + 1;
    if(level == leaf->depth) return leaf->id;
    while(true){
        if(leaf->parent != NULL){
            leaf = leaf->parent;
            if(level == leaf->depth) return leaf->id;
        }
        else break;
    }
    return -1;
}

/*-------------------------------------------------------------------*/
/*                   Check and save incoming data                    */
/*-------------------------------------------------------------------*/
void update_messages(){
    int received_node = derive_agent_node(received_committed,received_leaf,received_level);
    update_m(&messages_array,&messages_list,NULL,received_id,received_node,received_leaf,received_utility);
    sort_m(&messages_array);
}

/*-------------------------------------------------------------------*/
/*                      Parse smart messages                         */
/*-------------------------------------------------------------------*/
void parse_kilo_message(uint8_t data[9]){
    received_utility = 0;
    sa_id = (data[0] & 0b11111100) >> 2;
    sa_type = data[0] & 0b00000011;
    sa_payload = (((uint16_t)data[1]) << 8) | data[2];
    int temp_leaf;
    switch(sa_type){
        case MSG_A:
            received_id = sa_id;
            received_utility = (float)(((uint8_t)(sa_payload >> 8)) & 0b01111111) * 0.1;
            received_committed = (((uint8_t)(sa_payload >> 8)) & 0b10000000) >> 7;
            temp_leaf = (((uint8_t)sa_payload) & 0b11110000) >> 4;
            received_leaf = get_leaf_vec_id_in(temp_leaf);
            received_level = (((uint8_t)sa_payload) & 0b00001100) >> 2;
            update_messages();
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
                control_parameter = (data[2] >> 4);
                gain_h = control_parameter / (1+control_parameter);
                gain_k = 1 / (1+control_parameter);
                int depth = ((data[2] >> 2)& 0b00000011)+1;
                int branches = (data[2] & 0b00000011)+1;
                complete_tree(&tree_array,&the_tree,depth,branches,leafs_id,best_leaf_id,MAX_UTILITY,k);
                offset_x = (ARENA_X*.1)/2;
                offset_y = (ARENA_Y*.1)/2;
                goal_position.position_x = offset_x;
                goal_position.position_y = offset_y;
                set_vertices(&the_tree,((ARENA_X*.1)-0.02),((ARENA_Y*.1)-0.02));
                float expiring_dist = sqrt(pow((ARENA_X*.1)*100,2)+pow((ARENA_Y*.1)*100,2));
                set_expiring_ticks_message(expiring_dist * TICKS_PER_SEC * 1);
                set_expiring_ticks_quorum_item(expiring_dist * TICKS_PER_SEC * 1);
                init_received_A = true;
            }
            break;
        case MSG_B:
            if(init_received_A && !init_received_B){   
                int id1 = (data[0] & 0b11111100) >> 2;
                int id2 = (data[3] & 0b11111100) >> 2;
                int id3 = (data[6] & 0b11111100) >> 2;
                if (id1 == kilo_uid) parse_smart_arena_message(data, 0);
                else if (id2 == kilo_uid) parse_smart_arena_message(data, 1);
                else if (id3 == kilo_uid) parse_smart_arena_message(data, 2);
                select_new_point(true);
                set_motion(FORWARD);
                init_received_B = true;
                set_color(RGB(0,0,0));
            }
            break;
        case MSG_C:
            if(my_state.current_level == (int)(data[0] >> 2)){
                if(my_state.current_node == my_state.commitment_node){
                    set_color(RGB(0,0,3));
                }
                else set_color(RGB(3,0,0));
            }
            else set_color(RGB(0,0,0));
            break;
    }
}

/*-------------------------------------------------------------------*/
/*              Callback function for message reception              */
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
/*                      Compute angle to Goal                        */
/*-------------------------------------------------------------------*/
void NormalizeAngle(int* angle){
    while(*angle > 180){
        *angle = *angle-360;
    }
    while(*angle < -180){
        *angle = *angle+360;
    }
}

int AngleToGoal(){
    int angletogoal = (atan2(gps_position.position_y-goal_position.position_y,gps_position.position_x-goal_position.position_x)/PI)*180 - (gps_angle - 180);
    NormalizeAngle(&angletogoal);
    return angletogoal;
}

/*-------------------------------------------------------------------*/
/*                      Random way point model                       */
/*-------------------------------------------------------------------*/
void random_way_point_model(){   
    if(init_received_B){
        select_new_point(false);
        int angleToGoal = AngleToGoal();
        if(fabs(angleToGoal) <= 24){
            set_motion(FORWARD);
            last_motion_ticks = kilo_ticks;
        }
        else{
            if(angleToGoal > 0){
                set_motion(TURN_LEFT);
                last_motion_ticks = kilo_ticks;
                turning_ticks = (unsigned int) (fabs(angleToGoal)/(RotSpeed*32.0));
            }
            else{
                set_motion(TURN_RIGHT);
                last_motion_ticks = kilo_ticks;
                turning_ticks = (unsigned int) (fabs(angleToGoal)/(RotSpeed*32.0));
            }
        }
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
}

/*-------------------------------------------------------------------*/
/*                          Init function                            */
/*-------------------------------------------------------------------*/
void setup(){
    /* Initialise LED and motors */
    set_color(RGB(0,0,0));
    set_motors(0,0);
    
    /* Initialise state, message type and control parameters*/
    my_state.current_node = 0;
    my_state.commitment_node = 0;
    my_message.type = KILO_BROADCAST_MSG;
    init_array_msg(&messages_array);
    init_array_qrm(&quorum_array);

    /* Initialise random seed */
    uint8_t seed = rand_hard();
    rand_seed(seed);
    seed = rand_hard();
    srand(seed);

    /* Initialise motion variables */
    set_motion(STOP);
}

/*-------------------------------------------------------------------*/
/*                             loop                                  */
/*-------------------------------------------------------------------*/
void loop(){
    increment_messages_counter(&messages_array);
    increment_quorum_counter(&quorum_array);
    erase_expired_messages(&messages_array,&messages_list);
    erase_expired_items(&quorum_array,&quorum_list);
    random_way_point_model();
    if(last_sensing) broadcast();
}

/*-------------------------------------------------------------------*/
/*                             main                                  */
/*-------------------------------------------------------------------*/
int main(){
    kilo_init();
    
    // register message transmission callback
    kilo_message_tx = message_tx;

    // register tranmsission success callback
    kilo_message_tx_success = message_tx_success;

    // register message reception callback
    kilo_message_rx = message_rx;

    kilo_start(setup, loop);
    
    destroy_tree(&tree_array,&the_tree);
    destroy_messages_memory(&messages_array,&messages_list);
    destroy_quorum_memory(&quorum_array,&quorum_list);
    return 0;
}