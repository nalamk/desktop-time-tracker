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

I am Naveed Alam, a software engineer based in Pakistan. I work across the
.NET, Python, and JavaScript ecosystems and have shipped systems in fintech,
healthcare, and logistics. My day to day involves C#, .NET Core, React,
Next.js, Node.js, FastAPI, and cloud work on AWS and Azure. Lately I have
been spending time on AI tooling including RAG pipelines and LangChain.

This time tracker is something I built for myself to keep an eye on where my
hours actually go during the day.

You can reach me on GitHub at [@nalamk](https://github.com/nalamk).
