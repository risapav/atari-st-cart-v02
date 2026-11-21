#!/usr/bin/env python3
"""
Generátor testovacích ROM súborov pre Atari ST ROM Cartridge v2.

Vytvára 512 KB súbory pre oba čipy (U1=lo, U2=hi) so známym vzorcom,
ktorý kóduje adresu čipu aj číslo banku — umožňuje plnú verifikáciu
dekódovania adries a prepínania bankov.

Vzorec dát:
  U1[addr] = (local_addr + bank * 7)   & 0xFF   — lo bajt
  U2[addr] = ((local_addr >> 8) + bank * 13) & 0xFF   — hi bajt

  kde:  bank       = addr >> 16        (0–7)
        local_addr = addr & 0xFFFF     (offset v rámci banku)

Vlastnosti vzorca:
  - 16-bitové slovo na adrese 0 každého banku je unikátne pre daný bank
  - Vzorec je deterministický a ľahko overiteľný bez ukladania referenčných dát
  - Každý bajt závisí od pozície aj od banku → testuje address decoding aj bank select
"""

import os
import struct

CHIP_SIZE   = 512 * 1024   # 512 KB na čip
BANK_SIZE   = 64 * 1024    # 64 KB na bank na čip
NUM_BANKS   = 8


def chip_lo_byte(chip_addr: int) -> int:
    """Vypočíta očakávaný bajt U1 (lo) na adrese chip_addr."""
    bank       = (chip_addr >> 16) & 0x7
    local_addr = chip_addr & 0xFFFF
    return (local_addr + bank * 7) & 0xFF


def chip_hi_byte(chip_addr: int) -> int:
    """Vypočíta očakávaný bajt U2 (hi) na adrese chip_addr."""
    bank       = (chip_addr >> 16) & 0x7
    local_addr = chip_addr & 0xFFFF
    return ((local_addr >> 8) + bank * 13) & 0xFF


def expected_word(chip_addr: int) -> int:
    """Vypočíta očakávané 16-bitové slovo na adrese chip_addr."""
    return (chip_hi_byte(chip_addr) << 8) | chip_lo_byte(chip_addr)


def generate_chips() -> tuple[bytearray, bytearray]:
    """Vygeneruje kompletné 512 KB polia pre U1 a U2."""
    u1 = bytearray(CHIP_SIZE)
    u2 = bytearray(CHIP_SIZE)
    for addr in range(CHIP_SIZE):
        u1[addr] = chip_lo_byte(addr)
        u2[addr] = chip_hi_byte(addr)
    return u1, u2


def print_bank_summary(u1: bytearray, u2: bytearray):
    """Vypíše prvé slovo každého banku pre rýchlu kontrolu."""
    print("\nBanka  | Chip addr | Očakávané slovo | lo bajt | hi bajt")
    print("-------|-----------|-----------------|---------|--------")
    for bank in range(NUM_BANKS):
        chip_addr = bank * BANK_SIZE
        lo = u1[chip_addr]
        hi = u2[chip_addr]
        word = (hi << 8) | lo
        print(f"  {bank}    | 0x{chip_addr:06X}  |     0x{word:04X}       |  0x{lo:02X}   |  0x{hi:02X}")


def save_full_chips(u1: bytearray, u2: bytearray, out_dir: str):
    """Uloží plné 512 KB súbory čipov."""
    u1_path = os.path.join(out_dir, "chip_u1_lo.bin")
    u2_path = os.path.join(out_dir, "chip_u2_hi.bin")
    with open(u1_path, "wb") as f:
        f.write(u1)
    with open(u2_path, "wb") as f:
        f.write(u2)
    print(f"U1 (lo, 512 KB): {u1_path}")
    print(f"U2 (hi, 512 KB): {u2_path}")


def save_bank_files(u1: bytearray, u2: bytearray, out_dir: str):
    """Uloží každý bank zvlášť ako pár 64 KB súborov (lo + hi)."""
    for bank in range(NUM_BANKS):
        offset  = bank * BANK_SIZE
        lo_path = os.path.join(out_dir, f"bank{bank}_lo.bin")
        hi_path = os.path.join(out_dir, f"bank{bank}_hi.bin")
        with open(lo_path, "wb") as f:
            f.write(u1[offset : offset + BANK_SIZE])
        with open(hi_path, "wb") as f:
            f.write(u2[offset : offset + BANK_SIZE])
        print(f"  bank {bank}: {os.path.basename(lo_path)} + {os.path.basename(hi_path)}"
              f"  ({BANK_SIZE // 1024} KB každý)")


if __name__ == "__main__":
    out_dir  = os.path.dirname(os.path.abspath(__file__))
    roms_dir = os.path.join(out_dir, "roms")
    os.makedirs(roms_dir, exist_ok=True)

    print("=" * 60)
    print("Generujem testovacie ROM dáta pre cart_v02...")
    print("=" * 60)

    u1, u2 = generate_chips()

    print("\n[ Plné 512 KB súbory čipov ]")
    save_full_chips(u1, u2, roms_dir)

    print("\n[ Jednotlivé banky (64 KB × 2) ]")
    save_bank_files(u1, u2, roms_dir)

    print_bank_summary(u1, u2)

    total = 2 * CHIP_SIZE + 2 * NUM_BANKS * BANK_SIZE
    print(f"\nCelkovo vygenerovaných: {total // 1024} KB v {2 + 2*NUM_BANKS} súboroch")
    print("Hotovo.")
