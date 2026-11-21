#!/usr/bin/env python3
"""
Testovací runner pre Atari ST ROM Cartridge v2 — virtuálna simulácia.

Testy overujú:
  T01  Preklad adries $FA/$FB → adresa čipu
  T02  Čítanie 16-bitového slova (bank 0, spotové kontroly)
  T03  Izolácia byte strobe (/LDS a /UDS zvlášť)
  T04  Prepínanie bankov (všetkých 8 bankov)
  T05  CE logika (okno $FA0000–$FBFFFF, mimo okna)
  T06  Kompletný sekvenčný sken banku 0 (128 KB)
  T07  Zarovnanie na 68000 word (A0 ignorovaný)
  T08  Hraničné adresy
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cartridge_model import CartridgeModel
from generate_test_roms import chip_lo_byte, chip_hi_byte, expected_word, generate_chips

ROMS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roms")
U1_FILE  = os.path.join(ROMS_DIR, "chip_u1_lo.bin")
U2_FILE  = os.path.join(ROMS_DIR, "chip_u2_hi.bin")

# ----------------------------------------------------------------------------
# Pomocné funkcie reportovania
# ----------------------------------------------------------------------------

_passed = 0
_failed = 0
_results: list[tuple[str, bool, str]] = []


def test(name: str, condition: bool, detail: str = ""):
    global _passed, _failed
    status = "PASS" if condition else "FAIL"
    suffix = f"  ({detail})" if detail and not condition else ""
    print(f"  [{status}]  {name}{suffix}")
    _results.append((name, condition, detail))
    if condition:
        _passed += 1
    else:
        _failed += 1


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def setup() -> CartridgeModel:
    if not os.path.exists(U1_FILE) or not os.path.exists(U2_FILE):
        print("ROM súbory nenájdené. Spúšťam generate_test_roms.py ...")
        import subprocess
        gen = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generate_test_roms.py")
        subprocess.run([sys.executable, gen], check=True)
    model = CartridgeModel()
    model.load_chips(U1_FILE, U2_FILE)
    return model


# ----------------------------------------------------------------------------
# T01 — Preklad adries
# ----------------------------------------------------------------------------

def test_t01_address_translation():
    section("T01: Preklad adries ST bus → adresa čipu")
    model = setup()
    model.set_bank(0)

    cases = [
        # (st_addr,   exp_chip_addr, popis)
        (0xFA0000, 0x000000, "$FA0000 → chip 0x000000  (začiatok $FA, A15=0)"),
        (0xFA0002, 0x000001, "$FA0002 → chip 0x000001  (A1=1 → chipA0=1)"),
        (0xFA0004, 0x000002, "$FA0004 → chip 0x000002"),
        (0xFA0100, 0x000080, "$FA0100 → chip 0x000080"),
        (0xFAFFFE, 0x007FFF, "$FAFFFE → chip 0x007FFF  (koniec $FA)"),
        (0xFB0000, 0x008000, "$FB0000 → chip 0x008000  (začiatok $FB, A15=1)"),
        (0xFB0002, 0x008001, "$FB0002 → chip 0x008001"),
        (0xFBFFFE, 0x00FFFF, "$FBFFFE → chip 0x00FFFF  (koniec $FB, koniec banku 0)"),
    ]

    for st_addr, exp_chip, label in cases:
        got_chip = model.st_to_chip_addr(st_addr)
        test(label, got_chip == exp_chip,
             f"očakávané 0x{exp_chip:06X}, dostali 0x{got_chip:06X}")

    # Bank 1: rovnaká ST adresa, chip adresa posunutá o 0x010000
    model.set_bank(1)
    got = model.st_to_chip_addr(0xFA0000)
    test("bank 1 → $FA0000 → chip 0x010000", got == 0x010000,
         f"dostali 0x{got:06X}")

    model.set_bank(7)
    got = model.st_to_chip_addr(0xFBFFFE)
    test("bank 7 → $FBFFFE → chip 0x07FFFF", got == 0x07FFFF,
         f"dostali 0x{got:06X}")


# ----------------------------------------------------------------------------
# T02 — 16-bitové slovo, bank 0
# ----------------------------------------------------------------------------

def test_t02_word_read_bank0():
    section("T02: 16-bitové čítanie slov (bank 0)")
    model = setup()
    model.set_bank(0)

    for st_addr in [0xFA0000, 0xFA0002, 0xFA0100, 0xFA0200,
                    0xFAFFFE, 0xFB0000, 0xFB0002, 0xFBFFFE]:
        chip_addr = model.st_to_chip_addr(st_addr)
        exp = expected_word(chip_addr)
        got = model.read_word(st_addr)
        test(f"slovo @ ${st_addr:06X}  (chip=0x{chip_addr:06X})",
             got == exp,
             f"očakávané 0x{exp:04X}, dostali 0x{got:04X}")


# ----------------------------------------------------------------------------
# T03 — Izolácia byte strobe
# ----------------------------------------------------------------------------

def test_t03_byte_strobes():
    section("T03: Izolácia byte strobe (/LDS a /UDS)")
    model = setup()
    model.set_bank(0)

    for st_addr in [0xFA0000, 0xFA0100, 0xFB0000, 0xFBFFFE]:
        chip_addr = model.st_to_chip_addr(st_addr)
        exp_lo = chip_lo_byte(chip_addr)
        exp_hi = chip_hi_byte(chip_addr)

        got_lo   = model.read_byte_lo(st_addr)
        got_hi   = model.read_byte_hi(st_addr)
        got_word = model.read_word(st_addr)

        test(f"/LDS  lo bajt @ ${st_addr:06X}",
             got_lo == exp_lo, f"exp 0x{exp_lo:02X}, got 0x{got_lo:02X}")
        test(f"/UDS  hi bajt @ ${st_addr:06X}",
             got_hi == exp_hi, f"exp 0x{exp_hi:02X}, got 0x{got_hi:02X}")
        test(f"slovo = (hi<<8)|lo @ ${st_addr:06X}",
             got_word == (got_hi << 8) | got_lo,
             f"slovo=0x{got_word:04X}, hi=0x{got_hi:02X}, lo=0x{got_lo:02X}")


# ----------------------------------------------------------------------------
# T04 — Prepínanie bankov
# ----------------------------------------------------------------------------

def test_t04_bank_switching():
    section("T04: Prepínanie bankov (všetkých 8)")

    words_at_fa0000: dict[int, int] = {}

    for bank in range(8):
        model = setup()
        model.set_bank(bank)

        chip_addr = bank * 0x10000
        exp = expected_word(chip_addr)
        got = model.read_word(0xFA0000)
        words_at_fa0000[bank] = got

        test(f"bank {bank}  @ $FA0000  (chip=0x{chip_addr:06X})",
             got == exp,
             f"exp 0x{exp:04X}, got 0x{got:04X}")

        # Overíme aj $FB0000 pre daný bank
        chip_addr_fb = bank * 0x10000 + 0x8000
        exp_fb = expected_word(chip_addr_fb)
        got_fb = model.read_word(0xFB0000)
        test(f"bank {bank}  @ $FB0000  (chip=0x{chip_addr_fb:06X})",
             got_fb == exp_fb,
             f"exp 0x{exp_fb:04X}, got 0x{got_fb:04X}")

    unique = len(set(words_at_fa0000.values()))
    vals_str = "  ".join(f"B{b}=0x{v:04X}" for b, v in words_at_fa0000.items())
    test("všetkých 8 bankov dáva odlišné slová na $FA0000",
         unique == 8, f"len {unique}/8 unikátnych hodnôt: {vals_str}")


# ----------------------------------------------------------------------------
# T05 — CE logika
# ----------------------------------------------------------------------------

def test_t05_chip_enable():
    section("T05: CE logika — okno cartridge")
    model = setup()
    model.set_bank(0)

    # Vnútri okna — CE musí byť aktívne (read != -1)
    in_window = [0xFA0000, 0xFA0002, 0xFAFFFE, 0xFB0000, 0xFB0002, 0xFBFFFE]
    for addr in in_window:
        w = model.read_word(addr)
        test(f"CE aktívne    @ ${addr:06X}", w != -1, f"got {w}")

    # Mimo okna — CE neaktívne (read == -1)
    out_window = [0xF90000, 0xF9FFFE, 0xFC0000, 0xFC0002,
                  0x000000, 0x200000, 0xFFFFFF]
    for addr in out_window:
        w = model.read_word(addr)
        test(f"CE neaktívne  @ ${addr:06X}", w == -1, f"got 0x{w:08X}" if w != -1 else "")


# ----------------------------------------------------------------------------
# T06 — Kompletný sekvenčný sken
# ----------------------------------------------------------------------------

def test_t06_full_scan():
    section("T06: Kompletný sekvenčný sken banku 0 (128 KB = 65536 slov)")
    model = setup()
    model.set_bank(0)

    errors = 0
    first_errors: list[str] = []

    # $FA región (chip A15=0, chip adresy 0x0000–0x7FFF)
    for word_off in range(0x8000):
        st_addr   = 0xFA0000 + word_off * 2
        chip_addr = word_off
        exp = expected_word(chip_addr)
        got = model.read_word(st_addr)
        if got != exp:
            errors += 1
            if len(first_errors) < 3:
                first_errors.append(f"${st_addr:06X}: exp 0x{exp:04X} got 0x{got:04X}")

    # $FB región (chip A15=1, chip adresy 0x8000–0xFFFF)
    for word_off in range(0x8000):
        st_addr   = 0xFB0000 + word_off * 2
        chip_addr = 0x8000 + word_off
        exp = expected_word(chip_addr)
        got = model.read_word(st_addr)
        if got != exp:
            errors += 1
            if len(first_errors) < 3:
                first_errors.append(f"${st_addr:06X}: exp 0x{exp:04X} got 0x{got:04X}")

    detail = f"{errors} nezhôd" + ("; prvé: " + ", ".join(first_errors) if first_errors else "")
    test("128 KB sken, 0 nezhôd", errors == 0, detail if errors else "")


# ----------------------------------------------------------------------------
# T07 — 68000 zarovnanie (A0 ignorovaný)
# ----------------------------------------------------------------------------

def test_t07_word_alignment():
    section("T07: 68000 word zarovnanie (A0 ignorovaný na cartridge porte)")
    model = setup()
    model.set_bank(0)

    # Cartridge port neposkytuje A0; A0 (párnos/nepárnos) je vyriešená cez /UDS, /LDS.
    # Párna a nepárna adresa (líšia sa len A0) musia mapovať na rovnakú adresu čipu.
    pairs = [
        (0xFA0000, 0xFA0001),
        (0xFA0100, 0xFA0101),
        (0xFB0000, 0xFB0001),
        (0xFBFFFE, 0xFBFFFF),
    ]
    for even, odd in pairs:
        c_even = model.st_to_chip_addr(even)
        c_odd  = model.st_to_chip_addr(odd)
        test(f"${even:06X} a ${odd:06X} → rovnaká chip adresa (0x{c_even:06X})",
             c_even == c_odd,
             f"párna→0x{c_even:06X}, nepárna→0x{c_odd:06X}")


# ----------------------------------------------------------------------------
# T08 — Hraničné adresy
# ----------------------------------------------------------------------------

def test_t08_boundary():
    section("T08: Hraničné adresy")
    model = setup()

    for bank in [0, 7]:
        model.set_bank(bank)
        base_chip = bank * 0x10000

        cases = [
            (0xFA0000, base_chip + 0x0000, f"B{bank} $FA0000  prvé slovo $FA"),
            (0xFAFFFE, base_chip + 0x7FFF, f"B{bank} $FAFFFE  posledné slovo $FA"),
            (0xFB0000, base_chip + 0x8000, f"B{bank} $FB0000  prvé slovo $FB"),
            (0xFBFFFE, base_chip + 0xFFFF, f"B{bank} $FBFFFE  posledné slovo $FB"),
        ]
        for st_addr, exp_chip, label in cases:
            got_chip = model.st_to_chip_addr(st_addr)
            exp_w = expected_word(exp_chip)
            got_w = model.read_word(st_addr)
            ok = (got_chip == exp_chip) and (got_w == exp_w)
            test(label, ok,
                 f"chip exp 0x{exp_chip:06X} got 0x{got_chip:06X},"
                 f" slovo exp 0x{exp_w:04X} got 0x{got_w:04X}")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Atari ST ROM Cartridge v2 — virtuálna simulácia")
    print("=" * 60)

    test_t01_address_translation()
    test_t02_word_read_bank0()
    test_t03_byte_strobes()
    test_t04_bank_switching()
    test_t05_chip_enable()
    test_t06_full_scan()
    test_t07_word_alignment()
    test_t08_boundary()

    print(f"\n{'='*60}")
    print(f"  Výsledky: {_passed} prešlo, {_failed} zlyhalo")
    if _failed == 0:
        print("  VŠETKY TESTY PREŠLI ✓")
    else:
        print(f"  ZLYHANIA: {_failed}")
    print("=" * 60)
    sys.exit(0 if _failed == 0 else 1)


if __name__ == "__main__":
    main()
