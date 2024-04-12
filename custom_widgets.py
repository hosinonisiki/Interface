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
        self.re = re.compile("^([-])?([0-9]{1,%d})(\.[0-9]{0,%d})?([%s])?(%s)?$"%(digits_limit[0], digits_limit[1], "".join(self.prefix.keys()), unit))     

    def match(self, str):
        result = self.re.match(str)
        if result == None:
            return None, None
        if result.group(3) == None:
            value = float(result.group(2))
        else:
            value = float(result.group(2) + result.group(3))
        if result.group(4) == None:
            return result, value
        else:
            return result, value * self.prefix[result.group(4)]

class QuantityEntry(tk.Text):
    def __init__(self, master = None, format = QuantityFormat(), report = lambda x: None, **kw):
        super().__init__(master, wrap = tk.NONE, **kw)
        self.format = format
        self.report = report
        self.stored = ""
        self.state = "changed"
        self.result = None
        self.value = None

        self.bind("<Key>", self.handle_key)
        self.bind("<Button-1>", self.handle_button)
        self.bind("<<Selection>>", self.handle_selection)
        self.bind("<<Destroy>>", self.handle_destroy)
    
        self.destroying = False
        self.check_thread = threading.Thread(target = self.check, args = (), daemon = True)
        self.check_thread.start()

        self.tag_config("unchanged", background = "white")
        self.tag_config("changed", background = "yellow")
        self.tag_config("selected", background = "black", foreground = "white")
        self.tag_config("highlight", background = "blue", foreground = "white")

    def set(self, str):
        self.delete("1.0", "end-1c")
        self.insert("1.0", str)
        self.store()

    def check(self):
        while self.destroying == False:
            time.sleep(0.05)
            if self.state == "unchanged" and self.get("1.0", "end-1c") != self.stored:
                self.state = "changed"
                self.tag_remove("unchanged", "1.0", "end-1c")
            if self.state == "changed":
                self.tag_add("changed", "1.0", "end-1c")
             
    def handle_key(self, event):
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
                return self.overwrite(event)
            case _:
                return "break"
            
    def handle_button(self, event):
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
        match self.state:
            case "unchanged":
                self.tag_remove("highlight", "1.0", "end")
                try:
                    start = self.index("sel.first")
                    end = self.index("sel.last")
                    self.tag_add("highlight", start, end)
                except:
                    pass
            case "changed":
                self.tag_remove("highlight", "1.0", "end")
                try:
                    start = self.index("sel.first")
                    end = self.index("sel.last")
                    self.tag_add("highlight", start, end)
                except:
                    pass
            case "rolling":
                return
            
    def handle_destroy(self, event):
        self.destroying = True
        self.check_thread.join()

    def store(self):
        text = self.get("1.0", "end-1c")
        self.result, self.value = self.format.match(text)
        if self.result != None:
            formalize = "" if self.result.group(1) == None else "-"
            formalize += self.result.group(2)
            if self.result.group(3) == None:
                formalize += "." + "0" * self.format.digits_limit[2]
            elif len(self.result.group(3)) < self.format.digits_limit[2] + 1:
                formalize += self.result.group(3) + "0" * (self.format.digits_limit[2] - len(self.result.group(3)) + 1)
            formalize += "" if self.result.group(4) == None else self.result.group(4)
            formalize += self.format.unit
            self.result, self.value = self.format.match(formalize)
            self.delete("1.0", "end-1c")
            self.insert("1.0", formalize)
            self.stored = formalize
            self.state = "unchanged"
            self.tag_remove("changed", "1.0", "end-1c")
            self.tag_add("unchanged", "1.0", "end-1c")
            self.report(self.value)
        return "break"

    def enter_roll(self, event):
        self["insertwidth"] = 0
        self.state = "rolling"
        self.minus = False if self.result.group(1) == None else True
        self.integer = self.result.group(2)
        self.fraction = "" if self.result.group(3) == None else self.result.group(3)[1:]
        self.quantity = self.integer if self.fraction == "" else self.integer + "." + self.fraction
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
                self.report(self.format.match(self.get("1.0", "end-1c"))[1])
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
                    if current == 0 and self.quantity[current] == "1":
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
                self.report(self.format.match(self.get("1.0", "end-1c"))[1])
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
                self.report(self.format.match(self.get("1.0", "end-1c"))[1])
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
                self.report(self.format.match(self.get("1.0", "end-1c"))[1])
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
        self.report(self.format.match(self.get("1.0", "end-1c"))[1])
        return "break"

    def exit_roll_key(self, event):
        self["insertwidth"] = 1
        self.state = "unchanged"
        self.tag_remove("selected", "1.0", "end-1c")
        self.tag_add("unchanged", "1.0", "end-1c")
        self.store()
        return "break"
    
    def exit_roll_button(self, event):
        self["insertwidth"] = 1
        self.state = "unchanged"
        self.tag_remove("selected", "1.0", "end-1c")
        self.tag_add("unchanged", "1.0", "end-1c")
        self.store()
        return

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("220x280")
    '''
    knob = KnobFrame(root, "icons/knob.png", 100, name = "Manual offset", scale = 0.334, unit = "mV", relief = tk.GROOVE, borderwidth = 2)
    knob.knob.value_step = 30
    knob.knob.on_spin = knob.update
    knob.knob.max = 32767
    knob.knob.min = -32767
    knob.place(x = 50, y = 50)
    knob.update()
    
    knob.knob.step = 36
    knob.knob.resistance = 1.4
    knob.knob.lag = 0.65
    '''
    format = QuantityFormat((5,5,3), unit = "V")
    entry = QuantityEntry(root, format, lambda x: print(x), width = 10, height = 1, font = ("Arial", 12))
    entry.place(x = 50, y = 50)

    root.mainloop()