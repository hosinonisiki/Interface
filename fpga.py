import moku.instruments as instruments
import numpy as np
import time
from typing import Union, NoReturn
import requests
import json
import xml.etree.ElementTree as ET
import threading
import queue
import re
import sys

# for AXKU041 connection
sys.path.append("./AXKU041/python control/")
import uart
import bus
import module_signal_router
import module_moku_mim_wrapper
import spi
import port_numbers

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
    def __init__(self, mcc: object, slot: int, controls: dict[int, int] = None, mode: str = "default"):
        self.mcc = mcc
        self.slot = slot
        self.controls = {i:0 for i in range(16)}
        self.mode = mode
        if self.mode == "http":
            assert self.mcc is None, "HTTP mode does not require an MCC object."

        self.default_controls = self.controls.copy()
    
    def set_default_control(self) -> object:
        self.set_control(self.default_controls)
        return self
    
    def download_control(self) -> object:
        if self.mode == "default":
            if self.mcc is None:
                pass
            else:
                try:
                    self.controls = {index:value for index, value in zip(range(16), [self.mcc.get_control(i)[i] for i in range(16)])}
                except Exception as e:
                    raise Exception("Connection error: %s"%e.__repr__())
        elif self.mode == "http":
            try:
                response = requests.get("http://192.168.73.1/api/v2/registers")
                if response.status_code != 200:
                    raise Exception("Status code: %s"%response.status_code)
                for i in response.json():
                    if i[0] == "instr" + str(self.slot - 1) and all([str(j) in i[1] for j in range(6, 22)]):
                        self.controls = {index:i[1][str(index + 6)] for index in range(16)}
                        break
                else:
                    self.controls = {index:0 for index in range(16)}
            except Exception as e:
                raise Exception("Connection error: %s"%e.__repr__())
        elif self.mode == "AXKU041":
            try:
                for i in range(15, -1, -1):
                    self.controls[i] = int.from_bytes(self.mcc.read(i + (self.slot - 1) * 16), "big")
            except Exception as e:
                raise Exception("Connection error: %s"%e.__repr__())
        return self

    def upload_control(self, controls: dict[int, int]) -> object:
        if self.mode == "default":
            try:
                for i in range(15, -1, -1):
                    self.mcc.set_control(i, controls[i])
            except Exception as e:
                raise Exception("Connection error: %s"%e.__repr__())
        elif self.mode == "http":
            post = "[[\"instr" + str(self.slot - 1) + "\", {"
            for i in range(0, 16):
                post = post + "\"" + str(i + 6) + "\":" + str(controls[i])
                if i != 15:
                    post = post + ","
            post = post + "}]]"
            try:
                request = json.loads(post)
                response = requests.post(url = "http://192.168.73.1/api/v2/registers", json = request)
                if response.status_code != 200:
                    raise Exception("Status code: %s"%response.status_code)
            except Exception as e:
                raise Exception("Connection error: %s"%e.__repr__())
        elif self.mode == "AXKU041":
            try:
                for i in range(15, -1, -1):
                    self.mcc.write(i + (self.slot - 1) * 16, controls[i])
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
    def __init__(self, mcc: object, slot: int, parameters: dict[str, int], mapping: dict[str, dict[str, int]], controls: dict[int, int] = None, mode: str = "default"):
        super().__init__(mcc, slot, controls, mode)
        self.default_parameters = parameters
        self.mapping = mapping

    def set_default_parameter(self) -> object:
        for i in self.default_parameters:
            self.set_parameter(i, self.default_parameters[i])

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
    def __init__(self, mcc: object, slot: int, parameters: dict[str, int], mapping: dict[str, dict[str, int]], controls: dict[int, int] = None, mode: str = "default"):
        super().__init__(mcc, slot, controls, mode)
        self.default_parameters = parameters
        self.mapping = mapping
        self.waveform = []

    def set_default_parameter(self) -> object:
        for i in self.default_parameters:
            self.set_parameter(i, self.default_parameters[i])
    
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
    def __init__(self, mcc: object, slot: int, parameters: dict[str, int], mapping: dict[str, dict[str, int]], controls: dict[int, int] = None, mode: str = "default"):
        super().__init__(mcc, slot, controls, mode)
        self.default_parameters = parameters
        self.mapping = mapping

    def set_default_parameter(self) -> object:
        for i in self.default_parameters:
            self.set_parameter(i, self.default_parameters[i])

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
        self.logger = logger
        self.config_id = config_id
        if re.match(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$", ip) or re.match(r"^\[([0-9a-fA-F]{0,4}:){5,7}[0-9a-fA-F]{0,4}\]$", ip):
            self.ip = ip
            self.mode = "default"
            # claim ownership at class initialization under default mode
            self.mim = instruments.MultiInstrument(self.ip, force_connect = True, platform_id = 4)
        elif ip == "local":
            self.ip = "192.168.73.1"
            self.mode = "http"
            # verify the connection by sending a request
            response = requests.get("http://192.168.73.1/api/v2/registers")
            if response.status_code != 200:
                if self.logger:
                    self.logger.error("Connection error: %s"%response.status_code)
                raise Exception("Status Code: %s"%response.status_code)
        elif re.match(r"^COM[0-9]{1,2}$", ip):
            # Serial connection indicates instead of Moku:Pro,
            # the custom FPGA design running on AXKU041 is used.
            self.ip = ip
            self.mode = "AXKU041"
            try:
                self.serial = uart.MySerial(self.ip, baudrate = 19200, parity = "E", timeout = 0.5)
                self.bus = bus.Bus(self.serial)
                self.module_mim = module_moku_mim_wrapper.ModuleMokuMIMWrapper(self.bus, self.config_id)
                self.module_router = module_signal_router.ModuleSignalRouter(self.bus)
                # Set up the routing to let the MIM module directly connect to design's interface
                self.module_router.set_routing(port_numbers.OUTPUT_A, port_numbers.MIM_OUT_A)
                self.module_router.set_routing(port_numbers.OUTPUT_B, port_numbers.MIM_OUT_B)
                self.module_router.set_routing(port_numbers.OUTPUT_C, port_numbers.MIM_OUT_C)
                self.module_router.set_routing(port_numbers.OUTPUT_D, port_numbers.MIM_OUT_D)
                self.module_router.set_routing(port_numbers.MIM_IN_A, port_numbers.INPUT_A)
                self.module_router.set_routing(port_numbers.MIM_IN_B, port_numbers.INPUT_B)
                self.module_router.set_routing(port_numbers.MIM_IN_C, port_numbers.INPUT_C)
                self.module_router.set_routing(port_numbers.MIM_IN_D, port_numbers.INPUT_D)
                self.module_router.upload()
                self.sp = spi.Spi(self.serial)
                self.sp.write("adc1", 3, 3, b"\x00\x14\x41")
                self.sp.write("adc1", 3, 3, b"\x00\x17\x06")
                self.sp.write("adc1", 3, 3, b"\x00\xFF\x01")
                self.sp.write("adc2", 3, 3, b"\x00\x14\x41")
                self.sp.write("adc2", 3, 3, b"\x00\x17\x06")
                self.sp.write("adc2", 3, 3, b"\x00\xFF\x01")
            except Exception as e:
                if self.logger:
                    self.logger.error("Connection error: %s"%e.__repr__())
                raise Exception("Connection error: %s"%e.__repr__())
        else:
            if self.logger:
                self.logger.error("Invalid IP address.")
            raise Exception("Invalid IP address.")
        if self.logger:
            self.logger.debug("MIM Created.")
        self.instruments = {1:None, 2:None, 3:None, 4:None}
        self.purposes = {}
        self.config = None
        if self.mode == "default" or self.mode == "http":
            self.bitstreams = {1:None, 2:None, 3:None, 4:None}
            self.other_instruments = {1:None, 2:None, 3:None, 4:None}
            self.connections = []
            self.frontends = {}
            self.outputs = {}
        
        self.uploading_queue = queue.Queue() 
        self.data_uploading_queue = queue.Queue() # only allows one queueing at a time
        self.uploader = threading.Thread(target = self.uploader_function, args = (), daemon = True)
        self.uploader.start()

    def get_slot(self, type: str) -> Union[int, None]:
        if type in self.purposes:
            return self.purposes[type]
        return None

    def get_instrument(self, arg: Union[int, str, None]) -> Union[Turnkey, Feedback, None]:
        if type(arg) == int:
            return self.instruments[arg]
        elif type(arg) == str:
            return self.get_instrument(self.get_slot(arg))
        return None

    def parse_config(self) -> object:
        # parse config from xml
        if self.logger:
            self.logger.debug("Parsing configuration.")
        root = ET.parse("config.xml").getroot()
        for i in root.findall("./configurations/config"):
            if i.get("id") == self.config_id:
                self.config = i
                break
        else:
            raise Exception("Configuration not found.")
        if self.logger:
            if self.mode == "default" or self.mode == "http":
                if self.config.get("platform") and self.config.get("firmware") and self.config.get("comb_id"):
                    self.logger.debug("Configuration found, working on %s firmware version %s with comb No.%s. %s"%(self.config.get("platform"), self.config.get("firmware"), self.config.get("comb_id"), self.config.get("description")))
                else:
                    # a miscellanous configuration
                    self.logger.debug("Configuration found, working with %s."%self.config.get("description"))
            elif self.mode == "AXKU041":
                # Verify if the configuration is supported in the design
                if self.config.get("AXKU041_supported") == "True":
                    self.logger.debug("Configuration found, working on AXKU041. %s"%self.config.get("description"))
                else:
                    raise Exception("The chosen configuration is not supported on AXKU041.")
        
        # set up instruments
        self.instruments = {1:None, 2:None, 3:None, 4:None}
        self.purposes = {}
        if self.mode == "default" or self.mode == "http":
            self.bitstreams = {1:None, 2:None, 3:None, 4:None}
            self.other_instruments = {1:None, 2:None, 3:None, 4:None}
        for i in self.config.findall("./instruments/instrument"):
            match i.get("type"):
                case "CloudCompile":
                    slot = int(i.get("slot"))
                    mapping = {j.get("name"):{"index": int(j.get("index")), "high": int(j.get("high")), "low": int(j.get("low"))} for j in i.findall("./parameters/parameter")}
                    if self.mode == "default" or self.mode == "http":
                        parameters = {j.get("name"):int(j.get("value")) for j in i.findall("./parameters/parameter")}
                        mcc_object = None
                        self.bitstreams[slot] = "./bitstreams/" + i.find("bitstream").text + ".tar.gz"
                    elif self.mode == "AXKU041":
                        parameters = {j.get("name"):int(j.get("value")) for j in i.findall("./parameters_for_AXKU041/parameter")}
                        mcc_object = self.module_mim
                    match i.get("purpose"):
                        case "turnkey":
                            if self.logger:
                                self.logger.debug("Creating turnkey.")
                            self.instruments[slot] = Turnkey(mcc_object, slot, parameters, mapping, {}, self.mode)
                            self.purposes["turnkey"] = slot
                        case "feedback":
                            if self.logger:
                                self.logger.debug("Creating feedback.")
                            self.instruments[slot] = Feedback(mcc_object, slot, parameters, mapping, {}, self.mode)
                            self.purposes["feedback"] = slot
                        case "feedback and turnkey":
                            if self.logger:
                                self.logger.debug("Creating feedback and turnkey.")
                            self.instruments[slot] = Feedback(mcc_object, slot, parameters, mapping, {}, self.mode)
                            self.purposes["feedback"] = slot
                            self.purposes["turnkey"] = slot
                        case _:
                            if self.logger:
                                self.logger.debug("Unregistered MCC purpose.")
                            self.instruments[slot] = MCC_Template(mcc_object, slot, parameters, mapping, {}, self.mode)
                            self.purposes[i.get("purpose")] = slot
                case _:
                    if self.mode == "default" or self.mode == "http":
                        if self.logger:
                            self.logger.debug("Creating %s."%i.get("type"))
                        slot = int(i.get("slot"))
                        self.other_instruments[slot] = eval("instruments.%s"%i.get("type"))
                    elif self.mode == "AXKU041":
                        if self.logger:
                            self.logger.debug("Skipping the creation of %s."%i.get("type"))

        if self.mode == "default" or self.mode == "http":
            # set up connections, frontends and outputs
            if self.logger:
                self.logger.debug("Setting connections.")
            self.connections = []
            for i in self.config.findall("./connections/connection"):
                self.connections.append({"source": i.get("source"), "destination": i.get("destination")})

            if self.logger:
                self.logger.debug("Setting frontends and outputs.")
            self.frontends = {}
            self.outputs = {}
            for i in self.config.findall("./io_settings/input"):
                self.frontends[int(i.get("channel"))] = {"impedance": i.get("impedance"), "coupling": i.get("coupling"), "attenuation": i.get("attenuation")}
            for i in self.config.findall("./io_settings/output"):
                self.outputs[int(i.get("channel"))] = {"gain": i.get("gain")}
        return self

    def upload_config(self) -> object:
        if self.logger:
            self.logger.debug("Uploading configuration.")
        if self.mode == "http":
            # claim ownership at uploading function under http mode
            self.mim = instruments.MultiInstrument(self.ip, force_connect = True, platform_id = 4)
        if self.mode == "default" or self.mode == "http":
            for i in range(1, 5):
                if self.bitstreams[i]:
                    self.instruments[i].mcc = self.mim.set_instrument(i, instruments.CloudCompile, bitstream = self.bitstreams[i])
            for i in self.other_instruments:
                if self.other_instruments[i]:
                    self.instruments[i] = self.mim.set_instrument(i, self.other_instruments[i])
            self.mim.set_connections(self.connections)
            for i in self.frontends:
                self.mim.set_frontend(i, self.frontends[i]["impedance"], self.frontends[i]["coupling"], self.frontends[i]["attenuation"])
            for i in self.outputs:
                self.mim.set_output(i, self.outputs[i]["gain"])
        elif self.mode == "AXKU041":
            self.module_mim.set_config(self.config_id)
            # Refresh the module
            self.module_mim.reset()
            # Set the module to the specified configuration
            self.module_mim.enable()
            self.module_mim.upload()
        return self

    def upload_parameter(self) -> object:
        for purpose in self.purposes:
            self.get_instrument(purpose).set_default_parameter()
            self.upload_control(purpose)
        return self

    def initialize(self) -> object:
        if self.logger:
            self.logger.info("Initializing MIM.")
        self.parse_config()
        self.upload_config()
        self.upload_parameter()
        return self
    
    def sync_download(self) -> object:
        if self.logger:
            self.logger.info("Synchronizing local parameters.")
        for purpose in self.purposes:
            self.get_instrument(purpose).download_control()
        return self

    def sync_upload(self) -> object:
        if self.logger:
            self.logger.info("Synchronizing remote parameters.")
        for purpose in self.purposes:
            self.get_instrument(purpose).upload_control()
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
        package[0].upload_control(package[1])
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
        if self.mode == "default" or self.mode == "http":
            self.mim.relinquish_ownership()
        elif self.mode == "AXKU041":
            self.serial.close()
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