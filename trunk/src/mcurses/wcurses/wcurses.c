#include "Python.h"
#include <stdio.h>
#include <windows.h>

/* wcurses type definition */
typedef struct {
    PyObject_HEAD
    int inited;
    HANDLE std_i, std_o, std_e;
	SMALL_RECT extent;
} WCursesObject;

staticforward PyTypeObject WCurses_Type;

static PyObject *wcurses_init(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_deinit(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_get_screen_size(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_move(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_noecho(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_echo(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_write_row_attrs(WCursesObject *wc, PyObject *args);
static PyObject *wcurses_write_row_chars(WCursesObject *wc, PyObject *args);
static int grok_extent(WCursesObject *wc);

static PyObject *
wcurses_new(PyObject *self_, PyObject *args)
{
    WCursesObject *wc;
    
    wc = PyObject_NEW(WCursesObject, &WCurses_Type);
    if (!wc) return (PyObject *)wc;
    
    wc->inited = 0;
    
    return (PyObject *)wc;
}

static void
wcurses_dealloc(WCursesObject *wc)
{
    PyMem_DEL(wc);
}

static PyObject *
wcurses_init(WCursesObject *wc, PyObject *args)
{
    DWORD mode;
    
    if (wc->inited) goto out;    
	
	wc->std_i = GetStdHandle(STD_INPUT_HANDLE);
	wc->std_o = GetStdHandle(STD_OUTPUT_HANDLE);
	wc->std_e = GetStdHandle(STD_ERROR_HANDLE);
	grok_extent(wc);
	
	GetConsoleMode(wc->std_i, &mode);
	/* Disabling line input requires disabling echo,
	   otherwise Windows throws an error 87, invalid 
	   parameter.
	   Disabling processed input gives us ESC, etc.
	*/
	mode &= ~(ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT | ENABLE_PROCESSED_INPUT);
	SetConsoleMode(wc->std_i, mode);

    wc->inited = 1;
    
out:
	Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
wcurses_deinit(WCursesObject *wc, PyObject *args)
{
    DWORD mode;
    
    if (!wc->inited) goto out;
    
	GetConsoleMode(wc->std_i, &mode);
	mode |= ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT;
	SetConsoleMode(wc->std_i, mode);
    wc->inited = 0;
    
out:
	Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
wcurses_get_screen_size(WCursesObject *wc, PyObject *args)
{
    return Py_BuildValue("ii", wc->extent.Right - wc->extent.Left + 1, wc->extent.Bottom - wc->extent.Top + 1);
}

static PyObject *
wcurses_move(WCursesObject *wc, PyObject *args)
{
	COORD xy;
	int x, y;
	
	if (!PyArg_ParseTuple(args, "ii", &x, &y))
        return NULL;
	
	xy.X = x + wc->extent.Left;
	xy.Y = y + wc->extent.Top;
	
	if (xy.X < wc->extent.Left  ||  xy.X > wc->extent.Right) return NULL;
	if (xy.Y < wc->extent.Top  ||  xy.Y > wc->extent.Bottom) return NULL;
	
	SetConsoleCursorPosition(wc->std_o, xy);
	
	Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
wcurses_noecho(WCursesObject *wc, PyObject *args)
{
    DWORD mode;
    BOOL res;
     
    GetConsoleMode(wc->std_i, &mode);
    mode &= ~ENABLE_ECHO_INPUT;
    res = SetConsoleMode(wc->std_i, mode);

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
wcurses_echo(WCursesObject *wc, PyObject *args)
{
    DWORD mode;
    
    GetConsoleMode(wc->std_i, &mode);
    mode |= ENABLE_ECHO_INPUT;
    SetConsoleMode(wc->std_i, mode);
 
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
wcurses_write_row_attrs(WCursesObject *wc, PyObject *args)
{
 DWORD written;
 COORD xy;
 int x, y, i, len;
 PyObject *list, *item;
 WORD *ws;
 
 if (!PyArg_ParseTuple(args, "iiO", &x, &y, &list))
    return NULL;
 if (!PyList_Check(list))
    return NULL;
    
 len = (int)PyList_Size(list);
 if (len >= wc->extent.Right - wc->extent.Left)
  {
   len = wc->extent.Right - wc->extent.Left;
  }
  
 ws = PyMem_Malloc(sizeof(WORD)*len);
 if (!ws)
  {
   return NULL;
  }
 
 for (i = 0; i < len; i++)
   {
    item = PyList_GetItem(list, i);
    if (!PyInt_Check(item))
     {
      PyMem_Free(ws);
      return NULL;
     }
     
    ws[i] = (WORD)PyInt_AsLong(item); 
   }
     
 xy.X = x + wc->extent.Left;
 xy.Y = y + wc->extent.Top;
 
 WriteConsoleOutputAttribute(wc->std_o, ws, len, xy, &written);
 
 PyMem_Free(ws);
  
 Py_INCREF(Py_None);
 return Py_None;
}

static PyObject *
wcurses_write_row_chars(WCursesObject *wc, PyObject *args)
{
 DWORD written;
 COORD xy;
 int x, y, i, len;
 PyObject *list, *item;
 WORD *ws;
 
 if (!PyArg_ParseTuple(args, "iiO", &x, &y, &list))
    return NULL;
 if (!PyList_Check(list))
    return NULL;
    
 len = (int)PyList_Size(list);
 if (len >= wc->extent.Right - wc->extent.Left)
  {
   len = wc->extent.Right - wc->extent.Left;
  }
  
 ws = PyMem_Malloc(sizeof(WORD)*len);
 if (!ws)
  {
   return NULL;
  }
 
 for (i = 0; i < len; i++)
   {
    item = PyList_GetItem(list, i);
    if (!PyInt_Check(item))
     {
      PyMem_Free(ws);
      return NULL;
     }
     
    ws[i] = (WORD)PyInt_AsLong(item); 
   }
 
 xy.X = x + wc->extent.Left;
 xy.Y = y + wc->extent.Top;

 WriteConsoleOutputCharacter(wc->std_o, ws, len, xy, &written);
 
 PyMem_Free(ws);
 
 Py_INCREF(Py_None);
 return Py_None;
}

static int
grok_extent(WCursesObject *wc)
{
	CONSOLE_SCREEN_BUFFER_INFO ci;
	
	GetConsoleScreenBufferInfo(wc->std_o, &ci);
	wc->extent = ci.srWindow;
    
    return 0;
}

static PyMethodDef
wcurses_methods[] = {
    {"init", (PyCFunction)wcurses_init, 1},
    {"deinit", (PyCFunction)wcurses_deinit, 1},
    {"get_screen_size", (PyCFunction)wcurses_get_screen_size, 1},
    {"move", (PyCFunction)wcurses_move, 1},
    {"noecho", (PyCFunction)wcurses_noecho, 1},
    {"echo", (PyCFunction)wcurses_echo, 1},
    {"write_row_attrs", (PyCFunction)wcurses_write_row_attrs, 1},
    {"write_row_chars", (PyCFunction)wcurses_write_row_chars, 1},
    {NULL, NULL}
};


static PyObject*  
wcurses_getattr(WCursesObject *wc, char *name)
{
    return Py_FindMethod(wcurses_methods, (PyObject *)wc, name);
}

statichere PyTypeObject WCurses_Type = {
    PyObject_HEAD_INIT(NULL)
    0, /* ob_size */
    "wc", /* tp_name */
    sizeof(WCursesObject), /* tp_size */
    0, /* tp_itemsize */
    /* methods */
    (destructor)wcurses_dealloc, /* tp_dealloc */
    NULL, /* tp_print */
    (getattrfunc)wcurses_getattr, /* tp_getattr */
    NULL, /* tp_setattr */
};

static PyMethodDef _functions[] = {
    {"WCurses", (PyCFunction)wcurses_new, 1},
    {NULL, NULL}
};


DL_EXPORT(void)
init_wcurses_c()
{
    /* Patch object type */
    WCurses_Type.ob_type = &PyType_Type;

    Py_InitModule("_wcurses_c", _functions);
}