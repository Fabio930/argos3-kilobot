/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
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
    my_message.data[0] = 0;
    my_message.data[1] = 0;
    my_message.data[2] = 0;
    sending_msg = false;
}

void talk(){
    if (!sending_msg && kilo_ticks > last_broadcast_ticks + broadcasting_ticks){
        last_broadcast_ticks = kilo_ticks;
        float_t p;
        switch(broadcasting_flag){
            case 0:
                broadcast();
                break;
            case 1:
                selected_msg_indx = select_a_random_message();
                switch(msg_n_hops){
                    case 0:
                        p = random_in_range(0,1);
                        if(p<=0.5){
                            if(selected_msg_indx != 0b1111111111111111) rebroadcast();
                            else broadcast();
                        }
                        else{
                            broadcast();
                        }
                        break;
                    default:
                        compute_msg_hops();
                        if(selected_msg_indx != 0b1111111111111111 && quorum_array[selected_msg_indx]->msg_n_hops < msg_n_hops_rnd){
                            quorum_array[selected_msg_indx]->msg_n_hops += 1;
                            rebroadcast();
                        }
                        else broadcast();
                        break;
                }
                break;
            case 2:
                selected_msg_indx = select_message_by_fifo(&quorum_array,msg_n_hops);
                if(selected_msg_indx != 0b1111111111111111) rebroadcast();
                else broadcast();                
                break;
            default:
                break;   
        }
        selected_msg_indx = 0b1111111111111111;
        sending_msg = true;
    }
}

void compute_msg_hops(){
    if(kilo_ticks > buff_ticks_sec + buff_ticks){
        buff_ticks = kilo_ticks;
        if(buffer_update_rng>0) msg_n_hops_rnd = 0;
        else if(buffer_erase>0) msg_n_hops_rnd -= 6;// -1 on erase for 60 sec. timeout
        else msg_n_hops_rnd += 1;
        buffer_update_rng = 0;
        buffer_erase = 0;
    }
    if(msg_n_hops_rnd>msg_n_hops) msg_n_hops_rnd = msg_n_hops;
    printf("HOPS: %d\n",msg_n_hops_rnd);
}

void broadcast(){
    // frequency log
    num_own_info += 1;
    // message
    sa_type = 0;
    uint8_t msg_n_hops_fifo = msg_n_hops;
    if(broadcasting_flag==2 && msg_n_hops > 0) sa_type = msg_n_hops_fifo;
    sa_id = kilo_uid;
    sa_payload = my_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

void rebroadcast(){
    // frequency log
    num_other_info +=1;
    // message
    sa_type = 0;
    if(broadcasting_flag==2 && msg_n_hops > 0) sa_type = quorum_array[selected_msg_indx]->msg_n_hops - 1;
    sa_id = quorum_array[selected_msg_indx]->agent_id;
    sa_payload = quorum_array[selected_msg_indx]->agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    quorum_array[selected_msg_indx]->delivered = 1;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

float_t random_in_range(float_t min, float_t max){
    float_t r = (float_t)rand_hard() / 255.0;
    return min + (r*(max-min));
}

void select_new_point(bool force){
    /* if the robot arrived to the destination, a new goal is selected and a noisy sample is taken from the respective leaf*/
    if (force || ((abs((int16_t)((gps_position.position_x-goal_position.position_x)*100))*.01<.02) && (abs((int16_t)((gps_position.position_y-goal_position.position_y)*100))*.01<.02))){
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
            if(flag >= expiring_dist + 0.01){
                avoid_tmmts=1;
                float_t angleToGoal = AngleToGoal();
                float_t p = rand_hard()/255.0;
                if(p < .33){
                    last_motion_ticks = kilo_ticks;
                    turning_ticks = (uint32_t) ((fabs(angleToGoal))/(RotSpeed*32.0));
                    set_motion(TURN_LEFT);
                }
                else if(p < .66){
                    last_motion_ticks = kilo_ticks;
                    turning_ticks = (uint32_t) ((fabs(angleToGoal))/(RotSpeed*32.0));
                    set_motion(TURN_RIGHT);
                }
                else avoid_tmmts=0;
            }
        }
        else{
            if(current_motion_type==TURN_LEFT || current_motion_type==TURN_RIGHT){
                if(kilo_ticks > last_motion_ticks + turning_ticks){
                    last_motion_ticks = kilo_ticks;  
                    prev_motion_type = current_motion_type;
                    set_motion(FORWARD);
                }
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
            gps_angle = (((uint8_t)(sa_payload >> 8) & 0b00000011) << 2 | ((uint8_t)sa_payload & 0b11000000) >> 6) * 24;
            if(init_received_B && !init_received_C){
                init_received_C = true;
                select_new_point(true);
                set_motion(FORWARD);
                set_color(led);
            }
            break;
        case MSG_B:
            if(init_received_A){
                uint8_t quorum_threshold = (uint8_t)(sa_payload >> 8);
                uint8_t state = (uint8_t)sa_payload & 0b00000001;
                msg_n_hops = (uint8_t)sa_payload >> 1;
                msg_n_hops_rnd = msg_n_hops;
                switch (state){
                    case 0:
                        led = RGB(0,0,0);
                        my_state = uncommitted;
                        break;
                    
                    case 1:
                        led = RGB(0,0,3);
                        my_state = committed;
                        break;
                }
                set_quorum_threshold(quorum_threshold);
                init_received_B = true;
            }
            break;
    }
}

void update_messages(const uint8_t Msg_n_hops){
    uint32_t expiring_time = (uint32_t)exponential_distribution(expiring_ticks_quorum);
    uint8_t result = update_q(&quorum_array,&quorum_list,NULL,received_id,received_committed,expiring_time,Msg_n_hops);
    sort_q(&quorum_array);
    switch (result){
        case 0:
            buffer_neglect += 1;
            break;
        case 1:
            buffer_insertion += 1;
            break;
        case 2:
            buffer_update_rng += 1;
            buffer_update +=1;
            break;
    }
}

void check_quorum(quorum_a **Array[]){
    uint8_t tmp = my_state;
    for (uint8_t i = 0; i < num_quorum_items; i++) tmp += (*Array)[i]->agent_state;
    if(num_quorum_items >= min_quorum_length && tmp >= (num_quorum_items + 1)*quorum_threshold) quorum_reached = 1;
    else quorum_reached = 0;
}

void parse_kilo_message(uint8_t data[9]){
    sa_id = data[0];
    if(sa_id!=(uint8_t)kilo_uid){
        sa_type = data[1];
        sa_payload = data[2];
        received_id = sa_id;
        received_committed = (uint8_t)sa_payload;
        update_messages(sa_type);
    }
    else sa_id = 0;
}

void parse_smart_arena_broadcast(uint8_t data[9]){   
    uint8_t id1;
    uint8_t id2;
    uint8_t id3;
    sa_type = data[0] & 0b00000001;
    
    switch (sa_type){
        case MSG_A:
            sa_payload = ((uint16_t)data[0]>>1) << 7 | (data[1]>>1);
            if(!init_received_A){   
                led = RGB(3,3,0);
                set_color(led);
                complete_tree(&the_arena);
                set_vertices(&the_arena,(ARENA_X*.1),(ARENA_Y*.1));
                uint32_t expiring_dist;
                switch (sa_payload){
                    case 0:
                        expiring_dist = (uint32_t)sqrt(pow((ARENA_X)*10,2)+pow((ARENA_Y)*10,2));
                        break;
                    default:
                        expiring_dist = sa_payload;
                        break;
                }
                broadcasting_flag = data[2];
                set_msg_life(expiring_dist * TICKS_PER_SEC);
                init_received_A = true;
            }
            break;
        case MSG_B:
            id1 = (data[0] & 0b11111110) >> 1;
            id2 = (data[3] & 0b11111110) >> 1;
            id3 = (data[6] & 0b11111110) >> 1;
            if (id1 == kilo_uid) parse_smart_arena_message(data, 0);
            else if (id2 == kilo_uid) parse_smart_arena_message(data, 1);
            else if (id3 == kilo_uid) parse_smart_arena_message(data, 2);
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

void NormalizeAngle(float_t* angle){
    while(*angle > 180){
        *angle = *angle-360;
    }
    while(*angle < -180){
        *angle = *angle+360;
    }
}

float_t AngleToGoal(){
    float_t angletogoal = (atan2(gps_position.position_y-goal_position.position_y,gps_position.position_x-goal_position.position_x)/PI)*180 - (gps_angle - 180);
    NormalizeAngle(&angletogoal);
    return angletogoal;
}

void random_way_point_model(){   
    if(init_received_C){
        select_new_point(false);
        if(avoid_tmmts == 0){
            float_t angleToGoal = AngleToGoal();
            if(fabs(angleToGoal) <= 36){
                last_motion_ticks = kilo_ticks;
                set_motion(FORWARD);
            }
            else{
                last_motion_ticks = kilo_ticks;
                if(angleToGoal > 0){
                    set_motion(TURN_LEFT);
                    turning_ticks = (uint32_t) (fabs(angleToGoal)/(RotSpeed*32.0));
                }
                else{
                    set_motion(TURN_RIGHT);
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
    snprintf(log_title,30,"quorum_log_agent#%d.tsv",kilo_uid);
    /* Init LED and motors */
    set_color(RGB(0,0,0));
    set_motors(0,0);
    /* Init state, message type and control parameters*/
    my_message.type = KILO_BROADCAST_MSG;
    my_message.crc = message_crc(&my_message);
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
    decrement_quorum_counter(&quorum_array);
    erase_expired_items(&quorum_array,&quorum_list,&buffer_erase);
    random_way_point_model();
    check_quorum(&quorum_array);
    if(init_received_C) talk();
    fp = fopen(log_title,"a");
    fprintf(fp,"%d\t%d\t%d\t%ld\t%ld\n",my_state,quorum_reached,num_quorum_items,num_own_info,num_other_info/*,buffer_neglect,buffer_insertion,buffer_update*/);
    fclose(fp);
    if(quorum_reached==1) set_color(RGB(3,0,0));
    else set_color(led);
}

void deallocate_memory(){
    destroy_tree(&the_arena);
    destroy_quorum_memory(&quorum_array,&quorum_list);
    return;
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
    
    deallocate_memory();

    return 0;
}