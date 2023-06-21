#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>

typedef struct arena{
    float tlX,tlY,brX,brY;
}arena_a;

void complete_tree(arena_a **the_arena);

void set_vertices(arena_a **the_arena,const float BrX,const float BrY);

void destroy_tree(arena_a **the_arena);
