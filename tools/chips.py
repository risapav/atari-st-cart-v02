"""
Definície podporovaných pamäťových čipov pre Atari ST ROM Cartridge v2.

Každá položka obsahuje všetky parametre potrebné na prípravu, rozdelenie
a verifikáciu ROM obrazov pre daný typ čipu.
"""

CHIPS: dict[str, dict] = {
    "w29c040": {
        "name":          "Winbond W29C040-90B",
        "chip_size":     512 * 1024,   # 512 KB na čip (8-bit)
        "num_banks":     8,
        "bank_per_chip": 64 * 1024,    # 64 KB na bank na čip
        "bank_combined": 128 * 1024,   # 128 KB na bank (kombinovaný 16-bit obraz)
        "erase_byte":    0xFF,          # mazaný stav flash bunky
        "notes":         [],
    },
    "tc57h1000": {
        "name":          "Toshiba TC57H1000AD-85",
        "chip_size":     128 * 1024,   # 128 KB na čip (8-bit), A0–A16
        "num_banks":     2,            # len A16 je efektívny (SW1-1); A17→NC, A18→VPP
        "bank_per_chip": 64 * 1024,
        "bank_combined": 128 * 1024,
        "erase_byte":    0xFF,
        "notes": [
            "SW1-3 musí ostať OPEN — pin 1 je VPP (+5 V cez R3); skratovanie na GND môže zničiť čip.",
            "SW1-2 je irelevantný — pin 30 je NC (not connected).",
            "Dostupné sú len 2 banky (iba SW1-1 / A16 je aktívny bank select).",
        ],
    },
}

CHIP_ALIASES: dict[str, str] = {
    "w29c040-90b":    "w29c040",
    "winbond":        "w29c040",
    "tc57h1000ad":    "tc57h1000",
    "tc57h1000ad-85": "tc57h1000",
    "toshiba":        "tc57h1000",
}


def resolve_chip(key: str) -> dict:
    """Vráti chip dict pre daný kľúč alebo alias. Vyhodí ValueError ak neexistuje."""
    k = key.lower().strip()
    k = CHIP_ALIASES.get(k, k)
    if k not in CHIPS:
        valid = list(CHIPS.keys())
        raise ValueError(f"Neznámy čip '{key}'. Platné hodnoty: {valid}")
    return CHIPS[k]


def chip_key(key: str) -> str:
    k = key.lower().strip()
    return CHIP_ALIASES.get(k, k)


def combined_size(chip: dict) -> int:
    """Celková veľkosť kombinovaného 16-bit obrazu (= 2 × chip_size)."""
    return chip["chip_size"] * 2


def align_up(size: int, boundary: int) -> int:
    return (size + boundary - 1) & ~(boundary - 1)


def split_to_chips(combined: bytes | bytearray) -> tuple[bytearray, bytearray]:
    """
    De-interleave kombinovaného obrazu na chip súbory.

    Kombinovaný obraz (big-endian, 68000 formát):
      offset 0: high byte slova na $FAxxxx  → U2 (D8–D15)
      offset 1: low  byte slova na $FAxxxx  → U1 (D0–D7)
      offset 2: high byte nasledujúceho slova → U2
      ...

    Returns: (u1_lo, u2_hi)
    """
    u2 = bytearray(combined[0::2])  # párne offsety → hi byte → U2
    u1 = bytearray(combined[1::2])  # nepárne offsety → lo byte → U1
    return u1, u2


def merge_from_chips(u1: bytes | bytearray, u2: bytes | bytearray) -> bytearray:
    """Spoji U1 (lo) a U2 (hi) chip súbory späť do kombinovaného obrazu."""
    if len(u1) != len(u2):
        raise ValueError(f"U1 ({len(u1)} B) a U2 ({len(u2)} B) musia mať rovnakú veľkosť.")
    combined = bytearray(len(u1) * 2)
    combined[0::2] = u2
    combined[1::2] = u1
    return combined
