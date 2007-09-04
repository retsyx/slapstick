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
import fnmatch, os, socket, re, sys, threading, time
import mutagen, mutagen.easyid3
import player
from mcurses import textbox

VERSION = 2

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

# key map format is
# keys, function, parameter
class wObject(object):
    def _prepare_key_map(self, map):
        for entry in map:
            keys = entry[0]
            for i in xrange(len(keys)):
                k = keys[i]
                if type(k) == str:
                    keys[i] = ord(k)
    def _dispatch_key(self, map, key_code):
        for entry in map:
            keys, fn, param = entry
            if key_code in keys:
                if param == None:
                    fn()
                else:    
                    fn(eval(param))
                return True
        return False       
    def invalidate(self):
        self.scr.touchwin()
    def refresh(self):
        self.scr.noutrefresh()
        
class wDialog(wObject):
    maybe, no, yes = range(3)
    def __init__(self, scr, text):
        self.scr = scr
        self.text = text
        self.result = wDialog.maybe
        self.key_map = \
         [[['Y', 'y', 'N', 'n', curses.ascii.ESC], self.quit, 'key_code'],
         ]
        self._prepare_key_map(self.key_map)
    def draw(self):
        self.scr.box()
        yx = self.scr.getmaxyx()
        self.scr.addstr(yx[0]/2, (yx[1]-len(self.text))/2, self.text)
        action_text = 'Yes/No?'
        self.scr.addstr(yx[0]-2, (yx[1]-len(action_text))/2, action_text)
    def dispatch_key(self, key_code):
        return self._dispatch_key(self.key_map, key_code)
    def quit(self, key_code):
        if key_code in ('Y', 'y'):
            self.result = wDialog.yes
        else:
            self.result = wDialog.no
            
class wList(wObject):
    MODE_SELECT, MODE_VIEW = range(2)
    def __init__(self, scr):
        self.scr = scr
        self.items = []
        self.mode = self.MODE_SELECT
        self.cursor = 0
        self.hilite = 0
        self.view_offset = 0
        self.text_offset = 0
        self.size = 0, 0
        self.grok_size()
        # key map: keys, function, parameter
        self.key_map_all = \
        [[['s', 'S', curses.KEY_LEFT], self.text_offset_move, '-5'],
         [['d', 'D', curses.KEY_RIGHT], self.text_offset_move, '5'],
        ]
        self.key_map_select = \
        [[['a', curses.KEY_UP], self.cursor_move, '-1'],
         [['A', curses.KEY_PPAGE], self.cursor_move, '-self.size[1]'],
         [['z', curses.KEY_DOWN], self.cursor_move, '1'],
         [['Z', curses.KEY_NPAGE], self.cursor_move, 'self.size[1]'],
        ]
        self.key_map_view = \
        [[['a', curses.KEY_UP], self.view_move, '-1'],
         [['A', curses.KEY_PPAGE], self.view_move, '-self.size[1]'],
         [['z', curses.KEY_DOWN], self.view_move, '1'],
         [['Z', curses.KEY_NPAGE], self.view_move, 'self.size[1]'],
        ] 
        [self._prepare_key_map(map) for map in (self.key_map_all, self.key_map_select, self.key_map_view)]
        
    def grok_size(self):
        old_size = self.size
        y, x = self.scr.getmaxyx()
        self.size = x, y
        return self.size != old_size

    def set_items(self, items):
        if len(items) <= self.cursor:
            self.cursor = len(items)-1
        if len(items) <= self.hilite:
           self.hilite = len(items)-1
        if self.cursor < 0 and len(items) > 0:
            self.cursor = 0
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
        if self.mode == wList.MODE_SELECT:
            bi = self.cursor - self.hilite
            if bi < 0: bi = 0
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
        bi = ei - bi
        ei = self.size[1]
        if bi >= 0:
            for i in xrange(bi, ei):
                self.scr.move(i, 0)
                self.scr.clrtoeol()
            
    def dispatch_key(self, key_code):
        s = self._dispatch_key(self.key_map_all, key_code)
        if s:
            self.draw()
            return s
        if self.mode == wList.MODE_SELECT:
            key_map = self.key_map_select
        else:
            key_map = self.key_map_view
        s = self._dispatch_key(key_map, key_code)
        if s:
            self.draw()
        return s    

class wTextBox(wObject):
    def __init__(self, scr):
       self.scr = scr
       self.box = textbox.Textbox(self.scr)
       self.box.stripspaces = False
       self.key_map = []
    def clear(self):
        self.box.clear()
    def dispatch_key(self, key_code):
        if self._dispatch_key(self.key_map, key_code): return True
        self.box.edit_one(key_code)
        return True
    def draw(self):
        self.box.draw()
    def text(self):
        return self.box.gather()
            
class wSearchList(wObject):
    def __init__(self, scr, id=None, item_filter=None, item_sort=None):
        self.scr = scr
        self.id = id
        self.items = []
        self.item_filter = item_filter
        self.item_sort = item_sort
        scr_maxxy = list(scr.getmaxyx())
        scr_maxxy.reverse()
        if id == None:
            box_off = (0, 0)
        else:
            box_off = (2, 0)
        box_size = (scr_maxxy[0] - box_off[0], 1)
        box_scr = scr.derwin(box_size[1], box_size[0], box_off[1], box_off[0])
        self.text_box = wTextBox(box_scr)
        list_off = (0, 1)
        list_size = (scr_maxxy[0], scr_maxxy[1] - list_off[1])
        list_scr = scr.derwin(list_size[1], list_size[0], list_off[1], list_off[0])
        self.list = wList(list_scr)
        self.MODE_LIST, self.MODE_SEARCH = range(2)
        self.mode = self.MODE_LIST
        self.key_map_list = \
        [[['/'], self.mode_search, None],
         [[curses.ascii.ESC], self.clear_search, None],
        ]
        self.key_map_search = \
        [[[curses.ascii.ESC, curses.ascii.NL, curses.ascii.CR], self.mode_list, 'key_code'],
         [[curses.KEY_UP, curses.KEY_DOWN, curses.KEY_PPAGE, curses.KEY_NPAGE], self.list.dispatch_key, 'key_code'],
         [[curses.ascii.DEL, curses.KEY_BACKSPACE], self.text_box.dispatch_key, 'curses.ascii.BS'],
        ]
        [self._prepare_key_map(map) for map in (self.key_map_list, self.key_map_search)]

    def clear_search(self):
        self.text_box.clear()
        self._update_items()

    def invalidate(self):
        self.scr.touchwin()
        self.text_box.invalidate()
        self.list.invalidate()
        
    def mode_search(self):
        self.mode = self.MODE_SEARCH
    
    def mode_list(self, method):
        if method == curses.ascii.ESC:
            self.clear_search()
        self.mode = self.MODE_LIST
        
    def set_items(self, items):
        old_items = self.items
        self.items = items
        if old_items != self.items:
            self.list.set_items(items)
            self.list.cursor_move_absolute(0)
            self.text_box.clear()
            self._update_items()
            
    def add_items(self, items):
        self.items.extend(items)
        if self.item_sort:
            self.item_sort(self.items)
        self._update_items()
        
    def remove_items(self, items):
        for i in items:
            self.items.remove(i)
        if self.item_sort:
            self.item_sort(self.items)
        self._update_items()
    
    def set_list_mode(self, mode):
        self.list.mode = mode
    
    def cursor_move_absolute(self, off):
        self.list.cursor_move_absolute(off)

    def get_cursor(self):
        return self.list.cursor
    
    def view_center(self, off=None):
        self.list.view_center(off)
        
    def get_active_items(self):
        return self.list.items
        
    def _update_items(self):
        text = self.text_box.text()
        if self.item_filter:
            self.list.set_items(self.item_filter(self.items, text))
    
    def draw(self):
        self.list.draw()
        self.text_box.draw()
        if self.id != None:
            if self.mode == self.MODE_LIST:
                if self.items == self.list.items:
                    self.scr.addch(0, 0, self.id, curses.A_NORMAL)
                else:
                    self.scr.addch(0, 0, self.id, curses.A_STANDOUT)
            else: # self.mode == self.MODE_SEARCH
                self.scr.addch(0, 0, self.id, curses.A_NORMAL | curses.A_BOLD)

    def refresh(self):
        self.scr.noutrefresh()
        self.list.refresh()
        self.text_box.refresh()
    
    def dispatch_key(self, key_code):
        if self.mode == self.MODE_LIST:
            key_map = self.key_map_list
        else: # mode == self.MODE_SEARCH
            key_map = self.key_map_search
        if self._dispatch_key(key_map, key_code): return True
        if self.mode == self.MODE_LIST:
            return self.list.dispatch_key(key_code)
        else: # mode == self.MODE_SEARCH
            if self.text_box.dispatch_key(key_code): 
                self._update_items()
                return True
            return self.list.dispatch_key(key_code) # XXX at the moment text box always returns True so this never gets called
        
class wSlap(wObject):
    def __init__(self, scr, tracks):
        self.done = False
        self.player_controller = player.PlayerController()
        self.stats_init()
        self.scr = scr
        nof_modes = 7
        self.MODE_NONE, self.MODE_LIST, self.MODE_QUEUE, self.MODE_HELP, self.MODE_KEEP, self.MODE_KILL, self.MODE_STATS = range(nof_modes)
        self.mode = self.MODE_NONE
        self.mode_prev = self.MODE_NONE
        self.list = [None] * nof_modes
        alist = self.list[self.MODE_LIST] = wSearchList(self.scr, 'T', filter_items)
        alist.set_items(tracks) # load up tracks
        alist = self.list[self.MODE_QUEUE] = wSearchList(self.scr, 'Q', filter_items)
        alist.set_list_mode(wList.MODE_VIEW)
        alist = self.list[self.MODE_HELP] = wSearchList(self.scr, 'H', filter_items)
        alist.set_list_mode(wList.MODE_VIEW)
        alist = self.list[self.MODE_KEEP] = wSearchList(self.scr, 'J', filter_items, sort_media_files)
        alist.set_items(tracks[:]) # load up tracks
        alist = self.list[self.MODE_KILL] = wSearchList(self.scr, 'K', filter_items, sort_media_files)
        alist = self.list[self.MODE_STATS] = wSearchList(self.scr, '0', filter_items)
        alist.set_list_mode(wList.MODE_VIEW)
        self.help_print()
        self.key_map = \
        [[['T', 't'], self.enter_mode, 'self.MODE_LIST'],
         [['\t'], self.enter_mode, 'self.MODE_QUEUE'],
         [['H', 'h'], self.enter_mode, 'self.MODE_HELP'],
         [['J', 'j'], self.enter_mode, 'self.MODE_KEEP'],
         [['K', 'k'], self.enter_mode, 'self.MODE_KILL'],
         [['0'], self.enter_mode, 'self.MODE_STATS'],
         [['Q', 'q'], self.quit, None],
         [['N', 'n'], self.player_controller.next_track, None],
         [['B', 'b'], self.player_controller.previous_track, None],
         [[curses.ascii.SP], self.player_controller.pause, None],
         [[curses.ascii.NL, curses.ascii.CR], self.play_track_list, None],
         [["'", '"'], self.queue_track_list, None],
         [['\\', '|'], self.queue_track, None],
        ]
        self._prepare_key_map(self.key_map)
    
    def stats_init(self):
        self.stats = struct()
        self.stats.key_presses = 0

    def enter_mode(self, new_mode):
        if self.mode == new_mode:
            new_mode = self.mode_prev
        if new_mode == self.MODE_QUEUE:
            alist = self.list[new_mode]
            alist.set_items(self.player_controller.track_list)
            alist.view_center(self.player_controller.position)
        if new_mode == self.MODE_STATS:
            self.stats_print()
        self.mode_prev = self.mode    
        self.mode = new_mode
        self.list[self.mode].invalidate()
    
    def quit(self):
        self.done = True
    
    def play_track_list(self):
        alist = self.list[self.mode]
        cursor = alist.get_cursor()
        if cursor < 0: return
        items = alist.get_active_items()[cursor:]
        if self.mode == self.MODE_LIST:
            self.player_controller.start_track_list(items)
        elif self.mode == self.MODE_KEEP:
            blist = self.list[self.MODE_KILL]
            blist.add_items(items)
            alist.remove_items(items)
        elif self.mode == self.MODE_KILL:
            blist = self.list[self.MODE_KEEP]
            blist.add_items(items)
            alist.remove_items(items)
            
    def queue_track(self):
        alist = self.list[self.mode]
        cursor = alist.get_cursor()
        if cursor < 0: return
        items = [alist.get_active_items()[cursor]]
        if self.mode == self.MODE_LIST:
            self.player_controller.queue_track_list(items)
        elif self.mode == self.MODE_KEEP:
            blist = self.list[self.MODE_KILL]
            blist.add_items(items)
            alist.remove_items(items)
        elif self.mode == self.MODE_KILL:
            blist = self.list[self.MODE_KEEP]
            blist.add_items(items)
            alist.remove_items(items)
            
    def queue_track_list(self):
        alist = self.list[self.mode]
        cursor = alist.get_cursor()
        if cursor < 0: return
        items = alist.get_active_items()[cursor:]
        if self.mode == self.MODE_LIST:
            self.player_controller.queue_track_list(items)
        elif self.mode == self.MODE_KEEP:
            blist = self.list[self.MODE_KILL]
            blist.add_items(items)
            alist.remove_items(items)
        elif self.mode == self.MODE_KILL:
            blist = self.list[self.MODE_KEEP]
            blist.add_items(items)
            alist.remove_items(items)
    
    def dispatch_key(self, key_code):
        if self.list[self.mode].dispatch_key(key_code): return True
        return self._dispatch_key(self.key_map, key_code)
    
    def draw(self):
        alist = self.list[self.MODE_QUEUE]
        alist.cursor_move_absolute(self.player_controller.position)
        self.list[self.mode].draw()
                
    def refresh(self):
        self.list[self.mode].refresh()
        curses.doupdate()
        
    def run(self):
        self.enter_mode(self.MODE_LIST)
        self.draw()
        self.refresh()
        timeout = None
        while not self.done:
            sos = []
    
            sos.append(sys.stdin)
            sos.append(self.player_controller.fd())
            try:
                ri, ro, rerr = select.select(sos, [], [], timeout)
            except: # XXX force some window update logic here
                continue
            for so in ri:
                if so == sys.stdin:
                    self.stats.key_presses += 1
                    #key_code = self.scr.getch()
                    key_code = self.list[self.mode].text_box.scr.getch() # XXX
                    self.dispatch_key(key_code)
                    self.draw()
                    self.refresh()
                elif so == self.player_controller.fd():
                    if self.player_controller.update():
                        self.draw()
                        self.refresh()

    def stats_print(self):
        s = """
    Stats
    =====
    
    %d Release 
    %d files
    %.2fs to scan
    %d key presses
    %s running
    
""" % (VERSION, len(self.list[self.MODE_LIST].items), g_stats.scan_time, self.stats.key_presses, secs_to_str(time.time() - g_stats.scan_start))
        lines = s.split('\n')
        self.list[self.MODE_STATS].set_items(zip(lines, [0]*len(lines)))    

    def help_print(self):
        hlp = """

    Modes
    =====
    
    h/H           Help       (H) 
    t/T           Track List (T)
    <Tab>         Queue      (Q)
    0             Stats      (0)
    
    Controls
    ========

    q/Q           Quit
    <Space>       Pause/Unpause
    n/N           Play next track in queue
    b/B           Play previous track in queue
    
    /             Enter search mode
    <Esc>         Clear search filter
    a/<Up>        Scroll one line up/Move highlight one track up
    z/<Down>      Scroll one line down/Move highlight one track down
    A/<Page Up>   Scroll one page up/Move highlight one page up
    Z/<Page Down> Scroll one page down/Move highlight one page down
    s/S/<Left>    Scroll display to the left
    d/D/<Right>   Scroll display to the right
    
    Track List Mode
    ===============
    
    <Enter>       Start playing tracks starting with highlighted track
    \/|           Queue highlighted track
    '/"           Queue tracks starting with highlighted track
    
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

""" % (DB_ORDER_STR)
        lines = hlp.split('\n')
        self.list[self.MODE_HELP].set_items(zip(lines, [0]*len(lines)))

def slap(scr):
    global g_file_db
    app = wSlap(scr, g_file_db)
    app.run()
    
def filespec_match(split_filename, file_spec):
    if split_filename[1] == file_spec: return split_filename
    return ('', '')

def list_files(path='.', file_specs=()):
    all_filenames = []
    for root, dirs, files in os.walk(path):
        filenames = []
        for fspc in file_specs:
            filenames += fnmatch.filter(files, fspc)
        filenames = [os.path.join(root, fn) for fn in files]
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
            t = [tt for tt in [artist, album, title] if tt != None]
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
    if len(s) == 0 or len(items) == 0: return items
    if s[0] == '+':
        try:
            field = int(s[1])
        except:
            field = DB_DISPLAY
        if field >= DB_ORDINAL: field = DB_DISPLAY
        s = s[2:]
        if len(s) == 0: return items
    if field >= len(items[0]): field = DB_DISPLAY    
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

def secs_to_str(s):
    s = long(s)
    h = s / 3600
    s %= 3600
    m = s /60
    s %= 60
    return '%dh%02dm%02ds' % (h, m, s)
    
def main():
    global g_stats, g_file_db
    print 'Scanning files...'
    g_stats.scan_start = time.time()
    filenames = list_files(path='./media', file_specs=('*.mp3',)) # for now only support mp3
    g_file_db = scan_media_files(filenames)
    sort_media_files(g_file_db)
    g_stats.scan_time = time.time() - g_stats.scan_start
    curses.wrapper(slap)

main()
