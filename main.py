import tkinter as tk

from app import TimeTracker


def main():
    root = tk.Tk()
    TimeTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
