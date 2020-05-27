from typing import Awaitable, Dict, Union, Tuple
import mqtt_client
import cozmo_client
import json
import asyncio
import cozmo
from cozmo.lights import Color, Light
from cozmo.conn import CozmoConnection
from cozmo.faces import Face
from cozmo.objects import ObservableObject
import sys
from multiprocessing import SimpleQueue
import functools
import types
from message_manager import MessageManager
from datetime import datetime
from cozmo_states import CozmoStates

#Provide MQTT broker data if want mqtt
MQTT_BROKER_URL = None 
MQTT_BROKER_PORT = None
MQTT_USERNAME = None
MQTT_PASSWORD = None
MQTT_WEATHER_TOPIC = "home-assistant/cozmo/notification"
MQTT_CONTROL_TOPIC = "home-assistant/cozmo/control"
COZMO_MQTT_PUBLISHING_TOPIC = "cozmo/status"
MQTT_TOPICS = [MQTT_WEATHER_TOPIC, MQTT_CONTROL_TOPIC]
YELLOW = (255, 255, 0)
SLATE_GRAY = (119, 136, 153)


class CozmoMqttProgram():
    def __init__(self) -> None:
        self._cozmo = cozmo_client.Cozmo()
        self._queue = SimpleQueue()
        self._mqtt_client = None
        if MQTT_BROKER_URL is not None:
            self._mqtt_client = mqtt_client.MqttClient(
                MQTT_BROKER_URL,
                MQTT_BROKER_PORT,
                MQTT_USERNAME,
                MQTT_PASSWORD,
                MQTT_TOPICS, self._on_mqtt_message)
        self.sdk_conn: CozmoConnection = None
        self._faces: Dict[Face, datetime] = dict()
        self._visible_objects: Dict[ObservableObject, datetime] = dict()
        self._message_manager = MessageManager()
        self._cozmo_state = CozmoStates.Disconnected
    
    @property
    def cozmo_state(self) -> CozmoStates:
        return self._cozmo_state

    @cozmo_state.setter
    def cozmo_state(self, state: CozmoStates) -> None:
        self._cozmo_state = state
        self._publish_cozmo_state()

    async def run_with_robot_async(self, robot: cozmo.robot.Robot) -> None:
        self.sdk_conn = robot.world.conn
        await self._run_async(robot)    

    async def _run_async(self, robot: cozmo.robot.Robot) -> None:
        await self._initialize_async(robot)
        try:
            while self.sdk_conn.is_connected:
                self._cozmo.update_needs_level()
                if self._cozmo.needs_charging() and not self._cozmo.is_sleeping:
                    await self._charge_cycle()
                    await self._cozmo.wake_up_async()
                    self._cozmo_freetime()

                if not self._queue.empty():
                    await self._handel_queue_async()

                if self._cozmo.world.visible_face_count() > 0:
                    face = self._get_visible_face()
                    if face:
                        if face in self._faces:
                            last_seen = self._faces[face]
                            if (datetime.now() - last_seen).total_seconds() > 60:
                                await self._cozmo_do_async(self._on_saw_face(face))
                        else:
                            await self._cozmo_do_async(self._on_saw_face(face))

                if self._cozmo.robot.is_picked_up:
                    await self._cozmo_do_async(self._on_picked_up_async()) 
  
                if self._cozmo.robot.is_cliff_detected:                   
                    await self._cozmo_do_async(self._on_cliff_detected_async()) 
                
                if self._cozmo.world.visible_object_count(object_type=ObservableObject) > 0:
                    visible_object = self._get_visible_object()
                    if visible_object:
                        if visible_object in self._visible_objects:
                            last_seen = self._visible_objects[visible_object]
                            if (datetime.now() - last_seen).total_seconds() > 60 * 5:
                                await self._cozmo_do_async(self._on_new_object_appeared_async(visible_object))
                        else:
                            await self._cozmo_do_async(self._on_new_object_appeared_async(visible_object))

                await asyncio.sleep(0.1)
        except:
            print("Unexpected error:", sys.exc_info()[0])
        
        await self.terminate_async()

    async def _initialize_async(self, robot: cozmo.robot.Robot) -> None:
        self._observe_connection_lost(self.sdk_conn, self._on_connection_lost)
        self._cozmo.set_robot(robot)
        await asyncio.gather(
            self._cozmo.connect_to_cubes_async(),
            self._cozmo.get_off_charger_async()
        )
        if self._mqtt_client is not None:
            await self._mqtt_client.connect_async()
        self.cozmo_state = CozmoStates.Connected
        self._cozmo_freetime()
    
    async def terminate_async(self) -> None:
        print("Terminating")
        if self._mqtt_client is not None:
            await self._mqtt_client.disconnect_async()
        if self.sdk_conn.is_connected:
            print("Sending cozmo back to charger")
            await self._cozmo.stop_all_actions_async()
            self._cozmo.back_to_normal()
            await self._cozmo.get_on_charger_async()

    def _observe_connection_lost(self, connection: CozmoConnection, cb):
        meth = connection.connection_lost
        @functools.wraps(meth)
        def connection_lost(self, exc):
            meth(exc)
            cb()
        connection.connection_lost = types.MethodType(connection_lost, connection)

    def _on_connection_lost(self) -> None:
        print("Captured connection lost")
        self.cozmo_state = CozmoStates.ConnectionLost

    def _publish_cozmo_state(self) -> None:
        if self._mqtt_client is not None:
            payload = dict()
            payload["status"] = self.cozmo_state.value
            attributes = dict()
            if self._cozmo.robot:
                attributes["battery_voltage"] = self._cozmo.battery_voltage
            payload["attributes"] = attributes
            self._mqtt_client.publish(COZMO_MQTT_PUBLISHING_TOPIC, payload)
    
    async def _on_saw_face(self, face: Face) -> None:
        self._faces[face] = datetime.now()
        self.cozmo_state = CozmoStates.SawFace
        print("An face appeared: {}".format(face))
        if face.name:
            await self._cozmo.turn_toward_face_async(face)
            message = self._message_manager.get_hello_message(face)
            await self._cozmo.random_positive_anim_async()
            await self._cozmo.say_async(message)
            if face.known_expression:
                message = self._message_manager.get_fece_expression_message(face.known_expression, face)
                await self._cozmo.say_async(message)
        else:
            message = self._message_manager.get_non_recognized_message(face)
            await self._cozmo.say_async(message)

    async def _on_picked_up_async(self) -> None:
        print("Cozmo was picked up")
        self.cozmo_state = CozmoStates.PickedUp
        face = self._get_visible_face()
        message = self._message_manager.get_picked_up_message(face)
        await self._cozmo.random_positive_anim_async() 
        if face:
            await self._cozmo.display_camera_image_async()        
        await self._cozmo.say_async(message)
        while self._cozmo.robot.is_picked_up:
            await asyncio.sleep(0.1)
        print("Cozmo was put down")
        
    async def _on_cliff_detected_async(self) -> None:
        print("Cozmo detected a cliff")
        self.cozmo_state = CozmoStates.OnCliff
        self._cozmo.stop()
        self._cozmo.clear_current_animations()
        await self._cozmo.drive_wheels_async(-40, 1)
        face = self._get_visible_face()
        message = self._message_manager.get_cliff_detected_message(face)      
        await self._cozmo.random_negative_anim_async()      
        await self._cozmo.say_async(message)
        while self._cozmo.robot.is_cliff_detected:
            await asyncio.sleep(0.1)
        print("Cozmo away from cliff")
    
    async def _on_new_object_appeared_async(self, visible_object:ObservableObject ) -> None:
        self._visible_objects[visible_object] = datetime.now()
        print("An obbject appeared: {}".format(visible_object))
        face = self._get_visible_face()
        message = self._message_manager.get_object_appeared_message(visible_object, face)
        await self._cozmo.say_async(message)

    def _get_visible_face(self) -> Face:
        if self._cozmo.world.visible_face_count() == 0:
            print("Found no visibile faces")
            return None

        visible_face = next((face for face in self._cozmo.world.visible_faces), None)
        return visible_face
    
    def _get_visible_object(self) -> ObservableObject:
        if self._cozmo.world.visible_object_count(object_type=ObservableObject) == 0:
            print("Found no visibile objects")
            return None

        visible_obj = next((obj for obj in self._cozmo.world.visible_objects), None)
        return visible_obj

    def _cozmo_freetime(self) -> None:
        self._cozmo.start_free_time()
        self.cozmo_state = CozmoStates.Freetime

    async def _cozmo_do_async(self, async_f: Awaitable) -> None:
        if self._cozmo.freetime_enabled:
            self._cozmo.stop_free_time()
        try:
            await async_f
            self._cozmo_freetime()
        except cozmo.RobotBusy:
            print("Task Exception...cozmo is Busy")

    async def _charge_cycle(self) -> None:
        self.cozmo_state = CozmoStates.GoingToCharge
        print("Cozmo needs charging. Battery level {}".format(self._cozmo.battery_voltage))
        await self._cozmo.start_charging_routine_async()
        self.cozmo_state = CozmoStates.Charging
        await self._cozmo.charge_to_full_async()
        print("Cozmo charged")

    # MQTT Queue Related-------------------------------------------------------------------------------------------------------------------
    def _on_mqtt_message(self, client, topic, payload, qos, properties) -> None:
        try:
            json_data = json.loads(payload.decode('utf-8'))
            print("Topic: {}".format(topic))
            print("Data: {}".format(json_data))
            topic_data_tuple = (topic, json_data)
            self._queue.put(topic_data_tuple)
        except:
            print("Unexpected error:", sys.exc_info()[0])

    async def _handel_queue_async(self) -> None:
        if not self._queue.empty():
            print("Cozmo processing queue")
            await self._cozmo_do_async(self._process_message_async(self._queue.get()))
            await self._handel_queue_async()

    async def _process_message_async(self, topic_data_tuple: tuple) -> None:
        topic = topic_data_tuple[0]
        json_data = topic_data_tuple[1]
        if topic == MQTT_WEATHER_TOPIC:
            await self._process_weather_notification_async(json_data)
        elif topic == MQTT_CONTROL_TOPIC:
            await self._process_control_msg_async(json_data)
    
    async def _process_control_msg_async(self, json_data: dict) -> None:
        if "msg" in json_data:
            msg = json_data["msg"]
            if msg == 'sleep':
                asyncio.create_task(self._cozmo.sleep_async())
            if msg == 'freetime':
                await self._cozmo.wake_up_async()
                self._cozmo_freetime()

    async def _process_weather_notification_async(self, json_data: dict) -> None:
        if "msg" in json_data:
            msg = json_data["msg"]
            image_url = None
            color = None
            title = "I have a weather update notification for you."
            if "imagePath" in json_data:
                image_url = json_data["imagePath"]
            if 'clear' in msg:
                print("Clear outside!")
                color = YELLOW
            elif 'cloudy' in msg:
                print("Cloudy outside!")
                color = SLATE_GRAY
            await self._cozmo_annonuce_weather_update_async(msg, title, color, image_url)

    async def _cozmo_annonuce_weather_update_async(self, msg: str, title: str, rgb: Union[Tuple, None] = None, image_url: str = None) -> None:
        self.cozmo_state = CozmoStates.Anouncing
        if rgb:
            light = Light(Color(rgb=rgb)).flash()
            self._cozmo.cubes_change_lights(light)
            self._cozmo.backpack_change_light(light)
        await self._cozmo.random_positive_anim_async()
        await self._cozmo.say_async(title)
        await self._cozmo.say_async(msg)
        if image_url:
            await self._cozmo.show_image_from_url_async(image_url)
        if rgb:
            self._cozmo.turn_cubes_lights_off()
            self._cozmo.turn_backpack_light_off()
