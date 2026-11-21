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
# Jeden program, default W29C040, výstup do out/
python3 rom_pack.py mygame.bin

# Viac programov s explicitným čipom a adresárom
python3 rom_pack.py game1.bin game2.bin game3.bin --chip w29c040 --out build/

# TC57H1000 (max 256 KB, 2 banky)
python3 rom_pack.py rom.bin --chip tc57h1000 --out build/

# Zobraziť rozloženie bez zápisu súborov
python3 rom_pack.py p1.bin p2.bin --dry-run

# Uložiť aj kombinovaný 16-bit obraz
python3 rom_pack.py rom.bin --save-combined

# Vlastný pad bajt (namiesto 0xFF)
python3 rom_pack.py rom.bin --pad 0x00
```

### Parametre

| Parameter | Default | Popis |
|---|---|---|
| `ROMs` | (povinné) | Vstupné ROM súbory (jeden alebo viac) |
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

## Makefile

Skratky pre bežné workflow:

```bash
# Zabaľ ROM programy (SRCS = zoznam súborov)
make pack SRCS="game.bin"
make pack SRCS="p1.bin p2.bin" CHIP=w29c040

# TC57H1000
make pack SRCS="rom.bin" CHIP=tc57h1000 OUTDIR=build/

# Náhľad rozloženia bez zápisu
make dry-run SRCS="p1.bin p2.bin"

# Zabaľ + uloži kombinovaný obraz
make pack-combined SRCS="rom.bin"

# Rozdeľ existujúci combined.bin
make split SRC=combined.bin

# Zobraz info o chip súboroch
make info

# Zmaž výstupný adresár
make clean
```

Premenné Makefile:

| Premenná | Default | Popis |
|---|---|---|
| `CHIP` | `w29c040` | Typ čipu |
| `OUTDIR` | `out/` | Výstupný adresár |
| `SRCS` | — | Vstupné súbory (pre `pack`) |
| `SRC` | — | Jeden vstupný súbor (pre `split`) |
| `PAD` | `0xFF` | Výplňový bajt |

---

## Typický workflow

### W29C040 — plné nasadenie (1 MB, 8 bankov)

```bash
# 1. Príprava chip súborov
make pack SRCS="game1.bin game2.bin" OUTDIR=build/

# 2. Kontrola rozloženia
make info OUTDIR=build/

# 3. Programovanie čipov (externým programátorom)
#    U1 ← build/chip_u1_lo.bin
#    U2 ← build/chip_u2_hi.bin

# 4. Nastavenie DIP switch SW1
#    Bank 0: SW1-1=0, SW1-2=0, SW1-3=0
#    Bank 1: SW1-1=1, SW1-2=0, SW1-3=0
#    ...
```

### TC57H1000 — 128 KB SRAM, 2 banky

```bash
# 1. Príprava (max 256 KB, 2 banky)
make pack SRCS="rom.bin" CHIP=tc57h1000 OUTDIR=build/

# 2. Kontrola + varovania pre SW1
make info CHIP=tc57h1000 OUTDIR=build/

# 3. Programovanie U1 ← build/chip_u1_lo.bin, U2 ← build/chip_u2_hi.bin
# 4. SW1-3 musí ostať OPEN (VPP); SW1-1 vyberá bank 0 alebo 1
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
