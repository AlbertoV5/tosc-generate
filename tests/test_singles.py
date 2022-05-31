import tosclib as tosc
from tosclib.tosc import Partial, Value, Property, PropertyType
from tosclib.tosc import Controls

def test_singles():

    root = tosc.createTemplate()
    element = tosc.ElementTOSC(root[0])

    element.createValue(Value())

    element.setValue(Value("touch", "1", "1", "true", "1"))

    element.createOSC(
        message=tosc.OSC(
            "0",
            "0",
            "0",
            "1",
            "00001",
            [tosc.Trigger()],
            [tosc.Partial(), tosc.Partial()],
            [Partial(), Partial()],
        )
    )

    element.setColor(1, 0, 0, 1)
    element.setFrame(0, 0, 1, 1)

    element.showProperty("frame")

    print(tosc.PropertyKeys.COLOR)
    print(tosc.Controls.BOX.BACKGROUND)

if __name__ == "__main__":
    test_singles()
