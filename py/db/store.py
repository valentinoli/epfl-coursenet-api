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



def resolve_slugs(slugs, incoming=False, outgoing=False):
    # the courses listed in `slugs` are by default not
    # part of the neighborhood
    return [
        {**c, 'incomingNeighbor': incoming, 'outgoingNeighbor': outgoing}
        for c in courses_minimal
        if c['slug'] in slugs
    ]



def filter_links(slugs):
    return [
        l for l in links
        if l['source'] in slugs or l['target'] in slugs
    ]



def compute_graph(slugs, subgraph_courses):
    links_filtered = filter_links(slugs)

    incoming_links = [
        l for l in links_filtered
        if l['source'] not in slugs and l['target'] in slugs
    ]
    outgoing_links = [
        l for l in links_filtered
        if l['target'] not in slugs and l['source'] in slugs
    ]
    subgraph_links = [
        l for l in links_filtered
        if l not in incoming_links and l not in outgoing_links
    ]
    incoming_slugs = [l['source'] for l in incoming_links]
    outgoing_slugs = [l['target'] for l in outgoing_links]

    incoming_courses = resolve_slugs(incoming_slugs, incoming=True)
    outgoing_courses = resolve_slugs(outgoing_slugs, outgoing=True)

    for cin in incoming_courses:
        for cout in outgoing_courses:
            if cin['slug'] == cout['slug']:
                # Course is part of both incoming and outgoing neighborhoods
                cin['incomingNeighbor'] = True
                cin['outgoingNeighbor'] = True
                cout['incomingNeighbor'] = True
                cout['outgoingNeighbor'] = True

    return {
        'graph': {
            'subgraphCourses': subgraph_courses,
            'incomingCourses': incoming_courses,
            'outgoingCourses': outgoing_courses,
            'subgraphLinks': subgraph_links,
            'incomingLinks': incoming_links,
            'outgoingLinks': outgoing_links
        }
    }



def compute_filters(courses):
    return {
        'filters': {
            'sections': sorted({ c['section'] for c in courses }),
            'semesters': sorted({ c['semester'] for c in courses }),
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


all_courses_title = 'All courses'
all_courses_slug = 'all-courses'

# navigation info for Vuetify treeview and autocomplete components
nav_treeview = [
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
                        'value': s['value'],
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

nav_autocomplete = [{
    'title': all_courses_title,
    'path': f"/{all_courses_slug}",
    'icon': 'mdi-all-inclusive'
},{
    'divider': True
}]
for l in epfl['levels']:
    nav_autocomplete.extend([{
        'title': l['title'],
        'path': f"/{l['slug']}",
        'icon': 'mdi-school-outline'
    },
    {
        'divider': True
    },
    {
        'header': f"{l['title']} Programs"
    }])
    for p_idx, p in enumerate(l['programs']):
        nav_autocomplete.append({
            'title': p['title'],
            'subtitle': l['title'],
            'path': f"/{l['slug']}/{p['slug']}",
            'icon': 'mdi-school'
        })

        if l['slug'] == 'master' and len(p['specializations']) > 0:
            nav_autocomplete.extend([{
                'divider': True
            },
            {
                'header': f"{p['title']} Master Specializations"
            }])
            for s in p['specializations']:
                nav_autocomplete.append({
                    'title': s['title'],
                    'subtitle': f"{p['title']} Master Specialization",
                    'path': f"/{l['slug']}/{p['slug']}/{s['slug']}",
                    'specializationValue': s['value']
                })

            nav_autocomplete.append({
                'divider': True
            })
    nav_autocomplete.append({
        'divider': True
    })

nav = {
    'treeview': [{
        'id': all_courses_slug,
        'name': all_courses_title,
        'params': {
            'level': all_courses_slug,
            'program': None,
            'specialization': None
        },
        'children': nav_treeview
    }],
    'autocomplete': nav_autocomplete
}
redis_set(redis_key(prefix_slug = 'nav'), nav)

# root data object
# need to create a deep copy since we delete level['programs']
cepfl = copy.deepcopy(epfl)
cepfl_slugs = cepfl['courses']
del cepfl['courses']
cepfl_courses = resolve_slugs(cepfl_slugs)

cepfl = {
    'entity': 'root',
    'subentityKey': 'levels',
    'title': all_courses_title,
    'slug': all_courses_slug,
    **cepfl,
    **compute_graph(cepfl_slugs, cepfl_courses),
    **compute_filters(cepfl_courses)
}

for level in cepfl['levels']:
    del level['programs']

redis_set(redis_key(), cepfl)
specializationsKey = 'specializations'
programsKey = 'programs'

for level in epfl['levels']:
    clevel = level
    if level['slug'] == 'master':
        # need to create a deep copy since we delete a property
        clevel = copy.deepcopy(level)
        for p in clevel[programsKey]:
            del p[specializationsKey]

    clevel_slugs = clevel['courses']
    del clevel['courses']
    clevel_courses = resolve_slugs(clevel_slugs)

    clevel = {
        'entity': 'level',
        'subentityKey': programsKey,
        **clevel,
        **compute_graph(clevel_slugs, clevel_courses),
        **compute_filters(clevel_courses)
    }

    key = redis_key(level['slug'])
    redis_set(key, clevel)

    for program in level[programsKey]:
        if level['slug'] == 'master':
            # Master program
            for specialization in program[specializationsKey]:
                # Store specializations (if any)
                s = copy.deepcopy(specialization)
                s_slugs = s['courses']
                del s['courses']
                s_courses = resolve_slugs(s_slugs)
                s = {
                    'entity': 'specialization',
                    **s,
                    **compute_graph(s_slugs, s_courses),
                    **compute_filters(s_courses)
                }

                key = redis_key(level['slug'], program['slug'], specialization['slug'])
                redis_set(key, s)

            if len(program[specializationsKey]) == 0:
                # Remove property if there are no specializations
                del program[specializationsKey]

        program_slugs = program['courses']
        del program['courses']
        program_courses = resolve_slugs(program_slugs)

        p = {
            'entity': 'program'
        }
        if specializationsKey in program:
            p['subentityKey'] = specializationsKey
        p = {
            **p,
            **program,
            **compute_graph(program_slugs, program_courses),
            **compute_filters(program_courses)
        }

        key = redis_key(level['slug'], program['slug'])
        redis_set(key, p)


for course in courses:
    key = redis_key(course['slug'], prefix_slug='course')
    redis_set(key, course)
