# Functional Analysis — Atari ST ROM Cartridge v2

**Project:** cart_v02 · Rev 1.0 · 2026-11-08 · risapav  
**Analysis date:** 2026-11-19

---

## Summary

The schematic as committed contains **two critical bugs** that prevent the cartridge from functioning:

| # | Severity | Description |
|---|---|---|
| 1 | **Critical** | D1 and D2 diodes are reversed — chips are never enabled |
| 2 | **Critical** | Global label name collision — Atari A1–A3 shorted to /WE, /OE, /CE |

Both bugs must be corrected before the design can be assembled and tested.

---

## Bug 1 — Diodes D1 / D2 Reversed

### Intended circuit

The chip-enable wired-AND is supposed to pass `/ROM3` and `/ROM4` through diodes to a common `/CE` node with a pull-up to +5 V:

```
/ROM3 ──|>|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|>|── D1 ──┴── /CE (U1 pin 22, U2 pin 22)
```

For this to work:
- Cathode of each diode connects to the signal (`/ROM3`, `/ROM4`)
- Anode connects to the shared `/CE` node

When a signal goes LOW, current flows from `/CE` node through the diode to the pulled-low signal, pulling `/CE` LOW. When both signals are HIGH, R4 holds `/CE` HIGH. This is a standard passive wired-AND with diodes.

### Actual placement in schematic

In `cart_v02.kicad_sch`, D1 and D2 are placed at rotation = 0°. For KiCad's `Device:D`:
- Pin 2 = Anode (A) is on the **right** (x = +3.81 mm offset)
- Pin 1 = Cathode (K) is on the **left** (x = −3.81 mm offset)

The global label `/ROM4` connects to the **right** side (Anode) of D1.  
The `ROM_CE` net connects to the **left** side (Cathode) of D1.

This means current can only flow from `/ROM4` into the CE node — the diode is reverse-biased when `/ROM4` is LOW. The CE node is never pulled LOW regardless of the signal states.

### Effect

With reversed diodes:
- `/CE` is permanently held HIGH by R4
- Both Flash chips are permanently deselected
- The cartridge is **completely unreadable** — the ST bus reads $FFFF on every access

### Fix

Rotate D1 and D2 by 180° in the schematic, or redraw with Cathode on the signal side:

```
/ROM3 ──|<|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|<|── D1 ──┴── /CE
```

(Bar of diode symbol toward the signal, triangle toward the CE node.)

---

## Bug 2 — Global Label Name Collision

### How KiCad global labels work

A KiCad **global label** with a given name forms a single electrical net spanning the entire schematic, regardless of where the label is placed. Two global labels with the same name are **always connected**, even if placed on different pages or in different areas of the schematic.

**Local wires** only connect components that are physically drawn with a wire between them on the schematic canvas.

### The collision

The W29C040-90B chip symbol (U1, U2) exposes its address pins with KiCad global labels named `A1`, `A2`, `A3`, …, `A15`, `A16`, `A17`, `A18`.

The Atari ST cartridge connector symbol (J1) also exposes its address lines with global labels named `A1`, `A2`, `A3`, …, `A15`.

Because both use **global** labels with the same names, every chip address pin is electrically joined to the corresponding ST bus address line. This is correct for A1–A14 (the lower address bits), but it also creates unintended connections for pins that have different meanings on the chip vs. the schematic intent:

| Global label name | Atari ST bus meaning | W29C040 pin connected | Consequence |
|---|---|---|---|
| `A1` | Address bit 1 | Pin 31 = /WE | /WE driven by A1 (not tied to +5 V) |
| `A2` | Address bit 2 | Pin 24 = /OE | /OE driven by A2 (not GND) |
| `A3` | Address bit 3 | Pin 22 = /CE | /CE driven by A3 (bypasses wired-AND) |
| `A4` | Address bit 4 | Pin 1 = VPP/A18 | A18 (bank) driven by A4 |
| `A5` | Address bit 5 | Pin 30 = A17 | A17 (bank) driven by A5 |
| `A6` | Address bit 6 | Pin 2 = A16 | A16 (bank) driven by A6 |
| `/ROM4` | ROM4 chip select | Pin 3 = A6 | Chip A6 driven by /ROM4 instead of ST A6 |
| `ROM_CE` | CE node | Pin 2 = A2 on chip | A2 driven from CE wired-AND node |
| `~{UDS}` | Upper Data Strobe | Pin mapped to A0–A1 area | Address bits corrupted |
| `~{LDS}` | Lower Data Strobe | Same | Address bits corrupted |

The result is that the entire address decode logic and write-protect circuit is fundamentally incorrect — the chips would receive corrupted addresses, /WE would float/toggle with A1, and /CE would be driven directly from A3 rather than the wired-AND output.

### Fix

Replace the global labels on the **chip side** with **local labels** (net ties that do not propagate beyond their local wire segment), or rename the chip's address global labels to avoid collision. For example:

- Chip pins A0–A14 → connect directly by wire to J1 bus labels (no independent global label needed)
- Chip /WE → wire to +5 V directly (or use a power symbol `+5V`)
- Chip /OE → wire to GND directly
- Chip /CE → wire to the `ROM_CE` wired-AND node using a **local** net or a uniquely named global (e.g., `ROM_CE`)
- Chip A15 → wire to `/ROM4` using a uniquely named global label (e.g., `/ROM4` is fine as long as J1 does not also export a signal named `/ROM4`)
- Chip A16–A18 → wire from DIP switch SW1 outputs using local labels

---

## Correct Circuit Description (after fixes)

### Address bus

```
ST A1  → Chip A0   (pin  4)
ST A2  → Chip A1   (pin  3)   note: ST does not expose A0; byte select via /UDS, /LDS
ST A3  → Chip A2   (pin 25)
...
ST A15 → Chip A14  (pin 29)
/ROM4  → Chip A15  (pin 30)   selects upper/lower 128 KB half
SW1-1  → Chip A16  (pin  2)   ┐
SW1-2  → Chip A17  (pin 30)   ├ bank select (3-bit DIP)
SW1-3  → Chip A18  (pin  1)   ┘
```

### Control signals

```
/ROM3, /ROM4 → Diodes D2, D1 (Cathodes to signals) → ROM_CE node → /CE (pin 22)
ROM_CE node  → R4 (10 kΩ) → +5V
/OE          → GND  (output always enabled when /CE is asserted)
/WE          → +5V  (write permanently disabled)
```

### Data bus

```
U1 D0–D7  → ST bus D0–D7   (low byte)
U2 D0–D7  → ST bus D8–D15  (high byte)
```

---

## Memory Map — 2× W29C040-90B (1 MB total)

Each W29C040 is 512 K × 8. Two chips in parallel = 512 K × 16-bit words = 1 MB byte-addressable.  
3-bit DIP switch provides 8 banks × 128 KB = 1 MB total capacity.

### ST address window vs. chip address

| /ROM4 | ST bus region | Chip A15 | Description |
|---|---|---|---|
| LOW  | `$FA0000`–`$FAFFFF` | 0 | lower 128 KB of selected bank |
| HIGH | `$FB0000`–`$FBFFFF` | 1 | upper 128 KB of selected bank |

Both chips are enabled only when /ROM3 AND /ROM4 are both LOW simultaneously.

### Bank map (DIP switch SW1)

SW1 closed = 0 (pulled to GND) · SW1 open = 1 (pulled to +5 V via 10 kΩ)

| SW1-3 (A18) | SW1-2 (A17) | SW1-1 (A16) | Bank | Chip byte offset | ST window |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | `0x000000`–`0x01FFFF` | `$FA0000`–`$FBFFFF` |
| 0 | 0 | 1 | 1 | `0x020000`–`0x03FFFF` | `$FA0000`–`$FBFFFF` |
| 0 | 1 | 0 | 2 | `0x040000`–`0x05FFFF` | `$FA0000`–`$FBFFFF` |
| 0 | 1 | 1 | 3 | `0x060000`–`0x07FFFF` | `$FA0000`–`$FBFFFF` |
| 1 | 0 | 0 | 4 | `0x080000`–`0x09FFFF` | `$FA0000`–`$FBFFFF` |
| 1 | 0 | 1 | 5 | `0x0A0000`–`0x0BFFFF` | `$FA0000`–`$FBFFFF` |
| 1 | 1 | 0 | 6 | `0x0C0000`–`0x0DFFFF` | `$FA0000`–`$FBFFFF` |
| 1 | 1 | 1 | 7 | `0x0E0000`–`0x0FFFFF` | `$FA0000`–`$FBFFFF` |

### Chip address formula

```
chip_addr = (bank × 0x020000) | (ROM4_bit × 0x008000) | ST_word_offset
```

where `ST_word_offset` = (ST_byte_addr − `$FA0000`) >> 1  (the 68000 shifts A1 as chip A0).

### ROM binary file layout

Each chip is programmed with one byte of every 16-bit word from the ROM image:

| File | Chip | Contains |
|---|---|---|
| `rom_lo.bin` | U1 (D0–D7) | even bytes of ROM image (byte 0, 2, 4, …) |
| `rom_hi.bin` | U2 (D8–D15) | odd bytes of ROM image (byte 1, 3, 5, …) |

For a banked image, place bank N at chip offset `N × 0x020000` in each file.

---

## Memory Map — 2× TC57H1000AD-85 (256 KB total)

The Toshiba TC57H1000AD-85 is a 128 K × 8 SRAM, DIP-32, pin-compatible with the W29C040 on most pins:

| Pin | W29C040 | TC57H1000AD-85 |
|---|---|---|
| 1 | A18 | VPP (must be +5 V) |
| 2–29 | A0–A14, D0–D7, /CE, /OE, /WE, GND | identical |
| 30 | A17 | NC (no connection) |
| 31 | /PGM (W29C040: NC) | /WE (write enable) |
| 32 | VCC | VCC |

### DIP switch settings for TC57H1000AD-85

| Switch | Signal | Required setting | Reason |
|---|---|---|---|
| SW1-3 | Pin 1 = VPP | **OPEN** (= +5 V via R3) | VPP must be +5 V; must never be pulled LOW |
| SW1-2 | Pin 30 = NC | either (no effect) | pin 30 is not connected on TC57H1000 |
| SW1-1 | Pin 2 = A16 | bank select 0 or 1 | selects which 128 KB half of chip |

**SW1-3 must remain OPEN at all times.** Closing SW1-3 would pull VPP to GND, potentially damaging the chip or causing undefined behavior.

### Bank map (TC57H1000AD-85)

The TC57H1000 has 17 address bits (A0–A16 = 128 K locations × 8 bit = 128 KB).  
With SW1-1 as the only effective bank switch, there are 2 usable banks:

| SW1-1 (A16) | Bank | Chip byte offset | ST window |
|---|---|---|---|
| 0 (closed) | 0 | `0x000000`–`0x01FFFF` | `$FA0000`–`$FBFFFF` |
| 1 (open)   | 1 | `0x010000`–`0x01FFFF` | `$FA0000`–`$FBFFFF` |

> Total accessible ROM = 2 × 128 KB = **256 KB** (vs. 1 MB for W29C040).

### Note on /WE

The TC57H1000 has /WE on pin 31, which corresponds to W29C040's /PGM (unused/NC). The board routes /WE only to W29C040 pin 31 — however, since /WE on this board is permanently tied to +5 V via the design intent, the TC57H1000's pin 31 would also receive +5 V through R3 if connected, keeping it write-protected.

---

## Checklist for Rev 1.1

- [ ] Rotate D1 and D2 by 180° — Cathode toward `/ROM3`/`/ROM4`, Anode toward `ROM_CE` node
- [ ] Replace W29C040 address pin global labels (A1–A3, ROM_CE, /ROM4 at chip side) with direct wires or locally-scoped nets to prevent collision with J1 connector globals
- [ ] Tie /WE (chip pin 31) directly to `+5V` power symbol — no global label needed
- [ ] Tie /OE (chip pin 24) directly to `GND` symbol — no global label needed  
- [ ] Connect /CE (chip pin 22) via local wire to `ROM_CE` node only
- [ ] Re-run ERC after fixes; expect zero functional errors
