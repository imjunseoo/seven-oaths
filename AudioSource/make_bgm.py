"""Seven Oaths BGM -> build/masters/*.wav (lossless, stereo, sample-exact loops); encode_ogg.py -> Assets/Audio/BGM.

bgm_training: night cathedral training ground. 72 BPM, D minor, 24 bars = 80.000 s loop.
  A (1-8)   low strings + choir 'u', distant bell, solo cello foreshadows the theme
  B (9-16)  solo cello theme, harp quarter-note arpeggios, choir 'o', soft timpani
  C (17-24) violins take the theme an octave up, choir 'a', fuller strings; bar 24 thins out back into A
Original composition (no existing piece imitated).

bgm_boss: boss battle, 'holy war' orchestra v3 (tutti hits + choir theme), 96 BPM, 32 bars = 80.000 s loop.

Usage: python make_bgm.py [training|boss]
"""
import json
from pathlib import Path

import numpy as np

from nb.dsp import SR, N, mtof, make_ir, lp, hp, write_wav, rng
from nb.music import Arr, finalize_loop
from nb.orch import section, bowed, choir, church_bell, harp, timpani, timp_roll

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "masters"
CATHEDRAL = make_ir(rt60=3.6, predelay=0.035, stereo=True, seed=13, brightness=4500, hf_ratio=0.35, lf_ratio=1.1,
                    er=12, er_level=0.3, er_span=0.06)

# chord per bar (24 bars)
PROG = (["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "Asus4", "A"] +
        ["Dm", "C", "Bb", "F", "Gm", "Bb", "Asus4", "A"] +
        ["Bb", "F", "Gm", "Dm", "Bb", "C", "Dm", "A"])
ROOT = {"Dm": 38, "Bb": 34, "Gm": 31, "A": 33, "Asus4": 33, "C": 36, "F": 29}          # bass (MIDI)
CELLO = {"Dm": [50, 57], "Bb": [46, 53], "Gm": [43, 50], "A": [45, 52], "Asus4": [45, 52], "C": [48, 55],
         "F": [41, 48]}
UPPER = {"Dm": [62, 65, 69], "Bb": [62, 65, 70], "Gm": [62, 67, 70], "A": [61, 64, 69], "Asus4": [62, 64, 69],
         "C": [60, 64, 67], "F": [60, 65, 69]}                                          # violas / choir
HARP = {"Dm": [50, 57, 62, 65], "Bb": [46, 53, 58, 62], "Gm": [43, 50, 55, 58], "A": [45, 52, 57, 61],
        "Asus4": [45, 52, 57, 62], "C": [48, 55, 60, 64], "F": [41, 48, 53, 57]}

# melodies: per bar list of (beat, beats, midi)
FORESHADOW = [[(0, 2, 55), (2, 2, 58)], [(0, 4, 57)], [(0, 2, 62), (2, 2, 64)], [(0, 4, 61)]]          # bars 5-8
THEME_CELLO = [  # bars 9-16
    [(0, 2, 57), (2, 1.5, 62), (3.5, 0.5, 64)],
    [(0, 2, 64), (2, 1, 67), (3, 1, 64)],
    [(0, 3, 65), (3, 0.5, 64), (3.5, 0.5, 62)],
    [(0, 2, 60), (2, 2, 57)],
    [(0, 1.5, 58), (1.5, 0.5, 57), (2, 1, 55), (3, 1, 62)],
    [(0, 2, 65), (2, 1, 64), (3, 1, 62)],
    [(0, 2, 62), (2, 2, 64)],
    [(0, 3, 61), (3, 1, 57)],
]
THEME_VLN = [  # bars 17-24
    [(0, 2, 74), (2, 1.5, 77), (3.5, 0.5, 76)],
    [(0, 2, 72), (2, 2, 69)],
    [(0, 1.5, 70), (1.5, 0.5, 72), (2, 2, 74)],
    [(0, 3, 69), (3, 1, 65)],
    [(0, 1.5, 77), (1.5, 0.5, 76), (2, 2, 74)],
    [(0, 2, 76), (2, 1, 79), (3, 1, 76)],
    [(0, 4, 74)],
    [(0, 2, 74), (2, 2, 73)],
]


def dyn(bar):
    """section dynamics 0..1 (bar is 0-based)"""
    if bar < 8:
        return 0.45
    if bar < 16:
        return 0.6 + 0.05 * (bar - 8) / 8
    if bar < 23:
        return 0.78
    return 0.5


def place_line(A, bus, bars, start_bar, maker, send, gain=1.0, p=0.0):
    for bi, notes in enumerate(bars):
        for (b, d, m) in notes:
            A.add(bus, maker(float(mtof(m)), A.sec(d) * 1.02, start_bar + bi, b), A.pos(start_bar + bi, b), gain, p,
                  jitter_ms=6, send=send)


def bgm_training():
    A = Arr(72, 24, tail=10.0, seed=72)
    bar_s = A.sec(4)
    for bar, ch in enumerate(PROG):
        b0 = A.pos(bar)
        v = dyn(bar)
        # chords that last two bars in section A are bowed once over both bars
        if bar < 6 and bar % 2 == 1:
            continue
        span = 2 if bar < 6 else 1
        d = bar_s * span * 1.03
        # basses (an octave below the cello root)
        A.add("basses", section(float(mtof(ROOT[ch])), d, 0.75 * v + 0.2, seed=1000 + bar, players=3, attack=0.5,
                                release=0.9, bright=0.25, vib_cents=6, body=(110, 400, 1500), spread=0.3),
              b0, 1.0, send={"hall": 0.3})
        # cellos: root + fifth
        for k, m in enumerate(CELLO[ch]):
            A.add("cellos", section(float(mtof(m)), d, 0.7 * v + 0.2, seed=2000 + bar * 3 + k, players=4,
                                    attack=0.45, release=0.9, bright=0.35, vib_cents=8, spread=0.5),
                  b0, 1.0, -0.15 + 0.1 * k, send={"hall": 0.32})
        # violas: upper chord tones from section B on
        if bar >= 8:
            for k, m in enumerate(UPPER[ch][:2]):
                A.add("violas", section(float(mtof(m)), d, 0.6 * v + 0.15, seed=3000 + bar * 3 + k, players=3,
                                        attack=0.5, release=0.9, bright=0.4, vib_cents=9, body=(350, 1100, 2600),
                                        spread=0.6), b0, 1.0, 0.2, send={"hall": 0.35})
        # choir pad
        if bar >= 2:
            vowel = "u" if bar < 8 else ("o" if bar < 16 else "a")
            notes = UPPER[ch] if bar >= 16 else UPPER[ch][:2] + [UPPER[ch][2] - 12]
            for k, m in enumerate(notes):
                A.add("choir", choir(float(mtof(m)), d, vowel, 0.55 * v + 0.15, seed=4000 + bar * 5 + k,
                                     attack=0.9 if bar < 8 else 0.5), b0, 1.0, send={"hall": 0.5})
        # harp arpeggio, B and C
        if 8 <= bar < 23:
            pat = HARP[ch]
            order = [0, 1, 2, 3] if bar % 2 == 0 else [0, 2, 1, 3]
            for q in range(4):
                m = pat[order[q]] + (12 if bar >= 16 else 0)
                A.add("harp", harp(float(mtof(m)), A.sec(1.6), 0.5 + 0.1 * (q == 0), seed=5000 + bar * 4 + q),
                      b0 + q, 1.0, -0.3 + 0.2 * q, jitter_ms=5, send={"hall": 0.35})
    # solo cello: foreshadow (bars 5-8) and theme (9-16)
    solo = lambda f, d, bar, beat: bowed(f, d, 0.85 if bar >= 8 else 0.6, seed=6000 + bar * 8 + int(beat * 2),  # noqa
                                         attack=0.12, release=0.5, vib_cents=16, vib_rate=5.3, vib_delay=0.18,
                                         bright=0.6, noise=0.045, swell=0.15)
    place_line(A, "solo", FORESHADOW, 4, solo, {"hall": 0.28}, 1.0, -0.1)
    place_line(A, "solo", THEME_CELLO, 8, solo, {"hall": 0.28}, 1.0, -0.1)
    # violins: theme an octave up (bars 17-24), with a choir 'a' doubling an octave down
    vln = lambda f, d, bar, beat: section(f, d, 0.8 if bar < 23 else 0.45, seed=7000 + bar * 8 + int(beat * 2),  # noqa
                                          players=5, attack=0.14, release=0.6, bright=0.5, vib_cents=12,
                                          body=(450, 1300, 3000), spread=0.7, jitter=0.02)
    place_line(A, "violins", THEME_VLN, 16, vln, {"hall": 0.35}, 1.0, 0.1)
    # timpani: soft downbeats + a roll into the violin theme
    for bar, m in [(8, 38), (12, 38), (16, 38), (20, 38)]:
        A.add("timp", timpani(float(mtof(m)), 0.55, seed=bar), A.pos(bar), 1.0, 0, send={"hall": 0.4})
    A.add("timp", timp_roll(float(mtof(33)), A.sec(2.0), 0.08, 0.45, seed=15), A.pos(15, 2), 1.0, 0,
          send={"hall": 0.4})
    # rare bells: three tolls in 80 s, far away
    for bar, m, v in [(0, 50, 0.8), (8, 45, 0.6), (16, 50, 0.7)]:
        A.add("bell", church_bell(float(mtof(m)), v, tau=6.0, seed=bar), A.pos(bar), 1.0, 0.35,
              send={"hall": 0.9})
    levels = {"solo": -21.5, "violins": -21.5, "cellos": -23, "basses": -25, "violas": -26.5, "choir": -24.5,
              "harp": -29, "timp": -28, "bell": -26}
    fx = {"basses": lambda x: lp(x, 900, 2), "cellos": lambda x: hp(x, 50, 2), "choir": lambda x: hp(lp(x, 5000, 2), 120, 2),
          "harp": lambda x: hp(x, 120, 2), "bell": lambda x: hp(lp(x, 3500, 2), 60, 2)}
    effects = {"hall": (CATHEDRAL, 0.6)}
    pre = A.mixdown(fx, effects, levels)
    y = finalize_loop(pre, A.L, target_lufs=-18.0, wow_ms=0.12, flutter_ms=0.0, drive=1.1, comp_thr=-22.0,
                      ratio=1.8, hshelf=-1.5, lpf=10000.0)
    OUT.mkdir(parents=True, exist_ok=True)
    write_wav(OUT / "bgm_training.wav", y, seed=7)
    print(f"bgm_training: {A.L / SR:.3f}s ({A.L} samples) {A.bars} bars @ {A.bpm} BPM")
    return y


# ============================================================================ BOSS (96 BPM, D minor, 32 bars)
# v3 (user 2026-11-18): 'holy war' orchestra that EXPLODES - tutti hits (brass braam + string chord + choir 'HA!' +
# timpani + gran cassa + crash) and a real CHOIR THEME (sopranos sing the melody, tenors an octave below).
# Sacred colour kept: bells, tam-tam, pipe organ, Latin-ish vowels, Phrygian bII (Eb). Original material.
HALL_S = make_ir(rt60=2.6, predelay=0.028, stereo=True, seed=31, brightness=4800, hf_ratio=0.38, lf_ratio=1.1,
                 er=12, er_level=0.3, er_span=0.06)
S_PROG = (["Dm", "Dm", "Bb", "A"] +
          ["Dm", "Bb", "Gm", "A", "Dm", "Bb", "Eb", "A"] +
          ["Dm", "C", "Bb", "A", "Gm", "Bb", "Eb", "A"] +
          ["Dm", "Bb", "Gm", "A", "Dm", "Bb", "Eb", "A"] +
          ["Dm", "Dm", "Bb", "A"])
ORG = {"Dm": [38, 50, 57, 62, 65], "Gm": [43, 50, 55, 58, 62], "Bb": [34, 50, 53, 58, 62],
       "A": [45, 52, 57, 61, 64], "Eb": [39, 51, 55, 58, 63], "C": [36, 48, 55, 60, 64]}
S_ROOT = {"Dm": 50, "Gm": 43, "Bb": 46, "A": 45, "Eb": 51, "C": 48}
S_NB = {"Dm": 51, "Gm": 45, "Bb": 48, "A": 46, "Eb": 53, "C": 50}
S_BASS = {"Dm": 38, "Gm": 31, "Bb": 34, "A": 33, "Eb": 39, "C": 36}
S_TROM = {"Dm": [38, 45, 50, 53], "Gm": [31, 43, 50, 55], "Bb": [34, 46, 50, 53], "A": [33, 45, 49, 52],
          "Eb": [39, 46, 51, 55], "C": [36, 43, 48, 52]}
S_CHOIR = {"Dm": [57, 62, 65], "Gm": [55, 58, 62], "Bb": [58, 62, 65], "A": [57, 61, 64], "Eb": [55, 58, 63],
           "C": [55, 60, 64]}
THEME = [[(0, 2, 74), (2, 1, 69), (3, 1, 74)],
         [(0, 1.5, 77), (1.5, 0.5, 76), (2, 2, 74)],
         [(0, 1, 79), (1, 1, 77), (2, 1, 76), (3, 1, 74)],
         [(0, 3, 76), (3, 1, 69)],
         [(0, 2, 74), (2, 1, 69), (3, 1, 74)],
         [(0, 1, 77), (1, 1, 79), (2, 2, 81)],
         [(0, 2, 79), (2, 1, 77), (3, 1, 75)],
         [(0, 2, 74), (2, 2, 73)]]
SYL = ["a", "e", "o", "a", "u", "e", "a", "o", "e", "a", "u"]               # Latin-ish vowel colours


def bgm_boss():
    from nb.epic import spicc_ens, brass_section, braam, crash, rev_crash, battle_snare
    from nb.orch import organ, gran_cassa, tamtam
    A = Arr(96, 32, tail=10.0, seed=96)
    bar_s = A.sec(4)
    syl = iter(SYL * 40)
    sec = lambda bar: "I" if bar < 4 else "A" if bar < 12 else "B" if bar < 20 else "C" if bar < 28 else "D"  # noqa

    def tutti(bar, beat, ch, big=1.0, seed=0):
        """'빵': everything hits together"""
        pos = A.pos(bar, beat)
        A.add("brass", braam([float(mtof(m)) for m in S_TROM[ch]], 0.55, big, seed=900 + seed), pos, 1.0,
              send={"hall": 0.4})
        for k, m in enumerate(S_CHOIR[ch]):
            A.add("marc", spicc_ens(m, big, k % 4, dur=0.3), pos, 1.0, -0.3 + 0.3 * k, send={"hall": 0.3})
            A.add("marc", spicc_ens(m - 24 if m - 24 >= 28 else m - 12, big, (k + 1) % 4, dur=0.3), pos, 1.0, 0,
                  send={"hall": 0.3})
            A.add("choir", choir(float(mtof(m + 12)), 0.32, "a", 0.95 * big, seed=950 + seed * 5 + k, voices=10,
                                 attack=0.012, release=0.35, vib_cents=3), pos, 1.0, send={"hall": 0.5})
        A.add("timp", timpani(float(mtof(38 if ch in ("Dm", "Bb", "Gm") else 33)), 0.95 * big, seed=seed), pos, 1.0,
              send={"hall": 0.35})
        A.add("drum", gran_cassa(1.0 * big, seed=seed), pos, 1.0, send={"hall": 0.35})
        A.add("cym", crash(2.6, seed=seed), pos, 0.85 * big, send={"hall": 0.3})

    def snare_roll(bar, beat, beats, v0, v1, seed=0):
        k, tt = 0, 0.0
        while tt < beats:
            A.add("snare", battle_snare(v0 + (v1 - v0) * tt / beats, k % 3), A.pos(bar, beat + tt), 1.0, 0.1,
                  send={"hall": 0.25}, jitter_ms=3)
            tt += 0.125
            k += 1

    for bar, ch in enumerate(S_PROG):
        s = sec(bar)
        v = {"I": 0.7, "A": 0.8, "B": 0.85, "C": 1.0, "D": 0.55}[s]
        b0 = A.pos(bar)
        org = ORG[ch]
        # ---- organ: intro, climax, breakdown
        if s in "ICD":
            ov = {"I": 0.6, "C": 0.8, "D": 0.5}[s]
            A.add("organ", organ(float(mtof(org[0])), bar_s * 1.01, ov, seed=12000 + bar,
                                 ranks=((0.5, 0.6), (1.0, 1.0), (2.0, 0.3))), b0, 1.0, send={"hall": 0.5})
            for k, m in enumerate(org[1:]):
                A.add("organ", organ(float(mtof(m)), bar_s * 1.01, ov * 0.8, seed=12100 + bar * 7 + k), b0, 1.0,
                      send={"hall": 0.5})
        # ---- basses
        A.add("str", section(float(mtof(S_BASS[ch])), bar_s * 1.02, 0.55 * v + 0.15, seed=12200 + bar, players=3,
                             attack=0.12, release=0.5, bright=0.35, vib_cents=5, body=(110, 400, 1500), spread=0.3),
              b0, 1.0, send={"hall": 0.3})
        # ---- marcato low-string ostinato (8ths), doubled an octave down from A on
        if s != "D" or bar >= 30:
            r, nb = S_ROOT[ch], S_NB[ch]
            for e8, m in enumerate([r, r, r, r + 12, r, r, nb, r]):
                acc = 1.0 if e8 in (0, 4) else 0.7
                A.add("marc", spicc_ens(m, v * acc, (bar * 8 + e8) % 4, dur=0.22), b0 + e8 * 0.5, 1.0, -0.15,
                      jitter_ms=4, send={"hall": 0.25})
                if s in "ABC":
                    A.add("marc", spicc_ens(m - 12, v * acc * 0.8, (bar * 8 + e8 + 1) % 4, dur=0.22),
                          b0 + e8 * 0.5, 1.0, 0.1, jitter_ms=4, send={"hall": 0.25})
        # ---- violins: tremolo high chord in the climax
        if s == "C":
            for k, m in enumerate(S_CHOIR[ch]):
                tr = section(float(mtof(m + 12)), bar_s * 1.01, 0.55, seed=12300 + bar * 5 + k, players=5,
                             attack=0.1, release=0.4, bright=0.45, vib_cents=6, body=(450, 1300, 3000), spread=0.7)
                tt = np.arange(tr.shape[1]) / SR
                A.add("vln", tr * (0.55 + 0.45 * np.abs(np.sin(np.pi * 8.0 * tt))), b0, 1.0, send={"hall": 0.35})
        # ---- brass: trombone chorale (A, C), horn call (B)
        if s in "AC":
            for k, m in enumerate(S_TROM[ch]):
                A.add("brass", brass_section(float(mtof(m)), bar_s * 0.98, 0.55 if s == "A" else 0.8,
                                             seed=12400 + bar * 5 + k, players=2, attack=0.1, release=0.35,
                                             vib_cents=0, bright=0.85, growl=1.7), b0, 1.0, -0.2 + 0.13 * k,
                      send={"hall": 0.4})
        if s == "B":
            top, mid = S_CHOIR[ch][2], S_CHOIR[ch][1]
            for bt, d, m in ((0, 1, top), (1, 0.5, mid), (1.5, 0.5, top)):
                for octv in (0, -12):
                    A.add("brass", brass_section(float(mtof(m + octv)), A.sec(d) * 0.95, 0.9, seed=12500 + bar * 9 +
                                                 int(bt * 2) + (octv < 0), players=3, attack=0.03, release=0.2,
                                                 vib_cents=3, bright=1.1, growl=1.8), b0 + bt, 1.0, 0.0,
                          send={"hall": 0.4})
        # ---- CHOIR
        if s in "AC":   # the theme: sopranos + tenors an octave below + ATB pad
            th = THEME[(bar - 4) % 8]
            for (bt, d, m) in th:
                vo = next(syl)
                A.add("choir", choir(float(mtof(m)), A.sec(d) * 1.02, vo, 0.95 if s == "C" else 0.85,
                                     seed=12600 + bar * 8 + int(bt * 2), voices=12, attack=0.06, release=0.45,
                                     vib_cents=9), b0 + bt, 1.0, 0.15, send={"hall": 0.5})
                A.add("choir", choir(float(mtof(m - 12)), A.sec(d) * 1.02, vo, 0.8, seed=12700 + bar * 8 +
                                     int(bt * 2), voices=10, attack=0.06, release=0.45, vib_cents=7),
                      b0 + bt, 1.0, -0.15, send={"hall": 0.5})
                if s == "C":   # trumpets double the sopranos, horns the tenors
                    A.add("brass", brass_section(float(mtof(m - 12)), A.sec(d) * 0.97, 0.75,
                                                 seed=12800 + bar * 8 + int(bt * 2), players=4, attack=0.05,
                                                 release=0.25, vib_cents=5, bright=0.95), b0 + bt, 1.0, -0.1,
                          send={"hall": 0.4})
            for k, m in enumerate(S_CHOIR[ch]):
                A.add("choir", choir(float(mtof(m)), bar_s, "a", 0.55, seed=12900 + bar * 5 + k, attack=0.25,
                                     release=0.6), b0, 1.0, send={"hall": 0.5})
        elif s == "B":  # chant answers the horn call: 'HA - HA . HA'
            for bt in (2, 2.5, 3.5):
                for k, m in enumerate(S_CHOIR[ch]):
                    A.add("choir", choir(float(mtof(m + 12)), 0.22, "a", 0.9, seed=13000 + bar * 20 + int(bt * 2) * 3 + k,
                                         voices=10, attack=0.015, release=0.2, vib_cents=3), b0 + bt, 1.0,
                          send={"hall": 0.45})
        elif s == "I" or s == "D":  # low sustained 'o' / 'u'
            for k, m in enumerate(S_CHOIR[ch]):
                A.add("choir", choir(float(mtof(m - 12)), bar_s, "o" if s == "I" else "u", 0.6,
                                     seed=13100 + bar * 5 + k, attack=0.4, release=0.8), b0, 1.0, send={"hall": 0.55})
        # ---- percussion
        if s == "I":
            for e8 in range(8):
                if bar in (1, 3) or e8 >= 2:
                    A.add("timp", timpani(float(mtof(38)), 0.35 + 0.05 * (e8 % 2 == 0), seed=bar * 8 + e8),
                          b0 + e8 * 0.5, 1.0, send={"hall": 0.35})
        if s == "A":
            for bt, g in ((2, 0.7), (3.5, 0.55)):
                A.add("drum", gran_cassa(g, seed=bar * 4 + int(bt)), b0 + bt, 1.0, send={"hall": 0.35})
            A.add("timp", timpani(float(mtof(38)), 0.55, seed=bar), b0 + 2, 1.0, send={"hall": 0.35})
        if s == "B":
            for bt, g in ((0, 0.85), (1.5, 0.6), (2, 0.75), (3, 0.6), (3.5, 0.7)):
                A.add("drum", gran_cassa(g, seed=bar * 8 + int(bt * 2)), b0 + bt, 1.0, send={"hall": 0.35})
            A.add("timp", timpani(float(mtof(38 if ch in ("Dm", "Bb", "Gm", "C") else 33)), 0.6, seed=bar), b0, 1.0,
                  send={"hall": 0.35})
            if bar % 2 == 1:
                snare_roll(bar, 3, 1.0, 0.25, 0.6, seed=bar)
        if s == "C":
            for bt in range(4):
                A.add("drum", gran_cassa(0.9 if bt % 2 == 0 else 0.7, seed=bar * 4 + bt), b0 + bt, 1.0,
                      send={"hall": 0.35})
            for e8 in range(8):
                A.add("timp", timpani(float(mtof(38 if e8 % 2 == 0 else 33)), 0.55 + 0.2 * (e8 % 2 == 0),
                                      seed=bar * 8 + e8), b0 + e8 * 0.5, 1.0, send={"hall": 0.35})
        if s == "D" and bar >= 30:
            snare_roll(bar, 0, 4.0, 0.12 + 0.3 * (bar - 30), 0.42 + 0.35 * (bar - 30), seed=bar)
        # ---- tutti '빵' hits
        if bar in (0, 2) or (s in "AB" and bar % 2 == 0) or s == "C":
            tutti(bar, 0, ch, 1.0 if s != "I" or bar == 0 else 0.85, seed=bar)
        if bar in (23, 27):   # '빵 빵' pickups into the next phrase
            tutti(bar, 3, ch, 0.8, seed=bar * 10 + 1)
            tutti(bar, 3.5, ch, 0.95, seed=bar * 10 + 2)
        # ---- bells, tam-tam
        if bar in (0, 20, 28):
            A.add("bell", church_bell(float(mtof(50)), 0.9, tau=6.0, seed=bar), b0, 1.0, 0.3, send={"hall": 0.8})
        if bar in (0, 20):
            A.add("tamtam", tamtam(0.8, seed=bar), b0, 1.0, send={"hall": 0.4})
    A.add("timp", timp_roll(float(mtof(33)), A.sec(8.0), 0.08, 0.6, seed=30), A.pos(30), 1.0, send={"hall": 0.35})
    A.add("cym", rev_crash(1.8, seed=32), A.pos(32) - 1.8 / A.sec(1), 0.9, send={"hall": 0.25})
    levels = {"choir": -20.5, "brass": -21.5, "marc": -24, "str": -26.5, "vln": -26, "organ": -27, "timp": -23.5,
              "drum": -22.5, "snare": -29, "cym": -29.5, "tamtam": -29, "bell": -26}
    fx = {"organ": lambda x: hp(x, 30, 2), "marc": lambda x: hp(x, 45, 2), "vln": lambda x: hp(x, 150, 2),
          "choir": lambda x: hp(lp(x, 5200, 2), 90, 2), "bell": lambda x: hp(lp(x, 3800, 2), 60, 2),
          "cym": lambda x: hp(lp(x, 6500, 2), 300, 2), "drum": lambda x: lp(x, 1500, 2),
          "snare": lambda x: lp(x, 5000, 2)}
    effects = {"hall": (HALL_S, 0.55)}
    pre = A.mixdown(fx, effects, levels)
    y = finalize_loop(pre, A.L, target_lufs=-17.0, wow_ms=0.05, flutter_ms=0.0, drive=1.2, comp_thr=-21.0,
                      ratio=2.2, hshelf=-1.5, lpf=10000.0)
    OUT.mkdir(parents=True, exist_ok=True)
    write_wav(OUT / "bgm_boss_synth.wav", y, seed=8)   # replaced in game by import_bgm.py (user's licensed track)
    print(f"bgm_boss (synth, not shipped): {A.L / SR:.3f}s ({A.L} samples) {A.bars} bars @ {A.bpm} BPM")
    return y


# ============================================================================ REGION 1 (100 BPM, D minor, 32 bars)
# 'Ashen Rampart': tense march along the outer wall at night - syncopated marcato low strings, orchestral drums,
# wind (loop-periodic noise), a distant horn call, high-string tension clusters, low choir swells.
R_PROG = (["Dm", "Dm", "Bb", "C", "Dm", "Dm", "Gm", "A"] +
          ["Dm", "Bb", "Gm", "A", "Dm", "Bb", "Eb", "A"] +
          ["Gm", "Gm", "Dm", "Dm", "Bb", "C", "A", "A"] +
          ["Dm", "Dm", "Bb", "C", "Dm", "Gm", "A", "A"])
R_CALL = {8: [(0, 1.5, 62), (1.5, 0.5, 65), (2, 2, 69)], 9: [(0, 1, 67), (1, 1, 65), (2, 2, 62)],
          12: [(0, 1.5, 62), (1.5, 0.5, 65), (2, 2, 69)], 13: [(0, 1, 70), (1, 1, 69), (2, 2, 67)],
          14: [(0, 2, 67), (2, 2, 63)], 15: [(0, 4, 64)]}


def _periodic_lfo(L, seed, kmax=8, slope=1.0, kmin=1):
    r = rng(seed)
    t = np.arange(L) / L
    x = np.zeros(L)
    for k in range(kmin, kmax + 1):
        x += r.normal() / k ** slope * np.sin(2 * np.pi * k * t + r.uniform(0, 2 * np.pi))
    return x / (np.max(np.abs(x)) + 1e-12)


def bgm_region1():
    from nb.dsp import colored_noise, circular_process, bp
    from nb.dsp import rng as _rng  # noqa: F401
    from nb.epic import spicc_ens, brass_section, battle_snare
    from nb.orch import gran_cassa
    A = Arr(100, 32, tail=9.0, seed=100)
    bar_s = A.sec(4)
    sec = lambda bar: "ABCD"[bar // 8]  # noqa: E731
    for bar, ch in enumerate(R_PROG):
        s = sec(bar)
        v = {"A": 0.62, "B": 0.72, "C": 0.85, "D": 0.6 + 0.05 * max(0, bar - 27)}[s]
        b0 = A.pos(bar)
        # ---- basses
        A.add("str", section(float(mtof(S_BASS[ch])), bar_s * 1.02, 0.5 * v + 0.15, seed=14000 + bar, players=3,
                             attack=0.15, release=0.5, bright=0.3, vib_cents=4, body=(110, 400, 1500), spread=0.3),
              b0, 1.0, send={"hall": 0.25})
        # ---- syncopated marcato ostinato: da . da da . da da da
        r_, nb = S_ROOT[ch], S_NB[ch]
        for e8, m in ((0, r_), (2, r_), (3, r_), (5, r_), (6, nb), (7, r_)):
            acc = 1.0 if e8 in (0, 3) else 0.7
            A.add("marc", spicc_ens(m, v * acc, (bar * 8 + e8) % 4, dur=0.18), b0 + e8 * 0.5, 1.0, -0.15,
                  jitter_ms=4, send={"hall": 0.22})
            if s in "BC":
                A.add("marc", spicc_ens(m - 12, v * acc * 0.75, (bar * 8 + e8 + 1) % 4, dur=0.18), b0 + e8 * 0.5,
                      1.0, 0.15, jitter_ms=4, send={"hall": 0.22})
        # ---- high-string tension cluster (C, D): a tremolo minor second above the chord
        if s in "CD":
            for k, m in enumerate((81, 82)):
                tr = section(float(mtof(m)), bar_s * 1.01, 0.35 * v, seed=14100 + bar * 3 + k, players=4, attack=0.6,
                             release=0.6, bright=0.4, vib_cents=4, body=(450, 1300, 3000), spread=0.7)
                tt = np.arange(tr.shape[1]) / SR
                A.add("vln", tr * (0.6 + 0.4 * np.abs(np.sin(np.pi * 6.5 * tt))), b0, 1.0, send={"hall": 0.4})
        # ---- distant horn call (B)
        if bar in R_CALL:
            for (bt, d, m) in R_CALL[bar]:
                A.add("brass", brass_section(float(mtof(m)), A.sec(d) * 0.97, 0.6, seed=14200 + bar * 8 + int(bt * 2),
                                             players=3, attack=0.08, release=0.3, vib_cents=5, bright=0.8),
                      b0 + bt, 1.0, -0.3, send={"hall": 0.7})
        # ---- low brass pulses (C)
        if s == "C":
            for bt in (0, 2.5):
                for k, m in enumerate(S_TROM[ch][:2]):
                    A.add("brass", brass_section(float(mtof(m)), A.sec(1.2), 0.65, seed=14300 + bar * 6 + int(bt * 2) * 2 + k,
                                                 players=2, attack=0.03, release=0.3, vib_cents=0, bright=0.9,
                                                 growl=1.8), b0 + bt, 1.0, send={"hall": 0.35})
        # ---- low choir swells (C)
        if s == "C" and bar % 2 == 0:
            for k, m in enumerate(S_CHOIR[ch]):
                A.add("choir", choir(float(mtof(m - 12)), bar_s * 2, "u", 0.5, seed=14400 + bar * 5 + k, attack=1.2,
                                     release=1.2), b0, 1.0, send={"hall": 0.55})
        # ---- drums
        if s == "A" or (s == "D" and bar < 28):
            A.add("drum", gran_cassa(0.6 * v + 0.2, seed=bar), b0, 1.0, send={"hall": 0.3})
            if bar % 2 == 1:
                A.add("timp", timpani(float(mtof(38)), 0.45, seed=bar), b0 + 2, 1.0, send={"hall": 0.3})
                for k, bt in enumerate((3.5, 3.75)):
                    A.add("snare", battle_snare(0.25 + 0.1 * k, k), b0 + bt, 1.0, 0.1, send={"hall": 0.2})
        if s == "B":
            for bt, g in ((0, 0.8), (1.5, 0.55), (2.5, 0.65)):
                A.add("drum", gran_cassa(g, seed=bar * 4 + int(bt * 2)), b0 + bt, 1.0, send={"hall": 0.3})
            A.add("timp", timpani(float(mtof(38 if ch in ("Dm", "Bb", "Gm") else 33)), 0.55, seed=bar), b0, 1.0,
                  send={"hall": 0.3})
            for bt, g in ((1, 0.35), (3, 0.4), (3.75, 0.25)):
                A.add("snare", battle_snare(g, int(bt * 4) % 3), b0 + bt, 1.0, 0.1, send={"hall": 0.2})
        if s == "C":
            for bt, g in ((0, 0.9), (1, 0.55), (2, 0.75), (2.5, 0.55), (3, 0.65)):
                A.add("drum", gran_cassa(g, seed=bar * 6 + int(bt * 2)), b0 + bt, 1.0, send={"hall": 0.3})
            for e8 in range(8):
                A.add("timp", timpani(float(mtof(38 if e8 % 2 == 0 else 33)), 0.35 + 0.15 * (e8 % 4 == 0),
                                      seed=bar * 8 + e8), b0 + e8 * 0.5, 1.0, send={"hall": 0.3})
            if bar % 4 == 3:
                for k in range(8):
                    A.add("snare", battle_snare(0.2 + 0.05 * k, k % 3), b0 + 3 + k * 0.125, 1.0, 0.1,
                          send={"hall": 0.2})
        if s == "D" and bar >= 28:
            A.add("drum", gran_cassa(0.7, seed=bar), b0, 1.0, send={"hall": 0.3})
            A.add("drum", gran_cassa(0.5, seed=bar + 50), b0 + 2.5, 1.0, send={"hall": 0.3})
            if bar >= 30:
                k, tt = 0, 0.0
                while tt < 4.0:
                    A.add("snare", battle_snare(0.12 + 0.18 * (bar - 30) + 0.1 * tt / 4, k % 3), b0 + tt, 1.0, 0.1,
                          send={"hall": 0.2}, jitter_ms=3)
                    tt += 0.125
                    k += 1
    A.add("timp", timp_roll(float(mtof(33)), A.sec(4.0), 0.1, 0.5, seed=31), A.pos(31), 1.0, send={"hall": 0.3})
    # ---- wind over the battlements (loop-periodic: circular noise, harmonic-of-loop LFOs)
    L = A.L
    gust = np.clip(0.55 + 0.4 * _periodic_lfo(L, 141, kmax=10), 0.1, 1.2) ** 1.5
    wl = circular_process(colored_noise(L, -3.0, 142), lambda z: bp(z, 250, 1400, 2), reps=2)
    wr = circular_process(colored_noise(L, -3.0, 143), lambda z: bp(z, 250, 1400, 2), reps=2)
    A.add("wind", np.stack([wl * gust, wr * np.roll(gust, N(1.3))]), 0, 1.0, swing=False)
    levels = {"marc": -23.5, "str": -25.5, "drum": -22.5, "timp": -24.5, "snare": -29, "brass": -24, "vln": -29,
              "choir": -27.5, "wind": -30}
    fx = {"marc": lambda x: hp(x, 45, 2), "vln": lambda x: hp(lp(x, 6000, 2), 200, 2), "drum": lambda x: lp(x, 1500, 2),
          "snare": lambda x: lp(x, 5000, 2), "choir": lambda x: hp(lp(x, 4500, 2), 90, 2)}
    effects = {"hall": (HALL_S, 0.5)}
    pre = A.mixdown(fx, effects, levels)
    y = finalize_loop(pre, A.L, target_lufs=-18.0, wow_ms=0.05, flutter_ms=0.0, drive=1.15, comp_thr=-22.0,
                      ratio=2.0, hshelf=-1.5, lpf=10000.0)
    OUT.mkdir(parents=True, exist_ok=True)
    write_wav(OUT / "bgm_region1.wav", y, seed=9)
    print(f"bgm_region1: {A.L / SR:.3f}s ({A.L} samples) {A.bars} bars @ {A.bpm} BPM")
    return y


# ============================================================================ TITLE (64 BPM, D minor, 20 bars)
# main menu: night, moonlit ruined walls, a distant castle. majestic but lonely, an oath / prayer - not a battle.
# organ drone on a D pedal + low string pad + celesta arpeggios (icy, metal - not glass) + a far choir pad,
# a solo cello prayer, two crimson low-cluster shadows (D+Eb) that pass and resolve. bar 1 holds only the drone
# so the first ~3 s enter quietly (title fade-in); the last bars thin out back into that state -> seamless loop.
T_PROG = ["Dm", "Dm", "Bb", "Dm", "Dm", "Bb", "Gm", "A", "Bb", "F", "Gm", "Dm",
          "Bb", "C", "Dm", "A", "Dm", "Bb", "Dm", "Dm"]
T_CEL = {"Dm": [74, 77, 81, 86], "Bb": [74, 77, 82, 86], "Gm": [74, 79, 82, 86], "A": [73, 76, 81, 85],
         "F": [72, 77, 81, 84], "C": [72, 76, 79, 84]}
T_PAD = {"Dm": [57, 62, 65], "Bb": [58, 62, 65], "Gm": [55, 58, 62], "A": [57, 61, 64], "F": [57, 60, 65],
         "C": [55, 60, 64]}
T_MEL = {8: [(0, 2, 62), (2, 1, 60), (3, 1, 58)], 9: [(0, 3, 57), (3, 1, 60)], 10: [(0, 2, 62), (2, 1, 65), (3, 1, 62)],
         11: [(0, 4, 57)], 12: [(0, 2, 65), (2, 1, 67), (3, 1, 65)], 13: [(0, 2, 64), (2, 2, 60)],
         14: [(0, 4, 62)], 15: [(0, 2, 61), (2, 2, 64)], 16: [(0, 4, 62)]}


def bgm_title():
    from nb.orch import organ, celesta, church_bell
    A = Arr(64, 20, tail=10.0, seed=64)
    bar_s = A.sec(4)
    dyn = [0.35, 0.45, 0.5, 0.55, 0.6, 0.62, 0.65, 0.65, 0.75, 0.78, 0.8, 0.8, 0.85, 0.88, 0.9, 0.85,
           0.7, 0.55, 0.42, 0.35]
    for bar, ch in enumerate(T_PROG):
        b0 = A.pos(bar)
        v = dyn[bar]
        # ---- organ drone (D pedal; Bb / C pedal for a lift in bars 13-14)
        ped = {12: 34, 13: 36}.get(bar, 38)
        for k, m in enumerate((ped, ped + 7 if bar in (12, 13) else 45)):
            ov = {0: 0.12, 18: 0.24, 19: 0.12}.get(bar, 0.35 + 0.25 * v)   # bar 1 / loop end: quiet drone only
            A.add("organ", organ(float(mtof(m)), bar_s * 1.02, ov, seed=15000 + bar * 3 + k,
                                 ranks=((0.5, 0.4), (1.0, 1.0), (2.0, 0.2)), attack=0.6, release=1.2, chiff=0.0),
                  b0, 1.0, send={"hall": 0.55})
        # ---- low string pad from bar 3 to bar 19
        if 2 <= bar <= 18:
            for k, m in enumerate(T_PAD[ch]):
                A.add("pad", section(float(mtof(m)), bar_s * 1.03, 0.3 + 0.4 * v, seed=15100 + bar * 4 + k, players=4,
                                     attack=1.2, release=1.4, bright=0.3, vib_cents=6, spread=0.6), b0, 1.0,
                      send={"hall": 0.5})
        # ---- far choir pad (bars 9-16)
        if 8 <= bar <= 15:
            for k, m in enumerate(T_PAD[ch]):
                A.add("choir", choir(float(mtof(m + 12)), bar_s * 1.02, "u" if bar < 12 else "o", 0.5,
                                     seed=15200 + bar * 4 + k, attack=1.0, release=1.4), b0, 1.0, send={"hall": 0.8})
        # ---- celesta: none in bar 1 (quiet entry), quarters early/late, eighths in the middle, sparse at the end
        cel = T_CEL[ch]
        if 1 <= bar <= 3 or 16 <= bar <= 17:
            steps = [(q, cel[i]) for q, i in zip((0, 1, 2, 3), (0, 2, 1, 3))]
        elif 4 <= bar <= 15:
            steps = [(e * 0.5, cel[i]) for e, i in enumerate((0, 1, 2, 3, 2, 1, 2, 1))]
        elif bar == 18:
            steps = [(0, cel[0]), (2, cel[2])]
        else:
            steps = []
        for bt, m in steps:
            A.add("cel", celesta(float(mtof(m)), (0.45 + 0.35 * v) * (1.0 if bt % 1 == 0 else 0.8),
                                 seed=15300 + bar * 16 + int(bt * 2)), b0 + bt, 1.0, 0.3 - 0.2 * (m % 3), jitter_ms=6,
                  send={"hall": 0.55})
        # ---- small metal chimes on phrase starts, one far church bell
        if bar in (4, 8, 12, 16):
            for k, m in enumerate((86, 93)):
                A.add("cel", celesta(float(mtof(m)), 0.5, seed=15400 + bar * 2 + k, tau=2.5), b0 + 0.02 * k, 1.0,
                      -0.3 + 0.6 * k, send={"hall": 0.7})
        if bar in (8, 16):
            A.add("bell", church_bell(float(mtof(50)), 0.7, tau=6.0, seed=bar), b0, 1.0, -0.25, send={"hall": 0.9})
    # ---- solo cello prayer (bars 9-17)
    for bar, notes in T_MEL.items():
        for (bt, d, m) in notes:
            A.add("solo", bowed(float(mtof(m)), A.sec(d) * 1.02, 0.75, seed=15500 + bar * 8 + int(bt * 2), attack=0.25,
                                release=0.7, vib_cents=14, vib_rate=5.0, vib_delay=0.3, bright=0.5, noise=0.04,
                                swell=0.2), A.pos(bar, bt), 1.0, -0.1, jitter_ms=5, send={"hall": 0.45})
    # ---- crimson shadows: a D+Eb low cluster that swells and resolves (bars 7 and 15)
    for bar, depth in ((6, 0.45), (14, 0.8)):
        m = N(bar_s * 1.6)
        sw = np.interp(np.arange(m) / SR, [0, bar_s * 0.7, bar_s * 1.1, bar_s * 1.6], [0, 1, 0.6, 0])
        eb = section(float(mtof(39)), bar_s * 1.4, 0.6 * depth, seed=15600 + bar, players=4, attack=0.8, release=0.6,
                     bright=0.5, vib_cents=3, body=(110, 400, 1500), spread=0.4)
        eb = np.pad(eb, ((0, 0), (0, max(0, m - eb.shape[1]))))[:, :m] * sw
        rum = lp(rng(15700 + bar).standard_normal(m), 90, 4)
        rum = rum / (np.max(np.abs(rum)) + 1e-9) * sw * 0.25 * depth
        A.add("crimson", eb + np.stack([rum, rum]), A.pos(bar), 1.0, send={"hall": 0.4})
    levels = {"organ": -25.5, "pad": -25.5, "choir": -28.5, "cel": -24, "bell": -28, "solo": -22.5, "crimson": -29}
    fx = {"organ": lambda x: hp(x, 30, 2), "choir": lambda x: hp(lp(x, 2800, 2), 120, 2),
          "cel": lambda x: hp(lp(x, 6000, 2), 250, 2), "bell": lambda x: hp(lp(x, 3500, 2), 60, 2),
          "pad": lambda x: hp(x, 70, 2)}
    effects = {"hall": (CATHEDRAL, 0.65)}
    pre = A.mixdown(fx, effects, levels)
    y = finalize_loop(pre, A.L, target_lufs=-18.0, wow_ms=0.08, flutter_ms=0.0, drive=1.05, comp_thr=-24.0,
                      ratio=1.6, hshelf=-1.5, lpf=9500.0)
    OUT.mkdir(parents=True, exist_ok=True)
    write_wav(OUT / "bgm_title.wav", y, seed=10)
    print(f"bgm_title: {A.L / SR:.3f}s ({A.L} samples) {A.bars} bars @ {A.bpm} BPM")
    return y


DESC = {"bgm_training": "72 BPM · D단조 · 24마디 80초 루프. A: 낮은 현(베이스·첼로)+합창 '우'+먼 종, 첼로 솔로가 주제를 예고 → "
                        "B: 첼로 솔로 주제+하프 아르페지오+합창 '오'+약한 팀파니 → C: 바이올린이 한 옥타브 위로 주제, 합창 '아', "
                        "마지막 마디에서 잦아들며 처음으로. 성당 잔향(RT 3.6초).",
        "bgm_boss": "96 BPM · D단조(프리지안 ♭II=E♭) · 32마디 80초 루프, '성전' 오케스트라 v3 (오리지널). "
                    "서주: 종+탐탐+튜티 '빵!'(금관 브람+현 화음+합창 '하!'+팀파니+큰북+심벌) → A: 합창 주제(소프라노 주선율+테너 옥타브 아래) "
                    "+저음 현 마르카토, 2마디마다 튜티 → B: 호른 부름에 합창 '하-하 하!' 응답, 큰북 리듬+스네어 롤 → "
                    "C(절정): 합창 주제 최강음+트럼펫·호른 제창+바이올린 트레몰로+오르간, 매 마디 튜티, 마디 끝 '빵 빵' → "
                    "D: 낮은 합창 '우'+오르간 → 팀파니·스네어 롤과 역심벌로 서주의 '빵!'에 착지.",
        "bgm_region1": "100 BPM · D단조 · 32마디 76.8초 루프, 1지역 '잿빛 성벽' 길. 저음 현 당김음 마르카토(다 · 다다 · 다다다)+큰북·팀파니·작은북 "
                       "행진+성벽을 스치는 바람(루프 주기 노이즈) → B: 멀리서 부르는 호른(D-F-A) → C: 높은 현 단2도 트레몰로 긴장+저음 금관 "
                       "펄스+낮은 합창 '우' → D: 숨 고르고 작은북 롤로 처음으로. 수련장·보스와 같은 D단조라 전환 자연스러움.",
        "bgm_title": "64 BPM · D단조 · 20마디 75초 루프, 타이틀(메인 화면). 장엄하지만 쓸쓸한 서약·기도: D 페달 오르간 드론+낮은 현 패드+"
                     "첼레스타 아르페지오(얼음 파랑, 금속 음판)+먼 합창 우/오+첼로 솔로 기도 선율(9–17마디)+작은 금속 종·먼 교회 종. "
                     "7·15마디에 진홍 그림자(D+Eb 저음 클러스터)가 부풀었다 풀림. 1마디는 드론만 → 시작 약 3초 고요하게, "
                     "끝 마디들이 같은 상태로 잦아들어 끊김 없이 이어짐."}


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["training", "region1", "title"]   # "boss" = old synthesized boss theme, kept for reference
    if "training" in which:
        bgm_training()
    if "boss" in which:
        bgm_boss()
    if "region1" in which:
        bgm_region1()
    if "title" in which:
        bgm_title()
    mp = HERE / "build" / "long_meta.json"
    old = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    for k, v in DESC.items():
        old.setdefault(k, {})["desc"] = v
    mp.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
