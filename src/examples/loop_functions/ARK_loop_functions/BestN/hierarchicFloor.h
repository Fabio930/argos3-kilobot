/**
 * @file <hierarchicFloor.h>
 *
 * @author Fabio Oddi <fabio.oddi@uniroma1.it>
 */

#ifndef HIERARCHICFLOOR_H
#define HIERARCHICFLOOR_H
#include "node.h"

class ChierarchicFloor{
    private:
        Node *root=NULL;
        struct XYoffset{
            Real x=-1,y=-1;
        }v_offset;
        std::vector<Node *> leafs;
        UInt8 num_nodes=0;
        UInt8 depth=0;
        UInt8 branches=0;
        UInt8 swarm_size=0;
        float max_utility=-1;
        float k=-1;
        float noise=-1;

    public:
        ChierarchicFloor();

        ChierarchicFloor(const CVector2 Tl,const CVector2 Br,const UInt8 Depth,const UInt8 Branches,const float Utility,const float K,const float Noise,const Real Offsetx,const Real Offset);

        virtual ~ChierarchicFloor();
        
        void complete_tree();

        void complete_tree(Node **ToComplete,const UInt8 Deep);

        void assign_MAXutility(const UInt8 Index);

        void bottom_up_utility_update(Node **Start_node);

        void assign_distance_upTObottom(Node **Start_node);

        void set_distances_from_opt_node(Node **Start_node,const UInt8 Distance);

        void set_vertices();
        
        void loop_set_vertices(Node **Start_node,const UInt8 Index,const UInt8 Ref);

        void adjust_vertices(Node **Start_node);

        UInt8 derive_node_id(const UInt8 Level, CVector2 Position);

        std::vector<Node *> get_leafs_from_node(Node **Start_node);
        
        std::vector<Node *> get_leafs();

        int get_size();

        Node* get_best_leaf();

        Node* get_node(const UInt8 Id);

        Node* get_node(Node **Start_node,const UInt8 Id);

        Node* get_leaf_from_position(CVector2 Position);

        Real* get_offset_x();
        Real* get_offset_y();
};
#endif