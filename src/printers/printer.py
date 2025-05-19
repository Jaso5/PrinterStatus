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
            self.printer.recvcb = self.handle_msg # type: ignore
            self.printer.event_handler

        except Exception as err:
            self.logger.error(f"Could not setup printer {self.name}: {err}")
            self.connected = False

        return self.connected


    # Recieve callback
    def handle_msg(self, line: str):
        line = line.rstrip("\n")
        self.logger.debug(f"RECV: {line}")
        # Print Status echo: 'NORMAL MODE: Percent done: 32; print time remaining in mins: 8; Change in mins: -1'
        if line[0:11] == "NORMAL MODE":
            stats: regex.Match[str] = status_regex.search(line) # type: ignore
            self.logger.debug(f"{stats.group(1)}, {stats.group(2)}")

            self.client.publish(f"printers/{self.shortname}/percent_done", int(stats.group(1)), retain=True)
            self.client.publish(f"printers/{self.shortname}/time_remaining_mins", int(stats.group(2)), retain=True)
        # File Start echo: 'echo:enqueing "M23 CALI.G"'
        elif line[0:13] == "echo:enqueing":
            self.logger.debug(f"Print starting: {line[19:-1]}")

            self.client.publish(f"printers/{self.shortname}/state", "Printing", retain=True)
            self.client.publish(f"printers/{self.shortname}/file", line[19:-1], retain=True)
        # File Finished: 'Done printing file'
        elif line == "Done printing file":
            self.client.publish(f"printers/{self.shortname}/state", "Complete", retain=True)
            self.client.publish(f"sound/g1/speak ", f"Print finished on {self.name}")

        # Print manually paused: '//action:paused'
        elif line == "//action:paused":
            self.client.publish(f"printers/{self.shortname}/state", "Paused", retain=True)


    def get_firmware_info(self):
        self.logger.debug("SEND: M115 ; firmware info")
        self.printer.send_now("M115")

    def get_filename(self):
        self.logger.debug("SEND: M27 C ; filename info")
        self.printer.send_now("M27 C")