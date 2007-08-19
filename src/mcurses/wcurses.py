# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: wcurses.py $
#
# wcurses - minimal (e.g. woefully incomplete) curses display emulation on Windows
#
import sys

import ascii
import wcurses_c

wc = wcurses_c

A_NORMAL = 0x07
A_STANDOUT = 0x70

KEY_LEFT = 293 # XXX don't know
KEY_RIGHT = 295 # XXX don't know
KEY_UP = 294 # XXX don't know
KEY_DOWN = 296 # XXX don't know
KEY_PPAGE = 289 # don't know
KEY_NPAGE = 290 # don't know

KEY_BACKSPACE = 8
ACS_HLINE = 0x2500 # ascii 196
ACS_VLINE = 0x2502 # ascii 179 
ACS_URCORNER = 0x2510 # ascii 191 
ACS_LLCORNER = 0x2514 # ascii 192 
ACS_LRCORNER = 0x2518 # ascii 217 
ACS_ULCORNER = 0x250C # ascii 218 

def _screen_size():
    xx = wc.new_intp()
    yy = wc.new_intp()
    wc.get_screen_size(xx, yy)
    x = wc.intp_value(xx)
    y = wc.intp_value(yy)
    wc.delete_intp(xx)
    wc.delete_intp(yy)
    return x, y
    
def initscr():
    wc.init()
    return newwin(0, 0)
    
def cbreak():
    pass

def nocbreak():
    pass
    
def echo():
    wc.echo()
    
def endwin():
    wc.echo()
    wc.deinit()
    
def newwin(nlines, ncols, y=None, x=None):
    if (y and not x) or (not y and x):
        raise Exception, 'Illegal parameter combination'
    if not y:
        y, x = nlines, ncols
        nline, ncols = None, None
    if not x:
        x, y = 0, 0
    if not nlines:
        sx, sy = _screen_size()
        nlines, ncols = sy - y, sx - x
    return Window((x, y, x+ncols, y+nlines))
    
def noecho():
    wc.noecho()
    
def start_color():
    pass

class Window(object):
    def __init__(self, rect):
        self.rect = rect # [x0, y0, x1, y1] in absolute screen coordinates
        self.xy = [0, 0]
        self.default_attr = A_NORMAL
        self.dirty = []
        self.attrs = []
        self.buf = []
        self._init_buf()
        
    def _init_buf(self):
        # Initialize to rect to ensure drawing doesn't
        # need any fancy logic 
        xx = self.rect[2] - self.rect[0]
        yy = self.rect[3] - self.rect[1]
        self.dirty = [1] * yy
        self.attrs = [[self.default_attr for xxx in xrange(xx)] for yyy in xrange(yy)]
        self.buf = [[ascii.SP for xxx in xrange(xx)] for yyy in xrange(yy)]
                
    def _fit(self, length):
        x, y = self.xy
        dirty = self.dirty
        attrs = self.attrs
        buf = self.buf
        if y >= len(buf):
            dirty += [1] * (y-len(dirty)+1)
            attrs += [[] for yyy in xrange(y-len(attrs)+1)]
            buf += [[] for yyy in xrange(y-len(buf)+1)]
        if x + length >= len(buf[y]):
            attrs[y] += [self.default_attr for xxx in xrange(x+length-len(attrs[y]))]
            buf[y] += [ascii.SP for xxx in xrange(x+length-len(buf[y]))]
    
    def _move_x(self, off):
        x, y = self.xy
        x += off
        if x >= self.rect[2] - self.rect[0]:
            y += 1
            if y >= self.rect[3] - self.rect[1]: # revert if at bottom right already
                y -= 1
                x = self.rect[2] - self.rect[0] - 1
            else:   
                x = 0
        self.xy = [x, y]
        wc.move(x + self.rect[0], y + self.rect[1])
                
    def addch(self, y, x=None, ch=None, attr=None):
        # emulate silly parameter combinations
        # ch             3
        # ch, attr       2
        # y, x, ch       1
        # y, x, ch, attr 0
        nCount = 0
        if x == None: nCount += 1
        if ch == None: nCount += 1
        if attr == None: nCount += 1
        if nCount == 2:
            ch, attr = y, x
            y, x = None, None
        elif nCount == 3:
            ch = y
            y = None
        if attr == None:
            attr = self.default_attr
        if x != None and y != None:
            self.move(y, x)
        if type(ch) == type(''): ch = ord(ch)
        self._fit(1)    
        x, y = self.xy
        if self.attrs[y][x] != attr or self.buf[y][x] != ch:
            self.dirty[y] = 1    
        self.attrs[y][x] = attr
        self.buf[y][x] = ch
        self._move_x(1)
            
    def addstr(self, y, x=None, s=None, attr=None):
        # emulate silly parameter combinations
        # s             3
        # s, attr       2
        # y, x, s       1
        # y, x, s, attr 0
        nCount = 0
        if x == None: nCount += 1
        if s == None: nCount += 1
        if attr == None: nCount += 1
        if nCount == 2:
            s, attr  = y, x
            y, x = None, None
        elif nCount == 3:
            s = y
            y = None
        if attr == None:
            attr = self.default_attr
        if x != None and y != None:
            self.move(y, x)
        self._fit(len(s))
        x, y = self.xy
        new_attr = [attr for ch in s]
        new_buf = [ord(ch) for ch in s]
        if self.attrs[y][x:x+len(s)] != new_attr:
            self.attrs[y][x:x+len(s)] = new_attr
            self.dirty[y] = 1
        if self.buf[y][x:x+len(s)] != new_buf:
            self.buf[y][x:x+len(s)] = new_buf
            self.dirty[y] = 1
        self._move_x(len(s))
                
    def clear(self):
        self._init_buf()

    def clrtoeol(self):
        x, y = self.xy
        buf = self.buf
        if y >= len(buf): return
        if x >= len(buf[y]): return
        new_buf = [ascii.SP for xxx in xrange(len(buf[y]) - x)]
        if buf[y][x:] != new_buf:
            buf[y][x:] = new_buf
            self.dirty[y] = 1
    
    def delch(self, y=None, x=None):
        if x != None and y != None:
            self.move(y, x)
        x, y = self.xy
        buf = self.buf
        if y >= len(buf): return
        if x >= len(buf[y]): return
        self.dirty[y] = 1
        del buf[y][x]
        
    def deleteln(self):
        y = self.xy[1]
        if y >= len(self.buf): return
        del self.dirty[y]
        del self.attr[y]
        del self.buf[y]
        
    def derwin(self, nlines, ncols, y=None, x=None):
        if y == None:
            y, x = nlines, ncols
            nlines, ncols = None, None
        x += self.rect[0]
        y += self.rect[1]
        if not nlines:
            sx, sy = self.rect[2:4]
        else:
            sx = x + ncols
            sy = y + nlines 
        if sx >= self.rect[2]:
            sx = self.rect[2] - 1
        if sy >= self.rect[3]:
            sy = self.rect[3] - 1   
        return Window((x, y, sx, sy))
    # Should consider using msvcrt.getch() instead
    def getch(self, y=None, x=None):
        if x and y:
            self.move(x, y)
        return wc.getch()
    def getch_stdin(self, y=None, x=None):
        if x != None and y != None:
            self.move(x, y)
        bla = sys.stdin.read(1) # XXX No special key mapping
        #print ord(bla) 
        return bla
    def getmaxyx(self):
        return self.rect[3] - self.rect[1], self.rect[2] - self.rect[0]
    def getyx(self):
        return self.xy[1], self.xy[0]
    def hline(self, y, x, ch=None, n=None):
        # emulate silly parameter combinations
        # ch, n         2
        # y, x, ch, n   0
        nCount = 0
        if ch == None: nCount += 1
        if n == None: nCount += 1
        if nCount == 1: 
            raise Exception, 'Illegal parameter combination'
        elif nCount == 2:
            ch, n = y, x
            x, y = None, None
        if x != None and y != None:
            self.move(y, x)
        self._fit(n)
        x, y = self.xy
        buf = self.buf
        new_buf = [ch for xxx in xrange(n)]
        if new_buf != buf[y][x:x+n]:
            self.dirty[y] = 1
            buf[y][x:x+n] = new_buf
        self._move_x(n) 
    def inch(self, y=None, x=None):
        if x and y:
                    self.move(y, x)
        x, y = self.xy
        buf = self.buf  
        if y >= len(buf): return None
        if x >= len(buf[y]): return None
        return buf[y][x]    
    def insertln(self):
        y = self.xy[1]
        self.dirty.insert(y, 1)
        for yy in xrange(y, len(self.dirty)):
            self.dirty[yy] = 1
        self.attr.insert(y, [self.default_attr for xx in xrange(self.rect[2] - self.rect[0])])
        self.buf.insert(y, [ascii.SPs for xx in xrange(self.rect[2] - self.rect[0])])
    def keypad(self, yes):
        pass
    def move(self, y, x):
        sx = self.rect[2] - self.rect[0]
        sy = self.rect[3] - self.rect[1]
        if x < 0:
            x = 0
        elif x >= sx:
            x = sx - 1
        if y < 0:
            y = 0
        elif y >= sy: 
            y = sy - 1
        self.xy = [x, y]
        wc.move(x + self.rect[0], y + self.rect[1])

    def _ptr_array_build(self, a, lst):
        for i in xrange(len(lst)):
            wc.short_array_setitem(a, i, int(lst[i]))
            
    def refresh(self):
        x = self.rect[0]
        sx = self.rect[2] - x
        a = wc.new_short_array(sx)
        for y in xrange(self.rect[1], self.rect[3]):
            if self.dirty[y-self.rect[1]]:
                lnsx = self.attrs[y-self.rect[1]][:sx]
                lnsx_len = len(lnsx)
                self._ptr_array_build(a, lnsx)
                wc.write_row_attrs(x, y, lnsx_len, a)
                lnsx = self.buf[y-self.rect[1]][:sx]
                lnsx_len = len(lnsx)
                self._ptr_array_build(a, lnsx)
                wc.write_row_chars(x, y, lnsx_len, a)
                self.dirty[y-self.rect[1]] = 0
        wc.delete_short_array(a)        
        # restore cursor
        wc.move(self.xy[0] + self.rect[0], self.xy[1] + self.rect[1])
            
    def refresh1(self):
        y = self.rect[1]
        ey = self.rect[3]
        x = self.rect[0]
        sx = self.rect[2] - x
        for ln in self.buf:
            if self.dirty[y]:
                wc.move(x, y)
                #print ln[:sx]
                print ''.join([chr(ch) for ch in ln[:sx]]),
                #ll = len(ln[:sx])
                #if ll < sx: print chr(ascii.SP) * (sx - ll - 1),
                y += 1
                if y >= ey: break
                self.dirty[y] = 0
        # restore cursor
        wc.move(self.xy[0] + self.rect[0], self.xy[1] + self.rect[1])
            
    def debug_refresh(self):
        i = 0
        for ln in self.buf:
            print '%02d' % (i),
            print ''.join([chr(ch) for ch in ln])
            #print '\n'
            i += 1
    def vline(self, y, x, ch=None, n=None):     
        # emulate silly parameter combinations
        # ch, n         2
        # y, x, ch, n   0
        nCount = 0
        if ch == None: nCount += 1
        if n == None: nCount += 1
        if nCount == 1: 
            raise Exception, 'Illegal parameter combination'
        elif nCount == 2:
            ch, n = y, x
            x, y = None, None
        if x != None and y != None:
            self.move(y, x)
        x, y = self.xy
        buf = self.buf
        for yy in xrange(y, y+n):
            self.move(y, x)
            self._fit(1)
            if buf[yy][x] != ch:
                buf[yy][x] = ch
                self.dirty[yy] = 1
        self._move_x(1)


def rectangle(win, uly, ulx, lry, lrx):
    """Draw a rectangle with corners at the provided upper-left
    and lower-right coordinates.
    """
    win.vline(uly+1, ulx, ACS_VLINE, lry - uly - 1)
    win.hline(uly, ulx+1, ACS_HLINE, lrx - ulx - 1)
    win.hline(lry, ulx+1, ACS_HLINE, lrx - ulx - 1)
    win.vline(uly+1, lrx, ACS_VLINE, lry - uly - 1)
    win.addch(uly, ulx, ACS_ULCORNER)
    win.addch(uly, lrx, ACS_URCORNER)
    win.addch(lry, lrx, ACS_LRCORNER)
    win.addch(lry, ulx, ACS_LLCORNER)
    
def test():
    win = initscr()
    win.refresh()
    rectangle(win, 2, 2, 10, 15)
    win.addstr(4, 4, 'Hello World', A_NORMAL)
    win.addstr(5, 4, 'Goodbye', A_STANDOUT)
    win.addstr(6, 4, '0123456789abcdef0123456789abcdef', A_NORMAL)
    win.addch(7, 4, 'K')
    win.refresh()
    endwin()
    
if __name__ == '__main__':
    test()
