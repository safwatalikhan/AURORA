"""
MonkeyLabStrategy.py

An implementation of the MonkeyLab strategy.
"""

from typing import Optional, List, Tuple, Set

from math import pi, atan, sin, cos
from time import time, sleep
from random import choice, choices, sample, randint, uniform
from string import ascii_letters
from copy import deepcopy

from nltk.util import everygrams
from nltk.lm import KneserNeyInterpolated

from .GuiComponent import GuiComponent
from .Database import Database
from .TestingStrategy import TestingStrategy
from .Device import Device
from .DeviceConnector import DeviceConnector
from .Events import (Tap, LongTap, Swipe, Text, EnterKey, PowerButton, get_recorded_events,
        EventInstance, EventClass, EVENT_TYPE_TO_STR, EVENT_STR_TO_TYPE, get_swipe_direction)
from .Helpers import within_bounds, random_within_bounds
from .RandomStrategy import random_swipe, generate_random_event

_DEFAULT_LONG_TAP_DURATION = 750 # ms
_DEFAULT_SWIPE_DURATION = 400 # ms

class EventTuple:
    """
    Contains information representing an event tuple, which is the union of an event and a GUI
    component. There is information about the activity, the event action (and direction if Swipe),
    the component id, and the component class.

    Changes from MonkeyLab paper:

    Additions:

    - direction -- Reason: For Swipe events, we need to know the direction of the Swipe

    Removals:

    - window -- Reason: The only reason window was part of the event tuple in the first place was so
    that we could identify which events occurred in the main window and which occurred on the
    keyboard. Now, this distinction is made with the action field; Text and EnterKey events always
    happen on the keyboard, and all other events will be made to always not happen on the keyboard.
    """
    
    activity: str = None # never  empty
    action: EventClass = None # always one of {Tap, LongTap, Swipe, Text, EnterKey, PowerButton}
    direction: str = None # direction of Swipe event
    component_id: str = None
    component_class: str = None

    def __init__(self, activity: str, action: EventClass) -> None:
        self.action = action
        self.activity = activity
        self.direction = ""
        self.component_id = ""
        self.component_class = ""

    def print_pretty(self, padding = "") -> str:
        s = padding + EVENT_TYPE_TO_STR[self.action] + " during " + self.activity + "\n"
        for attr in ("direction", "component_id", "component_class"):
            value = getattr(self, attr, "")
            if value != "":
                s += padding + "    " + attr + ": " + value + "\n"
        print(s[:-1])

    def __str__(self) -> str:
        s = self.activity + "\\" + EVENT_TYPE_TO_STR[self.action] + "\\"
        for attr in ("direction", "component_id", "component_class"):
            value = getattr(self, attr, "")
            if value != "":
                s += value
            s += "\\"
        return s[:-1]
    
    def create_from_string(string: str) -> Optional["EventTuple"]:
        """
        Static method which constructs an EventTuple object from its string representation. If the
        string representation is invalid, then return None.
        """

        fields = string.split("\\")

        if len(fields) != 5 or fields[1] not in EVENT_STR_TO_TYPE:
            return None

        event_tuple = EventTuple(fields[0], EVENT_STR_TO_TYPE[fields[1]])
        event_tuple.direction = fields[2]
        event_tuple.component_id = fields[3]
        event_tuple.component_class = fields[4]

        return event_tuple

class MonkeyLabLanguageModel:
    """
    A n-gram language model contiaining stringified event tuples (tokens) in its vocabulary. The
    model can be queried to generate tokens which can then be converted to events for execution on
    a device.
    """

    # whether or not to print debug information
    __debug: bool = None

    # The n-gram order of the model
    __ORDER: int = 3

    # The universe of all possible tokens as a list of unique tokens; this is slightly different
    # from the model vocabulary, as the vocabulary contains some labels in addition to just tokens.
    __universe: List[str] = None

    # the actual language model
    __model: KneserNeyInterpolated = None

    # context to use for the next prediction; most recent tokens are indexed higher in the list
    __context: List[str] = None
    __MAX_HISTORY_LENGTH: int = __ORDER - 1

    def __init__(self, token_sequences: List[List[str]], debug: bool = False) -> None:
        """
        token_sequences: A list of sequences of tokens to be used as training data for the model;
        these sequences represent "normal" user interaction with the app.

        Raises an error if no tokens were provided.
        """

        self.__debug = debug
        self.__universe = []
        self.__context = []
        
        token_sequences = deepcopy(token_sequences)

        if self.__debug:
            print("    Training sequences:")
            for i in range(len(token_sequences)):
                print("        {}:".format(i + 1))
                for token in token_sequences[i]:
                    print("            " + token)

        # determine universe, ngrams, and vocabulary; tokens in the vocabulary may repeat
        ngrams = []
        vocabulary = []
        for sequence in token_sequences:
            self.__universe.extend(sequence)
            sequence.insert(0, "<s>")
            ngrams.append(list(everygrams(sequence, max_len = self.__ORDER)))
            vocabulary.extend(sequence)

        # convert universe to have only unique tokens and make sure it's not empty
        self.__universe = list(set(self.__universe))
        if len(self.__universe) == 0:
            raise ValueError("Cannot create model with zero tokens")

        # create the actual model and train it with the ngrams
        self.__model = KneserNeyInterpolated(self.__ORDER, discount = 0.15)
        self.__model.fit(ngrams, vocabulary)

        # add the start token to the model context
        self.add_to_context("<s>")

        if self.__debug:
            print("    Vocabulary:")
            for token in list(self.__model.vocab):
                print("        " + token)
            print("    Universe:")
            for token in self.__universe:
                print("        " + token)
            print()
    
    def generate_token(self, mix_coef: float = 0.0, exclude: Set[str] = set()) -> str:
        """
        Generates a token according to the model's probability distribution.

        mix_coef: Mixture coefficient -- a value between 0.0 and 1.0 which linearly interpolates
        between the "up" and "down" flavors. a value of 0.0 (default) means the "up" flavor, i.e.
        the natural distribution of the data. A value of 1.0 means the "down" flavor, i.e. the
        unnatural distribution of the data.

        exclude: Tokens in this set are ignored by the model and cannot be returned. If the size of
        the set is large enough such that this method is unable to return any token, then the set is
        truncated.

        TODO: optimize using cached prob_dist and context
        TODO: optimize by returning random token if context[-1] not in vocab
        """

        # Make sure the size of the exclude set is smaller than the universe
        if len(exclude) >= len(self.__universe):
            exclude = set(list(exclude)[:len(self.__universe) - 1])

        # Iterate randomly through the universe and assign probability values; have to iterate
        # randomly so that when sorting, tokens with the same probability will be subsorted
        # randomly -- important when calculating final probabilities. Ignore tokens that are in the
        # exclude set.
        prob_dist: List[Tuple[str, float]] = []
        for token in sample(self.__universe, len(self.__universe)):
            if token not in exclude:
                prob = self.__model.score(token, self.__context)
                prob_dist.append((token, prob))
        
        # sort the distribution according to probabilities
        prob_dist.sort(key = lambda x: x[1])

        # Linearly interpolate the probabilities of tokens with the tokens' mirror probabilities
        # according to the mix_coef.
        final_probs = [prob[1] for prob in prob_dist]
        sum_probs = 0
        for i in range(len(prob_dist)):
            if mix_coef > 0.0:
                other = prob_dist[len(prob_dist) - i - 1][1] # mirror (unnatural) probability
                final_probs[i] += (other - final_probs[i]) * mix_coef
            sum_probs += final_probs[i]
        
        # choose a token with a weighted choice
        token = choices([prob[0] for prob in prob_dist], final_probs, k = 1)[0]

        if self.__debug:
            print("    Model info:")
            s = "        context: " + ("None" if len(self.__context) == 0 else "")
            for elem in self.__context:
                s += "\n            " + elem
            print(s)
            s = "        excluding: " + ("None" if len(exclude) == 0 else "")
            for elem in list(exclude):
                s += "\n            " + elem
            print(s)
            print("        Mixture coefficient: {:.2f}".format(mix_coef))
            print("        Probabilities:\n            pre      post\n            -------  -------")
            i = 0
            while i < len(prob_dist):
                print("            {:.5f}  {:.5f}  {}".format(prob_dist[i][1], final_probs[i],
                        prob_dist[i][0]))
                if i == 4 and len(prob_dist) > 10:
                    print("            ...")
                    i = len(prob_dist) - 6
                i += 1
            print("            sum: {:.5f}".format(sum_probs))

        return token
    
    def add_to_context(self, token: str) -> None:
        """
        Adds the given token to the execution history.
        """

        self.__context.append(token)

        if len(self.__context) > self.__MAX_HISTORY_LENGTH:
            del self.__context[0]

class MonkeyLabStrategy(TestingStrategy):
    """
    An implementation of the MonkeyLab strategy.
    """

    # whether or not to show debug output
    __debug: bool = None

    # language model to be created after the mine phase
    __language_model: MonkeyLabLanguageModel = None

    # cached gui and activity to be used across multiple methods
    __cached_gui: Optional[GuiComponent] = None
    __cached_activity: Optional[str] = None

    # maximum number of tokens that can be passed to the language model as training data
    __MAX_TOKENS: int = 1000
    
    def __init__(self, dc: DeviceConnector, device: Device, package_name: str,
            debug: bool = False) -> None:
        """
        Creates the MonkeyLabStrategy with the given DeviceConnector, Device, and package_name.
        Raises an error if the specified package is not installed on the device.
        """

        # call __init__() of the parent TestingStrategy class
        super().__init__(dc, device, package_name)

        # make sure the package is actually installed on the device -- raise an error if it isn't
        if not self.dc.app_is_installed(self.device, self.package_name):
            raise FileNotFoundError('Could not find package "{}" on device "{}"'.format(
                    self.package_name, self.device.serial))

        self.__debug = debug
    
    def _populate_cache(self) -> None:
        """
        Determines the current gui and activity of the device and stores them in cache.
        """
        self.__cached_gui = self.dc.get_gui(self.device)
        self.__cached_activity = self.dc.get_current_activity(self.device)
    
    def _record(self, recording_file: str, recording_timeout: Optional[float],
            recording_event_limit: Optional[int]) -> None:
        """
        Record events from the device.
        """
        self.dc.record_events(self.device, save_path = recording_file, timeout = recording_timeout,
                event_limit = recording_event_limit)

    def _determine_event_tuple(self, event: EventInstance, use_cache: bool) -> Optional[EventTuple]:
        """
        Given an EventInstance, determine the event tuple. If the event tuple could not be
        dertermined, then return None. Loads gui and activity info from cache if use_cache is True.

        Tap, LongTap, and Swipe events always have an associated GUI component, and this component
        always has a non-empty component_class or non-empty resource_id attribute. However, if the
        event happened on the device's software keyboard, then the event is converted to a Text
        event.

        Text and EnterKey events do not have any associated GUI components.

        PowerButton events cannot be formed into event tuples.
        """

        # load activity from cache or determine it now depending on value of use_cache
        activity = (self.__cached_activity if use_cache else
                self.dc.get_current_activity(self.device))

        # immediately return if activity is None
        if activity is None:
            return None

        # determine event type
        event_type = type(event)

        # immediately return if PowerButton event
        if event_type == PowerButton:
            return None

        # convert touch events to Text if they occurred on the software keyboard
        if event_type in (Tap, LongTap, Swipe):
            bounds = self.dc.get_keyboard_bounds(self.device)
            if within_bounds(bounds, event.x, event.y):
                event_type = Text
        
        # create the event tuple
        event_tuple = EventTuple(activity, event_type)

        # If the event was a touch event, then need to try and find a corresponding GUI component.
        if event_type in (Tap, LongTap, Swipe):

            # load gui from cache or determine it now
            gui = self.__cached_gui if use_cache else self.dc.get_gui(self.device)
            component = None

            # First try and get a component that matches exactly with the event, but if none can be
            # found, then just get the topmost component at the event's position.
            component_list = self.dc.search_gui_components(gui, event = event)
            if len(component_list) > 0:
                component = component_list[0]
            else:
                component_list = self.dc.search_gui_components(gui, point = (event.x, event.y),
                        enabled = True)
                if len(component_list) > 0:
                    component = component_list[0]

            # If no component could be found, then set event_tuple to None; else, attach the
            # component's information to the event tuple
            if component is None:
                event_tuple = None
            else:
                if self.__debug:
                    print("        Associated component: {}".format(component))
                event_tuple.component_id = component.resource_id
                event_tuple.component_class = component.component_class
                if event_type == Swipe:
                    event_tuple.direction = get_swipe_direction(event.dx, event.dy)
        
        return event_tuple
    
    def _mine_event_tuples(self,
            recorded_events: List[Tuple[int, EventInstance]]) -> List[EventTuple]:
        """
        Plays back previously recorded events and determines event tuples. Return the event tuples
        in a list in the order they ocurred.
        """
        
        event_tuples = []

        # exit if there are no recorded events
        if len(recorded_events) == 0:
            return event_tuples

        # time standardization delta -- used to convert actual time into event timestamp space
        prev_timestamp = recorded_events[0][0]
        prev_actual_time = int(time() * 1000)

        # execute recorded events and attempt to mine GUI information
        for event_info in recorded_events:
            
            timestamp = event_info[0]
            event = event_info[1]

            # discard the event if it's a PowerButton
            if type(event) == PowerButton:
                continue

            # wait until the event should be executed according to its recorded timestamp
            timestamp_delta = timestamp - prev_timestamp
            actual_time = int(time() * 1000)
            actual_time_delta = actual_time - prev_actual_time
            delay = timestamp_delta - actual_time_delta
            if delay > 0:
                sleep(delay / 1000)
            prev_timestamp = timestamp
            prev_actual_time = actual_time
            
            # determine the event tuple for this event and add it to the list if it wasn't None
            if self.__debug:
                print("    Event: {}".format(event))
            event_tuple = self._determine_event_tuple(event, False)
            if event_tuple is None:
                if self.__debug:
                    print("        None")
            else:
                event_tuples.append(event_tuple)
                if self.__debug:
                    print("        Token: {}".format(event_tuple))
            
            # execute the event on the device
            if not self.__debug and event_tuple is not None:
                print("Extracted: {}".format(event_tuple))
            self.dc.send_event(self.device, event)

        return event_tuples
            
    def _process_mined_tuples(self, event_tuples: List[EventTuple]) -> List[str]:
        """
        Processes a given list of event tuples by doing the following:
        - discard any EnterKey events
        - squash sequences of Text events into one Text event, then insert an EnterKey event
        - convert EventTuple objects into string tokens
        """
        
        # iterate backward through the list of event tuples
        for i in range(len(event_tuples) - 1, -1, -1):

            event_tuple = event_tuples[i]

            # if the action is ENTER_KEY, then remove it and continue
            if event_tuple.action == EnterKey:
                del event_tuples[i]
                continue

            # If the action is TEXT, then remove it if the previous one is also TEXT and matches the
            # current tuple's activity. If the previous one wasn't a TEXT, then add an ENTER_KEY
            # tuple.
            elif event_tuple.action == Text:
                if (i >= 1 and event_tuples[i - 1].action == Text and
                        event_tuples[i - 1].activity == event_tuple.activity):
                    del event_tuples[i]
                    continue
                else:
                    new_tuple = EventTuple(event_tuple.activity, EnterKey)
                    event_tuples.insert(i + 1, str(new_tuple))
            
            # convert the current event tuple to a string token
            event_tuples[i] = str(event_tuples[i])

        return event_tuples
            
    def _mine(self, recorded_events: List[Tuple[int, EventInstance]]) -> List[str]:
        """
        Mines event tuples from a list of events formatted like (timestamp, event). Ouputs a list of
        event tuples represented as strings (now called tokens) that can be used as training data
        for the language model. If the length of the returned list would exceed max_tokens, then
        truncate the list as to not exceed that value.
        """

        event_tuples = self._mine_event_tuples(recorded_events)
        recording_tokens = self._process_mined_tuples(event_tuples)

        return recording_tokens
    
    def _validate_token(self, token: str) -> Optional[EventInstance]:
        """
        Determines if the given token (generated from the language model) can be turned into an
        event that can be executed on the device. If the validation is successful, then return the
        corresponding event to be executed. If the validation is unsuccessful, i.e. the token's
        corresponding GUI component does not exist on the screen, then return None.

        Always uses cached activity and gui.
        """

        if self.__debug:
            print("Validating token: " + token)

        # event to be returned
        event = None

        # convert the token into an EventTuple object so we can read its attributes
        event_tuple = EventTuple.create_from_string(token)

        # return None if the event tuple was not able to be created
        if event_tuple is None:
            return None

        # check the current activity against the activity from the event tuple
        if self.__cached_activity != event_tuple.activity:
            if self.__debug:
                print("    Activities do not match (current activity: {})"
                        .format(self.__cached_activity))
            return None
        
        # if the event was a touch event, then need to try and find a corresponding GUI component
        if event_tuple.action in (Tap, LongTap, Swipe):

            # Attempt to find the token's corresponding GUI component. If there was more than one
            # corresponding component, then choose one randomly.
            component = None
            component_list = self.dc.search_gui_components(self.__cached_gui,
                    resource_id = event_tuple.component_id,
                    component_class = event_tuple.component_class, enabled = True)
            if len(component_list) > 0:
                    component = choice(component_list)
            
            # Determine an event if a component was found
            if component is not None:
                if event_tuple.action == Tap:
                    event = Tap(*random_within_bounds(component.bounds))
                elif event_tuple.action == LongTap:
                    event = LongTap(*random_within_bounds(component.bounds),
                            _DEFAULT_LONG_TAP_DURATION)
                else:
                    event = random_swipe(component.bounds, event_tuple.direction,
                            self.device.screen_width, self.device.screen_height)
            
            if self.__debug:
                print("    Found component: " + str(component))
        
        # if the event was Text, then create random Text event
        elif event_tuple.action == Text:
            event = Text("".join(choice(ascii_letters) for _ in range(randint(1, 5))))
        
        # if the event was EnterKey, then create EnterKey event
        elif event_tuple.action == EnterKey:
            event = EnterKey()

        return event
    
    def _generate_and_validate(self, num_events: int) -> bool:
        """
        Generate tokens, convert them to events, and execute the events. Continue doing this until
        the target number of events have been executed, or the app crashed. Return if the target
        number of events was executed without the app crashing.

        The strangeness of generated events will increase (mixture coefficient will tend toward 0.5)
        as the concentraion of successful token validations increases, and vice versa.
        """

        need_to_cache = True
        event_count = 0
        VALIDATION_HISTORY_LIMIT = 5
        successes = 0 # number of successes out of the last VALIDATION_HISTORY_LIMIT validations
        repeated_failures = 0
        exclude = set() # tokens to exclude in the model
        FAILURES_BEFORE_RANDOM = 3

        while event_count < num_events:

            # return false if the app is no longer running, aka the app crashed
            if not self.dc.app_is_running(self.device, self.package_name):
                return False
            
            # Determine mixture coefficient based on number of successes; mixture coefficient will
            # increase with more successes to create stranger events
            successes = max(0, min(successes, VALIDATION_HISTORY_LIMIT))
            mix_coef = successes / VALIDATION_HISTORY_LIMIT / 2

            # generate a token
            if self.__debug:
                print("[{}/{}] Generating token...".format(event_count + 1, num_events))
            token = self.__language_model.generate_token(mix_coef, exclude)

            # Redetermine cached values if need be
            if need_to_cache:
                self._populate_cache()
                need_to_cache = False

            # attempt to get an event from the token
            event = self._validate_token(token)
            validation_successful = event is not None

            if validation_successful:
                if self.__debug:
                    print("    Validation SUCCESS: {}".format(event))
                successes += 1
            else:
                # Validation failed -- add the token to exclude and increment repeated_failures;
                # if this value reaches the limit, then generate a random event
                if self.__debug:
                    print("    Validation FAIL")
                successes -= 1
                repeated_failures += 1
                exclude.add(token)
                if repeated_failures >= FAILURES_BEFORE_RANDOM:
                    event = generate_random_event(self.dc, self.__cached_gui,
                            self.device.screen_width, self.device.screen_height,
                            self.dc.get_keyboard_bounds(self.device))
                    if self.__debug:
                        print("Repeated validation failure limit reached, generated random:")
                        print("    Event: {}".format(event))
                    token = str(self._determine_event_tuple(event, True))
                    if self.__debug:
                        print("        Token: {}".format(token))
                else:
                    continue
            
            # execute the event and update language model context
            if not self.__debug:
                print("[{}/{}] Sending event: {}".format(event_count + 1, num_events, event))
            self.dc.send_event(self.device, event)
            if token != str(None):
                self.__language_model.add_to_context(token)

            # need to cache for the next iteration; also update exclude and counters
            need_to_cache = True
            exclude = set()
            repeated_failures = 0
            event_count += 1

            if self.__debug:
                print()
        
        return True
    
    def restart_app(self):
        """
        Kills and launches the app. Used in between stages of the strategy.
        """
        if self.dc.app_is_running(self.device, self.package_name):
            self.dc.kill_app(self.device, self.package_name)
        self.dc.launch_app(self.device, self.package_name)

    def execute(self, num_events: int, perform_recording: bool = True,
            recording_timeout: Optional[float] = None, recording_event_limit: Optional[int] = None,
            use_past_data: bool = True, automatic_app_restart: bool = True) -> bool:
        """
        Executes the MonkeyLab Strategy and returns the testing result (True if the test was
        successful, False otherwise). Goes through the following stages:
        1. Record events
        2. Mine recorded events into event tuples
        4. Generate and validate events according to language model

        num_events: The number of events to execute. If a value < 1 is given, then no events are
        executed and True is always returned; this does not affect the recording and mining stages.

        perform_recording: Whether or not to record and mine events before the language model is
        created. If set to False, then data is only pulled from past MonkeyLab sessions and the 
        use_past_data parameter is ignored. Defaults to True, i.e. the default behavior is to
        perform the recording and mining.

        recording_timeout: Maximum number of seconds to record events, if recording is taking place.
        If None, then there is no timeout. Defaults to None.

        recording_event_limit: Maximum number of events to record, if recording is taking place. If
        None, then there is no limit. Defaults to None.

        use_past_data: If set to True, then the language model will use data from previous
        MonkeyLab sessions in addition to any data that was mined in the current session. If set to
        False, then only data mined in the current session is used.

        automatic_app_restart: If set to True, then the app will automatically be killed and
        launched between each stage of the strategy so the user does not have to manually navigate
        to the starting screen of the app each time. Set this to False if there is some barrier
        which must be overcome manually in order to get to the starting screen of the app, e.g. a
        login page, or if the app restarting is otherwise inconvenient. Defaults to True.
        """

        token_sequences = []
        recording_tokens = []

        # if perform_recording is True, then record events and mine them into tokens
        if perform_recording:

            if automatic_app_restart:
                self.restart_app()
                input("[RECORD] Make sure the app is at the starting screen. " +
                        "Press Enter when ready to record events.")
            else:
                input("[RECORD] Navigate to the starting screen of the app. " +
                        "Press Enter when ready to record events.")
            recording_file = ".events.txt"
            self._record(recording_file, recording_timeout, recording_event_limit)
            if self.__debug:
                print()

            # mine the recorded events, truncate if length exceeds __MAX_TOKENS
            if automatic_app_restart:
                self.restart_app()
                input("[MINE] Make sure the app is at the starting screen, then press Enter.")
            else:
                input("[MINE] Navigate to the starting screen of the app. Press Enter when done.")
            if self.__debug:
                print()
            print("Determining event tuples...")
            recording_tokens = self._mine(get_recorded_events(recording_file))[:self.__MAX_TOKENS]

            if self.__debug:
                print()

        # If use_prev_data is True, then get previously mined token sequences from the database.
        if use_past_data or not perform_recording:
            num_tokens = 0 if len(token_sequences) == 0 else len(token_sequences[0])
            needed_tokens = self.__MAX_TOKENS - num_tokens
            if needed_tokens > 0:
                database = Database()
                token_sequences.extend(database.get_token_sequences(needed_tokens,
                        self.package_name))

        # If the recorded token sequence isn't empty, then store it in the database and insert it
        # at the beginning of token_sequences.
        if len(recording_tokens) > 0:
            database = Database()
            database.add_token_sequence(recording_tokens, self.package_name)
            token_sequences.insert(0, recording_tokens)

        # Create the language model, then generate and validate (as long as num_events >= 1)
        if num_events >= 1:

            print("Creating model...")
            self.__language_model = MonkeyLabLanguageModel(token_sequences, self.__debug)
            if self.__debug:
                print()

            if automatic_app_restart:
                self.restart_app()
                input("[GENERATE+VALIDATE] Make sure the app is at the starting screen, then " +
                        "press Enter.")
            else:
                input("[GENERATE+VALIDATE] Navigate to the starting screen of the app. " +
                        "Press Enter when ready to begin testing.")
            if self.__debug:
                print()
            test_success = self._generate_and_validate(num_events)

            if test_success:
                print("TEST SUCCESS!")
                return True
            
            print("TEST FAIL: App crashed")
            return False
        
        # default to returning True
        return True
    
    def delete_past_data():
        """
        Permanently deletes all data from the MonkeyLab token database.
        """
        database = Database()
        database.destroyDatabase()
        print("Data has been deleted")
