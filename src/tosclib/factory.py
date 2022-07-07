"""
Tuple factories for the types in .elements
"""

from .core import *

__all__ = [
    "property",
    "value",
    "msgconfig",
    "trigger",
    "triggers",
    "partial",
    "address",
    "arguments",
    "midimsg",
    "midival",
    "localsrc",
    "localdst",
    "osc",
    "midi",
    "local",
]


def property(key: str, value: PropertyValue) -> Property:
    """Property factory"""
    return (key, value)


def value(
    key: ValueType = "touch",
    locked: bool = False,
    lockedCD: bool = False,
    default: str | bool | float = True,
    pull: int = 0,
) -> Value:
    """Value factory"""
    return (key, locked, lockedCD, default, pull)


def msgconfig(
    enabled: bool = True,
    send: bool = True,
    receive: bool = True,
    feedback: bool = False,
    connection: str = "11111",
) -> MsgConfig:
    """MessageConfig factory"""
    return MsgConfig((enabled, send, receive, feedback, connection))


def trigger(
    key: ValueType = "touch",
    condition: TriggerType = "ANY",
) -> Trigger:
    """Trigger factory"""
    return Trigger((key, condition))


def triggers(*args: Trigger) -> tuple[Trigger, ...]:
    """tuple[Trigger,...] factory"""
    if len(args) == 0:
        args = (trigger(),)
    return args


def partial(
    typ: PartialType = "CONSTANT",
    conv: ConversionType = "STRING",
    value: str = "/",
    scaleMin: int = 0,
    scaleMax: int = 1,
) -> Partial:
    """Partial factory"""
    return Partial((typ, conv, value, scaleMin, scaleMax))


def address(*args: Partial) -> tuple[Partial, ...]:
    """tuple[Partial, ...] factory"""
    if len(args) == 0:
        args = (partial(), partial("PROPERTY", "STRING", "name"), partial())
    return args


def arguments(*args: Partial) -> tuple[Partial, ...]:
    """tuple[Partial, ...] factory"""
    if len(args) == 0:
        args = (partial(), partial("VALUE", "FLOAT", "x"), partial())
    return args


def midimsg(
    typ: MidiMsgType = "CONTROLCHANGE",
    channel: int = 1,
    data1: str = "",
    data2: str = "",
) -> MidiMsg:
    """Midi Message factory"""
    return MidiMsg((typ, channel, data1, data2))


def midival(
    key: str = "x",
    typ: PartialType = "VALUE",
    scaleMin: int = 0,
    scaleMax: int = 127,
) -> MidiValue:
    """Midi Value factory"""
    return MidiValue((typ, key, scaleMin, scaleMax))


def localsrc(
    key: str = "x",
    typ: PartialType = "VALUE",
    conversion: ConversionType = "FLOAT",
    minRange: int = 0,
    maxRange: int = 1,
) -> LocalSrc:
    """Local Source factory"""
    return LocalSrc((typ, conversion, key, minRange, maxRange))


def localdst(
    key: str = "x",
    id: str = " ",
    typ: PartialType = "VALUE",
) -> LocalDst:
    """Local Destination factory"""
    return LocalDst((typ, key, id))


def osc(
    config: MsgConfig = None,
    triggs: tuple[Trigger, ...] = None,
    addrs: tuple[Partial, ...] = None,
    args: tuple[Partial, ...] = None,
) -> MessageOSC:
    """OSC message factory"""
    if config is None:
        config = msgconfig()
    if triggs is None:
        triggs = triggers()
    if addrs is None:
        addrs = address()
    if args is None:
        args = arguments()
    return MessageOSC(("osc", config, triggs, addrs, args))


def midi(
    config: MsgConfig = None,
    triggers: tuple[Trigger, ...] = None,
    message: MidiMsg = None,
    values: tuple[MidiValue, ...] = None,
) -> MessageMIDI:
    """MIDI Message Factory"""
    if config is None:
        config = msgconfig()
    if triggers is None:
        triggers = (trigger(),)
    if message is None:
        message = midimsg()
    if values is None:
        values = (midival(),)
    return MessageMIDI(("midi", config, triggers, message, values))


def local(
    enabled: bool = True,
    triggers: tuple[Trigger, ...] = None,
    source: LocalSrc = None,
    destination: LocalDst = None,
) -> MessageLOCAL:
    """LOCAL Message factory"""
    if triggers is None:
        triggers = (trigger(),)
    if source is None:
        source = localsrc()
    if destination is None:
        destination = localdst()
    return MessageLOCAL(("local", enabled, triggers, source, destination))
