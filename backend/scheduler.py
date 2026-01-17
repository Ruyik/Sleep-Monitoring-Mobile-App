import time
import threading
from datetime import datetime

class SleepScheduler:
    def __init__(self, mqtt_client, db):
        self.mqtt = mqtt_client
        self.db = db
        self.running = False
        self.remaining_seconds = 0

    def set_schedule(self, time_str):
        self.db.save_schedule(time_str)

    def start_countdown(self, target_time_str, callback_update, callback_finished):
        """ target_time_str format: '23:00' """

        self.running = True

        def run():
            while self.running:
                now = datetime.now().strftime("%H:%M")
                if now >= target_time_str:
                    callback_finished()
                    self.mqtt.publish_turn_off()
                    break
                time.sleep(1)

        thread = threading.Thread(target=run)
        thread.start()

    def extend_time(self, minutes):
        self.db.save_extension(minutes)
        self.mqtt.publish_extend(minutes)
