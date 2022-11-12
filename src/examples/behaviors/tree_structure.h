#ifndef TREE_STRUCT_H
#define TREE_STRUCT_H
#include "filter_structure.h"

int num_nodes=0;
int branches=2;
int Leafs_size=0;

typedef struct tree_structure
{
    int id;
    float gt_utility;
    struct tree_structure *parent;
    struct tree_structure *children;
    float tlX,tlY,brX,brY;
    filter_a *node_filter;
}tree_a;

void loop_complete_tree(tree_a **mytree,const int Depth,unsigned int *Leafs_id,unsigned int *Leafs_size, const unsigned int Best_leaf_id,const float Max_utility, const float K) 
{
    if(Depth>=0)
    {
        (*mytree)->children = (tree_a*)malloc(branches*sizeof(tree_a));
        tree_a *c = (*mytree)->children;
        for(int i=0;i<branches;i++){
            (c+i)->id=num_nodes++;
            (c+i)->parent=*mytree;
            (c+i)->children=NULL;
            (c+i)->tlX=0;
            (c+i)->tlY=0;
            (c+i)->brX=0;
            (c+i)->brY=0;
            (c+i)->node_filter=(filter_a*)malloc(sizeof(filter_a));
            if(Depth > 0) set_filter((c+i)->node_filter,.75,0);
            else
            {
                *(Leafs_id + *Leafs_size) = (c+i)->id;
                *Leafs_size = *Leafs_size+1;
                set_filter((c+i)->node_filter,.75,1);
                if((c+i)->id==Best_leaf_id)
                {
                    (c+i)->gt_utility=Max_utility;
                }
                else
                {
                    (c+i)->gt_utility=Max_utility*K;
                }
            }
            tree_a *cc= (c+i);
            loop_complete_tree(&cc,Depth-1,Leafs_id,Leafs_size,Best_leaf_id,Max_utility,K);
        }
    }
}

void complete_tree(tree_a **mytree,const int Depth,const int Branches,unsigned int *Leafs_id,unsigned int *Leafs_size, const unsigned int Best_leaf_id,const float Max_utility, const float K)
{
    branches=Branches;
    for(int i=0;i<16;i++) *(Leafs_id+i)=-1;
    *mytree=(tree_a*)malloc(sizeof(tree_a));
    (*mytree)->id=num_nodes++;
    (*mytree)->tlX=0,(*mytree)->tlY=0,(*mytree)->brX=0,(*mytree)->brY=0;
    (*mytree)->parent=NULL;
    (*mytree)->children=NULL;
    (*mytree)->node_filter = (filter_a*)malloc(sizeof(filter_a));
    set_filter((*mytree)->node_filter,.75,0);
    loop_complete_tree(mytree,Depth-1,Leafs_id,Leafs_size,Best_leaf_id,Max_utility,K);
}

tree_a* get_node(tree_a **mytree,const int Node_id)
{
    tree_a *out=NULL;
    if((*mytree)->id==Node_id) return (*mytree);
    else if ((*mytree)->children!=NULL)
    {
        tree_a *c=(*mytree)->children;
        for(int i=0;i<branches;i++)
        {
            tree_a *cc=c+i;
            out=get_node(&cc,Node_id);
            if(out!=NULL) break;
        }
        
    }
    if(out!=NULL) return out;
    return NULL;
}

void complete_update(tree_a *node)
{
    tree_a *c=node->children;
    float temp_utility=0,temp_distance=0;
    for(int i=0;i<branches;i++)
    {
        if((c+i)->node_filter->utility>temp_utility)
        {
            temp_utility=(c+i)->node_filter->utility;
            temp_distance=(c+i)->node_filter->distance;
        }
    }
    update_filter(node->node_filter,temp_utility,temp_distance);
    if(node->parent!=NULL) complete_update(node->parent);
}

void bottom_up_utility_update(tree_a **mytree,const int Leaf_id,const float Sensed_utility)
{
    tree_a *leaf=get_node(mytree,Leaf_id);
    update_filter(leaf->node_filter,Sensed_utility,0);
    if(leaf->parent!=NULL) complete_update(leaf->parent);
}

/*-------------------------------------------------------------------*/
/*  calculate the top_left and bottom_right corners of each node
    top to bottom partition in quad trees */
/*-------------------------------------------------------------------*/
void loop_set_vertices(tree_a **mytree,const int Index,const int Ref)
{
    float w1=(*mytree)->tlX;
    float w2=(*mytree)->brX;
    float h1=(*mytree)->tlY;
    float h2=(*mytree)->brY;
    if(Index!=0)
    {
        float dif = (w2-w1)/(pow(2,Index));
        h2=dif + h1;
        w2=dif + w1;
        if((*mytree)->children!=NULL)
        {   
            tree_a *c=(*mytree)->children;
            int count=0;
            for(int i=0;i<branches;i++)
            {
                (c+i)->tlX=w1;
                (c+i)->tlY=h1;
                (c+i)->brX=w2;
                (c+i)->brY=h2;
                tree_a *cc=c+i;
                loop_set_vertices(&cc,Index,-1);
                w1=w2;
                w2=w2+dif;
                count++;
                if(count == pow(2,Index))
                {
                    count=0;
                    w1=(*mytree)->tlX;
                    w2=dif + w1;
                    h1=h2;
                    h2=dif + h1;
                }
            }
        }
    }
    else
    {
        if(Ref==-1)
        {
            float dif = (w2-w1)/branches;
            w2=((*mytree)->brX/branches) + w1;
            tree_a *c=(*mytree)->children;
            for(int i=0;i<branches;i++)
            {
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
        else
        {
            if(Ref==1)
            {
                float dif = (h2-h1)/branches;
                h2=h1+dif;
                if((*mytree)->children!=NULL)
                {
                    tree_a *c=(*mytree)->children;
                    for(int i=0;i<branches;i++)
                    {
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
            else
            {
                float dif = (w2-w1)/branches;
                w2=w1+dif;
                if((*mytree)->children!=NULL)
                {
                    tree_a *c=(*mytree)->children;
                    for(int i=0;i<branches;i++)
                    {
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

void set_vertices(tree_a **mytree,const float BrX,const float BrY)
{
    (*mytree)->tlX=0;
    (*mytree)->tlY=0;
    (*mytree)->brX=BrX;
    (*mytree)->brY=BrY;
    int indx=0;
    for(int i=1;i<=4;i++)
    {
        if(pow(4,i)==branches)
        {
            indx = i;
            break;
        }
    }
    loop_set_vertices(mytree,indx,-1);
}

void erase_tree(tree_a **mytree)
{
    if((*mytree)->children!=NULL)
    {
        tree_a *c=(*mytree)->children;
        for(int i=0;i<branches;i++)
        {
            tree_a *cc = c+i;
            erase_tree(&cc);
        }
        (*mytree)->children=NULL;
    }
    erase_filter((*mytree)->node_filter);
    free((*mytree)->node_filter);
    (*mytree)->parent=NULL;
    free(*mytree);
}

#endif