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
import wcurses_c as wc
import msvcrt
import winsound

#COLS = 0
#LINES = 0
COLORS = COLOR_PAIRS = 256
_pairs = []

COLOR_BLACK = 0x00
COLOR_BLUE = 0x01
COLOR_GREEN = 0x02
COLOR_CYAN = 0x03
COLOR_RED = 0x04
COLOR_MAGENTA = 0x5
COLOR_YELLOW = 0x06
COLOR_WHITE = 0x07

A_NORMAL = 0x07
A_STANDOUT = 0x70
A_BOLD = 0x08


_KEY_SHIFT_1 = 0x80
_KEY_SHIFT_2 = 0x100

KEY_RESIZE = 0 # XXX no support for this

KEY_BACKSPACE = 8
KEY_F1 = 59 + _KEY_SHIFT_1
KEY_F2 = 60 + _KEY_SHIFT_1
KEY_F3 = 61 + _KEY_SHIFT_1
KEY_F4 = 62 + _KEY_SHIFT_1
KEY_F5 = 63 + _KEY_SHIFT_1
KEY_F6 = 64 + _KEY_SHIFT_1
KEY_F7 = 65 + _KEY_SHIFT_1
KEY_F8 = 66 + _KEY_SHIFT_1
KEY_F9 = 67 + _KEY_SHIFT_1
KEY_F10 = 68 + _KEY_SHIFT_1

KEY_HOME = 71 + _KEY_SHIFT_2
KEY_UP = 72 + _KEY_SHIFT_2    
KEY_PPAGE = 73 + _KEY_SHIFT_2 
KEY_LEFT = 75 + _KEY_SHIFT_2  
KEY_RIGHT = 77 + _KEY_SHIFT_2 
KEY_END = 79 + _KEY_SHIFT_2
KEY_DOWN = 80 + _KEY_SHIFT_2  
KEY_NPAGE = 81 + _KEY_SHIFT_2 
KEY_IC = 82 + _KEY_SHIFT_2
KEY_DC = 83 + _KEY_SHIFT_2
KEY_F11 = 133 + _KEY_SHIFT_2
KEY_F12 = 134 + _KEY_SHIFT_2

ACS_LARROW = 0x2190
ACS_RARROW = 0x2192
ACS_HLINE = 0x2500 # ascii 196
ACS_VLINE = 0x2502 # ascii 179 
ACS_URCORNER = 0x2510 # ascii 191 
ACS_LLCORNER = 0x2514 # ascii 192 
ACS_LRCORNER = 0x2518 # ascii 217 
ACS_ULCORNER = 0x250C # ascii 218 
ACS_LTEE = 0x251D
ACS_RTEE = 0x2525
ACS_CKBOARD = 0x2591

def _screen_size():
    xx = wc.new_intp()
    yy = wc.new_intp()
    wc.get_screen_size(xx, yy)
    x = wc.intp_value(xx)
    y = wc.intp_value(yy)
    wc.delete_intp(xx)
    wc.delete_intp(yy)
    return x, y

def get_cols():
    return _screen_size()[0]

def get_lines():
    return _screen_size()[1]
    
def beep():
    winsound.Beep(400, 100)

def can_change_color():
    return False

def cbreak():
    pass

def color_pair(n):
    return _pairs[n]

def curs_set(v):
    pass

def nocbreak():
    pass
    
def echo():
    wc.echo()
    
def endwin():
    wc.echo()
    wc.deinit()

def has_colors():
    return True

def has_ic():
    return True

def init_pair(n, fg, bg):
    _pairs[n] = fg|(bg<<4)

def initscr():
    #global COLS, LINES
    wc.init()
    #COLS, LINES = _screen_size()
    return newwin(0, 0)

def newpad(nlines, ncols):
    return Window((0, 0, ncols, nlines), True)

def newwin(nlines, ncols, y=None, x=None):
    if (y != None and x == None) or (y == None and x != None):
        raise Exception, 'Illegal parameter combination'
    if y == None:
        y, x = nlines, ncols
        nlines, ncols = None, None
    if nlines == None:
        sx, sy = _screen_size()
        nlines, ncols = sy - y, sx - x
    if nlines < 0 or ncols < 0: raise Exception, 'Illegal parameters'
    return Window((x, y, x+ncols, y+nlines))
    
def noecho():
    wc.noecho()

def raw():
    pass

def start_color():
    global COLORS, COLOR_PAIRS, _pairs
    COLORS = COLOR_PAIRS = 256
    _pairs = [0] * COLORS
    init_pair(0, COLOR_WHITE, COLOR_BLACK)
    init_pair(1, COLOR_BLACK, COLOR_BLACK)
    init_pair(2, COLOR_RED, COLOR_BLACK)
    init_pair(3, COLOR_GREEN, COLOR_BLACK)
    init_pair(4, COLOR_YELLOW, COLOR_BLACK)
    init_pair(5, COLOR_BLUE, COLOR_BLACK)
    init_pair(6, COLOR_MAGENTA, COLOR_BLACK)
    init_pair(7, COLOR_CYAN, COLOR_BLACK)
    init_pair(8, COLOR_WHITE, COLOR_BLACK)
    
class Window(object):
    def __init__(self, rect, pad=False):
        self.rect = rect # [x0, y0, x1, y1] in absolute screen coordinates
        self.pad = pad
        self.xy = [0, 0]
        self.default_attr = A_NORMAL
        self.default_char = ascii.SP
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
        self.buf = [[self.default_char for xxx in xrange(xx)] for yyy in xrange(yy)]
                
    def _fit(self, length):
        x, y = self.xy
        sx = self.rect[2] - self.rect[0]
        dirty = self.dirty
        attrs = self.attrs
        buf = self.buf
        if y >= len(buf):
            dirty += [1] * (y-len(dirty)+1)
            attrs += [[self.default_attr] * sx for yyy in xrange(y-len(attrs)+1)]
            buf += [[self.default_char] * sx for yyy in xrange(y-len(buf)+1)]
        if x + length >= len(buf[y]):
            attrs[y] += [self.default_attr for xxx in xrange(x+length-len(attrs[y]))] 
            buf[y] += [self.default_char for xxx in xrange(x+length-len(buf[y]))]
    
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
    def attrset(self, attr):
        if not attr:
            attr = A_NORMAL
        self.default_attr = attr
    def bkgdset(self, ch, attr=None):
        self.attrset(attr)
        if not ch:
            ch = ascii.SP
        self.default_char = ch
    def border(self, ls=0, rs=0, ts=0, bs=0, tl=0, tr=0, bl=0, br=0):
        if not ls: ls = ACS_VLINE
        if not rs: rs = ACS_VLINE
        if not ts: ts = ACS_HLINE
        if not bs: bs = ACS_HLINE
        if not tl: tl = ACS_ULCORNER
        if not tr: tr = ACS_URCORNER
        if not bl: bl = ACS_LLCORNER
        if not br: br = ACS_LRCORNER
        x, y = self.xy
        uly = 0
        ulx = 0
        lry = self.rect[3] - self.rect[1]
        lrx = self.rect[2] - self.rect[0]
        self.vline(uly+1, ulx, ACS_VLINE, lry - uly - 1)
        self.hline(uly, ulx+1, ACS_HLINE, lrx - ulx - 1)
        self.hline(lry, ulx+1, ACS_HLINE, lrx - ulx - 1)
        self.vline(uly+1, lrx, ACS_VLINE, lry - uly - 1)
        self.addch(uly, ulx, tl)
        self.addch(uly, lrx, tr)
        self.addch(lry, lrx, br)
        self.addch(lry, ulx, bl)
        self.move(x, y) # restore cursor
    def box(self, vertch=0, horch=0):
        self.border(ls=vertch, rs=vertch, ts=horch, bs=horch)
    def clear(self):
        self._init_buf()
    def clrtoeol(self):
        x, y = self.xy
        buf = self.buf
        attrs = self.attrs
        if y >= len(buf): return
        if x >= len(buf[y]): return
        new_buf = [self.default_char for xxx in xrange(len(buf[y]) - x)]
        if buf[y][x:] != new_buf:
            buf[y][x:] = new_buf
            self.dirty[y] = 1
        new_attrs = [self.default_attr for xxx in xrange(len(attrs[y]) - x)]
        if attrs[y][x:] != new_attrs:
            attrs[y][x:] = new_attrs
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
    def erase(self):
        self._init_buf()
    def getch(self, y=None, x=None):
        if x and y:
            self.move(x, y)
        ch = ord(msvcrt.getch())
        if ch == 0x00:
            ch = _KEY_SHIFT_1 + ord(msvcrt.getch())
        elif ch == 0xE0:
            ch = _KEY_SHIFT_2 + ord(msvcrt.getch())
        return ch
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
        self.buf.insert(y, [self.default_char for xx in xrange(self.rect[2] - self.rect[0])])
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
            
    def refresh(self, pminrow=None, pmincol=None, sminrow=None, smincol=None, smaxrow=None, smaxcol=None):
        t = (pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)
        if None in t:
            if len([tt for tt in t if tt != None]): raise Exception, 'Must specify all parameters or none'
        if self.pad and None in t:
            raise Exception, 'Must specify parameters for pad'
        # XXX handle pad drawing
        
        x = self.rect[0]
        sx = self.rect[2] - x
        a = wc.new_short_array(sx)
        for y in xrange(self.rect[1], self.rect[3]):
            if self.dirty[y-self.rect[1]]:
                lnsx = self.attrs[y-self.rect[1]][:sx]
                self._ptr_array_build(a, lnsx)
                wc.write_row_attrs(x, y, len(lnsx), a)
                lnsx = self.buf[y-self.rect[1]][:sx]
                self._ptr_array_build(a, lnsx)
                wc.write_row_chars(x, y, len(lnsx), a)
                self.dirty[y-self.rect[1]] = 0
        wc.delete_short_array(a)        
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

class error:
    pass

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
