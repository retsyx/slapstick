import mcurses as curses

def main(win):
    cd = [d for d in dir(curses) if 'KEY' in d]
    ad = [d for d in dir(curses.ascii)]
    
    win.addstr(0, 0, 'press a to exit')
    ch = 65
    while ch != 97:
        ch = win.getch()
        cdef = ''
        for d in cd:
            if ch == eval('curses.'+d):
                cdef = 'curses.'+d
                break
        if cdef == '':
            for d in ad:
                if ch == eval('curses.ascii.'+d):
                    cdef = 'curses.ascii.'+d
                    break
        s = '%d %s' % (ch, cdef)        
        win.move(10, 0)
        win.deleteln()
        win.move(0, 0)
        win.insertln()
        win.addstr(0, 0, s)
        
curses.wrapper(main)
