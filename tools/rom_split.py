#!/usr/bin/env python3
"""
rom_split.py — Rozdeľ existujúci kombinovaný ROM obraz na chip súbory LO a HI.

Vstupom je hotový 16-bit kombinovaný binárny obraz (interleaved, big-endian,
formát aký by čítal 68000). Výstupom sú chip súbory pre fyzické programovanie.

Použitie:
  python3 rom_split.py combined.bin [--chip w29c040] [--out out/]
  python3 rom_split.py combined.bin --banks         # aj per-bank 64 KB súbory
  python3 rom_split.py combined.bin --info          # len zobraz informácie

Formát kombinovaného obrazu (68000 big-endian):
  offset 0x000000: high byte slova na ST $FA0000  → U1 socket (D8–D15, /UDS) → chip_u2_hi.bin
  offset 0x000001: low  byte slova na ST $FA0000  → U2 socket (D0–D7, /LDS)  → chip_u1_lo.bin
  offset 0x000002: high byte slova na ST $FA0002  → U1 socket
  ...
"""

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chips import resolve_chip, chip_key, combined_size, split_to_chips, merge_from_chips


def fmt_size(n: int) -> str:
    if n % 1024 == 0:
        return f"{n // 1024} KB"
    return f"{n} B ({n / 1024:.1f} KB)"


def sha1_short(data: bytes | bytearray) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def is_empty(data: bytes | bytearray, fill: int = 0xFF) -> bool:
    return all(b == fill for b in data)


def print_bank_map(u1: bytearray, u2: bytearray, chip: dict):
    """Vypíše mapu bankov — obsadené / prázdne, prvé slovo, hash."""
    bsz = chip["bank_per_chip"]
    num_banks = chip["num_banks"]
    fill = chip["erase_byte"]

    print(f"  Mapa bankov ({num_banks} bankov × {fmt_size(bsz)} na čip):")
    print(f"  {'Bank':>4}  {'ST adresa':>18}  {'Stav':>8}  "
          f"{'Prvé slovo':>10}  {'SHA-1 (12 znakov)':>14}")
    print(f"  {'─'*4}  {'─'*18}  {'─'*8}  {'─'*10}  {'─'*14}")

    for b in range(num_banks):
        boff = b * bsz
        lo_bank = u1[boff:boff + bsz]
        hi_bank = u2[boff:boff + bsz]

        empty_lo = is_empty(lo_bank, fill)
        empty_hi = is_empty(hi_bank, fill)
        empty = empty_lo and empty_hi

        first_word = (hi_bank[0] << 8) | lo_bank[0]
        combined_bank = bytearray(bsz * 2)
        combined_bank[0::2] = hi_bank
        combined_bank[1::2] = lo_bank
        h = sha1_short(combined_bank)
        stav = "prázdny" if empty else "obsadenÝ"

        fa_start = 0xFA0000 + b * 0x20000
        fa_end   = fa_start + 0x1FFFE
        region_str = f"$FA{b:X}0000–$FA{b:X}FFFE" if b < 8 else f"${fa_start:06X}–${fa_end:06X}"
        # Korektné ST adresy pre každý bank
        fa_base = 0xFA0000
        fb_base = 0xFB0000
        region_str = f"${fa_base:06X}–${fb_base + 0xFFFE:06X} (B{b})"

        print(f"  {b:>4}  {region_str:>18}  {stav:>8}  "
              f"0x{first_word:04X}       {h}")


def split(args):
    chip = resolve_chip(args.chip)
    csize = combined_size(chip)
    num_banks = chip["num_banks"]

    p = Path(args.input)
    if not p.exists():
        print(f"CHYBA: súbor nenájdený: {p}", file=sys.stderr)
        return 1

    data = p.read_bytes()

    print(f"╔══ rom_split ═══════════════════════════════════════════════")
    print(f"║  Čip:    {chip['name']}")
    print(f"║  Vstup:  {p.name}  ({fmt_size(len(data))})")
    if chip["notes"]:
        print(f"║")
        for note in chip["notes"]:
            print(f"║  ⚠  {note}")
    print(f"╚═══════════════════════════════════════════════════════════")
    print()

    # Validácia veľkosti
    if len(data) % 2 != 0:
        print(f"  VAROVANIE: vstupný súbor má nepárnu veľkosť ({len(data)} B)."
              f" Posledný bajt bude ignorovaný.")
        data = data[:-1]

    if len(data) > csize:
        print(f"  CHYBA: vstupný obraz ({fmt_size(len(data))}) presahuje kapacitu čipu"
              f" {chip['name']} ({fmt_size(csize)}).", file=sys.stderr)
        return 1

    if len(data) < csize:
        padded = bytearray([chip["erase_byte"]] * csize)
        padded[:len(data)] = data
        data = padded
        print(f"  Obraz doplnený 0x{chip['erase_byte']:02X} na {fmt_size(csize)}.")

    u1, u2 = split_to_chips(data)

    print(f"  Kombinovaný obraz: {fmt_size(len(data))}  sha1:{sha1_short(data)}")
    print(f"  chip_u1_lo (D0–D7, socket U2):  {fmt_size(len(u1))}  sha1:{sha1_short(u1)}")
    print(f"  chip_u2_hi (D8–D15, socket U1): {fmt_size(len(u2))}  sha1:{sha1_short(u2)}")
    print()

    if args.info:
        print_bank_map(u1, u2, chip)
        return 0

    # --- Zápis ---
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    chip_u1 = out / "chip_u1_lo.bin"
    chip_u2 = out / "chip_u2_hi.bin"
    chip_u1.write_bytes(u1)
    chip_u2.write_bytes(u2)
    print(f"  Zapísané:")
    print(f"    {chip_u1}  ({fmt_size(len(u1))})")
    print(f"    {chip_u2}  ({fmt_size(len(u2))})")

    if args.banks:
        bsz = chip["bank_per_chip"]
        for b in range(num_banks):
            boff = b * bsz
            lo = u1[boff:boff + bsz]
            hi = u2[boff:boff + bsz]
            f_lo = out / f"bank{b}_lo.bin"
            f_hi = out / f"bank{b}_hi.bin"
            f_lo.write_bytes(lo)
            f_hi.write_bytes(hi)
        print(f"    bank{{N}}_lo/hi.bin  {num_banks} × 2 × {fmt_size(bsz)}")

    if args.map:
        print()
        print_bank_map(u1, u2, chip)

    print()
    print("  Hotovo.")
    return 0


def main():
    p = argparse.ArgumentParser(
        description="Rozdeľ kombinovaný 16-bit ROM obraz na chip súbory LO a HI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Príklady:
  Základné rozdelenie (W29C040, default):
    python3 rom_split.py combined.bin

  TC57H1000, vlastný výstupný adresár:
    python3 rom_split.py combined.bin --chip tc57h1000 --out build/

  Uložiť aj per-bank 64 KB súbory:
    python3 rom_split.py combined.bin --banks

  Len zobraziť mapu bankov bez zápisu:
    python3 rom_split.py combined.bin --info
        """,
    )
    p.add_argument("input", metavar="COMBINED_BIN", help="Vstupný kombinovaný 16-bit ROM obraz")
    p.add_argument("--chip", default="w29c040", metavar="TYP",
                   help="Typ čipu: w29c040 (default) alebo tc57h1000")
    p.add_argument("--out", default="out", metavar="ADRESÁR",
                   help="Výstupný adresár (default: out/)")
    p.add_argument("--banks", action="store_true",
                   help="Uložiť aj per-bank 64 KB súbory (bankN_lo.bin, bankN_hi.bin)")
    p.add_argument("--map", action="store_true",
                   help="Vypísať mapu bankov po rozdelení")
    p.add_argument("--info", action="store_true",
                   help="Len zobraziť informácie a mapu bankov, nič nezapisovať")
    args = p.parse_args()
    sys.exit(split(args))


if __name__ == "__main__":
    main()
