%module wselect_c

%{
#include <windows.h>
#include "wselect.h"
%}

%include wselect.h
%include cpointer.i
%include carrays.i

%array_functions(int, int_array);