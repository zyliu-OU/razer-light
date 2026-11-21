# razer-light

Small Linux scripts for the Razer Blade 16 (2024, RZ09-0510). They cover two things Razer only supports on Windows:

- **Keyboard and lid-logo lighting** — set a static color and brightness, without OpenRazer.
- **Internal speakers** — wake the speaker amplifier, which is silent on Linux out of the box.

Everything is plain Python 3 and shell, with no extra packages. Tested on one machine: Ubuntu 26.04, kernel 7.0.

## Quick start

```sh
git clone https://github.com/zyliu-OU/razer-light.git
cd razer-light

# Keyboard: green at 100%, lid logo at 100%
sudo python3 razer_static.py

# Speakers: turn the amplifier on
sudo python3 speaker-fix/razer_speaker_fix.py
```

Both settings are lost on reboot and suspend. To apply them automatically, run the installers below.

## Keyboard and logo lighting

```sh
sudo python3 razer_static.py [R G B] [brightness 0-100] [logo brightness 0-100]
```

| Example | Result |
| --- | --- |
| `sudo python3 razer_static.py` | Green keyboard at 100%, logo at 100% |
| `sudo python3 razer_static.py 255 0 0 50` | Red keyboard at 50%, logo at 100% |
| `sudo python3 razer_static.py 0 0 255 80 0` | Blue keyboard at 80%, logo off |

The script talks to the keyboard (USB `1532:02B7`) directly over hidraw, using the Razer Chroma 90-byte feature-report protocol.

### Apply on every boot and after suspend

```sh
sudo sh install.sh
```

This installs the script to `/usr/local/bin`, enables `razer-keyboard-color.service`, and adds a systemd sleep hook. The color is hard-coded to green at 100% in `razer-keyboard-color.service` and in `install.sh`; edit both to change it.

## Internal speakers

```sh
sudo python3 speaker-fix/razer_speaker_fix.py     # try it once
sudo speaker-fix/install.sh                       # apply on every boot and resume
sudo speaker-fix/install.sh --uninstall           # remove it
```

The speakers sit behind a smart amplifier that Windows programs on every boot. The script sends the same start-up sequence to the Realtek ALC298 codec. Nothing is written to firmware; a reboot clears it. The installer also adds a speaker protection filter (bass cut below 80 Hz, 3 dB less maximum level) and a volume curve that spreads the audible range over the whole slider. See [speaker-fix/README.md](speaker-fix/README.md) for details.

## What each script does

### Lighting

| File | What it does |
| --- | --- |
| `razer_static.py` | Sets the keyboard to a static color and brightness, and sets the lid logo on, dimmed, or off. |
| `install.sh` | Installs `razer_static.py`, the boot service, and the sleep hook. |
| `razer-keyboard-color.service` | systemd unit that runs `razer_static.py` at boot. |

### Speakers (`speaker-fix/`)

| File | What it does |
| --- | --- |
| `razer_speaker_fix.py` | Finds the ALC298 codec, sends it the amplifier start-up sequence, and sets its hardware gain to 0 dB. |
| `razer_blade16_alc298_verbs.txt` | The sequence itself: 2,000 codec coefficient writes, one per line. |
| `install.sh` | Installs the script, verb list, boot service, resume hook, protection filter, and volume curve; `--uninstall` removes them. |
| `razer-speaker-fix.service` | systemd unit that runs the fix at boot. |
| `sleep-hook` | Re-runs the fix after waking from suspend or hibernate. |
| `51-razer-speaker-protect.conf` | PipeWire/WirePlumber rule that protects the speakers: cuts bass below 80 Hz and lowers the maximum level by 3 dB. |
| `52-razer-speaker-volume.conf` | Volume curve for the speakers: 0% (and mute) is silent, 1–20% is −30 dB to −20 dB, 20–100% is −20 dB to 0 dB. |
| `61-razer-speaker-power.rules` | udev rule that keeps the codec powered on, so it doesn't lose the amp settings when the speakers are idle. |
| `razer-speaker-volume-sync.lua` | WirePlumber script that applies the saved volume to that curve when the speaker output starts. |

### Lid-closed breathing light (investigation only)

| File | What it does |
| --- | --- |
| `probe_lid_light.py` | Interactive probe that tries each HID command against the light that breathes when the lid is closed. |
| `probe.log` | Result of that probe: nothing over USB HID affects the light, so the embedded controller drives it. |
| `collect_acpi.sh` | Read-only dump of the ACPI tables and embedded-controller RAM into `acpi_dump/`, for investigating that light. |

## Credits

The speaker verb sequence comes from [Litesung/razer-blade-16-audio-fix](https://github.com/Litesung/razer-blade-16-audio-fix) (MIT, see `speaker-fix/LICENSE.verbs`).
