import os
import re
import json
import requests
from bs4 import BeautifulSoup as bsoup
import util

# https://isa.epfl.ch/imoniteur_ISAP/!GEDREPORTS.filter?ww_i_reportModel=2212045167
ISA_BASE_URL = 'https://isa.epfl.ch/imoniteur_ISAP/'
ISA_REPORT_MODEL = '2212045167'
ISA_REPORTS_INSCRIPTIONS_COURS = '!GEDREPORTS.filter'
ISA_COURSE_REPORT = '!GEDREPORTS.bhtml'
ISA_LOGIN_ACTION = '!logins.tryToConnect'

regex_years_end = re.compile('.+\d{4}.\d{4}$')


def get_login_form():
    username = os.environ.get("GASPAR_NAME")
    password = os.environ.get("GASPAR_PASS")

    if not username or not password:
        raise TypeError("GASPAR_NAME and GASPAR_PASS env vars not set")

    print(f"GASPAR_NAME: {username}, GASPAR_PASS: {'*' * len(password)}")
    return {
        'ww_x_urlAppelant': 'isacademia.htm',
        'ww_x_username': username,
        'ww_x_password': password
    }


def get_report_form(ww_x_MAT='', zz_x_PERIODE_ACAD='', ww_x_PERIODE_ACAD=''):
    return {
        # some hidden parameter, don't know if it is required
        'ww_b_list': '1',
        # the report type
        'ww_i_reportmodel': ISA_REPORT_MODEL,
        # the output format: html
        'ww_i_reportModelXsl': '2212045204',
        # parameter for course ID
        'ww_x_MAT': ww_x_MAT,
        # Période académique (<select> text)  default: all
        'zz_x_PERIODE_ACAD': zz_x_PERIODE_ACAD,
        # Période académique (<select> value) default: all
        'ww_x_PERIODE_ACAD': ww_x_PERIODE_ACAD
    }


def process_course_registration_report(reg, soup):
    # select elements with info about the number of students per program, year, semester
    colspan_2 = soup.select('tr > td[colspan="2"]')

    programs = []
    semesters = []

    for el in colspan_2:
        text = el.text

        if 'ét.' not in text:  # program name, year and semester info
            text = text.replace('Ecole polytechnique fédérale de Lausanne, ', '')  # replace epfl prefix which occurs sometimes

            if regex_years_end.match(text):
                # edoc (phd), no semester info
                text_split = text.rsplit(', ', maxsplit=1)
                program = text_split[0]
                year = text_split[1]
                semester = ''
            else:
                text_split = text.rsplit(', ', maxsplit=2)
                program = text_split[0]
                year = text_split[1]
                semester = text_split[2]

            if year not in reg:
                reg[year] = {}

            if program in programs:
                idx = programs.index(program)
                if semesters[idx] == semester:
                    continue  # continue if the semester info is the same

                sem = semester.rsplit(maxsplit=1)[1]
                oldsem = semesters[idx].rsplit(maxsplit=1)[1]

                try:
                    if int(sem) > int(oldsem):
                        semesters[idx] += (', ' + sem)  # append
                    else:
                        semesters[idx] = semesters[idx][:-1]
                        semesters[idx] += (sem + ', ' + oldsem)  # prepend
                except ValueError:
#                     print(course_name, program, year, sem)
                    semesters[idx] += (', ' + sem)

            else:
                programs.append(program)
                semesters.append(semester)

#             if program not in reg:
                # sometimes two master semesters in a row for the same program,
                # so we only extract info from the first line
                # For example:
                # Bioengineering, 2019-2020, Master semester 3
                # Bioengineering, 2019-2020, Master semester 1

#                 level = ''
#                 if 'edoc' in program.lower():
#                     level = 'doctoral_school'
#                 elif 'master' in semester.lower():
#                     level = 'master'
#                 elif 'bachelor' in semester.lower():
#                     level = 'bachelor'
#                 elif 'minor' in program.lower() or 'mineur' in program.lower():
#                     level = 'minor'
#                 else:
#                     the program might be a UNIL program or exchange program, for instance

#                 program_key = level + program
#                 reg[year][program]['level'] = level

        else:
#             reg[year][program]['count'] = re.search('\d+', text)[0]
            # we can't use lists as keys in a dictionary/json, but string - yes!
            programs_key = '\n'.join(
                list(map(
                    lambda tup: tup[0]+', '+tup[1] if tup[1] else tup[0],
                    zip(programs, semesters)
                ))
            )
            reg[year][programs_key] = int(re.search('\d+', text)[0])
            programs = []
            semesters = []


def scrape():
    login_data = get_login_form()

    # initialize
    registrations_data = {}

    with requests.Session() as session:
        login_url = util.join_path(ISA_BASE_URL, ISA_LOGIN_ACTION)
        session.post(login_url, data=login_data)

        report_url = util.join_path(ISA_BASE_URL, ISA_REPORTS_INSCRIPTIONS_COURS)
        report_data = get_report_form()
        response = session.get(report_url, data=report_data)
        soup = bsoup(response.text, 'html.parser')

        # get all ids and course names below
        # "Cliquez sur une des matières pour avoir les inscriptions"
        ww_x_MAT = [(link.get('onclick')[32:-42], link.text.strip()) for link in soup.find_all(class_='ww_x_MAT')]
        ww_x_MAT_timeouts = []

        course_report_url = util.join_path(ISA_BASE_URL, ISA_COURSE_REPORT)

        # loop over course ids and names
        for x_MAT, course_name in ww_x_MAT:
            try:
                print(f"scraping {x_MAT}: {course_name}")
                report_data = get_report_form(x_MAT)
                response = session.get(course_report_url, data=report_data, timeout=30)
                soup = bsoup(response.text, 'html.parser')
                print(soup.prettify())
                if course_name not in registrations_data:
                    # sometimes the course name is duplicated
                    registrations_data[course_name] = {}

                get_isa_course_report(registrations_data[course_name], soup)
            except requests.exceptions.Timeout:
                ww_x_MAT_timeouts.append((x_MAT, course_name))
                continue


if __name__ == '__main__':
    scrape()
