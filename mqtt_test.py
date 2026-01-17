import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.username_pw_set("Ruyik1207", "Ruyik1207")
client.tls_set(tls_version=ssl.PROTOCOL_TLS)

print("Connecting...")
client.connect("7ee730ad4f4844238c7b610899e8c193.s1.eu.hivemq.cloud", 8883)
print("Connected OK!")