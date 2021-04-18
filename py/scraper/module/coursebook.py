import re
from re import IGNORECASE
from bs4 import NavigableString, Tag
from urllib.parse import urlencode

from scraper.module import util
from scraper.module.const import base_url, coursebook_path, langs_dict

regex_heading_element = re.compile('^h[1-6]$')
regex_people_href = re.compile('people\.epfl\.ch\/(\d{6})?$')
regex_program_semester = re.compile('semester (\d)')

regex_lecturers = re.compile('Lecturer', IGNORECASE)
regex_language = re.compile('Langue|Language', IGNORECASE)
regex_withdrawal = re.compile('Retrait|Withdrawal', IGNORECASE)
regex_remark = re.compile('Remarque|Remark', IGNORECASE)
regex_summary = re.compile('Résumé|Summary', IGNORECASE)
regex_content = re.compile('Contenu|Content', IGNORECASE)
regex_keywords = re.compile('Mots-clés|Keywords', IGNORECASE)
regex_required = re.compile(
    'Required courses|Cours prérequis obligatoires', IGNORECASE)
regex_recommended = re.compile(
    'Recommended courses|Cours prérequis indicatifs', IGNORECASE)
regex_concepts = re.compile(
    'Important concepts|Concepts importants', IGNORECASE)
regex_prerequisites = re.compile(
    'Prerequisite for|Préparation pour', IGNORECASE)


def program_html_id(qs):
    """Returns program HTML id, constructed from query string"""
    return (
        qs['cb_cycle'].replace('min_', 'min')
        + '-'
        + qs['cb_section']
    )


def scrape_coursebook_lecturers(content):
    """Scrape info about lecturers from coursebook page"""
    lecturers = []
    heading_tag = content.find('h4', string=regex_lecturers)
    if heading_tag is not None:
        for sibling in heading_tag.next_siblings:
            name = sibling.name

            if isinstance(sibling, NavigableString) or name == 'br':
                # continue if
                # 1. the object is NavigableString
                # 2. the object is <br> tag
                continue

            elif regex_heading_element.match(name):
                # break the loop if next heading is reached
                break

            elif name == 'a':
                # link format: http://people.epfl.ch/:sciper
                href = sibling.get('href')
                match = regex_people_href.search(href)
                sciper = match.group(1)
                name = sibling.text.strip()
                if not sciper or sciper == '126096' or 'lecturers' in name.lower():
                    continue
                # if 'Profs divers' in name:
                    # name = 'Various lecturers'
                    # sciper = ''
                lecturers.append({
                    'name': name,
                    'sciper': sciper
                })

    return lecturers


def scrape_coursebook_content(content, regx, tagname='h4'):
    """Scrape main coursebook text content below given heading"""
    heading_tag = content.find(tagname, string=regx)
    list_str = []
    if heading_tag is None:
        return ''
    else:
        for sibling in heading_tag.next_siblings:
            if isinstance(sibling, NavigableString):
                list_str.append(str(sibling).strip())
            elif 'br' == sibling.name:
                continue
            elif regex_heading_element.match(sibling.name):
                # break the loop if next heading is reached
                break
            elif isinstance(sibling, Tag):
                list_str.extend(list(sibling.stripped_strings))

        # filter out small strings and "None"
        list_str = [x for x in list_str if len(x) > 3 and x != 'None']
        str_joined = ' '.join(list_str)
        return str_joined


def scrape(source_slug, source_query_dict):
    """
    Scrapes info about given course from the coursebook page
    :param source_slug: slug identifying the course
    :param source_query_dict: query parameters identifying the program
    """
    print(f'>>> Scraping coursebook: {source_slug}')
    querystring = urlencode(query=source_query_dict)
    url = util.join_path(
        base_url, coursebook_path, f'{source_slug}?{querystring}'
    )
    content, soup = util.bsoup(url, return_soup_object=True)

    course = {}

    # could have provided program_id as parameter
    program_id = util.program_html_id(source_query_dict)
    program_els = soup.find_all(id=program_id)
    for el in program_els:
        for li in el.find_next_sibling('ul').children:
            # call extract() to remove from DOM and not be included in val
            strong_text = li.strong.extract().text.strip()
            if not strong_text:
                continue
            strong_text_split = strong_text.split(' ')
            key = util.camelCase(strong_text_split)
            val = li.text.strip().replace('\xa0', ' ')
            if key in course and val != course[key]:
                if key == 'semester':
                    print('Both spring and fall semesters detected')
                    course[key] = 'Any'
                else:
                    print(f'Values for program {program_id} do not match: (1) {course[key]} (2) {val}')
            elif key not in course:
                course[key] = val

    in_the_programs_box = soup.find(class_='right-col').contents[0]
    underlined_divs = in_the_programs_box.find_all('div', class_='underline')

    # Save only ids and during post-processing replace the field with concrete data
    programs = []
    for div in underlined_divs:
        program_id = div.get('id')
        try:
            program = next(p for p in programs if p['programSourceId'] == program_id)
        except StopIteration:
            program = {
                'programSourceId': program_id,
                'semesterNumbers': []
            }
            programs.append(program)

        semester_match = regex_program_semester.search(div.string)
        if semester_match:
            # append semester number
            semester_num = int(semester_match.group(1))
            program['semesterNumbers'].append(semester_num)

    course['programs'] = programs

    course['lecturers'] = scrape_coursebook_lecturers(content)

    lang_heading = content.find('h4', string=regex_language)
    if lang_heading:
        lang_tags = []
        for sibling in lang_heading.next_siblings:
            if isinstance(sibling, Tag):
                if regex_heading_element.match(sibling.name):
                    break
                elif sibling.get('class')[0] == 'img_legende':
                    lang_tags.append(sibling)
        if len(lang_tags) > 2:
            raise ValueError('Cannot handle more than 2 languages')
        elif len(lang_tags) == 2:
            langs = [tag.get('class')[1] for tag in lang_tags]
            if 'anglais' in langs and 'francais' in langs:
                course['language'] = langs_dict['franglais']
            else:
                raise ValueError(
                    '2 languages detected, not French and English')
        else:
            lang_key = lang_tags[0].get('class')[1]
            course['language'] = langs_dict[lang_key]

    course['withdrawal'] = scrape_coursebook_content(content, regex_withdrawal)
    course_remark = scrape_coursebook_content(content, regex_remark)
    course['remark'] = util.clean_remark(course_remark)
    course['summary'] = scrape_coursebook_content(content, regex_summary)
    course['content'] = scrape_coursebook_content(content, regex_content)
    course['keywords'] = scrape_coursebook_content(content, regex_keywords)

    course['requiredCourses'] = scrape_coursebook_content(
        content, regex_required, 'h5')
    course['recommendedCourses'] = scrape_coursebook_content(
        content, regex_recommended, 'h5')
    course['priorConcepts'] = scrape_coursebook_content(
        content, regex_concepts, 'h5')
    course['preparationFor'] = scrape_coursebook_content(
        content, regex_prerequisites)

    return course


if __name__ == '__main__':
    import sys
    from pprint import pprint
    numargs = 4
    if len(sys.argv) != numargs:
        raise TypeError('Invalid number of arguments')
    path, slug, cb_cycle, cb_section = sys.argv
    print(f'testing module {path}')
    res = scrape(slug, {'cb_cycle': cb_cycle, 'cb_section': cb_section})
    pprint(res)
