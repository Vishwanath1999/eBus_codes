import sys
import numpy as np
import eBUS as eb
import lib.PvSampleUtils as psu

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import cv2

BUFFER_COUNT = 16

class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, device, stream):
        super().__init__()
        self.device = device
        self.stream = stream
        self.running = True

    def run(self):
        while self.running:
            result, pvbuffer, operational_result = self.stream.RetrieveBuffer(5000)
            if result.IsOK():
                if operational_result.IsOK():
                    image = pvbuffer.GetImage()
                    image_data = image.GetDataPointer()
                    height, width = image.GetHeight(), image.GetWidth()

                    # Convert to RGB for display
                    if image.GetPixelType() == eb.PvPixelRGB8:
                        image_data = cv2.cvtColor(image_data, cv2.COLOR_RGB2BGR)

                    frame = np.ndarray(shape=(height, width, 3), dtype=np.uint8, buffer=image_data)
                    self.frame_ready.emit(frame)

                    # Re-queue the pvbuffer in the stream object
                    self.stream.QueueBuffer(pvbuffer)
                else:
                    print(f"Operational Result: {operational_result.GetCodeString()}")
            else:
                print(f"Retrieve Buffer Result: {result.GetCodeString()}")


    def stop(self):
        self.running = False

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.device = None
        self.stream = None
        self.buffer_list = []

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('GigE Vision Streamer')

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)

        start_button = QPushButton('Start Streaming', self)
        start_button.clicked.connect(self.start_streaming)

        stop_button = QPushButton('Stop Streaming', self)
        stop_button.clicked.connect(self.stop_streaming)

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)
        layout.addWidget(start_button)
        layout.addWidget(stop_button)

    def connect_to_device(self,connection_ID):
        # Connect to the GigE Vision or USB3 Vision device
        print("Connecting to device.")
        result, device = eb.PvDevice.CreateAndConnect(connection_ID)
        if device == None:
            print(f"Unable to connect to device: {result.GetCodeString()} ({result.GetDescription()})")
        return device

    def open_stream(self,connection_ID):
        # Open stream to the GigE Vision or USB3 Vision device
        print("Opening stream from device.")
        result, stream = eb.PvStream.CreateAndOpen(connection_ID)
        if stream == None:
            print(f"Unable to stream from device. {result.GetCodeString()} ({result.GetDescription()})")
        return stream

    def configure_stream(self,device, stream):
        # If this is a GigE Vision device, configure GigE Vision specific streaming parameters
        if isinstance(device, eb.PvDeviceGEV):
            # Negotiate packet size
            device.NegotiatePacketSize()
            # Configure device streaming destination
            device.SetStreamDestination(stream.GetLocalIPAddress(), stream.GetLocalPort())

    def configure_stream_buffers(self,device, stream):
        buffer_list = []
        # Reading payload size from device
        size = device.GetPayloadSize()

        # Use BUFFER_COUNT or the maximum number of buffers, whichever is smaller
        buffer_count = stream.GetQueuedBufferMaximum()
        if buffer_count > BUFFER_COUNT:
            buffer_count = BUFFER_COUNT

        # Allocate buffers
        for i in range(buffer_count):
            # Create new pvbuffer object
            pvbuffer = eb.PvBuffer()
            # Have the new pvbuffer object allocate payload memory
            pvbuffer.Alloc(size)
            # Add to external list - used to eventually release the buffers
            buffer_list.append(pvbuffer)
        
        # Queue all buffers in the stream
        for pvbuffer in buffer_list:
            stream.QueueBuffer(pvbuffer)
        print(f"Created {buffer_count} buffers")
        return buffer_list
    
    def start_streaming(self):
        connection_ID = psu.PvSelectDevice()
        if connection_ID:
            self.device = self.connect_to_device(connection_ID)
            if self.device:
                self.stream = self.open_stream(connection_ID)
                if self.stream:
                    self.configure_stream(self.device, self.stream)
                    self.buffer_list = self.configure_stream_buffers(self.device, self.stream)

                    self.camera_thread = CameraThread(self.device, self.stream)
                    self.camera_thread.frame_ready.connect(self.update_frame)
                    self.camera_thread.start()

    def stop_streaming(self):
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread.wait()

        if self.stream:
            self.stream.Close()
            eb.PvStream.Free(self.stream)

        if self.device:
            self.device.Disconnect()
            eb.PvDevice.Free(self.device)

    def update_frame(self, frame):
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        self.image_label.setPixmap(pixmap)

    def closeEvent(self, event):
        self.stop_streaming()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
