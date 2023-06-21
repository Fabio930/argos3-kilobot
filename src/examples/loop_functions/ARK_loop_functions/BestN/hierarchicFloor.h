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
        UInt8 swarm_size=0;

    public:
        ChierarchicFloor();

        ChierarchicFloor(const CVector2 Tl,const CVector2 Br,const Real Offsetx,const Real Offset);

        virtual ~ChierarchicFloor();

        Real* get_offset_x();
        Real* get_offset_y();
};
#endif