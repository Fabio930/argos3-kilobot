/**
 * @file <hierarchicFloor.h>
 *
 * @author Fabio Oddi <fabio.oddi@uniroma1.it>
 */

#ifndef HIERARCHICFLOOR_H
#define HIERARCHICFLOOR_H
#include "node.h"

class ChierarchicFloor
{
    private:
        Node *root=NULL;
        struct XYoffset
        {
            float x=-1,y=-1;
        }v_offset;
        std::vector<Node *> leafs;
        int num_nodes=0;
        int depth=-1;
        long unsigned int branches=-1;
        int swarm_size=-1;
        float max_utility=-1;
        float k=-1;
        float noise=-1;

    public:
        ChierarchicFloor();

        ChierarchicFloor(const CVector2 Tl,const CVector2 Br,const int SwarmSize,const int Depth,const int Branches,const float Utility,const float K,const float Noise,const float Offsetx,const float Offset);

        ~ChierarchicFloor();
        
        void complete_tree();

        void complete_tree(Node **ToComplete,const int Deep);

        void assign_random_MAXutility();

        void bottom_up_utility_update(Node **Start_node);

        void assign_distance_upTObottom(Node **Start_node);

        void set_distances_from_opt_node(Node **Start_node,const int Distance);

        void set_vertices();
        
        void loop_set_vertices(Node **Start_node,const int Index,const int Ref);

        void adjust_vertices(Node **Start_node);

        std::vector<Node *> get_leafs_from_node(Node **Start_node);
        
        std::vector<Node *> get_leafs();

        Node* get_random_leaf();

        Node* get_best_leaf();

        float get_kernel_unit();

        Node* get_node(const int Id);

        Node* get_node(Node **Start_node,const int Id);

        Node* get_leaf_from_position(CVector2 Position);

        float* get_offset_x();
        float* get_offset_y();
};
#endif