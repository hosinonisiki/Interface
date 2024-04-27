import moku.instruments as instruments
import numpy as np
import time
from typing import Union, NoReturn
import requests
import json
import xml.etree.ElementTree as ET
import threading
import queue

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
    def __init__(self, mcc: object, slot: int, controls: dict[int, int] = None):
        self.mcc = mcc
        self.slot = slot
        self.controls = {}

        self.uploading_queue = queue.Queue() 
        self.data_uploading_queue = queue.Queue() # only allows one queueing at a time
        self.uploader = threading.Thread(target = self.uploader_function, args = (), daemon = True)
        self.uploader.start()

        self.download_control()
        self.set_control(controls) # initialize control
    
    def download_control(self) -> object:
        try:
            self.controls = {index:value for index, value in zip(range(16), [self.mcc.get_control(i)[i] for i in range(16)])}
        except Exception as e:
            raise Exception("Connection error: %s"%e.__repr__())
        return self
    
    '''   
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
    '''

    def upload_control(self) -> object:
        self.uploading_queue.put(self.controls.copy())
        return self

    def upload_data(self) -> str:
        if self.data_uploading_queue.empty():
            self.data_uploading_queue.put(self.controls.copy())
            return "queued"
        return "rejected"

    def uploader_function(self) -> NoReturn:
        while True:
            time.sleep(0.05)
            if not self.uploading_queue.empty():
                self.upload(self.uploading_queue.get())
            if not self.data_uploading_queue.empty():
                self.upload(self.data_uploading_queue.get())

    def upload(self, controls: dict[int, int]) -> object:
        try:
            for i in range(15, -1, -1):
                self.mcc.set_control(i, controls[i])
        except Exception as e:
            raise Exception("Connection error: %s"%e.__repr__())
        return self

    def set_control(self, *arg) -> object:
        if len(arg) == 1 and arg[0] is not None:
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
    def __init__(self, mcc: object, slot: int, parameters: dict[str, int], mapping: dict[str, dict[str, int]], controls: dict[int, int] = None):
        super().__init__(mcc, slot, controls)
        self.parameters = parameters
        self.mapping = mapping
        for i in self.parameters:
            self.set_parameter(i, self.parameters[i])

    def set_parameter(self, name: str, value: int) -> object:
        location = self.mapping[name]
        bits = convert_bits(value, location["high"] - location["low"] + 1)
        pointer = location["high"]
        for i in bits:
            self.set_bit(location["index"], pointer, i)
            pointer = pointer - 1
        return self
    
    def get_parameter(self, name: str) -> int:
        location = self.mapping[name]
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
    def __init__(self, mcc: object, slot: int, parameters: dict[str, int], mapping: dict[str, dict[str, int]], controls: dict[int, int] = None):
        super().__init__(mcc, slot, controls)
        self.parameters = parameters
        self.mapping = mapping
        for i in self.parameters:
            self.set_parameter(i, self.parameters[i])
        self.waveform = []
    
    def set_parameter(self, name: str, value: int) -> object:
        location = self.mapping[name]
        bits = convert_bits(value, location["high"] - location["low"] + 1)
        pointer = location["high"]
        for i in bits:
            self.set_bit(location["index"], pointer, i)
            pointer = pointer - 1
        return self

    def get_parameter(self, name: str) -> int:
        location = self.mapping[name]
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

    def auto_match_on(self) -> object:
        self.set_parameter("enable_auto_match", 0)
        self.upload_control()
        return self
    
    def auto_match_off(self) -> object:
        self.set_parameter("enable_auto_match", 1)
        self.upload_control()
        return self

    def launch_auto_match(self) -> object:
        self.set_parameter("initiate_auto_match", 1)
        self.upload_control()
        self.set_parameter("initiate_auto_match", 0)
        self.upload_control()
        self.set_parameter("initiate_auto_match", 1)
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

class MIM():
    def __init__(self, ip, config_id = "1", logger = None):
        self.mim = instruments.MultiInstrument(ip, force_connect = True, platform_id = 4)
        self.config_id = config_id
        self.logger = logger
        if self.logger:
            self.logger.debug("MIM Created.")
        self.instruments = {1:None, 2:None, 3:None, 4:None}

    def get_tk(self) -> Union[Turnkey, None]:
        for i in self.instruments:
            if self.instruments[i] is not None and self.instruments[i][0] == "turnkey":
                return self.instruments[i][1]
        return None
    
    def get_fb(self) -> Union[Feedback, None]:
        for i in self.instruments:
            if self.instruments[i] is not None and self.instruments[i][0] == "feedback":
                return self.instruments[i][1]
        return None

    def initialize(self) -> object:
        # parse config from xml
        if self.logger:
            self.logger.info("Initializing MIM.")
            self.logger.debug("Parsing configuration.")
        root = ET.parse("config.xml").getroot()
        for i in root.findall("./configurations/config"):
            if i.get("id") == self.config_id:
                self.config = i
                break
            else:
                raise Exception("Configuration not found.")
        if self.logger:
            self.logger.debug("Configuration found, working on %s firmware version %s with comb No.%s. %s"%(self.config.get("platform"), self.config.get("firmware"), self.config.get("comb_id"), self.config.get("description")))

        # set up instruments
        for i in self.config.findall("./instruments/instrument"):
            match i.get("type"):
                case "CloudCompile":
                    match i.get("purpose"):
                        case "turnkey":
                            if self.logger:
                                self.logger.debug("Creating turnkey.")
                            slot = int(i.get("slot"))
                            parameters = {j.get("name"):int(j.get("value")) for j in i.findall("./parameters/parameter")}
                            mapping = {j.get("name"):{"index": int(j.get("index")), "high": int(j.get("high")), "low": int(j.get("low"))} for j in i.findall("./parameters/parameter")}
                            self.instruments[slot] = ("turnkey", Turnkey(self.mim.set_instrument(slot, instruments.CloudCompile, bitstream = "./bitstreams/" + i.find("bitstream").text + ".tar.gz"), slot, parameters, mapping))
                        case "feedback":
                            if self.logger:
                                self.logger.debug("Creating feedback.")
                            slot = int(i.get("slot"))
                            parameters = {j.get("name"):int(j.get("value")) for j in i.findall("./parameters/parameter")}
                            mapping = {j.get("name"):{"index": int(j.get("index")), "high": int(j.get("high")), "low": int(j.get("low"))} for j in i.findall("./parameters/parameter")}
                            self.instruments[slot] = ("feedback", Feedback(self.mim.set_instrument(slot, instruments.CloudCompile, bitstream = "./bitstreams/" + i.find("bitstream").text + ".tar.gz"), slot, parameters, mapping))
                        case _:
                            raise Exception("Unknown MCC purpose.")
                case _:
                    if self.logger:
                        self.logger.debug("Creating %s."%i.get("type"))
                    self.instruments[int(i.get("slot"))] = (i.get("type"), self.mim.set_instrument(int(i.get("slot")), eval("instruments.%s"%i.get("type"))))

        # set up connections, frontends and outputs
        if self.logger:
            self.logger.debug("Setting connections.")
        self.con = []
        for i in self.config.findall("./connections/connection"):
            self.con.append({"source": i.get("source"), "destination": i.get("destination")})
        self.mim.set_connections(self.con)

        if self.logger:
            self.logger.debug("Setting frontends and outputs.")
        for i in self.config.findall("./io_settings/input"):
            self.mim.set_frontend(int(i.get("channel")), i.get("impedance"), i.get("coupling"), i.get("attenuation"))
        for i in self.config.findall("./io_settings/output"):
            self.mim.set_output(int(i.get("channel")), i.get("gain"))
        if self.logger:
            self.logger.debug("Final steps.")
        self.get_tk().upload(self.get_tk().controls)
        self.get_fb().upload(self.get_fb().controls)
        self.get_tk().stop()
        return self
    
    def disconnect(self) -> object:
        if self.logger:
            self.logger.info("Disconnecting MIM.")
        self.mim.relinquish_ownership()
        return self
    
    def run(self) -> object:
        if self.logger:
            self.logger.info("Running MIM.")
        self.get_tk().run()
        return self
    
    def stop(self) -> object:
        if self.logger:
            self.logger.info("Stopping MIM.")
        self.get_tk().stop()
        return self
    
    def sweep(self) -> object:
        if self.logger:
            self.logger.info("MIM starting sweeping.")
        self.get_tk().sweep()
        return self
    
    def power_lock(self, switch: bool) -> object:
        if self.logger:
            self.logger.info("MIM power lock switching.")
        self.get_tk().power_lock(switch)
        return self
    
    def get_waveform(self, frames: int = 50, delay: float = 0.000) -> list[float]:
        if self.logger:
            self.logger.info("Getting waveform from MIM.")
        result = []
        for i in range(frames):
            result = self.osc.get_data()["ch1"] + result
            time.sleep(delay)
        return result

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