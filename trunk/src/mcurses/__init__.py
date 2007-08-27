# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: __init__.py $

import platform, sys

class ModuleWrapper(object):
     def __init__(self, wrapped):
         self.wrapped = wrapped

     def __getattr__(self, name):
         if name == 'COLS':
             return self.wrapped.get_cols()
         elif name == 'LINES':
             return self.wrapped.get_lines()
         else:   
             return getattr(self.wrapped, name)
        
# bridge import the correct curses library depending on platform
if platform.system() == 'Windows':
    from wcurses import *
    import ascii
    from wrapper import *
    sys.modules[__name__] = ModuleWrapper(sys.modules[__name__])
else:
    from curses import *
    from curses import ascii
    from curses import wrapper
	
del platform
del sys
