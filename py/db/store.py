#!/usr/bin/env python
# coding: utf-8

import json
import copy
import redis
from os import getenv
from utils import read

epfl = read.read_json_processed('epfl')
courses = read.read_json_processed('courses')
links = read.read_json_processed('links')


# course dicts with only necessary fields for display and filtering
minimal_keys = (
    'slug', 'code', 'name', 'section', 'semester',
    'credits', 'language', 'examForm', 'lecturers'
)
courses_minimal = [dict((k, c[k]) for k in minimal_keys) for c in courses]

def get_neighborhood_key(incoming, outgoing):
    if incoming and outgoing:
        return 'incomingOutgoing'
    if incoming:
        return 'incoming'
    if outgoing:
        return 'outgoing'
    return None


def resolve_slugs(slugs, incoming=False, outgoing=False):
    # the courses listed in `slugs` are by default not
    # part of the neighborhood
    neighborhood_key = get_neighborhood_key(incoming, outgoing)
    return [
        {
            **course,
            'incoming': incoming,
            'outgoing': outgoing,
            'neighborhoodKey': neighborhood_key
        }
        for course in courses_minimal
        if course['slug'] in slugs
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
    incoming_slugs = set(l['source'] for l in incoming_links)
    outgoing_slugs = set(l['target'] for l in outgoing_links)

    # The intersection of the two sets consists of both incoming and outgoing courses
    incoming_outgoing_slugs = incoming_slugs.intersection(outgoing_slugs)
    incoming_slugs = incoming_slugs - incoming_outgoing_slugs
    outgoing_slugs = outgoing_slugs - incoming_outgoing_slugs

    incoming_outgoing_courses = resolve_slugs(incoming_outgoing_slugs, incoming=True, outgoing=True)
    incoming_courses = resolve_slugs(incoming_slugs, incoming=True)
    outgoing_courses = resolve_slugs(outgoing_slugs, outgoing=True)

    return {
        'graph': {
            'nodes': {
                'subgraph': subgraph_courses,
                'incoming': incoming_courses,
                'outgoing': outgoing_courses,
                'incomingOutgoing': incoming_outgoing_courses,
            },
            'links': {
                'subgraph': subgraph_links,
                'incoming': incoming_links,
                'outgoing': outgoing_links
            }
        }
    }



def compute_filters(courses):
    return {
        'filterOptions': {
            'section': sorted({ c['section'] for c in courses }),
            'semester': sorted({ c['semester'] for c in courses }),
            'credits': sorted({ c['credits'] for c in courses }),
            'language': sorted({ c['language'] for c in courses }),
            'examForm': sorted({ c['examForm'] for c in courses })
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
        'courses': l['courses'],
        'children': [
            {
                'id': f"{l['slug']}-{p['slug']}",
                'name': p['title'],
                'params': {
                    'level': l['slug'],
                    'program': p['slug'],
                    'specialization': None
                },
                'courses': p['courses'],
                'children': [
                    {
                        'id': f"{l['slug']}-{p['slug']}-{s['slug']}",
                        'name': s['title'],
                        'value': s['value'],
                        'params': {
                            'level': l['slug'],
                            'program': p['slug'],
                            'specialization': s['slug']
                        },
                        'courses': s['courses'],
                        'children': []
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


def create_path(level=None, program=None, specialization=None):
    path = ''
    if level:
        path += f'/{level}'
        if program:
            path += f'/{program}'
            if specialization:
                path += f'/{specialization}'
        return path
    return f'/{all_courses_slug}'


nav_autocomplete = [{
    'title': all_courses_title,
    'path': create_path(),
    'icon': 'mdi-all-inclusive',
    # 'parent': []
},{
    'divider': True,
    # 'parent': []
}]
for l in epfl['levels']:
    # level_path = create_path(l['slug'])
    nav_autocomplete.extend([{
        'title': l['title'],
        'path': create_path(l['slug']),
        'icon': 'mdi-school-outline',
        # 'parent': all_courses_path,
    },
    {
        'divider': True,
        # 'parent': level_path
    },
    {
        'header': f"{l['title']} Programs",
        # 'parent': level_path
    }])
    for p_idx, p in enumerate(l['programs']):
        # program_path = create_path(l['slug'], p['slug'])
        nav_autocomplete.append({
            'title': p['title'],
            'subtitle': l['title'],
            'path': create_path(l['slug'], p['slug']),
            'icon': 'mdi-school',
            # 'parent': level_path
        })

        if l['slug'] == 'master' and len(p['specializations']) > 0:
            nav_autocomplete.extend([{
                'divider': True,
                # 'parent': program_path
            },
            {
                'header': f"{p['title']} Master Specializations",
                # 'parent': program_path
            }])
            for s in p['specializations']:
                # spec_path = create_path(l['slug'], p['slug'], s['slug'])
                nav_autocomplete.append({
                    'title': s['title'],
                    'subtitle': f"{p['title']} Master Specialization",
                    'path': create_path(l['slug'], p['slug'], s['slug']),
                    'specializationValue': s['value'],
                    # 'parent': program_path
                })

            nav_autocomplete.append({
                'divider': True,
                # 'parent': program_path
            })
    nav_autocomplete.append({
        'divider': True,
        # 'parent': level_path
    })


# root data object
# need to create a deep copy since we delete level['programs']
cepfl = copy.deepcopy(epfl)
cepfl_slugs = cepfl['courses']
del cepfl['courses']
cepfl_courses = resolve_slugs(cepfl_slugs)
all_filters = compute_filters(cepfl_courses)

nav_treeview = {
    'id': all_courses_slug,
    'name': all_courses_title,
    'params': {
        'level': all_courses_slug,
        'program': None,
        'specialization': None
    },
    'courses': epfl['courses'],
    'children': nav_treeview
}

nav = {
    'treeview': nav_treeview,
    'autocomplete': nav_autocomplete,
    # pass all filter options
    'allFilterOptions': all_filters['filterOptions']
}
redis_set(redis_key(prefix_slug = 'nav'), nav)

cepfl = {
    'entity': 'root',
    'subentityKey': 'levels',
    'title': all_courses_title,
    'slug': all_courses_slug,
    **cepfl,
    'treeview': nav_treeview,
    **compute_graph(cepfl_slugs, cepfl_courses),
    **all_filters
}

for level in cepfl['levels']:
    del level['programs']

redis_set(redis_key(), cepfl)
specializationsKey = 'specializations'
programsKey = 'programs'

for l_idx, level in enumerate(epfl['levels']):
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
        'treeview': nav_treeview['children'][l_idx],
        **compute_graph(clevel_slugs, clevel_courses),
        **compute_filters(clevel_courses)
    }

    key = redis_key(level['slug'])
    redis_set(key, clevel)

    for p_idx, program in enumerate(level[programsKey]):
        if level['slug'] == 'master':
            # Master program
            for s_idx, specialization in enumerate(program[specializationsKey]):
                # Store specializations (if any)
                s = copy.deepcopy(specialization)
                s_slugs = s['courses']
                del s['courses']
                s_courses = resolve_slugs(s_slugs)
                s = {
                    'entity': 'specialization',
                    **s,
                    'treeview': nav_treeview['children'][l_idx]['children'][p_idx]['children'][s_idx],
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
            'treeview': nav_treeview['children'][l_idx]['children'][p_idx],
            **compute_graph(program_slugs, program_courses),
            **compute_filters(program_courses)
        }

        key = redis_key(level['slug'], program['slug'])
        redis_set(key, p)


for course in courses:

    key = redis_key(course['slug'], prefix_slug='course')
    redis_set(key, course)
