import sys

if len(sys.argv) < 3:
    raise ValueError('Some arguments are missing')

from operator import itemgetter

from sklearn.metrics.pairwise import linear_kernel

from search import helpers

tfidf = helpers.load_pickle('tfidf')
courses_df = helpers.load_df('courses_df')
features = helpers.load_sparsemat('features')

def search(query, tfidf, features, topk, threshold=0.1):
    query_features = tfidf.transform([query])
    cosine_similarities = linear_kernel(query_features, features).flatten()
    related_docs_indices, cos_sim_sorted = zip(
        *sorted(enumerate(cosine_similarities), key=itemgetter(1), reverse=True)
    )

    cutoff_index = 0
    for i, cos_sim in enumerate(cos_sim_sorted):
        if cos_sim < threshold or i == topk:
            cutoff_index = i
            break
    doc_ids = related_docs_indices[:cutoff_index]
    similarities = [round(s, 2) for s in cos_sim_sorted[:cutoff_index]]
    return doc_ids, similarities


topk = sys.argv[1]
try:
    topk = int(topk)
except:
    raise TypeError('topk query parameter should be an integer')
    
query = ' '.join(sys.argv[2:])

ids, similarities = search(query, tfidf, features, topk)
result_df = courses_df.loc[list(ids), ['slug', 'name', 'keywords']]
result_df.insert(0, "cosine_similarity", similarities, True) 

output = result_df.to_json(orient='records')

print(output)
