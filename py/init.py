from scraper import scraper
from utils import write

print('Running init.py...')

programs_info, courses_studyplan, courses_coursebook = scraper.scrape()
write.write_object_raw('programs', programs_info)
write.write_object_raw('courses-studyplan', courses_studyplan)
write.write_object_raw('courses-coursebook', courses_coursebook)

from postprocess import postprocess
from db import store
