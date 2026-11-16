#!/bin/sh
# Read-only collection of ACPI tables + embedded-controller RAM, for working out
# what drives the lid-closed breathing LED. Writes nothing to the firmware/EC.
# Usage: sudo sh collect_acpi.sh
set -e
cd "$(dirname "$0")"
OUT=acpi_dump
mkdir -p "$OUT"
LID=$(awk '{print $2}' /proc/acpi/button/lid/LID0/state)

# ACPI tables (DSDT, SSDTs, Razer's own RZR0 table)
for t in /sys/firmware/acpi/tables/DSDT /sys/firmware/acpi/tables/SSDT* /sys/firmware/acpi/tables/RZR0; do
    cat "$t" > "$OUT/$(basename "$t").aml"
done

# Decompiler (skipped quietly if apt is unavailable)
command -v iasl >/dev/null || apt-get install -y acpica-tools >/dev/null 2>&1 || echo "note: could not install acpica-tools"
if command -v iasl >/dev/null; then
    (cd "$OUT" && iasl -e SSDT*.aml RZR0.aml -d DSDT.aml >/dev/null 2>&1 || true
     for f in SSDT*.aml RZR0.aml; do iasl -d "$f" >/dev/null 2>&1 || true; done)
fi

# EC RAM: 24 snapshots, 0.25s apart, to catch bytes that move with the breathing
modprobe ec_sys 2>/dev/null || true
for ec in /sys/kernel/debug/ec/ec*; do
    [ -r "$ec/io" ] || continue
    n=$(basename "$ec")
    : > "$OUT/$n-lid-$LID.hex"
    i=0
    while [ $i -lt 24 ]; do
        od -An -v -tx1 -w256 "$ec/io" >> "$OUT/$n-lid-$LID.hex"
        sleep 0.25
        i=$((i + 1))
    done
done

chown -R "${SUDO_UID:-0}:${SUDO_GID:-0}" "$OUT"
echo "lid was: $LID"
ls "$OUT"
