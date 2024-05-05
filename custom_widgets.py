import tkinter as tk
import tkinter.ttk as ttk

from PIL import Image, ImageTk

import numpy as np

import threading
import time
import re

class ClampingKnob(tk.Canvas):
    def __init__(self, master = None, image_path = None, size = None, value_step = 1, step = 36, resistance = 1.5, lag = 0.5, value = 0, on_spin = None, max = np.inf, min = -np.inf, **kw):
        super().__init__(master, width = size + 2, height = size + 2, **kw)
        self.image = Image.open(image_path)
        self.size = size
        self.value_step = value_step
        self.step = step
        self.resistance = resistance
        self.lag = lag
        self.value = value
        self.on_spin = on_spin
        self.max = max
        self.min = min
        self.bind("<Button-1>", self.hold)
        self.bind("<B1-Motion>", self.spin)
        self.bind("<ButtonRelease-1>", self.release)
        self.knob_angle = 0
        self.draw()

    def set_value(self, value):
        self.value = value
    
    def get_value(self):
        return self.value

    def draw(self):
        #self.delete("all")
        self.image_tk = ImageTk.PhotoImage(self.image.rotate(-self.knob_angle))
        self.create_image(self.size / 2 + 2, self.size / 2 + 2, image = self.image_tk, anchor = tk.CENTER)

    def hold(self, event):
        self.start = event.x - event.y
        self.starting_angle = self.knob_angle

    def spin(self, event):
        self.angle = self.starting_angle + (event.x - event.y - self.start) / self.resistance
        if np.abs(self.angle - self.knob_angle) >= self.step:
            if self.angle - self.knob_angle > 0:
                direction = 1
                if self.value + self.value_step <= self.max:
                    self.value += self.value_step
            else:
                direction = -1
                if self.value - self.value_step >= self.min:
                    self.value -= self.value_step
            rotate_thread = threading.Thread(target = self.rotate_one_step, args = [direction])
            rotate_thread.start()
            if self.on_spin != None:
                self.on_spin()

    def rotate_one_step(self, direction):
        if direction == 1:
            self.knob_angle += (self.step - self.lag)
            self.draw()
            time.sleep(0.05)
            self.knob_angle += self.lag
            self.draw()
        else:
            self.knob_angle -= (self.step - self.lag)
            self.draw()
            time.sleep(0.05)
            self.knob_angle -= self.lag
            self.draw()

    def release(self, event):
        pass

class UnclampingKnob(tk.Canvas):
    def __init__(self, master = None, image_path = None, size = None, value_step = 1, step = 36, resistance = 1.5, lag = 0.5, value = 0, on_spin = None, **kw):
        super().__init__(master, width = size + 2, height = size + 2, **kw)
        self.image = Image.open(image_path)
        self.size = size
        self.value_step = value_step
        self.step = step
        self.resistance = resistance
        self.lag = lag
        self.value = value
        self.on_spin = on_spin
        self.bind("<Button-1>", self.hold)
        self.bind("<B1-Motion>", self.spin)
        self.bind("<ButtonRelease-1>", self.release)
        self.knob_angle = 0
        self.draw()

    def set_value(self, value):
        self.value = value
    
    def get_value(self):
        return self.value

    def draw(self):
        self.image_tk = ImageTk.PhotoImage(self.image.rotate(-self.knob_angle))
        self.create_image(self.size / 2 + 2, self.size / 2 + 2, image = self.image_tk, anchor = tk.CENTER)

    def hold(self, event):
        self.start = event.x - event.y
        self.starting_angle = self.knob_angle

    def spin(self, event):
        self.angle = self.starting_angle + (event.x - event.y - self.start) / self.resistance
        if np.abs(self.angle - self.knob_angle) >= self.step:
            if self.angle - self.knob_angle > 0:
                direction = 1
                self.value += self.value_step
            else:
                direction = -1
                self.value -= self.value_step
            rotate_thread = threading.Thread(target = self.rotate_one_step, args = [direction])
            rotate_thread.start()
            if self.on_spin != None:
                self.on_spin()

    def rotate_one_step(self, direction):
        if direction == 1:
            self.knob_angle += (self.step - self.lag)
            self.draw()
            time.sleep(0.05)
            self.knob_angle += self.lag
            self.draw()
        else:
            self.knob_angle -= (self.step - self.lag)
            self.draw()
            time.sleep(0.05)
            self.knob_angle -= self.lag
            self.draw()

    def release(self, event):
        pass

class KnobFrame(tk.Frame):
    def __init__(self, master = None, image_path = None, size = None, name = "", scale = 1, unit = "", clamped = True, **kw):
        super().__init__(master, width = size + 18, height = size + 50, **kw)
        self.name = name
        self.scale = scale
        self.unit = unit
        self.label = tk.Label(self, text = self.name)
        self.label.place(x = size / 2 + 6, y = 0, anchor = tk.N)
        if clamped:
            self.knob = ClampingKnob(self, image_path, size)
        else:
            self.knob = UnclampingKnob(self, image_path, size)
        self.knob.place(x = 4, y = 20, anchor = tk.NW)
        self.value_label = tk.Label(self, text = "% 3.3f"%(self.knob.get_value() * self.scale) + self.unit)
        self.value_label.place(x = size / 2 + 6, y = size + 22, anchor = tk.N)

    def set_value(self, value):
        self.knob.set_value(value)
        self.update()

    def get_value(self):
        return self.knob.get_value()
    
    def update(self):
        self.value_label.config(text = "% 3.3f"%(self.knob.get_value() * self.scale) + self.unit)

class QuantityFormat():
    default_prefix = {"m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
    def __init__(self, digits_limit = (9, 9, 3), prefix = None, unit = ""):
        self.digits_limit = digits_limit
        if prefix == None:
            self.prefix = self.default_prefix
        else:
            self.prefix = prefix
        self.unit = unit
        self.re = "^([-])?([0-9]{1,%d})"%digits_limit[0]
        if digits_limit[1] != 0:
            self.re += "(\.[0-9]{1,%d})?"%digits_limit[1]
        else:
            self.re += "(SomeRandomStringThatWillNeverOccur)?"
        if self.prefix != {}:
            self.re += "([%s])?"%"".join(self.prefix.keys())
        else:
            self.re += "(AnotherRandomStringThatWillNeverOccur)?"
        if self.unit != "":
            self.re += "(%s)?$"%unit
        else:
            self.re += "(YetAnotherRandomStringThatWillNeverOccur)?$"
        self.re = re.compile(self.re)

    def match(self, str):
        result = self.re.match(str)
        if result == None:
            return None, None, None
        value = "" if result.group(1) == None else "-"
        value += result.group(2)
        value += "" if result.group(3) == None else result.group(3)
        value = float(value)
        formalized = "" if result.group(1) == None else "-"
        formalized += result.group(2)
        if result.group(3) == None:
            if self.digits_limit[2] != 0:
                formalized += "." + "0" * self.digits_limit[2]
        elif len(result.group(3)) < self.digits_limit[2] + 1:
            formalized += result.group(3) + "0" * (self.digits_limit[2] - len(result.group(3)) + 1)
        else:
            formalized += result.group(3)
        formalized += "" if result.group(4) == None else result.group(4)
        formalized += self.unit
        if result.group(4) == None:
            return result, value, formalized
        else:
            return result, value * self.prefix[result.group(4)], formalized
        
    def break_up(self, formalized):
        digits_re = re.compile("[0-9\.]+")
        digits = digits_re.findall(formalized)
        split = digits[0].split(".")
        minus = False if formalized[0] != "-" else True
        if len(split) == 1:
            integer = split[0]
            fraction = ""
        else:
            integer = split[0]
            fraction = split[1]
        return minus, integer, fraction

class QuantityEntry(tk.Text):
    def __init__(self, master = None, formater = QuantityFormat(), report = lambda x: None, **kw):
        super().__init__(master, wrap = tk.NONE, height = 1, **kw)
        self.format = formater
        self.report = report
        self.stored = ""
        self.state = "changed"
        self.result = None
        self.value = None

        self.bind("<Key>", self.handle_key)
        self.bind("<Button-1>", self.handle_button)
        self.bind("<<Selection>>", self.handle_selection)
        self.bind("<<Destroy>>", self.destroy)
    
        self.destroying = False
        self.check_thread = threading.Thread(target = self.check, args = (), daemon = True)
        self.check_thread.start()

        self.tag_config("unchanged", background = "white", foreground = "black")
        self.tag_config("changed", background = "yellow", foreground = "black")
        self.tag_config("selected", background = "black", foreground = "white")
        self.tag_config("highlight", background = "blue", foreground = "white")
        self.tag_config("disabled", background = "#d3d3d3", foreground = "black")
        
    def call(self):
        self.report()

    def set(self, str):
        self.delete("1.0", "end-1c")
        self.insert("1.0", str)

    def get_value(self):
        return self.value

    def get_text(self):
        return self.get("1.0", "end-1c")

    def check(self):
        last_state = None
        while True:
            time.sleep(0.05)
            if self.destroying:
                return
            if self.state == "unchanged" and self.get("1.0", "end-1c") != self.stored:
                self.state = "changed"
                self.tag_remove("unchanged", "1.0", "end-1c")
            if self.state == "changed":
                self.tag_add("changed", "1.0", "end-1c")
            if self["state"] != last_state:
                last_state = self["state"]
                if self["state"] == "disabled":
                    self.tag_add("disabled", "1.0", "end-1c")
                    self["bg"] = "#d3d3d3"
                else:
                    self.tag_remove("disabled", "1.0", "end-1c")
                    self["bg"] = "white"
             
    def handle_key(self, event):
        if self["state"] == "disabled":
            return "break"
        match self.state:
            case "unchanged":
                return self.unchanged_handle_key(event)
            case "changed":
                return self.changed_handle_key(event)
            case "rolling":
                return self.rolling_handle_key(event)

    def unchanged_handle_key(self, event):
        match event.keysym:
            case "Return":
                return "break"
            case "Left" | "Right":
                return self.enter_roll(event)
            case _:
                return
            
    def changed_handle_key(self, event):
        match event.keysym:
            case "Return":
                self.store()
                self.report()
                return "break"
            case "Left" | "Right":
                return "break"
            case _:
                return
            
    def rolling_handle_key(self, event):
        match event.keysym:
            case "Return":
                return self.exit_roll_key(event)
            case "Up" | "Down" | "Left" | "Right":
                return self.roll(event) 
            case "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "0":
                # return self.overwrite(event)
                return "break"
            case _:
                return "break"
            
    def handle_button(self, event):
        if self["state"] == "disabled":
            return "break"
        match self.state:
            case "unchanged":
                return self.unchanged_handle_button(event)
            case "changed":
                return self.changed_handle_button(event)
            case "rolling":
                return self.rolling_handle_button(event)
            
    def unchanged_handle_button(self, event):
        return
    
    def changed_handle_button(self, event):
        return
    
    def rolling_handle_button(self, event):
        return self.exit_roll_button(event)

    def handle_selection(self, event):
        if self["state"] == "disabled":
            return "break"
        match self.state:
            case "unchanged":
                self.tag_remove("highlight", "1.0", "end")
                try:
                    start = self.index("sel.first")
                    end = self.index("sel.last")
                    if self.compare(end, "==", "end") or self.get(end) == "\n":
                        self.tag_remove("sel", "end-1c", "end")
                        end = "end-1c"
                    self.tag_add("highlight", start, end)
                except:
                    pass
            case "changed":
                self.tag_remove("highlight", "1.0", "end")
                try:
                    start = self.index("sel.first")
                    end = self.index("sel.last")
                    if self.compare(end, "==", "end") or self.get(end) == "\n":
                        self.tag_remove("sel", "end-1c", "end")
                        end = "end-1c"
                    self.tag_add("highlight", start, end)
                except:
                    pass
            case "rolling":
                return
            
    def destroy(self):
        self.destroying = True

    def store(self):
        text = self.get("1.0", "end-1c")
        self.result, self.value, self.formalized = self.format.match(text)
        if self.result != None:
            self.delete("1.0", "end-1c")
            self.insert("1.0", self.formalized)
            self.stored = self.formalized
            self.state = "unchanged"
            self.tag_remove("changed", "1.0", "end-1c")
            self.tag_add("unchanged", "1.0", "end-1c")
        return "break"

    def enter_roll(self, event):
        self["insertwidth"] = 0
        self.state = "rolling"
        self.minus, self.integer, self.fraction = self.format.break_up(self.formalized)
        self.quantity = self.integer if self.fraction == "" else self.integer + "." + self.fraction
        self.tag_remove("highlight", "1.0", "end")
        if event.keysym == "Left":
            self.selected = 0
            if self.minus == False:
                self.tag_remove("unchanged", "1.0", "1.1")
                self.tag_add("selected", "1.0", "1.1")
            else:
                self.tag_remove("unchanged", "1.1", "1.2")
                self.tag_add("selected", "1.1", "1.2")
        else:
            self.selected = len(self.quantity) - 1
            if self.minus == False:
                self.tag_remove("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
            else:
                self.tag_remove("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
        return "break"

    def break_up(self, quantity):
        split = quantity.split(".")
        if len(split) == 1:
            return split[0], ""
        else:
            return split[0], split[1]

    def roll(self, event):
        match event.keysym, self.minus:
            case "Up", False:
                if self.quantity[self.selected] != "9":
                    self.quantity = self.quantity[:self.selected] + str(int(self.quantity[self.selected]) + 1) + self.quantity[self.selected + 1:]
                    self.delete("1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.insert("1.%d"%(self.selected), self.quantity[self.selected])
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.integer, self.fraction = self.break_up(self.quantity)
                elif len(self.integer) < self.format.digits_limit[0] or any(x != "9" and x != "." for x in self.quantity[:self.selected]):
                    current = self.selected
                    while (self.quantity[current] == "9" or self.quantity[current] == ".") and current >= 0:
                        if self.quantity[current] == "9":
                            self.quantity = self.quantity[:current] + "0" + self.quantity[current + 1:]
                            self.delete("1.%d"%(current), "1.%d"%(current + 1))
                            self.insert("1.%d"%(current), "0")
                        current -= 1
                    if current < 0:
                        self.quantity = "1" + self.quantity
                        self.insert("1.0", "1")
                        self.selected += 1
                    else:
                        self.quantity = self.quantity[:current] + str(int(self.quantity[current]) + 1) + self.quantity[current + 1:]
                        self.delete("1.%d"%(current), "1.%d"%(current + 1))
                        self.insert("1.%d"%(current), self.quantity[current])
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.integer, self.fraction = self.break_up(self.quantity)
                text = self.get("1.0", "end-1c")
                self.result, self.value, self.formalized = self.format.match(text)
                self.report()
            case "Down", False:
                if self.quantity[self.selected] != "0":
                    self.quantity = self.quantity[:self.selected] + str(int(self.quantity[self.selected]) - 1) + self.quantity[self.selected + 1:]
                    self.delete("1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.insert("1.%d"%(self.selected), self.quantity[self.selected])
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.integer, self.fraction = self.break_up(self.quantity)
                elif self.selected != 0 and any(x != "0" and x != "." for x in self.quantity[:self.selected]):
                    current = self.selected
                    while self.quantity[current] == "0" or self.quantity[current] == ".":
                        if self.quantity[current] == "0":
                            self.quantity = self.quantity[:current] + "9" + self.quantity[current + 1:]
                            self.delete("1.%d"%(current), "1.%d"%(current + 1))
                            self.insert("1.%d"%(current), "9")
                        current -= 1
                    if current == 0 and self.quantity[0] == "1" and self.quantity[1] != ".":
                        self.quantity = self.quantity[1:]
                        self.delete("1.0")
                        self.selected -= 1
                    else:
                        self.quantity = self.quantity[:current] + str(int(self.quantity[current]) - 1) + self.quantity[current + 1:]
                        self.delete("1.%d"%(current), "1.%d"%(current + 1))
                        self.insert("1.%d"%(current), self.quantity[current])
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.integer, self.fraction = self.break_up(self.quantity)
                else:
                    self.minus = True
                    self.insert("1.0", "-")
                    if self.selected != len(self.quantity) - 1 and any(x != "0" and x != "." for x in self.quantity[self.selected + 1:]):
                        new_quantity = self.quantity[:self.selected + 1]
                        for i in range(self.selected + 1, len(self.quantity)):
                            if self.quantity[i] != ".":
                                if i == len(self.quantity) - 1 or all(x == "0" or x == "." for x in self.quantity[i + 1:]):
                                    new_quantity += str(10 - int(self.quantity[i]))
                                    for j in range(i + 1, len(self.quantity)):
                                        new_quantity += "0"
                                    break
                                else:
                                    new_quantity += str(9 - int(self.quantity[i]))
                            else:
                                new_quantity += "."
                        self.quantity = new_quantity
                    else:
                        self.quantity = self.quantity[:self.selected] + "1" + self.quantity[self.selected + 1:]
                    self.delete("1.1", "1.%d"%(len(self.quantity) + 1))
                    self.insert("1.1", self.quantity)
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.integer, self.fraction = self.break_up(self.quantity)
                text = self.get("1.0", "end-1c")
                self.result, self.value, self.formalized = self.format.match(text)
                self.report()
            case "Left", False:
                if self.selected > 0 and self.selected < len(self.quantity) - 1 or len(self.quantity) != 1 and self.selected == len(self.quantity) - 1 and (self.quantity[-1] != "0" or len(self.fraction) <= self.format.digits_limit[2]):
                    self.tag_remove("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.tag_add("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.selected -= 1
                    if self.quantity[self.selected] == ".":
                        self.selected -= 1
                    self.tag_remove("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                elif self.selected == 0 and self.format.digits_limit[0] > len(self.integer):
                    self.tag_remove("selected", "1.0", "1.1")
                    self.tag_add("unchanged", "1.0", "1.1")
                    self.quantity = "0" + self.quantity
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.insert("1.0", "0")
                    self.tag_add("selected", "1.0", "1.1")
                elif self.selected == len(self.quantity) - 1 and self.quantity[-1] == "0" and len(self.fraction) > self.format.digits_limit[2]:
                    self.quantity = self.quantity[:-1]
                    self.delete("1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.selected -= 1
                    if self.quantity[-1] == ".":
                        self.quantity = self.quantity[:-1]
                        self.delete("1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                        self.selected -= 1
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.tag_remove("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
            case "Right", False:
                if self.selected < len(self.quantity) - 1 and self.selected > 0 or len(self.quantity) != 1 and self.selected == 0 and (self.quantity[0] != "0" or self.integer == "0"):
                    self.tag_remove("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.tag_add("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.selected += 1
                    if self.quantity[self.selected] == ".":
                        self.selected += 1
                    self.tag_remove("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                elif self.selected == len(self.quantity) - 1 and self.format.digits_limit[1] > len(self.fraction):
                    self.tag_remove("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.tag_add("unchanged", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    if self.fraction == "":
                        self.quantity += "."
                        self.insert("1.%d"%(self.selected + 1), ".")
                        self.selected += 1
                    self.quantity += "0"
                    self.insert("1.%d"%(self.selected + 1), "0")
                    self.selected += 1
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                elif self.selected == 0 and self.quantity[0] == "0" and self.integer != "0":
                    self.quantity = self.quantity[1:]
                    self.delete("1.0", "1.1")
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.tag_remove("unchanged", "1.0", "1.1")
                    self.tag_add("selected", "1.0", "1.1")
            case "Up", True:
                if self.quantity[self.selected] != "0":
                    self.quantity = self.quantity[:self.selected] + str(int(self.quantity[self.selected]) - 1) + self.quantity[self.selected + 1:]
                    self.delete("1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.insert("1.%d"%(self.selected + 1), self.quantity[self.selected])
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.integer, self.fraction = self.break_up(self.quantity)
                    if all(x == "0" or x == "." for x in self.quantity):
                        self.minus = False
                        self.delete("1.0")  
                elif self.selected != 0 and any(x != "0" and x != "." for x in self.quantity[:self.selected]):
                    current = self.selected
                    while self.quantity[current] == "0" or self.quantity[current] == ".":
                        if self.quantity[current] == "0":
                            self.quantity = self.quantity[:current] + "9" + self.quantity[current + 1:]
                            self.delete("1.%d"%(current + 1), "1.%d"%(current + 2))
                            self.insert("1.%d"%(current + 1), "9")
                        current -= 1
                    if current == 0 and self.quantity[0] == "1" and self.quantity[1] != ".":
                        self.quantity = self.quantity[1:]
                        self.delete("1.1")
                        self.selected -= 1
                    else:
                        self.quantity = self.quantity[:current] + str(int(self.quantity[current]) - 1) + self.quantity[current + 1:]
                        self.delete("1.%d"%(current + 1), "1.%d"%(current + 2))
                        self.insert("1.%d"%(current + 1), self.quantity[current])
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.integer, self.fraction = self.break_up(self.quantity)
                else:
                    self.minus = False
                    self.delete("1.0")
                    if self.selected != len(self.quantity) - 1 and any(x != "0" and x != "." for x in self.quantity[self.selected + 1:]):
                        new_quantity = self.quantity[:self.selected + 1]
                        for i in range(self.selected + 1, len(self.quantity)):
                            if self.quantity[i] != ".":
                                if i == len(self.quantity) - 1 or all(x == "0" or x == "." for x in self.quantity[i + 1:]):
                                    new_quantity += str(10 - int(self.quantity[i]))
                                    for j in range(i + 1, len(self.quantity)):
                                        new_quantity += "0"
                                    break
                                else:
                                    new_quantity += str(9 - int(self.quantity[i]))
                            else:
                                new_quantity += "."
                        self.quantity = new_quantity
                    else:
                        self.quantity = self.quantity[:self.selected] + "1" + self.quantity[self.selected + 1:]
                    self.delete("1.0", "1.%d"%len(self.quantity))
                    self.insert("1.0", self.quantity)
                    self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
                    self.integer, self.fraction = self.break_up(self.quantity)
                text = self.get("1.0", "end-1c")
                self.result, self.value, self.formalized = self.format.match(text)
                self.report()
            case "Down", True:
                if self.quantity[self.selected] != "9":
                    self.quantity = self.quantity[:self.selected] + str(int(self.quantity[self.selected]) + 1) + self.quantity[self.selected + 1:]
                    self.delete("1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.insert("1.%d"%(self.selected + 1), self.quantity[self.selected])
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.integer, self.fraction = self.break_up(self.quantity)
                elif len(self.integer) < self.format.digits_limit[0] or any(x != "9" and x != "." for x in self.quantity[:self.selected]):
                    current = self.selected
                    while (self.quantity[current] == "9" or self.quantity[current] == ".") and current >= 0:
                        if self.quantity[current] == "9":
                            self.quantity = self.quantity[:current] + "0" + self.quantity[current + 1:]
                            self.delete("1.%d"%(current + 1), "1.%d"%(current + 2))
                            self.insert("1.%d"%(current + 1), "0")
                        current -= 1
                    if current < 0:
                        self.quantity = "1" + self.quantity
                        self.insert("1.1", "1")
                        self.selected += 1
                    else:
                        self.quantity = self.quantity[:current] + str(int(self.quantity[current]) + 1) + self.quantity[current + 1:]
                        self.delete("1.%d"%(current + 1), "1.%d"%(current + 2))
                        self.insert("1.%d"%(current + 1), self.quantity[current])
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.integer, self.fraction = self.break_up(self.quantity)
                text = self.get("1.0", "end-1c")
                self.result, self.value, self.formalized = self.format.match(text)
                self.report()
            case "Left", True:
                if self.selected > 0 and self.selected < len(self.quantity) - 1 or len(self.quantity) != 1 and self.selected == len(self.quantity) - 1 and (self.quantity[-1] != "0" or len(self.fraction) <= self.format.digits_limit[2]):
                    self.tag_remove("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.tag_add("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.selected -= 1
                    if self.quantity[self.selected] == ".":
                        self.selected -= 1
                    self.tag_remove("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                elif self.selected == 0 and self.format.digits_limit[0] > len(self.integer):
                    self.tag_remove("selected", "1.1", "1.2")
                    self.tag_add("unchanged", "1.1", "1.2")
                    self.quantity = "0" + self.quantity
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.insert("1.1", "0")
                    self.tag_add("selected", "1.1", "1.2")
                elif self.selected == len(self.quantity) - 1 and self.quantity[-1] == "0" and len(self.fraction) > self.format.digits_limit[2]:
                    self.quantity = self.quantity[:-1]
                    self.delete("1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.selected -= 1
                    if self.quantity[-1] == ".":
                        self.quantity = self.quantity[:-1]
                        self.delete("1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                        self.selected -= 1
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.tag_remove("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
            case "Right", True:
                if self.selected < len(self.quantity) - 1 and self.selected > 0 or len(self.quantity) != 1 and self.selected == 0 and (self.quantity[0] != "0" or self.integer == "0"):
                    self.tag_remove("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.tag_add("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.selected += 1
                    if self.quantity[self.selected] == ".":
                        self.selected += 1
                    self.tag_remove("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                elif self.selected == len(self.quantity) - 1 and self.format.digits_limit[1] > len(self.fraction):
                    self.tag_remove("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    self.tag_add("unchanged", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                    if self.fraction == "":
                        self.quantity += "."
                        self.insert("1.%d"%(self.selected + 2), ".")
                        self.selected += 1
                    self.quantity += "0"
                    self.insert("1.%d"%(self.selected + 2), "0")
                    self.selected += 1
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
                elif self.selected == 0 and self.quantity[0] == "0" and self.integer != "0":
                    self.quantity = self.quantity[1:]
                    self.delete("1.1", "1.2")
                    self.integer, self.fraction = self.break_up(self.quantity)
                    self.tag_remove("unchanged", "1.1", "1.2")
                    self.tag_add("selected", "1.1", "1.2")
        return "break"

    def overwrite(self, event):
        self.quantity = self.quantity[:self.selected] + event.char + self.quantity[self.selected + 1:]
        if self.minus == False:
            self.delete("1.%d"%(self.selected), "1.%d"%(self.selected + 1))
            self.insert("1.%d"%(self.selected), event.char)
        else:
            self.delete("1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
            self.insert("1.%d"%(self.selected + 1), event.char)
        if self.selected != len(self.quantity) - 1:
            self.selected += 1
            if self.quantity[self.selected] == ".":
                self.selected += 1
        elif len(self.fraction) == 0:
            self.quantity += ".0"
            self.insert("1.%d"%(self.selected + 1), ".0")
            self.selected += 2
        elif len(self.fraction) < self.format.digits_limit[1]:
            self.quantity += "0"
            self.insert("1.%d"%(self.selected + 1), "0")
            self.selected += 1
        if self.minus == False:
            self.tag_add("selected", "1.%d"%(self.selected), "1.%d"%(self.selected + 1))
        else:
            self.tag_add("selected", "1.%d"%(self.selected + 1), "1.%d"%(self.selected + 2))
        self.integer, self.fraction = self.break_up(self.quantity)
        self.result, self.value, self.formalized = self.format.match(self.get("1.0", "end-1c"))
        self.report()
        return "break"

    def exit_roll_key(self, event):
        self["insertwidth"] = 1
        self.state = "unchanged"
        self.tag_remove("selected", "1.0", "end-1c")
        self.tag_add("unchanged", "1.0", "end-1c")
        self.store()
        self.report()
        return "break"
    
    def exit_roll_button(self, event):
        self["insertwidth"] = 1
        self.state = "unchanged"
        self.tag_remove("selected", "1.0", "end-1c")
        self.tag_add("unchanged", "1.0", "end-1c")
        self.store()
        self.report()
        return

class WaveformDisplay(tk.Canvas):
    def __init__(self, master = None, waveform = [], periodic = False, prolong = True, horizontal_proportion = 0.6, vertical_proportion = 0.6, **kw):
        super().__init__(master, bg = "white", **kw)
        self.waveform = waveform
        self.periodic = periodic
        self.prolong = prolong
        self.enabled_segments = len(self.waveform)
        self.horizontal_proportion = horizontal_proportion
        self.vertical_proportion = vertical_proportion

    def scale(self, value, min, max, proportion):
        return (value - min) / (max - min) * proportion + (1 - proportion) / 2

    def draw(self):
        self.delete("all")
        if self.waveform == []:
            self.create_line(0, self.winfo_height() / 2, self.winfo_width(), self.winfo_height() / 2, fill = "black")
        else:
            try:
                #transform waveform into relative coordinates
                self.sequence = [(0, 0)]
                for segment in self.waveform[:self.enabled_segments]:
                    self.sequence.append((self.sequence[-1][0] + segment[0], self.sequence[-1][1] + segment[1]))
                points = [(self.scale(x, 0, self.sequence[-1][0], self.horizontal_proportion) * self.winfo_width(), (1 - self.scale(y, min([y for x, y in self.sequence]), max([y for x, y in self.sequence]), self.vertical_proportion)) * self.winfo_height()) for x, y in self.sequence]
            except ZeroDivisionError:
                # draw grid only
                for i in range(1, 10):
                    self.create_line(0, i / 10 * self.winfo_height(), self.winfo_width(), i / 10 * self.winfo_height(), fill = "#d3d3d3")
                    self.create_line(i / 10 * self.winfo_width(), 0, i / 10 * self.winfo_width(), self.winfo_height(), fill = "#d3d3d3")
                return False
            else:
                #draw grid
                for i in range(1, 10):
                    self.create_line(0, i / 10 * self.winfo_height(), self.winfo_width(), i / 10 * self.winfo_height(), fill = "#d3d3d3")
                    self.create_line(i / 10 * self.winfo_width(), 0, i / 10 * self.winfo_width(), self.winfo_height(), fill = "#d3d3d3")
                #draw waveform
                for i in range(len(points) - 1):
                    self.create_line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], fill = "black")
                    #enumerate the segments
                    if points[i + 1][0] - points[i][0] > 20:
                        self.create_text((points[i + 1][0] + points[i][0]) / 2, self.winfo_height() - 10, text = str(i + 1), fill = "#922B21")
                        self.create_oval((points[i + 1][0] + points[i][0]) / 2 - 6, self.winfo_height() - 4, (points[i + 1][0] + points[i][0]) / 2 + 6, self.winfo_height() - 16, fill = "", outline = "#922B21")
                for i in range(len(points)):
                    self.create_line(points[i][0], 0, points[i][0], self.winfo_height(), fill = "#922B21", dash = (4, 4))       
                self.create_line(0, (1 - self.vertical_proportion) / 2 * self.winfo_height(), self.winfo_width(), (1 - self.vertical_proportion) / 2 * self.winfo_height(), fill = "#922B21", dash = (4, 4))
                self.create_line(0, (1 + self.vertical_proportion) / 2 * self.winfo_height(), self.winfo_width(), (1 + self.vertical_proportion) / 2 * self.winfo_height(), fill = "#922B21", dash = (4, 4))
                match self.periodic, self.prolong:
                    case True, True:
                        translated_left = [(points[i][0] - self.winfo_width() * self.horizontal_proportion, points[i][1]) for i in range(len(points))]
                        translated_right = [(points[i][0] + self.winfo_width() * self.horizontal_proportion, points[i][1]) for i in range(len(points))]
                        step = points[0][1] - points[-1][1]
                        # extend waveform to the left
                        for i in range(len(points) - 1, -1, -1):
                            if translated_left[i][0] <= 0:
                                break
                            self.create_line(translated_left[i][0], translated_left[i][1] + step, translated_left[i - 1][0], translated_left[i - 1][1] + step, fill = "black")
                        # extend waveform to the right
                        for i in range(len(points)):
                            if translated_right[i][0] >= self.winfo_width():
                                break
                            self.create_line(translated_right[i][0], translated_right[i][1] - step, translated_right[i + 1][0], translated_right[i + 1][1] - step, fill = "black")
                    case True, False:
                        translated_left = [(points[i][0] - self.winfo_width() * self.horizontal_proportion, points[i][1]) for i in range(len(points))]
                        translated_right = [(points[i][0] + self.winfo_width() * self.horizontal_proportion, points[i][1]) for i in range(len(points))]
                        # extend waveform to the left
                        self.create_line(points[0][0], points[0][1], translated_left[-1][0], translated_left[-1][1], fill = "black")
                        for i in range(len(points) - 1, -1, -1):
                            if translated_left[i][0] <= 0:
                                break
                            self.create_line(translated_left[i][0], translated_left[i][1], translated_left[i - 1][0], translated_left[i - 1][1], fill = "black")
                        # extend waveform to the right
                        self.create_line(points[-1][0], points[-1][1], translated_right[0][0], translated_right[0][1], fill = "black")
                        for i in range(len(points)):
                            if translated_right[i][0] >= self.winfo_width():
                                break
                            self.create_line(translated_right[i][0], translated_right[i][1], translated_right[i + 1][0], translated_right[i + 1][1], fill = "black")
                    case False, True:
                        self.create_line(0, points[0][1], points[0][0], points[0][1], fill = "black")
                        self.create_line(points[-1][0], points[-1][1], self.winfo_width(), points[-1][1], fill = "black")
                    case False, False:
                        self.create_line(0, points[0][1], points[0][0], points[0][1], fill = "black")
                        self.create_line(points[-1][0], points[-1][1], points[-1][0], points[0][1], fill = "black")
                        self.create_line(points[-1][0], points[0][1], self.winfo_width(), points[0][1], fill = "black")
                return True

class WaveformControl(tk.Frame):
    def __init__(self, master = None, uploader = lambda x, y, z: None, launcher = lambda: None, terminator = lambda: None, **kw):
        super().__init__(master, height = 420, width = 872, relief = tk.GROOVE, borderwidth = 2, **kw)
        self.uploader = uploader
        self.launcher = launcher
        self.terminator = terminator
        
        # a combobox for selecting the number of segments, 8 * 2 QuanitityEntry for setting the segments, 4 buttons for periodic, prolong, uploading and initiating
        self.segments = ttk.Combobox(self, values = [str(i) for i in range(1, 9)], width = 5)
        self.segments.current(0)
        self.segments.place(x = 620, y = 14)
        
        self.state = "normal"
        self.periodic = False
        self.prolong = True
        self.uploaded = True
        self.periodically_running = False

        self.periodic_button = tk.Button(self, text = "Periodic", width = 32, relief = tk.RAISED, command = self.toggle_periodic)
        self.prolong_button = tk.Button(self, text = "Hold", width = 32, relief = tk.SUNKEN, command = self.toggle_prolong)
        self.upload_button = tk.Button(self, text = "Upload waveform", width = 32, relief = tk.SUNKEN, state = tk.DISABLED, command = self.upload_waveform)

        self.periodic_button.place(x = 620, y = 264)
        self.prolong_button.place(x = 620, y = 296)
        self.upload_button.place(x = 620, y = 328)

        self.initiate_button = tk.Button(self, text = "Initiate frequency control", width = 32, relief = tk.RAISED, command = self.handle_initiate)
        self.initiate_button.place(x = 620, y = 360)
        
        self.display = WaveformDisplay(self, height = 380, width = 550)
        self.display.place(x = 10, y = 10)
        
        x_format = QuantityFormat((6, 3, 0), {"m": 1e-3, "u": 1e-6}, "s")
        y_format = QuantityFormat((6, 3, 0), {"k": 1e3, "M": 1e6}, "Hz")
        self.x_entries = [QuantityEntry(self, x_format, lambda i = i: self.save_waveform("x" + str(i)), width = 10, font = ("Arial", 12)) for i in range(8)]
        self.y_entries = [QuantityEntry(self, y_format, lambda i = i: self.save_waveform("y" + str(i)), width = 10, font = ("Arial", 12)) for i in range(8)]
        for i in range(8):
            self.x_entries[i].place(x = 620, y = 42 + 28 * i)
            self.y_entries[i].place(x = 718, y = 42 + 28 * i)
            self.x_entries[i].set("0ms")
            self.y_entries[i].set("0MHz")
            self.x_entries[i].store()
            self.y_entries[i].store()

        self.scale_xmin = tk.Label(self, text = "", font = ("Arial", 12))
        self.scale_xmax = tk.Label(self, text = "", font = ("Arial", 12))
        self.scale_ymin = tk.Label(self, text = "", font = ("Arial", 12))
        self.scale_ymax = tk.Label(self, text = "", font = ("Arial", 12))

        self.scale_xmin.place(x = 120, y = 390, anchor = tk.N)
        self.scale_xmax.place(x = 452, y = 390, anchor = tk.N)
        self.scale_ymin.place(x = 563, y = 317, anchor = tk.W)
        self.scale_ymax.place(x = 563, y = 87, anchor = tk.W)

        self.after(100, self.save_all)
        
        self.bind("<<Destroy>>", self.destroy)

        self.destroying = False
        self.update_thread = threading.Thread(target = self.update, args = (), daemon = True)
        self.update_thread.start()

    def update(self):
        last_segments = 0
        last_state = {
            "state": self.state,
            "uploaded": self.uploaded,
            "periodically_running": self.periodically_running
        }
        while True:
            time.sleep(0.05)
            if self.destroying:
                return
            if self.segments.get() != last_segments:
                last_segments = self.segments.get()
                for i in range(8):
                    if i < int(last_segments):
                        self.x_entries[i]["state"] = tk.NORMAL
                        self.y_entries[i]["state"] = tk.NORMAL
                    else:
                        self.x_entries[i]["state"] = tk.DISABLED
                        self.y_entries[i]["state"] = tk.DISABLED
                self.display.enabled_segments = int(last_segments)
                self.draw()
            current_state = {
                "state": self.state,
                "uploaded": self.uploaded,
                "periodically_running": self.periodically_running
            }
            if current_state != last_state:
                last_state = current_state
                match (self.state, self.uploaded):
                    case "normal", False:
                        self.upload_button["state"] = tk.NORMAL
                        self.upload_button["relief"] = tk.RAISED
                    case "normal", True:
                        self.upload_button["state"] = tk.DISABLED
                        self.upload_button["relief"] = tk.SUNKEN
                    case "disabled", False:
                        self.upload_button["state"] = tk.DISABLED
                        self.upload_button["relief"] = tk.RAISED
                    case "disabled", True:
                        self.upload_button["state"] = tk.DISABLED
                        self.upload_button["relief"] = tk.SUNKEN
                match (self.state, self.periodically_running):
                    case "normal", True:
                        self.initiate_button["state"] = tk.NORMAL
                        self.initiate_button["relief"] = tk.SUNKEN
                        self.initiate_button["text"] = "Terminate frequency control"
                    case "normal", False:
                        self.initiate_button["state"] = tk.NORMAL
                        self.initiate_button["relief"] = tk.RAISED
                        self.initiate_button["text"] = "Initiate frequency control"
                    case "disabled", True:
                        self.initiate_button["state"] = tk.DISABLED
                        self.initiate_button["relief"] = tk.SUNKEN
                        self.initiate_button["text"] = "Terminate frequency control"
                    case "disabled", False:
                        self.initiate_button["state"] = tk.DISABLED
                        self.initiate_button["relief"] = tk.RAISED
                        self.initiate_button["text"] = "Initiate frequency control"

    def destroy(self):
        self.destroying = True
        for i in range(8):
            self.x_entries[i].destroy()
            self.y_entries[i].destroy()

    def draw(self):
        if self.display.draw():
            # label scales
            self.scale_xmin["text"] = "0ms"
            self.scale_xmax["text"] = "%d"%(max([x for x, y in self.display.sequence]) * 1e3) + "ms"
            self.scale_ymin["text"] = "%d"%(min([y for x, y in self.display.sequence]) * 1e-6) + "MHz"
            self.scale_ymax["text"] = "%d"%(max([y for x, y in self.display.sequence]) * 1e-6) + "MHz"
        else:
            self.scale_xmin["text"] = ""
            self.scale_xmax["text"] = ""
            self.scale_ymin["text"] = ""
            self.scale_ymax["text"] = ""

    def save_all(self):
        self.display.waveform = [[self.x_entries[i].get_value(), self.y_entries[i].get_value()] for i in range(8)]
        self.display.periodic = self.periodic
        self.display.prolong = self.prolong
        self.draw()

    def save_waveform(self, index):
        self.uploaded = False
        value = self.x_entries[int(index[1])].get_value() if index[0] == "x" else self.y_entries[int(index[1])].get_value()

        if index[0] == "x":
            self.display.waveform[int(index[1])][0] = value
        else:
            self.display.waveform[int(index[1])][1] = value
        self.draw()

    def toggle_periodic(self):
        self.uploaded = False

        if self.periodic == False:
            self.periodic = True
            self.periodic_button["relief"] = tk.SUNKEN
        else:
            self.periodic = False
            self.periodic_button["relief"] = tk.RAISED
        self.display.periodic = self.periodic
        self.draw()

    def toggle_prolong(self):
        self.uploaded = False

        if self.prolong == False:
            self.prolong = True
            self.prolong_button["relief"] = tk.SUNKEN
        else:
            self.prolong = False
            self.prolong_button["relief"] = tk.RAISED
        self.display.prolong = self.prolong
        self.draw()

    def upload_waveform(self):
        self.save_all()
        self.uploaded = True
        self.uploader(self.display.waveform[:self.display.enabled_segments], self.periodic, self.prolong)

    def handle_initiate(self):
        if self.periodically_running == True:
            self.periodically_running = False
            self.terminator()
        else:
            if self.periodic == True:
                self.periodically_running = True
            self.launcher()

def test():
    time.sleep(5)
    control.destroy()

def on_close():
    control.destroy()
    root.after(10, root.destroy)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x600")
    
    knob = KnobFrame(root, "icons/knob.png", 100, name = "Manual offset", scale = 0.334, unit = "mV", relief = tk.GROOVE, borderwidth = 2)
    knob.knob.value_step = 30
    knob.knob.on_spin = knob.update
    knob.knob.max = 32767
    knob.knob.min = -32767
    #knob.place(x = 50, y = 50)
    knob.update()
    
    knob.knob.step = 36
    knob.knob.resistance = 1.4
    knob.knob.lag = 0.65
    
    format = QuantityFormat((9, 0, 0), {}, "")
    entry = QuantityEntry(root, format, lambda x: print(x), width = 10, font = ("Arial", 12))
    #entry.place(x = 50, y = 50)

    display = WaveformDisplay(root, [(10, 10), (20, 0), (10, -10), (20, -10)], periodic = False, prolong = False, horizontal_proportion = 0.6, vertical_proportion = 0.6, width = 500, height = 400)
    #display.place(x = 50, y = 100)
    display.after(100, display.draw)
    

    control = WaveformControl(root, uploader = lambda x, y, z: print(x))
    control.place(x = 20, y = 20)
    
    thread = threading.Thread(target = test, args = (), daemon = True)
    #thread.start()

    root.protocol("WM_DELETE_WINDOW", on_close)  # Override close button
    root.mainloop()