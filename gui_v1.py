import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit
import eBUS as eb
import lib.PvSampleUtils as psu
import cv2
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
import numpy as np

BUFFER_COUNT = 50

class ImageAcquisitionApp(QWidget):
    def __init__(self, ip_address=None):
        super().__init__()

        # Initialize variables
        self.device_connected = False
        self.acquisition_active = False

        # UI elements
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Enter IP Address")
        self.status_label = QLabel("Status: Not connected")
        self.image_label = QLabel()
        self.connect_button = QPushButton("Connect")
        self.start_stop_button = QPushButton("Start Acquisition")

        # Set the provided IP address if available
        if ip_address:
            self.ip_input.setText(ip_address)

        # Set up the layout
        layout = QVBoxLayout()
        layout.addWidget(self.ip_input)
        layout.addWidget(self.status_label)
        layout.addWidget(self.image_label)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.start_stop_button)

        # Connect signals to slots
        self.connect_button.clicked.connect(self.toggle_connection)
        self.start_stop_button.clicked.connect(self.toggle_acquisition)

        # Set up the main window
        self.setLayout(layout)
        self.setWindowTitle("GigE Device Image Acquisition")
        self.setGeometry(100, 100, 600, 400)

        # Initialize eBUS library
        # self.ebus_initialized = eb.PvInitialize()

    def toggle_connection(self):
        ip_address = self.ip_input.text()

        if not self.device_connected:
            if ip_address:
                connection_ID = ip_address
            else:
                connection_ID = psu.PvSelectDevice()

            if connection_ID:
                self.device = connect_to_device(connection_ID)
                if self.device:
                    self.stream = open_stream(connection_ID)
                    if self.stream:
                        configure_stream(self.device, self.stream)
                        self.buffer_list = configure_stream_buffers(self.device, self.stream)
                        self.device_connected = True
                        self.status_label.setText(f"Status: Connected to {ip_address}")

    def toggle_acquisition(self):
        if self.device_connected:
            if not self.acquisition_active:
                self.acquisition_active = True
                self.start_stop_button.setText("Stop Acquisition")
                self.acquire_and_display_images()
            else:
                self.acquisition_active = False
                self.start_stop_button.setText("Start Acquisition")

    def disconnect_device(self):
        if self.device_connected:
            # Close the stream
            self.stream.Close()
            eb.PvStream.Free(self.stream)

            # Disconnect the device
            self.device.Disconnect()
            eb.PvDevice.Free(self.device)

            # Update UI
            self.device_connected = False
            self.status_label.setText("Status: Not connected")

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

def connect_to_device(connection_ID):
    # Connect to the GigE Vision or USB3 Vision device
    result, device = eb.PvDevice.CreateAndConnect(connection_ID)
    if device == None:
        print(f"Unable to connect to device: {result.GetCodeString()} ({result.GetDescription()})")
    return device

def open_stream(connection_ID):
    # Open stream to the GigE Vision or USB3 Vision device
    result, stream = eb.PvStream.CreateAndOpen(connection_ID)
    if stream == None:
        print(f"Unable to stream from device. {result.GetCodeString()} ({result.GetDescription()})")
    return stream

def configure_stream(device, stream):
    # If this is a GigE Vision device, configure GigE Vision specific streaming parameters
    if isinstance(device, eb.PvDeviceGEV):
        # Negotiate packet size
        device.NegotiatePacketSize()
        # Configure device streaming destination
        device.SetStreamDestination(stream.GetLocalIPAddress(), stream.GetLocalPort())

def configure_stream_buffers(device, stream):
    buffer_list = []
    # Reading payload size from device
    size = device.GetPayloadSize()

    # Use BUFFER_COUNT or the maximum number of buffers, whichever is smaller
    buffer_count = stream.GetQueuedBufferMaximum()
    if buffer_count > BUFFER_COUNT:
        buffer_count = BUFFER_COUNT

    # Allocate buffers
    for i in range(buffer_count):
        # Create a new pvbuffer object
        pvbuffer = eb.PvBuffer()
        # Have the new pvbuffer object allocate payload memory
        pvbuffer.Alloc(size)
        # Add to an external list - used to eventually release the buffers
        buffer_list.append(pvbuffer)

    # Queue all buffers in the stream
    for pvbuffer in buffer_list:
        stream.QueueBuffer(pvbuffer)
    print(f"Created {buffer_count} buffers")
    return buffer_list

if __name__ == "__main__":
    ip_address = None
    if len(sys.argv) > 1:
        ip_address = sys.argv[1]

    app = QApplication(sys.argv)
    window = ImageAcquisitionApp(ip_address)
    window.show()
    sys.exit(app.exec_())
