# JLCPCB Order — Atari ST ROM Cartridge v2

**Rev 1.2 · 2026-11-26**

## Gerber ZIP

Nahraj `Atari_ST_ROM_Cartridge_v2__2_W29C040-90B_16-bit_1.2.zip` na jlcpcb.com → PCB Quote.

## Parametre dosky

| Parameter | Hodnota | Poznámka |
|---|---|---|
| Base Material | FR-4 | |
| Layers | 2 | |
| Dimensions | 47,5 × 90,2 mm | Auto-detected z Gerber |
| PCB Qty | 5 | Minimálne množstvo JLCPCB |
| Different Design | 1 | |
| Delivery Format | Single PCB | |
| PCB Thickness | 1,6 mm | Štandard |
| PCB Color | zelená / čierna | Podľa vkusu |
| Silkscreen | White | |
| **Surface Finish** | **ENIG** | Povinné — edge connector |
| Outer Copper Weight | 1 oz | |
| Via Covering | Tented Vias | |
| Board Outline Tolerance | ±0,2 mm | |
| Confirm Production File | Yes | Odporúčané pri prvej objednávke |
| Remove Order Number | Yes | |
| Flying Probe Test | Fully Test | |

## Kritické nastavenia

Tieto tri nastavenia sú kľúčové — bez nich konektor nebude spoľahlivo fungovať.

| Nastavenie | Hodnota | Dôvod |
|---|---|---|
| **Surface Finish** | **ENIG** | Edge connector pady musia mať rovnomerný, oxidácii odolný povrch. HASL zanecháva nerovnomerné zvary a nesie riziko nespoľahlivého kontaktu. |
| **Gold Fingers** | **Yes** | Aktivácia zlatenia hrany konektora. |
| **30° Finger Chamfer** | **Yes** | Skosenie hrany pre ľahšie zasunutie do portu Atari ST. |

Všetky tri polia sa objavia v JLCPCB formulári až po výbere Surface Finish = ENIG.

## Postup objednania

1. Choď na **jlcpcb.com** → klikni **PCB Quote**
2. Klikni **Add Gerber File** → nahraj `Atari_ST_ROM_Cartridge_v2__2_W29C040-90B_16-bit_1.2.zip`
3. Over auto-detected parametre: **2 vrstvy**, rozmery **~47,5 × 90,2 mm**
4. Nastav **Surface Finish → ENIG**
5. Nastav **Gold Fingers → Yes**
6. Nastav **30° Finger Chamfer → Yes**
7. Nastav **Remove Order Number → Yes**
8. Nastav **Confirm Production File → Yes**
9. Zvol množstvo (min. 5 ks), skontroluj cenu a potvrď objednávku

## Rozmery dosky

- Telo PCB: 47,5 × 78,2 mm
- Jazyk hrany konektora: 42 × 12 mm
- Celkovo: 47,5 × 90,2 mm

Jazyk (42 mm) zodpovedá Atari ST cartridge port CB101494, piny J1 sú obojstranné 2×20, rozstup 2 mm.

## Po doručení DPS

- Vložiť čipy U1/U2 do DIP-32 socketov so správnou orientáciou (zárez k zárezu na footprinte)
- **U1 = nižší bajt** (D0–D7, /LDS); **U2 = vyšší bajt** (D8–D15, /UDS)
- JP1 nechaj **OTVORENÝ** pri použití W29C040-90B (zapoj iba pre TC57H1000AD-85)
- SW1 poloha 4 (NC) je nepoužívaná — nechaj otvorenú
- Programovanie čipov: pozri `tools/README_en.md` alebo `tools/README.md`
