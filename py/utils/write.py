import os
import json
from utils.pydir import datadir

def create_dirs(path):
    # Create path if it does not exist
    os.makedirs(os.path.dirname(path), exist_ok=True)


def write_df_processed(filename, dataframe, orient='records', indent=2):
    path = os.path.join(datadir, 'processed', f'{filename}.json')
    create_dirs(path)
    """Writes Pandas @dataframe to a json file @filename"""
    dataframe.to_json(path, orient=orient, indent=indent)


def write_object(filename, obj, subdir='raw', indent=2):
    """Writes the @obj to a processed json data file @filename"""
    path = os.path.join(datadir, subdir, f'{filename}.json')
    create_dirs(path)
    with open(path, 'w') as json_file:
        json.dump(obj, json_file, indent=indent)


def write_object_raw(filename, obj):
    write_object(filename, obj, subdir='raw')
