from titlecase import titlecase

from scraper.module import util
from scraper.module.const import base_url, studyplan_path


def scrape():
    """
    Scrapes all academic levels
    """
    print('>>> Scraping levels')
    url = util.join_path(base_url, studyplan_path)
    soup = util.bsoup(url)

    # Find all academic levels
    dl = soup.dl
    dts = dl.find_all('dt')
    levels = []

    for dt in dts:
        a = dt.a
        href = a.get('href')
        slug = href.rsplit('/', 1)[-1]
        title = a.text.replace('Cycle', '').strip()
        levels.append({
            'sourceSlug': slug,
            'slug': util.construct_level_slug(slug),
            'title': titlecase(title)
        })

    return levels


if __name__ == '__main__':
    import sys
    print(f'testing module {sys.argv[0]}')
    print(scrape())
