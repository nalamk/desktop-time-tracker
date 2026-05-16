import customtkinter as ctk

from ui.app import TimeTracker


def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    TimeTracker(root)
    root.mainloop()


if __name__ == "__main__":
    main()
