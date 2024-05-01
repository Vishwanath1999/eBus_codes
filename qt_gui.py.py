'''
Implelemnted pointing error tracking w.r.t marker position.
dated 2023-01-23
'''

import sys
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal,QDateTime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QMainWindow,\
    QHBoxLayout, QPushButton, QLabel, QLineEdit, QCheckBox, QTabWidget, QGroupBox, QGridLayout,QComboBox, QSlider
import numpy as np
from scipy.stats import multivariate_normal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt
import queue
import time
from pyqtgraph import ROI, mkPen
from PyQt5.QtGui import QIcon, QPixmap
import subprocess
import eBUS as eb
import lib.PvSampleUtils as psu
import crcmod
from PyQt5.QtCore import QMutex, QMutexLocker
import matplotlib.pyplot as plt


# import and suppress warnings
# import warnings
# warnings.filterwarnings("ignore")

BUFFER_COUNT = 64
SPEED = "Baud115200"
STOPBITS = "One"
PARITY = "None"
TEST_COUNT = 16

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
    def __init__(self, display_queue, mutex):
        super(ImageAcquisitionThread, self).__init__()
        self.display_queue = display_queue
        self.isRunning = True
        self.mutex = QMutex()
    
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
    
    def init_params(self,device,stream):
        self.device = device
        self.stream = stream
    
    def run(self):
        # Get device parameters need to control streaming
        device_params = self.device.GetParameters()

        # Map the GenICam AcquisitionStart and AcquisitionStop commands
        start = device_params.Get("AcquisitionStart")
        stop = device_params.Get("AcquisitionStop")

        # Get stream parameters
        stream_params = self.stream.GetParameters()

        # Map a few GenICam stream stats counters
        frame_rate = stream_params.Get("AcquisitionRate")
        bandwidth = stream_params[ "Bandwidth" ]

        # Enable streaming and send the AcquisitionStart command
        print("Enabling streaming and sending AcquisitionStart command.")
        self.device.StreamEnable()
        start.Execute()

        doodle = "|\\-|-/"
        doodle_index = 0
        display_image = False
        warning_issued = False

        while not self.isInterruptionRequested():
            # Retrieve next pvbuffer
            result, pvbuffer, operational_result = self.stream.RetrieveBuffer(1000)
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
                                with QMutexLocker(self.mutex):
                                    self.display_queue.put(np.transpose(image_data))
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
                self.stream.QueueBuffer(pvbuffer)

            else:
                # Retrieve pvbuffer failure
                print(f"{doodle[ doodle_index ]} {result.GetCodeString()}      ", end='\r')

            doodle_index = (doodle_index + 1) % 6

        # Tell the device to stop sending images.
        print("\nSending AcquisitionStop command to the device")
        stop.Execute()

        # Disable streaming on the device
        print("Disable streaming on the controller.")
        self.device.StreamDisable()

        # Abort all buffers from the stream and dequeue
        print("Aborting buffers still in stream")
        self.stream.AbortQueuedBuffers()
        while self.stream.GetQueuedBufferCount() > 0:
            result, pvbuffer, lOperationalResult = self.stream.RetrieveBuffer()
    
    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
    
    def is_paused(self):
        return self.is_paused
    
    def stop(self):
        self.isRunning = False
        print('Stopping image acquisition thread')
        self.terminate()

class ImageDisplayThread(QThread):
    update_signal = pyqtSignal(np.ndarray)
    def __init__(self,display_queue, mutex):
        super(ImageDisplayThread, self).__init__()
        self.display_queue = display_queue
        self.isRunning = True
        self.mutex = QMutex()
    def run(self):
        while not self.isInterruptionRequested():            
            try:
                with QMutexLocker(self.mutex):
                    image_data = self.display_queue.get(block=True, timeout=0.01)
                self.update_signal.emit(image_data)
                self.msleep(int(1000/30))
            except (queue.Empty, queue.Full):
                if queue.Empty:
                    print('Queue is empty')
                elif queue.Full:
                    print('Queue is full')
                pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
    
    def is_paused(self):
        return self.is_paused
            

    def stop(self):
        self.isRunning = False
        print('Stopping image acquisition thread')
        self.terminate

class GUI(QWidget):
    def __init__(self):
        super().__init__()

        self.current_integration_time = 4
        self.n_cols = 640#200
        self.n_rows = 512#200
        self.start_col = 0#200
        self.start_row = 0#200

        # Image display widgets
        self.image_view = pg.ImageView(view=pg.PlotItem())
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()

        # self.image_view.getView().wheelEvent = self.zoom
        # self.image_view.ui.histogram.hide()
        
        self.sum_plot = pg.PlotWidget()
        self.full_sum_plot = pg.PlotWidget()
        self.xprofile_plot = pg.PlotWidget()
        self.yprofile_plot = pg.PlotWidget()

        # start and stop buttons
        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.start_thread)

        self.stop_button = QPushButton('Stop', self)
        self.stop_button.clicked.connect(self.stop_thread)

        # Clear ROI plot button
        self.clear_roi_button = QPushButton('Clear ROI Plot', self)
        self.clear_roi_button.clicked.connect(self.clear_roi_plot)

        # ROI SUM widgets
        self.roi_label = QLabel('ROI Sum:')
        self.roi_textbox = QLineEdit(self)
        self.roi_textbox.setReadOnly(True)

        # ROI radius widgets
        self.roi_radius_label = QLabel('ROI Radius:')
        self.roi_radius_textbox = QLineEdit(self)
        self.roi_radius_textbox.setReadOnly(True)

        # ROI SUM widgets
        self.full_roi_label = QLabel('Full ROI Sum:')
        self.full_roi_textbox = QLineEdit(self)
        self.full_roi_textbox.setReadOnly(True)


        self.eff_label = QLabel('Efficiency:')
        self.eff_textbox = QLineEdit(self)
        self.eff_textbox.setReadOnly(True)


        # Full ROI radius widgets
        self.full_roi_radius_label = QLabel('Full ROI Radius:')
        self.full_roi_radius_textbox = QLineEdit(self)
        self.full_roi_radius_textbox.setReadOnly(True)

        # Set integration time widgets
        self.integration_time_label = QLabel('Integration Time:')
        self.integration_time_input = QLineEdit(self)
        self.integration_time_input.setPlaceholderText('Enter float value')
        self.set_int_time_button = QPushButton('Set Integration Time', self)
        self.set_int_time_button.clicked.connect(self.set_integration_time)
        self.current_int_time_label = QLabel('Current Integration Time:')
        self.display_int_time_button = QPushButton('Display Int. Time', self)
        self.display_int_time_button.clicked.connect(self.display_integration_time)
        self.current_integration_time_label = QLabel(self)

        # set window widgets
        self.n_cols_label = QLabel('Num Cols:')
        self.n_cols_input = QLineEdit(self)
        self.n_cols_input.setPlaceholderText('Enter integer value')
        self.n_rows_label = QLabel('Num Rows:')
        self.n_rows_input = QLineEdit(self)
        self.n_rows_input.setPlaceholderText('Enter integer value')
        self.start_col_label = QLabel('Start Col:')
        self.start_col_input = QLineEdit(self)
        self.start_col_input.setPlaceholderText('Enter integer value')
        self.start_row_label = QLabel('Start Row:')
        self.start_row_input = QLineEdit(self)
        self.start_row_input.setPlaceholderText('Enter integer value')
        self.set_window_button = QPushButton('Set Window', self)
        self.set_window_button.clicked.connect(self.set_window)

        # set marker widgets
        self.set_markers_checkbox = QCheckBox('Set Markers', self)
        self.set_markers_checkbox.stateChanged.connect(self.toggle_markers)

        # scatter marker checkbox
        self.scatter_marker_checkbox = QCheckBox('Side-lobe Marker', self)
        self.scatter_marker_checkbox.stateChanged.connect(self.toggle_rois)

        self.show_roi_checkbox = QCheckBox('Show ROIs',self)
        self.show_roi_checkbox.stateChanged.connect(self.show_rois)
        self.roi_flag=False

        # read background pushbutton
        self.read_background_button = QPushButton('Offset Background', self)
        self.read_background_button.clicked.connect(self.read_background)
        self.roi_bg_value = 0
        self.full_roi_bg_value = 0

        self.slider_label = QLabel('Zoom',self)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(0,250)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(5)
        # self.zoom_slider.toolTip()
        self.zoom_slider.valueChanged.connect(self.zoom)

        self.save_csv_image = QPushButton('Save Image CSV',self)
        self.save_csv_image.clicked.connect(self.save_csv_on_click)
        self.save_image = QPushButton('Save Image',self)
        self.save_image.clicked.connect(self.save_on_click)
        self.disp_hex_vertices = QPushButton('Print Vercices',self)
        self.disp_hex_vertices.clicked.connect(self.disp_hex_on_click)

        # start control checkbox
        self.start_control_checkbox = QCheckBox('Start Control', self)
        self.start_control_checkbox.stateChanged.connect(self.start_control_dummy_function)

        # create a list of 6 Qlineedit and a seprate list of 6 qtextbox
        self.pointing_error_labels = [QLabel('Pointing Error Beam {_i}: '.format(_i=i+1)+" (u rad)") for i in range(7)]
        self.pointing_error_textbox = [QLineEdit(self) for i in range(7)]
        for qline in self.pointing_error_textbox:
            qline.setReadOnly(True)

        self.p_err_label = QLabel("RMS Pointing Error (u rad):")
        self.p_err_out = QLineEdit(self)

        self.file_name = QLineEdit(self)
        self.file_name.setPlaceholderText('Enter File Name')
        
        
        self.combo_box_label = QLabel('Select Option')
        self.combo_box = QComboBox()
        self.combo_box.addItem('Use Max')
        self.combo_box.addItem('Use Centroid')
        self.combo_box.setCurrentIndex(1)
        self.combo_box.currentIndexChanged.connect(lambda: self.find_appr_coord(self.combo_box))

        self.flip_img_label = QLabel('Img Transformation')
        self.flip_img_cb = QComboBox()
        self.flip_img_cb.addItem('None')
        self.flip_img_cb.addItem('LR')
        self.flip_img_cb.addItem('UD')
        self.flip_img_cb.addItem('LR-UD')
        self.flip_img_cb.addItem('UD-LR')
        self.flip_img_cb.setCurrentIndex(3)
        self.flip_img_cb.currentIndexChanged.connect(lambda: self.img_transform(self.flip_img_cb))

        self.lock_hexagon = QPushButton('Lock hexagon', self)
        self.lock_hexagon.clicked.connect(self.hexagon_lock)

        self.is_hexagon_enable = False

        # Variables for storing marker lines
        self.horizontal_line = None
        self.vertical_line = None

        self.roi_tab = QTabWidget()  
        self.roi_sum_widget = QWidget()
        self.full_roi_sum_widget = QWidget()      
        self.roi_tab.addTab(self.roi_sum_widget, 'ROI Sum')
        # add self.sum_plot to the roi_sum_widget
        roi_sum_layout = QVBoxLayout(self.roi_sum_widget)
        roi_sum_layout.addWidget(self.sum_plot)
        self.roi_tab.addTab(self.full_roi_sum_widget, 'Efficiency')
        # add self.full_sum_plot to the full_roi_sum_widget
        full_roi_sum_layout = QVBoxLayout(self.full_roi_sum_widget)
        full_roi_sum_layout.addWidget(self.full_sum_plot)


        # Layouts
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.image_view, 7)  # Allocate 70% of the space
        left_layout.addWidget(self.roi_tab, 3)    # Allocate 30% of the space

        # Create tabs
        self.tab_widget = QTabWidget()
        self.camera_control_tab = QWidget()
        self.phase_control_tab = QWidget()
        self.line_profile_tab = QWidget()
        self.pointing_error_tab = QWidget()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.camera_control_tab, 'Camera Control')
        self.tab_widget.addTab(self.pointing_error_tab, 'Pointing Error')
        self.tab_widget.addTab(self.line_profile_tab, 'Line Profile')
        self.tab_widget.addTab(self.phase_control_tab, 'Phase Control')

        right_layout = QVBoxLayout(self.line_profile_tab)
        right_layout.addWidget(self.xprofile_plot)
        right_layout.addWidget(self.yprofile_plot)

        # Create a layout for the tab widget
        tab_widget_layout = QVBoxLayout()
        tab_widget_layout.addWidget(self.tab_widget)

        # Set layouts for the tabs
        self.init_camera_control_tab()
        self.init_phase_control_tab()
        self.init_pointing_error_tab()

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_layout, 2)            # Left side (2 parts)
        main_layout.addLayout(tab_widget_layout, 1)  # Right side (1 part)

        self.setLayout(main_layout)

        # Display queue for image threads
        display_queue = queue.Queue()

        # create mutex object
        self.mutex = QMutex()

        # Image acquisition and display threads
        self.image_acq_thread = ImageAcquisitionThread(display_queue, self.mutex)
        self.image_disp_thread = ImageDisplayThread(display_queue, self.mutex)
        self.image_disp_thread.update_signal.connect(self.update_image)

        self.connection_id = psu.PvSelectDevice()
        self.device = self.image_acq_thread.connect_to_device(self.connection_id)
        self.stream = self.image_acq_thread.open_stream(self.connection_id)
        
    
        # print row and column start and stop
        self.parameters = self.device.GetParameters()
        self.enable_serial(self.parameters)
        self.parameters.SetEnumValue("TestPattern", "Off")

        self.image_acq_thread.configure_stream(self.device, self.stream)
        self.buffer_list = self.image_acq_thread.configure_stream_buffers(self.device, self.stream)

        # Set initial color map
        self.image_view.setColorMap(pg.ColorMap(pos=[0, 0.5, 1], color=[(0, 0, 0), (255, 255, 255), (0, 0, 0)]))

        # Create a circular ROI
        pen = pg.mkPen(color=QColor(255,255,255),width=2.5)
        self.roi = pg.CircleROI([self.n_cols//2, self.n_rows//2], [300//15, 300//15], pen=pen)#[700//15, 700//15]
        self.image_view.getView().addItem(self.roi)
        self.roi.hide()

        pen = pg.mkPen(color=QColor(255,0,0),width=2.5)
        self.full_roi = pg.CircleROI([self.roi.pos()[0],self.roi.pos()[1]], [900//15, 900//15], pen=pen)#[2656//15, 2656//15]
        self.image_view.getView().addItem(self.full_roi)
        self.full_roi.hide()

        self.full_roi.sigRegionChanged.connect(self.update_inner_roi)

        # Lists to store data for the sum plot
        self.sum_data = []
        self.full_sum_data = []
        self.hexagon_vertices = []
        self.current_x = self.n_cols//2
        self.current_y = self.n_rows//2

        self.eff_hist = []
        self.p_err_hist = []
        self.roi_hist = []

        self.crosses = []
        self.hexagonal_vertices = []
        self.zoom_factor = 1

        # Set GUI properties
        self.setGeometry(100, 100, 1200, 600)
        self.setWindowTitle('TAC GUI')
        icon_path = 'icon.ico'
        pixmap = QPixmap(icon_path)

        # Set application icon
        icon = QIcon(pixmap)
        self.setWindowIcon(icon)

        self.transform = 2

        self.knn = 30
        self.find_coord = self.find_max_coordinates

        self.image_view.getView().scene().sigMouseClicked.connect(self.image_clicked)
        # Load JPEG image

        self.image = np.zeros((100,100))
        self.start_time = QDateTime.currentDateTime()
        self.time_axis = []

        self.show()
    
    # def show_rois(self,event)
    def update_inner_roi(self):
        center = self.full_roi.pos() + (self.full_roi.size() - self.roi.size())/2
        self.roi.setPos(center)

    def start_thread(self):
        
        self.image_acq_thread.init_params(self.device,self.stream)
        self.image_acq_thread.start()
        print('Image Generation Started')
        self.image_disp_thread.start()
        print('Image Display started')
        self.image_view.setPredefinedGradient('viridis')


    def stop_thread(self):
        self.image_acq_thread.requestInterruption()
        print('Image Generation Stopped')
        # self.image_acq_thread.stop()
        self.image_disp_thread.requestInterruption()
        print('Image Display Stopped')

        self.serial.Close()
        # self.image_disp_thread.stop()
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
        # Close the GUI
        self.close()
    
    def zoom(self,value):
       self.zoom_factor = 1+0.01*value
    
    def read_background(self, state):
        # read values from roi and full_roi and save to self.roi_bg_value and self.full_roi_bg_value
        
        self.roi_bg_value = float(self.roi_textbox.text())
        self.full_roi_bg_value = float(self.full_roi_textbox.text())
        # print values
        print('roi_bg_value:',self.roi_bg_value)
        print('full_roi_bg_value:',self.full_roi_bg_value)
    
    def update_hexagon(self, event):
        pos = event.pos()
        hexagon_radius = 125
        clicked_point = self.image_view.getImageItem().mapFromScene(pos)
        hexagon_center = [clicked_point.x(), clicked_point.y()] 
        # Set up the hexagon vertices
        angle_offset = np.pi / 3 + np.pi + np.deg2rad(2)  # Offset to start the hexagon from the top
        
        self.hexagon_vertices = [
            (
                hexagon_center[0] + hexagon_radius * np.cos(angle_offset - i * 2 * np.pi / 6),
                hexagon_center[1] + hexagon_radius * np.sin(angle_offset - i * 2 * np.pi / 6),
            )
            for i in range(6)
        ]
        self.hexagon_vertices.insert(0,(clicked_point.x(), clicked_point.y()))

        # Clear existing crosses
        for cross in self.crosses:
            self.image_view.getView().removeItem(cross)

        # Create new Cross-shaped ScatterPlotItems at updated hexagon vertices
        self.crosses = []
        pen = pg.mkPen(color=QColor(0,255,0))
        for vertex in self.hexagon_vertices:
            cross = pg.ScatterPlotItem()
            cross.addPoints(x=[vertex[0]], y=[vertex[1]], symbol='+', size=20, pen=pen)
            # cross.hide()
            self.image_view.getView().addItem(cross)
            self.crosses.append(cross)
    
    def toggle_rois(self, state):
        # Show/hide ROIs based on checkbox state
        
        if state == Qt.Checked:
            self.image_view.getView().scene().sigMouseClicked.connect(self.update_hexagon)
            # for cross in self.crosses:
            #     cross.show()
            self.is_hexagon_enable = True
        else:
            self.image_view.getView().scene().sigMouseClicked.disconnect(self.update_hexagon)
            for cross in self.crosses:
                cross.hide()
            self.is_hexagon_enable = False
    
    def xmodem_crc(self,hex_string):
        # Create a CRC-16 Xmodem instance
        crc_func = crcmod.predefined.mkPredefinedCrcFun('xmodem')
        # Convert hex string to bytes
        data_bytes = bytes.fromhex(hex_string)
        # Calculate the CRC
        crc_value = crc_func(data_bytes)
        # Convert CRC value to hexadecimal string
        crc_hex = format(crc_value, '04X')
        crc_hex=" ".join(crc_hex[i:i+2] for i in range(0, len(crc_hex), 2))
        return crc_hex
    
    def get_int_time_cmd(self,num):
        int_time = round(1e6*num/111.111)
        hex_prefix = "A3 57 00 10 00 03 "
        print('int_time hex:',hex(int_time)[2:])
        hex_string = hex(int_time)[2:].upper().zfill(6)
        # split the hex_string into bunch of two
        hex_string = " ".join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
        # calculate the crc
        crc = self.xmodem_crc(hex_prefix+hex_string)
        hex_string = hex_prefix + hex_string + " "+crc
        print('hex_string:',hex_string)
        hex_bytes = hex_string.split()
        print('hex_bytes:',hex_bytes)

        # Convert each byte to an integer
        int_bytes = [int(byte, 16) for byte in hex_bytes]
        
        # Convert the list of integers to a numpy array of np.uint8
        array = np.array(int_bytes).astype(np.uint8)
        print('int_bytes:',array)
        return array
    
    def get_window_cmd(self,start_col,start_row,num_cols, num_rows):
        cmd = {}
        cmd['window_init_write'] = 'A3 57 00 07 00 01 EE DB A4'
        
        hex_s = hex(start_col)[2:]#.upper().zfill(6)
        if len(hex(start_col)[2:]) % 2 == 1:
            hex_s = '0' + hex(start_col)[2:]
        else:
            hex_s = hex(start_col)[2:]
        hex_s = hex_s.upper()
        hex_s=" ".join(hex_s[i:i+2] for i in range(0, len(hex_s), 2))
        col_start = "A3 57 00 0E 00 02 00 "+hex_s
        crc = self.xmodem_crc(col_start)
        col_start = col_start + " "+crc
        cmd['col_start'] = col_start

        hex_s = hex(start_row)[2:]#.upper().zfill(6)
        if len(hex(start_row)[2:]) % 2 == 1:
            hex_s = '0' + hex(start_row)[2:]
        else:
            hex_s = hex(start_row)[2:]
        hex_s = hex_s.upper()
        hex_s=" ".join(hex_s[i:i+2] for i in range(0, len(hex_s), 2))
        row_start = "A3 57 00 0C 00 02 00 "+hex_s
        crc = self.xmodem_crc(row_start)
        row_start = row_start + " "+crc
        cmd['row_start'] = row_start

        hex_s = hex(num_cols)[2:]#.upper().zfill(6)
        if len(hex(num_cols)[2:]) % 2 == 1:
            hex_s = '0' + hex(num_cols)[2:]
        else:
            hex_s = hex(num_cols)[2:]
        hex_s = hex_s.upper()
        hex_s=" ".join(hex_s[i:i+2] for i in range(0, len(hex_s), 2))
        col = "A3 57 00 08 00 02 "+hex_s
        crc = self.xmodem_crc(col)
        col = col + " "+crc
        cmd['col'] = col

        hex_s = hex(num_rows)[2:]#.upper().zfill(6)
        if len(hex(num_rows)[2:]) % 2 == 1:
            hex_s = '0' + hex(num_rows)[2:]
        else:
            hex_s = hex(num_rows)[2:]
        hex_s = hex_s.upper()
        hex_s=" ".join(hex_s[i:i+2] for i in range(0, len(hex_s), 2))
        row = "A3 57 00 0A 00 02 "+hex_s
        crc = self.xmodem_crc(row)
        row = row + " "+crc
        cmd['row'] = row
        # print(cmd)
        cmd['soft_reset_read'] = 'A3 52 00 26 00 00 4A 1F'
        cmd['soft_reset1'] = "A3 57 00 26 00 01 FF 98 4E"
        cmd['soft_reset2'] = "A3 57 00 26 00 01 FE 88 6F"
        cmd['sensor_gain'] = "A3 52 0 007 00 00 FB E9"
        # print(cmd)
        return cmd
    
    def image_clicked(self, event):
        pos = event.pos()
        clicked_point = self.image_view.getImageItem().mapFromScene(pos)
        self.current_x = int(clicked_point.x())
        self.current_y = int(clicked_point.y())
        self.current_x = np.clip(self.current_x,0,640)
        self.current_y = np.clip(self.current_y,0,512)
        # self.update_image(self.image_view.getImageItem().image)
    
    def enable_serial(self,parameters):
        # ESTABLISH SERIAL CONNECTION
        parameters.SetEnumValue("BulkSelector", "Bulk0")
        parameters.SetEnumValue("BulkMode", "UART")
        parameters.SetEnumValue("BulkBaudRate", SPEED)
        # stop bits
        parameters.SetEnumValue("BulkNumOfStopBits", STOPBITS)
        # parity
        parameters.SetEnumValue("BulkParity", PARITY)
        parameters.SetBooleanValue("BulkLoopback", False)

        self.serial = eb.PvDeviceSerialPort()
        adaptor = eb.PvDeviceAdapter(self.device)
        result = self.serial.Open(adaptor, eb.PvDeviceSerialBulk0)
        if result.IsOK():
            print("Serial port opened")
        else:
            print("Serial port failed to open")
        rxbuffer_size = 256
        result = self.serial.SetRxBufferSize(rxbuffer_size)
        if result.IsOK():
            print("Buffer Size set to: ", rxbuffer_size)
        else:
            print("Buffer Size failed to set")
        result, size = self.serial.GetRxBufferSize()
        if result.IsOK():
            print("Buffer Size set to: ", size)
        else:
            print("Buffer Size failed to set")
        self.set_integration_time_default()
        self.set_window_default()
        
        
    
    def set_ebus_window(self,width,height):
        width_parameter =self.parameters.Get( "Width" )
        result, original_width = width_parameter.GetValue()
        result = width_parameter.SetValue(width)
        if result.IsOK():
            print("width set")
        # set height
        height_parameter = self.parameters.Get( "Height" )
        result, original_height = height_parameter.GetValue()
        result = height_parameter.SetValue(height)
        if result.IsOK():
            print("height set")
    
    
    def init_pointing_error_tab(self):
        pointing_error_layout = QVBoxLayout(self.pointing_error_tab)
        # create groupbox and grid layout
        pointing_error_group_box = QGroupBox("Pointing Error")
        pointing_error_grid_layout = QGridLayout()

        pointing_error_grid_layout.addWidget(self.combo_box_label,0,0)
        pointing_error_grid_layout.addWidget(self.combo_box,0,1)

        # add widgets to the grid layout inside groupbox
        for i in range(7):
            pointing_error_grid_layout.addWidget(self.pointing_error_labels[i],i+1,0)
            pointing_error_grid_layout.addWidget(self.pointing_error_textbox[i],i+1,1)

        pointing_error_grid_layout.addWidget(self.p_err_label,i+2,0)
        pointing_error_grid_layout.addWidget(self.p_err_out, i+2, 1)

        pointing_error_grid_layout.addWidget(self.lock_hexagon,i+3,0,1,2)

        # set the layout of the groupbox
        pointing_error_group_box.setLayout(pointing_error_grid_layout)
        # add the groupbox to the pointing_error_layout
        pointing_error_layout.addWidget(pointing_error_group_box)

        save_grp_box = QGroupBox("Saving")
        save_grid_layout = QGridLayout()
        save_grid_layout.addWidget(self.file_name)
        save_grid_layout.addWidget(self.save_csv_image)
        save_grid_layout.addWidget(self.save_image)
        save_grid_layout.addWidget(self.disp_hex_vertices)
        save_grp_box.setLayout(save_grid_layout)
        pointing_error_layout.addWidget(save_grp_box)


    def init_camera_control_tab(self):
        # Main layout for 'Camera Control' tab
        camera_control_layout = QVBoxLayout(self.camera_control_tab)

        # Group box for camera control buttons
        button_group_box = QGroupBox("Camera Control Buttons")
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_roi_button)
        button_group_box.setLayout(button_layout)
        camera_control_layout.addWidget(button_group_box)

        # Group box for ROI settings
        roi_group_box = QGroupBox("ROI Settings")
        roi_layout = QGridLayout()
        roi_layout.addWidget(self.roi_label, 0, 0)
        roi_layout.addWidget(self.roi_textbox, 0, 1)
        roi_layout.addWidget(self.roi_radius_label, 1, 0)
        roi_layout.addWidget(self.roi_radius_textbox, 1, 1)
        # roi_layout.addWidget(self.full_roi_label, 2, 0)
        # roi_layout.addWidget(self.full_roi_textbox, 2, 1)
        # roi_layout.addWidget(self.full_roi_radius_label, 3, 0)
        # roi_layout.addWidget(self.full_roi_radius_textbox, 3, 1)
        roi_layout.addWidget(self.full_roi_label, 0, 2)
        roi_layout.addWidget(self.full_roi_textbox, 0, 3)
        roi_layout.addWidget(self.full_roi_radius_label, 1, 2)
        roi_layout.addWidget(self.full_roi_radius_textbox, 1, 3)
        roi_layout.addWidget(self.eff_label, 2,0)
        roi_layout.addWidget(self.eff_textbox,2,1)
        roi_group_box.setLayout(roi_layout)
        camera_control_layout.addWidget(roi_group_box)

        # Group box for integration time controls
        int_time_group_box = QGroupBox("Integration Time Controls")
        int_time_layout = QGridLayout()
        int_time_layout.addWidget(self.integration_time_label, 0, 0)
        int_time_layout.addWidget(self.integration_time_input, 0, 1)
        int_time_layout.addWidget(self.set_int_time_button, 1, 0, 1, 2)
        int_time_layout.addWidget(self.display_int_time_button, 2, 0)
        int_time_layout.addWidget(self.current_integration_time_label, 2, 1)
        int_time_group_box.setLayout(int_time_layout)
        camera_control_layout.addWidget(int_time_group_box)

        # Group box for markers and checkboxes
        markers_group_box = QGroupBox("Markers and Checkboxes")
        markers_layout = QGridLayout()
        markers_layout.addWidget(self.set_markers_checkbox, 0, 0)
        markers_layout.addWidget(self.scatter_marker_checkbox, 0, 1)
        markers_layout.addWidget(self.show_roi_checkbox,1,0)
        markers_layout.addWidget(self.read_background_button, 1, 1)
        markers_layout.addWidget(self.slider_label,2,0)
        markers_layout.addWidget(self.zoom_slider,2,1)
        markers_group_box.setLayout(markers_layout)
        camera_control_layout.addWidget(markers_group_box)

        # Group box for window settings
        window_group_box = QGroupBox("Window Settings")
        window_layout = QGridLayout()
        window_layout.addWidget(self.n_cols_label, 0, 0)
        window_layout.addWidget(self.n_cols_input, 0, 1)
        window_layout.addWidget(self.n_rows_label, 1, 0)
        window_layout.addWidget(self.n_rows_input, 1, 1)
        window_layout.addWidget(self.start_col_label, 2, 0)
        window_layout.addWidget(self.start_col_input, 2, 1)
        window_layout.addWidget(self.start_row_label, 3, 0)
        window_layout.addWidget(self.start_row_input, 3, 1)
        window_layout.addWidget(self.set_window_button, 4, 0, 1, 2)
        window_layout.addWidget(self.flip_img_label,5,0)
        window_layout.addWidget(self.flip_img_cb,5,1)
        window_group_box.setLayout(window_layout)
        camera_control_layout.addWidget(window_group_box)
    
    def set_parameter(self, parameter_name, new_value, label):
        label.setText(f'{parameter_name} set to {new_value}')

    def set_gain(self):
        new_value = float(self.gain_input.text())
        self.set_parameter('Gain', new_value, self.gain_label)

    def set_perb_ul(self):
        new_value = float(self.perb_ul_input.text())
        self.set_parameter('Perb UL', new_value, self.perb_ul_label)

    def set_perb_ll(self):
        new_value = float(self.perb_ll_input.text())
        self.set_parameter('Perb LL', new_value, self.perb_ll_label)

    def init_phase_control_tab(self):
        # Add widgets for the 'Phase Control' tab
        phase_control_layout = QVBoxLayout(self.phase_control_tab)

        # Create input widgets
        self.gain_label = QLabel('', self.phase_control_tab)
        gain_label = QLabel('Gain:')
        self.gain_input = QLineEdit(self.phase_control_tab)
        self.gain_input.setPlaceholderText('Enter float value')
        self.gain_input.setText('50')  # Set default value

        self.perb_ul_label = QLabel('', self.phase_control_tab)
        perb_ul_label = QLabel('Perb UL:')
        self.perb_ul_input = QLineEdit(self.phase_control_tab)
        self.perb_ul_input.setPlaceholderText('Enter float value')
        self.perb_ul_input.setText('0.2')  # Set default value

        self.perb_ll_label = QLabel('', self.phase_control_tab)
        perb_ll_label = QLabel('Perb LL:')
        self.perb_ll_input = QLineEdit(self.phase_control_tab)
        self.perb_ll_input.setPlaceholderText('Enter float value')
        self.perb_ll_input.setText('0.05')  # Set default value

        # Create "Set" buttons for each input
        set_gain_button = QPushButton('Set Gain', self.phase_control_tab)
        set_gain_button.clicked.connect(self.set_gain)

        set_perb_ul_button = QPushButton('Set Perb UL', self.phase_control_tab)
        set_perb_ul_button.clicked.connect(self.set_perb_ul)

        set_perb_ll_button = QPushButton('Set Perb LL', self.phase_control_tab)
        set_perb_ll_button.clicked.connect(self.set_perb_ll)

        # Create the start control checkbox
        # self.start
        # _control_checkbox.stateChanged.connect(self.start_control_dummy_function)

        # Add widgets to the layout
        phase_control_layout.addWidget(gain_label)
        phase_control_layout.addWidget(self.gain_input)
        phase_control_layout.addWidget(set_gain_button)  # Add "Set" button
        phase_control_layout.addWidget(self.gain_label)  # Add label below "Set" button

        phase_control_layout.addWidget(perb_ul_label)
        phase_control_layout.addWidget(self.perb_ul_input)
        phase_control_layout.addWidget(set_perb_ul_button)  # Add "Set" button
        phase_control_layout.addWidget(self.perb_ul_label)  # Add label below "Set" button

        phase_control_layout.addWidget(perb_ll_label)
        phase_control_layout.addWidget(self.perb_ll_input)
        phase_control_layout.addWidget(set_perb_ll_button)  # Add "Set" button
        phase_control_layout.addWidget(self.perb_ll_label)  # Add label below "Set" button

        phase_control_layout.addWidget(self.start_control_checkbox)



    def start_control_dummy_function(self, state):
        if state == Qt.Checked:
            print('Starting control')
            # print gain, perb_ul, perb_ll

        else:
            print('Stopping control')
    # def start_control_dummy_function(self, state):
    #     if state == Qt.Checked:
    #         print('Starting control')
    #         gain = float(self.gain_input.text())
    #         perb_ul = float(self.perb_ul_input.text())
    #         perb_ll = float(self.perb_ll_input.text())
    #         # Execute the compilation and run commands with subprocess
    #         compile_command = 'gcc D:\\NIDAQ\\C_codes\\spgd_v4.c -o D:\\NIDAQ\\C_codes\\spgd_v4_test -L"C:\\Program Files (x86)\\National Instruments\\NI-DAQ\\DAQmx ANSI C Dev\\lib\\msvc" -I"C:\\Program Files (x86)\\National Instruments\\NI-DAQ\\DAQmx ANSI C Dev\\include" -lNIDAQmx'
    #         subprocess.run(compile_command, shell=True, check=True)

    #         run_command = 'D:\\NIDAQ\\C_codes\\spgd_v4_test.exe'+f' {gain} {perb_ul} {perb_ll}'
    #         self.c_process = subprocess.Popen(run_command, shell=True)
    #         print('Control started ..')
    #     else:
    #         print('Stopping control')
    #         # Stop the C code by terminating the process
    #         if hasattr(self, 'c_process') and self.c_process.poll() is None:
    #             self.c_process.communicate()
    #             print('Control stopped ..')
    
    def show_rois(self,state):
        if state == Qt.Checked:
            self.roi.show()
            self.full_roi.show()
            self.roi_flag=True
        else:
            self.roi.hide()
            self.full_roi.hide()
    
    def toggle_markers(self, state):
        # Toggle visibility of InfiniteLines based on checkbox state
        if state == Qt.Checked:
            # Create new InfiniteLines
            self.horizontal_line = pg.InfiniteLine(angle=0, movable=False, pen='g')
            self.vertical_line = pg.InfiniteLine(angle=90, movable=False, pen='g')

            # Add InfiniteLines to the image view
            self.image_view.getView().addItem(self.horizontal_line)
            self.image_view.getView().addItem(self.vertical_line)

            # Connect events to update InfiniteLines on mouse click
            self.image_view.getView().scene().sigMouseClicked.connect(self.update_infinite_lines)
        else:
            # Remove InfiniteLines and disconnect events
            if self.horizontal_line:
                self.image_view.getView().removeItem(self.horizontal_line)
            if self.vertical_line:
                self.image_view.getView().removeItem(self.vertical_line)
            self.image_view.getView().scene().sigMouseClicked.disconnect(self.update_infinite_lines)

    def update_infinite_lines(self, event):
        pos = event.pos()
        clicked_point = self.image_view.getImageItem().mapFromScene(pos)

        if self.horizontal_line:
            self.horizontal_line.setPos(self.current_y)#
        if self.vertical_line:
            self.vertical_line.setPos(self.current_x)#
    
    def set_int_time(self,int_time):
        # lock the threads
        # with QMutexLocker(self.mutex):

        if self.serial.IsOpened():
            cmd = self.get_int_time_cmd(int_time)
            self.serial.FlushRxBuffer()
            result,bytesWritten=self.serial.Write(cmd)
            print('num of bytes written:',bytesWritten)
            if result.IsOK():
                print("Serial port write successful")
            else:
                print("Serial port write failed")
            
            result,info,num_bits = self.serial.Read(8,1000)
            if result.IsOK():
                print("Serial port read successful")
            else:
                print("Serial port read failed ", result.GetCodeString().GetAscii(), result.GetDescription().GetAscii())
                
            success=all(x == y for x,y in zip(info[0:2], [163,0]))
            if success ==True:
                print("Integration time time set SUCCESSFULLY to:", int_time, "ms \n")
            else:
                print('Failed to set integration time .. \n')
        else:
            print('Serial Port not open')


    def read_int_time(self):
        # lock the threads
        hex_str = 'A3 52 00 10 00 00 3D 1A'
        hex_array = hex_str.split()
        int_array = [int(byte, 16) for byte in hex_array]
        hex_array = np.array(int_array).astype(np.uint8)
        print(hex_array)
        result,bytesWritten=self.serial.Write(hex_array)
        print('num of bytes written:',bytesWritten)
        if result.IsOK():
            print("Serial port write successful")
        else:
            print("Serial port write failed")
        result,info,num_bits = self.serial.Read(11,1000)
        # print('read:',info, 'n:', num_bits)
        # print hex of info
        # print('read:',[hex(i) for i in info])
        if result.IsOK():
            print("Serial port read successful")
        else:
            print("Serial port read failed ", result.GetCodeString().GetAscii(), result.GetDescription().GetAscii())
        success=all(x == y for x,y in zip(info[0:2], [163,0]))
        if success ==True:
            print("Integration time read SUCCESSFULLY")
        else:
            print('Failed to read integration time .. \n')
        hex_str = [hex(i)[2:].upper().zfill(2) for i in info]
        num_str=''
        for idx in range(6,9):
            num_str+=hex_str[idx]
        # flag = np.isclose(int(num_str,16)*111.111/int(1e6),self.current_integration_time,rtol=0.01)
        red_int_time = int(num_str,16)*111.111/int(1e6)

        return red_int_time

    def set_integration_time_default(self):
        # Set default integration time
        self.integration_time_input.setText(str(self.current_integration_time))
        self.set_int_time(self.current_integration_time)
        print('Set integration time as ',self.read_int_time())

    def set_window_params(self,start_col,start_row,width,height):

        cmd_dict = self.get_window_cmd(start_col,start_row,width,height)
        for key in cmd_dict:
            print('************** Setting ',key,'************** \n')
            hex_array = cmd_dict[key].split()
            int_array = [int(byte, 16) for byte in hex_array]
            array = np.array(int_array).astype(np.uint8)
            self.serial.FlushRxBuffer()
            result,bytesWritten=self.serial.Write(array)
            # time.sleep(0.1)
            print(bytesWritten, 'bytes written')
            print('written: ',[hex(i) for i in array])

            self.serial.FlushRxBuffer()
            if key == 'sensor_gain':            
                result,info,num_bits = self.serial.Read(9,1000)
            else:
                result,info,num_bits = self.serial.Read(8,1000)
            # print('read:',info, 'n:', num_bits)
            # print hex of info
            # print('read:',[hex(i) for i in info])
            if result.IsOK():
                print("Serial port read successful")
            else:
                print("Serial port read failed ", result.GetCodeString().GetAscii(), result.GetDescription().GetAscii())
            success=all(x == y for x,y in zip(info[0:2], [163,0]))
            if success == True:
                print(key,"set SUCCESSFULLY \n")
            else:
                print(key,"failed to set \n")
    

    def set_window_default(self):
        # Set default values for n_cols, n_rows, start_row, and start_col
        self.n_cols_input.setText(str(self.n_cols))
        self.n_rows_input.setText(str(self.n_rows))
        self.start_col_input.setText(str(self.start_col))
        self.start_row_input.setText(str(self.start_row))
        self.set_window_params(self.start_col,self.start_row,self.n_cols,self.n_rows)
        self.set_ebus_window(self.n_cols,self.n_rows)

    def find_max_coordinates(self,matrix):
        flattened_index = np.argmax(matrix)
        rows, cols = np.unravel_index(flattened_index, matrix.shape)
        return rows, cols
    
    def find_centroid_coord(self,matrix):
        rows,cols = np.indices(matrix.shape)

        centroid_x = int(np.average(cols,weights=matrix))
        centroid_y = int(np.average(rows,weights=matrix))

        return centroid_x, centroid_y
    
    def find_appr_coord(self, combo_box):
        selected_option = combo_box.currentText()
        if selected_option == 'Use Max':
            self.find_coord = self.find_max_coordinates
        elif selected_option == 'Use Centroid':
            self.find_coord = self.find_centroid_coord
    
    def img_transform(self,combo_box):
        selected_option = combo_box.currentText()
        if selected_option == 'None':
            self.transform = None
        elif selected_option == 'UD':
            self.transform = np.flipud
        elif selected_option == 'LR':
            self.transform = np.fliplr
        elif selected_option == 'LR-UD':
            self.transform = 1
        elif selected_option == 'UD-LR':
            self.transform = 2
    

    def update_pointing_error(self, image):
        # print('updating..')
        # print(self.hexagon_vertices)
        current_time = QDateTime.currentDateTime()
        elapsed_sec = self.start_time.msecsTo(current_time)/1000
        hexagon_vertices = np.array(self.hexagon_vertices).astype(int)
        dist_array = []
        for qline,vertex in zip(self.pointing_error_textbox,hexagon_vertices):
            if vertex[0]-self.knn >=0 and vertex[0]+self.knn<=640 and vertex[1]-self.knn >=0 and vertex[1]+self.knn<=512:
                img = image[vertex[0]-self.knn:vertex[0]+self.knn,vertex[1]-self.knn:vertex[1]+self.knn]
                # calculate euclidean distance between vertex and coordinate correspondng to max of the img
                max_coord = self.find_coord(img)
                dist = np.sqrt(np.sum((np.array(max_coord).ravel()-np.array([self.knn,self.knn]).ravel())**2))#np.round(np.linalg.norm(max_coord-vertex),2)
                dist = dist*15/2.8
                dist_array.append(dist)
                dist = np.round(dist,2)
                qline.setText(str(dist))
            else:
                pass
        if len(dist_array)>0:
            dist_array = np.array(dist_array)
            p_err = dist_array#*15/2.8
            rms_err = np.sqrt(np.mean(p_err[1:]**2))
            dist_array = np.append(np.array([elapsed_sec]),dist_array)
            self.p_err_hist.append(np.append(dist_array,rms_err))
            rms_err = np.round(rms_err,2)
            self.p_err_out.setText(str(rms_err))
            
    
    def hexagon_lock(self):
        vertex = np.array(self.hexagon_vertices[0]).astype(int)

        img = self.image[vertex[0]-self.knn:vertex[0]+self.knn,vertex[1]-self.knn:vertex[1]+self.knn]
        max_coord = self.find_coord(img)

        angle_offset = np.pi / 3 + np.pi+ np.deg2rad(5)  # Offset to start the hexagon from the top
        
        hexagon_center = np.array([vertex[0],vertex[1]])+np.array([max_coord[0],max_coord[1]])-np.array([self.knn,self.knn])
        hexagon_radius = 125
        self.hexagon_vertices = [
            (
                hexagon_center[0] + hexagon_radius * np.cos(angle_offset - i * 2 * np.pi / 6),
                hexagon_center[1] + hexagon_radius * np.sin(angle_offset - i * 2 * np.pi / 6),
            )
            for i in range(6)
        ]
        self.hexagon_vertices.insert(0,(hexagon_center[0], hexagon_center[1]))

        # Clear existing crosses
        for cross in self.crosses:
            self.image_view.getView().removeItem(cross)

        # Create new Cross-shaped ScatterPlotItems at updated hexagon vertices
        self.crosses = []
        pen = pg.mkPen(color=QColor(0,255,0))
        for vertex in self.hexagon_vertices:
            cross = pg.ScatterPlotItem()
            cross.addPoints(x=[vertex[0]], y=[vertex[1]], symbol='+', size=20, pen=pen)
            # cross.hide()
            self.image_view.getView().addItem(cross)
            self.crosses.append(cross)
    
    def save_csv_on_click(self):
        name = 'C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'.csv'
        img = self.image_view.image
        img = np.transpose(img)
        np.savetxt(name,img)

        hex_array = np.array(self.hexagon_vertices)
        

        hexagon_vertices = np.array(self.hexagon_vertices).astype(int)
        max_dist_array = []
        centroid_dist_array = []

        for qline,vertex in zip(self.pointing_error_textbox,hexagon_vertices):
            if vertex[0]-self.knn >=0 and vertex[0]+self.knn<=640 and vertex[1]-self.knn >=0 and vertex[1]+self.knn<=512:
                img = self.image[vertex[0]-self.knn:vertex[0]+self.knn,vertex[1]-self.knn:vertex[1]+self.knn]
                # calculate euclidean distance between vertex and coordinate correspondng to max of the img
                max_coord = self.find_max_coordinates(img)
                max_dist = np.sqrt(np.sum((np.array(max_coord).ravel()-np.array([self.knn,self.knn]).ravel())**2))#np.round(np.linalg.norm(max_coord-vertex),2)
                max_dist = max_dist*15/2.8
                max_dist_array.append(max_dist)

                max_coord = self.find_centroid_coord(img)
                centroid_dist = np.sqrt(np.sum((np.array(max_coord).ravel()-np.array([self.knn,self.knn]).ravel())**2))#np.round(np.linalg.norm(max_coord-vertex),2)
                centroid_dist = centroid_dist*15/2.8
                centroid_dist_array.append(centroid_dist)
            else:
                pass
        
        if len(max_dist_array)>0 and len(centroid_dist_array)>0:
            max_dist_array = np.array(max_dist_array)
            max_p_err = max_dist_array
            max_rms_err = np.sqrt(np.mean(max_p_err[1:]**2))
            # max_rms_err = np.round(max_rms_err,2)

            centroid_dist_array = np.array(centroid_dist_array)
            centroid_p_err = centroid_dist_array
            centroid_rms_err = np.sqrt(np.mean(centroid_p_err[1:]**2))
            # centroid_rms_err = np.round(centroid_rms_err,2)
        
            p_err_data = np.zeros((2,len(max_dist_array)+1))
            p_err_data[0,0:len(max_dist_array)] = max_p_err
            p_err_data[0,len(max_dist_array)] = max_rms_err

            p_err_data[1,0:len(max_dist_array)] = centroid_p_err
            p_err_data[1,len(max_dist_array)] = centroid_rms_err



            np.savetxt('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_p_err_data.csv',p_err_data, delimiter=',')
            np.savetxt('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_vertices.csv', hex_array, delimiter=',')

            np.savetxt('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_p_err_hist.csv',np.array(self.p_err_hist), delimiter=',')

            plt.figure(figsize=(10,7))
            plt.plot(np.array(self.p_err_hist)[:,0],np.array(self.p_err_hist)[:,-1])
            plt.xlabel('Time (s)',fontsize=14)
            plt.ylabel('RMS Pointing Error ' + r'$\mu rad$', fontsize=14)
            plt.grid()
            plt.xticks(fontsize=14)
            plt.yticks(fontsize=14)
            plt.savefig('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_p_err_hist.png')
            plt.clf()
            plt.close()

        else:
            np.savetxt('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_efficiency_hist.csv',np.array(self.eff_hist), delimiter=',')
            np.savetxt('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_roi_hist.csv',np.array(self.roi_hist), delimiter=',')

            plt.figure(figsize=(10,7))
            plt.plot(np.array(self.eff_hist)[:,0],100*np.array(self.eff_hist)[:,1])
            plt.xlabel('Time (s)',fontsize=14)
            plt.ylabel('Efficiency (%)', fontsize=14)
            plt.grid()
            plt.ylim(0,26)
            plt.xticks(fontsize=14)
            plt.yticks(fontsize=14)
            plt.savefig('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'_efficiency_hist.png')
            plt.clf()
            plt.close()

        

    def save_on_click(self):
        img = self.image_view.image
        img = np.transpose(img)
        plt.figure()
        plt.imshow(img,cmap='jet')
        plt.colorbar()
        plt.tight_layout()
        plt.savefig('C:/Users/bs-iitm/OneDrive - smail.iitm.ac.in/my gui/data/'+self.file_name.text()+'.png')
        plt.clf()
    
    def disp_hex_on_click(self):
        print(self.hexagon_vertices)

    def update_image(self, image):

        current_time = QDateTime.currentDateTime()
        elapsed_sec = self.start_time.msecsTo(current_time)
        self.time_axis.append(elapsed_sec*1e-3)

        if self.transform is not None:
            if self.transform == 2:
                image = np.fliplr(np.flipud(image))#self.transform(image)
            elif self.transform ==1:
                image = np.flipud(np.fliplr(image))
            else:
                image = self.transform(image)
        
        self.image = image
        shape_x,shape_y = self.image.shape
        self.current_x = np.clip(self.current_x,0,shape_x)
        self.current_y = np.clip(self.current_y,0,shape_y)
        # self.image_view.getView().setLimits(xMin=0,xMax=shape_x,yMin=0,yMax=shape_y)
        self.image_view.setImage(image, levels=(0, 255),autoHistogramRange=False)
        if self.zoom_factor == 1:
            self.image_view.getView().setLimits(xMin=0,xMax=shape_x,yMin=0,yMax=shape_y)
        else:
            #, levels=(0, 255),autoHistogramRange=False
            w,h = self.image_view.getImageItem().width()/self.zoom_factor,self.image_view.getImageItem().height()/self.zoom_factor
            center_x,center_y = self.current_x,self.current_y
            self.image_view.getView().setRange(xRange=[center_x-w/2,center_x+w/2],yRange=[center_y-h/2,center_y+h/2])

        self.image_view.getView().showGrid(x=True, y=True)
        self.image_view.getView().getAxis('left').setStyle(tickFont=pg.QtGui.QFont("Arial",8))
        self.image_view.getView().getAxis('left').setTextPen(pg.mkPen(color=(255,255,255)))
        self.image_view.getView().getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont("Arial",8))
        self.image_view.getView().getAxis('bottom').setTextPen(pg.mkPen(color=(255,255,255)))

        
        x_profile = image[:, self.current_y]
        y_profile = image[self.current_x, :]

        self.xprofile_plot.clear()
        self.yprofile_plot.clear()

        x_curve = self.xprofile_plot.plot(x_profile, pen='r', name='X profile')
        y_curve = self.yprofile_plot.plot(y_profile, pen='g', name='Y profile')

        # Set y limit to 255 for the line profile plots
        self.yprofile_plot.setYRange(0, 255)
        self.xprofile_plot.setYRange(0, 255)

        # Add grid lines to the line profiles
        self.xprofile_plot.showGrid(x=True, y=True)
        self.xprofile_plot.getAxis('left').setStyle(tickFont=pg.QtGui.QFont("Arial",10))
        self.xprofile_plot.getAxis('left').setTextPen(pg.mkPen(color=(255,255,255)))
        self.xprofile_plot.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont("Arial",10))
        self.xprofile_plot.getAxis('bottom').setTextPen(pg.mkPen(color=(255,255,255)))
        self.yprofile_plot.showGrid(x=True, y=True)
        self.yprofile_plot.getAxis('left').setStyle(tickFont=pg.QtGui.QFont("Arial",10))
        self.yprofile_plot.getAxis('left').setTextPen(pg.mkPen(color=(255,255,255)))
        self.yprofile_plot.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont("Arial",10))
        self.yprofile_plot.getAxis('bottom').setTextPen(pg.mkPen(color=(255,255,255)))

        self.update_pointing_error(image)

        # Increase the fontsize of x and y ticks
        styles = {'color': '#ffffff', 'font-size': '12pt'}
        self.xprofile_plot.setLabel('left', 'Intensity', **styles)
        self.xprofile_plot.setLabel('bottom', 'X', **styles)
        self.yprofile_plot.setLabel('left', 'Intensity', **styles)
        self.yprofile_plot.setLabel('bottom', 'Y', **styles)
        

        # Get the region inside the ROI using the CircleROI's getArrayRegion method
        roi_region = self.roi.getArrayRegion(image,
                                            self.image_view.getImageItem(),
                                            axes=(0, 1),
                                            returnMappedCoords=False)

        # Update the sum plot with the sum inside ROI as a function of time
        roi_sum = np.round(np.sum(roi_region)*(15e-3*15e-3),3)
        self.roi_textbox.setText(str(np.round(roi_sum-self.roi_bg_value,2)))
        self.roi_radius_textbox.setText(str(np.round(self.roi.size()[0]*0.5*15))+' um')

        self.sum_data.append((len(self.sum_data), roi_sum-self.roi_bg_value))

        if len(self.time_axis) > 2500:
            self.time_axis.pop(0)
        if len(self.sum_data) > 2500:
            self.sum_data.pop(0)
        self.sum_plot.clear()#np.arange(len(self.sum_data))
        self.sum_plot.plot(np.array(self.time_axis), [item[1] for item in self.sum_data], pen='y')
        self.sum_plot.setLabel('left', 'Sum Inside ROI', **styles)
        self.sum_plot.setLabel('bottom', 'Time (s)', **styles)
        self.sum_plot.showGrid(x=True, y=True)
        self.sum_plot.getAxis('left').setStyle(tickFont=pg.QtGui.QFont("Arial",11))
        self.sum_plot.getAxis('left').setTextPen(pg.mkPen(color=(255,255,255)))
        self.sum_plot.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont("Arial",11))
        self.sum_plot.getAxis('bottom').setTextPen(pg.mkPen(color=(255,255,255)))
        full_roi_region = self.full_roi.getArrayRegion(image,
                                            self.image_view.getImageItem(),
                                            axes=(0, 1),
                                            returnMappedCoords=False)
        full_roi_sum = np.round(np.sum(full_roi_region)*(15e-3*15e-3),3)
        self.full_roi_textbox.setText(str(np.round(full_roi_sum-self.full_roi_bg_value,2)))
        self.full_roi_radius_textbox.setText(str(np.round(self.full_roi.size()[0]*0.5*15))+' um')

        self.eff_textbox.setText(str(np.round(100*((roi_sum-self.roi_bg_value)/(full_roi_sum-self.full_roi_bg_value)),3)))

        self.eff_hist.append([elapsed_sec/1000,(roi_sum-self.roi_bg_value)/(full_roi_sum-self.full_roi_bg_value)])

        self.roi_hist.append([elapsed_sec*1e-3, (roi_sum-self.roi_bg_value), (full_roi_sum-self.full_roi_bg_value)])

        self.full_sum_data.append((len(self.full_sum_data), (roi_sum-self.roi_bg_value)/(full_roi_sum-self.full_roi_bg_value)))
        if len(self.full_sum_data) > 2500:
            self.full_sum_data.pop(0)
        self.full_sum_plot.clear()
        kernel = np.ones(20)/20
        # result = np.convolve(np.array([item[1] for item in self.full_sum_data]),kernel, mode='same')
        # self.full_sum_plot.plot(np.arange(len(result)), result, pen='y') np.arange(len(self.full_sum_data))
        self.full_sum_plot.plot(np.array(self.time_axis), [item[1] for item in self.full_sum_data], pen='y')
        self.full_sum_plot.setLabel('left', 'Efficiency', **styles)
        self.full_sum_plot.setLabel('bottom', 'Time (s)', **styles)
        self.full_sum_plot.showGrid(x=True, y=True)
        self.full_sum_plot.setYRange(0,0.25)
        self.full_sum_plot.getAxis('left').setStyle(tickFont=pg.QtGui.QFont("Arial",11))
        self.full_sum_plot.getAxis('left').setTextPen(pg.mkPen(color=(255,255,255)))
        self.full_sum_plot.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont("Arial",11))
        self.full_sum_plot.getAxis('bottom').setTextPen(pg.mkPen(color=(255,255,255)))

    def clear_roi_plot(self):
        self.sum_data = []
        self.sum_plot.clear()

        self.full_sum_data = []
        self.full_sum_plot.clear()

        self.eff_hist = []
        self.p_err_hist = []
        self.roi_hist = []

        self.time_axis=[]
        self.start_time = QDateTime.currentDateTime()

    def set_integration_time(self):
        try:
            prev_integration_time = self.current_integration_time
            new_integration_time = float(self.integration_time_input.text())
            print(f'Integration time changed from {prev_integration_time} to {new_integration_time}')
            self.current_integration_time = new_integration_time
            self.set_int_time(self.current_integration_time)
            # Update the label with the new integration time only when set_integration_time is called
            # self.current_integration_time_label.setText(f'Current Integration Time: {self.current_integration_time}')

            print('Process completed')
        except Exception as e:
            print(f"Exception in serial communication thread: {e}")
    
    def display_integration_time(self):
        red_int_time = self.read_int_time()
        # Display the current integration time when the "Display Int. Time" button is clicked

        self.current_integration_time_label.setText(f'Current Integration Time: {red_int_time} ms')

    def set_window(self):
        try:

            prev_n_cols = self.n_cols
            prev_n_rows = self.n_rows
            prev_start_col = self.start_col
            prev_start_row = self.start_row

            new_n_cols = int(self.n_cols_input.text())
            new_n_rows = int(self.n_rows_input.text())
            new_start_col = int(self.start_col_input.text())
            new_start_row = int(self.start_row_input.text())

            if prev_n_cols != new_n_cols:
                print(f'n_cols changed from {prev_n_cols} to {new_n_cols}')
            if prev_n_rows != new_n_rows:
                print(f'n_rows changed from {prev_n_rows} to {new_n_rows}')
            if prev_start_col != new_start_col:
                print(f'Start Col changed from {prev_start_col} to {new_start_col}')
            if prev_start_row != new_start_row:
                print(f'Start Row changed from {prev_start_row} to {new_start_row}')

            # Update instance variables with new values
            self.n_cols = new_n_cols
            self.n_rows = new_n_rows
            self.start_col = new_start_col
            self.start_row = new_start_row

            self.set_window_params(self.start_col,self.start_row,self.n_cols,self.n_rows)
            self.set_ebus_window(self.n_cols,self.n_rows)

            print('Process completed')
        except ValueError:
            print('Invalid input. Please enter integer values.')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)
    gui = GUI()
    window = QMainWindow()
    icon_path = 'icon.ico'
    pixmap = QPixmap(icon_path)

    # Set application icon
    icon = QIcon(pixmap)
    window.setWindowIcon(icon)
    sys.exit(app.exec_())
