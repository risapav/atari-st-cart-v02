# Atari ST ROM Cartridge v2 — 2× W29C040-90B (16-bit)

**KiCad 10 project · Rev 1.0 · 2026-11-08 · risapav**

A read-only ROM cartridge PCB for the Atari ST/STE/Mega family.  
Two Winbond W29C040-90B Flash EEPROMs work in parallel to provide a full 16-bit data bus.  
A 3-position DIP switch selects one of 8 banks of 128 KB, giving up to **1 MB** of banked ROM storage.

---

## Features

| Feature | Detail |
|---|---|
| Data bus | 16-bit (U1 → D0–D7 low byte, U2 → D8–D15 high byte) |
| ROM chips | 2× Winbond W29C040-90B (512 K × 8, DIP-32, 90 ns) |
| Total capacity | 1 MB (8 banks × 128 KB) |
| Address window | `$FA0000`–`$FBFFFF` (256 KB visible at once) |
| Bank switching | 3-bit DIP switch (SW1) on chip A16–A18 |
| Chip select | Wired-AND of /ROM3 + /ROM4 via 1N4148 diodes + 10 kΩ pull-up |
| Write-protect | /WE permanently tied to +5 V — the ST cannot write to the chip |
| Board size | 42 × 68 mm |
| Connector | 40-pin dual-row edge connector, 2 mm pitch (Atari CB101494) |

---

## Address Mapping

The Atari ST 68000 CPU does not expose A0 — byte selection is done through /UDS and /LDS.  
The cartridge port provides A1–A15, /ROM3, /ROM4, /UDS, /LDS, D0–D15.

```
ST bus signal   →   W29C040 pin
─────────────────────────────────
A1  – A15       →   A0  – A14   (15 bits)
/ROM4           →   A15         (0 = $FA bank, 1 = $FB bank)
SW1-1 (A16)     →   A16         ┐
SW1-2 (A17)     →   A17         ├ bank select (8 banks)
SW1-3 (A18)     →   A18         ┘
/ROM3 AND /ROM4 →   /CE (both chips, wired-AND)
/OE             →   /OE (both chips, tied together)
/WE             →   +5V (write-protect)
```

The full 256 KB window (`$FA0000`–`$FBFFFF`) is split by the /ROM4 signal:

| /ROM4 | /ROM3 | Region | Chip A15 |
|---|---|---|---|
| LOW  | HIGH | `$FA0000`–`$FAFFFF` | 0 |
| HIGH | LOW  | `$FB0000`–`$FBFFFF` | 1 |

Both chips are enabled only when **both** /ROM3 and /ROM4 are asserted (wired-AND through D1, D2).

---

## Bank Selection (DIP Switch SW1)

Switch closed = 0 (GND via switch) · Switch open = 1 (pulled to +5 V via 10 kΩ)

| SW1-3 | SW1-2 | SW1-1 | Bank | Offset in chip |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0x000000 |
| 0 | 0 | 1 | 1 | 0x040000 |
| 0 | 1 | 0 | 2 | 0x080000 |
| 0 | 1 | 1 | 3 | 0x0C0000 |
| 1 | 0 | 0 | 4 | 0x100000 |
| 1 | 0 | 1 | 5 | 0x140000 |
| 1 | 1 | 0 | 6 | 0x180000 |
| 1 | 1 | 1 | 7 | 0x1C0000 |

Each bank holds 128 KB visible through the ST cartridge window.  
Both U1 and U2 must be programmed with the same bank layout (each chip carries one byte of every 16-bit word).

---

## Bill of Materials

| Ref | Value / Part | Package | Note |
|---|---|---|---|
| U1, U2 | Winbond W29C040-90B | DIP-32 W15.24 mm | 512 K × 8 Flash EEPROM, 90 ns |
| J1 | Atari ST cartridge port | 2×20 edge, 2 mm pitch | CB101494 compatible |
| SW1 | 3-position DIP switch | through-hole | bank select A16–A18 |
| D1, D2 | 1N4148 | DO-35 axial | wired-AND for /CE |
| R1 | 10 kΩ | axial | pull-up for chip A16 |
| R2 | 10 kΩ | axial | pull-up for chip A17 |
| R3 | 10 kΩ | axial | pull-up for chip A18 (also VPP for TC57H1000) |
| R4 | 10 kΩ | axial | pull-up on /CE wired-AND node |
| C1, C2 | 100 nF | — | decoupling, one per chip |

### Alternative chip: TC57H1000AD-85

The TC57H1000AD-85 (Toshiba 1 M × 8 SRAM) can be substituted with these adjustments:

| SW1 position | Setting | Reason |
|---|---|---|
| SW1-3 (A18 / VPP) | **open** | VPP must be +5 V; R3 pull-up provides this |
| SW1-2 (A17 / pin 30) | ignore | pin 30 is NC on TC57H1000 |
| SW1-1 (A16) | as desired | active bank select |

---

## Chip Enable Logic

```
/ROM3 ──|>|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|>|── D1 ──┴── /CE (U1 pin 22, U2 pin 22)
```

Diodes D1 and D2 perform a passive wired-AND: /CE goes LOW only when **both** /ROM3 and /ROM4 are LOW simultaneously.  
R4 (10 kΩ) keeps /CE HIGH (chips deselected) whenever neither signal is asserted.  
This isolates the two open-drain-like ST outputs from each other without any active logic.

---

## Repository Contents

```
cart_v02/
├── cart_v02.kicad_pro   — KiCad 10 project file
├── cart_v02.kicad_sch   — schematic
├── cart_v02.kicad_pcb   — PCB layout
├── gerber/              — production Gerber + drill files
│   ├── cart_v02-F_Cu.gbr
│   ├── cart_v02-B_Cu.gbr
│   ├── cart_v02-F_Mask.gbr
│   ├── cart_v02-B_Mask.gbr
│   ├── cart_v02-F_Silkscreen.gbr
│   ├── cart_v02-B_Silkscreen.gbr
│   ├── cart_v02-Edge_Cuts.gbr
│   ├── cart_v02-PTH.drl
│   ├── cart_v02-NPTH.drl
│   └── cart_v02-job.gbrjob
└── ERC.rpt              — ERC report (2 minor warnings, no functional errors)
```

### KiCad library dependency

Custom symbols and footprints are bundled inside `my-libs/` and referenced with `${KIPRJMOD}` paths in `fp-lib-table` and `sym-lib-table`.  
No global library installation is needed — just open `cart_v02.kicad_pro` directly.

---

## ERC Notes

The ERC report lists two non-functional errors:

- `power_pin_not_driven` on `#PWR01` and `#PWR03` — standard KiCad artefact when power symbols have no explicit PWR_FLAG; does not affect the design.
- `footprint_link_issues` on J1 — the `atari_st` footprint library must be added to the global footprint table (see above).

---

## Programming the Chips

Each chip is 512 K × 8 and must be programmed **out of circuit** (remove from DIP socket).

1. Prepare two binary files from your ROM image:
   - `rom_lo.bin` — even bytes (D0–D7, goes into U1)
   - `rom_hi.bin` — odd bytes (D8–D15, goes into U2)
2. For a banked image, lay out all banks consecutively:  
   bank 0 at offset `0x000000`, bank 1 at `0x040000`, …, bank 7 at `0x1C0000`.
3. Program each file into the respective chip using any W29C040-compatible EEPROM programmer.
4. Insert chips with correct orientation (pin 1 at the notch end).
5. Set SW1 to the desired bank.

> The W29C040-90B supports in-system Software Data Protection (SDP).  
> Disable SDP before programming if your programmer requires it.

---

## License

Hardware design released under [CERN-OHL-P v2](https://ohwr.org/cern_ohl_p_v2.txt) (permissive).
