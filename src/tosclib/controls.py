"""
Hexler's Enumerations
"""

from dataclasses import dataclass, field
import logging
from typing import ClassVar, Final, NewType, Protocol, Tuple, Literal
from .elements import *
import xml.etree.ElementTree as ET
from lxml import etree as ET


@dataclass
class _ControlProperties:
    """Common properties across all Control Types
    https://hexler.net/touchosc/manual/script-properties-and-values"""

    name: Final[str] = " "
    """Any string"""
    tag: Final[str] = "tag"
    """Any string"""
    script: Final[str] = " "
    """Any string"""
    frame: Final[tuple] = field(default_factory=lambda: (0, 0, 100, 100))
    """x,y,w,h float list"""
    color: Final[tuple] = field(default_factory=lambda: (0.25, 0.25, 0.25, 1.0))
    """r,g,b,a float list"""
    locked: Final[bool] = False
    visible: Final[bool] = True
    interactive: Final[bool] = True
    background: Final[bool] = True
    outline: Final[bool] = True
    outlineStyle: int = 1
    """0,1,2, = Full, Corner, Edges"""
    grabFocus: bool = True
    """Depends on the control, groups are false"""
    pointerPriority: Final[int] = 0
    """0,1 = Oldest, Newest"""
    cornerRadius: Final[float] = 0.0
    """An integer number value ranging from 0 to 10"""
    orientation: int = 0
    """0,1,2,3 = North, East, South, West"""

    def build(self, *args) -> tuple[Property]:
        """ Build all Property objects of this class.
        Returns:
            tuple[Property] from this class' attributes.
        """
        if len(args) == 0:
            args = [key for key in vars(self) if key != "props"]

        return (PropertyFactory.build(arg, getattr(self, arg)) for arg in args if arg in vars(self))


@dataclass
class _BoxProperties:
    shape: int = 0
    """0,1,2,3,4,5 Rectangle, Circle, Triangle, Diamond, Pentagon, Hexagon"""


@dataclass
class _GroupProperties:
    outlineStyle: int = 0
    """0,1,2, = Full, Corner, Edges"""
    grabFocus: bool = False
    """Depends on the control, groups are false"""


@dataclass
class _GridProperties:
    grid: Final[bool] = True
    gridSteps: Final[int] = 10
    """Size of grid"""


@dataclass
class _ResponseProperties:
    response: Final[int] = 0
    """0,1 = Absolute, Relative"""
    responseFactor: Final[int] = 100
    """An integer value ranging from 1 to 100."""


@dataclass
class _CursorProperties:
    cursor: Final[bool] = True
    cursorDisplay: Final[int] = 0
    """Cursor display 0, 1, 2 = always, active, inactive"""


@dataclass
class _LineProperties:
    lines: Final[bool] = 1
    linesDisplay: Final[int] = 0
    """Cursor display 0, 1, 2 = always, active, inactive"""


@dataclass
class _XyProperties:
    lockX: Final[bool] = False
    lockY: Final[bool] = False
    gridX: Final[bool] = True
    gridY: Final[bool] = True
    gridStepsX: Final[int] = 10
    gridStepsY: Final[int] = 10


@dataclass
class _TextProperties:
    font: int = 0
    """0, 1 = default, monospaced"""
    textSize: Final[int] = 14
    """Any int"""
    textColor: Final[tuple] = field(default_factory=lambda: (1, 1, 1, 1))
    """rgba dict from 0 to 1 as str"""
    textAlignH: Final[int] = 2
    """1,2,3 = left, center, right"""


@dataclass
class BoxProperties(_ControlProperties, _BoxProperties):
    orientation: int = 0
    """0,1,2,3 = North, East, South, West"""


@dataclass
class ButtonProperties(_ControlProperties, _BoxProperties):
    buttonType: Final[int] = 0
    """0,1,2 Momentary, Toggle_Release, Toggle_Press"""
    press: Final[bool] = True
    release: Final[bool] = True
    valuePosition: Final[bool] = False


@dataclass
class LabelProperties(_ControlProperties, _TextProperties):
    textLength: Final[int] = 0
    """0 is infinite length"""
    textClip: Final[bool] = True


@dataclass
class TextProperties(_ControlProperties, _TextProperties):
    pass


@dataclass
class FaderProperties(
    _ControlProperties, _ResponseProperties, _GridProperties, _CursorProperties
):
    bar: Final[bool] = True
    barDisplay: Final[int] = 0


@dataclass
class XyProperties(
    _ControlProperties,
    _ResponseProperties,
    _CursorProperties,
    _XyProperties,
):
    pass


@dataclass
class RadialProperties(
    _ControlProperties,
    _ResponseProperties,
    _GridProperties,
    _CursorProperties,
):
    outlineStyle: int = 0
    """0,1,2, = Full, Corner, Edges"""
    inverted: Final[bool] = False
    centered: Final[bool] = False


@dataclass
class EncoderProperties(_ControlProperties, _ResponseProperties, _GridProperties):
    outlineStyle: int = 0
    """0,1,2, = Full, Corner, Edges"""


@dataclass
class RadarProperties(
    _ControlProperties,
    _CursorProperties,
    _LineProperties,
    _XyProperties,
):
    pass


@dataclass
class RadioProperties(_ControlProperties):
    steps: Final[int] = 5
    """Amount of radio steps"""
    radioType: Final[int] = 0
    """0,1 = select, meter"""
    orientation: int = 0
    """0,1,2,3 = North, East, South, West"""


@dataclass
class GroupProperties(_ControlProperties, _GroupProperties):
    pass


@dataclass
class GridProperties(_ControlProperties):
    grabFocus: bool = False
    """Depends on the control, groups are false"""
    exclusive: bool = False
    gridNaming: Final[int] = 0
    """0,1,2 = Index, Column, Row"""
    gridOrder: Final[int] = 0
    """0,1 = Row, Column"""
    gridStart: Final[int] = 0
    """0,1,2,3 = Top left, Top right, Bottom Left, Bottom Right"""
    gridType: Final[int] = 4
    """0,1,2,3,4,5,6,7,8 See ControlType, can't hold groups"""
    gridX: Final[int] = 2
    """amount of elements on X"""
    gridY: Final[int] = 2
    """amount of elements on Y"""


@dataclass
class PagerProperties(_ControlProperties, _GroupProperties):
    """0,1,2, = Full, Corner, Edges"""

    tabLabels: Final[bool] = 1
    tabbar: Final[bool] = 1
    tabbarDoubleTap: Final[bool] = 0
    tabbarSize: Final[int] = 40
    """int from 10 to 300"""
    textSizeOff: Final[int] = 14
    """font size any int"""
    textSizeOn: Final[int] = 14
    """font size any int"""


@dataclass
class PageProperties(_ControlProperties, _GroupProperties):
    tabColorOff: Final[tuple] = field(default_factory=lambda: (0.25, 0.25, 0.25, 1))
    tabColorOn: Final[list] = field(default_factory=lambda: (0, 0, 0, 0))
    tabLabel: Final[str] = "1"
    textColorOff: Final[list] = field(default_factory=lambda: (1, 1, 1, 1))
    textColorOn: Final[list] = field(default_factory=lambda: (1, 1, 1, 1))


@dataclass
class Page:
    """Not a main control"""

    controlT: ClassVar[controlType] = ControlType.GROUP
    properties: tuple[Property] = field(default_factory=PageProperties())
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())
    children: tuple[controlType] = field(default_factory=lambda: ())


@dataclass
class Box:
    controlT: ClassVar[controlType] = ControlType.BOX
    properties: tuple[Property] = field(default_factory=lambda: BoxProperties().build())
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Button:
    controlT: ClassVar[controlType] = ControlType.BUTTON
    properties: tuple[Property] = field(
        default_factory=lambda: ButtonProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Label:
    controlT: ClassVar[controlType] = ControlType.LABEL
    properties: tuple[Property] = field(
        default_factory=lambda: LabelProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Text:
    controlT: ClassVar[controlType] = ControlType.TEXT
    properties: tuple[Property] = field(
        default_factory=lambda: TextProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Fader:
    controlT: ClassVar[controlType] = ControlType.FADER
    properties: tuple[Property] = field(
        default_factory=lambda: FaderProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Xy:
    controlT: ClassVar[controlType] = ControlType.XY
    properties: tuple[Property] = field(default_factory=lambda: XyProperties().build())
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Radial:
    controlT: ClassVar[controlType] = ControlType.RADIAL
    properties: tuple[Property] = field(
        default_factory=lambda: RadialProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Encoder:
    controlT: ClassVar[controlType] = ControlType.ENCODER
    properties: tuple[Property] = field(
        default_factory=lambda: EncoderProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Radar:
    controlT: ClassVar[controlType] = ControlType.RADAR
    properties: tuple[Property] = field(
        default_factory=lambda: RadarProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Radio:
    controlT: ClassVar[controlType] = ControlType.RADIO
    properties: tuple[Property] = field(
        default_factory=lambda: RadioProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())


@dataclass
class Group:
    controlT: ClassVar[controlType] = ControlType.GROUP
    properties: tuple[Property] = field(
        default_factory=lambda: GroupProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())
    children: tuple[controlType] = field(default_factory=lambda: ())


@dataclass
class Grid:
    controlT: ClassVar[controlType] = ControlType.GRID
    properties: tuple[Property] = field(
        default_factory=lambda: GridProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())
    children: tuple[controlType] = field(default_factory=lambda: ())


@dataclass
class Pager:
    controlT: ClassVar[controlType] = ControlType.PAGER
    properties: tuple[Property] = field(
        default_factory=lambda: PagerProperties().build()
    )
    values: tuple[Value] = field(default_factory=lambda: ())
    messages: tuple[Message] = field(default_factory=lambda: ())
    children: tuple[controlType] = field(
        default_factory=lambda: (Page(), Page(), Page())
    )


class Control(Protocol):
    controlT: ClassVar[controlType]
    properties: tuple[Property]
    values: tuple[Value]
    messages: tuple[Message]



class ControlFactory:
    @classmethod
    def build(cls, control: Control):
        node = ET.Element(
            ControlElements.NODE.value, attrib={"type": control.controlT.value}
        )
        properties = ET.Element(ControlElements.PROPERTIES.value)
        values = ET.SubElement(node, ControlElements.VALUES.value)
        messages = ET.SubElement(node, ControlElements.MESSAGES.value)
        children = ET.SubElement(node, ControlElements.CHILDREN.value)

        xmlFactory.buildProperties(control.properties, properties)
        xmlFactory.buildValues(control.values, values)
        xmlFactory.buildMessages(control.messages, messages)


class xmlFactory:
    @classmethod
    def buildProperties(cls, props: tuple[Property], e: ET.Element) -> bool:
        for prop in props:
            property = ET.SubElement(
                e, ControlElements.PROPERTY.value, attrib={"type": prop.type}
            )
            ET.SubElement(property, "key").text = prop.key
            value = ET.SubElement(property, "value")
            value.text = prop.value
            for k in prop.params:
                ET.SubElement(value, k).text = prop.params[k]
        return True

    @classmethod
    def buildValues(cls, vals: tuple[Value], e: ET.Element) -> bool:
        for val in vals:
            value = ET.SubElement(e, ControlElements.VALUE.value)
            for k in val.__slots__:
                ET.SubElement(value, k).text = getattr(val, k)
        return True

    @classmethod
    def buildMessages(cls, msgs: tuple[Message], e: ET.Element) -> bool:
        for msg in msgs:
            message = ET.SubElement(e, ControlElements[type(msg)])
            for k in msg.__slots__:
                ET.SubElement(message, k).text = getattr(msg, k)
        return True
