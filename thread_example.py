# %%
# import sys
# from PyQt5.QtCore import Qt, QThread, pyqtSignal
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# import matplotlib.pyplot as plt
# import numpy as np

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             while not self.isInterruptionRequested():
#                 image = np.random.uniform(0, 255, (100, 100))
#                 self.update_signal.emit(image)
#                 self.msleep(100)  # Add a short pause to allow the GUI to update
#         except KeyboardInterrupt:
#             pass

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.initUI()

#     def initUI(self):
#         self.fig, self.ax = plt.subplots()
#         plt.ion()
#         self.canvas = FigureCanvas(self.fig)

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         layout = QVBoxLayout()
#         layout.addWidget(self.canvas)
#         layout.addWidget(self.start_button)
#         layout.addWidget(self.stop_button)

#         self.setLayout(layout)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.setGeometry(100, 100, 800, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def update_image(self, image):
#         if not self.ax.images:
#             img = self.ax.imshow(image, cmap='gray')
#         else:
#             self.ax.images[0].set_array(image)

#         self.fig.canvas.draw()

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())
# %%
# import sys
# from PyQt5.QtCore import QThread, pyqtSignal
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
# from PyQt5.QtWidgets import QSizePolicy
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure
# import matplotlib.pyplot as plt
# import numpy as np

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             while not self.isInterruptionRequested():
#                 image = np.random.uniform(0, 255, (100, 100))
#                 self.update_signal.emit(image)
#                 self.msleep(500)  # Add a short pause to allow the GUI to update
#         except KeyboardInterrupt:
#             pass

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.initUI()

#     def initUI(self):
#         self.fig, (self.ax_image, self.ax_xprofile, self.ax_yprofile) = plt.subplots(1, 3, figsize=(12, 4))
#         self.canvas = FigureCanvas(self.fig)

#         self.canvas.mpl_connect('button_press_event', self.on_click)

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         layout = QVBoxLayout()
#         layout.addWidget(self.canvas)

#         layout_buttons = QVBoxLayout()
#         layout_buttons.addWidget(self.start_button)
#         layout_buttons.addWidget(self.stop_button)

#         main_layout = QVBoxLayout()
#         main_layout.addLayout(layout)
#         main_layout.addLayout(layout_buttons)

#         self.setLayout(main_layout)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.setGeometry(100, 100, 1200, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def update_image(self, image):
#         self.ax_image.clear()
#         self.ax_xprofile.clear()
#         self.ax_yprofile.clear()

#         img = self.ax_image.imshow(image, cmap='gray')
#         self.ax_xprofile.plot(img.get_array()[0, :], label='X profile')
#         self.ax_yprofile.plot(img.get_array()[:, 0], label='Y profile')

#         self.ax_image.set_xlabel('X')
#         self.ax_image.set_ylabel('Y')

#         self.ax_xprofile.set_xlabel('X')
#         self.ax_xprofile.set_ylabel('Intensity')

#         self.ax_yprofile.set_xlabel('Y')
#         self.ax_yprofile.set_ylabel('Intensity')

#         # add grid for the line profile plots
#         self.ax_xprofile.grid()
#         self.ax_yprofile.grid()

#         self.ax_image.legend()
#         self.ax_xprofile.legend()
#         self.ax_yprofile.legend()

#         self.fig.canvas.draw()

#     def on_click(self, event):
#         if event.inaxes == self.ax_image:
#             x, y = int(event.xdata), int(event.ydata)
#             self.update_line_profiles(x, y)

#     def update_line_profiles(self, x, y):
#         img = self.ax_image.images[0].get_array()
#         self.ax_xprofile.plot(img[x, :], label='X profile')
#         self.ax_yprofile.plot(img[:, y], label='Y profile')
#         self.fig.canvas.draw()

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())
# %%
# import sys
# import pyqtgraph as pg
# from PyQt5.QtCore import Qt, QThread, pyqtSignal
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
# from pyqtgraph.Qt import QtCore, QtGui
# import numpy as np

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             while not self.isInterruptionRequested():
#                 image = np.random.uniform(0, 255, (100, 100))
#                 self.update_signal.emit(image)
#                 self.msleep(50)  # Add a short pause to allow the GUI to update
#         except KeyboardInterrupt:
#             pass

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.initUI()

#     def initUI(self):
#         self.image_view = pg.ImageView()
#         self.xprofile_plot = pg.PlotWidget()
#         self.yprofile_plot = pg.PlotWidget()

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         layout = QVBoxLayout()
#         layout.addWidget(self.image_view)
        
#         profiles_layout = QVBoxLayout()
#         profiles_layout.addWidget(self.xprofile_plot)
#         profiles_layout.addWidget(self.yprofile_plot)

#         layout.addLayout(profiles_layout)
#         layout.addWidget(self.start_button)
#         layout.addWidget(self.stop_button)

#         self.setLayout(layout)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.setGeometry(100, 100, 1200, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def update_image(self, image):
#         self.image_view.setImage(image)
#         x_profile = image[0, :]
#         y_profile = image[:, 0]

#         self.xprofile_plot.clear()
#         self.yprofile_plot.clear()

#         self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
#         self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())
# %%
# import sys
# import pyqtgraph as pg
# from PyQt5.QtCore import QThread, pyqtSignal
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
# import numpy as np
# from scipy.stats import multivariate_normal

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             while not self.isInterruptionRequested():
#                 mean = np.random.uniform(25, 75, 2)  # Randomly change the mean
#                 cov = [[100, 0], [0, 100]]  # Covariance matrix (adjust as needed)
#                 gaussian = multivariate_normal(mean=mean, cov=cov)

#                 x, y = np.meshgrid(np.arange(100), np.arange(100))
#                 positions = np.column_stack((x.ravel(), y.ravel()))
#                 image = gaussian.pdf(positions).reshape(100, 100)

#                 self.update_signal.emit(image)
#                 self.msleep(50)  # Updated sleep time to 50 milliseconds
#         except KeyboardInterrupt:
#             pass

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.initUI()

#     def initUI(self):
#         self.image_view = pg.ImageView()
#         self.xprofile_plot = pg.PlotWidget()
#         self.yprofile_plot = pg.PlotWidget()

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         layout = QHBoxLayout()

#         left_layout = QVBoxLayout()
#         left_layout.addWidget(self.image_view)

#         right_layout = QVBoxLayout()
#         right_layout.addWidget(self.xprofile_plot)
#         right_layout.addWidget(self.yprofile_plot)

#         layout.addLayout(left_layout, 2)  # Left side (2 parts)
#         layout.addLayout(right_layout, 1)  # Right side (1 part)

#         buttons_layout = QVBoxLayout()
#         buttons_layout.addWidget(self.start_button)
#         buttons_layout.addWidget(self.stop_button)

#         main_layout = QHBoxLayout()
#         main_layout.addLayout(layout)
#         main_layout.addLayout(buttons_layout)

#         self.setLayout(main_layout)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.setGeometry(100, 100, 1200, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def update_image(self, image):
#         self.image_view.setImage(image)
#         x_profile = image[0, :]
#         y_profile = image[:, 0]

#         self.xprofile_plot.clear()
#         self.yprofile_plot.clear()

#         x_curve = self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
#         y_curve = self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')

#         # Add grid lines to the line profiles
#         self.xprofile_plot.showGrid(x=True, y=True)
#         self.yprofile_plot.showGrid(x=True, y=True)

#         # Increase the fontsize of x and y ticks
#         styles = {'color': '#ffffff', 'font-size': '12pt'}
#         self.xprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.xprofile_plot.setLabel('bottom', 'X', **styles)
#         self.yprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.yprofile_plot.setLabel('bottom', 'Y', **styles)

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())

# %% Working perfectly
# import sys
# import pyqtgraph as pg
# from PyQt5.QtCore import QThread, pyqtSignal, Qt
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit
# import numpy as np
# from scipy.stats import multivariate_normal
# from pyqtgraph.colormap import getFromMatplotlib

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             while not self.isInterruptionRequested():
#                 means = np.random.uniform(10, 90, (4, 2))
#                 sigmas = np.random.uniform(5, 75, 4)

#                 x, y = np.meshgrid(np.arange(100), np.arange(100))
#                 positions = np.column_stack((x.ravel(), y.ravel()))

#                 image = np.sum([multivariate_normal(mean=mean, cov=np.diag([sigma, sigma])).pdf(positions)
#                                 for mean, sigma in zip(means, sigmas)], axis=0)
#                 image = image.reshape(100, 100)
#                 # rescale images to 0-255
#                 image = (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
#                 self.update_signal.emit(image)
#                 self.msleep(50)  # Updated sleep time to 50 milliseconds
#         except KeyboardInterrupt:
#             pass

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.image_view = pg.ImageView(view=pg.PlotItem())
#         self.xprofile_plot = pg.PlotWidget()
#         self.yprofile_plot = pg.PlotWidget()

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         self.current_x = 0
#         self.current_y = 0

#         self.x_label = QLabel('X:')
#         self.y_label = QLabel('Y:')
#         self.x_textbox = QLineEdit(self)
#         self.y_textbox = QLineEdit(self)

#         # Set maximum width for textboxes
#         self.x_textbox.setMaximumWidth(50)
#         self.y_textbox.setMaximumWidth(50)

#         layout = QHBoxLayout()

#         left_layout = QVBoxLayout()
#         left_layout.addWidget(self.image_view)

#         right_layout = QVBoxLayout()
#         right_layout.addWidget(self.xprofile_plot)
#         right_layout.addWidget(self.yprofile_plot)

#         layout.addLayout(left_layout, 2)  # Left side (2 parts)
#         layout.addLayout(right_layout, 1)  # Right side (1 part)

#         buttons_layout = QVBoxLayout()
#         buttons_layout.addWidget(self.start_button)
#         buttons_layout.addWidget(self.stop_button)

#         labels_layout = QVBoxLayout()
#         labels_layout.addWidget(self.x_label)
#         labels_layout.addWidget(self.x_textbox)
#         labels_layout.addWidget(self.y_label)
#         labels_layout.addWidget(self.y_textbox)

#         main_layout = QHBoxLayout()
#         main_layout.addLayout(layout)
#         main_layout.addLayout(buttons_layout)
#         main_layout.addLayout(labels_layout)

#         self.setLayout(main_layout)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.image_view.ui.menuBtn.hide()  # Hide the menu button
#         self.image_view.getView().setMenuEnabled(False)  # Disable the context menu
#         # disable ROI button
#         self.image_view.ui.roiBtn.hide()
        

#         self.image_view.getView().scene().sigMouseClicked.connect(self.image_clicked)

#         self.setGeometry(100, 100, 1200, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def update_image(self, image):
#         self.image_view.setImage(image)
#         x_profile = image[self.current_y, :]
#         y_profile = image[:, self.current_x]

#         self.xprofile_plot.clear()
#         self.yprofile_plot.clear()

#         x_curve = self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
#         y_curve = self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')
#         # Set y limit to 255 for the line profile plots
#         self.yprofile_plot.setYRange(0, 255)
#         self.xprofile_plot.setYRange(0, 255)
#         # Add grid lines to the line profiles
#         self.xprofile_plot.showGrid(x=True, y=True)
#         self.yprofile_plot.showGrid(x=True, y=True)

#         # Increase the fontsize of x and y ticks
#         styles = {'color': '#ffffff', 'font-size': '12pt'}
#         self.xprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.xprofile_plot.setLabel('bottom', 'X', **styles)
#         self.yprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.yprofile_plot.setLabel('bottom', 'Y', **styles)

#         # Update the textboxes with current (x, y) location
#         self.x_textbox.setText(str(self.current_x))
#         self.y_textbox.setText(str(self.current_y))


#     def image_clicked(self, event):
#         pos = event.pos()
#         clicked_point = self.image_view.getImageItem().mapFromScene(pos)
#         self.current_x = int(clicked_point.x())
#         self.current_y = int(clicked_point.y())
#         self.update_image(self.image_view.getImageItem().image)

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())

# %%
# import sys
# import pyqtgraph as pg
# from PyQt5.QtCore import QThread, pyqtSignal
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit
# import numpy as np
# from scipy.stats import multivariate_normal

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             while not self.isInterruptionRequested():
#                 means = np.random.uniform(10, 90, (4, 2))
#                 sigmas = np.random.uniform(5, 75, 4)

#                 x, y = np.meshgrid(np.arange(100), np.arange(100))
#                 positions = np.column_stack((x.ravel(), y.ravel()))

#                 image = np.sum([multivariate_normal(mean=mean, cov=np.diag([sigma, sigma])).pdf(positions)
#                                 for mean, sigma in zip(means, sigmas)], axis=0)
#                 image = image.reshape(100, 100)
#                 # rescale images to 0-255
#                 image = (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
#                 self.update_signal.emit(image)
#                 self.msleep(500)  # Updated sleep time to 500 milliseconds
#         except KeyboardInterrupt:
#             pass

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.image_view = pg.ImageView(view=pg.PlotItem())
#         self.xprofile_plot = pg.PlotWidget()
#         self.yprofile_plot = pg.PlotWidget()

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         self.find_sum_button = QPushButton('Find Sum', self)
#         self.find_sum_button.clicked.connect(self.find_sum)

#         self.x_label = QLabel('X:')
#         self.x_textbox = QLineEdit(self)
#         self.x_textbox.setReadOnly(True)

#         self.y_label = QLabel('Y:')
#         self.y_textbox = QLineEdit(self)
#         self.y_textbox.setReadOnly(True)

#         self.roi_label = QLabel('ROI Sum:')
#         self.roi_textbox = QLineEdit(self)
#         self.roi_textbox.setReadOnly(True)

#         # Set maximum width for textboxes
#         self.roi_textbox.setMaximumWidth(50)
#         self.x_textbox.setMaximumWidth(50)
#         self.y_textbox.setMaximumWidth(50)

#         layout = QHBoxLayout()

#         left_layout = QVBoxLayout()
#         left_layout.addWidget(self.image_view)

#         right_layout = QVBoxLayout()
#         right_layout.addWidget(self.xprofile_plot)
#         right_layout.addWidget(self.yprofile_plot)

#         layout.addLayout(left_layout, 2)  # Left side (2 parts)
#         layout.addLayout(right_layout, 1)  # Right side (1 part)

#         buttons_layout = QVBoxLayout()
#         buttons_layout.addWidget(self.start_button)
#         buttons_layout.addWidget(self.stop_button)
#         buttons_layout.addWidget(self.find_sum_button)

#         labels_layout = QVBoxLayout()
#         labels_layout.addWidget(self.x_label)
#         labels_layout.addWidget(self.x_textbox)
#         labels_layout.addWidget(self.y_label)
#         labels_layout.addWidget(self.y_textbox)
#         labels_layout.addWidget(self.roi_label)
#         labels_layout.addWidget(self.roi_textbox)

#         main_layout = QHBoxLayout()
#         main_layout.addLayout(layout)
#         main_layout.addLayout(buttons_layout)
#         main_layout.addLayout(labels_layout)

#         self.setLayout(main_layout)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.image_view.getView().scene().sigMouseClicked.connect(self.image_clicked)

#         # Set initial color map
#         self.image_view.setColorMap(pg.ColorMap(pos=[0, 0.5, 1], color=[(0, 0, 0), (255, 255, 255), (0, 0, 0)]))

#         # Create CircleROI
#         self.roi = pg.CircleROI([50, 50], [20, 20], pen=(0, 9))  # Initial circular ROI

#         # Add the ROI to the same scene as the image
#         self.image_view.getView().addItem(self.roi)

#         self.setGeometry(100, 100, 1200, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def update_image(self, image):
#         self.image_view.setImage(image)
#         x_profile = image[self.current_y, :]
#         y_profile = image[:, self.current_x]

#         self.xprofile_plot.clear()
#         self.yprofile_plot.clear()

#         x_curve = self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
#         y_curve = self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')

#         # Set y limit to 255 for the line profile plots
#         self.yprofile_plot.setYRange(0, 255)
#         self.xprofile_plot.setYRange(0, 255)

#         # Add grid lines to the line profiles
#         self.xprofile_plot.showGrid(x=True, y=True)
#         self.yprofile_plot.showGrid(x=True, y=True)

#         # Increase the fontsize of x and y ticks
#         styles = {'color': '#ffffff', 'font-size': '12pt'}
#         self.xprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.xprofile_plot.setLabel('bottom', 'X', **styles)
#         self.yprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.yprofile_plot.setLabel('bottom', 'Y', **styles)

#         # Update the textboxes with current (x, y) location
#         self.x_textbox.setText(str(self.current_x))
#         self.y_textbox.setText(str(self.current_y))
        

#     def image_clicked(self, event):
#         pos = event.pos()
#         clicked_point = self.image_view.getImageItem().mapFromScene(pos)
#         self.current_x = int(clicked_point.x())
#         self.current_y = int(clicked_point.y())
#         self.update_image(self.image_view.getImageItem().image)

#     def find_sum(self):
#         # Get the region inside the ROI using the CircleROI's getArrayRegion method
#         roi_region = self.roi.getArrayRegion(self.image_view.getImageItem().image,
#                                             self.image_view.getImageItem(),
#                                             axes=(0, 1),
#                                             returnMappedCoords=False)

#         roi_sum = np.round(np.sum(roi_region),2)
#         self.roi_textbox.setText(str(roi_sum))


# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())
# %%
import sys
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit
import numpy as np
from scipy.stats import multivariate_normal
# import and supress warnings
import warnings
warnings.filterwarnings("ignore")

class ImageThread(QThread):
    update_signal = pyqtSignal(np.ndarray)

    def run(self):
        try:
            time = 0
            while not self.isInterruptionRequested():
                means = np.random.uniform(10, 90, (10, 2))
                sigmas = np.random.uniform(5, 75, 10)

                x, y = np.meshgrid(np.arange(100), np.arange(100))
                positions = np.column_stack((x.ravel(), y.ravel()))

                image = np.sum([multivariate_normal(mean=mean, cov=np.diag([sigma, sigma])).pdf(positions)
                                for mean, sigma in zip(means, sigmas)], axis=0)
                image = image.reshape(100, 100)
                # rescale images to 0-255
                image = (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
                self.update_signal.emit(image)
                time += 1
                self.msleep(50)  # Updated sleep time to 500 milliseconds
        except KeyboardInterrupt:
            pass

class GUI(QWidget):
    def __init__(self):
        super().__init__()

        self.image_view = pg.ImageView(view=pg.PlotItem())
        self.xprofile_plot = pg.PlotWidget()
        self.yprofile_plot = pg.PlotWidget()
        self.sum_plot = pg.PlotWidget()

        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.start_thread)

        self.stop_button = QPushButton('Stop', self)
        self.stop_button.clicked.connect(self.stop_thread)

        self.clear_roi_button = QPushButton('Clear ROI Plot', self)
        self.clear_roi_button.clicked.connect(self.clear_roi_plot)

        self.x_label = QLabel('X:')
        self.x_textbox = QLineEdit(self)
        self.x_textbox.setReadOnly(True)

        self.y_label = QLabel('Y:')
        self.y_textbox = QLineEdit(self)
        self.y_textbox.setReadOnly(True)

        self.roi_label = QLabel('ROI Sum:')
        self.roi_textbox = QLineEdit(self)
        self.roi_textbox.setReadOnly(True)

        # Set maximum width for textboxes
        self.roi_textbox.setMaximumWidth(50)
        self.x_textbox.setMaximumWidth(50)
        self.y_textbox.setMaximumWidth(50)

        layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.image_view, 7)  # Allocate 70% of the space
        left_layout.addWidget(self.sum_plot, 3)  # Allocate 30% of the space

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.xprofile_plot)
        right_layout.addWidget(self.yprofile_plot)

        layout.addLayout(left_layout, 2)  # Left side (2 parts)
        layout.addLayout(right_layout, 1)  # Right side (1 part)

        buttons_layout = QVBoxLayout()
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.clear_roi_button)

        labels_layout = QVBoxLayout()
        labels_layout.addWidget(self.x_label)
        labels_layout.addWidget(self.x_textbox)
        labels_layout.addWidget(self.y_label)
        labels_layout.addWidget(self.y_textbox)
        labels_layout.addWidget(self.roi_label)
        labels_layout.addWidget(self.roi_textbox)

        main_layout = QHBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(buttons_layout)
        main_layout.addLayout(labels_layout)

        self.setLayout(main_layout)

        self.image_thread = ImageThread()
        self.image_thread.update_signal.connect(self.update_image)

        self.image_view.getView().scene().sigMouseClicked.connect(self.image_clicked)

        # Set initial color map
        self.image_view.setColorMap(pg.ColorMap(pos=[0, 0.5, 1], color=[(0, 0, 0), (255, 255, 255), (0, 0, 0)]))

        # Create CircleROI
        self.roi = pg.CircleROI([50, 50], [20, 20], pen=(0, 9))  # Initial circular ROI

        # Add the ROI to the same scene as the image
        self.image_view.getView().addItem(self.roi)

        self.sum_data = []
        self.current_x = 0
        self.current_y = 0

        self.setGeometry(100, 100, 1200, 600)
        self.setWindowTitle('Image Rendering GUI')
        self.show()

    def start_thread(self):
        self.image_thread.start()

    def stop_thread(self):
        self.image_thread.requestInterruption()

    def update_image(self, image):
        self.image_view.setImage(image)
        x_profile = image[self.current_y, :]
        y_profile = image[:, self.current_x]

        self.xprofile_plot.clear()
        self.yprofile_plot.clear()

        x_curve = self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
        y_curve = self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')

        # Set y limit to 255 for the line profile plots
        self.yprofile_plot.setYRange(0, 255)
        self.xprofile_plot.setYRange(0, 255)

        # Add grid lines to the line profiles
        self.xprofile_plot.showGrid(x=True, y=True)
        self.yprofile_plot.showGrid(x=True, y=True)


        # Increase the fontsize of x and y ticks
        styles = {'color': '#ffffff', 'font-size': '12pt'}
        self.xprofile_plot.setLabel('left', 'Intensity', **styles)
        self.xprofile_plot.setLabel('bottom', 'X', **styles)
        self.yprofile_plot.setLabel('left', 'Intensity', **styles)
        self.yprofile_plot.setLabel('bottom', 'Y', **styles)

        # Update the textboxes with current (x, y) location
        self.x_textbox.setText(str(self.current_x))
        self.y_textbox.setText(str(self.current_y))

        # Get the region inside the ROI using the CircleROI's getArrayRegion method
        roi_region = self.roi.getArrayRegion(image,
                                            self.image_view.getImageItem(),
                                            axes=(0, 1),
                                            returnMappedCoords=False)

        roi_sum = np.sum(roi_region)
        self.roi_textbox.setText(str(roi_sum))

        # Update the sum plot with the sum inside ROI as a function of time
        self.sum_data.append((len(self.sum_data), roi_sum))
        self.sum_plot.clear()
        self.sum_plot.plot([item[0] for item in self.sum_data], [item[1] for item in self.sum_data], pen='y')
        self.sum_plot.setLabel('left', 'Sum Inside ROI', **styles)
        self.sum_plot.setLabel('bottom', 'Step', **styles)
        self.sum_plot.showGrid(x=True, y=True)


    def image_clicked(self, event):
        pos = event.pos()
        clicked_point = self.image_view.getImageItem().mapFromScene(pos)
        self.current_x = int(clicked_point.x())
        self.current_y = int(clicked_point.y())
        self.update_image(self.image_view.getImageItem().image)

    def clear_roi_plot(self):
        self.sum_data = []
        self.sum_plot.clear()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = GUI()
    sys.exit(app.exec_())
# %%
# import sys
# import cv2
# import numpy as np
# import pyqtgraph as pg
# from PyQt5.QtCore import QThread, pyqtSignal, Qt
# from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog
# from scipy.stats import multivariate_normal

# class ImageThread(QThread):
#     update_signal = pyqtSignal(np.ndarray)

#     def run(self):
#         try:
#             time = 0
#             while not self.isInterruptionRequested():
#                 means = np.random.uniform(10, 90, (10, 2))
#                 sigmas = np.random.uniform(5, 75, 10)

#                 x, y = np.meshgrid(np.arange(100), np.arange(100))
#                 positions = np.column_stack((x.ravel(), y.ravel()))

#                 image = np.sum([multivariate_normal(mean=mean, cov=np.diag([sigma, sigma])).pdf(positions)
#                                 for mean, sigma in zip(means, sigmas)], axis=0)
#                 image = image.reshape(100, 100)
#                 # rescale images to 0-255
#                 image = (image - np.min(image)) / (np.max(image) - np.min(image)) * 255
#                 self.update_signal.emit(image)
#                 time += 1
#                 self.msleep(50)  # Updated sleep time to 50 milliseconds
#         except KeyboardInterrupt:
#             pass

# class SaveVideoThread(QThread):
#     save_signal = pyqtSignal()

#     def __init__(self, gui):
#         super().__init__()
#         self.gui = gui
#         self.recording = False

#     def run(self):
#         fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#         out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (100, 100))

#         try:
#             while not self.isInterruptionRequested():
#                 self.save_signal.emit()
#                 if self.gui.recording:
#                     frame = np.array(self.gui.image_view.getImageItem().image)
#                     out.write(frame)
#                     self.msleep(50)  # Adjust sleep time as needed
#         except KeyboardInterrupt:
#             pass
#         finally:
#             out.release()
#             self.recording = False

# class GUI(QWidget):
#     def __init__(self):
#         super().__init__()

#         self.image_view = pg.ImageView(view=pg.PlotItem())
#         self.xprofile_plot = pg.PlotWidget()
#         self.yprofile_plot = pg.PlotWidget()
#         self.sum_plot = pg.PlotWidget()

#         self.start_button = QPushButton('Start', self)
#         self.start_button.clicked.connect(self.start_thread)

#         self.stop_button = QPushButton('Stop', self)
#         self.stop_button.clicked.connect(self.stop_thread)

#         self.record_button = QPushButton('Start Recording', self)
#         self.record_button.clicked.connect(self.toggle_record)

#         self.clear_roi_button = QPushButton('Clear ROI Plot', self)
#         self.clear_roi_button.clicked.connect(self.clear_roi_plot)

#         self.x_label = QLabel('X:')
#         self.x_textbox = QLineEdit(self)
#         self.x_textbox.setReadOnly(True)

#         self.y_label = QLabel('Y:')
#         self.y_textbox = QLineEdit(self)
#         self.y_textbox.setReadOnly(True)

#         self.roi_label = QLabel('ROI Sum:')
#         self.roi_textbox = QLineEdit(self)
#         self.roi_textbox.setReadOnly(True)

#         # Set maximum width for textboxes
#         self.roi_textbox.setMaximumWidth(50)
#         self.x_textbox.setMaximumWidth(50)
#         self.y_textbox.setMaximumWidth(50)


#         layout = QHBoxLayout()

#         left_layout = QVBoxLayout()
#         left_layout.addWidget(self.image_view, 7)  # Allocate 70% of the space
#         left_layout.addWidget(self.sum_plot, 3)  # Allocate 30% of the space

#         right_layout = QVBoxLayout()
#         right_layout.addWidget(self.xprofile_plot)
#         right_layout.addWidget(self.yprofile_plot)

#         layout.addLayout(left_layout, 2)  # Left side (2 parts)
#         layout.addLayout(right_layout, 1)  # Right side (1 part)

#         buttons_layout = QVBoxLayout()
#         buttons_layout.addWidget(self.start_button)
#         buttons_layout.addWidget(self.stop_button)
#         buttons_layout.addWidget(self.record_button)
#         buttons_layout.addWidget(self.clear_roi_button)

#         labels_layout = QVBoxLayout()
#         labels_layout.addWidget(self.x_label)
#         labels_layout.addWidget(self.x_textbox)
#         labels_layout.addWidget(self.y_label)
#         labels_layout.addWidget(self.y_textbox)
#         labels_layout.addWidget(self.roi_label)
#         labels_layout.addWidget(self.roi_textbox)

#         main_layout = QHBoxLayout()
#         main_layout.addLayout(layout)
#         main_layout.addLayout(buttons_layout)
#         main_layout.addLayout(labels_layout)

#         self.setLayout(main_layout)

#         self.save_video_thread = SaveVideoThread(self)
#         self.save_video_thread.save_signal.connect(self.save_frame)

#         layout.addWidget(self.record_button)

#         self.image_thread = ImageThread()
#         self.image_thread.update_signal.connect(self.update_image)

#         self.image_view.getView().scene().sigMouseClicked.connect(self.image_clicked)

#         # Set initial color map
#         self.image_view.setColorMap(pg.ColorMap(pos=[0, 0.5, 1], color=[(0, 0, 0), (255, 255, 255), (0, 0, 0)]))

#         # Create CircleROI
#         self.roi = pg.CircleROI([50, 50], [20, 20], pen=(0, 9))  # Initial circular ROI

#         # Add the ROI to the same scene as the image
#         self.image_view.getView().addItem(self.roi)

#         self.sum_data = []
#         self.current_x = 0
#         self.current_y = 0

#         self.setGeometry(100, 100, 1200, 600)
#         self.setWindowTitle('Image Rendering GUI')
#         self.show()
    
#     def toggle_record(self):
#         self.recording = self.save_video_thread.recording

#         if self.recording:
#             self.record_button.setText('Stop Recording')
#             self.save_video_thread.start()
#         else:
#             self.record_button.setText('Start Recording')
#             self.save_video_thread.requestInterruption()

#     def save_frame(self):
#         image = np.array(self.image_view.getImageItem().image)
#         # Your existing code to update the image
#         self.image_view.setImage(image)

#     def start_thread(self):
#         self.image_thread.start()

#     def stop_thread(self):
#         self.image_thread.requestInterruption()

#     def toggle_record(self):
#         self.recording = self.save_video_thread.recording
#         if not self.recording:
#             self.recording = True
#             self.record_button.setText('Stop Recording')
#         else:
#             self.recording = False
#             self.record_button.setText('Start Recording')

#     def update_image(self, image):
#         self.image_view.setImage(image)
#         x_profile = image[self.current_y, :]
#         y_profile = image[:, self.current_x]

#         self.xprofile_plot.clear()
#         self.yprofile_plot.clear()

#         x_curve = self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
#         y_curve = self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')

#         # Set y limit to 255 for the line profile plots
#         self.yprofile_plot.setYRange(0, 255)
#         self.xprofile_plot.setYRange(0, 255)

#         # Add grid lines to the line profiles
#         self.xprofile_plot.showGrid(x=True, y=True)
#         self.yprofile_plot.showGrid(x=True, y=True)

#         # Increase the fontsize of x and y ticks
#         styles = {'color': '#ffffff', 'font-size': '12pt'}
#         self.xprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.xprofile_plot.setLabel('bottom', 'X', **styles)
#         self.yprofile_plot.setLabel('left', 'Intensity', **styles)
#         self.yprofile_plot.setLabel('bottom', 'Y', **styles)

#         # Update the textboxes with current (x, y) location
#         self.x_textbox.setText(str(self.current_x))
#         self.y_textbox.setText(str(self.current_y))

#         # Get the region inside the ROI using the CircleROI's getArrayRegion method
#         roi_region = self.roi.getArrayRegion(image,
#                                             self.image_view.getImageItem(),
#                                             axes=(0, 1),
#                                             returnMappedCoords=False)

#         roi_sum = np.sum(roi_region)
#         self.roi_textbox.setText(str(roi_sum))

#         # Update the sum plot with the sum inside ROI as a function of time
#         self.sum_data.append((len(self.sum_data), roi_sum))
#         self.sum_plot.clear()
#         self.sum_plot.plot([item[0] for item in self.sum_data], [item[1] for item in self.sum_data], pen='y')
#         self.sum_plot.setLabel('left', 'Sum Inside ROI', **styles)
#         self.sum_plot.setLabel('bottom', 'Step', **styles)
#         self.sum_plot.showGrid(x=True, y=True)

#     def image_clicked(self, event):
#         pos = event.pos()
#         clicked_point = self.image_view.getImageItem().mapFromScene(pos)
#         self.current_x = int(clicked_point.x())
#         self.current_y = int(clicked_point.y())
#         self.update_image(self.image_view.getImageItem().image)

#     def clear_roi_plot(self):
#         self.sum_data = []
#         self.sum_plot.clear()

# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     gui = GUI()
#     sys.exit(app.exec_())

