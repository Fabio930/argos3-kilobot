/**
 * @author Fabio Oddi <fabio.oddi@diag.uniroma1.it>
**/
#include "hierarchicFloor.h"

ChierarchicFloor::ChierarchicFloor(){}

ChierarchicFloor::ChierarchicFloor(const CVector2 Tl,const CVector2 Br,const UInt8 Depth,const UInt8 Branches,const float Utility,const float K,const float Noise,const Real Offsetx,const Real Offsety){
    depth = Depth;
    branches = Branches;
    max_utility = Utility;
    k = K;
    noise = Noise;
    v_offset.x = Offsetx;
    v_offset.y = Offsety;

    root = new Node(0,max_utility*k,noise);
    num_nodes++;
    root->set_vertices(Tl,Br);
    complete_tree();
    set_vertices();
}

ChierarchicFloor::~ChierarchicFloor(){
    root->~Node();
    for(UInt8 i=0;i<leafs.size();i++) delete [] leafs[i];
    delete [] root;
}

void ChierarchicFloor::complete_tree(){
    UInt8 deep = depth-1;
    for(UInt8 i=0;i<branches;i++){
        Node *temp = new Node(num_nodes++,max_utility*k,noise);
        root->add_child(&temp);
        temp->set_parent(&root);
        if(deep == 0) leafs.push_back(temp);
        complete_tree(&temp,deep);
    }
}

void ChierarchicFloor::complete_tree(Node **ToComplete,const UInt8 Deep){
    if(Deep>0){
        UInt8 deep = Deep-1;
        for(UInt8 i=0;i<branches;i++){
            Node *temp = new Node(num_nodes++,max_utility*k,noise);
            (*ToComplete)->add_child(&temp);
            temp->set_parent(ToComplete);
            if(deep == 0) leafs.push_back(temp);
            complete_tree(&temp,deep);
        }
    }
}

void ChierarchicFloor::assign_MAXutility(const UInt8 Index){
    Node *random_leaf = leafs[Index];
    random_leaf->update_utility(max_utility);
    random_leaf->set_distance_from_opt(0);
    if(random_leaf->parent!=NULL){
        bottom_up_utility_update(&(random_leaf->parent));
        set_distances_from_opt_node(&random_leaf,0);
    }
}

void ChierarchicFloor::bottom_up_utility_update(Node **Start_node){
    float utility_temp  = 0;
    for(UInt8 i=0;i<branches;i++) if((*Start_node)->children[i]->utility > utility_temp) utility_temp = (*Start_node)->children[i]->utility;
    (*Start_node)->update_utility(utility_temp);
    if((*Start_node)->parent!=NULL) bottom_up_utility_update(&((*Start_node)->parent));
}

void ChierarchicFloor::assign_distance_upTObottom(Node **Start_node){
    if((*Start_node)->children.size()==branches){
        std::vector<Node *> temp_child=(*Start_node)->children;
        for(UInt8 j=0;j<branches;j++){
            temp_child[j]->set_distance_from_opt((*Start_node)->parent->distance_from_opt);
            assign_distance_upTObottom(&temp_child[j]);
        }
    }
}

void ChierarchicFloor::set_distances_from_opt_node(Node **Start_node,const UInt8 Distance){
    if((*Start_node)->parent!=NULL){
        (*Start_node)->parent->set_distance_from_opt(Distance+1);
        for(UInt8 i=0;i<branches;i++){
            Node *temp = (*Start_node)->parent->children[i];
            if(temp->id!=(*Start_node)->id){
                temp->set_distance_from_opt((*Start_node)->parent->distance_from_opt);
                assign_distance_upTObottom(&temp);
            }
        }
        set_distances_from_opt_node(&((*Start_node)->parent),Distance+1);
    }
}

void ChierarchicFloor::set_vertices(){
    switch (branches){
    case 2:
        for(uint8_t i=0;i<root->children.size();i++){
            switch (i){
            case 0:
                (root)->children[i]->set_vertices(CVector2(root->get_top_left_angle().GetY(),root->get_top_left_angle().GetX()),CVector2(root->get_bottom_right_angle().GetY(),0));
                break;
            case 1:
                (root)->children[i]->set_vertices(CVector2(root->get_top_left_angle().GetY(),0),CVector2(root->get_bottom_right_angle().GetY(),root->get_bottom_right_angle().GetX()));
                break;
            }
            if(root->children[i]->children.size()!=0) loop_set_vertices(&(root->children[i]),0,1,root->get_top_left_angle().GetY()+.05,root->get_bottom_right_angle().GetY()-.05,root->get_top_left_angle().GetX()+.05,root->get_bottom_right_angle().GetX()-.05);
        }
        break;
    case 4:
        for(uint8_t i=0;i<(root)->children.size();i++){
            switch (i){
            case 0:
                (root)->children[i]->set_vertices(CVector2(root->get_top_left_angle().GetY(),root->get_top_left_angle().GetX()),CVector2(0,0));
                break;
            case 1:
                (root)->children[i]->set_vertices(CVector2(root->get_top_left_angle().GetY(),0),CVector2(0,root->get_bottom_right_angle().GetX()));
                break;
            case 2:
                (root)->children[i]->set_vertices(CVector2(0,root->get_top_left_angle().GetX()),CVector2(root->get_bottom_right_angle().GetY(),0));
                break;
            case 3:
                (root)->children[i]->set_vertices(CVector2(0,0),CVector2(root->get_bottom_right_angle().GetY(),root->get_bottom_right_angle().GetX()));
                break;
            }
            if(root->children[i]->children.size()!=0) loop_set_vertices(&(root->children[i]),1,0,root->get_top_left_angle().GetY()+.05,root->get_bottom_right_angle().GetY()-.05,root->get_top_left_angle().GetX()+.05,root->get_bottom_right_angle().GetX()-.05);
        }
        break;
    default:
        std::cout<<"Structure not supported.\n";
        break;
    }
}

void ChierarchicFloor::loop_set_vertices(Node **Start_node,const UInt8 Index,const UInt8 Ref,const float minX,const float maxX,const float minY,const float maxY){
    float w1 = (*Start_node)->get_top_left_angle().GetX();
    float w2 = (*Start_node)->get_bottom_right_angle().GetX();
    float h1 = (*Start_node)->get_top_left_angle().GetY();
    float h2 = (*Start_node)->get_bottom_right_angle().GetY();
    w1+=v_offset.x;
    w2+=v_offset.x;
    h1+=v_offset.y;
    h2+=v_offset.x;
    if(w1<minY+v_offset.y) w1=minY+v_offset.y;
    if(w2>maxY+v_offset.y) w2=maxY+v_offset.y;
    if(h1<minX+v_offset.x) h1=minX+v_offset.x;
    if(h2>maxX+v_offset.x) h2=maxX+v_offset.x;
    float dif;
    switch (Index){
    case 0:
        switch (Ref){
        case 1:
            dif = (w2-w1)/2.0;
            w2=w1+dif;
            if((*Start_node)->children.size()!=0){
                for(UInt8 c=0;c<branches;c++){
                    (*Start_node)->children[c]->set_vertices(CVector2(w1-v_offset.x,h1-v_offset.y),CVector2(w2-v_offset.x,h2-v_offset.y));
                    loop_set_vertices(&((*Start_node)->children[c]),Index,0,minX,maxX,minY,maxY);
                    w1=w1+dif;
                    w2=w2+dif;
                }
            }
        break;
        default:
            dif = (h2-h1)/2.0;
            h2=h1+dif;
            if((*Start_node)->children.size()!=0){
                for(UInt8 c=0;c<branches;c++){
                    (*Start_node)->children[c]->set_vertices(CVector2(w1-v_offset.x,h1-v_offset.y),CVector2(w2-v_offset.x,h2-v_offset.y));
                    loop_set_vertices(&((*Start_node)->children[c]),Index,1,minX,maxX,minY,maxY);
                    h1=h1+dif;
                    h2=h2+dif;
                }
            }
        break;
        }
    break;
    case 1:
        dif = (h2-h1)/2.0;
        h2=dif + h1;
        w2=dif + w1;
        if((*Start_node)->children.size()!=0){
            UInt8 count=0;
            for(UInt8 c=0;c<branches;c++){
                (*Start_node)->children[c]->set_vertices(CVector2(w1-v_offset.x,h1-v_offset.y),CVector2(w2-v_offset.x,h2-v_offset.y));
                loop_set_vertices(&((*Start_node)->children[c]),Index,0,minX,maxX,minY,maxY);
                h1=h2;
                h2=h2+dif;
                count++;
                if(count == 2){
                    count=0;
                    w1=w2;
                    h1=(*Start_node)->get_top_left_angle().GetY();
                    h1+= v_offset.y;
                    if(h1<minY+v_offset.x) h1=minY+v_offset.x;
                    w2=dif + w1;
                    h2=dif + h1;
                }
            }
        }
    break;
    }
}

UInt8 ChierarchicFloor::derive_node_id(const UInt8 Level, CVector2 Position){
    Node *leaf = get_leaf_from_position(Position);
    if(leaf->depth == Level) return leaf->id;
    else{
        for(UInt8 i=0;i<depth;i++){
            leaf = leaf->parent;
            if(leaf->depth == Level) return leaf->id;
        }
    }
    return 0;
}

std::vector<Node *> ChierarchicFloor::get_leafs_from_node(Node **Start_node){
    std::vector<Node *> out;
    if((*Start_node)->children.size()==branches){
        for(UInt8 i=0;i<branches;i++){
            std::vector<Node *> temp = get_leafs_from_node(&((*Start_node)->children[i]));
            for(UInt8 j=0;j<temp.size();j++) out.push_back(temp[j]);
        }
    }
    else out.push_back((*Start_node));
    return out;
}

std::vector<Node *> ChierarchicFloor::get_leafs(){
    return leafs;
}

int ChierarchicFloor::get_size(){
    return num_nodes;
}

Node* ChierarchicFloor::get_best_leaf(){
    for(UInt8 i=0;i<leafs.size();i++) if(leafs[i]->distance_from_opt==0) return leafs[i];
    return NULL;
}

Node* ChierarchicFloor::get_node(const UInt8 Id){
    if(root->id==Id){
        return root;
    }
    Node *temp;
    for(UInt8 i=0;i<branches;i++){
        temp = get_node(&(root->children[i]),Id);
        if(temp!=NULL) return temp;
    }
    return NULL;
}

Node* ChierarchicFloor::get_node(Node **Start_node,const UInt8 Id){
    if((*Start_node)->id==Id) return (*Start_node);
    if((*Start_node)->children.size()==branches){
        Node *temp;
        for(UInt8 i=0;i<branches;i++){
            temp = get_node(&((*Start_node)->children[i]),Id);
            if(temp!=NULL) return temp;
        }
    }
    return NULL;
}

Node* ChierarchicFloor::get_leaf_from_position(CVector2 Position){
    for(UInt8 i=0;i<leafs.size();i++){
        float sx = leafs[i]->tl_br.tl.GetX();
        float rx = leafs[i]->tl_br.br.GetX();
        float ty = leafs[i]->tl_br.tl.GetY();
        float by = leafs[i]->tl_br.br.GetY();
        if(sx==0.05-v_offset.x) sx = -v_offset.x;
        if(ty==0.05-v_offset.y) ty = -v_offset.y;
        if(rx==v_offset.x-0.05) rx = v_offset.x;
        if(by==v_offset.x-0.05) by = v_offset.y;
        if((Position.GetX()>=sx) && (Position.GetX()<=rx)){
            if((Position.GetY()>=ty) && (Position.GetY()<=by)) return leafs[i];
        }
    }
    return NULL;
}

Real* ChierarchicFloor::get_offset_x(){
    return& v_offset.x;
}
Real* ChierarchicFloor::get_offset_y(){
    return& v_offset.y;
}