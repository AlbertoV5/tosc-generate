# type: ignore
"""
API for TOSC Control Elements.
"""
import logging
from copy import deepcopy
import re
from typing import TypeAlias
import zlib
import uuid
from typing import Any
from .elements import *
from .controls import (
    ControlConverter,
    XmlFactory,
    controlType,
    Control,
)

import xml.etree.ElementTree as ET

# from lxml import etree as ET

ElementXML: TypeAlias = ET.Element


class ElementTOSC:
    """
    Control as XML ElementTree, references Node and top layer children.
    Creates them if not found.
    """

    __slots__ = ("node", "properties", "values", "messages", "children")

    def __init__(self, e: ElementXML):
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
        self.properties = self._getCreate("properties")
        self.values = self._getCreate("values")
        self.messages = self._getCreate("messages")
        self.children = self._getCreate("children")

    def __iter__(self):
        """Return iter over children"""
        return iter(self.children)

    def __getitem__(self, item):
        """Index children as Elements"""
        return self.__class__(self.children[item])

    def __repr__(self):
        return f"""
Control: {getControlType(self)}
Name: {getName(self)}"""

    def append(self, e: "ElementTOSC") -> "ElementTOSC":
        """Append an ElementTOSC's Node to this element's Children"""
        self.children.append(e.node)
        return self

    def _getCreate(self, target):
        s = self.node.find(target)
        if s is not None:
            return s
        return ET.SubElement(self.node, target)

    @classmethod
    def fromFile(cls, file: str) -> "ElementTOSC":
        """Load a .tosc file into an XML Element and then as ElementTOSC"""
        return cls(load(file)[0])


def setSimpleProperty(func):
    """Pass value as text arg"""

    def wrapper(e: "ElementTOSC", value):
        type, key = func(e)
        element = getProperty(e, key)
        if element is not None:
            e.properties.remove(element)
        return createPropertyNoCheck(e, Property(type.value, key, str(value)))

    return wrapper


def setBooleanProperty(func):
    """Pass value as bool, so outline is True"""

    def wrapper(e: "ElementTOSC", value):
        type, key = func(e)
        element = getProperty(e, key)
        if element is not None:
            e.properties.remove(element)
        return createPropertyNoCheck(e, Property(type.value, key, repr(int(value))))

    return wrapper


def setMultiProperty(func):
    """Pass args as tuple of keys, so color is ("r","g","b","a")"""

    def wrapper(e: "ElementTOSC", params):
        type, key, paramKeys = func(e)
        element = getProperty(e, key)
        if element is not None:
            e.properties.remove(element)
        return createPropertyNoCheck(
            e,
            Property(
                type.value,
                key,
                params={k: repr(params[i]) for i, k in enumerate(paramKeys)},
            ),
        )

    return wrapper


"""

PROPERTY

"""


def hasProperty(e: ElementTOSC, key: str) -> bool:
    return True if findKey(e.properties, key) else False


def getProperty(e: ElementTOSC, key: str) -> ElementXML | None:
    """Finds property that has a key child that matches

    Args:
        key (str): Key text

    Returns:
        ElementXML | None: ./property
    """
    return findKey(e.properties, key)


def getPropertyValue(e: ElementTOSC, key: str) -> ElementXML | None:
    """Finds value child of property with given key.

    Args:
        key (str): Key text

    Returns:
        ElementXML | None: ./property/value
    """
    return findKey(e.properties, key).find("value")


def getPropertyParam(e: ElementTOSC, key: str, param: str) -> ElementXML | None:
    """Finds value child of property with given key, then
    finds the param child of value.

    Args:
        key (str): Key text
        param (str): Param tag

    Returns:
        ElementXML | None: ./property/value/param
    """
    if (value := findKey(e.properties, key).find("value")) is not None:
        return value.find(param)
    return None


def setProperty(e: ElementTOSC, key: str, value: str = "", params: dict = {}) -> bool:
    if (k := findKey(e.properties, key)) is None:
        raise ValueError(f"{key} doesn't exist.")
    return XmlFactory.modifyProperty(k, value, params)


def createProperty(e: ElementTOSC, property: Property) -> bool:
    if findKey(e.properties, property.key) is not None:
        raise ValueError(f"{property.key} already exists.")
    return createPropertyNoCheck(e, property)


def createPropertyNoCheck(e: ElementTOSC, property: Property) -> bool:
    return XmlFactory.buildProperties(e.properties, [property])


"""

VALUES

"""


def hasValue(e: ElementTOSC, key: str) -> bool:
    return True if findKey(e.values, key) is not None else False


def getValue(e: ElementTOSC, key: str) -> ElementXML | None:
    return findKey(e.values, key)


def getValueParam(e: ElementTOSC, key: str, param: str) -> ElementXML | None:
    return findKey(e.values, key).find(param)


def createValue(e: ElementTOSC, value: Value) -> bool:
    if findKey(e.values, value.key) is not None:
        raise ValueError(f"{value.key} already exists.")
    return XmlFactory.buildValues(e.values, [value])


def setValue(e: ElementTOSC, value: Value) -> bool:
    if (v := findKey(e.values, value.key)) is None:
        raise ValueError(f"{value.key} doesn't exist.")
    return XmlFactory.modifyValue(v, value)


"""
MESSAGES
"""


def createOSC(e: ElementTOSC, message: MessageOSC = MessageOSC()) -> bool:
    """Builds and appends an OSC message"""
    return XmlFactory.buildMessages(e.messages, [message])


def createMIDI(e: ElementTOSC, message: MessageMIDI = MessageMIDI()) -> bool:
    """Builds and appends a M1D1 message"""
    return XmlFactory.buildMessages(e.messages, [message])


def createLOCAL(e: ElementTOSC, message: MessageLOCAL = MessageLOCAL()) -> bool:
    """Builds and appends a LOCAL message"""
    return XmlFactory.buildMessages(e.messages, [message])


def removeOSC(e: ElementTOSC) -> bool:
    """Find and remove all OSC messages"""
    [msg.remove for msg in e.messages.findall(ControlElements.OSC.value)]
    return True


def removeMIDI(e: ElementTOSC) -> bool:
    """Find and remove all MIDI messages"""
    [msg.remove for msg in e.messages.findall(ControlElements.MIDI.value)]
    return True


def removeLOCAL(e: ElementTOSC) -> bool:
    """Find and remove all LOCAL messages"""
    [msg.remove for msg in e.messages.findall(ControlElements.LOCAL.value)]
    return True


def findChildByName(e: ElementTOSC, name: str) -> ElementXML | None:
    for child in e.children:
        if child.find(ControlElements.PROPERTIES.value) is None:
            continue
        if re.fullmatch(
            getTextValueFromKey(child.find(ControlElements.PROPERTIES.value), "name"),
            name,
        ):
            return child
    return None


def createChild(e: ElementTOSC, type: controlType) -> ElementXML:
    return XmlFactory.buildNode(e.children, type)


def getID(e: ElementTOSC) -> str:
    return str(e.node.attrib["ID"])


def getControlType(e: ElementTOSC):
    return str(e.node.attrib["type"])


def isControlType(e: ElementTOSC, control: ControlType):
    return str(e.node.attrib["type"]) == control.value


def setControlType(e: ElementTOSC, value: ControlType):
    """See ControlType Element"""
    e.node.attrib["type"] = value.value
    return True


"""

PROPERTIES API

"""


def getFrame(e: ElementTOSC) -> tuple[int, ...]:
    """Wrapper for getX, getY, etc."""
    return (
        getX(e),
        getY(e),
        getW(e),
        getH(e),
    )


def getColor(e: ElementTOSC) -> tuple[float, ...]:
    """Wrapper for getR getB, etc."""
    return (
        getR(e),
        getG(e),
        getB(e),
        getA(e),
    )


def getR(e: ElementTOSC) -> Any:
    if (p := getPropertyParam(e, "color", "r")) is not None:
        return float(str(p.text))
    raise ValueError("Could not find color: r")


def getG(e: ElementTOSC) -> float:
    if (p := getPropertyParam(e, "color", "g")) is not None:
        return float(str(p.text))
    raise ValueError("Could not find color: g")


def getB(e: ElementTOSC) -> float:
    if (p := getPropertyParam(e, "color", "b")) is not None:
        return float(str(p.text))
    raise ValueError("Could not find color: b")


def getA(e: ElementTOSC) -> float:
    if (p := getPropertyParam(e, "color", "a")) is not None:
        return float(str(p.text))
    raise ValueError("Could not find color: a")


def getX(e: ElementTOSC) -> int:
    if (p := getPropertyParam(e, "frame", "x")) is not None:
        return int(str(p.text))
    raise ValueError("Could not find frame: x")


def getY(e: ElementTOSC) -> int:
    if (p := getPropertyParam(e, "frame", "y")) is not None:
        return int(str(p.text))
    raise ValueError("Could not find frame: y")


def getW(e: ElementTOSC) -> int:
    if (p := getPropertyParam(e, "frame", "w")) is not None:
        return int(str(p.text))
    raise ValueError("Could not find frame: w")


def getH(e: ElementTOSC) -> int:
    if (p := getPropertyParam(e, "frame", "h")) is not None:
        return int(str(p.text))
    raise ValueError("Could not find frame: h")


@setSimpleProperty
def setName():
    """String"""
    return PropertyType.STRING, "name"


def getName(e: ElementTOSC):
    if (n := getPropertyValue(e, "name")) is not None:
        return n.text
    raise ValueError


@setSimpleProperty
def setTag():
    """String"""
    return PropertyType.STRING, "tag"


@setSimpleProperty
def setScript():
    """String"""
    return PropertyType.STRING, "script"


@setMultiProperty
def setFrame():
    """Tuple of x,y,w,h"""
    return PropertyType.FRAME, "frame", ("x", "y", "w", "h")


@setMultiProperty
def setColor():
    """r, g, b, a"""
    return PropertyType.COLOR, "color", ("r", "g", "b", "a")


@setBooleanProperty
def setLocked():
    """Boolean"""
    return PropertyType.BOOLEAN, "locked"


@setBooleanProperty
def setBackground():
    """Boolean"""
    return PropertyType.BOOLEAN, "background"


@setBooleanProperty
def setVisible():
    """Boolean"""
    return PropertyType.BOOLEAN, "visible"


@setBooleanProperty
def setInteractive():
    """Boolean"""
    return PropertyType.BOOLEAN, "interactive"


@setBooleanProperty
def setOutline():
    """Boolean"""
    return PropertyType.BOOLEAN, "outline"


def show(e: ElementTOSC):
    showElement(e.node)


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


"""

GENERAL FUNCTIONS

"""


def findKey(elements: ElementXML, key: str) -> ElementXML | Any:
    """Iterate through element with children and return child whose key matches"""
    return elements.find(f"*[key='{key}']")
    # for e in elements:
    #     if re.fullmatch(e.find("key").text, key):
    #         return e
    # return None


def showElement(e: ElementXML | None):
    """Generic print string function, UTF-8, indented 2 spaces"""
    if e is not None:
        ET.indent(e, "  ")
        print(ET.tostring(e).decode("utf-8"))


def createTemplate(frame: tuple = None) -> ElementXML:
    """Generates a root xml Element and adds the base GROUP node to it."""
    root = ET.Element("lexml", attrib={"version": "3"})
    node = ET.SubElement(
        root,
        ControlElements.NODE.value,
        attrib={"ID": str(uuid.uuid4()), "type": ControlType.GROUP.value},
    )
    if frame is not None:
        setFrame(ElementTOSC(node), frame)
    return root


def createGroup() -> ElementXML:
    """Simple create Node type GROUP"""
    return ET.Element(
        ControlElements.NODE.value,
        attrib={"ID": str(uuid.uuid4()), "type": ControlType.GROUP.value},
    )


def load(inputPath: str) -> ElementXML:
    """Reads a .tosc file and returns the XML root Element"""
    with open(inputPath, "rb") as file:
        return ET.fromstring(zlib.decompress(file.read()))


def write(root: ElementXML, outputPath: str) -> bool:
    """Encodes a root Element to .tosc"""
    with open(outputPath, "wb") as file:
        treeFile = ET.tostring(root, encoding="UTF-8", method="xml")
        file.write(zlib.compress(treeFile))
    return True


def getTextValueFromKey(properties: ElementXML | Any, key: str) -> str | Any:
    """Find the value.text from a known key"""
    if prop := properties.find(f"./property/[key='{key}']"):
        value = prop.find("value")
        return value.text if value is not None else ""
    return None


def asCtrl(xml: ElementXML) -> Control:
    pass


def asXml(source: Control) -> ElementXML:
    return ControlConverter.toXML(source)


def asRoot(source: Control) -> ElementXML:
    root = ET.Element("lexml", attrib={"version": "3"})
    root.append(asXml(source))
    return root


def asEtosc(source: ElementXML | Control) -> ElementTOSC:
    if isinstance(source, ElementXML):
        return ElementTOSC(source)
    else:
        return ElementTOSC(ControlConverter.toXML(source))


"""
COPY AND MOVE
"""


def copyProperties(source: ElementTOSC, target: ElementTOSC, *args: str):
    """Args can be any number of property keys"""
    if args is None:
        [target.properties.append(deepcopy(e)) for e in source.properties]
        return True
    for arg in args:
        if elements := source.properties.findall(f"*[key='{arg}']"):
            [target.properties.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {args}")
    return True


def moveProperties(source: ElementTOSC, target: ElementTOSC, *args):
    elements = []
    if args is None:
        elements = source.properties
    for arg in args:
        if e := source.properties.findall(f"*[key='{arg}']"):
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
        if elements := source.values.findall(f"*[key='{arg}']"):
            [target.values.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {args}")
    return True


def moveValues(source: ElementTOSC, target: ElementTOSC, *args: str):
    elements = []
    if args is None:
        elements = source.values
    for arg in args:
        if e := source.values.findall(f"*[key='{arg}']"):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {args}")

    [target.values.append(deepcopy(e)) for e in elements]
    [source.values.remove(e) for e in elements]
    return True


def copyMessages(source: ElementTOSC, target: ElementTOSC, *args: elementType):
    """Args can be ControlElements.OSC, MIDI, LOCAL, GAMEPAD"""
    if args is None:
        [target.messages.append(deepcopy(e)) for e in source.messages]
        return True
    for arg in args:
        if elements := source.messages.findall(f"./{arg.value}"):
            [target.messages.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {arg.value}")
    return True


def moveMessages(source: ElementTOSC, target: ElementTOSC, *args: elementType):
    elements = []
    if args is None:
        elements = source.messages
    for arg in args:
        if e := source.messages.findall(f"./{arg.value}"):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {arg.value}")

    [target.messages.append(deepcopy(e)) for e in elements]
    [source.messages.remove(e) for e in elements]
    return True


def copyChildren(source: ElementTOSC, target: ElementTOSC, *args: elementType):
    """Args can be ControlType.BOX, BUTTON, etc."""
    if args is None:
        [target.children.append(deepcopy(e)) for e in source.children]
        return True
    for arg in args:
        if elements := source.children.findall(
            f"./{ControlElements.NODE.value}[@type='{arg.value}']"
        ):
            [target.children.append(deepcopy(e)) for e in elements]
        else:
            raise ValueError(f"Failed to find all elements with {arg.value}")
    return True


def moveChildren(source: ElementTOSC, target: ElementTOSC, *args: elementType):
    elements = []
    if args is None:
        elements = source.children
    for arg in args:
        if e := source.children.findall(
            f"./{ControlElements.NODE}[@type='{arg.value}']"
        ):
            elements += e
        else:
            raise ValueError(f"Failed to find all elements with {arg.value}")

    [target.children.append(deepcopy(e)) for e in elements]
    [source.children.remove(e) for e in elements]
    return True


"""

GENERAL PARSERS

"""


def pullValueFromKey(
    inputFile: str, key: str, value: str, targetKey: str
) -> str | None:
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
            if e.find("properties") is None:
                continue
            if re.fullmatch(getTextValueFromKey(e.find("properties"), key), value):
                parser.close()
                return getTextValueFromKey(e.find("properties"), targetKey)

    parser.close()
    return None


def pullValueFromKey2(
    root: ElementXML, key: str, value: str, targetKey: str
) -> str | None:
    """If you know the name of an element but don't know its other properties.
    This parses an Element and has to convert it to string so its slower.

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
        if e.find("properties") is None:
            continue
        if re.fullmatch(getTextValueFromKey(e.find("properties"), key), value):
            parser.close()
            return getTextValueFromKey(e.find("properties"), targetKey)
    return None


def pullIdfromName(root: ElementXML, name: str) -> str:
    """ """
    parser = ET.XMLPullParser()
    parser.feed(ET.tostring(root, encoding="UTF-8"))
    for _, e in parser.read_events():  # event, element
        if e.find("properties") is None:
            continue
        # xpath ftw
        if e.find(f"./properties/property/[value='{name}']") is not None:
            parser.close()
            return e.attrib["ID"]

    raise ValueError(f"{name}'s ID wasn't found.")


class PropertyParser:
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
        if tag == ControlElements.NODE.value:
            self.index += 1
            self.node = True
            self.targetList.append({arg: "" for arg in [*self.args]})
        elif self.node and tag == ControlElements.PROPERTY.value:
            self.property = True
        elif self.property and tag == "key":
            self.key = True
        elif self.property and tag == "value":
            self.value = True

    def end(self, tag):
        if tag == ControlElements.NODE.value:
            self.node = False
        elif self.node and tag == ControlElements.PROPERTY.value:
            self.property = False
        elif self.property and tag == "key":
            self.key = False
        elif self.property and tag == "value":
            self.value = False

        if self.targetFound and tag == "value":
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


def parseProperties(node: ElementXML, *args) -> list:
    """
    Specify all properties you want to find and this will parse
    the entire Node and its children and return a list of key value pairs.

    For example:

    [{"name":"control1", "script":"scriptContent1"},
    {"name":"control2", "script":""},
    {"name":"control3", "script":"scriptContent3"}]

    Args:
        node (ET.Element): Node element to parse.

    Returns:
        List[dict]: [{arg: "" for arg in [args]}]
    """
    target = PropertyParser(*args)
    line = ET.tostring(node, encoding="UTF-8")
    parser = ET.XMLParser(target=target)
    parser.feed(line)
    return parser.close()


"""

Testing stuff

"""


def testFromString(data):
    return ET.fromstring(data)
