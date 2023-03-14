/**
 * @file <node.h>
 *
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/
#ifndef NODE_H
#define NODE_H
#include <string>
#include <random>
#include <argos3/core/utility/math/vector2.h>

namespace argos{
    class CSpace;
}

using namespace argos;

class Node{
    private:
        UInt8 id,depth;
        UInt8 distance_from_opt=0;
        float utility=-1;
        float noise=-1;
        Node *parent=NULL;
        std::vector<Node *> children;
        struct Vertices{
            CVector2 tl=CVector2(),br=CVector2(),tl_offset=CVector2(),br_offset=CVector2();
        }tl_br;

    public:
        Node();

        Node(const UInt8 Id,const float Utility,const float Noise);

        ~Node();
                
        void set_parent(Node **Parent);

        void add_child(Node **Child);
        
        void set_distance_from_opt(const UInt8 Distance);

        void set_vertices(CVector2 Tl,CVector2 Br);
        
        void set_vertices_offset(CVector2 Tl,CVector2 Br);

        void update_utility(const float Utility);
        
        void update_noise(const float Noise);

        UInt8 get_distance_from_opt();

        UInt8 get_id();
        
        CVector2 get_top_left_angle();
        
        CVector2 get_bottom_right_angle();
        
        Node* get_parent();
        
        std::vector<Node *> get_children();
        
        Node* get_sibling_node(UInt8 Node_id);

        bool isin(CVector2 Point);

        friend class ChierarchicFloor;
};
#endif