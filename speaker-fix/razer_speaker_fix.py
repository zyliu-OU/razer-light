#!/usr/bin/env python3
"""Wake the internal speaker amplifier on a Razer Blade 16 (ALC298).

Sends a list of HD-audio codec verbs (one "nid verb param" per line, hex)
to the codec's hwdep device, the same thing `hda-verb` does.
The writes are runtime-only: they are lost on reboot / suspend.
"""
import fcntl
import glob
import os
import struct
import sys

HDA_IOCTL_VERB_WRITE = 0xC0084811  # _IOWR('H', 0x11, struct hda_verb_ioctl)


def find_alc298():
    for path in sorted(glob.glob("/proc/asound/card*/codec#*")):
        with open(path) as f:
            if "ALC298" in f.readline():
                card = path.split("/")[3][len("card"):]
                codec = path.rsplit("#", 1)[1]
                return f"/dev/snd/hwC{card}D{codec}"
    return None


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    verbs_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        here, "razer_blade16_alc298_verbs.txt")
    dev = find_alc298()
    if not dev:
        sys.exit("ALC298 codec not found")

    verbs = []
    with open(verbs_path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                nid, verb, param = (int(x, 16) for x in line.split())
                verbs.append((nid << 24) | (verb << 8) | param)

    fd = os.open(dev, os.O_RDWR)
    try:
        for v in verbs:
            fcntl.ioctl(fd, HDA_IOCTL_VERB_WRITE, struct.pack("II", v, 0))
    finally:
        os.close(fd)
    print(f"sent {len(verbs)} verbs to {dev}")


if __name__ == "__main__":
    main()
