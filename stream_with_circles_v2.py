'''
*****************************************************************************
*
*   Copyright (c) 2020, Pleora Technologies Inc., All rights reserved.
*
*****************************************************************************

Shows how to use a PvStream object to acquire images from a GigE Vision or
USB3 Vision device.
'''

import numpy as np
import eBUS as eb
import lib.PvSampleUtils as psu
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
BUFFER_COUNT = 50
global Height, Width
# plt.ion()
kb = psu.PvKb()

opencv_is_available=True
try:
    # Detect if OpenCV is available
    import cv2
    opencv_version=cv2.__version__
except:
    opencv_is_available=False
    print("Warning: This sample requires python3-opencv to display a window")

def connect_to_device(connection_ID):
    # Connect to the GigE Vision or USB3 Vision device
    print("Connecting to device.")
    result, device = eb.PvDevice.CreateAndConnect(connection_ID)
    if device == None:
        print(f"Unable to connect to device: {result.GetCodeString()} ({result.GetDescription()})")
    return device

def open_stream(connection_ID):
    # Open stream to the GigE Vision or USB3 Vision device
    print("Opening stream from device.")
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

def sum_of_intensity_within_circle(image_data, radius_mm):
    pixel_size = 15e-3  # Pixel size in mm
    # Calculate the radius in pixels
    radius_pixels = radius_mm / pixel_size

    # Get the center of the image
    center = (image_data.shape[1] // 2, image_data.shape[0] // 2)

    # Create a mask for the circle
    y, x = np.ogrid[-center[1]:image_data.shape[0]-center[1], -center[0]:image_data.shape[1]-center[0]]
    mask = x*x + y*y <= radius_pixels*radius_pixels

    # Calculate the sum of pixel intensities within the circle
    sum_intensity = np.sum(image_data[mask])

    return sum_intensity

def process_multiple_circles(image_data, centers, radius_mm):
    pixel_size = 15e-3  # Pixel size in mm
    # Calculate the radius in pixels
    radius_pixels = int(radius_mm / pixel_size)
    centers = centers.astype(int)
    sum_intensities = []
    idx = 0
    for center in centers:
        # Create a mask for the circle
        y, x = np.ogrid[-center[1]:image_data.shape[0]-center[1], -center[0]:image_data.shape[1]-center[0]]
        mask = x*x + y*y <= radius_pixels*radius_pixels

        # Calculate the sum of pixel intensities within the circle
        sum_intensity = np.sum(image_data[mask])*(pixel_size**2)
        sum_intensities.append(sum_intensity)

        
    return sum_intensities

def generate_hexagon_vertices(center, radius):
    # Define the angles for the vertices of the hexagon
    angles_deg = np.array([60 * i for i in range(6)])
    angles_rad = np.radians(angles_deg)

    # Calculate the coordinates of the vertices
    x = center[0] + radius * np.cos(angles_rad)
    y = center[1] + radius * np.sin(angles_rad)
    vertices = np.column_stack([x, y])

    # Include the center point
    vertices = np.vstack([vertices, center])
    # print(vertices)

    return vertices

def acquire_images(device, stream):
    # Get device parameters need to control streaming
    device_params = device.GetParameters()
    mail_lobe=[]

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

    fig, ax = plt.subplots()
    im = ax.imshow(np.zeros((Height, Width)))

    # Create the animation
    animation = FuncAnimation(fig, update_animation, fargs=(im, stream, doodle), blit=False)

    # Start the animation
    plt.show()

    # Wait for keyboard input loop to finish
    kb.start()
    while not kb.is_stopping():
        # Continue looping until a key is pressed
        pass
    kb.stop()

    # Close the plot window after stopping the keyboard input loop
    plt.close()

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
    return mail_lobe

def update_animation(im, stream, doodle):
    # Retrieve next pvbuffer
    result, pvbuffer, operational_result = stream.RetrieveBuffer(1000)

    if result.IsOK():
        if operational_result.IsOK():
            payload_type = pvbuffer.GetPayloadType()

            if payload_type == eb.PvPayloadTypeImage:
                image = pvbuffer.GetImage()
                image_data = image.GetDataPointer()

                if opencv_is_available and image.GetPixelType() == eb.PvPixelMono8:
                    image_data = cv2.applyColorMap(image_data, cv2.COLORMAP_JET)

                im.set_array(image_data)
                plt.draw()
                plt.pause(1 / 300)  # Adjust the pause duration based on the frame rate

            # Re-queue the pvbuffer in the stream object
            stream.QueueBuffer(pvbuffer)

        else:
            # Non OK operational result
            print(f"{doodle[doodle_index]} {operational_result.GetCodeString()}       ", end='\r')

    else:
        # Retrieve pvbuffer failure
        print(f"{doodle[doodle_index]} {result.GetCodeString()}      ", end='\r')

    doodle_index = (doodle_index + 1) % 6

print("PvStreamSample:")

connection_ID = psu.PvSelectDevice()
if connection_ID:
    device = connect_to_device(connection_ID)
    # print(dir(device.GetParameters()))
    width=640
    height=512
    x_offset=0
    y_offset=0
    
    Height,Width = height,width 
    # print row and column start and stop
    print('Row start:',y_offset,'Row stop:',y_offset+height, 'Column start:',x_offset,'Column stop:',x_offset+width)
    parameters = device.GetParameters()
    print(type(parameters))
    width_parameter = parameters.Get( "Width" )
    result, original_width = width_parameter.GetValue()
    result = width_parameter.SetValue(width)
    if result.IsOK():
        print("width set")
    # set height
    height_parameter = parameters.Get( "Height" )
    result, original_height = height_parameter.GetValue()
    result = height_parameter.SetValue(height)
    if result.IsOK():
        print("height set")
    # set OffsetX
    x_offset_parameter = parameters.Get( "OffsetX" )
    result, original_x_offset = x_offset_parameter.GetValue()
    result = x_offset_parameter.SetValue(x_offset)
    if result.IsOK():
        print("x_offset set")
    # set OffsetY
    y_offset_parameter = parameters.Get( "OffsetY" )
    result, original_y_offset = y_offset_parameter.GetValue()
    result = y_offset_parameter.SetValue(y_offset)
    if result.IsOK():
        print("y_offset set")   
    
    if device:
        stream = open_stream(connection_ID)
        if stream:
            configure_stream(device, stream)
            buffer_list = configure_stream_buffers(device, stream)
            main_lobe = acquire_images(device, stream)
            buffer_list.clear()
            
            # Close the stream
            print("Closing stream")
            stream.Close()
            eb.PvStream.Free(stream);    

        # Disconnect the device
        print("Disconnecting device")
        device.Disconnect()
        eb.PvDevice.Free(device)
# plot main_lobe
# plt.plot(main_lobe)
# plt.grid()
# plt.show()
print("<press a key to exit>")
kb.start()
kb.getch()
kb.stop()
