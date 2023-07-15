/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
/* TODO fare in modo che Argos sappia quali sono i punti scelti da i kilobot...usano un segnale luminoso quando nel punto scelto*/
#include "bestN.h"

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

message_t *message_tx(){    
    if (sending_msg) return &my_message;
    return 0;
}

void message_tx_success(){
    sending_msg = false;
}

void talk(){
    if (!sending_msg && kilo_ticks > last_broadcast_ticks + broadcasting_ticks){
        last_broadcast_ticks = kilo_ticks;
        sending_msg = true;
    }
}

void broadcast(){
    sa_type = 0;
    sa_id = 0;
    sa_payload = 0;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = kilo_uid;
    my_message.data[1] = sa_type;
    my_message.data[2] = my_state;
    my_message.crc = message_crc(&my_message);
}

void rebroadcast(quorum_a *rnd_msg){
    sa_type = 0;
    sa_id = 0;
    sa_payload = 0;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    rnd_msg->delivered = 1;
    my_message.data[0] = rnd_msg->agent_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = rnd_msg->agent_state;
    my_message.crc = message_crc(&my_message);
}

uint8_t check_quorum_trigger(quorum_a **Array[]){
    uint8_t out = 0;
    for(uint8_t i = 0;i < num_quorum_items;i++) if((*Array)[i]->agent_state == committed) out++;
    return out;
}

void check_quorum(quorum_a **Array[]){
    uint8_t commit_counter;
    switch (my_state){
        case committed:
            commit_counter = (check_quorum_trigger(Array) + 1);
            break;
        default:
            commit_counter = check_quorum_trigger(Array);
            break;
    }
    quorum_percentage = commit_counter*(1.0/num_quorum_items);
    if(commit_counter >= (num_quorum_items)*quorum_scaling_factor) quorum_reached = true;
    if(quorum_reached && my_state==uncommitted) led = RGB(3,0,0);
    else if(quorum_reached && my_state==committed) led = RGB(0,3,0);
}

void check_quorum_and_prepare_messages(){
    // select a random message
    quorum_a *rnd_msg;
    switch (broadcasting_flag){
        case 1:
            rnd_msg = select_a_random_message(&quorum_array);
            if(rnd_msg != NULL && rnd_msg->delivered == 0) rebroadcast(rnd_msg);
            else broadcast();
            break;
        
        default:
            broadcast();
            break;
    }
    quorum_percentage = 0.f;
    quorum_reached = false;
    if(quorum_list != NULL && num_quorum_items >= min_quorum_length) check_quorum(&quorum_array);
}

float random_in_range(float min, float max){
    float r = (float)rand_hard() / 255.0;
    return min + (r*(max-min));
}

void select_new_point(bool force){
    /* if the robot arrived to the destination, a new goal is selected and a noisy sample is taken from the respective leaf*/
    if (force || ((abs((int16_t)((gps_position.position_x-goal_position.position_x)*100))*.01<.03) && (abs((int16_t)((gps_position.position_y-goal_position.position_y)*100))*.01<.03))){
        if(!force){
            set_color(RGB(0,3,3));
        }
        goal_position.position_x = random_in_range(the_arena->tlX,the_arena->brX);
        goal_position.position_y = random_in_range(the_arena->tlY,the_arena->brY);
        expiring_dist = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
        reaching_goal_ticks = expiring_dist * goal_ticks_sec;

    }
    else{
        set_color(led);
        if(avoid_tmmts==0){
            uint32_t flag = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
            if(flag >= expiring_dist + .01){
                if(rand_soft()/255.0 <= .5) set_motion(TURN_LEFT);
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
    sa_type = data[shift] & 0b00000001;
    sa_payload = ((uint16_t)(data[shift + 1]) << 8) | data[shift + 2];
    switch(sa_type){
        case MSG_A:
            gps_position.position_x = (((sa_payload >> 8) & 0b11111100) >> 2) * 0.01 * 2;
            gps_position.position_y = ((uint8_t)sa_payload & 0b00111111) * 0.01 * 2;
            gps_angle = (((sa_payload >> 8) & 0b00000011) << 2 | ((uint8_t)sa_payload & 0b0000000011000000) >> 6) * 24;
            if(!init_received_B) init_received_B = true;
            break;
        case MSG_B:
            switch (sa_payload){
                case 0:
                    led = RGB(0,0,0);
                    my_state = uncommitted;
                    break;
                
                case 1:
                    led = RGB(0,0,3);
                    my_state = committed;
                    break;
            }
            if(init_received_B && !init_received_C){
                init_received_C = true;
                select_new_point(true);
                set_motion(FORWARD);
                set_color(led);
            }
            break;
    }
}

void update_messages(){
    update_q(&quorum_array,&quorum_list,NULL,received_id,received_committed);
    sort_q(&quorum_array);
}

void parse_kilo_message(uint8_t data[9]){
    sa_id = data[0];
    sa_type = data[1];
    sa_payload = data[2];
    received_id = sa_id;
    received_committed = (uint8_t)sa_payload;
    update_messages();
}

void parse_smart_arena_broadcast(uint8_t data[9]){   
    sa_type = data[0] & 0b00000001;
    uint8_t extra_payload = data[2];
    sa_payload = ((uint16_t)data[0]>>1) << 8 | (data[1]>>1) ;
    switch (sa_type){
        case MSG_A:
            if(!init_received_A){   
                led = RGB(3,3,0);
                set_color(led);
                complete_tree(&the_arena);
                set_vertices(&the_arena,(ARENA_X*.1),(ARENA_Y*.1));
                uint32_t expiring_dist = (uint32_t)sqrt(pow((ARENA_X)*10,2)+pow((ARENA_Y)*10,2));
                broadcasting_flag = extra_payload;
                set_quorum_vars(expiring_dist * quorum_ticks_sec,(uint8_t)(sa_payload>>8),(uint8_t)sa_payload);
                init_received_A = true;
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
            id1 = (msg->data[0] & 0b11111110) >> 1;
            id2 = (msg->data[3] & 0b11111110) >> 1;
            id3 = (msg->data[6] & 0b11111110) >> 1;
            if (id1 == kilo_uid) parse_smart_arena_message(msg->data, 0);
            else if (id2 == kilo_uid) parse_smart_arena_message(msg->data, 1);
            else if (id3 == kilo_uid) parse_smart_arena_message(msg->data, 2);
            break;
        case KILO_BROADCAST_MSG:
            parse_kilo_message(msg->data);
            break;
        case KILO_IDENTIFICATION:
            id1 = (msg->data[0] & 0b11111110) >> 1;
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
    if(init_received_C){
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
    my_message.type = KILO_BROADCAST_MSG;
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
    fprintf(fp,"%d\t%d\t%f\n",kilo_uid,num_quorum_items,quorum_percentage);
    fclose(fp);
    increment_quorum_counter(&quorum_array);
    erase_expired_items(&quorum_array,&quorum_list);
    check_quorum_and_prepare_messages();
    random_way_point_model();
    talk();
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
    
    destroy_tree(&the_arena);
    destroy_quorum_memory(&quorum_array,&quorum_list);
    return 0;
}