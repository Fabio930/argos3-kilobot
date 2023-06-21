/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/ 

#include "node.h"

Node::Node(){}

Node::~Node(){}

void Node::set_vertices(CVector2 Tl,CVector2 Br){
    tl_br.tl = Tl;
    tl_br.br = Br;
}

CVector2 Node::get_top_left_angle(){
    return tl_br.tl;
}

CVector2 Node::get_bottom_right_angle(){
    return tl_br.br;
}