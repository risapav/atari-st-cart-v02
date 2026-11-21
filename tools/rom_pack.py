#!/usr/bin/env python3
"""
rom_pack.py — Zabaľ ROM programy pre Atari ST ROM Cartridge v2.

Načíta jeden alebo viac ROM programov (binárnych súborov), zarovná každý
na hranicu banku, zreťazí ich za sebou a vygeneruje chip súbory pre
programovanie fyzických pamätí.

Použitie:
  python3 rom_pack.py program.bin [--chip w29c040] [--out out/]
  python3 rom_pack.py p1.bin p2.bin p3.bin --chip tc57h1000 --out out/
  python3 rom_pack.py p1.bin --dry-run

Výstupy (v adresári --out):
  chip_u1_lo.bin      — plný obraz čipu U1 (lo bajty, D0–D7)
  chip_u2_hi.bin      — plný obraz čipu U2 (hi bajty, D8–D15)
  bankN_lo.bin        — 64 KB bank N pre U1  (N = 0 … num_banks-1)
  bankN_hi.bin        — 64 KB bank N pre U2
  combined.bin        — kombinovaný 16-bit obraz (voliteľne)
"""

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from chips import resolve_chip, chip_key, combined_size, align_up, split_to_chips


# ---------------------------------------------------------------------------
# Pomocné funkcie
# ---------------------------------------------------------------------------

def fmt_size(n: int) -> str:
    if n % 1024 == 0:
        return f"{n // 1024} KB"
    return f"{n} B ({n / 1024:.1f} KB)"


def sha1_short(data: bytes | bytearray) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def is_empty(data: bytes | bytearray, fill: int = 0xFF) -> bool:
    return all(b == fill for b in data)


# ---------------------------------------------------------------------------
# Vyhľadávanie vstupných súborov
# ---------------------------------------------------------------------------

ROM_EXTENSIONS = {".bin", ".stc", ".rom", ".img"}


def collect_inputs(inputs: list[str]) -> list[Path] | None:
    """Expanduje adresáre na zoradené zoznamy ROM súborov. Vracia None pri chybe."""
    paths: list[Path] = []
    seen: set[Path] = set()

    for s in inputs:
        p = Path(s)
        if p.is_dir():
            found = sorted(f for f in p.iterdir()
                           if f.is_file() and f.suffix.lower() in ROM_EXTENSIONS)
            if not found:
                exts = " / ".join(sorted(ROM_EXTENSIONS))
                print(f"  VAROVANIE: adresár {p} neobsahuje žiadne súbory ({exts}).")
            for f in found:
                if f.resolve() not in seen:
                    seen.add(f.resolve())
                    paths.append(f)
        elif p.exists():
            if p.resolve() not in seen:
                seen.add(p.resolve())
                paths.append(p)
        else:
            print(f"  CHYBA: súbor nenájdený: {p}", file=sys.stderr)
            return None

    return paths


# ---------------------------------------------------------------------------
# Hlavná logika balenia
# ---------------------------------------------------------------------------

def pack(args):
    chip = resolve_chip(args.chip)
    ckey = chip_key(args.chip)
    csize = combined_size(chip)
    bank_sz = chip["bank_combined"]
    num_banks = chip["num_banks"]
    pad_byte = args.pad & 0xFF

    input_paths = collect_inputs(args.inputs)
    if input_paths is None:
        return 1
    if not input_paths:
        print("  CHYBA: žiadne vstupné súbory.", file=sys.stderr)
        return 1

    print(f"╔══ rom_pack ════════════════════════════════════════════════")
    print(f"║  Čip:      {chip['name']}")
    print(f"║  Kapacita: {fmt_size(csize)} kombinovaných  │  {num_banks} bankov × {fmt_size(bank_sz)}")
    if chip["notes"]:
        print(f"║")
        for note in chip["notes"]:
            print(f"║  ⚠  {note}")
    print(f"╚═══════════════════════════════════════════════════════════")
    print()

    # Kombinovaný obraz naplníme pad bajt-om (erase stav)
    combined = bytearray([pad_byte] * csize)
    offset = 0
    bank = 0

    # --- Spracovanie vstupných súborov ---
    for p in input_paths:
        if not p.exists():
            print(f"  CHYBA: súbor nenájdený: {p}", file=sys.stderr)
            return 1

        data = bytearray(p.read_bytes())
        if len(data) == 0:
            print(f"  VAROVANIE: {p.name} je prázdny, preskakujem.")
            continue

        # Steem STC formát: 4-bajtová nulová hlavička pred 128 KB ROM obrazom
        stc_stripped = False
        if len(data) == 128 * 1024 + 4 and data[:4] == b'\x00\x00\x00\x00':
            data = data[4:]
            stc_stripped = True

        padded = align_up(len(data), bank_sz)
        banks_needed = padded // bank_sz
        banks_remaining = num_banks - bank

        label = f"  [{bank}] {p.name}"
        print(f"{label}")
        if stc_stripped:
            print(f"       STC:        4-bajtová hlavička odstránená (Steem formát)")
        print(f"       veľkosť:    {fmt_size(len(data))}")
        print(f"       zarovnané:  {fmt_size(padded)}  "
              f"→ {banks_needed} {'bank' if banks_needed == 1 else 'banky/bankov'}"
              f"  (bank {bank}–{bank + banks_needed - 1})")

        if banks_needed > banks_remaining:
            print(f"  CHYBA: program sa nezmestí! Zostáva {banks_remaining} bankov,"
                  f" potrebné {banks_needed}.", file=sys.stderr)
            if args.force:
                print("         --force: pokračujem napriek chybe (dáta budú orezané).")
                padded = banks_remaining * bank_sz
                data = data[:padded]
                banks_needed = banks_remaining
            else:
                return 1

        combined[offset:offset + len(data)] = data
        # zvyšok banku zostáva pad_byte (pad_byte je tam od inicializácie)
        offset += padded
        bank += banks_needed
        print()

    # --- Súhrn ---
    free_banks = num_banks - bank
    print(f"  Obsadené:  {bank}/{num_banks} bankov  ({fmt_size(offset)} / {fmt_size(csize)})")
    print(f"  Voľné:     {free_banks} bankov  ({fmt_size(csize - offset)})")
    print(f"  Pad bajt:  0x{pad_byte:02X}")

    if args.dry_run:
        print("\n  [dry-run] Žiadne súbory neboli zapísané.")
        return 0

    # --- Zápis výstupov ---
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    u1, u2 = split_to_chips(combined)

    written = []

    # Plné chip súbory
    chip_u1 = out / "chip_u1_lo.bin"
    chip_u2 = out / "chip_u2_hi.bin"
    chip_u1.write_bytes(u1)
    chip_u2.write_bytes(u2)
    written += [chip_u1, chip_u2]

    # Per-bank súbory
    bsz = chip["bank_per_chip"]
    for b in range(num_banks):
        boff = b * bsz
        lo = u1[boff:boff + bsz]
        hi = u2[boff:boff + bsz]
        f_lo = out / f"bank{b}_lo.bin"
        f_hi = out / f"bank{b}_hi.bin"
        f_lo.write_bytes(lo)
        f_hi.write_bytes(hi)
        written += [f_lo, f_hi]

    # Kombinovaný obraz (voliteľne)
    if args.save_combined:
        comb_path = out / "combined.bin"
        comb_path.write_bytes(combined)
        written.append(comb_path)

    print(f"\n  Zapísané do {out}/:")
    print(f"    chip_u1_lo.bin   {fmt_size(len(u1))}  sha1:{sha1_short(u1)}")
    print(f"    chip_u2_hi.bin   {fmt_size(len(u2))}  sha1:{sha1_short(u2)}")
    print(f"    bank{{N}}_lo/hi.bin  {num_banks} × 2 × {fmt_size(bsz)}")
    if args.save_combined:
        print(f"    combined.bin     {fmt_size(len(combined))}  sha1:{sha1_short(combined)}")

    print()
    print("  Hotovo.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Zabaľ ROM programy do chip súborov pre Atari ST ROM Cartridge v2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Príklady:
  Jeden program pre W29C040 (default):
    python3 rom_pack.py mygame.bin

  Dva programy, určiť chip a výstupný adresár:
    python3 rom_pack.py game1.bin game2.bin --chip w29c040 --out build/

  TC57H1000 (max 2 banky × 128 KB = 256 KB):
    python3 rom_pack.py rom.bin --chip tc57h1000 --out build/

  Zobraziť čo by sa stalo bez zápisu:
    python3 rom_pack.py p1.bin p2.bin --dry-run

  Uložiť aj kombinovaný 16-bit obraz:
    python3 rom_pack.py rom.bin --save-combined
        """,
    )
    p.add_argument("inputs", nargs="+", metavar="ROM", help="Vstupný ROM súbor (jeden alebo viac)")
    p.add_argument("--chip", default="w29c040", metavar="TYP",
                   help="Typ čipu: w29c040 (default) alebo tc57h1000")
    p.add_argument("--out", default="out", metavar="ADRESÁR",
                   help="Výstupný adresár (default: out/)")
    p.add_argument("--pad", type=lambda x: int(x, 0), default=0xFF, metavar="BAJT",
                   help="Výplňový bajt pre zarovnanie (default: 0xFF = erase stav)")
    p.add_argument("--save-combined", action="store_true",
                   help="Uložiť aj combined.bin (16-bit interleaved obraz)")
    p.add_argument("--dry-run", action="store_true",
                   help="Vypočítaj rozloženie bez zápisu súborov")
    p.add_argument("--force", action="store_true",
                   help="Pokračuj aj keď program presahuje kapacitu čipu (oreže dáta)")
    args = p.parse_args()
    sys.exit(pack(args))


if __name__ == "__main__":
    main()
