import random
from typing import List
from cozmo.faces import Face, FACIAL_EXPRESSION_HAPPY, FACIAL_EXPRESSION_SURPRISED, FACIAL_EXPRESSION_ANGRY, FACIAL_EXPRESSION_SAD
from cozmo.objects import ObservableObject, Charger, LightCube

HELLO = [
    "Hello {name}",
    "Hi {name}, how are you?",
    "Hello {name}, it's so {good} to see you!",
    "Hello {name}, it's {good} to see you",
    "Hey {name}, what's up?",
    "{name}, there you are. It's {good} to see you!",
    "Hey {name}, what are you up to today?",
    "{name}, I'm really happy to see you",
    "Hey {name}, how are you doing?",
    "What are you up to today {name}?",
    "There you are {name}. I missed you",
    "{name}, I enjoy spending time with you",
    "I sure like seeing your face {name}",
    "I see you {name}. Are you having a nice day?",
    "I love you {name}. You are my favorite human"
]
HAPPY = [
    "You look {happy}, I will be {happy} too!",
    "{happy} {name}, how cute!",
    "Your face looks {happy}",
    "Do I see a {happy} smile on {name} face?"
]
SURPRISED = [
    "You look {surprised}, are you {happy} to see me too?",
    "{surprised}, why?",
    "Are you {surprised}?"
]
ANGRY = [
    "You look {angry}, I'd bether run away!",
    "{angry} {name}, I'd better hide!",
    "You seem {angry}, did I do something?"
]
SAD = [
    "You look {sad}, why is that? You want to talk about it?",
    "{sad} {name}, I might cry as well",
    "You seem {sad}, is there anything I can do to help you?"
]
NATURAL = [
    "You don't seem neither happy, nor sad, nor angry, nor surprised",
    "What's this facial expression?",
    "Your face tells me nothing"
]
NOT_RECOGNIZED = [
    "Hello, I don't think I recognize you.",
    "Do we know eachother?",
    "Your face doesn't seem familiar",
    "And who are You?",
    "Don't think we were introduced, my name is Cozmo, and you are?"
]
PICKED_UP = [
    "Don't drop me",
    "Don't let me fall",
    "Please be careful {name}",
    "Don't let go please",
    "Weeeee",
    "I'm in the air",
    "You are strong {name}",
    "It's nice to be held",
    "I like to be held",
    "Your hands are warm",
    "Put me down please {name}",
    "I am flying",
    "{name}. You are my human",
    "This is like a cuddle",
    "I love you"
]
CLIFF_DETECTED = [
    "Wow",
    "That was {scary}",
    "Well, that was a little {scary}",
    "That was super scary {name}",
    "I thought I was going to fall",
    "I'm sure glad that I didn't fall {name}",
    "Wow {name}, that was very scary",
    "Holy smokes, I was very scared",
    "I thought I was going to fall",
    "Holy smokes, that was kind of intense"
]
FACE_APPEARED = [
    "I see a face!",
    "A face appeared!",
    "I wonder who's face it that?"
]
CUBE_APPEARED = [
    "I see my cube",
    "Oh, there's my cube",
    "That's my cube in front of me",
    "Hey, I see my cube",
    "There's my cube",
    "My cube is over there",
    "I love looking at my cube",
    "My cube makes me happy",
    "Look at my cool cube. Do you see it?",
    "Hey, look! That's my cube right there! I love it so much"
]
CHARGER_APPEARED = [
    "This is my charger",
    "I like my charger {name}",
    "Yummy! I love my charger {name}!",
    "I found my charger",
    "ooooo power source!"
]
SOMETHING_APPEARED = [
    "What is this?",
    "Hey, what is this thing?",
    "What is this thing in my path?",
    "I wonder what this thing is.",
    "This thing in my way is very strange.",
    "This thing is {weird}.",
    "Could you move this thing?",
    "I see something, it's blocking my way.",
    "There is something blocking my path.",
    "What is this {weird} thing?",
    "Hey, what is this thing blocking me?",
    "The thing in front of me is {weird}.",
    "I can see that there is something in front of me.",
    "My proximity sensor detected an obstacle.",
    "This thing I see in front of me is very {weird}."
]


class MessageManager():

    def get_hello_message(self, face: Face = None) -> str:
        return self._message_randomizer(HELLO, face)

    def get_non_recognized_message(self, face: Face = None) -> str:
        return self._message_randomizer(NOT_RECOGNIZED, face)

    def get_picked_up_message(self, face: Face = None) -> str:
        return self._message_randomizer(PICKED_UP, face)

    def get_cliff_detected_message(self, face: Face = None) -> str:
        return self._message_randomizer(CLIFF_DETECTED, face)

    def get_object_appeared_message(self, visible_object: ObservableObject, face: Face = None) -> str:
        if isinstance(visible_object, Face):
            messages = FACE_APPEARED
        elif isinstance(visible_object, LightCube):
            messages = CUBE_APPEARED
        elif isinstance(visible_object, Charger):
            messages = CHARGER_APPEARED
        else:
            messages = SOMETHING_APPEARED
        return self._message_randomizer(messages, face)

    def get_fece_expression_message(self, expression: str, face: Face = None) -> str:
        if expression == FACIAL_EXPRESSION_HAPPY:
            messages = HAPPY
        elif expression == FACIAL_EXPRESSION_SURPRISED:
            messages = SURPRISED
        elif expression == FACIAL_EXPRESSION_ANGRY:
            messages = ANGRY
        elif expression == FACIAL_EXPRESSION_SAD:
            messages = SAD
        else:
            messages = NATURAL
        return self._message_randomizer(messages, face)

    def _message_randomizer(self, messages: List[str], face: Face = None) -> str:
        message = random.choice(messages)
        if face and face.name:
            message = message.replace("{name}", face.name)
        else:
            message = message.replace("{name}", "")

        surprised = ["astonished", "bewildered", "dazed", "frightened", "shocked",
                     "startled", "stunned", "alarmed", "astounded", "confounded", "stupefied"]
        angry = ["annoyed", "bitter", "enraged", "exasperated", "furious", "heated",
                 "impassioned", "indignant", "irate", "irritable", "irritated", "offended", "outraged"]
        sad = ["bitter", "dismal", "heartbroken", "melancholy", "mournful",
               "pessimistic", "somber", "sorrowful", "sorry", "wistful", "bereaved", "blue"]
        happy = ["cheerful", "contented", "delighted", "ecstatic", "elated",
                 "glad", "joyful", "joyous", "jubilant", "merry", "overjoyed", "jolly"]
        good = ["good", "great", "very good", "wonderful", "lovely", "charming", "nice",
                "enjoyable", "incredible", "remarkable", "fabulous", "pleasant", "fantastic"]
        weird = ["weird", "odd", "strange", "very weird", "crazy", "bizarre",
                 "remarkable", "outlandish", "different", "random", "curious", "freaky"]
        scary = ["scary", "frightening", "very scary", "terrifying",
                 "alarming", "daunting", "frightful", "grim", "harrowing", "shocking"]
        interesting = ["interesting", "weird", "strange", "curious", "fascinating",
                       "intriguing", "provocative", "thought-provoking", "unusual", "captivating", "amazing"]
        message = message.format(
            good=random.choice(good),
            scary=random.choice(scary),
            weird=random.choice(weird),
            interesting=random.choice(interesting),
            happy=random.choice(happy),
            sad=random.choice(sad),
            angry=random.choice(angry),
            surprised=random.choice(surprised)
        )
        print("Randomized message: {}".format(message))
        return message
