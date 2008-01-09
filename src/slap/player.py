# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: player.py $

# Player - simple wrapper class to control mpg123 -R
# PlayerController - simple tracklist player controller

import os
import platform
import subprocess

STOPPED, PAUSED, PLAYING = range(3)

def secs_to_tuple(s):
    secs = long(float(s))
    h = secs/3600
    secs %= 3600
    m = secs/60
    secs %= 60
    return h, m , secs

class Player(object):
    def __init__(self):
        self.pn = 'player/mpg123-%s' % (platform.system()), '-R'
        self.p = subprocess.Popen(self.pn, 
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        self.__time_left = (0L, 0L, 0L)
        self.__time_elapsed = (0L, 0L, 0L)
        self.__status = STOPPED
    def __del__(self):
        self.p.stdin.write('Q\n')
        self.p.stdout.close()
        self.p.stdin.close()
        self.p.wait()
    def fd(self):
        return self.p.stdout
    def update(self):
        l = self.p.stdout.readline()
        sl = l.split()
        if sl[0] == '@F':
            self.__time_elapsed = sl[3]
            self.__time_left = sl[4]
        elif sl[0] == '@P':
            if sl[1] == '0':
                self.__status = STOPPED
            elif sl[1] == '1':
                self.__status = PAUSED
            elif sl[1] == '2':
                self.__status = PLAYING
    def play(self, filename):
        self.p.stdin.write('L %s\n' % (filename))
    def pause(self):
        self.p.stdin.write('P\n')
    def stop(self):
        self.p.stdin.write('S\n')
    def status(self):
        return self.__status
    def time_elapsed(self): 
        return secs_to_tuple(self.__time_elapsed)
    def time_left(self): 
        return secs_to_tuple(self.__time_left)

class PlayerController(object):
    def __init__(self, max_history=100):
        self.player = Player()
        self.track_list = []
        self.position = -1
        self.ignore_stop = 0
        self.max_history = max_history

    def fd(self): return self.player.fd()

    def update(self):
        old_status = self.player.status()
        self.player.update()
        new_status = self.player.status()
        if old_status != new_status and new_status == STOPPED:
            if self.ignore_stop:
                self.ignore_stop = 0
            else:    
                self.next_track()
                return True
        return False    

    def start_track_list(self, track_list):
        """ Immediately start playing track list """
        if self.player.status() != STOPPED: self.ignore_stop = 1
        self.player.stop()
        self.position = len(self.track_list) - 1
        self.track_list.extend(track_list)
        if len(track_list) == 0: return
        self.next_track()

    def queue_track_list(self, track_list):
        """ Queue track list after currently playing track list """
        if len(track_list) == 0: return
        if self.player.status() == STOPPED: 
            self.start_track_list(track_list)
            return
        self.track_list.extend(track_list)

    def delete_track_list(self, track_list):
        old_status = self.player.status()
        stopped = False
        for t in track_list:
            if t in self.track_list:
                i = self.track_list.index(t)
                # if the track is the currently playing track, we need to stop
                # playback. It will be resumed at the next available track later.
                # If the track being deleted is in the list before the currently
                # playing track, the current track position needs to be decremented
                if i == self.position and self.player.status() != STOPPED and not stopped:
                    self.player.stop()
                    self.ignore_stop = 1
                    stopped = True
                    self.position -= 1 # next track will bring us back
                elif i < self.position:
                    self.position -= 1
                self.track_list.remove(t)
        # Make sure position makes sense (in case last track in list was playing and got
        # deleted)     
        if self.position >= len(self.track_list):
            self.position = len(self.track_list) - 1
        if stopped:
            if old_status == PAUSED and stopped:
                self.next_track()
                self.pause()
            elif old_status == PLAYING and stopped:
                self.next_track()
            
    def next_track(self):
        if self.position >= len(self.track_list)-1: return
        self.position += 1
        self.clean_old_tracks()
        self.player.play(self.track_list[self.position][-1])

    def previous_track(self):
        if self.position == 0: return
        self.position -= 1
        self.player.play(self.track_list[self.position][-1])

    def goto_track(self, n):
        if n < 0:
            n = 0
        elif n >= len(self.track_list):
            n = len(self.track_list) - 1
        self.position = n
        self.clean_old_tracks()
        self.player.play(self.track_list[self.position][-1])
            
    def clean_old_tracks(self):
        if self.position >= self.max_history:
            del self.track_list[:self.position-self.max_history+1]
            self.position = self.max_history-1    
        
    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()
        self.player.ignore_stop = 1
        self.position = -1
