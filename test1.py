# import matplotlib.pyplot as plt
# import numpy as np
# import pyqtgraph as pg

# # fig, ax = plt.subplots()
# # plt.ion()
# # plt.show()
# from PyQt5 import uic
# from PyQt5.QtWidgets import QApplication

# app = QApplication([])

# window = uic.loadUi("first.ui")
# window.show()
# window.widget.image()
# app.exec_()
# # try:
# #     while True:
# #         image = np.random.uniform(0, 255, (100, 100))
# #         if not ax.images:
# #             # If there's no existing image, create one
# #             img = ax.imshow(image, cmap='gray')
# #         else:
# #             # If an image already exists, update its data
# #             ax.images[0].set_array(image)

# #         fig.canvas.draw()
# #         plt.pause(1/1000)  # Add a short pause to allow the GUI to update
# # except KeyboardInterrupt:
# #     pass

# %%
import numpy as np
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MyWindow():
    def __init__(self):
        self.window = uic.loadUi("first.ui")
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        # self.window.widget.layout().addWidget(self.canvas)
        self.plot = self.window.widget.imageItem(image=np.random.normal(size=(100,100)))
        # self.update_plot()

        self.window.show()

    # def update_plot(self):
    #     image = np.random.uniform(0, 255, (100, 100))
    #     self.figure.clear()
    #     ax = self.figure.add_subplot(111)
    #     ax.imshow(image, cmap='gray')
    #     self.canvas.draw()

app = QApplication([])
my_window = MyWindow()
app.exec_()