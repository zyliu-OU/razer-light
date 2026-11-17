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
import subprocess
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


def set_hw_volumes(card):
    """Put the codec's Speaker and Headphone gain at 0 dB.

    With 52-razer-speaker-volume.conf installed, PipeWire no longer drives these
    controls and does all volume in software, so they must sit at 0 dB or the
    maximum is lower. Without that file PipeWire drives them itself and
    overwrites this, so it is harmless either way.
    """
    for ctl in ("Speaker", "Headphone"):
        try:
            subprocess.run(["amixer", "-q", "-c", card, "sset", ctl, "0dB"],
                           check=False, timeout=5)
        except (OSError, subprocess.SubprocessError) as e:
            print(f"could not set {ctl} volume: {e}", file=sys.stderr)


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
    set_hw_volumes(dev[len("/dev/snd/hwC"):].split("D")[0])


if __name__ == "__main__":
    main()
