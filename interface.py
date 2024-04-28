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

class Interface():

    FPGA_STATE_OFFLINE = 0
    FPGA_STATE_STANDBY = 1
    FPGA_STATE_BUSY = 2
    FPGA_STATE_UNKNOWN = 3
    FPGA_STATE_CONNECTING = 4

    TCM_STATE_OFFLINE = 0
    TCM_STATE_STANDBY = 1
    TCM_STATE_BUSY = 2
    TCM_STATE_UNKNOWN = 3
    TCM_STATE_CONNECTING = 4

    SOLITON_STATE_OFF = 0
    SOLITON_STATE_ON = 1

    LOCKTEMP_STATE_OFF = 0
    LOCKTEMP_STATE_ON = 1

    SETPOINT_STATE_OFF = 0
    SETPOINT_STATE_ON = 1

    SWEEPING_STATE_OFF = 0
    SWEEPING_STATE_ON = 1

    POWERLOCK_STATE_OFF = 0
    POWERLOCK_STATE_ON = 1

    KNOB_PANEL_STATE_OFF = 0
    KNOB_PANEL_STATE_ON = 1

    FPGA_CONTROL_PANEL_STATE_OFF = 0
    FPGA_CONTROL_PANEL_STATE_ON = 1

    LO_STATE_OFF = 0
    LO_STATE_ON = 1

    FAST_PID_STATE_OFF = 0
    FAST_PID_STATE_ON = 1

    SLOW_PID_STATE_OFF = 0
    SLOW_PID_STATE_ON = 1

    AUTO_MATCH_STATE_OFF = 0
    AUTO_MATCH_STATE_ON = 1

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

        self.fpga_state = self.FPGA_STATE_OFFLINE

        # tcm states

        self.tcm_state = self.TCM_STATE_OFFLINE

        # state of commands

        self.soliton_state = self.SOLITON_STATE_OFF

        self.locktemp_state = self.LOCKTEMP_STATE_OFF

        self.setpoint_state = self.SETPOINT_STATE_OFF

        self.sweeping_state = self.SWEEPING_STATE_OFF

        self.powerlock_state = self.POWERLOCK_STATE_OFF

        self.knob_panel_state = self.KNOB_PANEL_STATE_OFF

        self.fpga_control_panel_state = self.FPGA_CONTROL_PANEL_STATE_OFF

        self.LO_state = self.LO_STATE_OFF

        self.fast_PID_state = self.FAST_PID_STATE_OFF

        self.slow_PID_state = self.SLOW_PID_STATE_OFF

        self.auto_match_state = self.AUTO_MATCH_STATE_OFF

        # temperature parameters
        
        self.temperature_setpoint = 0
        self.temperature_actual = 0
        
        # interthread communication flags

        self.tcm_locktemp_flag = False
        self.tcm_disconnection_flag = False
        self.tcm_save_flag = False

        self.setpoint_disconnection_flag = False

        self.knob_uploading_flag = False

        self.destroying_flag = False

        # other flags

        self.developer = False

        # other initializations

        self.mim = None
        self.frequency_control_periodic_next = 1

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
        
        self.fpga_frame = ttk.LabelFrame(self.root, text = "FPGA", width = 280, height = 220, relief = tk.GROOVE)
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
        
        self.manual_offset_label = ttk.Label(self.fpga_frame, text = "Manual offset:")
        self.manual_offset_label.place(x = 20, y = 102, anchor = tk.NW)

        self.manual_offset_format = custom_widgets.QuantityFormat((3, 3, 3), {"m": 1e-3}, "V")
        self.manual_offset_entry = custom_widgets.QuantityEntry(self.fpga_frame, self.manual_offset_format, self.manual_offset_report, width = 10, font = ("Arial", 12))
        self.manual_offset_entry.place(x = 20, y = 122, anchor = tk.NW)

        self.fpga_control_panel_button = ttk.Button(self.fpga_frame, text = "Control panel", command = self.fpga_control_panel_button_onclick, width = 32)
        self.fpga_control_panel_button.place(x = 20, y = 146, anchor = tk.NW)

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
        self.logger.info("Closing main window.")
        self.destroying_flag = True
        if self.fpga_control_panel_state == self.FPGA_CONTROL_PANEL_STATE_ON:
            self.fpga_control_panel_onclose()
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
            "fpga_state": self.fpga_state,
            "tcm_state": self.tcm_state,
            "soliton_state": self.soliton_state,
            "locktemp_state": self.locktemp_state,
            "setpoint_state": self.setpoint_state,
            "sweeping_state": self.sweeping_state,
            "powerlock_state": self.powerlock_state,
            "knob_panel_state": self.knob_panel_state,
            "fpga_control_panel_state": self.fpga_control_panel_state,
            "LO_state": self.LO_state,
            "fast_PID_state": self.fast_PID_state,
            "slow_PID_state": self.slow_PID_state,
            "auto_match_state": self.auto_match_state
        }
        while(True):
            time.sleep(0.03)
            if self.destroying_flag:
                self.logger.info("Stopping update thread.")
                return
            current = {
                "fpga_state": self.fpga_state,
                "tcm_state": self.tcm_state,
                "soliton_state": self.soliton_state,
                "locktemp_state": self.locktemp_state,
                "setpoint_state": self.setpoint_state,
                "sweeping_state": self.sweeping_state,
                "powerlock_state": self.powerlock_state,
                "knob_panel_state": self.knob_panel_state,
                "fpga_control_panel_state": self.fpga_control_panel_state,
                "LO_state": self.LO_state,
                "fast_PID_state": self.fast_PID_state,
                "slow_PID_state": self.slow_PID_state,
                "auto_match_state": self.auto_match_state
            }
            changed = False
            for state in current:
                if current[state] != last[state]:
                    self.logger.info("State change detected in %s: %d -> %d"%(state, last[state], current[state]))
                    changed = True
                    last[state] = current[state]
            if changed:
                self.update()
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
                self.manual_offset_entry["state"] = tk.DISABLED
            case self.FPGA_STATE_STANDBY:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_STANDBY"
                self.status_fpga_label["text"] = "FPGA status: STANDBY"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.DISABLED
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.NORMAL
                self.fpga_initialization_button["state"] = tk.NORMAL
                self.manual_offset_entry["state"] = tk.NORMAL
            case self.FPGA_STATE_BUSY:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_BUSY"
                self.status_fpga_label["text"] = "FPGA status: BUSY"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.DISABLED
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.NORMAL
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.manual_offset_entry["state"] = tk.NORMAL
            case self.FPGA_STATE_UNKNOWN:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_UNKNOWN"
                self.status_fpga_label["text"] = "FPGA status: UNKNOWN"
                self.fpga_connection_button["text"] = "Reconnect"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.NORMAL
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.manual_offset_entry["state"] = tk.DISABLED
            case self.FPGA_STATE_CONNECTING:
                if self.developer:
                    self.developer_state_fpga_label["text"] = "fpga_state = FPGA_STATE_CONNECTING"
                self.status_fpga_label["text"] = "FPGA_status: CONNECTING"
                self.fpga_connection_button["text"] = "Submit"
                self.fpga_connection_entry["state"] = tk.NORMAL
                self.fpga_connection_button["state"] = tk.DISABLED
                self.fpga_disconnection_button["state"] = tk.DISABLED
                self.fpga_initialization_button["state"] = tk.DISABLED
                self.manual_offset_entry["state"] = tk.DISABLED
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
                    self.developer_state_setpoint_label["text"] = "setpoint_state = SETPOINT_STATE_OFF"
            case self.SETPOINT_STATE_ON:
                if self.developer:
                    self.developer_state_setpoint_label["text"] = "setpoint_state = SETPOINT_STATE_ON"
        match self.sweeping_state:
            case self.SWEEPING_STATE_OFF:
                if self.developer:
                    self.developer_state_sweeping_label["text"] = "sweeping_state = SWEEPING_STATE_OFF"
            case self.SWEEPING_STATE_ON:
                if self.developer:
                    self.developer_state_sweeping_label["text"] = "sweeping_state = SWEEPING_STATE_ON"
        match self.powerlock_state:
            case self.POWERLOCK_STATE_OFF:
                if self.developer:
                    self.developer_state_powerlock_label["text"] = "powerlock_state = POWERLOCK_STATE_OFF"
            case self.POWERLOCK_STATE_ON:
                if self.developer:
                    self.developer_state_powerlock_label["text"] = "powerlock_state = POWERLOCK_STATE_ON"
        match self.knob_panel_state:
            case self.KNOB_PANEL_STATE_OFF:
                if self.developer:
                    self.developer_state_knob_panel_label["text"] = "knob_panel_state = KNOB_PANEL_STATE_OFF"
            case self.KNOB_PANEL_STATE_ON:
                if self.developer:
                    self.developer_state_knob_panel_label["text"] = "knob_panel_state = KNOB_PANEL_STATE_ON"
        match self.fpga_control_panel_state:
            case self.FPGA_CONTROL_PANEL_STATE_OFF:
                if self.developer:
                    self.developer_state_fpga_control_panel_label["text"] = "fpga_control_panel_state = FPGA_CONTROL_PANEL_STATE_OFF"
            case self.FPGA_CONTROL_PANEL_STATE_ON:
                if self.developer:
                    self.developer_state_fpga_control_panel_label["text"] = "fpga_control_panel_state = FPGA_CONTROL_PANEL_STATE_ON"
        match self.LO_state:
            case self.LO_STATE_OFF:
                if self.developer:
                    self.developer_state_LO_label["text"] = "LO_state = LO_STATE_OFF"
            case self.LO_STATE_ON:
                if self.developer:
                    self.developer_state_LO_label["text"] = "LO_state = LO_STATE_ON"
        match self.fast_PID_state:
            case self.FAST_PID_STATE_OFF:
                if self.developer:
                    self.developer_state_fast_PID_label["text"] = "fast_PID_state = FAST_PID_STATE_OFF"
            case self.FAST_PID_STATE_ON:
                if self.developer:
                    self.developer_state_fast_PID_label["text"] = "fast_PID_state = FAST_PID_STATE_ON"
        match self.slow_PID_state:
            case self.SLOW_PID_STATE_OFF:
                if self.developer:
                    self.developer_state_slow_PID_label["text"] = "slow_PID_state = SLOW_PID_STATE_OFF"
            case self.SLOW_PID_STATE_ON:
                if self.developer:
                    self.developer_state_slow_PID_label["text"] = "slow_PID_state = SLOW_PID_STATE_ON"
        match self.auto_match_state:
            case self.AUTO_MATCH_STATE_OFF:
                if self.developer:
                    self.developer_state_auto_match_label["text"] = "auto_match_state = AUTO_MATCH_STATE_OFF"
            case self.AUTO_MATCH_STATE_ON:
                if self.developer:
                    self.developer_state_auto_match_label["text"] = "auto_match_state = AUTO_MATCH_STATE_ON"
        
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
        match self.fpga_control_panel_state:
            case self.FPGA_CONTROL_PANEL_STATE_OFF:
                self.fpga_control_panel_button["state"] = tk.NORMAL
            case self.FPGA_CONTROL_PANEL_STATE_ON:
                self.fpga_control_panel_button["state"] = tk.DISABLED
        # fpga control panel widgets
        if self.fpga_control_panel_state == self.FPGA_CONTROL_PANEL_STATE_ON:
            match self.fpga_state:
                case self.FPGA_STATE_OFFLINE:
                    self.frequency_bias_entry["state"] = tk.DISABLED
                case self.FPGA_STATE_STANDBY:
                    self.frequency_bias_entry["state"] = tk.NORMAL
                case self.FPGA_STATE_BUSY:
                    self.frequency_bias_entry["state"] = tk.NORMAL
                case self.FPGA_STATE_UNKNOWN:
                    self.frequency_bias_entry["state"] = tk.DISABLED
                case self.FPGA_STATE_CONNECTING:
                    self.frequency_bias_entry["state"] = tk.DISABLED
            match (self.fpga_state, self.LO_state):
                case (self.FPGA_STATE_STANDBY, self.LO_STATE_OFF) | (self.FPGA_STATE_BUSY, self.LO_STATE_OFF):
                    self.LO_button["state"] = tk.NORMAL
                    self.LO_button["relief"] = tk.RAISED
                case (self.FPGA_STATE_STANDBY, self.LO_STATE_ON) | (self.FPGA_STATE_BUSY, self.LO_STATE_ON):
                    self.LO_button["state"] = tk.NORMAL
                    self.LO_button["relief"] = tk.SUNKEN
                case _:
                    self.LO_button["state"] = tk.DISABLED
                    self.LO_button["relief"] = tk.RAISED
            match (self.fpga_state, self.soliton_state, self.LO_state, self.fast_PID_state):
                case (self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON, self.LO_STATE_ON, self.FAST_PID_STATE_OFF):
                    self.fast_PID_button["state"] = tk.NORMAL
                    self.fast_PID_button["relief"] = tk.RAISED
                case (self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON, self.LO_STATE_ON, self.FAST_PID_STATE_ON):
                    self.fast_PID_button["state"] = tk.NORMAL
                    self.fast_PID_button["relief"] = tk.SUNKEN
                case _:
                    self.fast_PID_button["state"] = tk.DISABLED
                    self.fast_PID_button["relief"] = tk.RAISED
            match (self.fpga_state, self.soliton_state, self.LO_state, self.slow_PID_state):
                case (self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON, self.LO_STATE_ON, self.SLOW_PID_STATE_OFF):
                    self.slow_PID_button["state"] = tk.NORMAL
                    self.slow_PID_button["relief"] = tk.RAISED
                case (self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON, self.LO_STATE_ON, self.SLOW_PID_STATE_ON):
                    self.slow_PID_button["state"] = tk.NORMAL
                    self.slow_PID_button["relief"] = tk.SUNKEN
                case _:
                    self.slow_PID_button["state"] = tk.DISABLED
                    self.slow_PID_button["relief"] = tk.RAISED
            match (self.fpga_state, self.LO_state):
                case (self.FPGA_STATE_STANDBY, self.LO_STATE_ON) | (self.FPGA_STATE_BUSY, self.LO_STATE_ON):
                    self.waveform_control_panel.state = "normal"
                case _:
                    self.waveform_control_panel.state = "disabled"
            match (self.fpga_state, self.soliton_state, self.auto_match_state):
                case self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON, self.AUTO_MATCH_STATE_OFF:
                    self.enable_auto_match_button["state"] = tk.NORMAL
                    self.enable_auto_match_button["relief"] = tk.RAISED
                case self.FPGA_STATE_BUSY, self.SOLITON_STATE_ON, self.AUTO_MATCH_STATE_ON:
                    self.enable_auto_match_button["state"] = tk.NORMAL
                    self.enable_auto_match_button["relief"] = tk.SUNKEN
                case _:
                    self.enable_auto_match_button["state"] = tk.DISABLED
                    self.enable_auto_match_button["relief"] = tk.RAISED
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

            self.developer_state_frame = ttk.LabelFrame(self.developer_mode, text = "Internal states", width = 720, height = 245, relief = tk.GROOVE)
            self.developer_state_frame.place(x = 10, y = 0, anchor = tk.NW)

            self.developer_state_fpga_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_fpga_label.place(x = 10, y = 0, anchor = tk.NW)

            self.developer_state_tcm_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_tcm_label.place(x = 10, y = 20, anchor = tk.NW)

            self.developer_state_soliton_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_soliton_label.place(x = 10, y = 40, anchor = tk.NW)

            self.developer_state_locktemp_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_locktemp_label.place(x = 10, y = 60, anchor = tk.NW)

            self.developer_state_setpoint_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_setpoint_label.place(x = 10, y = 80, anchor = tk.NW)

            self.developer_state_sweeping_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_sweeping_label.place(x = 10, y = 100, anchor = tk.NW)

            self.developer_state_powerlock_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_powerlock_label.place(x = 10, y = 120, anchor = tk.NW)

            self.developer_state_knob_panel_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_knob_panel_label.place(x = 10, y = 140, anchor = tk.NW)

            self.developer_state_fpga_control_panel_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_fpga_control_panel_label.place(x = 10, y = 160, anchor = tk.NW)

            self.developer_state_LO_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_LO_label.place(x = 10, y = 180, anchor = tk.NW)

            self.developer_state_fast_PID_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_fast_PID_label.place(x = 10, y = 200, anchor = tk.NW)

            self.developer_state_slow_PID_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_slow_PID_label.place(x = 400, y = 0, anchor = tk.NW)

            self.developer_state_auto_match_label = ttk.Label(self.developer_state_frame, text = "")
            self.developer_state_auto_match_label.place(x = 400, y = 20, anchor = tk.NW)

            self.developer_monitorC_box = ttk.Combobox(self.developer_mode, values = [
                "phase", "freq", "I", "Q", "error", "ref", "ref shift", "auto match freq", "TestA", "TestB", "TestC", "TestD", "LO freq", "LO freq diff"
            ])
            self.developer_monitorC_box.set("phase")
            self.developer_monitorC_box.place(x = 750, y = 10, anchor = tk.NW)

            self.developer_monitorC_button = ttk.Button(self.developer_mode, text = "upload to MonitorC", command = self.developer_monitorC_button_onclick, width = 20)
            self.developer_monitorC_button.place(x = 750, y = 35, anchor = tk.NW)
            
            self.developer_monitorD_box = ttk.Combobox(self.developer_mode, values = [
                "phase", "freq", "I", "Q", "error", "ref", "ref shift", "auto match freq", "TestA", "TestB", "TestC", "TestD", "LO freq", "LO freq diff"
            ])
            self.developer_monitorD_box.set("freq")
            self.developer_monitorD_box.place(x = 750, y = 65, anchor = tk.NW)

            self.developer_monitorD_button = ttk.Button(self.developer_mode, text = "upload to MonitorD", command = self.developer_monitorD_button_onclick, width = 20)
            self.developer_monitorD_button.place(x = 750, y = 90, anchor = tk.NW)
            
            # assuming that fpga is already initialized
            instruments = [i.get("purpose") for i in self.mim.config.findall("./instruments/instrument") if i.get("type") == "CloudCompile"]
            self.developer_instrument_box = ttk.Combobox(self.developer_mode, values = [""] + instruments)
            self.developer_instrument_box.current(0)
            self.developer_instrument_box.place(x = 750, y = 120, anchor = tk.NW)
            self.developer_instrument_box.bind("<<ComboboxSelected>>", lambda event:self.developer_parameter_setting("replace instrument"))

            self.developer_parameter_name_box = ttk.Combobox(self.developer_mode, values = [""])
            self.developer_parameter_name_box.current(0)
            self.developer_parameter_name_box.place(x = 750, y = 150, anchor = tk.NW)
            self.developer_parameter_name_box.bind("<<ComboboxSelected>>", lambda event:self.developer_parameter_setting("replace parameter"))

            self.developer_parameter_value_format = custom_widgets.QuantityFormat((10, 0, 0), {}, "")
            self.developer_parameter_value_entry = custom_widgets.QuantityEntry(self.developer_mode, formater = self.developer_parameter_value_format, report = lambda:self.developer_parameter_setting("upload parameter"), width = 10, font = ("Arial", 12))
            self.developer_parameter_value_entry.place(x = 750, y = 180, anchor = tk.NW)

            self.update()

            self.logger.debug("Developer panel generated.")
        else:
            self.logger.debug("Developer password incorrect.")
            self.information["text"] = "Wrong password."
        return
    
    def developer_monitorC_button_onclick(self) -> None:
        self.logger.info("Uploading selected channel to MonitorC.")
        self.mim.get_fb().set_parameter("monitorC", self.developer_monitorC_box["values"].index(self.developer_monitorC_box.get()))
        self.mim.get_fb().upload_control()
        return
    
    def developer_monitorD_button_onclick(self) -> None:
        self.logger.info("Uploading selected channel to MonitorD.")
        self.mim.get_fb().set_parameter("monitorD", self.developer_monitorC_box["values"].index(self.developer_monitorC_box.get()))
        self.mim.get_fb().upload_control()
        return

    def developer_parameter_setting(self, action: str) -> None:
        match action:
            case "replace instrument":
                if self.developer_instrument_box.get() == "":
                    self.developer_parameter_name_box["values"] = [""]
                else:
                    instrument = self.mim.config.find("./instruments/instrument[@purpose='%s']"%self.developer_instrument_box.get())
                    self.developer_parameter_name_box["values"] = [""] + [i.get("name") for i in instrument.findall("./parameters/parameter")]
                self.developer_parameter_name_box.current(0)
                self.developer_parameter_value_entry.set("")
                self.developer_parameter_value_entry.store()
            case "replace parameter":
                if self.developer_parameter_name_box.get() == "":
                    self.developer_parameter_value_entry.set("")
                else:
                    # using new ports that would be updated with branch issues/#4
                    pass
                self.developer_parameter_value_entry.store()


    def knob_panel_button_onclick(self) -> None:
        self.logger.debug("Knob panel button clicked.")
        self.information["text"] = "Deprecated."
        '''
        self.knob_panel_thread = threading.Thread(target = self.knob_panel_thread_function, args = (), daemon = True)
        self.knob_panel_thread.start()
        '''
        return

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
            self.manual_offset_knob.knob.set_value(self.mim.get_tk().get_parameter("manual_offset"))
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
            self.mim.get_tk().set_parameter("manual_offset", self.manual_offset_knob.knob.get_value())
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
        self.mim.get_tk().upload_control()
        self.knob_uploading_flag = False
        self.logger.debug("Knob parameter uploaded.")
        return

    def command_soliton_button_onclick(self) -> None:
        self.logger.info("Soliton button clicked.")
        if self.mim.get_tk() is None:
            self.logger.debug("turnkey not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
        match self.soliton_state:
            case self.SOLITON_STATE_ON:
                try:
                    self.logger.debug("Stopping soliton generation.")
                    self.mim.stop()
                    self.mim.get_fb().fast_PID_off()
                    self.mim.get_fb().slow_PID_off()
                    self.mim.get_fb().auto_match_off()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Soliton generation Stopped.")
                    self.information["text"] = "Soliton generation interrupted."
                    self.fpga_state = self.FPGA_STATE_STANDBY
                    self.soliton_state = self.SOLITON_STATE_OFF
                    self.fast_PID_state = self.FAST_PID_STATE_OFF
                    self.slow_PID_state = self.SLOW_PID_STATE_OFF
                    self.auto_match_state = self.AUTO_MATCH_STATE_OFF
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
                    if self.fpga_control_panel_state == self.FPGA_CONTROL_PANEL_STATE_ON:
                        self.manual_offset_entry.set("0.000V")
                        self.manual_offset_entry.store()
                        self.manual_offset_entry.call()
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
        # check if modules exist
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
            self.logger.debug("Waveforms collected.")
            characteristics = list(map(characteristic, waveforms))
            self.logger.debug("Characteristics calculated: %s"%characteristics)
            print(characteristics)
            start = 0
            for i in range(0, N - 1):
                if start == 0 and characteristics[i] > 0.150:
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
        if self.mim.get_tk() is None:
            self.logger.debug("turnkey not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
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
                    if self.fpga_control_panel_state == self.FPGA_CONTROL_PANEL_STATE_ON:
                        self.manual_offset_entry.set("0.000V")
                        self.manual_offset_entry.store()
                        self.manual_offset_entry.call()
        return
    
    def command_powerlock_button_onclick(self) -> None:
        self.logger.info("Powerlock button clicked.")
        if self.mim.get_tk() is None:
            self.logger.debug("turnkey not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
        match self.powerlock_state:
            case self.POWERLOCK_STATE_ON:
                try:
                    self.logger.debug("Stopping power lock.")
                    self.mim.get_tk().power_lock_OFF()
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
                    self.mim.get_tk().power_lock_ON()
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
            self.mim = fpga.MIM(self.ip, config_id = "1", logger = self.logger)
            self.powerlock_state = self.POWERLOCK_STATE_OFF
            self.LO_state = self.LO_STATE_OFF
            self.fast_PID_state = self.FAST_PID_STATE_OFF
            self.slow_PID_state = self.SLOW_PID_STATE_OFF
            self.auto_match_state = self.AUTO_MATCH_STATE_OFF
            if self.mim.get_tk() is None:
                self.logger.debug("turnkey not found. Skipping parameter synchronizations.")
            else:
                if self.mim.get_tk().get_parameter("PID_lock") == 0:
                    self.powerlock_state = self.POWERLOCK_STATE_ON
                self.manual_offset_entry.set(self.manual_offset_control2quantity(self.mim.get_tk().get_parameter("manual_offset")))
                self.manual_offset_entry.store()
            if self.mim.get_fb() is None:
                self.logger.debug("feedback not found. Skipping parameter synchronizations.")
            else:
                if self.fpga_control_panel_state == self.FPGA_CONTROL_PANEL_STATE_ON:
                    self.frequency_bias_entry.set(self.frequency_bias_control2quantity(self.mim.get_fb().get_parameter("frequency_bias")))
                    self.frequency_bias_entry.store()
                    if self.mim.get_fb().get_parameter("LO_Reset") == 0:
                        self.LO_state = self.LO_STATE_ON
                    if self.mim.get_fb().get_parameter("fast_PID_Reset") == 0:
                        self.fast_PID_state = self.FAST_PID_STATE_ON
                    if self.mim.get_fb().get_parameter("slow_PID_Reset") == 0:
                        self.slow_PID_state = self.SLOW_PID_STATE_ON
                    if self.mim.get_fb().get_parameter("enable_auto_match") == 0:
                        self.auto_match_state = self.AUTO_MATCH_STATE_ON
        except Exception as e:
            self.logger.error("Failed to connect to FPGA: %s"%e.__repr__())
            self.information["text"] = "Failed to connect to FPGA: %s"%e.__repr__()
            self.fpga_state = self.FPGA_STATE_OFFLINE
        else:
            self.logger.debug("FPGA connected.")
            self.information["text"] = "FPGA online."
            self.fpga_state = self.FPGA_STATE_STANDBY
            self.soliton_state = self.SOLITON_STATE_OFF
            self.sweeping_state = self.SWEEPING_STATE_OFF
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
            if self.mim.get_tk().get_parameter("PID_lock") == 0:
                self.powerlock_state = self.POWERLOCK_STATE_ON
            else:
                self.powerlock_state = self.POWERLOCK_STATE_OFF
            self.manual_offset_entry.set(self.manual_offset_control2quantity(self.mim.get_tk().get_parameter("manual_offset")))
            self.manual_offset_entry.store()
            if self.fpga_control_panel_state == self.FPGA_CONTROL_PANEL_STATE_ON:
                self.frequency_bias_entry.set(self.frequency_bias_control2quantity(self.mim.get_fb().get_parameter("frequency_bias")))
                self.frequency_bias_entry.store()
                if self.mim.get_fb().get_parameter("LO_Reset") == 0:
                    self.LO_state = self.LO_STATE_ON
                if self.mim.get_fb().get_parameter("fast_PID_Reset") == 0:
                    self.fast_PID_state = self.FAST_PID_STATE_ON
                if self.mim.get_fb().get_parameter("slow_PID_Reset") == 0:
                    self.slow_PID_state = self.SLOW_PID_STATE_ON
                if self.mim.get_fb().get_parameter("enable_auto_match") == 0:
                    self.auto_match_state = self.AUTO_MATCH_STATE_ON
                self.waveform_control_panel.uploaded = False
                self.waveform_control_panel.periodically_running = False
        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Failed to initialize: %s"%e.__repr__()
        else:
            self.logger.debug("FPGA initialized.")
            self.information["text"] = "FPGA initialized."
        finally:
            self.fpga_state = self.FPGA_STATE_STANDBY
        return
    
    def manual_offset_report(self, value) -> None:
        self.logger.debug("Setting manual offset to %s."%self.manual_offset_entry.get_text())
        if self.mim.get_tk() is None:
            self.logger.debug("turnkey not found. Aborting setting manual offset.")
            self.information["text"] = "Module not found. Did you forget to initialize?"
            return
        self.mim.get_tk().set_parameter("manual_offset", self.manual_offset_value2control(value))
        result = self.mim.get_tk().upload_data()
        match result:
            case "queued":
                self.logger.debug("Parameters queued.")
            case "rejected":
                self.logger.debug("Parameters rejected.")
        return
    
    def manual_offset_control2quantity(self, control: int) -> str:
        if control < 32767:
            return "%.3fV"%(control * 0.33417 * 1e-3)
        else:
            return "%.3fV"%((control - 65536) * 0.33417 * 1e-3)

    def manual_offset_value2control(self, value: float) -> int:
        return int(np.round(value / 0.33417 * 1e3))

    def fpga_control_panel_button_onclick(self) -> None:
        self.logger.info("FPGA control panel button clicked.")
        self.information["text"] = "FPGA control panel."
        try:
            self.fpga_control_panel_state = self.FPGA_CONTROL_PANEL_STATE_ON
            self.fpga_control_panel = tk.Toplevel()
            self.fpga_control_panel.title("FPGA control panel")
            self.fpga_control_panel.geometry("1140x440")
            self.fpga_control_panel.protocol("WM_DELETE_WINDOW", self.fpga_control_panel_onclose)

            # entries
            self.frequency_bias_label = ttk.Label(self.fpga_control_panel, text = "Frequency bias:")
            self.frequency_bias_label.place(x = 10, y = 10, anchor = tk.NW)
            self.frequency_bias_format = custom_widgets.QuantityFormat((6, 6, 0), {"M": 1e6, "k": 1e3}, "Hz")
            self.frequency_bias_entry = custom_widgets.QuantityEntry(self.fpga_control_panel, self.frequency_bias_format, self.frequency_bias_report, width = 10, font = ("Arial", 12))
            self.frequency_bias_entry.place(x = 10, y = 30, anchor = tk.NW)
            
            # buttons
            self.LO_button = tk.Button(self.fpga_control_panel, text = "Local oscillator", command = self.LO_button_onclick, width = 32)
            self.LO_button.place(x = 10, y = 54, anchor = tk.NW)

            self.fast_PID_button = tk.Button(self.fpga_control_panel, text = "Fast PID", command = self.fast_PID_button_onclick, width = 32)
            self.fast_PID_button.place(x = 10, y = 84, anchor = tk.NW)

            self.slow_PID_button = tk.Button(self.fpga_control_panel, text = "Slow PID", command = self.slow_PID_button_onclick, width = 32)
            self.slow_PID_button.place(x = 10, y = 114, anchor = tk.NW)

            self.enable_auto_match_button = tk.Button(self.fpga_control_panel, text = "Use auto match", command = self.enable_auto_match_button_onclick, width = 32)
            self.enable_auto_match_button.place(x = 10, y = 144, anchor = tk.NW)

            # panel
            self.waveform_control_panel = custom_widgets.WaveformControl(self.fpga_control_panel, self.upload_waveform, self.initiate_frequency_control, self.terminate_frequency_control)
            self.waveform_control_panel.place(x = 255, y = 10, anchor = tk.NW)

            self.LO_state = self.LO_STATE_OFF
            self.fast_PID_state = self.FAST_PID_STATE_OFF
            self.slow_PID_state = self.SLOW_PID_STATE_OFF
            self.auto_match_state = self.AUTO_MATCH_STATE_OFF
            if self.mim is None or self.mim.get_fb() is None:
                self.logger.debug("mim/feedback not found. Skipping setting default values.")
            else:
                self.frequency_bias_entry.set(self.frequency_bias_control2quantity(self.mim.get_fb().get_parameter("frequency_bias")))
                self.frequency_bias_entry.store()
                if self.mim.get_fb().get_parameter("LO_Reset") == 0:
                    self.LO_state = self.LO_STATE_ON
                if self.mim.get_fb().get_parameter("fast_PID_Reset") == 0:
                    self.fast_PID_state = self.FAST_PID_STATE_ON
                if self.mim.get_fb().get_parameter("slow_PID_Reset") == 0:
                    self.slow_PID_state = self.SLOW_PID_STATE_ON
                if self.mim.get_fb().get_parameter("enable_auto_match") == 0:
                    self.auto_match_state = self.AUTO_MATCH_STATE_ON

        except Exception as e:
            self.logger.error("%s"%e.__repr__())
            self.information["text"] = "Error encountered when generating FPGA control panel: %s"%e.__repr__()
        else:
            self.logger.debug("FPGA control panel generated.")
            self.fpga_control_panel.mainloop()
        return
    
    def fpga_control_panel_onclose(self) -> None:
        self.logger.debug("FPGA control panel closed.")
        self.fpga_control_panel_state = self.FPGA_CONTROL_PANEL_STATE_OFF
        self.waveform_control_panel.destroy()
        self.fpga_control_panel.after(10, self.fpga_control_panel.destroy)
        return

    def frequency_bias_report(self, value) -> None:
        self.logger.debug("Setting frequency bias to %s."%self.frequency_bias_entry.get_text())
        if self.mim.get_fb() is None:
            self.logger.debug("feedback not found. Aborting setting frequency bias.")
            self.information["text"] = "Module not found. Did you forget to initialize?"
            return
        self.mim.get_fb().set_parameter("frequency_bias", self.frequency_bias_value2control(value))
        result = self.mim.get_fb().upload_data()
        match result:
            case "queued":
                self.logger.debug("Parameters queued.")
            case "rejected":
                self.logger.debug("Parameters rejected.")
        return
    
    def frequency_bias_control2quantity(self, control: int) -> str:
        return "%.3fMHz"%(control * 298.023 * 1e-6)

    def frequency_bias_value2control(self, value: float) -> int:
        return int(np.round(value / 298.023))

    def LO_button_onclick(self) -> None:
        self.logger.info("Local oscillator button clicked.")
        if self.mim.get_fb() is None:
            self.logger.debug("feedback not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
        match self.LO_state:
            case self.LO_STATE_ON:
                try:
                    self.logger.debug("Stopping local oscillator.")
                    self.mim.get_fb().LO_off()
                    self.mim.get_fb().fast_PID_off()
                    self.mim.get_fb().slow_PID_off()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Local oscillator stopped.")
                    self.information["text"] = "Local oscillator turned off."
                    self.LO_state = self.LO_STATE_OFF
                    self.fast_PID_state = self.FAST_PID_STATE_OFF
                    self.slow_PID_state = self.SLOW_PID_STATE_OFF
            case self.LO_STATE_OFF:
                try:
                    self.logger.debug("Starting local oscillator.")
                    self.mim.get_fb().LO_on()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Local oscillator started.")
                    self.information["text"] = "Local oscillator turned on."
                    self.LO_state = self.LO_STATE_ON
                    self.waveform_control_panel.uploaded = False
        return
    
    def fast_PID_button_onclick(self) -> None:
        self.logger.info("Fast PID button clicked.")
        if self.mim.get_fb() is None:
            self.logger.debug("feedback not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
        match self.fast_PID_state:
            case self.FAST_PID_STATE_ON:
                try:
                    self.logger.debug("Stopping fast PID.")
                    self.mim.get_fb().fast_PID_off()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Fast PID stopped.")
                    self.information["text"] = "Fast PID turned off."
                    self.fast_PID_state = self.FAST_PID_STATE_OFF
            case self.FAST_PID_STATE_OFF:
                try:
                    self.logger.debug("Starting fast PID.")
                    self.mim.get_fb().fast_PID_on()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Fast PID started.")
                    self.information["text"] = "Fast PID turned on."
                    self.fast_PID_state = self.FAST_PID_STATE_ON
        return
    
    def slow_PID_button_onclick(self) -> None:
        self.logger.info("Slow PID button clicked.")
        if self.mim.get_fb() is None:
            self.logger.debug("feedback not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
        match self.slow_PID_state:
            case self.SLOW_PID_STATE_ON:
                try:
                    self.logger.debug("Stopping slow PID.")
                    self.mim.get_fb().slow_PID_off()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Slow PID stopped.")
                    self.information["text"] = "Slow PID turned off."
                    self.slow_PID_state = self.SLOW_PID_STATE_OFF
            case self.SLOW_PID_STATE_OFF:
                try:
                    self.logger.debug("Starting slow PID.")
                    self.mim.get_fb().slow_PID_on()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Slow PID started.")
                    self.information["text"] = "Slow PID turned on."
                    self.slow_PID_state = self.SLOW_PID_STATE_ON
        return

    def enable_auto_match_button_onclick(self) -> None:
        self.logger.info("Enable auto match button clicked.")
        if self.mim.get_fb() is None:
            self.logger.debug("feedback not found.")
            self.information["text"] = "Module not found. Try initializing first."
            return
        match self.auto_match_state:
            case self.AUTO_MATCH_STATE_ON:
                try:
                    self.logger.debug("Disabling auto match.")
                    self.mim.get_fb().auto_match_off()
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Auto match disabled.")
                    self.information["text"] = "Auto match disabled."
                    self.auto_match_state = self.AUTO_MATCH_STATE_OFF
            case self.AUTO_MATCH_STATE_OFF:
                try:
                    self.logger.debug("Enabling auto match.")
                    self.mim.get_fb().auto_match_on()
                    self.mim.get_fb().launch_auto_match() # may need to decouple this later
                except Exception as e:
                    self.logger.error("%s"%e.__repr__())
                    self.information["text"] = "Error encountered when communicating with FPGA, initialization recommended: %s"%e.__repr__()
                else:
                    self.logger.debug("Auto match enabled.")
                    self.information["text"] = "Auto match enabled."
                    self.auto_match_state = self.AUTO_MATCH_STATE_ON
        return

    def upload_waveform(self, waveform: list[list[float]], periodic: bool, prolong: bool) -> None:
        # waveform [[time(s), frequency(Hz)], ...]
        # bit rate: 3.2ns/bit & 298.023Hz/bit
        converted = [{
                        "sign": 1 if waveform[i][1] < 0 else 0,
                        "x": int(np.round(waveform[i][0] * 312.5e6)),
                        "y": int(np.round(np.abs(waveform[i][1] / 298.023))),
                        "slope": int(np.floor(np.round(np.abs(waveform[i][1] / 298.023)) / np.round(waveform[i][0] * 312.5e6)))
                    } for i in range(len(waveform))]
        self.logger.info("Uploading waveform : %s."%converted)
        self.mim.get_fb().waveform = converted
        self.frequency_control_periodic_next = 0 if periodic else 1
        self.mim.get_fb().set_parameter("prolong", 0 if prolong else 1)
        self.mim.get_fb().upload_waveform()
        self.logger.debug("Waveform uploaded.")
        return

    def initiate_frequency_control(self) -> None:
        self.logger.info("Initiating frequency control.")
        self.mim.get_fb().set_parameter("periodic", self.frequency_control_periodic_next)
        self.mim.get_fb().launch_frequency_control()
        self.logger.debug("Frequency control initiated.")
        return
    
    def terminate_frequency_control(self) -> None:
        self.logger.info("Terminating frequency control.")
        self.mim.get_fb().set_parameter("periodic", 1)
        self.mim.get_fb().upload_control()
        self.logger.debug("Frequency control terminated.")
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
        self.last_tcm_locktemp_flag = self.tcm_locktemp_flag
        while(True):
            time.sleep(0.1)
            try:
                if self.tcm_disconnection_flag:
                    self.logger.debug("TCM temperature thread interrupted due to disconnection.")
                    return
                if self.tcm_locktemp_flag and not self.last_tcm_locktemp_flag:
                    self.logger.debug("Locking temperature.")
                    self.tcm.set_on()
                    self.logger.debug("Temperature locked.")
                elif not self.tcm_locktemp_flag and self.last_tcm_locktemp_flag:
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

if __name__ == "__main__":

    main = Interface()
    main.logger.info("Main panel initialized.")
    main.loop()