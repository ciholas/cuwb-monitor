# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

################
# UDP DEFAULTS #
################
UDP_IP = '239.255.76.67'
UDP_PORT = 7667
IFACE_IP = '127.0.0.1'

######################
# GLOBAL DEFINITIONS #
######################
C = 2.997e8
TICK = 1 / (128*499.2e6)
A_PRF16 = 115.72
A_PRF64 = 121.74
ANT_DELAY = 16440
MS_TO_SECONDS = .001

TRAIL_LENGTH = 1000
QPLOT_FREQUENCY = 100  #in mS
FREQUENCY_CALCULATION_TIME_INTERVAL = 30 # in seconds
FREQUENCY_CALCULATION_DEQUE_LENGTH = int(FREQUENCY_CALCULATION_TIME_INTERVAL / (QPLOT_FREQUENCY * MS_TO_SECONDS))
TOTAL_PKTS_FOR_FREQ_CALC = 50
NUM_PROCESSES = 1

SEC_PER_DECATICK = 15.650040064102564e-12 #15.65e-12
MSEC_PER_DECATICK = SEC_PER_DECATICK * 1e3
USEC_PER_DECATICK = MSEC_PER_DECATICK * 1e3

UNKNOWN_FILTER_TYPE = 65535
UNKNOWN_FILTER_NAME = 'Unknown'

global clickable_color;
clickable_color = "color : blue"
global title_color
title_color = "color : black"

def GetClickableColor():
    global clickable_color;
    return clickable_color

def SetClickableColor(color):
    global clickable_color 
    clickable_color = color

def GetTitleColor():
    global title_color
    return title_color

def SetTitleColor(color):
    global title_color
    title_color = color