import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QCheckBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import eBUS as eb
import cv2
import numpy as np
import matplotlib.pyplot as plt

class ImageAcquisitionApp(QWidget):
    def __init__(self, ip_address=None):
        super().__init__()

        # Initialize variables
        self.device_connected = False
        self.acquisition_active = False
        self.measure_distance = False
        self.selected_points = []
        self.marker_position = (0, 0)
        self.current_image_data = None

        # UI elements
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Enter IP Address")
        self.status_label = QLabel("Status: Not connected")
        self.image_label = QLabel()
        self.connect_button = QPushButton("Connect")
        self.start_stop_button = QPushButton("Start Acquisition")
        self.measure_checkbox = QCheckBox("Measure Distance")
        self.distance_label = QLabel("Distance: N/A")
        self.horizontal_profile_checkbox = QCheckBox("Show Horizontal Profile")
        self.vertical_profile_checkbox = QCheckBox("Show Vertical Profile")

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.ip_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.image_label)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.start_stop_button)
        layout.addWidget(self.measure_checkbox)
        layout.addWidget(self.distance_label)
        layout.addWidget(self.horizontal_profile_checkbox)
        layout.addWidget(self.vertical_profile_checkbox)

        # Connect signals to slots
        self.connect_button.clicked.connect(self.toggle_connection)
        self.start_stop_button.clicked.connect(self.toggle_acquisition)
        self.measure_checkbox.stateChanged.connect(self.toggle_measure_distance)
        self.horizontal_profile_checkbox.stateChanged.connect(self.toggle_show_horizontal_profile)
        self.vertical_profile_checkbox.stateChanged.connect(self.toggle_show_vertical_profile)

        # Set up the figure for line profiles
        self.horizontal_profile_fig, self.horizontal_profile_ax = plt.subplots()
        self.vertical_profile_fig, self.vertical_profile_ax = plt.subplots()

    def toggle_show_horizontal_profile(self, state):
        if state == Qt.Checked:
            self.update_line_profile('horizontal')

    def toggle_show_vertical_profile(self, state):
        if state == Qt.Checked:
            self.update_line_profile('vertical')

    def update_line_profile(self, direction):
        if self.acquisition_active:
            image_data = self.current_image_data
            marker_x, marker_y = self.marker_position

            if marker_x >= 0 and marker_x < image_data.shape[1] and marker_y >= 0 and marker_y < image_data.shape[0]:
                if direction == 'horizontal':
                    line_profile = np.mean(image_data[marker_y, :, :], axis=1)
                    profile_label = 'Profile along X'
                    profile_ax = self.horizontal_profile_ax
                elif direction == 'vertical':
                    line_profile = np.mean(image_data[:, marker_x, :], axis=1)
                    profile_label = 'Profile along Y'
                    profile_ax = self.vertical_profile_ax

                # Convert pixel distances to mm
                pixel_size = self.device.GetFloatParameter("SensorWidth").GetValue() / image_data.shape[1]
                distance = np.arange(0, len(line_profile)) * pixel_size

                # Plot line profile
                profile_ax.clear()
                profile_ax.plot(distance, line_profile, label=profile_label, color='b', marker='o')
                profile_ax.set_xlabel('Distance (mm)')
                profile_ax.set_ylabel('Intensity (a.u.)')
                profile_ax.grid(True)
                profile_ax.set_title(profile_label)

                # Show the updated plot
                if direction == 'horizontal':
                    self.horizontal_profile_fig.canvas.draw()
                    self.horizontal_profile_fig.canvas.flush_events()
                elif direction == 'vertical':
                    self.vertical_profile_fig.canvas.draw()
                    self.vertical_profile_fig.canvas.flush_events()

    def toggle_connection(self):
        ip_address = self.ip_input.text()

        if not self.device_connected:
            if ip_address:
                connection_ID = ip_address  # Use the provided IP address directly
            else:
                connection_ID = eb.PvSelectDevice()

            if connection_ID:
                self.device = self.connect_to_device(connection_ID)
                if self.device:
                    self.stream = self.open_stream(connection_ID)
                    if self.stream:
                        self.configure_stream(self.device, self.stream)
                        self.buffer_list = self.configure_stream_buffers(self.device, self.stream)
                        self.device_connected = True
                        self.status_label.setText(f"Status: Connected to {ip_address}")

    def connect_to_device(self, connection_ID):
        result, device = eb.PvDevice.CreateAndConnect(connection_ID)
        if device is None:
            print(f"Unable to connect to device: {result.GetCodeString()} ({result.GetDescription()})")
        return device

    def open_stream(self, connection_ID):
        result, stream = eb.PvStream.CreateAndOpen(connection_ID)
        if stream is None:
            print(f"Unable to stream from device. {result.GetCodeString()} ({result.GetDescription()})")
        return stream

    def configure_stream(self, device, stream):
        if isinstance(device, eb.PvDeviceGEV):
            device.NegotiatePacketSize()
            device.SetStreamDestination(stream.GetLocalIPAddress(), stream.GetLocalPort())

    def configure_stream_buffers(self, device, stream):
        buffer_list = []
        size = device.GetPayloadSize()
        buffer_count = stream.GetQueuedBufferMaximum()
        if buffer_count > 50:
            buffer_count = 50

        for _ in range(buffer_count):
            pvbuffer = eb.PvBuffer()
            pvbuffer.Alloc(size)
            buffer_list.append(pvbuffer)

        for pvbuffer in buffer_list:
            stream.QueueBuffer(pvbuffer)
        print(f"Created {buffer_count} buffers")
        return buffer_list

    def toggle_measure_distance(self, state):
        if state == Qt.Checked:
            self.measure_distance = True
        else:
            self.measure_distance = False
            self.selected_points = []
            self.distance_label.setText("Distance: N/A")

    def toggle_acquisition(self):
        if not self.acquisition_active and self.device_connected:
            self.acquisition_active = True
            self.start_stop_button.setText("Stop Acquisition")
            self.acquire_images()
        elif self.acquisition_active:
            self.acquisition_active = False
            self.start_stop_button.setText("Start Acquisition")

    def acquire_and_display_images(self):
        try:
            while self.acquisition_active:
                # Retrieve next pvbuffer
                result, pvbuffer, operational_result = self.stream.RetrieveBuffer(1000)
                if result.IsOK():
                    if operational_result.IsOK():
                        # We now have a valid pvbuffer.
                        # This is where you would typically process the pvbuffer.

                        # Retrieve Numpy array
                        image_data = pvbuffer.GetImage().GetDataPointer()

                        # Display the live feed
                        self.display_live_feed(image_data)

        except KeyboardInterrupt:
            self.acquisition_active = False
            self.start_stop_button.setText("Start Acquisition")
            self.disconnect_device()

    def display_live_feed(self, image_data):
        # Convert NumPy array to QImage
        height, width, channel = image_data.shape
        bytes_per_line = 3 * width
        q_image = QImage(image_data.data, width, height, bytes_per_line, QImage.Format_RGB888)

        # Convert QImage to QPixmap
        pixmap = QPixmap.fromImage(q_image)

        # Display the image
        self.image_label.setPixmap(pixmap)

        # Update the UI
        self.image_label.repaint()
        QApplication.processEvents()
        # ... (existing code)

    def mousePressEvent(self, event):
        # ... (existing code)
        if self.measure_distance and len(self.selected_points) < 2:
            x = event.pos().x()
            y = event.pos().y()
            self.selected_points.append((x, y))
        # Update marker position for line profile
        self.marker_position = (x, y)

        # Update line profile if the checkbox is checked
        self.update_line_profile('horizontal')
        self.update_line_profile('vertical')

# ... (existing code)

if __name__ == "__main__":
    # ... (existing code)

    app = QApplication(sys.argv)
    window = ImageAcquisitionApp()
    window.show()
    sys.exit(app.exec_())
