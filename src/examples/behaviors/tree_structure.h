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

int num_nodes=0;
int branches=2;
unsigned int num_leafs=0;

typedef struct tree_structure{
    unsigned int id, depth;
    float gt_utility;
    struct tree_structure *parent;
    struct tree_structure *children;
    float tlX,tlY,brX,brY;
    filter_a *node_filter;
}tree_a;

void loop_complete_tree(tree_a **Mytree,const int Depth,unsigned int *Leafs_id, const unsigned int Best_leaf_id,const float Max_utility, const float K);

void sort_t(tree_a **Array[]);

tree_a* get_node_from_3(tree_a **Mytree,const int Node_id);

void fill_tree_array(tree_a **Array[],tree_a **Mytree);

void complete_tree(tree_a **Array[],tree_a **Mytree,const int Depth,const int Branches,unsigned int *Leafs_id, const unsigned int Best_leaf_id,const float Max_utility, const float K);

tree_a* get_node(tree_a **Array[],const int Node_id);

int get_nearest_node(tree_a **Array[],const int MYnode,const int MSGnode);

int msg_received_from(tree_a **Array[],const int Mynode_id,const int Messagednode_id);

void complete_update(tree_a **node);

void bottom_up_utility_update(tree_a **Array[],const int Leaf_id,float Sensed_utility);

void loop_set_vertices(tree_a **Mytree,const int Index,const int Ref);

void set_vertices(tree_a **Mytree,const float BrX,const float BrY);

void destroy_tree(tree_a **Array[],tree_a **Mytree);
