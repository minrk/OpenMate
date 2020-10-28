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
orphan_sibling_opens_folder = package_settings.get("orphan-sibling-opens-folder", True)
never_implicitly_open_folders = package_settings.get(
    "never-implicitly-open-folders",
    [
        "~",
        "/",
        "/etc",
        "/tmp",
        "/usr",
        "/usr/local",
    ],
)


class OpenMateCommand(sublime_plugin.ApplicationCommand):
    """Open a file or folder in an existing window if it is already open"""

    def run(self, path):
        path = path.rstrip(os.path.sep)
        parent_path = os.path.dirname(path)
        its_a_dir = os.path.isdir(path)
        # when considering a directory,
        # use the directory itself when given a path to a dir
        # or the parent when it's a file
        if its_a_dir:
            dir_path = path
        else:
            dir_path = parent_path

        avoid_implicit_folders = set(
            [os.path.expanduser(p) for p in never_implicitly_open_folders]
        )

        # window priority
        # 0: current window
        # 1: project window with open folders
        # 2: orphan-file window
        active_window = sublime.active_window()
        active_id = active_window.id()

        def sort_key(win):
            if win.id() == active_id:
                return 0
            if win.folders():
                return 1
            else:
                return 2

        window_list = sorted(sublime.windows(), key=sort_key)

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
            folders = win.folders()
            if folders:
                has_folders = True
            elif not single_orphan_window:
                # no-folder view
                # when looking for a directory match for single-files,
                # consider folder-less windows a match
                # if they have an open file in the same folder
                has_folders = False
                folders = set()
                for view in win.views():
                    folders.add(os.path.dirname(view.file_name()))
                folders = sorted(folders)

            for folder in folders:
                if (
                    (
                        # it's a folder-having window, use prefix-match
                        # to find files in any sub-directory
                        has_folders
                        and (path + os.path.sep).startswith(folder + os.path.sep)
                    )
                    or (
                        # it's an orphan-file window and we've been asked to open a directory
                        # consider any open file in a subdirectory to be a match
                        # (reverse of above, preserves same behavior for `mate foo/x` `mate x` regardless of order)
                        (not has_folders)  # should we do this only for orphan files, or also sub-directories?
                        and its_a_dir
                        and (folder + os.path.sep).startswith(dir_path + os.path.sep)
                    )
                    or (
                        # it's an orphan-file window and we've been asked to open a file
                        # open two siblings in an adjacent folder
                        (not has_folders)
                        and not its_a_dir
                        and folder == dir_path
                    )
                ):
                    # found a matching window
                    # focus file and/or folder
                    # open view for file
                    # opening two siblings as orphans opens shared parent folder
                    # opening parent of orphan re-uses window (same for file then folder as folder then file)
                    if not its_a_dir:
                        # single-file

                        # create file if it doesn't exist?
                        # if not os.path.exists(path):
                        #     with open(path, "a"):
                        #         pass

                        if (
                            not has_folders
                            and orphan_sibling_opens_folder
                            # never implicitly open a project for big/common directories
                            and parent_path not in avoid_implicit_folders
                        ):
                            # window has no folder view,
                            # but has an open file in the same folder.
                            # add parent folder to the window
                            proj = win.project_data() or {"folders": []}
                            proj["folders"].append({"path": parent_path})
                            win.set_project_data(proj)
                        win.open_file(path)
                        win.run_command("reveal_in_side_bar")
                    elif (not has_folders) or path not in folders:
                        # requested opening of parent directory when a file
                        # within the
                        # window has no folder view,
                        # but has an open file in our folder.
                        # add our folder to the window and finish
                        proj = win.project_data() or {"folders": []}
                        proj["folders"].append({"path": path})
                        win.set_project_data(proj)
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
