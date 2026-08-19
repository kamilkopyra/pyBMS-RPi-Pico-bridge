# This script is an example demonstration of communication between the pyBMS framework and
# a Raspberry Pi Pico 2 acting as a USB-to-SPI bridge.
#
# It executes the most commonly used pyBMS commands and can be used to verify
# communication, register access, ADC conversions, and PEC integrity.
#
# The script also generates parsed and raw communication logs that can be
# used for debugging and validation purposes.

from pathlib import Path
import sys
import serial.tools.list_ports
import argparse
from BMS_logger import (BMSLogger, RawFrameLogger)


sys.path.insert(0, str(Path(__file__).parent / "pybms"))

from DUTs.BMS import BMS
from Interfaces.USB_TO_SPI_BYTE import USB_TO_SPI_BYTE
from DUTs.BMS_Configs.ADBMS6832 import ADBMS6832
import time



def find_pico():
    for port in serial.tools.list_ports.comports():
        if port.vid == 0x2E8A:
            return port.device
    raise RuntimeError("Pi Pico not found")

def find_linduino():
    for port in serial.tools.list_ports.comports():
            if port.vid == 0x0403:
                return port.device
    raise RuntimeError("Linduino not found")



if __name__ == "__main__":


    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", choices = ["pico", "linduino"], default="pico")
    args = parser.parse_args()


    for p in serial.tools.list_ports.comports():
            print(
                p.device,
                p.vid,
                p.pid,
                p.description
            )


    if args.device == "pico":
         port = find_pico()

    else :
        port = find_linduino()

   

    interface = USB_TO_SPI_BYTE(
        port,
        115200,
    )
    logger = BMSLogger()
    raw_logger = RawFrameLogger(interface)

    logger.write("connection established")


    bms = BMS(interface)    

    board_list = [
        {   "Device": ADBMS6832      }
    ]

    

         

    init_list = [
    {'command': '$SPI_SET_FREQUENCY_kHz$', 'arguments': {'Frequency': 1000}},
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 400}},
    {'command': 'WRCFGA', 'arguments': {'FC': 5}},
    {'command': 'RDCFGA', 'map_key': 'CFG'},
    {'command': 'WRCFGB'},
    {'command': 'RDCFGB', 'map_key': 'CFG'},
    {'command': 'ADCV', 'arguments': {'CONT': True}},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 5}}
    ]

    balance_list = [
            {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
            {'command': 'WRCFGB'},
            {'command': 'SNAP'},
            {'command': 'RDSTATC', 'map_key': 'CT'},
            {'command': 'UNSNAP'},
    ]
    meas_list = [
        {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
        {'command': 'SNAP'},
        {'command': 'RDFCA', 'map_key': 'CELLS'},
        {'command': 'RDFCB', 'map_key': 'CELLS'},
        {'command': 'RDFCC', 'map_key': 'CELLS'},
        {'command': 'RDFCD', 'map_key': 'CELLS'},
        {'command': 'RDFCE', 'map_key': 'CELLS'},
        {'command': 'RDFCF', 'map_key': 'CELLS'},
        {'command': 'RDSTATC', 'map_key': 'CT'},
        {'command': 'UNSNAP'},
    ]
    redundant_meas_list = [
        {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
        {'command': 'MUTE'},
        {'command': 'SNAP'},
        # {'command': 'ADSV', 'arguments': {'CONT': True}},
        {'command': 'RDSTATC', 'map_key': 'MUTE'},
        {'command': 'UNSNAP'},
        {'command': '$DELAY_MS$', 'arguments': {'Delay': 16}},
        {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
        {'command': 'UNMUTE'},
        {'command': 'SNAP'},
        # {'command': 'ADSV', 'arguments': {'CONT': False}},
        {'command': 'RDACA', 'map_key': 'CELLS'},
        {'command': 'RDACB', 'map_key': 'CELLS'},
        {'command': 'RDACC', 'map_key': 'CELLS'},
        {'command': 'RDACD', 'map_key': 'CELLS'},
        {'command': 'RDACE', 'map_key': 'CELLS'},
        {'command': 'RDACF', 'map_key': 'CELLS'},
        {'command': 'RDSTATC', 'map_key': 'UNMUTE'},
        {'command': 'UNSNAP'},
    ]

    test_list = [
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 400}},
    {'command': 'ADAX'},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 20}},
    {'command': 'RDSTATA', 'map_key' : 'A'},
    {'command': 'RDSTATB', 'map_key' : 'B'},
    ]
    

    test_list2 = [
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 400}},
    {'command': 'ADCV', 'arguments': {'CONT': False}},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 20}},
    {'command': 'RDCVA'},
    ]


    logger.write("init")
    for i in range (2):
        
        try:
            logger.log(bms.run_generic_command_list(init_list,board_list))
            logger.write("init ok")
        except Exception as e1:
                    logger.write("init problem :  {e1}")
                    
        print(f"TEST {i} init OK")

        try:
            logger.write("meas")
            logger.log(bms.run_generic_command_list(meas_list,board_list))
        except Exception as e2:
            logger.write("meas problem : {e2}")
            
        print(f"TEST {i} meas OK")

        try:
            logger.write("balance")
            logger.log(bms.run_generic_command_list(balance_list, board_list))
        except Exception as e3:
            logger.write("balance problem : {e3}")

        print(f"TEST {i} balance OK")
        
        try: 
            logger.write("redundant_meas")
            logger.log(bms.run_generic_command_list(redundant_meas_list, board_list))
        except Exception as e4 :
             logger.write("redundant_meas problem : {e4}")
             
        print(f"TEST {i} redundant_meas OK")
        
        try:
            logger.write("test list")
            logger.log(bms.run_generic_command_list(test_list2,board_list))
        except Exception as e5:
             logger.write("test_list problem : {e5}")
             
        print(f"TEST {i} test_list2 OK")


    interface.close()

