import re
import zlib
from pathlib import Path
from .core import *
from .factory import property, value
from tosclib.decode import to_property
from tosclib.encode import (
    SENTINEL,
    xml_control,
    xml_message,
    xml_property,
    property_matcher,
    xml_value,
)

# __all__ = [
#     "ControlElement",

# ]


class Node:
    """
    The XML Element version of the Control protocol.
    Creates sub XML Elements if not found.
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

    def append(self, e: "Node") -> "Node":
        """Append an ElementTOSC's Node to this element's Children"""
        self.children.append(e.node)
        return self

    def _getCreate(self, target):
        s = self.node.find(target)
        if s is not None:
            return s
        return SubElement(self.node, target)

    def has_prop(self, key: str) -> bool:
        """Check if property with given key exists.

        Args:
            key (str): key of <property>

        Returns:
            bool: true if finds key
        """
        return (
            True
            if self.properties.find(f".//property/[key='{key}']") is not None
            else False
        )

    def get_prop(self, key: str) -> Property:
        if (p := self.properties.find(f".//property/[key='{key}']")) is not None:
            if (prop := to_property(p)) is not None:
                return prop
        return property("", "")

    def add_prop(self, *props: Property) -> "Node":
        """Get N number of Property, convert them to xml and append them.

        Returns:
            ElementTOSC: chaining
        """
        for prop in props:
            if self.has_prop(prop[0]):
                raise ValueError(f"{prop} already exists.")
            self.properties.append(xml_property(prop))
        return self

    def set_prop(self, prop: Property) -> "Node":
        """Finds a property by key and replaces it with a new one.

        Args:
            prop (Property): New Property.

        Raises:
            KeyError: If Property key doesn't exist.

        Returns:
            ElementTOSC: chaining.
        """
        if (p := self.properties.find(f".//property/[key='{prop[0]}']")) is None:
            # raise KeyError(f"Element can't find property: {prop}")
            return self.add_prop(prop)

        if (value := p.find("value")) is not None:
            p.remove(value)

        value = SubElement(p, "value")
        p = property_matcher(prop, p, value)
        return self

    def show_prop(self, key: str) -> "Node":
        """Print XML of a Property

        Args:
            key (str): key of <property>

        Returns:
            ElementTOSC: chaining
        """
        show(self.properties.find(f".//property/[key='{key}']"))
        return self

    def add_msg(self, msg: Message) -> "Node":
        """Append Message to list as XML Element

        Args:
            msg (Message): Message tuple type alias

        Returns:
            Node: Self
        """
        self.messages.append(xml_message(msg))
        return self

    def add_value(self, val: Value) -> "Node":
        """Append Value to list as XML Element

        Args:
            val (Value): Value tuple type alias

        Returns:
            Node: Self
        """
        self.values.append(xml_value(val))
        return self


def createTemplate(frame: tuple = None) -> Element:
    """Generates a root xml Element and adds the base GROUP node to it."""
    root = Element("lexml", attrib={"version": "3"})
    group = Group()
    if frame is not None:
        group.set_frame(frame)
    root.append(xml_control(group))
    return root


def load(inputPath: str | Path) -> Element:
    """Reads a .tosc file and returns the XML root Element"""
    with open(str(inputPath), "rb") as file:
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


def find_child(e: Element, name: str) -> Element:
    if (children := e.find("children")) is None:
        return SENTINEL(find_child)
    for child in children:
        if (p := child.find("./properties/property/[key='name']")) is None:
            continue
        if p[1].text == name:
            return child
    return SENTINEL(find_child)


def pull_value_from_key(
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
            if (p := e.find("properties")) is None:
                continue
            if get_text_value_from_key(p, key) == value:
                parser.close()
                return get_text_value_from_key(p, targetKey)

    parser.close()
    return None


def pull_value_from_key_2(
    root: Element, key: str, value: str, targetKey: str
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
    parser = XMLPullParser()
    parser.feed(tostring(root, encoding="UTF-8"))
    for _, e in parser.read_events():  # event, element
        if (p := e.find("properties")) is None:
            continue
        if re.fullmatch(get_text_value_from_key(p, key), value):
            parser.close()
            return get_text_value_from_key(p, targetKey)
    return None


def compare_elements(e1: Element, e2: Element, depth: int = 0) -> bool:
    """Checks if both element's tags coincide.

    Args:
        e1 (Element): First element.
        e2 (Element): Second element.
        depth (int): How deep into the tree,
        0 is root, -1 is until the end.

    Returns:
        bool: If tag's match.
    """
    if len(e1) != len(e2) or e1.tag != e2.tag:
        return False
    for c1, c2, _ in zip(e1, e2, range(depth)):
        if not compare_elements(c1, c2, depth - 1):
            return False
    return True


def replace_element_whole(old: Element, new: Element):
    """Replaces old element's with new one. Keeping tags.

    Args:
        old (Element):
        new (Element):
    """
    old.attrib = new.attrib
    old.text = new.text
    old.tail = new.tail
    for e in old:
        old.remove(e)
    for e in new:
        old.append(e)


def replace_element(
    old: Element, new: Element, match_elements: bool = True, depth: int = 0
) -> Element:
    """
    ElementTree doesn't have a way to replace elements.

    This compares element tags and sizes recursively.
    It will only check until certain specified depth.
    ElementTree doesn't provide a way to get the depth,
    so pass any large integer for maximum depth.

    Args:
        old (Element): Element that will be replaced.
        new (Element): Replacer Element.
        match (bool): Match tags of root and first set of children.

    Raises:
        ValueError: In case of mismatch.

    Returns:
        Element: Returns "new".
    """
    if match_elements and not compare_elements(old, new, depth):
        raise ValueError(f"{old.tag}'s doesn't match {new.tag}")
    replace_element_whole(old, new)
    return new