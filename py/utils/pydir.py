import os
cwd = os.getcwd()

drive, tail = os.path.splitdrive(cwd)
tail_split = tail.split(os.sep)

try:
    idx = tail_split.index('py')
    pydir = os.path.join(drive, os.sep, *tail_split[:(idx+1)])
except ValueError:
    # assume current working directory is parent of 'py', i.e. root of project
    pydir = os.path.join(drive, os.sep, *tail_split, 'py')

datadir = os.path.join(pydir, 'data')
