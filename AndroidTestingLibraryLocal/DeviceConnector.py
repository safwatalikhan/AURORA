"""
DeviceConnector.py

Contains all necessary methods for connecting with devices.
"""

from typing import Union, Optional, List, Tuple

import inspect
import time
from ppadb.client import Client as PPADB_client
import subprocess
from threading import Thread
from queue import Queue, Empty
import re
import xml.etree.ElementTree as ET

from .Device import Device
from .Events import EventInstance, EventClass, Tap, LongTap, Swipe, PowerButton, DownKey, MoveEnd, LongBackSpace
from .GeteventParser import GeteventParser
from .GuiComponent import (GuiComponent, component_matches_event_type, make_gui_component,
        component_contains_point)

class DeviceConnector:

    __adb_client: PPADB_client = None

    def __init__(self, host: str = "127.0.0.1", port: int = 5037) -> None:
        """
        Start the ADB client and server on the specified host and port number.
        """

        try:
            # attempt to start the server and initialize the ppadb client
            subprocess.run(["adb", "start-server"])
            self.__adb_client = PPADB_client(host, port)
        
        except FileNotFoundError as error:
            # this probably means that the system does not recognize `adb` as a command
            raise FileNotFoundError("The command 'adb start-server' failed to execute; make sure " +
                    "adb is installed and that your PATH environment variable points to the adb " +
                    "executable.") from error

    def _fill_device_basic_properties(self, device: Device) -> None:
        """
        Helper method to set basic properties of a given device. Raises an error if any of the
        properties could not be retreived.
        """

        device_properties = {
            "name":            None,
            "model":           None,
            "android_version": None,
            "sdk_level":       None,
            "device_type":     None,
            "screen_width":    None,
            "screen_height":   None
        }

        # use `adb shell getprop ...` to collect the more detailed information
        device_properties["name"] = device.ppadb.shell("getprop ro.product.name").strip()
        device_properties["model"] = device.ppadb.shell("getprop ro.product.model").strip()
        device_properties["android_version"] = device.ppadb.shell(
                "getprop ro.build.version.release").strip()
        device_properties["sdk_level"] = int(device.ppadb.shell(
                "getprop ro.build.version.sdk").strip())
        device_properties["device_type"] = device.ppadb.shell(
                "getprop ro.product.device").strip()
        
        # get the screen dimensions
        screen_size_str = device.ppadb.shell("wm size").strip()
        match = re.search(r"(\d+)x(\d+) *$", screen_size_str)
        if match:
            device_properties["screen_width"] = int(match.group(1))
            device_properties["screen_height"] = int(match.group(2))

        # assign the extracted information to the Device object
        for key in device_properties:

            # Raise an error if any properties were not found; we have to do this because some
            # functionality relies on these properties being populated
            if device_properties[key] is None:
                raise RuntimeError("Could not get all device properties!")

            setattr(device, key, device_properties[key])
    
    def _fill_device_input_properties(self, device: Device) -> None:
        """
        Helper method to get properties regarding the device's input devices. If properties were not
        able to be collected, then raise an error.
        """

        # Getting the long tap delay is a simple settings retreival, everything else requires
        # parsing through longer output
        match = re.match(r"(^\d+)", device.ppadb.shell("settings get secure long_press_timeout"))
        if match:
            device.input_properties["min_long_tap_duration"] = int(match.group(1))
        
        # execute the `adb shell dumpsys input inputs` to get input device info
        output_lines = device.ppadb.shell("dumpsys input inputs").split("\n")

        device_paths = {} # {name: path}
        current_device = None
        current_device_output_region = 0
        reading = False

        regex_device_path_header = re.compile(r"^    -?\d+: ((?:(?! \().)+)")
        regex_device_path = re.compile(r"^      Path: (.*)")
        regex_device_info_header = re.compile(r"^  Device -?\d+: (.*)")
        regex_x = re.compile(r"^        X: .*min=(\d+).*max=(\d+)(?:$|[^\d])")
        regex_y = re.compile(r"^        Y: .*min=(\d+).*max=(\d+)(?:$|[^\d])")
        regex_tap_slop = re.compile(r"^      TapSlop: (\d+(?:\.\d+)?)px")

        # parse through the command output and collect input device information
        for line in output_lines:

            # this is where input devices' names are attached to their corresponding paths
            if reading and current_device_output_region == 1:

                if line[:4] != "    ":
                    current_device = None
                    reading = False
                    continue
            
                match = regex_device_path_header.match(line)
                if match:
                    current_device = match.group(1)
                    continue
                
                if current_device is not None:
                    match = regex_device_path.match(line)
                    if match is not None:
                        device_paths[current_device] = match.group(1)
                        current_device = None
            
            # This is where actual info, e.g. min_x, max_x, is collected for each input device path.
            # Also, configuration info like tap slop is collected here.
            elif reading and current_device_output_region == 2:

                if line[:2] != "  ":
                    reading = False
                    continue
                    
                if line[:4] != "    ":
                    current_device = None

                # look for tap slop property
                match = regex_tap_slop.match(line)
                if match:
                    device.input_properties["tap_slop"] = float(match.group(1))
                    continue

                # look for input devices and input device properties
                match = regex_device_info_header.match(line)
                if match and match.group(1) in device_paths:
                    current_device = device_paths[match.group(1)]
                    device.input_devices[current_device] = {"name": match.group(1)}
                    continue
                
                if current_device is not None:
                    for axis in ("x", "y"):
                        match = locals()["regex_" + axis].match(line)
                        if match:
                            device.input_devices[current_device][axis + "_min"] = int(match.group(1))
                            device.input_devices[current_device][axis + "_max"] = int(match.group(2))
                            break

            # detect when entering the first relevant output region (names and paths)
            elif line[:10] == "  Devices:":
                reading = True
                current_device_output_region = 1
            
            # detect when entering the second relevant output region (input device properties and
            # config info).
            elif line[:19] == "Input Reader State:":
                reading = True
                current_device_output_region = 2

    def enumerate_discoverable_devices(self) -> List[Device]:
        """
        Return a list of Device objects that are discoverable, i.e. devices with which we are able
        to establish a connection.
        """

        device_list = []

        # get a list of devices in ppadb representation
        ppadb_device_list = self.__adb_client.devices()

        # iterate through each ppadb device, convert it to a Device object, and attempt to collect
        # more information about it
        for ppadb_device in ppadb_device_list:
            
            # create a Device object from the ppadb device and get info about it
            device = Device(ppadb_device, ppadb_device.serial)
            self._fill_device_basic_properties(device)
            self._fill_device_input_properties(device)
            
            device_list.append(device)

        return device_list
    
    def get_device(self,
            serial: Optional[str] = None,
            name: Optional[str] = None,
            model: Optional[str] = None,
            android_version: Optional[str] = None,
            sdk_level: Optional[int] = None,
            device_type: Optional[str] = None,
            screen_width: Optional[int] = None,
            screen_height: Optional[int] = None) -> Optional[Device]:
        """
        Return the first found Device object matching all of the given conditions. If no device was
        found, then return None. To simply get the first available device, do not provide any
        parameters. 
        """

        # build a dictionary of attributes from the given search parameters
        search_attribs = {}
        for param in inspect.signature(self.get_device).parameters:
            if locals()[param] is not None:
                search_attribs[param] = locals()[param]

        # enumerate discoverable devices and return first one to match all search attributes
        for device in self.enumerate_discoverable_devices():

            should_continue = False

            for key in search_attribs:
                if getattr(device, key) != search_attribs[key]:
                    should_continue = True
                    break

            if should_continue:
                continue
        
            return device

        # no device was found, so return None
        return None

    def send_event(self, device: Device, event: EventInstance) -> None:
        """
        Send the specified event to the specified device. This method is blocking, i.e. code after
        this method call will not execute until the event completes.
        """
        device.ppadb.shell(event.get_cmd_str())
    
    def get_screen_capture(self, device: Device,
            save_path: Optional[str] = "screen.png") -> None:
        """
        Take a sceenshot of the given device in PNG format and save it to the given save_path. Saves
        by default as 'screen.png'.
        """

        png_data = device.ppadb.screencap()

        with open(save_path, "wb") as file:
            file.write(png_data)
    
    def get_gui_hier(self, device: Device) -> Optional[GuiComponent]:
        xml = device.ppadb.shell("uiautomator dump --all /dev/tty | " +
                "grep -ov 'UI hierchary dumped to: /dev/tty$'")
        return xml
        

    def get_gui(self, device: Device) -> Optional[GuiComponent]:
        """
        Retrieve all GUI components currently shown on the screen of the given device. Returns the
        root GuiComponent, or None if the GUI was not able to be retrieved.
        """

        # get xml representation of gui hierarchy as a string
        xml = device.ppadb.shell("uiautomator dump --all /dev/tty | " +
                "grep -ov 'UI hierchary dumped to: /dev/tty$'")

        try:

            # parse the xml and get the root node
            tree = ET.ElementTree(ET.fromstring(xml))
            root = tree.getroot()

            return make_gui_component(root[0], None)
        
        except:
            return None
    
    def search_gui_components(self,
            target: Union[Device, GuiComponent],
            event: Optional[EventInstance] = None,
            event_type: Optional[EventClass] = None,
            point: Optional[Tuple[int, int]] = None,
            enabled: Optional[bool] = None,
            resource_id: Optional[str] = None,
            full_resource_id: Optional[str] = None,
            component_class: Optional[str] = None,
            package: Optional[str] = None,
            text: Optional[str] = None,
            content_description: Optional[str] = None,
            checked: Optional[bool] = None) -> List[GuiComponent]:
        """
        Returns a list of GuiComponents from the given target where each GuiComponent in the list
        satisfies all the given search parameters. The earlier a GuiComponent appears in the
        returned list, the more nested that GuiComponent is in the GUI hierarchy.

        target: Can either be a Device or a GuiComponent. If a Device, then the currently
        displayed GUI on the device will be searched. If a GuiComponent, then this method will not
        pull the GUI from a device, but will instead search through the GUI hierarchy rooted at the
        given GuiComponent.

        Search parameters (one or more may be given):
        - event: Returned GuiComponents must be interactable with the given event, such that
        the GuiComponents...
            - are enabled
            - have attributes matching the event type
            - contain the starting point of the event in their bounds attribute
        - event_type: A type of event, e.g. Tap, LongTap, Swipe. Retuned GuiComponents must be
        interactable with events of this type.
        - point: Returned GuiComponents must contain the given point in its bounds attribute. The
        point must be formatted like (x, y).
        - all others: The given value for the search parameter name must match exactly with that
        attribute of the GuiComponent in order for the GuiComponent to be returned.
        """

        search_params = list(inspect.signature(self.search_gui_components).parameters)[1:]

        # ensure that at least one of the search parameters is defined
        should_exit = True
        for param in search_params:
            if locals()[param] is not None:
                should_exit = False
                break
        if should_exit:
            return []

        if type(target) == Device:
            target = self.get_gui(target)
        
        # exit if GUI extraction failed
        if target is None:
            return []
        
        component_list = []

        # iterate through the components and look for matches with search parameters
        for component in reversed(target.iterate_hierarchy()):

            if event is not None:
                if not (type(event) in (Tap, LongTap, Swipe) and
                        component.enabled and
                        component_matches_event_type(component, type(event)) and
                        component_contains_point(component, event.x, event.y)):
                    continue
            
            if event_type is not None:
                if not component_matches_event_type(component, event_type):
                    continue

            if point is not None:
                if not component_contains_point(component, *point):
                    continue
            
            should_continue = False
            for attrib in search_params[3:]:
                if locals()[attrib] is not None and getattr(component, attrib) != locals()[attrib]:
                    should_continue = True
                    break
            if should_continue:
                continue
            
            component_list.append(component)
        
        return component_list
        

    def record_events(self, device: Device, save_path: str = "events.txt", 
            manual_override: bool = True, timeout: Optional[float] = None,
            event_limit: Optional[int] = None) -> None:
        """
        Records events on the given device and saves them to the file denoted by save_path. If no
        save_path is given, defaults to "events.txt"

        manual_override: If set to True, the recording can be stopped by pressing the power button
        on the device two times, with each press less than a second apart. Defaults to True.

        timeout: Recording is terminated after the given amount of seconds has passed. If None, then
        there is no timeout. Defaults to None.

        event_limit: Recording is terminated after the given number of events has been detected. If
        set to None, then there is no limit. Defaults to None.
        """

        # daemon to read from stdout; iterate over lines in stdout and push them to queue
        def read_stdout(stdout, queue: Queue) -> None:
            for line in stdout:
                queue.put(line)
        
        # Start the subprocess which does the recording.
        command = "adb -s " + device.serial + " shell getevent -lt"
        process = subprocess.Popen(command, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.PIPE, shell = True)
        start_time = time.time()
        print('Started recording events on device "' + device.serial + '"')

        # start the read daemon; the queue will receive stdout from the read daemon
        queue = Queue()
        read_daemon = Thread(target = read_stdout, args = (process.stdout, queue), daemon = True)
        read_daemon.start()

        # create (or overwrite) the file denoted by save_path with the intention of writing the
        # parsed event stream
        with open(save_path, "w") as save_file:

            parser = GeteventParser(device)
            should_die = False
            num_events = 0
            time_last_pressed = None

            # loop to continuously read from queue as long as process is alive
            while not should_die:
                
                # if there is a timeout and it has been exceeded, then need to exit the loop
                if timeout is not None and time.time() - start_time > timeout:
                    should_die = True
                    
                # attempt to get the next line from the queue
                line = ""
                try:
                    line = queue.get_nowait()
                    line = line.decode("utf8").strip()
                except Empty:
                    # only skip to next iteration if this is not the last iteration
                    if not should_die:
                        continue
                
                # parse the line and retreive any events that were outputted; if this is the last
                # iteration of the loop, then flush the parser beforehand
                completed_events = []
                if should_die:
                    completed_events.extend(parser.flush())
                completed_events.extend(parser.parse(line))

                for event_info in completed_events:

                    timestamp = event_info[0]
                    event = event_info[1]

                    # print the output and send it to save_path
                    event_str = "[" + str(timestamp) + "] " + str(event)
                    print(event_str)
                    save_file.write(event_str + "\n")
                    num_events += 1

                    # if event_limit is set, then need to check if that has been exceeded
                    if event_limit is not None and num_events >= event_limit:
                        should_die = True

                    # if manual_override is True, then handle stuff for the manual override
                    if manual_override and type(event) == PowerButton:
                        if time_last_pressed is not None and timestamp - time_last_pressed < 1000:
                            should_die = True
                        else:
                            time_last_pressed = timestamp

        process.kill()
        print('Stopped recording events on device "' + device.serial + '"')
    
    def get_keyboard_bounds(self,
            device: Device) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Returns the bounds of the software keyboard on the device formatted like
        ((x1, y1), (x2, y2)) if the keybaoard is showing. If the keyboard is not showing, then None
        is returned.
        """

        # get the output of the shell command that gives information about the keyboard
        output = device.ppadb.shell("dumpsys window InputMethod")
        # the "mHasSurface" output parameter tells us if the keyboard is displayed or not
        match = re.search(r"mHasSurface=(true|false)", output)

        if match:

            # if the keyboard is displayed, then try to extract the bounds info from the output
            if match.group(1) == "true":

                match = re.search(r"touchable region=SkRegion\(\((\d+),(\d+),(\d+),(\d+)\)\)",
                        output)
                
                if match:
                    
                    # get the bounds and return them
                    x1 = int(match.group(1)) 
                    y1 = int(match.group(2)) 
                    x2 = int(match.group(3)) 
                    y2 = int(match.group(4))
                    
                    return ((x1, y1), (x2, y2))

        # default to returning None	
        return None

    def get_current_activity(self, device: Device) -> Optional[str]:
        """
        Returns the name of the current activity on the given deivce. If the activity could not be
        determined, then return None.
        """

        # get the output of the shell command that gives information about activities
        output = device.ppadb.shell("dumpsys activity activities")

        # determine the name of the activity
        match = re.search(r"m?ResumedActivity: ?ActivityRecord{[^ ]+ [^ ]+ .+/(?:.*\.)?([^ ]+)",
                output)

        # return the name if the match was successful
        if match:
            return match.group(1)

        return None
        
    def launch_app(self, device: Device, package_name: str) -> None:
        """
        Launches the specified app on the given device.
        """
        device.ppadb.shell("monkey -p " + package_name + " -c android.intent.category.LAUNCHER 1")

    def kill_app(self, device: Device, package_name: str) -> None:
        """
        Kills the specified app on the given device.
        """
        device.ppadb.shell("am force-stop " + package_name)
    
    def app_is_running(self, device: Device, package_name: str) -> bool:
        """
        Return True if the app denoted by package_name is running on the device; otherwise, returns
        False.
        """

        output = device.ppadb.shell("pidof " + package_name).strip()
        match = re.match(r"\d+", output)

        return match is not None

    def get_current_app(self, device: Device):
        """
        Returns the package name of the currently running app.
        """

        # get the output of the shell command that gives information about activities
        output = device.ppadb.shell("dumpsys activity activities")

        # determine the name of the package
        match = re.search(r"m?ResumedActivity: ?ActivityRecord{[^ ]+ [^ ]+ (.+)/",
                output)

        # return the name if the match was successful
        if match:
            return match.group(1)

        return None
    
    def install_app(self, device: Device, apk_path: str) -> None:
        """
        Installs the APK at apk_path on the given device.
        """
        subprocess.run(["adb", "-s", device.serial, "install", "-r", apk_path])

    def uninstall_app(self, device: Device, package_name: str) -> None:
        """
        Uninstalls the app denoted by package_name from the given device.
        """
        subprocess.run(["adb", "-s", device.serial, "uninstall", package_name])

    def enumerate_installed_apps(self, device: Device) -> List[str]:
        """
        Returns a list of package names representing apps that are installed on the given device.
        """
        
        #output = device.ppadb.shell("pm list packages")
        # Changed in February 7, 2023
        # apk list had a trailing '\r' for all the items
        output = device.ppadb.shell("pm list packages").replace("\r","")
        pk_list = re.findall(r"(?:^|\n)package:(.+)", output)
        
        return pk_list
    
    def app_is_installed(self, device: Device, package_name: Optional[str]) -> bool:
        """
        Returns True if the given app (package) is installed on the given device; returns False
        otherwise.
        """
        return package_name in self.enumerate_installed_apps(device)

    def get_apk(self, device: Device, package_name: str, save_path: str = "app.apk") -> None:
        """
        From the given device, pull the APK file of the app whose package name is package_name. Save
        the pulled APK file to the given save_path; defaults to "app.apk".
        """

        # get the package 
        package = device.ppadb.shell("pm path " + package_name)

        # remove prefix "package:"
        apk_path = package[8:]

        # remove \n
        apk_path = apk_path.strip()

        if apk_path:
            subprocess.run(["adb", "-s", device.serial, "pull", apk_path, save_path])
