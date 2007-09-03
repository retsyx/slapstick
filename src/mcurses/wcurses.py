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
import msvcrt, sys, time, weakref, winsound

import ascii
import wcurses_c as wc

stdscr = None
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
A_COLOR = 0xFF
A_REVERSE = 0x100

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

def napms(ms):
    time.sleep(ms/1000.0)
    
def nocbreak():
    pass

def doupdate():
    stdscr.doupdate()
    
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
    global stdscr
    wc.init()
    stdscr = newwin(0, 0)
    stdscr.refresh() # clear the screen
    return stdscr

def newpad(nlines, ncols):
    return Window((0, 0, ncols, nlines), pad=True)

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
    return Window((x, y, x+ncols, y+nlines), pad=False)
    
def noecho():
    wc.noecho()

def nl():
    pass

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
        self.delay = -1
        self.xy = [0, 0]
        self.default_attr = A_NORMAL
        self.default_char = ascii.SP
        self.dirty = []
        self.attrs = []
        self.buf = []
        self._init_buf()
    def _attr_grok(self, attr):
        if attr == None:
            attr = self.default_attr
        if attr & A_REVERSE:
            attr &= 0xFF
            attr = ((attr&0xf0)>>8) | ((attr&0x0f)<<8)
        return attr    
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
            attrs[y] += [self.default_attr] * (x+length-len(attrs[y])) 
            buf[y] += [self.default_char] * (x+length-len(buf[y]))
    def _init_buf(self):
        # Initialize to rect to ensure drawing doesn't
        # need any fancy logic 
        xx = self.rect[2] - self.rect[0]
        yy = self.rect[3] - self.rect[1]
        self.dirty = [1] * yy
        self.attrs = [[self.default_attr] * xx for yyy in xrange(yy)]
        self.buf = [[self.default_char] * xx for yyy in xrange(yy)]
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
    def _ptr_array_build(self, a, lst):
        for i in xrange(len(lst)):
            wc.short_array_setitem(a, i, int(lst[i]))
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
        attr = self._attr_grok(attr)    
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
        attr = self._attr_grok(attr)
        if x != None and y != None:
            self.move(y, x)
        self._fit(len(s))
        x, y = self.xy
        new_attr = [attr] * len(s)
        new_buf = [ord(ch) for ch in s]
        if self.attrs[y][x:x+len(s)] != new_attr:
            self.attrs[y][x:x+len(s)] = new_attr
            self.dirty[y] = 1
        if self.buf[y][x:x+len(s)] != new_buf:
            self.buf[y][x:x+len(s)] = new_buf
            self.dirty[y] = 1
        self._move_x(len(s))
    def attroff(self, attr):
        self.default_attr &= ~attr
    def attron(self, attr):
        self.default_attr |= attr    
    def attrset(self, attr):
        self.default_attr = self._attr_grok(attr)
    def bkgdset(self, ch, attr=None):
        if not attr:
            attr = ch
            ch = None
        self.attrset(attr)
        if ch:
            if type(ch) == str: ch = ord(ch)
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
        new_buf = [self.default_char] * (len(buf[y]) - x)
        if buf[y][x:] != new_buf:
            buf[y][x:] = new_buf
            self.dirty[y] = 1
        new_attrs = [self.default_attr] * (len(attrs[y]) - x)
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
        del self.attrs[y]
        del self.buf[y]
    def derwin(self, nlines, ncols, y=None, x=None):
        if y == None:
            y, x = nlines, ncols
            nlines, ncols = None, None
        x += self.rect[0]
        y += self.rect[1]
        return self.subwin(nlines, ncols, y, x)
    def doupdate(self):
        if self != stdscr: return
        bx, by, ex, ey = self.rect
        x = bx
        a = wc.new_short_array(ex-bx)
        for y in xrange(by, ey):
            if self.dirty[y]:
                lnsx = self.attrs[y]
                self._ptr_array_build(a, lnsx)
                wc.write_row_attrs(x, y, len(lnsx), a)
                lnsx = self.buf[y]
                self._ptr_array_build(a, lnsx)
                wc.write_row_chars(x, y, len(lnsx), a)
                self.dirty[y] = 0
        wc.delete_short_array(a)        
        # move cursor
        wc.move(self.xy[0] + self.rect[0], self.xy[1] + self.rect[1])
    def erase(self):
        self._init_buf()
    def getbegyx(self):
        return self.rect[1], self.rect[0]
    def _getch(self):
        ch = ord(msvcrt.getch())
        if ch == 0x00:
            ch = _KEY_SHIFT_1 + ord(msvcrt.getch())
        elif ch == 0xE0:
            ch = _KEY_SHIFT_2 + ord(msvcrt.getch())
        return ch
    def getch(self, y=None, x=None):
        if not self.pad: self.refresh()
        if x and y:
            self.move(x, y)
        delay = self.delay
        if delay < 0: return self._getch()
        while delay >= 0:
            if msvcrt.kbhit(): return self._getch()
            if delay >= 100:
                st = 0.1
            else:
                st = delay/1000.0
            time.sleep(st)
            delay -= 100
        return -1
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
        attrs = self.attrs
        new_buf = [ch] * n
        if new_buf != buf[y][x:x+n]:
            self.dirty[y] = 1
            buf[y][x:x+n] = new_buf
        new_attr = [self.default_attr] * n
        if new_attr != attrs[y][x:x+n]:
            self.dirty[y] = 1
            attrs[y][x:x+n] = new_attr
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
        self.attrs.insert(y, [self.default_attr for xx in xrange(self.rect[2] - self.rect[0])])
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
    def nodelay(self, yes):
        if yes:
            self.delay = 0 # non-blocking
        else:
            self.delay = -1 # blocking
    def _noutrefresh(self, child, cbx=None, cby=None, sbx=None, sby=None, sex=None, sey=None):
        if cbx == None:
            sbx, sby = child.rect[:2]
            cbx, cby = 0, 0
            cex, cey = child.rect[2] - child.rect[0], child.rect[3] - child.rect[1]
            lx, ly = cex - cbx, cey - cby
        else:
            lx, ly = sex - sbx, sey - sby
            cex, cey = cbx + lx, cby + ly
        rx, ry = sbx - cbx, sby - cby
        for y in xrange(ly):
            if not child.dirty[y]: continue
            child.dirty[y] = 0
            self.dirty[y+ry] = 1
            self.buf[y+ry][rx:rx+lx] = child.buf[y][:lx]
            self.attrs[y+ry][rx:rx+lx] = child.attrs[y][:lx]
        self.xy = child.xy[0]+rx, child.xy[1]+ry    
    def noutrefresh(self): 
            stdscr._noutrefresh(self)
    def refresh(self, pminrow=None, pmincol=None, sminrow=None, smincol=None, smaxrow=None, smaxcol=None):
        t = (pminrow, pmincol, sminrow, smincol, smaxrow, smaxcol)
        if None in t:
            if len([tt for tt in t if tt != None]): raise Exception, 'Must specify all parameters or none'
        if self.pad and None in t:
            raise Exception, 'Must specify parameters for pad'
        if pminrow < 0: pminrow = 0
        if pmincol < 0: pmincol = 0
        if sminrow < 0: sminrow = 0
        if smincol < 0: smincol = 0
        if self.pad:
            buf_bx, buf_by = pmincol, pminrow
            scr_bx, scr_by = smincol, sminrow
            scr_ex, scr_ey = smaxcol, smaxrow
            # ugh, fudge to match what curses seems to accept
            scr_ey += 1
            if scr_ey - scr_by > len(self.buf): scr_ey = len(self.buf) + scr_by
            scr_ex += 1
        else:
            buf_bx, buf_by = 0, 0
            scr_bx, scr_by, scr_ex, scr_ey = self.rect
        stdscr._noutrefresh(self, buf_bx, buf_by, scr_bx, scr_by, scr_ex, scr_ey)
        doupdate()
    def subwin(self, nlines, ncols, y=None, x=None):
        if y == None:
            y, x = nlines, ncols
            nlines, ncols = None, None
        if not nlines:
            sx, sy = self.rect[2:4]
            sx -= x
            sy -= y
        else:
            sx = x + ncols
            sy = y + nlines 
        if sx >= self.rect[2]:
            sx = self.rect[2] - 1
        if sy >= self.rect[3]:
            sy = self.rect[3] - 1
        win = Window((x, y, sx, sy), pad=False)
        return win
    def timeout(self, delay):
        self.delay = delay
    def touchline(self, start, count, changed=1):
        if start > len(self.dirty): return
        if start + count > len(self.dirty):
            count = len(self.dirty) - start
        self.dirty[start:start+count] = [changed] * count    
    def touchwin(self):
        self.dirty = [1] * len(self.dirty)
    def untouchwin(self):
        self.dirty = [0] * len(self.dirty)
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
        attrs = self.attrs
        for yy in xrange(y, y+n):
            self.move(y, x)
            self._fit(1)
            if buf[yy][x] != ch:
                buf[yy][x] = ch
                self.dirty[yy] = 1
            if attrs[yy][x] != self.default_attr:
                attrs[yy][x] = self.default_attr
                self.dirty[yy] = 1
        self._move_x(1)

class error:
    pass

def test():
    win = initscr()
    win.refresh()
    win.box()
    win.addstr(4, 4, 'Hello World', A_NORMAL)
    win.addstr(5, 4, 'Goodbye', A_STANDOUT)
    win.addstr(6, 4, '0123456789abcdef0123456789abcdef', A_NORMAL)
    win.addch(7, 4, 'K')
    win.refresh()
    endwin()

   

if __name__ == '__main__':
    test()
