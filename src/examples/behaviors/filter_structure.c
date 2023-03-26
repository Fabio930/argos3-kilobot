#include "filter_structure.h"

void set_filter(filter_a *myfilter,const float Gain,const uint8_t Im_leaf){
    myfilter->utility=-1;
    myfilter->distance=-1;
    myfilter->im_leaf=Im_leaf;
    myfilter->count_1=0;
    myfilter->count_2=0;
    myfilter->data_switch=0;
    myfilter->gain=Gain;
    myfilter->data_1=(float*)malloc(2*sizeof(float));
    myfilter->data_2=(float*)malloc(2*sizeof(float));
}

void update_filter(filter_a *myfilter,const float Sensed_utility, const float Ref_distance){
    if(myfilter->utility==-1 && myfilter->distance==-1){
        myfilter->utility = Sensed_utility;
        myfilter->distance = 1;
    }
    else myfilter->utility = (myfilter->utility*myfilter->gain) + (1-myfilter->gain)*Sensed_utility;
    switch (myfilter->im_leaf){
    case 1:
        switch (myfilter->data_switch){
        case 1:
            myfilter->count_1++;
            myfilter->data_1[0] = myfilter->data_1[0] + (Sensed_utility-myfilter->data_1[0])/myfilter->count_1;
            if(myfilter->count_1 > 1) myfilter->data_1[1] = myfilter->data_1[1]*((myfilter->count_1-2)/(myfilter->count_1-1)) + pow(Sensed_utility-myfilter->data_1[0],2)/myfilter->count_1;
            myfilter->data_switch = 0;
            break;
        default:
            myfilter->count_2++;
            myfilter->data_2[0] = myfilter->data_2[0] + (Sensed_utility-myfilter->data_2[0])/myfilter->count_2;
            if(myfilter->count_2 > 1) myfilter->data_2[1] = myfilter->data_2[1]*((myfilter->count_2-2)/(myfilter->count_2-1)) + pow(Sensed_utility-myfilter->data_2[0],2)/myfilter->count_2;
            myfilter->data_switch = 1;
            break;
        }
        break;
    default:
        myfilter->distance=Ref_distance;
        break;
    }
}

void destroy_filter(filter_a *myfilter){
    free(myfilter->data_1);
    free(myfilter->data_2);
}

float get_utility(filter_a *myfilter){
    return myfilter->utility;
}