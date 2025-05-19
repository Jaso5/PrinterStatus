from printrun.printcore import printcore
from printers.status_packet import Status
import regex
from logging import Logger, getLogger

status_regex = regex.compile(r"done: ([0-9]*).+?mins: ([0-9]*)")

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


    def __init__(self, config: dict[str, str | int]):
        self.name = str(config["name"])
        self.model = str(config["model"])
        self.colour = str(config["colour"])
        self.serial = str(config["serial"])
        self.baud = int(config["baud"])

        self.logger = getLogger(self.name)


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

        except Exception as err:
            self.logger.error(f"Could not setup printer {self.name}: {err}")
            self.connected = False

        return self.connected


    # Recieve callback
    def handle_msg(self, line: str):
        self.logger.debug(line)
        # if line[0:11] == "NORMAL MODE":
        #     stats: regex.Match[str] = status_regex.match(line) # type: ignore

    def get_firmware_info(self):
        self.printer.send_now("M115")

    def get_filename(self):
        self.printer.send_now("M27 C")