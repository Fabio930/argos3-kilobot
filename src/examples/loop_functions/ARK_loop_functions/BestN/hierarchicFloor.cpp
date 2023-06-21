/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/
#include "hierarchicFloor.h"

ChierarchicFloor::ChierarchicFloor(){}

ChierarchicFloor::ChierarchicFloor(const CVector2 Tl,const CVector2 Br,const Real Offsetx,const Real Offsety){
    v_offset.x = Offsetx;
    v_offset.y = Offsety;

    root = new Node();
    root->set_vertices(Tl,Br);
}

ChierarchicFloor::~ChierarchicFloor(){
    root->~Node();
    delete [] root;
}

Real* ChierarchicFloor::get_offset_x(){
    return& v_offset.x;
}
Real* ChierarchicFloor::get_offset_y(){
    return& v_offset.y;
}