"""
CartridgeModel — virtuálna simulácia hardvéru Atari ST ROM Cartridge v2.

Modeluje dvojicu W29C040-90B (U1/U2) s dekódovaním adries, CE logikou
a riadením byte strobe presne podľa schémy cart_v02 Rev 1.1.

Mapovanie adries (z functional_analysis.md):
  ST A1–A15  →  chip A0–A14
  /ROM4      →  chip A15  (LOW pri $FA regióne → A15=0; HIGH pri $FB → A15=1)
  B_SW1/2/3  →  chip A16/A17/A18  (DIP switch SW1)

CE logika (D1, D2 wired-AND):
  ROM_CE LOW  keď  /ROM3 LOW  ALEBO  /ROM4 LOW
  R4 (10 kΩ) drží ROM_CE HIGH keď sú oba signály HIGH
"""


class CartridgeModel:
    ST_ROM4_BASE = 0xFA0000   # /ROM4 región
    ST_ROM3_BASE = 0xFB0000   # /ROM3 región
    REGION_SIZE  = 0x010000   # 64 KB na región
    CHIP_SIZE    = 512 * 1024 # 512 KB na čip

    def __init__(self):
        self.u1 = bytearray(self.CHIP_SIZE)   # U1 — lo byte chip (D0–D7, /LDS)
        self.u2 = bytearray(self.CHIP_SIZE)   # U2 — hi byte chip (D8–D15, /UDS)
        # DIP switch SW1: False=open (+5 V cez pull-up = 1), True=closed (GND = 0)
        self._sw1 = False   # B_SW1 → A16
        self._sw2 = False   # B_SW2 → A17
        self._sw3 = False   # B_SW3 → A18

    # ------------------------------------------------------------------
    # Načítanie ROM súborov
    # ------------------------------------------------------------------

    def load_chips(self, u1_file: str, u2_file: str):
        """Načíta binárne súbory do interných polí U1 a U2."""
        with open(u1_file, "rb") as f:
            data = f.read()
        if len(data) > self.CHIP_SIZE:
            raise ValueError(f"U1 file too large: {len(data)} > {self.CHIP_SIZE}")
        self.u1[:len(data)] = data

        with open(u2_file, "rb") as f:
            data = f.read()
        if len(data) > self.CHIP_SIZE:
            raise ValueError(f"U2 file too large: {len(data)} > {self.CHIP_SIZE}")
        self.u2[:len(data)] = data

    def load_bank_files(self, lo_file: str, hi_file: str, bank: int):
        """Načíta 64 KB LO a HI súbory do správneho banku čipov."""
        if not 0 <= bank <= 7:
            raise ValueError(f"Bank must be 0–7, got {bank}")
        offset = bank * 0x10000
        with open(lo_file, "rb") as f:
            data = f.read()
        if len(data) != 0x10000:
            raise ValueError(f"LO bank file must be exactly 64 KB, got {len(data)}")
        self.u1[offset:offset + 0x10000] = data

        with open(hi_file, "rb") as f:
            data = f.read()
        if len(data) != 0x10000:
            raise ValueError(f"HI bank file must be exactly 64 KB, got {len(data)}")
        self.u2[offset:offset + 0x10000] = data

    # ------------------------------------------------------------------
    # DIP switch / bank
    # ------------------------------------------------------------------

    def set_bank(self, bank: int):
        """Nastaví DIP switch SW1 na bank 0–7. Closed=GND=0, Open=+5V=1."""
        if not 0 <= bank <= 7:
            raise ValueError(f"Bank must be 0–7, got {bank}")
        self._sw1 = bool((bank >> 0) & 1)   # B_SW1 → A16
        self._sw2 = bool((bank >> 1) & 1)   # B_SW2 → A17
        self._sw3 = bool((bank >> 2) & 1)   # B_SW3 → A18

    @property
    def bank(self) -> int:
        return (int(self._sw3) << 2) | (int(self._sw2) << 1) | int(self._sw1)

    # ------------------------------------------------------------------
    # CE logika
    # ------------------------------------------------------------------

    def _rom4_asserted(self, st_addr: int) -> bool:
        """True ak /ROM4 je LOW (adresa v $FA0000–$FAFFFF)."""
        return self.ST_ROM4_BASE <= st_addr < self.ST_ROM4_BASE + self.REGION_SIZE

    def _rom3_asserted(self, st_addr: int) -> bool:
        """True ak /ROM3 je LOW (adresa v $FB0000–$FBFFFF)."""
        return self.ST_ROM3_BASE <= st_addr < self.ST_ROM3_BASE + self.REGION_SIZE

    def ce_asserted(self, st_addr: int) -> bool:
        """ROM_CE LOW keď /ROM3 ALEBO /ROM4 je LOW (wired-AND cez D1, D2)."""
        return self._rom4_asserted(st_addr) or self._rom3_asserted(st_addr)

    # ------------------------------------------------------------------
    # Preklad adresy ST → chip
    # ------------------------------------------------------------------

    def st_to_chip_addr(self, st_addr: int) -> int:
        """
        Preloží ST bajt adresu na bajt adresu čipu.

        chip_A[0:14]  = ST_A[1:15]   = (st_addr >> 1) & 0x7FFF
        chip_A15      = /ROM4 stav   = 0 pre $FA, 1 pre $FB
        chip_A[16:18] = SW1 stav     = bank select
        """
        chip_A0_14 = (st_addr >> 1) & 0x7FFF
        # /ROM4 je LOW pri $FA → chip A15 = 0; HIGH pri $FB → chip A15 = 1
        chip_A15 = 0 if self._rom4_asserted(st_addr) else 1
        return (self.bank << 16) | (chip_A15 << 15) | chip_A0_14

    # ------------------------------------------------------------------
    # Čítanie dát
    # ------------------------------------------------------------------

    def read_word(self, st_addr: int) -> int:
        """
        Číta 16-bitové slovo (oba /UDS aj /LDS aktívne).
        Vracia -1 ak adresa nie je v cartridge okne.
        """
        if not self.ce_asserted(st_addr):
            return -1
        chip_addr = self.st_to_chip_addr(st_addr)
        lo = self.u1[chip_addr]   # D0–D7
        hi = self.u2[chip_addr]   # D8–D15
        return (hi << 8) | lo

    def read_byte_lo(self, st_addr: int) -> int:
        """
        Číta len dolný bajt (/LDS aktívny, /UDS neaktívny).
        Modeluje čítanie párnej bajt adresy + 1 (odd byte).
        Vracia -1 ak adresa nie je v okne.
        """
        if not self.ce_asserted(st_addr):
            return -1
        chip_addr = self.st_to_chip_addr(st_addr)
        return self.u1[chip_addr]

    def read_byte_hi(self, st_addr: int) -> int:
        """
        Číta len horný bajt (/UDS aktívny, /LDS neaktívny).
        Modeluje čítanie párnej bajt adresy (even byte).
        Vracia -1 ak adresa nie je v okne.
        """
        if not self.ce_asserted(st_addr):
            return -1
        chip_addr = self.st_to_chip_addr(st_addr)
        return self.u2[chip_addr]
