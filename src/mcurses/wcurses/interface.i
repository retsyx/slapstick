%module wcurses_c

%include cpointer.i
%include carrays.i
%pointer_functions(int, intp);
%array_functions(unsigned short, short_array);

%{
#include "interface.h"
%}

%include interface.h
