import json
from datetime import datetime

class LoggerBase:
    
    def __init__(self, filename):
        self.filename = filename

        with open(self.filename, "w", encoding="utf-8"):
            pass

    def write_entry(self, entry):

        with open(self.filename, "a", encoding="utf-8") as f:
            json.dump(entry, f, default=str)
            f.write("\n")



class BMSLogger(LoggerBase):

    def __init__(self, filename="bms_log.jsonl"):
        super().__init__(filename)

    def log(self, result):

        entry = {
            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "PEC":
                result.get(
                    "Total_PEC_Status"
                )
        }

        if "CFG" in result:
            entry["CFG"] = result["CFG"]

        if "CELLS" in result:
            entry["CELLS"] = result["CELLS"]

        if "CT" in result:
            entry["CT"] = result["CT"]

        if "MUTE" in result:
            entry["MUTE"] = result["MUTE"]

        if "UNMUTE" in result:
            entry["UNMUTE"] = result["UNMUTE"]

        self.write_entry(entry)

        return result

    def write(self, message):

        self.write_entry({
            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "message":
                message
        })

    

class RawFrameLogger(LoggerBase):

    def __init__(self, interface,
                 filename="raw_frames.jsonl"):

        super().__init__(filename)

        self.interface = interface

        orig_get = self.interface.get_commands
        orig_add = self.interface.add_command_to_buffer

        def wrapped_get(*args, **kwargs):

            raw = orig_get(*args,**kwargs)

            if raw:
                self.log("RX", raw)
            return raw
        def wrapped_add (command):
            result = orig_add(command)
            self.log("TX", {"TYPE": command.TYPE, "bytes": list(command.bytes)})
            return result

        self.interface.get_commands = wrapped_get
        self.interface.add_command_to_buffer = wrapped_add

    def log(self, direction, data):

        entry = {
            "timestamp":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            "direction": direction,

            "data" : data
        }

        self.write_entry(entry)
