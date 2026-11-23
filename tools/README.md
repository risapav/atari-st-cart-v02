# ROM Tools — Atari ST ROM Cartridge v2

A set of Python scripts for preparing ROM programs for physical chip programming of the
`cart_v02` cartridge. The scripts handle bank-boundary alignment, concatenation of multiple
programs, and splitting the resulting image into LO (U2) and HI (U1) chip files.

---

## Files

| File | Description |
|---|---|
| `chips.py` | Chip definitions and shared functions (imported by other scripts) |
| `rom_pack.py` | Pack and concatenate ROM programs → chip files |
| `rom_split.py` | Split an existing combined 16-bit image → LO + HI |
| `rom_info.py` | Display statistics and bank map of chip files |
| `rom_validate.py` | Validate ROM files — size, magic, content, GEMDOS header |
| `Makefile` | Shortcuts for common operations |

---

## Supported chips

### Winbond W29C040-90B (`--chip w29c040`, default)

| Parameter | Value |
|---|---|
| Capacity per chip | 512 KB (8-bit) |
| Number of banks | 8 |
| Combined image | 1 MB |
| Bank size | 128 KB (combined) / 64 KB (per chip) |

Both chips (U1 + U2) are programmed **separately** (remove from socket).

### Toshiba TC57H1000AD-85 (`--chip tc57h1000`)

| Parameter | Value |
|---|---|
| Capacity per chip | 128 KB (8-bit), A0–A16 |
| Number of banks | **2** (only A16 is effective) |
| Combined image | 256 KB |
| Bank size | 128 KB (combined) / 64 KB (per chip) |

> **WARNING — TC57H1000AD-85:**
> - **SW1-3 must remain OPEN** — pin 1 is `VPP` (+5 V via R3); closing to GND may destroy the chip.
> - **SW1-2 is irrelevant** — pin 30 is NC (not connected).
> - Only **2 banks** are available (only SW1-1 / A16 is an active bank select).

---

## File formats

### Combined 16-bit image (`combined.bin`)

Standard Motorola 68000 big-endian binary image. Each 16-bit word is stored at an even
address with the high byte first:

```
offset 0x000000: high byte of word at ST $FA0000  → U1 (D8–D15)
offset 0x000001: low  byte of word at ST $FA0000  → U2 (D0–D7)
offset 0x000002: high byte of word at ST $FA0002  → U1
offset 0x000003: low  byte of word at ST $FA0002  → U2
...
```

### Chip files (LO / HI)

Each chip receives **de-interleaved** bytes from the combined image:

| File | Chip | Content | Byte strobe |
|---|---|---|---|
| `chip_u1_lo.bin` | U2 | odd bytes (D0–D7) | /LDS |
| `chip_u2_hi.bin` | U1 | even bytes (D8–D15) | /UDS |

```
chip_u1_lo[n] = combined[2n + 1]   (low byte of each word → programs into U2)
chip_u2_hi[n] = combined[2n + 0]   (high byte of each word → programs into U1)
```

### Per-bank files

Each bank is 64 KB per chip (= 128 KB combined). Files `bankN_lo.bin` and `bankN_hi.bin`
are slices of the chip files for direct programming of a single bank.

---

## rom_pack.py — pack ROM programs

Reads one or more ROM programs, aligns each to a 128 KB bank boundary, concatenates them,
and generates chip files.

Supported input formats: `.bin`, `.rom`, `.img` — and `.stc` (Steem format):
the 4-byte null header is automatically stripped before alignment.

### Bank alignment

Each program is rounded **up** to the nearest multiple of 128 KB (bank size):

```
program  48 KB  → aligned to 128 KB  (1 bank)
program 128 KB  → stays   128 KB     (1 bank)
program 192 KB  → aligned to 256 KB  (2 banks)
program 300 KB  → aligned to 384 KB  (3 banks)
```

The gap between the end of the program and the bank boundary is filled with the `--pad` value
(default `0xFF`).

### Concatenation

Programs are assigned to banks in the order they are given on the command line.
Bank 0 = first program; the next program starts at the first free bank after it.

### Examples

```bash
# Recommended — pack all ROMs from the prg/ directory (default)
python3 rom_pack.py prg/
make pack                        # equivalent via Makefile

# Different source directory or chip type
python3 rom_pack.py myroms/ --chip tc57h1000 --out build/
make pack PRGDIR=myroms/ CHIP=tc57h1000 OUTDIR=build/

# Explicit file list (no spaces in filenames)
python3 rom_pack.py game1.bin game2.bin game3.bin --out build/
make pack SRCS="game1.bin game2.bin" OUTDIR=build/

# Show layout without writing files
python3 rom_pack.py prg/ --dry-run
make dry-run

# Also save the combined 16-bit image
python3 rom_pack.py prg/ --save-combined
make pack-combined

# Custom pad byte (instead of 0xFF)
python3 rom_pack.py prg/ --pad 0x00
```

> **Spaces in filenames:** `make pack SRCS="..."` cannot handle filenames with spaces.
> The recommended approach is to place files into `prg/` and call `make pack` or
> `python3 rom_pack.py prg/` — the directory path itself contains no spaces.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `ROMs / directory` | (required) | Input ROM files or directory to scan |
| `--chip` | `w29c040` | Chip type: `w29c040` or `tc57h1000` |
| `--out` | `out/` | Output directory |
| `--pad` | `0xFF` | Fill byte for alignment padding |
| `--save-combined` | — | Also save `combined.bin` |
| `--dry-run` | — | Calculate layout only, write nothing |
| `--force` | — | Continue even if programs exceed chip capacity (truncates data) |

### Outputs

```
out/
├── chip_u1_lo.bin           — full U2 image (512 KB for W29C040, 128 KB for TC57H1000)
├── chip_u2_hi.bin           — full U1 image
├── bank0_lo.bin             — 64 KB bank 0 for U2
├── bank0_hi.bin             — 64 KB bank 0 for U1
├── bank1_lo.bin             — 64 KB bank 1 for U2
├── bank1_hi.bin             — ...
├── bank0_BUGBCRT2.STC       — (directory input only) source copy for bank 0
├── bank1_DiagROMCart.rom    — source copy for bank 1
├── ...
└── combined.bin             — (only with --save-combined) combined 16-bit image
```

Numbered source copies (`bank{N}_{original_name}`) are created only when the input is a
directory. Each copy corresponds to the ROM image that occupies that bank — makes it easy
to identify content without running `rom_info.py`.

### pack_order.txt — controlling bank assignment order

When the input is a directory, the script automatically manages `prg/pack_order.txt`:

**First run** (file does not exist):
- files are sorted alphabetically (case-insensitive)
- after a successful pack, `prg/pack_order.txt` is written with filenames in that order

**Subsequent runs** (file exists):
- files are ordered according to `pack_order.txt`
- new files missing from the file are appended alphabetically at the end
- files listed in `pack_order.txt` that no longer exist are silently skipped
- `pack_order.txt` is updated with the current order

**Changing bank assignment:**
1. Edit `prg/pack_order.txt` manually — rearrange lines as needed
2. Run `make pack` — files are processed in the new order
3. `out/bank{N}_{original_name}` copies reflect the new bank assignments

```
prg/pack_order.txt (example):
  # ROM pack order — edit order, then run make pack again
  # One filename per line. Lines starting with # are comments.

  etoscart.img        ← bank 0 (moved to first position)
  DiagROMCart.rom     ← bank 1
  JOUMPCRT.STC        ← bank 2
  ...
  BUGBCRT2.STC        ← bank 7 (moved to last position)
```

---

## rom_split.py — split a combined image

If you have an existing combined 16-bit ROM image (e.g. from another source), this script
de-interleaves it into chip files.

### Examples

```bash
# Basic split
python3 rom_split.py combined.bin

# TC57H1000, custom output directory
python3 rom_split.py combined.bin --chip tc57h1000 --out build/

# Also save per-bank 64 KB files + print bank map
python3 rom_split.py combined.bin --banks --map

# Display info only, write nothing
python3 rom_split.py combined.bin --info
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `COMBINED_BIN` | (required) | Input combined 16-bit image |
| `--chip` | `w29c040` | Chip type |
| `--out` | `out/` | Output directory |
| `--banks` | — | Also save per-bank 64 KB files |
| `--map` | — | Print bank map after splitting |
| `--info` | — | Display info only, write nothing |

---

## rom_info.py — chip file info

Displays statistics, bank map, and signatures (first word of each bank) for a quick visual
check of chip files before programming.

### Examples

```bash
# LO + HI chip files
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin

# Combined image
python3 rom_info.py --combined combined.bin

# TC57H1000
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin --chip tc57h1000

# Single bank (bank 2)
python3 rom_info.py out/bank2_lo.bin out/bank2_hi.bin --bank 2
```

---

## rom_validate.py — ROM image validation

Checks files in a directory (or directly specified files) and verifies each against a set
of criteria. Output is a summary table with columns: size, format, chip compatibility,
occupied banks, magic constant, and overall status `PASS / WARN / FAIL`.

Directory scan: files with extensions `.bin`, `.stc`, `.rom`, `.img` (case-insensitive).

### What is checked

| Check | Detail |
|---|---|
| Size and alignment | File must be a multiple of 64 KB; must fit within chip capacity |
| STC format | Automatic stripping of the 4-byte Steem header (`\x00\x00\x00\x00`) before 128 KB image |
| Format detection | `combined` (16-bit interleaved) / `chip` (lo or hi) / `bank` (64 KB slice) |
| Chip compatibility | W29C040 (max 1 MB) / TC57H1000 (max 256 KB) / both / none |
| Bank content | Number of occupied banks, fill percentage (≠ 0xFF) |
| Magic constant | First 16-bit word at $FA0000; classified against 25+ known values |
| GEMDOS header | If magic = `0x601A`: parses TLEN/DLEN/BLEN/SLEN/ABSFLAG, reports errors |
| Per-bank SHA-1 | Checksum of each bank for content identification |

### Steem STC format

The Steem emulator stores cartridge ROM files with a 4-byte null prefix before the 128 KB image:

```
offset 0x000000–0x000003:  00 00 00 00   (Steem header)
offset 0x000004–0x020003:  <128 KB ROM image>
```

The script automatically detects this format (size 131 076 B, first 4 bytes zero) and strips
the header before analysis. The resulting size, magic, and bank count are computed from the
ROM content itself. The output line includes a note `STC: 4-byte header stripped`.

### Magic constants

The script classifies the first 16-bit word of the combined image (address `$FA0000`):

| Value | Description | Status |
|---|---|---|
| `0xFA52` | Atari ST cartridge magic — TOS scans for `FA52 235F` or `FA52 235A` | OK |
| `0xABCD` | `LINE-A #$BCD` — entry point of some cartridge programs (e.g. Steem STC files) | OK |
| `0x601A` | GEMDOS exec magic — TOS autoboots this program | OK |
| `0x601C` | GEMDOS exec (variant) | OK |
| `0x4EF9` | `JMP abs.l` — direct ROM code | OK |
| `0x4EB9` | `JSR abs.l` | OK |
| `0x6000` | `BRA.W` — branch with 16-bit offset | OK |
| `0x60xx` (xx ≠ 00, FE) | `BRA.B ±N` — short branch | OK |
| `0x48E7` | `MOVEM.L regs,-(SP)` — C/ASM prologue | OK |
| `0x41FA`, `0x43FA` | `LEA d(PC),An` — position-independent code | OK |
| `0x4E71` | `NOP` — unusual as first instruction | WARN |
| `0x4E75` | `RTS` — first instruction should not be a return | WARN |
| `0x60FE` | `BRA.S *-0` — infinite loop | FAIL |
| `0x4AFC` | `ILLEGAL` — illegal instruction | FAIL |
| `0xFFFF` | Unerased flash (erase state) | FAIL |
| `0x0000` | Zeroed memory | FAIL |

For magic `0xFA52` the script also checks the second word and refines the description:
`Atari ST cart magic (FA52/235F)` or `Atari ST cart magic (FA52/235A)`.

### Result status

| Status | Condition |
|---|---|
| `PASS` | Valid size, non-empty content, valid first instruction |
| `WARN` | Valid size, but partially filled / unusual magic / bad GEMDOS header / too little content |
| `FAIL` | Invalid size, empty file (all-0xFF), harmful magic (infinite loop, ILLEGAL) |

### Examples

```bash
# Validate entire directory
python3 rom_validate.py out/

# Specific files
python3 rom_validate.py combined.bin chip_u1_lo.bin chip_u2_hi.bin

# Also show per-bank table and GEMDOS detail
python3 rom_validate.py out/ --detail

# Filter for a specific chip
python3 rom_validate.py out/ --chip tc57h1000
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `FILE_OR_DIR` | (required) | One or more files (`.bin/.stc/.rom/.img`), or directory to scan |
| `--chip` | — | Filter results for a given chip (`w29c040` / `tc57h1000`) |
| `--detail` | — | Print per-bank table and GEMDOS detail for combined images |

### Sample output

```
╔══ rom_validate ════════════════════════════════════════════
║  Directory: out
║  Files: 7
╚═══════════════════════════════════════════════════════════

  File               Size      Format                          Chip          Banks      Fill     Magic     Magic description                      Status
  ─────────────────  ────────  ──────────────────────────────  ────────────  ─────────  ───────  ────────  ────────────────────────────────────  ─────
  BUGBCRT2.STC       128 KB    combined(TC5) / combined(W29)   both          1/1        96.9%    0xABCD    LINE-A #0xBCD (cartridge entry)        PASS
  DiagROMCart.rom    128 KB    combined(TC5) / combined(W29)   both          1/1        96.7%    0xFA52    Atari ST cart magic (FA52/235F)        PASS
  JOUMPCRT.STC       128 KB    combined(TC5) / combined(W29)   both          1/1        87.0%    0xABCD    LINE-A #0xBCD (cartridge entry)        PASS
  MXCRT.STC          128 KB    combined(TC5) / combined(W29)   both          1/1        86.8%    0xABCD    LINE-A #0xBCD (cartridge entry)        PASS
  ST Test v4.4.img   64 KB     chip(TC5) / chip(W29)           both          1/1        91.4%    —         — (chip file: magic is split acro…     PASS
  STE Test v1.9.img  64 KB     chip(TC5) / chip(W29)           both          1/1        91.9%    —         — (chip file: magic is split acro…     PASS
  etoscart.img       128 KB    combined(TC5) / combined(W29)   both          1/1        98.0%    0xFA52    Atari ST cart magic (FA52/235F)        PASS

  Summary: 7 files  │  7 PASS  │  0 WARN  │  0 FAIL
```

---

## Makefile

Shortcuts for common workflows:

```bash
# Pack ROMs from prg/ (default) — recommended
make pack

# Different source directory or chip type
make pack PRGDIR=myroms/ CHIP=tc57h1000 OUTDIR=build/

# Explicit file list (no spaces in filenames)
make pack SRCS="game.bin"
make pack SRCS="p1.bin p2.bin" CHIP=w29c040

# Preview layout without writing
make dry-run

# Pack + save combined image
make pack-combined

# Split an existing combined.bin
make split SRC=combined.bin

# Display chip file info
make info

# Validate (summary table)
make validate
make validate VALDIR=build/ CHIP=tc57h1000

# Validate with per-bank detail and GEMDOS output
make validate-detail

# Delete output directory
make clean
```

Makefile variables:

| Variable | Default | Description |
|---|---|---|
| `CHIP` | `w29c040` | Chip type |
| `PRGDIR` | `prg/` | Source directory for `pack` (if `SRCS` is not set) |
| `OUTDIR` | `out/` | Output directory (for `pack`, `split`, `info`) |
| `VALDIR` | `out/` | Directory to validate (for `validate`) |
| `SRCS` | — | Explicit input files (for `pack`; no spaces in filenames) |
| `SRC` | — | Single input file (for `split`) |
| `PAD` | `0xFF` | Fill byte |

---

## Typical workflow

### W29C040 — full deployment (1 MB, 8 banks)

Place all source files into `prg/`. The script automatically scans the directory, handles
filenames with spaces, and strips STC headers — no quoting or explicit file lists needed.

```bash
# 1. Validate sources
make validate VALDIR=prg/

# 2. Prepare chip files (scans prg/ automatically)
make pack

# 3. Check content (bank map, signatures)
make info

# 4. Program chips (with external programmer)
#    U1 ← out/chip_u2_hi.bin  (D8–D15 / high byte)
#    U2 ← out/chip_u1_lo.bin  (D0–D7 / low byte)

# 5. Set DIP switch SW1
#    Bank 0: SW1-1=0, SW1-2=0, SW1-3=0
#    Bank 1: SW1-1=1, SW1-2=0, SW1-3=0
#    ...
```

### W29C040 — mix of real cartridge ROMs (prg/ directory)

Example with real files (including filenames with spaces and STC format):

```bash
# 0. Validate sources (prg/ directory)
python3 rom_validate.py prg/

# 1. Pack — scans prg/, banks assigned alphabetically (first run)
make pack
#    — or directly: python3 rom_pack.py prg/
#    → creates prg/pack_order.txt + out/bank{N}_{original_name} copies

# 2. Optional: change bank order manually
#    Edit prg/pack_order.txt, reorder lines, run make pack again.
#    out/bank{N}_{original_name} will reflect the new bank assignments.

# 3. Check resulting chip image (bank map, magic signatures)
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin

# 4. Program chips
#    U1 ← out/chip_u2_hi.bin  (512 KB, D8–D15 / high byte)
#    U2 ← out/chip_u1_lo.bin  (512 KB, D0–D7 / low byte)

# 5. Set DIP switch SW1 for the desired program
#    (order = per prg/pack_order.txt or alphabetical on first run):
#    Bank 0 (SW1=000): etoscart.img
#    Bank 1 (SW1=001): DiagROMCart.rom
#    Bank 2 (SW1=010): ST Test v4.4.img
#    Bank 3 (SW1=011): STE Test v1.9.img
#    Bank 4 (SW1=100): JOUMPCRT.STC
#    Bank 5 (SW1=101): MXCRT.STC
#    Bank 6 (SW1=110): BUGBCRT2.STC
#    Bank 7 (SW1=111): WBCRT.STC
```

### TC57H1000 — 128 KB SRAM, 2 banks

```bash
# 1. Prepare (max 256 KB, 2 banks)
make pack PRGDIR=prg/ CHIP=tc57h1000 OUTDIR=build/

# 2. Validate (shows warnings for SW1-3 / SW1-2)
make validate CHIP=tc57h1000 VALDIR=build/

# 3. Check + SW1 warnings
make info CHIP=tc57h1000 OUTDIR=build/

# 4. Program U1 ← build/chip_u2_hi.bin, U2 ← build/chip_u1_lo.bin
# 5. SW1-3 must remain OPEN (VPP); SW1-1 selects bank 0 or 1
```

---

## W29C040-90B programming notes

- Programmed **out of circuit** (remove from DIP-32 socket).
- The chip supports Software Data Protection (SDP) — if enabled, disable it before
  programming with the write-enable command sequence (depends on the programmer).
- Erased (blank) byte state = `0xFF`.
- Set programmer to type `W29C040` or compatible `29C040`.

## TC57H1000AD-85 notes

- **Never close SW1-3** — pin 1 is `VPP`, pull-up R3 provides +5 V.
  Closing the switch pulls VPP to GND and may permanently damage the chip.
- Programmed as a standard 128 KB SRAM or `TC57H1000`.
- Content is lost when power is removed (this is SRAM, not flash).
