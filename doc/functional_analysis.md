# Functional Analysis — Atari ST ROM Cartridge v2

**Project:** cart_v02 · Rev 1.0 · 2026-11-08 · risapav  
**Analysis date:** 2026-11-19 (updated after U1/U2 reference swap)

---

## Status: PASS — no functional errors found

The previously identified bugs (reversed diodes, global label name collision) have been corrected.  
The schematic is functionally correct. All connections verified against the W29C040-90B datasheet and
Atari ST cartridge port specification.

---

## Verified Fixes

### Fix 1 — Diodes D1 / D2 orientation

**Original bug:** D1 and D2 were placed at rotation 0°, connecting Anode to the /ROM4 and /ROM3 signals respectively. With forward bias blocked, the ROM_CE node was permanently HIGH → chips never enabled.

**Correction:** D1 and D2 are now at rotation 180°:

| Diode | Cathode (K) | Anode (A) |
|---|---|---|
| D1 | `ST_~{ROM4}` signal (x = 81.28) | ROM_CE node (x = 73.66) |
| D2 | `ST_~{ROM3}` signal (x = 81.28) | ROM_CE node (x = 69.85 junction) |

**Correct circuit:**

```
/ROM3 ──|<|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|<|── D1 ──┴── ROM_CE → /CE (U1 pin 22, U2 pin 22)
```

`|<|` = Cathode on signal side, Anode on ROM_CE side.

When a signal goes LOW, current flows from ROM_CE (Anode, pulled HIGH by R4) through the diode to the signal (Cathode, LOW). ROM_CE is pulled LOW → chips enabled. When both signals are HIGH, R4 keeps ROM_CE HIGH → chips deselected. ✓

### Fix 2 — Net label naming

**Original bug:** Address pins on the chip symbols used KiCad global labels with names `A1`, `A2`, `A3`, matching the same-named global labels on the J1 connector. This shorted ST address lines A1–A3 directly to chip /WE, /OE, /CE.

**Correction:** All nets now use KiCad **local labels** with descriptive prefixes:
- `ST_A1` … `ST_A15` — Atari ST address bus lines
- `ST_D0` … `ST_D15` — Atari ST data bus lines
- `ST_~{ROM3}`, `ST_~{ROM4}` — chip select signals
- `ST_~{UDS}`, `ST_~{LDS}` — byte strobe signals
- `B_SW1`, `B_SW2`, `B_SW3` — DIP switch bank select outputs
- `ROM_CE` — wired-AND output to both chips' /CE pins

Local labels are sheet-local in KiCad and cannot inadvertently collide with other global nets. ✓

---

## Full Connection Verification

### U1 — Low byte chip (D0–D7, /LDS)

U1 placed at schematic position (96.52, 149.86).

| Chip pin | Signal | Pin name |
|---|---|---|
| Pin 12 (A0)  | `ST_A1`  | ✓ |
| Pin 11 (A1)  | `ST_A2`  | ✓ |
| Pin 10 (A2)  | `ST_A3`  | ✓ |
| Pin 9 (A3)   | `ST_A4`  | ✓ |
| Pin 8 (A4)   | `ST_A5`  | ✓ |
| Pin 7 (A5)   | `ST_A6`  | ✓ |
| Pin 6 (A6)   | `ST_A7`  | ✓ |
| Pin 5 (A7)   | `ST_A8`  | ✓ |
| Pin 27 (A8)  | `ST_A9`  | ✓ |
| Pin 26 (A9)  | `ST_A10` | ✓ |
| Pin 23 (A10) | `ST_A11` | ✓ |
| Pin 25 (A11) | `ST_A12` | ✓ |
| Pin 4 (A12)  | `ST_A13` | ✓ |
| Pin 28 (A13) | `ST_A14` | ✓ |
| Pin 29 (A14) | `ST_A15` | ✓ |
| Pin 3 (A15)  | `ST_~{ROM4}` | ✓ — half-bank select |
| Pin 2 (A16)  | `B_SW1`  | ✓ |
| Pin 30 (A17) | `B_SW2`  | ✓ |
| Pin 1 (A18)  | `B_SW3`  | ✓ |
| Pin 22 (/CE) | `ROM_CE` | ✓ — wired-AND output |
| Pin 24 (/OE) | `ST_~{LDS}` | ✓ — low byte strobe |
| Pin 31 (/WE) | +5V (via #PWR09) | ✓ — write protect |
| Pin 32 (VCC) | +5V | ✓ |
| Pin 16 (GND) | GND | ✓ |
| Pins 13–21 (D0–D7) | `ST_D0`–`ST_D7` | ✓ |

### U2 — High byte chip (D8–D15, /UDS)

U2 placed at schematic position (175.26, 151.13). Same address/control wiring as U1 (verified pin-by-pin), with two differences:

| Chip pin | Signal | Note |
|---|---|---|
| Pin 24 (/OE) | `ST_~{UDS}` | ✓ — high byte strobe |
| Pin 31 (/WE) | +5V (via #PWR010) | ✓ |
| Pins 13–21 (D0–D7) | `ST_D8`–`ST_D15` | ✓ — upper byte |

### Chip enable logic

The ROM_CE wired-AND node connects to:
- R4 (10 kΩ) pull-up to +5V
- Anode of D1 (K → `ST_~{ROM4}`)
- Anode of D2 (K → `ST_~{ROM3}`)
- Both chips' /CE (pin 22)

ROM_CE goes LOW when EITHER /ROM3 OR /ROM4 is asserted LOW. The two signals never assert simultaneously on the ST bus, so this functions as a union of the two 64 KB address windows ($FA and $FB) giving a 128 KB addressable window per bank.

### SW1 — Bank select

SW1 at (332.74, 86.36). Common (P-side) pins tied to GND. T-side outputs:

| SW pin | Net | Chip address bit | Pull-up |
|---|---|---|---|
| T1 | `B_SW1` | A16 | R1 (10 kΩ) to +5V |
| T2 | `B_SW2` | A17 | R2 (10 kΩ) to +5V |
| T3 | `B_SW3` | A18 | R3 (10 kΩ) to +5V |

Closed = GND = 0; Open = pulled HIGH = 1. ✓

### /OE byte strobe operation

Unlike a simple ROM where /OE is tied to GND, this design drives each chip's /OE individually with the byte strobe:

| Access type | /UDS | /LDS | U2 /OE | U1 /OE | Active chips |
|---|---|---|---|---|---|
| Word (16-bit) | LOW | LOW | LOW | LOW | both |
| Upper byte only | LOW | HIGH | LOW | HIGH | U2 only |
| Lower byte only | HIGH | LOW | HIGH | LOW | U1 only |

This prevents bus contention when only one byte is accessed. For ROM use (read-only), bus contention would not cause damage, but the byte-strobe /OE is cleaner design practice. ✓

---

## Address Mapping

### ST bus → chip address

```
ST bus signal   →   W29C040 chip address bit
─────────────────────────────────────────────
A1  (bit 1)     →   A0   (bit 0)
A2  (bit 2)     →   A1
...
A15 (bit 15)    →   A14
/ROM4           →   A15  (0 = $FA region, 1 = $FB region)
B_SW1 (SW1-1)   →   A16  ┐
B_SW2 (SW1-2)   →   A17  ├ bank select (3 bits → 8 banks)
B_SW3 (SW1-3)   →   A18  ┘
```

The 68000 does not drive A0 — byte lane selection is handled by /UDS and /LDS. The lowest chip address bit (A0) comes from ST A1 (the lowest CPU address line visible on the cartridge port). ✓

### ST address window

| /ROM4 | /ROM3 | Region | Chip A15 |
|---|---|---|---|
| LOW  | HIGH | `$FA0000`–`$FAFFFF` | 0 |
| HIGH | LOW  | `$FB0000`–`$FBFFFF` | 1 |

Combined window: `$FA0000`–`$FBFFFF` (128 KB of byte addresses per bank).

---

## Memory Map — 2× W29C040-90B

### Chip address calculation

Each chip has 19 address bits (A0–A18) = 512 K locations = 512 KB per chip.

For a given bank (A18:A17:A16 fixed), the address bits A15:A14:...:A0 vary (16 bits = 64 K locations = 64 KB per chip). Two chips in parallel provide 64 K × 16-bit words = 128 KB of content per bank.

```
chip_addr = (bank × 0x010000) | (ROM4_bit × 0x008000) | ST_word_offset
```

where `ST_word_offset` = ST_byte_addr[14:0] (from A1–A15, shifted right as word address).

### Bank map

Switch closed = 0 (GND); switch open = 1 (+5 V via pull-up).

| SW1-3 (A18) | SW1-2 (A17) | SW1-1 (A16) | Bank | Chip byte offset | Range |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | `0x000000` | `0x000000`–`0x00FFFF` |
| 0 | 0 | 1 | 1 | `0x010000` | `0x010000`–`0x01FFFF` |
| 0 | 1 | 0 | 2 | `0x020000` | `0x020000`–`0x02FFFF` |
| 0 | 1 | 1 | 3 | `0x030000` | `0x030000`–`0x03FFFF` |
| 1 | 0 | 0 | 4 | `0x040000` | `0x040000`–`0x04FFFF` |
| 1 | 0 | 1 | 5 | `0x050000` | `0x050000`–`0x05FFFF` |
| 1 | 1 | 0 | 6 | `0x060000` | `0x060000`–`0x06FFFF` |
| 1 | 1 | 1 | 7 | `0x070000` | `0x070000`–`0x07FFFF` |

Total: 8 × 64 KB = 512 KB per chip = chip fully utilized.  
Combined 16-bit content: 8 × 128 KB = **1 MB**. ✓

### ROM binary programming layout

The 68000 places the high byte (MSB) at an even address. /UDS asserts for even-address bytes.

| File | Chip | Contains | Byte selection |
|---|---|---|---|
| `rom_hi.bin` | U2 (D8–D15) | even bytes of ROM image (0, 2, 4, …) | /UDS — upper byte |
| `rom_lo.bin` | U1 (D0–D7) | odd bytes of ROM image (1, 3, 5, …) | /LDS — lower byte |

For a banked image, lay each bank consecutively: bank 0 at offset `0x000000`, bank 1 at `0x010000`, …, bank 7 at `0x070000`. Each bank occupies 64 KB (0x10000 bytes) in each file.

---

## Memory Map — 2× TC57H1000AD-85 (alternative)

The Toshiba TC57H1000AD-85 is a 128 K × 8 SRAM, DIP-32:

| Pin | W29C040-90B | TC57H1000AD-85 | Required setting |
|---|---|---|---|
| 1 | A18 | VPP | **SW1-3 must be OPEN** (VPP = +5 V via R3) |
| 2–29, 32 | A0–A16, D0–D7, /CE, /OE, GND, VCC | identical | — |
| 30 | A17 | NC | SW1-2 irrelevant |
| 31 | /WE | /WE (same) | stays +5 V ✓ |

**SW1-3 must remain OPEN at all times with TC57H1000.** Closing SW1-3 would pull VPP (pin 1) to GND and may damage the chip.

### Bank map (TC57H1000AD-85)

The TC57H1000 has A0–A16 (17 address bits = 128 K locations = 128 KB). With A17 going to NC (pin 30), only SW1-1 (→ A16) is effective as a bank switch.

| SW1-3 | SW1-2 | SW1-1 (A16) | Bank | Chip byte offset |
|---|---|---|---|---|
| **1 (OPEN)** | any | 0 (closed) | 0 | `0x000000`–`0x00FFFF` |
| **1 (OPEN)** | any | 1 (open)   | 1 | `0x010000`–`0x01FFFF` |

Total accessible: 2 × 64 KB = **128 KB** per chip, **256 KB** combined.

---

## Checklist — Rev 1.0 (corrected)

| Item | Status |
|---|---|
| D1 Cathode → /ROM4 signal | ✅ |
| D2 Cathode → /ROM3 signal | ✅ |
| ROM_CE wired-AND with R4 pull-up | ✅ |
| ST A1–A15 → Chip A0–A14 (local labels, no global collision) | ✅ |
| /ROM4 → Chip A15 | ✅ |
| DIP switch (B_SW1/2/3) → Chip A16/A17/A18 | ✅ |
| ROM_CE → Chip /CE (both U1, U2) | ✅ |
| U1 /OE → /LDS (low byte strobe) | ✅ |
| U2 /OE → /UDS (high byte strobe) | ✅ |
| /WE → +5V (both chips, write protect) | ✅ |
| U1 D0–D7 → ST D0–D7 | ✅ |
| U2 D0–D7 → ST D8–D15 | ✅ |
| VCC, GND, decoupling capacitors | ✅ |
