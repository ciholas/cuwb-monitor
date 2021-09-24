# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import numpy as np
import sys
import time
from collections import deque
from math import sqrt, log10, pi, e
from scipy.signal import find_peaks_cwt

# Local libraries
from settings import *


class UwbNetwork:
    """Global network class contains dictionaries of actors and some network variables"""

    nodes = dict()           # Hash of anchor objects, stored by serial number.
    running = True           # This is used to close threads.
    node_count = 1           # This changes with total number of seeds, should never fall below 1.
    system_repeat_rate = 30  # This is default, it should get updated with config file.
    prf = 64                 # This is default, it should get updated with config file.
    time_initial = time.time()

    def stop_network(self):
        self.running = False


class Node:
    """Network node class contains functions and parameters present for all devices in the network."""

    def __init__ (self, _serial):
        """Initialize position and serial number for network device"""
        self.x = np.nan        # Device X position as calculated
        self.y = np.nan        # Device Y position as calculated
        self.z = np.nan        # Device Z position as calculated
        self.serial = _serial  # Device serial number

        self.cdp_pkts = dict()
        self.cdp_pkts_time = dict()
        self.cdp_pkts_name = dict()
        self.cdp_pkts_count = dict()
        self.cdp_pkts_freq = dict()
        self.cdp_pkts_selected = dict()
        self.cdp_pkts_frequency_deques = dict()

        self.time_initial = time.time()

        self.cdp_total = 0

        self.filtering = False
        self.filter_set = []
        self.paused = False

        UwbNetwork.nodes.update([(self.serial, self)])

    def get_xyz(self):
        """Return the XYZ position in a numpy array."""
        return np.array([[self.x], [self.y], [self.z]])

    def update(self, data_item, data_item_name, timestamp):
        # If paused, update no nodes
        # If not filtering and not paused, update all nodes
        # If filtering, update only nodes selected in the filter window
        if not self.paused and (not self.filtering or (self.filtering and (data_item.type in self.filter_set
           or (UNKNOWN_FILTER_TYPE in self.filter_set and UNKNOWN_FILTER_NAME in data_item_name)))):
            if not data_item.type in self.cdp_pkts:
                self.cdp_pkts.update([(data_item.type, deque([], TRAIL_LENGTH))])
                self.cdp_pkts_time.update([(data_item.type, deque([], TRAIL_LENGTH))])
                self.cdp_pkts_name.update([(data_item.type, data_item_name)])
                self.cdp_pkts_count.update([(data_item.type, 0)])
                self.cdp_pkts_freq.update([(data_item.type, np.nan)])
                self.cdp_pkts_selected.update([(data_item.type, False)])
                self.cdp_pkts_frequency_deques.update([(data_item.type, deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH))])
            self.cdp_pkts[data_item.type].append(data_item)
            self.cdp_pkts_count[data_item.type] += 1
            self.cdp_pkts_time[data_item.type].append(timestamp-UwbNetwork.time_initial)
            self.cdp_total += 1

    def start_filtering(self, filter_set):
        self.filtering = True
        self.filter_set = filter_set
        for type in list(self.cdp_pkts):
            # Clear all nodes not selected in the filter window
            if (not type in self.filter_set) and not (UNKNOWN_FILTER_TYPE in self.filter_set and UNKNOWN_FILTER_NAME in self.cdp_pkts_name[type]):
                del self.cdp_pkts[type]
                del self.cdp_pkts_time[type]
                del self.cdp_pkts_name[type]
                self.cdp_total -= self.cdp_pkts_count[type]
                del self.cdp_pkts_count[type]
                del self.cdp_pkts_freq[type]
                del self.cdp_pkts_selected[type]
                del self.cdp_pkts_frequency_deques[type]

    def stop_filtering(self):
        self.filtering = False

    def reset(self):
        for type in self.cdp_pkts:
            self.cdp_total = 0
            self.cdp_pkts[type] = deque([], TRAIL_LENGTH)
            self.cdp_pkts_time[type] = deque([], TRAIL_LENGTH)
            self.cdp_pkts_count[type] = 0
            self.cdp_pkts_freq[type] = np.nan
            self.cdp_pkts_frequency_deques[type] = deque([], FREQUENCY_CALCULATION_DEQUE_LENGTH)
            UwbNetwork.time_initial = time.time()
    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def calculate_frequency(self, packet_time_deque):
        if self.paused:
            return 0
        if len(packet_time_deque) > 2:
            packet_diff = packet_time_deque[-1][0] - packet_time_deque[0][0]
            time_diff = packet_time_deque[-1][1] - packet_time_deque[0][1]
            return packet_diff / time_diff
        return 0

    def set_xyz(self, _XYZ):
        """Change XYZ position. This is fed in as a numpy array."""
        self.x = _XYZ[0][0]
        self.y = _XYZ[1][0]
        self.z = _XYZ[2][0]

    #######################
    # Useful calculations #
    #######################

    # Function: first_path
    #
    # F1: first path amplitude 1 reported from DW1000
    # F2: first path amplitude 2 reported from DW1000
    # F3: first path amplitude 3 reported from DW1000
    # N  : Receive pre-amble count reported from DW1000
    # Return: Float with dB value of first path amplitued
    def first_path(self, F1, F2, F3, N):
        """Provide First Path amplitude in dB given DW1000 RF state information"""
        # Sanity check on N to prevent taking log of zero
        if N == 0: N = 0.1

        if (F1 == 0) or (F2 == 0) or (F3 == 0): return 200.0

        # Equation from decawave datasheets, return value dependant on network PRF value.
        if UwbNetwork.prf == 16: return 10.0 * log10((F1**2.0 + F2**2.0 + F3**2.0)/N**2.0) - A_PRF16
        else                   : return 10.0 * log10((F1**2.0 + F2**2.0 + F3**2.0)/N**2.0) - A_PRF64

    # Function: total_path
    #
    # CIR: CIR power reported from DW1000
    # N   : Receive pre-amble count reported from DW1000
    def total_path(self, CIR, N):
        """Provide Total Path amplitude in dB given DW1000 RF state information"""
        #Sanity check on CIR and N to prevent taking log of zero
        if CIR == 0: CIR = 0.1
        if N==0: N = 0.1

        #Equation from decawave datasheets, return value dependant on network PRF value.
        if UwbNetwork.prf == 16: return 10.0 * log10((CIR * 2.0**17.0) / N**2.0) - A_PRF16
        else                   : return 10.0 * log10((CIR * 2.0**17.0) / N**2.0) - A_PRF64
