import logging
import re
import zlib
from tosclib.controls import Group
from tosclib.decode import to_prop
from tosclib.encode import SENTINEL, xml_node, xml_property
from .elements import *
from xml.etree.ElementTree import (
    Element, 
    SubElement, 
    fromstring, 
    indent, 
    tostring, 
    XMLPullParser
    )

# __all__ = [
#     "ElementTOSC",

# ]


class ElementTOSC:
    """
    Control as XML ElementTree, references Node and top layer children.
    Creates them if not found.
    """

    __slots__ = ("node", "properties", "values", "messages", "children")

    def __init__(self, e: Element):
        """Find SubElements on init

        Args:
            e (ET.Element): <node> Element

        Attributes:
            properties (ET.Element): Find <properties>
            values (ET.Element): Find <values>
            messages (ET.Element): Find <messages>
            children (ET.Element): Find <children>
        """
        self.node: Element = e
        self.properties: Element = self._getCreate("properties")
        self.values: Element = self._getCreate("values")
        self.messages: Element = self._getCreate("messages")
        self.children: Element = self._getCreate("children")

    def __iter__(self):
        """Return iter over children"""
        return iter(self.children)

    def __getitem__(self, item):
        """Index children as Elements"""
        return self.__class__(self.children[item])

    def append(self, e: "ElementTOSC") -> "ElementTOSC":
        """Append an ElementTOSC's Node to this element's Children"""
        self.children.append(e.node)
        return self

    def _getCreate(self, target):
        s = self.node.find(target)
        if s is not None:
            return s
        return SubElement(self.node, target)

    def has_prop(self, key:str) -> bool:
        """Check if property with given key exists.

        Args:
            key (str): key of <property>

        Returns:
            bool: true if finds key
        """
        return True if self.properties.find(f".//property/[key='{key}']") is not None else False

    def get_prop(self, key:str) -> Property:
        if (p:= self.properties.find(f".//property/[key='{key}']")) is not None:
            if (prop:=to_prop(p)) is not None:
                return prop
        return ("","")

    def add_prop(self, *props: Property) -> "ElementTOSC":
        """Get N number of Property, convert them to xml and append them.

        Returns:
            ElementTOSC: chaining
        """
        for prop in props:
            self.properties.append(xml_property(prop))
        return self
    
    def set_prop(self, prop: Property) -> "ElementTOSC":
        """Finds a property by key and replaces it with a new one.

        Args:
            prop (Property): New Property.

        Raises:
            KeyError: If Property key doesn't exist.

        Returns:
            ElementTOSC: chaining.
        """
        if (p:= self.properties.find(f".//property/[key='{prop[0]}']")) is None:
            raise KeyError(f"Element can't find property: {prop}")
        self.properties.remove(p)
        self.add_prop(prop)
        return self

    def show_prop(self, key:str) -> "ElementTOSC":
        """Print XML of a Property

        Args:
            key (str): key of <property>

        Returns:
            ElementTOSC: chaining
        """
        show(self.properties.find(f".//property/[key='{key}']"))
        return self


def createTemplate(frame: tuple = None) -> Element:
    """Generates a root xml Element and adds the base GROUP node to it."""
    root = Element("lexml", attrib={"version": "3"})
    group = Group()
    if frame is not None:
        group.set_prop(("frame", frame))
    root.append(xml_node(group))
    return root


def load(inputPath: str) -> Element:
    """Reads a .tosc file and returns the XML root Element"""
    with open(inputPath, "rb") as file:
        return fromstring(zlib.decompress(file.read()))


def write(root: Element, outputPath: str) -> bool:
    """Saves an Element to .tosc"""
    with open(outputPath, "wb") as file:
        treeFile = tostring(root, encoding="UTF-8", method="xml")
        file.write(zlib.compress(treeFile))
    return True


def show(e: Element | None):
    """Generic print string function, UTF-8, indented 2 spaces"""
    if e is not None:
        indent(e, "  ")
        print(tostring(e).decode("utf-8"))


"""
PARSERS
"""

def get_text_value_from_key(properties: Element, key: str) -> str:
    """Find the value.text from a known key"""
    if prop := properties.find(f"./property/[key='{key}']"):
        if (value := prop.find("value")) is not None:
            if (text := value.text) is not None:
                return text 
    return ""


def find_child(e: Element, name: str) -> Element | None:
    if (children:= e.find("children")) is None:
        return None
    for child in children:
        if (p:=child.find("./properties/property/[key='name']")) is None:
            continue
        if p[1].text == name:
            return child
    return SENTINEL(find_child)



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
    parser = XMLPullParser()
    with open(inputFile, "rb") as file:
        parser.feed(zlib.decompress(file.read()))
        for _, e in parser.read_events():  # event, element
            if e.find("properties") is None:
                continue
            if (p:=e.find("properties")) is None:
                continue
            if get_text_value_from_key(p, key) == value:
                parser.close()
                return get_text_value_from_key(p, targetKey)

    parser.close()
    return None