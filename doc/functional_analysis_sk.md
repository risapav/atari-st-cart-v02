# Funkčná analýza — Atari ST ROM Cartridge v2

**Projekt:** cart_v02 · Rev 1.1 · 2026-11-08 · risapav  
**Dátum analýzy:** 2026-11-21 (aktualizácia: rozpoznávanie cartridge TOS, formáty ROM obrazov)

---

## Stav: PASS — nenájdené žiadne funkčné chyby

Predtým identifikované chyby (obrátená polarita diód, kolízia názvov globálnych spojov) boli opravené.  
Schéma je funkčne správna. Všetky spoje overené voči datasheetu W29C040-90B
a špecifikácii cartridge portu Atari ST.

---

## Overené opravy

### Oprava 1 — Polarita diód D1 / D2

**Pôvodná chyba:** D1 a D2 boli umiestnené v rotácii 0°, čím bola Anóda pripojená k signálom /ROM4 a /ROM3. Bez priepustného smeru prúdu bol uzol ROM_CE trvale HIGH → čipy neboli nikdy povolené.

**Oprava:** D1 a D2 sú teraz v rotácii 180°:

| Dióda | Katóda (K) | Anóda (A) |
|---|---|---|
| D1 | Signál `ST_~{ROM4}` (x = 81,28) | Uzol ROM_CE (x = 73,66) |
| D2 | Signál `ST_~{ROM3}` (x = 81,28) | Uzol ROM_CE (x = 69,85 spojenie) |

**Správny obvod:**

```
/ROM3 ──|<|── D2 ──┬── R4 ── +5V
                   │
/ROM4 ──|<|── D1 ──┴── ROM_CE → /CE (U1 pin 22, U2 pin 22)
```

`|<|` = Katóda na strane signálu, Anóda na strane ROM_CE.

Keď signál prejde na LOW, prúd tečie z ROM_CE (Anóda, potiahnutá na HIGH cez R4) cez diódu k signálu (Katóda, LOW). ROM_CE sa pritiahne na LOW → čipy povolené. Keď sú oba signály HIGH, R4 drží ROM_CE HIGH → čipy deaktivované. ✓

### Oprava 2 — Pomenovanie sieťových spojov

**Pôvodná chyba:** Adresové piny na symboloch čipov používali KiCad globálne labely s názvami `A1`, `A2`, `A3`, zhodujúcimi sa s rovnako nazvanými globálnymi labelmi na konektore J1. Tým boli adresové linky Atari ST A1–A3 priamo skratované na /WE, /OE, /CE čipov.

**Oprava:** Všetky spoje teraz používajú KiCad **lokálne labely** s popisnými predponami:
- `ST_A1` … `ST_A15` — adresová zbernica Atari ST
- `ST_D0` … `ST_D15` — dátová zbernica Atari ST
- `ST_~{ROM3}`, `ST_~{ROM4}` — signály výberu čipu
- `ST_~{UDS}`, `ST_~{LDS}` — signály bytového strobu
- `B_SW1`, `B_SW2`, `B_SW3` — výstupy DIP prepínača pre výber banku
- `ROM_CE` — výstup wired-AND na piny /CE oboch čipov

Lokálne labely sú v KiCad platné len v rámci listu a nemôžu kolizovať s inými globálnymi sieťami. ✓

---

## Úplné overenie zapojenia

### U1 — Čip nižšieho bajtu (D0–D7, /LDS)

U1 umiestnený na pozícii (96,52; 149,86).

| Pin čipu | Signál | Stav |
|---|---|---|
| Pin 12 (A0)  | `ST_A1`  | ✓ |
| Pin 11 (A1)  | `ST_A2`  | ✓ |
| Pin 10 (A2)  | `ST_A3`  | ✓ |
| Pin 9 (A3)   | `ST_A4`  | ✓ |
| Pin 8 (A4)   | `ST_A5`  | ✓ |
| Pin 7 (A5)   | `ST_A6`  | ✓ |
| Pin 6 (A6)   | `ST_A7`  | ✓ |
| Pin 5 (A7)   | `ST_A8`  | ✓ |
| Pin 27 (A8)  | `ST_A9`  | ✓ |
| Pin 26 (A9)  | `ST_A10` | ✓ |
| Pin 23 (A10) | `ST_A11` | ✓ |
| Pin 25 (A11) | `ST_A12` | ✓ |
| Pin 4 (A12)  | `ST_A13` | ✓ |
| Pin 28 (A13) | `ST_A14` | ✓ |
| Pin 29 (A14) | `ST_A15` | ✓ |
| Pin 3 (A15)  | `ST_~{ROM4}` | ✓ — výber polovice banku |
| Pin 2 (A16)  | `B_SW1`  | ✓ |
| Pin 30 (A17) | `B_SW2`  | ✓ |
| Pin 1 (A18)  | `B_SW3`  | ✓ |
| Pin 22 (/CE) | `ROM_CE` | ✓ — výstup wired-AND |
| Pin 24 (/OE) | `ST_~{LDS}` | ✓ — strob nižšieho bajtu |
| Pin 31 (/WE) | +5V (cez #PWR09) | ✓ — ochrana proti zápisu |
| Pin 32 (VCC) | +5V | ✓ |
| Pin 16 (GND) | GND | ✓ |
| Piny 13–21 (D0–D7) | `ST_D0`–`ST_D7` | ✓ |

### U2 — Čip vyššieho bajtu (D8–D15, /UDS)

U2 umiestnený na pozícii (175,26; 151,13). Rovnaké zapojenie adresových a riadiacich pinov ako U1 (overené pin po pine), s dvoma rozdielmi:

| Pin čipu | Signál | Poznámka |
|---|---|---|
| Pin 24 (/OE) | `ST_~{UDS}` | ✓ — strob vyššieho bajtu |
| Pin 31 (/WE) | +5V (cez #PWR010) | ✓ |
| Piny 13–21 (D0–D7) | `ST_D8`–`ST_D15` | ✓ — horný bajt |

### Logika výberu čipu

Uzol ROM_CE (wired-AND) je pripojený na:
- R4 (10 kΩ) pull-up na +5V
- Anódu D1 (K → `ST_~{ROM4}`)
- Anódu D2 (K → `ST_~{ROM3}`)
- /CE (pin 22) oboch čipov

ROM_CE prejde na LOW keď BUĎ /ROM3 ALEBO /ROM4 je aktívny (LOW). Oba signály nikdy nie sú aktívne súčasne na ST zbernici, takže obvod funguje ako zjednotenie dvoch 64 KB adresových okien ($FA a $FB), čím poskytuje 128 KB adresovateľné okno na bank.

### SW1 — Výber banku

SW1 na pozícii (332,74; 86,36). Spoločné (P-strana) piny pripojené na GND. Výstupy T-strany:

| Pin SW | Sieť | Adresový bit čipu | Pull-up |
|---|---|---|---|
| T1 | `B_SW1` | A16 | R1 (10 kΩ) na +5V |
| T2 | `B_SW2` | A17 | R2 (10 kΩ) na +5V |
| T3 | `B_SW3` | A18 | R3 (10 kΩ) na +5V |

Zatvorené = GND = 0; Otvorené = potiahnuté na HIGH = 1. ✓

### Operácia bytového strobu /OE

Na rozdiel od jednoduchého ROM kde je /OE pripojen na GND, tento návrh riadi /OE každého čipu individuálne cez bytový strob:

| Typ prístupu | /UDS | /LDS | U2 /OE | U1 /OE | Aktívne čipy |
|---|---|---|---|---|---|
| Slovo (16-bit) | LOW | LOW | LOW | LOW | oba |
| Len horný bajt | LOW | HIGH | LOW | HIGH | len U2 |
| Len dolný bajt | HIGH | LOW | HIGH | LOW | len U1 |

Toto zabraňuje konfliktu na zbernici pri prístupe len k jednému bajtu. ✓

---

## Mapovanie adries

### ST zbernica → adresa čipu

```
Signál ST zbernice  →   Adresový bit W29C040
─────────────────────────────────────────────
A1  (bit 1)         →   A0   (bit 0)
A2  (bit 2)         →   A1
...
A15 (bit 15)        →   A14
/ROM4               →   A15  (0 = oblasť $FA, 1 = oblasť $FB)
B_SW1 (SW1-1)       →   A16  ┐
B_SW2 (SW1-2)       →   A17  ├ výber banku (3 bity → 8 bankov)
B_SW3 (SW1-3)       →   A18  ┘
```

68000 nevystavuje A0 — výber bytovej linky je riešený cez /UDS a /LDS. Najnižší adresový bit čipu (A0) pochádza z ST A1 (najnižšia viditeľná adresová linka CPU na cartridge porte). ✓

### Adresové okno ST

| /ROM4 | /ROM3 | Oblasť | Chip A15 |
|---|---|---|---|
| LOW  | HIGH | `$FA0000`–`$FAFFFF` | 0 |
| HIGH | LOW  | `$FB0000`–`$FBFFFF` | 1 |

Kombinované okno: `$FA0000`–`$FBFFFF` (128 KB bajtových adries na bank).

---

## Mapa pamäte — 2× W29C040-90B

### Výpočet adresy čipu

Každý čip má 19 adresových bitov (A0–A18) = 512 K pozícií = 512 KB na čip.

Pre daný bank (A18:A17:A16 fixné) sa adresové bity A15:A14:...:A0 menia (16 bitov = 64 K pozícií = 64 KB na čip). Dva čipy paralelne poskytujú 64 K × 16-bit slov = 128 KB obsahu na bank.

```
chip_addr = (bank × 0x010000) | (ROM4_bit × 0x008000) | ST_word_offset
```

kde `ST_word_offset` = ST_byte_addr[14:0] (z A1–A15, posunuté doprava ako wordová adresa).

### Mapa bankov

Prepínač zatvorený = 0 (GND); prepínač otvorený = 1 (+5 V cez pull-up).

| SW1-3 (A18) | SW1-2 (A17) | SW1-1 (A16) | Bank | Offset v čipe | Rozsah |
|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | `0x000000` | `0x000000`–`0x00FFFF` |
| 0 | 0 | 1 | 1 | `0x010000` | `0x010000`–`0x01FFFF` |
| 0 | 1 | 0 | 2 | `0x020000` | `0x020000`–`0x02FFFF` |
| 0 | 1 | 1 | 3 | `0x030000` | `0x030000`–`0x03FFFF` |
| 1 | 0 | 0 | 4 | `0x040000` | `0x040000`–`0x04FFFF` |
| 1 | 0 | 1 | 5 | `0x050000` | `0x050000`–`0x05FFFF` |
| 1 | 1 | 0 | 6 | `0x060000` | `0x060000`–`0x06FFFF` |
| 1 | 1 | 1 | 7 | `0x070000` | `0x070000`–`0x07FFFF` |

Spolu: 8 × 64 KB = 512 KB na čip = čip plne využitý.  
Kombinovaný 16-bit obsah: 8 × 128 KB = **1 MB**. ✓

### Rozloženie binárneho ROM programovania

68000 ukladá vyšší bajt (MSB) na párnu adresu. /UDS sa aktivuje pre bajty na párnych adresách.

| Súbor | Čip | Obsah | Výber bajtu |
|---|---|---|---|
| `chip_u2_hi.bin` | U2 (D8–D15) | párne bajty ROM obrazu (0, 2, 4, …) | /UDS — horný bajt |
| `chip_u1_lo.bin` | U1 (D0–D7) | nepárne bajty ROM obrazu (1, 3, 5, …) | /LDS — dolný bajt |

Pre bankovaný obraz sa banky ukladajú za sebou: bank 0 na offset `0x000000`, bank 1 na `0x010000`, …, bank 7 na `0x070000`. Každý bank zaberá 64 KB (0x10000 bajtov) v každom súbore.

---

## Mapa pamäte — 2× TC57H1000AD-85 (alternatíva)

Toshiba TC57H1000AD-85 je 128 K × 8 SRAM, DIP-32:

| Pin | W29C040-90B | TC57H1000AD-85 | Požiadavka |
|---|---|---|---|
| 1 | A18 | VPP | **SW1-3 musí ostať OPEN** (VPP = +5 V cez R3) |
| 2–29, 32 | A0–A16, D0–D7, /CE, /OE, GND, VCC | identické | — |
| 30 | A17 | NC | SW1-2 irelevantný |
| 31 | /WE | /WE (rovnaký) | zostáva +5 V ✓ |

**SW1-3 musí ostať OPEN vždy pri použití TC57H1000.** Zatvorenie SW1-3 by pritiahlo VPP (pin 1) na GND a môže čip trvalo poškodiť.

### Mapa bankov (TC57H1000AD-85)

TC57H1000 má A0–A16 (17 adresových bitov = 128 K pozícií = 128 KB). Keďže A17 ide na NC (pin 30), len SW1-1 (→ A16) je efektívny bank select.

| SW1-3 | SW1-2 | SW1-1 (A16) | Bank | Offset v čipe |
|---|---|---|---|---|
| **1 (OPEN)** | ľubovoľné | 0 (zatvorené) | 0 | `0x000000`–`0x00FFFF` |
| **1 (OPEN)** | ľubovoľné | 1 (otvorené)  | 1 | `0x010000`–`0x01FFFF` |

Celkovo dostupné: 2 × 64 KB = **128 KB** na čip, **256 KB** kombinovaných.

---

## Rozpoznávanie cartridge ROM systémom TOS

TOS skenuje adresu `$FA0000` pri každom studenom aj teplom štarte a hľadá špecifické magické hodnoty. Cartridge hardvér sprístupňuje tento obsah cez logiku povolenia čipu /ROM3 + /ROM4 popísanú vyššie.

### Štandardná cartridge hlavička

TOS overuje prvé dve 16-bit slová na `$FA0000`:

| Adresa | Hodnota | Význam |
|---|---|---|
| `$FA0000` | `0xFA52` | Cartridge magic — prvé slovo |
| `$FA0002` | `0x235F` | Cartridge magic — druhé slovo (TOS 1.x) |
| `$FA0002` | `0x235A` | Cartridge magic — druhé slovo (TOS 2.x a novší) |

Ak obe slová súhlasia, TOS skočí na `$FA0004` a spustí cartridge program. Tento formát je najkompatibilnejší pre reálny hardvér.

### Vstupný bod LINE-A

Niektoré cartridge programy začínajú priamo opkódom LINE-A:

| Adresa | Hodnota | Význam |
|---|---|---|
| `$FA0000` | `0xABCD` | Opkód `LINE-A #$BCD` — alternatívny vstupný bod cartridge |

Tento formát používa staršia cartridge softvér, vrátane súborov `.STC` emulátora Steem. TOS môže volať `$FA0000` priamo, ak na danom mieste nenájde GEMDOS program.

### GEMDOS autoboot

Ak TOS nájde platnú GEMDOS spustiteľnú hlavičku na `$FA0000` (magic `0x601A`, čo je inštrukcia `BRA.S +26` preskakujúca 28-bajtovú hlavičku), načíta a spustí ho cez štandardný program loader — rovnakým spôsobom ako programy z disku.

---

## Formáty súborov ROM obrazov

### Kombinovaný 16-bit obraz

Kombinovaný obraz je štandardný big-endian 68000 bajtový tok, identický s tým, čo sa zobrazí na dátovej zbernici. Každé 16-bit slovo zaberá dva po sebe idúce bajty: párny offset = vyšší bajt (D8–D15, U2), nepárny offset = nižší bajt (D0–D7, U1).

```
offset 0x000000: D15–D8  → U2  (vyšší bajt na ST $FA0000)
offset 0x000001: D7–D0   → U1  (nižší bajt na ST $FA0000)
offset 0x000002: D15–D8  → U2  (vyšší bajt na ST $FA0002)
offset 0x000003: D7–D0   → U1  (nižší bajt na ST $FA0002)
...
```

Veľkosti: 128 KB (TC57H1000, 1 bank), 512 KB (W29C040, 4 banky), alebo 1 MB (W29C040, 8 bankov).

### Formát Steem STC

Emulátor Steem zabaľuje cartridge ROM obrazy s 4-bajtovou nulovou predponou pred štandardným 128 KB kombinovaným obrazom:

```
bajty 0x000000–0x000003:  00 00 00 00   (Steem hlavička — nie je súčasťou ROM)
bajty 0x000004–0x020003:  <128 KB kombinovaný ROM obraz>
```

Celková veľkosť súboru: **131 076 bajtov** (128 × 1024 + 4).  
ROM obraz na offsete 4 je štandardný kombinovaný 16-bit obraz; magická hodnota na offsete 4 (ekvivalent `$FA0000`) je typicky `0xABCD`.  
`rom_validate.py` automaticky rozpozná tento formát (veľkosť = 131 076 B, prvé 4 bajty = `00 00 00 00`) a pred analýzou hlavičku odstraní.

### Chip súbory (LO / HI)

Každý čip dostane de-interleaved bajty z kombinovaného obrazu:

| Súbor | Čip | Odvodenie | Pin |
|---|---|---|---|
| `chip_u1_lo.bin` | U1 (D0–D7) | `combined[2n+1]`  nepárne bajty | strob /LDS |
| `chip_u2_hi.bin` | U2 (D8–D15) | `combined[2n]`  párne bajty | strob /UDS |

Pre W29C040 s 8 bankami má každý chip súbor veľkosť 512 KB. Bank N začína na bajtovom offsete `N × 0x10000` v každom súbore.

---

## Kontrolný zoznam — Rev 1.1

| Položka | Stav |
|---|---|
| D1 Katóda → signál /ROM4 | ✅ |
| D2 Katóda → signál /ROM3 | ✅ |
| ROM_CE wired-AND s pull-up R4 | ✅ |
| ST A1–A15 → Chip A0–A14 (lokálne labely, bez globálnej kolízie) | ✅ |
| /ROM4 → Chip A15 | ✅ |
| DIP prepínač (B_SW1/2/3) → Chip A16/A17/A18 | ✅ |
| ROM_CE → Chip /CE (oba U1, U2) | ✅ |
| U1 /OE → /LDS (strob nižšieho bajtu) | ✅ |
| U2 /OE → /UDS (strob vyššieho bajtu) | ✅ |
| /WE → +5V (oba čipy, ochrana proti zápisu) | ✅ |
| U1 D0–D7 → ST D0–D7 | ✅ |
| U2 D0–D7 → ST D8–D15 | ✅ |
| VCC, GND, blokovacie kondenzátory | ✅ |
