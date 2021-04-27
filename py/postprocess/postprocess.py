#!/usr/bin/env python
# coding: utf-8

import pandas as pd
from utils import read, write


programs = read.read_json_raw('programs')
courses_studyplan = read.read_json_raw('courses-studyplan')
courses_coursebook = read.read_json_raw('courses-coursebook')

###################################
# Process `courses_studyplan`     #
###################################

courses_sp = pd.DataFrame.from_records(courses_studyplan, index='slug')
print('columns in courses_sp:\n', courses_sp.columns)
print(f'Number of courses in courses_sp: {courses_sp.index.nunique()}')


# We want to deal with specializations column separately
courses_specializations = courses_sp.pop('specializations')

# Merge specializations
def merge_dicts(series):
    return {k:v for d in series for k,v in d.items()}

courses_specializations = (
    courses_specializations.groupby('slug')
    .aggregate(merge_dicts)
)

# Commonly, a single course has multiple coursebook source slugs.
# The pages that each points to might differ.
# So we will deal with this column separately.
courses_sourceslugs = courses_sp.pop('sourceSlug')
courses_sourceslugs = (
    courses_sourceslugs.groupby('slug')
    .apply(lambda series: [] if series[0] == None else sorted(set(series)))
)


def get_duplicates(df):
    nunique = df.groupby(df.index).nunique(dropna=False)

    # Here we compute the number of different values for each column per course
    # and only keep those courses where at least one column has different values
    duplicates = nunique.loc[(nunique > 1).any(axis=1)]
    duplicates = duplicates[duplicates.columns[duplicates.gt(1).any()]]
    return duplicates


# Convert list or dict columns to str to avoid error when calling .nunique()
# TypeError: unhashable type: 'list' (or 'dict')
courses_sp = courses_sp.astype({ 'lecturers': str })

dups = get_duplicates(courses_sp)
print(dups)


# courses_sp.loc['bioeng-448', 'remark'] = ''
# courses_sp.loc['bioeng-448', 'lecturers'] = courses_sp.loc['bioeng-448', 'lecturers'][1]
courses_sp.loc['che-803', 'remark'] = courses_sp.loc['che-803', 'remark'][0]
courses_sp.loc['com-503', 'remark'] = courses_sp.loc['com-503', 'remark'][0]
courses_sp.loc['com-506', 'examForm'] = courses_sp.loc['com-506', 'examForm'][0]
courses_sp.loc['cs-448', 'remark'] = courses_sp.loc['cs-448', 'remark'][0]
courses_sp.loc['cs-596', 'remark'] = courses_sp.loc['cs-596', 'remark'][0]
courses_sp.loc['ee-492-d', 'remark'] = 'Only from second semester (Electrical and Electronics Engineering, Master)'
courses_sp.loc['eng-466', 'examForm'] = courses_sp.loc['eng-466', 'examForm'][0]
courses_sp.loc['fin-406', 'remark'] = courses_sp.loc['cs-524', 'remark'][1]
courses_sp.loc['math-318', 'remark'] = courses_sp.loc['math-318', 'remark'][1]
# me-411: probably 5 credits and not 4? Note different source slugs.
courses_sp.loc['me-411', 'credits'] = courses_sp.loc['me-411', 'credits'][0]
# courses_sp.loc['me-418', 'remark'] = courses_sp.loc['me-418', 'remark'][1]
courses_sp.loc['mgt-431', 'remark'] = courses_sp.loc['mgt-431', 'remark'][2]
courses_sp.loc['mgt-555', 'remark'] = 'Can be taken instead of Research Project in Materials I (Material Science and Engineering, Master)'
# courses_sp.loc['micro-723', 'remark'] = ''


dups = get_duplicates(courses_sp)
if len(dups) > 0:
    print('Unhandled duplicates (studyplan):\n', dups)
    print(courses_sp.loc[dups.index])
assert dups.size == 0


# Strip whitespace
def df_strip(df):
    return df.applymap(lambda v: v.strip().replace('\xa0', ' ') if type(v) == str else v)

courses_sp = df_strip(courses_sp)

# Remove duplicates
courses_sp.drop_duplicates(subset='code', inplace=True)


courses_sp['sourceSlug'] = courses_sourceslugs


###################################
# Process `courses_coursebook`    #
###################################

courses_cb = pd.DataFrame.from_records(courses_coursebook, index='slug')


print('columns in courses_cb:\n', courses_cb.columns)
print(f'Number of courses in courses_sp: {courses_cb.index.nunique()}')


# Format workload columns
def format_workload_col(el):
    if el.startswith('0 hour(s)'):
        return ''
    if el.startswith('1 hour(s)'):
        return el.replace('hour(s)', 'hour')
    return el.replace('hour(s)', 'hours')

workload_cols = ['labs', 'lecture', 'project', 'practicalWork', 'exercises']
courses_cb[workload_cols] = (
    courses_cb[workload_cols].fillna('')
    .apply(lambda s: s.str.lower())
    .applymap(format_workload_col)
)

# Interpret no semester info as the course is taught in any semester
courses_cb.loc[courses_cb.semester == '', 'semester'] = 'Any'


# The columns `coefficient` and `credits` should be merged.

assert not (courses_cb.credits == courses_cb.coefficient).any()


# No rows should have both `credits` and `coefficient` column. Some rows have neither column specified.
#
# Let's first merge the columns and then manually fill in the gaps if possible.

courses_cb.credits.fillna(courses_cb.coefficient, inplace=True)
courses_cb.drop('coefficient', axis=1, inplace=True)


# Let's now fill in the gaps

print('Courses with no credits info (imputed with 0):')
print(courses_cb[courses_cb.credits.isna()].index)


# Notes:
# * ENG-274 is without credits
# * PENS-200 Ground control in Swiss law, credits are included in the ENAC week
# * PHYS-300(a) is also without credits

courses_cb.fillna(value={'credits': '0'}, inplace=True)
assert courses_cb.credits.notna().all()


# Treat programs column separately
courses_programs = courses_cb.pop('programs')
courses_cb = courses_cb.astype({ 'lecturers': str })
dups = get_duplicates(courses_cb)
print(dups)


courses_cb.loc['bio-482', 'lecturers'] = courses_cb.loc['bio-482'].lecturers[0]
courses_cb.loc['bio-502', 'semester'] = courses_cb.loc['bio-502'].semester[0]
# courses_cb.loc['bioeng-448', 'lecturers'] = courses_cb.loc['bioeng-448'].lecturers[1]
courses_cb.loc['ch-443', 'semester'] = courses_cb.loc['ch-443'].semester[0]
courses_cb.loc['ch-444', 'semester'] = courses_cb.loc['ch-444'].semester[0]
# courses_cb.loc['cs-433', 'lecturers'] = courses_cb.loc['cs-433'].lecturers[0]
courses_cb.loc['com-506', 'examForm'] = courses_cb.loc['com-506'].examForm[0]
courses_cb.loc['dh-500', 'semester'] = courses_cb.loc['dh-500'].semester[0]
courses_cb.loc['eng-466', 'examForm'] = courses_cb.loc['eng-466'].examForm[0]
courses_cb.loc['fin-401', 'practicalWork'] = courses_cb.loc['fin-401'].practicalWork[0]
courses_cb.loc['me-411', 'practicalWork'] = courses_cb.loc['me-411'].practicalWork[0]
courses_cb.loc['me-411', 'credits'] = courses_cb.loc['me-411'].credits[0]
courses_cb.loc['micro-568', 'lecturers'] = courses_cb.loc['micro-568'].lecturers[0]
courses_cb.loc['micro-723', 'semester'] = courses_cb.loc['micro-723'].semester[0]


dups = get_duplicates(courses_cb)
if len(dups) > 0:
    print('Unhandled duplicates (coursebook):\n', dups)
    print(courses_cb.loc[dups.index])
assert dups.size == 0

courses_cb = df_strip(courses_cb)
courses_cb.drop_duplicates(inplace=True)


# merge programs fields for each course
# first explode lists and transform to dataframe
# with columns programSourceId and semesterNumbers
programs_exploded = courses_programs.explode()
programs_df = pd.json_normalize(programs_exploded).set_index(programs_exploded.index)


programs_map = {
    program['sourceId']: {
        'levelSlug': level['slug'],
        'levelTitle': level['title'],
        'programSlug': program['slug'],
        'programTitle': program['title']
    }
    for level in programs
    for program in level['programs']
}


# Retain only supported program ids
programs_df = programs_df[programs_df.programSourceId.isin(programs_map)]

# Map each source id to level and program details dict
programs_details = programs_df.programSourceId.apply(lambda v: programs_map[v])
programs_details = pd.json_normalize(programs_details).set_index(programs_details.index)

# Concatenate resulting DF with semesterNumbers column
programs_df = pd.concat([programs_details, programs_df.semesterNumbers], axis=1).astype({ 'semesterNumbers': str })


# duplicate sanity check
programs_df = programs_df.reset_index().set_index(['slug', 'levelSlug', 'programSlug'])
dups = get_duplicates(programs_df)
print(dups)

programs_df.loc[('cs-596', 'master', 'computer-science'), 'semesterNumbers'] = programs_df.loc[('cs-596', 'master', 'computer-science')].semesterNumbers[0]
programs_df.loc[('cs-596', 'master', 'cybersecurity'), 'semesterNumbers'] = programs_df.loc[('cs-596', 'master', 'cybersecurity')].semesterNumbers[0]

dups = get_duplicates(programs_df)
if len(dups) > 0:
    print('Unhandled duplicates (programs):\n', dups)
    print(programs_df.loc[dups.index])
assert dups.size == 0


programs_df = programs_df.reset_index().drop_duplicates()
programs_df['semesterNumbers'] = programs_df.semesterNumbers.apply(eval)


def key_func(series):
    if series.name == 'levelSlug':
        return series.replace({
            'propedeutics': 0,
            'bachelor': 1,
            'master': 2,
            'minor': 3,
            'doctoral-school': 4
        })
    return series

programs_df = programs_df.sort_values(by=['slug', 'levelSlug', 'programSlug'], key=key_func)


def create_program_column(r):
    program = {
        'title': r.programTitle,
        'slug': r.programSlug,
        'semesterNumbers': r.semesterNumbers
    }

    if r.levelSlug == 'master':
        program['specializations'] = (
            courses_specializations.loc[r.slug][r.programSlug]
            if r.programSlug in courses_specializations.loc[r.slug]
            else []
        )
    return program

programs_df['program'] = programs_df.apply(create_program_column, axis=1)


programs_df.drop(['programTitle', 'programSlug', 'semesterNumbers'], axis=1, inplace=True)


def agg_programs(df):
    first = df.iloc[0]
    return {
        'title': first.levelTitle,
        'slug': first.levelSlug,
        'programs': list(df.program)
    }

programs_df = programs_df.groupby(['slug', 'levelSlug'], sort=False).apply(agg_programs).droplevel('levelSlug')
programs_df = programs_df.groupby('slug', sort=False).apply(lambda ser: list(ser)).rename('levels')


courses_cb['levels'] = programs_df.astype(str)


courses_nolink = courses_sp[~courses_sp.index.isin(courses_cb.index)]
print('Courses without linked coursebook page:\n', courses_nolink.name)

# Manually fill in semester info for these courses later


# Ensure indexes of dataframes are compatible:
courses_cb = courses_cb.reindex(index=courses_sp.index)

# Fill NaN with empty list string (later converted to list)
courses_cb.loc[courses_cb.levels.isna(), 'levels'] = '[]'

#######################################
# Merge `courses_sp` and `courses_cb` #
#######################################

common_cols = courses_cb.columns.intersection(courses_sp.columns)
for col in common_cols:
    idx = courses_cb[col].isna()
    # Replace NaN in courses_cb with values in courses_sp
    courses_cb.loc[idx, col] = courses_sp.loc[idx, col]


# Lecturers in one dataframe contains only last names
# so we need to compare SCIPER numbers to detect discrepancies
lecturers = (
    pd.concat(
        [courses_sp.lecturers, courses_cb.lecturers],
        keys=['l_studyplan', 'l_coursebook'],
        axis=1
    )
    # str --> list
    .applymap(eval)
    # remove "Various/Invited lecturers", sciper 126096 is also used for that
    # note: remove this line later, since scraping code will take care of it
    .applymap(lambda lec: list(filter(lambda l: l['sciper'] and l['sciper'] != '126096', lec)))
)

lecturers_sciper = (
    lecturers
    .applymap(lambda val: sorted(v['sciper'] for v in val))
    # convert list back to string since we want to compare columns
    .astype(str)
)


lecturers_inconsistent = lecturers[lecturers_sciper.l_studyplan != lecturers_sciper.l_coursebook]
print('Inconsistent lecturers info in studyplans vs coursebooks')
print(lecturers_inconsistent)


# Lecturers info in coursebooks seem to be more reliable
# than info in studyplans, so we rely on the coursebooks
# Note! lecturers.l_coursebook column has already been cast to list
courses_sp.lecturers = lecturers.l_coursebook
courses_cb.drop('lecturers', axis=1, inplace=True)


common_cols = common_cols.drop('lecturers')


diffs = courses_sp[common_cols].ne(courses_cb[common_cols])
# drop columns with no differences
cols_diff = common_cols[diffs.any()]
cols_nodiff = common_cols.drop(cols_diff)
# drop from either dataframe
courses_cb.drop(cols_nodiff, axis=1, inplace=True)


with pd.option_context('display.max_rows', None):
    for col in cols_diff:
        df = pd.concat([
            courses_sp[col].loc[diffs[col]],
            courses_cb[col].loc[diffs[col]]
        ], axis=1, keys=[f'{col}_studyplan', f'{col}_coursebook'])
        print(df)


# coursebook is more up to date for columns 'credits' and 'examForm'
courses_sp.drop(['credits', 'examForm'], axis=1, inplace=True)
# studyplan is more up to date for column 'remark'
courses_cb.drop('remark', axis=1, inplace=True)


courses = pd.concat([courses_sp, courses_cb], axis=1)


# Manually fill in semester info for courses without coursebook link
print('Manually filling in semester info for courses without coursebook link')
print(list(courses_nolink.index))


spring = 'Spring'
fall = 'Fall'
Any = 'Any'

manual_semester = {
    # 'pens-223': spring,
    'civil-226': spring,
    'math-511': spring,
    'civil-464': spring,
    'ee-599-d': Any,
    'mgt-431': spring,
    'ch-709': spring,
    'ch-710': Any,  # uncertain
    'che-608-1': fall,
    'che-608-2': spring,
    'ch-610': fall,
    'ch-611': fall,
    'eng-628': Any,
    'bioeng-803': fall,  # summer school (late August)
    'phys-635': spring,
    # 'phys-642': Any,  # https://edu.epfl.ch/coursebook/en/statistical-physics-for-optimization-learning-PHYS-642
    # 'phys-816': spring
}

for idx, semester in manual_semester.items():
    courses.loc[idx, 'semester'] = semester


# values in these columns should not be NaN
cols_notna = ['code', 'name', 'section', 'language', 'lecturers', 'sourceSlug', 'semester', 'examForm', 'credits', 'levels']
cols_notna_each = courses[cols_notna].notna().all()
print('Columns not NaN check:\n')
print(cols_notna_each)
assert cols_notna_each.all()


# Fill NaN in other columns with empty string
courses.fillna(value='', inplace=True)


print('Comparing `subjectExamined` and `name` fields\n')
print(courses[courses.subjectExamined != courses.name][['subjectExamined', 'name']])


# Drop subjectExamined field
courses.drop('subjectExamined', axis=1, inplace=True)


text_cols = ['summary', 'content', 'keywords', 'requiredCourses', 'recommendedCourses', 'priorConcepts', 'preparationFor']
courses_text = courses[text_cols]
courses.drop(text_cols, axis=1, inplace=True)


# str --> list
courses[['levels']] = courses[['levels']].applymap(eval)
# str --> int
courses = courses.astype({
    'credits': int
})


#######################################
# Process and filter links            #
#######################################
links = read.read_json('req-links', 'labelled')

# filter out links that reference courses
# that are not there any more
course_slugs = courses.index.to_list()

links = [
    l for l in links
    if l['source'] in course_slugs and l['target'] in course_slugs
]

write.write_object('links', links, subdir='processed')

courses['requiredCourses'] = [[] for _ in range(len(courses))]
courses['dependentCourses'] = [[] for _ in range(len(courses))]

# add index as one of the columns
courses['slug'] = courses.index

cols = ['slug', 'code', 'name']
for link in links:
    source = courses.loc[link['source']]
    target = courses.loc[link['target']]
    target.requiredCourses.append(dict(source[cols]))
    source.dependentCourses.append(dict(target[cols]))

courses.reset_index(inplace=True, drop=True)
write.write_df_processed('courses', courses)
write.write_df_processed('courses-text', courses_text, orient='index')

# Process `programs` and create `epfl` dict

# add 'courses' property to all levels
for level in programs:
    # set comprehension
    level['courses'] = list({
        c
        for p in level['programs']
        for c in p['courses']
    })


# add 'courses' property to top level
epfl = {
    'courses': course_slugs,
    'levels': programs
}

write.write_object('epfl', epfl, subdir='processed')
