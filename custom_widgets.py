import tkinter as tk
import tkinter.ttk as ttk

from PIL import Image, ImageTk

import numpy as np

import threading
import time

class UnclampingKnob(tk.Canvas):
    def __init__(self, image_path, size, value_step, master = None, step = 36, resistance = 1.5, value = 0, **kw):
        super().__init__(master, width = size + 2, height = size + 2, **kw)
        self.image = Image.open(image_path)
        self.size = size
        self.value_step = value_step
        self.step = step
        self.resistance = resistance
        self.value = value
        self.bind("<Button-1>", self.hold)
        self.bind("<B1-Motion>", self.spin)
        self.bind("<ButtonRelease-1>", self.release)
        self.knob_angle = 0

    def set_value(self, value):
        self.value = value
    
    def get_value(self):
        return self.value

    def draw(self):
        #self.delete("all")
        self.image_tk = ImageTk.PhotoImage(self.image.rotate(-self.knob_angle))
        self.create_image(self.size / 2 + 2, self.size / 2 + 2, image = self.image_tk, anchor = "c")

    def hold(self, event):
        self.start = event.x
        self.starting_angle = self.knob_angle

    def spin(self, event):
        self.angle = self.starting_angle + (event.x - self.start) / self.resistance
        if np.abs(self.angle - self.knob_angle) >= self.step:
            if self.angle - self.knob_angle > 0:
                direction = 1
            else:
                direction = -1
            rotate_thread = threading.Thread(target = self.rotate_one_step, args = [direction])
            rotate_thread.start()

    def rotate_one_step(self, direction):
        if direction == 1:
            self.value += self.value_step
            self.knob_angle += (self.step - 0.5)
            self.draw()
            time.sleep(0.05)
            self.knob_angle += 0.5
            self.draw()
        else:
            self.value -= self.value_step
            self.knob_angle -= (self.step - 0.5)
            self.draw()
            time.sleep(0.05)
            self.knob_angle -= 0.5
            self.draw()

    def release(self, event):
        pass

if __name__ == "__main__":
    root = tk.Tk("200x200")
    knob = UnclampingKnob("icons/knob.png", 100, root)
    knob.place(x = 50, y = 50)
    knob.draw()
    root.mainloop()