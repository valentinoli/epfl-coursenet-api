import re
import copy
from collections import OrderedDict
from string import punctuation
from titlecase import titlecase
from urllib.parse import urlparse, parse_qs, parse_qsl
from bs4 import NavigableString, Tag

from scraper.module import util
from scraper.module.const import base_url, studyplan_path, langs_dict

regex_specializations = re.compile('Specialization|Orientation', re.IGNORECASE)
regex_spec_endswith_SP = re.compile('-SP$')
regex_code_parens = re.compile('\((.+)\)$')

"""
Notes about master's specializations:

1.
The specializations legend on studyplan pages is sometimes obsolete (hasn't been removed)
We remove these programs from the list of specialization programs

Materials Science and Engineering (only one specialization now)
https://www.epfl.ch/education/master/wp-content/uploads/2018/08/STI_MX_MA-1.pdf
vs.
https://edu.epfl.ch/studyplan/en/master/materials-science-and-engineering

Microengineering
https://www.epfl.ch/education/master/wp-content/uploads/2018/08/STI_SMT_MA_RV-1.pdf
vs.
https://edu.epfl.ch/studyplan/en/master/microengineering
"""
obsolete_specializations = ['materials-science-and-engineering', 'microengineering']

"""
2.
Sometimes, the studyplan page differs greatly from the up-to-date studyplan brochure
which indicates that the studyplan page hasn't been updated.
We must hard-code these specializations:

Architecture
https://www.epfl.ch/education/master/wp-content/uploads/2018/08/ENAC_ARCHI_MA-1.pdf
vs.
https://edu.epfl.ch/studyplan/en/master/architecture
"""
architecture_specs = {
    "b": {
        "value": "b",
        "title": "Housing",
        "slug": "housing"
    },
    "d": {
        "value": "d",
        "title": "Protection and Heritage",
        "slug": "protection-and-heritage"
    },
    "m": {
        "value": "m",
        "title": "Urbanizations and Territories",
        "slug": "urbanization-and-territories"
    },
    "n": {
        "value": "n",
        "title": "Resources",
        "slug": "resources"
    },
    "o": {
        "value": "o",
        "title": "Types",
        "slug": "types"
    },
    "p": {
        "value": "p",
        "title": "Art and Architecture",
        "slug": "art-and-architecture"
    }
}

# Important!
# Courses are ordered by order of appearance in studyplan.
# Course ids included here for ease of reference.
architecture_course_specs = list(OrderedDict({
    "ar-599": [],
    "ar-481": [],
    "ar-486": [],
    "ar-488": ["b"],
    "ar-430": [],
    "ar-423-a": ["o"],
    "ar-485": [],
    "ar-469": ["p"],
    "ar-472": ["b"],
    "ar-498": [],
    "ar-521": [],
    "ar-597-a": [],
    "ar-597-b": [],
    "ar-598": [],
    # Studios BEGIN #
    # https://www.epfl.ch/schools/enac/education/architecture-en/master/studios-ma/
    "ar-401-f": ["n"],
    "ar-401-l": ["m"],
    "ar-401-m": ["o"],
    "ar-401-o": ["b"],
    "ar-401-y": ["o"],
    "ar-401-t": ["p"],
    "ar-401-r": ["n"],
    "ar-401-a": ["m"],
    "ar-401-q": ["d"],
    "ar-401-e": ["n"],
    "ar-402-f": ["n"],
    "ar-402-l": ["m"],
    "ar-402-m": ["o"],
    "ar-402-o": ["b"],
    "ar-402-y": ["o"],
    "ar-402-r": ["n"],
    "ar-402-t": ["m"],
    "ar-402-a": ["m"],
    "ar-402-q": ["d"],
    "ar-402-e": ["n"],
    # Studios END #
    "ar-462": [],
    "ar-495-b": [],
    "ar-457": ["o"],
    "ar-451": ["b", "m", "o"],
    "ar-452": ["b", "m", "o"],
    "ar-449": ["b", "d", "n"],
    "ar-453": [],
    "ar-496": [],
    "ar-497": ["n"],
    "ar-458": ["m"],
    "ar-442": ["b", "d", "n"],
    "ar-535": ["n"],
    "ar-428": [],
    "pens-490": ["d", "n"],
    "ar-427": ["b"],
    "ar-483": ["n"],
    "ar-484": ["n"],
    "ar-431": ["n"],
    "ar-491": ["b"],
    "ar-454": [],
    "ar-492": ["m"],
    "civil-434": [],
    "pens-491": [],
    "ar-487": ["d", "n"],
    "eng-484": [],
    "ar-434": ["b", "d"],
    "ar-514": ["m", "o"],
    # UE courses BEGIN #
    "ar-404": ["p"],
    "ar-467": ["b"],
    "ar-466": ["b"],
    "ar-439": ["b", "d"],
    "ar-433": [],
    "ar-471": ["m"],
    "ar-440": ["b", "m", "n"],
    "ar-415": ["m", "o"],
    "ar-416": ["m", "o"],
    "ar-448": ["n"],
    "ar-435": [],
    "ar-476": ["m", "o"],
    "ar-480": ["o"],
    # UE courses END #
    "ar-465": ["m"],
    "ar-455": ["m", "o"],
    "ar-456": ["o"],
    "ar-489": ["b", "m"],
    "ar-499": [],
    "ar-407": ["o"],
    "ar-417": []
}).values())

"""
3.
The specializations legend on studyplan pages is sometimes obsolete, but the studyplan itself
contains references to specializations that correctly correspond to the the studyplan brochure
In this case, we update the legend manually and fix the data

Electrical and Electronics Engineering
https://www.epfl.ch/education/master/wp-content/uploads/2018/08/STI_EL_MA-1.pdf
vs.
https://edu.epfl.ch/studyplan/en/master/electrical-and-electronics-engineering
"""
electrical_electronics_engineering_specs_values = {
    "a": {
        "value": "a",
        "title": "Microelectronics Circuits and Systems",
        "slug": "microelectronics-circuits-and-systems"
    },
    "b": {
        "value": "b",
        "title": "Electronic Technologies and Device-circuit Interactions",
        "slug": "electronic-technologies-and-device-circuit-interactions"
    },
    "c": {
        "value": "c",
        "title": "Bioelectronics",
        "slug": "bioelectronics"
    },
    "d": {
        "value": "d",
        "title": "Internet of Things",
        "slug": "internet-of-things"
    },
    "e": {
        "value": "e",
        "title": "Data Science and Systems",
        "slug": "data-science-and-systems"
    },
    "f": {
        "value": "f",
        "title": "Signal, Image, Video and Communication",
        "slug": "signal-image-video-and-communication"
    },
    "g": {
        "value": "g",
        "title": "Wireless and Photonics Circuits and Systems",
        "slug": "wireless-and-photonics-circuits-and-systems"
    }
}

def filter_lines(lines):
    for line in lines:
        code = line.find(class_='cours-code').text.strip()
        # Exclude ETH courses, for example Nuclear Eng. joint master studyplan
        # See joint/dobule degrees: https://www.epfl.ch/education/master/double-degrees/
        if code and not code.startswith('ETH'):
            yield (line, code)


def scrape_studyplan_specializations(soup):
    """Scrape all specializations for particular program"""
    tag = soup.find('div', class_='right-col')
    specialization_heading = tag.find('h3', string=regex_specializations)

    if specialization_heading is None:
        return None

    ul = specialization_heading.next_sibling.ul
    specs = {}
    for li in ul.children:
        key = li.img.get('src')[-5:-4]
        title = titlecase(regex_spec_endswith_SP.sub('', li.text))
        title_lowered_no_punct = ''.join(ch for ch in title.lower() if ch not in punctuation)
        slug = '-'.join(title_lowered_no_punct.split())
        specs[key] = {
            'value': key,
            'slug': slug,
            'title': title
        }
    return specs


def scrape_course_source_slug(name_tag):
    if name_tag.a:
        path_no_qs, _ = name_tag.a.get('href').split('?')
        _, slug = path_no_qs.rsplit('/', maxsplit=1)
        return slug
    return None


def construct_course_slug(course_code):
    return regex_code_parens.sub('-\g<1>', course_code).lower()


def scrape_lecturers(line_tag):
    enseignement_name = line_tag.find(class_='enseignement-name')
    lecturers = []
    for child in enseignement_name.children:
        if isinstance(child, NavigableString) and child.strip():
            # Various lecturers
            continue
            # lecturers.append({
            #     'name': 'Various lecturers',#  str(child.strip()),
            #     'sciper': ''
            # })
        elif child.name == 'a':
            href = child.get('href')
            qs = parse_qs(urlparse(href).query)
            sciper = qs['id'][0]
            lecturers.append({
                'name': child.text.strip(),
                'sciper': sciper
            })
    return lecturers


def scrape_course_specs_generator(line, specs_dict):
    for img in line.find(class_='specialisation').find_all('img'):
        spec_value = img.get('src')[-5:-4]
        try:
            matched_spec = next(spec_dict for key, spec_dict in specs_dict.items() if spec_value == key)
            yield matched_spec
        except StopIteration:
            course_code = line.find(class_="cours-code").string.strip()
            print(f'Specialization "{spec_value}" not found in specialization legend [{course_code}]')


def scrape(program):#(level_source_slug, program_source_slug, program_slug):
    """
    Scrapes studyplan data for the given level and program.
    Returns metadata for the program and the list of courses.
    """
    level_source_slug = program['levelSourceSlug']
    program_source_slug = program['sourceSlug']
    print(f'\n>>> Scraping studyplan {level_source_slug}: {program_source_slug}\n')

    # visit program's studyplan and fetch content soup
    url = util.join_path(base_url, studyplan_path, level_source_slug, program_source_slug)
    content, soup = util.bsoup(url, return_soup_object=True)

    program_data = {}
    courses_data = []

    # find all courses for which there is a course code
    # (skipping SHS lines, for instance)
    all_lines = content.find_all(class_='line')

    lines_and_codes = list(filter_lines(all_lines))

    # extract course codes and create generator for lines
    lines = [t[0] for t in lines_and_codes]
    codes = [t[1] for t in lines_and_codes]

    # extract more relevant information from studyplan page
    cours_name = [line.find(class_='cours-name') for line in lines]

    # parse query string for coursebook pages (it's the same for all courses in a program)
    # and create the id that locates program information on each coursebook page
    coursebook_link = content.find('a', href=re.compile('^/coursebook/en/'))
    querystring = urlparse(coursebook_link.get('href')).query
    qs = dict(parse_qsl(querystring))
    program_data['sourceQuery'] = qs
    program_data['sourceCBSection'] = qs['cb_section']
    program_data['sourceId'] = util.program_html_id(qs)

    source_slugs = [scrape_course_source_slug(name) for name in cours_name]
    slugs = [construct_course_slug(code) for code in codes]
    names = [name.contents[0].text.strip() for name in cours_name]
    remarks = [
        util.clean_remark(name.i.text)
        if name.i else ''
        for name in cours_name
    ]
    sections = [
        (
            line.find(class_='section-name')
            .text
            .strip()
            # PH_NE (nuclear engineering) --> PH
            .replace('PH_NE', 'PH')
        )
        for line in lines
    ]
    lang = [
        langs_dict[
            line.find(class_='langue').find(class_='langue').get('class')[1]
        ]
        for line in lines
    ]
    lecturers = [scrape_lecturers(line) for line in lines]
    exam_form = [
        line.find(class_='examen').text.strip()
        if line.find(class_='examen')
        else ''
        for line in lines
    ]
    credits = [
        line.find(class_='credit-time').text.strip()
        if line.find(class_='credit-time')
        else ''
        for line in lines
    ]

    # find all master's specializations (if any)
    specs_dict = course_specs = None
    if level_source_slug == 'master':
        program_data['specializations'] = []
        if program_source_slug not in obsolete_specializations:
            if program_source_slug == 'architecture':
                specs_dict = architecture_specs
                course_specs = [
                    [
                        # substitute spec id with spec object
                        specs_dict[spec]
                        for spec in course_spec_list
                    ]
                    for course_spec_list in architecture_course_specs
                ]
                assert len(course_specs) == len(lines)
            elif program_source_slug == 'electrical-and-electronics-engineering':
                specs_dict = electrical_electronics_engineering_specs_values
            elif program_source_slug == 'computer-science-cybersecurity':
                # Cyber Security "Depth requirement", incomplete info
                specs_dict = None
            else:
                # returns None if no specializations found
                specs_dict = scrape_studyplan_specializations(soup)

            if specs_dict:
                if not course_specs:
                    # scrape specializations per course
                    course_specs = [
                        list(scrape_course_specs_generator(line, specs_dict))
                        for line in lines
                    ]

                # create dict for info about program specializations
                program_specs = copy.deepcopy(specs_dict)
                for s in program_specs.values():
                    s.update({
                        'programSourceSlug': program['sourceSlug'],
                        'programSlug': program['slug'],
                        'programTitle': program['title'],
                        'levelSourceSlug': program['levelSourceSlug'],
                        'levelSlug': program['levelSlug'],
                        'levelTitle': program['levelTitle'],
                        'courses': []  # course list
                    })

                for i, course_slug in enumerate(slugs):
                    for spec in course_specs[i]:
                        program_specs[spec['value']]['courses'].append(course_slug)


                program_data['specializations'] = list(program_specs.values())


    # create dict for each course and append to courses list
    for i, code in enumerate(codes):
        course = {
            'code': code,
            'name': names[i],
            'sourceSlug': source_slugs[i],
            'slug': slugs[i],
            'remark': remarks[i],
            'section': sections[i],
            'language': lang[i],
            'lecturers': lecturers[i],
            'examForm': exam_form[i],
            'credits': credits[i],
            'specializations': {}
        }

        if specs_dict:
            course['specializations'] = { program['slug']: course_specs[i] }

        courses_data.append(course)

    program_data['courses'] = slugs
    print('>>> Studyplan scraped successfully!\n')
    return program_data, courses_data


if __name__ == '__main__':
    import sys
    from pprint import pprint
    numargs = 3
    if len(sys.argv) != numargs:
        raise TypeError('Invalid number of arguments')
    path, level_slug, program_slug = sys.argv
    print(f'testing module {path}')
    program_data, courses_data = scrape({
        'sourceSlug': program_slug,
        'slug': program_slug,
        'title': program_slug,
        'levelSourceSlug': level_slug,
        'levelSlug': level_slug,
        'levelTitle': level_slug
    })
    pprint(courses_data)
    pprint(program_data)
