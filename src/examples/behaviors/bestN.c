#include "bestN.h"

float random_in_range(float min, float max){
    float r = (float)rand_hard() / 256.0f;
    return min + (r*(max-min));
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
        for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
        comm_talk((uint8_t)kilo_uid, my_state, my_message.data);
        sending_msg = true;
    }
}

uint8_t compute_quorum_value(){
    uint8_t start = comm_first_sample();
    uint8_t eligible = num_quorum_items - start;
    if(eligible < min_quorum_length) return 0;
    uint16_t agreeing = 1;
    for(uint8_t i = start; i < num_quorum_items; ++i){
        if(quorum_buf[i].agent_state == my_state){
            ++agreeing;
        }
    }
    float q_val_f = (float)agreeing / (float)(eligible + 1);
    control_value = compute_r_threshold(quorum_value);
    return (uint8_t)roundf(q_val_f * 100.0f);
}

uint8_t compute_r_threshold(uint8_t q_value_int){
    float quorum_val = q_value_int / 100.0f;
    float ctrl_param = control_parameter / 100.0f;    
    if(control_mode == f_static) return (uint8_t)roundf(clamp01(ctrl_param) * 100.0f);    
    switch(control_mode){
        case f_linear:
            return (uint8_t)roundf(clamp01(quorum_val) * 100.0f);
        case f_sigmoid:
        {
            const float num = quorum_val;
            const float den = 1.0f + expf(-10.0f*(quorum_val - ctrl_param));
            return (uint8_t)roundf(clamp01(num / den) * 100.0f);
        }
        case f_polynomial:
        {
            const float polynomial = (1.0f - ctrl_param) * powf(quorum_val,3.0f) + ctrl_param;
            return (uint8_t)roundf(clamp01(polynomial) * 100.0f);
        }
        default:
            return (uint8_t)roundf(clamp01(ctrl_param) * 100.0f);
    }
}

uint8_t led_from_color_value(uint8_t color_value){
    switch(color_value){
        case 0: return RGB(3,0,0);
        case 1: return RGB(0,3,0);
        case 2: return RGB(0,0,3);
        case 3: return RGB(3,3,0);
        case 4: return RGB(0,3,3);
        case 5: return RGB(3,0,3);
        default: return RGB(0,0,0);
    }
}

void update_debug_led(){
    led = led_from_color_value(my_state);
    set_color(led);
}

void select_new_point(bool force){
    if (force || ((abs((int16_t)((gps_position.position_x-goal_position.position_x)*100))*.01f<.02f) && (abs((int16_t)((gps_position.position_y-goal_position.position_y)*100))*.01f<.02f))){
        goal_position.position_x = random_in_range(the_arena->tlX,the_arena->brX);
        goal_position.position_y = random_in_range(the_arena->tlY,the_arena->brY);
        expiring_dist = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
        reaching_goal_ticks = expiring_dist * goal_ticks_sec;
    }
    else{
        if(avoid_tmmts==0){
            uint32_t flag = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
            if(flag >= expiring_dist + 0.01f){
                avoid_tmmts=1;
                float angleToGoal = AngleToGoal();
                float p = rand_hard()/256.0f;
                if(p < .33){
                    last_motion_ticks = kilo_ticks;
                    turning_ticks = (uint32_t) ((fabs(angleToGoal))/(RotSpeed*32.0f));
                    set_motion(TURN_LEFT);
                }
                else if(p < .66){
                    last_motion_ticks = kilo_ticks;
                    turning_ticks = (uint32_t) ((fabs(angleToGoal))/(RotSpeed*32.0f));
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
    uint8_t shift = kb_index * 3;
    sa_type = data[shift] & 0b00000001;
    sa_payload = ((uint16_t)(data[shift + 1]) << 8) | data[shift + 2];
    
    switch(sa_type){
        case MSG_A:
        {
            uint32_t payload24 = (((uint32_t)(data[shift] >> 1) & 0x7F) << 16) |
                                 ((uint32_t)data[shift + 1] << 8) |
                                 (uint32_t)data[shift + 2];
            uint8_t x_q = (uint8_t)(payload24 & 0x3F);
            uint8_t y_q = (uint8_t)((payload24 >> 6) & 0x3F);
            uint8_t angle_q = (uint8_t)((payload24 >> 12) & 0xFF);
            uint8_t color_q = (uint8_t)((payload24 >> 20) & 0x07);

            gps_position.position_x = x_q * 0.01f * 2.0f;
            gps_position.position_y = y_q * 0.01f * 2.0f;
            gps_angle = angle_q * (360.0f / 256.0f);
            gps_floor_color = color_q;
            if(init_received_B && init_control_received && !init_received_C){
                init_received_C = true;
                /* first vote 5 s after start, not on the first tick */
                last_decision_ticks = kilo_ticks;
                select_new_point(true);
                set_motion(FORWARD);
            }
            break;
        }
        case MSG_B:
            if(init_received_A){
                if(kb_index == 0){
                    if(!comm_ready){
                        /* last communication parameter: the protocol can start */
                        comm_configure(!cfg_id_aware, cfg_rebroadcast, cfg_expiring_s, (uint8_t)(sa_payload & 0x1F),
                                       cfg_hop_count, cfg_queue_lenght, cfg_k_sampling, TICKS_PER_SEC);
                        comm_ready = true;
                    }
                    init_received_B = true;
                }
                else if(kb_index == 1){
                    control_mode = (uint8_t)((sa_payload >> 14) & 0x03);
                    voting_msgs = (uint8_t)((sa_payload >> 7) & 0x7F);
                    
                    my_state = (uint8_t)(sa_payload & 0x7F);
                    init_control_received = true;
                    update_debug_led();
                    /* r starts from its base value (its value at quorum 0): the assigned value if static */
                    if(!init_received_C) control_value = compute_r_threshold(0);
                }
                else if(kb_index == 2){
                    control_parameter_q = (uint8_t)(sa_payload & 0x7F);
                    float temp_cp = control_parameter_q / 127.0f;
                    control_parameter = (uint8_t)roundf(temp_cp * 100.0f);
                    /* Same as above, whichever of control mode and parameter arrives last */
                    if(!init_received_C) control_value = compute_r_threshold(0);
                }
            }
            break;
    }
}

void parse_kilo_message(uint8_t data[9]){
    sa_id = data[0];
    if(comm_ready && sa_id!=(uint8_t)kilo_uid){
        sa_type = data[1];
        sa_payload = data[2];
        comm_receive(sa_id, (uint8_t)sa_payload, sa_type);
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
            {
                uint8_t packet_type = (uint8_t)(data[2] >> 6);
                uint8_t packet_data = (uint8_t)(data[2] & 0b00111111);
                if(packet_type == 0){
                    if(the_arena == NULL){
                        build_arena(&the_arena);
                    }
                    update_arena_from_received_bounds();
                    cfg_expiring_s = sa_payload;
                    cfg_rebroadcast = (uint8_t)(packet_data & 0x1F);
                    init_received_A = true;
                }
                else if(packet_type == 1){
                    cfg_queue_lenght = (uint8_t)(sa_payload & 0xFF);
                }
                else if(packet_type == 2){
                    cfg_k_sampling = (uint8_t)(sa_payload & 0x7F);
                    cfg_id_aware = (uint8_t)((sa_payload >> 7) & 0x01);
                    cfg_hop_count = (uint8_t)((sa_payload >> 8) & 0x01);
                }
                else if(packet_type == 3){
                    gps_max_x_q = (uint8_t)((sa_payload >> 7) & 0x7F);
                    gps_max_y_q = (uint8_t)(sa_payload & 0x7F);
                    if(gps_max_x_q == 0){
                        gps_max_x_q = 100;
                    }
                    if(gps_max_y_q == 0){
                        gps_max_y_q = 100;
                    }
                    update_arena_from_received_bounds();
                }
            }
            break;
        case MSG_B:
            id1 = (data[0] & 0b11111110) >> 1;
            id2 = (data[3] & 0b11111110) >> 1;
            id3 = (data[6] & 0b11111110) >> 1;
            if (id1 == kilo_uid) parse_smart_arena_message(data, 0);
            if (id2 == kilo_uid) parse_smart_arena_message(data, 1);
            if (id3 == kilo_uid) parse_smart_arena_message(data, 2);
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
            if((msg->data[0] & 0x01) == MSG_A) parse_smart_arena_message(msg->data, 0);
            else{
                id1 = (msg->data[0] & 0b11111110) >> 1;
                id2 = (msg->data[3] & 0b11111110) >> 1;
                id3 = (msg->data[6] & 0b11111110) >> 1;
                if (id1 == kilo_uid) parse_smart_arena_message(msg->data, 0);
                if (id2 == kilo_uid) parse_smart_arena_message(msg->data, 1);
                if (id3 == kilo_uid) parse_smart_arena_message(msg->data, 2);
            }
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
            if(fabs(angleToGoal) <= 36){
                last_motion_ticks = kilo_ticks;
                set_motion(FORWARD);
            }
            else{
                last_motion_ticks = kilo_ticks;
                if(angleToGoal > 0){
                    set_motion(TURN_LEFT);
                    turning_ticks = (uint32_t) (fabs(angleToGoal)/(RotSpeed*32.0f));
                }
                else{
                    set_motion(TURN_RIGHT);
                    turning_ticks = (uint32_t) (fabs(angleToGoal)/(RotSpeed*32.0f));
                }
            }
            switch(current_motion_type){
                case TURN_LEFT:
                    if(kilo_ticks > last_motion_ticks + turning_ticks){
                        last_motion_ticks = kilo_ticks;
                        set_motion(FORWARD);
                    }
                    break;
                case TURN_RIGHT:
                    if(kilo_ticks > last_motion_ticks + turning_ticks){
                        last_motion_ticks = kilo_ticks;
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

void decision(){
    if (kilo_ticks > last_decision_ticks + decision_ticks){
        last_decision_ticks = kilo_ticks;
        uint8_t majority_state = majority_vote();
        float control_value_f = control_value / 100.0f;
        float p = rand_hard()/256.0f;
        if(p < control_value_f) my_state = majority_state;
        else my_state = gps_floor_color;
        update_debug_led();
    }
}

uint8_t majority_vote() {
    uint8_t start = comm_first_sample();
    uint8_t eligible = num_quorum_items - start;
    if (eligible == 0) return my_state;
    uint8_t valid_states[QUORUM_CAPACITY];
    uint8_t vote_count = 0;
    for(uint8_t i = start; i < num_quorum_items; ++i){
        valid_states[vote_count] = quorum_buf[i].agent_state;
        vote_count++;
    }
    if (vote_count < voting_msgs || voting_msgs == 0) return my_state;
    for (uint8_t i = 0; i < voting_msgs; i++) {
        uint8_t random_idx = i + (rand_hard() % (vote_count - i));
        uint8_t temp = valid_states[i];
        valid_states[i] = valid_states[random_idx];
        valid_states[random_idx] = temp;
    }
    uint8_t buffer[6] = {0};
    for (uint8_t i = 0; i < voting_msgs; i++) {
        if (valid_states[i] < sizeof(buffer)) {
            buffer[valid_states[i]]++;
        }
    }
    uint8_t max = 0;
    uint8_t selection = 0;
    for (uint8_t i = 0; i < sizeof(buffer); i++) {
        if (buffer[i] > max) {
            max = buffer[i];
            selection = i;
        }
        else if (max != 0 && buffer[i] == max) {
            float p = rand_hard() / 256.0f;
            if (p < 0.5) selection = i;
        }
    }
    return (max == 0) ? my_state : selection;
}

void setup(){
    set_color(RGB(0,0,0));
    set_motors(0,0);
    my_state = 255;
    my_message.type = KILO_BROADCAST_MSG;
    my_message.crc = message_crc(&my_message);
    comm_configure(0, 0, 0, 0, 0, 0, 0, TICKS_PER_SEC);
    
    uint8_t seed = rand_hard();
    rand_seed(seed);
    seed = rand_hard();
    srand(seed);
    
    snprintf(log_title,30,"quorum_log_agent#%d.tsv",kilo_uid);
    fp = fopen(log_title,"a");
    set_motion(STOP);
}

void loop(){
    delta_elapsed = kilo_ticks - ticks_elapsed;
    ticks_elapsed = kilo_ticks;
    comm_tick(delta_elapsed);
    if(my_state != 255 && init_received_C){
        random_way_point_model();
        quorum_value = compute_quorum_value();
        decision();
        talk();
    }
    fprintf(fp,"%d\t %d\t %.2f\t %.2f\n", my_state, comm_distinct_ids(), quorum_value / 100.0f, control_value / 100.0f);
}

void deallocate_memory(){
    fclose(fp);
    destroy_tree(&the_arena);
    quorum_clear();
    return;
}

uint8_t main(){
    kilo_init();
    kilo_message_tx = message_tx;
    kilo_message_tx_success = message_tx_success;
    kilo_message_rx = message_rx;
    kilo_start(setup, loop);
    deallocate_memory();
    return 0;
}