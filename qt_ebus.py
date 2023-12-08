import numpy as np
import eBUS as eb
import lib.PvSampleUtils as psu
import sys
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit
import numpy as np

BUFFER_COUNT = 16

kb = psu.PvKb()

opencv_is_available=True
try:
    # Detect if OpenCV is available
    import cv2
    opencv_version=cv2.__version__
except:
    opencv_is_available=False
    print("Warning: This sample requires python3-opencv to display a window")

class ImageAcquisitionThread(QThread):
    update_signal = pyqtSignal(np.ndarray)

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

    def acquire_images(self,device, stream):
        # Get device parameters need to control streaming
        device_params = device.GetParameters()

        # Map the GenICam AcquisitionStart and AcquisitionStop commands
        start = device_params.Get("AcquisitionStart")
        stop = device_params.Get("AcquisitionStop")

        # Get stream parameters
        stream_params = stream.GetParameters()

        # Map a few GenICam stream stats counters
        frame_rate = stream_params.Get("AcquisitionRate")
        bandwidth = stream_params[ "Bandwidth" ]

        # Enable streaming and send the AcquisitionStart command
        print("Enabling streaming and sending AcquisitionStart command.")
        device.StreamEnable()
        start.Execute()

        doodle = "|\\-|-/"
        doodle_index = 0
        display_image = False
        warning_issued = False

        # Acquire images until the user instructs us to stop.
        print("\n<press a key to stop streaming>")
        kb.start()
        while not kb.is_stopping() and not self.isInterruptionRequested():
            # Retrieve next pvbuffer
            result, pvbuffer, operational_result = stream.RetrieveBuffer(1000)
            if result.IsOK():
                if operational_result.IsOK():
                    #
                    # We now have a valid pvbuffer. This is where you would typically process the pvbuffer.
                    # -----------------------------------------------------------------------------------------
                    # ...

                    result, frame_rate_val = frame_rate.GetValue()
                    result, bandwidth_val = bandwidth.GetValue()

                    print(f"{doodle[doodle_index]} BlockID: {pvbuffer.GetBlockID()}", end='')
                    print(f" {frame_rate_val:.1f} FPS  {bandwidth_val / 1000000.0:.1f} Mb/s     ", end='\r')

                    payload_type = pvbuffer.GetPayloadType()
                    if payload_type == eb.PvPayloadTypeImage:
                        image = pvbuffer.GetImage()
                        image_data = image.GetDataPointer()
                        print(f" W: {image.GetWidth()} H: {image.GetHeight()} ", end='')
                        
                        if opencv_is_available:
                            if image.GetPixelType() == eb.PvPixelMono8:
                                display_image = True
                            if image.GetPixelType() == eb.PvPixelRGB8:
                                image_data = cv2.cvtColor(image_data, cv2.COLOR_RGB2BGR)
                                display_image = True

                            if display_image:
                                # cv2.imshow("stream",image_data)
                                self.update_signal.emit(image_data)
                                self.msleep(1/frame_rate_val)
                            else:
                                if not warning_issued:
                                    # display a message that video only display for Mono8 / RGB8 images
                                    print(f" ")
                                    print(f" Currently only Mono8 / RGB8 images are displayed", end='\r')
                                    print(f"")
                                    warning_issued = True

                            if cv2.waitKey(1) & 0xFF != 0xFF:
                                break

                    elif payload_type == eb.PvPayloadTypeChunkData:
                        print(f" Chunk Data payload type with {pvbuffer.GetChunkCount()} chunks", end='')

                    elif payload_type == eb.PvPayloadTypeRawData:
                        print(f" Raw Data with {pvbuffer.GetRawData().GetPayloadLength()} bytes", end='')

                    elif payload_type == eb.PvPayloadTypeMultiPart:
                        print(f" Multi Part with {pvbuffer.GetMultiPartContainer().GetPartCount()} parts", end='')

                    else:
                        print(" Payload type not supported by this sample", end='')

                    print(f" {frame_rate_val:.1f} FPS  {bandwidth_val / 1000000.0:.1f} Mb/s     ", end='\r')
                else:
                    # Non OK operational result
                    print(f"{doodle[ doodle_index ]} {operational_result.GetCodeString()}       ", end='\r')
                # Re-queue the pvbuffer in the stream object
                stream.QueueBuffer(pvbuffer)

            else:
                # Retrieve pvbuffer failure
                print(f"{doodle[ doodle_index ]} {result.GetCodeString()}      ", end='\r')

            doodle_index = (doodle_index + 1) % 6
            if kb.kbhit():
                kb.getch()
                break

        kb.stop()
        # if opencv_is_available:
        #     cv2.destroyAllWindows()

        # Tell the device to stop sending images.
        print("\nSending AcquisitionStop command to the device")
        stop.Execute()

        # Disable streaming on the device
        print("Disable streaming on the controller.")
        device.StreamDisable()

        # Abort all buffers from the stream and dequeue
        print("Aborting buffers still in stream")
        stream.AbortQueuedBuffers()
        while stream.GetQueuedBufferCount() > 0:
            result, pvbuffer, lOperationalResult = stream.RetrieveBuffer()

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

        self.image_thread = ImageAcquisitionThread()
        self.connection_id = psu.PvSelectDevice()
        self.device = self.image_thread.connect_to_device(self.connection_id)
        self.stream = self.image_thread.open_stream(self.connection_id)
        self.image_thread.configure_stream(self.device, self.stream)
        self.buffer_list = self.image_thread.configure_stream_buffers(self.device, self.stream)
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
        self.buffer_list.clear()
                
        # Close the stream
        print("Closing stream")
        self.stream.Close()
        eb.PvStream.Free(self.stream);    

        # Disconnect the device
        print("Disconnecting device")
        self.device.Disconnect()
        eb.PvDevice.Free(self.device)

        print("<press a key to exit>")
        kb.start()
        kb.getch()
        kb.stop()

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