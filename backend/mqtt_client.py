import paho.mqtt.client as mqtt
import json
from kivy.clock import Clock

# ====== CONFIGURE MQTT CONNECTION AND TOPICS ======
BROKER = "10.207.185.23"
PORT = 1883
USERNAME = "Ruyik1207"
PASSWORD = "Ruyik1207"

# Topics for Dashboard Data
TOPIC_TEMP = "lm35"
TOPIC_AIR = "mq135"
TOPIC_FAN = "PWM_Fan"
TOPIC_LIGHT = "light"
# =================================================

class DashboardClient(object):
    """
    Manages the MQTT connection and handles data updates for the Dashboard.
    Requires a reference to the Kivy App instance to update UI elements.
    """

    def __init__(self, app_instance):
        self.app = app_instance
        self.client = mqtt.Client()

        # Attach callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Set credentials and TLS for HiveMQ Cloud
        if USERNAME and PASSWORD:
            self.client.username_pw_set(USERNAME, PASSWORD)
            self.client.tls_set()

    def connect(self):
        try:
            print(f"Attempting MQTT connection to {BROKER}:{PORT}")
            self.client.connect_async(BROKER, PORT, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"MQTT connection error: {e}")
            # Update status label on the UI if possible
            Clock.schedule_once(lambda dt: self._update_status(f"Connect Error: {e}"))

    def on_connect(self, client, userdata, flags, rc):
        print(f"MQTT Dashboard connected with result code {rc}")
        if rc == 0:
            client.subscribe(TOPIC_TEMP)
            client.subscribe(TOPIC_AIR)
            client.subscribe(TOPIC_FAN)
            Clock.schedule_once(lambda dt: self._update_status("Connected"))
        else:
            Clock.schedule_once(lambda dt: self._update_status(f"Connection Failed: RC {rc}"))

    def on_disconnect(self, client, userdata, rc):
        print(f"MQTT Dashboard disconnected with result code {rc}")
        Clock.schedule_once(lambda dt: self._update_status("Disconnected"))

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8', errors='ignore')
        topic = msg.topic

        def update_ui(dt):
            # RESILIENCE FIX: Check if the screen manager and the screen exist
            try:
                # Use screen_names check to avoid the ScreenManagerException crash during early startup
                if 'dashboard' not in self.app.root.screen_names:
                    return
            except AttributeError:
                # Catches cases where self.app.root is not yet fully initialized
                return

            screen = self.app.root.get_screen('dashboard')

            if topic == TOPIC_TEMP:
                try:
                    # Expecting JSON like {"temp":26.5,"humidity":60}
                    data = json.loads(payload)
                    screen.ids.temp_lbl.text = str(data.get("temp", "--"))
                except Exception:
                    # Handle single value update if not JSON
                    screen.ids.temp_lbl.text = payload

            elif topic == TOPIC_AIR:
                screen.ids.aqi_lbl.text = payload

            elif topic == TOPIC_FAN:
                # FIX: Parse the JSON payload to get the speed integer
                try:
                    data = json.loads(payload)
                    speed = str(data.get("speed", "--"))
                except Exception:
                    speed = payload  # Fallback if it's just the speed string

                screen.ids.fan_speed_lbl.text = f"Speed: {speed}"

        Clock.schedule_once(update_ui)

    def _update_status(self, text):
        """Updates the status label on the Dashboard screen."""
        try:
            # RESILIENCE FIX: Check if the screen manager and the screen exist
            if 'dashboard' not in self.app.root.screen_names:
                return

            screen = self.app.root.get_screen('dashboard')
            screen.ids.status_lbl.text = f"MQTT: {text}"
        except Exception:
            # Fallback in case of any Kivy internal error during early startup
            pass

    def publish_turn_off(self):
        """Sends the command to turn off the smart light when sleep time is reached."""
        if not self.client.is_connected():
             print("MQTT Warning: Not connected. Cannot send OFF command.")
             return

        payload = "OFF"
        self.client.publish(TOPIC_LIGHT, payload, qos=1)
        print(f"MQTT Published: {TOPIC_LIGHT} OFF command.")
        Clock.schedule_once(lambda dt: self._update_status("Sent Light OFF"))

    def set_fan_speed(self, speed):
        """Publishes fan speed control message."""
        payload = json.dumps({"speed": speed})
        self.client.publish(TOPIC_FAN, payload, qos=1)
        # Status update relies on the subscription callback

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception:
            pass