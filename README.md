# Desktop Time Tracker

A simple desktop time tracker built with Python's standard library, with no
external dependencies. Tracks both a primary work session and per-task time, persists
everything to local JSON files, and shows a rolling 14-day history with
per-task breakdown.

The UI is a dark-themed Tkinter window with a large digital timer, START /
PAUSE / STOP controls, a task dropdown with its own live timer, and a
top-right clock showing the current local date and time. All session data is
stored in `C:\time_tracker\logs\` and survives app restarts; an in-flight
session is flushed to disk on window close so no time is lost.

## Features

* Start / pause / stop timer
* Per-task timers
* Daily logs
* 14-day history

## How To Run

1. Install [Python 3](https://www.python.org/downloads/) (Tkinter ships with the
   standard installer on Windows).
2. Clone the repo:

   ```
   git clone https://github.com/nalamk/desktop-time-tracker.git
   ```

3. Run the app:

   ```
   python main.py
   ```

## About Me

_Your name here._ Short bio goes here. A sentence or two about who built this,
what you do, and how to reach you. Replace this paragraph with your own
introduction, role, and links (portfolio, LinkedIn, email, etc.).
