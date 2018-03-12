"""SublimeText command for opening files and folders

mimics TextMate's `mate` behavior rather than `subl's`.

Rather than opening files in the current window by default regardless of folder,
files are only opened in windows where a parent folder is already open.
If no such window exists, open a new window with the parent folder.
"""

import os

import sublime
import sublime_plugin


class OpenMateCommand(sublime_plugin.ApplicationCommand):
    """Open a file or folder in an existing window if it is already open"""
    def run(self, path):
        # prioritize current window
        window_list = sublime.windows()
        active_window = sublime.active_window()
        window_list.remove(active_window)
        window_list.insert(0, active_window)

        # first priority, focus already-open view
        if not os.path.isdir(path):
            for win in window_list:
                view = win.find_open_file(path)
                if view:
                    print("found already open", path)
                    win.focus_view(view)
                    if win is not active_window:
                        self.focus(win)
                    return

        # second priority, existing window with folder open
        for win in window_list:
            for folder in win.folders():
                if (path + os.path.sep).startswith(folder + os.path.sep):
                    print("found folder for", path)
                    if not os.path.isdir(path):
                        win.open_file(path)
                    if win is not active_window:
                        self.focus(win)
                    return

        # not already open, new window
        sublime.run_command("new_window")
        win = sublime.active_window()
        if os.path.isdir(path):
            proj = win.project_data() or {'folders': []}
            dir_path = path
            proj['folders'].append({'path': dir_path})
            win.set_project_data(proj)
        else:
            win.open_file(path)

    # window-focus logic from https://github.com/ccampbell/sublime-goto-window

    def focus(self, window_to_move_to):
        active_view = window_to_move_to.active_view()
        active_group = window_to_move_to.active_group()

        # In Sublime Text 2 if a folder has no open files in it the active view
        # will return None. This tries to use the actives view and falls back
        # to using the active group

        # Calling focus then the command then focus again is needed to make this
        # work on Windows
        if active_view is not None:
            window_to_move_to.focus_view(active_view)
            window_to_move_to.run_command('focus_neighboring_group')
            window_to_move_to.focus_view(active_view)
            return

        if active_group is not None:
            window_to_move_to.focus_group(active_group)
            window_to_move_to.run_command('focus_neighboring_group')
            window_to_move_to.focus_group(active_group)

    def description(self):
        return "Open a file in the right window"
