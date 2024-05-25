"""
GeteventParser.py

Contains classes which when used together, transform output from `adb shell getevent -lt` to Event
objects such as Tap, LongTap, etc. The parsing algorithm is online, so large amounts of data can be
processed with minimal memory overhead.

***IMPORTANT*** Documentation for protocol: 
https://www.kernel.org/doc/Documentation/input/multi-touch-protocol.txt
"""

import re
from typing import Optional, Any, Tuple, Dict, List, Union

from .Device import Device
from .Helpers import (hex_to_int, seconds_to_ms,
        points_within_threshold, scale_linear)
from .Events import (EventInstance, Tap, LongTap, Swipe, Text, EnterKey,
        PowerButton, MoveEnd, LongBackSpace)

_WORD_SIZE = 32 # word size, in bits, of the "value" field of incoming lines from getevent
_DEFAULT_MAX_COORD_VALUE = 32767 # maximum value of ABS_MT_POSITION_X/Y

_DEFAULT_MIN_LONG_TAP_DURATION = 400 # cutoff from tap to long tap (ms)
_DEFAULT_TAP_SLOP = 20.0 # pixel amount denoting the mininum distance for swipe event

# states for the IncomingEvent class
_STATE_ONGOING = "ONGOING"
_STATE_COMPLETE = "COMPLETE"

# types of events for the IncomingEvent class
_TYPE_TOUCH = "TOUCH"
_TYPE_KEY = "KEY"

# possible keys that would get turned into a Text event
_KEY_MAP = {

    "KEY_0": "0",    "KEY_A": "a",    "KEY_K": "k",    "KEY_U": "u",
    "KEY_1": "1",    "KEY_B": "b",    "KEY_L": "l",    "KEY_V": "v",
    "KEY_2": "2",    "KEY_C": "c",    "KEY_M": "m",    "KEY_W": "w",
    "KEY_3": "3",    "KEY_D": "d",    "KEY_N": "n",    "KEY_X": "x",
    "KEY_4": "4",    "KEY_E": "e",    "KEY_O": "o",    "KEY_Y": "y",
    "KEY_5": "5",    "KEY_F": "f",    "KEY_P": "p",    "KEY_Z": "z",
    "KEY_6": "6",    "KEY_G": "g",    "KEY_Q": "q",
    "KEY_7": "7",    "KEY_H": "h",    "KEY_R": "r",
    "KEY_8": "8",    "KEY_I": "i",    "KEY_S": "s",
    "KEY_9": "9",    "KEY_J": "j",    "KEY_T": "t",

    "KEY_GREEN":     "`",    "KEY_RIGHTBRACE": "]",    "KEY_COMMA": ",",
    "KEY_MINUS":     "-",    "KEY_BACKSLASH": "\\",    "KEY_DOT":   ".",
    "KEY_EQUAL":     "=",    "KEY_SEMICOLON":  ";",    "KEY_SLASH": "/",
    "KEY_LEFTBRACE": "[",    "KEY_APOSTROPHE": "'",    "KEY_SPACE": " "
}

class _IncomingEvent:
    """
    A sort of state machine that handles incoming parsed lines and stores their properties. The
    type and state attributes are updated to reflect the status of the potential event.
    """

    state: str = None
    type: str = None

    x: list = None
    y: list = None
    key: str = None
    t1: float = None
    t2: float = None

    def __init__(self) -> None:
        self.reset()
    
    def handle_line(self, parsed_line: Dict[str, Any]) -> None:
        """
        Change state, type, and attributes based on information that the parsed line contains.
        """

        # a type of EV_ABS denotes some kind of TOUCH event
        if parsed_line["type"] == "EV_ABS":

            # If incoming line is a positive tracking id, it's the beginning of a touch event; if
            # the line is a negative tracking id, then it's the end of a touch event
            if parsed_line["field"] == "ABS_MT_TRACKING_ID":
            
                if hex_to_int(parsed_line["value"], _WORD_SIZE) >= 0:
                    self.reset()
                    self.type = _TYPE_TOUCH
                    self.t1 = parsed_line["timestamp"]
                
                else:
                    self.state = _STATE_COMPLETE
                    self.t2 = parsed_line["timestamp"]

            # if the line contains x and y information, update properties accordingly
            if parsed_line["field"] == "ABS_MT_POSITION_X":
                self.x.append(hex_to_int(parsed_line["value"], _WORD_SIZE))
            elif parsed_line["field"] == "ABS_MT_POSITION_Y":
                self.y.append(hex_to_int(parsed_line["value"], _WORD_SIZE))

        # A type of EV_KEY denotes some kind of KEY event; only handle power button and keys in the
        # map
        elif (parsed_line["type"] == "EV_KEY" and 
                (parsed_line["field"] in _KEY_MAP or
                parsed_line["field"] in ("KEY_ENTER", "KEY_POWER"))):

            # If the value of the incoming line is DOWN, it's the beginning of a key event; if the
            # value is UP, then it's the end of a key event
            if parsed_line["value"] == "DOWN":
                self.reset()
                self.type = _TYPE_KEY
                self.key = parsed_line["field"]
                self.t1 = parsed_line["timestamp"]
            
            elif parsed_line["value"] == "UP":
                # this is assuming that an UP packet immediately follows a DOWN packet; i.e. these
                # KEY events are atomic and cannot be interrupted by other KEY events
                self.state = _STATE_COMPLETE
                self.t2 = parsed_line["timestamp"]

    def balance_coordinates(self, last_x: int, last_y: int) -> None:
        """
        If the x and y lists are different lengths, the last value of the shorter list will be
        duplicated so that lists are the same length. If one or both of the lists are empty, then
        the appropriate last_x and/or last_y will be appended.
        """

        # append last_x and/or last_y if needed
        if len(self.x) == 0 and last_x is not None:
            self.x.append(last_x)
        if len(self.y) == 0 and last_y is not None:
            self.y.append(last_y)
        
        # If one of the lists is still empty at this point, it means that no x and/or y coordinates
        # have been sent at all; so make both lists empty and return.
        if len(self.x) == 0 or len(self.y) == 0:

            self.x = []
            self.y = []

            return

        # do nothing if the lists are the same length
        if len(self.x) == len(self.y):
            return

        # balance the lists
        while len(self.x) < len(self.y):
            self.x.append(self.x[-1])
        while len(self.y) < len(self.x):
            self.y.append(self.y[-1])

    def compile(self, screen_width: int, min_x: int, max_x: int, screen_height: int, min_y: int,
            max_y: int, min_long_tap_duration: int, tap_slop: float) -> Tuple[int, EventInstance]:
        """
        Compiles into an Event object. Returns timestamp, event

        Preconditions:
          - balance_coordinates() must be called beforehand
          - the state must be _STATE_COMPLETE
        """

        # discard if t1 or t2 is None
        if self.t1 is None or self.t2 is None:
            return None, None
        
        start_time = seconds_to_ms(self.t1)
        duration = seconds_to_ms(self.t2) - seconds_to_ms(self.t1)
        
        if self.type == _TYPE_TOUCH:

            # if there's only one element in the x and y lists, then it's a tap or long tap
            if len(self.x) == 1:
                return start_time, self._compile_tap(duration, screen_width, min_x, max_x,
                            screen_height, min_y, max_y, min_long_tap_duration)
            
            # If there's > 1 element in the x and y lists, then it can be anything, need to compute
            # how close together the points were to determine if it was a (tap or long tap) or
            # swipe.
            elif len(self.x) > 1:

                # determine if the points were close enough together to be a tap or long tap
                if points_within_threshold(
                        [scale_linear(x, min_x, max_x, 0, screen_width) for x in self.x],
                        [scale_linear(y, min_y, max_y, 0, screen_height) for y in self.y],
                        tap_slop):
                    return start_time, self._compile_tap(duration, screen_width, min_x, max_x,
                            screen_height, min_y, max_y, min_long_tap_duration)
                else:
                    x1 = int(scale_linear(self.x[0], min_x, max_x, 0, screen_width))
                    y1 = int(scale_linear(self.y[0], min_y, max_y, 0, screen_height))
                    x2 = int(scale_linear(self.x[-1], min_x, max_x, 0, screen_width))
                    y2 = int(scale_linear(self.y[-1], min_y, max_y, 0, screen_height))
                    return start_time, Swipe(x1, y1, x2 - x1, y2 - y1, duration)
            
        elif self.type == _TYPE_KEY:

            # if the key is in KEY_MAP, then it's a Text event
            if self.key in _KEY_MAP:
                return start_time, Text(_KEY_MAP[self.key])
            
            # "KEY_ENTER" means an EnterKey event
            elif self.key == "KEY_ENTER":
                return start_time, EnterKey()

            # "KEY_POWER" means a PowerButton event
            elif self.key == "KEY_POWER":
                return start_time, PowerButton()
            
        return None, None
    
    def _compile_tap(self, duration: int, screen_width: int, min_x: int, max_x: int,
            screen_height: int, min_y: int, max_y: int,
            min_long_tap_duration: int) -> EventInstance:
        """
        Logic to return either a tap or a long tap based on the duration (ms) of the event. If the
        duration is >= min_long_tap_duration, then it's a long tap; else, it's a tap.
        """

        x = int(scale_linear(self.x[0], min_x, max_x, 0, screen_width))
        y = int(scale_linear(self.y[0], min_y, max_y, 0, screen_height))

        if duration >= min_long_tap_duration:
            return LongTap(x, y, duration)
        else:
            return Tap(x, y)

    def reset(self) -> None:
        """Resets attributes to initial state"""

        self.state = _STATE_ONGOING
        self.type = None

        self.x = []
        self.y = []
        self.key = None
        self.t1 = None
        self.t2 = None

    def __str__(self) -> str:
        return ("type: " + str(self.type) + ", state: " + str(self.state) + "\n" +
                "            x:        " + str(self.x) + "\n" +
                "            y:        " + str(self.y) + "\n" +
                "            key:      "  + str(self.key) + "\n" +
                "            (t1, t2): (" + str(self.t1) + ", " + str(self.t2) + ")")

class _EventStream:
    """
    Responsible for determining packet and subpacket boundaries, then handing parsed lines to their
    corresponding IncomingEvents. Multiple IncomingEvents can be present in one EventStream if there
    is a multi-touch gesture, where each IncomingEvent has its own "slot".

    Note: EventStreams dedicated to key presses always only have one slot in this algorithm.
    """

    __incoming_events: Dict[int, _IncomingEvent] = None # organized by slot number
    __active_slot: int = None
    __active_text: Optional[List[Union[int, Text]]] = None # any ongoing text event

    __last_x: int = None
    __last_y: int = None

    # input properties
    __min_x: int = None
    __max_x: int = None
    __screen_width: int = None
    __min_y: int = None
    __max_y: int = None
    __screen_height: int = None
    __min_long_tap_duration: float = None
    __tap_slop: int = None

    def __init__(self, input_device: Dict[str, Any], screen_width: int, screen_height: int,
            min_long_tap_duration: int, tap_slop: float) -> None:

        self.__incoming_events = {}
        self.__active_slot = 0

        self.__screen_width = screen_width
        self.__screen_height = screen_height
        self.__min_long_tap_duration = min_long_tap_duration
        self.__tap_slop = tap_slop

        # If the input_device already has the min/max properties set, then pull from there; else,
        # just use the default values.
        if all(key in input_device for key in ("x_min", "x_max", "y_min", "y_max")):
            self.__min_x = input_device["x_min"]
            self.__max_x = input_device["x_max"]
            self.__min_y = input_device["y_min"]
            self.__max_y = input_device["y_max"]
        else:
            self.__min_x = self.__min_y = 0
            self.__max_x = self.__max_y = _DEFAULT_MAX_COORD_VALUE

    def handle_line(self, parsed_line: Dict[str, Any]) -> List[Tuple[int, EventInstance]]:
        """
        Takes a prased line and hands it off to the correct IncomingEvent. If the end of a packet is
        detected, then all incoming events that are of state COMPLETE will be attempted to be
        compiled into Event objects. Returns any events that were successfully compliled.
        """

        completed_events = []

        # Determine if the line is a SYN_REPORT; if so, iterate through all incoming events and see
        # if any are complete. If any are, then compile them into an Event object.
        if parsed_line["type"] == "EV_SYN" and parsed_line["field"] == "SYN_REPORT":

            slots_to_delete = []
            
            # iterate through all incoming events
            for slot_num in self.__incoming_events:

                e = self.__incoming_events[slot_num]

                # balance the incoming event's coordinate lists if it's a touch event
                if e.type == _TYPE_TOUCH:
                    e.balance_coordinates(self.__last_x, self.__last_y)
                
                # If the incoming event is complete, compile it, delete it, and see if the
                # compilation results in an actual event.
                if e.state == _STATE_COMPLETE:

                    start_time, event = e.compile(self.__screen_width, self.__min_x, self.__max_x,
                            self.__screen_height, self.__min_y, self.__max_y,
                            self.__min_long_tap_duration, self.__tap_slop)
                    slots_to_delete.append(slot_num)

                    if event is not None:

                        # if it's a text event, then update the active text
                        if type(event) == Text:
                            if self.__active_text is None:
                                self.__active_text = [start_time, event]
                            else:
                                self.__active_text[1] = (Text(self.__active_text[1].text +
                                        event.text))

                        # if it's anything else, then flush any active text and append both
                        else:
                            finished_text = self.flush()
                            if finished_text is not None:
                                completed_events.append(finished_text)
                            completed_events.append((start_time, event))
            
            # delete slots that were compiled
            for slot_num in slots_to_delete:
                del self.__incoming_events[slot_num]

        # Determine if the line is a SLOT; if so, change the active slot number so that the
        # following incoming lines get directed to the IncomingEvent at that slot.
        elif parsed_line["type"] == "EV_ABS" and parsed_line["field"] == "ABS_MT_SLOT":
            self.__active_slot = hex_to_int(parsed_line["value"], _WORD_SIZE)

        # If the incoming line is not a packet delimiter, simply pass it to the IncomingEvent at
        # the currently active slot
        else:

            # If an event comes in that was at the same x and/or y location as the last one, then
            # that x and/or y coordinate will not get sent in the event's initial packet. Therefore,
            # the most recently received x and y coordinates need to be stored.
            if parsed_line["type"] == "EV_ABS":
                if parsed_line["field"] == "ABS_MT_POSITION_X":
                    self.__last_x = hex_to_int(parsed_line["value"], _WORD_SIZE)
                elif parsed_line["field"] == "ABS_MT_POSITION_Y":
                    self.__last_y = hex_to_int(parsed_line["value"], _WORD_SIZE)
            
            # if there is no incoming event at the current slot, then create one
            if self.__active_slot not in self.__incoming_events:
                self.__incoming_events[self.__active_slot] = _IncomingEvent()
            
            # pass parsed line to appropriate IncomingEvent
            self.__incoming_events[self.__active_slot].handle_line(parsed_line)
        
        return completed_events
    
    def flush(self) -> Optional[Tuple[int, Text]]:
        """
        Returns any active text event that may be happening. If there are no ongoing text events,
        then return None.
        """

        if self.__active_text is not None:
            temp = self.__active_text
            self.__active_text = None
            return tuple(temp)
        
        return None

    def __str__(self) -> str:

        s = "{"

        if len(self.__incoming_events) == 0:
            s += "}"
            return s
        
        s += "\n        active text: "
        if self.__active_text is None:
            s += "None"
        else:
            s += '"' + self.__active_text[1].text + '"'

        for slot_num in self.__incoming_events:
            s += "\n        slot " + str(slot_num) + " -> " + str(self.__incoming_events[slot_num])

        s += "\n    }"

        return s

class GeteventParser:
    """
    The GeteventParser is responsible for accepting raw strings from the getevent command, splitting
    each line into separate fields, and giving the parsed lines to their corresponding EventStream.
    """

    __device: Device = None

    __event_streams: Dict[str, _EventStream] = None
    __last_stream: str = None
    __debug: bool = None
    __regex: re.Pattern = None

    def __init__(self, device: Device, debug: Optional[bool] = False) -> None:
        """
        Setting debug to True will print a mighty amount of text logging the parser's progress.
        """

        self.__device = device

        self.__event_streams = {}
        self.__last_stream = ""
        self.__debug = debug

        # this is the regex that parses the raw line into separate sections
        regex_str = (r"^\[ +(?P<timestamp>\d+(?:\.\d+)?) *\] +(?P<path>/dev/input/event\d+): +" +
                r"(?P<type>[^ ]+) +(?P<field>[^ ]+) +(?P<value>[^ ]+) *$")
        self.__regex = re.compile(regex_str)

    def parse(self, line: str) -> List[Tuple[str, EventInstance]]:
        """
        Takes one raw getevent line as input, and outputs any events that were determined.
        Typically, this will return an empty list as one event is comprised of multiple lines.
        Events are returned as tuples with the format (timestamp, event).
        """

        if self.__debug:
            print("before regex:", line)
        
        # match the line against the regex
        match = self.__regex.search(line)

        # if no match, discard
        if match is None:
            return []
        
        # get the input device path
        path = match.group("path")
        
        # create dictionary to more easily handle the parsed line
        parsed_line = {
            "timestamp": float(match.group("timestamp")),
            "type": match.group("type"),
            "field": match.group("field"),
            "value": match.group("value")
        }
        
        # print the parsed line
        if self.__debug:
            print("incoming to {}: {}".format(path, parsed_line))
        
        # Here, we need to divert the parsed line to the correct event stream.
        # If no event stream exists for the stream path of the incoming line, then create one.
        if path not in self.__event_streams:

            input_device = {}
            min_long_tap_duration = _DEFAULT_MIN_LONG_TAP_DURATION
            tap_slop = _DEFAULT_TAP_SLOP

            # attempt to get information about input device and input properties
            if path in self.__device.input_devices:
                input_device = self.__device.input_devices[path]
            if "min_long_tap_duration" in self.__device.input_properties:
                min_long_tap_duration = self.__device.input_properties["min_long_tap_duration"]
            if "tap_slop" in self.__device.input_properties:
                tap_slop = self.__device.input_properties["tap_slop"]

            # create the EventStream
            self.__event_streams[path] = _EventStream(input_device, self.__device.screen_width,
                    self.__device.screen_height, min_long_tap_duration, tap_slop)
        
        # Flush the streams of any active text if the line is going to a new stream. Then, pass the
        # parsed line to the appropriate event stream and receive any completed events.
        completed_events = []
        if path != self.__last_stream:
            completed_events.extend(self.flush())
        self.__last_stream = path
        completed_events.extend(self.__event_streams[path].handle_line(parsed_line))

        if self.__debug:

            print("event streams:")

            for stream in self.__event_streams:
                print("    " + str(stream) + ": " + str(self.__event_streams[stream]))

        return completed_events
    
    def flush(self) -> List[Tuple[int, Text]]:
        """
        Return any ongoing Text events in the event streams
        """

        completed_events = []

        for path in self.__event_streams:
            event_info = self.__event_streams[path].flush()
            if event_info is not None:
                completed_events.append(event_info)
        
        return completed_events
