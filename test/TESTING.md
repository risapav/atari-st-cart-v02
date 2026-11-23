# Testovanie — Atari ST ROM Cartridge v2

**Projekt:** cart_v02 · Rev 1.1  
**Autor testov:** risapav  
**Dátum:** 2026-11-21  
**Stav:** PASS — 73/73 testov prešlo

---

## Prehľad

Testovacie prostredie virtuálne simuluje čítanie dát cez Atari ST cartridge port.
Cieľom je overiť, že hardvérové zapojenie (podľa schémy Rev 1.1) dekóduje adresy
a prenáša dáta správne — bez nutnosti fyzického hardware.

Simulácia modeluje:
- Dvojicu W29C040-90B Flash EEPROM čipov (U1 = hi bajt D8–D15, U2 = lo bajt D0–D7)
- Dekódovanie adries ST A1–A15 → chip A0–A14
- Signál /ROM4 → chip A15 (odlíšenie $FA / $FB regiónu)
- DIP switch SW1 (B_SW1/B_SW2/B_SW3) → chip A16/A17/A18 (bank select)
- CE logiku (wired-AND D1+D2 cez BAT42, R4 pull-up)
- Byte strobe signály /UDS → U1 /OE, /LDS → U2 /OE

---

## Štruktúra testovacieho adresára

```
test/
├── TESTING.md              — táto dokumentácia
├── cartridge_model.py      — virtuálny model hardvéru
├── generate_test_roms.py   — generátor testovacích ROM súborov
├── run_tests.py            — testovací runner (T01–T08)
└── roms/
    ├── chip_u1_lo.bin      — 512 KB testovací obraz U2 (lo bajty, D0–D7)
    ├── chip_u2_hi.bin      — 512 KB testovací obraz U1 (hi bajty, D8–D15)
    ├── bank0_lo.bin        — 64 KB bank 0 pre U2
    ├── bank0_hi.bin        — 64 KB bank 0 pre U1
    ├── bank1_lo.bin … bank7_hi.bin  — banky 1–7
```

---

## Formát testovacích binárnych súborov

### Rozdelenie LO / HI

Každý bank obsahuje 128 KB kombinovaného obsahu, rozdeleného na dva **64 KB** súbory:

| Súbor | Čip | Dátová linka | Byte strobe |
|---|---|---|---|
| `bankN_lo.bin` | U2 | D0–D7 (dolný bajt) | /LDS |
| `bankN_hi.bin` | U1 | D8–D15 (horný bajt) | /UDS |

68000 neposkytuje A0 — výber bajtu je realizovaný cez /UDS a /LDS:
- Párna adresa (even byte): U1 platí → D8–D15 → `rom_hi.bin`
- Nepárna adresa (odd byte): U2 platí → D0–D7 → `rom_lo.bin`

> **Poznámka k premenným modelu:** V `cartridge_model.py` sa používajú premenné `u1`/`u2`
> ako logické názvy pre bajt-roly (lo = D0–D7, hi = D8–D15). Fyzicky: socket U1 = chip_u2_hi.bin, socket U2 = chip_u1_lo.bin.

### Testovací vzorec

Pre bajt na adrese čipu `addr`:

```
bank       = addr >> 16          (0–7)
local_addr = addr & 0xFFFF       (offset v rámci banku)

U1[addr]   = (local_addr + bank * 7)        & 0xFF   # lo bajt
U2[addr]   = ((local_addr >> 8) + bank * 13) & 0xFF  # hi bajt
```

**Vlastnosti vzorca:**
- 16-bitové slovo na adrese 0 každého banku je unikátne → testuje bank select
- Hodnota závisí od presnej chip adresy → testuje address decoding
- Vypočítateľné bez ukladania referenčných dát (pure function)

**Podpisy bankov na ST adrese $FA0000:**

| Bank | Chip adresa | lo bajt | hi bajt | 16-bit slovo |
|------|-------------|---------|---------|--------------|
| 0    | 0x000000    | 0x00    | 0x00    | 0x0000       |
| 1    | 0x010000    | 0x07    | 0x0D    | 0x0D07       |
| 2    | 0x020000    | 0x0E    | 0x1A    | 0x1A0E       |
| 3    | 0x030000    | 0x15    | 0x27    | 0x2715       |
| 4    | 0x040000    | 0x1C    | 0x34    | 0x341C       |
| 5    | 0x050000    | 0x23    | 0x41    | 0x4123       |
| 6    | 0x060000    | 0x2A    | 0x4E    | 0x4E2A       |
| 7    | 0x070000    | 0x31    | 0x5B    | 0x5B31       |

---

## Mapovanie adries (overené testom T01)

```
ST bajt adresa          →   adresa čipu
────────────────────────────────────────────────────────────
$FA0000                 →   0x000000  (bank 0, A15=0, begin $FA)
$FA0002                 →   0x000001  (ST A1=1 → chip A0=1)
$FAFFFE                 →   0x007FFF  (koniec $FA regiónu)
$FB0000                 →   0x008000  (A15=1, begin $FB)
$FBFFFE                 →   0x00FFFF  (koniec banku 0)
$FA0000  (bank 1)       →   0x010000
$FBFFFE  (bank 7)       →   0x07FFFF  (posledný bajt čipu)
```

**Vzorec prekladu:**

```python
chip_A0_14  = (st_addr >> 1) & 0x7FFF          # ST A1–A15 → chip A0–A14
chip_A15    = 0 if st_addr < 0xFB0000 else 1   # /ROM4 stav
chip_addr   = (bank << 16) | (chip_A15 << 15) | chip_A0_14
```

---

## Popis testov

### T01 — Preklad adries ST bus → chip adresa
Overuje presnú transformáciu adries pre všetky kľúčové body okna a všetky krajné
prípady (začiatok/koniec $FA, začiatok/koniec $FB, bank 1, bank 7).

### T02 — 16-bitové čítanie slov
Číta 16-bitové slová na 8 rôznych ST adresách v banku 0 a porovnáva s očakávaným
vzorcom. Overuje korektné zostavenie slova z U1 (lo) a U2 (hi).

### T03 — Izolácia byte strobe (/LDS a /UDS)
Pre každú testovaciu adresu číta:
- len lo bajt (`read_byte_lo`, modeluje /LDS aktívny, /UDS neaktívny)
- len hi bajt (`read_byte_hi`, modeluje /UDS aktívny, /LDS neaktívny)
- plné 16-bit slovo

Verifikuje, že `word == (hi_byte << 8) | lo_byte`.

### T04 — Prepínanie bankov
Pre každý z 8 bankov:
1. Nastaví DIP switch (set_bank)
2. Číta slovo na $FA0000 a $FB0000
3. Porovnáva s očakávanou hodnotou pre daný bank

Záverečná kontrola: všetkých 8 bankov dáva na $FA0000 rôzne hodnoty.

### T05 — CE logika (chip enable)
Overuje, že:
- Čítanie v $FA0000–$FAFFFF vracia platné dáta (CE aktívne)
- Čítanie v $FB0000–$FBFFFF vracia platné dáta (CE aktívne)
- Čítanie mimo okna ($F90000, $FC0000, $000000 atď.) vracia -1 (CE neaktívne)

### T06 — Kompletný sekvenčný sken
Prechádza všetkých 65 536 slov (128 KB) v banku 0 a overuje každé slovo oproti
deterministickému vzorcu. Počíta nezhody, vypíše prvé 3 chybné adresy.

### T07 — 68000 word zarovnanie (A0 ignorovaný)
Atari ST 68000 neposkytuje A0 na cartridge porte — byte selection je cez /UDS a /LDS.
Test overuje, že párna a nepárna adresa (líšia sa len A0) mapujú na **rovnakú** adresu čipu.

### T08 — Hraničné adresy
Pre banky 0 a 7 overuje prvé a posledné slovo každého regiónu ($FA a $FB).
Kombinácia krajných bankov a krajných adries odhaľuje chyby v carry bitoch.

---

## Spustenie testov

```bash
cd /home/palo/atari/atari_st/cart_v02/test

# 1. Vygenerovanie ROM súborov (iba raz)
python3 generate_test_roms.py

# 2. Spustenie všetkých testov
python3 run_tests.py
```

Ak ROM súbory neexistujú, `run_tests.py` ich vygeneruje automaticky.

Návratový kód: `0` = všetky testy prešli, `1` = niektorý zlyhal.

---

## Výsledky testov (2026-11-21)

```
Atari ST ROM Cartridge v2 — virtuálna simulácia

T01: Preklad adries ST bus → adresa čipu          10 / 10  PASS
T02: 16-bitové čítanie slov (bank 0)               8 /  8  PASS
T03: Izolácia byte strobe (/LDS a /UDS)           12 / 12  PASS
T04: Prepínanie bankov (všetkých 8)               17 / 17  PASS
T05: CE logika — okno cartridge                   13 / 13  PASS
T06: Kompletný sekvenčný sken banku 0              1 /  1  PASS  (65 536 slov bez nezhody)
T07: 68000 word zarovnanie                         4 /  4  PASS
T08: Hraničné adresy                               8 /  8  PASS

Výsledky: 73 prešlo, 0 zlyhalo
VŠETKY TESTY PREŠLI ✓
```

---

## Záver

Virtuálna simulácia potvrdila, že:

1. **Dekódovanie adries** je korektné — ST A1–A15 sa presne mapujú na chip A0–A14,
   /ROM4 korektne určuje chip A15 (0 pre $FA, 1 pre $FB).

2. **CE logika** (wired-AND D1+D2) správne aktivuje čipy len v okne $FA0000–$FBFFFF
   a drží ich neaktívne mimo tohto okna.

3. **Byte strobe** (/LDS → U1, /UDS → U2) funguje izolovane — každý čip odpovedá
   len na príslušný strobe signál, 16-bitové slovo sa korektne skladá z oboch bajtov.

4. **Bank switching** (DIP switch SW1) správne posúva chip adresu o 64 KB na bank,
   všetkých 8 bankov dáva odlišné a predvídateľné hodnoty.

5. **A0 ignorovanie** je implementované správne — párna aj nepárna ST adresa mapujú
   na rovnakú adresu čipu (byte selection je výhradne cez /UDS a /LDS).

Hardvér je pripravený na programovanie fyzických čipov a osadenie na PCB.
