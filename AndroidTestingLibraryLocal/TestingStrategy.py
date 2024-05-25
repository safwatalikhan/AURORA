"""
TestingStrategy.py

Superclass for all testing strategies. Subclasses should not have an __init__() method, but they
should override the execute() method.

Need to also think about how reports can be generated from the data produced by ther execution of
testing strategies.
"""

from .DeviceConnector import DeviceConnector
from .Device import Device

class TestingStrategy: 

    dc: DeviceConnector = None
    device: Device = None
    package_name: str = None
    
    # subclasses must call this method
    def __init__(self, dc: DeviceConnector, device: Device, package_name: str) -> None:
        self.dc = dc
        self.device = device
        self.package_name = package_name
    
    # subclasses override this method
    def execute(self) -> bool:
        """
        Returns the success result of the test.
        """
        pass

    # Add any more methods that should get inherited by all testing strategies
