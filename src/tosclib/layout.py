"""General Layout shortcuts"""

from copy import deepcopy
from .tosc import *
from .tosc import ElementTOSC
from .elements import Property, ControlElements
from .controls import Control
import numpy as np


"""
COPY AND MOVE 
"""


def copyProperties(source: ElementTOSC, target: ElementTOSC, *args: str):
    """Args can be any number of property keys"""
    if args is None:
        [target.properties.append(deepcopy(e)) for e in source.properties]
        return True
    for arg in args:
        if elements := source.properties.findall(f"*[{Property.Elements.KEY}='{arg}']"):
            [target.properties.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {args}")
    return True


def moveProperties(source: ElementTOSC, target: ElementTOSC, *args):
    elements = []
    if args is None:
        elements = source.properties
    for arg in args:
        if e := source.properties.findall(f"*[{Property.Elements.KEY}='{arg}']"):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {args}")

    [target.properties.append(deepcopy(e)) for e in elements]
    [source.properties.remove(e) for e in elements]
    return True


def copyValues(source: ElementTOSC, target: ElementTOSC, *args: str):
    """Args can be any number of value keys"""
    if args is None:
        [target.values.append(deepcopy(e)) for e in source.values]
        return True
    for arg in args:
        if elements := source.values.findall(f"*[{Property.Elements.KEY}='{arg}']"):
            [target.values.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {args}")
    return True


def moveValues(source: ElementTOSC, target: ElementTOSC, *args: str):
    elements = []
    if args is None:
        elements = source.values
    for arg in args:
        if e := source.values.findall(f"*[{Property.Elements.KEY}='{arg}']"):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {args}")

    [target.values.append(deepcopy(e)) for e in elements]
    [source.values.remove(e) for e in elements]
    return True


def copyMessages(source: ElementTOSC, target: ElementTOSC, *args: str):
    """Args can be ControlElements.OSC, MIDI, LOCAL, GAMEPAD"""
    if args is None:
        [target.messages.append(deepcopy(e)) for e in source.messages]
        return True
    for arg in args:
        if elements := source.messages.findall(f"./{arg}"):
            [target.messages.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {args}")
    return True


def moveMessages(source: ElementTOSC, target: ElementTOSC, *args: str):
    elements = []
    if args is None:
        elements = source.messages
    for arg in args:
        if e := source.messages.findall(f"./{arg}"):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {args}")

    [target.messages.append(deepcopy(e)) for e in elements]
    [source.messages.remove(e) for e in elements]
    return True


def copyChildren(source: ElementTOSC, target: ElementTOSC, *args: str):
    """Args can be ControlType.BOX, BUTTON, etc."""
    if args is None:
        [target.children.append(deepcopy(e)) for e in source.children]
        return True
    for arg in args:
        if elements := source.children.findall(
            f"./{ControlElements.NODE}[@type='{arg}']"
        ):
            [target.children.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {args}")
    return True


def moveChildren(source: ElementTOSC, target: ElementTOSC, *args: str):
    elements = []
    if args is None:
        elements = source.children
    for arg in args:
        if e := source.children.findall(f"./{ControlElements.NODE}[@type='{arg}']"):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {args}")

    [target.children.append(deepcopy(e)) for e in elements]
    [source.children.remove(e) for e in elements]
    return True


""" 
ARRANGE AND LAYOUT
"""


def arrangeChildren(
    parent: ElementTOSC, rows: int, columns: int, zeroPad: bool = False
) -> bool:
    """Get n number of children and arrange them in rows and columns"""
    number = len(parent.children)
    number = rows * columns

    fw = int(parent.getPropertyParam("frame", "w").text)
    fh = int(parent.getPropertyParam("frame", "h").text)
    w, h = fw / rows, fh / columns
    N = np.asarray(range(0, number)).reshape(rows, columns)
    X = np.asarray([(N[0][:columns] * w) for i in range(rows)]).reshape(1, number)
    Y = np.repeat(N[0][:rows] * h, columns).reshape(1, number)
    XYN = np.stack((X, Y, N.reshape(1, number)), axis=2)[0]

    for x, y, n in XYN:
        if zeroPad and n >= len(parent.children):
            continue
        e = ElementTOSC(parent.children[int(n)])
        e.setFrame(x, y, w, h)

    return True


# 2560x1600
def layoutColumn(func):
    def wrapper(
        ratios: tuple[float] = (1, 2, 1),
        frame: tuple[float] = (0, 0, 640, 1600),
        color: tuple[tuple] = ((0.25, 0.25, 0.25, 1.0), (0.5, 0.5, 0.5, 1.0)),
    ):
        """Function to create N groups with a:b:c:.. ratios"""
        parent = ElementTOSC(createGroup())
        parent.setFrame(frame[0], frame[1], frame[2], frame[3])
        groups = [addGroup(parent) for i in range(len(ratios))]
        [g.setName(f"group{str(i+1)}") for i, g in enumerate(groups)]

        R = np.asarray(ratios) / np.sum(ratios)
        H = R * frame[3]
        Y = [np.sum(H[0 : i[0]]) for i, v in np.ndenumerate(H)]
        YH = np.stack((Y, H), axis=1).astype(int)

        xy = np.linspace(color[0], color[1], 4)
        print(xy)

        [g.setFrame(frame[0], y, frame[2], h) for (y, h), g in zip(YH, groups)]
        func(parent)
        return parent

    return wrapper