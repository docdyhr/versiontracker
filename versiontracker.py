"""Get Applications incl. version obtained from other sources
    """

import json
import logging
import os
import re
from fuzzywuzzy.fuzz import partial_ratio

SYSTEM_PROFILER_CMD = '/usr/sbin/system_profiler -json SPApplicationsDataType'
DESIRED_PATHS = ('/Applications/')  # desired paths for app filtering tuple

BREW_CMD = '/usr/local/bin/brew list --casks'
BREW_SEARCH = '/usr/local/bin/brew search'

# Logging: logging.DEBUG, logging.INFO
# https://docs.python.org/3/library/logging.html
# TODO: Change locations of logfiles ie. '~/Library/Logs/Versiontracker'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(filename='versiontracker.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s',
                    encoding='utf-8', filemode='w', level=LOG_LEVEL)


def normalise_name(name):
    """Normalise names"""
    name = name.strip()  # removing whitespace
    name = re.sub(r'\d+', '', name)  # get rid of numbers in name
    if not name.isprintable():  # remove non printables
        name = ''.join(c for c in name if c.isprintable())
    return name


def get_applications(data):
    """Get applications from other sources

    Args:
        DESIRED_PATHS (tuple): search paths
        data (json): system_profiler output
    """
    apps = []
    for app in data['SPApplicationsDataType']:
        if (app['path'].startswith(DESIRED_PATHS)
            and 'apple' not in app['obtained_from']
                and 'mac_app_store' not in app['obtained_from']):
            try:
                app_name = normalise_name(app['_name'])
                app_version = app['version'].strip()
                if app_name not in apps:
                    apps.append([app_name, app_version])
                logging.debug("\t%s %s", app_name.strip(), app_version)
            except KeyError:
                apps.append([app_name, ''])
                logging.info("\t%s,  KeyError: no version fixed!", app_name)
                logging.debug("\t%s %s", app_name, '')
    apps.sort(key=lambda apps: apps[0].casefold())
    return apps


def filter_out_brews(applications, brews):
    """Filter out brews in"""
    candidates = []
    search_list = []

    for app in applications:
        # app_name = normalise_name(app[0])
        app_name = app[0].strip().lower()
        candidates.extend(app[0]
                          for brew in brews if partial_ratio(app_name, brew) > 75)  # Fussy compare

    search_list.extend(app for app in applications if app[0] not in candidates)
    # TODO: Remove duplicate entries based on the name with a list comprehension usining unpacking

    search_list.sort(key=lambda item: item[0].casefold())
    return search_list


def check_brew_optional_install(data):
    """Returns list of optional apps to be installed with brew

    Args:
        data (list): list of optional installs with brew
    """
    installers = []

    for app in data:
        brew_search = f"{BREW_SEARCH} '{app[0]}'"
        if response := os.popen(brew_search).read().splitlines():
            response = [
                item for item in response if item and '==>' not in item]
            # print(response)
            logging.debug("\tBREW SEARCH: %s", response)
            installers.extend(
                app[0] for brew in response if partial_ratio(app[0], brew) > 75)
            # DEBUG:
            # print(installers)
    installers = list(set(installers))
    installers.sort(key=str.casefold)
    return installers


def main():
    """Main Function"""
    # Get data with system_profiler
    raw_data = json.loads(os.popen(SYSTEM_PROFILER_CMD).read())
    apps_folder = get_applications(raw_data)

    apps_homebrew = os.popen(BREW_CMD).read().splitlines()

    search_brutto = filter_out_brews(apps_folder, apps_homebrew)

    brew_options = check_brew_optional_install(search_brutto)

    for app in brew_options:
        print(app)

    # DEBUG:
    # for appliaction in search_brutto:
    #     app, ver = appliaction
    #     print(app, ver)


if __name__ == '__main__':
    main()
