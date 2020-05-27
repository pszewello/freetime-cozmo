import cozmo
from cozmo.anim import Triggers
from cozmo.faces import Face
from cozmo.lights import Light
from cozmo.robot import Robot
from cozmo.objects import LightCube1Id, LightCube2Id, LightCube3Id, LightCube, ObservableObject, Charger
from cozmo.util import degrees, radians, distance_mm, speed_mmps, Pose
from cozmo.behavior import BehaviorTypes
from cozmo.world import World
import math
import sys
import io
import base64
from urllib.request import urlopen
from typing import List
import asyncio
import random

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


class Cozmo():
    def __init__(self) -> None:
        self._robot: Robot = None
        Robot.drive_off_charger_on_connect = False
        cozmo.setup_basic_logging()
        self.PI: float = 3.14159265359
        self._cubes_connected = False
        self._freetime = False
        self._sleeping = False

    def set_robot(self, robot: Robot):
        self._robot = robot
        self._robot.enable_stop_on_cliff(True)
        self._robot.set_robot_volume(0.2)
        self._robot.camera.enable_auto_exposure()
        self._robot.enable_facial_expression_estimation(True)
        self._robot.camera.image_stream_enabled = True
        self._robot.camera.color_image_enabled = False
        #reactions to surroundings
        self._robot.enable_all_reaction_triggers(False)
        print("Battery voltage: {}".format(self.battery_voltage))

    @property
    def freetime_enabled(self) -> bool:
        return self._freetime

    @property
    def battery_voltage(self) -> float:
        return self._robot.battery_voltage

    @property
    def world(self) -> World:
        return self._robot.world

    @property
    def robot(self) -> Robot:
        return self._robot

    @property
    def cubes(self) -> List[LightCube]:
        return [self.get_cube_by_id(LightCube1Id), self.get_cube_by_id(LightCube2Id), self.get_cube_by_id(LightCube3Id)]

    def back_to_normal(self) -> None:
        print("Seting Cozmo back to normal")
        if self._freetime:
            self.stop_free_time()
        self.turn_backpack_light_off()
        if self._cubes_connected:
            self._disconnect_from_cubes()
        self._robot.clear_idle_animation()

    async def stop_all_actions_async(self) -> None:
        print("Stoping all Cozmo actions")
        if self._freetime:
            self.stop_free_time()
        self._robot.abort_all_actions(log_abort_messages=True)
        self._robot.stop_all_motors()
        await self._robot.wait_for_all_actions_completed()

    # Charging / Sleeping ----------------------------------------------------------------
    @property
    def is_charging(self) -> bool:
        return self._robot.is_charging

    @property
    def is_sleeping(self) -> bool:
        return self._sleeping

    def needs_charging(self) -> bool:
        return self.battery_voltage <= 3.4 and not self.is_charging
    
    def is_charged(self) -> bool:
        return not self._robot.is_charging

    async def start_charging_routine_async(self) -> None:
        print("Starting charging routine")
        if self._cubes_connected:
            self._disconnect_from_cubes()
        await self.stop_all_actions_async()
        await self.go_to_sleep_anim_async()
        await self.get_on_charger_async()

    async def charge_to_full_async(self) -> None:
        print("Charging...")
        await self.go_to_sleep_off_anim_async()
        while not self.is_charged():
            await self.snore_anim_async()
            await asyncio.sleep(random.randint(30, 60)) 
        self.update_needs_level(1)     
        await self.get_off_charger_async()
    
    async def sleep_async(self) -> None:
        await self.start_charging_routine_async()
        print("Sleeping...")
        self._sleeping = True
        await self.go_to_sleep_off_anim_async()
        while self.is_sleeping:
            print("Battery voltage: {}".format(self.battery_voltage))
            await self.snore_anim_async()
            await asyncio.sleep(random.randint(30, 60)) 
            if self.needs_charging():
                await self._robot.backup_onto_charger(max_drive_time=5)
            elif self.is_charged():
                await self._robot.drive_off_charger_contacts(self._robot).wait_for_completed()

    async def wake_up_async(self) -> None:
        self._sleeping = False
        await self.connect_to_cubes_async()
        await self.wake_up_anim_async()       

    def update_needs_level(self, needs_level: float = None):
        if not needs_level:
            needs_level = 1 - (4.05 - self.battery_voltage)
        if needs_level < 0.1:
            needs_level = 0.1
        if needs_level > 1:
            needs_level = 1
        needs_level = round(needs_level, 2)
        #print("Setting Cozmo needs to {}".format(needs_level))
        self._robot.set_needs_levels(repair_value=needs_level, energy_value=needs_level, play_value=needs_level)

    # Speak ----------------------------------------------------------------
    async def say_async(self, message: str) -> None:
        print("Cozmo will speak: " + message)
        await self._robot.say_text(message).wait_for_completed()

    # Display Images ----------------------------------------------------------------
    async def show_image_from_bytes_async(self, imageToShow: str) -> None:
        print("Cozmo will show and image: " + imageToShow)
        data = imageToShow.encode("utf-8")
        image = Image.open(io.BytesIO(base64.b64decode(data)))
        await self._show_image_async(image)

    async def show_image_from_url_async(self, imageUrl: str) -> None:
        print("Cozmo will show and image: " + imageUrl)
        image = Image.open(urlopen(imageUrl))
        await self._show_image_async(image)

    async def _show_image_async(self, image: Image) -> None:
        print("Getting ready to show image")
        await self._show_face_async()
        # image.show()
        resized_image = image.resize(cozmo.oled_face.dimensions(), Image.NEAREST)
        face_image = cozmo.oled_face.convert_image_to_screen_data(resized_image, invert_image=True)
        print("Showing image:{}".format(image))
        await self._robot.display_oled_face_image(face_image, 5 * 1000.0).wait_for_completed()

    async def _show_face_async(self) -> None:
        if (self._robot.lift_height.distance_mm > 45) or (self._robot.head_angle.degrees < 40):
            lift_action = self._robot.set_lift_height(0.0, in_parallel=True)
            head_action = self._robot.set_head_angle(cozmo.robot.MAX_HEAD_ANGLE, in_parallel=True)
            await lift_action.wait_for_completed()
            await head_action.wait_for_completed()
    
    async def display_camera_image_async(self) -> None:
        image = self.get_camera_image()
        image = image.transpose(Image.FLIP_LEFT_RIGHT)
        await self._show_image_async(image)

    # Vision --------------------------------------------------------------------------
    def head_lights(self, on: bool) -> None:
        self._robot.set_head_light(on)
    
    def get_camera_image(self) -> Image:
        print("Getting last image")
        return self._robot.world.latest_image.raw_image
    
    # Sound --------------------------------------------------------------------------
    def play_sound(self, audio_event: cozmo.audio._AudioEvent) -> None:
        self._robot.play_audio(audio_event)

    # Faces and Reactions ----------------------------------------------------------------
    def clear_current_animations(self) -> None:
        self._robot.clear_idle_animation()

    async def random_positive_anim_async(self) -> None:
        triggers = [
            Triggers.MajorWin,
            Triggers.CodeLabHappy,
            Triggers.CodeLabYes,
            Triggers.CodeLabAmazed,
            Triggers.CodeLabCelebrate,
            Triggers.PopAWheelieInitial,
            Triggers.FeedingAteFullEnough_Normal,
            Triggers.DriveEndHappy,
            Triggers.BlockReact
        ]
        trigger = random.choice(triggers)
        print("Animating positive emotions: {}".format(trigger))
        await self._robot.play_anim_trigger(trigger).wait_for_completed()
    
    async def random_negative_anim_async(self) -> None:
        triggers = [
            Triggers.MajorFail,
            Triggers.CubeMovedUpset,
            Triggers.CodeLabUnhappy,
            Triggers.PounceFail,
            Triggers.CodeLabBored,
            Triggers.FrustratedByFailureMajor
        ]
        trigger = random.choice(triggers)
        print("Animating negative emotions: {}".format(trigger))
        await self._robot.play_anim_trigger(trigger).wait_for_completed()

    async def go_to_sleep_anim_async(self) -> None:
        trigger = Triggers.GoToSleepGetIn
        await self._robot.play_anim_trigger(trigger).wait_for_completed()

    async def go_to_sleep_off_anim_async(self) -> None:
        trigger = Triggers.GoToSleepOff
        await self._robot.play_anim_trigger(trigger).wait_for_completed()

    async def snore_anim_async(self) -> None:
        trigger = Triggers.Sleeping
        await self._robot.play_anim_trigger(trigger).wait_for_completed()
    
    async def wake_up_anim_async(self) -> None:
        trigger = Triggers.ConnectWakeUp
        await self._robot.play_anim_trigger(trigger).wait_for_completed()
    # Movement ----------------------------------------------------------------
    async def move_straight_async(self, distance: float, speed: float) -> None:
	    await self._robot.drive_straight(distance_mm(distance), speed_mmps(speed)).wait_for_completed()
		#self.robot.go_to_pose(Pose(Distance, 0, 0, angle_z=degrees(0)), relative_to_robot=True)

    async def drive_wheels_async(self, distance: float, duration: float) -> None:
        await self._robot.drive_wheels(distance, distance, duration=duration)

    async def turn_async(self, angle: float) -> None:
        await self._robot.turn_in_place(degrees(angle)).wait_for_completed() 

    async def turn_around_async(self) -> None:
        await self._robot.turn_in_place(degrees(-180)).wait_for_completed()
    
    def stop(self) -> None:  
        print("Stopping!")
        self._robot.stop_all_motors()
        self._robot.abort_all_actions(log_abort_messages=False)

    def move_head(self, radians: int) -> None:
        if radians > cozmo.robot.MAX_HEAD_ANGLE:
            radians = cozmo.robot.MAX_HEAD_ANGLE
        if radians < cozmo.robot.MIN_HEAD_ANGLE:
            radians = cozmo.robot.MIN_HEAD_ANGLE
        self._robot.move_head(radians)
    
    def move_lift(self, radians: int) -> None:
        if radians > cozmo.robot.MAX_LIFT_ANGLE:
            radians = cozmo.robot.MAX_LIFT_ANGLE
        if radians < cozmo.robot.MIN_LIFT_ANGLE:
            radians = cozmo.robot.MIN_LIFT_ANGLE
        self._robot.move_lift(radians)
    
    # Face --------------------------------------------------------------
    async def try_find_face_async(self) -> Face:
        print("Trying to find a face")
        face = None
        try:
            face = await self._robot.world.wait_for_observed_face(timeout=30)
        except asyncio.TimeoutError:
            print("Didn't find a face.")
        return face

    async def turn_toward_face_async(self, face_to_follow: Face) -> None:
        print("Turning towards face")
        turn_action = self._robot.turn_towards_face(face_to_follow)
        if not (face_to_follow and face_to_follow.is_visible):
            await self.try_find_face_async()
        await turn_action.wait_for_completed()

    # Lights --------------------------------------------------------------
    def turn_cubes_lights_off(self) -> None:
        print("Turning cubes color off")
        for cube in self.cubes:
            cube.set_lights_off()

    def cubes_change_lights(self, light: Light) -> None:
        for cube in self.cubes: 
            self.cube_change_lights(cube, light)

    def cube_change_lights(self, cube: LightCube, light: Light) -> None:
        print("Setting cube {} lights to {}".format(cube, light))
        cube.set_lights(light) 
    
    def flash_cube_lights(self, cube: LightCube, light: Light) -> None:
        print("Flashing cube {} lights with {}".format(cube, light))
        cube.set_lights(light.flash())
    
    def backpack_change_light(self, light: Light) -> None:
        print("Setting backpack lights to {}".format(light))
        self._robot.set_all_backpack_lights(light) 
    
    def flash_backpack_lights(self, light: Light) -> None:
        print("Flashing backpack lights with {}".format(light))
        self._robot.set_all_backpack_lights(light.flash())
    
    def turn_backpack_light_off(self) -> None:
        print("Turning backpack lights off")
        self._robot.set_backpack_lights_off()

    # Objects ------------------------------------------------------------
    async def place_on_object_async(self, obj: ObservableObject) -> None:
        await self._robot.place_on_object(obj, num_retries=3).wait_for_completed()
    
    async def place_object_on_ground_async(self, obj: ObservableObject) -> None:
        await self._robot.place_object_on_ground_here(obj).wait_for_completed()
    # Cube ----------------------------------------------------------------
    async def connect_to_cubes_async(self) -> None:
        self._cubes_connected = await self._robot.world.connect_to_cubes()
    
    def _disconnect_from_cubes(self) -> None:
        print("Disconecting from cubes")
        self.turn_cubes_lights_off()
        self._robot.world.disconnect_from_cubes() 
        self._cubes_connected = False

    async def try_to_find_cube_async(self) -> LightCube:
        print("Trying to find cube")
        await self._show_face_async()
        look_around = self._robot.start_behavior(BehaviorTypes.LookAroundInPlace)
        cube = None
        try:
            cube = await self._robot.world.wait_for_observed_light_cube(timeout=30)
            print("Found cube: %s" % cube)
        except asyncio.TimeoutError:
            print("Didn't find a cube")
        finally:
            # whether we find it or not, we want to stop the behavior
            look_around.stop()
        return cube

    async def try_to_find_cubes_async(self, no_cubes: int) -> List[LightCube]:
        print("Trying to find cubes")
        lookaround = self._robot.start_behavior(BehaviorTypes.LookAroundInPlace)
        cubes = await self._robot.world.wait_until_observe_num_objects(num=2, object_type=LightCube, timeout=10)
        print("Found %s cubes" % len(cubes))
        lookaround.stop()
        if len(cubes) == 0:
            await self.random_negative_anim_async()
        else:
            await self.random_positive_anim_async()
        return cubes

    def get_cube_by_id(self, cube_id) -> LightCube:
        return self._robot.world.get_light_cube(cube_id)

    async def get_in_distance_to_cube_async(self, cube: LightCube, distance: float) -> None:
        print("Moving within {} mm of cube {}".format(distance, cube))
        await self._robot.go_to_object(cube, distance_mm(distance)).wait_for_completed()
    
    async def dock_with_cube_async(self, cube: LightCube) -> None:
        print("Docking with cube {}".format(cube))
        await self._robot.dock_with_cube(cube, approach_angle=cozmo.util.degrees(90), num_retries=3).wait_for_completed()
    
    async def pick_up_cube_async(self, cube: LightCube) -> None:
        print("Picking up cube {}".format(cube))
        await self._robot.pickup_object(cube, num_retries=3).wait_for_completed()

    async def roll_cube_async(self, cube: LightCube) -> None:
        print("Rolling cube {}".format(cube))
        await self._robot.roll_cube(cube, check_for_object_on_top=True, num_retries=3).wait_for_completed()
    
    async def pop_a_wheelie_async(self, cube: LightCube) -> None:
        print("Poping a wheelie on cube {}".format(cube))
        await self._robot.pop_a_wheelie(cube, num_retries=3).wait_for_completed()
    
    # Free time ----------------------------------------------------------------
    def start_free_time(self) -> None:
        print("Starting freetime")
        print("Battery voltage: {}".format(self.battery_voltage))
        self._robot.enable_freeplay_cube_lights(enable=True)
        self.update_needs_level()
        self._robot.start_freeplay_behaviors()
        self._freetime = True

    def stop_free_time(self) -> None:
        print("Stopping freetime")
        self._robot.stop_freeplay_behaviors()
        self._freetime = False

    # Go On Off Charger ----------------------------------------------------------------
    async def get_off_charger_async(self):
        print("Getting off charger")
        if self._robot.is_on_charger:
            await self._robot.drive_off_charger_contacts(self._robot).wait_for_completed()
            await self._robot.drive_straight(distance_mm(100), speed_mmps(100)).wait_for_completed()

    async def get_on_charger_async(self):
        if self._robot.is_on_charger:
            return

        print("Getting on charger")
        await self._robot.set_head_angle(degrees(0), in_parallel=False).wait_for_completed()
        pitch_threshold = math.fabs(self._robot.pose_pitch.degrees)
        pitch_threshold += 1  # Add 1 degree to threshold
        print('Pitch threshold: ' + str(pitch_threshold))
        # Drive towards charger
        charger = await self._go_to_charger_async()
        # Adjust position in front of the charger
        await self._final_adjust_async(charger, critical=True)
        # Turn around and start going backward
        await self.turn_around_async()
        await self._robot.set_lift_height(height=0.5, max_speed=10, in_parallel=True).wait_for_completed()
        await self._robot.set_head_angle(degrees(0), in_parallel=True).wait_for_completed()
        await self._robot.backup_onto_charger(max_drive_time=5)
        if(self._robot.is_on_charger):
            print('PROCEDURE SUCCEEDED')
        else:
            await self._restart_get_on_charger_async(charger)
            return
        return

    async def _find_charger_async(self) -> Charger:
        max_tries = 5
        counter = 0
        while counter < max_tries:
            print("Looking around for charger for {} time".format(counter))
            behavior = self._robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
            try:
                seen_charger = await self._robot.world.wait_for_observed_charger(timeout=10, include_existing=True)
            except:
                seen_charger = None
            behavior.stop()
            if(seen_charger != None):
                return seen_charger
            await self.random_negative_anim_async()
            counter += 1
        
        counter = 0
        while counter < max_tries:
            print("Driving around looking for charger for {} time".format(counter))
            await self._go_to_random_position_async()
            seen_charger = await self._check_for_charger_async()
            if seen_charger:
                return seen_charger
            await self.random_negative_anim_async()
            counter += 1
    
    async def _look_for_charger_untill_found(self) -> Charger:
        print("Looking for charger")
        while True:
            charger = await self._find_charger_async()
            if charger:
                await self.random_positive_anim_async()
                return charger

    async def _go_to_random_position_async(self) -> None:
        print("Going to random position")
        x = -150
        y = -150
        if random.choice((True, False)):
            x = 150
        if random.choice((True, False)):
            y = 150
        z= random.randrange(-40, 41, 80)
        await self._robot.go_to_pose(Pose(x, y, 0, angle_z=degrees(z)), relative_to_robot=True).wait_for_completed()
    
    async def _check_for_charger_async(self) -> Charger:
        print("Checking for charger")
        self.head_lights(False)
        await asyncio.sleep(0.25)
        self.head_lights(True)
        await asyncio.sleep(0.25)
        self.head_lights(False)
        if self._robot.world.charger and self._robot.world.charger.pose.is_comparable(self._robot.pose):
            print("Found charger")
            return self._robot.world.charger
        return None

    async def _go_to_charger_async(self) -> None:
        print("Going to charger")
        charger = None
        if self._robot.world.charger:
            # make sure Cozmo was not delocalised after observing the charger
            if self._robot.world.charger.pose.is_comparable(self._robot.pose):
                print("Cozmo already knows where the charger is!")
                charger = self._robot.world.charger
            else:
                # Cozmo knows about the charger, but the pose is not based on the
                # same origin as the robot (e.g. the robot was moved since seeing
                # the charger) so try to look for the charger first
                pass
        if not charger:
            charger = await self._look_for_charger_untill_found()

        await self._robot.go_to_object(charger, distance_from_object=distance_mm(80), in_parallel=False, num_retries=5).wait_for_completed()
        return charger

    async def _final_adjust_async(self, charger: Charger, dist_charger=40, speed=40, critical=False) -> None:
        # Final adjustement to properly face the charger.
        # The position can be adjusted several times if
        # the precision is critical, i.e. when climbing
        # back onto the charger.
        while(True):
            # Calculate positions
            r_coord = [0, 0, 0]
            c_coord = [0, 0, 0]
            # Coordonates of robot and charger
            # .x .y .z, .rotation otherwise
            r_coord[0] = self._robot.pose.position.x
            r_coord[1] = self._robot.pose.position.y
            r_coord[2] = self._robot.pose.position.z
            r_zRot = self._robot.pose_angle.radians  # .degrees or .radians
            c_coord[0] = charger.pose.position.x
            c_coord[1] = charger.pose.position.y
            c_coord[2] = charger.pose.position.z
            c_zRot = charger.pose.rotation.angle_z.radians

            # Create target position
            # dist_charger in mm, distance if front of charger
            c_coord[0] -= dist_charger*math.cos(c_zRot)
            c_coord[1] -= dist_charger*math.sin(c_zRot)

            # Direction and distance to target position (in front of charger)
            distance = math.sqrt((c_coord[0]-r_coord[0])**2 + (c_coord[1]-r_coord[1])**2 + (c_coord[2]-r_coord[2])**2)
            vect = [c_coord[0]-r_coord[0], c_coord[1] - r_coord[1], c_coord[2]-r_coord[2]]
            # Angle of vector going from robot's origin to target's position
            theta_t = math.atan2(vect[1], vect[0])

            print('CHECK: Adjusting position')
            # Face the target position
            angle = self._clip_angle(theta_t-r_zRot)
            await self._robot.turn_in_place(radians(angle)).wait_for_completed()
            # Drive toward the target position
            await self._robot.drive_straight(distance_mm(distance), speed_mmps(speed)).wait_for_completed()
            # Face the charger
            angle = self._clip_angle(c_zRot-theta_t)
            await self._robot.turn_in_place(radians(angle)).wait_for_completed()

            # In case the robot does not need to climb onto the charger
            if not critical:
                break
            elif(await self._check_tol_async(charger, dist_charger)):
                print('CHECK: Robot aligned relativ to the charger.')
                break
        return

    async def _restart_get_on_charger_async(self, charger: Charger) -> None:
        print("Restarting get on charger")
        self._robot.stop_all_motors()
        await self._robot.set_lift_height(height=0.5, max_speed=10, in_parallel=True).wait_for_completed()
        self._robot.pose.invalidate()
        charger.pose.invalidate()
        print('ABORT: Driving away')
        # robot.drive_straight(distance_mm(150),speed_mmps(80),in_parallel=False).wait_for_completed()
        await self._robot.drive_wheels(80, 80, duration=2)
        await self.turn_around_async()
        await self._robot.set_lift_height(height=0, max_speed=10, in_parallel=True).wait_for_completed()
        # Restart procedure
        await self.get_on_charger_async()
        return

    async def _check_tol_async(self, charger: Charger, dist_charger=40):
        # Check if the position tolerance in front of the charger is respected
        distance_tol = 10  # mm, tolerance for placement error
        angle_tol = 5*self.PI/180  # rad, tolerance for orientation error
        try:
            charger = await self._robot.world.wait_for_observed_charger(timeout=2, include_existing=True)
        except:
            print('WARNING: Cannot see the charger to verify the position.')

        # Calculate positions
        r_coord = [0, 0, 0]
        c_coord = [0, 0, 0]
        # Coordonates of robot and charger
        # .x .y .z, .rotation otherwise
        r_coord[0] = self._robot.pose.position.x
        r_coord[1] = self._robot.pose.position.y
        r_coord[2] = self._robot.pose.position.z
        r_zRot = self._robot.pose_angle.radians  # .degrees or .radians
        c_coord[0] = charger.pose.position.x
        c_coord[1] = charger.pose.position.y
        c_coord[2] = charger.pose.position.z
        c_zRot = charger.pose.rotation.angle_z.radians

        # Create target position
        # dist_charger in mm, distance if front of charger
        c_coord[0] -= dist_charger*math.cos(c_zRot)
        c_coord[1] -= dist_charger*math.sin(c_zRot)

        # Direction and distance to target position (in front of charger)
        distance = math.sqrt((c_coord[0]-r_coord[0])**2 + (c_coord[1]-r_coord[1])**2 + (c_coord[2]-r_coord[2])**2)
        angle = math.fabs(r_zRot-c_zRot)
        print('Distance is {}, tolerance {}. Angel is {}, tolerance {}'.format(distance, distance_tol, angle, angle_tol))
        if(distance < distance_tol and angle < angle_tol):
            return 1
        else:
            return 0

    def _clip_angle(self, angle=3.1415):
        # Allow Cozmo to turn the least possible. Without it, Cozmo could
        # spin on itself several times or turn for instance -350 degrees
        # instead of 10 degrees.
        # Retreive supplementary turns (in radians)
        while(angle >= 2*self.PI):
            angle -= 2*self.PI
        while(angle <= -2*self.PI):
            angle += 2*self.PI
        # Select shortest rotation to reach the target
        if(angle > self.PI):
            angle -= 2*self.PI
        elif(angle < -self.PI):
            angle += 2*self.PI
        return angle
