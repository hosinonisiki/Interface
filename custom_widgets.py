import tkinter as tk
import tkinter.ttk as ttk

from PIL import Image, ImageTk

import numpy as np

import threading
import time

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

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("220x280")
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
    root.mainloop()