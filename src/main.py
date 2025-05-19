import argparse
import time
import paho.mqtt.client as mqtt
import json
import logging

from printers.printer import Printer

mqtt = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt.connect("mqtt.hacklab")

logger = logging.getLogger()

name = None

printers = []

def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument("config", help="Path to a json config file")

    args = p.parse_args()

    return (args.config)

def main():
    # Write to log file
    logging.basicConfig(filename='log', level=logging.DEBUG)
    # Write to stderr
    logging.getLogger().addHandler(logging.StreamHandler())

    config_path: str = parse_args()

    logger.info("Loading config")

    try:
        config = json.load(open(config_path))
    except Exception as err:
        logger.error(f"Could not load config: {err}")
        exit(-1)

    logger.info("Printer init")

    for printer_config in config["printers"]:
        printer = Printer(printer_config)
        printer.connect()
        printers.append(printer)

    logger.info("Running")

    while True:
        time.sleep(10)

        

if __name__ == "__main__":
    main()