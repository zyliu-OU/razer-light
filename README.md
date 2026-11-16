# razer-light

Keyboard backlight control for the Razer Blade 16 (2024, RZ09-0510, USB `1532:02B7`) on Linux, without OpenRazer. Talks to the keyboard directly over hidraw using the Razer Chroma 90-byte feature-report protocol.

## Usage

```sh
sudo python3 razer_static.py [R G B] [brightness 0-100]   # default: 0 255 0, 100%
```

Sets the keyboard to a static color and brightness, and turns the lid logo on with a static effect.

## Apply on every boot and after suspend

```sh
sudo sh install.sh
```

Installs the script to `/usr/local/bin`, enables `razer-keyboard-color.service`, and adds a systemd sleep hook. The color is hard-coded to green at 100% in the service file and in `install.sh`; edit both to change it.

## Lid-closed breathing light

- `probe_lid_light.py` — interactive probe that tries each HID command against the light that breathes when the lid is closed. Result in `probe.log`: nothing over USB HID affects it, so it is driven by the embedded controller.
- `collect_acpi.sh` — read-only dump of the ACPI tables and EC RAM for investigating that.
