# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: wselect.py $

# emulate select call for Windows

import _wselect_c as ws
import msvcrt

# XXX currently only supports rlist
def select(rlist, wlist, xlist, timeout=None):
    if timeout == None:
        timo = -1
    else:
        timo = long(timeout*1000) # convert from float sec. to ms
    if wlist != None and len(wlist) > 0: raise Exception, 'wlist not supported'
    if xlist != None and len(xlist) > 0: raise Exception, 'xlist not supported'
    if rlist == None or len(rlist) == 0: return [], [], []
    a = [msvcrt.get_osfhandle(h.fileno()) for h in rlist]
    n = ws.select(a, timo)
    # Should we raise an exception on error?    
    if n <= 0: return [], [], []
    return [rlist[n - 1]], [], []

