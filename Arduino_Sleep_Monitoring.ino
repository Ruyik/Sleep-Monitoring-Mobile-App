#include <WiFi.h>
#include <PubSubClient.h>
#include "MQ135.h"

// -------------------- 0. WIFI & MQTT CONFIG --------------------
const char* ssid     = "Jn";
const char* password = "12345678";

// Broker (NON-TLS)
const char* mqtt_server = "172.20.10.2";
const uint16_t mqtt_port = 1883;

const char* mqtt_user = "Ruyik1207";
const char* mqtt_pass = "Ruyik1207";

// MQTT topics (KEEP ORIGINAL)
const char* topic_lm35        = "lm35";
const char* topic_mq135       = "mq135";
const char* topic_fan         = "PWM_Fan";
const char* topic_light       = "light";          // subscribe
const char* topic_dcfan       = "DC_Fan";         // subscribe command (Node-RED -> ESP32)

// NEW essential topics (added, original topics unchanged)
const char* topic_dcfan_btn   = "DC_Fan_btn";     // ESP32 button event -> Node-RED ("TOGGLE")
const char* topic_dcfan_state = "DC_Fan_state";   // ESP32 publishes effective DC fan state (0/1)

WiFiClient espClient;
PubSubClient client(espClient);

// --- 1. PIN DEFINITIONS ---
const int GAS_AOUT_PIN    = 32;
const int TEMP_SENSOR_PIN = 35;
const int BUTTON_DC_FAN   = 12;
const int BUTTON_LED_PIN  = 16;
const int LED_PIN         = 2;

const int IN1 = 26; // PWM Fan Channel A
const int IN2 = 27;
const int IN3 = 18; // DC Fan Channel B
const int IN4 = 19;

// --- 2. CONFIGURATION & STATE ---
const float MY_CALIBRATED_R0 = 60.0;
MQ135 gasSensor = MQ135(GAS_AOUT_PIN, MY_CALIBRATED_R0);

// Thresholds
const float PWM_FAN_TEMP_MIN = 28.0;
const float PWM_FAN_PPM_MIN  = 500.0;

// DC fan high-temp OFF (safety / automation requirement)
const float DC_FAN_TEMP_OFF  = 35.0;   // adjust as needed

// LED states
bool manualLedState = false;
bool lastLedBtnReading = HIGH;

// DC fan states
bool dcFanState = true;            // kept (not directly used for control now; Node-RED decides)
bool dcFanForceOff = false;        // true when Node-RED says OFF (for display)
bool lastDcBtnReading = HIGH;

// Node-RED command (source of truth for ON/OFF)
bool dcFanCmdFromNR = true;        // ON/OFF from Node-RED via topic_dcfan
bool dcFanTempOff = false;         // local safety override when temp too high
bool dcFanEffectiveState = false;  // final applied to motor

// Timing Variables
unsigned long lastDebounceTimeLed = 0;
unsigned long lastDebounceTimeDc  = 0;
const unsigned long debounceDelay = 50;

unsigned long lastSerialTime = 0;
const unsigned long serialInterval = 5000; // 5 Seconds

unsigned long lastPublish = 0;
const unsigned long publishInterval = 1000; // 1 Second

// -------------------- MQTT CALLBACK --------------------
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String t = String(topic);

  String p;
  for (unsigned int i = 0; i < length; i++) p += (char)payload[i];
  p.trim();

  // DC fan command from Node-RED (ON/OFF)
  if (t == topic_dcfan) {
    if (p.equalsIgnoreCase("ON")  || p == "1") dcFanCmdFromNR = true;
    if (p.equalsIgnoreCase("OFF") || p == "0") dcFanCmdFromNR = false;
  }

  // LED command from Node-RED (ON/OFF)
  if (t == topic_light) {
    if (p.equalsIgnoreCase("ON")  || p == "1") manualLedState = true;
    if (p.equalsIgnoreCase("OFF") || p == "0") manualLedState = false;
  }
}

// -------------------- WIFI SETUP --------------------
void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("WiFi connected. IP address: ");
  Serial.println(WiFi.localIP());
}

// -------------------- MQTT RECONNECT --------------------
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection... ");

    String clientId = "ESP32_Proto_";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("connected.");

      // Subscribe to command topics (Node-RED -> ESP32)
      client.subscribe(topic_light);
      client.subscribe(topic_dcfan);

    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" — retry in 5 seconds");
      delay(5000);
    }
  }
}

// -------------------- DC FAN BUTTON -> NODE-RED (PUBLISH EVENT) --------------------
void handleDcFanButton(unsigned long now) {
  bool currentReading = digitalRead(BUTTON_DC_FAN);

  // detect press (HIGH -> LOW) with debounce
  if (currentReading == LOW && lastDcBtnReading == HIGH) {
    if ((now - lastDebounceTimeDc) > debounceDelay) {
      // IMPORTANT: publish to NEW button topic, not DC_Fan command topic
      client.publish(topic_dcfan_btn, "TOGGLE", true);
      lastDebounceTimeDc = now;
    }
  }
  lastDcBtnReading = currentReading;
}

// -------------------- APPLY DC FAN OUTPUT --------------------
void applyDcFanOutput() {
  // Node-RED is source of command, but temp override forces OFF
  dcFanEffectiveState = (dcFanCmdFromNR && !dcFanTempOff);

  // for monitoring print: "NR_OFF" when Node-RED command is OFF
  dcFanForceOff = (!dcFanCmdFromNR);

  if (dcFanEffectiveState) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  } else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(BUTTON_DC_FAN, INPUT_PULLUP);
  pinMode(BUTTON_LED_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  Serial.println("--- Monitoring Started: 5s Interval + MQTT ---");

  setupWiFi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqttCallback);
}

void loop() {
  // MQTT keep-alive
  if (!client.connected()) reconnectMQTT();
  client.loop();

  unsigned long currentTime = millis();

  // --- A. READ SENSORS (use your code) ---
  int raw_temp = analogRead(TEMP_SENSOR_PIN);
  float tempC = (raw_temp / 4095.0f) * 330.0f;

  
  if (tempC < 25.0) {
    tempC = 25.0;
  }

  float ppm = gasSensor.getPPM();
  if (isnan(ppm) || ppm < 400) {
    ppm = 400.0; 
  }

  // 3. FIX: Cap Maximum at 1000
  // If the sensor screams 2000+, we force it down to 1000
  if (ppm > 1000.0) {
    ppm = 1000.0;
  }

  // --- B. PWM FAN LOGIC ---
  bool pwmShouldRun = (tempC >= PWM_FAN_TEMP_MIN || ppm >= PWM_FAN_PPM_MIN);
  if (pwmShouldRun) {
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  } else {
    digitalWrite(IN1, LOW);  digitalWrite(IN2, LOW);
  }

  // --- C. DC FAN LOGIC (IoT: button -> Node-RED; Node-RED -> command; temp high forces OFF) ---
  handleDcFanButton(currentTime);

  // local safety override: turn OFF when temperature is high
  dcFanTempOff = (tempC >= DC_FAN_TEMP_OFF);

  applyDcFanOutput();

  // --- D. LED TOGGLE LOGIC (Button local + Node-RED command) ---
  bool currentLedBtnReading = digitalRead(BUTTON_LED_PIN);
  if (currentLedBtnReading == LOW && lastLedBtnReading == HIGH) {
    if ((currentTime - lastDebounceTimeLed) > debounceDelay) {
      manualLedState = !manualLedState;
 lastDebounceTimeLed = currentTime;
    }
  }
  lastLedBtnReading = currentLedBtnReading;
  digitalWrite(LED_PIN, manualLedState ? HIGH : LOW);

  // --- E. MONITORING (Every 5 Seconds) ---
  if (currentTime - lastSerialTime >= serialInterval) {
    Serial.println("---------------------------------------------");
    Serial.print("| TEMP: "); Serial.print(tempC, 1); Serial.print("C ");
    Serial.print("| PPM: ");  Serial.print(ppm, 0);   Serial.println(" |");

    Serial.print("| LED: ");  Serial.print(manualLedState ? "ON " : "OFF");
    Serial.print(" | DC FAN: "); Serial.print(dcFanEffectiveState ? "RUN " : "STOP");
    Serial.print(dcFanForceOff ? " (NR_OFF)" : " (NR_ON)");
    Serial.print(dcFanTempOff ? " (TEMP_OFF)" : "");
    Serial.print(" | PWM FAN: "); Serial.println(pwmShouldRun ? "RUN " : "IDLE");
    Serial.println("---------------------------------------------");

    lastSerialTime = currentTime;
  }

  // --- F. MQTT PUBLISH (Every 1 Second) ---
  if (currentTime - lastPublish >= publishInterval) {
    lastPublish = currentTime;

    char bufTemp[16];
    char bufPPM[16];
    char bufPwmFan[4];
    char bufDcFan[4];
    char bufLight[4];

    dtostrf(tempC, 6, 2, bufTemp);
    dtostrf(ppm,   6, 0, bufPPM);

    itoa(pwmShouldRun ? 1 : 0, bufPwmFan, 10);
    itoa(manualLedState ? 1 : 0, bufLight, 10);
    itoa(dcFanEffectiveState ? 1 : 0, bufDcFan, 10);

    client.publish(topic_lm35, bufTemp, true);
    client.publish(topic_mq135, bufPPM, true);
    client.publish(topic_fan, bufPwmFan, true);
    client.publish(topic_light, bufLight, true);
    client.publish(topic_dcfan_state, bufDcFan, true);
  }

  delay(100); // 0.1s Operation Speed
}
