"""
GuiComponent.py

Class to hold information about a GUI component on an Android device.
"""

from typing import Optional, Tuple, List

import inspect
import re
import xml.etree.ElementTree as ET

from .Events import Tap, LongTap, Swipe

class GuiComponentIterator:
    """
    Iterator for the GuiComponent class; iterates through each element of the GuiComponent's
    children attribute.
    """

    __child_list: List["GuiComponent"] = None
    __list_index: int = None
    
    def __init__(self, child_list: list) -> None:
        self.__child_list = child_list
        self.__list_index = 0

    def __next__(self):
        
        if self.__list_index < len(self.__child_list):
            self.__list_index += 1
            return self.__child_list[self.__list_index - 1]
        
        raise StopIteration

class GuiComponentBreadthFirstIterator:
    """Does a breadth-first iteration through a GuiComponent."""

    __component_list: List["GuiComponent"] = None

    def __init__(self, base_component: "GuiComponent") -> None:
        
        self.__component_list = [base_component]
        index = 0

        while index < len(self.__component_list):
            for child in self.__component_list[index]:
                self.__component_list.append(child)
            index += 1
    
    def __iter__(self) -> "GuiComponentBreadthFirstIterator":
        return self
    
    def __reversed__(self) -> "GuiComponentBreadthFirstIterator":
        self.__component_list = list(reversed(self.__component_list))
        return self
    
    def __next__(self) -> "GuiComponent":
        
        if len(self.__component_list) > 0:
            
            component = self.__component_list[0]
            self.__component_list = self.__component_list[1:]

            return component

        raise StopIteration

class GuiComponent:

    enabled: bool = None

    resource_id: str = None
    full_resource_id: str = None
    component_class: str = None
    package: str = None
    text: str = None
    content_description: str = None

    tappable: bool = None
    checkable: bool = None
    checked: bool = None
    long_tappable: bool = None
    scrollable: bool = None

    bounds: Tuple[Tuple[int, int], Tuple[int, int]] = None
    center: Tuple[int, int] = None
    right: Tuple[int,int] = None	
    parent: Optional["GuiComponent"] = None
    children: List["GuiComponent"] = None

    def __init__(self,

            enabled: bool = False,

            resource_id: str = "",
            full_resource_id: str = "",
            component_class: str = "",
            package: str = "",
            text: str = "",
            content_description: str = "",

            tappable: bool = False,
            checkable: bool = False,
            checked: bool = False,
            long_tappable: bool = False,
            scrollable: bool = False,

            bounds: Tuple[Tuple[int, int], Tuple[int, int]] = ((0, 0), (0, 0)),
            center: Tuple[int, int] = (0, 0),
            right: Tuple[int,int] = (0,0)) -> None:

        for param in inspect.signature(self.__init__).parameters:
            setattr(self, param, locals()[param])
        
        self.parent = None
        self.children = []
    
    def iterate_hierarchy(self) -> GuiComponentBreadthFirstIterator:
        """
        Allows the breadth-first iteration of the GuiComponent's hierarchical structure.
        """
        return GuiComponentBreadthFirstIterator(self)
    
    def _print_hierarchy(self, indent: str, index: int, last_child: bool) -> None:
        """Receursive helper to print_hierarchy"""
        
        _indent = indent
        if _indent != "":
                _indent = _indent[:-4] + ("'-- " if last_child else "|-- ") + str(index) + " "
            
        print(_indent + str(self))
        
        for i in range(len(self)):
            last_child = i >= len(self) - 1
            self[i]._print_hierarchy(indent + ("    " if last_child else "|   "), i, last_child)
    
    def print_hierarchy(self) -> None:
        """
        Prints the hierarchy of GuiComponents treating this GuiComponent as the root of the
        hierarchy.
        """
        self._print_hierarchy("", 0, True)
    
    def get_parent(self, steps: int = 1) -> Optional["GuiComponent"]:
        """
        Gets the parent which is the given amount of steps up the hierarchy. Another way to think
        about it is that the steps argument is the number of times you would have to manually type
        out the parent attribute. For example, component.get_parent(3) is akin to saying
        component.parent.parent.parent.

        The steps argument must be >= 1. Default behavior is to get the direct parent, i.e.
        steps = 1.
        """

        if steps < 1:
            raise ValueError("steps must be >= 1")

        # base case
        if steps == 1:
            return self.parent
        
        # recursive case
        return self.parent.get_parent(steps - 1)
    
    def __str__(self) -> str:
        return ("<" +
                ("e" if self.enabled else ".") +
                ("t" if self.tappable else ".") +
                ("c" if self.checkable else ".") +
                ("C" if self.checked else ".") +
                ("l" if self.long_tappable else ".") +
                ("s" if self.scrollable else ".") +
                "> " + self.component_class + ": [" + self.resource_id + '] "' + self.text + '"')
    
    def __iter__(self) -> GuiComponentIterator:
        return GuiComponentIterator(self.children)
    
    def __getitem__(self, key) -> "GuiComponent":
        return self.children[key]
    
    def __len__(self) -> int:
        return len(self.children)
    
    def __hash__(self) -> int:
        return hash((self.enabled, self.full_resource_id, self.component_class, self.package,
                self.text, self.content_description, self.tappable, self.checkable, self.checked,
                self.long_tappable, self.scrollable, self.bounds))

def make_gui_component(node: ET.Element, parent: GuiComponent) -> GuiComponent:
    """Recursively create GuiComponent objects from the given etree.Element object."""

    comp = GuiComponent(
        enabled = True if node.attrib["enabled"] == "true" else False,
        full_resource_id = node.attrib["resource-id"],
        component_class = node.attrib["class"],
        package = node.attrib["package"],
        text = node.attrib["text"],
        content_description = node.attrib["content-desc"],
        tappable = True if node.attrib["clickable"] == "true" else False,
        checkable = True if node.attrib["checkable"] == "true" else False,
        checked = True if node.attrib["checked"] == "true" else False,
        long_tappable = True if node.attrib["long-clickable"] == "true" else False,
        scrollable = True if node.attrib["scrollable"] == "true" else False
    )

    # get resource_id
    match = re.match(r"^.*:id/(.*)", comp.full_resource_id)
    comp.resource_id = match.group(1) if match else comp.full_resource_id

    # get bounds
    match = re.match(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib["bounds"])
    if match:
        x1, y1, x2, y2 = match.group(1, 2, 3, 4)
        comp.bounds = ((int(x1), int(y1)), (int(x2), int(y2)))
    
    # set center
    center_x = (comp.bounds[0][0] + comp.bounds[1][0]) // 2
    center_y = (comp.bounds[0][1] + comp.bounds[1][1]) // 2
    comp.center = (center_x, center_y)
	
    # set right
    right_x = (comp.bounds[1][0]*9) // 10
    right_y = (comp.bounds[0][1] + comp.bounds[1][1]) // 2
    comp.right = (right_x, right_y)	
    # set parent
    comp.parent = parent

    # iterate throug the node's children and set the child elements
    for child in node:
        comp.children.append(make_gui_component(child, comp))
    
    return comp

def component_contains_point(component: GuiComponent, x: int, y: int) -> bool:
    """Returns True if the given x and y coordinates fall within the given component's bounds."""
    
    x1, y1 = component.bounds[0]
    x2, y2 = component.bounds[1]

    if x1 <= x <= x2 and y1 <= y <= y2:
        return True
    
    return False

def component_matches_event_type(component: GuiComponent, event_type) -> bool:
    """
    Return True if the given event_type makes sense according to the attributes of the component.
    """
    
    if event_type == Tap:
        return component.tappable or component.checkable
    elif event_type == LongTap:
        return component.long_tappable
    elif event_type == Swipe:
        return component.scrollable
    
    return False
