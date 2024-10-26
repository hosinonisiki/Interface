import tkinter as tk
import tkinter.ttk as ttk

import re
import threading
import time
import typing
from typing import NoReturn
import logging
import xml.etree.ElementTree as ET
import requests

import numpy as np

import fpga
import custom_widgets

class GeneralInterface():
    # state constants
    FPGA_STATE_OFFLINE = 0
    FPGA_STATE_STANDBY = 1
    FPGA_STATE_BUSY = 2
    FPGA_STATE_UNKNOWN = 3
    FPGA_STATE_CONNECTING = 4

    def __init__(self):
        # loggings

        self.logger = logging.getLogger("logger")
        self.logger.setLevel(logging.DEBUG)
        self.log_handler = logging.FileHandler("logs/%s.log"%time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()))
        self.log_handler.setLevel(logging.DEBUG)
        self.error_handler = logging.FileHandler("logs/%s.err"%time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()))
        self.error_handler.setLevel(logging.ERROR)
        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d, %(funcName)s, %(filename)s: %(message)s")
        self.log_handler.setFormatter(self.formatter)
        self.error_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.log_handler)
        self.logger.addHandler(self.error_handler)
        
        # state variables

        self.fpga_state = self.FPGA_STATE_OFFLINE

        self.destroying_flag = False

        # layout

        # fpga settings

        self.root = tk.Tk()
        self.root.geometry("1000x500")
        self.root.title("General Interface")
        self.root.protocol("WM_DELETE_WINDOW", self.root_onclose)

        self.information = ttk.Label(self.root, text = "Information will be displayed here.")
        self.information.place(rely = 1, anchor = tk.SW)

        self.fpga_frame = ttk.LabelFrame(self.root, text = "FPGA", width = 280, height = 234, relief = tk.GROOVE)
        self.fpga_frame.place(x = 20, y = 15, anchor = tk.NW)

        self.fpga_connection_label = ttk.Label(self.fpga_frame, text = "FPGA IP address:")
        self.fpga_connection_label.place(x = 20, y = 0, anchor = tk.NW)

        self.fpga_connection_entry = ttk.Entry(self.fpga_frame, width = 20)
        self.fpga_connection_entry.place(x = 20, y = 20, anchor = tk.NW)
        self.fpga_connection_entry.insert(0, "COM3")
        self.fpga_connection_entry.bind("<Return>", lambda event:self.fpga_connection_button_onclick())
        
        self.fpga_connection_button = ttk.Button(self.fpga_frame, text = "Connect", command = self.fpga_connection_button_onclick)
        self.fpga_connection_button.place(x = 170, y = 18, anchor = tk.NW)
    
        self.fpga_disconnection_button = ttk.Button(self.fpga_frame, text = "Disconnect", command = self.fpga_disconnection_button_onclick, width = 32)
        self.fpga_disconnection_button.place(x = 20, y = 47, anchor = tk.NW)

        self.fpga_config_label = ttk.Label(self.fpga_frame, text = "Select configuration:")
        self.fpga_config_label.place(x = 20, y = 76, anchor = tk.NW)

        self.fpga_config_combobox = ttk.Combobox(self.fpga_frame, width = 30)
        self.fpga_config_combobox.place(x = 20, y = 96, anchor = tk.NW)
        self.fpga_config_combobox.bind("<<ComboboxSelected>>", lambda event:self.fpga_config_combobox_onselect())
        # parse config options
        self.config_root = ET.parse("config.xml").getroot()
        self.configs = []
        for i in self.config_root.findall("./configurations/config"):
            description = i.get("description")
            if len(description) > 35:
                description = description[:32] + "..."
            self.configs.append(description)
        self.fpga_config_combobox["values"] = self.configs

        self.fpga_initialization_button = ttk.Button(self.fpga_frame, text = "Initialize", command = self.fpga_initialization_button_onclick, width = 32)
        self.fpga_initialization_button.place(x = 20, y = 126, anchor = tk.NW)

        self.fpga_default_button = ttk.Button(self.fpga_frame, text = "Default parameter", command = self.fpga_default_button_onclick, width = 32)
        self.fpga_default_button.place(x = 20, y = 155, anchor = tk.NW)

        self.fpga_status_label = ttk.Label(self.fpga_frame, text = "FPGA status: OFFLINE")
        self.fpga_status_label.place(x = 20, y = 184, anchor = tk.NW)

        # terminal

        self.terminal_history = [""]
        self.terminal_history_pointer = 0

        self.terminal = ttk.Entry(self.root, width = 120)
        self.terminal.place(rely = 1, x = 5, y = -20, anchor = tk.SW)
        self.terminal.bind("<Return>", lambda event:self.terminal_enter())
        self.terminal.bind("<Up>", lambda event:self.terminal_up())
        self.terminal.bind("<Down>", lambda event:self.terminal_down())

        # parameter controllers

        self.parameter_controllers_rows = 4
        self.parameter_controllers_columns = 4
        self.parameter_controllers = []
        for i in range(self.parameter_controllers_rows):
            for j in range(self.parameter_controllers_columns):
                self.parameter_controllers.append(custom_widgets.ParameterController(self.root, x = 310 + 170 * j, y = 30 + 90 * i, mim = None))

        # command buttons

        self.command_buttons = []

        self.update()

    def root_onclose(self) -> None:
        self.logger.info("Closing main window.")
        self.destroying_flag = True
        self.root.after(20, self.root.destroy)
        return

    def loop(self) -> None:
        self.update_thread = threading.Thread(target = self.update_thread_function, args = (), daemon = True)
        self.update_thread.start()
        self.update()
        self.logger.info("Starting main loop.")
        self.root.mainloop()
        return

    def update_thread_function(self) -> NoReturn:
        self.logger.info("Update thread started.")
        last = {
            "fpga_state": self.fpga_state
        }
        while(True):
            time.sleep(0.03)
            if self.destroying_flag:
                self.logger.info("Stopping update thread.")
                return
            current = {
                "fpga_state": self.fpga_state
            }
            changed = False
            for state in current:
                if current[state] != last[state]:
                    self.logger.info("State change detected in %s: %d -> %d"%(state, last[state], current[state]))
                    changed = True
                    last[state] = current[state]
            if changed:
                self.update()

    def update(self) -> None:
        match self.fpga_state:
            case self.FPGA_STATE_OFFLINE:
                self.fpga_status_label["text"] = "FPGA status: OFFLINE"
                self.fpga_connection_button["text"] = "Connect"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.NORMAL
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_config_combobox["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.fpga_default_button["state"] = tk.DISABLED
            case self.FPGA_STATE_STANDBY:
                self.fpga_status_label["text"] = "FPGA status: STANDBY"
                self.fpga_connection_button["text"] = "Connect"
                self.fpga_connection_entry["state"] = tk.DISABLED
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.NORMAL
                self.fpga_config_combobox["state"] = tk.NORMAL
                self.fpga_initialization_button["state"] = tk.NORMAL
                self.fpga_default_button["state"] = tk.NORMAL
            case self.FPGA_STATE_BUSY:
                self.fpga_status_label["text"] = "FPGA status: BUSY"
                self.fpga_connection_button["text"] = "Connect"
                self.fpga_connection_entry["state"] = tk.DISABLED
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.NORMAL
                self.fpga_config_combobox["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.fpga_default_button["state"] = tk.DISABLED
            case self.FPGA_STATE_UNKNOWN:
                self.fpga_status_label["text"] = "FPGA status: UNKNOWN"
                self.fpga_connection_button["text"] = "Reconnect"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.NORMAL
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_config_combobox["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.fpga_default_button["state"] = tk.DISABLED
            case self.FPGA_STATE_CONNECTING:
                self.fpga_status_label["text"] = "FPGA status: CONNECTING"
                self.fpga_connection_button["text"] = "Connect"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_config_combobox["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.fpga_default_button["state"] = tk.DISABLED

    def fpga_connection_button_onclick(self) -> None:
        self.logger.info("FPGA connection button clicked.")
        self.ip = self.fpga_connection_entry.get()
        self.logger.debug("Connecting to FPGA at %s."%self.ip)
        self.information["text"] = "Connecting to FPGA."
        self.fpga_state = self.FPGA_STATE_CONNECTING
        self.fpga_connection_thread = threading.Thread(target = self.fpga_connection_thread_function, args = (), daemon = True)
        self.fpga_connection_thread.start()

    def fpga_connection_thread_function(self) -> None:
        self.logger.info("FPGA connection thread started.")
        try:
            self.logger.debug("Connecting to FPGA.")
            self.config_id = str(self.fpga_config_combobox.current())
            self.mim = fpga.MIM(self.ip, config_id = self.config_id, logger = self.logger)
        except Exception as e:
            self.logger.error("Failed to connect to FPGA: %s"%e.__repr__())
            self.information["text"] = "Failed to connect to FPGA: %s"%e.__repr__()
            self.fpga_state = self.FPGA_STATE_OFFLINE
        else:
            self.logger.debug("FPGA connected.")
            self.information["text"] = "FPGA online."
            self.fpga_state = self.FPGA_STATE_STANDBY
            for i in self.parameter_controllers:
                i.mim = self.mim
        return

    def fpga_disconnection_button_onclick(self) -> None:
        self.logger.info("FPGA disconnection button clicked.")
        self.information["text"] = "FPGA offline."
        self.fpga_state = self.FPGA_STATE_OFFLINE
        self.fpga_config_combobox.set("")
        for i in self.parameter_controllers:
            i.mim = None
            i.refresh()
        for i in self.command_buttons:
            i.destroy()
        self.fpga_disconnection_thread = threading.Thread(target = self.fpga_disconnection_thread_function, args = (), daemon = True)
        self.fpga_disconnection_thread.start()
        return
    
    def fpga_disconnection_thread_function(self) -> None:
        self.logger.info("FPGA disconnection thread started.")
        try:
            self.logger.debug("Disconnecting FPGA.")
            self.mim.disconnect()
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Error encountered when disconnecting FPGA: %s"%e.__repr__()
        else:
            self.logger.debug("FPGA disconnected.")
        return

    def fpga_config_combobox_onselect(self) -> None:
        self.mim.config_id = str(self.fpga_config_combobox.current())
        self.mim.parse_config()
        self.mim.sync_download()
        for i in self.parameter_controllers:
            i.refresh()
        for i in self.command_buttons:
            i.destroy()
        self.command_buttons = []
        root = ET.parse("button_config.xml").getroot()
        for i in root.findall("./configurations/config"):
            if i.get("id") == self.mim.config_id:
                for j in i.findall("./buttons/button"):
                    button = custom_widgets.ParameterSwitch(self.root, instrument = j.get("instrument"), parameter = j.get("parameter"), mim = self.mim, inverted = eval(j.get("inverted")), text = j.get("text"), width = 32)
                    button.place(x = 40, y = 254 + 32 * len(self.command_buttons), anchor = tk.NW)
                    self.command_buttons.append(button)
                break
        return

    def fpga_initialization_button_onclick(self) -> None:
        self.logger.info("FPGA initialization button clicked.")
        self.information["text"] = "Initializing FPGA."
        self.fpga_state = self.FPGA_STATE_BUSY
        self.fpga_initialization_thread = threading.Thread(target = self.fpga_initialization_thread_function, args = (), daemon = True)
        self.fpga_initialization_thread.start()
        return
            
    def fpga_initialization_thread_function(self) -> None:
        self.logger.info("FPGA initialization thread started.")
        try:
            self.logger.debug("Initializing FPGA.")
            self.mim.upload_config()
            self.mim.upload_parameter()
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Failed to initialize: %s"%e.__repr__()
        else:
            self.logger.debug("FPGA initialized.")
            self.information["text"] = "FPGA initialized."
            for i in self.parameter_controllers:
                i.refresh()
            for i in self.command_buttons:
                i.refresh()
        finally:
            self.fpga_state = self.FPGA_STATE_STANDBY
        return
    
    def fpga_default_button_onclick(self) -> None:
        self.logger.info("FPGA default button clicked.")
        self.information["text"] = "Uploading default parameters."
        self.fpga_state = self.FPGA_STATE_BUSY
        self.fpga_default_thread = threading.Thread(target = self.fpga_default_thread_function, args = (), daemon = True)
        self.fpga_default_thread.start()
        return
    
    def fpga_default_thread_function(self) -> None:
        self.logger.info("FPGA default thread started.")
        try:
            self.logger.debug("Uploading default parameters.")
            self.mim.upload_parameter()
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Failed to set default parameters: %s"%e.__repr__()
        else:
            self.logger.debug("Default parameters uploaded.")
            self.information["text"] = "Default parameters uploaded."
            for i in self.parameter_controllers:
                i.refresh_parameter()
            for i in self.command_buttons:
                i.refresh()
        finally:
            self.fpga_state = self.FPGA_STATE_STANDBY
        return
    
    def terminal_enter(self) -> None:
        command = self.terminal.get()
        try:
            self.logger.info("Terminal command entered: %s"%command)
            eval(command)
        except Exception as e:
            self.logger.error("%s"%e.__repr__())                         
            self.information["text"] = "Error encountered when implementing code: %s"%e.__repr__()
        else:
            self.logger.debug("Terminal command implemented.")
            self.information["text"] = command
            self.terminal.delete(0, tk.END)
            if len(self.terminal_history) == 1 and self.terminal_history[0] == "":
                self.terminal_history = [command]
            else:
                self.terminal_history.append(command)
            self.terminal_history_pointer = len(self.terminal_history)
        return

    def terminal_up(self) -> None:
        if self.terminal_history_pointer != 0:
            self.terminal_history_pointer = self.terminal_history_pointer - 1
        self.terminal.delete(0, tk.END)
        self.terminal.insert(0, self.terminal_history[self.terminal_history_pointer])
        return
        
    def terminal_down(self) -> None:
        if self.terminal_history_pointer != len(self.terminal_history):
            self.terminal_history_pointer = self.terminal_history_pointer + 1
        self.terminal.delete(0, tk.END)
        if self.terminal_history_pointer != len(self.terminal_history):
            self.terminal.insert(0, self.terminal_history[self.terminal_history_pointer])
        return

def main():
    main_window = GeneralInterface()
    main_window.loop()

if __name__ == '__main__':
    main()