import re
from string import punctuation
from os import path

from utils.pydir import datadir

from scipy import sparse
import pickle

from pandas import read_pickle as pd_read_pickle
from pandas import to_pickle as pd_to_pickle

import nltk
from nltk.corpus import stopwords
nltk.download('stopwords', quiet=True)
stopwords_en_fr = stopwords.words('french') + stopwords.words('english')

def datadir_join(filepath):
    return path.join(datadir, filepath)

def picklefile(filename):
    return datadir_join(f'{filename}.pickle')


duplicate_space_regex = re.compile(r'\s{2,}')
def clean_text(text):
    # remove punctuation
    text = "".join([ch if ch not in punctuation else ' ' for ch in text])
    text = duplicate_space_regex.sub(' ', text)
    text = text.strip().lower()
    text = " ".join([w for w in text.split() if w not in stopwords_en_fr])
    return text



def save_sparsemat(mat, filename):
    sparse.save_npz(datadir_join(filename), mat)
    
def load_sparsemat(filename):
    return sparse.load_npz(datadir_join(filename) + '.npz')

def save_pickle(obj, filename):
    pickle.dump(obj, open(picklefile(filename), 'wb'))
    
def load_pickle(filename):
    return pickle.load(open(picklefile(filename), 'rb'))

def save_df(df, filename):
    pd_to_pickle(df, picklefile(filename))
    
def load_df(filename):
    return pd_read_pickle(picklefile(filename))
