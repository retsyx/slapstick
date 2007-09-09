#include <Python.h>
#include <conio.h>
#include <time.h>
#include <windows.h>

#define OFFSET 1

typedef enum {
    HND_TYPE_INVALID,
    HND_TYPE_CONSOLE,
    HND_TYPE_PIPE,
    HND_TYPE_FILE,
    HND_TYPE_SOCKET,
} hnd_type;

struct mhnd {
    hnd_type type;
    HANDLE hnd;
};
 
static PyObject *
wselect(PyObject *self, PyObject *args)
{
    struct mhnd *hnds;
    BOOL res;
    DWORD bytes_avail, type;
    int i, len, timeout_ms, timo;
    PyObject *list, *item;
 
    /* XXX hideous hack to pretend we have select for the purposes
        XXX of our app
    */
    hnds = NULL;
    i = -OFFSET;
 
    if (!PyArg_ParseTuple(args, "Oi", &list, &timeout_ms))
        return NULL;
 
    if (timeout_ms < 0)
        timo = 100;
    else
        timo = timeout_ms;
 
    if (!PyList_Check(list))
        return NULL;
 
    len = (int)PyList_Size(list);
    if (!len) goto out;
    
    hnds = PyMem_Malloc(sizeof(struct mhnd)*len);
    if (!hnds)
        return NULL;
  
    for (i = 0; i < len; i++)
    {
        item = PyList_GetItem(list, i);
        if (!PyInt_Check(item))
        {
            PyMem_Free(hnds);
            return NULL;
        }
     
        hnds[i].hnd = (HANDLE)PyInt_AsLong(item);
        type = GetFileType(hnds[i].hnd);
        switch (type)
        {
            case FILE_TYPE_CHAR:
                hnds[i].type = HND_TYPE_CONSOLE;
                break;
            case FILE_TYPE_PIPE:
                if (hnds[i].hnd == GetStdHandle(STD_INPUT_HANDLE))
                    hnds[i].type = HND_TYPE_CONSOLE;
                else
                    hnds[i].type = HND_TYPE_PIPE;
                break;
            case FILE_TYPE_DISK:
                hnds[i].type = HND_TYPE_FILE;
                break;
            default:
                hnds[i].type = HND_TYPE_SOCKET; /* XXX this is probably a bad assumption */        
        } 
    }
    
    do 
    {
        for (i = 0; i < len; i++)
        {
            switch (hnds[i].type)
            {
                case HND_TYPE_CONSOLE:
                    if (_kbhit()) goto out;
                break;
                case HND_TYPE_PIPE:
                    bytes_avail = 0;
                    res = PeekNamedPipe(hnds[i].hnd, NULL, 0, NULL, &bytes_avail, NULL);
                    if (bytes_avail) goto out;
                    break;
                default: /* XXX don't handle anything else */
                    break;  
            }
        }  
    
        if (timo >= 100)
            Sleep(100);
        else
            Sleep(timo);
           
        if (timeout_ms > 0)
            timo -= 100;
        
    } while (timo > 0);

    i = -1;

out:
    if (hnds) PyMem_Free(hnds);
 
    return Py_BuildValue("i", OFFSET + i);   
}

static PyMethodDef _functions[] = {
    {"select", (PyCFunction)wselect, 1},
    {NULL, NULL}
};

DL_EXPORT(void)
init_wselect_c()
{
    Py_InitModule("_wselect_c", _functions);
}