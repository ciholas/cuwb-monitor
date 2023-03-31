#!/usr/bin/env python

# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

import sys
import signal
import pyqtgraph as pg

import argparse

libs_dir = './libs'
sys.path.append(libs_dir)

from settings import *
from network_objects import *
from socket_processing import *
from plots import *
from ui_main_window import *

VERSION = '1.0.X'
UDP_IP = None
UDP_PORT = None
IFACE_IP = None

print("CuwbMonitor.py v{}".format(VERSION))

#####################################################
#Parse command line options and store appropriately #
#####################################################
parser = argparse.ArgumentParser(description=("The CUWB Monitor provides a " +
                                 "method for gathering and visualizing data " +
                                 "from a CUWB Network"))

parser.add_argument("-u", "--udp", action="store",
                    dest="udp_cfg", help="UDP port configurations as IP:PORT ie. 239.255.76.67:7667")
parser.add_argument("-i", "--iface-ip", action="store",
                    dest="iface_ip", help="Interface IP for VLAN")
parser.add_argument("-p", "--processes", action="store", type=int, dest='num_processes',
                    default=1, help="Set the number of processes to use for CDP decoding.")
parser.add_argument("-d", "--device-id", action="store", type=int,
                    dest='device_id', help="Only listen for packets from [Device ID]")
parser.add_argument('-4k',               action="store_true",        help="Fix display issues with plotting on 4K monitors.")
parser.add_argument('--dark',               action="store_true",        help="Contrasting Text for Dark Mode")


option_dict = vars(parser.parse_args())

if option_dict['udp_cfg'] is not None:
    [UDP_IP, UDP_PORT] = option_dict['udp_cfg'].split(':')
    UDP_PORT = int(UDP_PORT)
    print("Using IP: {} Port: {}".format(UDP_IP, UDP_PORT))

if option_dict['iface_ip'] is not None:
    IFACE_IP = option_dict['iface_ip']
    print("Using Interface IP: {}".format(IFACE_IP))

if option_dict['num_processes'] > 1:
    NUM_PROCESSES = option_dict['num_processes']
    print("Using {} processes".format(NUM_PROCESSES))

if option_dict['device_id'] is not None:
    print('Monitoring device {:08X}'.format(option_dict['device_id']))

if option_dict['4k'] :
    pg.QtWidgets.QApplication.setAttribute(pg.QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

if option_dict['dark'] :
    SetClickableColor("color : cyan")
    SetTitleColor("color : white")


############################
## MAIN CODE STARTS HERE  ##
############################

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = pg.mkQApp()

    main_window = UiMainWindow(NUM_PROCESSES, UDP_IP, UDP_PORT, IFACE_IP)

    if option_dict['device_id'] is None:
        main_window.show()
    else:
        device_stats_window = StatsWindow(option_dict['device_id'], main_window)
        device_stats_window.show()

    #Launch the Qt application to get things started.
    sys.exit(app.exec_())
