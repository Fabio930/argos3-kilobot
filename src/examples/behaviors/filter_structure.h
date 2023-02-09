
#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
typedef struct filter_structure{
    float utility, distance;
    int count_1, count_2, data_switch, im_leaf;
    float *data_1, *data_2, gain;
}filter_a;

void set_filter(filter_a *myfilter,const float Gain,const int Im_leaf);

void update_filter(filter_a *myfilter,const float Sensed_utility, const float Ref_distance);

void destroy_filter(filter_a *myfilter);

float get_utility(filter_a *myfilter);

