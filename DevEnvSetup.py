import ctypes
import os
import subprocess
import time
import traceback

import win32gui  # requires pip install pywin32
from colorama import Fore

import Helper
from custom_exceptions import ParamError, IncompleteConfigFile, JustExit


class DevEnvSetup:

    def __init__(self, show_debug_info: bool, dry_run: bool, config: dict, helper: Helper):
        self.show_debug_info = show_debug_info
        self.dry_run = dry_run
        self.helper = helper
        self.config = config
        self.browser_name = ''  # name from a list of browsers. see json file
        self.browser_exe = ''
        self.browser_title = ''
        self.url = ''
        self.url2 = ''
        self.url3 = ''
        self.url4 = ''
        self.url5 = ''
        self.app_name = ''  # main app name
        self.work_dir = ''
        self.wait_before_start_delay: int = 0
        self.wait_after_start_delay: int = 0
        self.barrier_app_pathname = ''  # full path name of the barrier app
        self.barrier_service_name = ''  # if this is not blank, it is assumed that the barrier app will start it

    # Main entry point of this class
    def run(self) -> bool:
        try:
            required_sections = {
                'default',
                'browsers',
                'before',
                'after'
            }

            # scan through all the sections in the list and if any of them are not found in the config file,
            # add them to 'missing'
            missing = [section for section in required_sections if section not in self.config]

            if missing:
                raise IncompleteConfigFile(
                    f"Missing required config sections: {', '.join(missing)}"
                )

            self.work_dir = self.config['default']['work_dir']
            self.app_name = self.config['default']['app_name']
            self.browser_name = self.config['default']['browser']
            self.browser_title = self.config['default']['browser_title']

            # do variable expansion and replace $appName in the string with the app_name from above
            self.browser_title = self.expand_variables(self.browser_title)
            self.url = self.expand_variables(self.config.get('default', 'url', fallback=''))
            self.url2 = self.expand_variables(self.config.get('default', 'url2', fallback=''))
            self.url3 = self.expand_variables(self.config.get('default', 'url3', fallback=''))
            self.url4 = self.expand_variables(self.config.get('default', 'url4', fallback=''))

            # Collect info relating to the barrier app.
            # If the appname is not blank, make sure that app is running. Start it if not.
            # If the service name is not blank, wait for that service to start.
            # (It is assumed that the above # app will start it.)
            #
            # The app name can be blank, in which case it will be ignored.
            # The service name can be blank, in which case it will be ignored.
            if 'barrier_app' in self.config['default']:
                # The name of the app to run. Can be blank
                self.barrier_app_pathname = self.config['default']['barrier_app']

                # The name of the service to wait for. It is assumed that the above app will start it. Can be blank
                self.barrier_service_name = self.config['default']['barrier_service_name']

                # if 'service_name' in self.config['default']:
                #     self.traffic_light_service_name = self.config['default']['service_name']

            for x in self.config['browsers']:
                if x == self.browser_name:
                    self.browser_exe = self.config['browsers'][x]
                    break

            print(Helper.COLOUR_NORMAL + "Starting 'before' apps")
            ok2Continue = self.open_apps('before')
            if not ok2Continue:
                print(Helper.COLOUR_WARNING + "'before' apps failed to start")
            else:
                print(Helper.COLOUR_NORMAL + "'before' apps have started")

            # go start the barrier app, if there is one
            ok2Continue = self.start_barrier()

            if ok2Continue:
                print(Helper.COLOUR_NORMAL + "Starting 'after' apps")
                ok2Continue = self.open_apps('after')
                if not ok2Continue:
                    print(Helper.COLOUR_WARNING + "'after' apps failed to start")
                else:
                    print(Helper.COLOUR_NORMAL + "'after' apps have started")

        except IncompleteConfigFile as ex:
            # traceback.print_tb(ex.__traceback__)
            print(Fore.RED + f'Incomplete config file. {ex}')

        except KeyError as ex:
            # traceback.print_tb(ex.__traceback__)
            print(Fore.RED + f'Missing property in config file: {ex}')

        except Exception as ex:
            traceback.print_tb(ex.__traceback__)
            print(f'Exception! {ex}')

        return ok2Continue

    def expand_variables(self, text: str) -> str:
        """Expand variables like $appName in a string."""
        if not text:
            return text

        replacements = {
            '$appName': self.app_name
        }

        for placeholder, value in replacements.items():
            if placeholder in text:
                text = text.replace(placeholder, str(value))

        return text

    def open_apps(self, section_name: str) -> bool:
        """
        open all specified apps
        format      app0=C:/Program Files/xxx/xxx.exe~XXX Ultimate~4030, 0, 1096, 1080

        :param section_name:
        :return: bool   ok to continue
        """

        ok2Continue = True
        cmd2_run = ''
        try:
            # now process up to 16 app definitions in the specified section
            for i in range(16):
                other_app_name_idx = f'app{i}'
                if other_app_name_idx not in self.config[section_name]:
                    continue

                current_app_line = self.config[section_name][other_app_name_idx]
                if current_app_line == "":
                    continue

                s1 = current_app_line  # remember this as we need it for the debug print below
                current_app_line = current_app_line.replace('${url}', self.url)
                current_app_line = current_app_line.replace('${url2}', self.url2)
                current_app_line = current_app_line.replace('${url3}', self.url3)
                current_app_line = current_app_line.replace('${url4}', self.url4)
                current_app_line = current_app_line.replace('${url5}', self.url5)
                current_app_line = current_app_line.replace('${appName}', self.app_name)
                current_app_line = current_app_line.replace('${browser_title}', self.browser_title)
                current_app_line = current_app_line.replace('${workDir}', self.work_dir)
                current_app_line = current_app_line.replace('${app_name}', self.app_name)

                # ; format: 	(the following are separated by ' ~ '
                # Ignore the numbers at the start of line, they are only here for reference!
                #	0		appPath
                #	1		appTitle
                #	2		x, y, w, h
                #	3		params
                #	4		minimised
                #	5		before_start_delay, after_start_delay
                #   6		app2waitForPathname, app2waitForTitle
                #
                # Example:
                #   app2=${workDir}\00 file watcher.bat ~ File watcher ~ 5135, 800, 1270, 620 ~ none ~ no ~ 15,0 ~ netbeans64.exe,*Apache NetBeans*

                if self.show_debug_info:
                    print(Helper.COLOUR_DEBUG + f'before keyword expansion: {s1}')
                    print(Helper.COLOUR_DEBUG + f'after keyword expansion: {current_app_line}')

                self.wait_before_start_delay = 0
                self.wait_after_start_delay = 0
                # e.g.     app0=app_path~app_title~app x, y, w, h~delay_before,delay_after
                arr = current_app_line.split('~')
                for x in range(0, len(arr)):
                    arr[x] = arr[x].strip()

                if len(arr) < 2:
                    # print(Helper.COLOUR_WARNING + "*** App param should contain app path and title")
                    raise ParamError(Helper.COLOUR_WARNING + "*** App param should contain app path and title")

                # Get app title
                app_title = arr[1].strip()
                if app_title == '':
                    print(Helper.COLOUR_WARNING + "*** App title cannot be blank")
                    continue

                # Get app path
                app_path = arr[0].strip()
                if app_path == '${browser}':
                    app_path = self.browser_exe

                app_path = app_path.replace('/', '\\')
                if app_path == '':
                    print(Helper.COLOUR_WARNING + "*** App path cannot be blank")
                    continue

                if app_title == '${browser}':
                    app_path = self.browser_name

                # app_title = app_title.replace('${appName}', my_app_name)
                # app_title = app_title.replace('${browser_title}', self.browser_title)
                exact = True
                if app_title[0:1] == '*':
                    app_title = app_title[1:]
                    exact = False

                # get app params
                app_params = ''
                if len(arr) > 3:
                    app_params = arr[3].strip()
                    app_params = app_params.replace('/', '\\')

                start_minimised = False
                if len(arr) > 4:
                    s = arr[4]
                    start_minimised = s.lower() in ['true', '1', 't', 'y', 'yes']

                # get the wait before and after delays
                if len(arr) > 5:
                    s = arr[5]
                    if s != '':
                        app_delays = s.split(',')
                        self.wait_before_start_delay = int(app_delays[0])
                        self.wait_after_start_delay = int(app_delays[1])

                # wait for app to start, window title to look for
                if len(arr) > 6:
                    s = arr[6]
                    app_to_wait = s.split(',')  # [0] = app EXE pathname, [1] = app window title
                    if len(app_to_wait) != 2:
                        # print(Fore.RED + f'**********\nError: The app_to_wait_for option needs 2 parts, separated by comma.')
                        # break
                        raise ParamError(
                            Fore.RED + '**********\nError: The app_to_wait_for option needs 2 parts, separated by comma.')

                    self.wait_for_app(app_to_wait[0], app_to_wait[1])

                (hwnd, wndText) = self.helper.find_window_by_title(app_title, exact)
                if hwnd:
                    if self.show_debug_info:
                        print(Helper.COLOUR_DEBUG + f'\tUsing existing instance "{app_path}" {app_params}')
                else:
                    cmd2_run = f'"{app_path}" {app_params}'
                    if self.show_debug_info:
                        print(Helper.COLOUR_DEBUG + f'\tStarting {app_path} {app_params}')
                        print(Helper.COLOUR_DEBUG + f'\t\t{cmd2_run}')

                    if not self.dry_run:
                        if self.wait_before_start_delay != 0:
                            if self.show_debug_info:
                                print(
                                    Helper.COLOUR_DEBUG + f'\twaiting {self.wait_before_start_delay}s before starting app')

                            time.sleep(self.wait_before_start_delay)

                        print(f'Launching {cmd2_run}')
                        # subprocess.Popen(cmd2_run, shell=False)

                        try:
                            subprocess.Popen(cmd2_run, shell=False)
                        except FileNotFoundError:
                            # Handle the case where the file does not exist
                            print(Fore.RED + f'**********\nError: The file ["{cmd2_run}] was not found.')
                            break
                        except IOError as e:
                            # Handle other I/O errors (optional)
                            print(f"An I/O error occurred when trying to run: {cmd2_run}\n{e}")
                            break

                        except Exception as e:
                            # Catch any other unexpected exceptions (optional)
                            print(f"An unexpected error occurred when trying to run: {cmd2_run}\n{e}")
                            break

                        if self.wait_after_start_delay != 0:
                            if self.show_debug_info:
                                print(
                                    Helper.COLOUR_DEBUG + f'\twaiting {self.wait_after_start_delay}s after starting app')

                            time.sleep(self.wait_after_start_delay)

                    wait_counter = 0
                    window_found = False
                    if not self.dry_run:
                        while wait_counter < 20:
                            print(Helper.COLOUR_DEBUG + f'\r\tlooking for {app_title}, iteration {wait_counter}',
                                  end='')
                            (hwnd, wndText) = self.helper.find_window_by_title(app_title, exact)
                            if hwnd:
                                print(Helper.COLOUR_DEBUG + f'\n\t\twindow {app_title} found')
                                window_found = True
                                break

                            wait_counter += 1
                            time.sleep(2)

                    if not window_found:
                        print('')

                # the entry may contain a '~'-separated section with the window title
                # e.g.   app=C:/Program Files/SQLyog/SQLyog.exe~The title
                if hwnd and len(arr) >= 2:
                    s = arr[2]
                    coords = s.split(',')
                    x0 = int(coords[0])
                    y0 = int(coords[1])
                    w = int(coords[2])
                    h = int(coords[3])
                    if self.show_debug_info:
                        print(Helper.COLOUR_DEBUG + f'\tPositioning {app_title} at {x0}, {y0}, {w}, {h}')

                    win32gui.MoveWindow(hwnd, x0, y0, w, h, True)
                    if start_minimised:
                        ShowWindow = ctypes.windll.user32.ShowWindow
                        ShowWindow(hwnd, 6)  # MINIMIZE

        except ParamError as e:
            # Catch any other unexpected exceptions (optional)
            print(e)
            ok2Continue = False

        except Exception as e:
            # Catch any other unexpected exceptions (optional)
            print(f"An unexpected error occurred when trying to run: {cmd2_run}\n{e}")

        return ok2Continue

    def wait_for_app(self, app_EXE_pathname: str, app_EXE_Name: str):
        """
        Wait for an app to start
        # [0] = app EXE pathname, [1] = app window title
        """
        # is app running?
        if self.helper.is_exe_running(app_EXE_pathname):
            # if app is already running, skip all this
            print(Helper.COLOUR_INFO + f'\t{app_EXE_Name} is already running')
        else:
            if not self.dry_run:
                # otherwise start it and wait for it to settle
                print(Helper.COLOUR_INFO + f'\t{app_EXE_pathname} is not running, so i am starting it.')
                subprocess.Popen(app_EXE_pathname, shell=True)
                for i in range(15):
                    if self.helper.is_exe_running(app_EXE_Name):
                        print(Helper.COLOUR_INFO + f'\t{app_EXE_Name} is now running')
                        break

                    time.sleep(4 if i == 0 else 10)
            else:
                print(
                    Helper.COLOUR_INFO + f'\t{app_EXE_pathname} not running. I would have started it but we are in dry-run mode!')

    def start_barrier(self) -> bool:
        """
        At this point, the 'before' apps have been started
        Make sure the required barrier app and optional service are running
        If a barrier app is not specified, no checks are done to see if the specified barrier service is running!

        :return: bool  means ok to continue
        """

        ok2Continue = True
        try:
            # # no need to do anything if this is a dry run
            # if self.dry_run:
            #     raise JustExit(Helper.COLOUR_NORMAL + "Dry run. Skipping barrier app and service startup")

            # if no barrier app has been specified, don't bother checking anything else
            if self.barrier_app_pathname == '':
                raise JustExit(
                    Helper.COLOUR_NORMAL + "No barrier app specified. Skipping barrier app and service startup")

            # are we supposed to launch a barrier app and then wait for it to start?
            self.barrier_app_pathname = self.barrier_app_pathname.replace('/', '\\')
            barrier_exe = os.path.basename(self.barrier_app_pathname)

            # is the barrier app running?
            if self.helper.is_exe_running(barrier_exe):
                # if barrier app is already running skip all this
                print(Helper.COLOUR_INFO + f'\tBarrier app {barrier_exe} is already running')
            else:
                # otherwise start it and wait for it to settle
                cmd2_run = self.barrier_app_pathname
                if self.dry_run:
                    raise JustExit(
                        Helper.COLOUR_INFO + f'\tBarrier app {cmd2_run} not running. I would have started it.')

                print(
                    Helper.COLOUR_INFO + f'\tBarrier app {cmd2_run} not running. Starting it')

                # launch the barrier app
                subprocess.Popen(cmd2_run, shell=True)
                # make 15 rounds, waiting for it to start
                for i in range(15):
                    if self.helper.is_exe_running(barrier_exe):
                        print(Helper.COLOUR_INFO + f'\tBarrier app {barrier_exe} is now running')
                        break

                    # for the first iteration, only wait 2 seconds (the app may already be running), 10 for every other
                    time.sleep(2 if i == 0 else 10)

                # after all this, is it actually running?
                ok2Continue = ok2Continue and self.helper.is_exe_running(barrier_exe)

            # ok. the barrier app, if there is one specified, is running.
            # If there is a service name also specified, make sure it is running. It is assumed that the above
            # app will have launched it
            if ok2Continue and self.barrier_service_name != '':
                # is barrier service running?
                cmd2_run = self.barrier_service_name
                if not self.helper.is_exe_running(cmd2_run):
                    print(Helper.COLOUR_INFO + f'\t{cmd2_run} not running. Waiting for it ...')

                    # make 15 rounds, waiting for it to start
                    for i in range(15):
                        if self.helper.is_exe_running(cmd2_run):
                            print(Helper.COLOUR_INFO + f'\t {cmd2_run} is now running')
                            break

                        print(Helper.COLOUR_INFO + f'\r\twaiting for {cmd2_run}, attempt {i}')
                        # for the first iteration, only wait 2 seconds (the service may already be running), 10 for every other
                        time.sleep(2 if i == 0 else 10)
                else:
                    print(Helper.COLOUR_INFO + f'\t{cmd2_run} is already running')

                # after all this, is it actually running?
                ok2Continue = ok2Continue and self.helper.is_exe_running(cmd2_run)
        except JustExit:
            None

        return ok2Continue
