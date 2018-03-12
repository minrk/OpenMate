# OpenMate

SublimeText plugin for mimicking TextMate's CLI for opening files.
The goal is to keep files in windows with their parent folders.
When opening a file:

- If the file is already open, focus the relevant window/view
- If a window is already open with a folder containing the file, open in that window
- If no matching window is found, open a new window with the parent folder of the file as the project folder

Defines the `open_mate` command. In this repo is a `mate` script which opens files.
