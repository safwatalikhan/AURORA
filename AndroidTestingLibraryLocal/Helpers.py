"""
Helpers.py

A collection of static helper functions for the library.
"""

from typing import Tuple, Optional

from random import randint
from math import sqrt

def hex_to_int(hex_num: str, word_size: int) -> int:
    """
    Converts a two's complement hexadecimal number of a given word_size (in bits) to an integer.
    """
    
    num = int(hex_num, 16)

    if num >= 2 ** (word_size - 1):
        num -= 2 ** word_size
    
    return num

def seconds_to_ms(seconds: float) -> int:
    """Converts from seconds (as a float) to milliseconds (as an int)"""
    return int(seconds * 1000)

def points_within_threshold(x: list, y: list, threshold: float) -> bool:
    """
    Takes two lists of the same length (must be >= 1) representing x and y coordinates. If all the
    points are within threshold distance of the first point, then return True; else return False.
    """

    for i in range(1, len(x)):
        if sqrt((x[0] - x[i]) ** 2 + (y[0] - y[i]) ** 2) > threshold:
            return False
    
    return True

def scale_linear(val: int, min_1: int, max_1: int, min_2: int, max_2: int) -> float:
    """
    Scales a value in a range onto another range.
    e.g. scale_linear(5, 0, 10, 50, 100) -> 75
    """
    
    range_1 = max_1 - min_1
    if range_1 == 0:
        range_1 = 0.00001
    
    return (val - min_1) / range_1 * (max_2 - min_2) + min_2

def within_bounds(bounds: Optional[Tuple[Tuple[int, int], Tuple[int, int]]], x: int,
        y: int) -> bool:
    """
    Returns True if the given x, y coordinates are contained in the given bounds formatted like
    ((x1, y1), (x2, y2)). Returns False if the given x, y coordinates are not within the bounds, or
    if bounds is None.
    """

    if bounds is None:
        return False
    
    return bounds[0][0] <= x <= bounds[1][0] and bounds[0][1] <= y <= bounds[1][1]

def random_within_bounds(bounds: Tuple[Tuple[int, int], Tuple[int, int]]) -> Tuple[int, int]:
    """
    Returns a random point (x, y) that is within the given bounds ((x1, y1), (x2, y2))
    """

    x = randint(bounds[0][0], bounds[1][0])
    y = randint(bounds[0][1], bounds[1][1])

    return (x, y)
