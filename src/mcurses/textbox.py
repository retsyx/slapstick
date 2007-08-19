"""Simple textbox editing widget with Emacs-like keybindings.
   Derived from textpad.py from the Python distribution.
"""

import __init__ as curses
import ascii

def rectangle(win, uly, ulx, lry, lrx):
    """Draw a rectangle with corners at the provided upper-left
    and lower-right coordinates.
    """
    win.vline(uly+1, ulx, curses.ACS_VLINE, lry - uly - 1)
    win.hline(uly, ulx+1, curses.ACS_HLINE, lrx - ulx - 1)
    win.hline(lry, ulx+1, curses.ACS_HLINE, lrx - ulx - 1)
    win.vline(uly+1, lrx, curses.ACS_VLINE, lry - uly - 1)
    win.addch(uly, ulx, curses.ACS_ULCORNER)
    win.addch(uly, lrx, curses.ACS_URCORNER)
    win.addch(lry, lrx, curses.ACS_LRCORNER)
    win.addch(lry, ulx, curses.ACS_LLCORNER)

class Textbox:
    """Editing widget using the interior of a window object.
     Supports the following Emacs-like key bindings:

    Ctrl-A      Go to left edge of window.
    Ctrl-B      Cursor left, wrapping to previous line if appropriate.
    Ctrl-D      Delete character under cursor.
    Ctrl-E      Go to right edge (stripspaces off) or end of line (stripspaces on).
    Ctrl-F      Cursor right, wrapping to next line when appropriate.
    Ctrl-G      Terminate, returning the window contents.
    Ctrl-H      Delete character backward.
    Ctrl-J      Terminate if the window is 1 line, otherwise insert newline.
    Ctrl-K      If line is blank, delete it, otherwise clear to end of line.
    Ctrl-L      Refresh screen.
    Ctrl-N      Cursor down; move down one line.
    Ctrl-O      Insert a blank line at cursor location.
    Ctrl-P      Cursor up; move up one line.

    Move operations do nothing if the cursor is at an edge where the movement
    is not possible.  The following synonyms are supported where possible:

    KEY_LEFT = Ctrl-B, KEY_RIGHT = Ctrl-F, KEY_UP = Ctrl-P, KEY_DOWN = Ctrl-N
    KEY_BACKSPACE = Ctrl-h
    """
    def __init__(self, win, validate=None, callback=None):
        self.win = win
        (self.maxy, self.maxx) = win.getmaxyx()
        self.maxy -= 1
        self.maxx -= 1
        self.stripspaces = 1
        self.lastcmd = None
        self.validate = validate
        self.callback = callback
        self.text = [[] for y in xrange(self.maxy+1)]
        win.keypad(1)

    def text_insert(self, y, x, ch):
        if len(self.text[y]) > x:
            self.text[y].insert(x, ch)
        else: # <= x
            self.text[y] += [ascii.SP] * (x - len(self.text[y]))
            self.text[y].append(ch)

    def text_delete(self, y, x):
        if y < 0 or x < 0 or y >= len(self.text) or x >= len(self.text[y]): return
        del self.text[y][x]
 
    def text_delete_line(y, x=0):
        del self.text[y][x:]

    def text_insert_line(y):
        self.text.insert(y, [])

    def _end_of_line(self, y):
        "Go to the location of the first blank on the given line."
        last = self.maxx
        while 1:
            if ascii.ascii(self.win.inch(y, last)) != ascii.SP:
                last = min(self.maxx, last+1)
                break
            elif last == 0:
                break
            last = last - 1
        return last

    def do_command(self, ch):
        "Process a single editing command."
        (y, x) = self.win.getyx()
        self.lastcmd = ch
        if ascii.isprint(ch):
            if y < self.maxy or x < self.maxx:
                # The try-catch ignores the error we trigger from some curses
                # versions by trying to write into the lowest-rightmost spot
                # in the window.
                try:
                    self.text_insert(y, x, ch)
                    self.win.addstr(y, 0, ''.join([chr(ascii.ascii(ch)) for ch in self.text[y]]))
                    self.win.move(y, x+1)
                except curses.error:
                    pass
        elif ch == ascii.SOH:                           # ^a
            self.win.move(y, 0)
        elif ch in (ascii.STX,curses.KEY_LEFT, ascii.BS, curses.KEY_BACKSPACE):
            if x > 0:
                self.win.move(y, x-1)
            elif y == 0:
                pass
            elif self.stripspaces:
                self.win.move(y-1, self._end_of_line(y-1))
            else:
                self.win.move(y-1, self.maxx)
            if ch in (ascii.BS, curses.KEY_BACKSPACE):
                self.win.delch()
                y, x = self.win.getyx()
                self.text_delete(y, x)
        elif ch == ascii.EOT:                           # ^d
            self.win.delch()
            self.text_delete(y, x)
        elif ch == ascii.ENQ:                           # ^e
            if self.stripspaces:
                self.win.move(y, self._end_of_line(y))
            else:
                self.win.move(y, self.maxx)
        elif ch in (ascii.ACK, curses.KEY_RIGHT):       # ^f
            if x < self.maxx:
                self.win.move(y, x+1)
            elif y == self.maxy:
                pass
            else:
                self.win.move(y+1, 0)
        elif ch == ascii.BEL:                           # ^g
            return True
        elif ch in (ascii.NL, ascii.CR):                # ^j ^m
            if self.maxy == 0:
                return True
            elif y < self.maxy:
                self.win.move(y+1, 0)
        elif ch == ascii.VT:                            # ^k
            if x == 0 and self._end_of_line(y) == 0:
                self.win.deleteln()
                self.text_delete_line(y)
            else:
                # first undo the effect of self._end_of_line
                self.win.move(y, x)
                self.win.clrtoeol()
                self.text_delete_line(y, x)
        elif ch == ascii.FF:                            # ^l
            self.win.refresh()
        elif ch in (ascii.SO, curses.KEY_DOWN):         # ^n
            if y < self.maxy:
                self.win.move(y+1, x)
                if x > self._end_of_line(y+1):
                    self.win.move(y+1, self._end_of_line(y+1))
        elif ch == ascii.SI:                            # ^o
            self.win.insertln()
            self.text_insert_line(y)
        elif ch in (ascii.DLE, curses.KEY_UP):          # ^p
            if y > 0:
                self.win.move(y-1, x)
                if x > self._end_of_line(y-1):
                    self.win.move(y-1, self._end_of_line(y-1))
        return False

    def gather(self):
        tmp = [''] * len(self.text)
        # convert each line to ASCII and join to a single string
        for y in xrange(len(self.text)):
            tmp[y] = ''.join([chr(ascii.ascii(ch)) for ch in self.text[y]])
            if self.stripspaces:
                tmp[y] = tmp[y].rstrip()
        return '\n'.join(tmp)

    def clear(self):
        self.text = [[] for y in xrange(self.maxy+1)]
        for y in xrange(self.maxy+1):
            self.win.move(y, 0)
            self.win.clrtoeol()
        self.win.move(0, 0)

    def edit(self):
        "Edit in the widget window and collect the results."
        while 1:
            ch = self.win.getch()
            o_ch = ch
            if self.validate:
                ch = self.validate(ch)
            if ch:
                if self.do_command(ch):
                    break
            if self.callback:
                if self.callback(o_ch):
                    break
            self.win.refresh()
        return self.gather()

    def edit_one(self):
        "Edit in the widget window and collect the results."
        status = False
        ch = self.win.getch()
        o_ch = ch
        if self.validate: 
            ch = self.validate(ch)
        if ch: 
            if self.do_command(ch):
                 return True 
        if self.callback:
            status = self.callback(o_ch)
        self.win.refresh()
        return status

if __name__ == '__main__':
    def test_editbox(stdscr):
        ncols, nlines = 9, 4
        uly, ulx = 15, 20
        stdscr.addstr(uly-2, ulx, "Use Ctrl-G to end editing.")
        win = curses.newwin(nlines, ncols, uly, ulx)
        #rectangle(stdscr, uly-1, ulx-1, uly + nlines, ulx + ncols)
        stdscr.refresh()
        return Textbox(win).edit()

    str = curses.wrapper(test_editbox)
    print 'Contents of text box:', repr(str)
