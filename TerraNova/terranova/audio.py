# -*- coding: utf-8 -*-
"""Процедурная музыка и звуки. Всё синтезируется в WAV при первом запуске."""
from __future__ import annotations

import glob
import math
import os
import wave
import random

import numpy as np
import pygame

from . import config

SR = 22050
AUDIO_VERSION = "7"

# ------------------------------------------------------------- ноты и волны
MINOR = (0, 2, 3, 5, 7, 8, 10)
MAJOR = (0, 2, 4, 5, 7, 9, 11)
HARMONIC = (0, 2, 3, 5, 7, 8, 11)
PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)


def freq(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def scale_note(key: int, scale: tuple, degree: int, octave: int = 0) -> int:
    octv, deg = divmod(degree, len(scale))
    return key + 12 * (octv + octave) + scale[deg]


def _wave(kind: str, f: float, t: np.ndarray, phase: float = 0.0) -> np.ndarray:
    ph = 2.0 * np.pi * f * t + phase
    if kind == "sine":
        return np.sin(ph)
    if kind == "triangle":
        return (2.0 / np.pi) * np.arcsin(np.sin(ph))
    if kind == "square":
        return np.sign(np.sin(ph))
    if kind == "pulse":
        return np.where((np.sin(ph) + 1.0) % 1.0 < 0.28, 1.0, -1.0)
    if kind == "saw":
        return 2.0 * ((f * t + phase / (2 * np.pi)) % 1.0) - 1.0
    return np.sin(ph)


def _env(n: int, attack: float = 0.01, decay: float = 2.0,
         release: float = 0.05, sustain: float = 0.65) -> np.ndarray:
    t = np.arange(n) / SR
    if n <= 0:
        return np.zeros(0)
    a = max(1, int(attack * SR))
    env = np.ones(n) * sustain + (1.0 - sustain) * np.exp(-decay * t)
    env[:a] *= np.linspace(0.0, 1.0, a)
    r = min(n, max(1, int(release * SR)))
    env[-r:] *= np.linspace(1.0, 0.0, r)
    return env


def _add_note(buf: np.ndarray, start: float, dur: float, midi: float, wave: str,
              vol: float, attack=0.01, decay=2.2, release=0.05, sustain=0.55,
              detune=0.0):
    if midi is None or vol <= 0:
        return
    start_i = int(start * SR)
    n = int(dur * SR)
    if start_i >= len(buf) or n <= 1:
        return
    n = min(n, len(buf) - start_i)
    f = freq(midi)
    t = np.arange(n) / SR
    s = _wave(wave, f, t)
    if detune:
        s = 0.65 * s + 0.35 * _wave(wave, f * (1.0 + detune), t, 0.7)
    s *= _env(n, attack, decay, release, sustain) * vol
    buf[start_i:start_i + n] += s


def _add_kick(buf, start, vol=0.5):
    n = int(0.16 * SR)
    i = int(start * SR)
    if i >= len(buf):
        return
    n = min(n, len(buf) - i)
    t = np.arange(n) / SR
    f = 55 + 80 * np.exp(-t * 32)
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 18) * vol
    buf[i:i + n] += s


def _add_snare(buf, start, vol=0.22, rng=None):
    rng = rng or np.random.default_rng(4)
    n = int(0.14 * SR)
    i = int(start * SR)
    if i >= len(buf):
        return
    n = min(n, len(buf) - i)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n) * np.exp(-t * 30)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35) * 0.35
    buf[i:i + n] += (noise * 0.8 + tone) * vol


def _add_hat(buf, start, vol=0.09, rng=None):
    rng = rng or np.random.default_rng(7)
    n = int(0.045 * SR)
    i = int(start * SR)
    if i >= len(buf):
        return
    n = min(n, len(buf) - i)
    t = np.arange(n) / SR
    noise = rng.uniform(-1, 1, n)
    noise = np.diff(noise, prepend=0.0) * 0.7 + noise * 0.2
    buf[i:i + n] += noise * np.exp(-t * 90) * vol


TRACK_SPECS = {
    "menu": dict(
        bpm=76, bars=8, key=57, scale=MINOR, progression=[0, 5, 2, 6],
        lead_wave="triangle", lead_vol=0.17, lead_oct=2,
        pattern=[0, 2, 4, 7, 4, 2, 4, 2], pad=True, bass=True,
        drums=None, echo=0.30, echo_delay=0.36, lead_decay=1.6,
    ),
    "day": dict(
        bpm=112, bars=8, key=60, scale=MAJOR, progression=[0, 4, 5, 3],
        lead_wave="square", lead_vol=0.095, lead_oct=2,
        pattern=[0, 2, 4, 2, 7, 4, 2, 4], pad=True, bass=True,
        drums="light", echo=0.13, echo_delay=0.22, lead_decay=6.5,
    ),
    "night": dict(
        bpm=68, bars=8, key=57, scale=MINOR, progression=[0, 5, 2, 6],
        lead_wave="sine", lead_vol=0.17, lead_oct=2,
        pattern=[None, 4, None, 2, None, 7, None, 4], pad=True, bass=True,
        drums=None, echo=0.34, echo_delay=0.42, lead_decay=1.2,
    ),
    "cave": dict(
        bpm=82, bars=8, key=50, scale=MINOR, progression=[0, 5, 2, 6],
        lead_wave="triangle", lead_vol=0.15, lead_oct=2,
        pattern=[0, None, 2, None, 4, None, 2, 7], pad=True, bass=True,
        drums="drip", echo=0.38, echo_delay=0.46, lead_decay=1.4,
    ),
    "boss": dict(
        bpm=150, bars=8, key=52, scale=MINOR, progression=[0, 6, 5, 4],
        lead_wave="pulse", lead_vol=0.11, lead_oct=2,
        pattern=[0, 0, 7, 4, 2, 2, 4, 7], pad=False, bass=True,
        drums="heavy", echo=0.12, echo_delay=0.2, lead_decay=4.5,
    ),
    "desert": dict(
        bpm=98, bars=8, key=55, scale=PHRYGIAN, progression=[0, 1, 5, 4],
        lead_wave="triangle", lead_vol=0.15, lead_oct=2,
        pattern=[0, 4, 2, 4, 7, 4, 2, 1], pad=True, bass=True,
        drums="tribal", echo=0.25, echo_delay=0.31, lead_decay=3.2,
    ),
    "snow": dict(
        bpm=64, bars=8, key=57, scale=MAJOR, progression=[0, 5, 3, 4],
        lead_wave="sine", lead_vol=0.15, lead_oct=3,
        pattern=[0, None, 4, None, 7, None, 4, None], pad=True, bass=True,
        drums="frost", echo=0.40, echo_delay=0.48, lead_decay=1.4,
    ),
    "corrupt": dict(
        bpm=74, bars=8, key=45, scale=HARMONIC, progression=[0, 1, 0, 4],
        lead_wave="saw", lead_vol=0.075, lead_oct=2,
        pattern=[0, None, 1, 0, 4, 1, None, 0], pad=True, bass=True,
        drums="heart", echo=0.43, echo_delay=0.52, lead_decay=1.1,
    ),
    "boss2": dict(
        bpm=164, bars=8, key=45, scale=HARMONIC, progression=[0, 5, 1, 4],
        lead_wave="pulse", lead_vol=0.115, lead_oct=2,
        pattern=[0, 7, 4, 7, 1, 7, 4, 11], pad=False, bass=True,
        drums="heavy", echo=0.18, echo_delay=0.24, lead_decay=3.8,
    ),
    "boss_forest": dict(
        bpm=138, bars=8, key=50, scale=PHRYGIAN, progression=[0, 4, 1, 5],
        lead_wave="saw", lead_vol=0.095, lead_oct=2,
        pattern=[0, 2, 4, 2, 1, 4, 7, 4], pad=True, bass=True,
        drums="tribal", echo=0.22, echo_delay=0.28, lead_decay=2.8,
    ),
    "boss_frost": dict(
        bpm=148, bars=8, key=57, scale=HARMONIC, progression=[0, 5, 3, 4],
        lead_wave="triangle", lead_vol=0.13, lead_oct=2,
        pattern=[0, 7, 4, 7, 3, 7, 5, 11], pad=True, bass=True,
        drums="heavy", echo=0.30, echo_delay=0.34, lead_decay=3.2,
    ),
    "beach": dict(
        bpm=86, bars=8, key=60, scale=MAJOR, progression=[0, 5, 3, 4],
        lead_wave="triangle", lead_vol=0.14, lead_oct=2,
        pattern=[0, 2, 4, 7, 4, 2, 7, 4], pad=True, bass=True,
        drums="light", echo=0.34, echo_delay=0.40, lead_decay=2.2,
    ),
}


def render_track(key: str) -> np.ndarray:
    spec = TRACK_SPECS[key]
    bpm = spec["bpm"]
    bars = spec["bars"]
    spb = 60.0 / bpm
    beat_step = spb
    step = spb * 0.5
    total_beats = bars * 4
    total = int(total_beats * beat_step * SR)
    buf = np.zeros(total, dtype=np.float64)
    rng = np.random.default_rng(abs(hash(key)) % 10000)

    scale = spec["scale"]
    prog = spec["progression"]
    key_m = spec["key"]
    pattern = spec["pattern"]

    for bar in range(bars):
        bar_start = bar * 4 * beat_step
        deg = prog[bar % len(prog)]
        root = scale_note(key_m, scale, deg, 0)
        third = scale_note(key_m, scale, deg + 2, 0)
        fifth = scale_note(key_m, scale, deg + 4, 0)
        octave = scale_note(key_m, scale, deg + 7, 0)

        # мягкая подложка-аккорд
        if spec["pad"]:
            for note in (root, third, fifth):
                _add_note(buf, bar_start, 4 * beat_step * 1.02, note, "triangle",
                          0.038, attack=0.35, decay=0.0, release=0.4, sustain=1.0,
                          detune=0.003)
            if bar % 2 == 0:
                _add_note(buf, bar_start, 4 * beat_step * 1.02, root + 12, "sine",
                          0.018, attack=0.5, decay=0.0, release=0.5, sustain=1.0)

        # бас
        if spec["bass"]:
            bass_note = root - 12
            if key in ("boss", "boss2", "boss_forest", "boss_frost", "day"):
                _add_note(buf, bar_start, beat_step * 0.8, bass_note, "triangle", 0.22,
                          attack=0.006, decay=4.0, release=0.04, sustain=0.7)
                _add_note(buf, bar_start + 2 * beat_step, beat_step * 0.8, bass_note, "triangle",
                          0.20, attack=0.006, decay=4.0, release=0.04, sustain=0.7)
                _add_note(buf, bar_start + 3.5 * beat_step, beat_step * 0.4,
                          fifth - 12, "triangle", 0.12, attack=0.006, decay=6, release=0.03)
            else:
                _add_note(buf, bar_start, 2 * beat_step, bass_note, "triangle", 0.18,
                          attack=0.03, decay=1.2, release=0.1, sustain=0.6)
                _add_note(buf, bar_start + 2 * beat_step, 2 * beat_step, fifth - 12,
                          "triangle", 0.12, attack=0.03, decay=1.2, release=0.1)

        # мелодия
        note_dur = step * (1.75 if spec["lead_wave"] in ("triangle", "sine") else 0.82)
        for i, entry in enumerate(pattern):
            if entry is None:
                continue
            nt = scale_note(key_m, scale, deg + entry, spec["lead_oct"])
            start = bar_start + i * step
            if bar % 4 == 3 and i == 6:
                nt = scale_note(key_m, scale, deg + 7, spec["lead_oct"])
            vol = spec["lead_vol"] * (0.82 if i % 2 else 1.0)
            _add_note(buf, start, note_dur, nt, spec["lead_wave"], vol,
                      attack=0.008, decay=spec["lead_decay"], release=0.06, sustain=0.6,
                      detune=0.004 if spec["lead_wave"] in ("square", "pulse") else 0.0)
            # тихая октава для объёма
            if key in ("day", "boss", "boss2", "boss_forest", "boss_frost", "menu") and i % 4 == 0:
                _add_note(buf, start, note_dur * 0.9, nt + 12, "sine", vol * 0.28,
                          attack=0.01, decay=3.0, release=0.05, sustain=0.4)

        # барабаны
        drums = spec["drums"]
        if drums == "light":
            _add_kick(buf, bar_start, 0.30)
            _add_kick(buf, bar_start + 2 * beat_step, 0.26)
            _add_snare(buf, bar_start + beat_step, 0.13, rng)
            _add_snare(buf, bar_start + 3 * beat_step, 0.13, rng)
            for b in range(8):
                _add_hat(buf, bar_start + b * step, 0.045 if b % 2 else 0.06, rng)
        elif drums == "heavy":
            for b in range(4):
                _add_kick(buf, bar_start + b * beat_step, 0.34)
            _add_snare(buf, bar_start + beat_step, 0.19, rng)
            _add_snare(buf, bar_start + 3 * beat_step, 0.19, rng)
            for b in range(8):
                _add_hat(buf, bar_start + b * step, 0.05, rng)
        elif drums == "drip":
            if rng.random() < 0.7:
                _add_note(buf, bar_start + rng.integers(0, 4) * beat_step, 0.3,
                          scale_note(key_m, scale, 7, 2), "sine", 0.045,
                          attack=0.005, decay=5.0, release=0.2)
            if bar % 2 == 0:
                _add_kick(buf, bar_start, 0.12)
        elif drums == "tribal":
            _add_kick(buf, bar_start, 0.30)
            _add_kick(buf, bar_start + 2.5 * beat_step, 0.22)
            _add_snare(buf, bar_start + beat_step, 0.11, rng)
            _add_snare(buf, bar_start + 3 * beat_step, 0.16, rng)
            for b in range(8):
                _add_hat(buf, bar_start + b * step + (rng.random() * 0.02), 0.035, rng)
        elif drums == "frost":
            if bar % 2 == 0:
                _add_kick(buf, bar_start, 0.10)
            if rng.random() < 0.55:
                ping = scale_note(key_m, scale, int(rng.integers(4, 10)), 3)
                _add_note(buf, bar_start + int(rng.integers(0, 8)) * step, 0.52,
                          ping, "sine", 0.038, attack=0.005, decay=4.5, release=0.3)
        elif drums == "heart":
            _add_kick(buf, bar_start, 0.20)
            _add_kick(buf, bar_start + 0.55, 0.12)
            if bar % 2 == 1:
                _add_snare(buf, bar_start + 2 * beat_step, 0.07, rng)

    # эхо (заворачивается, чтобы петля была бесшовной)
    delay = int(spec["echo_delay"] * SR)
    if delay > 0:
        buf += np.roll(buf, delay) * spec["echo"]
    # лёгкое сглаживание
    if len(buf) > 8:
        buf = np.convolve(buf, np.array([0.2, 0.6, 0.2]), mode="same")
    peak = float(np.max(np.abs(buf))) or 1.0
    buf = buf / peak * 0.72
    return buf


def write_wav(path: str, data: np.ndarray):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767.0).astype("<i2")
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


# ------------------------------------------------------------- звуковые эффекты
def _tone_sweep(f0, f1, dur, wave_kind="sine", vol=0.5, decay=3.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    k = np.geomspace(max(20, f0), max(20, f1), n)
    phase = 2 * np.pi * np.cumsum(k) / SR
    if wave_kind == "square":
        s = np.sign(np.sin(phase))
    elif wave_kind == "saw":
        s = 2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0
    elif wave_kind == "triangle":
        s = (2.0 / np.pi) * np.arcsin(np.sin(phase))
    else:
        s = np.sin(phase)
    env = np.exp(-decay * t)
    env[:max(1, int(0.004 * SR))] *= np.linspace(0, 1, max(1, int(0.004 * SR)))
    return s * env * vol


def _noise(dur, vol=0.4, decay=14.0, seed=0, highpass=False):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    noise = rng.uniform(-1, 1, n)
    if highpass:
        noise = np.diff(noise, prepend=0.0)
    t = np.arange(n) / SR
    return noise * np.exp(-decay * t) * vol


def _mix(*arrays):
    n = max(len(a) for a in arrays)
    out = np.zeros(n)
    for a in arrays:
        out[:len(a)] += a
    return out


def _seq(notes, step, wave="sine", vol=0.4):
    total = int((len(notes) * step + 0.4) * SR)
    buf = np.zeros(total)
    for i, midi in enumerate(notes):
        start = int(i * step * SR)
        n = int(0.5 * SR)
        n = min(n, total - start)
        t = np.arange(n) / SR
        s = _wave(wave, freq(midi), t) * np.exp(-3.2 * t) * vol
        buf[start:start + n] += s
    return buf


SFX_BUILDERS = {
    "click": lambda: _tone_sweep(900, 640, 0.06, "square", 0.18, 20),
    "jump": lambda: _tone_sweep(280, 640, 0.16, "triangle", 0.28, 7),
    "swing": lambda: _noise(0.12, 0.22, 26, 3, highpass=True),
    "mine": lambda: _noise(0.09, 0.18, 30, 9, highpass=True),
    "break": lambda: _mix(_noise(0.20, 0.34, 16, 12), _tone_sweep(150, 70, 0.18, "sine", 0.18, 14)),
    "place": lambda: _mix(_tone_sweep(180, 95, 0.10, "triangle", 0.25, 22), _noise(0.06, 0.1, 40, 2)),
    "hit": lambda: _mix(_noise(0.10, 0.22, 24, 5), _tone_sweep(220, 120, 0.09, "square", 0.10, 18)),
    "hurt": lambda: _tone_sweep(420, 110, 0.30, "saw", 0.22, 6),
    "pickup": lambda: _seq([88, 93], 0.055, "sine", 0.20),
    "craft": lambda: _seq([72, 76, 79, 84], 0.065, "triangle", 0.22),
    "heal": lambda: _seq([76, 81, 84, 88], 0.08, "sine", 0.18),
    "roar": lambda: _mix(_tone_sweep(110, 38, 0.9, "saw", 0.3, 1.7), _noise(0.8, 0.18, 2.2, 11)),
    "death": lambda: _seq([64, 60, 55, 48], 0.16, "triangle", 0.25),
    "victory": lambda: _seq([72, 76, 79, 84, 88, 91, 96], 0.12, "triangle", 0.25),
    "boss_die": lambda: _mix(_noise(0.9, 0.4, 3.0, 17), _seq([45, 40, 33], 0.22, "saw", 0.18)),
    "summon": lambda: _mix(_tone_sweep(60, 180, 1.2, "saw", 0.25, 1.5), _noise(1.1, 0.15, 2.0, 19)),
    "save": lambda: _seq([79, 84], 0.09, "sine", 0.18),
}


def ensure_audio(progress=None) -> bool:
    """Создаёт все аудиофайлы. progress(доля, подпись)."""
    version_file = os.path.join(config.AUDIO_DIR, "version.txt")
    current = ""
    try:
        with open(version_file, "r", encoding="utf-8") as f:
            current = f.read().strip()
    except OSError:
        pass
    if current != AUDIO_VERSION:
        for pattern in ("*.wav", "sfx/*.wav"):
            for path in glob.glob(os.path.join(config.AUDIO_DIR, pattern)):
                try:
                    os.remove(path)
                except OSError:
                    pass
        tracks = list(TRACK_SPECS.keys())
        for i, key in enumerate(tracks):
            if progress:
                progress(0.05 + 0.75 * i / len(tracks), f"Синтез музыки: {key}...")
            write_wav(os.path.join(config.AUDIO_DIR, f"{key}.wav"), render_track(key))
        snds = list(SFX_BUILDERS.keys())
        for i, key in enumerate(snds):
            if progress:
                progress(0.8 + 0.18 * i / len(snds), "Создание звуков...")
            write_wav(os.path.join(config.SFX_DIR, f"{key}.wav"),
                      np.clip(SFX_BUILDERS[key](), -1, 1))
        try:
            with open(version_file, "w", encoding="utf-8") as f:
                f.write(AUDIO_VERSION)
        except OSError:
            pass
    if progress:
        progress(1.0, "Готово")
    return True


class AudioManager:
    def __init__(self, settings: dict, progress=None):
        self.enabled = True
        self.current_music: str | None = None
        self.music_volume = float(settings.get("music", 0.55))
        self.sfx_volume = float(settings.get("sfx", 0.7))
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SR, size=-16, channels=1, buffer=512)
        except pygame.error:
            self.enabled = False
            return
        try:
            ensure_audio(progress)
            for path in glob.glob(os.path.join(config.SFX_DIR, "*.wav")):
                name = os.path.splitext(os.path.basename(path))[0]
                self.sounds[name] = pygame.mixer.Sound(path)
        except (pygame.error, OSError):
            self.enabled = False

    # ------------------------------------------------------------------ музыка
    def play_music(self, key: str):
        if not self.enabled or key == self.current_music:
            return
        path = os.path.join(config.AUDIO_DIR, f"{key}.wav")
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(-1, fade_ms=500)
            self.current_music = key
        except pygame.error:
            pass

    def stop_music(self):
        if self.enabled:
            try:
                pygame.mixer.music.stop()
            except pygame.error:
                pass
            self.current_music = None

    def set_music_volume(self, value: float):
        self.music_volume = max(0.0, min(1.0, value))
        if self.enabled:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except pygame.error:
                pass

    def set_sfx_volume(self, value: float):
        self.sfx_volume = max(0.0, min(1.0, value))

    # ------------------------------------------------------------------ звуки
    def sfx(self, name: str, volume: float = 1.0):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if not snd:
            return
        try:
            channel = snd.play()
            if channel:
                channel.set_volume(self.sfx_volume * volume)
        except pygame.error:
            pass


# для теста
if __name__ == "__main__":
    ensure_audio(lambda p, t: print(f"{p:.0%} {t}"))
