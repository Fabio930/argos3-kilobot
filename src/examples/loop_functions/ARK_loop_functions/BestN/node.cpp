/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/ 

#include "node.h"

Node::Node(){}

Node::Node(const UInt8 Id,const float Utility,const float Noise){
    id = Id;
    utility = Utility;
    noise = Noise;
    depth = 0;
}

Node::~Node(){
    if(children.size()>0){
        for(UInt8 i = 0; i < children.size(); ++i){
            this->children[i]->~Node();
            delete [] children[i];
        }
    }
    delete [] parent;
}

void Node::set_parent(Node **Parent){
    parent = *Parent;
    depth = parent->depth+1;
}

void Node::add_child(Node **Child){
    children.push_back(*Child);
}

void Node::set_distance_from_opt(const UInt8 Distance){
    distance_from_opt = Distance;
}

void Node::set_vertices(CVector2 Tl,CVector2 Br){
    tl_br.tl = Tl;
    tl_br.br = Br;
}

void Node::set_vertices_offset(CVector2 Tl,CVector2 Br){
    tl_br.tl_offset = Tl;
    tl_br.br_offset = Br;
}

void Node::update_utility(const float Utility){
    utility = Utility;
}

void Node::update_noise(const float Noise){
    noise = Noise;
}

UInt8 Node::get_distance_from_opt(){
    return distance_from_opt;
}

UInt8 Node::get_id(){
    return id;
}

CVector2 Node::get_top_left_angle(){
    return tl_br.tl;
}

CVector2 Node::get_bottom_right_angle(){
    return tl_br.br;
}

Node* Node::get_parent(){
    return parent;
}

std::vector<Node *> Node::get_children(){
    return children;
}

bool Node::isin(CVector2 Position){
    if((Position.GetX()>=this->tl_br.tl.GetX()) && (Position.GetX()<=this->tl_br.br.GetX()) && (Position.GetY()>=this->tl_br.tl.GetY()) && (Position.GetY()<=this->tl_br.br.GetY()))return true;
    return false;
}