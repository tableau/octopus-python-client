import tkinter as tk

from octopus_python_client.common import Common
from octopus_python_client.config import Config
from octopus_python_client.gui.wizard import Wizard


class MainGUI:
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.config = Config()
        self.server = Common(config=self.config)
        self.source_config = Config(is_source_server=True)
        self.source = Common(config=self.source_config)

    def set_gui(self):
        window = tk.Tk()
        window.title('Octopus python client - Developed by Tony Li & Tableau Cloud Engineering')
        window.option_add("*font", "calibri 14")
        window["bg"] = "black"

        # window.geometry('800x600')

        wiz = Wizard(window, server=self.server, source=self.source)
        wiz.pack()

        window.mainloop()


if __name__ == "__main__":
    MainGUI().set_gui()
