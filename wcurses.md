Curses for Windows

# Introduction #

The Python distribution does not support curses on Windows because there is no native curses library for Windows. wcurses/mcurses is a curses implementation written to allow Slap to run with a curses interface on Windows.

# Details #

## mcurses ##

mcurses is a small wrapper that decides at runtime which curses library to import based on the running OS. If on Windows, mcurses will import wcurses, otherwise, it will import the Python distribution curses.

mcurses is a drop in replacement for the curses library. To use in your Python code, you would need to modify

`import curses`

to

`import mcurses as curses`


## wcurses ##

wcurses is a partial implementation of the curses library for Windows. It is currently complete enough to run the Python demo scripts life.py, rain.py and tclock.py (but not xmas.py) and Slap, of course. It has been lightly tested with other Python curses apps and appeared to work.

### Structure ###

wcurses is constructed out of a Python emulation layer (wcurses.py) and a simple Windows extension (`_`wcurses`_`c.pyd). All of the curses logic is in wcurses.py while the native C extension provides a minimal set of low level Windows console routines.. The advantage of this architecture is that enhancing wcurses is straight forward Python programming. For most functionality (with some exceptions), there is no need to deal with any low level Windows details.
An additional benefit of this architecture is runtime stability.

### Missing ###

wcurses does not implement:
  * panel class
  * some of the window class methods
  * some curses functions

The above are not implemented because Slap does not require them (Slap requires much less than is implemented). However, adding this functionality would be straight forward for those interested in implementing it (patches are welcome!).

## Where to get it ##

wcurses/mcurses is available as part of the Slap source code. You can browse the source here: http://slapstick.googlecode.com/svn/trunk/src/mcurses/




