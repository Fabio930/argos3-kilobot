/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
#include "bestN.h"


static uint8_t buffer_skip_prefix(){
    if(priority_sampling_k == 0){
        return 0;
    }
    if(priority_sampling_k >= num_quorum_items){
        return num_quorum_items;
    }
    return priority_sampling_k;
}

static uint8_t eligible_quorum_items(){
    uint8_t start = buffer_skip_prefix();
    return (num_quorum_items > start) ? (num_quorum_items - start) : 0;
}

static uint16_t find_quorum_index_by_id(const uint8_t agent_id){
    for(uint8_t i = 0; i < num_quorum_items; ++i){
        if(quorum_array[i] != NULL && quorum_array[i]->agent_id == agent_id){
            return i;
        }
    }
    return 0b1111111111111111;
}

float random_in_range(float min, float max){
    float r = (float)rand_hard() / 255.0;
    return min + (r*(max-min));
}

static float clamp01(float value){
    if(value < 0.0f){
        return 0.0f;
    }
    if(value > 1.0f){
        return 1.0f;
    }
    return value;
}

void fifo_msg_init(fifo_msg_buffer_t* fifo) {
    fifo->head = 0;
    fifo->tail = 0;
    fifo->count = 0;
}

uint8_t fifo_msg_enqueue(fifo_msg_buffer_t* fifo, uint8_t agent_id, uint8_t Msg_n_hops, uint8_t agent_state) {
    for (uint8_t i = 0, idx = fifo->head; i < fifo->count; ++i, idx = (idx + 1) % FIFO_MSG_SIZE) {
        if (fifo->buffer[idx].agent_id == agent_id) return fifo_msg_move_to_tail(fifo,agent_id,Msg_n_hops,agent_state);
    }
    if (fifo->count >= FIFO_MSG_SIZE) {
        fifo->head = (fifo->head + 1) % FIFO_MSG_SIZE;
        fifo->count--;
    }
    fifo->buffer[fifo->tail].agent_id = agent_id;
    fifo->buffer[fifo->tail].msg_n_hops = Msg_n_hops;
    fifo->buffer[fifo->tail].agent_state = agent_state;
    fifo->tail = (fifo->tail + 1) % FIFO_MSG_SIZE;
    fifo->count++;
    return 1;
}

uint8_t fifo_msg_remove(fifo_msg_buffer_t* fifo, uint8_t agent_id) {
    if (fifo->count == 0) return 0;
    uint8_t idx = fifo->head;
    for (uint8_t i = 0; i < fifo->count; ++i) {
        if (fifo->buffer[idx].agent_id == agent_id) {
            for (uint8_t j = i; j < fifo->count - 1; ++j) {
                uint8_t from = (fifo->head + j + 1) % FIFO_MSG_SIZE;
                uint8_t to = (fifo->head + j) % FIFO_MSG_SIZE;
                fifo->buffer[to] = fifo->buffer[from];
            }
            fifo->tail = (fifo->tail == 0) ? FIFO_MSG_SIZE - 1 : fifo->tail - 1;
            fifo->count--;
            return 1;
        }
        idx = (idx + 1) % FIFO_MSG_SIZE;
    }
    return 0;
}

uint8_t fifo_msg_move_to_tail(fifo_msg_buffer_t* fifo, uint8_t agent_id, uint8_t Msg_n_hops, uint8_t agent_state) {
    if (fifo->count == 0) return 0;
    uint8_t idx = fifo->head;
    uint8_t found = 0;
    for (uint8_t i = 0; i < fifo->count; ++i) {
        if (fifo->buffer[idx].agent_id == agent_id) {
            fifo->buffer[idx].msg_n_hops = Msg_n_hops;
            fifo->buffer[idx].agent_state = agent_state;
            fifo_msg_remove(fifo, agent_id);
            found = 1;
            break;
        }
        idx = (idx + 1) % FIFO_MSG_SIZE;
    }
    if (!found) return 0;
    return fifo_msg_enqueue(fifo, agent_id, Msg_n_hops, agent_state);
}

uint8_t fifo_msg_peek(fifo_msg_buffer_t* fifo, uint8_t* agent_id) {
    if (fifo->count == 0) return 0;
    *agent_id = fifo->buffer[fifo->head].agent_id;
    return 1;
}

uint8_t fifo_msg_dequeue(fifo_msg_buffer_t* fifo) {
    if (fifo->count == 0) return 0;
    fifo->head = (fifo->head + 1) % FIFO_MSG_SIZE;
    fifo->count--;
    return 1;
}

static uint8_t sat_inc_u8(const uint8_t value){
    return (value == UINT8_MAX) ? UINT8_MAX : (uint8_t)(value + 1);
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

static uint32_t received_arena_diagonal_cm(){
    float dx_cm = (float)gps_max_x_q;
    float dy_cm = (float)gps_max_y_q;
    if(dx_cm < 0.0f) dx_cm = 0.0f;
    if(dy_cm < 0.0f) dy_cm = 0.0f;
    return (uint32_t)sqrtf(dx_cm*dx_cm + dy_cm*dy_cm);
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
        float p;
        switch(broadcasting_flag){
            case 0:
                broadcast();
                break;
            case 1:
                p = random_in_range(0,1);
                if(p<0.5){
                    selected_msg_indx = select_a_random_message();
                    switch(msg_n_hops){
                        case 0:
                            if(selected_msg_indx != 0b1111111111111111) rnd_rebroadcast();
                            else broadcast();
                            break;
                        default:
                            if(adaptive_comm == 1) compute_msg_hops();
                            uint8_t hop_limit = (adaptive_comm == 1) ? msg_n_hops_rnd : msg_n_hops;
                            if(selected_msg_indx != 0b1111111111111111 && quorum_array[selected_msg_indx]->delivered < hop_limit) rnd_rebroadcast();
                            else broadcast();
                            break;
                    }
                }
                else broadcast();
                break;
            case 2:
                p = random_in_range(0,1);
                if(p<0.5){
                    if(id_aware){
                        uint8_t agent_id;
                        if(fifo_msg_peek(&rebroadcast_fifo, &agent_id)) {
                            uint8_t msg_n_hops_local = 0;
                            uint8_t agent_state = 0;
                            uint8_t agent_idx = 0xFF;
                            for(uint8_t i=0, idx=rebroadcast_fifo.head; i<rebroadcast_fifo.count; ++i, idx=(idx+1)%FIFO_MSG_SIZE) {
                                if(rebroadcast_fifo.buffer[idx].agent_id == agent_id) {
                                    msg_n_hops_local = rebroadcast_fifo.buffer[idx].msg_n_hops;
                                    agent_state = rebroadcast_fifo.buffer[idx].agent_state;
                                    agent_idx = idx;
                                    break;
                                }
                            }
                            if(agent_idx != 0xFF) {
                                fifo_rebroadcast(agent_id, agent_state, msg_n_hops_local, agent_idx);
                                fifo_msg_dequeue(&rebroadcast_fifo);
                            } else broadcast();
                        } else broadcast();
                    }
                    else broadcast();
                }
                else broadcast();                
                break;
            default:
                break;   
        }
        selected_msg_indx = 0b1111111111111111;
        sending_msg = true;
    }
}

void broadcast(){
    sa_type = 0;
    sa_id = kilo_uid;
    sa_payload = my_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

void rnd_rebroadcast(){
    sa_type = sat_inc_u8(quorum_array[selected_msg_indx]->msg_n_hops);
    sa_id = quorum_array[selected_msg_indx]->agent_id;
    sa_payload = quorum_array[selected_msg_indx]->agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    quorum_array[selected_msg_indx]->delivered = sat_inc_u8(quorum_array[selected_msg_indx]->delivered);
    quorum_array[selected_msg_indx]->msg_n_hops = sa_type;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

uint8_t fifo_rebroadcast(uint8_t agent_id, uint8_t agent_state, uint8_t msg_hops, uint8_t agent_idx){
    uint8_t sa_type_local = sat_inc_u8(msg_hops);
    sa_type = sa_type_local;
    sa_id = agent_id;
    sa_payload = agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;

    uint16_t q_idx = find_quorum_index_by_id(agent_id);
    if(q_idx != 0b1111111111111111){
        quorum_array[q_idx]->delivered = sat_inc_u8(quorum_array[q_idx]->delivered);
        quorum_array[q_idx]->msg_n_hops = sa_type_local;
    }

    rebroadcast_fifo.buffer[agent_idx].msg_n_hops = sa_type_local;
    return 1;
}

void compute_msg_hops(){
    if(kilo_ticks > buff_ticks_sec + buff_ticks){
        buff_ticks = kilo_ticks;
        if(buffer_update_rng > 0){
            msg_n_hops_rnd = 0;
        }
        else{
            msg_n_hops_rnd += 1;
        }
        buffer_update_rng = 0;
    }
    if(msg_n_hops_rnd > msg_n_hops){
        msg_n_hops_rnd = msg_n_hops;
    }
}


void vote_fifo_update(const uint8_t agent_id, const uint8_t agent_state){
    uint8_t capacity = voting_msgs;
    if(capacity == 0){
        vote_fifo_head = 0;
        vote_fifo_tail = 0;
        vote_fifo_count = 0;
        return;
    }
    if(capacity > FIFO_BUFFER_SIZE){
        capacity = FIFO_BUFFER_SIZE;
    }
    while(vote_fifo_count > capacity){
        vote_fifo_head = (uint8_t)((vote_fifo_head + 1) % FIFO_BUFFER_SIZE);
        vote_fifo_count--;
    }
    if(vote_fifo_count == 0){
        vote_fifo_head = vote_fifo_tail;
    }

    if(!id_aware){
        if(vote_fifo_count >= capacity){
            vote_fifo_head = (uint8_t)((vote_fifo_head + 1) % FIFO_BUFFER_SIZE);
            vote_fifo_count--;
        }
        vote_fifo_ids[vote_fifo_tail] = 0;
        vote_fifo_states[vote_fifo_tail] = agent_state;
        vote_fifo_tail = (uint8_t)((vote_fifo_tail + 1) % FIFO_BUFFER_SIZE);
        vote_fifo_count++;
        return;
    }

    int16_t found = -1;
    for(uint8_t i = 0; i < vote_fifo_count; ++i){
        uint8_t idx = (uint8_t)((vote_fifo_head + i) % FIFO_BUFFER_SIZE);
        if(vote_fifo_ids[idx] == agent_id){
            found = i;
            break;
        }
    }

    if(found < 0){
        if(vote_fifo_count >= capacity){
            vote_fifo_head = (uint8_t)((vote_fifo_head + 1) % FIFO_BUFFER_SIZE);
            vote_fifo_count--;
        }
        vote_fifo_ids[vote_fifo_tail] = agent_id;
        vote_fifo_states[vote_fifo_tail] = agent_state;
        vote_fifo_tail = (uint8_t)((vote_fifo_tail + 1) % FIFO_BUFFER_SIZE);
        vote_fifo_count++;
        return;
    }

    uint8_t last_offset = (uint8_t)(vote_fifo_count - 1);
    if((uint8_t)found != last_offset){
        for(uint8_t i = (uint8_t)found; i < last_offset; ++i){
            uint8_t from = (uint8_t)((vote_fifo_head + i + 1) % FIFO_BUFFER_SIZE);
            uint8_t to = (uint8_t)((vote_fifo_head + i) % FIFO_BUFFER_SIZE);
            vote_fifo_ids[to] = vote_fifo_ids[from];
            vote_fifo_states[to] = vote_fifo_states[from];
        }
        uint8_t last_idx = (uint8_t)((vote_fifo_head + last_offset) % FIFO_BUFFER_SIZE);
        vote_fifo_ids[last_idx] = agent_id;
        vote_fifo_states[last_idx] = agent_state;
    }
    else{
        uint8_t idx = (uint8_t)((vote_fifo_head + last_offset) % FIFO_BUFFER_SIZE);
        vote_fifo_states[idx] = agent_state;
    }
}

float compute_quorum_value(){
    uint8_t eligible = eligible_quorum_items();
    if(quorum_array == NULL || eligible < min_quorum_length) return 2.0f;
    uint16_t agreeing = 1; /* include own opinion */
    uint8_t start = buffer_skip_prefix();
    for(uint8_t i = start; i < num_quorum_items; ++i){
        if(quorum_array[i] != NULL && quorum_array[i]->agent_state == my_state){
            ++agreeing;
        }
    }
    return (float)agreeing / (float)(eligible + 1);
}

float compute_r_threshold(float quorum_value){
    if(control_mode == f_static) return clamp01(control_parameter);
    if(quorum_value > 1.0f) return 0.0f;
    switch(control_mode){
        case f_linear:
            return clamp01(quorum_value);
        case f_sigmoid:
        {
            const float num = quorum_value;
            const float den = 1.0f + expf(-10.0*(quorum_value - control_parameter));
            return clamp01(num / den);
        }
        case f_polynomial:
        {
            const float polynomial = (1.0f - control_parameter) * powf(quorum_value,3.0f) + control_parameter;
            return clamp01(polynomial);
        }
        default:
            return clamp01(control_parameter);
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
    /* if the robot arrived to the destination, a new goal is selected */
    if (force || ((abs((int16_t)((gps_position.position_x-goal_position.position_x)*100))*.01<.02) && (abs((int16_t)((gps_position.position_y-goal_position.position_y)*100))*.01<.02))){
        goal_position.position_x = random_in_range(the_arena->tlX,the_arena->brX);
        goal_position.position_y = random_in_range(the_arena->tlY,the_arena->brY);
        expiring_dist = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
        reaching_goal_ticks = expiring_dist * goal_ticks_sec;
    }
    else{
        if(avoid_tmmts==0){
            uint32_t flag = (uint32_t)sqrt(pow((gps_position.position_x-goal_position.position_x)*100,2)+pow((gps_position.position_y-goal_position.position_y)*100,2));
            if(flag >= expiring_dist + 0.01){
                avoid_tmmts=1;
                float angleToGoal = AngleToGoal();
                float p = rand_hard()/255.0;
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
                select_new_point(true);
                set_motion(FORWARD);
            }
            break;
        }

        case MSG_B:
            if(init_received_A){
                if(kb_index == 0){
                    msg_n_hops = (uint8_t)(sa_payload & 0x1F);
                    msg_n_hops_rnd = msg_n_hops;
                    if(!id_aware){
                        msg_n_hops = 0;
                        msg_n_hops_rnd = 0;
                    }
                    init_received_B = true;
                }
                else if(kb_index == 1){
                    control_mode = (uint8_t)((sa_payload >> 14) & 0x03);
                    voting_msgs = (uint8_t)((sa_payload >> 7) & 0x7F);
                    
                    my_state = (uint8_t)(sa_payload & 0x7F);
                    init_control_received = true;
                    update_debug_led();
                }
                else if(kb_index == 2){
                    control_parameter_q = (uint8_t)(sa_payload & 0x7F);
                    control_parameter = control_parameter_q / 127.0f;
                }
            }
            break;
    }
}

void update_messages(const uint8_t Msg_n_hops){
    uint32_t expiring_time = (uint32_t)exponential_distribution(expiring_ticks_quorum);
    uint8_t result = update_q(&quorum_array,&quorum_list,NULL,received_id,received_committed,expiring_time,Msg_n_hops);
    if(result == 2 && broadcasting_flag == 1 && adaptive_comm == 1) buffer_update_rng += 1;
    sort_q(&quorum_array);
    vote_fifo_update(received_id, received_committed);
    if(id_aware && broadcasting_flag == 2){
        if(result == 1) fifo_msg_enqueue(&rebroadcast_fifo, received_id, Msg_n_hops, received_committed);
        else if(result == 2) fifo_msg_move_to_tail(&rebroadcast_fifo, received_id, Msg_n_hops, received_committed);
    }
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
            {
                uint8_t packet_type = (uint8_t)(data[2] >> 6);
                uint8_t packet_data = (uint8_t)(data[2] & 0b00111111);
                if(packet_type == 0){
                    if(the_arena == NULL){
                        build_arena(&the_arena);
                    }
                    update_arena_from_received_bounds();
                    uint32_t msg_timeout = sa_payload;
                    adaptive_comm = (uint8_t)((packet_data >> 5) & 0x01);
                    broadcasting_flag = (uint8_t)(packet_data & 0x1F);
                    if(broadcasting_flag == 0){
                        adaptive_comm = 0;
                    }
                    set_quorum_vars(msg_timeout * TICKS_PER_SEC,5);
                    init_received_A = true;
                }
                else if(packet_type == 2){
                    priority_sampling_k = (uint8_t)(sa_payload & 0x7F);
                    id_aware = (uint8_t)((sa_payload >> 7) & 0x01);
                    if(priority_sampling_k > buffer_length){
                        priority_sampling_k = buffer_length;
                    }
                    if(!id_aware){
                        broadcasting_flag = 0;
                        msg_n_hops = 0;
                        msg_n_hops_rnd = 0;
                        adaptive_comm = 0;
                    }
                    if(broadcasting_flag == 0){
                        adaptive_comm = 0;
                    }
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

void decision(){
    if (kilo_ticks > last_decision_ticks + decision_ticks){
        last_decision_ticks = kilo_ticks;
        quorum_value = compute_quorum_value();
        control_value = compute_r_threshold(quorum_value);
        float p = rand_hard()/255.0;
        if(p < 0.01) my_state = gps_floor_color;
        else{
            p = rand_hard()/255.0;
            if(p < control_value){
                my_state = majority_vote();
            }
            else my_state = gps_floor_color;
        }
        update_debug_led();
    }
}

int majority_vote() {
    if (vote_fifo_count == 0 || voting_msgs == 0) return my_state;
    uint8_t sample_target = voting_msgs;
    if(sample_target > FIFO_BUFFER_SIZE) sample_target = FIFO_BUFFER_SIZE;
    if(vote_fifo_count < sample_target) return my_state;
    uint8_t buffer[6] = {0};
    uint8_t start_offset = (uint8_t)(vote_fifo_count - sample_target);
    uint8_t idx = (uint8_t)((vote_fifo_head + start_offset) % FIFO_BUFFER_SIZE);
    for(uint8_t i = 0; i < sample_target; ++i){
        uint8_t state = vote_fifo_states[idx];
        idx = (uint8_t)((idx + 1) % FIFO_BUFFER_SIZE);
        if(state < sizeof(buffer)){
            buffer[state]++;
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
            float p = rand_hard() / 255.0;
            if (p < 0.5) selection = i;
        }
    }
    return (max == 0) ? my_state : selection;
}

void setup(){
    snprintf(log_title,30,"quorum_log_agent#%d.tsv",kilo_uid);
    set_color(RGB(0,0,0));
    set_motors(0,0);
    my_state = 255;
    my_message.type = KILO_BROADCAST_MSG;
    my_message.crc = message_crc(&my_message);
    init_array_qrm(&quorum_array, FIFO_BUFFER_SIZE);
    id_aware = 1;
    priority_sampling_k = 0;

    uint8_t seed = rand_hard();
    rand_seed(seed);
    seed = rand_hard();
    srand(seed);

    fp = fopen(log_title,"a");
    set_motion(STOP);
    fifo_msg_init(&rebroadcast_fifo);
    vote_fifo_head = 0;
    vote_fifo_tail = 0;
    vote_fifo_count = 0;
}

void loop(){
    delta_elapsed = kilo_ticks - ticks_elapsed;
    ticks_elapsed = kilo_ticks;
    decrement_quorum_counter(&quorum_array, delta_elapsed);
    erase_expired_items(&quorum_array,&quorum_list);
    if(my_state != 255){
        random_way_point_model();
        decision();
        talk();
    }
    fprintf(fp,"%d\t %d\t %f\t %f\n",my_state,true_quorum_items,quorum_value,control_value);
}

void deallocate_memory(){
    fclose(fp);
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
