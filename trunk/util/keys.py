import platform
import mcurses as curses

def main(win):
    # pierce through wcurses wrapper to get at dictionary
    if platform.system() == 'Windows':
        c_dict_str = 'curses.wrapped'
    else:
        c_dict_str = 'curses'

    cd = [d for d in eval('dir(%s)' % (c_dict_str)) if 'KEY' in d]
    ad = [d for d in dir(curses.ascii)]
    
    win.addstr(0, 0, 'press q to exit')
    ch = 0
    while ch != 113:
        ch = win.getch()
        cdef = ''
        for d in cd:
            if ch == eval('%s.'%(c_dict_str)+d):
                cdef = 'curses.'+d
                break
        if cdef == '':
            for d in ad:
                if ch == eval('curses.ascii.'+d):
                    cdef = 'curses.ascii.'+d
                    break
        if curses.ascii.isprint(ch):
            s = '%3d %c %s' % (ch, chr(ch), cdef)
        else:
            s = '%3d   %s' % (ch, cdef)
        win.move(10, 0)
        win.deleteln()
        win.move(0, 0)
        win.insertln()
        win.addstr(0, 0, s)
        
curses.wrapper(main)
