#!/usr/bin/env python3
"""
rom_validate.py — Validácia ROM obrazov pre Atari ST ROM Cartridge v2.

Overuje súbory v adresári (alebo priamo zadané súbory) voči:
  - veľkosti a zarovnaniu na hranice bankov
  - kompatibilite s W29C040 / TC57H1000
  - magickým konštantám a štruktúre GEMDOS hlavičky
  - obsahu bankov (obsadené / prázdne, naplnenosť)
  - platnosti prvej 68000 inštrukcie na začiatku každého banku

Použitie:
  python3 rom_validate.py out/                     # skenuj adresár
  python3 rom_validate.py combined.bin             # jeden súbor
  python3 rom_validate.py out/*.bin                # wildcard
  python3 rom_validate.py out/ --detail            # aj per-bank tabuľky
  python3 rom_validate.py out/ --chip tc57h1000    # pre TC57H1000
"""

import argparse
import hashlib
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from chips import CHIPS, combined_size, split_to_chips, merge_from_chips


# ---------------------------------------------------------------------------
# Magické konštanty
# ---------------------------------------------------------------------------

# (popis, stav)  — stav: OK / WARN / FAIL
MAGIC_TABLE: dict[int, tuple[str, str]] = {
    # GEMDOS/TOS spustiteľný program — TOS ho automaticky spustí z cartridge
    0x601A: ("GEMDOS exec (TOS autoboot)",    "OK"),
    0x601C: ("GEMDOS exec (variant)",         "OK"),
    # 68000 priamy kód — rôzne platné otváracie inštrukcie
    0x4EF9: ("JMP abs.l",                     "OK"),
    0x4EB9: ("JSR abs.l",                     "OK"),
    0x6000: ("BRA.W (branch word-sized)",     "OK"),
    0x48E7: ("MOVEM.L regs,-(SP)",            "OK"),
    0x2F3C: ("MOVE.L #imm,-(SP)",             "OK"),
    0x41FA: ("LEA d(PC),A0",                  "OK"),
    0x43FA: ("LEA d(PC),A1",                  "OK"),
    0x207C: ("MOVEA.L #abs,A0",               "OK"),
    0x227C: ("MOVEA.L #abs,A1",               "OK"),
    0x4E56: ("LINK A6,#n (C prologue)",       "OK"),
    # Podozrivé — platné inštrukcie, ale neobvyklé na začiatku ROM
    0x4E71: ("NOP",                           "WARN"),
    0x4E75: ("RTS (bad first instr)",         "WARN"),
    0x4E73: ("RTE (bad first instr)",         "WARN"),
    0x4E77: ("RTR (bad first instr)",         "WARN"),
    0x4E4F: ("TRAP #15",                      "WARN"),
    # Jednoznačne neplatné
    0x60FE: ("BRA.S *-0 (infinite loop!)",    "FAIL"),
    0x4AFC: ("ILLEGAL",                       "FAIL"),
    0xFFFF: ("Flash erased (0xFF fill)",      "FAIL"),
    0x0000: ("All-zero memory",               "FAIL"),
}

# Rozsah BRA.B inštrukcií: horný bajt = 0x60, dolný = 0x01..0xFD alebo 0xFF
def _classify_magic(word: int) -> tuple[str, str]:
    if word in MAGIC_TABLE:
        return MAGIC_TABLE[word]
    hi, lo = (word >> 8) & 0xFF, word & 0xFF
    if hi == 0x60 and lo not in (0x00, 0xFE):
        sign = "+" if lo < 0x80 else "-"
        off  = lo if lo < 0x80 else lo - 256
        return (f"BRA.B {sign}{abs(off)} bytes", "OK")
    if hi == 0x60 and lo == 0xFF:
        return ("BRA.B -1 (unusual)", "WARN")
    # Horné bity 00/01/10 sú bežné 68000 inštrukcie (MOVE, ADD, AND...)
    if (hi >> 6) in (0b00, 0b01, 0b10, 0b11):
        return (f"68000 inštrukcia (0x{word:04X})", "INFO")
    return (f"neznáma hodnota (0x{word:04X})", "WARN")


# ---------------------------------------------------------------------------
# GEMDOS hlavička
# ---------------------------------------------------------------------------

GEMDOS_MAGIC  = 0x601A
GEMDOS_HLEN   = 28  # bajtov

def _parse_gemdos(data: bytes) -> Optional[dict]:
    """Parsuje GEMDOS hlavičku ak magic = 0x601A. Vracia dict alebo None."""
    if len(data) < GEMDOS_HLEN:
        return None
    magic = struct.unpack_from(">H", data, 0)[0]
    if magic != GEMDOS_MAGIC:
        return None
    tlen, dlen, blen, slen = struct.unpack_from(">LLLL", data, 2)
    rsvd, pflags           = struct.unpack_from(">LL",   data, 18)
    absflag                = struct.unpack_from(">H",    data, 26)[0]

    issues: list[str] = []
    if rsvd != 0:
        issues.append(f"RSVD1=0x{rsvd:08X} ≠ 0")
    if absflag not in (0, 1):
        issues.append(f"ABSFLAG=0x{absflag:04X} (očakáva sa 0/1)")
    if tlen == 0:
        issues.append("TLEN=0 (prázdny text segment)")
    code_total = tlen + dlen
    available  = max(0, len(data) - GEMDOS_HLEN)
    if code_total > available:
        issues.append(f"seg ({tlen}+{dlen}={code_total} B) > dostupné ({available} B)")

    return {
        "tlen": tlen, "dlen": dlen, "blen": blen, "slen": slen,
        "rsvd": rsvd, "pflags": pflags, "absflag": absflag,
        "issues": issues,
        "valid": len(issues) == 0,
    }


# ---------------------------------------------------------------------------
# Detekcia formátu
# ---------------------------------------------------------------------------

SIZE_64K  = 64  * 1024
SIZE_128K = 128 * 1024

@dataclass
class FormatHit:
    chip_key:   str    # "w29c040" / "tc57h1000"
    kind:       str    # "combined" / "chip" / "bank"
    banks:      int    # počet bankov v súbore
    max_banks:  int    # maximálny počet bankov pre daný čip
    full:       bool   # súbor plne využíva čip

def _detect_formats(size: int) -> list[FormatHit]:
    hits: list[FormatHit] = []
    for ckey, chip in CHIPS.items():
        bpc = chip["bank_per_chip"]   # 64 KB
        bc  = chip["bank_combined"]   # 128 KB
        cs  = chip["chip_size"]       # max na čip
        nb  = chip["num_banks"]

        # combined: násobok 128 KB, max = 2 × cs
        if size % bc == 0 and 0 < size <= cs * 2:
            banks = size // bc
            hits.append(FormatHit(ckey, "combined", banks, nb, banks == nb))

        # chip (lo alebo hi): násobok 64 KB, max = cs
        if size % bpc == 0 and 0 < size <= cs:
            banks = size // bpc
            # vyhni sa duplikátu ak je to zároveň "combined" pre TC57H1000 128KB
            already = any(h.chip_key == ckey and h.kind == "combined" and h.banks == banks
                          for h in hits)
            if not already:
                hits.append(FormatHit(ckey, "chip", banks, nb, banks == nb))

    return hits


def _short_format(hits: list[FormatHit]) -> str:
    if not hits:
        return "neznámy"
    # prednostne zobraz combined, potom chip
    ordered = sorted(hits, key=lambda h: (h.kind != "combined", h.chip_key))
    parts = []
    seen = set()
    for h in ordered:
        label = f"{h.kind}({h.chip_key[:3].upper()})"
        if label not in seen:
            parts.append(label)
            seen.add(label)
    return " / ".join(parts[:3])


def _compat_str(hits: list[FormatHit]) -> str:
    keys = sorted({h.chip_key for h in hits})
    if set(keys) == {"w29c040", "tc57h1000"}:
        return "oba"
    return " / ".join(CHIPS[k]["name"].split()[0] for k in keys) if keys else "—"


# ---------------------------------------------------------------------------
# Analýza obsahu
# ---------------------------------------------------------------------------

def _fill_pct(data: bytes | bytearray, fill: int = 0xFF) -> float:
    """Percento NENAPLNENÝCH bajtov (obsah ≠ fill)."""
    return sum(1 for b in data if b != fill) / len(data) * 100 if data else 0.0


def _count_used_banks(data: bytes | bytearray, bank_size: int, fill: int = 0xFF) -> int:
    count = 0
    for i in range(0, len(data), bank_size):
        chunk = data[i:i + bank_size]
        if any(b != fill for b in chunk):
            count += 1
    return count


def _sha1(data: bytes | bytearray) -> str:
    return hashlib.sha1(data).hexdigest()[:10]


# ---------------------------------------------------------------------------
# Hlavná dátová štruktúra výsledku
# ---------------------------------------------------------------------------

@dataclass
class FileResult:
    path:         Path
    size:         int
    formats:      list[FormatHit]
    # analýza pre combined (ak bol formát jednoznačne určený)
    magic_word:   Optional[int]      = None
    magic_desc:   str                = "—"
    magic_status: str                = "—"
    gemdos:       Optional[dict]     = None
    fill_pct:     float              = 0.0     # % obsadených (≠ 0xFF) bajtov
    banks_used:   int                = 0
    banks_total:  int                = 0
    sha1:         str                = ""
    # stav
    status:       str                = "FAIL"
    notes:        list[str]          = field(default_factory=list)
    # per-bank detail (len pre combined)
    bank_details: list[dict]         = field(default_factory=list)


def analyse_file(path: Path) -> FileResult:
    r = FileResult(path=path, size=0, formats=[])

    if not path.exists():
        r.notes.append("súbor neexistuje")
        return r

    data = path.read_bytes()
    r.size    = len(data)
    r.sha1    = _sha1(data)
    r.formats = _detect_formats(r.size)

    if not r.formats:
        r.status = "FAIL"
        kb = r.size / 1024
        r.notes.append(
            f"veľkosť {kb:.1f} KB nie je násobok 64 KB ani nie je kompatibilná"
            f" so žiadnym čipom"
        )
        return r

    # Preferujeme combined formát pre ďalšiu analýzu
    combined_hits = [h for h in r.formats if h.kind == "combined"]
    primary = combined_hits[0] if combined_hits else r.formats[0]
    chip    = CHIPS[primary.chip_key]

    # Naplnenosť
    r.fill_pct = _fill_pct(data, chip["erase_byte"])

    if primary.kind == "combined":
        bc = chip["bank_combined"]
        bpc = chip["bank_per_chip"]

        r.banks_total = primary.banks
        r.banks_used  = _count_used_banks(data, bc, chip["erase_byte"])

        # Magic na začiatku celého obrazu (prvé 16-bit slovo = $FA0000)
        if len(data) >= 2:
            r.magic_word   = struct.unpack_from(">H", data, 0)[0]
            r.magic_desc, r.magic_status = _classify_magic(r.magic_word)

        # GEMDOS hlavička
        if r.magic_word == GEMDOS_MAGIC:
            r.gemdos = _parse_gemdos(data)

        # Per-bank detail
        for b in range(primary.banks):
            off   = b * bc
            chunk = data[off:off + bc]
            u1, u2 = split_to_chips(chunk)
            first_word = struct.unpack_from(">H", chunk, 0)[0] if len(chunk) >= 2 else None
            last_word  = struct.unpack_from(">H", chunk, -2)[0] if len(chunk) >= 2 else None
            empty      = all(bb == chip["erase_byte"] for bb in chunk)
            m_desc, m_st = _classify_magic(first_word) if first_word is not None else ("—", "—")
            r.bank_details.append({
                "bank":       b,
                "empty":      empty,
                "fill_pct":   _fill_pct(chunk, chip["erase_byte"]),
                "first_word": first_word,
                "last_word":  last_word,
                "magic_desc": m_desc,
                "magic_st":   m_st,
                "sha1":       _sha1(chunk),
            })
    else:
        # chip alebo bank súbor
        bpc = chip["bank_per_chip"]
        r.banks_total = primary.banks
        r.banks_used  = _count_used_banks(data, bpc, chip["erase_byte"])
        r.magic_desc  = "— (chip súbor: magic je rozdelený medzi LO a HI)"
        r.magic_status = "INFO"

    # --- Určenie celkového stavu ---
    r.status = _determine_status(r, primary)
    return r


def _determine_status(r: FileResult, primary: FormatHit) -> str:
    # FAIL podmienky
    if r.fill_pct == 0.0:
        r.notes.append("súbor je prázdny (všetky bajty = 0xFF)")
        return "FAIL"
    if r.magic_status == "FAIL":
        r.notes.append(f"neplatná magic hodnota: {r.magic_desc}")
        return "FAIL"
    if r.banks_used == 0:
        r.notes.append("žiadny bank neobsahuje dáta")
        return "FAIL"

    # WARN podmienky
    warns = []
    if r.magic_status == "WARN":
        warns.append(f"podozrivá magic: {r.magic_desc}")
    if r.banks_used < r.banks_total and primary.kind == "combined":
        warns.append(f"obsadené {r.banks_used}/{r.banks_total} bankov")
    if r.gemdos and not r.gemdos["valid"]:
        warns.append("GEMDOS hlavička má chyby: " + "; ".join(r.gemdos["issues"]))
    if r.fill_pct < 5.0:
        warns.append(f"veľmi málo obsahu ({r.fill_pct:.1f}%)")

    if warns:
        r.notes.extend(warns)
        return "WARN"

    return "PASS"


# ---------------------------------------------------------------------------
# Výstup — tabuľky
# ---------------------------------------------------------------------------

COL_STATUS = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL", "INFO": "INFO"}

STATUS_MARK = {"PASS": "✓", "WARN": "!", "FAIL": "✗", "INFO": "i"}


def _trunc(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _fmt_size(n: int) -> str:
    if n == 0:
        return "0 B"
    if n % (1024 * 1024) == 0:
        return f"{n // (1024*1024)} MB"
    if n % 1024 == 0:
        return f"{n // 1024} KB"
    return f"{n} B"


def print_main_table(results: list[FileResult]):
    # Hlavička
    H = {
        "file":    "Súbor",
        "size":    "Veľkosť",
        "fmt":     "Formát",
        "compat":  "Čip",
        "banks":   "Banky",
        "fill":    "Obsah",
        "magic":   "Magic",
        "mdesc":   "Popis magic",
        "status":  "Stav",
    }

    # Dynamická šírka stĺpca Súbor podľa najdlhšieho mena
    max_name = max((len(r.path.name) for r in results), default=len(H["file"]))
    W_FILE = max(max_name, len(H["file"]))
    W_FILE = min(W_FILE, 30)

    W = {
        "file":   W_FILE,
        "size":   8,
        "fmt":    22,
        "compat": 12,
        "banks":  9,
        "fill":   7,
        "magic":  8,
        "mdesc":  28,
        "status": 5,
    }

    sep_len = sum(W.values()) + len(W) * 2 + 1

    def row(*vals):
        keys = list(W.keys())
        return "  " + "  ".join(
            str(v).ljust(W[k]) if k != "status" else str(v).center(W[k])
            for k, v in zip(keys, vals)
        )

    hdr = row(H["file"], H["size"], H["fmt"], H["compat"],
              H["banks"], H["fill"], H["magic"], H["mdesc"], H["status"])
    sep = "  " + "  ".join("─" * W[k] for k in W)

    print(hdr)
    print(sep)

    for r in results:
        name    = _trunc(r.path.name, W["file"])
        size_s  = _fmt_size(r.size)
        fmt_s   = _trunc(_short_format(r.formats), W["fmt"])
        compat  = _trunc(_compat_str(r.formats), W["compat"])
        banks_s = (f"{r.banks_used}/{r.banks_total}"
                   if r.banks_total > 0 else "—")
        fill_s  = f"{r.fill_pct:.1f}%" if r.fill_pct > 0 else "0%"
        magic_s = (f"0x{r.magic_word:04X}" if r.magic_word is not None else "—")
        mdesc   = _trunc(r.magic_desc, W["mdesc"])
        status  = r.status

        print(row(name, size_s, fmt_s, compat, banks_s, fill_s, magic_s, mdesc, status))

        # Poznámky pod riadkom súboru (len WARN/FAIL)
        if r.status in ("WARN", "FAIL") and r.notes:
            for note in r.notes:
                print(f"  {'':>{W_FILE}}  {_trunc(note, sep_len - W_FILE - 4)}")


def print_gemdos_detail(r: FileResult):
    if not r.gemdos:
        return
    g = r.gemdos
    valid = "platná" if g["valid"] else "CHYBNÁ"
    print(f"\n  GEMDOS hlavička @ {r.path.name}  ({valid})")
    print(f"    magic   = 0x601A  (BRA.S +26 — preskočí 28-bajtovú hlavičku)")
    print(f"    TLEN    = {g['tlen']:>10} B  (text segment)")
    print(f"    DLEN    = {g['dlen']:>10} B  (data segment)")
    print(f"    BLEN    = {g['blen']:>10} B  (BSS segment)")
    print(f"    SLEN    = {g['slen']:>10} B  (tabuľka symbolov)")
    print(f"    PFLAGS  = 0x{g['pflags']:08X}")
    print(f"    ABSFLAG = {g['absflag']}  "
          f"({'bez relokovania' if g['absflag'] == 1 else 'vyžaduje relokovanie'})")
    if g["issues"]:
        for issue in g["issues"]:
            print(f"    ⚠  {issue}")


def print_bank_table(r: FileResult):
    if not r.bank_details:
        return
    print(f"\n  Banky — {r.path.name}")
    print(f"  {'Bank':>4}  {'Stav':>8}  {'Fill':>6}  {'Prvé slovo':>10}  "
          f"{'Posl. slovo':>11}  {'Magic / Inštrukcia':<30}  {'SHA-1':>10}")
    print(f"  {'─'*4}  {'─'*8}  {'─'*6}  {'─'*10}  {'─'*11}  {'─'*30}  {'─'*10}")
    for bd in r.bank_details:
        b     = bd["bank"]
        stav  = "prázdny" if bd["empty"] else "OBSADENÝ"
        fill  = f"{bd['fill_pct']:.1f}%"
        fw    = f"0x{bd['first_word']:04X}" if bd["first_word"] is not None else "—"
        lw    = f"0x{bd['last_word']:04X}"  if bd["last_word"]  is not None else "—"
        mdesc = _trunc(bd["magic_desc"], 30)
        sha   = bd["sha1"]
        print(f"  {b:>4}  {stav:>8}  {fill:>6}  {fw:>10}  {lw:>11}  {mdesc:<30}  {sha:>10}")


def print_summary(results: list[FileResult]):
    total = len(results)
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for r in results:
        if r.status in counts:
            counts[r.status] += 1
    print(f"\n  Súhrn: {total} súborov  │  "
          f"{counts['PASS']} PASS  │  {counts['WARN']} WARN  │  {counts['FAIL']} FAIL")


# ---------------------------------------------------------------------------
# Vyhľadávanie súborov
# ---------------------------------------------------------------------------

def collect_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for s in inputs:
        p = Path(s)
        if p.is_dir():
            found = sorted(p.glob("*.bin"))
            if not found:
                print(f"  Adresár {p} neobsahuje žiadne .bin súbory.")
            paths.extend(found)
        elif p.exists():
            paths.append(p)
        else:
            # Môže ísť o glob expanziu shellu ktorú Python nedostal (ak bol v úvodzovkách)
            import glob
            expanded = sorted(glob.glob(s))
            if expanded:
                paths.extend(Path(e) for e in expanded)
            else:
                print(f"  VAROVANIE: {s} nenájdený, preskakujem.")
    return paths


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Validácia ROM obrazov pre Atari ST ROM Cartridge v2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Príklady:
  python3 rom_validate.py out/
  python3 rom_validate.py combined.bin chip_u1_lo.bin chip_u2_hi.bin
  python3 rom_validate.py out/ --detail
  python3 rom_validate.py out/ --chip tc57h1000
        """,
    )
    p.add_argument("inputs", nargs="+", metavar="SÚBOR_ALEBO_ADRESÁR",
                   help="Súbor(y) .bin alebo adresár na skenovanie")
    p.add_argument("--detail", action="store_true",
                   help="Vypísať per-bank tabuľku a GEMDOS detail pre každý combined obraz")
    p.add_argument("--chip", default=None, metavar="TYP",
                   help="Filtrovať výsledky pre konkrétny čip (w29c040 / tc57h1000)")
    args = p.parse_args()

    paths = collect_paths(args.inputs)
    if not paths:
        print("Žiadne súbory na validáciu.")
        sys.exit(1)

    # Prehľad vstupov
    dirs = sorted({str(p.parent) for p in paths})
    print(f"╔══ rom_validate ════════════════════════════════════════════")
    for d in dirs:
        print(f"║  Adresár: {d}")
    print(f"║  Súborov: {len(paths)}")
    if args.chip:
        print(f"║  Filter čipu: {args.chip}")
    print(f"╚═══════════════════════════════════════════════════════════")
    print()

    results = [analyse_file(path) for path in paths]

    # Filter podľa čipu ak bol zadaný
    if args.chip:
        from chips import chip_key as resolve_key
        ckey = resolve_key(args.chip)
        results = [r for r in results
                   if any(h.chip_key == ckey for h in r.formats)]

    if not results:
        print("  Žiadne súbory nezodpovedajú kritériám.")
        sys.exit(0)

    # Hlavná tabuľka
    print_main_table(results)
    print_summary(results)

    # Detail pre combined obrazy
    if args.detail:
        for r in results:
            has_combined = any(h.kind == "combined" for h in r.formats)
            if has_combined:
                print_bank_table(r)
                print_gemdos_detail(r)

    print()
    # Návratový kód: 1 ak existuje aspoň jeden FAIL
    fail_count = sum(1 for r in results if r.status == "FAIL")
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
