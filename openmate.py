"""SublimeText command for opening files and folders

mimics TextMate's `mate` behavior rather than `subl's`.

Rather than opening files in the current window by default regardless of folder,
files are only opened in windows where a parent folder is already open.
If no such window exists, open a new window with the parent folder.
"""

import os
import shutil

import sublime
import sublime_plugin

package_settings = sublime.load_settings("OpenMate.sublime-settings")
single_orphan_window = package_settings.get("single-orphan-window", False)


class OpenMateCommand(sublime_plugin.ApplicationCommand):
    """Open a file or folder in an existing window if it is already open"""

    def run(self, path):
        # prioritize current window
        window_list = sublime.windows()
        active_window = sublime.active_window()
        window_list.remove(active_window)
        window_list.insert(0, active_window)

        its_a_dir = os.path.isdir(path)
        # first priority, focus already-open view
        if not its_a_dir:
            for win in window_list:
                view = win.find_open_file(path)
                if view:
                    win.focus_view(view)
                    if win is not active_window:
                        self.focus(win)
                    return

        # second priority, existing window with folder open
        for win in window_list:
            for folder in win.folders():
                if (path + os.path.sep).startswith(folder + os.path.sep):
                    if not os.path.isdir(path):
                        # create file
                        with open(path, "w"):
                            pass
                        win.open_file(path)
                        win.run_command("reveal_in_side_bar")
                    else:
                        # it's a directory. No way to reveal a folder in side bar,
                        # so reveal the first file in the side bar
                        found = False
                        for root, dirs, files in os.walk(path):
                            for filename in sorted(files):
                                # check if there's already an open file
                                # in our folder and focus it
                                file_path = os.path.join(root, filename)
                                view = win.find_open_file(file_path)
                                if view:
                                    win.focus_view(view)
                                    win.run_command("reveal_in_side_bar")
                                    found = True
                                    break
                            if found:
                                break
                            if files:
                                # files found in folder, but none open
                                # open first one, reveal in sidebar
                                # and close immediately
                                file_path = os.path.join(root, sorted(files)[0])
                                win.open_file(file_path)
                                win.run_command("reveal_in_side_bar")
                                win.run_command("close")
                                found = True
                        if not found:
                            print("no file to open for folder %s" % path)

                    if win is not active_window:
                        self.focus(win)
                    return

        # not already open, open in first no-folder window
        # if single-orphan-window is enabled
        if single_orphan_window and not its_a_dir:
            folderless_windows = [w for w in window_list if not w.folders()]
            if folderless_windows:
                win = folderless_windows[0]
                win.open_file(path)
                if win is not active_window:
                    self.focus(win)
                return

        # no appropriate window found, make a new one
        sublime.run_command("new_window")
        win = sublime.active_window()
        if its_a_dir:
            # TODO: find window with orphaned files and add folder to it
            dir_path = path
            proj = win.project_data() or {"folders": []}
            proj["folders"].append({"path": dir_path})
            win.set_project_data(proj)
        else:
            win.open_file(path)

    def nearby_window_key(self, path, win):
        """sort-key function for the window with files in the nearest folder"""
        distance = float("inf")
        for view in win.views():
            filename = view.file_name()
            if filename:
                distance = min(
                    self.path_distance(path, os.path.dirname(filename)), distance
                )
        return distance

    def path_distance(self, a, b):
        """Return relative path distance for two files

        For ranking nearby files
        """

        a_parts = a.split(os.path.sep)
        b_parts = b.split(os.path.sep)
        if len(a_parts) > len(b_parts):
            # force a to be shorter
            # since the results are symmetrical
            a_parts, b_parts = b_parts, a_parts
        for prefix_len in range(len(a_parts) + 1):
            if a_parts[: prefix_len + 1] != b_parts[: prefix_len + 1]:
                break

        return len(a_parts) + len(b_parts) - (2 * prefix_len)

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
            window_to_move_to.run_command("focus_neighboring_group")
            window_to_move_to.focus_view(active_view)
            return

        if active_group is not None:
            window_to_move_to.focus_group(active_group)
            window_to_move_to.run_command("focus_neighboring_group")
            window_to_move_to.focus_group(active_group)

    def description(self):
        return "Open a file in the right window"


class InstallOpenMateCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        win = sublime.active_window()
        win.show_input_panel(
            "Select installation location",
            "/usr/local/bin/openmate",
            self.on_done,
            None,
            None,
        )

    def on_done(self, dest):
        src = os.path.join(os.path.dirname(__file__), "mate")
        shutil.copyfile(src, dest)

    def description(self):
        """Install openmate executable"""
