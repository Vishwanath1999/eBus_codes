import os
import numpy as np
import eBUS as eb
import lib.PvSampleUtils as psu
import cv2
import datetime
import pandas as pd

BUFFER_COUNT = 50
IMAGE_DIR = 'images'

kb = psu.PvKb()
opencv_is_available=True
try:
    # Detect if OpenCV is available
    import cv2
    opencv_version=cv2.__version__
except:
    opencv_is_available=False
    print("Warning: This sample requires python3-opencv to display a window")

# Check if the directory exists, if not, create it
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

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

# def process_pv_buffer(pvbuffer, image_count):
#     """
#     Use this method to process the buffer with your own algorithm.
#     """
#     print_string_value = "Image Processing"

#     image = pvbuffer.GetImage()
#     pixel_type = image.GetPixelType()

#     # Verify we can handle this format, otherwise continue.
#     if (pixel_type != eb.PvPixelMono8) and (pixel_type != eb.PvPixelRGB8):
#         return pvbuffer

#     # Retrieve Numpy array
#     image_data = image.GetDataPointer()

#     # Apply 'jet' colormap
#     image_data = cv2.applyColorMap(image_data, cv2.COLORMAP_JET)

#     # Save the image
#     cv2.imwrite(os.path.join(IMAGE_DIR, f'image_{image_count}.png'), image_data)

#     return 
def sum_of_intensity_within_circle(image_data, radius_mm, pixel_size):
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
        sum_intensity = np.sum(image_data[mask])
        sum_intensities.append(sum_intensity)

        # Draw the circle on the image
        cv2.circle(image_data, center, radius_pixels, (0, 0, 255), 2, lineType=cv2.LINE_AA)
        # add index of center near circle
        # cv2.putText(image_data, str(idx), (center[0], center[1]), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        # idx+=1

        # Write the sum of intensity on the image
        # text = f'Sum of intensity: {sum_intensity}'
        # cv2.putText(image_data, text, (center[0] - radius_pixels, center[1] - radius_pixels), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # cv2.imwrite(os.path.join(IMAGE_DIR, 'image_with_circles.png'), image_data)
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

def process_pv_buffer(pvbuffer, image_count):
    """
    Use this method to process the buffer with your own algorithm.
    """
    print_string_value = "Image Processing"
    pixel_size = 15e-3  # Pixel size in mm

    image = pvbuffer.GetImage()
    pixel_type = image.GetPixelType()

    # Verify we can handle this format, otherwise continue.
    if (pixel_type != eb.PvPixelMono8) and (pixel_type != eb.PvPixelRGB8):
        return pvbuffer

    # Retrieve Numpy array
    image_data = image.GetDataPointer()
    image_size = image_data.shape

    # Apply 'jet' colormap
    # image_data = cv2.applyColorMap(image_data, cv2.COLORMAP_JET)
    # Apply 'hot' colormap
    image_data = cv2.applyColorMap(image_data, cv2.COLORMAP_HOT)

    # Calculate the sum of intensity within a circle
    radius_mm = 0.3  # Set the radius in mm
    centers = generate_hexagon_vertices((image_size[1]//2, image_size[0]//2), 50)
    sum_intensity = process_multiple_circles(image_data, centers, radius_mm)
    # sum_of_intensity_within_circle(image_data, radius_mm, pixel_size)
    # process_multiple_circles(image_data, centers, radius_mm)
    print(f'Sum of intensity within a circle of radius {radius_mm} mm: {sum_intensity}')

    # Draw the circle on the image
    # center = (370,256)#(image_data.shape[1] // 2, image_data.shape[0] // 2)
    # radius_pixels = int(radius_mm / pixel_size)
    # cv2.circle(image_data, center, radius_pixels, (0, 0, 255), 2, lineType=cv2.LINE_AA)

    # Write the sum of intensity on the image
    # text = f'Sum of intensity: {sum_intensity}'
    # cv2.putText(image_data, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Save the image
    cv2.imwrite(os.path.join(IMAGE_DIR, f'image_{image_count}.png'), image_data)    
    return sum_intensity

# function to read the images from the IMG_DIR and convert to video
def images_to_video():
    # get the list of images
    images = [img for img in os.listdir(IMAGE_DIR) if img.endswith(".png")]
    # sort the images
    images.sort()
    # get the first image
    frame = cv2.imread(os.path.join(IMAGE_DIR, images[0]))
    # get the height, width and number of channels of the image
    height, width, channels = frame.shape
    # define the video codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    # create the video writer object
    video = cv2.VideoWriter('video.mp4', fourcc, 10, (width, height))
    # loop through the images
    for image in images:
        # read the image
        frame = cv2.imread(os.path.join(IMAGE_DIR, image))
        # write the image to video
        video.write(frame)
    # release the video writer object
    video.release()

def acquire_images(device, stream):
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
    sl_array = []
    image_count = 0
    while not kb.is_stopping():
        # Retrieve next pvbuffer
        result, pvbuffer, operational_result = stream.RetrieveBuffer(1000)
        if result.IsOK():
            if operational_result.IsOK():
                # We now have a valid pvbuffer. 
                # This is where you would typically process the pvbuffer.
                sl = process_pv_buffer(pvbuffer, image_count)
                sl_array.append(sl)
                image_count += 1

    images_to_video() # convert images to video
    sl_array = np.array(sl_array)

    # Assuming sl_array is your array of data
    df = pd.DataFrame(sl_array, columns=['side-lobe 1', 'side-lobe 2', 'side-lobe 3', 'side-lobe 4', 'side-lobe 5', 'side-lobe 6', 'main lobe'])

    # Get current datetime
    now = datetime.datetime.now()

    # Format datetime as a string
    datetime_stamp = now.strftime("%Y%m%d_%H%M%S")

    # Add datetime stamp to filename
    filename = f'sum_intensities_{datetime_stamp}.csv'

    # Save DataFrame to CSV
    df.to_csv(os.path.join(IMAGE_DIR, filename), index=False)

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

print("PvStreamSample:")

connection_ID = psu.PvSelectDevice()
if connection_ID:
    device = connect_to_device(connection_ID)
    if device:
        stream = open_stream(connection_ID)
        if stream:
            configure_stream(device, stream)
            buffer_list = configure_stream_buffers(device, stream)
            acquire_images(device, stream)
            buffer_list.clear()
            
            # Close the stream
            print("Closing stream")
            stream.Close()
            eb.PvStream.Free(stream);    

        # Disconnect the device
        print("Disconnecting device")
        device.Disconnect()
        eb.PvDevice.Free(device)

print("<press a key to exit>")
kb.start()
kb.getch()
kb.stop()