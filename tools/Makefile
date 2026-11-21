# =============================================================================
# Makefile — Atari ST ROM Cartridge v2 · ROM príprava
#
# Premenné (prepisovateľné z príkazového riadku):
#   CHIP    — typ čipu: w29c040 (default) alebo tc57h1000
#   OUTDIR  — výstupný adresár (default: out/)
#   SRCS    — vstupné ROM súbory oddelené medzerami
#   SRC     — jeden vstupný súbor pre cieľ split
#   PAD     — výplňový bajt (default: 0xFF)
#   VALDIR  — adresár na validáciu (default: out/)
#
# Príklady:
#   make pack SRCS="game.bin"
#   make pack SRCS="p1.bin p2.bin" CHIP=w29c040
#   make pack SRCS="rom.bin" CHIP=tc57h1000 OUTDIR=build/
#   make split SRC=combined.bin
#   make info
#   make validate
#   make validate VALDIR=build/ --detail
#   make clean
# =============================================================================

PYTHON  ?= python3
CHIP    ?= w29c040
OUTDIR  ?= out
PAD     ?= 0xFF
SRCS    ?=
SRC     ?=
VALDIR  ?= out
DETAIL  ?=

PACK_SCRIPT     := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))rom_pack.py
SPLIT_SCRIPT    := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))rom_split.py
INFO_SCRIPT     := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))rom_info.py
VALIDATE_SCRIPT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))rom_validate.py

CHIP_U1 := $(OUTDIR)/chip_u1_lo.bin
CHIP_U2 := $(OUTDIR)/chip_u2_hi.bin

.PHONY: pack split info validate clean help check-srcs check-src check-out

# -----------------------------------------------------------------------------
# help — vypíše dostupné ciele
# -----------------------------------------------------------------------------
help:
	@echo ""
	@echo "  Atari ST ROM Cartridge v2 — ROM príprava"
	@echo "  ─────────────────────────────────────────"
	@echo "  Ciele:"
	@echo "    pack      Zabaľ ROM programy do chip súborov"
	@echo "    split     Rozdeľ existujúci kombinovaný obraz na LO/HI"
	@echo "    info      Zobraz informácie o chip súboroch"
	@echo "    validate  Validuj ROM súbory (veľkosť, magic, obsah)"
	@echo "    clean     Zmaž výstupný adresár"
	@echo "    help      Tento text"
	@echo ""
	@echo "  Premenné:"
	@echo "    CHIP=$(CHIP)   (w29c040 | tc57h1000)"
	@echo "    OUTDIR=$(OUTDIR)"
	@echo "    SRCS=$(if $(SRCS),$(SRCS),(neuvedené — použiť: make pack SRCS='a.bin b.bin'))"
	@echo "    SRC=$(if $(SRC),$(SRC),(neuvedené — použiť: make split SRC=combined.bin))"
	@echo "    VALDIR=$(VALDIR)  (pre make validate)"
	@echo "    PAD=$(PAD)"
	@echo ""

# -----------------------------------------------------------------------------
# pack — zabaľ SRCS do chip súborov
# -----------------------------------------------------------------------------
check-srcs:
	@if [ -z "$(SRCS)" ]; then \
		echo "CHYBA: premenná SRCS je prázdna."; \
		echo "Príklad: make pack SRCS='game.bin'"; \
		exit 1; \
	fi

pack: check-srcs
	$(PYTHON) $(PACK_SCRIPT) \
		--chip $(CHIP) \
		--out  $(OUTDIR) \
		--pad  $(PAD) \
		$(SRCS)

# To isté s uložením kombinovaného obrazu
pack-combined: check-srcs
	$(PYTHON) $(PACK_SCRIPT) \
		--chip $(CHIP) \
		--out  $(OUTDIR) \
		--pad  $(PAD) \
		--save-combined \
		$(SRCS)

# Náhľad bez zápisu
dry-run: check-srcs
	$(PYTHON) $(PACK_SCRIPT) \
		--chip $(CHIP) \
		--out  $(OUTDIR) \
		--pad  $(PAD) \
		--dry-run \
		$(SRCS)

# -----------------------------------------------------------------------------
# split — rozdeľ existujúci kombinovaný obraz
# -----------------------------------------------------------------------------
check-src:
	@if [ -z "$(SRC)" ]; then \
		echo "CHYBA: premenná SRC je prázdna."; \
		echo "Príklad: make split SRC=combined.bin"; \
		exit 1; \
	fi

split: check-src
	$(PYTHON) $(SPLIT_SCRIPT) \
		--chip  $(CHIP) \
		--out   $(OUTDIR) \
		--banks \
		--map \
		$(SRC)

# -----------------------------------------------------------------------------
# info — zobraz informácie o chip súboroch
# -----------------------------------------------------------------------------
check-out:
	@if [ ! -f "$(CHIP_U1)" ] || [ ! -f "$(CHIP_U2)" ]; then \
		echo "CHYBA: chip súbory nenájdené v $(OUTDIR)/."; \
		echo "Spusti najprv: make pack SRCS='...' alebo make split SRC=..."; \
		exit 1; \
	fi

info: check-out
	$(PYTHON) $(INFO_SCRIPT) \
		--chip $(CHIP) \
		$(CHIP_U1) $(CHIP_U2)

# -----------------------------------------------------------------------------
# validate — overí ROM súbory v adresári
# -----------------------------------------------------------------------------
validate:
	$(PYTHON) $(VALIDATE_SCRIPT) \
		--chip $(CHIP) \
		$(if $(DETAIL),--detail,) \
		$(VALDIR)

# Validácia s per-bank detailom
validate-detail:
	$(PYTHON) $(VALIDATE_SCRIPT) \
		--chip $(CHIP) \
		--detail \
		$(VALDIR)

# -----------------------------------------------------------------------------
# clean
# -----------------------------------------------------------------------------
clean:
	@echo "Mažem $(OUTDIR)/ ..."
	rm -rf $(OUTDIR)
	@echo "Hotovo."
