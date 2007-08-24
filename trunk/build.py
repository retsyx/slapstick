# Copyright (C) 2007 xyster.net
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id: build.py $

# script to gather and layout Python source files in the build directory along with potentially
# building mpg123 and Windows extensions.
# XXX This is a giant hack. No effort has been made to make it maintainable.
# XXX maybe this can be more cleanly implemented as a setup.py script?
# XXX currently no provisions for Windows build

import errno, glob, os, os.path, platform, shutil, stat, subprocess, sys

def dir_create(path):
    pass

def file_is_newer(src, dst):
    src_stat = os.stat(src)
    try:
        dst_stat = os.stat(dst)
    except:
        return True
    return src_stat[stat.ST_MTIME] > dst_stat[stat.ST_MTIME]
        
def file_copy_newer(src, dst):
    if file_is_newer(src, dst):
        shutil.copy(src, dst)
        return True
    return False

def dir_create(dir):
    try:
        os.mkdir(dir)
    except OSError, e:
        if e.errno != errno.EEXIST: raise
        
def dir_delete(dir):
    try:
        os.rmdir(dir)
    except OSError, e:
        if e.errno != errno.ENOENT: raise

def file_binary_find(name):
    path_var = 'PATH'
    if path_var not in os.environ.keys():
        return None
    dirs = os.environ[path_var].split(os.path.pathsep)
    for d in dirs:
        full_path = os.path.join(d, name)
        try:
            os.stat(full_path)
        except:
            continue
        return full_path
    return None    

def mpg123_build(mpg123_dir):
    o_dir = os.getcwd()
    try:
        os.chdir(mpg123_dir)
        # only run configure if it is newer than the Makefile
        if file_is_newer('configure', 'Makefile'):
            subprocess.check_call(['./configure'], stdout=sys.stdout, stderr=sys.stderr)
        subprocess.check_call(['make'], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)
    return os.path.join(mpg123_dir, 'src', 'mpg123')

def mpg123_clean(mpg123_dir):
    o_dir = os.getcwd()
    try:
        os.chdir(mpg123_dir)
        subprocess.check_call(['make', 'clean'], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)
    
def wcurses_build(wcurses_dir, target='Release'):
    o_dir = os.getcwd()
    try:
        os.chdir(wcurses_dir)
        subprocess.check_call(['vcbuild', 'wcurses.vcproj', target], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)
    return os.path.join(wcurses_dir, target, '_wcurses_c.pyd')    

def wcurses_clean(wcurses_dir, target='Release'):
    o_dir = os.getcwd()
    try:
        os.chdir(wcurses_dir)
        subprocess.check_call(['vcbuild', '/c', 'wcurses.vcproj', target], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)
# Steps:
# Create destination directories
# Copy Python code
# Build mpg123 if necessary
# copy mpg123 to build
# On Windows build wcurses and wselect and copy
def cmd_build():
    print 'Creating directories'
    for d in dirs:
        if d[1] != '':
            dir_create(os.path.join(dir_base_dst, d[1]))

    print 'Copying Python files'
    for d in dirs:
        if len(d[2]) == 0: continue
        for f in d[2]:
            filenames = glob.glob(os.path.join(dir_base_src, d[0], f))
            for filename in filenames:
                file_copy_newer(filename, os.path.join(dir_base_dst, d[1], os.path.basename(filename))) 
    
    mpg123_filename = 'mpg123-%s' % (platform.system())
    mpg123_binary_path_dst = os.path.join(dir_base_dst, 'player', mpg123_filename)
    print 'Searching for existing mpg123 in path'
    mpg123_binary_path_src = file_binary_find('mpg123')
    if mpg123_binary_path_src != None:
        print 'Copying system mpg123'
    else:
        print 'Building mpg123'
        mpg123_dir = os.path.join(dir_base_src, 'mpg123')
        mpg123_binary_path_src = mpg123_build(mpg123_dir)
    file_copy_newer(mpg123_binary_path_src, mpg123_binary_path_dst)

    if platform.system() == 'Windows':
        print 'Building wcurses'
        wcurses_dir = os.path.join(dir_base_src, 'mcurses', 'wcurses')
        wcurses_binary_path_src = wcurses_build(wcurses_dir)
        wcurses_binary_path_dst = os.path.join(dir_base_dst, 'mcurses', os.path.basename(wcurses_binary_path_src)) 
        file_copy_newer(wcurses_binary_path_src, wcurses_binary_path_dst)
        wcurses_py_path_src = os.path.join(wcurses_dir, 'wcurses_c.py')
        wcurses_py_path_dst = os.path.join(dir_base_dst, 'mcurses', 'wcurses_c.py')
        file_copy_newer(wcurses_py_path_src, wcurses_py_path_dst)
    
def cmd_clean():
    print 'Cleaning wcurses workspace'
    wcurses_dir = os.path.join(dir_base_src, 'mcurses', 'wcurses')
    wcurses_clean(wcurses_dir)    
    print 'Cleaning mpg123 workspace'
    mpg123_dir = os.path.join(dir_base_src, 'mpg123')
    mpg123_clean(mpg123_dir)
    print 'Deleting files in build area'
    for d in dirs:
        if d[1] != '':
            shutil.rmtree(os.path.join(dir_base_dst, d[1]), ignore_errors=True)
    for f in os.listdir(dir_base_dst):
        try: # try/except to skip CVS/.svn directories
            os.unlink(os.path.join(dir_base_dst, f))
        except:
            pass
    
dir_base_src = './src'
dir_base_dst = './build'

# source, destination, files to copy
dirs = (('slap', '', ('*.py',)),
        ('mcurses', 'mcurses', ('*.py',)),
        ('mselect', 'mselect', ('*.py',)),
        ('mutagen', 'mutagen', ('*.py',)),
        ('', 'player', []),
        ('', 'media', []),
       ) 


cmds = {'build': cmd_build, 'clean': cmd_clean}

if len(sys.argv) == 1:
    cmd_arg = 'build'
else:    
    cmd_arg = sys.argv[1]
    
cmds[cmd_arg]()
print '\nOK'
