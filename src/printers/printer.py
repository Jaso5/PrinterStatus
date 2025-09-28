from printrun.printcore import printcore
from printers.status_packet import Status
import re
from logging import Logger, getLogger
from paho.mqtt.client import Client
import json

status_regex = re.compile(r"done: ([0-9]*).+?mins: ([0-9]*)")


class Printer:
    printer: printcore

    # Config
    name: str
    model: str
    colour: str
    serial: str
    baud: int

    # Status
    connected = False
    paused = False
    file = "None"
    cwd = "None"

    # Internal
    mode = 'n' # n = normal, f = file list

    logger: Logger
    packet = Status()
    client: Client

    def __init__(self, config: dict[str, str | int], client: Client):
        self.name = str(config["name"])
        self.shortname = str(config["shortname"])
        self.model = str(config["model"])
        self.colour = str(config["colour"])
        self.serial = str(config["serial"])
        self.baud = int(config["baud"])

        self.logger = getLogger(self.name)
        self.client = client
        self.publish(f"printers/{self.shortname}/state", "Complete", retain=True)
        self.publish(
            f"printers/{self.shortname}/percent_done",
            0,
            retain=True,
        )
        self.publish(
            f"printers/{self.shortname}/time_remaining_mins",
            0,
            retain=True,
        )

    def connect(self) -> bool:
        self.logger.info(f"Connecting to printer {self.name}")
        # Connect
        try:
            # Connect to printer
            self.printer = printcore(port=self.serial, baud=self.baud)
            self.connected = True

        except Exception as err:
            self.logger.error(f"Could not connect to printer {self.name}: {err}")
            self.connected = False

        # Setup
        try:
            # Setup recieve callback
            self.printer.recvcb = self.handle_msg  # type: ignore
            self.printer.event_handler

        except Exception as err:
            self.logger.error(f"Could not setup printer {self.name}: {err}")
            self.connected = False

        return self.connected

    # Recieve callback
    def handle_msg(self, line: str):
        line = line.rstrip("\n")
        self.logger.debug(f"M: {self.mode} RECV: {line}")
        
        # Normal mode
        if self.mode == 'n':
            # Print Status echo: 'NORMAL MODE: Percent done: 32; print time remaining in mins: 8; Change in mins: -1'
            if line[0:11] == "NORMAL MODE":
                stats: regex.Match[str] = status_regex.search(line)  # type: ignore
                self.logger.debug(f"{stats.group(1)}, {stats.group(2)}")

                self.publish(
                    f"printers/{self.shortname}/state",
                    "Printing",
                    retain=True
                )
                self.publish(
                    f"printers/{self.shortname}/percent_done",
                    int(stats.group(1)),
                    retain=True,
                )
                self.publish(
                    f"printers/{self.shortname}/time_remaining_mins",
                    int(stats.group(2)),
                    retain=True,
                )

            # File opened: /JACOB/0.4/Cali-Dragon-Tiny_PLA.gcode Size: 467996
            elif line[0:12] == "File opened:":
                file_name = line[13:-1].split(" ")[0]
                self.publish(
                    f"printers/{self.shortname}/state", "Printing", retain=True
                )
                self.publish(
                    f"printers/{self.shortname}/file", file_name, retain=True
                )
                self.file = file_name
                self.cwd = '/'.join(file_name.split('/')[0:-2])

            # File Finished: 'Done printing file'
            elif line == "Done printing file":
                self.publish(
                    f"printers/{self.shortname}/state", "Complete", retain=True
                )
                # Get list of files
                self.printer.send_now("M20 L")
                self.publish(f"sound/g1/speak", f"Print finished on {self.name}")

            # Print manually paused: '//action:paused'
            elif line == "//action:paused":
                self.publish(
                    f"printers/{self.shortname}/state", "Paused", retain=True
                )

            # Print paused automatically
            elif line == "echo:busy: paused for user" and not self.paused:
                self.paused = True

                self.publish(
                    f"printers/{self.shortname}/state", "Paused", retain=True
                )
                self.client.publish(f"sound/g1/speak", f"Print paused on {self.name}")

            # Print cancelled
            elif line == "//action:cancel":
                self.client.publish(
                    f"printers/{self.shortname}/state", "Cancelled", retain=True
                )

            elif line[0:15] == "Begin file list":
                self.mode = 'f'
            else:
                self.logger.debug(f"Unknown Recv")
        
        # File list mode
        elif self.mode == 'f':
            if line == "End file list":
                self.mode = 'n'
            elif line[0:len(self.cwd)] == self.cwd:
                self.logger.debug(f"Matched dir: {line}")
                _SD_path, _size, long_name = line.split(" ")
                if long_name[1:18] == "config.discord...":
                    username = long_name[18:-9]

                    self.publish("irc/send", json.dumps({
                        "to": "#edinhacklab-things",
                        "message": f"@{username} print '{self.file}' complete on {self.name}"
                    }))

    def get_firmware_info(self):
        self.logger.debug("SEND: M115 ; firmware info")
        self.printer.send_now("M115")

    def get_filename(self):
        self.logger.debug("SEND: M27 C ; filename info")
        self.printer.send_now("M27 C")

    def publish(self, topic: str, payload: str, retain=False):
        if not self.client.is_connected():
            self.client.connect("mqtt.hacklab")
        
        self.client.publish(topic, payload, retain=retain)