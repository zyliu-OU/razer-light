# speaker-fix

Turns on the internal speakers of the Razer Blade 16 (2024, RZ09-0510, Realtek ALC298, PCI subsystem `1a58:300a`) on Linux.

## The problem

Everything looks fine in software (the "Speaker" output exists, nothing is muted), but the speakers are silent. The speakers sit behind a smart amplifier that has to be programmed through the codec's vendor coefficient registers (NID `0x20`). Windows does this on every boot; the Linux kernel has no quirk for this model, so the amp stays off.

## The fix

`razer_speaker_fix.py` sends the amp's start-up sequence (2,000 coefficient writes, listed in `razer_blade16_alc298_verbs.txt`) to the codec's hwdep device, the same thing `hda-verb` from `alsa-tools` does, without needing that package.

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

Installs the script and verb list to `/usr/local/lib/razer-speaker-fix/`, enables `razer-speaker-fix.service`, and adds a systemd sleep hook that re-runs it on resume.

Uninstall:

```sh
sudo ./install.sh --uninstall
```

## Status

Tested on one machine: Ubuntu 26.04, kernel 7.0, PipeWire 1.6. A manual run brings the speakers up. Use moderate volume the first time; if you hear distortion, reboot to clear the settings.

## Credits

The verb sequence comes from [Litesung/razer-blade-16-audio-fix](https://github.com/Litesung/razer-blade-16-audio-fix) (MIT, see `LICENSE.verbs`), which derived it from the Windows driver.
