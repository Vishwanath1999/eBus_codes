#!/usr/bin/env python3

'''
*****************************************************************************
*
*   Copyright (c) 2022, Pleora Technologies Inc., All rights reserved.
*
*****************************************************************************
'''

import time
import struct
import eBUS as eb
import numpy as np
import Utilities as utils
from Defines import *

class MyMultiPartSource(eb.IPvStreamingChannelSource):

    _DATA_TYPE_1 = eb.PvMultiPart3DImage
    _PIXEL_TYPE_1 = eb.PvPixelCoord3D_A8
    _DATA_TYPE_2 = eb.PvMultiPartConfidenceMap
    _PIXEL_TYPE_2 = eb.PvPixelConfidence8

    def __init__(self):
        super().__init__()
        self._width = WIDTH_DEFAULT
        self._height = HEIGHT_DEFAULT
        self._pixel_type = eb.PvPixelMono8
        self._acquisition_buffer = None
        self._test_pattern_buffer = eb.PvBuffer()
        self._seed = 0
        self._frame_count = 0
        self._chunk_mode_active = False
        self._chunk_sample_enabled = False
        self._stabilizer = eb.PvFPSStabilizer()
        self._multipart_allowed = False
        self._supported_pixel_types = [
            eb.PvPixelMono8
        ]

    def SetMultiPartAllowed(self, allowed):
        self._multipart_allowed = allowed

    def GetPixelType(self):
        return self._pixel_type

    def SetPixelType(self, pixel_type):
        self._pixel_type = pixel_type
        return eb.PV_OK

    def GetSupportedPixelType(self, index):
        if index < len(self._supported_pixel_types):
            return eb.PV_OK, self._supported_pixel_types[index]
        return eb.PV_INVALID_PARAMETER, 0

    def GetWidth(self):
        return self._width

    def GetWidthInfo(self):
        return WIDTH_MIN, WIDTH_MAX, WIDTH_INC

    def SetWidth(self, width):
        if (width < WIDTH_MIN ) or ( width > WIDTH_MAX):
            return eb.PV_INVALID_PARAMETER

        self._width = width
        return eb.PV_OK

    def GetHeight(self):
        return self._height

    def GetHeightInfo(self):
        return HEIGHT_MIN, HEIGHT_MAX, HEIGHT_INC

    def SetHeight(self, height):
        if (height < HEIGHT_MIN ) or (height > HEIGHT_MAX):
            return eb.PV_INVALID_PARAMETER

        self._height = height
        return eb.PV_OK

    def GetOffsetX(self):
        return 0

    def GetOffsetY(self):
        return 0

    def SetOffsetX(self, offset_x):
        return eb.PV_NOT_SUPPORTED

    def SetOffsetY(self, offset_y):
        return eb.PV_NOT_SUPPORTED

    def GetChunksSize(self):
        return self.GetRequiredChunkSize()

    def GetPayloadSize(self):
        return 0

    def GetScanType(self):
        return eb.PvScanTypeArea

    def GetChunkModeActive(self):
        return self._chunk_mode_active

    def SetChunkModeActive(self, enabled):
        self._chunk_mode_active = enabled
        return eb.PV_OK

    def GetSupportedChunk(self, index):
        if index == 0:
            return eb.PV_OK, CHUNKID, "Sample"
        return eb.PV_INVALID_PARAMETER, 0, ""

    def GetChunkEnable(self, chunk_id):
        if chunk_id == CHUNKID:
            return self._chunk_sample_enabled
        return False

    def SetChunkEnable(self, chunk_id, enabled):
        if chunk_id == CHUNKID:
            self._chunk_sample_enabled = enabled
            return eb.PV_OK
        return eb.PV_INVALID_PARAMETER

    def OnOpen(self, dest_ip, dest_port):
        print(f"Streaming channel opened to {dest_ip}:{dest_port}")

    def OnClose(self):
        print("Streaming channel closed")

    def OnStreamingStart(self):
        self._stabilizer.Reset()
        self.AllocMultiPart(self._test_pattern_buffer)

        # Prime test pattern
        container = self._test_pattern_buffer.GetMultiPartContainer()
        self.fill_test_pattern_mono8(container.GetPart(0))
        self.fill_test_pattern_mono8(container.GetPart(1))

        print("Streaming start")

    def OnStreamingStop(self):
        print("Streaming stop")

    def AllocBuffer(self):
        buffer = eb.PvBuffer(eb.PvPayloadTypeMultiPart)
        self.AllocMultiPart(buffer)
        return buffer

    def FreeBuffer(self, pvbuffer):
        return

    def QueueBuffer(self, pvbuffer):
        # We use mAcqusitionBuffer as a 1-deep acquisition pipeline
        if not self._acquisition_buffer:
            self._acquisition_buffer = pvbuffer
            self.fill_test_pattern()
            self.add_chunk_sample(self._acquisition_buffer)
            self._frame_count += 1
            return eb.PV_OK

        # We already have a pvbuffer queued for acquisition
        return eb.PV_BUSY

    def RetrieveBuffer(self, not_used):
        if not self._acquisition_buffer:
            # No pvbuffer queued for acquisition
            return eb.PV_NO_AVAILABLE_DATA, None

        while not self._stabilizer.IsTimeToDisplay(DEFAULT_FPS):
            time.sleep(0.0001)

        # Remove pvbuffer from 1-deep pipeline
        pvbuffer = self._acquisition_buffer
        self._acquisition_buffer = None
        return eb.PV_OK, pvbuffer

    def AbortQueuedBuffers(self):
        pass

    def GetRequiredChunkSize(self):
        return CHUNKSIZE if (self._chunk_mode_active and self._chunk_sample_enabled) else 0

    def AllocMultiPart(self, buffer):
        buffer.Reset(eb.PvPayloadTypeMultiPart)
        container = buffer.GetMultiPartContainer()
        container.Reset()
        container.AddImagePart(self._DATA_TYPE_1, self._width, self._height, self._PIXEL_TYPE_1)
        container.AddImagePart(self._DATA_TYPE_2, self._width, self._height, self._PIXEL_TYPE_2)
        container.AllocAllParts()

    def fill_test_pattern(self):
            src_container = self._test_pattern_buffer.GetMultiPartContainer()
            src_1 = src_container.GetPart(0).GetImage().GetDataPointer()
            src_2 = src_container.GetPart(1).GetImage().GetDataPointer()
            dst_container = self._acquisition_buffer.GetMultiPartContainer()

            dst_container.AttachPart(0, src_1.flatten())
            dst_container.AttachPart(1, src_2.flatten())

            # Advance the test pattern
            src_1 += 1
            src_2 += 1

    def fill_test_pattern_mono8(self, section):
        height = section.GetImage().GetHeight()
        width = section.GetImage().GetWidth()
        img_array = section.GetImage().GetDataPointer()
        
        for y in range(height):
            base = (self._seed + y) & 0xFF
            for x in range(width) :
                img_array[y,x] = base
                base = (base + 1) & 0xFF
        self._seed += 1

    def add_chunk_sample(self, pvbuffer):
        if not self._chunk_mode_active or not self._chunk_sample_enabled:
            return

        # pack the data into 36 bytes
        chunk_data = struct.pack("<I32s", self._frame_count, bytes(time.asctime(), 'utf-8'))

        # Add chunk data to pvbuffer
        pvbuffer.ResetChunks()
        pvbuffer.SetChunkLayoutID(CHUNKLAYOUTID)
        pvbuffer.AddChunk(CHUNKID, chunk_data)
