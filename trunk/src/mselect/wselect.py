# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: wselect.py $

# emulate select call for Windows

import wselect_c as ws
import msvcrt

# XXX currently only supports rlist
# Limited to wselect_c.MAX_HANDLES files to select for
def select(rlist, wlist, xlist, timeout=None):
    if timeout == None:
        timo = ws.INFINITE 
    else:
        timo = long(timeout*1000) # convert from float sec. to ms
    if wlist != None and len(wlist) > 0: raise Exception, 'wlist not supported'
    if xlist != None and len(xlist) > 0: raise Exception, 'xlist not supported'
    if rlist == None or len(rlist) == 0: return [], [], []
    if len(rlist) > ws.MAX_HANDLES: raise Exception, 'too many files (%d > %d)' % (len(rlist), ws.MAX_HANDLES)

    a = ws.new_int_array(ws.MAX_HANDLES)
    try:
        for i in xrange(len(rlist)):
            ws.int_array_setitem(a, i, msvcrt.get_osfhandle(rlist[i].fileno()))
        n = ws.wselect(len(rlist), a, timo)
    finally:
        ws.delete_int_array(a) 
    
    # Should we raise an exception on error?    
    if n <= 0: return [], [], []
    return [rlist[n - ws.OFFSET]], [], []

