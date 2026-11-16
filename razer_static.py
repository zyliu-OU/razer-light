#!/usr/bin/env python3
"""Set Razer Blade keyboard backlight to a static color + brightness via hidraw.

Usage: sudo python3 razer_static.py [R G B] [brightness 0-100]
Default: 0 255 0, 100%
Uses the Razer Chroma 90-byte feature-report protocol (same as OpenRazer).
"""
import fcntl, glob, os, sys, time

VID, PID = "00001532", "000002B7"
TRANSACTION_ID = 0x1F  # newer Blade laptops

def _IOC(d, t, nr, size):
    return (d << 30) | (size << 16) | (ord(t) << 8) | nr

def HIDIOCSFEATURE(n): return _IOC(3, 'H', 0x06, n)
def HIDIOCGFEATURE(n): return _IOC(3, 'H', 0x07, n)

def build_report(cmd_class, cmd_id, args):
    r = bytearray(90)
    r[1] = TRANSACTION_ID
    r[5] = len(args)
    r[6] = cmd_class
    r[7] = cmd_id
    r[8:8 + len(args)] = bytes(args)
    crc = 0
    for b in r[2:88]:
        crc ^= b
    r[88] = crc
    return r

def send(fd, cmd_class, cmd_id, args):
    buf = bytearray(b"\x00") + build_report(cmd_class, cmd_id, args)  # report ID 0
    fcntl.ioctl(fd, HIDIOCSFEATURE(len(buf)), buf)
    time.sleep(0.05)
    resp = bytearray(91)
    fcntl.ioctl(fd, HIDIOCGFEATURE(len(resp)), resp)
    return resp[1:]  # strip report ID; resp[0] = status (0x02 = success)

def find_device():
    for d in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        ue = open(f"{d}/device/uevent").read()
        if f"HID_ID=0003:{VID}:{PID}" not in ue:
            continue
        path = "/dev/" + os.path.basename(d)
        try:
            fd = os.open(path, os.O_RDWR)
            resp = send(fd, 0x00, 0x81, [0, 0])  # get firmware version
            if resp[0] == 0x02:
                print(f"Using {path} (firmware v{resp[8]}.{resp[9]})")
                return fd
            os.close(fd)
        except OSError:
            pass
    sys.exit("No responding Razer Blade control interface found (run with sudo?)")

def main():
    a = [int(x) for x in sys.argv[1:]]
    r, g, b = a[0:3] if len(a) >= 3 else (0, 255, 0)
    pct = a[3] if len(a) >= 4 else 100
    for attempt in range(15):  # at boot the USB device may not be ready yet
        try:
            fd = find_device()
            break
        except SystemExit:
            if attempt == 14:
                raise
            time.sleep(2)
    # Static effect: extended matrix effect, VARSTORE=0x01, BACKLIGHT_LED=0x05, effect 0x01
    s = send(fd, 0x0F, 0x02, [0x01, 0x05, 0x01, 0x00, 0x00, 0x01, r, g, b])
    print("static color:", "OK" if s[0] == 0x02 else f"status 0x{s[0]:02x}")
    # Blade brightness: class 0x0E id 0x04, [0x01, 0-255]
    s = send(fd, 0x0E, 0x04, [0x01, round(pct * 255 / 100)])
    print("brightness:  ", "OK" if s[0] == 0x02 else f"status 0x{s[0]:02x}")
    # Lid logo: LED state on + static effect (not breathing), VARSTORE=0x01, LOGO_LED=0x04
    # The plain "on" is not enough when the lid is closed (clamshell), so send every
    # variant that could wake the logo: off->on toggle, no-store slot, brightness,
    # extended static effect, and the legacy 0xFF transaction id.
    global TRANSACTION_ID
    send(fd, 0x03, 0x00, [0x01, 0x04, 0x00])
    time.sleep(0.3)
    results = [
        send(fd, 0x03, 0x00, [0x01, 0x04, 0x01]),        # state on (stored)
        send(fd, 0x03, 0x02, [0x01, 0x04, 0x00]),        # effect static (stored)
        send(fd, 0x03, 0x00, [0x00, 0x04, 0x01]),        # state on (no-store)
        send(fd, 0x03, 0x03, [0x01, 0x04, 0xFF]),        # legacy brightness
        send(fd, 0x0F, 0x04, [0x01, 0x04, 0xFF]),        # extended brightness
        send(fd, 0x0F, 0x02, [0x01, 0x04, 0x01, 0x00, 0x00, 0x01, r, g, b]),  # extended static
    ]
    TRANSACTION_ID = 0xFF
    results += [
        send(fd, 0x03, 0x00, [0x01, 0x04, 0x01]),
        send(fd, 0x03, 0x02, [0x01, 0x04, 0x00]),
    ]
    TRANSACTION_ID = 0x1F
    print("logo:        ", " ".join("OK" if s[0] == 0x02 else f"0x{s[0]:02x}" for s in results))
    os.close(fd)

if __name__ == "__main__":
    main()
