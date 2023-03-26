#include "filter_structure.c"
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

typedef enum{
    OTHER=0,
    THISNODE=1,
    PARENTNODE=2,
    SUBTREE=3,
    SIBLINGTREE=4
} message_source;

uint8_t num_nodes=0;
uint8_t branches=2;
uint8_t num_leafs=0;

typedef struct tree_structure{
    uint8_t id, depth;
    float gt_utility;
    struct tree_structure *parent;
    struct tree_structure *children;
    float tlX,tlY,brX,brY;
    filter_a *node_filter;
}tree_a;

void complete_tree(tree_a **Array[],tree_a **Mytree,const uint8_t Depth,const uint8_t Branches,uint8_t *Leafs_id, const uint8_t Best_leaf_id,const float Max_utility, const float K);

void loop_complete_tree(tree_a **Mytree,const uint8_t Depth, uint8_t *Leafs_id, const uint8_t Best_leaf_id,const float Max_utility, const float K);

void sort_t(tree_a **Array[]);

tree_a* get_node_from_3(tree_a **Mytree,const uint8_t Node_id);

void fill_tree_array(tree_a **Array[],tree_a **Mytree);

tree_a* get_node(tree_a **Array[],const uint8_t Node_id);

uint8_t get_nearest_node(tree_a **Array[],const uint8_t MYnode,const uint8_t MSGnode);

uint8_t msg_received_from(tree_a **Array[],const uint8_t Mynode_id,const uint8_t Messagednode_id);

void complete_update(tree_a **node);

void bottom_up_utility_update(tree_a **Array[],const uint8_t Leaf_id,float Sensed_utility);

void loop_set_vertices(tree_a **Mytree,const uint8_t Index,const uint8_t Ref);

void set_vertices(tree_a **Mytree,const float BrX,const float BrY);

void destroy_tree(tree_a **Array[],tree_a **Mytree);
