#!/usr/bin/env python3
"""
rom_info.py — Zobraz informácie o chip súboroch pre Atari ST ROM Cartridge v2.

Prijíma chip súbory (chip_u1_lo + chip_u2_hi) alebo kombinovaný obraz a vypíše:
  - veľkosť a hash
  - mapu bankov (obsadený / prázdny, prvé a posledné slovo, SHA-1)
  - súhrn prvého slova každého banku (podpis)

Použitie:
  python3 rom_info.py --chip w29c040 out/chip_u1_lo.bin out/chip_u2_hi.bin
  python3 rom_info.py --combined combined.bin --chip w29c040
  python3 rom_info.py out/bank0_lo.bin out/bank0_hi.bin --chip w29c040 --bank 0
"""

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chips import resolve_chip, combined_size, split_to_chips, merge_from_chips


def fmt_size(n: int) -> str:
    if n % 1024 == 0:
        return f"{n // 1024} KB"
    return f"{n} B ({n / 1024:.1f} KB)"


def sha1_hex(data: bytes | bytearray) -> str:
    return hashlib.sha1(data).hexdigest()


def sha1_short(data: bytes | bytearray) -> str:
    return sha1_hex(data)[:12]


def is_empty(data: bytes | bytearray, fill: int = 0xFF) -> bool:
    return all(b == fill for b in data)


def fill_ratio(data: bytes | bytearray, fill: int = 0xFF) -> float:
    return sum(1 for b in data if b == fill) / len(data) * 100 if data else 0.0


def print_header(chip: dict):
    csize = combined_size(chip)
    print(f"╔══ rom_info ════════════════════════════════════════════════")
    print(f"║  Čip:      {chip['name']}")
    print(f"║  Kapacita: {fmt_size(chip['chip_size'])} / čip  │  "
          f"{chip['num_banks']} bankov × {fmt_size(chip['bank_per_chip'])}")
    print(f"║  Kombinovaný obraz: {fmt_size(csize)}")
    if chip["notes"]:
        print(f"║")
        for note in chip["notes"]:
            print(f"║  ⚠  {note}")
    print(f"╚═══════════════════════════════════════════════════════════")
    print()


def print_chip_summary(u1: bytearray, u2: bytearray, chip: dict, label_u1="chip_u1_lo (D0–D7/U2)", label_u2="chip_u2_hi (D8–D15/U1)"):
    fill = chip["erase_byte"]
    combined = merge_from_chips(u1, u2)

    print(f"  {label_u1:<20} {fmt_size(len(u1)):<10}  sha1: {sha1_hex(u1)}")
    print(f"  {label_u2:<20} {fmt_size(len(u2)):<10}  sha1: {sha1_hex(u2)}")
    print(f"  {'kombinovaný':<20} {fmt_size(len(combined)):<10}  sha1: {sha1_hex(combined)}")
    empty_pct_u1 = fill_ratio(u1, fill)
    empty_pct_u2 = fill_ratio(u2, fill)
    print(f"  Naplnenosť: lo/U2 {100-empty_pct_u1:.1f}%  │  hi/U1 {100-empty_pct_u2:.1f}%  "
          f"(0x{fill:02X} = erase stav)")
    print()


def print_bank_detail(u1: bytearray, u2: bytearray, chip: dict):
    bsz = chip["bank_per_chip"]
    num_banks = chip["num_banks"]
    fill = chip["erase_byte"]

    # Hlavička tabuľky
    print(f"  {'Bank':>4}  "
          f"{'FA región':>14}  {'FB región':>14}  "
          f"{'Stav':>8}  "
          f"{'Prvé slovo':>10}  "
          f"{'Posledné':>8}  "
          f"{'SHA-1 (bank)':>14}")
    print(f"  {'─'*4}  {'─'*14}  {'─'*14}  {'─'*8}  {'─'*10}  {'─'*8}  {'─'*14}")

    has_content = False

    for b in range(num_banks):
        boff = b * bsz
        lo = u1[boff:boff + bsz]
        hi = u2[boff:boff + bsz]

        empty = is_empty(lo, fill) and is_empty(hi, fill)
        if not empty:
            has_content = True

        first_word = (hi[0] << 8) | lo[0]
        last_word  = (hi[-1] << 8) | lo[-1]

        combined_bank = bytearray(bsz * 2)
        combined_bank[0::2] = hi
        combined_bank[1::2] = lo
        h = sha1_short(combined_bank)

        stav = "prázdny" if empty else "OBSADENÝ"

        # ST adresy pre bank b:  $FA0000–$FAFFFF a $FB0000–$FBFFFF
        # (oba regióny sú vždy rovnaké bez ohľadu na bank — bank posúva chip adresu)
        fa_str = f"$FA0000–$FAFFFF"
        fb_str = f"$FB0000–$FBFFFF"

        print(f"  {b:>4}  "
              f"{fa_str:>14}  {fb_str:>14}  "
              f"{stav:>8}  "
              f"0x{first_word:04X}       "
              f"0x{last_word:04X}  "
              f"{h}")

    if not has_content:
        print(f"\n  Čip je prázdny (všetky bajty = 0x{fill:02X}).")
    print()


def print_bank_signatures(u1: bytearray, u2: bytearray, chip: dict):
    """Prvé slovo každého banku na ST $FA0000 — rýchly identifikátor obsahu."""
    bsz = chip["bank_per_chip"]
    num_banks = chip["num_banks"]

    print(f"  Podpisy bankov (prvé slovo na ST $FA0000):")
    for b in range(num_banks):
        boff = b * bsz
        lo_first = u1[boff]
        hi_first = u2[boff]
        word = (hi_first << 8) | lo_first
        mark = " ← tento bank nastavíš SW1" if b == 0 else ""
        print(f"    Bank {b}  (SW1={b:03b}):  0x{word:04X}{mark}")
    print()


def run(args):
    chip = resolve_chip(args.chip)
    print_header(chip)

    # --- Načítanie dát ---
    if args.combined:
        p = Path(args.combined)
        if not p.exists():
            print(f"CHYBA: {p} nenájdený.", file=sys.stderr)
            return 1
        raw = p.read_bytes()
        csize = combined_size(chip)
        if len(raw) > csize:
            print(f"VAROVANIE: vstup ({fmt_size(len(raw))}) > kapacita čipu ({fmt_size(csize)}).")
        padded = bytearray([chip["erase_byte"]] * csize)
        padded[:min(len(raw), csize)] = raw[:csize]
        u1, u2 = split_to_chips(padded)
        print(f"  Zdroj: {p.name}  ({fmt_size(len(raw))}  kombinovaný obraz)")
        print()
    else:
        if len(args.chip_files) != 2:
            print("CHYBA: zadaj presne 2 chip súbory (chip_u1_lo.bin a chip_u2_hi.bin) alebo --combined.",
                  file=sys.stderr)
            return 1
        p1 = Path(args.chip_files[0])
        p2 = Path(args.chip_files[1])
        for p in [p1, p2]:
            if not p.exists():
                print(f"CHYBA: {p} nenájdený.", file=sys.stderr)
                return 1
        u1 = bytearray(p1.read_bytes())
        u2 = bytearray(p2.read_bytes())
        if len(u1) != len(u2):
            print(f"VAROVANIE: U1 ({fmt_size(len(u1))}) ≠ U2 ({fmt_size(len(u2))}).")
        label_u1 = p1.name
        label_u2 = p2.name
        print(f"  Zdroj: {p1.name} + {p2.name}")
        print()
        print_chip_summary(u1, u2, chip, label_u1, label_u2)

    # Ak bol zadaný konkrétny bank (pre bank N lo/hi súbory)
    if args.bank is not None:
        b = args.bank
        bsz = chip["bank_per_chip"]
        # Chip súbory sú len 64 KB (jeden bank)
        if len(u1) == bsz:
            print(f"  Bank {b}  (chip offset 0x{b * bsz:06X}–0x{b * bsz + bsz - 1:06X})")
            first_word = (u2[0] << 8) | u1[0]
            print(f"  Prvé slovo:    0x{first_word:04X}")
            print(f"  SHA-1 (bank):  {sha1_hex(merge_from_chips(u1, u2))}")
            print()
            return 0

    print_bank_detail(u1, u2, chip)
    print_bank_signatures(u1, u2, chip)
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Zobraz informácie o chip súboroch pre Atari ST ROM Cartridge v2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Príklady:
  Chip súbory LO a HI:
    python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin --chip w29c040

  Kombinovaný obraz:
    python3 rom_info.py --combined combined.bin --chip w29c040

  Jeden bank (bank 2):
    python3 rom_info.py out/bank2_lo.bin out/bank2_hi.bin --bank 2

  TC57H1000:
    python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin --chip tc57h1000
        """,
    )
    p.add_argument("chip_files", nargs="*", metavar="CHIP_BIN",
                   help="Chip súbory: U1_lo.bin U2_hi.bin (alebo použiť --combined)")
    p.add_argument("--chip", default="w29c040", metavar="TYP",
                   help="Typ čipu: w29c040 (default) alebo tc57h1000")
    p.add_argument("--combined", metavar="BIN",
                   help="Kombinovaný 16-bit obraz namiesto chip súborov")
    p.add_argument("--bank", type=int, metavar="N",
                   help="Číslo banku (ak sú vstupné súbory 64 KB bank súbory)")
    args = p.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
