#include "tree_structure.h"

void loop_complete_tree(tree_a **Mytree,const uint8_t Depth,uint8_t *Leafs_id, const uint8_t Best_leaf_id,const float Max_utility, const float K){
    if(Depth>=0){
        (*Mytree)->children = (tree_a*)malloc(branches*sizeof(tree_a));
        tree_a *c = (*Mytree)->children;
        for(uint8_t i=0;i<branches;i++){
            (c+i)->id=num_nodes++;
            (c+i)->parent=*Mytree;
            (c+i)->children=NULL;
            (c+i)->tlX=0;
            (c+i)->tlY=0;
            (c+i)->brX=0;
            (c+i)->brY=0;
            (c+i)->depth=(*Mytree)->depth + 1;
            (c+i)->node_filter=(filter_a*)malloc(sizeof(filter_a));
            if(Depth > 0) set_filter((c+i)->node_filter,0.75,0);
            else{
                *(Leafs_id + num_leafs) = (c+i)->id;
                num_leafs++;
                set_filter((c+i)->node_filter,0.75,1);
                if((c+i)->id==Best_leaf_id) (c+i)->gt_utility=Max_utility;
                else (c+i)->gt_utility=Max_utility*K;
            }
            tree_a *cc= (c+i);
            if(Depth > 0) loop_complete_tree(&cc,Depth-1,Leafs_id,Best_leaf_id,Max_utility,K);
        }
    }
}

void sort_t(tree_a **Array[]){
    for (uint8_t i = 0; i < num_nodes-1; i++){
        for (uint8_t j = i+1; j < num_nodes; j++){
            if((*Array)[i]->id > (*Array)[j]->id){
                tree_a *flag = (*Array)[i];
                (*Array)[i] = (*Array)[j];
                (*Array)[j] = flag;
            }
        }
    }
}

tree_a* get_node_from_3(tree_a **Mytree,const uint8_t Node_id){
    tree_a *out=NULL;
    if((*Mytree)->id==Node_id) return (*Mytree);
    else if ((*Mytree)->children!=NULL){
        tree_a *c=(*Mytree)->children;
        for(uint8_t i=0;i<branches;i++){
            tree_a *cc=c+i;
            out=get_node_from_3(&cc,Node_id);
            if(out!=NULL) break;
        }
    }
    return out;
}

void fill_tree_array(tree_a **Array[],tree_a **Mytree){
    *Array=(tree_a**)malloc(num_nodes*sizeof(tree_a*));
    tree_a *node;
    for(uint8_t i=0;i<num_nodes;i++){
        node = get_node_from_3(Mytree,i);
        (*Array)[i] = node;
    }
    sort_t(Array);
}

void complete_tree(tree_a **Array[],tree_a **Mytree,const uint8_t Depth,const uint8_t Branches,uint8_t *Leafs_id, const uint8_t Best_leaf_id,const float Max_utility, const float K){
    branches=Branches;
    for(uint8_t i=0;i<16;i++) *(Leafs_id+i)=-1;
    *Mytree=(tree_a*)malloc(sizeof(tree_a));
    (*Mytree)->depth = 0;
    (*Mytree)->id=num_nodes++;
    (*Mytree)->tlX=0,(*Mytree)->tlY=0,(*Mytree)->brX=0,(*Mytree)->brY=0;
    (*Mytree)->parent=NULL;
    (*Mytree)->children=NULL;
    (*Mytree)->node_filter = (filter_a*)malloc(sizeof(filter_a));
    set_filter((*Mytree)->node_filter,0.75,0);
    if(Depth > 0) loop_complete_tree(Mytree,Depth-1,Leafs_id,Best_leaf_id,Max_utility,K);
    fill_tree_array(Array,Mytree);
}

tree_a* get_node(tree_a **Array[],const uint8_t Node_id){
    return (*Array)[Node_id];
}

uint8_t get_nearest_node(tree_a **Array[],const uint8_t MYnode,const uint8_t MSGnode){
    tree_a *my_node=(*Array)[MYnode];
    tree_a *msg_node=(*Array)[MSGnode];
    for(uint8_t i=0;i<msg_node->depth-my_node->depth-1;i++) msg_node=msg_node->parent;
    return msg_node->id;
}

uint8_t msg_received_from(tree_a **Array[],const uint8_t Mynode_id,const uint8_t Messagednode_id){
    if(Mynode_id==Messagednode_id) return THISNODE;
    tree_a *my_node=get_node(Array,Mynode_id);
    if(my_node->parent!=NULL && my_node->parent->id==Messagednode_id) return PARENTNODE;
    tree_a *flag=get_node_from_3(&my_node,Messagednode_id);
    if(flag!=NULL) return SUBTREE;
    if(my_node->parent!=NULL) flag=get_node_from_3(&(my_node->parent),Messagednode_id);
    if(flag!=NULL) return SIBLINGTREE;
    else return OTHER;
}

void complete_update(tree_a **node){
    tree_a *c=(*node)->children;
    float temp_utility=0,temp_distance=0;
    for(uint8_t i=0;i<branches;i++){
        if((c+i)->node_filter->utility>temp_utility){
            temp_utility=(c+i)->node_filter->utility;
            temp_distance=(c+i)->node_filter->distance;
        }
    }
    update_filter((*node)->node_filter,temp_utility,temp_distance);
    if((*node)->parent!=NULL) complete_update(&((*node)->parent));
}

void bottom_up_utility_update(tree_a **Array[],const uint8_t Leaf_id,float Sensed_utility){
    tree_a *leaf=get_node(Array,Leaf_id);
    update_filter(leaf->node_filter,Sensed_utility,0);
    if(leaf->parent!=NULL) complete_update(&(leaf->parent));
}

/*-------------------------------------------------------------------*/
/*   calculate the top_left and bottom_right corners of each node    */
/*           top to bottom partition in quad trees                   */
/*-------------------------------------------------------------------*/
void loop_set_vertices(tree_a **Mytree,const uint8_t Index,const uint8_t Ref){
    float w1=(*Mytree)->tlX;
    float w2=(*Mytree)->brX;
    float h1=(*Mytree)->tlY;
    float h2=(*Mytree)->brY;
    if(Index!=0){
        float dif = (w2-w1)/(pow(2,Index));
        h2=dif + h1;
        w2=dif + w1;
        if((*Mytree)->children!=NULL){   
            tree_a *c=(*Mytree)->children;
            uint8_t count=0;
            for(uint8_t i=0;i<branches;i++){
                (c+i)->tlX=w1;
                (c+i)->tlY=h1;
                (c+i)->brX=w2;
                (c+i)->brY=h2;
                tree_a *cc=c+i;
                loop_set_vertices(&cc,Index,2);
                w1=w2;
                w2=w2+dif;
                count++;
                if(count == pow(2,Index)){
                    count=0;
                    w1=(*Mytree)->tlX;
                    w2=dif + w1;
                    h1=h2;
                    h2=dif + h1;
                }
            }
        }
    }
    else{
        if(Ref==2){
            float dif = (w2-w1)/branches;
            w2=((*Mytree)->brX/branches) + w1;
            tree_a *c=(*Mytree)->children;
            for(uint8_t i=0;i<branches;i++){
                (c+i)->tlX=w1;
                (c+i)->tlY=h1;
                (c+i)->brX=w2;
                (c+i)->brY=h2;
                tree_a *cc=c+i;
                loop_set_vertices(&cc,Index,1);
                w1=w1+dif;
                w2=w2+dif;
            }
        }
        else{
            if(Ref==1){
                float dif = (h2-h1)/branches;
                h2=h1+dif;
                if((*Mytree)->children!=NULL){
                    tree_a *c=(*Mytree)->children;
                    for(uint8_t i=0;i<branches;i++){
                        (c+i)->tlX=w1;
                        (c+i)->tlY=h1;
                        (c+i)->brX=w2;
                        (c+i)->brY=h2;
                        tree_a *cc=c+i;
                        loop_set_vertices(&cc,Index,0);
                        h1=h1+dif;
                        h2=h2+dif;
                    }
                }
            }                   
            else{
                float dif = (w2-w1)/branches;
                w2=w1+dif;
                if((*Mytree)->children!=NULL){
                    tree_a *c=(*Mytree)->children;
                    for(uint8_t i=0;i<branches;i++){
                        (c+i)->tlX=w1;
                        (c+i)->tlY=h1;
                        (c+i)->brX=w2;
                        (c+i)->brY=h2;
                        tree_a *cc=c+i;
                        loop_set_vertices(&cc,Index,1);
                        w1=w1+dif;
                        w2=w2+dif;
                    }
                }
            }
        }
    }
}

void set_vertices(tree_a **Mytree,const float BrX,const float BrY){
    (*Mytree)->tlX=0.1;
    (*Mytree)->tlY=0.1;
    (*Mytree)->brX=BrX;
    (*Mytree)->brY=BrY;
    tree_a *c = (*Mytree)->children;
    if(branches==2){
        for(uint8_t i=0;i<branches;i++){
            if(i==0){
                (c+i)->tlX=0.1;
                (c+i)->tlY=0.1;
                (c+i)->brX=0.5;
                (c+i)->brY=0.25;
            }
            else if(i==1){
                (c+i)->tlX=0.1;
                (c+i)->tlY=0.25;
                (c+i)->brX=0.5;
                (c+i)->brY=0.5;
            }
        }
    }
    else if(branches==4){
        for(uint8_t i=0;i<branches;i++){
            if(i==0){
                (c+i)->tlX=0.1;
                (c+i)->tlY=0.1;
                (c+i)->brX=0.25;
                (c+i)->brY=0.25;
            }
            else if(i==1){
                (c+i)->tlX=0.1;
                (c+i)->tlY=0.25;
                (c+i)->brX=0.25;
                (c+i)->brY=0.5;
            }
            if(i==2){
                (c+i)->tlX=0.25;
                (c+i)->tlY=0.1;
                (c+i)->brX=0.5;
                (c+i)->brY=0.25;
            }
            else if(i==3){
                (c+i)->tlX=0.25;
                (c+i)->tlY=0.25;
                (c+i)->brX=0.5;
                (c+i)->brY=0.5;
            }
        }
    }
    // uint8_t indx=0;
    // for(uint8_t i=1;i<=4;i++){
    //     uint8_t Pow=pow(4,1);
    //     if(Pow==branches){
    //         indx = i;
    //         break;
    //     }
    // }
    // loop_set_vertices(Mytree,indx,2);
}

void destroy_tree(tree_a **Array[],tree_a **Mytree){
    if(num_nodes>0){
        for (uint8_t i=0; i<num_nodes;i++){
            destroy_filter((*Array)[i]->node_filter);
            free((*Array)[i]->node_filter);            
            free((*Array)[i]);
        }
        free(*Array);
        num_nodes=0;
        num_leafs=0;
        *Mytree=NULL;
    }
}