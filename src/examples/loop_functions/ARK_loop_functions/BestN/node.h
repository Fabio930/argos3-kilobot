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
        struct Vertices{
            CVector2 tl=CVector2(),br=CVector2();
        }tl_br;

    public:
        Node();

        virtual ~Node();
                
        void set_vertices(CVector2 Tl,CVector2 Br);

        CVector2 get_top_left_angle();
        
        CVector2 get_bottom_right_angle();
        
        friend class ChierarchicFloor;
};
#endif