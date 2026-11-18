/* Kilobot control software for the simple ALF experment : bestN
 * author: Fabio Oddi (Università la Sapienza di Roma) oddi@diag.uniroma1.it
 */
#include "bestN.h"

/* ticks elapsed before the CONFIG message arrived: the per-tick logs of every
 * variant start from tick 0, so these lines are written (with the default
 * values, an empty buffer for the static variants) once the variant is known */
uint32_t pending_log_lines = 0;

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
        for (uint8_t i = 0; i < 9; ++i) my_message.data[i]=0;
        comm_talk((uint8_t)kilo_uid, my_state, my_message.data);
        sending_msg = true;
    }
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
                comm_configure(anonymous_comm, data[3], read_u16(&data[4]), data[6],
                               (data[2] & CFG_FLAG_HOP_COUNT) ? 1 : 0, data[7], data[8], TICKS_PER_SEC);
                led = RGB(3,3,0);
                set_color(led);
                init_received_config = true;
                for(uint32_t i = 0; i < pending_log_lines; i++){
                    if(dynamic_env || confined_env) log_step();
                    else fputc('\n',fp);
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

void parse_kilo_message(uint8_t data[9]){
    sa_id = data[0];
    if(init_received_config && sa_id!=(uint8_t)kilo_uid){
        sa_type = data[1];
        sa_payload = data[2];
        comm_receive(sa_id, (uint8_t)sa_payload, sa_type);
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
 * order), an empty line when the buffer is empty so that line i is always tick i */
void log_buffer_ids(){
    for (uint8_t i = 0; i < num_quorum_items; i++){
        if(i > 0) fputc(',',fp);
        fprintf(fp,"%d",quorum_buf[i].agent_id);
    }
    fputc('\n',fp);
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
    comm_configure(0, 0, 0, 0, 0, 0, 0, TICKS_PER_SEC);
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

}

void loop(){
    delta_elapsed = kilo_ticks - ticks_elapsed;
    ticks_elapsed = kilo_ticks;
    bool per_tick_log = dynamic_env || confined_env;
    if(init_received_config && !per_tick_log) log_buffer_ids();
    comm_tick(delta_elapsed);
    random_way_point_model();
    if(dynamic_env) apply_state_changes();
    comm_quorum(my_state);
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
