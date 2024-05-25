"""
Device.py

A representation of an Android device.
"""

from typing import Any, Dict

from ppadb.device import Device as PPADB_device

class Device:
    
    ppadb: PPADB_device = None # the ppadb representation of the device

    serial: str = None # serial code given by adb to identify device
    name: str = None
    model: str = None
    device_type: str = None
    android_version: str = None
    sdk_level: int = None
    screen_width: int = None # in pixels
    screen_height: int = None # in pixels

    # input_properties holds values pertaining to input behavior. Possible value are:
    #   min_long_tap_duration (int)
    #   tap_slop (float)
    input_properties: Dict[str, Any] = None # {property: value}

    # input_devices holds the paths of input devices and any properties of interest.
    # Formatted like {path: {prop1: val, prop2: val}}
    input_devices: Dict[str, Dict[Any, Any]] = None # {path: properties}
    
    def __init__(self, ppadb: PPADB_device, serial: str) -> None:

        self.ppadb = ppadb
        self.serial = serial

        self.input_properties = {}
        self.input_devices = {}
    
    def __str__(self) -> str:
        return ('Android device "' + self.serial + '":' +
                '\n    name:            "' + self.name + '"' +
                '\n    model:           "' + self.model + '"' +
                '\n    device type:     "' + self.device_type + '"' +
                '\n    Android version: "' + self.android_version + '"' +
                "\n    sdk level:       " + str(self.sdk_level) +
                "\n    screen width:    " + str(self.screen_width) +
                "\n    screen height:   " + str(self.screen_height))
