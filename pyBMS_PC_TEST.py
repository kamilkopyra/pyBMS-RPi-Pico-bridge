from pathlib import Path
import sys
import serial.tools.list_ports

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


if __name__ == "__main__":

    interface = USB_TO_SPI_BYTE(
        find_pico(),
        115200
    )

    bms = BMS(interface)

    board_list = [
        {
            "Device": ADBMS6832
        }
    ]

    init_list = [
    {'command': '$SPI_SET_FREQUENCY_kHz$', 'arguments': {'Frequency': 1000}},
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 400}},
    {'command': 'WRCFGA', 'arguments': {'FC': 5}},
    {'command': 'WRCFGB'},
    {'command': 'RDCFGA', 'map_key': 'CFG'},
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
    {'command': 'RDSTATC'},
]


    for i in range (1):
        print("init")
        
        try:
            bms.run_generic_command_list(test_list,board_list)
            print("init ok")
        except Exception as e1:
                    print("init problem : ", e1)
        # print(interface.get_commands())
        # print("length :", len(interface.get_commands()))
        
        # print(f"TEST {i} OK")

        # #print(interface.get_firmware_version())
        # try:
        #     print("meas")
        #     bms.run_generic_command_list(meas_list,board_list)
        # except Exception as e2:
        #     print("meas problem : ", e2)
        
        # print(f"TEST {i} OK")

        # print("balance")
        # bms.run_generic_command_list(balance_list, board_list)
      
        
        
        # print(f"TEST {i} OK")
        # print("redundant_meas")
        # (bms.run_generic_command_list(redundant_meas_list, board_list))
        
        
        # print(f"TEST {i} OK")



    interface.close()

