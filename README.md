# Atari ST ROM Cartridge v2 — 2× W29C040-90B (16-bit)

**KiCad 10 project · Rev 1.1 · 2026-11-08 · risapav**  
https://github.com/risapav/atari-st-cart-v02

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
| Chip select | Wired-AND of /ROM3 + /ROM4 via BAT42 diodes + 10 kΩ pull-up |
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
/LDS            →   /OE on U1 (D0–D7, low byte chip)
/UDS            →   /OE on U2 (D8–D15, high byte chip)
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
| 0 | 0 | 1 | 1 | 0x010000 |
| 0 | 1 | 0 | 2 | 0x020000 |
| 0 | 1 | 1 | 3 | 0x030000 |
| 1 | 0 | 0 | 4 | 0x040000 |
| 1 | 0 | 1 | 5 | 0x050000 |
| 1 | 1 | 0 | 6 | 0x060000 |
| 1 | 1 | 1 | 7 | 0x070000 |

Each bank holds 128 KB visible through the ST cartridge window.  
U1 and U2 must be programmed independently (each chip carries one byte of every 16-bit word).  
Each chip holds 64 KB per bank (0x10000 bytes); the combined 16-bit content per bank is 128 KB.

---

## Bill of Materials

| Ref | Value / Part | Package | LCSC | Note |
|---|---|---|---|---|
| U1, U2 | Winbond W29C040-90B | DIP-32 W15.24 mm | C2331 | 512 K × 8 Flash EEPROM, 90 ns |
| J1 | Atari ST cartridge port | 2×20 edge, 2 mm pitch | — | CB101494 compatible |
| SW1 | 3-pos slide DIP switch | THT 7.62 mm pitch | C501525 | bank select A16–A18 |
| D1, D2 | BAT42 | DO-35 axial | C2798198 | wired-AND for /CE |
| R1 | 10 kΩ | axial | C2903232 | pull-up for chip A16 |
| R2 | 10 kΩ | axial | C2903232 | pull-up for chip A17 |
| R3 | 10 kΩ | axial | C2903232 | pull-up for chip A18 (also VPP for TC57H1000) |
| R4 | 10 kΩ | axial | C2903232 | pull-up on /CE wired-AND node |
| C1, C2 | 100 nF | 0805 | C83055 | decoupling, one per chip |

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
/ROM3 ──|<|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|<|── D1 ──┴── /CE (U1 pin 22, U2 pin 22)
```

`|<|` = Cathode (K) on the signal side, Anode (A) on the /CE node side.

Diodes D1 and D2 perform a passive wired-OR on active-low signals: /CE goes LOW whenever **either** /ROM3 or /ROM4 is LOW.  
When both signals are HIGH (no access), R4 (10 kΩ) holds /CE HIGH (chips deselected).  
In practice /ROM3 and /ROM4 are never both LOW simultaneously on the ST bus, so this effectively enables the chips when EITHER region is accessed.

---

## Repository Contents

```
cart_v02/
├── cart_v02.kicad_pro      — KiCad 10 project file
├── cart_v02.kicad_sch      — schematic
├── cart_v02.kicad_pcb      — PCB layout
├── my-libs/                — project-local symbol and footprint libraries
├── production/             — fabrication output (rev 1.1)
│   ├── Atari_ST_ROM_Cartridge_v2__2_W29C040-90B_16-bit_1.1.zip
│   ├── bom.csv
│   ├── designators.csv
│   ├── netlist.ipc
│   └── positions.csv
├── tools/                  — Python scripts for ROM image preparation
│   ├── chips.py            — chip definitions (W29C040, TC57H1000)
│   ├── rom_pack.py         — pack & align multiple ROMs → chip files
│   ├── rom_split.py        — split combined 16-bit image → LO + HI
│   ├── rom_info.py         — display bank map and chip statistics
│   ├── rom_validate.py     — validate ROM files (.bin/.stc/.rom/.img): size, magic, STC strip
│   ├── Makefile            — shortcuts: pack / split / info / validate
│   └── README.md           — full tool documentation
├── doc/
│   ├── functional_analysis.md    — address decoding, CE logic, ROM formats (EN)
│   └── functional_analysis_sk.md — address decoding, CE logic, ROM formats (SK)
└── test/                   — virtual cartridge simulation (Python)
    ├── cartridge_model.py  — hardware model of the cartridge bus
    ├── generate_test_roms.py
    ├── run_tests.py        — 73 tests: address decode, bank switch, CE logic
    └── TESTING.md          — test methodology and results
```

### KiCad library dependency

Custom symbols and footprints are bundled inside `my-libs/` and referenced with `${KIPRJMOD}` paths in `fp-lib-table` and `sym-lib-table`.  
No global library installation is needed — just open `cart_v02.kicad_pro` directly.

---

## Programming the Chips

Each chip is 512 K × 8 and must be programmed **out of circuit** (remove from DIP socket).

The `tools/` directory contains Python scripts that automate all preparation steps:

```bash
cd tools/

# Pack one or more ROM programs → chip files (auto-aligned to 128 KB banks)
python3 rom_pack.py game.bin --out build/
python3 rom_pack.py p1.bin p2.bin p3.bin --out build/

# Validate before burning — scans .bin/.stc/.rom/.img, checks size, magic, GEMDOS header
# Steem .STC files (131076 B) are detected and the 4-byte header stripped automatically
python3 rom_validate.py build/
python3 rom_validate.py build/ --detail   # per-bank table + GEMDOS detail

# Display bank map and chip signatures
python3 rom_info.py build/chip_u1_lo.bin build/chip_u2_hi.bin
```

Or use the Makefile:

```bash
make pack SRCS="game.bin" OUTDIR=build/
make validate VALDIR=build/
make info OUTDIR=build/
```

Manual procedure (without scripts):

1. Prepare two binary files by de-interleaving the combined ROM image:
   - `chip_u2_hi.bin` — even bytes (D8–D15, upper byte) → **U2**
   - `chip_u1_lo.bin` — odd bytes (D0–D7, lower byte) → **U1**
2. For a banked image, place each bank at offset `bank × 0x10000` in each chip file.
3. Program each chip file into the respective chip using any W29C040-compatible EEPROM programmer.
4. Insert chips with correct orientation (pin 1 at the notch end).
5. Set SW1 to the desired bank.

> The W29C040-90B supports in-system Software Data Protection (SDP).  
> Disable SDP before programming if your programmer requires it.

See `tools/README.md` for full documentation including TC57H1000AD-85 support.

---

## License

Hardware design released under [CERN-OHL-P v2](https://ohwr.org/cern_ohl_p_v2.txt) (permissive).
