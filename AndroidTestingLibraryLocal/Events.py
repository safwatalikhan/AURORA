"""
Events.py

Defines events such as tap, swipe, etc. to be sent to devices. Also defines static helper methods
having to do with events.
"""

from typing import List, Type, Union, Tuple

import re
from math import pi, atan

class Event:
    """
    Superclass to make sure every subclass has the get_cmd_str() and __str__() methods
    """

    cmd_str: str = None

    def get_cmd_str(self) -> str:
        return self.cmd_str
    
    def __str__(self) -> str:
        pass

class Tap(Event):

    x: int = None
    y: int = None

    def __init__(self, x: int, y: int) -> None:
        """
        A short tap at pixel location (x, y)
        """

        if not all(type(arg) == int for arg in (x, y)):
            raise TypeError("All arguments must be of type int")

        self.x = x
        self.y = y

        self.cmd_str = "input tap " + str(self.x) + " " + str(self.y)
    
    def __str__(self) -> str:
        return "TAP " + str(self.x) + " " + str(self.y)


class MoveEnd(Event):


    def __init__(self) -> None:
        """
        Move to the end of a selected text field
        """

        self.cmd_str = "input keyevent KEYCODE_MOVE_END"

    def __str__(self) -> str:
        return "MOVE_END"


class LongTap(Event):

    x: int = None
    y: int = None
    duration: int = None

    def __init__(self, x: int, y: int, duration: int) -> None:
        """
        A long tap at pixel location (x, y) lasting the given duration milliseconds
        """

        if not all(type(arg) == int for arg in (x, y, duration)):
            raise TypeError("All arguments must be of type int")

        self.x = x
        self.y = y
        self.duration = duration

        x = str(self.x)
        y = str(self.y)

        self.cmd_str = "input swipe " + x + " " + y + " " + x + " " + y + " " + str(self.duration)
    
    def __str__(self) -> str:
        return "LONG_TAP " + str(self.x) + " " + str(self.y) + " " + str(self.duration)

class Swipe(Event):

    x: int = None
    y: int = None
    dx: int = None
    dy: int = None
    duration: int = None

    def __init__(self, x: int, y: int, dx: int, dy: int, duration: int) -> None:
        """
        A swipe starting from pixel location (x, y) and moving (dx, dy) pixels, lasting for the
        given duration in milliseconds
        """

        if not all(type(arg) == int for arg in (x, y, dx, dy, duration)):
            raise TypeError("All arguments must be of type int")

        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.duration = duration

        self.cmd_str = ("input swipe " + str(self.x) + " " + str(self.y) + " " +
                str(self.x + self.dx) + " " + str(self.y + self.dy) + " " + str(self.duration))
    
    def __str__(self) -> str:
        return ("SWIPE " + str(self.x) + " " + str(self.y) + " " + str(self.dx) + " " +
                str(self.dy) + " " + str(self.duration))

class Text(Event):

    text: str = None

    def __init__(self, text: str) -> None:
        """
        Types the given text to the device. No whitespace allowed except for a literal space.
        """

        if type(text) != str:
            raise TypeError("text argument must be of type str")

        # only whitespace that's allowed is a space
        if re.search(r"\s(?:(?<! ))", text):
            raise ValueError('Invalid text: "' + repr(text)[1:-1] + '"')

        self.text = text

        # build the cmd_str so that it's compatible with bash shell
        self.cmd_str = "input text '"
        for char in self.text:
            if char == "'":
                self.cmd_str += "'\\'"
            self.cmd_str += char
        self.cmd_str += "'"
    
    def __str__(self) -> str:
        return 'TEXT "' + repr(self.text)[1:-1] + '"'

class EnterKey(Event):

    def __init__(self) -> None:
        self.cmd_str = "input keyevent 66"
    
    def __str__(self) -> str:
        return "ENTER_KEY"

class PowerButton(Event):

    def __init__(self) -> None:
        self.cmd_str = "input keyevent 26"
    
    def __str__(self) -> str:
        return "POWER_BUTTON"
        
class BackButton(Event):

    def __init__(self) -> None:
        self.cmd_str = "input keyevent 4"
    
    def __str__(self) -> str:
        return "BACK_BUTTON"

class BackSpace(Event):

    def __init__(self) -> None:
        
        self.cmd_str = "input keyevent 67"
    
    def __str__(self) -> str:
        return "BACK_SPACE"


class LongBackSpace(Event):
    #Pressing backspace for 250 times, as a longpress
    def __init__(self) -> None:
        self.cmd_str = "input keyevent --longpress "+" ".join([i for i in ['67']*250])
    
    def __str__(self) -> str:
        return "LONG_BACK_SPACE"


        
class DownKey(Event):

    def __init__(self) -> None:
        self.cmd_str = "input keyevent 20"
    
    def __str__(self) -> str:
        return "DOWN_KEY"

class MoveEnd(Event):

    def __init__(self) -> None:
        self.cmd_str = "input keyevent KEYCODE_MOVE_END"
    
    def __str__(self) -> str:
        return "MOVE_END"


# any instantiated object that derives from Event
EventInstance = Union[Tap, LongTap, Swipe, Text, EnterKey, PowerButton, BackButton, BackSpace, MoveEnd, LongBackSpace]
# any uninstantied class type that derives from Event
EventClass = Union[Type[Tap], Type[LongTap], Type[Swipe], Type[Text], Type[EnterKey],
        Type[PowerButton],Type[BackButton],Type[BackSpace], Type[MoveEnd], Type[LongBackSpace]]

# converts from an event type to a string
EVENT_TYPE_TO_STR = {
    Tap:         "TAP",
    LongTap:     "LONG_TAP",
    Swipe:       "SWIPE",
    Text:        "TEXT",
    EnterKey:    "ENTER_KEY",
    PowerButton: "POWER_BUTTON",
    BackButton: "BACK_BUTTON",
    BackSpace: "BACK_SPACE",
    DownKey: "DOWN_KEY",
    MoveEnd: "MOVE_END"
}

# converts from a string to an event type
EVENT_STR_TO_TYPE = {
    "TAP":          Tap,
    "LONG_TAP":     LongTap,
    "SWIPE":        Swipe,
    "TEXT":         Text,
    "ENTER_KEY":    EnterKey,
    "POWER_BUTTON": PowerButton,
    "BACK_BUTTON":  BackButton,
    "BACK_SPACE":   BackSpace,
    "DOWN_KEY": DownKey,
    "MOVE_END": MoveEnd,
    "LONG_BACK_SPACE": LongBackSpace 
}

# contains angle information corresponding to a swipe direction
SWIPE_DIRECTION_TO_ANGLE = {
    "RIGHT":      0,
    "DOWN-RIGHT": pi / 4,
    "DOWN":       pi / 2,
    "DOWN-LEFT":  pi * 3 / 4,
    "LEFT":       pi,
    "UP-LEFT":    pi * 5 / 4,
    "UP":         pi * 3 / 2,
    "UP-RIGHT":   pi * 7 / 4
}

def get_swipe_direction(dx: int, dy: int) -> str:
    """
    Determines the direction of a Swipe event given its dx and dy attributes.
    """

    if dx == 0:
        if dy > 0:
            angle = pi / 2
        else:
            angle = -pi / 2
    else:
        angle = atan(dy / dx)
        if dx < 0:
            angle += pi
    
    if angle <= -pi / 8:
        angle += 2 * pi

    index = min([round(angle / pi * 4), 7])
    return list(SWIPE_DIRECTION_TO_ANGLE.keys())[index]

def get_recorded_events(filepath: str = "events.txt") -> List[Tuple[int, EventInstance]]:
    """
    Given a filepath which points to a file generated by DeviceConnector.record_events(),
    returns a list of tuples formatted like (timestamp, event). The filepath defaults to
    "events.txt". Note that the list of tuples will be ordered according to the ordering in the
    file, not necessarily by the order of the events' timestamps.
    """
    
    regexes = {
        Tap:         r"^\[(\d+)\] TAP (\d+) (\d+)$",
        LongTap:     r"^\[(\d+)\] LONG_TAP (\d+) (\d+) (\d+)$",
        Swipe:       r"^\[(\d+)\] SWIPE (\d+) (\d+) (-?\d+) (-?\d+) (\d+)$",
        Text:        r'^\[(\d+)\] TEXT "(.+)"$',
        EnterKey:    r"^\[(\d+)\] ENTER_KEY$",
        PowerButton: r"^\[(\d+)\] POWER_BUTTON$",
        BackButton: r"^\[(\d+)\] BACK_BUTTON$",
        BackSpace: r"^\[(\d+)\] BACK_SPACE$"
    }

    event_infos = []

    with open(filepath, "r") as file:

        for line in file:

            line = line.strip()

            for event_class in regexes:

                captured_groups = re.findall(regexes[event_class], line)

                if len(captured_groups) > 0:

                    if event_class in (PowerButton, EnterKey):
                        event_infos.append((int(captured_groups[0]), event_class()))
                    
                    elif event_class == Text:
                        event_infos.append((int(captured_groups[0][0]),
                                event_class(captured_groups[0][1])))
                    
                    else:
                        event_infos.append((int(captured_groups[0][0]),
                                event_class(*(int(arg) for arg in captured_groups[0][1:]))))
    
    return event_infos
