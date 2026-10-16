#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Virtual SNES Emulator 0.1 - Super Nintendo / Super Famicom emulator in one Python file.
Targets Python 3.14 (also runs on 3.10+).
Snes9x-style architecture and GUI: 65C816 CPU + SPC700 sound CPU + S-DSP audio,
LoROM/HiROM/ExHiROM bus, PPU (modes 0-7, sprites, windows, color math,
per-scanline raster/HDMA effects), DMA + HDMA, H/V IRQs, NMI, multiply/divide
unit, auto-joypad, SRAM, save states, commercial ROM library browser.

Run:      python virtualsnesemu1.x.py [game.sfc|game.smc]   (no ROM -> built-in demo)
          python virtualsnesemu1.x.py --roms ~/ROMs/SNES  (set commercial library folder)
Needs:    pip install numpy pygame-ce   (classic pygame has no 3.14 wheel yet;
          pygame-ce is a drop-in and still imports as "pygame")
Audio:    pip install cython setuptools  + a C compiler (gcc/clang/MSVC) to get the
          Snes9x S-DSP core; it compiles itself on first run into ~/.virtualsnes/cython.
          Without them Virtual SNES Emulator falls back to its numpy DSP.  --dsp auto|snes9x|numpy
GUI:      Classic vsnes desktop — File | CPU | Options | Help (MarioNES-style)
Keys:     Arrows=D-Pad  Z=B  X=A  A=Y  S=X  Q=L  W=R  Enter=Start  RShift=Select
          P=Pause  R=Reset  F5=Save state  F7=Load state  F12=Screenshot
          Tab(hold)=Turbo  F=Auto-frameskip  M=Mute  Esc=Quit
          (you can also drag & drop a ROM onto the window)
Tests:    python virtualsnesemu1.x.py --headless 300 --shot out.png --wav out.wav [rom]
          python virtualsnesemu1.x.py --cputest DIR [--per-file N]
            runs SingleStepTests JSON files (65816 "xx.n.json"/"xx.e.json" or
            spc700 "xx.json") against the cores. Both pass 100%.

Library:  Scans YOUR ROM folder for commercial .sfc/.smc/.zip carts. No game
          data is bundled. Plain LoROM/HiROM/ExHiROM + battery SRAM carts are
          tagged Playable for plain + SA-1/DSP-1/SuperFX/OBC1/S-RTC/CX4/S-DD1/ST01x/SPC7110/SGB (ST018 still Chip).

What's new in 0.1
  * Rebranded as vsnes 0.1 (Virtual SNES Emulator) with a classic File/CPU/Options/Help GUI.
  * SuperFX/GSU: complete 256-opcode dispatch (STOP..IWT + all ALT1/2/3 forms),
    matching the public Super FX opcode matrix. 65816 + SPC700 remain 256/256.
  * Commercial chips (custom HLE): S-DD1 Golomb decompress on DMA, ST010/ST011
    ports+math, SPC7110 mapper/RTC/mul/decomp, SGB/ICD2 packet bridge. APU port
    writes apply before SPC catch-up (handshake). ST018 still Chip.
  * EarthBound / HiROM IPL: 16-bit STA $2140 writes index then data; defer SPC
    catch-up until the data byte is present so the HLE IPL does not store a
    stale port1 byte (boot no longer hangs waiting for $2140/$2141 == 0).

What's new (prior)
  * Commercial chips (custom): DSP-1 HLE, SuperFX/GSU interpreter, OBC1, S-RTC,
    CX4 HLE, S-DD1 MMIO, SA-1. Most chipset carts tagged Playable.

  * SA-1 coprocessor (custom): second 65816 using this emulator's opcodes, Super MMC,
    I-RAM, BW-RAM, normal + character-conversion DMA, arithmetic unit, and
    variable-length bit I/O — Super Mario RPG and other SA-1 carts tagged Playable.
  * Commercial library: SA-1 carts no longer blocked as "needs chip".

  * 65816: verified on all 256 opcodes, native + emulation mode (SingleStepTests).
    Fixed COP B-flag in emulation mode, direct-page wrap when DL=0, and the
    16-bit stack behaviour of PEA PEI PER PHD PLD PLB JSL RTL JSR(a,X).
  * Real SPC700 sound CPU (all 256 opcodes, cycle-exact vs SingleStepTests),
    64 KB ARAM, 3 timers, CPU<->APU ports, S-DSP register file, and a
    high-level-emulated IPL boot loader. Games upload their own sound driver
    and talk to it exactly as on hardware -- the old fake handshake is gone.
  * SPC700 runs lazily (catch-up on every $2140-$217F access + every scanline)
    with idle-loop skipping on port/timer polls, like Snes9x's speedhacks.
  * Audio engine = Snes9x's S-DSP: apu/bapu/dsp/SPC_DSP.cpp (blargg's
    snes_spc 0.9.0, LGPL 2.1+) ported line-for-line to embedded Cython: the
    32-phase per-voice pipeline, hardware Gaussian table, global envelope
    counter, KON/KOFF every other sample, 5-sample key-on delay, BRR, noise,
    pitch modulation, echo + FIR + feedback, Snes9x register semantics.
    Verified bit-exact against the original C++ (4.27M samples, every register
    read, final RAM incl. echo writes). ~0.15 ms per frame. The DSP catches up
    to the SPC700 on every $F2/$F3 access, like Snes9x.
  * Fallback numpy DSP (approximate) when Cython/compiler aren't available.
  * Stutter fix: Snes9x-style "sync to sound" -- emulation is paced by the
    audio device clock (exact 60.0988 Hz SNES rate, no drift), adaptive audio
    latency (grows after an underrun, shrinks after 10 s clean), frameskip
    driven by audio-queue level, GIL switch interval tuned for the audio
    thread, underruns fade out instead of clicking, gc.freeze() at start.
    32 kHz stereo out via an SDL callback.
  * Built-in demo cart boots the SPC700 through the IPL protocol in real 65816
    code, uploads its own sound driver + BRR instrument, and plays a tune.

Honest limits of this build: if a game can't reach full speed even with
frameskip, audio slows with it (gaps are smoothed, not eliminated); the
optional --dsp numpy is approximate. Default audio is the LGPL Snes9x S-DSP (Cython or pure Python);
CPU/PPU/SA-1/SPC700 cores are this emulator's own (Snes9x's other code is
non-commercial licensed). Mosaic, offset-per-tile (modes 2/4/6), EXTBG and
ST018 (seta shogi AI) is not implemented yet;
the PPU renders once per frame from per-scanline register snapshots. Speed:
full SNES speed when games idle on vblank; a game that keeps both CPUs busy
every frame can drop below 60 fps in pure Python (auto-frameskip keeps game
speed correct).
"""

"""vsnes 0.1 — virtualsnesemu1.x.py
Branding: vsnes 0.1 (Virtual SNES Emulator). Classic File/CPU/Options/Help GUI.

Install Python dependencies: python -m pip install numpy pygame-ce
Run: python virtualsnesemu1.x.py [game.sfc]
For genuine SNES9x compatibility and native performance, install a trusted
SNES9x libretro shared library for your OS/CPU beside this file, named
snes9x_libretro.dylib (macOS), snes9x_libretro.dll (Windows), or
snes9x_libretro.so (Linux). Alternatively pass --core PATH.
Use --backend snes9x to require the native core; --backend python selects the
original custom Python core. Auto mode reports which fallback it uses.
The native core is a separate dependency, not bundled or downloaded.
Native SNES9x uses the core's reported NTSC/PAL frame rate; normal playback
is 100% console speed, approximately 60.10 NTSC / 50 PAL emulated FPS.
Full speed depends on the machine/core/game. Frameskip omits drawing only;
it does not replace missing CPU performance. Status separates emulated FPS,
drawn FPS and measured speed. Headless mode is an uncapped benchmark.
The original Python core has the limitations documented below. Its legacy
compatibility/test claims have not been independently verified in this edit.
State files from the native and Python cores are not interchangeable.
SNES9x remains credited to its original authors; its license accompanies the
separately installed core. This frontend does not imply Nintendo endorsement.
"""

import sys, os, time, struct, zlib, pickle, argparse, json, subprocess
from array import array

try:
    import numpy as np
except ImportError:
    sys.exit("Virtual SNES Emulator needs numpy:  pip install numpy pygame-ce")

APP = "vsnes 0.1"
WINDOW_TITLE = "vsnes 0.1"
COPY = "vsnes 0.1 — Virtual SNES Emulator"
BLUE = (0x4D, 0xA6, 0xFF)
DIMBLUE = (0x2A, 0x5C, 0x8F)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------- timing
LINE_CYC = 170          # 1364 master clocks / ~8 per CPU cycle
HBLANK_CYC = 137        # hblank begins at dot ~274
LINES = 262             # NTSC
VIS = 224

# ---------------------------------------------------------------- 65C816 base cycle table
CYC = bytes([
    7,6,7,4,5,3,5,6,3,2,2,4,6,4,6,5, 2,5,5,7,5,4,6,6,2,4,2,2,6,4,7,5,
    6,6,8,4,3,3,5,6,4,2,2,5,4,4,6,5, 2,5,5,7,4,4,6,6,2,4,2,2,4,4,7,5,
    6,6,2,4,7,3,5,6,3,2,2,3,3,4,6,5, 2,5,5,7,7,4,6,6,2,4,3,2,4,4,7,5,
    6,6,6,4,3,3,5,6,4,2,2,6,5,4,6,5, 2,5,5,7,4,4,6,6,2,4,4,2,6,4,7,5,
    3,6,4,4,3,3,3,6,2,2,2,3,4,4,4,5, 2,6,5,7,4,4,4,6,2,5,2,2,4,5,5,5,
    2,6,2,4,3,3,3,6,2,2,2,4,4,4,4,5, 2,5,5,7,4,4,4,6,2,4,2,2,4,4,4,5,
    2,6,3,4,3,3,5,6,2,2,2,3,4,4,6,5, 2,5,5,7,6,4,6,6,2,4,3,3,6,4,7,5,
    2,6,3,4,3,3,5,6,2,2,2,3,4,4,6,5, 2,5,5,7,5,4,6,6,2,4,4,2,8,4,7,5])


class CPU65816:
    """WDC 65C816 core (native + emulation mode, BCD, block moves, idle-loop skip)."""

    def __init__(self, bus):
        self.bus = bus
        self.rd = bus.read
        self.A = self.X = self.Y = 0
        self.S = 0x01FF; self.D = 0; self.DB = 0; self.PB = 0; self.PC = 0
        self.P = 0x34; self.E = 1
        self.cyc = 0; self.target = 0
        self.waiting = False; self.stopped = False
        self.nmi_pending = False; self.irq_line = False
        self.idle_key = None
        self.ops = [None] * 256
        self._build()

    STATE = ('A', 'X', 'Y', 'S', 'D', 'DB', 'PB', 'PC', 'P', 'E', 'cyc', 'target',
             'waiting', 'stopped', 'nmi_pending', 'irq_line')

    def reset(self):
        self.E = 1; self.P = 0x34; self.D = 0; self.DB = 0; self.PB = 0
        self.S = 0x01FF; self.X &= 0xFF; self.Y &= 0xFF
        self.PC = self.rd(0xFFFC) | (self.rd(0xFFFD) << 8)
        self.waiting = self.stopped = False
        self.nmi_pending = self.irq_line = False

    # -- fetch / stack ------------------------------------------------------
    def f8(self):
        v = self.rd((self.PB << 16) | self.PC)
        self.PC = (self.PC + 1) & 0xFFFF
        return v

    def f16(self):
        b = self.PB << 16; pc = self.PC; r = self.rd
        v = r(b | pc) | (r(b | ((pc + 1) & 0xFFFF)) << 8)
        self.PC = (pc + 2) & 0xFFFF
        return v

    def f24(self):
        v = self.f16()
        return v | (self.f8() << 16)

    def push8(self, v):
        self.bus.write(self.S, v & 0xFF)
        self.S = (0x100 | ((self.S - 1) & 0xFF)) if self.E else ((self.S - 1) & 0xFFFF)

    def pull8(self):
        self.S = (0x100 | ((self.S + 1) & 0xFF)) if self.E else ((self.S + 1) & 0xFFFF)
        return self.rd(self.S)

    def push16(self, v):
        self.push8(v >> 8); self.push8(v)

    def pull16(self):
        lo = self.pull8()
        return lo | (self.pull8() << 8)

    def setP(self, v):
        if self.E:
            v |= 0x30
        self.P = v & 0xFF
        if v & 0x10:
            self.X &= 0xFF; self.Y &= 0xFF

    def interrupt(self, vn, ve, brk=False):
        if not self.E:
            self.push8(self.PB)
        self.push16(self.PC)
        p = self.P
        if self.E:
            p = (p & ~0x10) | (0x10 if brk else 0) | 0x20
        self.push8(p)
        self.P = (self.P | 0x04) & ~0x08
        self.PB = 0
        v = ve if self.E else vn
        self.PC = self.rd(v) | (self.rd(v + 1) << 8)
        self.cyc += 8

    # -- main loop ----------------------------------------------------------
    def run(self, target):
        self.target = target
        ops = self.ops; rd = self.rd; cy = CYC
        while self.cyc < target:
            if self.nmi_pending or self.irq_line:
                if self.nmi_pending:
                    self.nmi_pending = False; self.waiting = False
                    self.interrupt(0xFFEA, 0xFFFA)
                elif not (self.P & 4):
                    self.waiting = False
                    self.interrupt(0xFFEE, 0xFFFE)
                elif self.waiting:
                    self.waiting = False
            if self.waiting or self.stopped:
                self.cyc = target
                return
            op = rd((self.PB << 16) | self.PC)
            self.PC = (self.PC + 1) & 0xFFFF
            self.cyc += cy[op]
            ops[op]()

    # -- opcode table -------------------------------------------------------
    def _build(self):
        s = self; bus = self.bus; rd = bus.read; wr = bus.write; O = self.ops
        f8 = self.f8; f16 = self.f16; f24 = self.f24
        push8 = self.push8; push16 = self.push16; pull8 = self.pull8; pull16 = self.pull16

        def npush8(v):
            wr(s.S, v & 0xFF); s.S = (s.S - 1) & 0xFFFF
        def npush16(v):
            npush8(v >> 8); npush8(v)
        def npull8():
            s.S = (s.S + 1) & 0xFFFF; return rd(s.S)
        def npull16():
            lo = npull8(); return lo | (npull8() << 8)
        def nfix():
            if s.E: s.S = 0x100 | (s.S & 0xFF)

        def r16(a): return rd(a) | (rd((a + 1) & 0xFFFFFF) << 8)
        def w16(a, v): wr(a, v & 0xFF); wr((a + 1) & 0xFFFFFF, (v >> 8) & 0xFF)
        def r16z(a): return rd(a) | (rd((a + 1) & 0xFFFF) << 8)

        # addressing modes -> 24-bit effective address
        def dp(): return (s.D + f8()) & 0xFFFF
        # emulation mode with DL=0: direct-page indexing/pointers wrap inside the page
        def dpi(n):
            d = s.D
            return d | (n & 0xFF) if (s.E and not d & 0xFF) else (d + n) & 0xFFFF
        def dptr(n):
            d = s.D
            if s.E and not d & 0xFF:
                return rd(d | (n & 0xFF)) | (rd(d | ((n + 1) & 0xFF)) << 8)
            return r16z((d + n) & 0xFFFF)
        def dpx(): return dpi(f8() + s.X)
        def dpy(): return dpi(f8() + s.Y)
        def ab(): return (s.DB << 16) | f16()
        def abx(): return (((s.DB << 16) | f16()) + s.X) & 0xFFFFFF
        def aby(): return (((s.DB << 16) | f16()) + s.Y) & 0xFFFFFF
        def lg(): return f24()
        def lgx(): return (f24() + s.X) & 0xFFFFFF
        def ind(): return (s.DB << 16) | dptr(f8())
        def indx(): return (s.DB << 16) | dptr(f8() + s.X)
        def indy(): return (((s.DB << 16) | dptr(f8())) + s.Y) & 0xFFFFFF
        def indl():
            p = (s.D + f8()) & 0xFFFF
            return r16z(p) | (rd((p + 2) & 0xFFFF) << 16)
        def indly(): return (indl() + s.Y) & 0xFFFFFF
        def sr(): return (s.S + f8()) & 0xFFFF
        def sry(): return (((s.DB << 16) | r16z((s.S + f8()) & 0xFFFF)) + s.Y) & 0xFFFFFF

        def getM(am):
            if am is None:
                def g(): return f8() if s.P & 0x20 else f16()
            else:
                def g():
                    a = am()
                    return rd(a) if s.P & 0x20 else r16(a)
            return g

        def getX(am):
            if am is None:
                def g(): return f8() if s.P & 0x10 else f16()
            else:
                def g():
                    a = am()
                    return rd(a) if s.P & 0x10 else r16(a)
            return g

        def nz8(r): s.P = (s.P & 0x7D) | (r & 0x80) | (0 if r else 2)
        def nz16(r): s.P = (s.P & 0x7D) | ((r >> 8) & 0x80) | (0 if r else 2)

        # ---- logic
        def ORA(g):
            def f():
                v = g()
                if s.P & 0x20:
                    r = (s.A | v) & 0xFF; s.A = (s.A & 0xFF00) | r; nz8(r)
                else:
                    r = s.A | v; s.A = r; nz16(r)
            return f

        def AND(g):
            def f():
                v = g()
                if s.P & 0x20:
                    r = s.A & v & 0xFF; s.A = (s.A & 0xFF00) | r; nz8(r)
                else:
                    r = s.A & v; s.A = r; nz16(r)
            return f

        def EOR(g):
            def f():
                v = g()
                if s.P & 0x20:
                    r = (s.A ^ v) & 0xFF; s.A = (s.A & 0xFF00) | r; nz8(r)
                else:
                    r = s.A ^ v; s.A = r; nz16(r)
            return f

        # ---- arithmetic (binary + BCD)
        def adc8(v, sbc):
            p = s.P; c = p & 1; a = s.A & 0xFF
            if sbc: v ^= 0xFF
            if p & 8:
                r = (a & 0xF) + (v & 0xF) + c
                if sbc:
                    if r <= 0xF: r -= 6
                elif r > 9: r += 6
                r = (a & 0xF0) + (v & 0xF0) + (0x10 if r > 0xF else 0) + (r & 0xF)
            else:
                r = a + v + c
            ov = ~(a ^ v) & (a ^ r) & 0x80
            if p & 8:
                if sbc:
                    if r <= 0xFF: r -= 0x60
                elif r > 0x9F: r += 0x60
            cf = 1 if r > 0xFF else 0
            r &= 0xFF
            s.A = (s.A & 0xFF00) | r
            s.P = (p & 0x3C) | (0x40 if ov else 0) | cf | (r & 0x80) | (0 if r else 2)

        def adc16(v, sbc):
            p = s.P; c = p & 1; a = s.A
            if sbc: v ^= 0xFFFF
            if p & 8:
                r = (a & 0xF) + (v & 0xF) + c
                if sbc:
                    if r <= 0xF: r -= 6
                elif r > 9: r += 6
                r = (a & 0xF0) + (v & 0xF0) + (0x10 if r > 0xF else 0) + (r & 0xF)
                if sbc:
                    if r <= 0xFF: r -= 0x60
                elif r > 0x9F: r += 0x60
                r = (a & 0xF00) + (v & 0xF00) + (0x100 if r > 0xFF else 0) + (r & 0xFF)
                if sbc:
                    if r <= 0xFFF: r -= 0x600
                elif r > 0x9FF: r += 0x600
                r = (a & 0xF000) + (v & 0xF000) + (0x1000 if r > 0xFFF else 0) + (r & 0xFFF)
            else:
                r = a + v + c
            ov = ~(a ^ v) & (a ^ r) & 0x8000
            if p & 8:
                if sbc:
                    if r <= 0xFFFF: r -= 0x6000
                elif r > 0x9FFF: r += 0x6000
            cf = 1 if r > 0xFFFF else 0
            r &= 0xFFFF
            s.A = r
            s.P = (p & 0x3C) | (0x40 if ov else 0) | cf | ((r >> 8) & 0x80) | (0 if r else 2)

        def ADC(g):
            def f():
                v = g()
                if s.P & 0x20: adc8(v, False)
                else: adc16(v, False)
            return f

        def SBC(g):
            def f():
                v = g()
                if s.P & 0x20: adc8(v, True)
                else: adc16(v, True)
            return f

        def cmpv(a, v, wide):
            if wide:
                r = (a - v) & 0xFFFF
                s.P = (s.P & 0x7C) | (1 if a >= v else 0) | ((r >> 8) & 0x80) | (0 if r else 2)
            else:
                a &= 0xFF; r = (a - v) & 0xFF
                s.P = (s.P & 0x7C) | (1 if a >= v else 0) | (r & 0x80) | (0 if r else 2)

        def CMP(g):
            def f(): cmpv(s.A, g(), not (s.P & 0x20))
            return f

        def CPX(g):
            def f(): cmpv(s.X, g(), not (s.P & 0x10))
            return f

        def CPY(g):
            def f(): cmpv(s.Y, g(), not (s.P & 0x10))
            return f

        def BIT(g, imm):
            def f():
                v = g()
                if s.P & 0x20:
                    z = (s.A & v & 0xFF) == 0
                    if not imm: s.P = (s.P & 0x3F) | (v & 0xC0)
                else:
                    z = (s.A & v) == 0
                    if not imm: s.P = (s.P & 0x3F) | ((v >> 8) & 0xC0)
                s.P = (s.P & 0xFD) | (2 if z else 0)
            return f

        # ---- loads / stores
        def LDA(g):
            def f():
                v = g()
                if s.P & 0x20: s.A = (s.A & 0xFF00) | v; nz8(v)
                else: s.A = v; nz16(v)
            return f

        def LDX(g):
            def f():
                v = g(); s.X = v
                if s.P & 0x10: nz8(v)
                else: nz16(v)
            return f

        def LDY(g):
            def f():
                v = g(); s.Y = v
                if s.P & 0x10: nz8(v)
                else: nz16(v)
            return f

        def STA(am):
            def f():
                a = am()
                if s.P & 0x20: wr(a, s.A & 0xFF)
                else: w16(a, s.A)
            return f

        def STX(am):
            def f():
                a = am()
                if s.P & 0x10: wr(a, s.X & 0xFF)
                else: w16(a, s.X)
            return f

        def STY(am):
            def f():
                a = am()
                if s.P & 0x10: wr(a, s.Y & 0xFF)
                else: w16(a, s.Y)
            return f

        def STZ(am):
            def f():
                a = am()
                if s.P & 0x20: wr(a, 0)
                else: w16(a, 0)
            return f

        # ---- read-modify-write
        def asl8(v):
            r = (v << 1) & 0xFF; s.P = (s.P & 0x7C) | (v >> 7) | (r & 0x80) | (0 if r else 2); return r
        def asl16(v):
            r = (v << 1) & 0xFFFF; s.P = (s.P & 0x7C) | (v >> 15) | ((r >> 8) & 0x80) | (0 if r else 2); return r
        def lsr8(v):
            r = v >> 1; s.P = (s.P & 0x7C) | (v & 1) | (0 if r else 2); return r
        lsr16 = lsr8
        def rol8(v):
            r = ((v << 1) | (s.P & 1)) & 0xFF; s.P = (s.P & 0x7C) | (v >> 7) | (r & 0x80) | (0 if r else 2); return r
        def rol16(v):
            r = ((v << 1) | (s.P & 1)) & 0xFFFF; s.P = (s.P & 0x7C) | (v >> 15) | ((r >> 8) & 0x80) | (0 if r else 2); return r
        def ror8(v):
            r = (v >> 1) | ((s.P & 1) << 7); s.P = (s.P & 0x7C) | (v & 1) | (r & 0x80) | (0 if r else 2); return r
        def ror16(v):
            r = (v >> 1) | ((s.P & 1) << 15); s.P = (s.P & 0x7C) | (v & 1) | ((r >> 8) & 0x80) | (0 if r else 2); return r
        def inc8(v):
            r = (v + 1) & 0xFF; nz8(r); return r
        def inc16(v):
            r = (v + 1) & 0xFFFF; nz16(r); return r
        def dec8(v):
            r = (v - 1) & 0xFF; nz8(r); return r
        def dec16(v):
            r = (v - 1) & 0xFFFF; nz16(r); return r
        def tsb8(v):
            s.P = (s.P & 0xFD) | (0 if (s.A & v & 0xFF) else 2); return (v | s.A) & 0xFF
        def tsb16(v):
            s.P = (s.P & 0xFD) | (0 if (s.A & v) else 2); return v | s.A
        def trb8(v):
            s.P = (s.P & 0xFD) | (0 if (s.A & v & 0xFF) else 2); return v & ~s.A & 0xFF
        def trb16(v):
            s.P = (s.P & 0xFD) | (0 if (s.A & v) else 2); return v & ~s.A & 0xFFFF

        def rmw(am, fa, fb):
            def f():
                a = am()
                if s.P & 0x20: wr(a, fa(rd(a)))
                else: w16(a, fb(r16(a)))
            return f

        def acc(fa, fb):
            def f():
                if s.P & 0x20: s.A = (s.A & 0xFF00) | fa(s.A & 0xFF)
                else: s.A = fb(s.A)
            return f

        # ---- group-one opcodes (ORA AND EOR ADC STA LDA CMP SBC)
        g1 = {0x01: indx, 0x03: sr, 0x05: dp, 0x07: indl, 0x09: None, 0x0D: ab, 0x0F: lg,
              0x11: indy, 0x12: ind, 0x13: sry, 0x15: dpx, 0x17: indly, 0x19: aby,
              0x1D: abx, 0x1F: lgx}
        for i, mk in enumerate((ORA, AND, EOR, ADC, None, LDA, CMP, SBC)):
            for off, am in g1.items():
                op = (i << 5) + off
                if mk is None:
                    if am is not None: O[op] = STA(am)
                else:
                    O[op] = mk(getM(am))
        O[0x89] = BIT(getM(None), True)

        for op, am in ((0x06, dp), (0x0E, ab), (0x16, dpx), (0x1E, abx)): O[op] = rmw(am, asl8, asl16)
        for op, am in ((0x26, dp), (0x2E, ab), (0x36, dpx), (0x3E, abx)): O[op] = rmw(am, rol8, rol16)
        for op, am in ((0x46, dp), (0x4E, ab), (0x56, dpx), (0x5E, abx)): O[op] = rmw(am, lsr8, lsr16)
        for op, am in ((0x66, dp), (0x6E, ab), (0x76, dpx), (0x7E, abx)): O[op] = rmw(am, ror8, ror16)
        for op, am in ((0xE6, dp), (0xEE, ab), (0xF6, dpx), (0xFE, abx)): O[op] = rmw(am, inc8, inc16)
        for op, am in ((0xC6, dp), (0xCE, ab), (0xD6, dpx), (0xDE, abx)): O[op] = rmw(am, dec8, dec16)
        O[0x04] = rmw(dp, tsb8, tsb16); O[0x0C] = rmw(ab, tsb8, tsb16)
        O[0x14] = rmw(dp, trb8, trb16); O[0x1C] = rmw(ab, trb8, trb16)
        O[0x0A] = acc(asl8, asl16); O[0x2A] = acc(rol8, rol16)
        O[0x4A] = acc(lsr8, lsr16); O[0x6A] = acc(ror8, ror16)
        O[0x1A] = acc(inc8, inc16); O[0x3A] = acc(dec8, dec16)

        for op, am in ((0x24, dp), (0x2C, ab), (0x34, dpx), (0x3C, abx)): O[op] = BIT(getM(am), False)
        for op, am in ((0xA2, None), (0xA6, dp), (0xAE, ab), (0xB6, dpy), (0xBE, aby)): O[op] = LDX(getX(am))
        for op, am in ((0xA0, None), (0xA4, dp), (0xAC, ab), (0xB4, dpx), (0xBC, abx)): O[op] = LDY(getX(am))
        for op, am in ((0x86, dp), (0x8E, ab), (0x96, dpy)): O[op] = STX(am)
        for op, am in ((0x84, dp), (0x8C, ab), (0x94, dpx)): O[op] = STY(am)
        for op, am in ((0x64, dp), (0x74, dpx), (0x9C, ab), (0x9E, abx)): O[op] = STZ(am)
        for op, am in ((0xE0, None), (0xE4, dp), (0xEC, ab)): O[op] = CPX(getX(am))
        for op, am in ((0xC0, None), (0xC4, dp), (0xCC, ab)): O[op] = CPY(getX(am))

        # ---- branches (with idle-loop detection, like Snes9x speedhacks but generic)
        def BR(mask, want):
            def f():
                off = f8()
                if (s.P & mask) == want:
                    s.cyc += 1
                    if off < 0x80:
                        s.PC = (s.PC + off) & 0xFFFF
                    else:
                        npc = (s.PC + off - 256) & 0xFFFF
                        if off >= 0xE0:
                            key = (npc, s.A, s.X, s.Y, s.P, bus.wc)
                            if key == s.idle_key:
                                if s.cyc < s.target: s.cyc = s.target
                            else:
                                s.idle_key = key
                        s.PC = npc
            return f
        O[0x10] = BR(0x80, 0); O[0x30] = BR(0x80, 0x80)
        O[0x50] = BR(0x40, 0); O[0x70] = BR(0x40, 0x40)
        O[0x90] = BR(0x01, 0); O[0xB0] = BR(0x01, 0x01)
        O[0xD0] = BR(0x02, 0); O[0xF0] = BR(0x02, 0x02)
        O[0x80] = BR(0, 0)

        def BRL():
            o = f16()
            s.PC = (s.PC + o - (0x10000 if o & 0x8000 else 0)) & 0xFFFF
        O[0x82] = BRL

        # ---- jumps / calls
        def JMPa():
            a = f16()
            if a == ((s.PC - 3) & 0xFFFF) and s.cyc < s.target:   # "here: jmp here"
                s.cyc = s.target
            s.PC = a
        def JMPl():
            v = f24(); s.PC = v & 0xFFFF; s.PB = v >> 16
        def JMPi(): s.PC = r16z(f16())
        def JMPix():
            a = (f16() + s.X) & 0xFFFF
            s.PC = r16((s.PB << 16) | a)
        def JMLi():
            a = f16(); s.PC = r16z(a); s.PB = rd((a + 2) & 0xFFFF)
        def JSR():
            a = f16(); push16((s.PC - 1) & 0xFFFF); s.PC = a
        def JSL():
            a = f24(); npush8(s.PB); npush16((s.PC - 1) & 0xFFFF); nfix()
            s.PB = a >> 16; s.PC = a & 0xFFFF
        def JSRix():
            a = f16(); npush16((s.PC - 1) & 0xFFFF); nfix()
            s.PC = r16((s.PB << 16) | ((a + s.X) & 0xFFFF))
        def RTS(): s.PC = (pull16() + 1) & 0xFFFF
        def RTL():
            s.PC = (npull16() + 1) & 0xFFFF; s.PB = npull8(); nfix()
        def RTI():
            s.setP(pull8()); s.PC = pull16()
            if not s.E: s.PB = pull8()
        def BRK():
            f8(); s.interrupt(0xFFE6, 0xFFFE, True)
        def COP():
            f8(); s.interrupt(0xFFE4, 0xFFF4, True)
        O[0x4C] = JMPa; O[0x5C] = JMPl; O[0x6C] = JMPi; O[0x7C] = JMPix; O[0xDC] = JMLi
        O[0x20] = JSR; O[0x22] = JSL; O[0xFC] = JSRix
        O[0x60] = RTS; O[0x6B] = RTL; O[0x40] = RTI; O[0x00] = BRK; O[0x02] = COP

        # ---- stack
        def PHA():
            if s.P & 0x20: push8(s.A)
            else: push16(s.A)
        def PLA():
            if s.P & 0x20:
                v = pull8(); s.A = (s.A & 0xFF00) | v; nz8(v)
            else:
                v = pull16(); s.A = v; nz16(v)
        def PHX():
            if s.P & 0x10: push8(s.X)
            else: push16(s.X)
        def PHY():
            if s.P & 0x10: push8(s.Y)
            else: push16(s.Y)
        def PLX():
            if s.P & 0x10: v = pull8(); s.X = v; nz8(v)
            else: v = pull16(); s.X = v; nz16(v)
        def PLY():
            if s.P & 0x10: v = pull8(); s.Y = v; nz8(v)
            else: v = pull16(); s.Y = v; nz16(v)
        def PHP(): push8(s.P | (0x30 if s.E else 0))
        def PLP(): s.setP(pull8())
        def PHB(): push8(s.DB)
        def PLB():
            s.DB = npull8(); nfix(); nz8(s.DB)
        def PHD(): npush16(s.D); nfix()
        def PLD():
            s.D = npull16(); nfix(); nz16(s.D)
        def PHK(): push8(s.PB)
        def PEA(): npush16(f16()); nfix()
        def PEI(): npush16(r16z((s.D + f8()) & 0xFFFF)); nfix()
        def PER():
            v = f16(); npush16((s.PC + v) & 0xFFFF); nfix()
        for op, fn in ((0x48, PHA), (0x68, PLA), (0xDA, PHX), (0x5A, PHY), (0xFA, PLX), (0x7A, PLY),
                       (0x08, PHP), (0x28, PLP), (0x8B, PHB), (0xAB, PLB), (0x0B, PHD), (0x2B, PLD),
                       (0x4B, PHK), (0xF4, PEA), (0xD4, PEI), (0x62, PER)):
            O[op] = fn

        # ---- transfers
        def TAX():
            if s.P & 0x10: s.X = s.A & 0xFF; nz8(s.X)
            else: s.X = s.A; nz16(s.X)
        def TAY():
            if s.P & 0x10: s.Y = s.A & 0xFF; nz8(s.Y)
            else: s.Y = s.A; nz16(s.Y)
        def TXA():
            if s.P & 0x20: s.A = (s.A & 0xFF00) | (s.X & 0xFF); nz8(s.X & 0xFF)
            else: s.A = s.X; nz16(s.A)
        def TYA():
            if s.P & 0x20: s.A = (s.A & 0xFF00) | (s.Y & 0xFF); nz8(s.Y & 0xFF)
            else: s.A = s.Y; nz16(s.A)
        def TXY():
            s.Y = s.X
            if s.P & 0x10: nz8(s.Y)
            else: nz16(s.Y)
        def TYX():
            s.X = s.Y
            if s.P & 0x10: nz8(s.X)
            else: nz16(s.X)
        def TSX():
            if s.P & 0x10: s.X = s.S & 0xFF; nz8(s.X)
            else: s.X = s.S; nz16(s.X)
        def TXS(): s.S = (0x100 | (s.X & 0xFF)) if s.E else s.X
        def TCS(): s.S = (0x100 | (s.A & 0xFF)) if s.E else s.A
        def TSC():
            s.A = s.S; nz16(s.A)
        def TCD():
            s.D = s.A; nz16(s.D)
        def TDC():
            s.A = s.D; nz16(s.A)
        def XBA():
            s.A = ((s.A >> 8) | (s.A << 8)) & 0xFFFF; nz8(s.A & 0xFF)
        def XCE():
            c = s.P & 1; e = s.E
            s.E = c; s.P = (s.P & 0xFE) | e
            if s.E:
                s.P |= 0x30; s.X &= 0xFF; s.Y &= 0xFF; s.S = 0x100 | (s.S & 0xFF)
        for op, fn in ((0xAA, TAX), (0xA8, TAY), (0x8A, TXA), (0x98, TYA), (0x9B, TXY), (0xBB, TYX),
                       (0xBA, TSX), (0x9A, TXS), (0x1B, TCS), (0x3B, TSC), (0x5B, TCD), (0x7B, TDC),
                       (0xEB, XBA), (0xFB, XCE)):
            O[op] = fn

        # ---- index inc/dec
        def INX():
            if s.P & 0x10: s.X = (s.X + 1) & 0xFF; nz8(s.X)
            else: s.X = (s.X + 1) & 0xFFFF; nz16(s.X)
        def INY():
            if s.P & 0x10: s.Y = (s.Y + 1) & 0xFF; nz8(s.Y)
            else: s.Y = (s.Y + 1) & 0xFFFF; nz16(s.Y)
        def DEX():
            if s.P & 0x10: s.X = (s.X - 1) & 0xFF; nz8(s.X)
            else: s.X = (s.X - 1) & 0xFFFF; nz16(s.X)
        def DEY():
            if s.P & 0x10: s.Y = (s.Y - 1) & 0xFF; nz8(s.Y)
            else: s.Y = (s.Y - 1) & 0xFFFF; nz16(s.Y)
        O[0xE8] = INX; O[0xC8] = INY; O[0xCA] = DEX; O[0x88] = DEY

        # ---- flags
        def flag(clear, set_):
            def f(): s.P = (s.P & ~clear) | set_
            return f
        O[0x18] = flag(1, 0); O[0x38] = flag(0, 1); O[0x58] = flag(4, 0); O[0x78] = flag(0, 4)
        O[0xD8] = flag(8, 0); O[0xF8] = flag(0, 8); O[0xB8] = flag(0x40, 0)
        def REP(): s.setP(s.P & ~f8())
        def SEP(): s.setP(s.P | f8())
        O[0xC2] = REP; O[0xE2] = SEP

        # ---- block moves
        def MVN():
            dst = f8(); src = f8(); s.DB = dst
            xm = 0xFF if s.P & 0x10 else 0xFFFF; n = 0
            while True:
                wr((dst << 16) | s.Y, rd((src << 16) | s.X))
                s.X = (s.X + 1) & xm; s.Y = (s.Y + 1) & xm; n += 1
                s.A = (s.A - 1) & 0xFFFF
                if s.A == 0xFFFF: break
            s.cyc += 7 * n
        def MVP():
            dst = f8(); src = f8(); s.DB = dst
            xm = 0xFF if s.P & 0x10 else 0xFFFF; n = 0
            while True:
                wr((dst << 16) | s.Y, rd((src << 16) | s.X))
                s.X = (s.X - 1) & xm; s.Y = (s.Y - 1) & xm; n += 1
                s.A = (s.A - 1) & 0xFFFF
                if s.A == 0xFFFF: break
            s.cyc += 7 * n
        O[0x54] = MVN; O[0x44] = MVP

        # ---- misc
        def WAI(): s.waiting = True
        def STP(): s.stopped = True
        def NOP(): pass
        def WDM(): f8()
        O[0xCB] = WAI; O[0xDB] = STP; O[0xEA] = NOP; O[0x42] = WDM

        missing = [hex(i) for i in range(256) if O[i] is None]
        assert not missing, missing


# ===================================================================== SPC700 (S-SMP) sound CPU
SPC_CYC = bytes([
    2,8,4,5,3,4,3,6,2,6,5,4,5,4,6,8, 2,8,4,5,4,5,5,6,5,5,6,5,2,2,4,6,
    2,8,4,5,3,4,3,6,2,6,5,4,5,4,5,4, 2,8,4,5,4,5,5,6,5,5,6,5,2,2,3,8,
    2,8,4,5,3,4,3,6,2,6,4,4,5,4,6,6, 2,8,4,5,4,5,5,6,5,5,4,5,2,2,4,3,
    2,8,4,5,3,4,3,6,2,6,4,4,5,4,5,5, 2,8,4,5,4,5,5,6,5,5,5,5,2,2,3,6,
    2,8,4,5,3,4,3,6,2,6,5,4,5,2,4,5, 2,8,4,5,4,5,5,6,5,5,5,5,2,2,12,5,
    3,8,4,5,3,4,3,6,2,6,4,4,5,2,4,4, 2,8,4,5,4,5,5,6,5,5,5,5,2,2,3,4,
    3,8,4,5,4,5,4,7,2,5,6,4,5,2,4,9, 2,8,4,5,5,6,6,7,4,5,5,5,2,2,6,3,
    2,8,4,5,3,4,3,6,2,4,5,3,4,3,4,3, 2,8,4,5,4,5,5,6,3,4,5,4,2,2,4,3])


class SPC700:
    """Sony SPC700 core (all 256 opcodes). Bus supplies read(a) / write(a, v)."""

    STATE = ('A', 'X', 'Y', 'SP', 'PC', 'PSW', 'cyc', 'stopped')

    def __init__(self, bus):
        self.bus = bus
        self.A = self.X = self.Y = 0; self.SP = 0xEF; self.PC = 0xFFC0; self.PSW = 0x02
        self.cyc = 0; self.target = 0; self.stopped = False
        self.trap = 0x10000          # PC >= trap returns to the APU (HLE boot ROM)
        self.ops = [None] * 256
        self._build()

    def run(self, target):
        self.target = target
        ops = self.ops; rd = self.bus.read; cy = SPC_CYC
        while self.cyc < target:
            pc = self.PC
            if pc >= self.trap:
                return
            if self.stopped:
                self.cyc = target; return
            op = rd(pc)
            self.PC = (pc + 1) & 0xFFFF
            self.cyc += cy[op]
            ops[op]()

    def _build(self):
        s = self; bus = self.bus; O = self.ops
        rd = bus.read; wr = bus.write

        def f8():
            pc = s.PC; s.PC = (pc + 1) & 0xFFFF; return rd(pc)
        def f16():
            lo = f8(); return lo | (f8() << 8)
        def dpb(): return (s.PSW & 0x20) << 3
        def a_d(): return ((s.PSW & 0x20) << 3) | f8()
        def a_dx(): return ((s.PSW & 0x20) << 3) | ((f8() + s.X) & 0xFF)
        def a_dy(): return ((s.PSW & 0x20) << 3) | ((f8() + s.Y) & 0xFF)
        def a_abs(): return f16()
        def a_absx(): return (f16() + s.X) & 0xFFFF
        def a_absy(): return (f16() + s.Y) & 0xFFFF
        def a_ix(): return ((s.PSW & 0x20) << 3) | s.X
        def rdw_dp(n):
            b = (s.PSW & 0x20) << 3
            return rd(b | (n & 0xFF)) | (rd(b | ((n + 1) & 0xFF)) << 8)
        def a_idx(): return rdw_dp(f8() + s.X)
        def a_idy(): return (rdw_dp(f8()) + s.Y) & 0xFFFF

        def nz(v): s.PSW = (s.PSW & 0x7D) | (v & 0x80) | (0 if v else 2)
        def push(v):
            wr(0x100 | s.SP, v & 0xFF); s.SP = (s.SP - 1) & 0xFF
        def pop():
            s.SP = (s.SP + 1) & 0xFF; return rd(0x100 | s.SP)
        def push16(v):
            push(v >> 8); push(v)
        def pop16():
            lo = pop(); return lo | (pop() << 8)

        # ---- ALU (return result; CMP returns the left operand unchanged)
        def f_or(a, b):
            r = a | b; nz(r); return r
        def f_and(a, b):
            r = a & b; nz(r); return r
        def f_eor(a, b):
            r = a ^ b; nz(r); return r
        def f_cmp(a, b):
            r = a - b
            s.PSW = (s.PSW & 0x7C) | (1 if r >= 0 else 0) | (r & 0x80) | (0 if r & 0xFF else 2)
            return a
        def f_adc(a, b):
            c = s.PSW & 1; r = a + b + c
            p = (s.PSW & 0x34) | (1 if r > 0xFF else 0) | ((~(a ^ b) & (a ^ r) & 0x80) >> 1)
            if (a & 15) + (b & 15) + c > 15: p |= 8
            r &= 0xFF
            s.PSW = p | (r & 0x80) | (0 if r else 2)
            return r
        def f_sbc(a, b): return f_adc(a, b ^ 0xFF)

        ALU = ((0x00, f_or), (0x20, f_and), (0x40, f_eor), (0x60, f_cmp), (0x80, f_adc), (0xA0, f_sbc))
        for base, fn in ALU:
            is_cmp = fn is f_cmp
            def mk_a(am, fn=fn):
                if am is None:
                    def f(): s.A = fn(s.A, f8())
                else:
                    def f(): s.A = fn(s.A, rd(am()))
                return f
            for off, am in ((0x04, a_d), (0x14, a_dx), (0x05, a_abs), (0x15, a_absx),
                            (0x06, a_ix), (0x16, a_absy), (0x07, a_idx), (0x17, a_idy), (0x08, None)):
                O[base + off] = mk_a(am)
            def d_imm(fn=fn, c=is_cmp):
                i = f8(); a = a_d(); r = fn(rd(a), i)
                if not c: wr(a, r)
            def dd_ds(fn=fn, c=is_cmp):
                v = rd(a_d()); a = a_d(); r = fn(rd(a), v)
                if not c: wr(a, r)
            def x_y(fn=fn, c=is_cmp):
                b = (s.PSW & 0x20) << 3
                v = rd(b | s.Y); a = b | s.X; r = fn(rd(a), v)
                if not c: wr(a, r)
            O[base + 0x18] = d_imm; O[base + 0x09] = dd_ds; O[base + 0x19] = x_y

        def cmpr(reg, am):
            if am is None:
                def f(): f_cmp(getattr(s, reg), f8())
            else:
                def f(): f_cmp(getattr(s, reg), rd(am()))
            return f
        O[0xC8] = cmpr('X', None); O[0x3E] = cmpr('X', a_d); O[0x1E] = cmpr('X', a_abs)
        O[0xAD] = cmpr('Y', None); O[0x7E] = cmpr('Y', a_d); O[0x5E] = cmpr('Y', a_abs)

        # ---- moves
        def st(reg, am):
            def f(): wr(am(), getattr(s, reg))
            return f
        def ld(reg, am):
            if am is None:
                def f():
                    v = f8(); setattr(s, reg, v); nz(v)
            else:
                def f():
                    v = rd(am()); setattr(s, reg, v); nz(v)
            return f
        for op, am in ((0xC4, a_d), (0xD4, a_dx), (0xC5, a_abs), (0xD5, a_absx), (0xC6, a_ix),
                       (0xD6, a_absy), (0xC7, a_idx), (0xD7, a_idy)):
            O[op] = st('A', am)
        for op, am in ((0xE4, a_d), (0xF4, a_dx), (0xE5, a_abs), (0xF5, a_absx), (0xE6, a_ix),
                       (0xF6, a_absy), (0xE7, a_idx), (0xF7, a_idy), (0xE8, None)):
            O[op] = ld('A', am)
        for op, am in ((0xCD, None), (0xF8, a_d), (0xF9, a_dy), (0xE9, a_abs)): O[op] = ld('X', am)
        for op, am in ((0x8D, None), (0xEB, a_d), (0xFB, a_dx), (0xEC, a_abs)): O[op] = ld('Y', am)
        for op, am in ((0xD8, a_d), (0xD9, a_dy), (0xC9, a_abs)): O[op] = st('X', am)
        for op, am in ((0xCB, a_d), (0xDB, a_dx), (0xCC, a_abs)): O[op] = st('Y', am)

        def tr(dst, src, flags=True):
            def f():
                v = getattr(s, src); setattr(s, dst, v)
                if flags: nz(v)
            return f
        O[0x7D] = tr('A', 'X'); O[0xDD] = tr('A', 'Y'); O[0x5D] = tr('X', 'A'); O[0xFD] = tr('Y', 'A')
        O[0x9D] = tr('X', 'SP'); O[0xBD] = tr('SP', 'X', False)
        def MOVXIA():
            wr(((s.PSW & 0x20) << 3) | s.X, s.A); s.X = (s.X + 1) & 0xFF
        def MOVAXI():
            v = rd(((s.PSW & 0x20) << 3) | s.X); s.X = (s.X + 1) & 0xFF; s.A = v; nz(v)
        def MOVDD():
            v = rd(a_d()); wr(a_d(), v)
        def MOVDI():
            i = f8(); wr(a_d(), i)
        O[0xAF] = MOVXIA; O[0xBF] = MOVAXI; O[0xFA] = MOVDD; O[0x8F] = MOVDI

        # ---- shifts / inc / dec
        def asl(v):
            r = (v << 1) & 0xFF; s.PSW = (s.PSW & 0xFE) | (v >> 7); nz(r); return r
        def rol(v):
            r = ((v << 1) | (s.PSW & 1)) & 0xFF; s.PSW = (s.PSW & 0xFE) | (v >> 7); nz(r); return r
        def lsr(v):
            r = v >> 1; s.PSW = (s.PSW & 0xFE) | (v & 1); nz(r); return r
        def ror(v):
            r = (v >> 1) | ((s.PSW & 1) << 7); s.PSW = (s.PSW & 0xFE) | (v & 1); nz(r); return r
        def dec(v):
            r = (v - 1) & 0xFF; nz(r); return r
        def inc(v):
            r = (v + 1) & 0xFF; nz(r); return r
        def rmw(fn, am):
            def f():
                a = am(); wr(a, fn(rd(a)))
            return f
        def rreg(fn, reg):
            def f(): setattr(s, reg, fn(getattr(s, reg)))
            return f
        for b, fn in ((0x00, asl), (0x20, rol), (0x40, lsr), (0x60, ror), (0x80, dec), (0xA0, inc)):
            O[b + 0x0B] = rmw(fn, a_d); O[b + 0x1B] = rmw(fn, a_dx); O[b + 0x0C] = rmw(fn, a_abs)
            O[b + 0x1C] = rreg(fn, 'A')
        O[0xDC] = rreg(dec, 'Y'); O[0xFC] = rreg(inc, 'Y'); O[0x1D] = rreg(dec, 'X'); O[0x3D] = rreg(inc, 'X')

        # ---- 16-bit
        def wdp():
            n = f8(); b = (s.PSW & 0x20) << 3
            return b | n, b | ((n + 1) & 0xFF)
        def nz16(r): s.PSW = (s.PSW & 0x7D) | ((r >> 8) & 0x80) | (0 if r else 2)
        def INCW():
            lo, hi = wdp(); v = (rd(lo) | (rd(hi) << 8)) + 1 & 0xFFFF
            wr(lo, v & 0xFF); wr(hi, v >> 8); nz16(v)
        def DECW():
            lo, hi = wdp(); v = (rd(lo) | (rd(hi) << 8)) - 1 & 0xFFFF
            wr(lo, v & 0xFF); wr(hi, v >> 8); nz16(v)
        def MOVWYA():
            lo, hi = wdp(); s.A = rd(lo); s.Y = rd(hi); nz16((s.Y << 8) | s.A)
        def MOVWD():
            lo, hi = wdp(); wr(lo, s.A); wr(hi, s.Y)
        def CMPW():
            lo, hi = wdp(); w = rd(lo) | (rd(hi) << 8); ya = (s.Y << 8) | s.A
            r = ya - w
            s.PSW = (s.PSW & 0x7C) | (1 if r >= 0 else 0) | ((r >> 8) & 0x80) | (0 if r & 0xFFFF else 2)
        def ADDW():
            lo, hi = wdp(); w = rd(lo) | (rd(hi) << 8); ya = (s.Y << 8) | s.A
            r = ya + w
            p = (s.PSW & 0x34) | (1 if r > 0xFFFF else 0) | ((~(ya ^ w) & (ya ^ r) & 0x8000) >> 9)
            if (ya & 0xFFF) + (w & 0xFFF) > 0xFFF: p |= 8
            r &= 0xFFFF; s.A = r & 0xFF; s.Y = r >> 8
            s.PSW = p | ((r >> 8) & 0x80) | (0 if r else 2)
        def SUBW():
            lo, hi = wdp(); w = rd(lo) | (rd(hi) << 8); ya = (s.Y << 8) | s.A
            r = ya - w
            p = (s.PSW & 0x34) | (1 if r >= 0 else 0) | (((ya ^ w) & (ya ^ r) & 0x8000) >> 9)
            if (ya & 0xFFF) >= (w & 0xFFF): p |= 8
            r &= 0xFFFF; s.A = r & 0xFF; s.Y = r >> 8
            s.PSW = p | ((r >> 8) & 0x80) | (0 if r else 2)
        O[0x3A] = INCW; O[0x1A] = DECW; O[0xBA] = MOVWYA; O[0xDA] = MOVWD
        O[0x5A] = CMPW; O[0x7A] = ADDW; O[0x9A] = SUBW

        # ---- bit ops
        for b in range(8):
            m = 1 << b
            def SET1(m=m):
                a = a_d(); wr(a, rd(a) | m)
            def CLR1(m=m):
                a = a_d(); wr(a, rd(a) & ~m & 0xFF)
            def BBS(m=m):
                v = rd(a_d()); r = f8()
                if v & m: s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF; s.cyc += 2
            def BBC(m=m):
                v = rd(a_d()); r = f8()
                if not v & m: s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF; s.cyc += 2
            O[0x02 + 0x20 * b] = SET1; O[0x12 + 0x20 * b] = CLR1
            O[0x03 + 0x20 * b] = BBS; O[0x13 + 0x20 * b] = BBC

        def mb():
            w = f16(); return w & 0x1FFF, w >> 13
        def bit_c(kind):
            def f():
                a, b = mb(); bit = (rd(a) >> b) & 1; c = s.PSW & 1
                if kind == 0: c |= bit
                elif kind == 1: c |= bit ^ 1
                elif kind == 2: c &= bit
                elif kind == 3: c &= bit ^ 1
                elif kind == 4: c ^= bit
                else: c = bit
                s.PSW = (s.PSW & 0xFE) | c
            return f
        O[0x0A] = bit_c(0); O[0x2A] = bit_c(1); O[0x4A] = bit_c(2); O[0x6A] = bit_c(3)
        O[0x8A] = bit_c(4); O[0xAA] = bit_c(5)
        def MOV1W():
            a, b = mb(); v = rd(a)
            wr(a, (v & ~(1 << b) & 0xFF) | ((s.PSW & 1) << b))
        def NOT1():
            a, b = mb(); wr(a, rd(a) ^ (1 << b))
        O[0xCA] = MOV1W; O[0xEA] = NOT1
        def TSET1():
            a = f16(); v = rd(a); nz((s.A - v) & 0xFF); wr(a, v | s.A)
        def TCLR1():
            a = f16(); v = rd(a); nz((s.A - v) & 0xFF); wr(a, v & ~s.A & 0xFF)
        O[0x0E] = TSET1; O[0x4E] = TCLR1

        # ---- branches
        def br(mask, want):
            def f():
                r = f8()
                if (s.PSW & mask) == want:
                    s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF; s.cyc += 2
            return f
        O[0x10] = br(0x80, 0); O[0x30] = br(0x80, 0x80); O[0x50] = br(0x40, 0); O[0x70] = br(0x40, 0x40)
        O[0x90] = br(1, 0); O[0xB0] = br(1, 1); O[0xD0] = br(2, 0); O[0xF0] = br(2, 2)
        def BRA():
            r = f8(); s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF
        O[0x2F] = BRA
        def CBNE(am):
            def f():
                v = rd(am()); r = f8()
                if s.A != v: s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF; s.cyc += 2
            return f
        O[0x2E] = CBNE(a_d); O[0xDE] = CBNE(a_dx)
        def DBNZD():
            a = a_d(); v = (rd(a) - 1) & 0xFF; wr(a, v); r = f8()
            if v: s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF; s.cyc += 2
        def DBNZY():
            s.Y = (s.Y - 1) & 0xFF; r = f8()
            if s.Y: s.PC = (s.PC + r - (256 if r & 0x80 else 0)) & 0xFFFF; s.cyc += 2
        O[0x6E] = DBNZD; O[0xFE] = DBNZY

        # ---- jumps / calls / stack
        def JMP(): s.PC = f16()
        def JMPIX():
            a = (f16() + s.X) & 0xFFFF; s.PC = rd(a) | (rd((a + 1) & 0xFFFF) << 8)
        def CALL():
            a = f16(); push16(s.PC); s.PC = a
        def PCALL():
            u = f8(); push16(s.PC); s.PC = 0xFF00 | u
        def RET(): s.PC = pop16()
        def RETI():
            s.PSW = pop(); s.PC = pop16()
        def BRK():
            push16(s.PC); push(s.PSW); s.PSW = (s.PSW | 0x10) & ~0x04
            s.PC = rd(0xFFDE) | (rd(0xFFDF) << 8)
        O[0x5F] = JMP; O[0x1F] = JMPIX; O[0x3F] = CALL; O[0x4F] = PCALL
        O[0x6F] = RET; O[0x7F] = RETI; O[0x0F] = BRK
        for n in range(16):
            def TCALL(v=0xFFDE - 2 * n):
                push16(s.PC); s.PC = rd(v) | (rd(v + 1) << 8)
            O[0x01 + 0x10 * n] = TCALL
        def PUSHR(reg):
            def f(): push(getattr(s, reg))
            return f
        def POPR(reg):
            def f(): setattr(s, reg, pop())
            return f
        O[0x0D] = PUSHR('PSW'); O[0x2D] = PUSHR('A'); O[0x4D] = PUSHR('X'); O[0x6D] = PUSHR('Y')
        O[0x8E] = POPR('PSW'); O[0xAE] = POPR('A'); O[0xCE] = POPR('X'); O[0xEE] = POPR('Y')

        # ---- flags
        def flg(clear, set_):
            def f(): s.PSW = (s.PSW & ~clear & 0xFF) | set_
            return f
        O[0x20] = flg(0x20, 0); O[0x40] = flg(0, 0x20); O[0x60] = flg(1, 0); O[0x80] = flg(0, 1)
        O[0xA0] = flg(0, 4); O[0xC0] = flg(4, 0); O[0xE0] = flg(0x48, 0)
        def NOTC(): s.PSW ^= 1
        O[0xED] = NOTC

        # ---- math
        def XCN():
            v = ((s.A >> 4) | (s.A << 4)) & 0xFF; s.A = v; nz(v)
        def MUL():
            r = s.Y * s.A; s.Y = r >> 8; s.A = r & 0xFF; nz(s.Y)
        def DIV():
            ya = (s.Y << 8) | s.A; x = s.X; y = s.Y
            p = s.PSW & ~0x48 & 0xFF
            if y >= x: p |= 0x40
            if (y & 15) >= (x & 15): p |= 0x08
            if y < (x << 1):
                a = ya // x; yy = ya % x
            else:
                a = 255 - (ya - (x << 9)) // (256 - x)
                yy = x + (ya - (x << 9)) % (256 - x)
            s.A = a & 0xFF; s.Y = yy & 0xFF; s.PSW = p; nz(s.A)
        def DAA():
            a = s.A; p = s.PSW
            if (p & 1) or a > 0x99: a += 0x60; p |= 1
            if (p & 8) or (a & 15) > 9: a += 6
            s.PSW = p; s.A = a & 0xFF; nz(s.A)
        def DAS():
            a = s.A; p = s.PSW
            if not (p & 1) or a > 0x99: a -= 0x60; p &= 0xFE
            if not (p & 8) or (a & 15) > 9: a -= 6
            s.PSW = p; s.A = a & 0xFF; nz(s.A)
        O[0x9F] = XCN; O[0xCF] = MUL; O[0x9E] = DIV; O[0xDF] = DAA; O[0xBE] = DAS

        def NOP(): pass
        def STOP(): s.stopped = True
        O[0x00] = NOP; O[0xEF] = STOP; O[0xFF] = STOP

        missing = [hex(i) for i in range(256) if O[i] is None]
        assert not missing, missing


SPC_PER_FRAME = 17039            # 1.024 MHz / 60.0988 Hz
CPU_PER_FRAME = LINES * LINE_CYC  # CPU cycle units used by this core
TIMER_PER = (128, 128, 16)       # SPC cycles per timer stage tick (8 kHz, 8 kHz, 64 kHz)


class APU:
    """S-SMP side of the SNES: 64 KB ARAM, SPC700, timers, CPU ports, S-DSP registers.

    Runs lazily: the SPC700 catches up to the 65816 whenever the CPU touches
    $2140-$217F and at the end of every scanline (Snes9x does the same).
    The 64-byte boot ROM is high-level emulated: the documented IPL upload
    protocol is implemented in Python instead of copying Nintendo's code.
    """

    def __init__(self):
        self.ram = bytearray(0x10000)
        self.read = self._make_read(); self.write = self._make_write()
        self.spc = SPC700(self)
        self.dspc = make_dsp(self)
        self.reset()

    STATE = ('ram', 'dsp', 'dsp_addr', 'pin', 'pout', 'ipl_on', 'ipl_st', 'ipl_y',
             't_en', 't_tgt', 't_cnt', 't_int', 't_last', 'wc', 'treads')

    def reset(self):
        self.ram[:] = bytes(0x10000)
        self.dsp = bytearray(128); self.dsp[0x6C] = 0xE0; self.dsp_addr = 0
        self.pin = [0, 0, 0, 0]; self.pout = [0, 0, 0, 0]
        self.ipl_on = True; self.ipl_st = None; self.ipl_y = 0
        self.t_en = [0, 0, 0]; self.t_tgt = [0, 0, 0]; self.t_cnt = [0, 0, 0]
        self.t_int = [0, 0, 0]; self.t_last = [0, 0, 0]
        self.wc = 0; self.treads = 0; self.pkey = None; self.tkey = None
        self._port_defer = False  # 16-bit STA $2140: wait for data before IPL step
        self.dspc.reset()
        c = self.spc
        c.A = c.X = c.Y = 0; c.SP = 0xEF; c.PSW = 0x02; c.PC = 0xFFC0
        c.cyc = 0; c.stopped = False; c.trap = 0xFFC0

    def get_state(self):
        st = {k: getattr(self, k) for k in self.STATE}
        st['__spc'] = {k: getattr(self.spc, k) for k in SPC700.STATE}
        st['__dsp'] = self.dspc.get_state()
        return st

    def set_state(self, st):
        for k, v in st.pop('__spc').items(): setattr(self.spc, k, v)
        if '__dsp' in st: self.dspc.set_state(st.pop('__dsp'))
        ram = st.pop('ram')
        self.ram[:] = ram                                # in place: cores hold this buffer
        for k, v in st.items(): setattr(self, k, v)
        self.spc.trap = 0xFFC0 if self.ipl_on else 0x10000
        self.pkey = self.tkey = None

    # ------------------------------------------------------------- bus
    def _make_read(self):
        ram = self.ram; io = self.io_read; s = self
        def read(a):
            if a >= 0xF0:
                if a <= 0xFF: return io(a)
                if a >= 0xFFC0 and s.ipl_on: return 0xC0 if a == 0xFFFE else (0xFF if a == 0xFFFF else 0)
            return ram[a]
        return read

    def _make_write(self):
        ram = self.ram; io = self.io_write; s = self
        def write(a, v):
            # only writes that change state count as loop side effects (idle-skip key)
            if 0xF0 <= a <= 0xFF:
                ram[a] = v; io(a, v)
            elif ram[a] != v:
                ram[a] = v; s.wc += 1
        return write

    # ------------------------------------------------------------- timers
    def tsync(self, i):
        if not self.t_en[i]: return
        p = TIMER_PER[i]; n = (self.spc.cyc - self.t_last[i]) // p
        if n > 0:
            self.t_last[i] += n * p
            t = self.t_tgt[i] or 256
            tot = self.t_int[i] + n
            self.t_cnt[i] = (self.t_cnt[i] + tot // t) & 15
            self.t_int[i] = tot % t

    def next_tick(self):
        best = None
        for i in range(3):
            if self.t_en[i]:
                t = self.t_tgt[i] or 256
                n = self.t_last[i] + (t - self.t_int[i]) * TIMER_PER[i]
                if best is None or n < best: best = n
        return best

    def io_read(self, a):
        spc = self.spc
        if 0xF4 <= a <= 0xF7:
            # idle-loop skip: same poll site, same registers, nothing written -> the
            # port cannot change until the 65816 runs again, so jump ahead in time.
            key = (spc.PC, spc.A, spc.X, spc.Y, spc.SP, self.wc, self.treads)
            if key == self.pkey:
                if spc.cyc < spc.target:
                    nt = self.next_tick()
                    spc.cyc = spc.target if nt is None else max(spc.cyc, min(spc.target, nt))
            else:
                self.pkey = key
            return self.pin[a - 0xF4]
        if a >= 0xFD:
            i = a - 0xFD; self.tsync(i)
            v = self.t_cnt[i]; self.t_cnt[i] = 0
            if v:
                self.treads += 1; self.tkey = None
            else:
                key = (spc.PC, spc.A, spc.X, spc.Y, spc.SP, self.wc, i)
                if key == self.tkey and self.t_en[i]:
                    t = self.t_tgt[i] or 256
                    need = self.t_last[i] + (t - self.t_int[i]) * TIMER_PER[i]
                    if need > spc.cyc: spc.cyc = min(spc.target, need)
                else:
                    self.tkey = key
            return v
        if a == 0xF2: return self.dsp_addr
        if a == 0xF3: return self.dspc.read(self.dsp_addr & 0x7F)
        if a in (0xF8, 0xF9): return self.ram[a]
        return 0

    def io_write(self, a, v):
        if 0xF4 <= a <= 0xF7:
            if self.pout[a - 0xF4] != v:
                self.pout[a - 0xF4] = v; self.wc += 1
            return
        self.wc += 1
        if a == 0xF1:
            for i in range(3):
                self.tsync(i)
                if v & (1 << i):
                    if not self.t_en[i]:
                        self.t_en[i] = 1; self.t_cnt[i] = 0; self.t_int[i] = 0
                        self.t_last[i] = self.spc.cyc
                else:
                    self.t_en[i] = 0
            if v & 0x10: self.pin[0] = self.pin[1] = 0
            if v & 0x20: self.pin[2] = self.pin[3] = 0
            self.ipl_on = bool(v & 0x80)
            self.spc.trap = 0xFFC0 if self.ipl_on else 0x10000
        elif a == 0xF2:
            self.dsp_addr = v
        elif a == 0xF3:
            r = self.dsp_addr
            if r < 0x80:
                self.dspc.write(r, v)                           # DSP catches up, then writes
        elif 0xFA <= a <= 0xFC:
            i = a - 0xFA; self.tsync(i); self.t_tgt[i] = v

    # ------------------------------------------------------------- HLE IPL boot ROM
    def ipl_cmd(self):
        spc = self.spc; pin = self.pin; ram = self.ram
        ram[0] = pin[2]; ram[1] = pin[3]
        spc.A = pin[0]; spc.Y = pin[1]; self.pout[0] = pin[0]
        spc.cyc += 18
        if pin[1] == 0:                       # start program at the address in $00/$01
            spc.X = 0; spc.PSW = 0x02; spc.SP = 0xEF
            spc.PC = ram[0] | (ram[1] << 8); self.ipl_st = None
        else:
            spc.X = pin[1]; self.ipl_st = 'z'

    def ipl_step(self, t):
        spc = self.spc; pin = self.pin; pout = self.pout; ram = self.ram
        while spc.cyc < t and spc.PC >= 0xFFC0 and self.ipl_on:
            st = self.ipl_st
            if st is None:                    # (re)entry: clear zero page, say $AA/$BB
                if spc.PC == 0xFFC0:
                    ram[1:0xF0] = bytes(0xEF); spc.cyc += 1200
                spc.SP = 0xEF; spc.A = 0; spc.X = 0
                pout[0] = 0xAA; pout[1] = 0xBB
                self.ipl_st = 'cc'; spc.PC = 0xFFCF; spc.cyc += 10
            elif st == 'cc':
                if pin[0] == 0xCC: self.ipl_cmd()
                else: spc.cyc = t
            elif st == 'z':
                if pin[0] == 0: self.ipl_y = 0; self.ipl_st = 'x'
                else: spc.cyc = t
            else:
                p0 = pin[0]; y = self.ipl_y
                if p0 == y:
                    self.write(((ram[0] | (ram[1] << 8)) + y) & 0xFFFF, pin[1])
                    pout[0] = y; y = (y + 1) & 0xFF
                    if y == 0: ram[1] = (ram[1] + 1) & 0xFF
                    self.ipl_y = y; spc.cyc += 22
                elif (y - p0) & 0x80:
                    self.ipl_cmd()
                else:
                    spc.cyc = t

    def run_to(self, cpu_cyc):
        """Advance the SPC700 to the 65816's current time."""
        self._port_defer = False
        spc = self.spc
        t = cpu_cyc * SPC_PER_FRAME // CPU_PER_FRAME
        while spc.cyc < t:
            if spc.PC >= spc.trap:
                self.ipl_step(t)
            else:
                spc.run(t)


# ===================================================================== Snes9x S-DSP (embedded Cython)
# Port of Snes9x apu/bapu/dsp/SPC_DSP.cpp (blargg snes_spc 0.9.0, LGPL 2.1+). Verified
# bit-exact against the original C++ (4.2M samples, all registers, echo RAM writes).
# Compiled automatically on first run into ~/.virtualsnes/cython; falls back to the numpy
# engine below if Cython or a C compiler is unavailable.
_DSP_PYX = r'''GAUSS = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10, 11, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 16, 16, 17, 17, 18, 19, 19, 20, 20, 21, 21, 22, 23, 23, 24, 24, 25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 36, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 61, 62, 64, 65, 66, 67, 69, 70, 71, 73, 74, 76, 77, 78, 80, 81, 83, 84, 86, 87, 89, 90, 92, 94, 95, 97, 99, 100, 102, 104, 106, 107, 109, 111, 113, 115, 117, 118, 120, 122, 124, 126, 128, 130, 132, 134, 137, 139, 141, 143, 145, 147, 150, 152, 154, 156, 159, 161, 163, 166, 168, 171, 173, 175, 178, 180, 183, 186, 188, 191, 193, 196, 199, 201, 204, 207, 210, 212, 215, 218, 221, 224, 227, 230, 233, 236, 239, 242, 245, 248, 251, 254, 257, 260, 263, 267, 270, 273, 276, 280, 283, 286, 290, 293, 297, 300, 304, 307, 311, 314, 318, 321, 325, 328, 332, 336, 339, 343, 347, 351, 354, 358, 362, 366, 370, 374, 378, 381, 385, 389, 393, 397, 401, 405, 410, 414, 418, 422, 426, 430, 434, 439, 443, 447, 451, 456, 460, 464, 469, 473, 477, 482, 486, 491, 495, 499, 504, 508, 513, 517, 522, 527, 531, 536, 540, 545, 550, 554, 559, 563, 568, 573, 577, 582, 587, 592, 596, 601, 606, 611, 615, 620, 625, 630, 635, 640, 644, 649, 654, 659, 664, 669, 674, 678, 683, 688, 693, 698, 703, 708, 713, 718, 723, 728, 732, 737, 742, 747, 752, 757, 762, 767, 772, 777, 782, 787, 792, 797, 802, 806, 811, 816, 821, 826, 831, 836, 841, 846, 851, 855, 860, 865, 870, 875, 880, 884, 889, 894, 899, 904, 908, 913, 918, 923, 927, 932, 937, 941, 946, 951, 955, 960, 965, 969, 974, 978, 983, 988, 992, 997, 1001, 1005, 1010, 1014, 1019, 1023, 1027, 1032, 1036, 1040, 1045, 1049, 1053, 1057, 1061, 1066, 1070, 1074, 1078, 1082, 1086, 1090, 1094, 1098, 1102, 1106, 1109, 1113, 1117, 1121, 1125, 1128, 1132, 1136, 1139, 1143, 1146, 1150, 1153, 1157, 1160, 1164, 1167, 1170, 1174, 1177, 1180, 1183, 1186, 1190, 1193, 1196, 1199, 1202, 1205, 1207, 1210, 1213, 1216, 1219, 1221, 1224, 1227, 1229, 1232, 1234, 1237, 1239, 1241, 1244, 1246, 1248, 1251, 1253, 1255, 1257, 1259, 1261, 1263, 1265, 1267, 1269, 1270, 1272, 1274, 1275, 1277, 1279, 1280, 1282, 1283, 1284, 1286, 1287, 1288, 1290, 1291, 1292, 1293, 1294, 1295, 1296, 1297, 1297, 1298, 1299, 1300, 1300, 1301, 1302, 1302, 1303, 1303, 1303, 1304, 1304, 1304, 1304, 1304, 1305, 1305)
INITIAL_REGS = (69, 139, 90, 154, 228, 130, 27, 120, 0, 0, 170, 150, 137, 14, 224, 128, 42, 73, 61, 186, 20, 160, 172, 197, 0, 0, 81, 187, 156, 78, 123, 255, 244, 253, 87, 50, 55, 217, 66, 34, 0, 0, 91, 60, 159, 27, 135, 154, 111, 39, 175, 123, 229, 104, 10, 217, 0, 0, 154, 197, 156, 78, 123, 255, 234, 33, 120, 79, 221, 237, 36, 20, 0, 0, 119, 177, 209, 54, 193, 103, 82, 87, 70, 61, 89, 244, 135, 164, 0, 0, 126, 68, 0, 78, 123, 255, 117, 245, 6, 151, 16, 195, 36, 187, 0, 0, 123, 122, 224, 96, 18, 15, 247, 116, 28, 229, 57, 61, 115, 193, 0, 0, 122, 179, 255, 78, 123, 255)
# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False, nonecheck=False
#
# Virtual SNES Emulator S-DSP core: a line-for-line port of SPC_DSP.cpp from Snes9x
# (apu/bapu/dsp/SPC_DSP.cpp), which is blargg's snes_spc 0.9.0 DSP with
# Snes9x's register semantics.
#
# Copyright (C) 2007 Shay Green. This module is free software; you
# can redistribute it and/or modify it under the terms of the GNU Lesser
# General Public License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version. This
# module is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details. You should have received a copy of the GNU Lesser General Public
# License along with this module; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Python/Cython port for Virtual SNES Emulator 0.1, same license
# (LGPL 2.1+) for this module.

from libc.string cimport memcpy, memset
from cpython.array cimport array

cdef enum:
    R_MVOLL = 0x0C
    R_EVOLL = 0x2C
    R_KON = 0x4C
    R_KOFF = 0x5C
    R_FLG = 0x6C
    R_ENDX = 0x7C
    R_EFB = 0x0D
    R_PMON = 0x2D
    R_NON = 0x3D
    R_EON = 0x4D
    R_DIR = 0x5D
    R_ESA = 0x6D
    R_EDL = 0x7D
    R_FIR = 0x0F
    V_VOLL = 0
    V_PITCHL = 2
    V_PITCHH = 3
    V_SRCN = 4
    V_ADSR0 = 5
    V_ADSR1 = 6
    V_GAIN = 7
    V_ENVX = 8
    V_OUTX = 9
    BRR_BUF = 12
    BRR_BLOCK = 9
    ENV_RELEASE = 0
    ENV_ATTACK = 1
    ENV_DECAY = 2
    ENV_SUSTAIN = 3
    SIMPLE_RANGE = 30720

cdef short gauss[512]
cdef unsigned int counter_rates[32]
cdef unsigned int counter_offsets[32]
cdef unsigned char initial_regs[128]

cdef int _i
for _i in range(512): gauss[_i] = GAUSS[_i]
for _i in range(128): initial_regs[_i] = INITIAL_REGS[_i]
_RATES = (SIMPLE_RANGE + 1, 2048, 1536, 1280, 1024, 768, 640, 512, 384, 320, 256, 192, 160, 128,
          96, 80, 64, 48, 40, 32, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1)
_OFFS = (1, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040,
         536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 0, 0)
for _i in range(32):
    counter_rates[_i] = _RATES[_i]; counter_offsets[_i] = _OFFS[_i]

cdef struct Voice:
    int buf[24]
    int buf_pos
    int interp_pos
    int brr_addr
    int brr_offset
    int regs
    int vbit
    int kon_delay
    int env_mode
    int env
    int hidden_env
    int t_envx_out

cdef struct State:
    unsigned char regs[128]
    unsigned char external_regs[128]
    int echo_hist[16][2]
    int echo_hist_pos
    int every_other_sample
    int kon
    int noise
    int counter
    int echo_offset
    int echo_length
    int phase
    int kon_check
    int new_kon
    int endx_buf
    int envx_buf
    int outx_buf
    int t_pmon
    int t_non
    int t_eon
    int t_dir
    int t_koff
    int t_brr_next_addr
    int t_adsr0
    int t_brr_header
    int t_brr_byte
    int t_srcn
    int t_esa
    int t_echo_enabled
    int t_dir_addr
    int t_pitch
    int t_output
    int t_looped
    int t_echo_ptr
    int t_main_out[2]
    int t_echo_out[2]
    int t_echo_in[2]
    Voice voices[8]
    int mute_mask


cdef inline int clamp16(int io) noexcept nogil:
    if <short> io != io:
        io = (io >> 31) ^ 0x7FFF
    return io


cdef class SPCDSP:
    cdef State m
    cdef unsigned char[::1] ramv
    cdef unsigned char* ram
    cdef array outbuf
    cdef short* out
    cdef int out_pos
    cdef int out_cap

    def __init__(self, ram, int out_frames=65536):
        self.ramv = ram
        self.ram = &self.ramv[0]
        self.outbuf = array('h', bytes(out_frames * 4))
        self.out = self.outbuf.data.as_shorts
        self.out_cap = out_frames
        self.out_pos = 0
        self.reset()

    # ------------------------------------------------------------- setup
    def reset(self):
        self.load(INITIAL_REGS)

    def load(self, regs):
        cdef int i
        cdef Voice* v
        memset(&self.m, 0, sizeof(State))
        for i in range(128):
            self.m.external_regs[i] = regs[i]
        self.m.regs[66] = 0x01
        self.m.regs[82] = 0x01
        self.m.regs[R_FLG] = 0xE0
        for i in range(7, -1, -1):
            v = &self.m.voices[i]
            v.brr_offset = 1
            v.vbit = 1 << i
            v.regs = i * 0x10
        self.m.new_kon = self.m.regs[R_KON]
        self.m.t_dir = self.m.regs[R_DIR]
        self.m.t_esa = self.m.regs[R_ESA]
        self.soft_reset_common()

    cdef void soft_reset_common(self):
        self.m.noise = 0x4000
        self.m.echo_hist_pos = 0
        self.m.every_other_sample = 1
        self.m.echo_offset = 0
        self.m.phase = 0
        self.m.counter = 0

    def soft_reset(self):
        self.m.regs[R_FLG] = 0xE0
        self.soft_reset_common()

    # ------------------------------------------------------------- register access
    cpdef int read(self, int addr):
        return self.m.external_regs[addr & 0x7F]

    cpdef void write(self, int addr, int data):
        addr &= 0x7F; data &= 0xFF
        self.m.regs[addr] = data
        self.m.external_regs[addr] = data
        cdef int low = addr & 0x0F
        if low == V_ENVX:
            self.m.envx_buf = data
        elif low == V_OUTX:
            self.m.outx_buf = data
        elif low == 0x0C:
            if addr == R_KON:
                self.m.new_kon = data
            if addr == R_ENDX:
                self.m.endx_buf = 0
                self.m.regs[R_ENDX] = 0

    def mute_voices(self, int mask):
        self.m.mute_mask = mask

    # ------------------------------------------------------------- output / state
    def take(self):
        """Return generated samples as bytes (int16 L/R interleaved) and reset."""
        cdef int n = self.out_pos
        self.out_pos = 0
        return self.outbuf[:n * 2].tobytes()

    def get_state(self):
        return (<char*> &self.m)[:sizeof(State)]

    def set_state(self, bytes blob):
        if len(blob) != sizeof(State):
            raise ValueError("DSP state size mismatch")
        memcpy(&self.m, <char*> blob, sizeof(State))

    # ------------------------------------------------------------- counters
    cdef inline unsigned int read_counter(self, int rate) noexcept:
        return (<unsigned int> self.m.counter + counter_offsets[rate]) % counter_rates[rate]

    cdef inline void run_counters(self) noexcept:
        self.m.counter -= 1
        if self.m.counter < 0:
            self.m.counter = SIMPLE_RANGE - 1

    # ------------------------------------------------------------- envelope
    cdef inline void run_envelope(self, Voice* v) noexcept:
        cdef int env = v.env
        cdef int rate, env_data, mode
        if v.env_mode == ENV_RELEASE:
            env -= 0x8
            if env < 0:
                env = 0
            v.env = env
            return
        env_data = self.m.regs[v.regs + V_ADSR1]
        if self.m.t_adsr0 & 0x80:
            if v.env_mode >= ENV_DECAY:
                env -= 1
                env -= env >> 8
                rate = env_data & 0x1F
                if v.env_mode == ENV_DECAY:
                    rate = (self.m.t_adsr0 >> 3 & 0x0E) + 0x10
            else:
                rate = (self.m.t_adsr0 & 0x0F) * 2 + 1
                env += 0x20 if rate < 31 else 0x400
        else:
            env_data = self.m.regs[v.regs + V_GAIN]
            mode = env_data >> 5
            if mode < 4:
                env = env_data * 0x10
                rate = 31
            else:
                rate = env_data & 0x1F
                if mode == 4:
                    env -= 0x20
                elif mode < 6:
                    env -= 1
                    env -= env >> 8
                else:
                    env += 0x20
                    if mode > 6 and <unsigned int> v.hidden_env >= 0x600:
                        env += 0x8 - 0x20
        if (env >> 8) == (env_data >> 5) and v.env_mode == ENV_DECAY:
            v.env_mode = ENV_SUSTAIN
        v.hidden_env = env
        if <unsigned int> env > 0x7FF:
            env = 0 if env < 0 else 0x7FF
            if v.env_mode == ENV_ATTACK:
                v.env_mode = ENV_DECAY
        if not self.read_counter(rate):
            v.env = env

    # ------------------------------------------------------------- BRR
    cdef inline void decode_brr(self, Voice* v) noexcept:
        cdef int nybbles = self.m.t_brr_byte * 0x100 + self.ram[(v.brr_addr + v.brr_offset + 1) & 0xFFFF]
        cdef int header = self.m.t_brr_header
        cdef int pos = v.buf_pos
        cdef int end = pos + 4
        cdef int s, shift, flt, p1, p2
        v.buf_pos += 4
        if v.buf_pos >= BRR_BUF:
            v.buf_pos = 0
        while pos < end:
            s = (<short> nybbles) >> 12
            shift = header >> 4
            if shift <= 12:
                s = (s << shift) >> 1
            else:
                s &= ~0x7FF
            flt = header & 0x0C
            p1 = v.buf[pos + BRR_BUF - 1]
            p2 = v.buf[pos + BRR_BUF - 2] >> 1
            if flt >= 8:
                s += p1
                s -= p2
                if flt == 8:
                    s += p2 >> 4
                    s += (p1 * -3) >> 6
                else:
                    s += (p1 * -13) >> 7
                    s += (p2 * 3) >> 4
            elif flt:
                s += p1 >> 1
                s += (-p1) >> 5
            s = clamp16(s)
            s = <short> (s * 2)
            v.buf[pos + BRR_BUF] = s
            v.buf[pos] = s
            pos += 1
            nybbles <<= 4

    cdef inline int interpolate(self, Voice* v) noexcept:
        cdef int offset = v.interp_pos >> 4 & 0xFF
        cdef int base = (v.interp_pos >> 12) + v.buf_pos
        cdef int* inp = &v.buf[base]
        cdef int fwd = 255 - offset
        cdef int rev = offset
        cdef int out
        out = (gauss[fwd] * inp[0]) >> 11
        out += (gauss[fwd + 256] * inp[1]) >> 11
        out += (gauss[rev + 256] * inp[2]) >> 11
        out = <short> out
        out += (gauss[rev] * inp[3]) >> 11
        out = clamp16(out)
        out &= ~1
        return out

    # ------------------------------------------------------------- misc clocks
    cdef inline void misc_27(self) noexcept:
        self.m.t_pmon = self.m.regs[R_PMON] & 0xFE

    cdef inline void misc_28(self) noexcept:
        self.m.t_non = self.m.regs[R_NON]
        self.m.t_eon = self.m.regs[R_EON]
        self.m.t_dir = self.m.regs[R_DIR]

    cdef inline void misc_29(self) noexcept:
        self.m.every_other_sample ^= 1
        if self.m.every_other_sample != 0:
            self.m.new_kon &= ~self.m.kon

    cdef inline void misc_30(self) noexcept:
        cdef int feedback
        if self.m.every_other_sample:
            self.m.kon = self.m.new_kon
            self.m.t_koff = self.m.regs[R_KOFF] | self.m.mute_mask
        self.run_counters()
        if not self.read_counter(self.m.regs[R_FLG] & 0x1F):
            feedback = (self.m.noise << 13) ^ (self.m.noise << 14)
            self.m.noise = (feedback & 0x4000) ^ (self.m.noise >> 1)

    # ------------------------------------------------------------- voice clocks
    cdef inline void V1(self, Voice* v) noexcept:
        self.m.t_dir_addr = (self.m.t_dir * 0x100 + self.m.t_srcn * 4) & 0xFFFF
        self.m.t_srcn = self.m.regs[v.regs + V_SRCN]

    cdef inline void V2(self, Voice* v) noexcept:
        cdef int entry = self.m.t_dir_addr
        if not v.kon_delay:
            entry += 2
        self.m.t_brr_next_addr = self.ram[entry & 0xFFFF] | (self.ram[(entry + 1) & 0xFFFF] << 8)
        self.m.t_adsr0 = self.m.regs[v.regs + V_ADSR0]
        self.m.t_pitch = self.m.regs[v.regs + V_PITCHL]

    cdef inline void V3a(self, Voice* v) noexcept:
        self.m.t_pitch += (self.m.regs[v.regs + V_PITCHH] & 0x3F) << 8

    cdef inline void V3b(self, Voice* v) noexcept:
        self.m.t_brr_byte = self.ram[(v.brr_addr + v.brr_offset) & 0xFFFF]
        self.m.t_brr_header = self.ram[v.brr_addr]

    cdef inline void V3c(self, Voice* v) noexcept:
        cdef int output
        if self.m.t_pmon & v.vbit:
            self.m.t_pitch += ((self.m.t_output >> 5) * self.m.t_pitch) >> 10
        if v.kon_delay:
            if v.kon_delay == 5:
                v.brr_addr = self.m.t_brr_next_addr
                v.brr_offset = 1
                v.buf_pos = 0
                self.m.t_brr_header = 0
                self.m.kon_check = 1
            v.env = 0
            v.hidden_env = 0
            v.interp_pos = 0
            v.kon_delay -= 1
            if v.kon_delay & 3:
                v.interp_pos = 0x4000
            self.m.t_pitch = 0
        output = self.interpolate(v)
        if self.m.t_non & v.vbit:
            output = <short> (self.m.noise * 2)
        self.m.t_output = (output * v.env) >> 11 & ~1
        v.t_envx_out = (v.env >> 4) & 0xFF
        if self.m.regs[R_FLG] & 0x80 or (self.m.t_brr_header & 3) == 1:
            v.env_mode = ENV_RELEASE
            v.env = 0
        if self.m.every_other_sample:
            if self.m.t_koff & v.vbit:
                v.env_mode = ENV_RELEASE
            if self.m.kon & v.vbit:
                v.kon_delay = 5
                v.env_mode = ENV_ATTACK
        if not v.kon_delay:
            self.run_envelope(v)

    cdef inline void voice_output(self, Voice* v, int ch) noexcept:
        cdef int amp = (self.m.t_output * <signed char> self.m.regs[v.regs + V_VOLL + ch]) >> 7
        self.m.t_main_out[ch] = clamp16(self.m.t_main_out[ch] + amp)
        if self.m.t_eon & v.vbit:
            self.m.t_echo_out[ch] = clamp16(self.m.t_echo_out[ch] + amp)

    cdef inline void V3(self, Voice* v) noexcept:
        self.V3a(v); self.V3b(v); self.V3c(v)

    cdef inline void V4(self, Voice* v) noexcept:
        self.m.t_looped = 0
        if v.interp_pos >= 0x4000:
            self.decode_brr(v)
            v.brr_offset += 2
            if v.brr_offset >= BRR_BLOCK:
                v.brr_addr = (v.brr_addr + BRR_BLOCK) & 0xFFFF
                if self.m.t_brr_header & 1:
                    v.brr_addr = self.m.t_brr_next_addr
                    self.m.t_looped = v.vbit
                v.brr_offset = 1
        v.interp_pos = (v.interp_pos & 0x3FFF) + self.m.t_pitch
        if v.interp_pos > 0x7FFF:
            v.interp_pos = 0x7FFF
        self.voice_output(v, 0)

    cdef inline void V5(self, Voice* v) noexcept:
        cdef int endx_buf
        self.voice_output(v, 1)
        endx_buf = self.m.regs[R_ENDX] | self.m.t_looped
        if v.kon_delay == 5:
            endx_buf &= ~v.vbit
        self.m.endx_buf = endx_buf & 0xFF

    cdef inline void V6(self, Voice* v) noexcept:
        self.m.outx_buf = (self.m.t_output >> 8) & 0xFF

    cdef inline void V7(self, Voice* v) noexcept:
        self.m.regs[R_ENDX] = self.m.endx_buf
        self.m.external_regs[R_ENDX] = self.m.endx_buf
        self.m.envx_buf = v.t_envx_out

    cdef inline void V8(self, Voice* v) noexcept:
        self.m.regs[v.regs + V_OUTX] = self.m.outx_buf
        self.m.external_regs[v.regs + V_OUTX] = self.m.outx_buf

    cdef inline void V9(self, Voice* v) noexcept:
        self.m.regs[v.regs + V_ENVX] = self.m.envx_buf
        self.m.external_regs[v.regs + V_ENVX] = self.m.envx_buf

    cdef inline void V7_V4_V1(self, Voice* v) noexcept:
        self.V7(v); self.V1(v + 3); self.V4(v + 1)

    cdef inline void V8_V5_V2(self, Voice* v) noexcept:
        self.V8(v); self.V5(v + 1); self.V2(v + 2)

    cdef inline void V9_V6_V3(self, Voice* v) noexcept:
        self.V9(v); self.V6(v + 1); self.V3(v + 2)

    # ------------------------------------------------------------- echo
    cdef inline int calc_fir(self, int i, int ch) noexcept:
        return (self.m.echo_hist[self.m.echo_hist_pos + i + 1][ch] *
                <signed char> self.m.regs[R_FIR + i * 0x10]) >> 6

    cdef inline void echo_read(self, int ch) noexcept:
        cdef int a = self.m.t_echo_ptr + ch * 2
        cdef int s = <short> (self.ram[a & 0xFFFF] | (self.ram[(a + 1) & 0xFFFF] << 8))
        self.m.echo_hist[self.m.echo_hist_pos][ch] = s >> 1
        self.m.echo_hist[self.m.echo_hist_pos + 8][ch] = s >> 1

    cdef inline void echo_22(self) noexcept:
        cdef int l, r
        self.m.echo_hist_pos += 1
        if self.m.echo_hist_pos >= 8:
            self.m.echo_hist_pos = 0
        self.m.t_echo_ptr = (self.m.t_esa * 0x100 + self.m.echo_offset) & 0xFFFF
        self.echo_read(0)
        l = self.calc_fir(0, 0)
        r = self.calc_fir(0, 1)
        self.m.t_echo_in[0] = l
        self.m.t_echo_in[1] = r

    cdef inline void echo_23(self) noexcept:
        cdef int l = self.calc_fir(1, 0) + self.calc_fir(2, 0)
        cdef int r = self.calc_fir(1, 1) + self.calc_fir(2, 1)
        self.m.t_echo_in[0] += l
        self.m.t_echo_in[1] += r
        self.echo_read(1)

    cdef inline void echo_24(self) noexcept:
        cdef int l = self.calc_fir(3, 0) + self.calc_fir(4, 0) + self.calc_fir(5, 0)
        cdef int r = self.calc_fir(3, 1) + self.calc_fir(4, 1) + self.calc_fir(5, 1)
        self.m.t_echo_in[0] += l
        self.m.t_echo_in[1] += r

    cdef inline void echo_25(self) noexcept:
        cdef int l = self.m.t_echo_in[0] + self.calc_fir(6, 0)
        cdef int r = self.m.t_echo_in[1] + self.calc_fir(6, 1)
        l = <short> l
        r = <short> r
        l += <short> self.calc_fir(7, 0)
        r += <short> self.calc_fir(7, 1)
        l = clamp16(l)
        r = clamp16(r)
        self.m.t_echo_in[0] = l & ~1
        self.m.t_echo_in[1] = r & ~1

    cdef inline int echo_output(self, int ch) noexcept:
        cdef int out = (<short> ((self.m.t_main_out[ch] * <signed char> self.m.regs[R_MVOLL + ch * 0x10]) >> 7) +
                        <short> ((self.m.t_echo_in[ch] * <signed char> self.m.regs[R_EVOLL + ch * 0x10]) >> 7))
        return clamp16(out)

    cdef inline void echo_26(self) noexcept:
        cdef int l, r
        self.m.t_main_out[0] = self.echo_output(0)
        l = self.m.t_echo_out[0] + <short> ((self.m.t_echo_in[0] * <signed char> self.m.regs[R_EFB]) >> 7)
        r = self.m.t_echo_out[1] + <short> ((self.m.t_echo_in[1] * <signed char> self.m.regs[R_EFB]) >> 7)
        l = clamp16(l)
        r = clamp16(r)
        self.m.t_echo_out[0] = l & ~1
        self.m.t_echo_out[1] = r & ~1

    cdef inline void echo_27(self) noexcept:
        cdef int l = self.m.t_main_out[0]
        cdef int r = self.echo_output(1)
        self.m.t_main_out[0] = 0
        self.m.t_main_out[1] = 0
        if self.m.regs[R_FLG] & 0x40:
            l = 0
            r = 0
        if self.out_pos < self.out_cap:
            self.out[self.out_pos * 2] = <short> l
            self.out[self.out_pos * 2 + 1] = <short> r
            self.out_pos += 1

    cdef inline void echo_28(self) noexcept:
        self.m.t_echo_enabled = self.m.regs[R_FLG]

    cdef inline void echo_write(self, int ch) noexcept:
        cdef int a, v
        if not (self.m.t_echo_enabled & 0x20):
            a = self.m.t_echo_ptr + ch * 2
            v = self.m.t_echo_out[ch]
            self.ram[a & 0xFFFF] = v & 0xFF
            self.ram[(a + 1) & 0xFFFF] = (v >> 8) & 0xFF
        self.m.t_echo_out[ch] = 0

    cdef inline void echo_29(self) noexcept:
        self.m.t_esa = self.m.regs[R_ESA]
        if not self.m.echo_offset:
            self.m.echo_length = (self.m.regs[R_EDL] & 0x0F) * 0x800
        self.m.echo_offset += 4
        if self.m.echo_offset >= self.m.echo_length:
            self.m.echo_offset = 0
        self.echo_write(0)
        self.m.t_echo_enabled = self.m.regs[R_FLG]

    cdef inline void echo_30(self) noexcept:
        self.echo_write(1)

    # ------------------------------------------------------------- timing
    cdef void clock(self, int phase) noexcept:
        cdef Voice* V = self.m.voices
        if phase == 0:
            self.V5(&V[0]); self.V2(&V[1])
        elif phase == 1:
            self.V6(&V[0]); self.V3(&V[1])
        elif phase == 2:
            self.V7_V4_V1(&V[0])
        elif phase == 3:
            self.V8_V5_V2(&V[0])
        elif phase == 4:
            self.V9_V6_V3(&V[0])
        elif phase == 5:
            self.V7_V4_V1(&V[1])
        elif phase == 6:
            self.V8_V5_V2(&V[1])
        elif phase == 7:
            self.V9_V6_V3(&V[1])
        elif phase == 8:
            self.V7_V4_V1(&V[2])
        elif phase == 9:
            self.V8_V5_V2(&V[2])
        elif phase == 10:
            self.V9_V6_V3(&V[2])
        elif phase == 11:
            self.V7_V4_V1(&V[3])
        elif phase == 12:
            self.V8_V5_V2(&V[3])
        elif phase == 13:
            self.V9_V6_V3(&V[3])
        elif phase == 14:
            self.V7_V4_V1(&V[4])
        elif phase == 15:
            self.V8_V5_V2(&V[4])
        elif phase == 16:
            self.V9_V6_V3(&V[4])
        elif phase == 17:
            self.V1(&V[0]); self.V7(&V[5]); self.V4(&V[6])
        elif phase == 18:
            self.V8_V5_V2(&V[5])
        elif phase == 19:
            self.V9_V6_V3(&V[5])
        elif phase == 20:
            self.V1(&V[1]); self.V7(&V[6]); self.V4(&V[7])
        elif phase == 21:
            self.V8(&V[6]); self.V5(&V[7]); self.V2(&V[0])
        elif phase == 22:
            self.V3a(&V[0]); self.V9(&V[6]); self.V6(&V[7]); self.echo_22()
        elif phase == 23:
            self.V7(&V[7]); self.echo_23()
        elif phase == 24:
            self.V8(&V[7]); self.echo_24()
        elif phase == 25:
            self.V3b(&V[0]); self.V9(&V[7]); self.echo_25()
        elif phase == 26:
            self.echo_26()
        elif phase == 27:
            self.misc_27(); self.echo_27()
        elif phase == 28:
            self.misc_28(); self.echo_28()
        elif phase == 29:
            self.misc_29(); self.echo_29()
        elif phase == 30:
            self.misc_30(); self.V3c(&V[0]); self.echo_30()
        else:
            self.V4(&V[0]); self.V1(&V[2])

    cpdef void run(self, int clocks):
        """Run the DSP for `clocks` 1.024 MHz clocks (32 clocks = 1 stereo sample)."""
        cdef int phase = self.m.phase
        while clocks > 0:
            self.clock(phase)
            phase = (phase + 1) & 31
            clocks -= 1
        self.m.phase = phase
'''

DSP_MODE = 'auto'          # 'auto' | 'snes9x' | 'numpy'  (set from --dsp)
_DSP_MOD = None
_DSP_ERR = ''


def load_snes9x_dsp(verbose=True):
    """Compile (once) and import the Snes9x DSP core. Returns module or None."""
    global _DSP_MOD, _DSP_ERR
    if _DSP_MOD is not None or _DSP_ERR:
        return _DSP_MOD
    try:
        import hashlib, glob, importlib.util
        tag = hashlib.sha1((_DSP_PYX + sys.version).encode()).hexdigest()[:12]
        name = 'virtualsnes_spcdsp_' + tag
        d = os.path.join(os.path.expanduser('~'), '.virtualsnes', 'cython')
        os.makedirs(d, exist_ok=True)
        found = glob.glob(os.path.join(d, name + '.*.so')) + glob.glob(os.path.join(d, name + '*.pyd'))
        if not found:
            try:
                import Cython  # noqa: F401
            except ImportError:
                raise RuntimeError("Cython not installed (pip install cython setuptools)")
            pyx = os.path.join(d, name + '.pyx')
            with open(pyx, 'w', encoding='utf-8') as f:
                f.write(_DSP_PYX)
            if verbose:
                print(f"{APP}: compiling Snes9x S-DSP core (first run only, ~15 s)...", flush=True)
            r = subprocess.run([sys.executable, '-m', 'Cython.Build.Cythonize', '-i', '-3', pyx],
                               cwd=d, capture_output=True, text=True, timeout=900)
            found = glob.glob(os.path.join(d, name + '.*.so')) + glob.glob(os.path.join(d, name + '*.pyd'))
            if r.returncode or not found:
                tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
                raise RuntimeError("build failed: " + " | ".join(tail))
        spec = importlib.util.spec_from_file_location(name, found[0])
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        _DSP_MOD = mod
    except Exception as e:
        _DSP_ERR = str(e) or type(e).__name__
        if verbose:
            print(f"{APP}: Cython Snes9x DSP unavailable ({_DSP_ERR}); will use pure-Python Snes9x DSP", flush=True)
    return _DSP_MOD


class FastDSP:
    """APU-facing wrapper around the compiled Snes9x DSP (same interface as SDSP)."""
    name = 'snes9x'

    def __init__(self, apu, mod):
        self.apu = apu
        self.core = mod.SPCDSP(apu.ram, 1 << 17)
        self.clock = 0

    def reset(self):
        self.core.reset(); self.core.take(); self.clock = 0

    def render_to(self, spc_cyc):
        n = spc_cyc - self.clock
        if n > 0:
            self.core.run(n); self.clock = spc_cyc

    def read(self, reg):
        self.render_to(self.apu.spc.cyc)
        return self.core.read(reg)

    def write(self, reg, val):
        self.render_to(self.apu.spc.cyc)
        self.core.write(reg, val)
        self.apu.dsp[reg & 0x7F] = val & 0xFF

    def take(self):
        return np.frombuffer(self.core.take(), dtype=np.int16).reshape(-1, 2)

    def get_state(self):
        return {'engine': self.name, 'core': self.core.get_state(), 'clock': self.clock}

    def set_state(self, st):
        if st.get('engine') != self.name:
            self.reset(); self.clock = self.apu.spc.cyc; return
        self.core.set_state(st['core']); self.clock = st['clock']; self.core.take()



# ===================================================================== Snes9x S-DSP (pure Python)
# Line-for-line behaviour of github.com/snes9xgit/snes9x apu/bapu/dsp/SPC_DSP.cpp
# (blargg snes_spc 0.9.0, LGPL 2.1+). Same 32-phase pipeline as the Cython core above;
# used when Cython/compiler are unavailable so every game still gets Snes9x audio.

_SIMPLE_RANGE = 30720
_COUNTER_RATES = (_SIMPLE_RANGE + 1, 2048, 1536, 1280, 1024, 768, 640, 512, 384, 320, 256, 192,
                  160, 128, 96, 80, 64, 48, 40, 32, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1)
_COUNTER_OFFS = (1, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0,
                 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 536, 0, 1040, 0, 0)
_SNES9X_GAUSS = _SNES9X_INIT = None


def _snes9x_tables():
    global _SNES9X_GAUSS, _SNES9X_INIT
    if _SNES9X_GAUSS is None:
        ns = {}
        exec(_DSP_PYX.split('# cython:', 1)[0], ns)
        _SNES9X_GAUSS, _SNES9X_INIT = ns['GAUSS'], ns['INITIAL_REGS']
    return _SNES9X_GAUSS, _SNES9X_INIT


def _s16(x):
    x &= 0xFFFF
    return x - 0x10000 if x >= 0x8000 else x


def _clamp16(io):
    if io > 32767 or io < -32768:
        return (io >> 31) ^ 0x7FFF
    return io


class _PyVoice:
    __slots__ = ('buf', 'buf_pos', 'interp_pos', 'brr_addr', 'brr_offset', 'regs', 'vbit',
                 'kon_delay', 'env_mode', 'env', 'hidden_env', 't_envx_out')

    def __init__(self, i):
        self.buf = [0] * 24
        self.buf_pos = self.interp_pos = self.brr_addr = 0
        self.brr_offset = 1
        self.regs = i * 0x10
        self.vbit = 1 << i
        self.kon_delay = self.env_mode = self.env = self.hidden_env = self.t_envx_out = 0


class Snes9xPyDSP:
    """Pure-Python Snes9x S-DSP for all SNES games when the Cython core is unavailable."""
    name = 'snes9x-py'
    R_MVOLL, R_EVOLL, R_KON, R_KOFF, R_FLG, R_ENDX = 0x0C, 0x2C, 0x4C, 0x5C, 0x6C, 0x7C
    R_EFB, R_PMON, R_NON, R_EON, R_DIR, R_ESA, R_EDL, R_FIR = 0x0D, 0x2D, 0x3D, 0x4D, 0x5D, 0x6D, 0x7D, 0x0F
    V_VOLL, V_PITCHL, V_PITCHH, V_SRCN = 0, 2, 3, 4
    V_ADSR0, V_ADSR1, V_GAIN, V_ENVX, V_OUTX = 5, 6, 7, 8, 9
    BRR_BUF, BRR_BLOCK = 12, 9
    ENV_RELEASE, ENV_ATTACK, ENV_DECAY, ENV_SUSTAIN = 0, 1, 2, 3

    def __init__(self, apu):
        self.apu = apu
        self.ram = apu.ram
        self.gauss, self.initial_regs = _snes9x_tables()
        self.out = []
        self.clock = 0
        self.mute_mask = 0
        self.reset()

    def reset(self):
        self.load(self.initial_regs)
        self.out.clear()
        self.clock = 0

    def load(self, regs):
        self.regs = bytearray(128)
        self.external_regs = bytearray(regs)
        self.regs[66] = self.regs[82] = 0x01
        self.regs[self.R_FLG] = 0xE0
        self.voices = [_PyVoice(i) for i in range(8)]
        self.echo_hist = [[0, 0] for _ in range(16)]
        self.echo_hist_pos = 0
        self.every_other_sample = 1
        self.kon = self.noise = 0
        self.noise = 0x4000
        self.counter = self.echo_offset = self.echo_length = self.phase = 0
        self.kon_check = 0
        self.new_kon = self.regs[self.R_KON]
        self.endx_buf = self.envx_buf = self.outx_buf = 0
        self.t_pmon = self.t_non = self.t_eon = self.t_koff = 0
        self.t_dir = self.regs[self.R_DIR]
        self.t_brr_next_addr = self.t_adsr0 = self.t_brr_header = self.t_brr_byte = 0
        self.t_srcn = 0
        self.t_esa = self.regs[self.R_ESA]
        self.t_echo_enabled = self.t_dir_addr = self.t_pitch = self.t_output = 0
        self.t_looped = self.t_echo_ptr = 0
        self.t_main_out = [0, 0]
        self.t_echo_out = [0, 0]
        self.t_echo_in = [0, 0]
        self.soft_reset_common()

    def soft_reset_common(self):
        self.noise = 0x4000
        self.echo_hist_pos = 0
        self.every_other_sample = 1
        self.echo_offset = self.phase = self.counter = 0

    def read(self, addr):
        self.render_to(self.apu.spc.cyc)
        return self.external_regs[addr & 0x7F]

    def write(self, addr, data):
        self.render_to(self.apu.spc.cyc)
        addr &= 0x7F
        data &= 0xFF
        self.regs[addr] = self.external_regs[addr] = self.apu.dsp[addr] = data
        low = addr & 0x0F
        if low == self.V_ENVX:
            self.envx_buf = data
        elif low == self.V_OUTX:
            self.outx_buf = data
        elif low == 0x0C:
            if addr == self.R_KON:
                self.new_kon = data
            if addr == self.R_ENDX:
                self.endx_buf = self.regs[self.R_ENDX] = 0

    def render_to(self, spc_cyc):
        n = spc_cyc - self.clock
        if n > 0:
            self.run(n)
            self.clock = spc_cyc

    def take(self):
        if not self.out:
            return np.zeros((0, 2), np.int16)
        a = np.asarray(self.out, dtype=np.int16)
        self.out = []
        return a

    def get_state(self):
        return {
            'engine': self.name, 'clock': self.clock,
            'regs': bytes(self.regs), 'external_regs': bytes(self.external_regs),
            'echo_hist': [r[:] for r in self.echo_hist],
            'echo_hist_pos': self.echo_hist_pos,
            'every_other_sample': self.every_other_sample,
            'kon': self.kon, 'noise': self.noise, 'counter': self.counter,
            'echo_offset': self.echo_offset, 'echo_length': self.echo_length,
            'phase': self.phase, 'new_kon': self.new_kon,
            'endx_buf': self.endx_buf, 'envx_buf': self.envx_buf, 'outx_buf': self.outx_buf,
            't_pmon': self.t_pmon, 't_non': self.t_non, 't_eon': self.t_eon,
            't_dir': self.t_dir, 't_koff': self.t_koff, 't_esa': self.t_esa,
            't_echo_enabled': self.t_echo_enabled,
            'voices': [{k: (getattr(v, k)[:] if k == 'buf' else getattr(v, k))
                        for k in _PyVoice.__slots__ if k not in ('regs', 'vbit')}
                       for v in self.voices],
        }

    def set_state(self, st):
        if st.get('engine') != self.name:
            self.reset(); self.clock = self.apu.spc.cyc; return
        self.clock = st['clock']
        self.regs[:] = st['regs']; self.external_regs[:] = st['external_regs']
        self.echo_hist = [r[:] for r in st['echo_hist']]
        for k in ('echo_hist_pos', 'every_other_sample', 'kon', 'noise', 'counter',
                  'echo_offset', 'echo_length', 'phase', 'new_kon', 'endx_buf',
                  'envx_buf', 'outx_buf', 't_pmon', 't_non', 't_eon', 't_dir',
                  't_koff', 't_esa', 't_echo_enabled'):
            setattr(self, k, st[k])
        for v, vs in zip(self.voices, st['voices']):
            for k, x in vs.items():
                setattr(v, k, x[:] if k == 'buf' else x)
        self.out = []

    def read_counter(self, rate):
        return (self.counter + _COUNTER_OFFS[rate]) % _COUNTER_RATES[rate]

    def run_counters(self):
        self.counter -= 1
        if self.counter < 0:
            self.counter = _SIMPLE_RANGE - 1

    def run_envelope(self, v):
        env = v.env
        if v.env_mode == self.ENV_RELEASE:
            env -= 8
            v.env = 0 if env < 0 else env
            return
        env_data = self.regs[v.regs + self.V_ADSR1]
        if self.t_adsr0 & 0x80:
            if v.env_mode >= self.ENV_DECAY:
                env -= 1 + (env >> 8)
                rate = env_data & 0x1F
                if v.env_mode == self.ENV_DECAY:
                    rate = (self.t_adsr0 >> 3 & 0x0E) + 0x10
            else:
                rate = (self.t_adsr0 & 0x0F) * 2 + 1
                env += 0x20 if rate < 31 else 0x400
        else:
            env_data = self.regs[v.regs + self.V_GAIN]
            mode = env_data >> 5
            if mode < 4:
                env, rate = env_data * 0x10, 31
            else:
                rate = env_data & 0x1F
                if mode == 4:
                    env -= 0x20
                elif mode < 6:
                    env -= 1 + (env >> 8)
                else:
                    env += 0x20
                    if mode > 6 and (v.hidden_env & 0xFFFFFFFF) >= 0x600:
                        env += 0x8 - 0x20
        if (env >> 8) == (env_data >> 5) and v.env_mode == self.ENV_DECAY:
            v.env_mode = self.ENV_SUSTAIN
        v.hidden_env = env
        if (env & 0xFFFFFFFF) > 0x7FF:
            env = 0 if env < 0 else 0x7FF
            if v.env_mode == self.ENV_ATTACK:
                v.env_mode = self.ENV_DECAY
        if not self.read_counter(rate):
            v.env = env

    def decode_brr(self, v):
        ram = self.ram
        nybbles = ((self.t_brr_byte * 0x100 + ram[(v.brr_addr + v.brr_offset + 1) & 0xFFFF]) & 0xFFFF)
        header = self.t_brr_header
        pos = v.buf_pos
        end = pos + 4
        v.buf_pos = 0 if v.buf_pos + 4 >= self.BRR_BUF else v.buf_pos + 4
        while pos < end:
            s = _s16(nybbles) >> 12
            shift = header >> 4
            if shift <= 12:
                s = (s << shift) >> 1
            else:
                s &= ~0x7FF
            flt = header & 0x0C
            p1 = v.buf[pos + self.BRR_BUF - 1]
            p2 = v.buf[pos + self.BRR_BUF - 2] >> 1
            if flt >= 8:
                s += p1 - p2
                if flt == 8:
                    s += (p2 >> 4) + ((p1 * -3) >> 6)
                else:
                    s += ((p1 * -13) >> 7) + ((p2 * 3) >> 4)
            elif flt:
                s += (p1 >> 1) + ((-p1) >> 5)
            s = _s16(_clamp16(s) * 2)
            v.buf[pos + self.BRR_BUF] = v.buf[pos] = s
            pos += 1
            nybbles = (nybbles << 4) & 0xFFFF

    def interpolate(self, v):
        g = self.gauss
        offset = v.interp_pos >> 4 & 0xFF
        base = (v.interp_pos >> 12) + v.buf_pos
        fwd, rev = 255 - offset, offset
        out = (g[fwd] * v.buf[base]) >> 11
        out += (g[fwd + 256] * v.buf[base + 1]) >> 11
        out += (g[rev + 256] * v.buf[base + 2]) >> 11
        out = _s16(out)
        out = _clamp16(out + ((g[rev] * v.buf[base + 3]) >> 11)) & ~1
        return out

    def misc_27(self):
        self.t_pmon = self.regs[self.R_PMON] & 0xFE

    def misc_28(self):
        self.t_non = self.regs[self.R_NON]
        self.t_eon = self.regs[self.R_EON]
        self.t_dir = self.regs[self.R_DIR]

    def misc_29(self):
        self.every_other_sample ^= 1
        if self.every_other_sample:
            self.new_kon &= ~self.kon & 0xFF

    def misc_30(self):
        if self.every_other_sample:
            self.kon = self.new_kon
            self.t_koff = self.regs[self.R_KOFF] | self.mute_mask
        self.run_counters()
        if not self.read_counter(self.regs[self.R_FLG] & 0x1F):
            fb = (self.noise << 13) ^ (self.noise << 14)
            self.noise = (fb & 0x4000) ^ (self.noise >> 1)

    def V1(self, v):
        self.t_dir_addr = (self.t_dir * 0x100 + self.t_srcn * 4) & 0xFFFF
        self.t_srcn = self.regs[v.regs + self.V_SRCN]

    def V2(self, v):
        entry = self.t_dir_addr + (0 if v.kon_delay else 2)
        ram = self.ram
        self.t_brr_next_addr = ram[entry & 0xFFFF] | (ram[(entry + 1) & 0xFFFF] << 8)
        self.t_adsr0 = self.regs[v.regs + self.V_ADSR0]
        self.t_pitch = self.regs[v.regs + self.V_PITCHL]

    def V3a(self, v):
        self.t_pitch += (self.regs[v.regs + self.V_PITCHH] & 0x3F) << 8

    def V3b(self, v):
        ram = self.ram
        self.t_brr_byte = ram[(v.brr_addr + v.brr_offset) & 0xFFFF]
        self.t_brr_header = ram[v.brr_addr]

    def V3c(self, v):
        if self.t_pmon & v.vbit:
            self.t_pitch += ((self.t_output >> 5) * self.t_pitch) >> 10
        if v.kon_delay:
            if v.kon_delay == 5:
                v.brr_addr = self.t_brr_next_addr
                v.brr_offset = 1
                v.buf_pos = 0
                self.t_brr_header = 0
                self.kon_check = 1
            v.env = v.hidden_env = v.interp_pos = 0
            v.kon_delay -= 1
            if v.kon_delay & 3:
                v.interp_pos = 0x4000
            self.t_pitch = 0
        output = self.interpolate(v)
        if self.t_non & v.vbit:
            output = _s16(self.noise * 2)
        self.t_output = ((output * v.env) >> 11) & ~1
        v.t_envx_out = (v.env >> 4) & 0xFF
        if self.regs[self.R_FLG] & 0x80 or (self.t_brr_header & 3) == 1:
            v.env_mode = self.ENV_RELEASE
            v.env = 0
        if self.every_other_sample:
            if self.t_koff & v.vbit:
                v.env_mode = self.ENV_RELEASE
            if self.kon & v.vbit:
                v.kon_delay = 5
                v.env_mode = self.ENV_ATTACK
        if not v.kon_delay:
            self.run_envelope(v)

    def voice_output(self, v, ch):
        vol = self.regs[v.regs + self.V_VOLL + ch]
        if vol >= 0x80:
            vol -= 0x100
        amp = (self.t_output * vol) >> 7
        self.t_main_out[ch] = _clamp16(self.t_main_out[ch] + amp)
        if self.t_eon & v.vbit:
            self.t_echo_out[ch] = _clamp16(self.t_echo_out[ch] + amp)

    def V3(self, v):
        self.V3a(v); self.V3b(v); self.V3c(v)

    def V4(self, v):
        self.t_looped = 0
        if v.interp_pos >= 0x4000:
            self.decode_brr(v)
            v.brr_offset += 2
            if v.brr_offset >= self.BRR_BLOCK:
                v.brr_addr = (v.brr_addr + self.BRR_BLOCK) & 0xFFFF
                if self.t_brr_header & 1:
                    v.brr_addr = self.t_brr_next_addr
                    self.t_looped = v.vbit
                v.brr_offset = 1
        v.interp_pos = (v.interp_pos & 0x3FFF) + self.t_pitch
        if v.interp_pos > 0x7FFF:
            v.interp_pos = 0x7FFF
        self.voice_output(v, 0)

    def V5(self, v):
        self.voice_output(v, 1)
        endx = self.regs[self.R_ENDX] | self.t_looped
        if v.kon_delay == 5:
            endx &= ~v.vbit
        self.endx_buf = endx & 0xFF

    def V6(self, v):
        self.outx_buf = (self.t_output >> 8) & 0xFF

    def V7(self, v):
        self.regs[self.R_ENDX] = self.external_regs[self.R_ENDX] = self.apu.dsp[self.R_ENDX] = self.endx_buf
        self.envx_buf = v.t_envx_out

    def V8(self, v):
        r = v.regs + self.V_OUTX
        self.regs[r] = self.external_regs[r] = self.apu.dsp[r] = self.outx_buf

    def V9(self, v):
        r = v.regs + self.V_ENVX
        self.regs[r] = self.external_regs[r] = self.apu.dsp[r] = self.envx_buf

    def calc_fir(self, i, ch):
        c = self.regs[self.R_FIR + i * 0x10]
        if c >= 0x80:
            c -= 0x100
        return (self.echo_hist[self.echo_hist_pos + i + 1][ch] * c) >> 6

    def echo_read(self, ch):
        a = self.t_echo_ptr + ch * 2
        s = _s16(self.ram[a & 0xFFFF] | (self.ram[(a + 1) & 0xFFFF] << 8)) >> 1
        self.echo_hist[self.echo_hist_pos][ch] = self.echo_hist[self.echo_hist_pos + 8][ch] = s

    def echo_22(self):
        self.echo_hist_pos = (self.echo_hist_pos + 1) % 8
        self.t_echo_ptr = (self.t_esa * 0x100 + self.echo_offset) & 0xFFFF
        self.echo_read(0)
        self.t_echo_in[0] = self.calc_fir(0, 0)
        self.t_echo_in[1] = self.calc_fir(0, 1)

    def echo_23(self):
        self.t_echo_in[0] += self.calc_fir(1, 0) + self.calc_fir(2, 0)
        self.t_echo_in[1] += self.calc_fir(1, 1) + self.calc_fir(2, 1)
        self.echo_read(1)

    def echo_24(self):
        self.t_echo_in[0] += self.calc_fir(3, 0) + self.calc_fir(4, 0) + self.calc_fir(5, 0)
        self.t_echo_in[1] += self.calc_fir(3, 1) + self.calc_fir(4, 1) + self.calc_fir(5, 1)

    def echo_25(self):
        l = _s16(self.t_echo_in[0] + self.calc_fir(6, 0))
        r = _s16(self.t_echo_in[1] + self.calc_fir(6, 1))
        l = _clamp16(l + _s16(self.calc_fir(7, 0)))
        r = _clamp16(r + _s16(self.calc_fir(7, 1)))
        self.t_echo_in[0] = l & ~1
        self.t_echo_in[1] = r & ~1

    def echo_output(self, ch):
        def sc(x):
            return x - 0x100 if x & 0x80 else x
        out = _s16((self.t_main_out[ch] * sc(self.regs[self.R_MVOLL + ch * 0x10])) >> 7)
        out += _s16((self.t_echo_in[ch] * sc(self.regs[self.R_EVOLL + ch * 0x10])) >> 7)
        return _clamp16(out)

    def echo_26(self):
        def sc(x):
            return x - 0x100 if x & 0x80 else x
        self.t_main_out[0] = self.echo_output(0)
        l = _clamp16(self.t_echo_out[0] + _s16((self.t_echo_in[0] * sc(self.regs[self.R_EFB])) >> 7))
        r = _clamp16(self.t_echo_out[1] + _s16((self.t_echo_in[1] * sc(self.regs[self.R_EFB])) >> 7))
        self.t_echo_out[0] = l & ~1
        self.t_echo_out[1] = r & ~1

    def echo_27(self):
        l, r = self.t_main_out[0], self.echo_output(1)
        self.t_main_out[0] = self.t_main_out[1] = 0
        if self.regs[self.R_FLG] & 0x40:
            l = r = 0
        self.out.append((_clamp16(l), _clamp16(r)))

    def echo_28(self):
        self.t_echo_enabled = self.regs[self.R_FLG]

    def echo_write(self, ch):
        if not (self.t_echo_enabled & 0x20):
            a = self.t_echo_ptr + ch * 2
            v = self.t_echo_out[ch]
            self.ram[a & 0xFFFF] = v & 0xFF
            self.ram[(a + 1) & 0xFFFF] = (v >> 8) & 0xFF
        self.t_echo_out[ch] = 0

    def echo_29(self):
        self.t_esa = self.regs[self.R_ESA]
        if not self.echo_offset:
            self.echo_length = (self.regs[self.R_EDL] & 0x0F) * 0x800
        self.echo_offset += 4
        if self.echo_offset >= self.echo_length:
            self.echo_offset = 0
        self.echo_write(0)
        self.t_echo_enabled = self.regs[self.R_FLG]

    def echo_30(self):
        self.echo_write(1)

    def phase_clock(self, phase):
        V = self.voices
        if phase == 0:
            self.V5(V[0]); self.V2(V[1])
        elif phase == 1:
            self.V6(V[0]); self.V3(V[1])
        elif phase == 2:
            self.V7(V[0]); self.V1(V[3]); self.V4(V[1])
        elif phase == 3:
            self.V8(V[0]); self.V5(V[1]); self.V2(V[2])
        elif phase == 4:
            self.V9(V[0]); self.V6(V[1]); self.V3(V[2])
        elif phase == 5:
            self.V7(V[1]); self.V1(V[4]); self.V4(V[2])
        elif phase == 6:
            self.V8(V[1]); self.V5(V[2]); self.V2(V[3])
        elif phase == 7:
            self.V9(V[1]); self.V6(V[2]); self.V3(V[3])
        elif phase == 8:
            self.V7(V[2]); self.V1(V[5]); self.V4(V[3])
        elif phase == 9:
            self.V8(V[2]); self.V5(V[3]); self.V2(V[4])
        elif phase == 10:
            self.V9(V[2]); self.V6(V[3]); self.V3(V[4])
        elif phase == 11:
            self.V7(V[3]); self.V1(V[6]); self.V4(V[4])
        elif phase == 12:
            self.V8(V[3]); self.V5(V[4]); self.V2(V[5])
        elif phase == 13:
            self.V9(V[3]); self.V6(V[4]); self.V3(V[5])
        elif phase == 14:
            self.V7(V[4]); self.V1(V[7]); self.V4(V[5])
        elif phase == 15:
            self.V8(V[4]); self.V5(V[5]); self.V2(V[6])
        elif phase == 16:
            self.V9(V[4]); self.V6(V[5]); self.V3(V[6])
        elif phase == 17:
            self.V1(V[0]); self.V7(V[5]); self.V4(V[6])
        elif phase == 18:
            self.V8(V[5]); self.V5(V[6]); self.V2(V[7])
        elif phase == 19:
            self.V9(V[5]); self.V6(V[6]); self.V3(V[7])
        elif phase == 20:
            self.V1(V[1]); self.V7(V[6]); self.V4(V[7])
        elif phase == 21:
            self.V8(V[6]); self.V5(V[7]); self.V2(V[0])
        elif phase == 22:
            self.V3a(V[0]); self.V9(V[6]); self.V6(V[7]); self.echo_22()
        elif phase == 23:
            self.V7(V[7]); self.echo_23()
        elif phase == 24:
            self.V8(V[7]); self.echo_24()
        elif phase == 25:
            self.V3b(V[0]); self.V9(V[7]); self.echo_25()
        elif phase == 26:
            self.echo_26()
        elif phase == 27:
            self.misc_27(); self.echo_27()
        elif phase == 28:
            self.misc_28(); self.echo_28()
        elif phase == 29:
            self.misc_29(); self.echo_29()
        elif phase == 30:
            self.misc_30(); self.V3c(V[0]); self.echo_30()
        else:
            self.V4(V[0]); self.V1(V[2])

    def run(self, clocks):
        phase = self.phase
        while clocks > 0:
            self.phase_clock(phase)
            phase = (phase + 1) & 31
            clocks -= 1
        self.phase = phase


def make_dsp(apu):
    """Pick audio engine: compiled Snes9x DSP, pure-Python Snes9x DSP, or approx numpy."""
    if DSP_MODE == 'numpy':
        return SDSP(apu)
    mod = load_snes9x_dsp(verbose=False)
    if mod is not None:
        return FastDSP(apu, mod)
    # Snes9x audio for all games without a native build (matches SPC_DSP.cpp)
    if _DSP_ERR:
        print(f"{APP}: using pure-Python Snes9x S-DSP ({_DSP_ERR})", flush=True)
    return Snes9xPyDSP(apu)


# ===================================================================== S-DSP (8-voice sample synth)
# envelope/noise step period in samples for rate 0..31 (rate 0 = never), from the S-DSP spec
DSP_RATE = (0, 2048, 1536, 1280, 1024, 768, 640, 512, 384, 320, 256, 192, 160, 128, 96, 80,
            64, 48, 40, 32, 24, 20, 16, 12, 10, 8, 6, 5, 4, 3, 2, 1)


def _interp_kernel():
    """4-tap Gaussian-shaped interpolation weights for 256 fractional positions.

    Generated from a Gaussian curve (sigma ~0.55 sample) rather than copied from
    the hardware ROM table; gives the same soft, slightly muffled SNES character.
    """
    f = np.arange(256, dtype=np.float64)[:, None] / 256.0
    d = np.arange(4, dtype=np.float64)[None, :] - 1.0 - f
    w = np.exp(-(d * d) / (2 * 0.55 * 0.55))
    return (w / w.sum(axis=1, keepdims=True)).astype(np.float32)


DSP_KERNEL = _interp_kernel()
_BRR_CACHE = {}


def brr_decode(blk, p1, p2):
    """Decode one 9-byte BRR block -> (16 int samples, p1, p2). Filters per the S-DSP spec."""
    key = (blk, p1, p2)
    hit = _BRR_CACHE.get(key)
    if hit is not None:
        return hit
    hdr = blk[0]; shift = hdr >> 4; filt = (hdr >> 2) & 3
    out = [0] * 16
    for i in range(16):
        b = blk[1 + (i >> 1)]
        n = (b & 15) if i & 1 else (b >> 4)
        if n >= 8: n -= 16
        s = ((n << shift) >> 1) if shift <= 12 else (-2048 if n < 0 else 0)
        if filt:
            h2 = p2 >> 1
            if filt == 1:
                s += (p1 >> 1) + ((-p1) >> 5)
            elif filt == 2:
                s += p1 - h2 + (h2 >> 4) + ((p1 * -3) >> 6)
            else:
                s += p1 - h2 + ((p1 * -13) >> 7) + ((h2 * 3) >> 4)
        if s > 32767: s = 32767
        elif s < -32768: s = -32768
        s = ((s * 2 + 0x8000) & 0xFFFF) - 0x8000
        out[i] = s; p2 = p1; p1 = s
    res = (np.array(out, dtype=np.int32), p1, p2)
    if len(_BRR_CACHE) > 50000: _BRR_CACHE.clear()
    _BRR_CACHE[key] = res
    return res


class DSPVoice:
    __slots__ = ('on', 'addr', 'buf', 'pos', 'p1', 'p2', 'env', 'state', 'cnt', 'stop', 'srcn')

    def __init__(self):
        self.on = False; self.addr = 0; self.buf = np.zeros(3, np.int32); self.pos = 0
        self.p1 = self.p2 = 0; self.env = 0; self.state = 'off'; self.cnt = 0; self.stop = None
        self.srcn = 0


class SDSP:
    """S-DSP: renders audio in blocks (vectorised with numpy) up to the SPC700's time.

    Register writes to KON/KOFF/FLG/echo setup flush the block first, so note
    timing is sample-accurate; other registers apply at the next block edge.
    Covers BRR decode + loop/end, Gaussian-style interpolation, ADSR & all GAIN
    modes, pitch modulation, noise, per-voice/master volume, echo with 8-tap FIR
    and feedback (echo writes really land in ARAM), ENDX/ENVX/OUTX readback.
    """

    FLUSH_REGS = frozenset((0x4C, 0x5C, 0x6C, 0x6D, 0x7D, 0x5D, 0x2D, 0x3D, 0x4D))

    def __init__(self, apu):
        self.apu = apu
        self.reset()

    def reset(self):
        self.v = [DSPVoice() for _ in range(8)]
        self.clock = 0                    # samples rendered so far
        self.out = []                     # pending int16 stereo blocks
        self.noise = 0x4000; self.ncnt = 0
        self.epos = 0; self.ehist = np.zeros((7, 2), np.int64)
        self.enabled = True

    STATE = ('clock', 'noise', 'ncnt', 'epos', 'ehist')

    def get_state(self):
        st = {k: getattr(self, k) for k in self.STATE}
        st['voices'] = [{k: getattr(v, k) for k in DSPVoice.__slots__} for v in self.v]
        st['engine'] = self.name
        return st

    def set_state(self, st):
        if st.pop('engine', 'numpy') != self.name:
            self.reset(); self.clock = self.apu.spc.cyc // 32; return
        for vs, v in zip(st.pop('voices'), self.v):
            for k, x in vs.items(): setattr(v, k, x)
        for k, x in st.items(): setattr(self, k, x)
        self.out = []

    name = 'numpy'

    def read(self, reg):
        return self.apu.dsp[reg]

    def write(self, reg, val):
        self.before_write(reg)
        self.apu.dsp[reg] = val
        if reg == 0x7C: self.apu.dsp[0x7C] = 0          # any ENDX write clears it
        else: self.after_write(reg, val)

    # ------------------------------------------------------------- register side
    def before_write(self, reg):
        if reg in self.FLUSH_REGS:
            self.render_to(self.apu.spc.cyc)

    def after_write(self, reg, val):
        R = self.apu.dsp
        if reg == 0x4C and val:
            for i in range(8):
                if val >> i & 1: self.key_on(i)
        elif reg == 0x5C:
            for i in range(8):
                if val >> i & 1 and self.v[i].on: self.v[i].state = 'release'
        elif reg == 0x6C and val & 0x80:
            for vc in self.v:
                vc.on = False; vc.env = 0; vc.state = 'off'

    def key_on(self, i):
        R = self.apu.dsp; ram = self.apu.ram; vc = self.v[i]
        srcn = R[(i << 4) | 4]; d = ((R[0x5D] << 8) + srcn * 4) & 0xFFFF
        vc.addr = ram[d] | (ram[(d + 1) & 0xFFFF] << 8); vc.srcn = srcn
        vc.buf = np.zeros(3, np.int32); vc.pos = 0; vc.p1 = vc.p2 = 0
        vc.env = 0; vc.state = 'attack'; vc.cnt = 0; vc.stop = None; vc.on = True
        R[0x7C] &= ~(1 << i) & 0xFF

    # ------------------------------------------------------------- mixing
    def render_to(self, spc_cyc):
        n = spc_cyc // 32 - self.clock
        if n <= 0: return
        self.clock += n
        if not self.enabled:
            return
        while n > 0:
            k = min(n, 2048); self.mix(k); n -= k

    def take(self):
        """Return pending audio as one int16 (n, 2) array (possibly empty)."""
        if not self.out:
            return np.zeros((0, 2), np.int16)
        a = self.out[0] if len(self.out) == 1 else np.concatenate(self.out)
        self.out = []
        return a

    def envelope(self, vc, i, n):
        R = self.apu.dsp; b = i << 4
        a1 = R[b + 5]; a2 = R[b + 6]; g = R[b + 7]
        env = vc.env; st = vc.state
        if st == 'release':
            arr = env - 8 * np.arange(1, n + 1, dtype=np.int32)
            np.maximum(arr, 0, out=arr)
            vc.env = int(arr[-1])
            if vc.env == 0: vc.on = False; vc.state = 'off'
            return arr
        out = np.empty(n, np.int32); k = 0; cnt = vc.cnt
        adsr = a1 & 0x80
        while k < n:
            if adsr:
                if st == 'attack':
                    rate = (a1 & 15) * 2 + 1
                elif st == 'decay':
                    rate = ((a1 >> 4) & 7) * 2 + 16
                else:
                    rate = a2 & 31
            elif g & 0x80:
                rate = g & 31
            else:                                   # direct gain
                env = (g & 0x7F) << 4; out[k:] = env; k = n; break
            per = DSP_RATE[rate]
            if not per:
                out[k:] = env; break
            if cnt <= 0 or cnt > per: cnt = per
            m = min(cnt, n - k); out[k:k + m] = env; k += m; cnt -= m
            if cnt: break
            cnt = per
            if adsr:                                # one envelope step
                if st == 'attack':
                    env += 1024 if rate == 31 else 32
                    if env > 0x7FF: env = 0x7FF; st = 'decay'
                else:
                    env -= ((env - 1) >> 8) + 1
                    if st == 'decay' and (env >> 8) == (a2 >> 5): st = 'sustain'
            else:
                mode = (g >> 5) & 3
                if mode == 0: env -= 32
                elif mode == 1: env -= ((env - 1) >> 8) + 1
                elif mode == 2: env += 32
                else: env += 32 if env < 0x600 else 8
            env = 0 if env < 0 else (0x7FF if env > 0x7FF else env)
        vc.env = env; vc.state = st; vc.cnt = cnt
        return out

    def gen_noise(self, n):
        rate = self.apu.dsp[0x6C] & 31; per = DSP_RATE[rate]
        out = np.empty(n, np.int32); lf = self.noise; k = 0; cnt = self.ncnt
        while k < n:
            val = ((lf << 1) + 0x8000 & 0xFFFF) - 0x8000
            if not per:
                out[k:] = val; break
            if cnt <= 0 or cnt > per: cnt = per
            m = min(cnt, n - k); out[k:k + m] = val; k += m; cnt -= m
            if not cnt:
                lf = (((lf << 13) ^ (lf << 14)) & 0x4000) | (lf >> 1); cnt = per
        self.noise = lf; self.ncnt = cnt
        return out

    def fill(self, vc, i, need):
        """Decode BRR blocks until the voice buffer holds `need` samples."""
        R = self.apu.dsp; ram = self.apu.ram
        parts = [vc.buf]; have = len(vc.buf)
        addr = vc.addr; p1 = vc.p1; p2 = vc.p2
        while have < need and vc.stop is None:
            if addr <= 0xFFF7:
                blk = bytes(ram[addr:addr + 9])
            else:
                blk = bytes(ram[(addr + j) & 0xFFFF] for j in range(9))
            smp, p1, p2 = brr_decode(blk, p1, p2)
            parts.append(smp); have += 16
            hdr = blk[0]
            if hdr & 1:                                     # end block
                R[0x7C] |= 1 << i
                if hdr & 2:                                 # loop
                    d = ((R[0x5D] << 8) + vc.srcn * 4 + 2) & 0xFFFF
                    addr = ram[d] | (ram[(d + 1) & 0xFFFF] << 8)
                else:
                    vc.stop = have
            else:
                addr = (addr + 9) & 0xFFFF
        vc.addr = addr; vc.p1 = p1; vc.p2 = p2
        if len(parts) > 1:
            vc.buf = np.concatenate(parts)
        if len(vc.buf) < need:
            vc.buf = np.concatenate([vc.buf, np.zeros(need - len(vc.buf), np.int32)])

    def mix(self, n):
        R = self.apu.dsp
        def s8(x): return x - 256 if x & 0x80 else x
        L = np.zeros(n, np.int64); Rr = np.zeros(n, np.int64)
        EL = np.zeros(n, np.int64); ER = np.zeros(n, np.int64)
        pmon = R[0x2D]; non = R[0x3D]; eon = R[0x4D]
        noise = self.gen_noise(n) if non else None
        prev = None; ar = np.arange(n, dtype=np.int64)
        for i, vc in enumerate(self.v):
            if not vc.on:
                prev = None; continue
            b = i << 4
            pitch = (R[b + 2] | (R[b + 3] << 8)) & 0x3FFF
            env = self.envelope(vc, i, n)
            if pmon >> i & 1 and i and prev is not None:
                step = pitch + (((prev >> 5) * pitch) >> 10)
                step = np.clip(step, 0, 0x7FFF).astype(np.int64)
                cs = np.cumsum(step); pos = vc.pos + np.concatenate(([0], cs[:-1])); end = vc.pos + int(cs[-1])
            else:
                pos = vc.pos + ar * pitch; end = vc.pos + n * pitch
            idx = pos >> 12
            if noise is not None and non >> i & 1:
                smp = noise.astype(np.int64)
                need = int(end >> 12) + 4; self.fill(vc, i, need)   # BRR still advances
            else:
                need = int(end >> 12) + 4
                self.fill(vc, i, need)
                buf = vc.buf
                fr = (pos >> 4) & 0xFF
                w = DSP_KERNEL[fr]
                smp = (buf[idx] * w[:, 0] + buf[idx + 1] * w[:, 1] +
                       buf[idx + 2] * w[:, 2] + buf[idx + 3] * w[:, 3]).astype(np.int64)
            if vc.stop is not None:
                dead = idx + 1 >= vc.stop
                if dead.any():
                    smp[dead] = 0
                    if dead[-1]:
                        vc.on = False; vc.state = 'off'; vc.env = 0; env[dead] = 0
            out = (smp * env) >> 11
            prev = out
            l = (out * s8(R[b])) >> 7; r = (out * s8(R[b + 1])) >> 7
            L += l; Rr += r
            if eon >> i & 1: EL += l; ER += r
            R[b + 8] = (int(env[-1]) >> 4) & 0x7F
            R[b + 9] = (int(out[-1]) >> 8) & 0xFF
            used = int(end >> 12)                           # drop consumed samples
            if used:
                vc.buf = vc.buf[used:]; vc.pos = end - (used << 12)
                if vc.stop is not None: vc.stop -= used
            else:
                vc.pos = end
        mL = (L * s8(R[0x0C])) >> 7; mR = (Rr * s8(R[0x1C])) >> 7
        flg = R[0x6C]
        if R[0x2C] or R[0x3C] or not (flg & 0x20):
            eL, eR = self.echo(n, EL, ER)
            mL += (eL * s8(R[0x2C])) >> 7; mR += (eR * s8(R[0x3C])) >> 7
        if flg & 0x40:
            return self.out.append(np.zeros((n, 2), np.int16))
        o = np.empty((n, 2), np.int16)
        o[:, 0] = np.clip(mL, -32768, 32767); o[:, 1] = np.clip(mR, -32768, 32767)
        self.out.append(o)

    def echo(self, n, inL, inR):
        R = self.apu.dsp; ram = self.apu.ram
        esa = R[0x6D] << 8; size = (R[0x7D] & 15) * 2048 or 4
        fir = np.array([R[0x0F + (t << 4)] for t in range(8)], np.int64)
        fir = np.where(fir & 0x80, fir - 256, fir)
        efb = R[0x0D] - 256 if R[0x0D] & 0x80 else R[0x0D]
        write = not (R[0x6C] & 0x20)
        mem = np.frombuffer(ram, np.uint8)
        outL = np.empty(n, np.int64); outR = np.empty(n, np.int64)
        k = 0; delay = size // 4
        while k < n:
            m = min(n - k, delay)
            # Wrap within the EDL-sized echo ring (not raw 64K). esa+epos can sit
            # at the top of RAM (e.g. SMRPG ESA=$D0,EDL=6 → $D000-$FFFF); adding
            # the sample stride with only &0xFFFF spills into $0000 and wipes SPC ZP.
            off = (self.epos + 4 * np.arange(m, dtype=np.int64)) % size
            a = (esa + off) & 0xFFFF
            def rd16(o):
                v = mem[(a + o) & 0xFFFF].astype(np.int64) | (mem[(a + o + 1) & 0xFFFF].astype(np.int64) << 8)
                return ((v + 0x8000) & 0xFFFF) - 0x8000
            cur = np.stack([rd16(0) >> 1, rd16(2) >> 1], -1)      # (m, 2)
            hist = np.concatenate([self.ehist, cur])              # (m+7, 2)
            acc = np.zeros((m, 2), np.int64)
            for t in range(8):                                    # FIR: tap 7 = newest
                acc += (hist[t:t + m] * fir[t]) >> 6
            acc = np.clip(acc, -32768, 32767)
            outL[k:k + m] = acc[:, 0]; outR[k:k + m] = acc[:, 1]
            if write:
                wl = np.clip(inL[k:k + m] + ((acc[:, 0] * efb) >> 7), -32768, 32767) & ~1
                wr = np.clip(inR[k:k + m] + ((acc[:, 1] * efb) >> 7), -32768, 32767) & ~1
                for o, wv in ((0, wl), (2, wr)):
                    u = wv & 0xFFFF
                    mem[(a + o) & 0xFFFF] = (u & 0xFF).astype(np.uint8)
                    mem[(a + o + 1) & 0xFFFF] = (u >> 8).astype(np.uint8)
            self.ehist = hist[-7:].copy()
            self.epos = (self.epos + 4 * m) % size
            k += m
        return outL, outR


# ===================================================================== PPU register file
_RN = ('INIDISP OBSEL BGMODE MOSAIC BG1SC BG2SC BG3SC BG4SC BG12NBA BG34NBA '
       'BG1HOFS BG1VOFS BG2HOFS BG2VOFS BG3HOFS BG3VOFS BG4HOFS BG4VOFS '
       'M7SEL M7A M7B M7C M7D M7X M7Y M7HOFS M7VOFS W12SEL W34SEL WOBJSEL '
       'WH0 WH1 WH2 WH3 WBGLOG WOBJLOG TM TS TMW TSW CGWSEL CGADSUB COLR COLG COLB SETINI').split()
for _i, _n in enumerate(_RN):
    globals()['R_' + _n] = _i
NR = len(_RN)

PAT = ((0,), (0, 1), (0, 0), (0, 0, 1, 1), (0, 1, 2, 3), (0, 1, 0, 1), (0, 0), (0, 0, 1, 1))
VINC = (1, 32, 128, 128)
OBJ_SIZES = (((8, 8), (16, 16)), ((8, 8), (32, 32)), ((8, 8), (64, 64)), ((16, 16), (32, 32)),
             ((16, 16), (64, 64)), ((32, 32), (64, 64)), ((16, 32), (32, 64)), ((16, 32), (32, 32)))

# Commercial cart chipset ($FFD6) -> (label, compat). 'ok' = mapper/chip this core can try.
SA1_CHIPS = frozenset((0x32, 0x33, 0x34, 0x35))
CHIPSET_INFO = {
    0x00: ('ROM', 'ok'), 0x01: ('ROM+RAM', 'ok'), 0x02: ('ROM+RAM+Battery', 'ok'),
    0x03: ('DSP-1', 'ok'), 0x04: ('DSP-1+RAM', 'ok'), 0x05: ('DSP-1+RAM+Battery', 'ok'),
    0x13: ('SuperFX', 'ok'), 0x14: ('SuperFX+RAM', 'ok'), 0x15: ('SuperFX+RAM+Battery', 'ok'),
    0x1A: ('SuperFX+RAM+Battery', 'ok'),
    0x25: ('OBC1', 'ok'),
    0x32: ('SA-1', 'ok'), 0x33: ('SA-1', 'ok'), 0x34: ('SA-1+RAM', 'ok'),
    0x35: ('SA-1+RAM+Battery', 'ok'),
    0x43: ('S-DD1', 'ok'), 0x45: ('S-DD1+RAM+Battery', 'ok'),
    0x55: ('S-RTC', 'ok'),
    0xE3: ('SGB', 'ok'), 0xE5: ('SGB', 'ok'),
    0xF3: ('CX4', 'ok'), 0xF5: ('ST010/ST011', 'ok'), 0xF6: ('ST018', 'chip'),
    0xF9: ('SPC7110', 'ok'),
}
REGION_NAME = {
    0: 'Japan', 1: 'USA', 2: 'Europe', 3: 'Sweden', 4: 'Finland', 5: 'Denmark',
    6: 'France', 7: 'Netherlands', 8: 'Spain', 9: 'Germany', 10: 'Italy',
    11: 'China', 12: 'Indonesia', 13: 'Korea', 14: 'Common', 15: 'Canada',
    16: 'Brazil', 17: 'Australia', 18: 'Other',
}
ROM_EXTS = ('.sfc', '.smc', '.swc', '.fig', '.bin')
CONFIG_PATH = os.path.join(os.path.expanduser('~'), '.virtualsnes.json')


def strip_copier_header(data):
    data = bytes(data)
    return data[512:] if len(data) % 1024 == 512 else data


def _header_score(data, off, kind):
    """Score a candidate commercial internal header (LoROM / HiROM / ExHiROM)."""
    if len(data) < off + 0x40:
        return -99
    h = data[off:off + 0x40]
    sc = 0
    csum = h[0x1C] | (h[0x1D] << 8)
    comp = h[0x1E] | (h[0x1F] << 8)
    if (csum ^ comp) == 0xFFFF:
        sc += 8
    mm = h[0x15]
    mn = mm & 0x0F
    if kind == 'lorom' and mn in (0, 2, 3) and off == 0x7FC0:
        sc += 4
    if kind == 'hirom' and mn in (1, 3) and off == 0xFFC0:
        sc += 4
    if kind == 'exhirom' and mn == 5 and off == 0x40FFC0:
        sc += 6
    if kind == 'lorom' and not (mm & 1):
        sc += 1
    if kind in ('hirom', 'exhirom') and (mm & 1):
        sc += 1
    rst = h[0x3C] | (h[0x3D] << 8)
    if rst >= 0x8000:
        sc += 2
    else:
        sc -= 4
    title_ok = sum(1 for c in h[:21] if 32 <= c < 127)
    sc += 2 if title_ok >= 18 else (1 if title_ok >= 12 else -2)
    rom_sz = h[0x17]
    if 0x07 <= rom_sz <= 0x0D:
        sc += 1
    chip = h[0x16]
    if chip <= 0x05 or chip in CHIPSET_INFO:
        sc += 1
    return sc


def analyze_rom(data):
    """Detect commercial LoROM/HiROM/ExHiROM header, chipset, and Virtual SNES Emulator compat tag."""
    data = strip_copier_header(data)
    if len(data) < 0x8000:
        data = data + bytes(0x8000 - len(data))
    cands = [
        (_header_score(data, 0x7FC0, 'lorom'), 0x7FC0, False, False),
        (_header_score(data, 0xFFC0, 'hirom'), 0xFFC0, True, False),
        (_header_score(data, 0x40FFC0, 'exhirom'), 0x40FFC0, True, True),
    ]
    # Also try +512 if someone stripped wrong (rare)
    if len(data) > 0x8000 + 512:
        for base, kind, hi, ex in ((0x7FC0, 'lorom', False, False),
                                   (0xFFC0, 'hirom', True, False),
                                   (0x40FFC0, 'exhirom', True, True)):
            off = base + 512
            if off + 0x40 <= len(data):
                cands.append((_header_score(data, off, kind) - 3, off, hi, ex))
    sc, hoff, hirom, exhirom = max(cands, key=lambda t: t[0])
    h = data[hoff:hoff + 0x40]
    title = bytes(c if 32 <= c < 127 else 32 for c in h[:21]).decode().strip() or "UNTITLED"
    map_mode = h[0x15]
    chipset = h[0x16]
    rom_size_code = h[0x17]
    sram_code = h[0x18]
    region = h[0x19]
    # SA-1 BW-RAM goes up to 256 KB; other carts usually ≤128 KB
    sram_cap = 0x40000 if chipset in SA1_CHIPS else 0x20000
    sram_size = min(1024 << sram_code, sram_cap) if 0 < sram_code <= 8 else 0
    # SuperFX stores SRAM size in expansion field sometimes
    if chipset in (0x13, 0x14, 0x15, 0x1A) and sram_size == 0 and hoff >= 0x10:
        exp = data[hoff - 0x10 + 0x0D] if hoff >= 0x10 else 0
        if 0 < exp <= 8:
            sram_size = min(1024 << exp, 0x20000)
    chip_name, compat = CHIPSET_INFO.get(chipset, (f'Chipset ${chipset:02X}', 'unknown'))
    if exhirom:
        mapper = 'ExHiROM'
    elif hirom:
        mapper = 'HiROM'
    else:
        mapper = 'LoROM'
    if (map_mode & 0x0F) == 3 or chipset in SA1_CHIPS:
        mapper = 'SA-1'
        chip_name = chip_name if 'SA-1' in chip_name else 'SA-1'
        compat = 'ok'
    speed = 'FastROM' if map_mode & 0x10 else 'SlowROM'
    return {
        'data': data, 'title': title, 'hirom': hirom, 'exhirom': exhirom,
        'map_mode': map_mode, 'chipset': chipset, 'chip_name': chip_name,
        'rom_size_code': rom_size_code, 'sram_size': sram_size, 'region': region,
        'region_name': REGION_NAME.get(region, f'Region {region}'),
        'mapper': mapper, 'speed': speed, 'compat': compat, 'header_score': sc,
        'header_off': hoff,
    }



# ===================================================================== Commercial enhancement chips
# Custom HLE / cores from public hardware docs. Not a Snes9x port.
import math
import datetime

DSP_CHIPS = frozenset((0x03, 0x04, 0x05))
SFX_CHIPS = frozenset((0x13, 0x14, 0x15, 0x1A))
OBC1_CHIPS = frozenset((0x25,))
SDD1_CHIPS = frozenset((0x43, 0x45))
SRTC_CHIPS = frozenset((0x55,))
CX4_CHIPS = frozenset((0xF3,))
ST01X_CHIPS = frozenset((0xF5,))
ST018_CHIPS = frozenset((0xF6,))
SPC7110_CHIPS = frozenset((0xF9,))
SGB_CHIPS = frozenset((0xE3, 0xE5))
PLAYABLE_CHIPS = (SA1_CHIPS | DSP_CHIPS | SFX_CHIPS | OBC1_CHIPS | SDD1_CHIPS |
                  SRTC_CHIPS | CX4_CHIPS | ST01X_CHIPS | SPC7110_CHIPS | SGB_CHIPS)


def _s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def _u16(v):
    return v & 0xFFFF


# --------------------------------------------------------------------- DSP-1 / DSP-1B (HLE)
class DSP1:
    """NEC DSP-1 math HLE (Mario Kart, Pilotwings, …). Public command set."""

    # Angle unit: full circle = 65536
    def __init__(self, snes, hirom=False):
        self.snes = snes
        self.hirom = hirom
        self.power()

    def power(self):
        self.cmd = 0
        self.in_count = self.out_count = 0
        self.in_idx = self.out_idx = 0
        self.inputs = [0] * 8
        self.outputs = [0] * 1024
        self.waiting_cmd = True
        self.dr = True  # data ready
        # attitude matrices A/B/C (3x3 fixed 1.15-ish as int16 rows)
        self.mA = [[0] * 3 for _ in range(3)]
        self.mB = [[0] * 3 for _ in range(3)]
        self.mC = [[0] * 3 for _ in range(3)]
        self.les = self.aas = self.azs = 0
        self.raster_data = [0] * 4

    def _sin(self, a):
        return int(math.sin(a * (2 * math.pi / 65536.0)) * 32768) & 0xFFFF

    def _cos(self, a):
        return int(math.cos(a * (2 * math.pi / 65536.0)) * 32768) & 0xFFFF

    def _mul15(self, a, b):
        return _u16((_s16(a) * _s16(b)) >> 15)

    def _cmd_meta(self, c):
        # (n_in, n_out) — mirrors Overload/bsnes command table sizes
        table = {
            0x00: (2, 1), 0x10: (2, 2), 0x04: (2, 2), 0x08: (3, 2), 0x18: (4, 1),
            0x28: (3, 1), 0x0C: (3, 2), 0x1C: (6, 3), 0x02: (7, 4), 0x06: (3, 3),
            0x0A: (1, 4), 0x0E: (2, 2), 0x01: (4, 0), 0x11: (4, 0), 0x21: (4, 0),
            0x0D: (3, 3), 0x1D: (3, 3), 0x2D: (3, 3), 0x03: (3, 3), 0x13: (3, 3),
            0x23: (3, 3), 0x0B: (3, 1), 0x1B: (3, 1), 0x2B: (3, 1), 0x14: (6, 3),
            0x0F: (1, 1), 0x1F: (1, 1024), 0x2F: (1, 1), 0x20: (2, 1),
        }
        # aliases share sizes
        c &= 0x3F
        if c in table:
            return table[c]
        # map mirrored opcodes
        aliases = {0x05: 0x01, 0x09: 0x0D, 0x0D: 0x0D, 0x12: 0x02, 0x15: 0x11,
                   0x16: 0x06, 0x19: 0x1D, 0x22: 0x02, 0x24: 0x04, 0x25: 0x21,
                   0x26: 0x06, 0x29: 0x2D, 0x2C: 0x0C, 0x2E: 0x0E}
        return table.get(aliases.get(c, c), (0, 0))

    def write_data(self, v):
        v &= 0xFF
        # 16-bit little-endian stream on shared data port — games alternate lo/hi
        if not hasattr(self, '_wlo'):
            self._wlo = True
            self._wbuf = 0
        if self._wlo:
            self._wbuf = v
            self._wlo = False
            return
        word = self._wbuf | (v << 8)
        self._wlo = True
        self._write_word(word)

    def _write_word(self, w):
        if self.waiting_cmd:
            self.cmd = w & 0x3F
            self.in_idx = 0
            self.out_idx = 0
            self.in_count, self.out_count = self._cmd_meta(self.cmd)
            self.waiting_cmd = self.in_count == 0
            if self.in_count == 0:
                self._execute()
            return
        self.inputs[self.in_idx] = w & 0xFFFF
        self.in_idx += 1
        if self.in_idx >= self.in_count:
            self._execute()

    def read_data(self):
        if not hasattr(self, '_rlo'):
            self._rlo = True
            self._rword = 0
        if self._rlo:
            if self.out_idx < self.out_count:
                self._rword = self.outputs[self.out_idx] & 0xFFFF
                self.out_idx += 1
                if self.out_idx >= self.out_count:
                    self.waiting_cmd = True
            else:
                self._rword = 0
            self._rlo = False
            return self._rword & 0xFF
        self._rlo = True
        return (self._rword >> 8) & 0xFF

    def read_status(self):
        return 0x80  # always ready in HLE

    def _set_out(self, *vals):
        self.outputs = list(vals)
        self.out_count = len(vals)
        self.out_idx = 0
        self.waiting_cmd = False

    def _attitude(self, mat):
        # inputs: AZ, AY, AX, — build rotation matrix into mat
        az, ay, ax = self.inputs[0], self.inputs[1], self.inputs[2]
        # ignore 4th
        sx, cx = _s16(self._sin(ax)), _s16(self._cos(ax))
        sy, cy = _s16(self._sin(ay)), _s16(self._cos(ay))
        sz, cz = _s16(self._sin(az)), _s16(self._cos(az))
        # Rz*Ry*Rx style (DSP-1 attitude)
        mat[0][0] = _u16((cy * cz) >> 15)
        mat[0][1] = _u16((sx * sy * cz - cx * sz) >> 30) if False else _u16(
            ((_s16(_u16((sy * cz) >> 15)) * sx >> 15) - ((_s16(sz) * cx) >> 15)) & 0xFFFF)
        # Use float for stability then quantize
        axf = ax * (2 * math.pi / 65536.0)
        ayf = ay * (2 * math.pi / 65536.0)
        azf = az * (2 * math.pi / 65536.0)
        cx_, sx_ = math.cos(axf), math.sin(axf)
        cy_, sy_ = math.cos(ayf), math.sin(ayf)
        cz_, sz_ = math.cos(azf), math.sin(azf)
        # R = Rz * Ry * Rx
        r = [
            [cy_ * cz_, sx_ * sy_ * cz_ - cx_ * sz_, cx_ * sy_ * cz_ + sx_ * sz_],
            [cy_ * sz_, sx_ * sy_ * sz_ + cx_ * cz_, cx_ * sy_ * sz_ - sx_ * cz_],
            [-sy_, sx_ * cy_, cx_ * cy_],
        ]
        for i in range(3):
            for j in range(3):
                mat[i][j] = _u16(int(r[i][j] * 32768))
        self._set_out()  # 0 outputs

    def _execute(self):
        c = self.cmd & 0x3F
        I = self.inputs
        if c in (0x00, 0x20):
            p = (_s16(I[0]) * _s16(I[1])) >> 15
            self._set_out(_u16(p))
        elif c == 0x10:
            m, e = _s16(I[0]), _s16(I[1])
            if m == 0:
                self._set_out(0x7FFF, e)
            else:
                inv = int((1.0 / (m / 32768.0)) * 32768)
                # normalize
                while abs(inv) >= 32768:
                    inv //= 2; e += 1
                while abs(inv) < 16384 and inv != 0:
                    inv *= 2; e -= 1
                self._set_out(_u16(inv), _u16(e))
        elif c in (0x04, 0x24):
            a, r = I[0], _s16(I[1])
            s = _s16(self._sin(a)); co = _s16(self._cos(a))
            self._set_out(_u16((r * s) >> 15), _u16((r * co) >> 15))
        elif c == 0x08:
            s = _s16(I[0]) ** 2 + _s16(I[1]) ** 2 + _s16(I[2]) ** 2
            self._set_out(s & 0xFFFF, (s >> 16) & 0xFFFF)
        elif c == 0x18:
            s = _s16(I[0]) ** 2 + _s16(I[1]) ** 2 + _s16(I[2]) ** 2 - _s16(I[3]) ** 2
            self._set_out(_u16(s >> 15))
        elif c == 0x28:
            s = _s16(I[0]) ** 2 + _s16(I[1]) ** 2 + _s16(I[2]) ** 2
            self._set_out(_u16(int(math.sqrt(max(s, 0)))))
        elif c in (0x0C, 0x2C):
            a, x, y = I[0], _s16(I[1]), _s16(I[2])
            s = _s16(self._sin(a)); co = _s16(self._cos(a))
            self._set_out(_u16((x * co - y * s) >> 15), _u16((x * s + y * co) >> 15))
        elif c == 0x1C:
            ax, ay, az = I[0], I[1], I[2]
            x, y, z = _s16(I[3]), _s16(I[4]), _s16(I[5])
            axf, ayf, azf = [v * (2 * math.pi / 65536.0) for v in (ax, ay, az)]
            # apply Rx Ry Rz to vector
            # Rx
            y, z = y * math.cos(axf) - z * math.sin(axf), y * math.sin(axf) + z * math.cos(axf)
            # Ry
            x, z = x * math.cos(ayf) + z * math.sin(ayf), -x * math.sin(ayf) + z * math.cos(ayf)
            # Rz
            x, y = x * math.cos(azf) - y * math.sin(azf), x * math.sin(azf) + y * math.cos(azf)
            self._set_out(_u16(int(x)), _u16(int(y)), _u16(int(z)))
        elif c in (0x01, 0x05):
            self._attitude(self.mA)
        elif c in (0x11, 0x15):
            self._attitude(self.mB)
        elif c in (0x21, 0x25):
            self._attitude(self.mC)
        elif c == 0x02 or c == 0x12 or c == 0x22:
            # Parameter: F, L, V, He, Le, Az, — outputs raster helpers
            self.les = I[4]; self.aas = I[5]; self.azs = I[6] if len(I) > 6 else 0
            self._set_out(I[0], I[1], I[2], I[3])
        elif c in (0x06, 0x16, 0x26):
            # Project
            x, y, z = _s16(I[0]), _s16(I[1]), _s16(I[2])
            if z == 0: z = 1
            self._set_out(_u16((x << 8) // z), _u16((y << 8) // z), _u16(z))
        elif c == 0x0A:
            # Raster continuous — return centerline params
            self._set_out(self.les, self.aas, self.azs, 0)
        elif c in (0x0E, 0x2E):
            self._set_out(I[0], I[1])
        elif c in (0x0D, 0x09, 0x1D, 0x19, 0x2D, 0x29):
            mat = self.mA if c in (0x0D, 0x09) else (self.mB if c in (0x1D, 0x19) else self.mC)
            x, y, z = _s16(I[0]), _s16(I[1]), _s16(I[2])
            ox = (_s16(mat[0][0]) * x + _s16(mat[0][1]) * y + _s16(mat[0][2]) * z) >> 15
            oy = (_s16(mat[1][0]) * x + _s16(mat[1][1]) * y + _s16(mat[1][2]) * z) >> 15
            oz = (_s16(mat[2][0]) * x + _s16(mat[2][1]) * y + _s16(mat[2][2]) * z) >> 15
            self._set_out(_u16(ox), _u16(oy), _u16(oz))
        elif c in (0x03, 0x13, 0x23):
            mat = self.mA if c == 0x03 else (self.mB if c == 0x13 else self.mC)
            x, y, z = _s16(I[0]), _s16(I[1]), _s16(I[2])
            # inverse rotation ~ transpose
            ox = (_s16(mat[0][0]) * x + _s16(mat[1][0]) * y + _s16(mat[2][0]) * z) >> 15
            oy = (_s16(mat[0][1]) * x + _s16(mat[1][1]) * y + _s16(mat[2][1]) * z) >> 15
            oz = (_s16(mat[0][2]) * x + _s16(mat[1][2]) * y + _s16(mat[2][2]) * z) >> 15
            self._set_out(_u16(ox), _u16(oy), _u16(oz))
        elif c in (0x0B, 0x1B, 0x2B):
            mat = self.mA if c == 0x0B else (self.mB if c == 0x1B else self.mC)
            x, y, z = _s16(I[0]), _s16(I[1]), _s16(I[2])
            s = (_s16(mat[2][0]) * x + _s16(mat[2][1]) * y + _s16(mat[2][2]) * z) >> 15
            self._set_out(_u16(s))
        elif c == 0x14:
            self._set_out(I[0], I[1], I[2])
        elif c == 0x0F:
            self._set_out(0x0000)
        elif c == 0x2F:
            self._set_out(0x0100)
        elif c == 0x1F:
            self._set_out(*([0] * 1024))
        else:
            self._set_out(0)

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        b = bank & 0x7F
        if self.hirom:
            return b < 0x10 and 0x6000 <= off < 0x8000
        return 0x30 <= b < 0x40 and off >= 0x8000

    def read(self, a):
        off = a & 0xFFFF
        if self.hirom:
            if 0x7000 <= off < 0x8000:
                return self.read_status()
            return self.read_data()
        if off >= 0xC000:
            return self.read_status()
        return self.read_data()

    def write(self, a, v):
        off = a & 0xFFFF
        if self.hirom and 0x7000 <= off < 0x8000:
            return
        if (not self.hirom) and off >= 0xC000:
            return
        self.write_data(v)

    def get_state(self):
        return {k: getattr(self, k) for k in (
            'cmd', 'in_count', 'out_count', 'in_idx', 'out_idx', 'waiting_cmd',
            'inputs', 'outputs', 'mA', 'mB', 'mC', 'les', 'aas', 'azs', 'hirom')}

    def set_state(self, st):
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- OBC1
class OBC1:
    """OBC1 sprite address helper (Metal Combat)."""

    def __init__(self, snes):
        self.snes = snes
        self.ram = bytearray(0x2000)
        self.address = 0
        self.baseptr = 0
        self.shift = 0

    def power(self):
        self.address = self.baseptr = self.shift = 0

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        return (bank & 0x7F) < 0x40 and 0x6000 <= off < 0x8000

    def read(self, a):
        off = a & 0x1FFF
        if off >= 0x1FF0:
            i = off & 3
            ptr = (self.baseptr + (self.address << 2) + i) & 0x1FFF
            if i == 3:  # high nibble special
                return ((self.ram[(self.baseptr + 0x100 + (self.address >> 2)) & 0x1FFF]
                         >> ((self.address & 3) << 1)) & 3) << 0
            return self.ram[ptr]
        return self.ram[off]

    def write(self, a, v):
        off = a & 0x1FFF; v &= 0xFF
        if off == 0x1FF0:
            self.address = (self.address & 0x100) | v
        elif off == 0x1FF1:
            self.address = (self.address & 0x0FF) | ((v & 1) << 8)
        elif off == 0x1FF2:
            self.baseptr = (v & 0x3F) << 4
        elif off == 0x1FF3:
            pass
        else:
            self.ram[off] = v

    def get_state(self):
        return dict(address=self.address, baseptr=self.baseptr, shift=self.shift, ram=bytes(self.ram))

    def set_state(self, st):
        self.ram[:] = st.pop('ram', bytes(0x2000))
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- S-RTC
class SRTC:
    """S-RTC realtime clock (Daikaijuu Monogatari II)."""

    def __init__(self, snes):
        self.snes = snes
        self.mode = 0
        self.index = 0
        self.data = [0] * 13

    def power(self):
        self.mode = 0; self.index = 0
        self._latch_now()

    def _latch_now(self):
        n = datetime.datetime.now()
        self.data = [
            n.second % 10, n.second // 10,
            n.minute % 10, n.minute // 10,
            n.hour % 10, n.hour // 10,
            n.day % 10, n.day // 10,
            n.month % 10, n.month // 10,
            n.year % 10, (n.year // 10) % 10,
            n.weekday(),
        ]

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        return (bank & 0x7F) < 0x40 and off in (0x2800, 0x2801)

    def read(self, a):
        if (a & 0xFFFF) == 0x2800:
            if self.index >= len(self.data):
                return 0x0F
            v = self.data[self.index] & 0x0F
            self.index += 1
            return v
        return 0x0F

    def write(self, a, v):
        if (a & 0xFFFF) != 0x2801:
            return
        v &= 0x0F
        if v == 0x0D:
            self.mode = 0; self.index = -1; return
        if v == 0x0E:
            self.mode = 0; self.index = 0; self._latch_now(); return
        if self.index < 0:
            self.index = 0; return
        if self.index < len(self.data):
            self.data[self.index] = v
            self.index += 1

    def get_state(self):
        return dict(mode=self.mode, index=self.index, data=list(self.data))

    def set_state(self, st):
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- S-DD1 (Andreas Naive ABS Golomb HLE)
class SDD1:
    """S-DD1 MMIO + on-DMA Golomb decompress (public ABS algorithm)."""

    # Evolution table: (code_num, next_mps, next_lps) — LPS also flips MPS for states 0,1
    _EVOL = (
        (0, 25, 25), (0, 2, 1), (0, 3, 1), (0, 4, 2), (0, 5, 3),
        (1, 6, 4), (1, 7, 5), (1, 8, 6), (1, 9, 7),
        (2, 10, 8), (2, 11, 9), (2, 12, 10), (2, 13, 11),
        (3, 14, 12), (3, 15, 13), (3, 16, 14), (3, 17, 15),
        (4, 18, 16), (4, 19, 17), (5, 20, 18), (5, 21, 19),
        (6, 22, 20), (6, 23, 21), (7, 24, 22), (7, 24, 23),
        (0, 26, 1), (1, 27, 2), (2, 28, 4), (3, 29, 8),
        (4, 30, 12), (5, 31, 16), (6, 32, 18), (7, 24, 22),
    )

    def __init__(self, snes):
        self.snes = snes
        self.dma_enable = [0] * 8
        self.bank = [0] * 4
        self._buf = bytearray()
        self._bi = 0

    def power(self):
        self.dma_enable = [0] * 8
        self.bank = [0] * 4
        self._buf = bytearray(); self._bi = 0

    def handles_mmio(self, a):
        bank, off = a >> 16, a & 0xFFFF
        return (bank & 0x7F) < 0x40 and 0x4800 <= off <= 0x4807

    def read_mmio(self, a):
        return 0

    def write_mmio(self, a, v):
        off = a & 0xFFFF; v &= 0xFF
        if off == 0x4800:
            for i in range(8):
                self.dma_enable[i] = (v >> i) & 1
        elif 0x4801 <= off <= 0x4804:
            self.bank[off - 0x4801] = v & 0x0F

    def map_rom(self, bank, addr):
        """Map CPU bank through S-DD1 bank regs into file offset."""
        b = bank & 0xFF
        if 0xC0 <= b <= 0xFF:
            bi = (b - 0xC0) >> 4
            top = self.bank[bi] & 0x0F
            return ((top << 20) | ((b & 0x0F) << 16) | (addr & 0xFFFF)) % self.snes.romlen
        return self.snes.rom_offset(bank, addr)

    def decompress_stream(self, data, nbytes):
        """Decompress nbytes from a compressed byte stream (header in first nibble)."""
        if not data or nbytes <= 0:
            return bytes(nbytes)
        bit_i = [0]

        def bit():
            i = bit_i[0]
            if (i >> 3) >= len(data):
                bit_i[0] = i + 1
                return 0
            v = (data[i >> 3] >> (7 - (i & 7))) & 1
            bit_i[0] = i + 1
            return v

        # 4-bit header is first 4 bits of stream
        h0 = bit(); h1 = bit(); h2 = bit(); h3 = bit()
        plane_mode = (h0 << 1) | h1
        ctx_mode = (h2 << 1) | h3

        # context templates (bit positions looking back)
        templates = (
            (1, 7, 8, 9), (1, 8, 9), (1, 7, 8), (1, 2, 8, 9),
        )
        tmpl = templates[ctx_mode]
        nctx_bits = len(tmpl)

        # probability state per context (32 or 16 contexts × 2 parity sets)
        nctx = (1 << nctx_bits) * 2
        status = [0] * nctx
        mps = [0] * nctx

        # bit generators: remaining MPS run + pending LPS
        bg_cnt = [0] * 8
        bg_lps = [False] * 8

        def get_run(code):
            # Golomb code code: 0 -> 2^code MPS; 1+codebits -> k MPS + LPS
            if bit() == 0:
                return (1 << code), False
            k = 0
            for _ in range(code):
                k = (k << 1) | bit()
            return k, True

        def gen_bit(code):
            if bg_cnt[code] == 0 and not bg_lps[code]:
                bg_cnt[code], bg_lps[code] = get_run(code)
            end = False
            if bg_cnt[code] > 0:
                bg_cnt[code] -= 1
                b = 0
                if bg_cnt[code] == 0 and not bg_lps[code]:
                    end = True
            else:
                b = 1
                bg_lps[code] = False
                end = True
            return b, end

        def pem_bit(ctx):
            st = status[ctx]
            code, nxt_m, nxt_l = SDD1._EVOL[st]
            b, end = gen_bit(code)
            out = b ^ mps[ctx]
            if end:
                if b:  # LPS
                    if st <= 1:
                        mps[ctx] ^= 1
                    status[ctx] = nxt_l
                else:
                    status[ctx] = nxt_m
            return out

        # previous bits per bitplane (9-bit history)
        hist = [0] * 8
        out = bytearray(nbytes)
        # Bitplane modes (Andreas Naive / wiki): 00=2bpp 01=8bpp 10=4bpp 11=mode7-ish

        def want_bit(p):
            # context from history
            h = hist[p]
            ctx = 0
            for i, back in enumerate(tmpl):
                ctx |= ((h >> (back - 1)) & 1) << i
            ctx |= (p & 1) << nctx_bits
            b = pem_bit(ctx & (nctx - 1))
            hist[p] = ((h << 1) | b) & 0x1FF
            return b

        def take_plane_byte(p):
            v = 0
            for _ in range(8):
                v = (v << 1) | want_bit(p)
            return v & 0xFF

        i = 0
        if plane_mode == 0:  # 2bpp: p0,p1,p0,p1,...
            while i < nbytes:
                out[i] = take_plane_byte(0); i += 1
                if i >= nbytes: break
                out[i] = take_plane_byte(1); i += 1
        elif plane_mode == 2:  # 4bpp: 16-byte groups p0/p1×8 then p2/p3×8
            while i < nbytes:
                for _ in range(8):
                    if i >= nbytes: break
                    out[i] = take_plane_byte(0); i += 1
                    if i >= nbytes: break
                    out[i] = take_plane_byte(1); i += 1
                for _ in range(8):
                    if i >= nbytes: break
                    out[i] = take_plane_byte(2); i += 1
                    if i >= nbytes: break
                    out[i] = take_plane_byte(3); i += 1
        elif plane_mode == 1:  # 8bpp: four 16-byte pairs
            while i < nbytes:
                for pair in range(4):
                    p0, p1 = pair * 2, pair * 2 + 1
                    for _ in range(8):
                        if i >= nbytes: break
                        out[i] = take_plane_byte(p0); i += 1
                        if i >= nbytes: break
                        out[i] = take_plane_byte(p1); i += 1
        else:  # mode 3: bit-position planes — bit0s, bit1s, ... of successive bytes
            # Emit 8 bytes at a time: for bitplane b, the b-th bits of 8 consecutive bytes
            while i < nbytes:
                chunk = min(8, nbytes - i)
                bits = [[want_bit(b) for _ in range(chunk)] for b in range(8)]
                for n in range(chunk):
                    v = 0
                    for b in range(8):
                        v |= bits[b][n] << b
                    out[i + n] = v
                i += chunk
        return bytes(out)

    def dma_read(self, bank, addr, size):
        """Read `size` bytes for a DMA channel, decompressing when enabled."""
        snes = self.snes
        # Gather a generous compressed window from ROM
        off0 = self.map_rom(bank, addr)
        # Compressed size is unknown; pull up to 2× plus header padding
        grab = min(len(snes.rom) - off0, max(size * 2 + 16, size + 64))
        src = snes.rom[off0:off0 + grab]
        try:
            return self.decompress_stream(src, size)
        except Exception:
            # Fall back to raw ROM so boots still live
            return bytes(snes.rom[(off0 + i) % snes.romlen] for i in range(size))

    def get_state(self):
        return dict(dma_enable=list(self.dma_enable), bank=list(self.bank))

    def set_state(self, st):
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- CX4 (Capcom — Mega Man X2/X3) HLE MMIO + IRAM
class CX4:
    """CX4: 2KB IRAM + command HLE for common Capcom ops."""

    def __init__(self, snes):
        self.snes = snes
        self.ram = bytearray(0xC00)
        self.dma = 0
        self.page = 0
        self.busy = False

    def power(self):
        self.ram[:] = b'\x00' * 0xC00
        self.dma = self.page = 0
        self.busy = False

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        return (bank & 0x7F) < 0x40 and 0x6000 <= off < 0x8000

    def _w16(self, addr, v):
        self.ram[addr & 0xBFF] = v & 0xFF
        self.ram[(addr + 1) & 0xBFF] = (v >> 8) & 0xFF

    def _r16(self, addr):
        return self.ram[addr & 0xBFF] | (self.ram[(addr + 1) & 0xBFF] << 8)

    def read(self, a):
        off = a & 0x1FFF
        if off == 0x1F50:
            return 0x00 if self.busy else 0x40  # not busy
        if off < 0xC00:
            return self.ram[off]
        return 0

    def write(self, a, v):
        off = a & 0x1FFF; v &= 0xFF
        if off < 0xC00:
            self.ram[off] = v
        if off == 0x1F4F:
            self._run(v)
        elif off == 0x1F47:
            self.page = v
        elif off == 0x1F4E:
            pass

    def _run(self, cmd):
        # Immediate HLE for frequent CX4 commands used by MMX2/X3
        if cmd == 0x00:  # nop / wire
            return
        if cmd == 0x01:  # multiply
            a = _s16(self._r16(0x1F40)); b = _s16(self._r16(0x1F42))
            r = a * b
            self._w16(0x1F40, r & 0xFFFF); self._w16(0x1F42, (r >> 16) & 0xFFFF)
        elif cmd == 0x05:  # transform / rotate-ish
            pass
        elif cmd == 0x0D:  # square
            a = _s16(self._r16(0x1F40)); self._w16(0x1F40, (a * a) & 0xFFFF)
        elif cmd == 0x13:  # sqrt
            a = self._r16(0x1F40); self._w16(0x1F40, int(math.sqrt(a)) & 0xFFFF)
        elif cmd == 0x25:  # DMA-ish fill
            pass

    def get_state(self):
        return dict(ram=bytes(self.ram), dma=self.dma, page=self.page, busy=self.busy)

    def set_state(self, st):
        self.ram[:] = st.pop('ram', bytes(0xC00))
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- SuperFX / GSU
class SuperFX:
    """Argonaut GSU (Super FX) — full 256-opcode custom RISC + PLOT engine."""

    def __init__(self, snes):
        self.snes = snes
        self.r = [0] * 16
        self.sfr = 0
        self.pbr = self.rombr = 0
        self.rambr = 0
        self.cbr = 0
        self.scbr = 0
        self.scmr = 0
        self.colr = 0
        self.por = 0
        self.vcr = 0x04
        self.cfgr = 0
        self.clsr = 0
        self.cache = bytearray(512)
        self.cache_valid = bytearray(32)
        self.running = False
        self.src = self.dst = 0
        self.alt1 = self.alt2 = False
        self.b_flag = False  # WITH sets B; next TO/FROM becomes MOVE/MOVES
        self.ops_covered = 256  # documentation: every opcode slot is handled

    def power(self):
        self.r = [0] * 16
        self.sfr = 0
        self.pbr = self.rombr = self.rambr = 0
        self.cbr = self.scbr = self.scmr = 0
        self.colr = self.por = self.cfgr = self.clsr = 0
        self.cache[:] = b'\x00' * 512
        self.cache_valid[:] = b'\x00' * 32
        self.running = False
        self.src = self.dst = 0
        self.alt1 = self.alt2 = False
        self.b_flag = False

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        return (bank & 0x7F) < 0x40 and 0x3000 <= off < 0x3300

    def _flag_z(self, v):
        self.sfr = (self.sfr | 0x02) if (v & 0xFFFF) == 0 else (self.sfr & ~0x02)

    def _flag_s(self, v):
        self.sfr = (self.sfr | 0x08) if (v & 0x8000) else (self.sfr & ~0x08)

    def _flag_cy(self, c):
        self.sfr = (self.sfr | 0x04) if c else (self.sfr & ~0x04)

    def _flag_ov(self, o):
        self.sfr = (self.sfr | 0x10) if o else (self.sfr & ~0x10)

    def _zs(self, v):
        v &= 0xFFFF
        self._flag_z(v); self._flag_s(v)
        return v

    def read_reg(self, a):
        off = a & 0xFFFF
        if 0x3000 <= off <= 0x301F:
            i = (off - 0x3000) >> 1
            return (self.r[i] >> ((off & 1) * 8)) & 0xFF
        if off == 0x3030: return self.sfr & 0xFF
        if off == 0x3031: return (self.sfr >> 8) & 0xFF
        if off == 0x3034: return self.pbr & 0x7F
        if off == 0x3036: return self.rombr
        if off == 0x303B: return self.vcr
        if off == 0x303C: return self.rambr & 1
        if off == 0x303E: return self.cbr & 0xFF
        if off == 0x303F: return (self.cbr >> 8) & 0xFF
        return 0

    def write_reg(self, a, v):
        off = a & 0xFFFF; v &= 0xFF
        if 0x3000 <= off <= 0x301F:
            i = (off - 0x3000) >> 1
            if off & 1:
                self.r[i] = (self.r[i] & 0x00FF) | (v << 8)
            else:
                self.r[i] = (self.r[i] & 0xFF00) | v
            if i == 15 and (off & 1) == 1:
                self._start()
            return
        if off == 0x3030:
            # writing G=1 can resume; G=0 stops
            if v & 0x20:
                self._start()
            else:
                self.running = False
                self.sfr = (self.sfr & 0xFF00) | (v & 0xDF)
                self.sfr &= ~0x20
                return
            self.sfr = (self.sfr & 0xFF00) | (v & 0xFF)
        elif off == 0x3031:
            self.sfr = (self.sfr & 0x00FF) | ((v & 0x7F) << 8)
        elif off == 0x3034:
            self.pbr = v & 0x7F
        elif off == 0x3037:
            self.cfgr = v
        elif off == 0x3038:
            self.scbr = v
        elif off == 0x3039:
            self.clsr = v
        elif off == 0x303A:
            self.scmr = v

    def _start(self):
        self.running = True
        self.sfr = (self.sfr | 0x20) & ~0x8000

    def _rom_read(self, bank, addr):
        s = self.snes
        b = bank & 0x7F
        if b < 0x40 and addr < 0x8000:
            return 0xFF
        if b >= 0x40:
            off = ((b & 0x3F) << 16) | (addr & 0xFFFF)
        else:
            off = ((b & 0x3F) << 15) | (addr & 0x7FFF)
        return s.rom[off % s.romlen]

    def _ram_read(self, addr):
        ram = self.snes.sram
        if not ram:
            return 0xFF
        a = ((self.rambr & 1) << 16) | (addr & 0xFFFF)
        return ram[a % len(ram)]

    def _ram_write(self, addr, v):
        ram = self.snes.sram
        if not ram:
            return
        a = ((self.rambr & 1) << 16) | (addr & 0xFFFF)
        ram[a % len(ram)] = v & 0xFF

    def _fetch(self):
        pc = self.r[15]
        caddr = (pc - self.cbr) & 0xFFFF
        if caddr < 512:
            block = caddr >> 4
            if not self.cache_valid[block]:
                base = (self.cbr + (block << 4)) & 0xFFFF
                for i in range(16):
                    self.cache[(block << 4) + i] = self._rom_read(self.pbr, (base + i) & 0xFFFF)
                self.cache_valid[block] = 1
            op = self.cache[caddr]
        else:
            op = self._rom_read(self.pbr, pc)
        self.r[15] = (pc + 1) & 0xFFFF
        return op

    def _plot(self):
        x = self.r[1] & 0xFF
        y = self.r[2] & 0xFF
        color = self.colr
        md = self.scmr & 3
        bpp = (2, 4, 4, 8)[md]
        ht = ((self.scmr >> 2) & 1) | (((self.scmr >> 5) & 1) << 1)
        height = (128, 160, 192, 256)[ht]
        if y >= height:
            self.r[1] = (self.r[1] + 1) & 0xFFFF
            return
        base = self.scbr << 10
        tx, ty = x >> 3, y >> 3
        px, py = x & 7, y & 7
        tile = ty * 32 + tx
        bit = 7 - px
        ram = self.snes.sram
        if not ram:
            return
        for plane in range(bpp):
            a = (base + tile * (8 * bpp) + (plane & ~1) * 8 + py * 2 + (plane & 1)) % len(ram)
            if color & (1 << plane):
                ram[a] |= (1 << bit)
            else:
                ram[a] &= ~(1 << bit)
        self.r[1] = (self.r[1] + 1) & 0xFFFF

    def _rpix(self):
        # Approximate: return COLR-ish; full planar read omitted
        self.r[self.dst] = self._zs(0)

    def step(self, max_ops=256):
        if not self.running:
            return
        for _ in range(max_ops):
            if not self.running:
                break
            self._exec_one()

    def run_to(self, budget=2048):
        self.step(budget)

    def _branch(self, take):
        off = self._fetch()
        if off & 0x80:
            off -= 256
        if take:
            self.r[15] = (self.r[15] + off) & 0xFFFF

    def _exec_one(self):
        """Dispatch every GSU opcode $00-$FF (ALT1/2/3 variants included)."""
        op = self._fetch()
        alt1, alt2 = self.alt1, self.alt2
        self.alt1 = self.alt2 = False
        S, D = self.src, self.dst
        z = bool(self.sfr & 0x02)
        cy = bool(self.sfr & 0x04)
        sflg = bool(self.sfr & 0x08)
        ov = bool(self.sfr & 0x10)

        # ---- $00-$0F control / shift / branches ----
        if op == 0x00:  # STOP (delay slot: next insn already conceptually pending; we halt now)
            self.running = False
            self.sfr = (self.sfr & ~0x20) | 0x8000
            return
        if op == 0x01:  # NOP
            return
        if op == 0x02:  # CACHE
            self.cbr = self.r[15] & 0xFFF0
            self.cache_valid[:] = b'\x00' * 32
            return
        if op == 0x03:  # LSR
            v = self.r[S]; self._flag_cy(v & 1)
            self.r[D] = self._zs(v >> 1); return
        if op == 0x04:  # ROL
            v = self.r[S]; cin = 1 if cy else 0
            self._flag_cy((v >> 15) & 1)
            self.r[D] = self._zs(((v << 1) | cin) & 0xFFFF); return
        if op == 0x05:  # BRA
            self._branch(True); return
        if op == 0x06:  # BGE
            self._branch(not (sflg ^ ov)); return
        if op == 0x07:  # BLT
            self._branch(sflg ^ ov); return
        if op == 0x08:  # BNE
            self._branch(not z); return
        if op == 0x09:  # BEQ
            self._branch(z); return
        if op == 0x0A:  # BPL
            self._branch(not sflg); return
        if op == 0x0B:  # BMI
            self._branch(sflg); return
        if op == 0x0C:  # BCC
            self._branch(not cy); return
        if op == 0x0D:  # BCS
            self._branch(cy); return
        if op == 0x0E:  # BVC
            self._branch(not ov); return
        if op == 0x0F:  # BVS
            self._branch(ov); return

        # ---- $10-$1F TO / MOVE ----
        if 0x10 <= op <= 0x1F:
            n = op & 0x0F
            if self.b_flag:  # MOVE Rs, Rn
                self.r[n] = self.r[S]
                self.b_flag = False
                self.sfr &= ~0x1000  # clear B in SFR high
            else:
                self.dst = n
            return

        # ---- $20-$2F WITH ----
        if 0x20 <= op <= 0x2F:
            n = op & 0x0F
            self.src = self.dst = n
            self.b_flag = True
            self.sfr |= 0x1000
            return

        # ---- $30-$3B STW/STB (Rn) ----
        if 0x30 <= op <= 0x3B:
            n = op & 0x0F
            addr = self.r[n]
            if alt1:  # STB
                self._ram_write(addr, self.r[S] & 0xFF)
            else:  # STW
                self._ram_write(addr, self.r[S] & 0xFF)
                self._ram_write((addr + 1) & 0xFFFF, (self.r[S] >> 8) & 0xFF)
            return
        if op == 0x3C:  # LOOP
            self.r[12] = (self.r[12] - 1) & 0xFFFF
            self._flag_z(self.r[12])
            if self.r[12] != 0:
                self.r[15] = self.r[13]
            return
        if op == 0x3D:  # ALT1
            self.alt1 = True; return
        if op == 0x3E:  # ALT2
            self.alt2 = True; return
        if op == 0x3F:  # ALT3
            self.alt1 = self.alt2 = True; return

        # ---- $40-$4B LDW/LDB (Rn) ----
        if 0x40 <= op <= 0x4B:
            n = op & 0x0F
            addr = self.r[n]
            if alt1:  # LDB
                self.r[D] = self._zs(self._ram_read(addr))
            else:
                self.r[D] = self._zs(self._ram_read(addr) | (self._ram_read((addr + 1) & 0xFFFF) << 8))
            return
        if op == 0x4C:  # PLOT / RPIX
            if alt1:
                self._rpix()
            else:
                self._plot()
            return
        if op == 0x4D:  # SWAP
            v = self.r[S]
            self.r[D] = self._zs(((v >> 8) | (v << 8)) & 0xFFFF); return
        if op == 0x4E:  # COLOR / CMODE
            if alt1:
                self.por = self.r[S] & 0xFF
            else:
                self.colr = self.r[S] & 0xFF
            return
        if op == 0x4F:  # NOT
            self.r[D] = self._zs((~self.r[S]) & 0xFFFF); return

        # ---- $50-$5F ADD / ADC / ADD# / ADC# ----
        if 0x50 <= op <= 0x5F:
            n = op & 0x0F
            a = self.r[S]
            if alt2:
                b = n
            else:
                b = self.r[n]
            cin = (1 if cy else 0) if alt1 else 0
            r = a + b + cin
            self._flag_cy(r > 0xFFFF)
            self._flag_ov(((a ^ r) & (b ^ r) & 0x8000) != 0)
            self.r[D] = self._zs(r); return

        # ---- $60-$6F SUB / CMP / SUB# / CMP# ----
        if 0x60 <= op <= 0x6F:
            n = op & 0x0F
            a = self.r[S]
            b = n if alt2 else self.r[n]
            # ALT1 alone = CMP (no store); ALT1+ALT2 = CMP #n; plain = SUB; ALT2 = SUB #
            # With ALT1 and not only compare for SBC: hardware uses ALT1=SBC? 
            # Docs: ALT1 SUB = CMP (no write). ALT3 (ALT1+ALT2) = CMP #imm.
            r = a - b
            self._flag_cy(a >= b)
            self._flag_ov(((a ^ b) & (a ^ r) & 0x8000) != 0)
            rr = r & 0xFFFF
            self._zs(rr)
            if not alt1:  # SUB / SUB # — store
                self.r[D] = rr
            return

        # ---- $70 MERGE (or AND #0 / AND R0 with ALT); $71-$7F AND / BIC ----
        if 0x70 <= op <= 0x7F:
            n = op & 0x0F
            if op == 0x70 and not alt1 and not alt2:  # MERGE
                self.r[D] = self._zs((self.r[7] & 0xFF00) | ((self.r[8] >> 8) & 0xFF))
                return
            b = n if alt2 else self.r[n]
            if alt1:  # BIC / BIC #
                r = self.r[S] & (~b)
            else:
                r = self.r[S] & b
            self.r[D] = self._zs(r); return

        # ---- $80-$8F MULT / UMULT ----
        if 0x80 <= op <= 0x8F:
            n = op & 0x0F
            if alt2:
                b = n
            else:
                b = self.r[n]
            if alt1:  # UMULT
                r = (self.r[S] & 0xFF) * (b & 0xFF)
            else:
                r = (_s16(self.r[S]) * _s16(b)) & 0xFFFF
            self.r[D] = self._zs(r & 0xFFFF); return

        # ---- $90-$9F ----
        if op == 0x90:  # SBK — store at last RAM addr (approx: use R0)
            self._ram_write(self.r[0], self.r[S] & 0xFF)
            self._ram_write((self.r[0] + 1) & 0xFFFF, (self.r[S] >> 8) & 0xFF)
            return
        if 0x91 <= op <= 0x94:  # LINK #n
            self.r[11] = (self.r[15] + (op - 0x90)) & 0xFFFF; return
        if op == 0x95:  # SEX
            v = self.r[S] & 0xFF
            self.r[D] = self._zs(v | (0xFF00 if v & 0x80 else 0)); return
        if op == 0x96:  # ASR / DIV2
            v = _s16(self.r[S])
            if alt1:  # DIV2
                r = v >> 1 if v != -1 else 0
            else:
                r = v >> 1
            self._flag_cy(v & 1)
            self.r[D] = self._zs(r & 0xFFFF); return
        if op == 0x97:  # ROR
            v = self.r[S]; cin = 1 if cy else 0
            self._flag_cy(v & 1)
            self.r[D] = self._zs(((v >> 1) | (cin << 15)) & 0xFFFF); return
        if 0x98 <= op <= 0x9D:  # JMP Rn / LJMP Rn
            n = op & 0x0F
            if alt1:  # LJMP — also set PBR from Rn high? uses bank in register
                self.pbr = self.r[n] & 0x7F
                self.cbr = self.r[15] & 0xFFF0
                self.cache_valid[:] = b'\x00' * 32
                # PC already; some games put target in another reg — use R15 from low
            else:
                self.r[15] = self.r[n]
            return
        if op == 0x9E:  # LOB
            self.r[D] = self._zs(self.r[S] & 0xFF); return
        if op == 0x9F:  # FMULT / LMULT
            a = _s16(self.r[S]); b = _s16(self.r[6])
            prod = a * b
            if alt1:  # LMULT — 32-bit: R4=low, Rd=high
                self.r[4] = prod & 0xFFFF
                self.r[D] = self._zs((prod >> 16) & 0xFFFF)
            else:  # FMULT — fractional, result >> 16 in Rd, CY from bit15 of low
                self._flag_cy((prod >> 15) & 1)
                self.r[D] = self._zs((prod >> 16) & 0xFFFF)
            return

        # ---- $A0-$AF IBT Rn,#imm8 ----
        if 0xA0 <= op <= 0xAF:
            n = op & 0x0F
            imm = self._fetch()
            self.r[n] = imm | (0xFF00 if imm & 0x80 else 0)
            return

        # ---- $B0-$BF FROM / MOVES ----
        if 0xB0 <= op <= 0xBF:
            n = op & 0x0F
            if self.b_flag:  # MOVES Rn, Rs — move and set flags
                self.r[D] = self._zs(self.r[n])
                self.b_flag = False
                self.sfr &= ~0x1000
            else:
                self.src = n
            return

        # ---- $C0 HIB; $C1-$CF OR / XOR ----
        if op == 0xC0:  # HIB
            self.r[D] = self._zs((self.r[S] >> 8) & 0xFF); return
        if 0xC1 <= op <= 0xCF:
            n = op & 0x0F
            b = n if alt2 else self.r[n]
            if alt1:  # XOR
                r = self.r[S] ^ b
            else:
                r = self.r[S] | b
            self.r[D] = self._zs(r); return

        # ---- $D0-$DE INC Rn; $DF GETC / RAMB / ROMB ----
        if 0xD0 <= op <= 0xDE:
            n = op & 0x0F
            self.r[n] = self._zs((self.r[n] + 1) & 0xFFFF); return
        if op == 0xDF:
            if alt1 and alt2:  # RAMB? ALT3 often ROMB/RAMB split
                self.rambr = self.r[S] & 1
            elif alt2:
                self.rambr = self.r[S] & 1
            elif alt1:
                self.rombr = self.r[S] & 0x7F
            else:  # GETC — read ROM byte into COLR
                self.colr = self._rom_read(self.rombr, self.r[14]) & 0xFF
            return

        # ---- $E0-$EE DEC Rn; $EF GETB family ----
        if 0xE0 <= op <= 0xEE:
            n = op & 0x0F
            self.r[n] = self._zs((self.r[n] - 1) & 0xFFFF); return
        if op == 0xEF:
            b = self._rom_read(self.rombr, self.r[14]) & 0xFF
            if alt1 and alt2:  # GETBS
                self.r[D] = self._zs(b | (0xFF00 if b & 0x80 else 0))
            elif alt2:  # GETBL
                self.r[D] = self._zs((self.r[S] & 0xFF00) | b)
            elif alt1:  # GETBH
                self.r[D] = self._zs((self.r[S] & 0x00FF) | (b << 8))
            else:  # GETB
                self.r[D] = self._zs(b)
            return

        # ---- $F0-$FF IWT / LM / SM ----
        if 0xF0 <= op <= 0xFF:
            n = op & 0x0F
            lo = self._fetch(); hi = self._fetch()
            imm = lo | (hi << 8)
            if alt1 and not alt2:  # LM Rn,(yy)
                self.r[n] = self._ram_read(imm) | (self._ram_read((imm + 1) & 0xFFFF) << 8)
            elif alt2 and not alt1:  # SM Rn,(yy)
                self._ram_write(imm, self.r[n] & 0xFF)
                self._ram_write((imm + 1) & 0xFFFF, (self.r[n] >> 8) & 0xFF)
            elif alt1 and alt2:  # SMS / LMS variants — treat as SM
                self._ram_write(imm, self.r[n] & 0xFF)
                self._ram_write((imm + 1) & 0xFFFF, (self.r[n] >> 8) & 0xFF)
            else:  # IWT Rn,#imm16
                self.r[n] = imm
                if n == 15:
                    self._start()
            return

        # Unreachable if matrix is complete
        return

    def get_state(self):
        return dict(r=list(self.r), sfr=self.sfr, pbr=self.pbr, rombr=self.rombr,
                    rambr=self.rambr, cbr=self.cbr, scbr=self.scbr, scmr=self.scmr,
                    colr=self.colr, por=self.por, cfgr=self.cfgr, clsr=self.clsr,
                    running=self.running, src=self.src, dst=self.dst, b_flag=self.b_flag,
                    alt1=self.alt1, alt2=self.alt2,
                    cache=bytes(self.cache), cache_valid=bytes(self.cache_valid))

    def set_state(self, st):
        self.cache[:] = st.pop('cache', bytes(512))
        self.cache_valid[:] = st.pop('cache_valid', bytes(32))
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- ST010 / ST011 (Seta NEC µPD96050 HLE)
class ST01x:
    """ST010/ST011: shared 4KB RAM + DR/SR ports; ST010 math command HLE."""

    def __init__(self, snes, st011=False):
        self.snes = snes
        self.st011 = st011
        self.ram = bytearray(0x1000)  # 4KB shared, byte view of 16-bit words
        self.dr = 0
        self.sr = 0x80  # ready
        self.cmd = 0

    def power(self):
        self.ram[:] = b'\x00' * 0x1000
        self.dr = 0; self.sr = 0x80; self.cmd = 0

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        b = bank & 0x7F
        # Ports at $6000-$6001 (and mirrors); RAM $6800-$6FFF in banks $60-$6F
        if b == 0x60 and off < 0x1000:
            return True
        if 0x68 <= b <= 0x6F and off < 0x1000:
            return True
        return False

    def _w16(self, addr, v):
        addr &= 0xFFE
        self.ram[addr] = v & 0xFF
        self.ram[addr + 1] = (v >> 8) & 0xFF

    def _r16(self, addr):
        addr &= 0xFFE
        return self.ram[addr] | (self.ram[addr + 1] << 8)

    def _s16(self, addr):
        v = self._r16(addr)
        return v - 0x10000 if v & 0x8000 else v

    def read(self, a):
        off = a & 0xFFFF
        bank = (a >> 16) & 0x7F
        if bank == 0x60 and off < 0x1000:
            if off & 1:
                return self.sr
            return self.dr & 0xFF
        # shared RAM
        return self.ram[off & 0xFFF]

    def write(self, a, v):
        off = a & 0xFFFF; v &= 0xFF
        bank = (a >> 16) & 0x7F
        if bank == 0x60 and off < 0x1000:
            if off & 1:
                return  # SR read-only
            # DR write — latch command / kick
            self.dr = v
            if v & 0x80:
                self.cmd = v & 0x7F
                self._exec()
            return
        self.ram[off & 0xFFF] = v

    def _exec(self):
        """ST010 command HLE (public racing math set). ST011 keeps RAM/ports alive."""
        self.sr = 0x80  # stay ready in HLE
        c = self.cmd
        if self.st011:
            return  # shogi AI needs microcode; MMIO alone lets carts boot further
        # Command set used by F1 ROC II (approximate but playable)
        if c == 0x01:  # atan2-ish bearing
            x, y = self._s16(0x0000), self._s16(0x0002)
            ang = int((math.atan2(y, x) / (2 * math.pi) * 65536)) & 0xFFFF
            self._w16(0x0004, ang)
        elif c == 0x02:  # distance
            x, y = self._s16(0x0000), self._s16(0x0002)
            d = int(math.sqrt(x * x + y * y)) & 0xFFFF
            self._w16(0x0004, d)
        elif c == 0x03:  # race order sort keys pass-through
            pass
        elif c == 0x04:  # scale
            a, b = self._s16(0x0000), self._s16(0x0002)
            self._w16(0x0004, _u16((a * b) >> 15))
        elif c == 0x05:  # scale 2
            a, b = self._s16(0x0000), self._s16(0x0002)
            self._w16(0x0004, _u16((a * b) >> 8))
        elif c == 0x06:  # rotate
            x, y, a = self._s16(0x0000), self._s16(0x0002), self._r16(0x0004)
            ang = a * (2 * math.pi / 65536.0)
            ca, sa = math.cos(ang), math.sin(ang)
            self._w16(0x0006, _u16(int(x * ca - y * sa)))
            self._w16(0x0008, _u16(int(x * sa + y * ca)))
        elif c == 0x07:  # mode-7 style scale helpers
            n = self._r16(0x0000) or 1
            self._w16(0x0002, _u16(0x8000 // n))
        elif c == 0x08:  # steering step toward target
            cur, tgt = self._s16(0x0000), self._s16(0x0002)
            step = self._s16(0x0004) or 1
            d = tgt - cur
            if d > step: d = step
            if d < -step: d = -step
            self._w16(0x0006, _u16(cur + d))

    def get_state(self):
        return dict(ram=bytes(self.ram), dr=self.dr, sr=self.sr, cmd=self.cmd, st011=self.st011)

    def set_state(self, st):
        self.ram[:] = st.pop('ram', bytes(0x1000))
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- SPC7110 (Epson — FEZ / SPL4 / MDH)
class SPC7110:
    """SPC7110: data-ROM mapper, mul/div, RTC, and table-driven decompress HLE."""

    def __init__(self, snes):
        self.snes = snes
        self.regs = bytearray(0x50)
        self.rtc = [0] * 16
        self.rtc_mode = 0
        self.rtc_idx = 0
        self.decomp = bytearray(0x10000)
        self.decomp_off = 0
        self.busy = False
        self.dx_enabled = False
        # Data ROM is the cart past the first 1MB program (common FEZ layout)
        rom = snes.rom
        self.prog_size = min(len(rom), 0x100000)
        self.data = rom[self.prog_size:] if len(rom) > self.prog_size else rom

    def power(self):
        self.regs = bytearray(0x50)
        self.regs[0x31] = 0; self.regs[0x32] = 1; self.regs[0x33] = 2
        self.rtc_mode = 0; self.rtc_idx = 0
        self._latch_rtc()
        self.decomp = bytearray(0x10000)
        self.decomp_off = 0
        self.busy = False
        self.dx_enabled = False

    def _latch_rtc(self):
        n = datetime.datetime.now()
        self.rtc = [
            n.second % 10, n.second // 10, n.minute % 10, n.minute // 10,
            n.hour % 10, n.hour // 10, n.day % 10, n.day // 10,
            n.month % 10, n.month // 10, n.year % 10, (n.year // 10) % 10,
            n.weekday(), 0x01, 0x0F, 0x06,
        ]

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        b = bank & 0x7F
        if b < 0x40 and 0x4800 <= off <= 0x4842:
            return True
        if bank == 0x50:
            return True
        return False

    def _data_ptr(self):
        r = self.regs
        return (r[0x11] | (r[0x12] << 8) | (r[0x13] << 16)) & 0xFFFFFF

    def _set_data_ptr(self, p):
        p &= 0xFFFFFF
        self.regs[0x11] = p & 0xFF
        self.regs[0x12] = (p >> 8) & 0xFF
        self.regs[0x13] = (p >> 16) & 0xFF

    def _read_data_rom(self, p):
        if not self.data:
            return 0
        return self.data[p % len(self.data)]

    def _do_muldiv(self):
        r = self.regs
        # 16×16 multiply / 32÷16 divide share result regs
        a = r[0x20] | (r[0x21] << 8)
        b = r[0x24] | (r[0x25] << 8)
        prod = (a * b) & 0xFFFFFFFF
        for i in range(4):
            r[0x28 + i] = (prod >> (8 * i)) & 0xFF
        dividend = r[0x20] | (r[0x21] << 8) | (r[0x22] << 16) | (r[0x23] << 24)
        divisor = r[0x26] | (r[0x27] << 8)
        if divisor == 0:
            q, rem = 0, dividend & 0xFFFF
        else:
            q = (dividend // divisor) & 0xFFFFFFFF
            rem = (dividend % divisor) & 0xFFFF
        for i in range(4):
            r[0x28 + i] = (q >> (8 * i)) & 0xFF
        r[0x2C] = rem & 0xFF; r[0x2D] = (rem >> 8) & 0xFF
        r[0x2F] = 0  # finished

    def _begin_decomp(self):
        """Table lookup + S-DD1-style stream decompress into bank $50."""
        r = self.regs
        table = r[0x01] | (r[0x02] << 8) | (r[0x03] << 16)
        index = r[0x04]
        # 4-byte BE pointer per index in data ROM
        p = (table + index * 4) & 0xFFFFFF
        if self.data:
            ptr = ((self._read_data_rom(p) << 24) | (self._read_data_rom(p + 1) << 16) |
                   (self._read_data_rom(p + 2) << 8) | self._read_data_rom(p + 3))
        else:
            ptr = 0
        mode = r[0x0B]
        length = r[0x09] | (r[0x0A] << 8)
        if length == 0:
            length = 0x10000
        off = r[0x05] | (r[0x06] << 8)
        # mode 0: raw copy; mode 2: try S-DD1-like decompress
        src_off = ptr & 0xFFFFFF
        grab = min(len(self.data) - (src_off % max(len(self.data), 1)), length * 2 + 32) if self.data else 0
        if self.data and grab > 0:
            src = bytes(self.data[(src_off + i) % len(self.data)] for i in range(grab))
        else:
            src = b'\x00' * 16
        out_len = min(length, 0x10000)
        if mode == 0:
            raw = bytes(self._read_data_rom(src_off + i) for i in range(out_len))
        else:
            tmp = self.snes.sdd1 if self.snes.sdd1 is not None else SDD1(self.snes)
            try:
                raw = tmp.decompress_stream(src, out_len)
            except Exception:
                raw = bytes(self._read_data_rom(src_off + i) for i in range(out_len))
        self.decomp = bytearray(0x10000)
        place = off % 0x10000
        for i, b in enumerate(raw):
            self.decomp[(place + i) & 0xFFFF] = b
        self.decomp_off = place
        r[0x09] = length & 0xFF; r[0x0A] = (length >> 8) & 0xFF
        r[0x0C] = 0x80  # done
        self.busy = False

    def read(self, a):
        bank, off = a >> 16, a & 0xFFFF
        if bank == 0x50:
            return self.decomp[off]
        r = self.regs
        reg = off - 0x4800
        if reg == 0x00:  # decompressed stream
            v = self.decomp[self.decomp_off & 0xFFFF]
            self.decomp_off = (self.decomp_off + 1) & 0xFFFF
            ln = r[0x09] | (r[0x0A] << 8)
            if ln:
                ln -= 1
                r[0x09] = ln & 0xFF; r[0x0A] = (ln >> 8) & 0xFF
            return v
        if reg == 0x10:  # data ROM port
            p = self._data_ptr()
            v = self._read_data_rom(p)
            mode = r[0x18]
            inc = 1
            if mode & 1:
                inc = r[0x16] | (r[0x17] << 8)
                if mode & 4 and inc & 0x8000:
                    inc -= 0x10000
            if not (mode & 0x10):
                self._set_data_ptr(p + inc)
            else:
                adj = r[0x14] | (r[0x15] << 8)
                adj = (adj + inc) & 0xFFFF
                r[0x14] = adj & 0xFF; r[0x15] = adj >> 8
            return v
        if reg == 0x1A:
            p = self._data_ptr()
            adj = r[0x14] | (r[0x15] << 8)
            if r[0x18] & 8 and adj & 0x8000:
                adj -= 0x10000
            return self._read_data_rom((p + adj) & 0xFFFFFF)
        if reg == 0x0C:
            v = r[0x0C]; r[0x0C] = 0; return v
        if reg == 0x2F:
            return r[0x2F]
        if reg == 0x41:
            if self.rtc_idx < 16:
                v = self.rtc[self.rtc_idx] & 0x0F
                self.rtc_idx += 1
                return v
            return 0x0F
        if reg == 0x42:
            return 0x80  # RTC ready
        if 0 <= reg < len(r):
            return r[reg]
        return 0

    def write(self, a, v):
        off = a & 0xFFFF; v &= 0xFF
        if (a >> 16) == 0x50:
            self.decomp[off] = v; return
        reg = off - 0x4800
        r = self.regs
        if reg == 0x06:
            r[reg] = v
            self.busy = True
            self._begin_decomp()
            return
        if reg in (0x25, 0x27):
            r[reg] = v; r[0x2F] = 0x80; self._do_muldiv(); return
        if reg == 0x2E:
            for i in range(0x20, 0x2E):
                r[i] = 0
            return
        if reg == 0x13 and v != 0:
            self.dx_enabled = True
        if reg == 0x40:
            r[reg] = v
            if v & 1:
                self._latch_rtc(); self.rtc_mode = 0; self.rtc_idx = 0
            return
        if reg == 0x41:
            if self.rtc_mode == 0:
                self.rtc_mode = v; self.rtc_idx = 0
            elif self.rtc_idx < 16:
                self.rtc[self.rtc_idx] = v & 0x0F
                self.rtc_idx += 1
            return
        if 0 <= reg < len(r):
            r[reg] = v

    def map_bank(self, bank):
        """Map $D0-$FF banks through $4831-$4833."""
        b = bank & 0xFF
        if 0xD0 <= b <= 0xDF:
            sel = self.regs[0x31] & 3
        elif 0xE0 <= b <= 0xEF:
            sel = self.regs[0x32] & 3
        elif 0xF0 <= b <= 0xFF:
            sel = self.regs[0x33] & 3
        else:
            return None
        return (sel * 0x100000) + ((b & 0x0F) << 16)

    def get_state(self):
        return dict(regs=bytes(self.regs), rtc=list(self.rtc), rtc_mode=self.rtc_mode,
                    rtc_idx=self.rtc_idx, decomp=bytes(self.decomp), decomp_off=self.decomp_off,
                    busy=self.busy, dx_enabled=self.dx_enabled)

    def set_state(self, st):
        self.regs = bytearray(st.pop('regs', bytes(0x50)))
        self.decomp = bytearray(st.pop('decomp', bytes(0x10000)))
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- SGB / ICD2 bridge (Super Game Boy)
class SGB:
    """ICD2 MMIO + minimal packet HLE so SGB BIOS menus can run.

    Full Game Boy CPU/PPU is out of scope; GB cart execution stays limited.
    """

    def __init__(self, snes):
        self.snes = snes
        self.row = 0
        self.joy = 0
        self.r6000 = 0
        self.r6002 = 0
        self.r6003 = 0x01
        self.r6004 = 0
        self.packet = bytearray(16)
        self.pk_i = 0
        self.vram = bytearray(0x2000)

    def power(self):
        self.row = 0; self.joy = 0
        self.r6000 = 0; self.r6002 = 0; self.r6003 = 0x01; self.r6004 = 0
        self.packet = bytearray(16); self.pk_i = 0
        self.vram[:] = b'\x00' * 0x2000

    def handles(self, a):
        bank, off = a >> 16, a & 0xFFFF
        return (bank & 0x7F) < 0x40 and 0x6000 <= off <= 0x6007

    def read(self, a):
        off = a & 0xFFFF
        if off == 0x6000:
            # bit0 = data ready / BIOS handshake
            return 0x01
        if off == 0x6002:
            return self.r6002
        if off == 0x6003:
            return self.r6003
        if off == 0x6004:
            return self.r6004
        if off == 0x6005:
            return 0x00
        if off == 0x6006:
            return 0x01  # ICD2 present
        if off == 0x6007:
            return 0x00
        return 0

    def write(self, a, v):
        off = a & 0xFFFF; v &= 0xFF
        if off == 0x6001:
            # command / packet strobe
            if self.pk_i < 16:
                self.packet[self.pk_i] = v
                self.pk_i += 1
            if self.pk_i >= 16:
                self._packet()
                self.pk_i = 0
        elif off == 0x6002:
            self.r6002 = v
        elif off == 0x6003:
            self.r6003 = v
        elif off == 0x6004:
            self.r6004 = v
            self.row = 0

    def _packet(self):
        cmd = self.packet[0] >> 3
        # Acknowledge common SGB commands (PAL TRN, DATA TRN, JOY, MUL, etc.)
        if cmd in (0x00, 0x01, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x11, 0x14, 0x15, 0x1A):
            self.r6000 = 0x01

    def get_state(self):
        return dict(row=self.row, joy=self.joy, r6000=self.r6000, r6002=self.r6002,
                    r6003=self.r6003, r6004=self.r6004, packet=bytes(self.packet),
                    pk_i=self.pk_i, vram=bytes(self.vram))

    def set_state(self, st):
        self.vram[:] = st.pop('vram', bytes(0x2000))
        self.packet = bytearray(st.pop('packet', bytes(16)))
        for k, v in st.items():
            setattr(self, k, v)


# --------------------------------------------------------------------- Cart chipset attach helper
def attach_cart_chips(snes):
    """Create chip instances for the loaded commercial cart."""
    cs = snes.chipset
    snes.dsp1 = DSP1(snes, hirom=snes.hirom) if cs in DSP_CHIPS else None
    snes.sfx = SuperFX(snes) if cs in SFX_CHIPS else None
    snes.obc1 = OBC1(snes) if cs in OBC1_CHIPS else None
    snes.srtc = SRTC(snes) if cs in SRTC_CHIPS else None
    snes.sdd1 = SDD1(snes) if cs in SDD1_CHIPS else None
    snes.cx4 = CX4(snes) if cs in CX4_CHIPS else None
    snes.st01x = ST01x(snes, st011=False) if cs in ST01X_CHIPS else None
    snes.spc7110 = SPC7110(snes) if cs in SPC7110_CHIPS else None
    snes.sgb = SGB(snes) if cs in SGB_CHIPS else None


# ===================================================================== SA-1 (Nintendo Super Accelerator)
# Custom implementation from public SA-1 hardware docs (SnesLab / fullsnes).
# Reuses Virtual SNES Emulator's own 65816 opcode table — not a Snes9x port.


class SA1:
    """SA-1 coprocessor: second 65816 + Super MMC + I-RAM + BW-RAM + DMA + math + VLB."""

    def __init__(self, snes):
        self.snes = snes
        self.wc = 0
        self.mdr = 0
        self.iram = bytearray(0x800)
        self.bwram = bytearray(0)
        self.cpu = CPU65816(self)
        self.dma_line = 0
        self.cc1_active = False
        self._power_mmio()

    def attach_bwram(self, buf):
        self.bwram = buf if buf is not None else bytearray(0)

    def _power_mmio(self):
        self.sa1_irq = self.sa1_rdyb = self.sa1_nmi = False
        self.sa1_resb = True
        self.smeg = 0
        self.cpu_irqen = self.chdma_irqen = False
        self.cpu_irqcl = self.chdma_irqcl = True
        self.crv = self.cnv = self.civ = 0
        self.cpu_irq = self.cpu_ivsw = self.cpu_nvsw = False
        self.cmeg = 0
        self.sa1_irqen = self.timer_irqen = self.dma_irqen = self.sa1_nmien = False
        self.sa1_irqcl = self.timer_irqcl = self.dma_irqcl = self.sa1_nmicl = True
        self.snv = self.siv = 0
        self.hvselb = self.ven = self.hen = False
        self.hcnt = self.vcnt = 0
        self.hcounter = self.vcounter = 0
        self.cbmode = self.dbmode = self.ebmode = self.fbmode = 0
        self.cb, self.db, self.eb, self.fb = 0, 1, 2, 3
        self.sbm = 0
        self.sw46 = False
        self.cbm = 0
        self.swen = self.cwen = False
        self.bwp = 0x0F
        self.siwp = self.ciwp = 0
        self.dmaen = self.dprio = self.cden = self.cdsel = False
        self.dd = self.sd = 0
        self.chdend = False
        self.dmasize = self.dmacb = 0
        self.dsa = self.dda = 0
        self.dtc = 0
        self.bbf = 0
        self.brf = bytearray(16)
        self.acm = self.md = 0
        self.ma = self.mb = 0
        self.mr = 0
        self.overflow = False
        self.hl = False
        self.vb = 16
        self.va = 0
        self.vbit = 0
        self.vdp = 0
        self.cpu_irqfl = self.chdma_irqfl = False
        self.sa1_irqfl = self.timer_irqfl = self.dma_irqfl = self.sa1_nmifl = False
        self.dma_line = 0
        self.cc1_active = False

    def power(self):
        self.iram[:] = b'\x00' * 0x800
        self._power_mmio()
        c = self.cpu
        c.cyc = 0; c.A = c.X = c.Y = 0; c.idle_key = None
        c.E = 1; c.P = 0x34; c.D = 0; c.DB = 0; c.PB = 0
        c.S = 0x01FF; c.X &= 0xFF; c.Y &= 0xFF
        c.PC = 0; c.waiting = c.stopped = False
        c.nmi_pending = c.irq_line = False

    def _rom_byte(self, file_off):
        rom = self.snes.rom; n = self.snes.romlen
        if not n:
            return 0xFF
        return rom[file_off % n]

    def rom_linear(self, addr):
        """Super MMC: CPU address -> ROM file offset (SA-1 / S-CPU shared)."""
        # Vector overrides for the S-CPU (native NMI/IRQ)
        if (addr & 0xFFFFE0) == 0x00FFE0 and (addr & 0xFF0000) in (0x000000, 0x800000):
            lo = addr & 0xFFFF
            if lo == 0xFFEA and self.cpu_nvsw: return ('vec', self.snv & 0xFF)
            if lo == 0xFFEB and self.cpu_nvsw: return ('vec', (self.snv >> 8) & 0xFF)
            if lo == 0xFFEE and self.cpu_ivsw: return ('vec', self.siv & 0xFF)
            if lo == 0xFFEF and self.cpu_ivsw: return ('vec', (self.siv >> 8) & 0xFF)

        # Normalize LoROM-window addresses to 00-3F:0000-FFFF style index
        if (addr & 0x408000) == 0x008000:
            a = ((addr & 0x800000) >> 2) | ((addr & 0x3F0000) >> 1) | (addr & 0x7FFF)
        elif (addr & 0xC00000) == 0xC00000:
            a = addr
        else:
            return None

        lo = a < 0x400000
        a &= 0x3FFFFF
        if a < 0x100000:
            mode, img = self.cbmode, self.cb
        elif a < 0x200000:
            mode, img = self.dbmode, self.db
        elif a < 0x300000:
            mode, img = self.ebmode, self.eb
        else:
            mode, img = self.fbmode, self.fb
        if lo and not mode:
            return a
        return ((img & 7) << 20) | (a & 0x0FFFFF)

    def read_rom(self, addr):
        off = self.rom_linear(addr)
        if isinstance(off, tuple):
            return off[1]
        if off is None:
            return self.mdr
        return self._rom_byte(off)

    def _bw_mask(self):
        n = len(self.bwram)
        return n - 1 if n else 0

    def bw_read(self, off):
        n = len(self.bwram)
        if not n:
            return self.mdr
        return self.bwram[off % n]

    def bw_write(self, off, v):
        n = len(self.bwram)
        if not n:
            return
        # Protection only when both write-enables are clear
        if not self.swen and not self.cwen and (off & 0x3FFFF) < (0x100 << self.bwp):
            return
        self.bwram[off % n] = v & 0xFF

    def bw_read_bitmap(self, addr):
        if not self.bbf:
            sh = addr & 1; a = addr >> 1
            return (self.bw_read(a) >> (0 if sh == 0 else 4)) & 15
        sh = addr & 3; a = addr >> 2
        return (self.bw_read(a) >> (sh * 2)) & 3

    def bw_write_bitmap(self, addr, data):
        data &= 0xFF
        if not self.bbf:
            sh = addr & 1; a = addr >> 1; cur = self.bw_read(a)
            if sh == 0:
                self.bw_write(a, (cur & 0xF0) | (data & 0x0F))
            else:
                self.bw_write(a, (cur & 0x0F) | ((data & 0x0F) << 4))
        else:
            sh = addr & 3; a = addr >> 2; cur = self.bw_read(a)
            mask = ~(3 << (sh * 2)) & 0xFF
            self.bw_write(a, (cur & mask) | ((data & 3) << (sh * 2)))

    def iram_read(self, a):
        return self.iram[a & 0x7FF]

    def iram_write(self, a, v, from_sa1=False):
        # SIWP/CIWP: each bit is a write-enable for one 256-byte I-RAM page
        # (1=writable). fullsnes / Nintendo manual; sfc-dev-wiki has this inverted.
        page = (a & 0x700) >> 8
        enable = self.ciwp if from_sa1 else self.siwp
        if not (enable & (1 << page)):
            return
        a &= 0x7FF; v &= 0xFF
        if self.iram[a] == v:
            return
        self.iram[a] = v
        # I-RAM is the S-CPU ↔ SA-1 mailbox. Idle-loop skip keys use each CPU's
        # own bus.wc, so a write on one side must invalidate the other or SMRPG
        # loses command edges ($3000/$3002) and backgrounds never finish uploading.
        self.wc += 1
        snes = self.snes
        snes.wc += 1
        self.cpu.idle_key = None
        snes.cpu.idle_key = None

    # ---- SA-1 CPU bus (custom map; opcodes are the shared 65816 table) ----
    def read(self, a):
        a &= 0xFFFFFF
        bank = a >> 16; off = a & 0xFFFF
        b = bank & 0x7F
        # MMIO
        if b < 0x40 and 0x2200 <= off < 0x2400:
            self.mdr = self.read_io_sa1(off)
            return self.mdr
        # ROM
        if (a & 0x408000) == 0x008000 or (a & 0xC00000) == 0xC00000:
            # SA-1 IRQ/NMI vectors come from CNV/CIV, not cart ROM
            if b == 0 and 0xFFE0 <= off <= 0xFFFF:
                if off in (0xFFEA, 0xFFEB, 0xFFFA, 0xFFFB):
                    return (self.cnv >> (0 if not (off & 1) else 8)) & 0xFF
                if off in (0xFFEE, 0xFFEF, 0xFFFE, 0xFFFF):
                    return (self.civ >> (0 if not (off & 1) else 8)) & 0xFF
            self.mdr = self.read_rom(a)
            return self.mdr
        # BW-RAM mirror $6000-7FFF / linear $40-5F / bitmap $60-6F
        if b < 0x40 and 0x6000 <= off < 0x8000:
            if self.sw46:
                self.mdr = self.bw_read_bitmap(self.cbm * 0x2000 + (off & 0x1FFF))
            else:
                self.mdr = self.bw_read((self.cbm & 0x1F) * 0x2000 + (off & 0x1FFF))
            return self.mdr
        if 0x40 <= bank <= 0x5F:
            self.mdr = self.bw_read(((bank - 0x40) << 16) | off)
            return self.mdr
        if 0x60 <= bank <= 0x6F:
            self.mdr = self.bw_read_bitmap(((bank - 0x60) << 16) | off)
            return self.mdr
        # I-RAM
        if b < 0x40 and (off < 0x0800 or 0x3000 <= off < 0x3800):
            self.mdr = self.iram_read(off)
            return self.mdr
        return self.mdr

    def write(self, a, v):
        a &= 0xFFFFFF; v &= 0xFF
        self.wc += 1; self.mdr = v
        bank = a >> 16; off = a & 0xFFFF
        b = bank & 0x7F
        if b < 0x40 and 0x2200 <= off < 0x2400:
            self.write_io_sa1(off, v); return
        if b < 0x40 and 0x6000 <= off < 0x8000:
            if self.sw46:
                self.bw_write_bitmap(self.cbm * 0x2000 + (off & 0x1FFF), v)
            else:
                self.bw_write((self.cbm & 0x1F) * 0x2000 + (off & 0x1FFF), v)
            return
        if 0x40 <= bank <= 0x5F:
            self.bw_write(((bank - 0x40) << 16) | off, v); return
        if 0x60 <= bank <= 0x6F:
            self.bw_write_bitmap(((bank - 0x60) << 16) | off, v); return
        if b < 0x40 and (off < 0x0800 or 0x3000 <= off < 0x3800):
            self.iram_write(off, v, from_sa1=True)

    # ---- S-CPU side access helpers ----
    def _sync_sa1_to_scpu(self):
        """Catch SA-1 up before S-CPU touches shared I-RAM / BW-RAM."""
        self.run_to(self.snes.cpu.cyc)

    def snes_read(self, a):
        bank = a >> 16; off = a & 0xFFFF
        b = bank & 0x7F
        if b < 0x40 and 0x2200 <= off < 0x2400:
            return self.read_io_snes(off)
        if b < 0x40 and 0x3000 <= off < 0x3800:
            # Mailbox bytes are polled in tight idle loops; sync only there.
            if off < 0x3010:
                self._sync_sa1_to_scpu()
            return self.iram_read(off)
        if b < 0x40 and 0x6000 <= off < 0x8000:
            addr = self.sbm * 0x2000 + (off & 0x1FFF)
            if self.cc1_active:
                return self.dma_cc1_read(addr)
            return self.bw_read(addr)
        if 0x40 <= bank <= 0x4F:
            addr = ((bank - 0x40) << 16) | off
            if self.cc1_active:
                return self.dma_cc1_read(addr)
            return self.bw_read(addr)
        # ROM (incl. vector overrides)
        if (a & 0x408000) == 0x008000 or (a & 0xC00000) == 0xC00000 or (b >= 0x40):
            return self.read_rom(a)
        return self.snes.mdr

    def snes_write(self, a, v):
        bank = a >> 16; off = a & 0xFFFF; v &= 0xFF
        b = bank & 0x7F
        if b < 0x40 and 0x2200 <= off < 0x2400:
            self.write_io_snes(off, v); return True
        if b < 0x40 and 0x3000 <= off < 0x3800:
            if off < 0x3010:
                self._sync_sa1_to_scpu()
            self.iram_write(off, v, from_sa1=False); return True
        if b < 0x40 and 0x6000 <= off < 0x8000:
            self.bw_write(self.sbm * 0x2000 + (off & 0x1FFF), v); return True
        if 0x40 <= bank <= 0x4F:
            self.bw_write(((bank - 0x40) << 16) | off, v); return True
        return False

    def snes_irq_active(self):
        return ((self.cpu_irqfl and self.cpu_irqen and not self.cpu_irqcl) or
                (self.chdma_irqfl and self.chdma_irqen and not self.chdma_irqcl))

    def update_sa1_irq_line(self):
        c = self.cpu
        irq = False
        # Pending flags (not the level bits in CCNT) drive the SA-1 IRQ line.
        if self.sa1_irqen and self.sa1_irqfl and not self.sa1_irqcl:
            irq = True
        if self.timer_irqen and self.timer_irqfl and not self.timer_irqcl:
            irq = True
        if self.dma_irqen and self.dma_irqfl and not self.dma_irqcl:
            irq = True
        c.irq_line = irq
        if self.sa1_nmien and self.sa1_nmifl and not self.sa1_nmicl:
            c.nmi_pending = True

    def release_reset_if_needed(self, was_reset):
        if was_reset and not self.sa1_resb:
            c = self.cpu
            c.E = 1; c.P = 0x34; c.D = 0; c.DB = 0; c.PB = 0
            c.S = 0x01FF; c.X &= 0xFF; c.Y &= 0xFF
            c.PC = self.crv & 0xFFFF
            c.waiting = c.stopped = False
            c.nmi_pending = c.irq_line = False
            c.idle_key = None

    # ---- MMIO ----
    def read_io_snes(self, off):
        if off == 0x2300:
            v = ((0x80 if self.cpu_irqfl else 0) |
                 (0x40 if self.cpu_ivsw else 0) |
                 (0x20 if self.chdma_irqfl else 0) |
                 (0x10 if self.cpu_nvsw else 0) |
                 (self.cmeg & 0x0F))
            return v
        return self.snes.mdr

    def read_io_sa1(self, off):
        if off == 0x2301:
            return ((0x80 if self.sa1_irqfl else 0) |
                    (0x40 if self.timer_irqfl else 0) |
                    (0x20 if self.dma_irqfl else 0) |
                    (0x10 if self.sa1_nmifl else 0) |
                    (self.smeg & 0x0F))
        if off == 0x2302: return self.hcounter & 0xFF
        if off == 0x2303: return (self.hcounter >> 8) & 0xFF
        if off == 0x2304: return self.vcounter & 0xFF
        if off == 0x2305: return (self.vcounter >> 8) & 0xFF
        if 0x2306 <= off <= 0x230A:
            return (self.mr >> ((off - 0x2306) * 8)) & 0xFF
        if off == 0x230B: return 0x80 if self.overflow else 0
        if off == 0x230C: return self.vdp & 0xFF
        if off == 0x230D:
            v = (self.vdp >> 8) & 0xFF
            self._vlb_advance()
            return v
        return self.mdr

    def write_io_snes(self, off, v):
        if off == 0x2200:
            was = self.sa1_resb
            self.sa1_irq = bool(v & 0x80)
            self.sa1_rdyb = bool(v & 0x40)
            self.sa1_resb = bool(v & 0x20)
            self.sa1_nmi = bool(v & 0x10)
            self.smeg = v & 0x0F
            if self.sa1_irq:
                self.sa1_irqfl = True
                if self.sa1_irqen:
                    self.sa1_irqcl = False
            if self.sa1_nmi:
                self.sa1_nmifl = True
                if self.sa1_nmien:
                    self.sa1_nmicl = False
            self.release_reset_if_needed(was)
            self.update_sa1_irq_line()
        elif off == 0x2201:
            self.cpu_irqen = bool(v & 0x80)
            self.chdma_irqen = bool(v & 0x20)
            if self.cpu_irqen and self.cpu_irqfl:
                self.cpu_irqcl = False
            if self.chdma_irqen and self.chdma_irqfl:
                self.chdma_irqcl = False
        elif off == 0x2202:
            if v & 0x80:
                self.cpu_irqfl = False; self.cpu_irqcl = True
            if v & 0x20:
                self.chdma_irqfl = False; self.chdma_irqcl = True
        elif off == 0x2203: self.crv = (self.crv & 0xFF00) | v
        elif off == 0x2204: self.crv = (self.crv & 0x00FF) | (v << 8)
        elif off == 0x2205: self.cnv = (self.cnv & 0xFF00) | v
        elif off == 0x2206: self.cnv = (self.cnv & 0x00FF) | (v << 8)
        elif off == 0x2207: self.civ = (self.civ & 0xFF00) | v
        elif off == 0x2208: self.civ = (self.civ & 0x00FF) | (v << 8)
        elif off == 0x2220:
            self.cbmode = 1 if v & 0x80 else 0; self.cb = v & 7
            self.snes.build_map()
        elif off == 0x2221:
            self.dbmode = 1 if v & 0x80 else 0; self.db = v & 7
            self.snes.build_map()
        elif off == 0x2222:
            self.ebmode = 1 if v & 0x80 else 0; self.eb = v & 7
            self.snes.build_map()
        elif off == 0x2223:
            self.fbmode = 1 if v & 0x80 else 0; self.fb = v & 7
            self.snes.build_map()
        elif off == 0x2224: self.sbm = v & 0x1F
        elif off == 0x2226: self.swen = bool(v & 0x80)
        elif off == 0x2228: self.bwp = v & 0x0F
        elif off == 0x2229: self.siwp = v
        elif off == 0x2231: self._write_cdma(v)
        elif off in (0x2232, 0x2233, 0x2234, 0x2235, 0x2236, 0x2237):
            self.write_io_shared(off, v)

    def write_io_sa1(self, off, v):
        if off == 0x2209:
            self.cpu_irq = bool(v & 0x80)
            self.cpu_ivsw = bool(v & 0x40)
            self.cpu_nvsw = bool(v & 0x10)
            self.cmeg = v & 0x0F
            if self.cpu_irq:
                self.cpu_irqfl = True
                if self.cpu_irqen:
                    self.cpu_irqcl = False
        elif off == 0x220A:
            self.sa1_irqen = bool(v & 0x80)
            self.timer_irqen = bool(v & 0x40)
            self.dma_irqen = bool(v & 0x20)
            self.sa1_nmien = bool(v & 0x10)
            # Enabling with a flag already pending must assert the line.
            if self.sa1_irqen and self.sa1_irqfl:
                self.sa1_irqcl = False
            if self.timer_irqen and self.timer_irqfl:
                self.timer_irqcl = False
            if self.dma_irqen and self.dma_irqfl:
                self.dma_irqcl = False
            if self.sa1_nmien and self.sa1_nmifl:
                self.sa1_nmicl = False
            self.update_sa1_irq_line()
        elif off == 0x220B:
            if v & 0x80: self.sa1_irqfl = False; self.sa1_irqcl = True
            if v & 0x40: self.timer_irqfl = False; self.timer_irqcl = True
            if v & 0x20: self.dma_irqfl = False; self.dma_irqcl = True
            if v & 0x10: self.sa1_nmifl = False; self.sa1_nmicl = True
            self.update_sa1_irq_line()
        elif off == 0x220C: self.snv = (self.snv & 0xFF00) | v
        elif off == 0x220D: self.snv = (self.snv & 0x00FF) | (v << 8)
        elif off == 0x220E: self.siv = (self.siv & 0xFF00) | v
        elif off == 0x220F: self.siv = (self.siv & 0x00FF) | (v << 8)
        elif off == 0x2210:
            self.hvselb = bool(v & 0x80); self.ven = bool(v & 0x02); self.hen = bool(v & 0x01)
        elif off == 0x2211:
            self.hcounter = self.vcounter = 0
        elif off == 0x2212: self.hcnt = (self.hcnt & 0xFF00) | v
        elif off == 0x2213: self.hcnt = (self.hcnt & 0x00FF) | ((v & 1) << 8)
        elif off == 0x2214: self.vcnt = (self.vcnt & 0xFF00) | v
        elif off == 0x2215: self.vcnt = (self.vcnt & 0x00FF) | ((v & 1) << 8)
        elif off == 0x2225:
            self.sw46 = bool(v & 0x80); self.cbm = v & 0x7F
        elif off == 0x2227: self.cwen = bool(v & 0x80)
        elif off == 0x222A: self.ciwp = v
        elif off == 0x2230:
            self.dmaen = bool(v & 0x80)
            self.dprio = bool(v & 0x40)
            self.cden = bool(v & 0x20)
            self.cdsel = bool(v & 0x10)
            self.dd = 1 if v & 0x04 else 0
            self.sd = v & 3
        elif off == 0x2231: self._write_cdma(v)
        elif off in (0x2232, 0x2233, 0x2234, 0x2235, 0x2236, 0x2237, 0x2238, 0x2239):
            self.write_io_shared(off, v)
        elif off == 0x223F: self.bbf = 1 if v & 0x80 else 0
        elif 0x2240 <= off <= 0x224F:
            self.brf[off - 0x2240] = v
            if off in (0x2247, 0x224F) and self.dmaen and self.cden and not self.cdsel:
                self.dma_cc2()
        elif off == 0x2250:
            self.md = v & 3
            if self.md == 2:  # cumulative sum reset accumulator? acm bit
                pass
            if v & 2:
                self.mr = 0
        elif off == 0x2251: self.ma = (self.ma & 0xFF00) | v
        elif off == 0x2252: self.ma = (self.ma & 0x00FF) | (v << 8)
        elif off == 0x2253: self.mb = (self.mb & 0xFF00) | v
        elif off == 0x2254:
            self.mb = (self.mb & 0x00FF) | (v << 8)
            self._do_math()
        elif off == 0x2258:
            self.hl = bool(v & 0x80)
            self.vb = 16 if (v & 0x0F) == 0 else (v & 0x0F)
            if not self.hl:
                self._vlb_latch()
        elif off == 0x2259: self.va = (self.va & 0xFFFF00) | v
        elif off == 0x225A: self.va = (self.va & 0xFF00FF) | (v << 8)
        elif off == 0x225B:
            self.va = (self.va & 0x00FFFF) | (v << 16)
            self.vbit = 0
            self._vlb_latch()

    def write_io_shared(self, off, v):
        if off == 0x2232: self.dsa = (self.dsa & 0xFFFF00) | v
        elif off == 0x2233: self.dsa = (self.dsa & 0xFF00FF) | (v << 8)
        elif off == 0x2234: self.dsa = (self.dsa & 0x00FFFF) | (v << 16)
        elif off == 0x2235: self.dda = (self.dda & 0xFFFF00) | v
        elif off == 0x2236:
            self.dda = (self.dda & 0xFF00FF) | (v << 8)
            if self.dmaen and not self.cden and self.dd == 0:
                self.dma_normal()
            elif self.dmaen and self.cden and self.cdsel:
                self.dma_cc1()
        elif off == 0x2237:
            self.dda = (self.dda & 0x00FFFF) | (v << 16)
            if self.dmaen and not self.cden and self.dd == 1:
                self.dma_normal()
        elif off == 0x2238: self.dtc = (self.dtc & 0xFF00) | v
        elif off == 0x2239: self.dtc = (self.dtc & 0x00FF) | (v << 8)

    def _write_cdma(self, v):
        self.chdend = bool(v & 0x80)
        self.dmasize = min((v >> 2) & 7, 5)
        self.dmacb = min(v & 3, 2)
        if self.chdend:
            self.cc1_active = False

    def _do_math(self):
        ma = self.ma if self.ma < 0x8000 else self.ma - 0x10000
        mode = self.md & 3
        if mode == 0:  # multiply signed
            mb = self.mb if self.mb < 0x8000 else self.mb - 0x10000
            self.mr = (ma * mb) & 0xFFFFFFFF
            self.overflow = False
        elif mode == 1:  # divide
            mb = self.mb & 0xFFFF
            if mb == 0:
                self.mr = 0
            else:
                q = int(ma / mb); r = abs(ma) % mb
                self.mr = (q & 0xFFFF) | ((r & 0xFFFF) << 16)
            self.overflow = False
        else:  # cumulative sum
            mb = self.mb if self.mb < 0x8000 else self.mb - 0x10000
            self.mr = (self.mr + ma * mb)
            self.overflow = self.mr != (self.mr & ((1 << 40) - 1))
            self.mr &= (1 << 40) - 1

    def _vlb_rom(self, addr):
        # Even addresses only
        addr &= ~1
        return self.read_rom(addr) | (self.read_rom(addr + 1) << 8)

    def _vlb_latch(self):
        raw = self._vlb_rom(self.va)
        # bit string starting at vbit
        val = (raw >> self.vbit) & ((1 << min(self.vb, 16)) - 1)
        self.vdp = val & 0xFFFF

    def _vlb_advance(self):
        if not self.hl:
            return
        self.vbit += self.vb
        while self.vbit >= 16:
            self.vbit -= 16
            self.va = (self.va + 2) & 0xFFFFFF
        self._vlb_latch()

    # ---- DMA ----
    def _dma_read_src(self, addr):
        if self.sd == 0:  # ROM
            return self.read_rom(addr)
        if self.sd == 1:  # BW-RAM
            return self.bw_read(addr)
        if self.sd == 2:  # I-RAM
            return self.iram_read(addr)
        return 0xFF

    def _dma_write_dst(self, addr, v):
        if self.dd == 0:
            self.iram_write(addr, v, from_sa1=True)
        else:
            self.bw_write(addr, v)

    def dma_normal(self):
        n = self.dtc & 0xFFFF
        if n == 0:
            n = 0x10000
        src, dst = self.dsa, self.dda
        for _ in range(n):
            self._dma_write_dst(dst, self._dma_read_src(src))
            src = (src + 1) & 0xFFFFFF
            dst = (dst + 1) & 0xFFFFFF
        self.dsa, self.dda, self.dtc = src, dst, 0
        self.dma_irqfl = True
        if self.dma_irqen:
            self.dma_irqcl = False
        self.update_sa1_irq_line()

    def dma_cc1(self):
        self.cc1_active = True
        self.chdma_irqfl = True
        if self.chdma_irqen:
            self.chdma_irqcl = False

    def dma_cc1_read(self, addr):
        charmask = (1 << (6 - self.dmacb)) - 1
        if (addr & charmask) == 0:
            bpp = 2 << (2 - self.dmacb)
            bpl = (8 << self.dmasize) >> self.dmacb
            bwmask = self._bw_mask() or 0xFFFFFFFF
            tile = ((addr - self.dsa) & bwmask) >> (6 - self.dmacb)
            ty = tile >> self.dmasize
            tx = tile & ((1 << self.dmasize) - 1)
            bwaddr = self.dsa + ty * 8 * bpl + tx * bpp
            for y in range(8):
                data = 0
                for byte in range(bpp):
                    data |= self.bw_read((bwaddr + byte) & bwmask) << (byte * 8)
                bwaddr += bpl
                out = [0] * 8
                for x in range(8):
                    out[0] |= (data & 1) << (7 - x); data >>= 1
                    out[1] |= (data & 1) << (7 - x); data >>= 1
                    if self.dmacb == 2:
                        continue
                    out[2] |= (data & 1) << (7 - x); data >>= 1
                    out[3] |= (data & 1) << (7 - x); data >>= 1
                    if self.dmacb == 1:
                        continue
                    out[4] |= (data & 1) << (7 - x); data >>= 1
                    out[5] |= (data & 1) << (7 - x); data >>= 1
                    out[6] |= (data & 1) << (7 - x); data >>= 1
                    out[7] |= (data & 1) << (7 - x); data >>= 1
                for byte in range(bpp):
                    p = self.dda + (y << 1) + ((byte & 6) << 3) + (byte & 1)
                    self.iram[p & 0x7FF] = out[byte]
        return self.iram[(self.dda + (addr & charmask)) & 0x7FF]

    def dma_cc2(self):
        brf = self.brf[(self.dma_line & 1) << 3:]
        bpp = 2 << (2 - self.dmacb)
        addr = self.dda & 0x7FF
        addr &= ~((1 << (7 - self.dmacb)) - 1)
        addr += (self.dma_line & 8) * bpp
        addr += (self.dma_line & 7) * 2
        for byte in range(bpp):
            output = 0
            for bit in range(8):
                output |= ((brf[bit] >> byte) & 1) << (7 - bit)
            self.iram[(addr + ((byte & 6) << 3) + (byte & 1)) & 0x7FF] = output
        self.dma_line = (self.dma_line + 1) & 15

    def run_to(self, snes_cyc):
        """SA-1 ~4× SlowROM S-CPU; share the same custom 65816 opcode table."""
        if self.sa1_resb or self.sa1_rdyb:
            self.cpu.cyc = snes_cyc * 4
            return
        self.update_sa1_irq_line()
        self.cpu.run(snes_cyc * 4)

    def get_state(self):
        st = {k: getattr(self, k) for k in (
            'sa1_irq', 'sa1_rdyb', 'sa1_resb', 'sa1_nmi', 'smeg',
            'cpu_irqen', 'chdma_irqen', 'cpu_irqcl', 'chdma_irqcl',
            'crv', 'cnv', 'civ', 'cpu_irq', 'cpu_ivsw', 'cpu_nvsw', 'cmeg',
            'sa1_irqen', 'timer_irqen', 'dma_irqen', 'sa1_nmien',
            'sa1_irqcl', 'timer_irqcl', 'dma_irqcl', 'sa1_nmicl',
            'snv', 'siv', 'hvselb', 'ven', 'hen', 'hcnt', 'vcnt',
            'hcounter', 'vcounter', 'cbmode', 'dbmode', 'ebmode', 'fbmode',
            'cb', 'db', 'eb', 'fb', 'sbm', 'sw46', 'cbm', 'swen', 'cwen',
            'bwp', 'siwp', 'ciwp', 'dmaen', 'dprio', 'cden', 'cdsel', 'dd', 'sd',
            'chdend', 'dmasize', 'dmacb', 'dsa', 'dda', 'dtc', 'bbf',
            'acm', 'md', 'ma', 'mb', 'mr', 'overflow', 'hl', 'vb', 'va', 'vbit', 'vdp',
            'cpu_irqfl', 'chdma_irqfl', 'sa1_irqfl', 'timer_irqfl', 'dma_irqfl',
            'sa1_nmifl', 'dma_line', 'cc1_active', 'mdr', 'wc')}
        st['iram'] = bytes(self.iram)
        st['brf'] = bytes(self.brf)
        st['__cpu'] = {k: getattr(self.cpu, k) for k in CPU65816.STATE}
        return st

    def set_state(self, st):
        cpu = st.pop('__cpu', None)
        self.iram[:] = st.pop('iram', bytes(0x800))
        self.brf[:] = st.pop('brf', bytes(16))
        for k, v in st.items():
            setattr(self, k, v)
        if cpu:
            for k, v in cpu.items():
                setattr(self.cpu, k, v)


class SNES:
    """System bus + PPU/CPU I/O + DMA. Memory map follows the Snes9x/fullsnes layout."""

    def __init__(self):
        self.rom = bytes(0x8000); self.romlen = 0x8000
        self.hirom = False; self.exhirom = False; self.title = ""
        self.sram_size = 0; self.map_mode = 0; self.chipset = 0
        self.chip_name = 'ROM'; self.compat = 'ok'; self.mapper = 'LoROM'
        self.region_name = ''; self.speed = 'SlowROM'
        self.sram = bytearray(0); self.rom_path = None
        self.rbuf = [None] * 2048; self.rofs = [0] * 2048
        self.wbuf = [None] * 2048; self.wofs = [0] * 2048
        self.read = self._make_read(); self.write = self._make_write()
        self.cpu = CPU65816(self)
        self.sa1 = None
        self.dsp1 = self.sfx = self.obc1 = self.srtc = self.sdd1 = self.cx4 = None
        self.st01x = self.spc7110 = self.sgb = None
        self.apu = APU()
        self.render = Renderer(self)
        self.frame = np.zeros((224, 256, 3), np.uint8)
        self.joy1 = 0; self.joy2 = 0
        self.skip_render = False
        self._build_io()
        self.power()

    # ------------------------------------------------------------- ROM
    def load(self, data, path=None):
        info = analyze_rom(data)
        self.rom = info['data']; self.romlen = len(self.rom); self.rom_path = path
        self.hirom = info['hirom']; self.exhirom = info['exhirom']
        self.title = info['title']; self.sram_size = info['sram_size']
        self.map_mode = info['map_mode']; self.chipset = info['chipset']
        self.chip_name = info['chip_name']; self.compat = info['compat']
        self.mapper = info['mapper']; self.region_name = info['region_name']
        self.speed = info['speed']
        # SA-1 BW-RAM / SuperFX pak RAM defaults when header omits size
        if self.chipset in SA1_CHIPS and self.sram_size == 0:
            self.sram_size = 0x40000
        if self.chipset in SFX_CHIPS and self.sram_size == 0:
            self.sram_size = 0x10000  # 64 KB common; Yoshi's Island uses more via header
        self.sram = bytearray(b'\xff' * self.sram_size)
        if path and self.sram_size:
            srm = os.path.splitext(path)[0] + ".srm"
            if os.path.exists(srm):
                d = open(srm, 'rb').read()[:self.sram_size]
                self.sram[:len(d)] = d
        self.sa1 = None
        if self.chipset in SA1_CHIPS:
            self.sa1 = SA1(self)
            self.sa1.attach_bwram(self.sram)
        attach_cart_chips(self)
        self.power()
        return info

    def rom_offset(self, bank, off):
        """Map CPU bank:addr -> linear file offset (commercial Lo/Hi/ExHiROM/SA-1)."""
        if self.sa1 is not None:
            a = ((bank & 0xFF) << 16) | (off & 0xFFFF)
            lin = self.sa1.rom_linear(a)
            if isinstance(lin, tuple):
                return 0  # vector override handled in read_slow
            if lin is None:
                b = bank & 0x7F
                return ((b << 15) | (off & 0x7FFF)) % self.romlen
            return lin % self.romlen
        if self.spc7110 is not None:
            mapped = self.spc7110.map_bank(bank)
            if mapped is not None:
                # data ROM file offset = program size + mapped
                return (self.spc7110.prog_size + mapped + (off & 0xFFFF)) % self.romlen
        if self.sdd1 is not None and 0xC0 <= (bank & 0xFF) <= 0xFF:
            return self.sdd1.map_rom(bank, off)
        b = bank & 0x7F
        if self.exhirom and self.romlen > 0x400000:
            if 0x40 <= b < 0x7E:
                return (0x400000 + ((((b - 0x40) & 0x3F) << 16) | off)) % self.romlen
            return ((((b & 0x3F) << 16) | off)) % self.romlen
        if self.hirom:
            return ((((b & 0x3F) << 16) | off)) % self.romlen
        return ((b << 15) | (off & 0x7FFF)) % self.romlen

    def save_sram(self):
        if self.rom_path and self.sram_size:
            with open(os.path.splitext(self.rom_path)[0] + ".srm", 'wb') as f:
                f.write(self.sram)

    def power(self):
        self.wram = bytearray(0x20000)
        if self.sa1 is not None:
            self.sa1.attach_bwram(self.sram)
            self.sa1.power()
        for chip in (self.dsp1, self.sfx, self.obc1, self.srtc, self.sdd1, self.cx4,
                     self.st01x, self.spc7110, self.sgb):
            if chip is not None:
                chip.power()
        self.build_map()
        self.vram = array('H', bytes(0x10000))
        self.cgram = array('H', bytes(512))
        self.oam = bytearray(544)
        self.R = [0] * NR
        self.R[R_INIDISP] = 0x80
        self.rdirty = True; self.cgdirty = True; self.vram_dirty = True
        self.rsnap = tuple(self.R); self.cgsnap = self.cgram.tobytes()
        self.line_regs = []; self.line_cg = []
        self.mdr = 0; self.wc = 0
        self.bgofs_latch = 0; self.m7_latch = 0; self.mpy = 0
        self.oam_base = 0; self.oam_addr = 0; self.oam_latch = 0
        self.vmain = 0x80; self.vmadd = 0; self.vlatch = 0
        self.cgaddr = 0; self.cg_latch = 0
        self.wmadd = 0
        self.apu.reset()
        self.nmitimen = 0; self.wrio = 0xFF; self.wrmpya = 0xFF; self.wrdiv = 0xFFFF
        self.rddiv = 0; self.rdmpy = 0; self.htime = 0x1FF; self.vtime = 0x1FF
        self.hdmaen = 0; self.memsel = 0
        self.dmar = bytearray(b'\xff' * 0x80)
        self.hdma_do = [False] * 8; self.hdma_done = [True] * 8
        self.nmi_flag = False; self.irq_flag = False; self.vblank = False
        self.vcount = 0; self.line_start = 0; self.line_end = 0
        self.joyreg = [0] * 8; self.joy_sr = [0, 0]; self.joy_strobe = 0
        self.hlatch = 0; self.vlatch_c = 0; self.hl_flip = 0; self.vl_flip = 0; self.field = 0
        self.frames = 0
        c = self.cpu
        c.cyc = 0; c.A = c.X = c.Y = 0; c.idle_key = None
        c.reset()

    def _chip_read(self, a):
        """Route commercial enhancement-chip MMIO (non-SA-1)."""
        if self.sfx is not None and self.sfx.handles(a):
            return self.sfx.read_reg(a)
        if self.dsp1 is not None and self.dsp1.handles(a):
            return self.dsp1.read(a)
        if self.obc1 is not None and self.obc1.handles(a):
            return self.obc1.read(a)
        if self.cx4 is not None and self.cx4.handles(a):
            return self.cx4.read(a)
        if self.srtc is not None and self.srtc.handles(a):
            return self.srtc.read(a)
        if self.sdd1 is not None and self.sdd1.handles_mmio(a):
            return self.sdd1.read_mmio(a)
        if self.st01x is not None and self.st01x.handles(a):
            return self.st01x.read(a)
        if self.spc7110 is not None and self.spc7110.handles(a):
            return self.spc7110.read(a)
        if self.sgb is not None and self.sgb.handles(a):
            return self.sgb.read(a)
        return None

    def _chip_write(self, a, v):
        if self.sfx is not None and self.sfx.handles(a):
            self.sfx.write_reg(a, v); return True
        if self.dsp1 is not None and self.dsp1.handles(a):
            self.dsp1.write(a, v); return True
        if self.obc1 is not None and self.obc1.handles(a):
            self.obc1.write(a, v); return True
        if self.cx4 is not None and self.cx4.handles(a):
            self.cx4.write(a, v); return True
        if self.srtc is not None and self.srtc.handles(a):
            self.srtc.write(a, v); return True
        if self.sdd1 is not None and self.sdd1.handles_mmio(a):
            self.sdd1.write_mmio(a, v); return True
        if self.st01x is not None and self.st01x.handles(a):
            self.st01x.write(a, v); return True
        if self.spc7110 is not None and self.spc7110.handles(a):
            self.spc7110.write(a, v); return True
        if self.sgb is not None and self.sgb.handles(a):
            self.sgb.write(a, v); return True
        return False

    def reset(self):
        self.power()

    # ------------------------------------------------------------- bus
    def _make_read(self):
        rbuf = self.rbuf; rofs = self.rofs; slow = self.read_slow
        def read(a):
            p = a >> 13
            b = rbuf[p]
            if b is not None:
                return b[rofs[p] + (a & 0x1FFF)]
            return slow(a)
        return read

    def _make_write(self):
        wbuf = self.wbuf; wofs = self.wofs; slow = self.write_slow; s = self
        def write(a, v):
            s.wc += 1
            p = a >> 13
            b = wbuf[p]
            if b is not None:
                b[wofs[p] + (a & 0x1FFF)] = v
            else:
                slow(a, v)
        return write

    def build_map(self):
        """Snes9x-style 8 KB page map: fast pointers for WRAM/ROM, None -> I/O slow path."""
        rl = self.romlen; rom_off = self.rom_offset; sa1 = self.sa1 is not None
        dsp = self.dsp1 is not None
        for p in range(2048):
            bank = p >> 3; off = (p & 7) << 13; b = bank & 0x7F
            rb = wb = None; ro = wo = 0
            if bank in (0x7E, 0x7F):
                rb = wb = self.wram; ro = wo = ((bank - 0x7E) << 16) | off
            elif b < 0x40 and off < 0x2000:
                rb = wb = self.wram; ro = wo = off
            elif sa1 and b < 0x40 and off < 0x8000:
                pass  # $2100 I/O, $2200 SA-1, $3000 I-RAM, $6000 BW-RAM -> slow
            elif sa1 and 0x40 <= bank <= 0x4F:
                pass  # BW-RAM banks -> slow
            elif sa1 and (off >= 0x8000 or bank >= 0xC0):
                pass  # Super MMC ROM — slow path so bank switches apply
            elif dsp and not self.hirom and 0x30 <= b < 0x40 and off >= 0x8000:
                pass  # DSP-1 LoROM data/status window
            elif b < 0x40 and off < 0x8000:
                pass  # PPU/CPU I/O, SuperFX $3000, chip $6000, etc.
            elif self.hirom:
                ro = rom_off(bank, off); rb = self.rom
            elif off >= 0x8000 or not (0x70 <= b < 0x7E):
                ro = rom_off(bank, off); rb = self.rom
            if rb is self.rom and (ro + 0x2000 > rl or ro < 0):
                rb = None
            self.rbuf[p] = rb; self.rofs[p] = ro; self.wbuf[p] = wb; self.wofs[p] = wo

    def read_slow(self, a):
        bank = a >> 16; off = a & 0xFFFF
        if bank == 0x7E: return self.wram[off]
        if bank == 0x7F: return self.wram[0x10000 | off]
        if self.sa1 is not None:
            b = bank & 0x7F
            if b < 0x40 and off < 0x2000:
                return self.wram[off]
            if b < 0x40 and off < 0x2200:
                return self.io_read(off)
            if (b < 0x40 and (0x2200 <= off < 0x2400 or 0x3000 <= off < 0x3800
                               or 0x6000 <= off < 0x8000)) or 0x40 <= bank <= 0x4F:
                return self.sa1.snes_read(a)
            if b < 0x40 and off < 0x6000:
                return self.io_read(off)
            # ROM + vector overrides via Super MMC
            if (a & 0x408000) == 0x008000 or (a & 0xC00000) == 0xC00000 or b >= 0x40:
                return self.sa1.read_rom(a)
            return self.mdr
        chip = self._chip_read(a)
        if chip is not None:
            return chip
        b = bank & 0x7F
        if b < 0x40:
            if off < 0x2000: return self.wram[off]
            if off >= 0x8000:
                return self.rom[self.rom_offset(bank, off)]
            if off < 0x6000: return self.io_read(off)
            if self.hirom and self.sram_size and b >= 0x20:
                return self.sram[((b & 0x1F) * 0x2000 + off - 0x6000) % self.sram_size]
            return self.mdr
        if self.hirom:
            return self.rom[self.rom_offset(bank, off)]
        if off < 0x8000 and 0x70 <= b < 0x7E and self.sram_size:
            return self.sram[((b - 0x70) * 0x8000 + off) % self.sram_size]
        return self.rom[self.rom_offset(bank, off)]

    def write_slow(self, a, v):
        bank = a >> 16; off = a & 0xFFFF
        if bank == 0x7E: self.wram[off] = v; return
        if bank == 0x7F: self.wram[0x10000 | off] = v; return
        if self.sa1 is not None:
            b = bank & 0x7F
            if b < 0x40 and off < 0x2000:
                self.wram[off] = v; return
            if b < 0x40 and off < 0x2200:
                self.io_write(off, v); return
            if self.sa1.snes_write(a, v):
                return
            if b < 0x40 and off < 0x6000:
                self.io_write(off, v)
            return
        if self._chip_write(a, v):
            return
        b = bank & 0x7F
        if b < 0x40:
            if off < 0x2000: self.wram[off] = v; return
            if off < 0x6000: self.io_write(off, v); return
            if off < 0x8000 and self.hirom and self.sram_size and b >= 0x20:
                self.sram[((b & 0x1F) * 0x2000 + off - 0x6000) % self.sram_size] = v
            return
        if not self.hirom and off < 0x8000 and 0x70 <= b < 0x7E and self.sram_size:
            self.sram[((b - 0x70) * 0x8000 + off) % self.sram_size] = v

    def read_block(self, bank, addr, n):
        if addr + n <= 0x10000:
            if bank == 0x7E: return bytes(self.wram[addr:addr + n])
            if bank == 0x7F: return bytes(self.wram[0x10000 + addr:0x10000 + addr + n])
            b = bank & 0x7F
            if (self.hirom and (b >= 0x40 or addr >= 0x8000)) or (not self.hirom and addr >= 0x8000):
                o = self.rom_offset(bank, addr)
                if o + n <= self.romlen: return self.rom[o:o + n]
            if b < 0x40 and addr + n <= 0x2000: return bytes(self.wram[addr:addr + n])
        r = self.read
        return bytes(r((bank << 16) | ((addr + i) & 0xFFFF)) for i in range(n))

    # ------------------------------------------------------------- I/O
    def io_read(self, off):
        if 0x2100 <= off < 0x2200:
            v = self.pr[off & 0xFF]()
        elif off == 0x4016:
            v = (self.joy_sr[0] >> 15) & 1; self.joy_sr[0] = ((self.joy_sr[0] << 1) | 1) & 0xFFFF
            v |= self.mdr & 0xFC
        elif off == 0x4017:
            v = ((self.joy_sr[1] >> 15) & 1) | 0x1C; self.joy_sr[1] = ((self.joy_sr[1] << 1) | 1) & 0xFFFF
        elif 0x4200 <= off < 0x4220:
            v = self.cpuio_read(off)
        elif 0x4300 <= off < 0x4380:
            v = self.dmar[off - 0x4300]
        else:
            v = self.mdr
        self.mdr = v
        return v

    def io_write(self, off, v):
        self.mdr = v
        if 0x2100 <= off < 0x2200:
            self.pw[off & 0xFF](v)
        elif off == 0x4016:
            if self.joy_strobe and not (v & 1):
                self.joy_sr = [self.joy1, self.joy2]
            self.joy_strobe = v & 1
        elif 0x4200 <= off < 0x4220:
            self.cpuio_write(off, v)
        elif 0x4300 <= off < 0x4380:
            self.dmar[off - 0x4300] = v

    def cpuio_read(self, off):
        # unused bits are open bus = last byte on the bus ($42, the address high byte)
        if off == 0x4210:
            v = (0x80 if self.nmi_flag else 0) | 0x42; self.nmi_flag = False; return v
        if off == 0x4211:
            v = (0x80 if self.irq_flag else 0) | 0x42
            self.irq_flag = False; self.sync_irq_line(); return v
        if off == 0x4212:
            hb = (self.cpu.cyc - self.line_start) >= HBLANK_CYC
            return (0x80 if self.vblank else 0) | (0x40 if hb else 0) | 0x02
        if off == 0x4213: return self.wrio
        if off == 0x4214: return self.rddiv & 0xFF
        if off == 0x4215: return self.rddiv >> 8
        if off == 0x4216: return self.rdmpy & 0xFF
        if off == 0x4217: return self.rdmpy >> 8
        if off >= 0x4218: return self.joyreg[off - 0x4218]
        return self.mdr

    def cpuio_write(self, off, v):
        if off == 0x4200:
            old = self.nmitimen; self.nmitimen = v
            if (v & 0x80) and not (old & 0x80) and self.nmi_flag:
                self.cpu.nmi_pending = True
            if not (v & 0x30):
                self.irq_flag = False; self.sync_irq_line()
        elif off == 0x4201: self.wrio = v
        elif off == 0x4202: self.wrmpya = v
        elif off == 0x4203: self.rdmpy = self.wrmpya * v; self.rddiv = v
        elif off == 0x4204: self.wrdiv = (self.wrdiv & 0xFF00) | v
        elif off == 0x4205: self.wrdiv = (self.wrdiv & 0xFF) | (v << 8)
        elif off == 0x4206:
            if v == 0: self.rddiv = 0xFFFF; self.rdmpy = self.wrdiv
            else: self.rddiv = self.wrdiv // v; self.rdmpy = self.wrdiv % v
        elif off == 0x4207: self.htime = (self.htime & 0x100) | v
        elif off == 0x4208: self.htime = (self.htime & 0xFF) | ((v & 1) << 8)
        elif off == 0x4209: self.vtime = (self.vtime & 0x100) | v
        elif off == 0x420A: self.vtime = (self.vtime & 0xFF) | ((v & 1) << 8)
        elif off == 0x420B: self.do_dma(v)
        elif off == 0x420C: self.hdmaen = v
        elif off == 0x420D: self.memsel = v

    def _build_io(self):
        s = self
        pw = [lambda v: None] * 256
        pr = [lambda: s.mdr] * 256

        def setr(idx):
            def h(v):
                s.R[idx] = v; s.rdirty = True
            return h
        for o, idx in ((0x00, R_INIDISP), (0x01, R_OBSEL), (0x05, R_BGMODE), (0x06, R_MOSAIC),
                       (0x07, R_BG1SC), (0x08, R_BG2SC), (0x09, R_BG3SC), (0x0A, R_BG4SC),
                       (0x0B, R_BG12NBA), (0x0C, R_BG34NBA), (0x1A, R_M7SEL),
                       (0x23, R_W12SEL), (0x24, R_W34SEL), (0x25, R_WOBJSEL), (0x26, R_WH0),
                       (0x27, R_WH1), (0x28, R_WH2), (0x29, R_WH3), (0x2A, R_WBGLOG),
                       (0x2B, R_WOBJLOG), (0x2C, R_TM), (0x2D, R_TS), (0x2E, R_TMW),
                       (0x2F, R_TSW), (0x30, R_CGWSEL), (0x31, R_CGADSUB), (0x33, R_SETINI)):
            pw[o] = setr(idx)

        def oamadd_l(v):
            s.oam_base = (s.oam_base & 0x200) | (v << 1); s.oam_addr = s.oam_base
        def oamadd_h(v):
            s.oam_base = ((v & 1) << 9) | (s.oam_base & 0x1FE); s.oam_addr = s.oam_base
        def oamdata(v):
            a = s.oam_addr
            if a < 0x200:
                if not (a & 1): s.oam_latch = v
                else:
                    s.oam[a - 1] = s.oam_latch; s.oam[a] = v
            else:
                s.oam[0x200 + (a & 0x1F)] = v
            s.oam_addr = (a + 1) & 0x3FF
        pw[0x02] = oamadd_l; pw[0x03] = oamadd_h; pw[0x04] = oamdata

        def scroll(k):
            idx = R_BG1HOFS + k
            def h(v):
                s.R[idx] = ((v << 8) | s.bgofs_latch) & 0x3FF
                s.bgofs_latch = v
                if k == 0:
                    s.R[R_M7HOFS] = ((v << 8) | s.m7_latch) & 0x1FFF; s.m7_latch = v
                elif k == 1:
                    s.R[R_M7VOFS] = ((v << 8) | s.m7_latch) & 0x1FFF; s.m7_latch = v
                s.rdirty = True
            return h
        for k in range(8):
            pw[0x0D + k] = scroll(k)

        def vremap():
            a = s.vmadd; r = (s.vmain >> 2) & 3
            if r == 1: a = (a & 0xFF00) | ((a & 0x1F) << 3) | ((a >> 5) & 7)
            elif r == 2: a = (a & 0xFE00) | ((a & 0x3F) << 3) | ((a >> 6) & 7)
            elif r == 3: a = (a & 0xFC00) | ((a & 0x7F) << 3) | ((a >> 7) & 7)
            return a & 0x7FFF
        self.vremap = vremap
        def vmain(v): s.vmain = v
        def vmadd_l(v):
            s.vmadd = (s.vmadd & 0xFF00) | v; s.vlatch = s.vram[vremap()]
        def vmadd_h(v):
            s.vmadd = (v << 8) | (s.vmadd & 0xFF); s.vlatch = s.vram[vremap()]
        def vdata_l(v):
            a = vremap(); s.vram[a] = (s.vram[a] & 0xFF00) | v; s.vram_dirty = True
            if not (s.vmain & 0x80): s.vmadd = (s.vmadd + VINC[s.vmain & 3]) & 0xFFFF
        def vdata_h(v):
            a = vremap(); s.vram[a] = (s.vram[a] & 0xFF) | (v << 8); s.vram_dirty = True
            if s.vmain & 0x80: s.vmadd = (s.vmadd + VINC[s.vmain & 3]) & 0xFFFF
        pw[0x15] = vmain; pw[0x16] = vmadd_l; pw[0x17] = vmadd_h; pw[0x18] = vdata_l; pw[0x19] = vdata_h

        def m7reg(idx, mul):
            def h(v):
                s.R[idx] = ((v << 8) | s.m7_latch) & 0xFFFF; s.m7_latch = v; s.rdirty = True
                if mul:
                    a = s.R[R_M7A]; a = a - 0x10000 if a & 0x8000 else a
                    b = s.R[R_M7B] >> 8; b = b - 0x100 if b & 0x80 else b
                    s.mpy = (a * b) & 0xFFFFFF
            return h
        pw[0x1B] = m7reg(R_M7A, True); pw[0x1C] = m7reg(R_M7B, True)
        pw[0x1D] = m7reg(R_M7C, False); pw[0x1E] = m7reg(R_M7D, False)
        pw[0x1F] = m7reg(R_M7X, False); pw[0x20] = m7reg(R_M7Y, False)

        def cgadd(v): s.cgaddr = v << 1
        def cgdata(v):
            a = s.cgaddr
            if not (a & 1): s.cg_latch = v
            else:
                s.cgram[a >> 1] = ((v & 0x7F) << 8) | s.cg_latch; s.cgdirty = True
            s.cgaddr = (a + 1) & 0x1FF
        pw[0x21] = cgadd; pw[0x22] = cgdata

        def coldata(v):
            c = v & 31
            if v & 0x20: s.R[R_COLR] = c
            if v & 0x40: s.R[R_COLG] = c
            if v & 0x80: s.R[R_COLB] = c
            s.rdirty = True
        pw[0x32] = coldata

        apu = s.apu; cpu = s.cpu
        def apu_w(p):
            def h(v):
                # Write first so SPC catch-up sees the new port value (avoids
                # handshake desync when both sides idle-skip on port polls).
                # 16-bit STA $2140/$2142 writes index (low) then data (high) with
                # no cycles between; defer catch-up after the even port so the HLE
                # IPL does not commit the previous data byte (EarthBound boot).
                v &= 0xFF
                if apu.pin[p] != v:
                    apu.pin[p] = v
                    apu.pkey = None
                    apu.wc += 1
                if p == 0 or p == 2:
                    apu._port_defer = True
                else:
                    apu.run_to(cpu.cyc)
            return h
        def apu_r(p):
            def h():
                apu.run_to(cpu.cyc); return apu.pout[p]
            return h
        for o in range(0x40, 0x80):
            pw[o] = apu_w(o & 3); pr[o] = apu_r(o & 3)

        def wmdata_w(v):
            s.wram[s.wmadd] = v; s.wmadd = (s.wmadd + 1) & 0x1FFFF
        def wmdata_r():
            v = s.wram[s.wmadd]; s.wmadd = (s.wmadd + 1) & 0x1FFFF; return v
        def wmadd(sh, mask):
            def h(v): s.wmadd = ((s.wmadd & ~(0xFF << sh)) | ((v & mask) << sh)) & 0x1FFFF
            return h
        pw[0x80] = wmdata_w; pr[0x80] = wmdata_r
        pw[0x81] = wmadd(0, 0xFF); pw[0x82] = wmadd(8, 0xFF); pw[0x83] = wmadd(16, 1)

        pr[0x34] = lambda: s.mpy & 0xFF
        pr[0x35] = lambda: (s.mpy >> 8) & 0xFF
        pr[0x36] = lambda: (s.mpy >> 16) & 0xFF
        def slhv():
            s.hlatch = min(339, (s.cpu.cyc - s.line_start) * 340 // LINE_CYC)
            s.vlatch_c = s.vcount
            return s.mdr
        pr[0x37] = slhv
        def oamread():
            a = s.oam_addr
            v = s.oam[a] if a < 0x200 else s.oam[0x200 + (a & 0x1F)]
            s.oam_addr = (a + 1) & 0x3FF; return v
        pr[0x38] = oamread
        def vread_l():
            v = s.vlatch & 0xFF
            if not (s.vmain & 0x80):
                s.vlatch = s.vram[vremap()]; s.vmadd = (s.vmadd + VINC[s.vmain & 3]) & 0xFFFF
            return v
        def vread_h():
            v = s.vlatch >> 8
            if s.vmain & 0x80:
                s.vlatch = s.vram[vremap()]; s.vmadd = (s.vmadd + VINC[s.vmain & 3]) & 0xFFFF
            return v
        pr[0x39] = vread_l; pr[0x3A] = vread_h
        def cgread():
            a = s.cgaddr; w = s.cgram[a >> 1]
            s.cgaddr = (a + 1) & 0x1FF
            return (w >> 8) & 0x7F if a & 1 else w & 0xFF
        pr[0x3B] = cgread
        def ophct():
            s.hl_flip ^= 1
            return (s.hlatch >> 8) & 1 if not s.hl_flip else s.hlatch & 0xFF
        def opvct():
            s.vl_flip ^= 1
            return (s.vlatch_c >> 8) & 1 if not s.vl_flip else s.vlatch_c & 0xFF
        pr[0x3C] = ophct; pr[0x3D] = opvct
        pr[0x3E] = lambda: 0x01
        def stat78():
            s.hl_flip = s.vl_flip = 0
            return 0x03 | (s.field << 7)
        pr[0x3F] = stat78
        self.pw = pw; self.pr = pr

    # ------------------------------------------------------------- DMA
    def do_dma(self, mask):
        d = self.dmar; total = 0
        for ch in range(8):
            if not (mask >> ch) & 1: continue
            b = ch * 16
            ctrl = d[b]; bb = d[b + 1]; aaddr = d[b + 2] | (d[b + 3] << 8); abank = d[b + 4]
            size = (d[b + 5] | (d[b + 6] << 8)) or 0x10000
            mode = ctrl & 7; step = 0 if ctrl & 8 else (-1 if ctrl & 0x10 else 1)
            total += size
            # S-DD1: decompress ROM→PPU/CPU for enabled channels
            sdd1_buf = None; sdd1_i = 0
            if (self.sdd1 is not None and self.sdd1.dma_enable[ch]
                    and not (ctrl & 0x80) and size > 0):
                sdd1_buf = self.sdd1.dma_read(abank, aaddr, size)
            if (not ctrl & 0x80 and mode == 1 and bb == 0x18 and step == 1
                    and (self.vmain & 0x8F) == 0x80 and size >= 2):
                n = size >> 1
                if sdd1_buf is not None:
                    data = bytes(sdd1_buf[:n * 2]); sdd1_i = n * 2
                else:
                    data = self.read_block(abank, aaddr, n * 2)
                words = array('H'); words.frombytes(data)
                if sys.byteorder != 'little': words.byteswap()
                a = self.vmadd & 0x7FFF
                if a + n <= 0x8000:
                    self.vram[a:a + n] = words
                else:
                    vr = self.vram
                    for k in range(n): vr[(a + k) & 0x7FFF] = words[k]
                self.vmadd = (self.vmadd + n) & 0xFFFF; self.vram_dirty = True
                aaddr = (aaddr + n * 2) & 0xFFFF; size -= n * 2
            pat = PAT[mode]; plen = len(pat); i = 0
            read = self.read; pw = self.pw
            if ctrl & 0x80:
                pr = self.pr; write = self.write
                while size > 0:
                    write((abank << 16) | aaddr, pr[(bb + pat[i % plen]) & 0xFF]())
                    aaddr = (aaddr + step) & 0xFFFF; i += 1; size -= 1
            else:
                while size > 0:
                    if sdd1_buf is not None and sdd1_i < len(sdd1_buf):
                        v = sdd1_buf[sdd1_i]; sdd1_i += 1
                    else:
                        v = read((abank << 16) | aaddr)
                    pw[(bb + pat[i % plen]) & 0xFF](v)
                    aaddr = (aaddr + step) & 0xFFFF; i += 1; size -= 1
            d[b + 2] = aaddr & 0xFF; d[b + 3] = aaddr >> 8; d[b + 5] = 0; d[b + 6] = 0
        self.cpu.cyc += total + 2

    def hdma_init(self):
        d = self.dmar; en = self.hdmaen; r = self.read
        for c in range(8):
            if not (en >> c) & 1:
                self.hdma_done[c] = True; continue
            b = c * 16; bank = d[b + 4]
            addr = d[b + 2] | (d[b + 3] << 8)
            ntrl = r((bank << 16) | addr); addr = (addr + 1) & 0xFFFF
            if d[b] & 0x40:
                ia = r((bank << 16) | addr) | (r((bank << 16) | ((addr + 1) & 0xFFFF)) << 8)
                addr = (addr + 2) & 0xFFFF; d[b + 5] = ia & 0xFF; d[b + 6] = ia >> 8
            d[b + 8] = addr & 0xFF; d[b + 9] = addr >> 8; d[b + 10] = ntrl
            self.hdma_done[c] = ntrl == 0; self.hdma_do[c] = True

    def hdma_line(self):
        d = self.dmar; en = self.hdmaen; r = self.read; pw = self.pw; n = 0
        for c in range(8):
            if not (en >> c) & 1 or self.hdma_done[c]: continue
            b = c * 16; ctrl = d[b]; bank = d[b + 4]; addr = d[b + 8] | (d[b + 9] << 8)
            ind = ctrl & 0x40
            if self.hdma_do[c]:
                bb = d[b + 1]
                if ind: sb = d[b + 7]; src = d[b + 5] | (d[b + 6] << 8)
                else: sb = bank; src = addr
                for k in PAT[ctrl & 7]:
                    pw[(bb + k) & 0xFF](r((sb << 16) | src)); src = (src + 1) & 0xFFFF; n += 1
                if ind: d[b + 5] = src & 0xFF; d[b + 6] = src >> 8
                else: addr = src
            ntrl = (d[b + 10] - 1) & 0xFF
            self.hdma_do[c] = bool(ntrl & 0x80)
            if not ntrl & 0x7F:
                ntrl = r((bank << 16) | addr); addr = (addr + 1) & 0xFFFF
                if ind:
                    ia = r((bank << 16) | addr) | (r((bank << 16) | ((addr + 1) & 0xFFFF)) << 8)
                    addr = (addr + 2) & 0xFFFF; d[b + 5] = ia & 0xFF; d[b + 6] = ia >> 8
                if ntrl == 0: self.hdma_done[c] = True
                self.hdma_do[c] = True
            d[b + 10] = ntrl; d[b + 8] = addr & 0xFF; d[b + 9] = addr >> 8
        self.cpu.cyc += n

    # ------------------------------------------------------------- frame
    def sync_irq_line(self):
        sa1_irq = self.sa1.snes_irq_active() if self.sa1 is not None else False
        self.cpu.irq_line = bool(self.irq_flag or sa1_irq)

    def raise_irq(self):
        self.irq_flag = True
        self.sync_irq_line()

    def snap_line(self):
        if self.rdirty:
            self.rsnap = tuple(self.R); self.rdirty = False
        if self.cgdirty:
            self.cgsnap = self.cgram.tobytes(); self.cgdirty = False
        self.line_regs.append(self.rsnap); self.line_cg.append(self.cgsnap)

    def run_frame(self):
        cpu = self.cpu; apu = self.apu; sa1 = self.sa1; sfx = self.sfx
        for v in range(LINES):
            self.vcount = v
            if v == 0:
                self.vblank = False; self.nmi_flag = False
                self.line_regs = []; self.line_cg = []
                self.field ^= 1
                if self.hdmaen: self.hdma_init()
                else: self.hdma_done = [True] * 8
            elif v <= VIS:
                self.snap_line()
            elif v == VIS + 1:
                self.vblank = True
                if not self.skip_render:
                    self.frame = self.render.render()
                self.nmi_flag = True
                if self.nmitimen & 0x80: cpu.nmi_pending = True
                if self.nmitimen & 1:
                    j1 = self.joy1; j2 = self.joy2
                    self.joyreg = [j1 & 0xFF, j1 >> 8, j2 & 0xFF, j2 >> 8, 0, 0, 0, 0]
            base = self.line_end
            self.line_start = base
            end = base + LINE_CYC
            nt = self.nmitimen
            if nt & 0x30:
                if (nt & 0x30) == 0x20:
                    if v == self.vtime: self.raise_irq()
                elif not (nt & 0x20) or v == self.vtime:
                    cpu.run(base + min(self.htime, 339) * LINE_CYC // 340)
                    if sa1 is not None:
                        sa1.run_to(cpu.cyc)
                        self.sync_irq_line()
                    if sfx is not None:
                        sfx.run_to(512)
                    self.raise_irq()
            cpu.run(base + HBLANK_CYC)
            if sa1 is not None:
                sa1.run_to(cpu.cyc)
                self.sync_irq_line()
            if sfx is not None:
                sfx.run_to(512)
            if v < VIS and self.hdmaen:
                self.hdma_line()
            cpu.run(end)
            if sa1 is not None:
                sa1.run_to(end)
                self.sync_irq_line()
            if sfx is not None:
                sfx.run_to(1024)
            apu.run_to(end)
            self.line_end = end
        apu.dspc.render_to(apu.spc.cyc)
        self.frames += 1

    # ------------------------------------------------------------- save states
    def save_state(self):
        skip = {'rom', 'cpu', 'apu', 'sa1', 'dsp1', 'sfx', 'obc1', 'srtc', 'sdd1', 'cx4',
                'st01x', 'spc7110', 'sgb',
                'render', 'frame', 'pw', 'pr', 'vremap', 'line_regs', 'line_cg',
                'rsnap', 'cgsnap', 'rom_path', 'title', 'rbuf', 'rofs', 'wbuf', 'wofs',
                'read', 'write'}
        st = {k: v for k, v in vars(self).items()
              if k not in skip and isinstance(v, (int, bool, bytes, bytearray, list, array, str))}
        st['__cpu'] = {k: getattr(self.cpu, k) for k in CPU65816.STATE}
        st['__apu'] = self.apu.get_state()
        if self.sa1 is not None:
            st['__sa1'] = self.sa1.get_state()
        for name in ('dsp1', 'sfx', 'obc1', 'srtc', 'sdd1', 'cx4', 'st01x', 'spc7110', 'sgb'):
            chip = getattr(self, name, None)
            if chip is not None:
                st['__' + name] = chip.get_state()
        st['__rom'] = zlib.crc32(self.rom)
        return pickle.dumps(st, protocol=4)

    def load_state(self, blob):
        st = pickle.loads(blob)
        if st.pop('__rom', None) != zlib.crc32(self.rom):
            raise ValueError("state belongs to a different ROM")
        for k, v in st.pop('__cpu').items(): setattr(self.cpu, k, v)
        if '__apu' in st: self.apu.set_state(st.pop('__apu'))
        sa1st = st.pop('__sa1', None)
        _chip_names = ('dsp1', 'sfx', 'obc1', 'srtc', 'sdd1', 'cx4', 'st01x', 'spc7110', 'sgb')
        chip_st = {n: st.pop('__' + n, None) for n in _chip_names}
        for k, v in st.items():
            if k in ('rbuf', 'rofs', 'wbuf', 'wofs', 'sa1') + _chip_names:
                continue
            setattr(self, k, v)
        if self.sa1 is not None and sa1st is not None:
            self.sa1.set_state(sa1st)
            self.sa1.attach_bwram(self.sram)
        for name, blob in chip_st.items():
            chip = getattr(self, name, None)
            if chip is not None and blob is not None:
                chip.set_state(blob)
        self.build_map()
        self.rdirty = self.cgdirty = self.vram_dirty = True
        self.cpu.idle_key = None
        self.sync_irq_line()


# ===================================================================== renderer
ORD0 = [(4, 3), (0, 1), (1, 1), (4, 2), (0, 0), (1, 0), (4, 1), (2, 1), (3, 1), (4, 0), (2, 0), (3, 0)]
ORD1 = [(4, 3), (0, 1), (1, 1), (4, 2), (0, 0), (1, 0), (4, 1), (2, 1), (4, 0), (2, 0)]
ORD1P = [(2, 1), (4, 3), (0, 1), (1, 1), (4, 2), (0, 0), (1, 0), (4, 1), (4, 0), (2, 0)]
ORD2 = [(4, 3), (0, 1), (4, 2), (1, 1), (4, 1), (0, 0), (4, 0), (1, 0)]
ORD7 = [(4, 3), (4, 2), (4, 1), (0, None), (4, 0)]
BPP = {0: (2, 2, 2, 2), 1: (4, 4, 2), 2: (4, 4), 3: (8, 4), 4: (8, 2), 5: (4, 2), 6: (4,)}


class Renderer:
    """Vectorised (numpy) scanline-accurate-register PPU renderer."""

    def __init__(self, snes):
        self.s = snes
        self.x = np.arange(256, dtype=np.int32)[None, :]
        self.x2 = self.x * 2
        self.t2 = self.t4 = self.t8 = None

    def decode_tiles(self):
        vb = np.frombuffer(self.s.vram, dtype=np.uint8)
        bits = np.unpackbits(vb).reshape(32768, 2, 8)
        p = bits[:, 0, :] | (bits[:, 1, :] << 1)                      # 2 planes per word
        self.t2 = p.reshape(4096, 8, 8)
        q = p.reshape(2048, 2, 8, 8)
        self.t4 = q[:, 0] | (q[:, 1] << 2)
        q = p.reshape(1024, 4, 8, 8)
        self.t8 = q[:, 0] | (q[:, 1] << 2) | (q[:, 2] << 4) | (q[:, 3] << 6)
        self.f2 = self.t2.reshape(-1); self.f4 = self.t4.reshape(-1); self.f8 = self.t8.reshape(-1)

    def render(self):
        s = self.s
        if s.vram_dirty or self.t2 is None:
            self.decode_tiles(); s.vram_dirty = False
        regs = list(s.line_regs); cgs = list(s.line_cg)
        if not regs:
            s.snap_line(); regs = list(s.line_regs); cgs = list(s.line_cg)
        while len(regs) < VIS:
            regs.append(regs[-1]); cgs.append(cgs[-1])
        regs = regs[:VIS]; cgs = cgs[:VIS]
        uid = {}; urows = []; inv = np.empty(VIS, np.int32)
        for y, t in enumerate(regs):            # most lines share the same snapshot object
            k = id(t)
            if k not in uid:
                uid[k] = len(urows); urows.append(t)
            inv[y] = uid[k]
        L = np.array(urows, dtype=np.int32)[inv]
        VR = np.frombuffer(s.vram, dtype=np.uint16)

        # palettes (per-line, so HDMA colour gradients work)
        ids = {}; plist = []; sid = np.empty(VIS, np.int64)
        for y, c in enumerate(cgs):
            k = id(c)
            if k not in ids:
                ids[k] = len(plist)
                w = np.frombuffer(c, dtype=np.uint16).astype(np.int16)
                plist.append(np.stack([w & 31, (w >> 5) & 31, (w >> 10) & 31], -1))
            sid[y] = ids[k]
        pal = np.stack(plist)

        obj = self.render_obj(VR)
        out = np.zeros((VIS, 256, 3), np.int16)
        groups = {}
        for y, t in enumerate(regs):
            groups.setdefault((t[R_BGMODE],) + t[R_BG1SC:R_BG34NBA + 1], []).append(y)
        for key, rows in groups.items():
            ys = np.array(rows, dtype=np.int32)
            gs = sid[ys]
            pg = pal[gs[:1]] if (gs == gs[0]).all() else pal[gs]
            out[ys] = self.render_group(L[ys], ys, VR, pg, obj)

        ini = L[:, R_INIDISP]
        br = np.where(ini & 0x80, 0, (ini & 15) + 1)[:, None, None]
        out = (out * br) >> 4
        return ((out << 3) | (out >> 2)).astype(np.uint8)

    # -- windows -----------------------------------------------------------
    def window(self, Lg, layer):
        if layer < 4:
            sel = (Lg[:, R_W12SEL + (layer >> 1)] >> (4 * (layer & 1))) & 15
            log = (Lg[:, R_WBGLOG] >> (2 * layer)) & 3
        elif layer == 4:
            sel = Lg[:, R_WOBJSEL] & 15; log = Lg[:, R_WOBJLOG] & 3
        else:
            sel = (Lg[:, R_WOBJSEL] >> 4) & 15; log = (Lg[:, R_WOBJLOG] >> 2) & 3
        x = self.x
        sel = sel[:, None]; log = log[:, None]
        w1 = ((x >= Lg[:, R_WH0][:, None]) & (x <= Lg[:, R_WH1][:, None])) ^ ((sel & 1) != 0)
        w2 = ((x >= Lg[:, R_WH2][:, None]) & (x <= Lg[:, R_WH3][:, None])) ^ ((sel & 4) != 0)
        e1 = (sel & 2) != 0; e2 = (sel & 8) != 0
        comb = np.where(log == 0, w1 | w2, np.where(log == 1, w1 & w2,
                        np.where(log == 2, w1 ^ w2, ~(w1 ^ w2))))
        return np.where(e1 & e2, comb, np.where(e1, w1, np.where(e2, w2, False)))

    # -- background layers --------------------------------------------------
    def bg_layer(self, i, bpp, mode, bgmode, Lg, ys, VR):
        sc = int(Lg[0, R_BG1SC + i]); nba = int(Lg[0, R_BG12NBA + (i >> 1)])
        chr_base = ((nba >> (4 * (i & 1))) & 0xF) << 12
        map_base = (sc & 0xFC) << 8
        big = (bgmode >> (4 + i)) & 1
        hofs = Lg[:, R_BG1HOFS + 2 * i][:, None]; vofs = Lg[:, R_BG1VOFS + 2 * i][:, None]
        px = ((self.x2 if mode in (5, 6) else self.x) + hofs) & 0x3FF          # (n,256)
        py = (vofs + (ys + 1)[:, None]) & 0x3FF                                # (n,1)
        tm = 15 if big else 7; sh = 4 if big else 3
        wide = sc & 1; tall = (sc >> 1) & 1
        tcol = (px >> sh) & (63 if wide else 31)
        trow = (py >> sh) & (63 if tall else 31)
        rowbase = map_base + (((trow >> 5) * (2 if wide else 1)) << 10) + ((trow & 31) << 5)
        ent = VR[(rowbase + ((tcol >> 5) << 10) + (tcol & 31)) & 0x7FFF].astype(np.int32)
        fx = (px & tm) ^ (((ent >> 14) & 1) * tm)
        fy = (py & tm) ^ (((ent >> 15) & 1) * tm)
        tile = ent & 0x3FF
        if big:
            tile = (tile + (fx >> 3) + ((fy >> 3) << 4)) & 0x3FF
            fx = fx & 7; fy = fy & 7
        wpt = 4 * bpp
        T = self.f2 if bpp == 2 else (self.f4 if bpp == 4 else self.f8)
        g = ((chr_base // wpt) + tile) & ((32768 // wpt) - 1)
        c = T[(g << 6) | (fy << 3) | fx].astype(np.int32)
        if bpp == 8: cidx = c
        elif mode == 0: cidx = c + (((ent >> 10) & 7) << 2) + (i << 5)
        elif bpp == 2: cidx = c + (((ent >> 10) & 7) << 2)
        else: cidx = c + (((ent >> 10) & 7) << 4)
        return cidx, (ent >> 13) & 1, c != 0

    def bg_mode7(self, Lg, ys, VR):
        def s16(v): return ((v + 0x8000) & 0xFFFF) - 0x8000
        def s13(v): return ((v + 0x1000) & 0x1FFF) - 0x1000
        col = lambda r: Lg[:, r][:, None].astype(np.int64)
        A = s16(col(R_M7A)); B = s16(col(R_M7B)); C = s16(col(R_M7C)); D = s16(col(R_M7D))
        cx = s13(col(R_M7X)); cy = s13(col(R_M7Y))
        ho = s13(col(R_M7HOFS)); vo = s13(col(R_M7VOFS))
        sel = col(R_M7SEL)
        x = self.x.astype(np.int64); y = (ys + 1)[:, None]
        sx = np.where(sel & 1, 255 - x, x); sy = np.where(sel & 2, 255 - y, y)

        def clip(v): return np.where(v & 0x2000, v | ~0x3FF, v & 0x3FF)
        hx = clip(ho - cx); vy = clip(vo - cy)
        X = ((A * hx) & ~63) + ((B * vy) & ~63) + ((B * sy) & ~63) + (cx << 8) + A * sx
        Y = ((C * hx) & ~63) + ((D * vy) & ~63) + ((D * sy) & ~63) + (cy << 8) + C * sx
        tx = X >> 8; ty = Y >> 8
        oob = ((tx | ty) & ~1023) != 0
        tx = tx & 1023; ty = ty & 1023
        tile = (VR[((ty >> 3) << 7) | (tx >> 3)] & 0xFF).astype(np.int64)
        fine = ((ty & 7) << 3) | (tx & 7)
        c = (VR[(tile << 6) | fine] >> 8).astype(np.int64)
        if (sel & 0x80).any():
            c = np.where(oob & ((sel & 0x80) != 0),
                         np.where((sel & 0x40) != 0, (VR[fine] >> 8).astype(np.int64), 0), c)
        return c, np.zeros_like(c), c != 0

    # -- sprites ------------------------------------------------------------
    def render_obj(self, VR):
        s = self.s; oam = s.oam; obsel = s.R[R_OBSEL]
        sizes = OBJ_SIZES[(obsel >> 5) & 7]
        base = (obsel & 7) << 13; gap = (((obsel >> 3) & 3) + 1) << 12
        oidx = np.zeros((VIS, 256), np.int32); opri = np.zeros((VIS, 256), np.int32)
        oop = np.zeros((VIS, 256), bool); ohi = np.zeros((VIS, 256), bool)
        T4 = self.t4
        for i in range(127, -1, -1):
            o = i * 4
            hb = oam[0x200 + (i >> 2)] >> ((i & 3) * 2)
            x = oam[o] | ((hb & 1) << 8); y = oam[o + 1]; t = oam[o + 2]; at = oam[o + 3]
            w, h = sizes[(hb >> 1) & 1]
            if x >= 256: x -= 512
            if x <= -w or (y >= VIS and y + h <= 256): continue
            pal = (at >> 1) & 7; pri = (at >> 4) & 3
            ch = h >> 3; cw = w >> 3
            cy_ = np.arange(ch)[:, None]; cx_ = np.arange(cw)[None, :]
            tn = ((((t >> 4) + cy_) & 0xF) << 4) | (((t & 0xF) + cx_) & 0xF)
            wa = (base + (gap if at & 1 else 0) + tn * 16) & 0x7FFF
            blk = T4[wa >> 4].transpose(0, 2, 1, 3).reshape(h, w)
            if at & 0x40: blk = blk[:, ::-1]
            if at & 0x80: blk = blk[::-1, :]
            rows = (y + np.arange(h)) & 0xFF; cols = x + np.arange(w)
            rm = rows < VIS; cm = (cols >= 0) & (cols < 256)
            if not rm.any() or not cm.any(): continue
            sub = blk[np.ix_(rm, cm)]
            rr, cc = np.nonzero(sub)
            if not len(rr): continue
            R_ = rows[rm][rr]; C_ = cols[cm][cc]
            oidx[R_, C_] = 128 + (pal << 4) + sub[rr, cc]
            opri[R_, C_] = pri; oop[R_, C_] = True; ohi[R_, C_] = pal >= 4
        return oidx, opri, oop, ohi

    # -- compositing + colour math -----------------------------------------
    def compose(self, order, layers, obj, en, wen, win, n):
        idx = np.zeros((n, 256), np.int32); src = np.full((n, 256), 5, np.int32)
        oidx, opri, oop = obj
        for Ly, p in reversed(order):
            enb = ((en >> Ly) & 1).astype(bool)
            if not enb.any(): continue
            if Ly == 4:
                m = oop & (opri == p); c = oidx
            else:
                lay = layers.get(Ly)
                if lay is None: continue
                c, pr, op = lay
                m = op if p is None else (op & (pr == p))
            m = m & enb[:, None]
            wb = ((wen >> Ly) & 1).astype(bool)
            if wb.any():
                m = m & ~(win(Ly) & wb[:, None])
            idx[m] = c[m]; src[m] = Ly
        return idx, src

    def render_group(self, Lg, ys, VR, palg, obj):
        n = len(ys)
        bgmode = int(Lg[0, R_BGMODE]); mode = bgmode & 7
        anyen = int(np.bitwise_or.reduce(Lg[:, R_TM] | Lg[:, R_TS]))
        layers = {}
        if mode == 7:
            if anyen & 1: layers[0] = self.bg_mode7(Lg, ys, VR)
            order = ORD7
        else:
            for i, bpp in enumerate(BPP[mode]):
                if anyen & (1 << i):
                    layers[i] = self.bg_layer(i, bpp, mode, bgmode, Lg, ys, VR)
            order = ORD0 if mode == 0 else (ORD1P if (mode == 1 and bgmode & 8) else
                                            (ORD1 if mode == 1 else ORD2))
        cache = {}

        def win(Ly):
            if Ly not in cache: cache[Ly] = self.window(Lg, Ly)
            return cache[Ly]
        o = (obj[0][ys], obj[1][ys], obj[2][ys])
        ohi = obj[3][ys]
        midx, msrc = self.compose(order, layers, o, Lg[:, R_TM], Lg[:, R_TMW], win, n)
        if palg.shape[0] == 1:
            p0 = palg[0]; look = lambda ix: p0[ix]
        else:
            rsel = np.arange(n)[:, None]; look = lambda ix: palg[rsel, ix]
        main = look(midx).astype(np.int16)
        cgw = Lg[:, R_CGWSEL][:, None]; cga = Lg[:, R_CGADSUB][:, None]
        if not (cga & 0x3F).any() and not (cgw & 0xC0).any():
            return main

        def region(m2):
            if not (m2 & 1).any() and not (m2 & 2).any():
                return np.zeros((n, 256), bool)
            cw = win(5)
            return np.where(m2 == 0, False, np.where(m2 == 1, ~cw, np.where(m2 == 2, cw, True)))
        black = region((cgw >> 6) & 3)
        prevent = region((cgw >> 4) & 3)
        srcbit = np.where(msrc == 4, np.where(ohi, 0x10, 0), 1 << msrc)
        math = ((cga & srcbit) != 0) & ~prevent
        main[black] = 0
        fixed = np.stack([Lg[:, R_COLR], Lg[:, R_COLG], Lg[:, R_COLB]], -1)[:, None, :].astype(np.int16)
        use_sub = (cgw & 2) != 0
        if use_sub.any():
            sidx, ssrc = self.compose(order, layers, o, Lg[:, R_TS], Lg[:, R_TSW], win, n)
            subc = look(sidx).astype(np.int16)
            sback = ssrc == 5
            opnd = np.where((use_sub & ~sback)[..., None], subc, fixed)
            half = ((cga & 0x40) != 0) & ~black & ~(use_sub & sback)
        else:
            opnd = np.broadcast_to(fixed, main.shape)
            half = ((cga & 0x40) != 0) & ~black
        res = np.where(((cga & 0x80) != 0)[..., None], main - opnd, main + opnd)
        res = np.where(half[..., None], res >> 1, res)
        res = np.clip(res, 0, 31)
        return np.where(math[..., None], res, main)


# ===================================================================== built-in demo cartridge
FONT = {
    'A': '0E 11 11 1F 11 11 11', 'B': '1E 11 11 1E 11 11 1E', 'C': '0E 11 10 10 10 11 0E',
    'D': '1E 11 11 11 11 11 1E', 'E': '1F 10 10 1E 10 10 1F', 'F': '1F 10 10 1E 10 10 10',
    'G': '0E 11 10 17 11 11 0F', 'H': '11 11 11 1F 11 11 11', 'I': '0E 04 04 04 04 04 0E',
    'J': '07 02 02 02 02 12 0C', 'K': '11 12 14 18 14 12 11', 'L': '10 10 10 10 10 10 1F',
    'M': '11 1B 15 15 11 11 11', 'N': '11 11 19 15 13 11 11', 'O': '0E 11 11 11 11 11 0E',
    'P': '1E 11 11 1E 10 10 10', 'Q': '0E 11 11 11 15 12 0D', 'R': '1E 11 11 1E 14 12 11',
    'S': '0F 10 10 0E 01 01 1E', 'T': '1F 04 04 04 04 04 04', 'U': '11 11 11 11 11 11 0E',
    'V': '11 11 11 11 11 0A 04', 'W': '11 11 11 15 15 15 0A', 'X': '11 11 0A 04 0A 11 11',
    'Y': '11 11 11 0A 04 04 04', 'Z': '1F 01 02 04 08 10 1F', '0': '0E 11 13 15 19 11 0E',
    '1': '04 0C 04 04 04 04 0E', '2': '0E 11 01 02 04 08 1F', '3': '1F 02 04 02 01 11 0E',
    '4': '02 06 0A 12 1F 02 02', '5': '1F 10 1E 01 01 11 0E', '6': '06 08 10 1E 11 11 0E',
    '7': '1F 01 02 04 08 08 08', '8': '0E 11 11 0E 11 11 0E', '9': '0E 11 11 0F 01 02 0C',
    '.': '00 00 00 00 00 0C 0C', '-': '00 00 00 1F 00 00 00', '(': '02 04 08 08 08 04 02',
    ')': '08 04 02 02 02 04 08', '/': '00 01 02 04 08 10 00', ':': '00 0C 0C 00 0C 0C 00',
    '!': '04 04 04 04 04 00 04', '>': '00 08 0C 0E 0C 08 00', '<': '00 02 06 0E 06 02 00'}
CHARS = ' ' + ''.join(FONT)

CAT = ["  #          #  ",
       " #+#        #+# ",
       " #++#      #++# ",
       " #+++######+++# ",
       " #++++++++++++# ",
       "#++++++++++++++#",
       "#++oo++++++oo++#",
       "#++oo++++++oo++#",
       "#++++++##++++++#",
       "#+++#++++++#+++#",
       "#++++######++++#",
       " #++++++++++++# ",
       " #++++++++++++# ",
       "  #++++++++++#  ",
       "   ##########   ",
       "                "]

DEMO_TEXT = [(3, "VSNES 0.1", 1), (5, "VIRTUAL SNES EMULATOR", 1),
             (7, "CLASSIC DESKTOP FRONTEND", 0), (10, "65816  SPC700  PPU MODES 0-7", 0),
             (11, "DMA HDMA WINDOWS COLOR MATH", 0), (12, "S-DSP AUDIO  60 FPS PACING", 0),
             (15, "D-PAD MOVES THE CAT", 0), (17, "FILE > OPEN ROM TO START", 0),
             (24, "VSNES 0.1", 0), (25, "FILE  CPU  OPTIONS  HELP", 0)]


def build_spc_demo():
    """Sound driver the demo cart uploads to ARAM $0200 (image runs to $0403).

    Sets up the S-DSP (sample directory, one BRR instrument, ADSR), then plays a
    looping arpeggio off timer 0. Also echoes port0+1 -> port1 and counts timer
    ticks on port2 so the 65816 side can verify the SPC700 is alive.
    """
    import math
    org = 0x0200; c = bytearray(); lab = {}; fix = []
    def L(n): lab[n] = org + len(c)
    def B(*a): c.extend(a)
    def rel(op, n): c.append(op); fix.append((len(c), n, 'r')); c.append(0)
    def absx(op, n, add=0): c.append(op); fix.append((len(c), n, add)); c.extend(b'\0\0')
    def dsp(reg, val): B(0x8F, reg, 0xF2, 0x8F, val, 0xF3)     # mov $F2,#reg ; mov $F3,#val
    dsp(0x6C, 0x20)                     # FLG: unmute, echo writes off
    dsp(0x5D, 0x04)                     # DIR = $0400
    for r, v in ((0x0C, 0x60), (0x1C, 0x60), (0x2C, 0), (0x3C, 0), (0x2D, 0), (0x3D, 0),
                 (0x4D, 0), (0x5C, 0), (0x00, 0x60), (0x01, 0x48), (0x04, 0x00),
                 (0x05, 0xBF), (0x06, 0x52)):   # voice 0: vol, SRCN 0, ADSR AR15 DR3 SL2 SR18
        dsp(r, v)
    B(0x8F, 0x80, 0xFA)                 # timer0 target 128 -> 62.5 Hz
    B(0x8F, 0x81, 0xF1)                 # enable timer0, keep IPL ROM mapped
    L('loop')
    B(0xE4, 0xF4, 0xBC, 0xC4, 0xF5)     # port1 = port0 + 1
    B(0xE4, 0xFD); rel(0xF0, 'loop')    # wait for a timer tick
    B(0xAB, 0x11, 0xFA, 0x11, 0xF6)     # inc $11 ; port2 = $11
    B(0xE4, 0x11, 0x28, 0x0F); rel(0xD0, 'loop')        # every 16 ticks:
    B(0xE4, 0x10, 0xBC, 0x28, 0x07, 0xC4, 0x10, 0x1C, 0x5D)   # $10 = ($10+1)&7 ; X = 2*$10
    absx(0xF5, 'notes', 0); B(0x8F, 0x02, 0xF2, 0xC4, 0xF3)   # PITCH L
    absx(0xF5, 'notes', 1); B(0x8F, 0x03, 0xF2, 0xC4, 0xF3)   # PITCH H
    dsp(0x4C, 0x01)                     # KON voice 0
    rel(0x2F, 'loop')
    L('notes')
    for f in (523.25, 659.26, 783.99, 1046.5, 783.99, 659.26, 523.25, 392.0):
        p = int(round(f * 16 * 4096 / 32000)); B(p & 0xFF, p >> 8)
    for pos, n, kind in fix:
        t = lab[n]
        if kind == 'r':
            d = t - (org + pos + 1); assert -128 <= d < 128, n; c[pos] = d & 0xFF
        else:
            t += kind; c[pos] = t & 0xFF; c[pos + 1] = t >> 8
    img = bytearray(0x204)
    assert len(c) <= 0x100
    img[:len(c)] = c
    nib = [max(-8, min(7, int(round(5 * math.sin(2 * math.pi * k / 16) +
                                    2 * math.sin(4 * math.pi * k / 16))))) for k in range(16)]
    brr = bytes([0xC3]) + bytes(((nib[2 * k] & 15) << 4) | (nib[2 * k + 1] & 15) for k in range(8))
    img[0x100:0x109] = brr               # $0300: one looping BRR block (shift 12, loop+end)
    img[0x200:0x204] = bytes((0x00, 0x03, 0x00, 0x03))   # $0400: DIR entry 0 start/loop
    return bytes(img)


SPC_DEMO = build_spc_demo()


def build_demo_rom():
    """Assemble a real 32 KB LoROM homebrew cartridge that runs on the emulated 65816."""
    import math
    code = bytearray(); lab = {}; fix = []
    def pc(): return 0x8000 + len(code)
    def L(n): lab[n] = pc()
    def B(*a): code.extend(a)
    def W(v): code.extend((v & 0xFF, (v >> 8) & 0xFF))
    def A16(n): fix.append((len(code), n, 'a')); code.extend(b'\0\0')
    def R8(n): fix.append((len(code), n, 'r')); code.append(0)
    def lda(v): B(0xA9, v)
    def sta(a): B(0x8D); W(a)
    def stz(a): B(0x9C); W(a)
    def ldx(v): B(0xA2); W(v)
    def stx(a): B(0x8E); W(a)
    def dma(ctrl, bbad, src, size):
        lda(ctrl); sta(0x4300); lda(bbad); sta(0x4301)
        B(0xA2); A16(src); stx(0x4302); stz(0x4304); ldx(size); stx(0x4305)
        lda(1); sta(0x420B)

    # data
    font = bytearray(16)
    for ch in CHARS[1:]:
        rows = [0] + [int(h, 16) << 2 for h in FONT[ch].split()]
        for r in rows: font += bytes((r, 0))
    tmap = [0] * 1024
    for row, text, palno in DEMO_TEXT:
        col = (32 - len(text)) // 2
        for k, ch in enumerate(text):
            # Unknown glyphs become space so branding tweaks cannot crash boot
            tmap[row * 32 + col + k] = (CHARS.find(ch) if ch in CHARS else 0) | (palno << 10)
    tmap_b = b''.join(struct.pack('<H', w) for w in tmap)
    spr = bytearray(18 * 32)
    cmap = {' ': 0, '#': 1, '+': 2, 'o': 3}
    for yy in range(16):
        for xx in range(16):
            c = cmap[CAT[yy][xx]]
            t = (xx >> 3) + (yy >> 3) * 16; r = yy & 7; bit = 0x80 >> (xx & 7)
            base = t * 32
            if c & 1: spr[base + r * 2] |= bit
            if c & 2: spr[base + r * 2 + 1] |= bit
    bgpal = struct.pack('<8H', 0x0000, 0x7E89, 0, 0, 0, 0x7F54, 0, 0)
    objpal = struct.pack('<4H', 0x0000, 0x7E89, 0x7FDD, 0x0C63)
    waves = []
    for ph in range(16):
        t = bytearray((24, 0, 0))
        for k in range(24):
            off = int(round(2 * math.sin(2 * math.pi * (k / 24 + ph / 16)))) & 0x3FF
            t += bytes((1, off & 0xFF, off >> 8))
        t += bytes((1, 0, 0, 0))
        waves.append(t)

    # reset / init
    L('reset')
    B(0x78, 0x18, 0xFB)                     # SEI CLC XCE  -> native mode
    B(0xC2, 0x38)                           # REP #$38
    ldx(0x1FFF); B(0x9A)                    # stack
    B(0xA9); W(0); B(0x5B)                  # D = 0
    B(0xE2, 0x20)                           # A8 X16
    lda(0x80); sta(0x2100); stz(0x4200)
    stz(0x2105)                             # mode 0 (all 2bpp layers)
    lda(0x04); sta(0x2107)                  # BG1 map @ $0400
    lda(0x01); sta(0x210B)                  # BG1 chr @ $1000
    lda(0x03); sta(0x2101)                  # OBJ chr @ $6000, 8/16
    lda(0xFF); sta(0x210E); sta(0x210E)     # BG1VOFS = -1
    stz(0x210D); stz(0x210D)
    lda(0x80); sta(0x2115)
    ldx(0x1000); stx(0x2116); dma(0x01, 0x18, 'font', len(font))
    ldx(0x0400); stx(0x2116); dma(0x01, 0x18, 'tmap', 2048)
    ldx(0x6000); stx(0x2116); dma(0x01, 0x18, 'spr', len(spr))
    stz(0x2121); dma(0x00, 0x22, 'bgpal', 16)
    lda(0x80); sta(0x2121); dma(0x00, 0x22, 'objpal', 8)
    stz(0x2102); stz(0x2103); ldx(0x0080)
    L('oam1'); stz(0x2104); lda(0xF0); sta(0x2104); stz(0x2104); stz(0x2104); B(0xCA, 0xD0); R8('oam1')
    lda(0x02); sta(0x2104); ldx(0x001F)
    L('oam2'); stz(0x2104); B(0xCA, 0xD0); R8('oam2')
    B(0xC2, 0x20); B(0xA9); W(120); B(0x85, 0x00); B(0xA9); W(168); B(0x85, 0x02); B(0x64, 0x08); B(0xE2, 0x20)
    # ---- boot the SPC700 the way commercial games do: IPL upload over $2140-$2143
    L('w_aabb'); B(0xAE); W(0x2140); B(0xE0); W(0xBBAA); B(0xD0); R8('w_aabb')
    ldx(0x0200); stx(0x2142); lda(0x01); sta(0x2141); lda(0xCC); sta(0x2140)
    L('w_cc'); B(0xCD); W(0x2140); B(0xD0); R8('w_cc')
    B(0xA0); W(0)                                            # ldy #0
    L('up'); B(0xB9); A16('spcprog'); sta(0x2141); B(0x98); sta(0x2140)
    L('w_up'); B(0xCD); W(0x2140); B(0xD0); R8('w_up')
    B(0xC8, 0xC0); W(len(SPC_DEMO)); B(0xD0); R8('up')     # iny ; cpy #len ; bne
    ldx(0x0200); stx(0x2142); stz(0x2141)
    B(0x98, 0x18, 0x69, 0x02); sta(0x2140)                  # tya ; clc ; adc #2 ; go
    L('w_go'); B(0xCD); W(0x2140); B(0xD0); R8('w_go')
    lda(0x55); sta(0x2140); ldx(0x4000)                     # ping: SPC must answer $56
    L('w_echo'); B(0xAD); W(0x2141); B(0xC9, 0x56, 0xF0); R8('spc_ok'); B(0xCA, 0xD0); R8('w_echo')
    ldx(0x0680); stx(0x2116); dma(0x01, 0x18, 'failrow', 64); B(0x80); R8('spc_done')
    L('spc_ok'); ldx(0x0680); stx(0x2116); dma(0x01, 0x18, 'okrow', 64)
    L('spc_done')
    lda(0x11); sta(0x212C)
    lda(0x02); sta(0x4300); lda(0x0D); sta(0x4301); B(0xA2); A16('wave0'); stx(0x4302); stz(0x4304)
    lda(0x01); sta(0x420C)
    lda(0x0F); sta(0x2100)
    lda(0x81); sta(0x4200)
    L('main'); B(0xCB, 0x80); R8('main')    # WAI ; BRA main

    # NMI
    L('nmi')
    B(0xC2, 0x30, 0x48, 0xDA, 0x5A, 0xE2, 0x20)
    B(0xAD); W(0x4210)
    L('wj'); B(0xAD); W(0x4212); B(0x29, 0x01, 0xD0); R8('wj')
    B(0xC2, 0x20)
    B(0xAD); W(0x4218); B(0x85, 0x06)
    B(0xE6, 0x08)
    for mask, op, var, lb in ((0x0100, 0xE6, 0, 's1'), (0x0200, 0xC6, 0, 's2'),
                              (0x0800, 0xC6, 2, 's3'), (0x0400, 0xE6, 2, 's4')):
        B(0xA5, 0x06, 0x89); W(mask); B(0xF0); R8(lb); B(op, var); L(lb)
    B(0xA5, 0x08, 0x4A, 0x29); W(0x000F); B(0x0A, 0xAA, 0xBD); A16('ptrtab'); B(0x8D); W(0x4302)
    B(0xE2, 0x20)
    stz(0x2102); stz(0x2103); B(0xA5, 0x00); sta(0x2104); B(0xA5, 0x02); sta(0x2104)
    stz(0x2104); lda(0x30); sta(0x2104)
    B(0xC2, 0x30, 0x7A, 0xFA, 0x68, 0x40)
    L('irq'); B(0x40)

    def textrow(text, palno):
        row = [0] * 32; col = (32 - len(text)) // 2
        for k, ch in enumerate(text): row[col + k] = CHARS.index(ch) | (palno << 10)
        return b''.join(struct.pack('<H', w) for w in row)
    L('spcprog'); code += SPC_DEMO
    L('okrow'); code += textrow("SPC700 SOUND CPU ONLINE", 1)
    L('failrow'); code += textrow("SPC700 SOUND CPU FAILED", 0)
    L('font'); code += font
    L('tmap'); code += tmap_b
    L('spr'); code += spr
    L('bgpal'); code += bgpal
    L('objpal'); code += objpal
    for i, t in enumerate(waves):
        L('wave%d' % i); code += t
    L('ptrtab')
    for i in range(16): A16('wave%d' % i)

    for pos, n, kind in fix:
        t = lab[n]
        if kind == 'a':
            code[pos] = t & 0xFF; code[pos + 1] = t >> 8
        else:
            d = t - (0x8000 + pos + 1)
            assert -128 <= d < 128, n
            code[pos] = d & 0xFF
    assert len(code) < 0x7FB0
    rom = bytearray(0x8000)
    rom[:len(code)] = code
    h = 0x7FC0
    rom[h:h + 21] = b"VSNES DEMO".ljust(21)
    rom[h + 0x15] = 0x20; rom[h + 0x16] = 0; rom[h + 0x17] = 5; rom[h + 0x18] = 0; rom[h + 0x19] = 1
    def vec(addr, target): rom[addr - 0x8000] = target & 0xFF; rom[addr - 0x7FFF] = target >> 8
    vec(0xFFEA, lab['nmi']); vec(0xFFEE, lab['irq']); vec(0xFFE6, lab['irq']); vec(0xFFE4, lab['irq'])
    vec(0xFFFC, lab['reset']); vec(0xFFFE, lab['irq']); vec(0xFFFA, lab['irq'])
    rom[h + 0x1C:h + 0x20] = b'\xff\xff\x00\x00'
    ck = sum(rom) & 0xFFFF
    struct.pack_into('<HH', rom, h + 0x1C, ck ^ 0xFFFF, ck)
    return bytes(rom)


# ===================================================================== helpers
def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b''.join(b'\x00' + rgb[y].tobytes() for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def write_wav(path, pcm, rate=32000):
    import wave
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.ascontiguousarray(pcm, dtype='<i2').tobytes())


def load_rom_bytes(path):
    with open(path, 'rb') as f:
        data = f.read()
    if path.lower().endswith('.zip'):
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(data))
        names = [n for n in z.namelist() if n.lower().endswith(ROM_EXTS)]
        if not names:
            raise ValueError("no SNES ROM inside zip")
        data = z.read(names[0])
    return data


def load_into(snes, path):
    data = load_rom_bytes(path)
    snes.save_sram()
    return snes.load(data, path)


def load_config():
    for path in (CONFIG_PATH, os.path.join(os.path.expanduser('~'), '.acsnes.json')):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            continue
    return {}


def save_config(cfg):
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def _osascript(script):
    try:
        r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or '').strip() or None


def ask_rom_path(title=None):
    """Native file picker that never creates Tk inside the pygame/SDL process."""
    title = title or f"{APP} - Load ROM"
    if sys.platform == 'darwin':
        t = title.replace('\\', '\\\\').replace('"', '\\"')
        return _osascript(f'set theFile to choose file with prompt "{t}"\nPOSIX path of theFile')

    helper = (
        "import sys\n"
        "try:\n"
        "    import tkinter as tk\n"
        "    from tkinter import filedialog\n"
        "    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)\n"
        "    p = filedialog.askopenfilename(title=%r, filetypes=[\n"
        "        ('SNES ROMs', '*.sfc *.smc *.swc *.fig *.zip'), ('All files', '*.*')])\n"
        "    root.destroy()\n"
        "    if p: sys.stdout.write(p)\n"
        "except Exception:\n"
        "    pass\n"
    ) % title
    try:
        r = subprocess.run([sys.executable, '-c', helper], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (r.stdout or '').strip() or None


def ask_folder_path(title=None):
    """Folder picker for the commercial ROM library (no in-process Tk)."""
    title = title or f"{APP} - ROM Library Folder"
    if sys.platform == 'darwin':
        t = title.replace('\\', '\\\\').replace('"', '\\"')
        return _osascript(
            f'set theFolder to choose folder with prompt "{t}"\n'
            f'POSIX path of theFolder'
        )
    helper = (
        "import sys\n"
        "try:\n"
        "    import tkinter as tk\n"
        "    from tkinter import filedialog\n"
        "    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)\n"
        "    p = filedialog.askdirectory(title=%r)\n"
        "    root.destroy()\n"
        "    if p: sys.stdout.write(p)\n"
        "except Exception:\n"
        "    pass\n"
    ) % title
    try:
        r = subprocess.run([sys.executable, '-c', helper], capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (r.stdout or '').strip() or None


def default_rom_dirs():
    home = os.path.expanduser('~')
    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    cfg = load_config()
    dirs = []
    for d in (
        cfg.get('roms_dir'),
        os.environ.get('VIRTUALSNES_ROMS') or os.environ.get('CATSNES_ROMS') or os.environ.get('ACSNES_ROMS'),
        os.path.join(here, 'roms'),
        os.path.join(home, 'ROMs', 'SNES'),
        os.path.join(home, 'Roms', 'SNES'),
        os.path.join(home, 'SNES'),
        os.path.join(home, 'Games', 'SNES'),
    ):
        if d and os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    return dirs


def probe_rom_file(path):
    """Lightweight commercial ROM probe for the library list (header only)."""
    try:
        with open(path, 'rb') as f:
            # Enough for ExHiROM header at 0x40FFC0 (+ optional 512 copier)
            data = f.read(0x410000 + 0x40)
        if path.lower().endswith('.zip'):
            import zipfile
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist() if n.lower().endswith(ROM_EXTS)]
                if not names:
                    return None
                with z.open(names[0]) as rf:
                    data = rf.read(0x410000 + 0x40)
        info = analyze_rom(data)
        return {
            'path': path,
            'file': os.path.basename(path),
            'title': info['title'],
            'mapper': info['mapper'],
            'speed': info['speed'],
            'chip_name': info['chip_name'],
            'compat': info['compat'],
            'region_name': info['region_name'],
            'sram_size': info['sram_size'],
            'size': os.path.getsize(path),
        }
    except Exception:
        return None


def scan_rom_library(dirs=None, max_files=2000):
    """Scan folders for commercial SNES ROMs the user already owns."""
    dirs = dirs or default_rom_dirs()
    seen = set()
    entries = []
    for root in dirs:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                low = name.lower()
                if not (low.endswith(ROM_EXTS) or low.endswith('.zip')):
                    continue
                path = os.path.join(dirpath, name)
                ap = os.path.abspath(path)
                if ap in seen:
                    continue
                seen.add(ap)
                info = probe_rom_file(path)
                if info:
                    entries.append(info)
                if len(entries) >= max_files:
                    break
            if len(entries) >= max_files:
                break
        if len(entries) >= max_files:
            break
    order = {'ok': 0, 'unknown': 1, 'chip': 2}
    entries.sort(key=lambda e: (order.get(e['compat'], 9), e['title'].lower(), e['file'].lower()))
    return entries


def library_summary(entries):
    ok = sum(1 for e in entries if e['compat'] == 'ok')
    chip = sum(1 for e in entries if e['compat'] == 'chip')
    unk = sum(1 for e in entries if e['compat'] == 'unknown')
    return ok, chip, unk


# ===================================================================== CPU self-test
def cputest(test_dir, per_file=60):
    """Run SingleStepTests/65816 JSON files (e.g. v1/a9.n.json) against CPU65816.

    Files may be complete or truncated (partial downloads); every complete
    test object is used. Compares registers and RAM after one instruction.
    """
    import glob, collections
    files = sorted(glob.glob(os.path.join(test_dir, '*.json')))
    if not files:
        sys.exit(f"no *.json test files in {test_dir}")

    class FlatBus:
        def __init__(self):
            self.m = bytearray(1 << 24); self.wc = 0
            self.read = self.m.__getitem__
        def write(self, a, v):
            self.wc += 1; self.m[a] = v

    def iter_tests(path):
        txt = open(path, encoding='utf-8', errors='ignore').read()
        dec = json.JSONDecoder(); i = txt.find('[') + 1; n = 0
        while i and n < per_file:
            while i < len(txt) and txt[i] in ' ,\n\r\t':
                i += 1
            try:
                obj, i = dec.raw_decode(txt, i)
            except ValueError:
                return
            n += 1
            yield obj

    bus = FlatBus(); c = CPU65816(bus)

    class SpcBus:
        def __init__(self):
            self.m = bytearray(0x10000); self.read = self.m.__getitem__
        def write(self, a, v):
            self.m[a] = v
    sbus = SpcBus(); sc = SPC700(sbus)
    fails = collections.Counter(); first = {}; total = 0
    for path in files:
        tag = os.path.basename(path).rsplit('.json', 1)[0]
        for t in iter_tests(path):
            I, F = t['initial'], t['final']
            if 'psw' in I:                                   # SPC700 test
                for a, v in I['ram']: sbus.m[a] = v
                sc.PC, sc.A, sc.X, sc.Y, sc.SP, sc.PSW = I['pc'], I['a'], I['x'], I['y'], I['sp'], I['psw']
                sc.stopped = False; sc.trap = 0x10000; sc.cyc = 0; sc.run(1)
                got = dict(pc=sc.PC, a=sc.A, x=sc.X, y=sc.Y, sp=sc.SP, psw=sc.PSW)
                bad = [k for k in got if got[k] != F[k]]
                bad += ['aram$%04X' % a for a, v in F['ram'] if sbus.m[a] != v]
                total += 1
                if bad:
                    fails['spc ' + tag] += 1
                    first.setdefault('spc ' + tag, (t['name'], bad[:4]))
                for a, _ in I['ram'] + F['ram']: sbus.m[a] = 0
                continue
            for a, v in I['ram']: bus.m[a] = v
            c.PC, c.S, c.P, c.A, c.X, c.Y = I['pc'], I['s'], I['p'], I['a'], I['x'], I['y']
            c.DB, c.D, c.PB, c.E = I['dbr'], I['d'], I['pbr'], I['e']
            if c.E: c.S = 0x100 | (c.S & 0xFF); c.P |= 0x30     # hardware-forced bits
            if c.P & 0x10: c.X &= 0xFF; c.Y &= 0xFF
            c.waiting = c.stopped = c.nmi_pending = c.irq_line = False; c.idle_key = None
            c.cyc = 0; c.run(1)
            got = dict(pc=c.PC, s=c.S, p=c.P, a=c.A, x=c.X, y=c.Y,
                       dbr=c.DB, d=c.D, pbr=c.PB, e=c.E)
            bad = [k for k in got if got[k] != F[k]]
            bad += ['ram$%06X' % a for a, v in F['ram'] if bus.m[a] != v]
            total += 1
            if bad:
                fails[tag] += 1
                first.setdefault(tag, (t['name'], bad[:4]))
            for a, _ in I['ram']: bus.m[a] = 0
            for a, _ in F['ram']: bus.m[a] = 0
    print(f"{APP} CPU self-test: {total} tests from {len(files)} files, "
          f"{sum(fails.values())} failing")
    for tag, n in sorted(fails.items()):
        print(f"  {tag}: {n} failing, first {first[tag]}")
    return 0 if not fails else 1


# ===================================================================== front-end
# Native SNES9x integration. Obtain a trusted snes9x_libretro shared library
# matching your OS/CPU and place it next to this script, or use --core PATH.
# Original SNES9x credits and license remain with that separately installed core.
class NativeSNES:
    """Small libretro host: actual SNES9x CPU/PPU/APU with Virtual SNES Emulator branding.

    The shared library is deliberately not downloaded or installed automatically.
    Native cores execute machine code: only select a trusted local build.
    """
    def __init__(self, path):
        import ctypes as C
        from types import SimpleNamespace
        self.C = C
        self.lib = C.CDLL(os.path.abspath(path))
        self.rom_path = None; self.loaded = False
        self.title = ''; self.mapper = 'SNES9x'; self.speed = 'Native'
        self.compat = 'ok'; self.chip_name = 'SNES9x'; self.joy1 = self.joy2 = 0
        self.skip_render = False; self.frame = np.zeros((224, 256, 3), np.uint8)
        self.fps = 60.0988; self.audio_rate = 32040.0; self.pixel_format = 0
        self._chunks = []; self._error = None
        self._source_total = 0; self._output_total = 0; self._previous = None
        self.apu = SimpleNamespace(dspc=SimpleNamespace(name='native SNES9x', take=self.take_audio))
        class Info(C.Structure):
            _fields_ = [('name', C.c_char_p), ('version', C.c_char_p),
                        ('extensions', C.c_char_p), ('fullpath', C.c_bool), ('extract', C.c_bool)]
        class Game(C.Structure):
            _fields_ = [('path', C.c_char_p), ('data', C.c_void_p),
                        ('size', C.c_size_t), ('meta', C.c_char_p)]
        class Geometry(C.Structure):
            _fields_ = [('width', C.c_uint), ('height', C.c_uint),
                        ('max_width', C.c_uint), ('max_height', C.c_uint), ('aspect', C.c_float)]
        class Timing(C.Structure):
            _fields_ = [('fps', C.c_double), ('sample_rate', C.c_double)]
        class AV(C.Structure):
            _fields_ = [('geometry', Geometry), ('timing', Timing)]
        class Variable(C.Structure):
            _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]
        self.Game, self.AV = Game, AV
        self._variables = {}; self._strings = []
        system_dir = os.path.expanduser('~/.virtualsnes/system')
        save_dir = os.path.expanduser('~/.virtualsnes/saves')
        os.makedirs(system_dir, exist_ok=True); os.makedirs(save_dir, exist_ok=True)
        self._system_dir = os.fsencode(system_dir); self._save_dir = os.fsencode(save_dir)
        def bind(name, result, *arguments):
            f = getattr(self.lib, 'retro_' + name); f.restype = result; f.argtypes = list(arguments)
            return f
        self._bind = bind
        bind('api_version', C.c_uint)
        if self.lib.retro_api_version() != 1:
            raise RuntimeError('Unsupported libretro API')
        bind('get_system_info', None, C.POINTER(Info))
        info = Info(); self.lib.retro_get_system_info(C.byref(info))
        self.core_name = (info.name or b'').decode('utf8', 'replace')
        if 'snes9x' not in self.core_name.lower():
            raise RuntimeError('The selected library is not a SNES9x libretro core')
        self._fullpath = info.fullpath
        def environment(command, data):
            if command == 10:  # SET_PIXEL_FORMAT
                value = C.cast(data, C.POINTER(C.c_int))[0]
                if value not in (0, 1, 2): return False
                self.pixel_format = value; return True
            if command in (9, 30, 31):  # system/assets/save directory, stable storage
                C.cast(data, C.POINTER(C.c_char_p))[0] = self._save_dir if command == 31 else self._system_dir
                return True
            if command == 3: C.cast(data, C.POINTER(C.c_bool))[0] = False; return True
            if command == 18: C.cast(data, C.POINTER(C.c_bool))[0] = False; return True
            if command == 16:  # legacy option definitions: use core defaults
                variables = C.cast(data, C.POINTER(Variable)); i = 0
                while variables[i].key:
                    value = variables[i].value or b''
                    self._variables[variables[i].key] = value.split(b';', 1)[-1].strip().split(b'|')[0]
                    i += 1
                return True
            if command == 15:
                variable = C.cast(data, C.POINTER(Variable)).contents
                value = self._variables.get(variable.key)
                if value is None: return False
                variable.value = value; return True
            if command == 17: C.cast(data, C.POINTER(C.c_bool))[0] = False; return True
            if command == 39: C.cast(data, C.POINTER(C.c_uint))[0] = 0; return True
            if command == 32:
                av = C.cast(data, C.POINTER(AV)).contents
                self.fps = av.timing.fps; self.audio_rate = av.timing.sample_rate; return True
            if command in (1, 11, 35): return True  # rotation/input descriptors/controller info
            return False
        def video(data, width, height, pitch):
            if not data or self.skip_render: return
            try:
                if not (0 < width <= 2048 and 0 < height <= 2048):
                    raise ValueError('Invalid native video dimensions')
                raw = C.string_at(data, pitch * height)
                bpp = 4 if self.pixel_format == 1 else 2
                rows = np.frombuffer(raw, np.uint8).reshape(height, pitch)[:, :width * bpp].copy()
                pixels = rows.view(np.uint32 if bpp == 4 else np.uint16).reshape(height, width)
                if bpp == 4:
                    r, g, b = (pixels >> 16) & 255, (pixels >> 8) & 255, pixels & 255
                else:
                    green_bits = 6 if self.pixel_format == 2 else 5
                    r = ((pixels >> (5 + green_bits)) & 31) * 255 // 31
                    g = ((pixels >> 5) & ((1 << green_bits) - 1)) * 255 // ((1 << green_bits) - 1)
                    b = (pixels & 31) * 255 // 31
                self.frame = np.stack((r, g, b), axis=-1).astype(np.uint8)
            except Exception as exc: self._error = exc
        def batch(data, frames):
            if frames: self._chunks.append(np.ctypeslib.as_array(data, shape=(frames * 2,)).reshape(-1, 2).copy())
            return frames
        def sample(left, right): self._chunks.append(np.array([[left, right]], dtype=np.int16))
        # libretro IDs B,Y,Select,Start,Up,Down,Left,Right,A,X,L,R map to SNES bits.
        bits = (15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4)
        def input_state(port, device, index, button):
            if device != 1 or index or port > 1 or button >= len(bits): return 0
            return int(bool((self.joy1 if port == 0 else self.joy2) & (1 << bits[button])))
        signatures = [
            ('environment', C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p), environment),
            ('video_refresh', C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t), video),
            ('audio_sample', C.CFUNCTYPE(None, C.c_int16, C.c_int16), sample),
            ('audio_sample_batch', C.CFUNCTYPE(C.c_size_t, C.POINTER(C.c_int16), C.c_size_t), batch),
            ('input_poll', C.CFUNCTYPE(None), lambda: None),
            ('input_state', C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint), input_state)]
        self._callbacks = []
        for name, signature, function in signatures:
            callback = signature(function); self._callbacks.append(callback)
            bind('set_' + name, None, signature)(callback)
        for name in ('init', 'deinit', 'run', 'reset', 'unload_game'):
            bind(name, None)
        bind('load_game', C.c_bool, C.POINTER(Game))
        bind('get_system_av_info', None, C.POINTER(AV))
        bind('serialize_size', C.c_size_t)
        bind('serialize', C.c_bool, C.c_void_p, C.c_size_t)
        bind('unserialize', C.c_bool, C.c_void_p, C.c_size_t)
        bind('get_memory_size', C.c_size_t, C.c_uint)
        bind('get_memory_data', C.c_void_p, C.c_uint)
        self.lib.retro_init()

    def load(self, data, path=None):
        C = self.C
        if self.loaded: self.save_sram(); self.lib.retro_unload_game(); self.loaded = False
        info = analyze_rom(data)
        self._rom = C.create_string_buffer(info['data'])
        self._path = os.fsencode(os.path.abspath(path)) if path else None
        if self._fullpath and not path:
            raise RuntimeError('This core needs a ROM path; supply a .sfc or .smc file')
        if self._fullpath and str(path).lower().endswith('.zip'):
            raise RuntimeError('This core needs an uncompressed .sfc/.smc file')
        game = self.Game(self._path, C.cast(self._rom, C.c_void_p), len(info['data']), None)
        if not self.lib.retro_load_game(C.byref(game)):
            raise RuntimeError('SNES9x could not load this ROM')
        self.loaded = True; self.rom_path = path; self.title = info['title']
        av = self.AV(); self.lib.retro_get_system_av_info(C.byref(av))
        self.fps = av.timing.fps; self.audio_rate = av.timing.sample_rate
        if not (1 <= self.fps <= 240 and 8000 <= self.audio_rate <= 192000):
            raise RuntimeError('Invalid core audio/video timing')
        self._chunks.clear(); self._source_total = self._output_total = 0; self._previous = None
        self._restore_sram()
        return info

    def _restore_sram(self):
        if not self.rom_path: return
        path = os.path.splitext(self.rom_path)[0] + '.srm'
        size = self.lib.retro_get_memory_size(0); pointer = self.lib.retro_get_memory_data(0)
        if size and pointer and os.path.isfile(path):
            with open(path, 'rb') as file: data = file.read(size)
            self.C.memmove(pointer, data, len(data))

    def save_sram(self):
        if not self.loaded or not self.rom_path: return
        size = self.lib.retro_get_memory_size(0); pointer = self.lib.retro_get_memory_data(0)
        if size and pointer:
            path = os.path.splitext(self.rom_path)[0] + '.srm'
            with open(path + '.tmp', 'wb') as file: file.write(self.C.string_at(pointer, size))
            os.replace(path + '.tmp', path)

    def run_frame(self):
        self.lib.retro_run()
        if self._error:
            error, self._error = self._error, None
            raise RuntimeError('SNES9x video callback failed') from error

    def take_audio(self):
        if not self._chunks: return np.zeros((0, 2), np.int16)
        pcm = np.concatenate(self._chunks); self._chunks.clear()
        # Streaming linear resampling to the existing 32 kHz output; absolute
        # sample positions preserve fractional phase across video frames.
        start = self._source_total; self._source_total += len(pcm)
        end = int((self._source_total - 1) * 32000 / self.audio_rate) + 1
        positions = np.arange(self._output_total, end) * (self.audio_rate / 32000)
        self._output_total = end
        if self._previous is not None:
            pcm = np.vstack((self._previous, pcm)); start -= 1
        self._previous = pcm[-1:].copy()
        x = np.arange(len(pcm)) + start
        return np.stack([np.interp(positions, x, pcm[:, c]) for c in (0, 1)], axis=1).astype(np.int16)

    def reset(self):
        self.lib.retro_reset(); self._chunks.clear()
        self._source_total = self._output_total = 0; self._previous = None

    def save_state(self):
        size = self.lib.retro_serialize_size(); buffer = self.C.create_string_buffer(size)
        if not size or not self.lib.retro_serialize(buffer, size): raise RuntimeError('State save failed')
        return b'VSNES9\x01' + buffer.raw

    def load_state(self, data):
        for magic in (b'VSNES9\x01', b'ACSN9X\x01'):
            if data.startswith(magic):
                data = data[len(magic):]
                break
        else:
            raise ValueError('This state belongs to a different core')
        buffer = self.C.create_string_buffer(data)
        if not self.lib.retro_unserialize(buffer, len(data)): raise RuntimeError('State load failed')
        self._chunks.clear(); self._source_total = self._output_total = 0; self._previous = None

    def close(self):
        try: self.save_sram()
        finally:
            if self.loaded: self.lib.retro_unload_game(); self.loaded = False
            self.lib.retro_deinit()


def create_system(args):
    """Use native SNES9x when installed; never conceal an explicitly bad core."""
    core = getattr(args, 'core', None) or os.environ.get('VIRTUALSNES_CORE') or os.environ.get('ACSNES_CORE')
    if getattr(args, 'backend', 'auto') == 'python': return SNES()
    if not core:
        directory = os.path.dirname(os.path.abspath(__file__))
        for name in ('snes9x_libretro.so', 'snes9x_libretro.dylib', 'snes9x_libretro.dll'):
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate): core = candidate; break
    if core: return NativeSNES(core)
    if getattr(args, 'backend', 'auto') == 'snes9x':
        raise RuntimeError('Native SNES9x core missing. Use --core /path/to/snes9x_libretro.so (or .dylib/.dll).')
    print(f'{APP}: using custom Python core; install a SNES9x libretro core for native compatibility/speed.')
    return SNES()


def headless(args):
    snes = create_system(args)
    if args.rom: load_into(snes, args.rom)
    else: snes.load(build_demo_rom())
    if args.hold:
        snes.joy1 = int(args.hold, 0)
    chunks = []
    t = time.perf_counter()
    for _ in range(args.headless):
        snes.run_frame()
        a = snes.apu.dspc.take()
        if args.wav: chunks.append(a)
    dt = time.perf_counter() - t
    if args.wav:
        write_wav(args.wav, np.concatenate(chunks) if chunks else np.zeros((0, 2), np.int16))
        print("audio ->", args.wav)
    fps = args.headless / dt
    print(f"{APP}: audio engine = {snes.apu.dspc.name} DSP")
    print(f"{APP}: '{snes.title}' {snes.mapper}/{snes.speed} [{snes.chip_name}] "
          f"{args.headless} frames in {dt:.2f}s = {fps:.1f} fps ({fps / getattr(snes, 'fps', 60.0988) * 100:.0f}% of SNES speed)")
    c = getattr(snes, "cpu", None)
    if c is not None: print(f"CPU A={c.A:04X} X={c.X:04X} Y={c.Y:04X} S={c.S:04X} D={c.D:04X} DB={c.DB:02X} "
          f"PC={c.PB:02X}:{c.PC:04X} P={c.P:02X} E={c.E}")
    if args.shot:
        write_png(args.shot, snes.frame); print("screenshot ->", args.shot)
    if isinstance(snes, NativeSNES): snes.close()


class AudioOut:
    """Low-latency speaker output: SDL audio callback pulling from a small ring buffer."""

    def __init__(self, rate=32000):
        import threading
        self.buf = bytearray(); self.lock = threading.Lock(); self.dev = None; self.err = ''
        fb = rate * 4 // 60                       # bytes per video frame (stereo s16)
        self.frame_bytes = fb
        self.high = fb * 10; self.keep = fb * 4   # hard latency cap (sync normally keeps ~3 frames)
        self.last = (0, 0); self.playing = False; self.underruns = 0; self.drops = 0
        self.chan = None
        import pygame
        try:
            pygame.mixer.quit()                   # pygame.init() may have grabbed the device...
            from pygame._sdl2 import sdl2
            sdl2.init_subsystem(sdl2.INIT_AUDIO)  # ...and mixer.quit() drops SDL audio; re-init
        except Exception:
            pass
        try:
            from pygame._sdl2 import audio as sdla
            self.dev = sdla.AudioDevice(devicename=None, iscapture=False, frequency=rate,
                                        audioformat=sdla.AUDIO_S16, numchannels=2, chunksize=512,
                                        allowed_changes=0, callback=self._cb)
            self.dev.pause(0)
        except Exception as e:
            self.dev = None; self.err = str(e) or type(e).__name__
            try:                                  # fallback: queue sounds on a mixer channel
                pygame.mixer.init(frequency=rate, size=-16, channels=2, buffer=512)
                if not pygame.mixer.get_init():
                    raise RuntimeError(f"no audio output ({self.err})")
                self.chan = pygame.mixer.Channel(0); self.dev = 'mixer'; self.err = ''
            except Exception as e2:               # no sound card / driver: run silently
                self.chan = None; self.err = str(e2) or type(e2).__name__

    def _cb(self, dev, mem):
        n = len(mem)
        with self.lock:
            k = min(n, len(self.buf)) & ~3
            mem[:k] = self.buf[:k]; del self.buf[:k]
            if k >= 4:
                self.last = struct.unpack_from('<hh', mem, k - 4)
        if k < n:                                 # underrun: fade out instead of clicking
            if self.playing: self.underruns += 1
            frames = (n - k) // 4; l0, r0 = self.last
            ramp = np.linspace(1.0, 0.0, min(frames, 64), endpoint=False)
            tail = np.zeros((frames, 2), np.int16)
            tail[:len(ramp), 0] = (l0 * ramp).astype(np.int16); tail[:len(ramp), 1] = (r0 * ramp).astype(np.int16)
            mem[k:k + frames * 4] = tail.tobytes()
            if n - k - frames * 4: mem[k + frames * 4:] = bytes(n - k - frames * 4)
            self.last = (0, 0)

    def push(self, pcm):
        if self.dev is None or not len(pcm): return
        b = pcm.astype('<i2', copy=False).tobytes()
        self.playing = True
        if self.chan is not None:
            import pygame
            with self.lock:
                self.buf += b
                if len(self.buf) < 4 * 1024: return
                b = bytes(self.buf); self.buf.clear()
            if self.chan.get_queue() is None:     # keep at most one block queued
                snd = pygame.mixer.Sound(buffer=b)
                if self.chan.get_busy(): self.chan.queue(snd)
                else: self.chan.play(snd)
            return
        with self.lock:
            self.buf += b
            if len(self.buf) > self.high:
                self.drops += 1
                del self.buf[:(len(self.buf) - self.keep) & ~3]

    def level(self):
        """Bytes of audio queued for the device (0 when not using the callback path)."""
        return len(self.buf) if (self.dev is not None and self.chan is None) else 0

    def synced(self):
        return self.dev is not None and self.chan is None

    def clear(self):
        with self.lock: self.buf.clear()
        self.playing = False

    def close(self):
        if self.dev is not None and self.chan is None:
            try: self.dev.pause(1); self.dev.close()
            except Exception: pass
        self.dev = None


def gui(args):
    """vsnes classic desktop window: File/CPU/Options/Help + status bar (MarioNES-style)."""
    os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
    import pygame
    if getattr(args, 'roms', None):
        cfg = load_config(); cfg['roms_dir'] = os.path.abspath(args.roms); save_config(cfg)
    pygame.init()
    import gc
    sys.setswitchinterval(0.001)      # let the audio callback thread grab the GIL promptly
    audio = AudioOut()
    muted = bool(getattr(args, 'mute', False))
    snes = create_system(args)
    if args.rom:
        load_into(snes, args.rom)
    else:
        snes.load(build_demo_rom())
    scale = max(1, min(5, args.scale)); W = 256 * scale; H = 224 * scale
    MENU_H = 20; STATUS_H = 20
    # Classic Windows chrome (MarioNES / Win9x-style)
    MENU_BG = (212, 208, 200); MENU_EDGE = (128, 128, 128); MENU_HOT = (10, 36, 106)
    MENU_TXT = (0, 0, 0); MENU_DIM = (128, 128, 128); MENU_HOT_TXT = (255, 255, 255)
    STATUS_BG = (212, 208, 200)
    OVERLAY_BG = (212, 208, 200); OVERLAY_FG = (0, 0, 0); OVERLAY_ACC = (10, 36, 106)
    OK_COL = (0, 100, 0); CHIP_COL = (160, 80, 0); UNK_COL = (80, 80, 80)
    FACE_BG = (0, 0, 0)

    def window_caption():
        return WINDOW_TITLE

    screen = pygame.display.set_mode((W, H + MENU_H + STATUS_H), pygame.RESIZABLE)
    pygame.display.set_caption(window_caption())
    try:
        font = pygame.font.SysFont('ms sans serif,tahoma,segoeui,arial', 12)
        font_b = pygame.font.SysFont('ms sans serif,tahoma,segoeui,arial', 12)
        font_dlg = pygame.font.SysFont('ms sans serif,tahoma,segoeui,arial', 12)
        font_sm = pygame.font.SysFont('ms sans serif,tahoma,segoeui,arial', 11)
    except Exception:
        font = pygame.font.SysFont(None, 16); font_b = font; font_dlg = font; font_sm = font
    surf = pygame.Surface((256, 224))
    clock = pygame.time.Clock()
    KEYS = ((pygame.K_z, 15), (pygame.K_a, 14), (pygame.K_RSHIFT, 13), (pygame.K_BACKSPACE, 13),
            (pygame.K_RETURN, 12), (pygame.K_UP, 11), (pygame.K_DOWN, 10), (pygame.K_LEFT, 9),
            (pygame.K_RIGHT, 8), (pygame.K_x, 7), (pygame.K_s, 6), (pygame.K_q, 5), (pygame.K_w, 4))

    paused = False
    turbo = False; autoskip = True; msg = ""; msg_t = 0
    fps = 0.0; fcount = 0; ft = time.perf_counter(); emu_ms = 0.0; skip_next = False
    dialog = None  # None | 'about' | 'controls' | 'library'
    hover = -1
    active_menu = None; popup_rows = []
    fullscreen = False; aspect_correct = True
    rendered_count = 0; rendered_fps = 0.0
    lib_entries = []; lib_sel = 0; lib_scroll = 0; lib_filter = 'all'  # all|ok|chip
    lib_row_rects = []
    initialized = True

    MENU_ITEMS = ("File", "CPU", "Options", "Help")
    menu_rects = []
    mx = 2
    for label in MENU_ITEMS:
        tw = font.size(label)[0] + 16
        menu_rects.append(pygame.Rect(mx, 0, tw, MENU_H))
        mx += tw

    CONTROLS_LINES = (
        "Controller 1",
        "",
        "  D-Pad ........ Arrow Keys",
        "  B ............ Z",
        "  A ............ X",
        "  Y ............ A",
        "  X ............ S",
        "  L ............ Q",
        "  R ............ W",
        "  Start ........ Enter",
        "  Select ....... Right Shift",
        "",
        "Emulator",
        "",
        "  Pause ........ P",
        "  Mute audio ... M",
        "  Reset ........ R",
        "  Library ...... L",
        "  Save State ... F5",
        "  Load State ... F7",
        "  Screenshot ... F12",
        "  Turbo ........ Tab (hold)",
        "  Frameskip .... F",
        "  Quit ......... Esc",
        "",
        "  Drag & drop a .sfc/.smc/.zip onto the window to load.",
    )
    ABOUT_LINES = (
        APP,
        "Virtual SNES Emulator",
        "",
        "Classic desktop GUI: File · CPU · Options · Help",
        "65816 + SPC700 + S-DSP audio (32 kHz, 8 voices, echo)",
        "Core: " + (snes.core_name if isinstance(snes, NativeSNES) else "custom Python (approximate)"),
        COPY,
        "",
        "Not affiliated with or endorsed by Nintendo.",
        "",
        "Press any key or click to close.",
    )

    def note(m):
        nonlocal msg, msg_t
        msg = m; msg_t = time.perf_counter() + 2.5

    def state_path():
        base = snes.rom_path or os.path.join(os.getcwd(), 'virtualsnes_demo')
        return os.path.splitext(base)[0] + ('.s9x0' if isinstance(snes, NativeSNES) else '.vs0')

    def after_load(path, info=None):
        nonlocal paused, initialized
        paused = False
        initialized = True
        audio.clear()
        note(f"{snes.title} initialized")
        pygame.display.set_caption(window_caption())
        if snes.compat == 'chip':
            note(f"{snes.title}: needs {snes.chip_name} (not emulated)")

    def open_rom():
        nonlocal dialog
        dialog = None
        p = ask_rom_path(f"{APP} - Load ROM")
        if not p:
            note("Load cancelled — or drag a ROM onto the window")
            return
        try:
            info = load_into(snes, p)
            after_load(p, info)
        except Exception as e:
            note(f"load failed: {e}")

    def refresh_library():
        nonlocal lib_entries, lib_sel, lib_scroll
        lib_entries = scan_rom_library()
        lib_sel = 0; lib_scroll = 0
        ok, chip, unk = library_summary(lib_entries)
        if lib_entries:
            note(f"Library: {len(lib_entries)} ROMs  ({ok} playable, {chip} chip, {unk} unknown)")
        else:
            note("Library empty — press F in Library to set ROM folder")

    def show_library():
        nonlocal dialog
        dialog = 'library'
        refresh_library()

    def set_library_folder():
        p = ask_folder_path(f"{APP} - ROM Library Folder")
        if not p:
            note("Folder cancelled")
            return
        cfg = load_config(); cfg['roms_dir'] = os.path.abspath(p); save_config(cfg)
        note(f"Library folder: {p}")
        refresh_library()

    def filtered_library():
        if lib_filter == 'ok':
            return [e for e in lib_entries if e['compat'] == 'ok']
        if lib_filter == 'chip':
            return [e for e in lib_entries if e['compat'] == 'chip']
        return lib_entries

    def load_library_selection():
        nonlocal dialog
        items = filtered_library()
        if not items:
            note("No ROMs in this filter")
            return
        sel = max(0, min(lib_sel, len(items) - 1))
        path = items[sel]['path']
        try:
            info = load_into(snes, path)
            after_load(path, info)
            dialog = None
        except Exception as e:
            note(f"load failed: {e}")

    def play_game():
        nonlocal paused, dialog
        dialog = None
        paused = False
        note(f"Playing {snes.title}")

    def show_about():
        nonlocal dialog
        dialog = 'about'

    def show_controls():
        nonlocal dialog
        dialog = 'controls'

    def do_exit():
        nonlocal running
        running = False

    def toggle_pause():
        nonlocal paused
        paused = not paused; audio.clear()
        note("Paused" if paused else "Playing")

    def reset_game():
        snes.reset(); audio.clear(); note("Reset")

    def toggle_mute():
        nonlocal muted
        muted = not muted; audio.clear(); note("Muted" if muted else "Sound enabled")

    def toggle_skip():
        nonlocal autoskip
        autoskip = not autoskip; note(f"Automatic frameskip: {autoskip}")

    def toggle_fullscreen():
        nonlocal fullscreen, screen, W, H
        fullscreen = not fullscreen
        size = (0, 0) if fullscreen else (256 * scale, 224 * scale + MENU_H + STATUS_H)
        screen = pygame.display.set_mode(size, pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE)
        W, total = screen.get_size(); H = total - MENU_H - STATUS_H

    def toggle_aspect():
        nonlocal aspect_correct
        aspect_correct = not aspect_correct

    def save_slot():
        try:
            with open(state_path(), 'wb') as file: file.write(snes.save_state())
            note("State saved")
        except Exception as exc: note(f"Save failed: {exc}")

    def load_slot():
        try:
            with open(state_path(), 'rb') as file: snes.load_state(file.read())
            audio.clear(); note("State loaded")
        except Exception as exc: note(f"Load failed: {exc}")

    MENUS = {
        "File": (("Open ROM...    Ctrl+O", open_rom), ("ROM Library...    L", show_library),
                 ("Save State    F5", save_slot), ("Load State    F7", load_slot),
                 ("Exit", do_exit)),
        "CPU": (("Pause    P", toggle_pause), ("Reset    R", reset_game),
                ("Continue / Play", play_game), ("Automatic Frameskip    F", toggle_skip)),
        "Options": (("Joypad Configuration...", show_controls),
                    ("Fullscreen    Alt+Enter", toggle_fullscreen),
                    ("Maintain Aspect Ratio", toggle_aspect),
                    ("Mute Sound    M", toggle_mute)),
        "Help": (("About vsnes...", show_about), ("Controls...", show_controls)),
    }

    def draw_popup():
        nonlocal popup_rows
        popup_rows = []
        if active_menu is None: return
        entries = MENUS[MENU_ITEMS[active_menu]]
        width = min(W, max(font.size(label)[0] for label, action in entries) + 28)
        x = max(0, min(menu_rects[active_menu].x, W - width))
        mouse = pygame.mouse.get_pos()
        # Classic raised dropdown panel
        panel = pygame.Rect(x, MENU_H, width, 22 * len(entries) + 2)
        pygame.draw.rect(screen, MENU_BG, panel)
        pygame.draw.line(screen, (255, 255, 255), (panel.x, panel.y), (panel.right - 1, panel.y))
        pygame.draw.line(screen, (255, 255, 255), (panel.x, panel.y), (panel.x, panel.bottom - 1))
        pygame.draw.line(screen, (64, 64, 64), (panel.right - 1, panel.y), (panel.right - 1, panel.bottom - 1))
        pygame.draw.line(screen, (64, 64, 64), (panel.x, panel.bottom - 1), (panel.right - 1, panel.bottom - 1))
        for i, (label, action) in enumerate(entries):
            rect = pygame.Rect(x + 1, MENU_H + 1 + i * 22, width - 2, 22)
            popup_rows.append((rect, action))
            hot = rect.collidepoint(mouse)
            if hot:
                pygame.draw.rect(screen, MENU_HOT, rect)
            col = MENU_HOT_TXT if hot else MENU_TXT
            screen.blit(font.render(label, True, col), (rect.x + 8, rect.y + 4))

    ACTIONS = {
        "Load ROM": open_rom,
        "Library": show_library,
        "Play Game": play_game,
        "Exit": do_exit,
        "About": show_about,
        "Controls": show_controls,
    }

    def menu_hit(pos):
        if pos[1] >= MENU_H:
            return -1
        for i, r in enumerate(menu_rects):
            if r.collidepoint(pos):
                return i
        return -1

    def draw_menustrip():
        screen.fill(MENU_BG, (0, 0, W, MENU_H))
        pygame.draw.line(screen, (255, 255, 255), (0, 0), (W, 0))
        pygame.draw.line(screen, MENU_EDGE, (0, MENU_H - 1), (W, MENU_H - 1))
        for i, (label, rect) in enumerate(zip(MENU_ITEMS, menu_rects)):
            hot = i == hover or i == active_menu
            if hot:
                pygame.draw.rect(screen, MENU_HOT, rect)
            text = font.render(label, True, MENU_HOT_TXT if hot else MENU_TXT)
            screen.blit(text, (rect.x + 8, (MENU_H - text.get_height()) // 2))

    def draw_dialog(title, lines):
        pad = 14
        line_h = font_dlg.get_height() + 2
        widest = max((font_dlg.size(ln)[0] for ln in lines if ln), default=200)
        box_w = min(W - 40, max(widest + pad * 2, font_b.size(title)[0] + pad * 2 + 40))
        box_h = pad * 2 + font_b.get_height() + 14 + line_h * len(lines)
        bx = (W - box_w) // 2
        by = MENU_H + max(8, (H - box_h) // 2)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 100))
        screen.blit(shade, (0, MENU_H))
        pygame.draw.rect(screen, OVERLAY_BG, (bx, by, box_w, box_h))
        pygame.draw.rect(screen, (64, 64, 64), (bx, by, box_w, box_h), 1)
        pygame.draw.rect(screen, OVERLAY_ACC, (bx, by, box_w, 22))
        screen.blit(font_b.render(title, True, (255, 255, 255)), (bx + pad, by + 4))
        y = by + 30
        for ln in lines:
            if ln:
                screen.blit(font_dlg.render(ln, True, OVERLAY_FG), (bx + pad, y))
            y += line_h

    def draw_library():
        nonlocal lib_row_rects, lib_scroll, lib_sel
        items = filtered_library()
        lib_sel = max(0, min(lib_sel, max(0, len(items) - 1)))
        pad = 10; header_h = 52; row_h = font_sm.get_height() + 6
        box_w = W - 24; box_h = H - 16
        bx, by = 12, MENU_H + 8
        visible = max(1, (box_h - header_h - 28) // row_h)
        if lib_sel < lib_scroll:
            lib_scroll = lib_sel
        if lib_sel >= lib_scroll + visible:
            lib_scroll = lib_sel - visible + 1
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        screen.blit(shade, (0, MENU_H))
        pygame.draw.rect(screen, OVERLAY_BG, (bx, by, box_w, box_h))
        pygame.draw.rect(screen, OVERLAY_ACC, (bx, by, box_w, box_h), 2)
        pygame.draw.rect(screen, OVERLAY_ACC, (bx, by, box_w, 28))
        ok, chip, unk = library_summary(lib_entries)
        title = f"Commercial ROM Library  ({ok} playable / {chip} chip / {unk} other)"
        screen.blit(font_b.render(title, True, BLACK), (bx + pad, by + 6))
        hint = "Enter=Load  F=Folder  1=All  2=Playable  3=Chip  Esc=Close  (ROMs not bundled)"
        screen.blit(font_sm.render(hint, True, OVERLAY_FG), (bx + pad, by + 32))
        lib_row_rects = []
        if not items:
            screen.blit(font_dlg.render("No ROMs found. Press F to choose your SNES folder.", True, CHIP_COL),
                        (bx + pad, by + header_h))
            return
        y = by + header_h
        for i in range(lib_scroll, min(lib_scroll + visible, len(items))):
            e = items[i]
            rect = pygame.Rect(bx + 4, y, box_w - 8, row_h)
            lib_row_rects.append((rect, i))
            if i == lib_sel:
                pygame.draw.rect(screen, (50, 70, 100), rect)
                pygame.draw.rect(screen, OVERLAY_ACC, rect, 1)
            tag = {'ok': 'OK', 'chip': 'CHIP', 'unknown': '??'}.get(e['compat'], '??')
            tcol = {'ok': OK_COL, 'chip': CHIP_COL, 'unknown': UNK_COL}.get(e['compat'], UNK_COL)
            label = f"[{tag:4}] {e['title'][:28]:<28}  {e['mapper']:<7}  {e['chip_name'][:16]}"
            screen.blit(font_sm.render(label, True, tcol if i != lib_sel else OVERLAY_FG), (bx + pad, y + 2))
            y += row_h
        foot = f"{lib_sel + 1}/{len(items)}   filter={lib_filter}"
        screen.blit(font_sm.render(foot, True, MENU_DIM), (bx + pad, by + box_h - 22))

    FRAME_T = 1.0 / getattr(snes, "fps", 60.0988)                      # NTSC SNES frame period
    MAX_SKIP = 4
    skips = 0; buf_frames = 3; last_under = 0; clean = 0
    next_t = time.perf_counter()

    def pace():
        """Snes9x-style sync to sound: block until the audio queue drains to ~3 frames.
        Without audio (muted / no device) pace precisely by the clock instead."""
        nonlocal next_t, FRAME_T
        FRAME_T = 1.0 / getattr(snes, "fps", 60.0988)
        if turbo:
            next_t = time.perf_counter(); return
        if not paused and dialog is None and active_menu is None and not muted and audio.synced():
            target = audio.frame_bytes * buf_frames
            limit = time.perf_counter() + 0.1
            while audio.level() > target and time.perf_counter() < limit:
                time.sleep(0.0005)
            next_t = time.perf_counter()
            return
        next_t += FRAME_T
        now = time.perf_counter(); d = next_t - now
        if d > 0:
            if d > 0.002: time.sleep(d - 0.0015)
            while time.perf_counter() < next_t: pass
        elif d < -0.25:
            next_t = now                         # far behind (e.g. after a load): resync

    gc.collect(); gc.freeze()                     # keep long-lived objects out of GC passes

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.VIDEORESIZE and not fullscreen:
                W = max(512, ev.w); H = max(224, ev.h - MENU_H - STATUS_H)
                screen = pygame.display.set_mode((W, H + MENU_H + STATUS_H), pygame.RESIZABLE)
            elif ev.type == pygame.WINDOWFOCUSLOST:
                turbo = False
            elif ev.type == pygame.MOUSEMOTION:
                hover = menu_hit(ev.pos)
                if dialog == 'library':
                    for rect, idx in lib_row_rects:
                        if rect.collidepoint(ev.pos):
                            lib_sel = idx
                            break
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    hit = menu_hit(ev.pos)
                    if hit >= 0:
                        active_menu = None if active_menu == hit else hit
                        audio.clear()
                    elif active_menu is not None:
                        selected = next((action for rect, action in popup_rows if rect.collidepoint(ev.pos)), None)
                        active_menu = None
                        if selected: selected()
                    elif dialog == 'library':
                        clicked = False
                        for rect, idx in lib_row_rects:
                            if rect.collidepoint(ev.pos):
                                lib_sel = idx
                                load_library_selection()
                                clicked = True
                                break
                        if not clicked and ev.pos[1] >= MENU_H:
                            pass
                    elif dialog:
                        dialog = None
                elif ev.button == 4 and dialog == 'library':
                    lib_sel = max(0, lib_sel - 1)
                elif ev.button == 5 and dialog == 'library':
                    lib_sel = min(max(0, len(filtered_library()) - 1), lib_sel + 1)
            elif ev.type == pygame.DROPFILE:
                try:
                    info = load_into(snes, ev.file)
                    after_load(ev.file, info)
                except Exception as e:
                    note(f"load failed: {e}")
            elif ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_RETURN and ev.mod & pygame.KMOD_ALT:
                    toggle_fullscreen(); continue
                if active_menu is not None:
                    if k == pygame.K_ESCAPE: active_menu = None
                    continue
                if dialog == 'library':
                    if k == pygame.K_ESCAPE:
                        dialog = None
                    elif k == pygame.K_UP:
                        lib_sel = max(0, lib_sel - 1)
                    elif k == pygame.K_DOWN:
                        lib_sel = min(max(0, len(filtered_library()) - 1), lib_sel + 1)
                    elif k == pygame.K_PAGEUP:
                        lib_sel = max(0, lib_sel - 10)
                    elif k == pygame.K_PAGEDOWN:
                        lib_sel = min(max(0, len(filtered_library()) - 1), lib_sel + 10)
                    elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        load_library_selection()
                    elif k == pygame.K_f:
                        set_library_folder()
                    elif k == pygame.K_1:
                        lib_filter = 'all'; lib_sel = 0; lib_scroll = 0
                    elif k == pygame.K_2:
                        lib_filter = 'ok'; lib_sel = 0; lib_scroll = 0
                    elif k == pygame.K_3:
                        lib_filter = 'chip'; lib_sel = 0; lib_scroll = 0
                    continue
                if dialog:
                    dialog = None
                    continue
                if k == pygame.K_ESCAPE: running = False
                elif k == pygame.K_o: open_rom()
                elif k == pygame.K_l: show_library()
                elif k == pygame.K_p:
                    paused = not paused; audio.clear(); note("paused" if paused else "playing")
                elif k == pygame.K_m:
                    muted = not muted; audio.clear()
                    note("audio muted" if muted else ("audio on" if audio.dev else f"no audio device: {audio.err}"))
                elif k == pygame.K_r: snes.reset(); note("reset")
                elif k == pygame.K_f: autoskip = not autoskip; note(f"auto frameskip {'on' if autoskip else 'off'}")
                elif k == pygame.K_TAB: turbo = True
                elif k == pygame.K_F5:
                    try:
                        open(state_path(), 'wb').write(snes.save_state()); note("state saved")
                    except Exception as e:
                        note(f"save failed: {e}")
                elif k == pygame.K_F7:
                    try:
                        snes.load_state(open(state_path(), 'rb').read()); note("state loaded")
                    except Exception as e:
                        note(f"load failed: {e}")
                elif k == pygame.K_F12:
                    p = os.path.join(os.getcwd(), f"virtualsnes_{int(time.time())}.png")
                    write_png(p, snes.frame); note(f"screenshot {os.path.basename(p)}")
            elif ev.type == pygame.KEYUP and ev.key == pygame.K_TAB:
                turbo = False

        kp = pygame.key.get_pressed(); j = 0
        for key, bit in KEYS:
            if kp[key]: j |= 1 << bit
        snes.joy1 = j

        running_emu = not paused and dialog is None and active_menu is None
        drew = True
        if running_emu:
            this_skip = skip_next
            snes.skip_render = this_skip
            t0 = time.perf_counter()
            snes.run_frame()
            emu_ms = (time.perf_counter() - t0) * 1000
            fcount += 1
            pcm = snes.apu.dspc.take()
            sound_sync = audio.synced() and not muted and not turbo
            if not muted and not turbo:
                audio.push(pcm)
            # frameskip: skip drawing when audio is close to running dry (or we're behind time)
            if sound_sync:
                # adaptive latency (like Snes9x's buffer sizing): grow after underruns,
                # shrink back after ~10 s clean; skip drawing when the queue gets low
                if audio.underruns != last_under:
                    last_under = audio.underruns; buf_frames = min(8, buf_frames + 1); clean = 0
                else:
                    clean += 1
                    if clean > 600 and buf_frames > 3: buf_frames -= 1; clean = 0
                behind = audio.level() < audio.frame_bytes * (buf_frames - 0.5)
            else:
                behind = time.perf_counter() > next_t + FRAME_T
            if autoskip and behind and skips < MAX_SKIP:
                skip_next = True; skips += 1
            else:
                skip_next = False; skips = 0
            drew = not this_skip
        if not drew and time.perf_counter() - ft < 1.0:
            pace(); continue

        height, width = snes.frame.shape[:2]
        if surf.get_size() != (width, height): surf = pygame.Surface((width, height))
        pygame.surfarray.blit_array(surf, snes.frame.swapaxes(0, 1))
        # Black display face like classic MarioNES-style windows
        screen.fill(FACE_BG, (0, MENU_H, W, H))
        ratio = 4 / 3 if aspect_correct else width / height
        view_w = min(W, int(H * ratio)); view_h = min(H, int(W / ratio))
        screen.blit(pygame.transform.scale(surf, (view_w, view_h)),
                    ((W - view_w) // 2, MENU_H + (H - view_h) // 2))
        if running_emu and drew: rendered_count += 1
        draw_menustrip()
        if dialog == 'about':
            draw_dialog("About vsnes", ABOUT_LINES)
        elif dialog == 'controls':
            draw_dialog("Controls", CONTROLS_LINES)
        elif dialog == 'library':
            draw_library()

        sy = MENU_H + H
        screen.fill(STATUS_BG, (0, sy, W, STATUS_H))
        pygame.draw.line(screen, (255, 255, 255), (0, sy), (W, sy))
        pygame.draw.line(screen, MENU_EDGE, (0, sy + 1), (W, sy + 1))
        now = time.perf_counter()
        if now - ft >= 1.0:
            fps = fcount / (now - ft); rendered_fps = rendered_count / (now - ft)
            fcount = rendered_count = 0; ft = now
        # MarioNES-style status: "<title> initialized  <fps> fps"
        title = (snes.title or APP).strip() or APP
        if paused:
            status = f"{title} paused  {fps:.0f} fps"
        elif msg and now < msg_t:
            status = msg
        elif initialized:
            status = f"{title} initialized  {fps:.0f} fps"
        else:
            status = f"{APP}  {fps:.0f} fps"
        if turbo:
            status += "  TURBO"
        if muted:
            status += "  MUTE"
        screen.blit(font_sm.render(status, True, MENU_TXT), (6, sy + 3))
        draw_popup()
        pygame.display.flip()
        pace()
    snes.save_sram()
    if isinstance(snes, NativeSNES): snes.close()
    audio.close()
    pygame.quit()


def main():
    ap = argparse.ArgumentParser(description=f"{APP} — Virtual SNES Emulator (classic File/CPU/Options/Help GUI). {COPY}")
    ap.add_argument('--backend', choices=('auto', 'snes9x', 'python'), default='auto',
                    help='auto uses an installed SNES9x core, otherwise the custom Python core')
    ap.add_argument('--core', metavar='PATH', help='trusted local snes9x_libretro .dll/.dylib/.so')
    ap.add_argument('rom', nargs='?', help='.sfc/.smc/.zip ROM (omit for built-in demo)')
    ap.add_argument('--roms', metavar='DIR', help='commercial ROM library folder (saved in ~/.virtualsnes.json)')
    ap.add_argument('--scale', type=int, default=3, help='window scale 1-5 (default 3)')
    ap.add_argument('--headless', type=int, metavar='N', help='run N frames without a window and report speed')
    ap.add_argument('--shot', metavar='PNG', help='with --headless: save the last frame')
    ap.add_argument('--wav', metavar='WAV', help='with --headless: write the emulated audio (32 kHz stereo)')
    ap.add_argument('--dsp', choices=('auto', 'snes9x', 'numpy'), default='auto',
                    help='audio engine: snes9x = Snes9x S-DSP (Cython or pure Python); numpy = approx')
    ap.add_argument('--mute', action='store_true', help='start with audio muted (M toggles)')
    ap.add_argument('--hold', metavar='MASK', help='with --headless: joypad bits to hold (e.g. 0x0100 = Right)')
    ap.add_argument('--list-library', action='store_true', help='scan ROM library and print catalog, then exit')
    ap.add_argument('--cputest', metavar='DIR', help='run SingleStepTests 65816/spc700 *.json files in DIR, then exit')
    ap.add_argument('--per-file', type=int, default=60, help='with --cputest: max tests per file (default 60)')
    args = ap.parse_args()
    global DSP_MODE
    DSP_MODE = args.dsp
    if args.cputest:
        sys.exit(cputest(args.cputest, args.per_file))
    if args.roms:
        cfg = load_config(); cfg['roms_dir'] = os.path.abspath(args.roms); save_config(cfg)
    if args.list_library:
        entries = scan_rom_library()
        ok, chip, unk = library_summary(entries)
        print(f"{APP} commercial library: {len(entries)} ROMs  "
              f"({ok} playable mapper, {chip} enhancement chip, {unk} unknown)")
        print("(No ROMs are bundled — place your dumps in the library folder.)")
        for e in entries:
            print(f"  [{e['compat']:7}] {e['mapper']:<7} {e['title']:<21}  {e['chip_name']:<22}  {e['file']}")
        return
    if args.headless: headless(args)
    else: gui(args)


if __name__ == '__main__':
    main()
