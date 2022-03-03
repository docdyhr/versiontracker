"""Get Applications incl. version obtained from other sources
    """

import argparse
import json
import logging
import os
import re
import sys
import textwrap

from fuzzywuzzy.fuzz import partial_ratio

# from ast import arguments


# TODO: Improve docstrings!

VERSION = "0.1.0"

SYSTEM_PROFILER_CMD = '/usr/sbin/system_profiler -json SPApplicationsDataType'
DESIRED_PATHS = ('/Applications/')  # desired paths for app filtering tuple

BREW_CMD = '/usr/local/bin/brew list --casks'
BREW_SEARCH = '/usr/local/bin/brew search'

# Logging: logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
# logging.ERROR, logging.CRITICAL,
# https://docs.python.org/3/library/logging.html
# TODO: Change locations of logfiles ie. '~/Library/Logs/Versiontracker'
LOG_LEVEL = logging.DEBUG

logging.basicConfig(filename='versiontracker.log',
                    format='%(asctime)s %(levelname)s %(name)s %(message)s',
                    encoding='utf-8', filemode='w', level=LOG_LEVEL)


def get_arguments() -> dict:
    """Return a dict of CLI arguments"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''\
         thomas@dyhr.com 2022
         '''))
    parser.add_argument(
        '-a',
        '--apps',
        # required=True,
        action='store_true',
        dest='apps',  # flexible number of values - incl. None / see parser.error
        help="return Apps in Applications/ that is not updated by App Store")
    parser.add_argument(
        '-b',
        '--brews',
        action='store_true',
        dest='brews',  # flexible number of values - incl. None / see parser.error
        help="return installable brews")
    parser.add_argument(
        '-r',
        '--recommend',
        action='store_true',
        dest='recom',  # flexible number of values - incl. None / see parser.error
        help="return recommandations for brew")

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '-q',
        '--quiet',
        action='store_true',  # flag only no args stores True / False value
        dest='quiet',
        help='only print errors')
    group.add_argument(
        '-v',
        '--verbose',
        action='store_true',  # flag only no args stores True / False value
        dest='verbose',
        help='increase output verbosity')
    group.add_argument(
        '-d',
        '--debug',
        action='store_true',  # flag only no args stores True / False value
        dest='debug',
        help='turn on debug mode')
    parser.add_argument(
        '-V',
        '--version',
        action='version',
        version=f'%(prog)s {VERSION}')

    # args = parser.parse_args()
    # if not args:
    #     parser.error(
    #         "[-] Please specify a website or a file with sites to check,"
    #         "use --help for more info.")

    return parser.parse_args(args=None if sys.argv[1:] else ['--help'])


def normalise_name(name: str) -> str:
    """Normalise names"""
    name = name.strip()  # removing whitespace
    name = re.sub(r'\d+', '', name)  # get rid of numbers in name
    if not name.isprintable():  # remove non printables
        name = ''.join(c for c in name if c.isprintable())
    return name

# TODO: Add custom type hint JSON


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


def filter_out_brews(applications: tuple, brews: list) -> tuple:
    """Filter out brews in Applications"""
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


def check_brew_optional_install(data: tuple) -> list:
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

    options = get_arguments()  # Get arguments
    print(f'DEBUG: {vars(options)}')  # DEBUG: Print arguments

    # DEBUG: Does not work when defined in main() i.e. out of scope
    # if options.debug:
    #     LOG_LEVEL = logging.DEBUG

    if options.apps:
        raw_data = json.loads(os.popen(SYSTEM_PROFILER_CMD).read())
        apps_folder = get_applications(raw_data)
        for item in apps_folder:
            app, ver = item
            print(f"{app} - ({ver})")

    if options.brews:
        apps_homebrew = os.popen(BREW_CMD).read().splitlines()
        for brew in apps_homebrew:
            if options.debug:
                logging.debug("\tbrew cask: %s", brew)
            print(brew)

    if options.recom:
        distill_recommended_apps(options)

    def distill_recommended_apps(options):
        raw_data = json.loads(os.popen(SYSTEM_PROFILER_CMD).read())
        apps_folder = get_applications(raw_data)
        apps_homebrew = os.popen(BREW_CMD).read().splitlines()
        search_brutto = filter_out_brews(apps_folder, apps_homebrew)
        brew_options = check_brew_optional_install(search_brutto)
        # cli_printer(brew_options)
        for re_brew in brew_options:
            if options.debug:
                logging.debug("\t recommended install: %s", re_brew)
            print(re_brew)


if __name__ == '__main__':
    main()
