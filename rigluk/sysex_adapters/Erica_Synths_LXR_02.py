# Erica Synths LXR-02 Drum Synthesizer Adaptation
from typing import List

def wrapSysex(data):
    return [0xf0, 0x00, 0x21, 0x1a, 0x02] + data + [0xf7]

def name():
    return "Erica Synths LXR-02"

def createDeviceDetectMessage(channel):
    return [0xf0, 0x7e, 0x7f, 0x06, 0x01, 0xF7]

def deviceDetectWaitMilliseconds():
    return 300

def generalMessageDelay():
    return 100

def needsChannelSpecificDetection():
    return False

def channelIfValidDeviceResponse(message):
    if len(message) >= 6 and message[0] == 0xf0 and message[1] == 0x7e:
        return 0
    return -1

def createEditBufferRequest(channel):
    return wrapSysex([0x01])

def isEditBufferDump(message):
    return len(message) > 5 and message[0] == 0xf0

def numberOfBanks():
    return 1

def numberOfPatchesPerBank():
    return 64

def patchName(message):
    return "LXR-02 Drum Preset"
