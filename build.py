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

import compiler, errno, glob, optparse, os, os.path, platform, shutil, stat, subprocess, sys

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
        if os.path.splitext(os.path.basename(src))[-1].lower() == '.py':
            file_check_python_syntax(src)
        shutil.copy(src, dst)
        return True
    return False

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

def file_check_python_syntax(name):
    compiler.parseFile(name)

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

def dir_copy_newer(src, dst):
    if file_is_newer(src, dst):
        shutil.copytree(src, dst)
        return True
    return False    

def mpg123_unix_build(mpg123_dir):
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

def mpg123_unix_clean(mpg123_dir):
    o_dir = os.getcwd()
    try:
        os.chdir(mpg123_dir)
        subprocess.check_call(['make', 'clean'], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)

def mpg123_windows_build(mpg123_dir, target='Release'):
    o_dir = os.getcwd()
    try:
        os.chdir(mpg123_dir)
        subprocess.check_call(['vcbuild', 'mpg123.vcproj', target], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)
    return os.path.join(mpg123_dir, target, 'mpg123.exe')    

def mpg123_windows_clean(mpg123_dir, target='Release'):
    o_dir = os.getcwd()
    try:
        os.chdir(mpg123_dir)
        subprocess.check_call(['vcbuild', '/c', 'mpg123.vcproj', target], stdout=sys.stdout, stderr=sys.stderr)
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

def wselect_build(wcurses_dir, target='Release'):
    o_dir = os.getcwd()
    try:
        os.chdir(wcurses_dir)
        subprocess.check_call(['vcbuild', 'wselect.vcproj', target], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)
    return os.path.join(wcurses_dir, target, '_wselect_c.pyd')    

def wselect_clean(wcurses_dir, target='Release'):
    o_dir = os.getcwd()
    try:
        os.chdir(wcurses_dir)
        subprocess.check_call(['vcbuild', '/c', 'wselect.vcproj', target], stdout=sys.stdout, stderr=sys.stderr)
    finally:
        os.chdir(o_dir)

def env_var_test():
    print 'Testing environment'
    env = {}
    env['PYTHON_INCLUDE'] = os.getenv('PYTHON_INCLUDE')
    env['PYTHON_LIB'] = os.getenv('PYTHON_LIB')
    for k, v in env.iteritems():
        if v:
            print k, '=', v
        else:
            print k, '?'
    if None in env.values():
        raise Exception, 'Missing environment variable'
    print 'Environment variables seem OK'

def env_msvc_test():
    print 'Testing MSVC environment'
    # do this by attempting to execute vcbuild
    subprocess.check_call(['vcbuild', '/?'], stdout=0, stderr=0)
    print 'MSVC environment seems to be OK'
    
        
# Steps:
# Create destination directories
# Copy Python code
# Build mpg123 if necessary
# copy mpg123 to build
# On Windows build wcurses and wselect and copy
def cmd_build():
    if platform.system() == 'Windows':
        env_var_test()
        env_msvc_test()
        
    print 'Creating directories'
    for d in dirs:
        if d[1] != '':
            dir_create(os.path.join(dir_base_dst, d[1]))

    print 'Copying source files'
    for d in dirs:
        if len(d[2]) == 0: continue
        for f in d[2]:
            filenames = glob.glob(os.path.join(dir_base_src, d[0], f))
            for filename in filenames:
                print filename,
                if os.path.isdir(filename):
                    a = dir_copy_newer(filename, os.path.join(dir_base_dst, d[1], os.path.basename(filename)))
                else:
                    a = file_copy_newer(filename, os.path.join(dir_base_dst, d[1], os.path.basename(filename)))
                if a:
                    print '\t\t(copied)'
                else:
                    print '\t\t(skipped)'

    if platform.system() == 'Windows':
        mpg123_filename_src = 'mpg123.exe'
        mpg123_filename_dst = 'mpg123-%s.exe' % (platform.system())
    else:
        mpg123_filename_src = 'mpg123'
        mpg123_filename_dst = 'mpg123-%s' % (platform.system())
    mpg123_binary_path_dst = os.path.join(dir_base_dst, 'player', mpg123_filename_dst)
    print 'Searching for existing mpg123 in path'
    mpg123_binary_path_src = file_binary_find(mpg123_filename_src)
    if mpg123_binary_path_src != None:
        print 'Copying system mpg123'
    else:
        print 'Building mpg123'
        if platform.system() == 'Windows':
            mpg123_dir = os.path.join(dir_base_src, 'mpg123-win')
            mpg123_binary_path_src = mpg123_windows_build(mpg123_dir)
        else:
            mpg123_dir = os.path.join(dir_base_src, 'mpg123')
            mpg123_binary_path_src = mpg123_unix_build(mpg123_dir)
    file_copy_newer(mpg123_binary_path_src, mpg123_binary_path_dst)

    if platform.system() == 'Windows':
        print 'Building wcurses'
        wcurses_dir = os.path.join(dir_base_src, 'mcurses', 'wcurses')
        wcurses_binary_path_src = wcurses_build(wcurses_dir)
        wcurses_binary_path_dst = os.path.join(dir_base_dst, 'mcurses', os.path.basename(wcurses_binary_path_src)) 
        file_copy_newer(wcurses_binary_path_src, wcurses_binary_path_dst)

        print 'Building wselect'
        wselect_dir = os.path.join(dir_base_src, 'mselect', 'wselect')
        wselect_binary_path_src = wselect_build(wselect_dir)
        wselect_binary_path_dst = os.path.join(dir_base_dst, 'mselect', os.path.basename(wselect_binary_path_src)) 
        file_copy_newer(wselect_binary_path_src, wselect_binary_path_dst)
    
def cmd_clean():
    if platform.system() == 'Windows':
        env_msvc_test()
    if platform.system() == 'Windows':
        print 'Cleaning wselect workspace'
        wselect_dir = os.path.join(dir_base_src, 'mselect', 'wselect')
        wselect_clean(wselect_dir)
        print 'Cleaning wcurses workspace'
        wcurses_dir = os.path.join(dir_base_src, 'mcurses', 'wcurses')
        wcurses_clean(wcurses_dir)    
    print 'Cleaning mpg123 workspace'
    if platform.system() == 'Windows':
        mpg123_dir = os.path.join(dir_base_src, 'mpg123-win')
        mpg123_binary_path_src = mpg123_windows_clean(mpg123_dir)
    else:
        mpg123_dir = os.path.join(dir_base_src, 'mpg123')
        mpg123_unix_clean(mpg123_dir)
    print 'Deleting files in build area'
    for d in dirs:
        if d[1] != '':
            shutil.rmtree(os.path.join(dir_base_dst, d[1]), ignore_errors=True)
    if dir_base_dst != './': # XXX don't nuke a USB build (when invoked with --mpg123-only)       
        for f in os.listdir(dir_base_dst):
            try: # try/except to skip CVS/.svn directories
                os.unlink(os.path.join(dir_base_dst, f))
            except:
                pass

dir_base_src = './src'
dir_base_dst = './build'

# source, destination, files to copy
dirs = [('slap', '', ('*.py',)),
        ('mcurses', 'mcurses', ('*.py',)),
        ('mselect', 'mselect', ('*.py',)),
        ('mutagen', 'mutagen', ('*.py',)),
        ('', 'player', []),
        ('', 'media', []),
       ] 


cmds = {'build': cmd_build, 'clean': cmd_clean}

parser = optparse.OptionParser()
parser.add_option('-t', '--target', dest='target', default='Release',
                  help='Windows target (Release/Debug)')
parser.add_option('-w', '--with-source', dest='with_source', action='store_true', default=False,
                  help='Copy mpg123 source and build.py to build directory')
parser.add_option('-m', '--mpg123-only', dest='mpg123_only', action='store_true', default=False,
                  help='Apply only to mpg123 on USB (*nix only). USB image must have been created with --with-source flag')
parser.add_option('-u', '--with-util', dest='with_util', action='store_true', default = False,
                  help='Copy utilities to build directory')
(options, args) = parser.parse_args()

if options.mpg123_only and platform.system() == 'Windows':
    raise Exception, 'mpg123 build on USB is not supported on Windows'

if options.mpg123_only and options.with_source:
    raise Exception, '--mpg123-only and --with-source are mutually exclusive options'

if options.mpg123_only:
    dir_base_dst = './'
    dirs = []

if options.with_source:
    dirs.append(('..', '', ('build.py',)))
    dirs.append(('', 'src', ('mpg123',)))

if options.with_util:
    dirs.append((os.path.join('..','util'), '', ('*.py',)))

if len(args) == 0:
    cmd_arg = 'build'
else:    
    cmd_arg = args[0]
    
cmds[cmd_arg]()
print '\nOK'
