"""
RandomStrategy.py

An implementation of the Random strategy.
"""
import os

from .Helpers import random_within_bounds
from typing import Optional, Tuple

from random import random, randint, uniform, choices, choice
from math import pi, sin, cos
from string import ascii_letters

from .TestingStrategy import TestingStrategy
from .DeviceConnector import DeviceConnector
from .Device import Device
from .GuiComponent import GuiComponent
from .Events import Tap, LongTap, Swipe, Text, EnterKey, EventInstance, SWIPE_DIRECTION_TO_ANGLE

_DEFAULT_LONG_TAP_DURATION = 750 # ms
_DEFAULT_SWIPE_DURATION = 400 # ms

def random_swipe(bounds: Tuple[Tuple[int, int], Tuple[int, int]], direction: Optional[str],
        screen_width: int, screen_height: int) -> Swipe:
    """
    Generates a Swipe event from the given bounds, direction, and screen parameters. The origin
    location of the Swipe will be inside the bounds and opposite its direction; e.g. if the
    direction is "RIGHT", then the Swipe will originate on the left side of the bounds.
    """

    # choose a random direction if none given
    if direction is None or direction == "":
        direction = choice(list(SWIPE_DIRECTION_TO_ANGLE.keys()))
    
    # determine origin location
    min_x, max_x = bounds[0][0], bounds[1][0]
    min_y, max_y = bounds[0][1], bounds[1][1]
    for d in direction.split("-"):
        if d == "RIGHT":
            min_x = bounds[0][0]
            max_x = bounds[0][0] + (bounds[1][0] - bounds[0][0]) // 2
        elif d == "LEFT":
            min_x = bounds[0][0] + (bounds[1][0] - bounds[0][0]) // 2
            max_x = bounds[1][0]
        elif d == "DOWN":
            min_y = bounds[0][1]
            max_y = bounds[0][1] + (bounds[1][1] - bounds[0][1]) // 2
        elif d == "UP":
            min_y = bounds[0][1] + (bounds[1][1] - bounds[0][1]) // 2
            max_y = bounds[1][1]
    x = randint(min_x, max_x)
    y = randint(min_y, max_y)

    # determine vector direction
    max_length = max(screen_width, screen_height) * 0.75
    min_length = max_length / 2
    length = uniform(min_length, max_length)
    angle = SWIPE_DIRECTION_TO_ANGLE[direction] + uniform(-pi / 8, pi / 8)
    dx, dy = int(length * cos(angle)), int(length * sin(angle))

    # create event
    return Swipe(x, y, dx, dy, _DEFAULT_SWIPE_DURATION)

def generate_random_event(dc: DeviceConnector, gui: GuiComponent, screen_width: int,
        screen_height: int,
        keyboard_bounds: Optional[Tuple[Tuple[int, int], Tuple[int, int]]]) -> EventInstance:
    """
    Generates a pseudo-random event based on the state of the GUI and the keyboard according to the
    following probability tree:

    Keyboard is showing:
        - 3/9: Text
        - 3/9: EnterKey
        - 1/9: Tap
            - 3/4: On GUI component
            - 1/4: Anywhere
        - 1/9: LongTap
            - 3/4: On GUI component
            - 1/4: Anywhere
        - 1/9: Swipe
            - 3/4: On GUI component
            - 1/4: Anywhere
    Keyboard is not showing:
        - 5/8: Tap
            - 3/4: On GUI component
            - 1/4: Anywhere
        - 2/8: Swipe
            - 3/4: On GUI component
            - 1/4: Anywhere
        - 1/8: LongTap
            - 3/4: On GUI component
            - 1/4: Anywhere
    """

    # determine the type of event depending on if the keyboard is showing
    events = (Tap, LongTap, Swipe, Text, EnterKey)
    weights = (5, 1, 2, 0, 0) if keyboard_bounds is None else (1, 1, 1, 3, 3)
    event_type = choices(events, weights, k = 1)[0]

    if event_type in (Tap, LongTap, Swipe):

        # there is a 75% chance to try and interact with a GUI component
        on_gui = random() < 0.75

        # try and find a GUI component with which an event of event_type can interact
        component = None
        if on_gui:
            components = dc.search_gui_components(gui, event_type = event_type)
            # choose a random component if there were any components found
            if len(components) > 0:
                component = choice(components)
        
        # Determine the bounds of the starting point of the event. If there is no GUI component,
        # then the bounds are the bounds of the root GUI component. If there was no root GUI
        # component, then the bounds are the top 80% of the screen (to avoid the home button). If
        # there was a GUI component, then the bounds are the bounds of the component.
        if component is None:
            if gui is None:
                bounds = ((0, 0), (screen_width, int(0.8 * screen_height)))
            else:
                bounds = gui.bounds
        else:
            bounds = component.bounds
        
        # create the event
        if event_type == Tap:
            return Tap(*random_within_bounds(bounds))
        elif event_type == LongTap:
            return LongTap(*random_within_bounds(bounds), _DEFAULT_LONG_TAP_DURATION)
        else:
            return random_swipe(bounds, None, screen_width, screen_height)
    
    elif event_type == EnterKey:
        return EnterKey()
    
    else:
        # generate some random text
        return Text("".join(choice(ascii_letters) for _ in range(randint(1, 5))))

class RandomStrategy(TestingStrategy):
    """
    The Random Strategy generates random events based on the current GUI.
    """

    def __init__(self, dc: DeviceConnector, device: Device, package_name: str) -> None:
        """
        Initializes the RandomStrategy with the given DeviceConnector, Device, and package name.
        Raises an error if the given package isn't installed on the device.
        """

        super().__init__(dc, device, package_name)

        # Raise error if the packe isn't installed on the device
        if not self.dc.app_is_installed(self.device, self.package_name):
            raise FileNotFoundError('Could not find package "{}" on device "{}"'.format(
                    self.package_name, self.device.serial))
  
    def execute(self, num_events: int, automatic_app_restart: bool = True, direct=False) -> bool:
        """
        Executes the Random Strategy and returns the testing result (True if the test was
        successful, False otherwise). Also stores the events that were executed in a file located at
        <AndroidTestingLibrary_package_loaction>/storage/random_strategy_events.txt.

        num_events: The number of random events to generate and execute. If the given value is <= 1,
        then nothing happens.

        automatic_app_restart: If set to True, then the app will automatically be killed and
        launched before the event execution begins. Set this to False if there is some barrier which
        must be overcome manually in order to get to the starting screen of the app, e.g. a login
        page, or if the app restarting is otherwise inconvenient. Defaults to True.
        """

        if automatic_app_restart:
            self.dc.kill_app(self.device, self.package_name)
            self.dc.launch_app(self.device, self.package_name)
            if not direct:
                input("Press Enter when ready to begin testing.")
        else:
            if not direct:
                input("Navigate to the starting screen of the app, then press Enter.")

        file_path = self.__get_path("random_strategy_events.txt")
        with open(file_path, "a") as f:

            for i in range(0, num_events):

                if(not self.dc.app_is_running(self.device, self.package_name)):
                    print("TEST FAIL: App crashed")
                    return False

                rootGui = self.dc.get_gui(self.device)
                keyboard_bounds = self.dc.get_keyboard_bounds(self.device)
                event = generate_random_event(self.dc, rootGui, self.device.screen_width, self.device.screen_height, keyboard_bounds)
                print("[{}/{}] Sending event: {}".format(i + 1, num_events, event))
                f.write(str(event) + "\n")    
                self.dc.send_event(self.device, event)

        print("TEST SUCCESS")
        return True


    def __get_path(self, file_name: str) -> str:
        dir_path = os.path.dirname(os.path.abspath(__file__))
        storage_path = os.sep.join([dir_path, "storage"])
        
        if(not os.path.isdir(storage_path)): # Checks to see if the storage folder has been created. 
            os.mkdir(storage_path)
        
        path = os.sep.join([storage_path, file_name])
        return path
