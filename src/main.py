import argparse
import time
import paho.mqtt.client as mqtt
import json
import logging

from printers.printer import Printer

mqtt = mqtt.Client()
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

    try:
        config = json.load(open(config_path))
    except Exception as err:
        logger.error(f"Could not load config: {err}")
        exit(-1)

    for printer_config in config["printers"]:
        printer = Printer(printer_config)
        printers.append(printer)

    while True:
        time.sleep(10)

        

if __name__ == "__main__":
    main()