## Freetime Cozmo
*************
Converts the Anki/DDL Cozmo robot to more of a Vector robot. 
He will play, he will chat, he will self charge.

## What it does:
*************
Using the Anki Cozmo SDK this async app runs cozmo mostly in freetime which allows him to be a very happy self sufficient robot.
If the battery needs charging, the robot will try to find his own way back to charger, and will charge untill full, and then go out again to have fun.
He will also chat a bit more and react to different situations.

You can also hook him up to a MQTT broker for control (not finished) and notifications.

I doubt I will continue with this project, as my Cozmo dissconects a lot and it beats the purpose, plus now I got Vector and will work on that one :)
But feel free to use, extend, what not.

## Acknowledgements, license and liability:
****************************************
Anki SDK:
* https://anki.com/en-gb/cozmo/SDK.html
* https://github.com/anki/cozmo-python-sdk

Special thanks to:
* Lucas Waelti https://github.com/LucasWaelti/Cozmo/ 
* cozmobotics https://github.com/cozmobotics/CozmoCommander/
* acidzebra https://gist.github.com/acidzebra/c02ff8c8ccb0e3a057ae0b48a5082a68

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License in the file LICENSE.txt or at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This applies especially but not limited to damages of the robot 
and damages or injuries caused by the robot. 

## How to run the app
*************************************
* Install Cozmo SDK -> http://cozmosdk.anki.com/docs/initial.html
* Install Pillow -> pip3 install --user Pillow
* Install qmqtt -> pip3 install --user gmqtt
* Run robot in SDK Mode
* Run py app.py
* Enjoy