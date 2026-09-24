# pyBMS RPi Pico bridge

Raspberry Pi Pico 2 firmware that works as a USB-to-SPI bridge between the
Analog Devices **pyBMS** framework on a PC and ADI battery monitors. It
replaces the SDP-K1 evaluation board in the original ADI measurement chain,
so a cheap Pico can be used instead of a dedicated eval board.

```
PC (pyBMS) --USB--> Raspberry Pi Pico 2 --SPI--> ADBMS6822 --isoSPI--> ADBMS6832
```

Tested with ADBMS6822 (isoSPI transceiver) + ADBMS6832. Other battery monitors
supported by pyBMS should work as well, since the Pico does not know anything
about the specific device — it only executes SPI transactions. Daisy-chained
devices are supported; the chain is defined on the PC side.

## How it works

The Pico is "dumb" on purpose. All BMS logic stays in pyBMS on the PC:

1. You describe what to do as a pyBMS **command list** (`WRCFGA`, `ADCV`,
   `RDCVA`, ...).
2. pyBMS builds the SPI frames (command codes, PEC, daisy chain handling) and
   sends them over USB through its `USB_TO_SPI_BYTE` interface.
3. The Pico buffers the frames, executes them on SPI and returns the read
   data.
4. pyBMS parses the response (register maps, voltages, PEC status) and gives
   you back a Python dict.

The firmware follows the SDP-K1 protocol, so on the PC side you use pyBMS
the normal way: everything pyBMS can do with the ADI eval board, you can do
through the Pico. That includes the example scripts shipped with pyBMS, e.g.
`Customer_GUI.py` for data visualization. The only thing that does not work is
connecting to the ADI desktop GUI software (it does not recognize the Pico as
an SDP-K1).

## Hardware

Pico 2 pinout (SPI0, mode 0):

| Pico pin | Signal |
|---|---|
| GP2 | SCK |
| GP3 | MOSI |
| GP4 | MISO |
| GP5 | CS |

The default SPI clock is 500 kHz. You can change it from the PC with
`$SPI_SET_FREQUENCY_kHz$`. The scripts find the Pico automatically by its USB
VID (`0x2E8A`).

Bridge operations supported by the firmware: SPI write, SPI read, poll,
`$DELAY_US$`, `$DELAY_MS$`, `$SPI_WAKEUP$` and `$SPI_SET_FREQUENCY_kHz$`.
Buffer limits: 128 commands per list, 256 bytes per command.

## Files

| File | Description |
|---|---|
| `pico_usb.c` | Pico firmware (USB-to-SPI bridge) |
| `pyBMS_PC_TEST.py` | Communication test: runs common pyBMS commands (config, cell measurement, balancing, redundant measurement), checks PEC and writes logs. `-d pico` (default) or `-d linduino` to compare against a Linduino |
| `demo_pico.py` | Flask web demo: cell voltages (raw / filtered / averaged), GPIO and device diagnostics. Calibration is currently disabled |
| `BMS_logger.py` | Loggers used by the test: parsed results (`bms_log.jsonl`) and raw TX/RX frames |
| `reference/demo_adi_original.py` | Original ADI Discharge_Algo_Demo (ADBMS6830, SDP-K1), kept as reference |
| `reference/logs/` | Captured communication logs (Linduino vs Pico) |

## Setup

1. Build `pico_usb.c` with the [Pico SDK](https://github.com/raspberrypi/pico-sdk)
   (USB stdio enabled, link `pico_stdlib` and `hardware_spi`) and flash the
   `.uf2` to the Pico.
2. Put the pyBMS library in a `pybms/` folder next to the scripts. The scripts
   add it to `sys.path` themselves.
3. Install the Python dependencies: `pip install pyserial flask waitress`.
4. Run:

```
python pyBMS_PC_TEST.py      # communication test + logs
python demo_pico.py          # web demo, opens http://127.0.0.1:5000/index
```

## Writing your own tests

Any pyBMS script works. You only have to use the Pico's serial port with the
`USB_TO_SPI_BYTE` interface. A minimal example that reads cell voltages:

```python
import sys
from pathlib import Path
import serial.tools.list_ports

sys.path.insert(0, str(Path(__file__).parent / "pybms"))

from DUTs.BMS import BMS
from Interfaces.USB_TO_SPI_BYTE import USB_TO_SPI_BYTE
from DUTs.BMS_Configs.ADBMS6832 import ADBMS6832

port = next(p.device for p in serial.tools.list_ports.comports() if p.vid == 0x2E8A)
interface = USB_TO_SPI_BYTE(port, 115200)
bms = BMS(interface)

# One entry per device in the daisy chain
board_list = [{"Device": ADBMS6832}]

commands = [
    {'command': '$SPI_SET_FREQUENCY_kHz$', 'arguments': {'Frequency': 1000}},
    {'command': '$SPI_WAKEUP$', 'arguments': {'Wakeup Time': 400}},
    {'command': 'WRCFGA'},
    {'command': 'ADCV', 'arguments': {'CONT': False}},
    {'command': '$DELAY_MS$', 'arguments': {'Delay': 20}},
    {'command': 'RDCVA', 'map_key': 'CELLS'},
]

result = bms.run_generic_command_list(commands, board_list)
print(result['CELLS'][0])   # results are lists, one entry per device in board_list
print("PEC OK:", result.get('Total_PEC_Status'))

interface.close()
```

Tips:
- `map_key` sets the key in the result dict. Reads with the same key are merged,
  e.g. `RDFCA`…`RDFCF` → `'CELLS'`.
- For more devices in the chain, add more entries to `board_list`, e.g.
  `[{"Device": ADBMS6832}, {"Device": ADBMS6832}]`.
- To see what actually goes over the wire, wrap the interface with
  `RawFrameLogger(interface)` from `BMS_logger.py`.
- `pyBMS_PC_TEST.py` and `demo_pico.py` have ready-made command lists for
  measurement, balancing, redundant measurement, GPIO and diagnostics you can
  copy from.

## Possible improvements

- Emulate the SDP-K1 USB descriptors so the ADI GUI software accepts the Pico.
- A standalone monitoring mode running directly on the Pico, without a PC.
- A dedicated PCB with the Pico 2 and the ADBMS6822 transceiver.
