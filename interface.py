import tkinter as tk
import tkinter.ttk as ttk

from PIL import Image, ImageTk

import re
import hashlib
import threading
import time
import typing
from typing import NoReturn
import logging

import numpy as np

import fpga
import tcm
import custom_widgets

def characteristic(waveform: list[float]) -> float:
    return np.max(waveform)

# todo: add a thread to constantly check the connection to FPGA
# todo: better analyzing algorithm for the temperature setpoint
# todo: control the states of knobs
# todo: provide guis to mim.fb

# maybe move to moku:go?
# change to datalogger for gathering data

class Interface():
    def __init__(self):
        # loggings

        self.logger = logging.getLogger("Logger")
        self.logger.setLevel(logging.DEBUG)

        # name log after the running time
        self.log_handler = logging.FileHandler("logs/%s.log"%time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()))
        self.log_handler.setLevel(logging.DEBUG)

        self.error_handler = logging.FileHandler("logs/%s.err"%time.strftime("%Y-%m-%d %H-%M-%S", time.localtime()))
        self.error_handler.setLevel(logging.ERROR)

        self.formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(lineno)d, %(funcName)s, %(filename)s: %(message)s")

        self.log_handler.setFormatter(self.formatter)
        self.error_handler.setFormatter(self.formatter)

        self.logger.addHandler(self.log_handler)
        self.logger.addHandler(self.error_handler)

        # constants and state variables

        # fpga states

        self.FPGA_STATE_OFFLINE = 0
        self.FPGA_STATE_STANDBY = 1
        self.FPGA_STATE_BUSY = 2
        self.FPGA_STATE_UNKNOWN = 3
        self.FPGA_STATE_CONNECTING = 4

        self.fpga_state = self.FPGA_STATE_OFFLINE

        # tcm states

        self.TCM_STATE_OFFLINE = 0
        self.TCM_STATE_STANDBY = 1
        self.TCM_STATE_BUSY = 2
        self.TCM_STATE_UNKNOWN = 3
        self.TCM_STATE_CONNECTING = 4

        self.tcm_state = self.TCM_STATE_OFFLINE

        # state of commands

        self.SOLITON_STATE_OFF = 0
        self.SOLITON_STATE_ON = 1

        self.soliton_state = self.SOLITON_STATE_OFF

        self.LOCKTEMP_STATE_OFF = 0
        self.LOCKTEMP_STATE_ON = 1

        self.locktemp_state = self.LOCKTEMP_STATE_OFF

        self.SETPOINT_STATE_OFF = 0
        self.SETPOINT_STATE_ON = 1

        self.setpoint_state = self.SETPOINT_STATE_OFF

        self.SWEEPING_STATE_OFF = 0
        self.SWEEPING_STATE_ON = 1

        self.sweeping_state = self.SWEEPING_STATE_OFF

        self.POWERLOCK_STATE_OFF = 0
        self.POWERLOCK_STATE_ON = 1

        self.powerlock_state = self.POWERLOCK_STATE_OFF

        self.KNOB_PANEL_STATE_OFF = 0
        self.KNOB_PANEL_STATE_ON = 1

        self.knob_panel_state = self.KNOB_PANEL_STATE_OFF

        # temperature parameters
        
        self.temperature_setpoint = 0
        self.temperature_actual = 0
        
        # interthread communication flags

        self.tcm_locktemp_flag = False
        self.tcm_disconnection_flag = False
        self.tcm_save_flag = False

        self.setpoint_disconnection_flag = False

        self.knob_uploading_flag = False

        # other flags

        self.developer = False
        self.setup_found = False

        # other initializations

        # Top class utilities
        
        self.root = tk.Tk()
        self.root.geometry("1200x400")
        self.root.title("Main panel")
        self.root.protocol("WM_DELETE_WINDOW", self.root_onclose)
        
        self.information = ttk.Label(self.root, text = "Information will be displayed here.")
        self.information.place(rely = 1, anchor = tk.SW)
        
        self.developer_entrance = ttk.Button(self.root, text = "D", command = self.developer_entrance_onclick, width = 2)
        self.developer_entrance.place(relx = 1, rely = 1, anchor = tk.SE)

        self.knob_panel_button = ttk.Button(self.root, command = self.knob_panel_button_onclick, width = 2.5)
        self.knob_panel_button.place(relx = 1, rely = 1, x = -25, anchor = tk.SE)
        self.knob_panel_button.image = ImageTk.PhotoImage(Image.open("icons/knob20.png").resize((17, 17)))
        self.knob_panel_button.config(image = self.knob_panel_button.image)
        
        # status panel
        
        self.status_panel_frame = ttk.LabelFrame(self.root, text = "Status panel", width = 280, height = 100, relief = tk.GROOVE)
        self.status_panel_frame.place(x = 910, y = 15, anchor = tk.NW)
        
        self.status_fpga_label = ttk.Label(self.status_panel_frame, text = "FPGA status: OFFLINE")
        self.status_fpga_label.place(x = 20, y = 0, anchor = tk.NW)

        self.status_tcm_label = ttk.Label(self.status_panel_frame, text = "TCM status: OFFLINE")
        self.status_tcm_label.place(x = 20, y = 20, anchor = tk.NW)
        
        # command panel
        
        self.command_panel = ttk.LabelFrame(self.root, text = "Command panel", width = 280, height = 194, relief = tk.GROOVE)
        self.command_panel.place(x = 910, y = 125, anchor = tk.NW)
        
        self.command_soliton_button = tk.Button(self.command_panel, text = "Generate soliton", command = self.command_soliton_button_onclick, width = 32)
        self.command_soliton_button.place(relx = 0.5, y = 4, anchor = tk.N)
        
        self.command_locktemp_button = tk.Button(self.command_panel, text = "Lock temperature", command = self.command_locktemp_button_onclick, width = 32)
        self.command_locktemp_button.place(relx = 0.5, y = 36, anchor = tk.N)
        
        self.command_setpoint_button = tk.Button(self.command_panel, text = "Auto configure temperature", command = self.command_setpoint_button_onclick, width = 32)
        self.command_setpoint_button.place(relx = 0.5, y = 68, anchor = tk.N)
        
        self.command_sweeping_button = tk.Button(self.command_panel, text = "Manual sweeping", command = self.command_sweeping_button_onclick, width = 32)
        self.command_sweeping_button.place(relx = 0.5, y = 100, anchor = tk.N)

        self.command_powerlock_button = tk.Button(self.command_panel, text = "Power lock", command = self.command_powerlock_button_onclick, width = 32)
        self.command_powerlock_button.place(relx = 0.5, y = 132, anchor = tk.N)


        # fpga section
        
        self.fpga_frame = ttk.LabelFrame(self.root, text = "FPGA", width = 280, height = 140, relief = tk.GROOVE)
        self.fpga_frame.place(x = 20, y = 15, anchor = tk.NW)
        
        self.fpga_connection_label = ttk.Label(self.fpga_frame, text = "FPGA local IP address:")
        self.fpga_connection_label.place(x = 20, y = 0, anchor = tk.NW)

        self.fpga_connection_entry = ttk.Entry(self.fpga_frame, width = 20)
        self.fpga_connection_entry.place(x = 20, y = 20, anchor = tk.NW)
        self.fpga_connection_entry.insert(0, "[fe80::7269:79ff:feb0:6d2]")
        self.fpga_connection_entry.bind("<Return>", lambda event:self.fpga_connection_button_onclick())
        
        self.fpga_connection_button = ttk.Button(self.fpga_frame, text = "Submit", command = self.fpga_connection_button_onclick)
        self.fpga_connection_button.place(x = 170, y = 18, anchor = tk.NW)
    
        self.fpga_disconnection_button = ttk.Button(self.fpga_frame, text = "Disconnect", command = self.fpga_disconnection_button_onclick, width = 32)
        self.fpga_disconnection_button.place(x = 20, y = 47, anchor = tk.NW)
    
        self.fpga_initialization_button = ttk.Button(self.fpga_frame, text = "Initialize", command = self.fpga_initialization_button_onclick, width = 32)
        self.fpga_initialization_button.place(x = 20, y = 76, anchor = tk.NW)
        
        # tcm section
        
        self.tcm_frame = ttk.LabelFrame(self.root, text = "TCM", width = 280, height = 200, relief = tk.GROOVE)
        self.tcm_frame.place(x = 300, y = 15, anchor = tk.NW)
        
        self.tcm_connection_label = ttk.Label(self.tcm_frame, text = "TCM port:")
        self.tcm_connection_label.place(x = 20, y = 0, anchor = tk.NW)

        self.tcm_connection_entry = ttk.Entry(self.tcm_frame, width = 20)
        self.tcm_connection_entry.place(x = 20, y = 20, anchor = tk.NW)
        self.tcm_connection_entry.insert(0, "COM13")
        self.tcm_connection_entry.bind("<Return>", lambda event:self.tcm_connection_button_onclick())
        
        self.tcm_connection_button = ttk.Button(self.tcm_frame, text = "Submit", command = self.tcm_connection_button_onclick)
        self.tcm_connection_button.place(x = 170, y = 18, anchor = tk.NW)
    
        self.tcm_disconnection_button = ttk.Button(self.tcm_frame, text = "Disconnect", command = self.tcm_disconnection_button_onclick, width = 32)
        self.tcm_disconnection_button.place(x = 20, y = 47, anchor = tk.NW)

        self.tcm_setpoint_entry = ttk.Entry(self.tcm_frame, width = 20)
        self.tcm_setpoint_entry.place(x = 20, y = 78, anchor = tk.NW)
        self.tcm_setpoint_entry.bind("<Return>", lambda event:self.tcm_setpoint_button_onclick())

        self.tcm_setpoint_button = ttk.Button(self.tcm_frame, text = "Set temp", command = self.tcm_setpoint_button_onclick)
        self.tcm_setpoint_button.place(x = 170, y = 76, anchor = tk.NW)
        
        self.tcm_setpoint_label = ttk.Label(self.tcm_frame, text = "Set temp: N/A")
        self.tcm_setpoint_label.place(x = 20, y = 102, anchor = tk.NW)
        
        self.tcm_temperature_label = ttk.Label(self.tcm_frame, text = "Current temp: N/A")
        self.tcm_temperature_label.place(x = 20, y = 122, anchor = tk.NW)
        
        self.tcm_save_button = ttk.Button(self.tcm_frame, text = "Save current temp", command = self.tcm_save_button_onclick, width = 32)
        self.tcm_save_button.place(x = 20, y = 142, anchor = tk.NW)

    def root_onclose(self) -> None:
        self.logger.info("Root closed.")
        self.root.destroy()
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
        last = (self.fpga_state, self.tcm_state, self.soliton_state, self.locktemp_state, self.setpoint_state, self.sweeping_state, self.powerlock_state, self.knob_panel_state)
        while(True):
            time.sleep(0.03)
            if (self.fpga_state, self.tcm_state, self.soliton_state, self.locktemp_state, self.setpoint_state, self.sweeping_state, self.powerlock_state, self.knob_panel_state) != last:
                self.logger.debug("State change detected: %d, %d, %d, %d, %d, %d, %d, %d"%(self.fpga_state, self.tcm_state, self.soliton_state, self.locktemp_state, self.setpoint_state, self.sweeping_state, self.powerlock_state, self.knob_panel_state))
                self.update()
                last = (self.fpga_state, self.tcm_state, self.soliton_state, self.locktemp_state, self.setpoint_state, self.knob_panel_state)
            # widgets that need real-time updates
            match self.tcm_state:
                case self.TCM_STATE_OFFLINE:
                    pass
                case self.TCM_STATE_STANDBY:
                    self.tcm_temperature_label["text"] = "Current temp: %.3f°C"%self.temperature_actual
                    self.tcm_setpoint_label["text"] = "Set temp: %.3f°C"%self.temperature_setpoint
                case self.TCM_STATE_BUSY:
                    self.tcm_temperature_label["text"] = "Current temp: %.3f°C"%self.temperature_actual
                    self.tcm_setpoint_label["text"] = "Set temp: %.3f°C"%self.temperature_setpoint
                case self.TCM_STATE_UNKNOWN:
                    pass
                case self.TCM_STATE_CONNECTING:
                    pass

    def update(self) -> None:
        # fpga panel widgets
        match self.fpga_state:
            case self.FPGA_STATE_OFFLINE:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_OFFLINE"
                self.status_fpga_label["text"] = "FPGA status: OFFLINE"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.NORMAL
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
            case self.FPGA_STATE_STANDBY:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_STANDBY"
                self.status_fpga_label["text"] = "FPGA status: STANDBY"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.DISABLED
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.NORMAL
                self.fpga_initialization_button["state"] = tk.NORMAL
            case self.FPGA_STATE_BUSY:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_BUSY"
                self.status_fpga_label["text"] = "FPGA status: BUSY"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.DISABLED
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.NORMAL
                self.fpga_initialization_button["state"] = tk.DISABLED
            case self.FPGA_STATE_UNKNOWN:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_UNKNOWN"
                self.status_fpga_label["text"] = "FPGA status: UNKNOWN"
                self.fpga_connection_button["text"] = "Reconnect"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.NORMAL
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
            case self.FPGA_STATE_CONNECTING:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_CONNECTING"
                self.status_fpga_label["text"] = "FPGA_status: CONNECTING"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
        # tcm panel widgets
        match self.tcm_state:
            case self.TCM_STATE_OFFLINE:
                if self.developer:
                    self.developer_state_tcm_label["text"] = "tcm_state = TCM_STATE_OFFLINE"
                self.status_tcm_label["text"] = "TCM status: OFFLINE"
                self.tcm_connection_button["text"] = "Submit"
                self.tcm_connection_entry["state"] = tk.NORMAL
                self.tcm_connection_button["state"] = tk.NORMAL
                self.tcm_disconnection_button["state"] = tk.DISABLED
                self.tcm_setpoint_entry["state"] = tk.DISABLED
                self.tcm_setpoint_button["state"] = tk.DISABLED
                self.tcm_save_button["state"] = tk.DISABLED
            case self.TCM_STATE_STANDBY:
                if self.developer:
                    self.developer_state_tcm_label["text"] = "tcm_state = TCM_STATE_STANDBY"
                self.status_tcm_label["text"] = "TCM status: STANDBY"
                self.tcm_connection_button["text"] = "Submit"
                self.tcm_connection_entry["state"] = tk.DISABLED
                self.tcm_connection_button["state"] = tk.DISABLED
                self.tcm_disconnection_button["state"] = tk.NORMAL
                self.tcm_setpoint_entry["state"] = tk.NORMAL
                self.tcm_setpoint_button["state"] = tk.NORMAL
                self.tcm_save_button["state"] = tk.NORMAL
            case self.TCM_STATE_BUSY:
                if self.developer:
                    self.developer_state_tcm_label["text"] = "tcm_state = TCM_STATE_BUSY"
                self.status_tcm_label["text"] = "TCM status: BUSY"
                self.tcm_connection_button["text"] = "Submit"
                self.tcm_connection_entry["state"] = tk.DISABLED
                self.tcm_connection_button["state"] = tk.DISABLED
                self.tcm_disconnection_button["state"] = tk.NORMAL
                self.tcm_setpoint_entry["state"] = tk.DISABLED
                self.tcm_setpoint_button["state"] = tk.DISABLED
                self.tcm_save_button["state"] = tk.DISABLED
            case self.TCM_STATE_UNKNOWN:
                if self.developer:
                    self.developer_state_tcm_label["text"] = "tcm_state = TCM_STATE_UNKNOWN"
                self.status_tcm_label["text"] = "TCM status: UNKNOWN"
                self.tcm_connection_button["text"] = "Reconnect"
                self.tcm_connection_entry["state"] = tk.NORMAL
                self.tcm_connection_button["state"] = tk.NORMAL
                self.tcm_disconnection_button["state"] = tk.DISABLED
                self.tcm_setpoint_entry["state"] = tk.DISABLED
                self.tcm_setpoint_button["state"] = tk.DISABLED
                self.tcm_save_button["state"] = tk.DISABLED
            case self.TCM_STATE_CONNECTING:
                if self.developer:
                    self.developer_state_tcm_label["text"] = "tcm_state = TCM_STATE_CONNECTING"
                self.status_tcm_label["text"] = "TCM status: CONNECTING"
                self.tcm_connection_button["text"] = "Submit"
                self.tcm_connection_entry["state"] = tk.NORMAL
                self.tcm_connection_button["state"] = tk.DISABLED
                self.tcm_disconnection_button["state"] = tk.DISABLED
                self.tcm_setpoint_entry["state"] = tk.DISABLED
                self.tcm_setpoint_button["state"] = tk.DISABLED
                self.tcm_save_button["state"] = tk.DISABLED
        match self.soliton_state:
            case self.SOLITON_STATE_OFF:
                if self.developer:
                    self.developer_state_soliton_label["text"] = "soliton_state = SOLITON_STATE_OFF"
            case self.SOLITON_STATE_ON:
                if self.developer:
                    self.developer_state_soliton_label["text"] = "soliton_state = SOLITON_STATE_ON"
        match self.locktemp_state:
            case self.LOCKTEMP_STATE_OFF:
                if self.developer:
                    self.developer_state_locktemp_label["text"] = "locktemp_state = LOCKTEMP_STATE_OFF"
            case self.LOCKTEMP_STATE_ON:
                if self.developer:
                    self.developer_state_locktemp_label["text"] = "locktemp_state = LOCKTEMP_STATE_ON"
        match self.setpoint_state:
            case self.SETPOINT_STATE_OFF:
                if self.developer:
                    self.developer_state_sweeping_label["text"] = "setpoint_state = SETPOINT_STATE_OFF"
            case self.SETPOINT_STATE_ON:
                if self.developer:
                    self.developer_state_sweeping_label["text"] = "setpoint_state = SETPOINT_STATE_ON"
        # command panel widgets
        match (self.fpga_state, self.soliton_state):
            case (self.FPGA_STATE_STANDBY, self.SOLITON_STATE_OFF):
                self.command_soliton_button["state"] = tk.NORMAL
                self.command_soliton_button["relief"] = tk.RAISED
            case (self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON):
                self.command_soliton_button["state"] = tk.NORMAL
                self.command_soliton_button["relief"] = tk.SUNKEN
            case _:
                self.command_soliton_button["state"] = tk.DISABLED
                self.command_soliton_button["relief"] = tk.RAISED
        match (self.tcm_state, self.locktemp_state):
            case (self.TCM_STATE_STANDBY, self.LOCKTEMP_STATE_OFF):
                self.command_locktemp_button["state"] = tk.NORMAL
                self.command_locktemp_button["relief"] = tk.RAISED
            case (self.TCM_STATE_STANDBY, self.LOCKTEMP_STATE_ON):
                self.command_locktemp_button["state"] = tk.NORMAL
                self.command_locktemp_button["relief"] = tk.SUNKEN
            case (self.TCM_STATE_BUSY, self.LOCKTEMP_STATE_ON):
                self.command_locktemp_button["state"] = tk.DISABLED
                self.command_locktemp_button["relief"] = tk.SUNKEN
            case _:
                self.command_locktemp_button["state"] = tk.DISABLED
                self.command_locktemp_button["relief"] = tk.RAISED
        match (self.fpga_state, self.tcm_state, self.locktemp_state, self.setpoint_state):
            case (self.FPGA_STATE_STANDBY, self.TCM_STATE_STANDBY, self.LOCKTEMP_STATE_ON, self.SETPOINT_STATE_OFF):
                self.command_setpoint_button["state"] = tk.NORMAL
                self.command_setpoint_button["relief"] = tk.RAISED
            case (self.FPGA_STATE_BUSY, self.TCM_STATE_BUSY, self.LOCKTEMP_STATE_ON, self.SETPOINT_STATE_ON):
                self.command_setpoint_button["state"] = tk.DISABLED
                self.command_setpoint_button["relief"] = tk.SUNKEN
            case _:
                self.command_setpoint_button["state"] = tk.DISABLED
                self.command_setpoint_button["relief"] = tk.RAISED
        match (self.fpga_state, self.sweeping_state):
            case (self.FPGA_STATE_STANDBY, self.SWEEPING_STATE_OFF):
                self.command_sweeping_button["state"] = tk.NORMAL
                self.command_sweeping_button["relief"] = tk.RAISED
            case (self.FPGA_STATE_BUSY, self.SWEEPING_STATE_ON):
                self.command_sweeping_button["state"] = tk.NORMAL
                self.command_sweeping_button["relief"] = tk.SUNKEN
            case _:
                self.command_sweeping_button["state"] = tk.DISABLED
                self.command_sweeping_button["relief"] = tk.RAISED
        match (self.fpga_state, self.powerlock_state):
            case (self.FPGA_STATE_STANDBY, self.POWERLOCK_STATE_OFF) | (self.FPGA_STATE_BUSY, self.POWERLOCK_STATE_OFF):
                self.command_powerlock_button["state"] = tk.NORMAL
                self.command_powerlock_button["relief"] = tk.RAISED
            case (self.FPGA_STATE_STANDBY, self.POWERLOCK_STATE_ON) | (self.FPGA_STATE_BUSY, self.POWERLOCK_STATE_ON):
                self.command_powerlock_button["state"] = tk.NORMAL
                self.command_powerlock_button["relief"] = tk.SUNKEN
            case _:
                self.command_powerlock_button["state"] = tk.DISABLED
                self.command_powerlock_button["relief"] = tk.RAISED
        match self.knob_panel_state:
            case self.KNOB_PANEL_STATE_OFF:
                self.knob_panel_button["state"] = tk.NORMAL
            case self.KNOB_PANEL_STATE_ON:
                self.knob_panel_button["state"] = tk.DISABLED
        return

    def developer_entrance_onclick(self) -> None:
        self.logger.debug("Developer entrance button clicked.")
        self.information["text"] = "Developer mode."
        self.developer_identification = tk.Tk()
        self.developer_identification.title("Developer identification")
        self.developer_identification.bind("<Return>", lambda event:self.developer_password_button_onclick())
        
        self.developer_password_label = ttk.Label(self.developer_identification, text = "Password:")
        self.developer_password_label.grid(row = 0, column = 0, sticky = tk.W)
        
        self.developer_password_entry = ttk.Entry(self.developer_identification)
        self.developer_password_entry.grid(row = 1, column = 0, sticky = tk.W)
        
        self.developer_password_button = ttk.Button(self.developer_identification, text = "Verify", command = self.developer_password_button_onclick)
        self.developer_password_button.grid(row = 2, column = 0, sticky = tk.N)
        return
    
    def developer_password_button_onclick(self) -> None:
        self.logger.debug("Developer password button clicked.")
        if hashlib.md5(self.developer_password_entry.get().encode()).hexdigest() == "51d963ab932f0861f7196c21553c2c52":
        #if True:
            self.logger.debug("Developer password verified.")
            self.information["text"] = "Unlocked developer utilities."
            self.developer_identification.destroy()
            self.developer_entrance.destroy()
            self.root.geometry("1200x700")
            self.developer = True
            
            self.developer_mode = ttk.LabelFrame(self.root, text = "Developer mode", width = 1160, height = 300, relief = tk.GROOVE)
            self.developer_mode.place(x = 20, y = 375, anchor = tk.NW)
            
            # developer mode
            
            self.terminal_history = [""]
            self.terminal_history_pointer = 0
            
            self.terminal = ttk.Entry(self.developer_mode, width = 120)
            self.terminal.place(rely = 1, x = 10, y = -10, anchor = tk.SW)
            self.terminal.bind("<Return>", lambda event:self.terminal_enter())
            self.terminal.bind("<Up>", lambda event:self.terminal_up())
            self.terminal.bind("<Down>", lambda event:self.terminal_down())

            # display internal states

            self.developer_state_frame = ttk.LabelFrame(self.developer_mode, text = "Internal states", width = 260, height = 125, relief = tk.GROOVE)
            self.developer_state_frame.place(x = 10, y = 0, anchor = tk.NW)

            self.developer_state_fpga_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_fpga_label.place(x = 10, y = 0, anchor = tk.NW)

            self.developer_state_tcm_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_tcm_label.place(x = 10, y = 20, anchor = tk.NW)

            self.developer_state_soliton_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_soliton_label.place(x = 10, y = 40, anchor = tk.NW)

            self.developer_state_locktemp_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_locktemp_label.place(x = 10, y = 60, anchor = tk.NW)

            self.developer_state_sweeping_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_sweeping_label.place(x = 10, y = 80, anchor = tk.NW)

            self.update()

            self.logger.debug("Developer panel generated.")
        else:
            self.logger.debug("Developer password incorrect.")
            self.information["text"] = "Wrong password."
        return
    
    def knob_panel_button_onclick(self) -> None:
        self.logger.debug("Knob panel button clicked.")
        self.information["text"] = "Knob panel."
        self.knob_panel_thread = threading.Thread(target = self.knob_panel_thread_function, args = (), daemon = True)
        self.knob_panel_thread.start()

    def knob_panel_thread_function(self) -> None:
        self.logger.info("Knob panel thread started.")
        try:
            self.knob_panel_state = self.KNOB_PANEL_STATE_ON
            self.knob_panel = tk.Toplevel()
            self.knob_panel.title("Knob panel")
            self.knob_panel.geometry("800x600")
            self.knob_panel.protocol("WM_DELETE_WINDOW", self.knob_panel_onclose)

            self.manual_offset_knob = custom_widgets.KnobFrame(self.knob_panel, image_path = "icons/knob.png", size = 100, name = "Manual offset", scale = 0.334, unit = "mV")
            self.manual_offset_knob.place(x = 10, y = 10, anchor = tk.NW)
            self.manual_offset_knob.knob.set_value(self.mim.tk.get_parameter("manual_offset"))
            self.manual_offset_knob.knob.on_spin = self.manual_offset_knob_onspin
            self.manual_offset_knob.knob.max = 32767
            self.manual_offset_knob.knob.min = -32767
            self.manual_offset_knob.knob.value_step = 30
            print(self.manual_offset_knob.knob.on_spin)
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Error encountered when generating knob panel: %s"%e.__repr__()
        else:
            self.logger.debug("Knob panel generated.")
            self.knob_panel.mainloop()
        return

    def knob_panel_onclose(self) -> None:
        self.logger.debug("Knob panel closed.")
        self.knob_panel_state = self.KNOB_PANEL_STATE_OFF
        self.knob_panel.destroy()
        return

    def manual_offset_knob_onspin(self) -> None:
        try:
            self.logger.debug("Setting manual offset to %d."%self.manual_offset_knob.knob.get_value())
            self.manual_offset_knob.update()
            self.mim.tk.set_parameter("manual_offset", self.manual_offset_knob.knob.get_value())
            if self.knob_uploading_flag == False:
                self.knob_uploading_flag = True
                self.knob_uploading_thread = threading.Thread(target = self.knob_uploading_thread_function, args = (), daemon = True)
                self.knob_uploading_thread.start()
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Error encountered when setting manual offset: %s"%e.__repr__()
        return

    def knob_uploading_thread_function(self) -> None:
        self.logger.info("Knob uploading thread started.")
        self.mim.tk.upload_control()
        self.knob_uploading_flag = False
        self.logger.debug("Knob parameter uploaded.")
        return

    def command_soliton_button_onclick(self) -> None:
        self.logger.info("Soliton button clicked.")
        match self.soliton_state:
            case self.SOLITON_STATE_ON:
                try:
                    self.logger.debug("Stopping soliton generation.")
                    self.mim.stop()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Soliton generation Stopped.")
                    self.information["text"] = "Soliton generation interrupted."
                    self.fpga_state = self.FPGA_STATE_STANDBY
                    self.soliton_state = self.SOLITON_STATE_OFF
            case self.SOLITON_STATE_OFF:
                try:
                    self.logger.debug("Starting soliton generation.")
                    self.mim.run()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Soliton generation started.")
                    self.information["text"] = "Started generation for single soliton."
                    self.fpga_state = self.FPGA_STATE_BUSY
                    self.soliton_state = self.SOLITON_STATE_ON
                    if self.knob_panel_state ==  self.KNOB_PANEL_STATE_ON:
                        self.manual_offset_knob.knob.set_value(0)
                        self.manual_offset_knob.update()
        return
    
    def command_locktemp_button_onclick(self) -> None:
        self.logger.info("Locktemp button clicked.")
        match self.locktemp_state:
            case self.LOCKTEMP_STATE_ON:
                self.logger.debug("Stopping locking temperature.")
                self.information["text"] = "Stopped locking temperature."
                self.locktemp_state = self.LOCKTEMP_STATE_OFF
                self.tcm_locktemp_flag = False
            case self.LOCKTEMP_STATE_OFF:
                self.logger.debug("Starting locking temperature.")
                self.information["text"] = "Started locking temperature."
                self.locktemp_state = self.LOCKTEMP_STATE_ON
                self.tcm_locktemp_flag = True
        return
    
    def command_setpoint_button_onclick(self) -> None:
        self.logger.info("Setpoint button clicked.")
        match self.setpoint_state:
            case self.SETPOINT_STATE_ON:
                self.logger.debug("Setpoint button accessed during sweeping.")
                self.information["text"] = "Error: setpoint button should not be accessible when sweeping."
            case self.SETPOINT_STATE_OFF:
                try:
                    self.logger.debug("Starting sweeping.")
                    self.mim.sweep()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Sweeping started.")
                    self.information["text"] = "Sweeping for moderate temperature."
                    self.fpga_state = self.FPGA_STATE_BUSY
                    self.tcm_state = self.TCM_STATE_BUSY
                    self.setpoint_state = self.SETPOINT_STATE_ON
                    self.setpoint_disconnection_flag = False
                    self.command_setpoint_thread = threading.Thread(target = self.command_setpoint_thread_function, args = (), daemon = True)
                    self.command_setpoint_thread.start()
        return
    
    def command_setpoint_thread_function(self) -> None:
        self.logger.info("Setpoint thread started.")
        N = 21
        templist = np.linspace(32.5, 34.5, N)
        waveforms = []
        try:
            for t in templist:
                self.temperature_setpoint = t
                for i in range(100):
                    if self.setpoint_disconnection_flag:
                        self.logger.debug("Setpoint thread interrupted due to disconnection.")
                        return
                    time.sleep(0.1)
                    if np.abs(self.temperature_actual - self.temperature_setpoint) >= 0.005:
                        continue
                    time.sleep(0.1)
                    if np.abs(self.temperature_actual - self.temperature_setpoint) >= 0.005:
                        continue
                    time.sleep(0.1)
                    if np.abs(self.temperature_actual - self.temperature_setpoint) >= 0.005:
                        continue
                    self.logger.debug("Temperature became stable around %.3f°C."%self.temperature_setpoint)
                    self.logger.debug("Collecting waveform.")
                    temp = self.mim.get_waveform()
                    if None in temp:
                        self.logger.debug("%d points collected with None value."%len(temp))
                    else:
                        self.logger.debug("%d points collected with max = %.3f, min = %.3f, mean = %.3f, dv = %.3f."%(len(temp), np.max(temp), np.min(temp), np.mean(temp), np.std(temp)))
                    waveforms.append(temp)
                    break
                else:
                    self.logger.error("Temperature did not stablize around %.3f°C in 10 seconds."%self.temperature_setpoint)
                    raise Exception("Actual temperature did not fall in expected zone in 10 seconds.")
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Timeout? when sweeping for moderate temperature: %s"%e.__repr__()
        else:
            # todo: better analyzing algorithm
            self.logger.debug("Waveforms collected.")
            characteristics = list(map(characteristic, waveforms))
            self.logger.debug("Characteristics calculated: %s"%characteristics)
            print(characteristics)
            start = 0
            for i in range(0, N - 1):
                if start == 0 and characteristics[i] > 0.150: # requires change if pd is to be replaced
                    self.logger.debug("Start found at %.3f°C."%templist[start])
                    start = i
                    continue
                if start != 0 and characteristics[i + 1] < np.mean(characteristics[start:i + 1]) * 0.95:
                    self.logger.debug("End found at %.3f°C."%templist[i])
                    self.temperature_setpoint = templist[i - 1]
                    self.information["text"] = "Found moderate temperature."
                    break
            else:
                self.logger.debug("Temperature setpoint not found.")
                self.temperature_setpoint = templist[0]
                self.information["text"] = "Temperature setpoint not found."
        finally:
            self.fpga_state = self.FPGA_STATE_STANDBY
            self.tcm_state = self.TCM_STATE_STANDBY
            self.setpoint_state = self.SETPOINT_STATE_OFF
            self.mim.stop()
            self.logger.debug("Setpoint thread ended.")
        return
    
    def command_sweeping_button_onclick(self) -> None:
        self.logger.info("Sweeping button clicked.")
        match self.sweeping_state:
            case self.SWEEPING_STATE_ON:
                try:
                    self.logger.debug("Stopping sweeping.")
                    self.mim.stop()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Sweeping stopped.")
                    self.information["text"] = "Sweeping stopped."
                    self.fpga_state = self.FPGA_STATE_STANDBY
                    self.sweeping_state = self.SWEEPING_STATE_OFF
            case self.SWEEPING_STATE_OFF:
                try:
                    self.logger.debug("Starting sweeping.")
                    self.mim.sweep()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Sweeping started.")
                    self.information["text"] = "Started sweeping."
                    self.fpga_state = self.FPGA_STATE_BUSY
                    self.sweeping_state = self.SWEEPING_STATE_ON
                    if self.knob_panel != None and self.knob_panel.winfo_exists():
                        self.manual_offset_knob.knob.set_value(0)
                        self.manual_offset_knob.update()
        return
    
    def command_powerlock_button_onclick(self) -> None:
        self.logger.info("Powerlock button clicked.")
        match self.powerlock_state:
            case self.POWERLOCK_STATE_ON:
                try:
                    self.logger.debug("Stopping power lock.")
                    self.mim.tk.power_lock_OFF()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Power lock stopped.")
                    self.information["text"] = "Power lock released."
                    self.powerlock_state = self.POWERLOCK_STATE_OFF
            case self.POWERLOCK_STATE_OFF:
                try:
                    self.logger.debug("Starting power lock.")
                    self.mim.tk.power_lock_ON()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Power lock started.")
                    self.information["text"] = "Power lock initiated."
                    self.powerlock_state = self.POWERLOCK_STATE_ON
        return
    
    def fpga_connection_button_onclick(self) -> None:
        self.logger.info("FPGA connection button clicked.")
        self.ip = self.fpga_connection_entry.get()
        # allow ipv6 connections
        if re.match(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$", self.ip) or re.match(r"^\[([0-9a-fA-F]{0,4}:){5,7}[0-9a-fA-F]{0,4}\]$", self.ip):
            self.logger.debug("Connecting to FPGA at %s."%self.ip)
            self.information["text"] = "Connecting to FPGA."
            self.fpga_state = self.FPGA_STATE_CONNECTING
            self.fpga_connection_thread = threading.Thread(target = self.fpga_connection_thread_function, args = (), daemon = True)
            self.fpga_connection_thread.start()
        else:
            self.logger.debug("Illegal ip address: %s"%self.ip)
            self.information["text"] = "Illegal ip address."
        return
    
    def fpga_connection_thread_function(self) -> None:
        self.logger.info("FPGA connection thread started.")
        try:
            self.logger.debug("Connecting to FPGA.")
            self.mim = fpga.MIM(self.ip, self.logger)
            self.setup_found = False # So far a connection to FPGA is destined to clear the setup
            self.powerlock_state = self.POWERLOCK_STATE_OFF
            if self.setup_found:
                if self.mim.tk.get_parameter("PID_lock") == 0:
                    self.powerlock_state = self.POWERLOCK_STATE_ON
        except BaseException as e:
            self.logger.error("Failed to connect to FPGA: %s"%e.__repr__())
            self.information["text"] = "Failed to connect to FPGA: %s"%e.__repr__()
            self.fpga_state = self.FPGA_STATE_OFFLINE
        else:
            self.logger.debug("FPGA connected.")
            self.information["text"] = "FPGA online."
            self.fpga_state = self.FPGA_STATE_STANDBY
            self.soliton_state = self.SOLITON_STATE_OFF
            self.sweeping_state = self.SWEEPING_STATE_OFF
            # todo: launch an idle task to constantly check the connection
        return
    
    def fpga_disconnection_button_onclick(self) -> None:
        self.logger.info("FPGA disconnection button clicked.")
        self.information["text"] = "FPGA offline."
        self.fpga_state = self.FPGA_STATE_OFFLINE
        self.fpga_disconnection_thread = threading.Thread(target = self.fpga_disconnection_thread_function, args = (), daemon = True)
        self.fpga_disconnection_thread.start()
        return
    
    def fpga_disconnection_thread_function(self) -> None:
        self.logger.info("FPGA disconnection thread started.")
        try:
            if self.setpoint_state == self.SETPOINT_STATE_ON:
                self.setpoint_disconnection_flag = True
                self.logger.debug("Waiting for setpoint thread to end.")
                self.command_setpoint_thread.join()
                self.logger.debug("Setpoint thread ended.")
                self.setpoint_disconnection_flag = False
            self.logger.debug("Disconnecting FPGA.")
            self.mim.disconnect()
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Error encountered when disconnecting FPGA: %s"%e.__repr__()
        else:
            self.logger.debug("FPGA disconnected.")
        return
    
    def fpga_initialization_button_onclick(self) -> None:
        self.logger.info("FPGA initialization button clicked.")
        if self.information["text"] != "Are you sure you want to initialize FPGA settings? Press again for to confirm.":
            self.information["text"] = "Are you sure you want to initialize FPGA settings? Press again for to confirm."
        else:
            self.information["text"] = "Initializing..."
            self.fpga_state = self.FPGA_STATE_BUSY
            self.fpga_initialization_thread = threading.Thread(target = self.fpga_initialization_thread_function, args = (), daemon = True)
            self.fpga_initialization_thread.start()
        return
            
    def fpga_initialization_thread_function(self) -> None:
        self.logger.info("FPGA initialization thread started.")
        try:
            self.logger.debug("Initializing FPGA.")
            self.mim.initialize()
            self.setup_found = True
            if self.mim.tk.get_parameter("PID_lock") == 0:
                self.powerlock_state = self.POWERLOCK_STATE_ON
            else:
                self.powerlock_state = self.POWERLOCK_STATE_OFF
        except BaseException as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Failed to initialize: %s"%e.__repr__()
        else:
            self.logger.debug("FPGA initialized.")
            self.information["text"] = "FPGA initialized."
        finally:
            self.fpga_state = self.FPGA_STATE_STANDBY
        return
    
    def tcm_connection_button_onclick(self) -> None:
        self.logger.info("TCM connection button clicked.")
        self.port = self.tcm_connection_entry.get()
        self.information["text"] = "Connecting..."
        self.tcm_state = self.TCM_STATE_CONNECTING
        self.tcm_connection_thread = threading.Thread(target = self.tcm_connection_thread_function, args = (), daemon = True)
        self.tcm_connection_thread.start()
        return
     
    def tcm_connection_thread_function(self) -> None:
        self.logger.info("TCM connection thread started.")
        try:
            self.logger.debug("Connecting to TCM.")
            self.tcm = tcm.TCM(self.port, logger = self.logger)
            self.temperature_setpoint = self.tcm.get_setpoint()
            match self.tcm.get_switch():
                case 1:
                    self.locktemp_state = self.LOCKTEMP_STATE_ON
                    self.tcm_locktemp_flag = True
                case 0:
                    self.locktemp_state = self.LOCKTEMP_STATE_OFF
                    self.tcm_locktemp_flag = False
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Failed to connect to TCM: %s"%e.__repr__()
            self.tcm_state = self.TCM_STATE_OFFLINE
        else:
            self.logger.debug("TCM connected.")
            self.information["text"] = "TCM online."
            self.tcm_state = self.TCM_STATE_STANDBY
            self.update()
            self.tcm_disconnection_flag = False
            self.tcm_temperature_thread = threading.Thread(target = self.tcm_temperature_thread_function, args = (), daemon = True)
            self.tcm_temperature_thread.start()
        return
            
    def tcm_temperature_thread_function(self) -> None:
        self.logger.info("TCM temperature thread started.")
        while(True):
            time.sleep(0.1)
            try:
                if self.tcm_disconnection_flag:
                    self.logger.debug("TCM temperature thread interrupted due to disconnection.")
                    return
                if self.tcm_locktemp_flag:
                    self.logger.debug("Locking temperature.")
                    self.tcm.set_on()
                    self.logger.debug("Temperature locked.")
                else:
                    self.logger.debug("Unlocking temperature.")
                    self.tcm.set_off()
                    self.logger.debug("Temperature unlocked.")
                if self.tcm_save_flag:
                    self.tcm_save_flag = False
                    self.logger.debug("Saving setpoint.")
                    self.tcm.save()
                self.tcm.set_temp(self.temperature_setpoint)
                self.temperature_actual = float(self.tcm.get_temp())
            except Exception as e:
                self.logger.error("%s"%e.__repr__())
                try:
                    self.logger.debug("Closing TCM.")
                    self.tcm.close()
                    if self.setpoint_state == self.SETPOINT_STATE_ON:
                        self.logger.debug("Stopping FPGA.")
                        self.mim.stop()
                except Exception:
                    self.logger.error("%s"%e.__repr__())
                    pass
                finally:
                    self.information["text"] = "Error encountered when communicating through TCM port: %s"%e.__repr__()
                    self.tcm_state = self.TCM_STATE_UNKNOWN
                    if self.setpoint_state == self.SETPOINT_STATE_ON:
                        self.fpga_state = self.FPGA_STATE_UNKNOWN
                    break
        return
       
    def tcm_disconnection_button_onclick(self) -> None:
        self.logger.info("TCM disconnection button clicked.")
        try:
            self.tcm_disconnection_flag = True
            self.logger.debug("Waiting for TCM temperature thread to end.")
            self.tcm_temperature_thread.join()
            self.logger.debug("TCM temperature thread ended.")
            self.tcm_disconnection_flag = False
            self.logger.debug("Closing TCM.")
            self.tcm.close()
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Error encountered when closing TCM port: %s"%e.__repr__()
        finally:
            self.logger.debug("TCM disconnected.")
            self.information["text"] = "TCM offline."
            self.tcm_state = self.TCM_STATE_OFFLINE
        return

    def tcm_setpoint_button_onclick(self) -> None:
        self.logger.info("TCM setpoint button clicked.")
        temp = self.tcm_setpoint_entry.get()
        if re.match(r"^[0-9]{2}(\.[0-9]+)?$", temp):
            self.logger.debug("Setting temperature to %s."%temp)
            self.temperature_setpoint = float(temp)
        else:
            self.logger.debug("Illegal temperature: %s"%temp)
            self.information["text"] = "Illegal temperature."
        return

    def tcm_save_button_onclick(self) -> None:
        self.logger.info("TCM save button clicked.")
        self.tcm_save_flag = True
        return

    def terminal_enter(self) -> None:
        command = self.terminal.get()
        try:
            eval(command)
        except BaseException as e:                         
            self.information["text"] = "Error encountered when implementing code: %s"%e.__repr__()
        else:
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

if __name__ == "__main__":

    main = Interface()
    main.logger.info("Main panel initialized.")
    main.loop()