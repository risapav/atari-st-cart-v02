# ROM Tools — Atari ST ROM Cartridge v2

Sada Python skriptov na prípravu ROM programov pre fyzické programovanie čipov
kartridžu `cart_v02`. Skripty riešia zarovnanie na hranice bankov, zreťazenie
viacerých programov a rozdelenie výsledného obrazu na LO (U1) a HI (U2) chip súbory.

---

## Súbory

| Súbor | Popis |
|---|---|
| `chips.py` | Definície čipov a spoločné funkcie (importované ostatnými skriptmi) |
| `rom_pack.py` | Zabaľ a zreťaz ROM programy → chip súbory |
| `rom_split.py` | Rozdeľ existujúci kombinovaný 16-bit obraz → LO + HI |
| `rom_info.py` | Zobraz štatistiky a mapu bankov chip súborov |
| `rom_validate.py` | Validuj ROM súbory — veľkosť, magic, obsah, GEMDOS hlavička |
| `Makefile` | Skratky pre bežné operácie |

---

## Podporované čipy

### Winbond W29C040-90B (`--chip w29c040`, default)

| Parameter | Hodnota |
|---|---|
| Kapacita na čip | 512 KB (8-bit) |
| Počet bankov | 8 |
| Kombinovaný obraz | 1 MB |
| Bank veľkosť | 128 KB (kombinovaný) / 64 KB (na čip) |

Oba čipy (U1 + U2) sa programujú **oddelene** (vybrať zo socketu).

### Toshiba TC57H1000AD-85 (`--chip tc57h1000`)

| Parameter | Hodnota |
|---|---|
| Kapacita na čip | 128 KB (8-bit), A0–A16 |
| Počet bankov | **2** (len A16 je efektívny) |
| Kombinovaný obraz | 256 KB |
| Bank veľkosť | 128 KB (kombinovaný) / 64 KB (na čip) |

> **POZOR — TC57H1000AD-85:**
> - **SW1-3 musí ostať OPEN** — pin 1 je `VPP` (+5 V cez R3); zatvorenie na GND môže zničiť čip.
> - **SW1-2 je irelevantný** — pin 30 je NC (not connected).
> - Dostupné sú **len 2 banky** (iba SW1-1 / A16 je aktívny bank select).

---

## Formát súborov

### Kombinovaný 16-bit obraz (`combined.bin`)

Štandardný Motorola 68000 big-endian binárny obraz. Každé 16-bitové slovo
je uložené na párnej adrese s high byteom ako prvým:

```
offset 0x000000: high byte slova na ST $FA0000  → U2 (D8–D15)
offset 0x000001: low  byte slova na ST $FA0000  → U1 (D0–D7)
offset 0x000002: high byte slova na ST $FA0002  → U2
offset 0x000003: low  byte slova na ST $FA0002  → U1
...
```

### Chip súbory (LO / HI)

Každý čip dostane **de-interleaved** bajty z kombinovaného obrazu:

| Súbor | Čip | Obsah | Byte strobe |
|---|---|---|---|
| `chip_u1_lo.bin` | U1 | nepárne bajty (D0–D7) | /LDS |
| `chip_u2_hi.bin` | U2 | párne bajty (D8–D15) | /UDS |

```
chip_u1_lo[n] = combined[2n + 1]   (low byte každého slova)
chip_u2_hi[n] = combined[2n + 0]   (high byte každého slova)
```

### Per-bank súbory

Každý bank je 64 KB na čip (= 128 KB kombinovaných). Súbory `bankN_lo.bin`
a `bankN_hi.bin` sú výrezy chip súborov pre priame programovanie jedného banku.

---

## rom_pack.py — zabaľ ROM programy

Načíta jeden alebo viac ROM programov, zarovná každý na hranicu 128 KB banku,
zreťazí ich za sebou a vygeneruje chip súbory.

Podporované vstupné formáty: `.bin`, `.rom`, `.img` — a `.stc` (Steem formát):
4-bajtová nulová hlavička je automaticky odstrihnutá pred zarovnaním.

### Zarovnanie na bank

Každý program sa zaokrúhli **nahor** na násobok 128 KB (bank veľkosť):

```
program 48 KB   → zarovná sa na 128 KB  (1 bank)
program 128 KB  → zostane 128 KB        (1 bank)
program 192 KB  → zarovná sa na 256 KB  (2 banky)
program 300 KB  → zarovná sa na 384 KB  (3 banky)
```

Medzera medzi koncom programu a hranicou banku sa vyplní hodnotou `--pad` (default `0xFF`).

### Zreťazenie

Programy sa zaraďujú do bankov v poradí, v akom sú zadané na príkazovom riadku.
Bank 0 = prvý program, nasledujúci program začína v prvom voľnom banku za ním.

### Príklady

```bash
# Odporúčaný spôsob — zabaľ všetky ROM z adresára prg/ (predvolené)
python3 rom_pack.py prg/
make pack                        # ekvivalent cez Makefile

# Iný zdrojový adresár alebo iný typ čipu
python3 rom_pack.py myroms/ --chip tc57h1000 --out build/
make pack PRGDIR=myroms/ CHIP=tc57h1000 OUTDIR=build/

# Explicitné súbory (bez medzier v názvoch)
python3 rom_pack.py game1.bin game2.bin game3.bin --out build/
make pack SRCS="game1.bin game2.bin" OUTDIR=build/

# Zobraziť rozloženie bez zápisu súborov
python3 rom_pack.py prg/ --dry-run
make dry-run

# Uložiť aj kombinovaný 16-bit obraz
python3 rom_pack.py prg/ --save-combined
make pack-combined

# Vlastný pad bajt (namiesto 0xFF)
python3 rom_pack.py prg/ --pad 0x00
```

> **Medzery v názvoch súborov:** `make pack SRCS="..."` nedokáže správne spracovať
> názvy s medzerami. Odporúčaný postup je vložiť súbory do `prg/` a volať
> `make pack` alebo `python3 rom_pack.py prg/` — cesta adresára medzery neobsahuje.

### Parametre

| Parameter | Default | Popis |
|---|---|---|
| `ROMs / adresár` | (povinné) | Vstupné ROM súbory alebo adresár na skenovanie |
| `--chip` | `w29c040` | Typ čipu: `w29c040` alebo `tc57h1000` |
| `--out` | `out/` | Výstupný adresár |
| `--pad` | `0xFF` | Výplňový bajt pre zarovnanie |
| `--save-combined` | — | Uložiť aj `combined.bin` |
| `--dry-run` | — | Len vypočítaj rozloženie, nič nezapisuj |
| `--force` | — | Pokračuj aj pri prekročení kapacity (oreže dáta) |

### Výstupy

```
out/
├── chip_u1_lo.bin      — plný obraz U1 (512 KB pre W29C040, 128 KB pre TC57H1000)
├── chip_u2_hi.bin      — plný obraz U2
├── bank0_lo.bin        — 64 KB bank 0 pre U1
├── bank0_hi.bin        — 64 KB bank 0 pre U2
├── bank1_lo.bin        — 64 KB bank 1 pre U1
├── bank1_hi.bin        — ...
└── combined.bin        — (iba s --save-combined) kombinovaný 16-bit obraz
```

---

## rom_split.py — rozdeľ kombinovaný obraz

Ak máš existujúci kombinovaný 16-bit ROM obraz (napr. z iného zdroja), tento
skript ho de-interleave-uje na chip súbory.

### Príklady

```bash
# Základné rozdelenie
python3 rom_split.py combined.bin

# TC57H1000, vlastný adresár
python3 rom_split.py combined.bin --chip tc57h1000 --out build/

# Uložiť aj per-bank 64 KB súbory + vypísať mapu bankov
python3 rom_split.py combined.bin --banks --map

# Len zobraziť info, nič nezapisovať
python3 rom_split.py combined.bin --info
```

### Parametre

| Parameter | Default | Popis |
|---|---|---|
| `COMBINED_BIN` | (povinné) | Vstupný kombinovaný 16-bit obraz |
| `--chip` | `w29c040` | Typ čipu |
| `--out` | `out/` | Výstupný adresár |
| `--banks` | — | Uložiť aj per-bank 64 KB súbory |
| `--map` | — | Vypísať mapu bankov po rozdelení |
| `--info` | — | Len zobraziť info, nič nezapisovať |

---

## rom_info.py — info o chip súboroch

Zobrazí štatistiky, mapu bankov a podpisy (prvé slovo každého banku) pre rýchlu
vizuálnu kontrolu chip súborov pred programovaním.

### Príklady

```bash
# Chip súbory LO + HI
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin

# Kombinovaný obraz
python3 rom_info.py --combined combined.bin

# TC57H1000
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin --chip tc57h1000

# Jeden bank (pre bank 2)
python3 rom_info.py out/bank2_lo.bin out/bank2_hi.bin --bank 2
```

---

## rom_validate.py — validácia ROM obrazov

Skontroluje súbory v adresári (alebo priamo zadané súbory) a overí každý voči
sade kritérií. Výstupom je prehľadová tabuľka so stĺpcami veľkosť, formát,
kompatibilita čipu, obsadené banky, magic konštanta a celkový stav `PASS / WARN / FAIL`.

Skenovaný adresár: súbory s príponami `.bin`, `.stc`, `.rom`, `.img` (bez ohľadu na veľkosť písmen).

### Čo sa kontroluje

| Kontrola | Detail |
|---|---|
| Veľkosť a zarovnanie | Súbor musí byť násobok 64 KB; musí sa vmestiť do kapacity čipu |
| Formát STC | Automatické odstrihnutie 4-bajtovej Steem hlavičky (`\x00\x00\x00\x00`) pred 128 KB obrazom |
| Detekcia formátu | `combined` (16-bit interleaved) / `chip` (lo alebo hi) / `bank` (64 KB výrez) |
| Kompatibilita čipu | W29C040 (max 1 MB) / TC57H1000 (max 256 KB) / oba / žiadny |
| Obsah bankov | Počet obsadených bankov, percento naplnenia (≠ 0xFF) |
| Magic konštanta | Prvé 16-bit slovo na $FA0000; klasifikovaný voči 25+ hodnotám |
| GEMDOS hlavička | Ak magic = `0x601A`: parsuje TLEN/DLEN/BLEN/SLEN/ABSFLAG, hlási chyby |
| Per-bank SHA-1 | Kontrolný súčet každého banku pre identifikáciu obsahu |

### Steem STC formát

Steem emulátor ukladá cartridge ROM súbory s 4-bajtovou nulovou hlavičkou pred 128 KB obrazom:

```
offset 0x000000–0x000003:  00 00 00 00   (Steem hlavička)
offset 0x000004–0x020003:  <128 KB ROM obraz>
```

Skript automaticky rozpozná tento formát (veľkosť 131 076 B, prvé 4 bajty nulové) a
hlavičku odstraní pred analýzou. Výsledná veľkosť, magic a banky sa počítajú zo samotného
ROM obsahu. Riadok výstupu obsahuje poznámku `STC: 4-bajtová hlavička odstránená`.

### Magické konštanty

Skript klasifikuje prvé 16-bit slovo kombinovaného obrazu (adresa `$FA0000`):

| Hodnota | Popis | Stav |
|---|---|---|
| `0xFA52` | Atari ST cartridge magic — TOS scanuje cartridge port na `FA52 235F` alebo `FA52 235A` | OK |
| `0xABCD` | `LINE-A #$BCD` — vstupný bod niektorých cartridge programov (napr. Steem STC súbory) | OK |
| `0x601A` | GEMDOS exec magic — TOS tento program automaticky spustí | OK |
| `0x601C` | GEMDOS exec (variant) | OK |
| `0x4EF9` | `JMP abs.l` — priamy ROM kód | OK |
| `0x4EB9` | `JSR abs.l` | OK |
| `0x6000` | `BRA.W` — vetva s 16-bit offsetom | OK |
| `0x60xx` (xx ≠ 00, FE) | `BRA.B ±N` — krátkodobá vetva | OK |
| `0x48E7` | `MOVEM.L regs,-(SP)` — C/ASM prológ | OK |
| `0x41FA`, `0x43FA` | `LEA d(PC),An` — position-independent kód | OK |
| `0x4E71` | `NOP` — neobvyklé na začiatku | WARN |
| `0x4E75` | `RTS` — prvá inštrukcia by nemala byť návrat | WARN |
| `0x60FE` | `BRA.S *-0` — nekonečná slučka | FAIL |
| `0x4AFC` | `ILLEGAL` — zakázaná inštrukcia | FAIL |
| `0xFFFF` | Nevymazaná flash (erase stav) | FAIL |
| `0x0000` | Nulovaná pamäť | FAIL |

Pre magic `0xFA52` skript overí aj druhé slovo a upresní popis: `Atari ST cart magic (FA52/235F)` alebo `Atari ST cart magic (FA52/235A)`.

### Stavy výsledku

| Stav | Podmienka |
|---|---|
| `PASS` | Platná veľkosť, neprázdny obsah, platná prvá inštrukcia |
| `WARN` | Platná veľkosť, ale čiastočne obsadený / neobvyklá magic / chybná GEMDOS hlavička / príliš málo obsahu |
| `FAIL` | Neplatná veľkosť, prázdny súbor (all-0xFF), škodlivá magic (inf. loop, ILLEGAL) |

### Príklady

```bash
# Validácia celého adresára
python3 rom_validate.py out/

# Konkrétne súbory
python3 rom_validate.py combined.bin chip_u1_lo.bin chip_u2_hi.bin

# Zobraziť aj per-bank tabuľku a GEMDOS detail
python3 rom_validate.py out/ --detail

# Filtrovanie pre konkrétny čip
python3 rom_validate.py out/ --chip tc57h1000
```

### Parametre

| Parameter | Default | Popis |
|---|---|---|
| `SÚBOR_ALEBO_ADRESÁR` | (povinné) | Jeden alebo viac súborov (`.bin/.stc/.rom/.img`), alebo adresár na skenovanie |
| `--chip` | — | Filtrovať výsledky pre daný čip (`w29c040` / `tc57h1000`) |
| `--detail` | — | Vypísať per-bank tabuľku a GEMDOS detail pre combined obrazy |

### Príklad výstupu

```
╔══ rom_validate ════════════════════════════════════════════
║  Adresár: out
║  Súborov: 7
╚═══════════════════════════════════════════════════════════

  Súbor              Veľkosť   Formát                          Čip           Banky      Obsah    Magic     Popis magic                            Stav
  ─────────────────  ────────  ──────────────────────────────  ────────────  ─────────  ───────  ────────  ────────────────────────────────────  ─────
  BUGBCRT2.STC       128 KB    combined(TC5) / combined(W29)   oba           1/1        96.9%    0xABCD    LINE-A #0xBCD (cartridge entry)        PASS
  DiagROMCart.rom    128 KB    combined(TC5) / combined(W29)   oba           1/1        96.7%    0xFA52    Atari ST cart magic (FA52/235F)        PASS
  JOUMPCRT.STC       128 KB    combined(TC5) / combined(W29)   oba           1/1        87.0%    0xABCD    LINE-A #0xBCD (cartridge entry)        PASS
  MXCRT.STC          128 KB    combined(TC5) / combined(W29)   oba           1/1        86.8%    0xABCD    LINE-A #0xBCD (cartridge entry)        PASS
  ST Test v4.4.img   64 KB     chip(TC5) / chip(W29)           oba           1/1        91.4%    —         — (chip súbor: magic je rozdelený m…   PASS
  STE Test v1.9.img  64 KB     chip(TC5) / chip(W29)           oba           1/1        91.9%    —         — (chip súbor: magic je rozdelený m…   PASS
  etoscart.img       128 KB    combined(TC5) / combined(W29)   oba           1/1        98.0%    0xFA52    Atari ST cart magic (FA52/235F)        PASS

  Súhrn: 7 súborov  │  7 PASS  │  0 WARN  │  0 FAIL
```

---

## Makefile

Skratky pre bežné workflow:

```bash
# Zabaľ ROM z prg/ (predvolene) — odporúčaný spôsob
make pack

# Iný zdrojový adresár alebo typ čipu
make pack PRGDIR=myroms/ CHIP=tc57h1000 OUTDIR=build/

# Explicitný zoznam súborov (bez medzier v názvoch)
make pack SRCS="game.bin"
make pack SRCS="p1.bin p2.bin" CHIP=w29c040

# Náhľad rozloženia bez zápisu
make dry-run

# Zabaľ + uloži kombinovaný obraz
make pack-combined

# Rozdeľ existujúci combined.bin
make split SRC=combined.bin

# Zobraz info o chip súboroch
make info

# Validácia (prehľadová tabuľka)
make validate
make validate VALDIR=build/ CHIP=tc57h1000

# Validácia s per-bank detailom a GEMDOS výpisom
make validate-detail

# Zmaž výstupný adresár
make clean
```

Premenné Makefile:

| Premenná | Default | Popis |
|---|---|---|
| `CHIP` | `w29c040` | Typ čipu |
| `PRGDIR` | `prg/` | Zdrojový adresár pre `pack` (ak nie je nastavené `SRCS`) |
| `OUTDIR` | `out/` | Výstupný adresár (pre `pack`, `split`, `info`) |
| `VALDIR` | `out/` | Adresár na validáciu (pre `validate`) |
| `SRCS` | — | Explicitné vstupné súbory (pre `pack`; bez medzier v názvoch) |
| `SRC` | — | Jeden vstupný súbor (pre `split`) |
| `PAD` | `0xFF` | Výplňový bajt |

---

## Typický workflow

### W29C040 — plné nasadenie (1 MB, 8 bankov)

Všetky zdrojové súbory ulož do `prg/`. Skript automaticky skenuje adresár, spracuje
súbory s medzerami v názvoch a odstraňuje STC hlavičky — žiadne citácie ani explicitné
zoznamy súborov nie sú potrebné.

```bash
# 1. Validácia zdrojov
make validate VALDIR=prg/

# 2. Príprava chip súborov (skenuje prg/ automaticky)
make pack

# 3. Kontrola obsahu (mapa bankov, podpisy)
make info

# 4. Programovanie čipov (externým programátorom)
#    U1 ← out/chip_u1_lo.bin
#    U2 ← out/chip_u2_hi.bin

# 5. Nastavenie DIP switch SW1
#    Bank 0: SW1-1=0, SW1-2=0, SW1-3=0
#    Bank 1: SW1-1=1, SW1-2=0, SW1-3=0
#    ...
```

### W29C040 — mix reálnych cartridge ROM-ov (prg/ adresár)

Príklad s reálnymi súbormi (vrátane názvov s medzerami a STC formátu):

```bash
# 0. Validácia zdrojov (prg/ adresár)
python3 rom_validate.py prg/

# 1. Zabalenie — skenuje prg/, banky sa priradia abecedne
make pack
#    — alebo priamo: python3 rom_pack.py prg/

# 2. Kontrola výsledného chip obrazu (mapa bankov, magic podpisy)
python3 rom_info.py out/chip_u1_lo.bin out/chip_u2_hi.bin

# 3. Programovanie čipov
#    U1 ← out/chip_u1_lo.bin  (512 KB)
#    U2 ← out/chip_u2_hi.bin  (512 KB)

# 4. Nastavenie DIP switch SW1 podľa požadovaného programu
#    (poradie = abecedné zoradenie súborov v prg/):
#    Bank 0 (SW1=000): BUGBCRT2.STC
#    Bank 1 (SW1=001): DiagROMCart.rom
#    Bank 2 (SW1=010): JOUMPCRT.STC
#    Bank 3 (SW1=011): MXCRT.STC
#    Bank 4 (SW1=100): ST Test v4.4.img
#    Bank 5 (SW1=101): STE Test v1.9.img
#    Bank 6 (SW1=110): WBCRT.STC
#    Bank 7 (SW1=111): etoscart.img
```

### TC57H1000 — 128 KB SRAM, 2 banky

```bash
# 1. Príprava (max 256 KB, 2 banky)
make pack PRGDIR=prg/ CHIP=tc57h1000 OUTDIR=build/

# 2. Validácia (zobrazí varovania pre SW1-3 / SW1-2)
make validate CHIP=tc57h1000 VALDIR=build/

# 3. Kontrola + varovania pre SW1
make info CHIP=tc57h1000 OUTDIR=build/

# 4. Programovanie U1 ← build/chip_u1_lo.bin, U2 ← build/chip_u2_hi.bin
# 5. SW1-3 musí ostať OPEN (VPP); SW1-1 vyberá bank 0 alebo 1
```

---

## Poznámky k programovaniu W29C040-90B

- Programuje sa **mimo obvodu** (vytiahnuť zo socketu DIP-32).
- Čip podporuje Software Data Protection (SDP) — ak je zapnutá, treba ju pred
  programovaním deaktivovať príkazom povolenia zápisu (závisí od programátora).
- Mazaný (erase) stav bajtu = `0xFF`.
- Programátor nastaviť na typ `W29C040` alebo kompatibilný `29C040`.

## Poznámky k TC57H1000AD-85

- **Nikdy nezatvoriť SW1-3** — pin 1 je `VPP`, pull-up R3 zabezpečuje +5 V.
  Zatvorenie prepne VPP na GND a môže trvalo poškodiť čip.
- Programuje sa ako štandardná 128 KB SRAM alebo `TC57H1000`.
- Obsah sa stratí po výpadku napájania (je to SRAM, nie flash).
