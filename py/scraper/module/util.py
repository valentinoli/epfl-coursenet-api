import re
from requests import get
from bs4 import BeautifulSoup

from scraper.module.const import default_container_id

headers = {'User-Agent': 'epfl-coursenet.herokuapp.com - valentin.loftsson@epfl.ch - Thank you!'}

def join_path(*paths):
    return '/'.join(s.strip('/') for s in paths)


def bsoup(
    url,
    return_container=True,
    return_soup_object=False,
    container_id=default_container_id
):
    res = get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    if return_container:
        if return_soup_object:
            return (
                soup.find(id=container_id),
                soup
            )

        return soup.find(id=container_id)

    return soup


def camelCase(list_str):
    pascal_cased = ''.join([s.lower().capitalize() for s in list_str])
    camel_cased = pascal_cased[0].lower() + pascal_cased[1:]
    return camel_cased


def program_html_id(qs):
    """Returns program HTML id, constructed from query string"""
    return (
        qs['cb_cycle'].replace('min_', 'min')
        + '-'
        + qs['cb_section']
    )


def construct_level_slug(original_slug):
    return original_slug.replace('_', '-')


clean_remark_regex = re.compile('^\(+|\)+$')
def clean_remark(remark):
    # remove starting and closing parentheses
    string = clean_remark_regex.sub('', remark.strip())
    string = string.strip()
    if len(string) > 1:
        string = string[0].upper() + string[1:]
    return string
