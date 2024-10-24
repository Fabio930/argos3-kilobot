/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
/* TODO fare in modo che Argos sappia quali sono i punti scelti da i kilobot...usano un segnale luminoso quando nel punto scelto*/
#include "bestN.h"
uint8_t get_leaf_vec_id_in(const uint8_t Leaf_id){
    return leafs_id[Leaf_id];
}

void set_motion( motion_t new_motion_type){
    if(current_motion_type != new_motion_type){
        switch( new_motion_type ) {
            case FORWARD:
                spinup_motors();
                set_motors(kilo_straight_left,kilo_straight_right);
                break;
            case TURN_LEFT:
                spinup_motors();
                set_motors(kilo_turn_left,0);
                break;
            case TURN_RIGHT:
                spinup_motors();
                set_motors(0,kilo_turn_right);
                break;
            case STOP:
            default:
                set_motors(0,0);
        }
        current_motion_type = new_motion_type;
    }
}

bool pos_isin_node(const float PositionX,const float PositionY, tree_a **Node){
    if(((*Node) != NULL) && (PositionX >= (*Node)->tlX && PositionX <= (*Node)->brX)&&(PositionY >= (*Node)->tlY && PositionY <= (*Node)->brY)) return true;
    return false;
}

message_t *message_tx(){    
    if (sending_msg) return &my_message;
    return 0;
}

void message_tx_success(){
    sending_msg = false;
}

void broadcast(){
    if (!sending_msg && kilo_ticks > last_broadcast_ticks + broadcasting_ticks){
        sa_type = 0;
        for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
        int8_t utility_to_send;
        utility_to_send = (int8_t)(last_sample_utility*10);
        my_message.data[0] = kilo_uid << 2 | sa_type;
        my_message.data[1] = last_sample_committed << 7 | utility_to_send;
        my_message.data[2] = last_sample_id << 4 | last_sample_level << 2;
        my_message.crc = message_crc(&my_message);
        last_broadcast_ticks = kilo_ticks;
        sending_msg = true;
    }
}

uint8_t check_quorum_trigger(quorum_a **Array[]){
    uint8_t out = 0;
    for(uint8_t i = 0;i < num_quorum_items;i++){
        uint8_t msg_src = msg_received_from(&tree_array,my_state.current_node,(*Array)[i]->agent_node);
        if(msg_src == THISNODE || msg_src == SUBTREE) out++;
    }
    return out;
}

void check_quorum(quorum_a **Array[]){
    uint8_t counter = check_quorum_trigger(Array) + 1;
    if(counter >= (num_quorum_items+1)*quorum_scaling_factor) my_state.commitment_node = my_state.current_node;
}

void update_quorum_list(tree_a **Current_node,message_a **Mymessage,const uint8_t Msg_switch){
    if(my_state.commitment_node == my_state.current_node && Msg_switch != SIBLINGTREE){
        update_q(&quorum_array,&quorum_list,NULL,(*Mymessage)->agent_id,(*Mymessage)->agent_node);
        sort_q(&quorum_array);
    }
    else if(my_state.commitment_node == (*Current_node)->parent->id){
        update_q(&quorum_array,&quorum_list,NULL,(*Mymessage)->agent_id,(*Mymessage)->agent_node);
        sort_q(&quorum_array);
    }
}

void sample_and_decide(tree_a **leaf){
    tree_a *current_node = get_node(&tree_array,my_state.current_node);
    // select a random message
    uint8_t message_switch = 0;
    for(uint8_t m = 0;m<num_messages;m++){
        update_quorum_list(&current_node,&messages_array[m],message_switch);
        message_switch = msg_received_from(&tree_array,my_state.current_node,messages_array[m]->agent_node);
    }
    message_a *rnd_msg = select_a_random_msg(&messages_array);
    if(rnd_msg != NULL) message_switch = msg_received_from(&tree_array,my_state.current_node,rnd_msg->agent_node);
    if(quorum_list != NULL){
        if(num_quorum_items >= min_quorum_length) check_quorum(&quorum_array);
        else if(num_quorum_items <= min_quorum_items && current_node->parent != NULL) my_state.commitment_node=current_node->parent->id; 
    }
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
        for(uint8_t i = 0;i < branches;i++){
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
    uint8_t agent_node_flag = 0;
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
    // control_parameter = control_gain * (1 - current_node->node_filter->distance);
    // gain_h = control_parameter / (1+control_parameter);
    // gain_k = 1 / (1+control_parameter);
    commitment = commitment * gain_k;
    abandonment = abandonment * gain_k;
    recruitment = recruitment * gain_h;
    cross_inhibition = cross_inhibition * gain_h;
    float p = (float)rand_hard() / 255.0;
    my_state.previous_node = my_state.current_node;
    if     (p < commitment)                                                          {my_state.current_node = over_node->id;           }
    else if(p < commitment + recruitment)                                            {my_state.current_node = agent_node_flag;         }
    else if(p < commitment + cross_inhibition)                                       {my_state.current_node = current_node->parent->id;}
    else if(p < (commitment + recruitment + cross_inhibition + abandonment) * 0.667) {my_state.current_node = current_node->parent->id;}
    erase_messages(&messages_array,&messages_list);
}

float random_in_range(float min, float max){
    float r = (float)rand_hard() / 255.0;
    return min + (r*(max-min));
}

void select_new_point(bool force){
    /* if the robot arrived to the destination, a new goal is selected and a noisy sample is taken from the respective leaf*/
    if (force || ((abs((int16_t)((gps_position.position_x-goal_position.position_x)*100))*.01<.03) && (abs((int16_t)((gps_position.position_y-goal_position.position_y)*100))*.01<.03))){
        if(!force){
            tree_a *leaf = NULL;
            set_color(RGB(0,3,0));
            for(uint8_t l = 0;l < num_leafs;l++){
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
        goal_position.position_x = random_in_range(actual_node->tlX,actual_node->brX);
        goal_position.position_y = random_in_range(actual_node->tlY,actual_node->brY);
        expiring_dist = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
        reaching_goal_ticks = expiring_dist * goal_ticks_sec;

    }
    else{
        set_color(led);
        if(avoid_tmmts==0){
            uint32_t flag = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
            if(flag >= expiring_dist + .01){
                if(rand_soft()/255.0 < .5) set_motion(TURN_LEFT);
                else set_motion(TURN_RIGHT);
                avoid_tmmts=1;
            }
        }
        else{
            if(current_motion_type==TURN_LEFT || current_motion_type==TURN_RIGHT){
                prev_motion_type = current_motion_type;
                set_motion(FORWARD);
                }
            else set_motion(prev_motion_type);
            uint32_t flag = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
            if(flag < expiring_dist) avoid_tmmts=0;
        }
        expiring_dist = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
        if(--reaching_goal_ticks<=0){
            goal_position = gps_position;
            select_new_point(false);
        }
    }
}

void parse_smart_arena_message(uint8_t data[9], uint8_t kb_index){
    // index of first element in the 3 sub-blocks of data
    uint8_t shift = kb_index * 3;
    sa_type = data[shift] & 0b00000011;
    sa_payload = ((uint16_t)data[shift + 1] << 8) | data[shift + 2];
    switch(sa_type){
        case MSG_B:
            gps_position.position_x = (sa_payload >> 10) * 0.01 *2;
            gps_position.position_y = ((uint8_t)sa_payload >> 2) * 0.01 *2;
            gps_angle = (((sa_payload >> 8) & 0b00000011) << 2 | ((uint8_t)sa_payload & 0b00000011)) * 24;
            break;
    }
}

uint8_t derive_agent_node(const uint8_t Received_committed, const uint8_t Received_leaf, const uint8_t Received_level){
    tree_a *leaf = get_node(&tree_array,Received_leaf);
    uint8_t level;
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
    return 0;
}

void update_messages(){
    uint8_t received_node = derive_agent_node(received_committed,received_leaf,received_level);
    update_m(&messages_array,&messages_list,NULL,received_id,received_node,received_leaf,received_utility);
    sort_m(&messages_array);
}

void parse_kilo_message(uint8_t data[9]){
    received_utility = 0;
    sa_id = (data[0] & 0b11111100) >> 2;
    sa_type = data[0] & 0b00000011;
    sa_payload = (((uint16_t)data[1]) << 8) | data[2];
    received_id = sa_id;
    received_utility = (((uint8_t)(sa_payload >> 8)) & 0b01111111) * 0.1;
    received_committed = (((uint8_t)(sa_payload >> 8)) & 0b10000000) >> 7;
    received_leaf = get_leaf_vec_id_in((((uint8_t)sa_payload) & 0b11110000) >> 4);
    received_level = (((uint8_t)sa_payload) & 0b00001100) >> 2;
    update_messages();
}

void parse_smart_arena_broadcast(uint8_t data[9]){   
    sa_type = data[0] & 0b00000011;
    switch (sa_type){
        case MSG_A:
            if(!init_received_A){   
                led = RGB(3,3,0);
                set_color(led);
                float k = data[1]*.01;
                uint8_t best_leaf_id = (data[0] >> 2)+1;
                control_gain = (data[2] >> 4);
                gain_h = (float)control_gain / (1+control_gain);
                gain_k = 1.0 / (1+control_gain);
                uint8_t depth = ((data[2] >> 2)& 0b00000011)+1;
                uint8_t branches = (data[2] & 0b00000011)+1;
                complete_tree(&tree_array,&the_tree,depth,branches,leafs_id,best_leaf_id,MAX_UTILITY,k);
                set_vertices(&the_tree,(ARENA_X*.1),(ARENA_Y*.1));
                uint32_t expiring_dist = (uint32_t)sqrt(pow((ARENA_X)*10,2)+pow((ARENA_Y)*10,2));
                set_expiring_ticks_quorum_item(expiring_dist * quorum_ticks_sec);
                init_received_A = true;
            }
            break;
        case MSG_B:
            if(init_received_A && !init_received_B){   
                uint8_t id1 = (data[0] & 0b11111100) >> 2;
                uint8_t id2 = (data[3] & 0b11111100) >> 2;
                uint8_t id3 = (data[6] & 0b11111100) >> 2;
                if (id1 == kilo_uid) parse_smart_arena_message(data, 0);
                else if (id2 == kilo_uid) parse_smart_arena_message(data, 1);
                else if (id3 == kilo_uid) parse_smart_arena_message(data, 2);
                select_new_point(true);
                set_motion(FORWARD);
                init_received_B = true;
                led = RGB(0,0,0);
                set_color(led);
            }
            break;
        case MSG_C:
            if(my_state.current_level == (data[0] >> 2)){
                if(my_state.current_node == my_state.commitment_node){
                    led = RGB(0,0,3);
                    set_color(led);
                }
                else{
                    led = RGB(3,0,0);
                    set_color(led);
                }
            }
            else{
                led = RGB(0,0,0);
                set_color(led);
            }
            break;
    }
}

void message_rx(message_t *msg, distance_measurement_t *d){
    sa_id = 0;
    sa_type = 0;
    sa_payload = 0;
    uint8_t id1;
    uint8_t id2;
    uint8_t id3;
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
            if (id1 == kilo_uid){
                led = RGB(0,0,3);
                set_color(led);
            }
            else{
                led = RGB(3,0,0);
                set_color(led);
            }
            break;
    }
}

void NormalizeAngle(float* angle){
    while(*angle > 180){
        *angle = *angle-360;
    }
    while(*angle < -180){
        *angle = *angle+360;
    }
}

float AngleToGoal(){
    float angletogoal = (atan2(gps_position.position_y-goal_position.position_y,gps_position.position_x-goal_position.position_x)/PI)*180 - (gps_angle - 180);
    NormalizeAngle(&angletogoal);
    return angletogoal;
}

void random_way_point_model(){   
    if(init_received_B){
        select_new_point(false);
        if(avoid_tmmts == 0){
            float angleToGoal = AngleToGoal();
            if(fabs(angleToGoal) <= 48){
                set_motion(FORWARD);
                last_motion_ticks = kilo_ticks;
            }
            else{
                if(angleToGoal > 0){
                    set_motion(TURN_LEFT);
                    last_motion_ticks = kilo_ticks;
                    turning_ticks = (uint32_t) (fabs(angleToGoal)/(RotSpeed*32.0));
                }
                else{
                    set_motion(TURN_RIGHT);
                    last_motion_ticks = kilo_ticks;
                    turning_ticks = (uint32_t) (fabs(angleToGoal)/(RotSpeed*32.0));
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
}

void setup(){
    /* Init LED and motors */
    set_color(RGB(0,0,0));
    set_motors(0,0);
    /* Init state, message type and control parameters*/
    my_state.previous_node = 0;
    my_state.current_node = 0;
    my_state.commitment_node = 0;
    my_state.current_level = 0;
    my_message.type = KILO_BROADCAST_MSG;
    init_array_msg(&messages_array);
    init_array_qrm(&quorum_array);

    /* Init random seed */
    uint8_t seed = rand_hard();
    rand_seed(seed);
    seed = rand_hard();
    srand(seed);

    /* Init motion variables */
    set_motion(STOP);
}

void loop(){
    fp = fopen("quorum_log.tsv","a");
    fprintf(fp,"%d\t%d\n",kilo_uid,num_quorum_items);
    fclose(fp);
    increment_quorum_counter(&quorum_array);
    erase_expired_items(&quorum_array,&quorum_list);
    random_way_point_model();
    if(last_sensing) broadcast();
}

uint8_t main(){
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