from cozmo_mqtt_program import CozmoMqttProgram
import cozmo

if __name__ == '__main__':   
    cozmo_mqqtt_app = CozmoMqttProgram()

    try:
        cozmo.run_program(cozmo_mqqtt_app.run_with_robot_async)
    except KeyboardInterrupt:
        print("")
        print("Exit requested by user")