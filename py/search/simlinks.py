import sys

import pandas as pd
from numpy import nan
from search import helpers

stdin1, stdin2 = sys.stdin.readline().split('#')

similarity_threshold = int(float(stdin1) * 100)
slugs = stdin2.split(',')

index = helpers.load_df('index')

df = (
    pd.DataFrame.sparse.from_spmatrix(
        helpers.load_sparsemat(f'sim{similarity_threshold}'),
        index=index.rename('source'),
        columns=index.rename('target')
    )
    .astype(pd.SparseDtype('float', nan))
)

# Filter out courses which don't match provided slugs
boolean_index = index.isin(slugs).values
df = df.loc[boolean_index, boolean_index]

# pair row and column indices (ignores NaNs)
df = df.stack().sparse.to_dense().rename('similarity').reset_index()
df['id'] = df.source + '--' + df.target

print(df.to_json(orient='records'))
