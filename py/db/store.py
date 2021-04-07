#!/usr/bin/env python
# coding: utf-8

import json
import copy
import redis
from os import getenv
from utils import read

epfl = read.read_json_processed('epfl')
courses = read.read_json_processed('courses')
links = read.read_json('req-links', 'labelled')

# filter out links that reference courses
# that are not there any more
courseslugs = epfl['courses']
links = [
    l for l in links
    if l['source'] in courseslugs and l['target'] in courseslugs
]



# course dicts with only necessary fields for display and filtering
minimal_keys = ('slug', 'code', 'name', 'section', 'semester', 'credits')
courses_minimal = [dict((k, c[k]) for k in minimal_keys) for c in courses]



def resolve_slugs(slugs, ingoing=False, outgoing=False):
    # the courses listed in `slugs` are by default not
    # part of the neighborhood
    return [
        {**c, 'ingoingNeighbor': ingoing, 'outgoingNeighbor': outgoing}
        for c in courses_minimal
        if c['slug'] in slugs
    ]



def filter_links(slugs):
    return [
        l for l in links
        if l['source'] in slugs or l['target'] in slugs
    ]



def get_neighborhood(slugs):
    links_filtered = filter_links(slugs)

    ingoing_links = [
        l for l in links_filtered
        if l['source'] not in slugs and l['target'] in slugs
    ]
    outgoing_links = [
        l for l in links_filtered
        if l['target'] not in slugs and l['source'] in slugs
    ]
    subgraph_links = [
        l for l in links_filtered
        if l not in ingoing_links and l not in outgoing_links
    ]
    ingoing_slugs = [l['source'] for l in ingoing_links]
    outgoing_slugs = [l['target'] for l in outgoing_links]

    ingoing_courses = resolve_slugs(ingoing_slugs, ingoing=True)
    outgoing_courses = resolve_slugs(outgoing_slugs, outgoing=True)

    for cin in ingoing_courses:
        for cout in outgoing_courses:
            if cin['slug'] == cout['slug']:
                # Course is part of both ingoing and outgoing neighborhoods
                cin['ingoingNeighbor'] = True
                cin['outgoingNeighbor'] = True
                cout['ingoingNeighbor'] = True
                cout['outgoingNeighbor'] = True

    return {
        'ingoingCourses': ingoing_courses,
        'outgoingCourses': outgoing_courses,
        'ingoingLinks': ingoing_links,
        'outgoingLinks': outgoing_links,
        'subgraphLinks': subgraph_links
    }



def get_filters(courses):
    return {
        'filters': {
            'section': sorted({ c['section'] for c in courses }),
            'semester': sorted({ c['semester'] for c in courses }),
            'credits': sorted({ c['credits'] for c in courses })
        }
    }



redis_url = getenv("REDIS_URL")
redis_url = redis_url if redis_url else 'redis://@localhost:6379'

r = redis.Redis(ssl_cert_reqs=None).from_url(redis_url)

def redis_key(*slugs, prefix_slug = 'epfl'):
    return '_'.join([prefix_slug, *slugs])

def redis_set(key, data_dict):
    r.set(key, json.dumps(data_dict))


# navigation info (for Vuetify treeview component)
nav = [
    {
        'id': l['slug'],
        'name': l['title'],
        'params': {
            'level': l['slug'],
            'program': None,
            'specialization': None
        },
        'children': [
            {
                'id': f"{l['slug']}-{p['slug']}",
                'name': p['title'],
                'params': {
                    'level': l['slug'],
                    'program': p['slug'],
                    'specialization': None
                },
                'children': [
                    {
                        'id': f"{l['slug']}-{p['slug']}-{s['slug']}",
                        'name': s['title'],
                        'params': {
                            'level': l['slug'],
                            'program': p['slug'],
                            'specialization': s['slug']
                        }
                    }
                    for s in p['specializations']
                ]
                if l['slug'] == 'master' else []
            }
            for p in l['programs']
        ]
    }
    for l in epfl['levels']
]
redis_set(redis_key(prefix_slug = 'nav'), nav)

# root data object
# need to create a deep copy since we delete level['programs']
cepfl = copy.deepcopy(epfl)
cepfl_slugs = cepfl['courses']
cepfl['courses'] = resolve_slugs(cepfl_slugs)
cepfl = {
    'title': 'All courses',
    **cepfl,
    'ingoingCourses': [],
    'outgoingCourses': [],
    'ingoingLinks': [],
    'outgoingLinks': [],
    'subgraphLinks': links,
    **get_filters(cepfl['courses'])
}

for level in cepfl['levels']:
    del level['programs']

redis_set(redis_key(), cepfl)



for level in epfl['levels']:
    clevel = level
    if level['slug'] == 'master':
        # need to create a deep copy since we delete a property
        clevel = copy.deepcopy(level)
        for p in clevel['programs']:
            del p['specializations']

    clevel_slugs = clevel['courses']
    clevel['courses'] = resolve_slugs(clevel_slugs)

    clevel = {
        **clevel,
        **get_neighborhood(clevel_slugs),
        **get_filters(clevel['courses'])
    }

    key = redis_key(level['slug'])
    redis_set(key, clevel)

    for program in level['programs']:
        program_slugs = program['courses']
        program['courses'] = resolve_slugs(program_slugs)

        program = {
            **program,
            **get_neighborhood(program_slugs),
            **get_filters(program['courses'])
        }

        key = redis_key(level['slug'], program['slug'])
        redis_set(key, program)

        if level['slug'] == 'master':
            for specialization in program['specializations']:
                specialization_slugs = specialization['courses']
                specialization['courses'] = resolve_slugs(specialization_slugs)
                specialization = {
                    **specialization,
                    **get_neighborhood(specialization_slugs),
                    **get_filters(specialization['courses'])
                }

                key = redis_key(level['slug'], program['slug'], specialization['slug'])
                redis_set(key, specialization)


for course in courses:
    key = redis_key(course['slug'], prefix_slug='course')
    redis_set(key, course)
