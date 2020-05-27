from enum import Enum

class CozmoStates(Enum):
    ConnectionLost = "Connection lost"
    Disconnected = "Disconnected"
    Connected = "Connected"
    Freetime = "Freetime"
    GoingToCharge = "Going to charge"
    Charging = "Charging"
    Sleeping = "Sleeping"
    PickedUp = "Picked up"
    OnCliff = "On cliff"
    SawFace = "Saw face"
    Anouncing = "Anouncing"