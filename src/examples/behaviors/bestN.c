/* Kilobot control software for the simple ALF experment : clustering
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
#include "bestN.h"

static uint32_t next_xorshift32(uint32_t *state){
    uint32_t x = *state;
    x ^= (x << 13);
    x ^= (x >> 17);
    x ^= (x << 5);
    *state = x;
    return x;
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
                selected_msg_indx = select_a_random_message();
                p = random_in_range(0,1);
                if(p<0.5){
                    switch(msg_n_hops){
                        case 0:
                            if(selected_msg_indx != 0b1111111111111111) rebroadcast();
                            else broadcast();
                            break;
                        default:
                            if(selected_msg_indx != 0b1111111111111111 && quorum_array[selected_msg_indx]->msg_n_hops < msg_n_hops){
                                quorum_array[selected_msg_indx]->msg_n_hops += 1;
                                rebroadcast();
                            }
                            else broadcast();
                            break;
                    }
                }
                else broadcast();
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

void broadcast(){
    // message
    sa_type = 0;
    if(broadcasting_flag==2 && msg_n_hops > 0) sa_type = msg_n_hops;
    sa_id = kilo_uid;
    sa_payload = my_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

void rebroadcast(){
    // message
    sa_type = 0;
    if(broadcasting_flag==2 && msg_n_hops > 0) sa_type = quorum_array[selected_msg_indx]->msg_n_hops - 1;
    sa_id = quorum_array[selected_msg_indx]->agent_id;
    sa_payload = quorum_array[selected_msg_indx]->agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    quorum_array[selected_msg_indx]->delivered = quorum_array[selected_msg_indx]->delivered + 1;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

float random_in_range(float min, float max){
    float r = (float)rand_hard() / 255.0;
    return min + (r*(max-min));
}

uint8_t led_from_color_id(uint8_t color_id){
    uint8_t id = color_id;
    if(id > 0){
        id = (uint8_t)(((id - 1) % 6) + 1);
    }
    switch(id){
        case 1: return RGB(3,0,0);
        case 2: return RGB(0,3,0);
        case 3: return RGB(0,0,3);
        case 4: return RGB(3,3,0);
        case 5: return RGB(0,3,3);
        case 6: return RGB(3,0,3);
        default: return RGB(0,0,0);
    }
}

void setup_floor_colors(){
    if(grid_rows == 0 || grid_cols == 0){
        return;
    }
    uint16_t total_cells = (uint16_t)(grid_rows * grid_cols);
    if(total_cells == 0){
        return;
    }
    if(floor_colors != NULL){
        free(floor_colors);
        floor_colors = NULL;
    }
    floor_colors = (uint8_t*)malloc(total_cells * sizeof(uint8_t));
    if(floor_colors == NULL){
        return;
    }

    if(map_options == 0){
        map_options = 1;
    }
    for(uint16_t i = 0; i < total_cells; ++i){
        floor_colors[i] = 1;
    }

    uint16_t worse_cells = (uint16_t)(((uint32_t)eta_q * total_cells + 63) / 127);
    if(worse_cells == 0 || map_options == 1){
        return;
    }

    uint8_t worse_options = (uint8_t)(map_options - 1);
    uint16_t base_count = (uint16_t)(worse_cells / worse_options);
    uint16_t remainder = (uint16_t)(worse_cells % worse_options);
    uint16_t cursor = 0;
    for(uint8_t opt = 0; opt < worse_options; ++opt){
        uint16_t cells_for_option = (uint16_t)(base_count + (opt < remainder ? 1 : 0));
        uint8_t color_id = (uint8_t)(opt + 2);
        for(uint16_t j = 0; j < cells_for_option && cursor < worse_cells; ++j, ++cursor){
            floor_colors[cursor] = color_id;
        }
    }

    uint32_t state = map_seed;
    if(state == 0){
        state = 1;
    }
    for(uint16_t i = (uint16_t)(total_cells - 1); i > 0; --i){
        uint16_t j = (uint16_t)(next_xorshift32(&state) % (i + 1));
        uint8_t tmp = floor_colors[i];
        floor_colors[i] = floor_colors[j];
        floor_colors[j] = tmp;
    }
}

uint8_t floor_color_id_at_position(float x, float y){
    if(floor_colors == NULL || grid_rows == 0 || grid_cols == 0){
        return 0;
    }
    float x_min = gps_min_x_q * 0.01f;
    float y_min = gps_min_y_q * 0.01f;
    float x_max = gps_max_x_q * 0.01f;
    float y_max = gps_max_y_q * 0.01f;
    if(x_max <= x_min || y_max <= y_min){
        x_min = 0.05f;
        y_min = 0.05f;
        x_max = 1.05f;
        y_max = 1.05f;
    }
    const float cell_w = (x_max - x_min) / grid_cols;
    const float cell_h = (y_max - y_min) / grid_rows;
    if(cell_w <= 0.0f || cell_h <= 0.0f){
        return 0;
    }

    /* Outside the colored inner area: this is the black safety border. */
    if(x <= x_min || x >= x_max || y <= y_min || y >= y_max){
        return 0;
    }

    int16_t col = (int16_t)((x - x_min) / cell_w);
    int16_t row = (int16_t)((y - y_min) / cell_h);
    if(col < 0) col = 0;
    if(row < 0) row = 0;
    if(col >= grid_cols) col = (int16_t)(grid_cols - 1);
    if(row >= grid_rows) row = (int16_t)(grid_rows - 1);

    return floor_colors[(uint16_t)(row * grid_cols + col)];
}

void update_debug_led(){
    if(!init_received_C){
        return;
    }
    uint8_t color_id = floor_color_id_at_position(gps_position.position_x, gps_position.position_y);
    led = led_from_color_id(color_id);
    set_color(led);
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
                update_debug_led();
            }
            break;
        case MSG_B:
            if(init_received_A){
                msg_n_hops = (uint8_t)(sa_payload >> 8);
                uint8_t state = (uint8_t)sa_payload;
                switch (state){
                    case 0:
                        my_state = uncommitted;
                        break;
                    
                    case 1:
                        my_state = committed;
                        break;
                }
                init_received_B = true;
            }
            break;
    }
}

void update_messages(const uint8_t Msg_n_hops){
    uint32_t expiring_time = (uint32_t)exponential_distribution(expiring_ticks_quorum);
    uint8_t result = update_q(&quorum_array,&quorum_list,NULL,received_id,received_committed,expiring_time,Msg_n_hops);
    sort_q(&quorum_array);
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
                        complete_tree(&the_arena);
                        set_vertices(&the_arena,(ARENA_X*.1),(ARENA_Y*.1));
                    }
                    uint32_t msg_timeout = sa_payload;
                    if(msg_timeout == 0){
                        msg_timeout = (uint32_t)sqrt(pow((ARENA_X)*10,2)+pow((ARENA_Y)*10,2));
                    }
                    broadcasting_flag = packet_data;
                    set_quorum_vars(msg_timeout * TICKS_PER_SEC,0,(uint8_t)(msg_timeout & 0x00FF));
                    init_struct_received = true;
                    init_received_A = true;
                }
                else if(packet_type == 1){
                    grid_rows = (uint8_t)((sa_payload >> 7) & 0x7F);
                    grid_cols = (uint8_t)(sa_payload & 0x7F);
                    seed_hi = packet_data;
                    init_grid_received = (grid_rows > 0 && grid_cols > 0);
                }
                else if(packet_type == 2){
                    eta_q = (uint8_t)((sa_payload >> 7) & 0x7F);
                    map_options = (uint8_t)(sa_payload & 0x7F);
                    if(map_options == 0){
                        map_options = 1;
                    }
                    seed_lo = packet_data;
                    map_seed = (uint16_t)((seed_hi << 6) | seed_lo);
                    if(map_seed == 0){
                        map_seed = 1;
                    }
                    init_map_received = true;
                }
                else if(packet_type == 3){
                    uint8_t is_y_bounds = (uint8_t)(packet_data & 0x01);
                    uint8_t gps_min_q = (uint8_t)((sa_payload >> 7) & 0x7F);
                    uint8_t gps_max_q = (uint8_t)(sa_payload & 0x7F);
                    if(gps_max_q <= gps_min_q){
                        gps_min_q = 5;
                        gps_max_q = 105;
                    }
                    if(is_y_bounds){
                        gps_min_y_q = gps_min_q;
                        gps_max_y_q = gps_max_q;
                        init_bounds_y_received = true;
                    }
                    else{
                        gps_min_x_q = gps_min_q;
                        gps_max_x_q = gps_max_q;
                        init_bounds_x_received = true;
                    }
                }

                if(init_struct_received &&
                   init_grid_received &&
                   init_map_received &&
                   init_bounds_x_received &&
                   init_bounds_y_received &&
                   floor_colors == NULL){
                    setup_floor_colors();
                    led = RGB(3,3,0);
                    set_color(led);
                }
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
        update_debug_led();
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
    delta_elapsed = kilo_ticks - ticks_elapsed;
    ticks_elapsed = kilo_ticks;
    fp = fopen(log_title,"a");
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if(i == num_quorum_items-1) fprintf(fp,"%d\n",quorum_array[i]->agent_id);
        else fprintf(fp,"%d,",quorum_array[i]->agent_id);
    }
    fclose(fp);
    decrement_quorum_counter(&quorum_array, delta_elapsed);
    erase_expired_items(&quorum_array,&quorum_list);
    random_way_point_model();
    if(init_received_C) talk();
}

void deallocate_memory(){
    destroy_tree(&the_arena);
    if(floor_colors != NULL){
        free(floor_colors);
        floor_colors = NULL;
    }
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
