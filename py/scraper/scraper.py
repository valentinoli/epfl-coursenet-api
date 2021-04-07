from scraper.module import levels, programs, studyplan, coursebook

def scrape():
    programs_info = levels.scrape()
    courses_studyplan = []
    courses_coursebook = []

    for level in programs_info:
        programs_list = programs.scrape(level)

        for program in programs_list:
            program_extra, courses_list = studyplan.scrape(program)

            # use update() to maintain reference
            program.update(program_extra)

            courses_studyplan.extend(courses_list)

            print(f'>>> Scraping studyplan coursebooks...\n')

            for course in courses_list:
                if course['sourceSlug'] is not None:
                    course_dict = coursebook.scrape(
                        course['sourceSlug'],
                        program['sourceQuery']
                    )
                    # add slug as a common identifier
                    # to course dict from studyplan page
                    # to facilitate merging
                    course_dict['slug'] = course['slug']
                    courses_coursebook.append(course_dict)

        level['sourceCBCycle'] = program['sourceQuery']['cb_cycle']
        level['programs'] = programs_list

    return programs_info, courses_studyplan, courses_coursebook
