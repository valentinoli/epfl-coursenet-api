from titlecase import titlecase

from scraper.module import util
from scraper.module.const import base_url, studyplan_path

# Only 13 bachelor programs are currently offered
# + Humanities and Social Sciences Program
# + Design Together ENAC
# https://www.epfl.ch/education/bachelor/programs/
bachelor_not_current = [
    'chemistry',
    'chemical-engineering'
]

# Only 25 master's programs are currently offered
# + Humanities and Social Sciences Program
# https://www.epfl.ch/education/master/programs/
master_not_current = [
    'bioengineering',
    'life-sciences-and-technologies-master-program',
    'micro-and-nanotechnologies-for-integrated-systems'
]

# Minors
# https://www.epfl.ch/education/master/study-programs-structure/minors-and-specializations/
# The following minors are missing, among possibly others:
#   Computational science and engineering
#     https://www.epfl.ch/schools/sb/education/sma/studies/master-ma-en/computational-science-and-engineering/
#   Integrated Design, Architecture & Sustainability
#     https://www.epfl.ch/schools/enac/education/ideas/minor
#   Architecture
#   Civil Engineering
#   Environmental Sciences & Engineering
#   Microengineering
#   Materials Science & Engineering
#   Electrical & Electronic Engineering
#   Mathematics
#   Physics
#   Chemistry & Chemical Engineering
#   Life Sciences Engineering
# STAS is not offered anymore https://www.epfl.ch/schools/cdh/education-2/stas-2/
# We do not take any action for now

def program_is_outofdate(level, slug):
    return (
        (level == 'bachelor' and slug in bachelor_not_current) or
        (level == 'master' and slug in master_not_current)
    )

def scrape(level):
    """
    Scrapes study programs for given level
    """
    print(f'\n>>> Scraping {level} programs')
    url = util.join_path(base_url, studyplan_path, level)
    soup = util.bsoup(url)
    ulist = soup.ul

    # Gather all slugs to program study plans
    anchors = ulist.find_all('a')
    programs = []

    for a in anchors:
        href = a.get('href')
        source_slug = href.rsplit('/', 1)[-1]
        if program_is_outofdate(level, source_slug):
            # skip out of date programs
            continue

        slug = source_slug
        title = a.text

        if level == 'minor':
            if title.startswith('Mineur STAS'):
                # STAS abolished from 2020-21
                # https://www.epfl.ch/schools/cdh/education-2/stas-2/
                continue
            title = (
                title
                .replace(' minor', '')
                .replace('Minor in ', '')
                # Integrated Design, Architecture and Sustainability (prev. Durability)
                .replace('Durability', 'Sustainability')
            )
            slug = (
                slug.replace('minor-in-', '')
                # integrated-design-architecture-and-sustainability (prev. durability)
                .replace('durability', 'sustainability')
            )
        elif level == 'master':
            title = (
                title
                .replace('Computer Science - Cybersecurity', 'Cyber Security')
                .replace(' - master program', '')
            )
            slug = (
                slug
                .replace('computer-science-cybersecurity', 'cybersecurity')
                .replace('-master-program', '')
            )
        elif level == 'doctoral_school':
            title = title.replace('(edoc)', '')

        programs.append({
            'sourceSlug': source_slug,
            'slug': slug,
            'title': titlecase(title.strip()),
            'levelSlug': util.construct_level_slug(level)
        })
    return programs


if __name__ == '__main__':
    import sys
    numargs = 2
    if len(sys.argv) != numargs:
        raise TypeError('Invalid number of arguments')
    path, level_slug = sys.argv
    print(f'testing module {path}')
    print(scrape(level_slug))
