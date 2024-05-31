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
    
class MCC_Template(MCC):
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

class MIM():
    def __init__(self, ip, config_id = "1", logger = None):
        self.mim = instruments.MultiInstrument(ip, force_connect = True, platform_id = 4)
        self.config_id = config_id
        self.logger = logger
        if self.logger:
            self.logger.debug("MIM Created.")
        self.instruments = {1:None, 2:None, 3:None, 4:None}
        self.config = None
        
        self.uploading_queue = queue.Queue() 
        self.data_uploading_queue = queue.Queue() # only allows one queueing at a time
        self.uploader = threading.Thread(target = self.uploader_function, args = (), daemon = True)
        self.uploader.start()

    def get_slot(self, type: str) -> Union[int, None]:
        for i in self.instruments:
            if self.instruments[i] is not None and self.instruments[i][0] == type:
                return i
        return None

    def get_instrument(self, arg: Union[int, str, None]) -> Union[Turnkey, Feedback, None]:
        if type(arg) == int:
            return self.instruments[arg][1]
        elif type(arg) == str:
            return self.get_instrument(self.get_slot(arg))
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
                            if self.logger:
                                self.logger.debug("Unregistered MCC purpose.")
                            slot = int(i.get("slot"))
                            parameters = {j.get("name"):int(j.get("value")) for j in i.findall("./parameters/parameter")}
                            mapping = {j.get("name"):{"index": int(j.get("index")), "high": int(j.get("high")), "low": int(j.get("low"))} for j in i.findall("./parameters/parameter")}
                            self.instruments[slot] = (i.get("purpose"), MCC_Template(self.mim.set_instrument(slot, instruments.CloudCompile, bitstream = "./bitstreams/" + i.find("bitstream").text + ".tar.gz"), slot, parameters, mapping))
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
        if "turnkey" in self.instruments.values():
            self.upload_control("turnkey")
            self.command("turnkey", "stop")
        if "feedback" in self.instruments.values():
            self.upload_control("feedback")
        return self
    
    def upload_control(self, purpose: str) -> object:
        if self.logger:
            self.logger.debug("Queued control for %s."%purpose)
        instrument = self.get_instrument(purpose)
        self.uploading_queue.put((instrument, instrument.controls.copy()))

    def upload_data(self, purpose: str) -> str:
        if self.data_uploading_queue.empty():
            if self.logger:
                self.logger.debug("Queued data for %s."%purpose)
            instrument = self.get_instrument(purpose)
            self.data_uploading_queue.put((instrument, instrument.controls.copy()))
            return "queued"
        if self.logger:
            self.logger.debug("Data uploading queue is busy.")
        return "rejected"
    
    def uploader_function(self) -> NoReturn:
        while True:
            time.sleep(0.05)
            if not self.uploading_queue.empty():
                if self.logger:
                    self.logger.debug("Uploading control.")
                self.upload(self.uploading_queue.get())
            if not self.data_uploading_queue.empty():
                if self.logger:
                    self.logger.debug("Uploading data.")
                self.upload(self.data_uploading_queue.get())

    def upload(self, package: tuple[object, dict[int, int]]) -> object:
        package[0].upload(package[1])
        return self

    # intercept all mcc commands
    def command(self, purpose: str, operation: str) -> object:
        if self.logger:
            self.logger.debug("Implementing operation \"%s\" for %s."%(operation, purpose))
        match purpose:
            case "turnkey":
                instrument = self.get_instrument("turnkey")
                match operation:
                    case "run":
                        instrument.set_parameter("mode", 0)
                        instrument.set_parameter("Reset", 0)
                        instrument.set_parameter("manual_offset", 0)
                        self.upload_control("turnkey")
                    case "stop":
                        instrument.set_parameter("Reset", 1)
                        self.upload_control("turnkey")
                    case "sweep":
                        instrument.set_parameter("mode", 1)
                        instrument.set_parameter("Reset", 0)
                        instrument.set_parameter("manual_offset", 0)
                        self.upload_control("turnkey")
                    case "power_lock_on":
                        instrument.set_parameter("PID_lock", 0)
                        self.upload_control("turnkey")
                    case "power_lock_off":
                        instrument.set_parameter("PID_lock", 1)
                        self.upload_control("turnkey")
                    case _:
                        raise Exception("Unknown operation.")
            case "feedback":
                instrument = self.get_instrument("feedback")
                match operation:
                    case "LO_on":
                        instrument.set_parameter("LO_Reset", 0)
                        self.upload_control("feedback")
                    case "LO_off":
                        instrument.set_parameter("LO_Reset", 1)
                        self.upload_control("feedback")
                    case "fast_PID_on":
                        instrument.set_parameter("fast_PID_Reset", 0)
                        self.upload_control("feedback")
                    case "fast_PID_off":
                        instrument.set_parameter("fast_PID_Reset", 1)
                        self.upload_control("feedback")
                    case "slow_PID_on":
                        instrument.set_parameter("slow_PID_Reset", 0)
                        self.upload_control("feedback")
                    case "slow_PID_off":
                        instrument.set_parameter("slow_PID_Reset", 1)
                        self.upload_control("feedback")
                    case "auto_match_on":
                        instrument.set_parameter("enable_auto_match", 0)
                        self.upload_control("feedback")
                    case "auto_match_off":
                        instrument.set_parameter("enable_auto_match", 1)
                        self.upload_control("feedback")
                    case "launch_auto_match":
                        instrument.set_parameter("initiate_auto_match", 1)
                        self.upload_control("feedback")
                        instrument.set_parameter("initiate_auto_match", 0)
                        self.upload_control("feedback")
                        instrument.set_parameter("initiate_auto_match", 1)
                        self.upload_control("feedback")
                    case "launch_frequency_control":
                        instrument.set_parameter("initiate", 1)
                        self.upload_control("feedback")
                        instrument.set_parameter("initiate", 0)
                        self.upload_control("feedback")
                        instrument.set_parameter("initiate", 1)
                        self.upload_control("feedback")
                    case "upload_waveform":
                        instrument.set_parameter("segments_enabled", len(instrument.waveform) - 1)
                        for i in range(len(instrument.waveform)):
                            instrument.set_parameter("set_sign", instrument.waveform[i]["sign"])
                            instrument.set_parameter("set_x", instrument.waveform[i]["x"])
                            instrument.set_parameter("set_y", instrument.waveform[i]["y"])
                            instrument.set_parameter("set_slope", instrument.waveform[i]["slope"])
                            instrument.set_parameter("set_address", i)
                            instrument.set_parameter("set", 1)
                            self.upload_control("feedback")
                            instrument.set_parameter("set", 0)
                            self.upload_control("feedback")
                            instrument.set_parameter("set", 1)
                            self.upload_control("feedback")
                    case _:
                        raise Exception("Unknown operation.")
            case _:
                raise Exception("Unknown purpose.")
        return self


    def disconnect(self) -> object:
        if self.logger:
            self.logger.info("Disconnecting MIM.")
        self.mim.relinquish_ownership()
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
    
    # testing
    test(mim, 100, 0.0005)