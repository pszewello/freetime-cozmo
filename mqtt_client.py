import sys
try:
    import gmqtt
except ImportError:
    sys.exit("Cannot import from gmqtt: Do `pip3 install --user gmqtt` to install")

class MqttClient():

    def __init__(self, broker_url, port, user_name, password, topics, on_message):
        self._broker_url = broker_url
        self._port = port
        self._client = gmqtt.Client("mqtt-client")
        self._client.set_auth_credentials(user_name, password)
        self._client.on_connect = self._on_connect
        self._client.on_message = on_message
        self._topics = topics

    async def connect_async(self) -> None:
        await self._client.connect(self._broker_url, self._port)
    
    async def disconnect_async(self) -> None:
        await self._client.disconnect()

    def publish(self, topic: str, payload: dict) -> None:
        print("Published {} to {}".format(payload, topic))
        self._client.publish(topic, payload)

    def _on_connect(self, client, flags, rc, properties) -> None:
        print("Connected with result code {}".format(str(rc)))
        for topic in self._topics:
            print("Subscribing to {}".format(topic))
            client.subscribe(topic, qos=0)

  


