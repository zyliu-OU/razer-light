#!/usr/bin/env python3
"""Interactive probe: find which command (if any) stops the lid-closed breathing light.

Run with the lid CLOSED, from a terminal on the external monitor:
    sudo python3 probe_lid_light.py
Watch the light and answer y/n. Everything is logged to probe.log next to this file.
"""
import os, sys, time
import razer_static as rz

LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "probe.log"), "w")

def log(msg):
    print(msg)
    LOG.write(msg + "\n")
    LOG.flush()

def ask(q):
    while True:
        a = input(f"\n>>> {q} [y/n] ").strip().lower()
        if a in ("y", "n"):
            LOG.write(f"Q: {q} -> {a}\n")
            LOG.flush()
            return a == "y"

def tx(fd, cls, cid, args, label=""):
    s = rz.send(fd, cls, cid, args)
    log(f"  {label:<34} {cls:02x}/{cid:02x} {bytes(args).hex()} -> status {s[0]:02x} args {bytes(s[8:14]).hex()}")
    return s

def dump(fd):
    log("-- read-back of every LED id (state / effect / brightness) --")
    for led in range(0x00, 0x21):
        vals = []
        for cid in (0x80, 0x82, 0x83):
            s = rz.send(fd, 0x03, cid, [0x01, led, 0x00])
            vals.append(f"{s[10]:02x}" if s[0] == 0x02 else f"err{s[0]:02x}")
        log(f"  led 0x{led:02x}: state={vals[0]} effect={vals[1]} brightness={vals[2]}")
    s = rz.send(fd, 0x00, 0x84, [0, 0])
    log(f"  device mode: status {s[0]:02x} mode {s[8]:02x} {s[9]:02x}")

def logo_static(fd):
    for vs in (0x01, 0x00):
        tx(fd, 0x03, 0x00, [vs, 0x04, 0x01], f"logo state on (vs{vs})")
        tx(fd, 0x03, 0x02, [vs, 0x04, 0x00], f"logo effect static (vs{vs})")
        tx(fd, 0x03, 0x03, [vs, 0x04, 0xFF], f"logo brightness max (vs{vs})")

def main():
    lid = open("/proc/acpi/button/lid/LID0/state").read().split()[-1] if os.path.exists("/proc/acpi/button/lid/LID0/state") else "?"
    log(f"lid: {lid}")
    fd = rz.find_device()
    dump(fd)

    is_logo = ask("Is the breathing light the Razer logo on the lid? (n = some other LED, e.g. front edge / power)")

    log("\n== Test 1: logo OFF ==")
    for vs in (0x01, 0x00):
        tx(fd, 0x03, 0x00, [vs, 0x04, 0x00], f"logo state off (vs{vs})")
    time.sleep(1)
    off_works = ask("Did the breathing light go fully OFF and stay off (watch ~5s)?")

    log("\n== Test 2: logo ON + static ==")
    logo_static(fd)
    time.sleep(1)
    if ask("Is the light now solid (NOT breathing)?"):
        log("RESULT: plain logo on+static works when sent while lid is closed")
        return finish(fd)

    log("\n== Test 3: driver mode (firmware stops running its own effects) ==")
    tx(fd, 0x00, 0x04, [0x03, 0x00], "device mode = driver")
    logo_static(fd)
    time.sleep(1)
    if ask("Is the light now solid (NOT breathing)?"):
        log("RESULT: driver mode + logo static works")
        return finish(fd)
    tx(fd, 0x00, 0x04, [0x00, 0x00], "device mode = normal (revert)")

    log("\n== Test 4: static effect on every other LED id ==")
    for led in list(range(0x00, 0x04)) + list(range(0x06, 0x21)):
        rz.send(fd, 0x03, 0x00, [0x01, led, 0x01])
        rz.send(fd, 0x03, 0x02, [0x01, led, 0x00])
    log("  sent state-on + effect-static to led 0x00-0x20 (except 4,5)")
    time.sleep(1)
    if ask("Is the light now solid (NOT breathing)?"):
        log("RESULT: one of the other LED ids controls it")
        return finish(fd)

    log("\n== Test 5: does the logo react to effects at all? (blink effect) ==")
    tx(fd, 0x03, 0x02, [0x01, 0x04, 0x01], "logo effect blinking")
    time.sleep(2)
    ask("Did the light change to fast blinking?")
    tx(fd, 0x03, 0x02, [0x01, 0x04, 0x00], "logo effect static")

    if off_works:
        log("\nRESULT: only OFF stops the breathing")
        if ask("Leave the light OFF now (instead of breathing)?"):
            for vs in (0x01, 0x00):
                tx(fd, 0x03, 0x00, [vs, 0x04, 0x00], f"logo state off (vs{vs})")
    else:
        log(f"\nRESULT: nothing over USB HID affected it (is_logo={is_logo}) -> EC-controlled")
    finish(fd)

def finish(fd):
    dump(fd)
    os.close(fd)
    log("done - log saved to probe.log")

if __name__ == "__main__":
    main()
