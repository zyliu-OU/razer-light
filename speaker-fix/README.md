# speaker-fix

Turns on the internal speakers of the Razer Blade 16 (2024, RZ09-0510, Realtek ALC298, PCI subsystem `1a58:300a`) on Linux.

## The problem

Everything looks fine in software (the "Speaker" output exists, nothing is muted), but the speakers are silent. The speakers sit behind a smart amplifier that has to be programmed through the codec's vendor coefficient registers (NID `0x20`). Windows does this on every boot; the Linux kernel has no quirk for this model, so the amp stays off.

## The fix

`razer_speaker_fix.py` sends the amp's start-up sequence (5,645 codec verbs, listed in `razer_blade16_alc298_verbs.txt`) to the codec's hwdep device, the same thing `hda-verb` from `alsa-tools` does, without needing that package.

The sequence has two parts:

1. The 2024 Windows driver trace from Litesung's project (2,000 verbs). It is cut off partway through programming the amp's DSP, right where the second channel's settings begin. With only this part, just the left speaker plays.
2. The rest of the DSP programming, the amp wake, and pin 0x14 switched on, taken from the Linux kernel's Razer Blade 16 (2025) fixup (`sound/hda/codecs/helpers/razer_blade16_2025.c`). The 2025 model uses the same amp: 90 of the 106 distinct writes in the 2024 trace appear in the 2025 table, and the two sequences match at the point where the trace stops. With both parts, both speakers play.

Try it once:

```sh
sudo python3 razer_speaker_fix.py
speaker-test -D pipewire -c 2 -t sine -f 440 -l 1
```

The writes live in volatile codec registers. They are lost on reboot and suspend, and nothing is written to firmware.

## Apply on every boot and after suspend

```sh
sudo ./install.sh
```

Installs the script and verb list to `/usr/local/lib/razer-speaker-fix/`, enables `razer-speaker-fix.service`, adds a systemd sleep hook that re-runs it on resume, and installs the speaker protection filter and the volume curve (below).

Uninstall:

```sh
sudo ./install.sh --uninstall
```

## Speaker protection

On Windows, Razer's audio software filters and limits what reaches the speakers. On Linux the signal goes to the amplifier raw, so `51-razer-speaker-protect.conf` adds a small filter to the PipeWire speaker output:

- a high-pass at 80 Hz, which removes bass the speakers cannot reproduce but that still drives the cones
- a 3 dB cut in maximum level

It applies to the internal speakers only; headphones, HDMI and Bluetooth are separate outputs. `install.sh` copies it to `/etc/wireplumber/wireplumber.conf.d/`. To activate it, or after editing the cut-off frequency or gain in the file:

```sh
systemctl --user restart wireplumber
```

To install it without the rest, copy the file to `~/.config/wireplumber/wireplumber.conf.d/` and run the same command.

This is not a limiter and does not replace the amplifier's own protection; it lowers the stress on the speakers. Needs PipeWire 1.4 or newer.

## Volume curve

The amplifier mutes any signal quieter than about −40 dBFS. With PipeWire's normal volume curve, the bottom half of the slider falls under that level: below 50% there is no sound, and everything audible is squeezed into 50–100%.

`52-razer-speaker-volume.conf` spreads a 20 dB range evenly over the slider, 2 dB per 10%:

| Slider | 0% | 20% | 40% | 50% | 60% | 80% | 100% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PipeWire default | silent | −42 dB | −24 dB | −18 dB | −13 dB | −5.8 dB | 0 dB |
| This file | −20 dB | −16 dB | −12 dB | −10 dB | −8 dB | −4 dB | 0 dB |

The maximum is unchanged. 0% is not silent; use mute for silence. How it works:

- PipeWire stops using the codec's hardware volume controls for this card (`api.alsa.soft-mixer`). `razer_speaker_fix.py` sets the `Speaker` and `Headphone` controls to 0 dB at boot and after resume.
- On the speaker output, the volume slider drives a control in a small filter graph that computes the gain (`input.volumes`), instead of being applied directly (`channelmix.lock-volumes`).
- PipeWire starts that control at the bottom of the curve until the volume next changes, so `razer-speaker-volume-sync.lua` (a WirePlumber script) re-applies the saved volume the first time the speaker output plays.

Headphones and HDMI keep the normal curve. They now use software volume, which sounds the same as before at every slider position.

To change the range, edit `Mult` and `Add` in the `db` node (the formula is in the file's comments), then restart WirePlumber.

If the speakers are much quieter than this table suggests, check `amixer -c 1 sget Speaker`. It must read 0 dB. A lower level saved earlier in `/var/lib/alsa/asound.state` is restored at boot. Re-run `sudo ./install.sh` so the installed script resets it, and run `sudo alsactl store` to save the 0 dB level.

## Status

Tested on one machine: Ubuntu 26.04, kernel 7.0, PipeWire 1.6. A manual run brings up both speakers. The second part of the sequence carries the 2025 model's tuning, which may not be exactly what Windows uses on the 2024 model. Use moderate volume the first time; if you hear distortion, reboot to clear the settings.

## Credits

- The first 2,000 verbs come from [Litesung/razer-blade-16-audio-fix](https://github.com/Litesung/razer-blade-16-audio-fix) (MIT, see `LICENSE.verbs`), which captured them from the Windows driver.
- The rest is converted from the Razer Blade 16 (2025) amp tables in the Linux kernel sound tree, `sound/hda/codecs/helpers/razer_blade16_2025.c` (GPL-2.0-or-later).
