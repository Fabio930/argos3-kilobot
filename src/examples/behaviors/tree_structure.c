#include "tree_structure.h"

void complete_tree(arena_a **the_arena){
    *the_arena=(arena_a*)malloc(sizeof(arena_a));
    (*the_arena)->tlX=0,(*the_arena)->tlY=0,(*the_arena)->brX=0,(*the_arena)->brY=0;
}

void set_vertices(arena_a **the_arena,const float BrX,const float BrY){
    (*the_arena)->tlX = .05;
    (*the_arena)->tlY = .05;
    (*the_arena)->brX = BrX;
    (*the_arena)->brY = BrY;
}

void destroy_tree(arena_a **the_arena){
    free(*the_arena);
    *the_arena = NULL;
}