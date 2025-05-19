from paho.mqtt.client import Client
import json

class Status:
    percent: float | None
    time_remaining: float | None

    file_name: str | None

    def set_percent(self, v: float) -> bool:
        self.percent = v
        return self.check_finished()

    def set_time_remaining(self, v: float) -> bool:
        self.time_remaining = v
        return self.check_finished()
    
    def set_file_name(self, v: str) -> bool:
        self.file_name = v
        return self.check_finished()
    
    def send(self, mqtt: Client, name: str):
        mqtt.publish(f"printers/{name}/status", json.dumps(self))
        
    def check_finished(self) -> bool:
        return (
            self.percent is not None and
            self.time_remaining is not None and
            self.file_name is not None
        )