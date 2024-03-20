import serial
import typing

class TCM():
    def __init__(self, port = "COM7", baudrate = "57600", timeout = 1, logger = None):
        self.ser = serial.Serial(port, baudrate = baudrate, timeout = timeout)
        self.logger = logger
        if self.logger:
            self.logger.info("TCM created.")

    def post(self, request: str) -> bytes:
        self.ser.write(request.encode())
        reply = self.ser.read_until(b"\r")
        if reply:
            #print(reply)
            return reply
        else:
            raise Exception("Empty response!")
    
    def get_temp(self) -> float:
        return float(self.post("TC1:TCACTTEMP?\r").decode()[14:-1])
        
    def get_setpoint(self) -> float:
        return float(self.post("TC1:TCADJTEMP?\r").decode()[14:-1])
    
    def get_switch(self) -> int:
        return int(self.post("TC1:TCSW?\r").decode()[9])
    
    def set_on(self) -> object:
        self.post("TC1:TCSW=1\r")
        return self
    
    def set_off(self) -> object:
        self.post("TC1:TCSW=0\r")
        return self
        
    def set_temp(self, target: float) -> object:
        self.post("TC1:TCADJTEMP=%.3f\r"%target)
        return self
    
    def save(self) -> object:
        self.post("TC1:TCADJTEMP!\r")
        return self
    
    def close(self) -> object:
        self.ser.close()
        return self
        
