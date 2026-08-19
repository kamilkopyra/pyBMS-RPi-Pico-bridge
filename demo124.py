
"""
Extended pyBMS monitoring demo rewritten for the Raspberry Pi Pico 2 and ADBMS6832.
This script periodically reads cell voltages, GPIO voltages and device
diagnostic parameters.

The results are displayed in a local Flask web interface.

Calibration is currently disabled. Parameters were copied from the
original pyBMS demo and have not been checked for accuracy and compatibility with ADBMS6832.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "pybms"))

import webbrowser
from multiprocessing import Process, Queue

from flask import Flask, jsonify, render_template_string
from waitress import serve

import serial.tools.list_ports
from DUTs.BMS import BMS
from Interfaces.USB_TO_SPI_BYTE import USB_TO_SPI_BYTE
from DUTs.BMS_Configs.ADBMS6832 import ADBMS6832



def find_pico():
    for p in serial.tools.list_ports.comports():
        if p.vid == 0x2E8A:
            return p.device
    raise RuntimeError("Pi Pico not found")


board_list = [{'Device': ADBMS6832}]


NUM_CELLS_CONNECTED = len(ADBMS6832.FILTERED_CELLS)


BALANCE_ACCUR   = 0.005   
MIN_BALANCE_VAL = 3.7     
CAL_PERIOD      = 15      


IIR_TABLE = [
    [0, 0], [1, 0.03125], [2, 0.061523438], [3, 0.09085083],
    [4, 0.119261742], [5, 0.146784812], [6, 0.173447787],
    [7, 0.199277543], [8, 0.224299908],
]



init_list = [
    {'command': '$SPI_SET_FREQUENCY_kHz$', 'arguments': {'Frequency': 1000}},
    {'command': '$SPI_WAKEUP$',            'arguments': {'Wakeup Time': 400}},
    {'command': 'WRCFGA',                  'arguments': {'FC': 5}},
    {'command': 'WRCFGB'},
    {'command': 'RDCFGA', 'map_key': 'CFG'},
    {'command': 'RDCFGB', 'map_key': 'CFG'},
    {'command': 'ADCV',                    'arguments': {'CONT': True}},
    {'command': '$DELAY_MS$',              'arguments': {'Delay': 5}},
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

diagnostic_list = [
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
    {'command': 'ADAX'},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 20}},
    {'command': 'RDSTATA', 'map_key': 'STATUS_A'},
    {'command': 'RDSTATB', 'map_key': 'STATUS_B'},
]

gpio_list = [
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
    {'command': 'ADAX'},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 20}},

    {'command': 'RDAUXA', 'map_key': 'RDAUXA'},
    {'command': 'RDAUXB', 'map_key': 'RDAUXB'},
    {'command': 'RDAUXC', 'map_key': 'RDAUXC'},
    {'command': 'RDAUXD', 'map_key': 'RDAUXD'},
    {'command': 'RDAUXE', 'map_key': 'RDAUXE'},
]

redundant_meas_list = [
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
    {'command': 'MUTE'},
    {'command': 'SNAP'},
    {'command': 'RDSTATC', 'map_key': 'MUTE'},
    {'command': 'UNSNAP'},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 16}},
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 10}},
    {'command': 'UNMUTE'},
    {'command': 'SNAP'},
    {'command': 'RDACA', 'map_key': 'CELLS'},
    {'command': 'RDACB', 'map_key': 'CELLS'},
    {'command': 'RDACC', 'map_key': 'CELLS'},
    {'command': 'RDACD', 'map_key': 'CELLS'},
    {'command': 'RDACE', 'map_key': 'CELLS'},
    {'command': 'RDACF', 'map_key': 'CELLS'},
    {'command': 'RDSTATC', 'map_key': 'UNMUTE'},
    {'command': 'UNSNAP'},
]




def iir_scale(old_ct, new_ct, need_scale, offset):
    """Zwraca wspolczynnik skalowania IIR dla biezacej liczby probek
    od przelaczenia rezystora balansujacego."""
    if not need_scale:
        return 1, False, 0

    if new_ct < old_ct:
        ct = new_ct + 2048 - old_ct + offset
    else:
        ct = new_ct - old_ct + offset

    if ct >= len(IIR_TABLE):
        return 1, False, 0
    return IIR_TABLE[ct][1], True, offset


def make_switch_config(state=False):
    return {f'DCC{n}': state for n in range(1, 17)}


def data_collection(queue, dcc_input):
    """Glowna petla: pomiar + kalibracja IIR + balansowanie.
    Struktura stanu ('start' -> 'switch_off' -> 'switch_on' -> None)
    odzwierciedla oryginalne demo ADI."""

    interface = USB_TO_SPI_BYTE(find_pico(), 115200)
    bms = BMS(interface)

    print("=== INIT ===")
    init_res = bms.run_generic_command_list(init_list, board_list)
    print("init PEC:", init_res.get('Total_PEC_Status'))

    
    cal_state             = None
    cal_in_progress        = False
    cal_time               = time.time()
    cal_base               = []
    switches_disabled      = False
    iir_scaling_required   = False
    gain                   = [1] * len(ADBMS6832.FILTERED_CELLS)
    prev_ct                = 0
    offset                 = 0

    switch_config      = make_switch_config()
    switch_config_base = make_switch_config()

   
    res = bms.run_generic_command_list(redundant_meas_list, board_list)
    acells, fcells = [], []
    for i, cell in enumerate(ADBMS6832.AVERAGED_CELLS):
        acells.append(res['CELLS'][0][cell])
        fcells.append(res['CELLS'][0][cell])
    prev_ct = res['UNMUTE'][0]['CT']
    redundant_timer = 0
    diagnostic_timer = 0
    diagnostics = {
        'VREF2' : None,
        'ITMP' : None,
        'VD' : None,
        'VA' : None,
        'VRES' : None
    }

    gpio = {
        'G1V': None,
        'G2V': None,
        'G3V': None,
        'G4V': None,
        'G5V': None,
        'G6V': None,
        'G7V': None,
        'G8V': None,
        'G9V': None,
        'G10V': None,
        'GA11V': None,
        'GA12V': None,
        'VMV': None,
        'VPV': None,
    }

    rawcells = list(fcells)

    while True:
        
        while not dcc_input.empty():
            cfg = dcc_input.get()
            switch_config[cfg['DCC']] = cfg['Val']

        packet = {
            'FCELLS': [],
            'RAWCELLS': [],
            'ACELLS': [],
            'CT': None,
            'VREF2': diagnostics['VREF2'],
            'ITMP': diagnostics['ITMP'],
            'VD': diagnostics['VD'],
            'VA': diagnostics['VA'],
            'VRES': diagnostics['VRES'],
            'G1V': gpio['G1V'],
            'G2V': gpio['G2V'],
            'G3V': gpio['G3V'],
            'G4V': gpio['G4V'],
            'G5V': gpio['G5V'],
            'G6V': gpio['G6V'],
            'G7V': gpio['G7V'],
            'G8V': gpio['G8V'],
            'G9V': gpio['G9V'],
            'G10V': gpio['G10V'],
            'GA11V': gpio['GA11V'],
            'GA12V': gpio['GA12V'],
            'VMV': gpio['VMV'],
            'VPV': gpio['VPV'],
        }

        diagnostic_timer -= 1

        if diagnostic_timer <= 0:
            diagnostic_timer = 10

            try:
                diagnostic_result = bms.run_generic_command_list(
                    diagnostic_list,
                    board_list
                )
                gpio_result = bms.run_generic_command_list(gpio_list, board_list)

                status_a = diagnostic_result.get('STATUS_A', [{}])[0]
                status_b = diagnostic_result.get('STATUS_B', [{}])[0]

                aux_groups = [
                    gpio_result.get('RDAUXA', [{}])[0],
                    gpio_result.get('RDAUXB', [{}])[0],
                    gpio_result.get('RDAUXC', [{}])[0],
                    gpio_result.get('RDAUXD', [{}])[0],
                    gpio_result.get('RDAUXE', [{}])[0],
                ]

                gpio_data = {}

                for group in aux_groups:
                    gpio_data.update(group)

                gpio.update({
                    name: gpio_data.get(name)
                    for name in gpio
                })
                diagnostics['VREF2'] = status_a.get('VREF2')
                diagnostics['ITMP'] = status_a.get('ITMP')
                diagnostics['VD'] = status_b.get('VD')

                diagnostics['VA'] = status_b.get('VA')
                diagnostics['VRES'] = status_b.get('VRES')



            except Exception as error:
                print("Diagnostic measurement error:", error)

        redundant_timer -= 1
        if redundant_timer <= 0 and not cal_in_progress:
            redundant_timer = 100
            res = bms.run_generic_command_list(redundant_meas_list, board_list)
            acells = [res['CELLS'][0][c] for c in ADBMS6832.AVERAGED_CELLS]

            mute_ct = res['MUTE'][0]['CT']
            unmute_ct = res['UNMUTE'][0]['CT']
            if unmute_ct < mute_ct:
                unmute_ct += 2048
            offset = unmute_ct - mute_ct
            if not iir_scaling_required:
                iir_scaling_required = True
                prev_ct = res['MUTE'][0]['CT']

      
        res = bms.run_generic_command_list(meas_list, board_list)
        current_ct = res['CT'][0]['CT']
        scale, iir_scaling_required, offset = iir_scale(
            prev_ct, current_ct, iir_scaling_required, offset)

        rawcells = []
        if not cal_in_progress:
            fcells = []

        for i, cell in enumerate(ADBMS6832.FILTERED_CELLS):
            packet['ACELLS'].append(acells[i])

            raw = res['CELLS'][0][cell]
            rawcells.append(raw)

            if not cal_in_progress:
                packet['RAWCELLS'].append(raw)
                fcells.append(raw)
            else:
                packet['RAWCELLS'].append(fcells[i])

            if switches_disabled:
                packet['FCELLS'].append(
                    raw * (1 + (gain[i] - 1) * (1 - scale)))
            else:
                packet['FCELLS'].append(
                    raw * (1 + (gain[i] - 1) * scale))

        packet['CT'] = res['CT'][0]['CT']
        packet['Total_PEC_Status'] = res.get('Total_PEC_Status')
        packet['cal_state'] = cal_state

        packet['VREF2'] = diagnostics['VREF2']
        packet['ITMP'] = diagnostics['ITMP']
        packet['VD'] = diagnostics['VD']
        packet['VA'] = diagnostics['VA']
        packet['VRES'] = diagnostics['VRES']


        packet['GPIO'] = dict(gpio)






        
        if False and (time.time() - cal_time > CAL_PERIOD or cal_in_progress):

            if not cal_state:
                cal_state = 'start'

            if cal_state == 'start':
                print("Starting CAL")
                board_list[0].update(switch_config_base)
                dat = bms.run_generic_command_list(balance_list, board_list)
                prev_ct = dat['CT'][0]['CT']
                iir_scaling_required = True
                cal_state = 'switch_off'
                switches_disabled = True
                cal_in_progress = True
                print("CAL - Switch Off")

            elif cal_state == 'switch_off':
                if current_ct < prev_ct:
                    ct = current_ct + 2048 - prev_ct
                else:
                    ct = current_ct - prev_ct

                if ct >= IIR_TABLE[-1][0]:
                    cal_state = 'switch_on'
                    switches_disabled = False
                    cal_base = list(rawcells)

                    min_cell = min(cal_base)
                    for i, cell in enumerate(ADBMS6832.FILTERED_CELLS):
                        if (cal_base[i] > min_cell + BALANCE_ACCUR
                                and cal_base[i] > MIN_BALANCE_VAL
                                and switch_config.get(f'DCC{i+1}', False)):
                            switch_config[f'DCC{i+1}'] = True

                    board_list[0].update(switch_config)
                    dat = bms.run_generic_command_list(balance_list, board_list)
                    prev_ct = dat['CT'][0]['CT']
                    iir_scaling_required = True
                    print("CAL - Switch On")

            elif cal_state == 'switch_on':
                if current_ct < prev_ct:
                    ct = current_ct + 2048 - prev_ct
                else:
                    ct = current_ct - prev_ct

                if ct >= IIR_TABLE[-1][0]:
                    cal_state = None
                    cal_in_progress = False
                    gain = []
                    for i, cell in enumerate(ADBMS6832.FILTERED_CELLS):
                        gain.append(cal_base[i] / rawcells[i]
                                    if rawcells[i] else 1)
                    cal_time = time.time()
                    print("CAL - Done")

        try:
            queue.put(packet)
        except Exception as e:
            print("queue error:", e)

        time.sleep(1)



app = Flask(__name__)
data_queue = Queue()
dcc_queue = Queue()

PAGE = """
<!doctype html>
<html>
<head>
    <title>ADBMS6832 </title>
    <meta http-equiv="refresh" content="1">
    <style>
        body { font-family: monospace; background:#111; color:#ddd; }
        table { border-collapse: collapse; margin-top: 1em; }
        td, th { border: 1px solid #444; padding: 4px 10px; text-align: right; }
        th { background:#222; }
        .stale { color:#888; }
        .pec-true  { color:#4caf50; }
        .pec-false { color:#f44336; }

        .tables-container {
            display: flex;
            align-items: flex-start;
            gap: 24px;
            flex-wrap: wrap;
        }

        .table-section h3 {
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <h2>ADBMS6832</h2>
    <p>
        CT: {{ ct }}
        &nbsp;|&nbsp; PEC:
        <span class="{{ 'pec-true' if pec else 'pec-false' }}">{{ pec }}</span>
        &nbsp;|&nbsp; cal_state: {{ cal_state }}
        &nbsp;|&nbsp; Last update: {{ ts }}
    </p>

<div class="tables-container">

    <div class="table-section">
        <h3>Cell measurements</h3>

        <table>
            <tr>
                <th>Cell</th>
                <th>Raw [V]</th>
                <th>Filtered [V]</th>
                <th>Averaged [V]</th>
            </tr>

            {% for i in range(n) %}
            <tr class="{{ 'stale' if i >= connected else '' }}">
                <td>{{ i + 1 }}</td>
                <td>
                    {{ '%.4f' % rawcells[i]
                       if i < rawcells|length else '-' }}
                </td>
                <td>
                    {{ '%.4f' % fcells[i]
                       if i < fcells|length else '-' }}
                </td>
                <td>
                    {{ '%.4f' % acells[i]
                       if i < acells|length else '-' }}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="table-section">
        <h3>GPIO measurements</h3>

        <table>
            <tr>
                <th>Input</th>
                <th>Voltage [V]</th>
            </tr>

            {% for name, value in gpio.items() %}
            <tr>
                <td>{{ name }}</td>
                <td>
                    {{ '%.4f' % value if value is not none else '-' }}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="table-section">
        <h3>Device diagnostics</h3>

        <table>
            <tr>
                <th>Parameter</th>
                <th>Value</th>
            </tr>

            <tr>
                <td>VREF2</td>
                <td>
                    {{ '%.4f V' % vref2
                       if vref2 is not none else '-' }}
                </td>
            </tr>

            <tr>
                <td>Internal temperature</td>
                <td>
                    {{ '%.2f °C' % itmp
                       if itmp is not none else '-' }}
                </td>
            </tr>

            <tr>
                <td>VD</td>
                <td>
                    {{ '%.4f V' % vd
                       if vd is not none else '-' }}
                </td>
            </tr>

            <tr>
                <td>VA</td>
                <td>
                    {{ '%.4f V' % va
                       if va is not none else '-' }}
                </td>
            </tr>

            <tr>
                <td>VRES</td>
                <td>
                    {{ '%.4f V' % vres
                       if vres is not none else '-' }}
                </td>
            </tr>
        </table>
    </div>

</div>
    {% if connected < n %}
    <p style="color:#888">
    </p>
    {% endif %}
</body>
</html>
"""

_last_packet = {'FCELLS': [], 'ACELLS': [], 'RAWCELLS': [], 'CT': None,
                 'Total_PEC_Status': None, 'cal_state': None, 'VREF2': None, 'ITMP' : None, 'VD' : None, 'VA' : None, 'VRES' : None,
                 'GPIO': {}}


@app.route("/index")
def index():
    global _last_packet
    while not data_queue.empty():
        _last_packet = data_queue.get()

    return render_template_string(
        PAGE,
        fcells=_last_packet.get('FCELLS', []),
        acells=_last_packet.get('ACELLS', []),
        rawcells=_last_packet.get('RAWCELLS', []),
        ct=_last_packet.get('CT'),
        pec=_last_packet.get('Total_PEC_Status'),
        cal_state=_last_packet.get('cal_state'),
        vref2=_last_packet.get('VREF2'),
        itmp=_last_packet.get('ITMP'),
        vd=_last_packet.get('VD'),
        va=_last_packet.get('VA'),
        vres=_last_packet.get('VRES'),
        ts=time.strftime('%H:%M:%S'),
        gpio = _last_packet.get('GPIO', {}),
        n=len(ADBMS6832.FILTERED_CELLS),
        connected=NUM_CELLS_CONNECTED,
    )


@app.route("/data_update")
def data_update():
    global _last_packet
    while not data_queue.empty():
        _last_packet = data_queue.get()
    return jsonify(_last_packet)


if __name__ == '__main__':
    background_process = Process(target=data_collection,
                                  args=(data_queue, dcc_queue))
    background_process.start()

    webbrowser.open('http://127.0.0.1:5000/index')
    serve(app, host='127.0.0.1', port=5000, threads=4)