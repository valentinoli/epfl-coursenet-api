import json
import os
from utils.pydir import datadir

def read_json(filename, subdir):
    """Reads the raw json data file @filename and returns a python object"""
    path = os.path.join(datadir, subdir, f'{filename}.json')
    with open(path) as file:
        return json.load(file)


def read_json_raw(filename):
    return read_json(filename, 'raw')

def read_json_processed(filename):
    return read_json(filename, 'processed')
