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

Installs the script and verb list to `/usr/local/lib/razer-speaker-fix/`, enables `razer-speaker-fix.service`, adds a systemd sleep hook that re-runs it on resume, and installs the speaker protection filter (below).

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

## Status

Tested on one machine: Ubuntu 26.04, kernel 7.0, PipeWire 1.6. A manual run brings up both speakers. The second part of the sequence carries the 2025 model's tuning, which may not be exactly what Windows uses on the 2024 model. Use moderate volume the first time; if you hear distortion, reboot to clear the settings.

## Credits

- The first 2,000 verbs come from [Litesung/razer-blade-16-audio-fix](https://github.com/Litesung/razer-blade-16-audio-fix) (MIT, see `LICENSE.verbs`), which captured them from the Windows driver.
- The rest is converted from the Razer Blade 16 (2025) amp tables in the Linux kernel sound tree, `sound/hda/codecs/helpers/razer_blade16_2025.c` (GPL-2.0-or-later).
