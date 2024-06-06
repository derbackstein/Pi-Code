import paho.mqtt.client as mqtt

broker_address = "192.168.188.95"  # IP-Adresse des Raspberry Pi
client = mqtt.Client("PCClient", transport="tcp")

def on_connect(client, userdata, flags, rc):
    print("Verbunden mit Ergebniscode " + str(rc))

client.on_connect = on_connect
client.connect(broker_address, 1883, 60)

client.loop_start()

topic = "your_topic"
message = "false"
client.publish(topic, message)
print(f"Sende '{message}' zum Thema '{topic}'")

client.loop_stop()