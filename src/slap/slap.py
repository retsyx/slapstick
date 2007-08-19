# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: slap.py $

# slapstick - Simple, low-tech audio player for your memory stick
import mcurses as curses
import mselect as select
import os, socket, re, sys, threading, time
import mutagen, mutagen.easyid3
import player
from mcurses import textbox

VERSION = 1

MODE_NONE, MODE_LIST, MODE_QUEUE, MODE_SEARCH, MODE_HELP, MODE_STATS = range(6)

DB_ENTRY_SIZE = 6
DB_DISPLAY, DB_ARTIST, DB_ALBUM, DB_TITLE, DB_ORDINAL, DB_PATH = range(DB_ENTRY_SIZE)
DB_ORDER_STR = """
    0 - artist, album or title
    1 - artist
    2 - album
    3 - title"""

DB_KEY = -1

class struct(object): 
    def __str__(self):
        return str(self.__dict__)
    def __repr__(self):
        return str(self.__dict__)

g_stats = struct()
g_stats.scan_start = 0
g_stats.scan_time = 0
g_stats.key_presses = 0
g_file_db = []
g_file_active_set = []
g_player_controller = None
g_display = None
g_mode = MODE_NONE

class wList(object):
    def __init__(self, scr):
        self.scr = scr
        self.items = []
        self.MODE_SELECT, self.MODE_VIEW = range(2)
        self.mode = self.MODE_SELECT
        self.cursor = 0
        self.hilite = 0
        self.view_offset = 0
        self.text_offset = 0
        self.size = 0, 0
        self.grok_size()

    def grok_size(self):
        old_size = self.size
        y, x = self.scr.getmaxyx()
        self.size = x, y
        return self.size != old_size

    def set_items(self, items, make_copy=False):
        if len(items) <= self.cursor:
            self.cursor = len(items)-1
        if len(items) <= self.hilite:
           self.hilite = len(items)-1
        if make_copy:
            self.items = items[:]
        else:    
            self.items = items

    def cursor_move(self, off):
        self.grok_size()
        new_cursor = self.cursor + off
        if new_cursor < 0:
            if self.cursor == 0: return
            new_cursor = 0
        elif new_cursor >= len(self.items):
            if self.cursor == len(self.items)-1: return
            new_cursor = len(self.items)-1
        new_hilite = self.hilite + off
        if new_hilite < 0:
            new_hilite = 0
        elif new_hilite >= self.size[1]:
            new_hilite = self.size[1]-1
        if new_hilite >= len(self.items): # properly handle lists of items that are shorter than the view
            new_hilite = len(self.items) - 1
        self.hilite = new_hilite
        self.cursor = new_cursor

    def cursor_move_absolute(self, off, center=False):
        if off < 0: 
            off = 0
        elif off >= len(self.items): 
            off = len(self.items)-1
        self.cursor = 0
        if center: self.hilite = self.size[1]/2 - off # center the hilite
        self.cursor_move(off)

    def view_move(self, off):
        new_view_offset = self.view_offset + off
        if new_view_offset >= len(self.items) - self.size[1]:
            new_view_offset = len(self.items) - self.size[1] - 1
        if new_view_offset < 0:
            new_view_offset = 0
        self.view_offset = new_view_offset

    def view_center(self, off=None):
        self.grok_size()
        if off == None:
            off = self.cursor
        if off < 0:
            off = 0
        elif off >= len(self.items):
            off = len(self.items)-1
        self.view_offset = off - (self.size[1]/2)
        if self.view_offset < 0:
            self.view_offset = 0
    
    def text_offset_move(self, off):
        self.text_offset += off
        if self.text_offset < 0:
            self.text_offset = 0
        elif self.text_offset >= 256:
            self.text_offset = 255
            
    def draw(self):
        if self.grok_size():
            self.cursor_move(0) # Window size changed, force a cursor update
        self.scr.clear()
        if self.mode == self.MODE_SELECT:
            bi = self.cursor - self.hilite
        else:
            bi = self.view_offset
        ei = min(min(len(self.items), self.size[1]) + bi, len(self.items))
        for i in xrange(ei-bi):
            # wrap in try/except to deal with curses implementations that
            # return an error (causing an exception) when addstr() hits the bottom right cell
            # of the screen
            try:
                if bi+i == self.cursor:
                    self.scr.addstr(i, 0, self.items[bi+i][DB_DISPLAY][self.text_offset:self.text_offset+self.size[0]], curses.A_STANDOUT)
                else:
                    self.scr.addstr(i, 0, self.items[bi+i][DB_DISPLAY][self.text_offset:self.text_offset+self.size[0]], curses.A_NORMAL)
            except:
                pass
            self.scr.clrtoeol()
            
    def refresh(self):
        self.scr.refresh()

def display_setup(scr):
    display = struct()
    display.scr = scr
    scr_maxyx = display.scr.getmaxyx()
    scr_maxxy = scr_maxyx[1], scr_maxyx[0]

    # textbox/pad
    display.pad_off = (2, 0)
    display.pad_size = (scr_maxxy[0] - display.pad_off[0], 1)
    display.pad_scr = scr.derwin(display.pad_size[1], display.pad_size[0], 
                                      display.pad_off[1], display.pad_off[0])
    display.pad = textbox.Textbox(display.pad_scr, slap_validate, slap_callback)
    display.pad.stripspaces = False
    # list
    display.list_off = (0, 1)
    display.list_size = (scr_maxxy[0], scr_maxxy[1] - display.list_off[1])
    display.list_scr = scr.derwin(display.list_size[1], display.list_size[0], 
                                  display.list_off[1], display.list_off[0])
    display.select_list = wList(display.list_scr)
    # queue
    display.queue_list = wList(display.list_scr)
    display.queue_list.mode = display.queue_list.MODE_VIEW
    # kill
    display.kill_list = wList(display.list_scr)
    # help
    display.help_list = wList(display.list_scr)
    display.help_list.mode = display.help_list.MODE_VIEW
    scr.clear()

    display.scr.addstr(0, 3, 'For help at any point press <ESC> H'[:scr_maxxy[0]-3], curses.A_STANDOUT)
    display.showing_help = 1

    return display

def display_update(display, mode, player_controller):
    display.scr.refresh()
    display.pad.win.refresh()
    if mode in (MODE_LIST, MODE_SEARCH):
        display.select_list.draw()
        display.select_list.refresh()
    elif mode == MODE_QUEUE:
        display.queue_list.cursor_move_absolute(player_controller.position)
        display.queue_list.draw()
        display.queue_list.refresh()
    elif mode in (MODE_HELP, MODE_STATS):
        display.help_list.draw()
        display.help_list.refresh()
    
def slap_enter_mode(new_mode):
    global g_display, g_mode, g_player_controller
    display = g_display
    mode = g_mode
    player_controller = g_player_controller
    if mode == new_mode: return
    if new_mode != MODE_LIST:
        if display.showing_help: # clear out startup help message
            display.scr.move(0, 3)
            display.scr.clrtoeol()
            display.showing_help = 0
    if new_mode == MODE_LIST:
        if g_file_active_set != g_file_db:
            display.scr.addch(0, 0, '=')
        else:
            display.scr.addch(0, 0, ' ')
    elif new_mode == MODE_QUEUE:
        display.scr.addch(0, 0, 'Q')
        display.queue_list.set_items(player_controller.track_list)
        display.queue_list.view_center(player_controller.position)
    elif new_mode == MODE_SEARCH:
        display.scr.addch(0, 0, '>')
    elif new_mode == MODE_HELP:
        display.scr.addch(0, 0, 'H')
        slap_print_help(display.help_list)
    elif new_mode == MODE_STATS:
        display.scr.addch(0, 0, 'S')
        slap_print_stats(display.help_list)
        
    g_mode = new_mode

def slap_validate(key_code):
    global g_display, g_mode, g_file_active_set, g_file_db, g_player_controller
    player_controller = g_player_controller
    display = g_display
    mode = g_mode
    if mode == MODE_LIST:
        if key_code == curses.ascii.ESC: # clear filter on ESC
            g_file_active_set = g_file_db
            display.select_list.set_items(g_file_active_set)
            display.pad.clear()
            display.scr.addch(0, 0, ' ')
        elif key_code in (curses.ascii.NL, curses.ascii.CR): # ENTER (PLAY track list)
            player_controller.start_track_list(g_file_active_set[display.select_list.cursor:])
        elif key_code in (ord("\\"), ord('|')): # '" (QUEUE track)
            player_controller.queue_track_list([g_file_active_set[display.select_list.cursor]])
        elif key_code in (ord("'"), ord('"')): # '" (QUEUE track list)
            player_controller.queue_track_list(g_file_active_set[display.select_list.cursor:])
        elif key_code == curses.ascii.SP: # SPACE (PAUSE/UNPAUSE)
            player_controller.pause()
        elif key_code in (ord('b'), ord('B')): # B (PREVIOUS)
            player_controller.previous_track()
        elif key_code in (ord('n'), ord('N')): # N (NEXT)
            player_controller.next_track()
        elif key_code in (ord('q'), ord('Q')): 
            return curses.ascii.BEL # Q (QUIT)
        elif key_code in (ord('a'), curses.KEY_UP): # a (UP)
            display.select_list.cursor_move(-1)
        elif key_code in (ord('A'), curses.KEY_PPAGE): # A (PAGE UP)
            display.select_list.cursor_move(-display.select_list.size[1])
        elif key_code in (ord('z'), curses.KEY_DOWN): # z (DOWN)
            display.select_list.cursor_move(1)
        elif key_code in (ord('Z'), curses.KEY_NPAGE): # Z (PAGE DOWN)
            display.select_list.cursor_move(display.select_list.size[1])
        elif key_code in (ord('s'), ord('S'), curses.KEY_LEFT): # S (text offset left)
            display.select_list.text_offset_move(-5)
        elif key_code in (ord('d'), ord('D'), curses.KEY_RIGHT): # D (text offset right)
            display.select_list.text_offset_move(5)
        elif key_code == ord('/'): # / (SEARCH)
            slap_enter_mode(MODE_SEARCH)
        elif key_code == ord('\t'): # TAB (QUEUE mode)
            slap_enter_mode(MODE_QUEUE)
        elif key_code in (ord('h'), ord('H')): # H (HELP)
            slap_enter_mode(MODE_HELP)
        elif key_code in (ord('t'), ord('T')): # T (STATS)
            slap_enter_mode(MODE_STATS)
        key_code = None
    elif mode == MODE_QUEUE:
        if key_code in (curses.ascii.ESC, ord('\t')): # exit mode on ESC
            slap_enter_mode(MODE_LIST)
        elif key_code == curses.ascii.SP: # SPACE (PAUSE/UNPAUSE)
            player_controller.pause()
        elif key_code in (ord('b'), ord('B')): # B (PREVIOUS)
            player_controller.previous_track()
        elif key_code in (ord('n'), ord('N')): # N (NEXT)
            player_controller.next_track()
        elif key_code in (ord('a'), curses.KEY_UP):
            display.queue_list.view_move(-1)
        elif key_code in (ord('A'), curses.KEY_PPAGE):
            display.queue_list.view_move(-display.queue_list.size[1])
        elif key_code in (ord('z'), curses.KEY_DOWN):
            display.queue_list.view_move(1)
        elif key_code in (ord('Z'), curses.KEY_NPAGE):
            display.queue_list.view_move(display.queue_list.size[1])
        elif key_code in (ord('s'), ord('S'), curses.KEY_LEFT): # S (text offset left)
            display.queue_list.text_offset_move(-5)
        elif key_code in (ord('d'), ord('D'), curses.KEY_RIGHT): # D (text offset right)
            display.queue_list.text_offset_move(5)
        key_code = None
    elif mode == MODE_SEARCH:
        #print key_code
        if key_code == curses.ascii.ESC: # exit mode on ESC
            g_file_active_set = g_file_db
            display.select_list.set_items(g_file_active_set)
            display.pad.clear()
            slap_enter_mode(MODE_LIST)
            key_code = None
        elif key_code in (curses.ascii.NL, curses.ascii.CR): # enter
            slap_enter_mode(MODE_LIST)
            key_code = None
        elif key_code == curses.KEY_UP: # (UP)
            display.select_list.cursor_move(-1)
            key_code = None
        elif key_code == curses.KEY_PPAGE: # (PAGE UP)
            display.select_list.cursor_move(-display.select_list.size[1])
            key_code = None
        elif key_code == curses.KEY_DOWN: # (DOWN)
            display.select_list.cursor_move(1)
            key_code = None
        elif key_code == curses.KEY_NPAGE: # (PAGE DOWN)
            display.select_list.cursor_move(display.select_list.size[1])
            key_code = None
        else:
            if key_code in (curses.ascii.DEL, curses.KEY_BACKSPACE) : # backspace
                key_code = curses.ascii.BS
    elif mode in (MODE_HELP, MODE_STATS):
        if key_code == curses.ascii.ESC: # exit mode on ESC
            slap_enter_mode(MODE_LIST)
        elif key_code == curses.ascii.SP: # SPACE (PAUSE/UNPAUSE)
            player_controller.pause()
        elif key_code in (ord('b'), ord('B')): # B (PREVIOUS)
            player_controller.previous_track()
        elif key_code in (ord('n'), ord('N')): # N (NEXT)
            player_controller.next_track()
        elif key_code in (ord('a'), curses.KEY_UP):
            display.help_list.view_move(-1)
        elif key_code in (ord('A'), curses.KEY_PPAGE):
            display.help_list.view_move(-display.queue_list.size[1])
        elif key_code in (ord('z'), curses.KEY_DOWN):
            display.help_list.view_move(1)
        elif key_code in (ord('Z'), curses.KEY_NPAGE):
            display.help_list.view_move(display.queue_list.size[1])
        key_code = None
    return key_code

def slap_callback(key_code):
    global g_file_active_set, g_file_db, g_player_controller
    mode = g_mode
    display = g_display
    player_controller = g_player_controller
    if mode == MODE_SEARCH:
        text = display.pad.gather()
        g_file_active_set = filter_items(g_file_db, text)
        display.select_list.set_items(g_file_active_set)
    display_update(display, g_mode, player_controller)
    
def slap(scr):
    global g_display, g_file_db, g_file_active_set, g_player_controller, g_mode, g_stats

    g_file_active_set = g_file_db
    player_controller = player.PlayerController()
    g_player_controller = player_controller
    display = display_setup(scr)
    g_display = display
    display.select_list.set_items(g_file_active_set)
    slap_enter_mode(MODE_LIST)
    display_update(display, g_mode, player_controller)

    timeout = None
    done = False
    while not done:
        sos = []

        sos.append(sys.stdin)
        sos.append(player_controller.fd())
        try:
            ri, ro, rerr = select.select(sos, [], [], timeout)
        except: # XXX force some window update logic here
            continue
        for so in ri:
            if so == sys.stdin:
                g_stats.key_presses += 1
                done = display.pad.edit_one()
            elif so == player_controller.fd():
                if player_controller.update():
                    display_update(display, g_mode, player_controller)
                    

def slap_print_help(lst):
    hlp = """
    
    Help
    ====
    
    <ESC>         Return to track selection mode
    a/<Up>        Scroll one line up
    z/<Down>      Scroll one line down
    A/<Page Up>   Scroll one page up
    Z/<Page Down> Scroll one page down
    <Space>       Pause/Unpause
    n/N           Play next track in queue
    b/B           Play previous track in queue
    
    Track Selection Mode
    ====================
    
    h/H           This help
    q/Q           Quit
    a/<Up>        Move highlight one track up
    z/<Down>      Move highlight one track down
    A/<Page Up>   Move highlight one page up
    Z/<Page down> Move highlight one page down
    s/S/<Left>    Scroll display to the left
    d/D/<Right>   Scroll display to the right
    <Enter>       Start playing tracks starting with highlighted track
    \/|           Queue highlighted track
    '/"           Queue tracks starting with highlighted track
    <Space>       Pause/Unpause
    n/N           Play next track in queue
    b/B           Play previous track in queue
    /             Enter search mode
    <Esc>         Clear search filter
    <Tab>         Enter queue view mode
    t/T           Enter stats mode
    
    Search Mode
    ===========
    
    <Enter>       Accept search filter and return to track selection mode
    <Esc>         Discard search filter and return to track selection mode
    <Up>          Move highlight one track up
    <Down>        Move highlight one track down
    <Page Up>     Move highlight one page up
    <Page down>   Move highlight one page down

    Searching
    ---------
    
    <words>       Match tracks with words in artist, album or title
    /<regex>      Regex match tracks in track artist, album or title
    +N<words>     Match tracks with words in field N of the track information
    +N/<regex>    Regex match tracks in field N of the track information

    Valid field numbers for N are:
    %s
    
    Queue View Mode
    ===============
    
    <Esc>/<Tab>   Return to track selection mode
    a/<Up>        Scroll one track up
    z/<Down>      Scroll one track down
    A/<Page Up>   Scroll one page up
    Z/<Page Down> Scroll one page down
    s/S/<Left>    Scroll display to the left
    d/D/<Right>   Scroll display to the right

    Stats Mode
    ==========
    
    <ESC>         Return to track selection mode
    a/<Up>        Scroll one line up
    z/<Down>      Scroll one line down
    A/<Page Up>   Scroll one page up
    Z/<Page Down> Scroll one page down
    <Space>       Pause/Unpause
    n/N           Play next track in queue
    b/B           Play previous track in queue
""" % (DB_ORDER_STR)
    lines = hlp.split('\n')
    lst.set_items(zip(lines, [0]*len(lines)))

def slap_print_stats(lst):
    s = """
    Stats
    =====
    
    %d Release 
    %d files
    %.2fs to scan
    %d key presses
    %.2fs running
    
""" % (VERSION, len(g_file_db), g_stats.scan_time, g_stats.key_presses, time.time() - g_stats.scan_start)
    lines = s.split('\n')
    lst.set_items(zip(lines, [0]*len(lines)))
    
def filespec_match(split_filename, file_spec):
    if split_filename[1] == file_spec: return split_filename
    return ('', '')

def list_files(path='.', file_specs=()):
    all_filenames = []
    for root, dirs, files in os.walk(path):
        filenames = [os.path.join(root, fn) for fn in files]
        split_filenames = [os.path.splitext(fn) for fn in filenames]
        filtered_filenames = []
        if len(file_specs) == 0: 
            filtered_filenames = split_filenames
        else:
            for fspc in file_specs:
                filtered_filenames += [filespec_match(sfn, fspc) for sfn in split_filenames]
        split_filenames = filtered_filenames
        filenames = [''.join(sfn) for sfn in split_filenames]
        while '' in filenames: filenames.remove('')
        all_filenames += filenames
        # traverse symbolic links
        for d in dirs:
            d_path = os.path.join(root, d)
            if os.path.islink(d_path):
                all_filenames += list_files(d_path, file_specs)
    return all_filenames

def scan_media_file(filename):
    info = [0] * DB_ENTRY_SIZE
    try:
        fid3 = mutagen.easyid3.EasyID3(filename)
        try:
            artist = ''.join(fid3['artist'])
        except: 
            artist = None
        try:    
            album = ''.join(fid3['album'])
        except:
            album = None
        try:    
            title = ''.join(fid3['title'])
        except:
            title = None
        try:
            ordinal = int(''.join(fid3['tracknumber']))
        except:
            ordinal = 0
        if not artist and not title:
            info[0] = os.path.basename(filename)
        else:
            t = [artist, album, title]
            while None in t: t.remove(None)
            info[DB_DISPLAY] = ' - '.join(t).encode('latin-1', 'replace') # could make configurable
    except:
        info[DB_DISPLAY] = os.path.splitext(os.path.basename(filename))[0]
        artist = None
        album = None
        title = None
        ordinal = 0
        
    info[DB_ARTIST] = artist
    info[DB_ALBUM] = album
    info[DB_TITLE] = title
    info[DB_ORDINAL] = ordinal 
    info[DB_PATH] = filename
    return info

def scan_media_files(filenames):
    file_infos = [scan_media_file(fn) for fn in filenames]
    return file_infos

def sort_media_files(file_infos):
    file_infos.sort(media_file_cmp)

def media_file_cmp(i1, i2):
    if i1[DB_ARTIST] > i2[DB_ARTIST]: return 1
    if i1[DB_ARTIST] < i2[DB_ARTIST]: return -1
    if i1[DB_ALBUM] > i2[DB_ALBUM]: return 1
    if i1[DB_ALBUM] < i2[DB_ALBUM]: return -1
    if i1[DB_ORDINAL] > i2[DB_ORDINAL]: return 1
    if i1[DB_ORDINAL] < i2[DB_ORDINAL]: return -1
    if i1[DB_TITLE] > i2[DB_TITLE]: return 1
    if i1[DB_TITLE] < i2[DB_TITLE]: return -1

    return 0      

def filter_items_regex(items, s, field=DB_DISPLAY):
    if len(s) == 0: return items
    try:
        rex = re.compile(s, re.IGNORECASE)
    except:
        return items
    p_items = []
    for i in items:
        if i[field] != None and rex.search(i[field]) != None:
            p_items.append(i)
    return p_items

def filter_items(items, s, field=DB_DISPLAY):
    if len(s) == 0: return items
    if s[0] == '+':
        try:
            field = int(s[1])
        except:
            field = DB_DISPLAY
        if field >= DB_ORDINAL: field = DB_DISPLAY
        s = s[2:]
        if len(s) == 0: return items
    if s[0] == '/': return filter_items_regex(items, s[1:], field)
    tokens = s.lower().split()
    p_items = items
    for t in tokens:
        n_items = []
        for i in p_items:
            if i[field] != None and t in i[field].lower():
                n_items.append(i)
        p_items = n_items
    return p_items

def main():
    global g_stats, g_file_db
    print 'Scanning files...'
    g_stats.scan_start = time.time()
    filenames = list_files(path='./media', file_specs=('.mp3',)) # for now only support mp3
    g_file_db = scan_media_files(filenames)
    sort_media_files(g_file_db)
    g_stats.scan_time = time.time() - g_stats.scan_start
    curses.wrapper(slap)

main()
