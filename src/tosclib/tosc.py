"""
Simplify navigating, editing and generating .tosc files.
"""
from collections import namedtuple
from copy import deepcopy
import sys
import xml.etree.ElementTree as ET
import re
import zlib
import uuid
from dataclasses import dataclass, field, fields
from typing import List, Final, NamedTuple


class ControlElements(NamedTuple):
    """Valid Sub Elements for a Node"""

    PROPERTIES = "properties"  #: <properties>
    VALUES = "values"  #: <values>
    MESSAGES = "messages"  #: <messages>
    CHILDREN = "children"  #: <children>
    PROPERTY = (
        "property"  #: <property type = `PropertyType <#tosclib.tosc.PropertyType>`_>
    )
    VALUE = "value"  #: <value>
    OSC = "osc"  #: <osc>
    MIDI = "midi"  #: <midi>
    LOCAL = "local"  #: <local>
    GAMEPAD = "gamepad"  #: <gamepad>
    NODE = "node"  #: <node type = `ControlType <#tosclib.tosc.ControlType>`_>


class ControlType(NamedTuple):
    """Enum of valid <node type=?>"""

    BOX = "BOX"  #: <node type = "BOX">
    BUTTON = "BUTTON"  #: <node type = "BUTTON">
    LABEL = "LABEL"  #: <node type = "LABEL">
    TEXT = "TEXT"  #: <node type = "TEXT">
    FADER = "FADER"  #: <node type = "FADER">
    XY = "XY"  #: <node type = "XY">
    RADIAL = "RADIAL"  #: <node type = "RADIAL">
    ENCODER = "ENCODER"  #: <node type = "ENCODER">
    RADAR = "RADAR"  #: <node type = "RADAR">
    RADIO = "RADIO"  #: <node type = "RADIO">
    GROUP = "GROUP"  #: <node type = "GROUP">
    PAGER = "PAGER"  #: <node type = "PAGER">
    GRID = "GRID"  #: <node type = "GRID">


class PropertyType(NamedTuple):
    """Enum of valid <property type=?>"""

    STRING = "s"  #: <property type="s">
    BOOLEAN = "b"  #: <property type="b">
    INTEGER = "i"  #: <property type="i">
    FLOAT = "f"  #: <property type="f">
    FRAME = "r"  #: <property type="r">
    COLOR = "c"  #: <property type="c">


@dataclass
class Property:
    """Element structure for a <property>

    Args:
        type (str): See PropertyType.
        key (str): See parameters of inner classes of Controls.
        value (str, optional): Exclusive with params.
        params (dict[str,str], optional): Exclusive with value.
    """

    type: str
    key: str
    value: str = ""
    params: dict = field(default_factory=lambda: {})

    def __post_init__(self):
        if self.value and self.params:
            raise ValueError(f"{self} can't have both value and params.")
        if not self.value and not self.params:
            raise ValueError(f"{self} is missing both value and params.")

    def create(self) -> ET.Element:
        property = ET.Element("property", attrib={"type": self.type})
        ET.SubElement(property, self.__class__.Elements.KEY).text = self.key
        value = ET.SubElement(property, self.__class__.Elements.VALUE)
        if self.value:
            value.text = self.value
            return property
        for paramKey in self.params:
            ET.SubElement(value, paramKey).text = self.params[paramKey]
        return property

    class Elements(NamedTuple):
        KEY = "key"
        VALUE = "value"
        R, G, B, A = "r", "g", "b", "a"
        X, Y, W, H = "x", "y", "w", "h"


@dataclass
class Value:
    """Default Elements for <value>.

    Args:
        key (str, optional): "x" or "touch". Defaults to "touch".
        locked (str, optional): boolean. Defaults to "0".
        lockedDefaultCurrent (str, optional): boolean. Defaults to "0".
        default (str, optional): float or boolean. Defaults to "false".
        defaultPull (str, optional): 0 to 100. Defaults to "0".
    """

    key: str = "touch"
    locked: str = "0"
    lockedDefaultCurrent: str = "0"
    default: str = "false"
    defaultPull: str = "0"

    class Elements(NamedTuple):
        KEY = "key"
        LOCKED = "locked"
        LOCKED_DEFAULT_CURRENT = "lockedDefaultCurrent"
        DEFAULT = "default"
        DEFAULT_PULL = "defaultPull"


@dataclass
class Partial:
    """Default Elements for <partial>

    Args:
        type (str, optional): "CONSTANT", "INDEX", "VALUE", "PROPERTY". Defaults to "CONSTANT".
        conversion (str, optional): "BOOLEAN", "INTEGER", "FLOAT", "STRING". Defaults to "STRING".
        value (str, optional): Depends on the context. Defaults to "/".
        scaleMin (str, optional): If "VALUE", set range. Defaults to "0".
        scaleMax (str, optional): If "VALUE", set range. Defaults to "1".
    """

    type: str = "CONSTANT"
    conversion: str = "STRING"
    value: str = "/"
    scaleMin: str = "0"
    scaleMax: str = "1"


@dataclass
class Trigger:
    """Default Elements for <trigger>

    Args:
        var (str, optional): "x" or "touch". Defaults to "x".
        con (str, optional): "ANY", "RISE" or "FALL". Defaults to "ANY".
    """

    var: str = "x"
    condition: str = "ANY"


@dataclass
class OSC:
    """Default Elements and Sub Elements for <osc>

    Args:
        enabled (str, optional): Boolean. Defaults to "1".
        send (str, optional): Boolean. Defaults to "1".
        receive (str, optional): Boolean. Defaults to "1".
        feedback (str, optional): Boolean. Defaults to "0".
        connections (str, optional): Binary. Defaults to "00001" (channel 1, "00011" means 1 and 2).
        triggers (List[Trigger], optional): [Trigger]. Defaults to [Trigger()].
        path (List[Partial], optional): [Partial]. Defaults to [Partial(), Partial(typ="PROPERTY", val="name")].
        arguments (List[Partial], optional): [Partial]. Defaults to [Partial(typ="VALUE", con="FLOAT", val="x")].
    """

    enabled: str = "1"
    send: str = "1"
    receive: str = "1"
    feedback: str = "0"
    connections: str = "00001"
    triggers: List[Trigger] = field(default_factory=lambda: [Trigger()])
    path: List[Partial] = field(
        default_factory=lambda: [Partial(), Partial(type="PROPERTY", value="name")]
    )
    arguments: List[Partial] = field(
        default_factory=lambda: [Partial(type="VALUE", conversion="FLOAT", value="x")]
    )


@dataclass
class MidiMessage:
    type: str = "CONTROLCHANGE"
    channel: str = "0"
    data1: str = "0"
    data2: str = "0"


@dataclass
class MidiValue:
    type: str = "CONSTANT"
    key: str = ""
    scaleMin: str = "0"
    scaleMax: str = "15"


@dataclass
class MIDI:
    """Default elements for <midi>
    Args:
        enabled: bool
        send : bool
        receive : bool
        feedback : bool
        connections : bool
        triggers : List of Trigger
        messages : MidiMessage
        values : List of MidiValue
    """

    enabled: str = "1"
    send: str = "1"
    receive: str = "1"
    feedback: str = "0"
    connections: str = "00001"
    triggers: List[Trigger] = field(default_factory=lambda: [Trigger()])
    message: MidiMessage = MidiMessage()
    values: List[MidiValue] = field(
        default_factory=lambda: [
            MidiValue(),
            MidiValue("INDEX", "", "0", "1"),
            MidiValue("VALUE", "x", "0", "127"),
        ]
    )


@dataclass
class LOCAL:
    """Default elements for <midi>
    Args:
        enabled: bool
        triggers : Trigger x or touch.
        type : BOOL, INT, FLOAT, STRING. The Type of Trigger.x
        conversion : BOOL, INT, FLOAT, STRING.
        value : The value sent to the other local Control.
        scaleMin : 0
        scaleMax : 1
        dstType : BOOL, INT, FLOAT, STRING of the target.
        dstVar : The value you want to change in the target.
        dstID : The node {ID} of the target.
    """

    enabled: str = "1"
    triggers: List[Trigger] = field(default_factory=lambda: [Trigger()])
    type: str = "VALUE"
    conversion: str = "FLOAT"
    value: str = "x"
    scaleMin: str = "0"
    scaleMax: str = "1"
    dstType: str = ""
    dstVar: str = ""
    dstID: str = ""


@dataclass
class _PropertiesControl:
    """All controls have these properties
    https://hexler.net/touchosc/manual/script-properties-and-values"""

    name: Final[str] = "name"
    """Any string"""
    tag: Final[str] = "tag"
    """Any string"""
    script: Final[str] = " "
    """Any string"""
    frame: Final[dict] = field(default_factory=lambda: {"x": 1, "y": 1, "w": 1, "h": 1})
    """x,y,w,h float dictionary"""
    color: Final[dict] = field(default_factory=lambda: {"r": 1, "g": 1, "b": 1, "a": 1})
    """r,g,b,a float dictionary"""
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

    def build(self, *args) -> bool:
        """Create Property Elements in CAPS. Pass args to filter."""
        for key in list(vars(self)):
            value = getattr(self, key)
            if args and key not in args:
                continue
            if isinstance(value, dict) and "r" in value.keys():
                prop = Property(PropertyType.COLOR, key, "", value)
            elif isinstance(value, dict) and "x" in value.keys():
                prop = Property(PropertyType.FRAME, key, "", value)
            elif isinstance(value, int):
                prop = Property(PropertyType.INTEGER, key, str(value))
            elif isinstance(value, bool):
                prop = Property(PropertyType.BOOLEAN, key, (str(int(value))))
            elif isinstance(value, float):
                prop = Property(PropertyType.FLOAT, key, str(value))
            else:
                prop = Property(PropertyType.STRING, key, str(value))

            setattr(self, key.upper(), prop)
        return True

    def insert(self, e: "ElementTOSC") -> bool:
        for key in vars(self):
            e.createProperty(getattr(self, key))
        return True


@dataclass
class _PropertiesBox:
    shape: int = 0
    """0,1,2,3,4,5 Rectangle, Circle, Triangle, Diamond, Pentagon, Hexagon"""


@dataclass
class _PropertiesGroup:
    outlineStyle: int = 0
    """0,1,2, = Full, Corner, Edges"""
    grabFocus: bool = False
    """Depends on the control, groups are false"""


@dataclass
class _PropertiesGrid:
    grid: Final[bool] = True
    gridSteps: Final[int] = 10
    """Size of grid"""


@dataclass
class _PropertiesResponse:
    response: Final[int] = 0
    """0,1 = Absolute, Relative"""
    responseFactor: Final[int] = 100
    """An integer value ranging from 1 to 100."""


@dataclass
class _PropertiesCursor:
    cursor: Final[bool] = True
    cursorDisplay: Final[int] = 0
    """Cursor display 0, 1, 2 = always, active, inactive"""


@dataclass
class _PropertiesLine:
    lines: Final[bool] = 1
    linesDisplay: Final[int] = 0
    """Cursor display 0, 1, 2 = always, active, inactive"""


@dataclass
class _PropertiesXY:
    lockX: Final[bool] = False
    lockY: Final[bool] = False
    gridX: Final[bool] = True
    gridY: Final[bool] = True
    gridStepsX: Final[int] = 10
    gridStepsY: Final[int] = 10


@dataclass
class _PropertiesText:
    font: int = 0
    """0, 1 = default, monospaced"""
    textSize: Final[int] = 14
    """Any int"""
    textColor: Final[int] = field(
        default_factory=lambda: {"r": 1, "g": 1, "b": 1, "a": 1}
    )
    """rgba dict from 0 to 1 as str"""
    textAlignH: Final[int] = 2
    """1,2,3 = left, center, right"""


class Control:
    """All the Node Types and their available properties

    https://hexler.net/touchosc/manual/script-enumerations#controltype"""

    TYPE = "type"
    ID = "ID"

    @dataclass
    class BOX(_PropertiesControl, _PropertiesBox):
        orientation: int = 0
        """0,1,2,3 = North, East, South, West"""

    @dataclass
    class BUTTON(_PropertiesControl, _PropertiesBox):
        buttonType: Final[int] = 0
        """0,1,2 Momentary, Toggle_Release, Toggle_Press"""
        press: Final[bool] = True
        release: Final[bool] = True
        valuePosition: Final[bool] = False

    @dataclass
    class LABEL(_PropertiesControl, _PropertiesText):
        textLength: Final[int] = 0
        """0 is infinite length"""
        textClip: Final[bool] = True

    @dataclass
    class TEXT(_PropertiesControl, _PropertiesText):
        pass

    @dataclass
    class FADER(
        _PropertiesControl, _PropertiesResponse, _PropertiesGrid, _PropertiesCursor
    ):
        bar: Final[bool] = True
        barDisplay: Final[int] = 0
        """Cursor display 0, 1, 2 = always, active, inactive"""

    @dataclass
    class XY(
        _PropertiesControl,
        _PropertiesResponse,
        _PropertiesCursor,
        _PropertiesXY,
    ):
        pass

    @dataclass
    class RADIAL(
        _PropertiesControl,
        _PropertiesResponse,
        _PropertiesGrid,
        _PropertiesCursor,
    ):
        outlineStyle: int = 0
        """0,1,2, = Full, Corner, Edges"""
        inverted: Final[bool] = False
        centered: Final[bool] = False

    @dataclass
    class ENCODER(_PropertiesControl, _PropertiesResponse, _PropertiesGrid):
        outlineStyle: int = 0
        """0,1,2, = Full, Corner, Edges"""

    @dataclass
    class RADAR(
        _PropertiesControl,
        _PropertiesCursor,
        _PropertiesLine,
        _PropertiesXY,
    ):
        pass

    @dataclass
    class RADIO(_PropertiesControl):
        steps: Final[int] = 5
        """Amount of radio steps"""
        radioType: Final[int] = 0
        """0,1 = select, meter"""
        orientation: int = 0
        """0,1,2,3 = North, East, South, West"""

    @dataclass
    class GROUP(_PropertiesControl, _PropertiesGroup):
        pass

    @dataclass
    class PAGER(_PropertiesControl):
        grabFocus: bool = False
        """Depends on the control, groups are false"""
        outlineStyle: int = 0
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
    class PAGE(_PropertiesControl):
        tabColorOff: Final[dict] = field(
            default_factory=lambda: {"r": 0.25, "g": 0.25, "b": 0.25, "a": 1}
        )
        tabColorOn: Final[dict] = field(
            default_factory=lambda: {"r": 0, "g": 0, "b": 0, "a": 0}
        )
        tabLabel: Final[str] = "1"
        textColorOff: Final[dict] = field(
            default_factory=lambda: {"r": 1, "g": 1, "b": 1, "a": 1}
        )
        textColorOn: Final[dict] = field(
            default_factory=lambda: {"r": 1, "g": 1, "b": 1, "a": 1}
        )

    @dataclass
    class GRID(_PropertiesControl):
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

    @classmethod
    def hasChildren(cls):
        return (cls.GRID, cls.GROUP, cls.PAGER)

    class _PropertyParser:
        """Find all defined properties in the Node"""

        def __init__(self, *args):
            self.targetList = []
            self.args = [*args]
            self.targetFound = None
            self.multiLine = ""
            self.node = False
            self.property = False
            self.key = False
            self.value = False
            self.index = -1

        def start(self, tag, attrib):
            if tag == ControlElements.NODE:
                self.index += 1
                self.node = True
                self.targetList.append({arg: "" for arg in [*self.args]})
            elif self.node and tag == ControlElements.PROPERTY:
                self.property = True
            elif self.property and tag == Property.Elements.KEY:
                self.key = True
            elif self.property and tag == Property.Elements.VALUE:
                self.value = True

        def end(self, tag):
            if tag == ControlElements.NODE:
                self.node = False
            elif self.node and tag == ControlElements.PROPERTY:
                self.property = False
            elif self.property and tag == Property.Elements.KEY:
                self.key = False
            elif self.property and tag == Property.Elements.VALUE:
                self.value = False

            if self.targetFound and tag == Property.Elements.VALUE:
                self.targetList[self.index][self.targetFound] = self.multiLine
                self.multiLine = ""
                self.targetFound = None

        def data(self, data):
            if (
                self.node
                and self.property
                and self.key
                # and data in self.targetList.keys()
                and data in self.args
            ):
                self.targetFound = data
            if self.node and self.property and self.value and self.targetFound:
                self.multiLine = f"{self.multiLine}{data}"

        def close(self):
            return self.targetList

    @classmethod
    def parseProperties(cls, node: ET.Element, *args) -> list:
        """
        Specify all properties you want to find and this will parse
        the entire Node and its children and return a list of key value pairs.

        For example:

        >>>Control.parseProperties(node, "name", "script")

        [{"name":"control1", "script":"scriptContent1"},
        {"name":"control2", "script":""},
        {"name":"control3", "script":"scriptContent3"}]

        Args:
            node (ET.Element): Node element to parse.

        Returns:
            List[dict]: [{arg: "" for arg in [args]}]
        """
        target = cls._PropertyParser(*args)
        line = ET.tostring(node, encoding="UTF-8")
        parser = ET.XMLParser(target=target)
        parser.feed(line)
        return parser.close()


class ElementTOSC:
    """
    Contains a Node Element and its SubElements. Creates them if not found.
    """

    def __init__(self, e: ET.Element):
        """Find SubElements on init

        Args:
            e (ET.Element): <node> Element

        Attributes:
            properties (ET.Element): Find <properties>
            values (ET.Element): Find <values>
            messages (ET.Element): Find <messages>
            children (ET.Element): Find <children>
        """
        self.node = e
        f = lambda v: e.find(v) if e.find(v) else ET.SubElement(e, v)
        self.properties = f(ControlElements.PROPERTIES)
        self.values = f(ControlElements.VALUES)
        self.messages = f(ControlElements.MESSAGES)
        self.children = f(ControlElements.CHILDREN)

    @classmethod
    def fromFile(cls, file: str) -> "ElementTOSC":
        return cls(load(file)[0])

    @classmethod
    def fromGroup(cls) -> "ElementTOSC":
        return cls(
            ET.Element(
                ControlElements.NODE,
                attrib={"ID": str(uuid.uuid4()), "type": ControlType.GROUP},
            )
        )

    def getProperty(self, key: str) -> ET.Element:
        return findKey(self.properties, key)

    def getPropertyValue(self, key: str) -> ET.Element:
        return findKey(self.properties, key).find("value")

    def getPropertyParam(self, key: str, param: str) -> ET.Element:
        return findKey(self.properties, key).find("value").find(param)

    def setProperty(self, key: str, value: str = "", params: dict = {}) -> bool:
        if not findKey(self.properties, key):
            raise ValueError(f"{key} doesn't exist.")
        val = self.getPropertyValue(key)
        if value:
            val.text = value
            return True
        for paramKey in params:
            val.find(paramKey).text = params[paramKey]
        return True

    def createProperty(self, property: Property) -> bool:
        if findKey(self.properties, property.key):
            raise ValueError(f"{property.key} already exists.")
        self.properties.append(property.create())
        return True

    def getValue(self, key: str) -> ET.Element:
        return findKey(self.values, key)

    def getValueParam(self, key: str, param: str) -> ET.Element:
        return findKey(self.values, key).find(param)

    def hasValue(self, key: str) -> bool:
        return True if findKey(self.values, key) else False

    def createValue(self, value: Value) -> bool:
        if self.hasValue(value.key):
            raise ValueError(f"{value.key} already exists.")
        element = ET.SubElement(self.values, "value")
        for v in vars(value):
            ET.SubElement(element, v).text = getattr(value, v)
        return True

    def setValue(self, value: Value) -> bool:
        if not self.hasValue(value.key):
            raise ValueError(f"{value.key} doesn't exist.")
        element = findKey(self.values, value.key)
        for v in vars(value):
            element.find(v).text = getattr(value, v)
        return True

    def _createMessage(self, name, message) -> ET.Element:
        msg = ET.SubElement(self.messages, name)
        for key in vars(message):
            element = ET.SubElement(
                msg, key
            )  # enabled, send, receive, message, values, etc.
            attribute = getattr(message, key)
            if isinstance(attribute, list):  # For Partials and Triggers
                for partialOrTrigger in attribute:
                    subElement = ET.SubElement(
                        element, type(partialOrTrigger).__name__.lower()
                    )  # Create <partial> or <trigger>
                    for v in vars(partialOrTrigger):  # Attributes of Partials/Triggers
                        ET.SubElement(subElement, v).text = getattr(partialOrTrigger, v)
            elif isinstance(attribute, MidiMessage):  # not a list of Partials, not str
                for v in vars(attribute):
                    ET.SubElement(element, v).text = getattr(attribute, v)
            else:
                element.text = getattr(message, key)
        return msg

    def createOSC(self, message: OSC = OSC()) -> ET.Element:
        return self._createMessage(ControlElements.OSC, message)

    def createMIDI(self, message: MIDI = MIDI()) -> ET.Element:
        return self._createMessage(ControlElements.MIDI, message)

    def createLOCAL(self, message: LOCAL = LOCAL()) -> ET.Element:
        return self._createMessage(ControlElements.LOCAL, message)

    def removeOSC(self) -> bool:
        return [e.remove for e in self.messages.findall(ControlElements.OSC)]

    def removeMIDI(self) -> bool:
        return [e.remove for e in self.messages.findall(ControlElements.MIDI)]

    def removeLOCAL(self) -> bool:
        return [e.remove for e in self.messages.findall(ControlElements.LOCAL)]

    def findChildByName(self, name: str) -> ET.Element:
        for child in self.children:
            if not child.find(ControlElements.PROPERTIES):
                continue
            if re.fullmatch(
                getTextValueFromKey(child.find(ControlElements.PROPERTIES), "name"),
                name,
            ):
                return child
        return None

    def createChild(self, type: ControlType) -> ET.Element:
        return ET.SubElement(
            self.children,
            ControlElements.NODE,
            attrib={"ID": str(uuid.uuid4()), "type": type},
        )

    def addBox(self):
        return self.__class__(self.createChild(ControlType.BOX))

    def addGroup(self, *args: ControlType):
        e = self.__class__(self.createChild(ControlType.GROUP))
        if not args:
            return e
        r = [e]
        for arg in args:
            r.append(self.__class__(e.createChild(arg)))
        return tuple(r)

    def addButton(self):
        return self.__class__(self.createChild(ControlType.BUTTON))

    def addLabel(self):
        return self.__class__(self.createChild(ControlType.LABEL))

    def getID(self) -> str:
        return str(self.node.attrib["ID"])

    def isControlType(self, control: str):
        return True if str(self.node.attrib["type"]) == control else False

    def copyProperties(self, target: "ElementTOSC", move: bool, *args):
        """Args can be any number of property keys"""
        if not args:
            return _copyAllElements(self.properties, target.properties, move)
        for arg in args:
            _copyElements(
                self.properties,
                target.properties,
                move,
                f"*[{Property.Elements.KEY}='{arg}']",
            )
        return True

    def copyValues(self, target: "ElementTOSC", move: bool, *args):
        """Args can be any number of value keys"""
        if not args:
            return _copyAllElements(self.values, target.values, move)
        for arg in args:
            _copyElements(
                self.values,
                target.values,
                move,
                f"*[{Value.Elements.KEY}='{arg}']",
            )
        return True

    def copyMessages(self, target: "ElementTOSC", move: bool, *args):
        """Args can be ControlElements.OSC, MIDI, LOCAL, GAMEPAD"""
        if not args:
            return _copyAllElements(self.messages, target.messages, move)
        for arg in args:
            _copyElements(self.messages, target.messages, move, f"./{arg}")
        return True

    def copyChildren(self, target: "ElementTOSC", move: bool, *args):
        """Args can be ControlType.BOX, BUTTON, etc."""
        if not args:
            return _copyAllElements(self.children, target.children, move)
        for arg in args:
            _copyElements(
                self.children,
                target.children,
                move,
                f"./{ControlElements.NODE}[@type='{arg}']",
            )
        return True

    def _overrideProperty(
        self, type: str, key: str, value: str = "", params: dict = {}
    ) -> bool:
        """Create a Property, if already exists, then modify its values."""
        if element := self.getProperty(key):
            self.properties.remove(element)
        return self.createProperty(Property(type, key, value, params))
        # if not findKey(self.properties, key):
        #     return self.createProperty(Property(type, key, value=value, params=params))
        # return self.setProperty(key, value=value, params=params)

    def setControlType(self, value: str):
        """See ControlType Element"""
        self.node.attrib = {"type": value}
        return True

    def setName(self, value: str):
        return self._overrideProperty(PropertyType.STRING, "name", value=value)

    def setTag(self, value: str):
        return self._overrideProperty(PropertyType.STRING, "tag", value=value)

    def setFrame(self, x: float, y: float, w: float, h: float):
        return self._overrideProperty(
            PropertyType.FRAME,
            "frame",
            params={"x": str(x), "y": str(y), "w": str(w), "h": str(h)},
        )

    def setColor(self, r: float, g: float, b: float, a: float):
        return self._overrideProperty(
            PropertyType.COLOR,
            "color",
            params={"r": str(r), "g": str(g), "b": str(b), "a": str(a)},
        )

    def setLocked(self, value: bool):
        return self._overrideProperty(PropertyType.BOOLEAN, "locked", str(int(value)))

    def setBackground(self, value: bool):
        return self._overrideProperty(
            PropertyType.BOOLEAN, "background", value=str(int(value))
        )

    def setVisible(self, value: bool):
        return self._overrideProperty(
            PropertyType.BOOLEAN, "visible", value=str(int(value))
        )

    def setInteractive(self, value: bool):
        return self._overrideProperty(
            PropertyType.BOOLEAN, "interactive", value=str(int(value))
        )

    def setOutline(self, value: bool):
        return self._overrideProperty(
            PropertyType.BOOLEAN, "outline", value=str(int(value))
        )

    def setScript(self, value: str):
        return self._overrideProperty(PropertyType.STRING, "script", value=value)

    def show(self):
        showElement(self.node)

    def showProperty(self, name: str):
        try:
            showElement(findKey(self.properties, name))
        except TypeError:
            raise ValueError(f"{name} doesn't exist")

    def showValue(self, name: str):
        try:
            showElement(findKey(self.values, name))
        except TypeError:
            raise ValueError(f"{name} doesn't exist")


def findKey(elements: ET.Element, key: str) -> ET.Element:
    """Iterate through element with children and return child whose key matches"""
    # return elements.find(f"./key/[.='{key}']")
    for e in elements:
        if re.fullmatch(e.find("key").text, key):
            return e
    return None


def showElement(e: ET.Element):
    """Generic print string function, UTF-8, indented 2 spaces"""
    if sys.version_info[0] == 3 and sys.version_info[1] >= 9:
        ET.indent(e, "  ")
    print(ET.tostring(e).decode("utf-8"))


def createTemplate() -> ET.Element:
    """Generates a root Element for your .tosc file"""
    root = ET.Element("lexml", attrib={"version": "3"})
    ET.SubElement(
        root,
        ControlElements.NODE,
        attrib={"ID": str(uuid.uuid4()), "type": ControlType.GROUP},
    )
    return root


def load(inputPath: str) -> ET.Element:
    """Reads a .tosc file and returns the XML root Element"""
    with open(inputPath, "rb") as file:
        return ET.fromstring(zlib.decompress(file.read()))


def write(root: ET.Element, outputPath: str = None) -> bool:
    """Encodes a root Element to .tosc"""
    with open(outputPath, "wb") as file:
        treeFile = ET.tostring(root, encoding="UTF-8", method="xml")
        file.write(zlib.compress(treeFile))
        return True


def getTextValueFromKey(properties: ET.Element, key: str) -> str:
    """Find the value.text from a known key"""
    for property in properties:
        if re.fullmatch(property.find("key").text, key):
            return property.find("value").text


def pullValueFromKey(inputFile: str, key: str, value: str, targetKey: str) -> str:
    """If you know the name of an element but don't know its other properties.
    This function uses a .tosc file and gets its root.
    For passing an element see pullValueFromKey2

    Args:
        inputFile (str): File to parse.
        key (str): Known key.
        value (str): Known value.
        targetKey (str): Known key of unknown value.

    Returns:
        str: Value
    """
    parser = ET.XMLPullParser()
    with open(inputFile, "rb") as file:
        parser.feed(zlib.decompress(file.read()))
        for _, e in parser.read_events():  # event, element
            if not e.find("properties"):
                continue
            if re.fullmatch(getTextValueFromKey(e.find("properties"), key), value):
                parser.close()
                return getTextValueFromKey(e.find("properties"), targetKey)

    parser.close()
    return ""


def pullValueFromKey2(root: ET.Element, key: str, value: str, targetKey: str) -> str:
    """If you know the name of an element but don't know its other properties.

    Args:
        root (ET.Element): Parses the whole element, so you can feed the root.
        key (str): Known key.
        value (str): Known value.
        targetKey (str): Known key of unknown value.

    Returns:
        str: Value
    """
    parser = ET.XMLPullParser()
    parser.feed(ET.tostring(root, encoding="UTF-8"))
    for _, e in parser.read_events():  # event, element
        if not e.find("properties"):
            continue
        if re.fullmatch(getTextValueFromKey(e.find("properties"), key), value):
            parser.close()
            return getTextValueFromKey(e.find("properties"), targetKey)


def _copyAllElements(source: ET.Element, target: ET.Element, move: bool) -> bool:
    [target.append(deepcopy(e)) for e in source]
    if move:
        source.clear()
    return True


def _copyElements(
    source: ET.Element,
    target: ET.Element,
    move: bool,
    path: str,
) -> bool:
    elements = source.findall(path)
    if not elements:
        raise ValueError(f"Failed to find elements with {path}")
    [target.append(deepcopy(e)) for e in elements]
    if move:
        [source.remove(e) for e in elements]
    return True
