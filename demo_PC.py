from pathlib import Path
import sys
import serial.tools.list_ports
import time

sys.path.insert(0, str(Path(__file__).parent / "pybms"))

from DUTs.BMS import BMS
from Interfaces.USB_TO_SPI_BYTE import USB_TO_SPI_BYTE
from DUTs.BMS_Configs.ADBMS6832 import ADBMS6832



def find_pico():
    for port in serial.tools.list_ports.comports():
        if port.vid == 0x2E8A:
            return port.device
    raise RuntimeError("Pi Pico not found")

board_list = [{"Device": ADBMS6832}]

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
    
if __name__ == "__main__":

    print("Hello")
    interface = USB_TO_SPI_BYTE(find_pico(), 115200)
    bms = BMS(interface)

    print("___INIT___")
    res = bms.run_generic_command_list(init_list, board_list)
    print("PEC: ", res.get('Total_PEC_Status'))

    print("__REDUNDANT__")
    res = bms.run_generic_command_list(redundant_meas_list, board_list)
    print("PEC: ", res.get("Total_PEC_Status"))

    print("averaged_cells: ", ADBMS6832.AVERAGED_CELLS[:3])
    print("filtered_cells: ", ADBMS6832.FILTERED_CELLS[:3])
    acells = []

    for cell in ADBMS6832.AVERAGED_CELLS:
                acells.append(res['CELLS'][0][cell])
    print("acells: ", [round(v,4) for v in acells])

    print("__LOOP__")

    pec_ok = 0
    pec_bad = 0
    previous = None
    redundant_timer = 0

    for i in range (50):

        
        redundant_timer -= 1
        if redundant_timer <=0:
            redundant_timer = 20
            r = bms.run_generic_command_list(redundant_meas_list,board_list)

            acells = []
            for cell in ADBMS6832.AVERAGED_CELLS:
                acells.append(r['CELLS'][0][cell])

            print(f"[redundant]  PEC = {r.get('Total_PEC_Status')}"
                  f"acells = [{[round(v,4) for v in acells]}]")
        print(f"START {i}")    
        try:
            res = bms.run_generic_command_list(meas_list, board_list)
        except Exception as e:
            print(f"{i:3d} EXCEPTION : {e}")
            break

        
        pec = res.get('Total_PEC_Status')
        if pec:
            pec_ok += 1
        else :   
            pec_bad += 1

        fcells = []
        for cell in ADBMS6832.FILTERED_CELLS:
            fcells.append(res['CELLS'][0][cell])

        ct = res['CT'][0].get('CT')

        marker = ""
        if previous is not None and fcells == previous:
             marker =" IDENTICAL"
        previous = list(fcells)

        print(f"{i:3d}  PEC={pec}  CT = {ct}"
              f"{[round(v,4) for v in fcells]}{marker}")

        time.sleep(0.1)
        print(f"END {i}")  

    print(f"\nPEC ok: {pec_ok}, PEC bad : {pec_bad}")

    interface.close()

