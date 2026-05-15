import configparser
import ctypes
import os
import sys
import time
import traceback

import click
from colorama import Style

import DevEnvSetup
import Helper
from custom_exceptions import JustExit, IncompleteConfigFile

"""
    Look in readme.md for info on how this app works
"""


#############################################
@click.command()
@click.option("--show-debug-info/--no-debug-info", default=False)
@click.option("--dry-run/--no-dry-run", default=False)
@click.option("--config-file", type=str)
def main(show_debug_info: bool, dry_run: bool, config_file: str) -> None:
    """

    The Click library makes this the entry point to this app.
    The above '@' options specify what options Click will accept in the command line.
    Parameters with 2 names, such as --dry-run/--no-dry-run, use the first name
    to create the variable name passed in, e.g. '--dry-run/--no-dry-run' becomes 'dry_run'

    Colorama.Style is used for terminal-output formatting.

    See the readme.md file for more info.

    :param show_debug_info:
    :param dry_run:
    :param config_file:
    :return:
    """
    version = "v1.0.7, 14may2026"
    app_exit_code: int = 0

    # reset colours etc used in the terminal output
    print(Style.RESET_ALL)

    try:
        # Helper contains misc low-level functions
        helper = Helper.Helper()

        # this is the name of this script, as passed to Python in the command line
        script_name = sys.argv[0]

        # and this is the full pathname of the current script
        script_full_path = os.path.realpath(script_name)
        # Get just the directory of the current script
        script_dir = os.path.dirname(script_full_path)
        # This is just the filename (incl extension)
        this_app_name = os.path.basename(script_full_path)

        # set the console title and make sure the app is in the foreground
        ctypes.windll.kernel32.SetConsoleTitleW(this_app_name)
        helper.bring_to_foreground(this_app_name)

        print(Helper.COLOUR_NORMAL + f'Work environment set up utility {version}')
        print(Helper.COLOUR_NORMAL + f'\tlocated at: {script_full_path}')

        if show_debug_info:
            print(Helper.COLOUR_DEBUG + f'{this_app_name = }')
            print(Helper.COLOUR_DEBUG + f'{script_name = }')
            print(Helper.COLOUR_DEBUG + f'{script_dir = }')

        if dry_run:
            print(Helper.COLOUR_INFO + 'This is just a dry run!')

        config: dict = {}
        if config_file == '' or config_file is None:
            print(Helper.COLOUR_WARNING + 'You must supply the --config-file argument')
            # one way or the other, we are done here
            raise JustExit()

        config_file = os.path.realpath(config_file)
        print(Helper.COLOUR_NORMAL + f'Config file: {config_file}')

        # open and parse the config file
        config = configparser.ConfigParser()
        config.read(config_file)

        # Ok, now we can go and do what we were designed for!
        des = DevEnvSetup.DevEnvSetup(show_debug_info, dry_run, config, helper)
        des.run()
    except JustExit:
        app_exit_code = 0

    except IncompleteConfigFile as ex:
        # traceback.print_tb(ex.__traceback__)
        print(Helper.COLOUR_WARNING + f'Incomplete config file exception! {ex}')
        app_exit_code = -2

    except Exception as ex:
        app_exit_code = -1
        traceback.print_tb(ex.__traceback__)
        print(Helper.COLOUR_WARNING + f'Exception! {ex}')

    finally:
        time.sleep(3)
        print(Helper.COLOUR_NORMAL + "Done!")
        exit(app_exit_code)


if __name__ == "__main__":
    main()
