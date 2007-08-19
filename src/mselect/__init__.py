# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: __init__.py $

import platform

if platform.system() == 'Windows':
    from wselect import select
else:
    from select import *
    
del platform    