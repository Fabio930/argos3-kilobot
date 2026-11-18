/* Kilobot control software for the simple ALF experment : bestN
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
#include "bestN.h"

/* ticks elapsed before the CONFIG message arrived: the per-tick logs of the
 * dynamic and confined variants start from tick 0, so these lines are written
 * (with the default values) once the variant is known */
uint32_t pending_log_lines = 0;
uint16_t msg_expiring_sec = 0;

/* optional position trace, used by the minitests: set BESTN_POSITION_LOG=1 */
FILE *pos_fp = NULL;

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

/*-------------------------------------------------------------------*/
/*                      Broadcasting functions                       */
/*-------------------------------------------------------------------*/

void talk(){
    if (!sending_msg && kilo_ticks > last_broadcast_ticks + broadcasting_ticks){
        last_broadcast_ticks = kilo_ticks;
        if(anonymous_comm) talk_anonymous();
        else talk_id_aware();
        selected_msg_indx = QUORUM_NOT_FOUND;
        sending_msg = true;
    }
}

void talk_id_aware(){
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
                        if(selected_msg_indx != QUORUM_NOT_FOUND) rnd_rebroadcast();
                        else broadcast();
                        break;
                    default:
                        if(selected_msg_indx != QUORUM_NOT_FOUND && quorum_buf[selected_msg_indx].delivered < msg_n_hops) rnd_rebroadcast();
                        else broadcast();
                        break;
                }
            }
            else broadcast();
            break;
        case 2:
            p = random_in_range(0,1);
            if(p<0.5){
                uint8_t agent_id;
                if(fifo_msg_peek(&rebroadcast_fifo, &agent_id)) {
                    uint8_t fifo_hops = 0;
                    uint8_t agent_state = 0;
                    uint8_t agent_idx = 0xFF;
                    for(uint8_t i=0, idx=rebroadcast_fifo.head; i<rebroadcast_fifo.count; ++i, idx=(idx+1)%FIFO_MSG_SIZE) {
                        if(rebroadcast_fifo.buffer[idx].agent_id == agent_id) {
                            fifo_hops = rebroadcast_fifo.buffer[idx].msg_n_hops;
                            agent_state = rebroadcast_fifo.buffer[idx].agent_state;
                            agent_idx = idx;
                            break;
                        }
                    }
                    if(agent_idx != 0xFF) {
                        fifo_rebroadcast(agent_id, agent_state, fifo_hops, agent_idx);
                        fifo_msg_dequeue(&rebroadcast_fifo);
                    } else broadcast();
                } else broadcast();
            }
            else broadcast();
            break;
        default:
            broadcast();
            break;
    }
}

void talk_anonymous(){
    switch(broadcasting_flag){
        case 0:
            broadcast();
            break;
        case 1:
            selected_msg_indx = select_a_random_message();
            if(selected_msg_indx != QUORUM_NOT_FOUND && quorum_buf[selected_msg_indx].delivered == 0) anonymous_rebroadcast();
            else broadcast();
            break;
        case 2:
            selected_msg_indx = quorum_select_undelivered();
            if(selected_msg_indx != QUORUM_NOT_FOUND) anonymous_rebroadcast();
            else broadcast();
            break;
        default:
            broadcast();
            break;
    }
}

void broadcast(){
    // frequency log
    num_own_info += 1;
    // message: a robot's own state always travels with 0 hops
    sa_type = 0;
    sa_id = kilo_uid;
    sa_payload = my_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

void anonymous_rebroadcast(){
    // frequency log
    num_other_info += 1;
    // message
    sa_type = 0;
    sa_id = quorum_buf[selected_msg_indx].agent_id;
    sa_payload = quorum_buf[selected_msg_indx].agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    quorum_buf[selected_msg_indx].delivered = 1;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

static uint8_t sat_inc_u8(const uint8_t value){
    return (value == UINT8_MAX) ? UINT8_MAX : (uint8_t)(value + 1);
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

uint8_t fifo_msg_move_to_tail(fifo_msg_buffer_t* fifo, uint8_t agent_id, uint8_t msg_hops, uint8_t agent_state) {
    if (fifo->count == 0) return 0;
    uint8_t idx = fifo->head;
    uint8_t found = 0;
    for (uint8_t i = 0; i < fifo->count; ++i) {
        if (fifo->buffer[idx].agent_id == agent_id) {
            fifo->buffer[idx].msg_n_hops = msg_hops;
            fifo->buffer[idx].agent_state = agent_state;
            fifo_msg_remove(fifo, agent_id);
            found = 1;
            break;
        }
        idx = (idx + 1) % FIFO_MSG_SIZE;
    }
    if (!found) return 0;
    return fifo_msg_enqueue(fifo, agent_id, msg_hops, agent_state);
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

void rnd_rebroadcast(){
    // frequency log
    num_other_info += 1;
    // message
    quorum_a *item = &quorum_buf[selected_msg_indx];
    sa_type = sat_inc_u8(item->msg_n_hops);
    sa_id = item->agent_id;
    sa_payload = item->agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    item->delivered = sat_inc_u8(item->delivered);
    item->msg_n_hops = sa_type;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;
}

uint8_t fifo_rebroadcast(uint8_t agent_id, uint8_t agent_state, uint8_t msg_hops, uint8_t agent_idx){
    // frequency log
    num_other_info += 1;
    // message
    sa_type = sat_inc_u8(msg_hops);
    sa_id = agent_id;
    sa_payload = agent_state;
    for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
    my_message.data[0] = sa_id;
    my_message.data[1] = sa_type;
    my_message.data[2] = sa_payload;

    uint16_t q_idx = quorum_find_by_id(agent_id);
    if(q_idx != QUORUM_NOT_FOUND){
        quorum_buf[q_idx].delivered = sat_inc_u8(quorum_buf[q_idx].delivered);
        quorum_buf[q_idx].msg_n_hops = sa_type;
    }

    rebroadcast_fifo.buffer[agent_idx].msg_n_hops = sa_type;
    return 1;
}

uint16_t select_a_random_message(){
    if(num_quorum_items>0) return rand_soft()%num_quorum_items;
    return QUORUM_NOT_FOUND;
}

float random_in_range(float min, float max){
    float r = (float)rand_hard() / 255.0;
    return min + (r*(max-min));
}

/*-------------------------------------------------------------------*/
/*                      Random way point model                       */
/*-------------------------------------------------------------------*/

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
    if(experiment_started){
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

/*-------------------------------------------------------------------*/
/*                   Environment set up                              */
/*-------------------------------------------------------------------*/

void set_state(uint8_t state){
    if(state == 1){
        my_state = committed;
        led = RGB(0,0,3);
    }
    else{
        my_state = uncommitted;
        led = RGB(0,0,0);
    }
}

void set_waypoint_area(){
    if(the_arena == NULL) complete_tree(&the_arena);
    float min_x = ARENA_BORDER_M;
    float max_x = arena_width - ARENA_BORDER_M;
    float min_y = ARENA_BORDER_M;
    float max_y = arena_height - ARENA_BORDER_M;
    if(confined_env && arena_midline >= 0){
        /* committed robots on the left of the midline, uncommitted on the right */
        if(my_state == committed) max_x = arena_midline;
        else min_x = arena_midline;
    }
    set_vertices(&the_arena,min_x,min_y,max_x,max_y);
}

bool init_completed(){
    return init_received_config && init_received_state && init_received_arena && (!dynamic_env || init_received_variation);
}

/*-------------------------------------------------------------------*/
/*                  Dynamic environment                              */
/*-------------------------------------------------------------------*/

uint16_t variation_rng_next(){
    if(variation_rng_state == 0){
        variation_rng_state = (uint32_t)variation_seed + 1;
    }
    variation_rng_state ^= variation_rng_state << 13;
    variation_rng_state ^= variation_rng_state >> 17;
    variation_rng_state ^= variation_rng_state << 5;
    return (uint16_t)(variation_rng_state & 0x0000FFFF);
}

void build_state_change_schedule(){
    next_state_change = 0;
    if(variation_num_flips > MAX_STATE_CHANGES) variation_num_flips = MAX_STATE_CHANGES;
    if(variation_num_flips == 0) return;
    variation_rng_state = variation_seed;

    const uint32_t start_tick_kilo = (uint32_t)variation_start_sec * TICKS_PER_SEC;

    if(variation_end_sec == 0 || variation_end_sec <= variation_start_sec){
        for(uint8_t i = 0; i < variation_num_flips; ++i) state_change_ticks[i] = start_tick_kilo;
        return;
    }

    uint32_t range = (uint32_t)variation_end_sec - variation_start_sec + 1;
    for(uint8_t i = 0; i < variation_num_flips; ++i){
        uint32_t random_sec = variation_start_sec + (variation_rng_next() % range);
        state_change_ticks[i] = random_sec * TICKS_PER_SEC;
    }

    for(uint8_t i = 0; i < variation_num_flips; ++i){
        for(uint8_t j = i + 1; j < variation_num_flips; ++j){
            if(state_change_ticks[j] < state_change_ticks[i]){
                uint32_t tmp = state_change_ticks[i];
                state_change_ticks[i] = state_change_ticks[j];
                state_change_ticks[j] = tmp;
            }
        }
    }
}

void apply_state_changes(){
    if(!experiment_started) return;
    while(next_state_change < variation_num_flips && kilo_ticks >= state_change_ticks[next_state_change]){
        set_state(my_state == committed ? 0 : 1);
        next_state_change += 1;
    }
}

/*-------------------------------------------------------------------*/
/*                   Parse ALF and kilobot messages                  */
/*-------------------------------------------------------------------*/

static uint16_t read_u16(const uint8_t *data){
    return ((uint16_t)data[0] << 8) | data[1];
}

void log_step();

void parse_alf_message(uint8_t data[9]){
    if(data[0] != (uint8_t)kilo_uid) return;
    switch(data[1]){
        case ALF_MSG_CONFIG:
            if(!init_received_config){
                anonymous_comm = (data[2] & CFG_FLAG_ANONYMOUS) ? true : false;
                dynamic_env = (data[2] & CFG_FLAG_DYNAMIC) ? true : false;
                confined_env = (data[2] & CFG_FLAG_CONFINED) ? true : false;
                broadcasting_flag = data[3];
                msg_expiring_sec = read_u16(&data[4]);
                msg_n_hops = data[6];
                k_sampling = anonymous_comm ? data[8] : 0;
                if(anonymous_comm) quorum_init(data[7], (uint32_t)msg_expiring_sec * TICKS_PER_SEC, 1);
                else quorum_init(QUORUM_CAPACITY, (uint32_t)msg_expiring_sec * TICKS_PER_SEC, 0);
                led = RGB(3,3,0);
                set_color(led);
                init_received_config = true;
                if(dynamic_env || confined_env){
                    for(uint32_t i = 0; i < pending_log_lines; i++) log_step();
                }
                pending_log_lines = 0;
            }
            break;
        case ALF_MSG_STATE:
            if(init_received_config && !init_received_state){
                set_state(data[2]);
                set_quorum_threshold(data[3]);
                init_received_state = true;
            }
            break;
        case ALF_MSG_ARENA:
            if(init_received_state && !init_received_arena){
                arena_width = read_u16(&data[2]) * 0.01;
                arena_height = read_u16(&data[4]) * 0.01;
                uint16_t midline = read_u16(&data[6]);
                arena_midline = (midline == ARENA_NO_MIDLINE) ? -1 : midline * 0.01;
                set_waypoint_area();
                if(!anonymous_comm && msg_expiring_sec == 0){
                    /* ID-aware default: as many seconds as the diagonal of the walkable area in cm */
                    float w = (arena_width - 2*ARENA_BORDER_M) * 100;
                    float h = (arena_height - 2*ARENA_BORDER_M) * 100;
                    expiring_ticks_quorum = (uint32_t)sqrt(w*w + h*h) * TICKS_PER_SEC;
                }
                init_received_arena = true;
            }
            break;
        case ALF_MSG_VARIATION:
            if(init_received_arena && dynamic_env && !init_received_variation){
                variation_start_sec = read_u16(&data[2]);
                variation_end_sec = read_u16(&data[4]);
                variation_seed = read_u16(&data[6]);
                variation_num_flips = data[8];
                build_state_change_schedule();
                init_received_variation = true;
            }
            break;
        case ALF_MSG_GPS:
            gps_position.position_x = read_u16(&data[2]) * GPS_UNIT_M;
            gps_position.position_y = read_u16(&data[4]) * GPS_UNIT_M;
            gps_angle = data[6] * GPS_ANGLE_UNIT_DEG;
            if(!experiment_started && init_completed()){
                experiment_started = true;
                select_new_point(true);
                set_motion(FORWARD);
                set_color(led);
            }
            break;
    }
}

void update_messages(const uint8_t Msg_n_hops){
    if(anonymous_comm){
        uint32_t expiring_time = 0;
        if(expiring_ticks_quorum > 0) expiring_time = (uint32_t)exponential_distribution(expiring_ticks_quorum);
        quorum_push_anonymous(received_id,received_committed,expiring_time);
    }
    else{
        uint32_t expiring_time = (uint32_t)exponential_distribution(expiring_ticks_quorum);
        uint8_t result = quorum_update_by_id(received_id,received_committed,expiring_time,Msg_n_hops);
        if(broadcasting_flag == 2) {
            if(result == 1) fifo_msg_enqueue(&rebroadcast_fifo, received_id, Msg_n_hops, received_committed);
            else if(result == 2) fifo_msg_move_to_tail(&rebroadcast_fifo, received_id, Msg_n_hops, received_committed);
        }
    }
    quorum_sort();
}

void parse_kilo_message(uint8_t data[9]){
    sa_id = data[0];
    if(init_received_config && sa_id!=(uint8_t)kilo_uid){
        sa_type = data[1];
        sa_payload = data[2];
        received_id = sa_id;
        received_committed = (uint8_t)sa_payload;
        update_messages(sa_type);
    }
    else sa_id = 0;
}

void message_rx(message_t *msg, distance_measurement_t *d){
    sa_id = 0;
    sa_type = 0;
    sa_payload = 0;
    uint8_t id1;
    switch (msg->type){
        case ARK_BROADCAST_MSG:
        case ARK_INDIVIDUAL_MSG:
            parse_alf_message(msg->data);
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

/*-------------------------------------------------------------------*/
/*                          Logging                                  */
/*-------------------------------------------------------------------*/

/* static variants: one line per tick with the IDs in the buffer (array
 * order), nothing when the buffer is empty */
void log_buffer_ids(){
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if(i == num_quorum_items-1) fprintf(fp,"%d\n",quorum_buf[i].agent_id);
        else fprintf(fp,"%d,",quorum_buf[i].agent_id);
    }
}

/* dynamic: state, quorum reached, distinct IDs in the buffer
 * confined: the same plus the robot position */
void log_step(){
    if(confined_env) fprintf(fp,"%d\t%d\t%d\t%f\t%f\n",my_state,quorum_reached,quorum_distinct_ids(),gps_position.position_x,gps_position.position_y);
    else fprintf(fp,"%d\t%d\t%d\n",my_state,quorum_reached,quorum_distinct_ids());
}

/*-------------------------------------------------------------------*/
/*                          Init / loop                              */
/*-------------------------------------------------------------------*/

void setup(){
    snprintf(log_title,30,"quorum_log_agent#%d.tsv",kilo_uid);
    /* Init LED and motors */
    set_color(RGB(0,0,0));
    set_motors(0,0);
    /* Init state, message type and control parameters*/
    my_message.type = KILO_BROADCAST_MSG;
    my_message.crc = message_crc(&my_message);
    quorum_init(QUORUM_CAPACITY, expiring_ticks_quorum, 0);
    next_state_change = 0;
    variation_num_flips = 0;
    for(uint8_t i = 0; i < MAX_STATE_CHANGES; ++i) state_change_ticks[i] = 0;

    /* Init random seed */
    uint8_t seed = rand_hard();
    rand_seed(seed);
    seed = rand_hard();
    srand(seed);

    fp = fopen(log_title,"a");
    if(getenv("BESTN_POSITION_LOG") != NULL){
        char pos_title[40];
        snprintf(pos_title,40,"position_log_agent#%d.tsv",kilo_uid);
        pos_fp = fopen(pos_title,"w");
    }
    /* Init motion variables */
    set_motion(STOP);

    // Inizializzazione della nuova coda strutturata
    fifo_msg_init(&rebroadcast_fifo);
}

void loop(){
    delta_elapsed = kilo_ticks - ticks_elapsed;
    ticks_elapsed = kilo_ticks;
    bool per_tick_log = dynamic_env || confined_env;
    if(init_received_config && !per_tick_log) log_buffer_ids();
    quorum_decrement(delta_elapsed);
    if(!anonymous_comm) quorum_erase_expired();
    random_way_point_model();
    if(dynamic_env) apply_state_changes();
    quorum_check(my_state, k_sampling);
    if(experiment_started) talk();
    if(!init_received_config) pending_log_lines++;
    else if(per_tick_log) log_step();
    if(pos_fp != NULL && experiment_started) fprintf(pos_fp,"%d\t%d\t%f\t%f\t%f\t%f\t%f\t%f\n",my_state,num_quorum_items,gps_position.position_x,gps_position.position_y,the_arena->tlX,the_arena->brX,the_arena->tlY,the_arena->brY);
    if(experiment_started){
        if(quorum_reached==1 && my_state==committed) set_color(RGB(3,0,0));
        else if(quorum_reached==1 && my_state==uncommitted) set_color(RGB(3,3,0));
        else set_color(led);
    }
}

void deallocate_memory(){
    fclose(fp);
    if(pos_fp != NULL) fclose(pos_fp);
    destroy_tree(&the_arena);
    quorum_clear();
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
