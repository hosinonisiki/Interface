import moku.instruments as instruments
import numpy as np
import time
import typing
import requests
import json

# for testing
import matplotlib.pyplot as plt

def set_bit(integer: int, index: int, bit: str) -> int:
    binary = bin(integer)[2:].zfill(32)
    return eval("0b" + binary[:31 - index] + bit + binary[32 - index:])

def set_hex(integer: int, index: int, hexa: str) -> int:
    hexadecimal = hex(integer)[2:].zfill(8)
    return eval("0x" + hexadecimal[:7 - index] + hexa + hexadecimal[8 - index:])

def bit_length(integer: int) -> int:
    if integer > 0:
        return int(np.log2(integer) + 1)
    elif integer == 0 or integer == -1:
        return 1
    else:
        return int(np.log2(-1 - integer) + 2)

def convert_bits(integer: int, length: int) -> str:
    if bit_length(integer) > length:
        raise Exception("Value is too large to fit into the bit length!")
    if integer >= 0:
        return bin(integer)[2:].zfill(length)
    else:
        return bin(integer + 2 ** length)[2:].zfill(length)
    

class MCC():
    def __init__(self, mcc: object, slot: int, controls: dict[int, int] = {}):
        self.mcc = mcc
        self.slot = slot
        self.download_control()
        self.set_control(controls) # initialize control
        self.upload_control()
    
    # needs an http implementation
    def download_control(self) -> object:
        try:
            self.controls = {index:value for index, value in zip(range(16), [self.mcc.get_control(i)[i] for i in range(16)])}
        except Exception as e:
            raise Exception("Connection error: %s"%e.__repr__())
        return self
        
    def upload_control(self, mode: str = "default", url: str = "http://localhost:8090/api/v2/registers") -> object:
        if mode == "default":
            try:
                for i in range(15, -1, -1):
                    self.mcc.set_control(i, self.controls[i])
            except Exception as e:
                raise Exception("Connection error: %s"%e.__repr__())
        elif mode == "http":
            post = "[[\"instr" + str(self.slot) + "\", {"
            for i in range(0, 16):
                post = post + "\"" + str(i) + "\":" + str(self.controls[i])
                if i != 15:
                    post = post + ","
            post = post + "}]]"
            try:
                r_json = json.loads(post)
                p_confiure = requests.post(url = url, json = r_json)
            except Exception as e:
                raise Exception("Connection error: %s"%e.__repr__())
        return self
    
    def set_control(self, *arg) -> object:
        if len(arg) == 1:
            self.controls.update(arg[0])
        elif len(arg) == 2:
            self.controls[arg[0]] = arg[1]
        return self
    
    def get_control(self, i: int) -> int:
        return self.controls[i]
    
    def set_bit(self, control: int, index: int, bit: str) -> object:
        self.controls[control] = set_bit(self.get_control(control), index, bit)
        return self
        
    def set_hex(self, control: int, index: int, hexa: str) -> object:
        self.controls[control] = set_hex(self.get_control(control), index, hexa)
        return self

class Turnkey(MCC):
    default_controls = {
        "drop_period": 7324,
        "climb_period": 24028,
        "kick_period": 488,
        "hold_period": 7324,
        "max_voltage": 14927,
        "min_voltage": 5971,
        "step_voltage": 20,
        "drop_amplitude": 14634,
        "climb_amplitude": 15232,
        "kick_amplitude": 598,
        "soliton_threshold_max": 4608,
        "soliton_threshold_min": 1536,
        "attempts": 1,
        "approaches": 64,
        "coarse_target": 1008,
        "fine_target": 96,
        "coarse_period": 4077,
        "fine_period": 20385,
        "stab_target": 2048,
        "stab_period": 2548,
        "floor": 65472,
        "PID_K_P": 65280,
        "PID_K_I": 57088,
        "PID_K_D": 0,
        "mode": 0,
        "sweep_period": 404,
        "PID_lock": 1,
        "input_gain": 16, # 256 indicates 16 time gain while 1 indicates 16 time attenuation
        "output_gain": 32, # 256 indicates 16 time gain while 1 indicates 16 time attenuation
        "manual_offset": 0,
        "Reset": 0
    } # {<name>:<value>}
    mapping = {
        "drop_period": {"index": 1, "high": 31, "low": 16},
        "climb_period": {"index": 1, "high": 15, "low": 0},
        "kick_period": {"index": 2, "high": 31, "low": 16},
        "hold_period": {"index": 2, "high": 15, "low": 0},
        "max_voltage": {"index": 3, "high": 31, "low": 16},
        "min_voltage": {"index": 3, "high": 15, "low": 0},
        "step_voltage": {"index": 4, "high": 31, "low": 16},
        "drop_amplitude": {"index": 4, "high": 15, "low": 0},
        "climb_amplitude": {"index": 5, "high": 31, "low": 16},
        "kick_amplitude": {"index": 5, "high": 15, "low": 0},
        "soliton_threshold_max": {"index": 6, "high": 31, "low": 16},
        "soliton_threshold_min": {"index": 6, "high": 15, "low": 0},
        "attempts": {"index": 7, "high": 31, "low": 24},
        "approaches": {"index": 7, "high": 23, "low": 16},
        "coarse_target": {"index": 7, "high": 15, "low": 0},
        "fine_target": {"index": 8, "high": 31, "low": 16},
        "coarse_period": {"index": 8, "high": 15, "low": 0},
        "fine_period": {"index": 9, "high": 31, "low": 16},
        "stab_target": {"index": 9, "high": 15, "low": 0},
        "stab_period": {"index": 10, "high": 31, "low": 16}, 
        "floor": {"index": 10, "high": 15, "low": 0},
        "PID_K_P": {"index": 11, "high": 31, "low": 0},
        "PID_K_I": {"index": 12, "high": 31, "low": 0},
        "PID_K_D": {"index": 13, "high": 31, "low": 0},
        "mode": {"index": 0, "high": 1, "low": 1},
        "sweep_period": {"index": 14, "high": 31, "low": 16},
        "PID_lock": {"index": 0, "high": 2, "low": 2},
        "input_gain": {"index": 14, "high": 7, "low": 0},
        "output_gain": {"index": 14, "high": 15, "low": 8},
        "manual_offset": {"index": 15, "high": 31, "low": 16},
        "Reset": {"index": 0, "high": 0, "low": 0}
    } # {<name>:{"index":<index>, "high":<high>, "low":<low>}}
        
    def set_default(self) -> object:
        for name in self.mapping:
            self.set_parameter(name, self.default_controls[name])
        self.upload_control()
        return self
        
    def set_parameter(self, name: str, value: int) -> object:
        location = Turnkey.mapping[name]
        bits = convert_bits(value, location["high"] - location["low"] + 1)
        pointer = location["high"]
        for i in bits:
            self.set_bit(location["index"], pointer, i)
            pointer = pointer - 1
        return self
    
    def get_parameter(self, name: str) -> int:
        location = Turnkey.mapping[name]
        bits = bin(self.get_control(location["index"]))[2:].zfill(32)
        return eval("0b" + bits[31 - location["high"]: 32 - location["low"]])
    
    def run(self) -> object:
        self.set_parameter("mode", 0)
        self.set_parameter("Reset", 0)
        self.set_parameter("manual_offset", 0)
        self.upload_control()
        return self
        
    def stop(self) -> object:
        self.set_parameter("Reset", 1)
        self.upload_control()
        return self
    
    def sweep(self) -> object:
        self.set_parameter("mode", 1)
        self.set_parameter("Reset", 0)
        self.set_parameter("manual_offset", 0)
        self.upload_control()
        return self

    def power_lock_ON(self) -> object:
        self.set_parameter("PID_lock", 0)
        self.upload_control()
        return self
    
    def power_lock_OFF(self) -> object:
        self.set_parameter("PID_lock", 1)
        self.upload_control()
        return self

class Feedback(MCC):
    default_controls = {
        "fast_PID_K_P": 4294443008,
        "fast_PID_K_I": 4261412864,
        "fast_PID_K_D": 4294836224,
        "monitorC": 0,
        "monitorD": 1,
        "segments_enabled": 3,
        "set_address": 0,
        "rate": 1, # modified from 8 to 1 due to the new IIR entity with cutoff freqeuncy around 1.5MHz already
        "slow_PID_K_P": 4096,
        "slow_PID_K_I": 4096,
        "slow_PID_K_D": 0,
        "set_x": 31250000,
        "set_y": 3355,
        "set_slope": 0,
        "frequency_bias": 33554,
        "amplitude": 28672,
        "fast_PID_Reset": 1,
        "slow_PID_Reset": 1,
        "LO_Reset": 1,
        "set_sign": 0,
        "initiate": 1,
        "periodic": 1,
        "prolong": 0,
        "lock_mode": 0,
        "slow_input": 1,
        "set": 1,
        "enable_auto_match": 1,
        "initiate_auto_match": 1,
        "frequency_match_threshold": 268,
        "frequency_lock_threshold": 3,
        "frequency_match_K_P": 16384,
        "frequency_match_K_I": 8192, # should match in around 1 ms
        "frequency_match_K_D": 0
    } # {<name>:<value>}
    mapping = {
        "fast_PID_K_P": {"index": 2, "high": 31, "low": 0},
        "fast_PID_K_I": {"index": 3, "high": 31, "low": 0},
        "fast_PID_K_D": {"index": 4, "high": 31, "low": 0},
        "monitorC" : {"index": 1, "high": 15, "low": 14},
        "monitorD" : {"index": 1, "high": 13, "low": 12},
        "segments_enabled": {"index": 1, "high": 11, "low": 8},
        "set_address": {"index": 1, "high": 7, "low": 4},
        "rate": {"index": 1, "high": 3, "low": 0},
        "slow_PID_K_P": {"index": 8, "high": 31, "low": 0},
        "slow_PID_K_I": {"index": 9, "high": 31, "low": 0},
        "slow_PID_K_D": {"index": 10, "high": 31, "low": 0},
        "set_x": {"index": 5, "high": 31, "low": 0},
        "set_y": {"index": 6, "high": 31, "low": 16},
        "set_slope": {"index": 6, "high": 15, "low": 0},
        "frequency_bias": {"index": 7, "high": 31, "low": 16},
        "amplitude": {"index": 7, "high": 15, "low": 0},
        "fast_PID_Reset": {"index": 0, "high": 10, "low": 10},
        "slow_PID_Reset": {"index": 0, "high": 11, "low": 11},
        # control0 0 is empty for now
        "LO_Reset": {"index": 0, "high": 1, "low": 1},
        "set_sign": {"index": 0, "high": 2, "low": 2},
        "initiate": {"index": 0, "high": 3, "low": 3},
        "periodic": {"index": 0, "high": 4, "low": 4},
        "prolong": {"index": 0, "high": 5, "low": 5},
        "lock_mode": {"index": 0, "high": 9, "low": 8},
        "slow_input": {"index": 0, "high": 6, "low": 6},
        "set": {"index": 0, "high": 7, "low": 7},

        "enable_auto_match": {"index": 0, "high": 12, "low": 12},
        "initiate_auto_match": {"index": 0, "high": 13, "low": 13},
        "frequency_match_threshold": {"index": 11, "high": 31, "low": 16},
        "frequency_lock_threshold": {"index": 11, "high": 15, "low": 0},
        "frequency_match_K_P": {"index": 12, "high": 31, "low": 0},
        "frequency_match_K_I": {"index": 13, "high": 31, "low": 0},
        "frequency_match_K_D": {"index": 14, "high": 31, "low": 0}
    } # {<name>:{"index":<index>, "high":<high>, "low":<low>}}
    # open frequency_bias and three resets first
    default_waveform = [
        {"sign": 1, "x": 1562500, "y": 3355, "slope": 0},
        {"sign": 0, "x": 31250000, "y": 0, "slope": 0},
        {"sign": 0, "x": 1562500, "y": 3355, "slope": 0},
        {"sign": 0, "x": 31250000, "y": 0, "slope": 0}
    ]
    def __init__(self, mcc: object, slot: int, controls: dict[int, int] = {}, waveform: list[dict[str, int]] = []):
        super().__init__(mcc, slot, controls)
        if waveform:
            self.waveform = waveform
        else:
            self.waveform = self.default_waveform
        self.upload_waveform()

    def set_default(self) -> object:
        for name in self.mapping:
            self.set_parameter(name, self.default_controls[name])
        self.upload_control()
        self.waveform = self.default_waveform
        self.upload_waveform()
        return self
    
    def set_parameter(self, name: str, value: int) -> object:
        location = Feedback.mapping[name]
        bits = convert_bits(value, location["high"] - location["low"] + 1)
        pointer = location["high"]
        for i in bits:
            self.set_bit(location["index"], pointer, i)
            pointer = pointer - 1
        return self

    def get_parameter(self, name: str) -> int:
        location = Feedback.mapping[name]
        bits = bin(self.get_control(location["index"]))[2:].zfill(32)
        return eval("0b" + bits[31 - location["high"]: 32 - location["low"]])

    def upload_waveform(self) -> object:
        self.set_parameter("segments_enabled", len(self.waveform) - 1)
        for i in range(len(self.waveform)):
            self.set_parameter("set_sign", self.waveform[i]["sign"])
            self.set_parameter("set_x", self.waveform[i]["x"])
            self.set_parameter("set_y", self.waveform[i]["y"])
            self.set_parameter("set_slope", self.waveform[i]["slope"])
            self.set_parameter("set_address", i)
            self.set_parameter("set", 1)
            self.upload_control()
            self.set_parameter("set", 0)
            self.upload_control()
            self.set_parameter("set", 1)
            self.upload_control()
        return self

    def LO_on(self) -> object:
        self.set_parameter("LO_Reset", 0)
        self.upload_control()
        return self
    
    def LO_off(self) -> object:
        self.set_parameter("LO_Reset", 1)
        self.upload_control()
        return self
    
    def fast_PID_on(self) -> object:
        self.set_parameter("fast_PID_Reset", 0)
        self.upload_control()
        return self

    def fast_PID_off(self) -> object:
        self.set_parameter("fast_PID_Reset", 1)
        self.upload_control()
        return self
    
    def slow_PID_on(self) -> object:
        self.set_parameter("slow_PID_Reset", 0)
        self.upload_control()
        return self
    
    def slow_PID_off(self) -> object:
        self.set_parameter("slow_PID_Reset", 1)
        self.upload_control()
        return self

    def launch_frequency_control(self) -> object:
        self.set_parameter("initiate", 1)
        self.upload_control()
        self.set_parameter("initiate", 0)
        self.upload_control()
        self.set_parameter("initiate", 1)
        self.upload_control()
        return self

# todo : check if the setup exists upon initialization
class MIM():
    def __init__(self, ip, logger = None):
        self.mim = instruments.MultiInstrument(ip, force_connect = True, platform_id = 4)
        self.logger = logger
        if self.logger:
            self.logger.debug("MIM Created.")
        self.tk = None
        self.fb = None
        
    def initialize(self) -> object:
        # Set the MultiInstrument configuration here
        if self.logger:
            self.logger.info("Initializing MIM.")
            self.logger.debug("Creating turnkey.")
        self.tk = Turnkey(self.mim.set_instrument(2, instruments.CloudCompile, bitstream = "bitstreams/turnkey.tar.gz"), 2)
        if self.logger:
            self.logger.debug("Initializing turnkey.")
        self.tk.set_default()
        if self.logger:
            self.logger.debug("Creating feedback.")
        self.fb = Feedback(self.mim.set_instrument(3, instruments.CloudCompile, bitstream = "bitstreams/feedback.tar.gz"), 3)
        if self.logger:
            self.logger.debug("Initializing feedback.")
        self.fb.set_default()
        if self.logger:
            self.logger.debug("Creating oscilloscope.")
        self.osc = self.mim.set_instrument(4, instruments.Oscilloscope)
        if self.logger:
            self.logger.debug("Setting connections.")
        self.con = self.mim.set_connections([{"source": "Input1", "destination": "Slot2InA"},
                                            {"source": "Slot2OutA", "destination": "Output1"},
                                            {"source": "Input2", "destination": "Slot3InA"},
                                            {"source": "Slot3OutA", "destination": "Output4"},
                                            {"source": "Slot3OutB", "destination": "Output3"},
                                            {"source": "Slot3OutC", "destination": "Output2"},
                                            {"source": "Input2", "destination": "Slot4InA"},
                                            {"source": "Slot3OutC", "destination": "Slot4InB"}])
        if self.logger:
            self.logger.debug("Setting frontends and outputs.")
        self.mim.set_frontend(1, "1MOhm", "DC", "0dB")
        self.mim.set_frontend(2, "1MOhm", "DC", "0dB")
        self.mim.set_output(1, "14dB")
        self.mim.set_output(2, "0dB")
        self.mim.set_output(3, "14dB")
        self.mim.set_output(4, "14dB")
        if self.logger:
            self.logger.debug("Final steps.")
        self.tk.stop()
        return self
    
    def disconnect(self) -> object:
        if self.logger:
            self.logger.info("Disconnecting MIM.")
        self.mim.relinquish_ownership()
        return self
    
    def run(self) -> object:
        if self.logger:
            self.logger.info("Running MIM.")
        self.tk.run()
        return self
    
    def stop(self) -> object:
        if self.logger:
            self.logger.info("Stopping MIM.")
        self.tk.stop()
        return self
    
    def sweep(self) -> object:
        if self.logger:
            self.logger.info("MIM starting sweeping.")
        self.tk.sweep()
        return self
    
    def power_lock(self, switch: bool) -> object:
        if self.logger:
            self.logger.info("MIM power lock switching.")
        self.tk.power_lock(switch)
        return self
    
    def get_waveform(self, frames: int = 50, delay: float = 0.000) -> list[float]:
        if self.logger:
            self.logger.info("Getting waveform from MIM.")
        result = []
        for i in range(frames):
            result = self.osc.get_data()["ch1"] + result
            time.sleep(delay)
        return result

    def get_module(self, name: str) -> typing.Union[Turnkey, Feedback, None]:
        if name == "turnkey" and self.tk:
            return self.tk
        elif name == "feedback" and self.fb:
            return self.fb
        else:
            return None

def test(mim, N, delay):
    fig, ax = plt.subplots()
    x = np.linspace(0, N, 1024 * N)
    y = mim.get_waveform(N, delay)
    ax.plot(x, y)
    plt.show()

if __name__ == "__main__":
    mim = MIM("192.168.73.1")
    mim.initialize()
    mim.sweep()
    
    # testing
    test(mim, 100, 0.0005)