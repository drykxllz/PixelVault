"""Flappy Bird — flap through the pipes, chase your best score.

Three modes, five skies, six birds, chiptune music and saved scores.
Run with:  python main.py
Requires:  pip install pygame   (pygame-ce works too)
"""

import json
import math
import os
import random
import struct
import sys
from pathlib import Path

import pygame

# --- Configuration ---------------------------------------------------------

WIDTH, HEIGHT = 460, 680
HUD_HEIGHT = 42
GROUND_HEIGHT = 94
PLAY_TOP = HUD_HEIGHT
PLAY_BOTTOM = HEIGHT - GROUND_HEIGHT

BIRD_X = 128
BIRD_RADIUS = 14
MAX_FALL = 820.0

PIPE_WIDTH = 74
PIPE_MIN_MARGIN = 58
PIPE_CAP_HEIGHT = 26
PIPE_CAP_OVERHANG = 7

SCORE_FILE = Path(__file__).with_name("highscore.json")
SETTINGS_FILE = Path(__file__).with_name("settings.json")

TEXT_COLOR = (235, 238, 245)
MUTED_COLOR = (150, 158, 175)
ACCENT_COLOR = (255, 208, 100)
DANGER_COLOR = (240, 110, 110)
OVERLAY_COLOR = (8, 10, 16, 196)

PAUSE_BTN_SIZE = (38, 30)
PAUSE_BTN_Y = 6
PAUSE_BTN_COLOR = (48, 54, 70)
PAUSE_BTN_HOVER = (68, 76, 98)
PAUSE_BTN_BORDER = (84, 94, 118)

# The launcher sets this so the game can say where quitting takes you.
LAUNCHED_FROM_LAUNCHER = os.environ.get("GAME_LAUNCHER") == "1"
QUIT_HINT = "ESC returns to the launcher" if LAUNCHED_FROM_LAUNCHER else "Press ESC to quit"

SAMPLE_RATE = 22050
MUSIC_VOLUME = 0.26  # peak amplitude baked into the music layers
EFFECT_VOLUME = 0.30
DEFAULT_MUSIC_VOLUME = 0.30  # first run with no settings file
DEFAULT_GAME_VOLUME = 0.8

THEMES = [
    {"name": "Day", "sky_top": (104, 190, 234), "sky_bottom": (198, 234, 244),
     "cloud": (255, 255, 255), "hill_back": (150, 208, 168),
     "hill_front": (116, 188, 144), "ground": (222, 206, 148),
     "ground_top": (110, 190, 116), "ground_alt": (206, 188, 130),
     "pipe": (108, 198, 110), "pipe_light": (162, 228, 158),
     "pipe_dark": (72, 148, 78), "hud": (34, 44, 56)},
    {"name": "Dusk", "sky_top": (58, 72, 138), "sky_bottom": (242, 158, 122),
     "cloud": (250, 210, 196), "hill_back": (104, 92, 140),
     "hill_front": (78, 68, 108), "ground": (152, 120, 98),
     "ground_top": (128, 104, 96), "ground_alt": (138, 108, 88),
     "pipe": (126, 174, 128), "pipe_light": (170, 208, 160),
     "pipe_dark": (84, 124, 90), "hud": (40, 42, 60)},
    {"name": "Night", "sky_top": (10, 14, 32), "sky_bottom": (44, 54, 90),
     "cloud": (86, 96, 136), "hill_back": (32, 38, 66),
     "hill_front": (24, 28, 52), "ground": (60, 58, 78),
     "ground_top": (56, 66, 74), "ground_alt": (50, 48, 68),
     "pipe": (82, 152, 122), "pipe_light": (116, 190, 152),
     "pipe_dark": (52, 104, 86), "hud": (18, 22, 36),
     "stars": True, "star": (225, 232, 255)},
    {"name": "Sunset", "sky_top": (238, 128, 92), "sky_bottom": (252, 212, 138),
     "cloud": (255, 234, 196), "hill_back": (196, 126, 108),
     "hill_front": (160, 96, 88), "ground": (200, 154, 112),
     "ground_top": (150, 160, 100), "ground_alt": (184, 138, 98),
     "pipe": (122, 186, 118), "pipe_light": (176, 220, 150),
     "pipe_dark": (86, 138, 82), "hud": (52, 36, 34)},
    {"name": "Mint", "sky_top": (118, 212, 194), "sky_bottom": (214, 244, 226),
     "cloud": (252, 255, 252), "hill_back": (128, 204, 176),
     "hill_front": (96, 178, 152), "ground": (204, 226, 172),
     "ground_top": (104, 186, 140), "ground_alt": (188, 210, 156),
     "pipe": (100, 190, 148), "pipe_light": (156, 226, 188),
     "pipe_dark": (68, 144, 110), "hud": (30, 46, 48)},
]

BIRD_STYLES = [
    {"name": "Sunny", "body": (255, 208, 82), "wing": (240, 166, 48),
     "belly": (255, 238, 184), "beak": (255, 138, 58)},
    {"name": "Ruby", "body": (236, 92, 104), "wing": (194, 60, 78),
     "belly": (255, 196, 196), "beak": (255, 176, 84)},
    {"name": "Cyan", "body": (84, 190, 236), "wing": (48, 140, 194),
     "belly": (198, 238, 255), "beak": (255, 168, 72)},
    {"name": "Lime", "body": (140, 214, 104), "wing": (94, 172, 70),
     "belly": (216, 248, 188), "beak": (255, 164, 74)},
    {"name": "Rose", "body": (238, 132, 190), "wing": (194, 88, 152),
     "belly": (255, 210, 236), "beak": (255, 176, 92)},
    {"name": "Snow", "body": (240, 244, 250), "wing": (198, 208, 224),
     "belly": (255, 255, 255), "beak": (255, 172, 70)},
]

GAME_MODES = [
    {"name": "Classic", "speed": 192.0, "max_speed": 268.0, "ramp": 3.4,
     "gap": 168, "interval": 1.45, "gravity": 1850.0, "flap": -520.0,
     "blurb": "The original pace — pipes tighten as you score"},
    {"name": "Breeze", "speed": 152.0, "max_speed": 196.0, "ramp": 1.6,
     "gap": 202, "interval": 1.70, "gravity": 1550.0, "flap": -470.0,
     "blurb": "Wide gaps and gentle gravity, easy flying"},
    {"name": "Frenzy", "speed": 236.0, "max_speed": 340.0, "ramp": 6.0,
     "gap": 146, "interval": 1.12, "gravity": 2150.0, "flap": -565.0,
     "blurb": "Tight gaps, heavy gravity, no mercy"},
]

CLOUDS = [(78, 120, 1.00), (282, 84, 0.78), (404, 190, 0.62),
          (168, 258, 0.55), (330, 326, 0.45)]

HILLS_BACK = [(-20, 300, 150), (200, 340, 190), (430, 300, 160)]
HILLS_FRONT = [(90, 280, 110), (320, 300, 130), (500, 280, 120)]

STARS = [(36, 48), (88, 96), (150, 38), (212, 122), (272, 58),
         (330, 136), (392, 46), (430, 100), (58, 164), (250, 184),
         (404, 214), (120, 208)]


# --- High score storage ----------------------------------------------------

def load_high_scores():
    """Best score per mode."""
    scores = {mode["name"]: 0 for mode in GAME_MODES}
    try:
        data = json.loads(SCORE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return scores
    if not isinstance(data, dict):
        return scores

    stored = data.get("best")
    if isinstance(stored, dict):
        for name in scores:
            value = stored.get(name)
            if isinstance(value, int) and not isinstance(value, bool):
                scores[name] = max(0, value)
    return scores


def save_high_scores(scores):
    try:
        SCORE_FILE.write_text(json.dumps({"best": scores}, indent=2), encoding="utf-8")
    except OSError:
        pass  # not fatal, just means no persistence


# --- Settings --------------------------------------------------------------

class Settings:
    def __init__(self):
        self.open = False
        self.drag_target = None  # None, "music" or "game"
        self.muted = False
        self.music_volume = DEFAULT_MUSIC_VOLUME
        self.game_volume = DEFAULT_GAME_VOLUME
        self.theme_index = 0
        self.bird_index = 0
        self.mode_index = 0
        self.load()

    @property
    def theme(self):
        return THEMES[self.theme_index]

    @property
    def bird_style(self):
        return BIRD_STYLES[self.bird_index]

    @property
    def mode(self):
        return GAME_MODES[self.mode_index]

    def cycle_theme(self, step):
        self.theme_index = (self.theme_index + step) % len(THEMES)

    def cycle_bird(self, step):
        self.bird_index = (self.bird_index + step) % len(BIRD_STYLES)

    def cycle_mode(self, step):
        self.mode_index = (self.mode_index + step) % len(GAME_MODES)

    def set_volume_from_x(self, x, slider_rect):
        fraction = (x - slider_rect.left) / slider_rect.width
        self.music_volume = max(0.0, min(1.0, fraction))

    def set_game_volume_from_x(self, x, slider_rect):
        fraction = (x - slider_rect.left) / slider_rect.width
        self.game_volume = max(0.0, min(1.0, fraction))

    def apply_audio(self, audio):
        audio.set_music_volume(self.music_volume, self.muted)
        audio.set_effect_volume(self.game_volume)

    def load(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return

        def number(key, current):
            value = data.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return max(0.0, min(1.0, float(value)))
            return current

        def index(key, current, size):
            value = data.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                return value % size
            return current

        self.music_volume = number("music_volume", self.music_volume)
        self.game_volume = number("game_volume", self.game_volume)
        self.muted = bool(data.get("muted", self.muted))
        self.theme_index = index("theme_index", self.theme_index, len(THEMES))
        self.bird_index = index("bird_index", self.bird_index, len(BIRD_STYLES))
        self.mode_index = index("mode_index", self.mode_index, len(GAME_MODES))

    def save(self):
        payload = {
            "music_volume": round(self.music_volume, 3),
            "game_volume": round(self.game_volume, 3),
            "muted": self.muted,
            "theme_index": self.theme_index,
            "bird_index": self.bird_index,
            "mode_index": self.mode_index,
        }
        try:
            SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass


# --- Audio synthesis -------------------------------------------------------

def _synth_note(freq, duration, volume, harmonics=((1, 1.0),), decay=2.0,
                attack=0.006, release=0.06, rate=SAMPLE_RATE):
    """Render one enveloped note to raw 16-bit mono PCM bytes."""
    frames = max(1, int(rate * duration))
    attack_frames = max(1, int(rate * attack))
    release_frames = max(1, min(frames // 2, int(rate * release)))
    normaliser = sum(weight for _, weight in harmonics)
    data = bytearray(frames * 2)

    for i in range(frames):
        t = i / rate
        envelope = min(1.0, i / attack_frames)
        remaining = frames - i
        if remaining < release_frames:
            envelope *= remaining / release_frames
        envelope *= math.exp(-decay * t)

        value = 0.0
        for harmonic, weight in harmonics:
            value += weight * math.sin(2.0 * math.pi * freq * harmonic * t)
        value = value / normaliser * envelope * volume

        struct.pack_into("<h", data, i * 2, int(max(-1.0, min(1.0, value)) * 32767))

    return bytes(data)


def _synth_noise(duration, volume, decay, seed, rate=SAMPLE_RATE):
    """Render a short noise burst, high-passed into a hi-hat tick."""
    frames = max(1, int(rate * duration))
    rng = random.Random(seed)
    data = bytearray(frames * 2)
    previous = 0.0

    for i in range(frames):
        sample = rng.uniform(-1.0, 1.0)
        value = (sample - previous) * math.exp(-decay * i / rate) * volume
        previous = sample
        struct.pack_into("<h", data, i * 2,
                         int(max(-1.0, min(1.0, value)) * 32767))

    return bytes(data)


def _fit_pcm(pcm, frames):
    """Pad or trim raw 16-bit PCM to exactly `frames` samples."""
    size = max(0, frames * 2)
    if len(pcm) >= size:
        return pcm[:size]
    return pcm + b"\x00" * (size - len(pcm))


def build_sound_effects():
    """Short one-shot sounds."""
    return {
        "flap": pygame.mixer.Sound(buffer=_synth_note(
            560, 0.07, EFFECT_VOLUME, ((1, 1.0), (2, 0.35)),
            decay=14, release=0.03)),
        "score": pygame.mixer.Sound(buffer=_synth_note(
            1046.5, 0.11, EFFECT_VOLUME * 0.9,
            ((1, 1.0), (2, 0.2), (3, 0.1)), decay=9, release=0.04)),
        "hit": pygame.mixer.Sound(buffer=_synth_note(
            170, 0.32, EFFECT_VOLUME + 0.05,
            ((1, 1.0), (2, 0.45), (3, 0.2)), decay=5, release=0.1)),
        "pause": pygame.mixer.Sound(buffer=_synth_note(
            660, 0.06, 0.22, ((1, 1.0),), decay=20)),
        "resume": pygame.mixer.Sound(buffer=_synth_note(
            880, 0.06, 0.22, ((1, 1.0),), decay=20)),
    }


def build_music():
    """A bouncy 8-bar F-major tune: plucky lead, walking bass and drums.

    The chords are F - Dm - Bb - C. All four layers are padded to the same
    slot grid, so they loop in sync.
    """
    step = 60.0 / 132.0 / 2.0  # eighth note at 132 BPM
    slot = int(SAMPLE_RATE * step)
    slots = 64  # 8 bars of 4/4

    def midi(note):
        return 440.0 * 2 ** ((note - 69) / 12.0)

    lead_cache = {}

    def lead(note):
        if note not in lead_cache:
            lead_cache[note] = _synth_note(
                midi(note), step * 0.82, MUSIC_VOLUME,
                ((1, 1.0), (3, 0.22), (5, 0.08)), decay=3.8,
                attack=0.004, release=0.045)
        return lead_cache[note]

    bass_cache = {}

    def bass(note):
        if note not in bass_cache:
            bass_cache[note] = _synth_note(
                midi(note), step * 0.8, MUSIC_VOLUME * 0.85,
                ((1, 1.0), (2, 0.28)), decay=8.0,
                attack=0.004, release=0.03)
        return bass_cache[note]

    hats = {
        False: [_synth_noise(0.032, MUSIC_VOLUME * 0.28, 110, seed=11 + i)
                for i in range(4)],
        True: [_synth_noise(0.038, MUSIC_VOLUME * 0.45, 95, seed=21 + i)
               for i in range(4)],
    }
    kick = _synth_note(72, 0.11, MUSIC_VOLUME * 0.6,
                       ((1, 1.0), (2, 0.25)), decay=14, release=0.04)

    melody = [
        84, 81, 77, 81, 84, 81, 77, 0,   # F
        77, 79, 81, 82, 81, 79, 77, 0,   # F
        74, 77, 81, 77, 74, 77, 81, 0,   # Dm
        81, 77, 74, 77, 81, 86, 84, 81,  # Dm
        70, 74, 77, 74, 70, 74, 77, 0,   # Bb
        77, 79, 81, 82, 84, 82, 81, 79,  # Bb
        72, 76, 79, 76, 72, 76, 79, 81,  # C
        79, 77, 76, 74, 72, 74, 76, 0,   # C
    ]
    roots = [41, 41, 38, 38, 34, 34, 36, 36]  # F2 F2 D2 D2 Bb1 Bb1 C2 C2
    bassline = [
        note
        for root in roots
        for note in (root, root + 7, root + 12, root + 7,
                     root, root + 7, root + 12, root + 7)
    ]

    lead_track = bytearray()
    for note in melody:
        lead_track += _fit_pcm(lead(note) if note else b"", slot)

    bass_track = bytearray()
    for note in bassline:
        bass_track += _fit_pcm(bass(note), slot)

    hat_track = bytearray()
    for index in range(slots):
        accent = index % 2 == 0
        hat_track += _fit_pcm(hats[accent][index % 4], slot)

    kick_track = bytearray()
    for index in range(slots):
        on_beat = index % 8 in (0, 4)
        kick_track += _fit_pcm(kick if on_beat else b"", slot)

    return [pygame.mixer.Sound(buffer=bytes(lead_track)),
            pygame.mixer.Sound(buffer=bytes(bass_track)),
            pygame.mixer.Sound(buffer=bytes(hat_track)),
            pygame.mixer.Sound(buffer=bytes(kick_track))]


class Audio:
    """Holds sound effects and the looping music layers."""

    def __init__(self):
        self.sounds = {}
        self.music_channels = []
        self.music_ready = False
        self.music_paused = False
        self.music_volume = 1.0
        self.effect_volume = 1.0
        try:
            # pygame.init() may already have opened the mixer at CD quality;
            # quit first, otherwise the new format is silently ignored.
            if pygame.mixer.get_init() != (SAMPLE_RATE, -16, 1):
                pygame.mixer.quit()
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1,
                                  buffer=512)
        except pygame.error:
            return

        self.sounds = build_sound_effects()
        tracks = build_music()
        if tracks:
            if pygame.mixer.get_num_channels() < len(tracks) + 4:
                pygame.mixer.set_num_channels(len(tracks) + 4)
            self.music_channels = [pygame.mixer.Channel(i) for i in range(len(tracks))]
            for channel, track in zip(self.music_channels, tracks):
                channel.play(track, loops=-1)
            self.music_ready = True

    def play(self, name):
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def set_music_volume(self, volume, muted):
        self.music_volume = 0.0 if muted else max(0.0, min(1.0, volume))
        for channel in self.music_channels:
            channel.set_volume(self.music_volume)

    def set_effect_volume(self, volume):
        self.effect_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.effect_volume)

    def pause_music(self):
        if self.music_ready and not self.music_paused:
            for channel in self.music_channels:
                channel.pause()
            self.music_paused = True

    def resume_music(self):
        if self.music_ready and self.music_paused:
            for channel in self.music_channels:
                channel.unpause()
            self.music_paused = False


# --- Game state ------------------------------------------------------------

class Pipe:
    __slots__ = ("x", "gap_y", "gap", "scored")

    def __init__(self, x, gap_y, gap):
        self.x = x
        self.gap_y = gap_y
        self.gap = gap
        self.scored = False

    def top_rect(self):
        bottom = int(self.gap_y - self.gap / 2)
        return pygame.Rect(int(self.x), PLAY_TOP, PIPE_WIDTH, bottom - PLAY_TOP)

    def bottom_rect(self):
        top = int(self.gap_y + self.gap / 2)
        return pygame.Rect(int(self.x), top, PIPE_WIDTH, PLAY_BOTTOM - top)


def circle_hits_rect(cx, cy, radius, rect):
    nearest_x = max(rect.left, min(cx, rect.right))
    nearest_y = max(rect.top, min(cy, rect.bottom))
    dx = cx - nearest_x
    dy = cy - nearest_y
    return dx * dx + dy * dy < radius * radius


class FlappyGame:
    def __init__(self, mode_index=0):
        self.mode_index = mode_index % len(GAME_MODES)
        self.high_scores = load_high_scores()
        self.reset()

    @property
    def mode(self):
        return GAME_MODES[self.mode_index]

    @property
    def high_score(self):
        return self.high_scores.get(self.mode["name"], 0)

    def reset(self):
        self.state = "ready"  # ready -> playing -> over
        self.paused = False
        self.ready_y = (PLAY_TOP + PLAY_BOTTOM) / 2 - 16
        self.bird_y = self.ready_y
        self.velocity = 0.0
        self.pipes = []
        self.score = 0
        self.new_best = False
        self.speed = self.mode["speed"]
        self.spawn_timer = 0.5
        self.scroll = 0.0
        self.elapsed = 0.0
        self.wing_timer = 0.0

    def start(self):
        self.reset()
        self.state = "playing"
        self.flap()

    def retry(self):
        self.start()

    def flap(self):
        self.velocity = self.mode["flap"]
        self.wing_timer = 0.16

    def spawn_pipe(self):
        gap = self.mode["gap"]
        low = PLAY_TOP + PIPE_MIN_MARGIN + gap / 2
        high = PLAY_BOTTOM - PIPE_MIN_MARGIN - gap / 2
        self.pipes.append(Pipe(WIDTH + 24, random.uniform(low, high), gap))

    def die(self):
        self.state = "over"
        self.paused = False
        self.new_best = self.score > self.high_score
        if self.new_best:
            self.high_scores[self.mode["name"]] = self.score
            save_high_scores(self.high_scores)

    def update(self, dt):
        """Advance the simulation. Returns a list of sound events."""
        events = []
        self.elapsed += dt
        self.wing_timer = max(0.0, self.wing_timer - dt)

        if self.state == "ready":
            self.bird_y = self.ready_y + math.sin(self.elapsed * 3.4) * 9.0
            return events
        if self.state != "playing" or self.paused:
            return events

        self.scroll += self.speed * dt
        self.velocity = min(MAX_FALL, self.velocity + self.mode["gravity"] * dt)
        self.bird_y += self.velocity * dt

        # The ceiling is a wall, the ground is death.
        if self.bird_y - BIRD_RADIUS < PLAY_TOP:
            self.bird_y = PLAY_TOP + BIRD_RADIUS
            self.velocity = max(self.velocity, 0.0)

        self.spawn_timer -= dt
        while self.spawn_timer <= 0:
            self.spawn_pipe()
            self.spawn_timer += self.mode["interval"]

        for pipe in self.pipes:
            pipe.x -= self.speed * dt
            if not pipe.scored and pipe.x + PIPE_WIDTH < BIRD_X:
                pipe.scored = True
                self.score += 1
                self.speed = min(self.mode["max_speed"],
                                 self.mode["speed"] + self.score * self.mode["ramp"])
                events.append("score")
        self.pipes = [pipe for pipe in self.pipes if pipe.x + PIPE_WIDTH + 24 > 0]

        if self.bird_y + BIRD_RADIUS >= PLAY_BOTTOM:
            self.bird_y = PLAY_BOTTOM - BIRD_RADIUS
            self.die()
            events.append("hit")
            return events

        for pipe in self.pipes:
            for rect in (pipe.top_rect(), pipe.bottom_rect()):
                if circle_hits_rect(BIRD_X, self.bird_y, BIRD_RADIUS - 1, rect):
                    self.die()
                    events.append("hit")
                    return events

        return events


# --- Bird art --------------------------------------------------------------

_BIRD_CACHE = {}


def shade(color, factor):
    return tuple(max(0, min(255, int(channel * factor))) for channel in color)


def bird_frames(style):
    """Two wing poses, rendered once per bird style."""
    cached = _BIRD_CACHE.get(style["name"])
    if cached is not None:
        return cached

    frames = []
    for wing_offset in (-3, 3):
        surf = pygame.Surface((52, 42), pygame.SRCALPHA)
        # Tail
        pygame.draw.polygon(surf, style["wing"], [(10, 20), (1, 12), (3, 30), (11, 27)])
        # Body with a darker outline
        pygame.draw.ellipse(surf, style["wing"], (4, 7, 38, 30))
        pygame.draw.ellipse(surf, style["body"], (6, 9, 34, 26))
        pygame.draw.ellipse(surf, style["belly"], (13, 20, 20, 11))
        # Wing
        pygame.draw.ellipse(surf, style["wing"], (8, 15 + wing_offset, 19, 11))
        # Eye
        pygame.draw.circle(surf, (252, 252, 255), (32, 16), 6)
        pygame.draw.circle(surf, (32, 34, 42), (34, 16), 3)
        # Beak
        pygame.draw.polygon(surf, style["beak"], [(35, 20), (50, 25), (35, 30)])
        pygame.draw.line(surf, shade(style["beak"], 0.75), (36, 25), (48, 25), 1)
        frames.append(surf)

    _BIRD_CACHE[style["name"]] = frames
    return frames


# --- Background art --------------------------------------------------------

_BACKGROUND_CACHE = {}


def build_background(theme):
    surface = pygame.Surface((WIDTH, PLAY_BOTTOM))
    top, bottom = theme["sky_top"], theme["sky_bottom"]
    for y in range(PLAY_BOTTOM):
        t = y / max(1, PLAY_BOTTOM - 1)
        color = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom))
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))

    if theme.get("stars"):
        for x, y in STARS:
            pygame.draw.circle(surface, theme["star"], (x, y), 2)

    for cx, cy, scale in CLOUDS:
        draw_cloud(surface, cx, cy, scale, theme["cloud"])

    for x, w, h in HILLS_BACK:
        pygame.draw.ellipse(surface, theme["hill_back"],
                            (x - w // 2, PLAY_BOTTOM - h, w, h * 2))
    for x, w, h in HILLS_FRONT:
        pygame.draw.ellipse(surface, theme["hill_front"],
                            (x - w // 2, PLAY_BOTTOM - h, w, h * 2))
    return surface


def background_for(theme_index):
    cached = _BACKGROUND_CACHE.get(theme_index)
    if cached is None:
        cached = build_background(THEMES[theme_index])
        _BACKGROUND_CACHE[theme_index] = cached
    return cached


def draw_cloud(surface, cx, cy, scale, color):
    width = max(2, int(96 * scale))
    height = max(2, int(34 * scale))
    pygame.draw.ellipse(surface, color,
                        (cx - width // 2, cy - height // 2, width, height))
    pygame.draw.circle(surface, color, (cx - width // 4, cy), max(2, int(16 * scale)))
    pygame.draw.circle(surface, color,
                       (cx + width // 5, cy - int(10 * scale)), max(2, int(20 * scale)))
    pygame.draw.circle(surface, color,
                       (cx + width // 3, cy + int(2 * scale)), max(2, int(13 * scale)))


# --- Layout ----------------------------------------------------------------

def pause_button_rect():
    width, height = PAUSE_BTN_SIZE
    return pygame.Rect((WIDTH - width) // 2, PAUSE_BTN_Y, width, height)


def settings_button_rect():
    pause = pause_button_rect()
    width, height = PAUSE_BTN_SIZE
    return pygame.Rect(pause.right + 8, pause.top, width, height)


def settings_layout():
    """Geometry for the full-window settings screen."""
    label_x = 48
    control_x = 224
    music_cy = 128
    game_cy = 172
    mute_cy = 216
    bg_cy = 264
    bird_cy = 308
    mode_cy = 352

    return {
        "label_x": label_x,
        "music_cy": music_cy,
        "game_cy": game_cy,
        "mute_cy": mute_cy,
        "bg_cy": bg_cy,
        "bird_cy": bird_cy,
        "mode_cy": mode_cy,
        "blurb_y": mode_cy + 26,
        "back": pygame.Rect(WIDTH - 126, 14, 86, 30),
        "slider": pygame.Rect(control_x, music_cy - 12, 152, 24),
        "game_slider": pygame.Rect(control_x, game_cy - 12, 152, 24),
        "percent_x": control_x + 166,
        "mute": pygame.Rect(control_x, mute_cy - 16, 104, 32),
        "bg_left": pygame.Rect(control_x, bg_cy - 15, 30, 30),
        "bg_right": pygame.Rect(control_x + 172, bg_cy - 15, 30, 30),
        "bird_left": pygame.Rect(control_x, bird_cy - 15, 30, 30),
        "bird_right": pygame.Rect(control_x + 172, bird_cy - 15, 30, 30),
        "mode_left": pygame.Rect(control_x, mode_cy - 15, 30, 30),
        "mode_right": pygame.Rect(control_x + 172, mode_cy - 15, 30, 30),
        "name_x": control_x + 94,
    }


# --- Rendering -------------------------------------------------------------

def draw_overlay(screen, title, lines, fonts, theme, top=None):
    """Center a card over the play area, or pin it below the HUD."""
    big_font = fonts[1]
    overlay = pygame.Surface((WIDTH, HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR)
    screen.blit(overlay, (0, HUD_HEIGHT))

    rendered = [(big_font.render(title, True, TEXT_COLOR), 14)]
    for text, font, color in lines:
        rendered.append((font.render(text, True, color), 7))

    content_width = max(surf.get_width() for surf, _ in rendered)
    total = sum(surf.get_height() + gap for surf, gap in rendered) - rendered[-1][1]
    card = pygame.Rect(0, 0, content_width + 60, total + 44)
    if top is None:
        card.center = (WIDTH // 2, (PLAY_TOP + PLAY_BOTTOM) // 2)
    else:
        card.top = top
        card.centerx = WIDTH // 2
    pygame.draw.rect(screen, theme["hud"], card, border_radius=16)
    pygame.draw.rect(screen, ACCENT_COLOR, card, width=2, border_radius=16)

    y = card.top + 22
    for surf, gap in rendered:
        screen.blit(surf, surf.get_rect(midtop=(WIDTH // 2, y)))
        y += surf.get_height() + gap


def draw_arrow_button(screen, rect, direction, hovered):
    pygame.draw.rect(screen, PAUSE_BTN_HOVER if hovered else PAUSE_BTN_COLOR,
                     rect, border_radius=6)
    pygame.draw.rect(screen, PAUSE_BTN_BORDER, rect, width=1, border_radius=6)
    cx, cy = rect.center
    if direction < 0:
        points = [(cx + 3, cy - 7), (cx + 3, cy + 7), (cx - 4, cy)]
    else:
        points = [(cx - 3, cy - 7), (cx - 3, cy + 7), (cx + 4, cy)]
    pygame.draw.polygon(screen, TEXT_COLOR, points)


def draw_hud_button(screen, rect, hovered):
    pygame.draw.rect(screen, PAUSE_BTN_HOVER if hovered else PAUSE_BTN_COLOR,
                     rect, border_radius=7)
    pygame.draw.rect(screen, PAUSE_BTN_BORDER, rect, width=1, border_radius=7)


def draw_pause_button(screen, game):
    rect = pause_button_rect()
    draw_hud_button(screen, rect, rect.collidepoint(pygame.mouse.get_pos()))
    cx, cy = rect.center

    if game.paused:
        pygame.draw.polygon(screen, TEXT_COLOR, [
            (cx - 6, cy - 8), (cx - 6, cy + 8), (cx + 8, cy),
        ])
    else:
        bar_w, bar_h, gap = 5, 16, 5
        left = cx - (bar_w * 2 + gap) // 2
        top = cy - bar_h // 2
        pygame.draw.rect(screen, TEXT_COLOR, (left, top, bar_w, bar_h), border_radius=2)
        pygame.draw.rect(screen, TEXT_COLOR,
                         (left + bar_w + gap, top, bar_w, bar_h), border_radius=2)


def draw_settings_button(screen, opened):
    rect = settings_button_rect()
    draw_hud_button(screen, rect, rect.collidepoint(pygame.mouse.get_pos()))
    cx, cy = rect.center
    # Three sliders, the usual "settings" glyph.
    for index, offset in enumerate((-7, 0, 7)):
        pygame.draw.line(screen, TEXT_COLOR, (cx - 10, cy + offset),
                         (cx + 10, cy + offset), 2)
        knob_x = cx + (-4 if index != 1 else 5)
        pygame.draw.circle(screen, ACCENT_COLOR if opened else TEXT_COLOR,
                           (knob_x, cy + offset), 3)


def draw_pipe_segment(screen, rect, theme, cap_at_bottom):
    if rect.height <= 0:
        return
    pygame.draw.rect(screen, theme["pipe"], rect)
    pygame.draw.rect(screen, theme["pipe_light"],
                     (rect.left + 8, rect.top, 7, rect.height))
    pygame.draw.rect(screen, theme["pipe_dark"],
                     (rect.right - 9, rect.top, 9, rect.height))

    lip = pygame.Rect(rect.left - PIPE_CAP_OVERHANG,
                      rect.bottom - PIPE_CAP_HEIGHT if cap_at_bottom else rect.top,
                      rect.width + PIPE_CAP_OVERHANG * 2, PIPE_CAP_HEIGHT)
    pygame.draw.rect(screen, theme["pipe"], lip, border_radius=3)
    pygame.draw.rect(screen, theme["pipe_dark"], lip, width=2, border_radius=3)
    pygame.draw.rect(screen, theme["pipe_light"],
                     (lip.left + 8, lip.top + 3, 7, lip.height - 6))


def draw_ground(screen, game, theme):
    pygame.draw.rect(screen, theme["ground"], (0, PLAY_BOTTOM, WIDTH, GROUND_HEIGHT))
    pygame.draw.rect(screen, theme["ground_top"], (0, PLAY_BOTTOM, WIDTH, 8))

    stripe_width, spacing = 26, 52
    offset = int(game.scroll) % spacing
    for x in range(-spacing + offset, WIDTH + spacing, spacing):
        pygame.draw.rect(screen, theme["ground_alt"],
                         (x, PLAY_BOTTOM + 8, stripe_width, GROUND_HEIGHT - 8))


def draw_bird(screen, game, settings):
    frames = bird_frames(settings.bird_style)
    if game.wing_timer > 0:
        frame = frames[int(game.elapsed * 30) % 2]
    else:
        frame = frames[int(game.elapsed * 6) % 2]

    if game.state == "playing":
        angle = max(-70.0, min(26.0, -game.velocity * 0.055))
    elif game.state == "over":
        angle = max(-70.0, min(26.0, -game.velocity * 0.055))
    else:
        angle = 0.0

    surface = pygame.transform.rotozoom(frame, angle, 1.0)
    screen.blit(surface, surface.get_rect(center=(BIRD_X, int(game.bird_y))))


def draw(screen, game, fonts, settings):
    hud_font, big_font, small_font, label_font, score_font = fonts
    theme = settings.theme

    screen.blit(background_for(settings.theme_index), (0, 0))
    draw_ground(screen, game, theme)

    for pipe in game.pipes:
        draw_pipe_segment(screen, pipe.top_rect(), theme, cap_at_bottom=True)
        draw_pipe_segment(screen, pipe.bottom_rect(), theme, cap_at_bottom=False)

    draw_bird(screen, game, settings)

    # Score, with a soft shadow so it reads on any sky.
    if game.state == "playing":
        score = str(game.score)
        shadow = score_font.render(score, True, shade(theme["sky_top"], 0.45))
        text = score_font.render(score, True, TEXT_COLOR)
        rect = text.get_rect(midtop=(WIDTH // 2, PLAY_TOP + 10))
        screen.blit(shadow, rect.move(3, 4))
        screen.blit(text, rect)

    # HUD
    pygame.draw.rect(screen, theme["hud"], (0, 0, WIDTH, HUD_HEIGHT))
    pygame.draw.line(screen, shade(theme["hud"], 1.4),
                     (0, HUD_HEIGHT - 1), (WIDTH, HUD_HEIGHT - 1), 2)

    best_surf = hud_font.render(f"Best  {game.high_score}", True, MUTED_COLOR)
    mode_surf = hud_font.render(game.mode["name"], True, theme["pipe_light"])
    screen.blit(best_surf, (14, (HUD_HEIGHT - best_surf.get_height()) // 2))
    screen.blit(mode_surf, (WIDTH - mode_surf.get_width() - 14,
                            (HUD_HEIGHT - mode_surf.get_height()) // 2))

    draw_pause_button(screen, game)
    draw_settings_button(screen, settings.open)

    # Overlays
    if game.state == "ready":
        draw_overlay(screen, "FLAPPY BIRD", [
            (f"Best {game.high_score}  ·  {game.mode['name']}", small_font, MUTED_COLOR),
            ("SPACE or click to flap", hud_font, ACCENT_COLOR),
            ("Up / Space flap  ·  P pause  ·  O settings", small_font, MUTED_COLOR),
            (QUIT_HINT, small_font, MUTED_COLOR),
        ], fonts, theme, top=PLAY_TOP + 22)
    elif game.state == "over":
        lines = [
            (f"Score {game.score}", hud_font, TEXT_COLOR),
            (f"Best ({game.mode['name']}) {game.high_score}", small_font, MUTED_COLOR),
        ]
        if game.new_best and game.score > 0:
            lines.append(("NEW BEST!", hud_font, ACCENT_COLOR))
        lines.append(("SPACE or R to retry", hud_font, ACCENT_COLOR))
        lines.append((QUIT_HINT, small_font, MUTED_COLOR))
        draw_overlay(screen, "GAME OVER", lines, fonts, theme)
    elif game.paused:
        draw_overlay(screen, "PAUSED", [
            (f"Score {game.score}", hud_font, TEXT_COLOR),
            ("Press P or click the button to resume", small_font, ACCENT_COLOR),
            (QUIT_HINT, small_font, MUTED_COLOR),
        ], fonts, theme)

    pygame.display.flip()


def draw_settings_screen(screen, settings, fonts):
    """The settings screen is a screen of its own, drawn over the whole window."""
    hud_font, big_font, small_font, label_font, score_font = fonts
    layout = settings_layout()
    theme = settings.theme
    mouse = pygame.mouse.get_pos()

    screen.fill(theme["hud"])

    title = big_font.render("SETTINGS", True, TEXT_COLOR)
    screen.blit(title, title.get_rect(midtop=(WIDTH // 2, 8)))
    subtitle = small_font.render("Changes save automatically", True, MUTED_COLOR)
    screen.blit(subtitle, subtitle.get_rect(midtop=(WIDTH // 2, 62)))
    pygame.draw.line(screen, shade(theme["hud"], 1.6),
                     (40, 88), (WIDTH - 40, 88), 2)

    back = layout["back"]
    hovered = back.collidepoint(mouse)
    pygame.draw.rect(screen, PAUSE_BTN_HOVER if hovered else PAUSE_BTN_COLOR,
                     back, border_radius=8)
    pygame.draw.rect(screen, PAUSE_BTN_BORDER, back, width=1, border_radius=8)
    back_text = label_font.render("Back", True, TEXT_COLOR)
    screen.blit(back_text, back_text.get_rect(center=back.center))

    def label(text, cy):
        surf = label_font.render(text, True, MUTED_COLOR)
        screen.blit(surf, surf.get_rect(midleft=(layout["label_x"], cy)))

    track_color = shade(theme["hud"], 1.9)

    def volume_row(text, cy, slider, level, dimmed):
        label(text, cy)
        track = pygame.Rect(slider.left, slider.centery - 4, slider.width, 8)
        pygame.draw.rect(screen, track_color, track, border_radius=4)

        filled = pygame.Rect(track.left, track.top,
                             round(track.width * level), track.height)
        if filled.width:
            pygame.draw.rect(screen, (110, 114, 126) if dimmed else ACCENT_COLOR,
                             filled, border_radius=4)
        pygame.draw.circle(screen, MUTED_COLOR if dimmed else TEXT_COLOR,
                           (track.left + round(track.width * level), track.centery), 8)

        percent = small_font.render(f"{round(level * 100)}%", True, TEXT_COLOR)
        screen.blit(percent, percent.get_rect(midleft=(layout["percent_x"], track.centery)))

    # --- Music volume ---
    volume_row("Music volume", layout["music_cy"], layout["slider"],
               0.0 if settings.muted else settings.music_volume, settings.muted)

    # --- Game (effects) volume ---
    volume_row("Game volume", layout["game_cy"], layout["game_slider"],
               settings.game_volume, False)

    # --- Mute toggle ---
    label("Mute music", layout["mute_cy"])
    mute = layout["mute"]
    hovered = mute.collidepoint(mouse)
    if settings.muted:
        background = (92, 52, 58) if hovered else (74, 42, 48)
        border = (150, 78, 86)
        text, text_color = "Unmute", (255, 170, 175)
    else:
        background = PAUSE_BTN_HOVER if hovered else PAUSE_BTN_COLOR
        border = PAUSE_BTN_BORDER
        text, text_color = "Mute", TEXT_COLOR
    pygame.draw.rect(screen, background, mute, border_radius=7)
    pygame.draw.rect(screen, border, mute, width=1, border_radius=7)
    mute_text = label_font.render(text, True, text_color)
    screen.blit(mute_text, mute_text.get_rect(center=mute.center))

    def choice_row(y, name, swatch_color, swatch_border, name_color,
                   left_rect, right_rect):
        draw_arrow_button(screen, left_rect, -1, left_rect.collidepoint(mouse))
        draw_arrow_button(screen, right_rect, 1, right_rect.collidepoint(mouse))

        text = label_font.render(name, True, name_color)
        swatch = pygame.Rect(0, 0, 16, 16)
        total = swatch.width + 8 + text.get_width()
        x = layout["name_x"] - total // 2
        swatch.topleft = (x, y - 8)
        pygame.draw.rect(screen, swatch_color, swatch, border_radius=4)
        pygame.draw.rect(screen, swatch_border, swatch, width=1, border_radius=4)
        screen.blit(text, text.get_rect(midleft=(x + swatch.width + 8, y)))

    # --- Background theme ---
    label("Sky", layout["bg_cy"])
    choice_row(layout["bg_cy"], theme["name"], theme["sky_top"],
               (120, 128, 148), TEXT_COLOR, layout["bg_left"], layout["bg_right"])

    # --- Bird color ---
    label("Bird", layout["bird_cy"])
    style = settings.bird_style
    choice_row(layout["bird_cy"], style["name"], style["body"], style["wing"],
               style["belly"], layout["bird_left"], layout["bird_right"])

    # --- Game mode ---
    label("Game mode", layout["mode_cy"])
    mode = settings.mode
    choice_row(layout["mode_cy"], mode["name"], ACCENT_COLOR, ACCENT_COLOR,
               ACCENT_COLOR, layout["mode_left"], layout["mode_right"])
    blurb = small_font.render(mode["blurb"], True, MUTED_COLOR)
    screen.blit(blurb, blurb.get_rect(midtop=(WIDTH // 2, layout["blurb_y"])))

    hint = small_font.render("New mode starts next round  ·  ESC / O returns",
                             True, MUTED_COLOR)
    screen.blit(hint, hint.get_rect(midbottom=(WIDTH // 2, HEIGHT - 12)))

    pygame.display.flip()


# --- Main loop -------------------------------------------------------------

def main():
    pygame.init()
    pygame.display.set_caption("Flappy Bird")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    fonts = (
        pygame.font.SysFont("consolas", 20, bold=True),
        pygame.font.SysFont("consolas", 40, bold=True),
        pygame.font.SysFont("consolas", 15),
        pygame.font.SysFont("consolas", 17, bold=True),
        pygame.font.SysFont("consolas", 56, bold=True),
    )

    audio = Audio()
    settings = Settings()
    game = FlappyGame(settings.mode_index)
    settings.apply_audio(audio)

    running = True
    music_paused = False

    def open_settings():
        settings.open = True
        audio.play("pause")

    def close_settings():
        settings.open = False
        settings.save()
        audio.play("resume")

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                layout = settings_layout()

                if settings.open:
                    if layout["back"].collidepoint(pos):
                        close_settings()
                    elif layout["slider"].collidepoint(pos):
                        settings.drag_target = "music"
                        settings.set_volume_from_x(pos[0], layout["slider"])
                        settings.apply_audio(audio)
                    elif layout["game_slider"].collidepoint(pos):
                        settings.drag_target = "game"
                        settings.set_game_volume_from_x(pos[0], layout["game_slider"])
                        settings.apply_audio(audio)
                    elif layout["mute"].collidepoint(pos):
                        settings.muted = not settings.muted
                        settings.apply_audio(audio)
                    elif layout["bg_left"].collidepoint(pos):
                        settings.cycle_theme(-1)
                    elif layout["bg_right"].collidepoint(pos):
                        settings.cycle_theme(1)
                    elif layout["bird_left"].collidepoint(pos):
                        settings.cycle_bird(-1)
                    elif layout["bird_right"].collidepoint(pos):
                        settings.cycle_bird(1)
                    elif layout["mode_left"].collidepoint(pos):
                        settings.cycle_mode(-1)
                    elif layout["mode_right"].collidepoint(pos):
                        settings.cycle_mode(1)

                elif settings_button_rect().collidepoint(pos):
                    open_settings()

                elif pause_button_rect().collidepoint(pos) and game.state == "playing":
                    game.paused = not game.paused
                    audio.play("resume" if not game.paused else "pause")

                elif game.state == "ready":
                    game.start()
                    audio.play("flap")

                elif game.state == "playing" and not game.paused:
                    game.flap()
                    audio.play("flap")

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                settings.drag_target = None

            elif event.type == pygame.MOUSEMOTION and settings.drag_target:
                layout = settings_layout()
                if settings.drag_target == "music":
                    settings.set_volume_from_x(event.pos[0], layout["slider"])
                else:
                    settings.set_game_volume_from_x(event.pos[0], layout["game_slider"])
                settings.apply_audio(audio)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_o:
                    if settings.open:
                        close_settings()
                    else:
                        open_settings()

                elif event.key == pygame.K_ESCAPE:
                    if settings.open:
                        close_settings()
                    else:
                        running = False

                elif settings.open:
                    pass  # the settings screen swallows the other keys

                elif event.key == pygame.K_q:
                    running = False

                elif game.state == "over":
                    if event.key in (pygame.K_SPACE, pygame.K_r,
                                     pygame.K_RETURN, pygame.K_KP_ENTER):
                        game.retry()
                        audio.play("flap")

                elif game.paused:
                    if event.key == pygame.K_p:
                        game.paused = False
                        audio.play("resume")

                elif game.state == "ready":
                    if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        game.start()
                        audio.play("flap")

                else:  # playing
                    if event.key == pygame.K_p:
                        game.paused = True
                        audio.play("pause")
                    elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                        game.flap()
                        audio.play("flap")

        if not settings.open:
            if game.mode_index != settings.mode_index:
                game.mode_index = settings.mode_index
                game.reset()
            for name in game.update(dt):
                audio.play(name)

        # Music is silent on the settings screen, and while paused or dead.
        should_pause = game.state == "over" or game.paused or settings.open
        if should_pause != music_paused:
            if should_pause:
                audio.pause_music()
            else:
                audio.resume_music()
            music_paused = should_pause

        if settings.open:
            draw_settings_screen(screen, settings, fonts)
        else:
            draw(screen, game, fonts, settings)

    settings.save()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
