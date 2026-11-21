# Atari ST ROM Cartridge v2 — 2× W29C040-90B (16-bit)

**KiCad 10 projekt · Rev 1.1 · 2026-11-08 · risapav**  
https://github.com/risapav/atari-st-cart-v02

ROM cartridge PCB (len na čítanie) pre rodinu Atari ST/STE/Mega.  
Dva Flash EEPROM Winbond W29C040-90B pracujú paralelne a zabezpečujú plnú 16-bitovú dátovú zbernicu.  
3-polohový DIP prepínač vyberá jeden z 8 bankov po 128 KB, čo dáva až **1 MB** bankovej ROM pamäte.

---

## Vlastnosti

| Vlastnosť | Detail |
|---|---|
| Dátová zbernica | 16-bit (U1 → D0–D7 nižší bajt, U2 → D8–D15 vyšší bajt) |
| ROM čipy | 2× Winbond W29C040-90B (512 K × 8, DIP-32, 90 ns) |
| Celková kapacita | 1 MB (8 bankov × 128 KB) |
| Adresové okno | `$FA0000`–`$FBFFFF` (256 KB viditeľných naraz) |
| Prepínanie bankov | 3-bitový DIP prepínač (SW1) na čipových A16–A18 |
| Chip select | Wired-AND z /ROM3 + /ROM4 cez BAT42 diódy + 10 kΩ pull-up |
| Ochrana zápisu | /WE trvalo pripojený na +5 V — ST nemôže zapisovať do čipu |
| Rozmer dosky | 42 × 68 mm |
| Konektor | 40-pinový dvojradový hranový konektor, rozstup 2 mm (Atari CB101494) |

---

## Mapovanie adries

Atari ST procesor 68000 nevystavuje A0 — výber bajtu sa robí cez /UDS a /LDS.  
Cartridge port poskytuje A1–A15, /ROM3, /ROM4, /UDS, /LDS, D0–D15.

```
Signál ST zbernice  →   Pin W29C040
─────────────────────────────────────
A1  – A15           →   A0  – A14   (15 bitov)
/ROM4               →   A15         (0 = oblasť $FA, 1 = oblasť $FB)
SW1-1 (A16)         →   A16         ┐
SW1-2 (A17)         →   A17         ├ výber banku (8 bankov)
SW1-3 (A18)         →   A18         ┘
/ROM3 AND /ROM4     →   /CE (oba čipy, wired-AND)
/LDS                →   /OE na U1 (D0–D7, čip nižšieho bajtu)
/UDS                →   /OE na U2 (D8–D15, čip vyššieho bajtu)
/WE                 →   +5V (ochrana zápisu)
```

Celé 256 KB okno (`$FA0000`–`$FBFFFF`) je rozdelené signálom /ROM4:

| /ROM4 | /ROM3 | Oblasť | Čip A15 |
|---|---|---|---|
| LOW  | HIGH | `$FA0000`–`$FAFFFF` | 0 |
| HIGH | LOW  | `$FB0000`–`$FBFFFF` | 1 |

Oba čipy sú aktivované len keď sú **oba** /ROM3 aj /ROM4 aktívne (wired-AND cez D1, D2).

---

## Výber banku (DIP prepínač SW1)

Zatvorený = 0 (GND cez prepínač) · Otvorený = 1 (cez 10 kΩ na +5 V)

| SW1-3 | SW1-2 | SW1-1 | Bank | Offset v čipe |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0x000000 |
| 0 | 0 | 1 | 1 | 0x010000 |
| 0 | 1 | 0 | 2 | 0x020000 |
| 0 | 1 | 1 | 3 | 0x030000 |
| 1 | 0 | 0 | 4 | 0x040000 |
| 1 | 0 | 1 | 5 | 0x050000 |
| 1 | 1 | 0 | 6 | 0x060000 |
| 1 | 1 | 1 | 7 | 0x070000 |

Každý bank obsahuje 128 KB viditeľných cez cartridge okno ST.  
U1 a U2 sa programujú samostatne (každý čip nesie jeden bajt každého 16-bitového slova).  
Každý čip obsahuje 64 KB na bank (0x10000 bajtov); kombinovaný 16-bitový obsah na bank je 128 KB.

---

## Zoznam materiálu

| Ref | Hodnota / Diel | Puzdro | LCSC | Poznámka |
|---|---|---|---|---|
| U1, U2 | Winbond W29C040-90B | DIP-32 W15.24 mm | C2331 | 512 K × 8 Flash EEPROM, 90 ns |
| J1 | Atari ST cartridge port | 2×20 hranový, rozstup 2 mm | — | kompatibilný CB101494 |
| SW1 | 3-polohový posuvný DIP prepínač | THT 7.62 mm rozstup | C501525 | výber banku A16–A18 |
| D1, D2 | BAT42 | DO-35 axiálny | C2798198 | wired-AND pre /CE |
| R1 | 10 kΩ | axiálny | C2903232 | pull-up pre čip A16 |
| R2 | 10 kΩ | axiálny | C2903232 | pull-up pre čip A17 |
| R3 | 10 kΩ | axiálny | C2903232 | pull-up pre čip A18 (aj VPP pre TC57H1000) |
| R4 | 10 kΩ | axiálny | C2903232 | pull-up na uzle wired-AND /CE |
| C1, C2 | 100 nF | 0805 | C83055 | blokovací kondenzátor, jeden na čip |

### Alternatívny čip: TC57H1000AD-85

TC57H1000AD-85 (Toshiba 1 M × 8 SRAM) možno použiť namiesto W29C040 s týmito úpravami:

| Poloha SW1 | Nastavenie | Dôvod |
|---|---|---|
| SW1-3 (A18 / VPP) | **otvorený** | VPP musí byť +5 V; pull-up R3 to zabezpečuje |
| SW1-2 (A17 / pin 30) | ignorovať | pin 30 je NC na TC57H1000 |
| SW1-1 (A16) | podľa potreby | aktívny výber banku |

---

## Logika aktivácie čipov

```
/ROM3 ──|<|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|<|── D1 ──┴── /CE (U1 pin 22, U2 pin 22)
```

`|<|` = Katóda (K) na strane signálu, Anóda (A) na strane /CE.

Diódy D1 a D2 realizujú pasívny wired-OR na aktívne-nízke signály: /CE sa prepne na LOW kedykoľvek je **niektorý** z /ROM3 alebo /ROM4 LOW.  
Keď sú oba signály HIGH (žiadny prístup), R4 (10 kΩ) drží /CE HIGH (čipy deaktivované).  
V praxi /ROM3 a /ROM4 nie sú nikdy oba LOW súčasne na zbernici ST, takže to efektívne aktivuje čipy pri prístupe do KTOREJKOĽVEK oblasti.

---

## Obsah repozitára

```
cart_v02/
├── cart_v02.kicad_pro      — súbor projektu KiCad 10
├── cart_v02.kicad_sch      — schéma
├── cart_v02.kicad_pcb      — layout DPS
├── my-libs/                — projektové knižnice symbolov a footprintov
├── production/             — výrobné výstupy (rev 1.1)
│   ├── Atari_ST_ROM_Cartridge_v2__2_W29C040-90B_16-bit_1.1.zip
│   ├── bom.csv
│   ├── designators.csv
│   ├── netlist.ipc
│   └── positions.csv
├── tools/                  — Python skripty na prípravu ROM obrazov
│   ├── chips.py            — definície čipov (W29C040, TC57H1000)
│   ├── rom_pack.py         — zabaľ adresár alebo zoznam súborov → chip súbory (auto-strip STC)
│   ├── rom_split.py        — rozdeľ kombinovaný 16-bit obraz → LO + HI
│   ├── rom_info.py         — zobraz mapu bankov a štatistiky čipov
│   ├── rom_validate.py     — validuj ROM súbory (.bin/.stc/.rom/.img): veľkosť, magic, strip STC
│   ├── Makefile            — skratky: pack / split / info / validate (PRGDIR=prg/)
│   ├── README.md           — plná dokumentácia nástrojov (SK)
│   ├── README_en.md        — plná dokumentácia nástrojov (EN)
│   └── prg/                — zdrojové ROM obrazy (predvolený vstup pre make pack)
├── doc/
│   ├── functional_analysis.md    — dekódovanie adries, CE logika, ROM formáty (EN)
│   └── functional_analysis_sk.md — dekódovanie adries, CE logika, ROM formáty (SK)
└── test/                   — simulácia virtuálneho cartridge (Python)
    ├── cartridge_model.py  — hardvérový model zbernice cartridge
    ├── generate_test_roms.py
    ├── run_tests.py        — 73 testov: dekódovanie adries, prepínanie bankov, CE logika
    └── TESTING.md          — metodológia testov a výsledky
```

### Závislosť od knižníc KiCad

Vlastné symboly a footprinty sú zabalené v `my-libs/` a odkazované s cestami `${KIPRJMOD}`
v `fp-lib-table` a `sym-lib-table`.  
Nie je potrebná žiadna globálna inštalácia knižníc — stačí otvoriť `cart_v02.kicad_pro` priamo.

---

## Programovanie čipov

Každý čip je 512 K × 8 a musí byť naprogramovaný **mimo obvodu** (vybrať zo socketu DIP).

Adresár `tools/` obsahuje Python skripty, ktoré automatizujú všetky kroky prípravy:

Všetky zdrojové ROM obrazy (`.bin`, `.rom`, `.img`, `.stc`) ulož do `tools/prg/`.
Nástroje tento adresár používajú ako predvolené miesto pre zdrojové súbory.

```bash
cd tools/

# Validácia zdrojových obrazov
python3 rom_validate.py prg/

# Zabalenie všetkých obrazov z prg/ → chip súbory  (adresár skenovaný automaticky,
# názvy s medzerami spracované správne, Steem .STC hlavičky odstrihnuté)
make pack
# — alebo ekvivalentne: python3 rom_pack.py prg/
# → zapíše prg/pack_order.txt a out/bank{N}_{original_name} kópie

# Zobrazenie mapy bankov a podpisov čipov
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin
```

**Zmena poradia bankov:** uprav `prg/pack_order.txt` (jedno meno súboru na riadok) a spusti `make pack` znova.  
Číslované kópie v `out/bank{N}_*` vždy odrážajú aktuálne priradenie bankov.

Alebo s explicitným zoznamom súborov / iným adresárom:

```bash
make pack PRGDIR=myroms/
make pack SRCS="game.bin other.rom"   # bez medzier v názvoch súborov
```

Manuálny postup (bez skriptov):

1. Priprav dva binárne súbory de-interleave-ovaním kombinovaného ROM obrazu:
   - `chip_u2_hi.bin` — párne bajty (D8–D15, vyšší bajt) → **U2**
   - `chip_u1_lo.bin` — nepárne bajty (D0–D7, nižší bajt) → **U1**
2. Pre bankovaný obraz umiestni každý bank na offset `bank × 0x10000` v každom chip súbore.
3. Naprogramuj každý chip súbor do príslušného čipu pomocou programátora kompatibilného s W29C040.
4. Vlož čipy so správnou orientáciou (pin 1 pri zárezu).
5. Nastav SW1 na požadovaný bank.

> W29C040-90B podporuje in-system Software Data Protection (SDP).  
> Deaktivuj SDP pred programovaním, ak to tvoj programátor vyžaduje.

Pozri `tools/README.md` (SK) alebo `tools/README_en.md` (EN) pre plnú dokumentáciu vrátane podpory TC57H1000AD-85.

---

## Licencia

Hardvérový návrh vydaný pod [CERN-OHL-P v2](https://ohwr.org/cern_ohl_p_v2.txt) (permisívna).
