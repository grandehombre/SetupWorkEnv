import psutil
import win32gui  # requires pip install pywin32
from colorama import Fore

COLOUR_DEBUG = Fore.LIGHTBLUE_EX
COLOUR_WARNING = Fore.MAGENTA
COLOUR_INFO = Fore.YELLOW
COLOUR_NORMAL = Fore.LIGHTWHITE_EX


class Helper:
    def __init__(self):
        pass

        # def get_service(self, name: str) -> dict:
        #     """
        #         Return info on specified service
        #
        #     :param name:
        #     :return:
        #
        #     """
        #     service = None
        #     try:
        #         service = psutil.win_service_get(name)
        #         service = service.as_dict()
        #
        #     except Exception as ex:
        #         print(ex)
        #
        #     # print(service)
        #     return service
        #

    def enum_windows(self) -> list[tuple[int, str]]:
        """
        Get a list of all visible top-level windows on a Windows desktop.
        Only windows with non-empty titles are included (this filters out many hidden/system windows).
        It only gets top-level windows (not child controls inside windows).

        :return: A list of tuples like this: [ (window handle, window_text), (window handle, window_text), ...]
        """

        hwnd_list: list[tuple[int, str]] = []

        def wnd_handler(hwnd: int, mouse) -> None:
            """
            Callback function for EnumWindows.
            """
            if win32gui.IsWindow(hwnd):
                window_text: str = win32gui.GetWindowText(hwnd)
                if window_text:
                    hwnd_list.append((hwnd, window_text))

        win32gui.EnumWindows(wnd_handler, 0)
        return hwnd_list

    def find_window_by_title(self, title: str, exact=True) -> tuple[int, str]:
        """


        :param title: str
        :param exact: bool
        :return: tuple[int, str]    return handle and title of found window
        """
        hwnd = None
        title = title.upper()
        title = title.strip()
        # hn = set()     # to be used when we want to get back all matching windows, instead of just the first one
        #hwnd_list: list[tuple[int, str]] = []
        hwnd_list: list[tuple[int, str]] = self.enum_windows()
        for handle in hwnd_list:
            (hWnd, wndText) = handle
            s = win32gui.GetWindowText(hWnd)
            s = s.upper()
            s = s.strip()
            if s == '':
                continue

            ret = False
            if exact:
                ret = title == s
            else:
                ret = title in s

            if ret:
                # hn.add(handle)
                hwnd = handle
                break

        # to be used when we want to get back all matching windows, instead of just the first one
        # return hn if len(hn) == 0 else None
        if not ret:
            hWnd = None
            wndText = ''

        return (hWnd, wndText)

    def is_exe_running(self, exe_name: str) -> bool:
        """
        Check if the specified EXE is running.

        :param exe_name:
        :return:
        """
        try:
            res = False
            for p in psutil.process_iter(attrs=['pid', 'name']):
                if p.info['name'] is not None:
                    if exe_name in (p.info['name']).lower():
                        # print("yes", (p.info['name']).lower())
                        res = True
                        break

        except Exception as ex:
            print(ex)
            res = False

        return res

    def bring_to_foreground(self, window_title: str) -> None:
        """
        Look for a window with the specified title and move it to the foreground

        :param window_title:
        :return:
        """
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
