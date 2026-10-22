"""Snake game with game modes, game-over/retry, pause, a settings screen,
sound, music and saved settings/high scores.

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

CELL = 24
COLS, ROWS = 22, 16
HUD_HEIGHT = 42
WIDTH = COLS * CELL
HEIGHT = ROWS * CELL + HUD_HEIGHT

START_LENGTH = 4

SCORE_FILE = Path(__file__).with_name("highscore.json")
SETTINGS_FILE = Path(__file__).with_name("settings.json")

TEXT_COLOR = (235, 238, 245)
MUTED_COLOR = (150, 158, 175)
ACCENT_COLOR = (255, 208, 100)
FOOD_COLOR = (240, 92, 92)
OVERLAY_COLOR = (10, 12, 16, 205)

PAUSE_BTN_SIZE = (38, 30)
PAUSE_BTN_Y = 6
PAUSE_BTN_COLOR = (48, 54, 70)
PAUSE_BTN_HOVER = (68, 76, 98)
PAUSE_BTN_BORDER = (84, 94, 118)

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# The launcher sets this so the game can say where quitting takes you.
LAUNCHED_FROM_LAUNCHER = os.environ.get("GAME_LAUNCHER") == "1"
QUIT_HINT = "ESC returns to the launcher" if LAUNCHED_FROM_LAUNCHER else "Press ESC to quit"

SAMPLE_RATE = 22050
MUSIC_VOLUME = 0.30  # peak amplitude baked into the music layers
EFFECT_VOLUME = 0.30
DEFAULT_MUSIC_VOLUME = 0.05  # first run with no settings file
DEFAULT_GAME_VOLUME = 0.8

THEMES = [
    {"name": "Midnight", "bg": (18, 20, 26), "grid": (28, 32, 42), "hud": (32, 36, 48)},
    {"name": "Forest", "bg": (14, 28, 20), "grid": (22, 42, 30), "hud": (24, 46, 34)},
    {"name": "Ocean", "bg": (12, 22, 36), "grid": (20, 32, 50), "hud": (22, 36, 56)},
    {"name": "Grape", "bg": (26, 16, 34), "grid": (40, 26, 50), "hud": (46, 30, 58)},
    {"name": "Ember", "bg": (30, 18, 14), "grid": (44, 28, 22), "hud": (52, 34, 26)},
]

SNAKE_STYLES = [
    {"name": "Lime", "body": (86, 220, 140), "head": (150, 255, 190)},
    {"name": "Cyan", "body": (80, 198, 235), "head": (160, 235, 255)},
    {"name": "Amber", "body": (235, 172, 70), "head": (255, 216, 130)},
    {"name": "Rose", "body": (232, 112, 175), "head": (255, 172, 214)},
    {"name": "Violet", "body": (156, 130, 242), "head": (206, 190, 255)},
    {"name": "Mono", "body": (200, 204, 212), "head": (245, 247, 250)},
]

GAME_MODES = [
    {"name": "Classic", "wrap": False, "start_speed": 135, "speed_step": 3,
     "min_speed": 75, "blurb": "Deadly walls, speeds up as you grow"},
    {"name": "Wrap", "wrap": True, "start_speed": 135, "speed_step": 3,
     "min_speed": 75, "blurb": "Edges wrap around, speeds up as you grow"},
    {"name": "Zen", "wrap": True, "start_speed": 160, "speed_step": 0,
     "min_speed": 160, "blurb": "Wrap around at a calm, constant speed"},
    {"name": "Blitz", "wrap": False, "start_speed": 110, "speed_step": 5,
     "min_speed": 55, "blurb": "Faster start, deadly walls, quick ramp-up"},
]


# --- High score storage ----------------------------------------------------

def load_high_scores():
    """Best score per mode. Old single-score files count as Classic."""
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

    legacy = data.get("high_score")
    if isinstance(legacy, int) and not isinstance(legacy, bool):
        scores[GAME_MODES[0]["name"]] = max(0, legacy)
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
        self.snake_index = 0
        self.mode_index = 0
        self.load()

    @property
    def theme(self):
        return THEMES[self.theme_index]

    @property
    def snake_style(self):
        return SNAKE_STYLES[self.snake_index]

    @property
    def mode(self):
        return GAME_MODES[self.mode_index]

    def cycle_theme(self, step):
        self.theme_index = (self.theme_index + step) % len(THEMES)

    def cycle_snake(self, step):
        self.snake_index = (self.snake_index + step) % len(SNAKE_STYLES)

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
        self.snake_index = index("snake_index", self.snake_index, len(SNAKE_STYLES))
        self.mode_index = index("mode_index", self.mode_index, len(GAME_MODES))

    def save(self):
        payload = {
            "music_volume": round(self.music_volume, 3),
            "game_volume": round(self.game_volume, 3),
            "muted": self.muted,
            "theme_index": self.theme_index,
            "snake_index": self.snake_index,
            "mode_index": self.mode_index,
        }
        try:
            SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass


# --- Audio synthesis -------------------------------------------------------

def _synth_note(freq, duration, volume, harmonics=((1, 1.0),), decay=2.0,
                attack=0.008, release=0.06, rate=SAMPLE_RATE):
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


def build_sound_effects():
    """Short one-shot sounds."""
    return {
        "eat": pygame.mixer.Sound(buffer=_synth_note(620, 0.09, EFFECT_VOLUME,
                                                     ((1, 1.0), (2, 0.2)), decay=6)),
        "death": pygame.mixer.Sound(buffer=_synth_note(300, 0.45, EFFECT_VOLUME + 0.04,
                                                       ((1, 1.0), (2, 0.3)), decay=2.5)),
        "pause": pygame.mixer.Sound(buffer=_synth_note(660, 0.06, 0.22,
                                                       ((1, 1.0),), decay=20)),
        "resume": pygame.mixer.Sound(buffer=_synth_note(880, 0.06, 0.22,
                                                        ((1, 1.0),), decay=20)),
    }


def build_music():
    """A gently looping 4-bar chiptune: soft arpeggio over a sustained bass."""
    beat = 0.3  # eighth note
    cache = {}

    def note(freq, duration, volume, harmonics, decay, release):
        key = (freq, duration, volume, harmonics, decay, release)
        if key not in cache:
            cache[key] = _synth_note(freq, duration, volume, harmonics, decay,
                                     release=release)
        return cache[key]

    # Am - G - F - E, arpeggiated.
    bars = [
        (220.00, [440.00, 523.25, 659.25, 523.25, 440.00, 523.25, 659.25, 880.00]),
        (196.00, [392.00, 493.88, 587.33, 493.88, 392.00, 493.88, 587.33, 783.99]),
        (174.61, [349.23, 440.00, 523.25, 440.00, 349.23, 440.00, 523.25, 698.46]),
        (164.81, [329.63, 415.30, 493.88, 415.30, 329.63, 415.30, 493.88, 659.25]),
    ]

    melody = bytearray()
    bass = bytearray()
    for root, arpeggio in bars:
        for freq in arpeggio:
            melody += note(freq, beat, MUSIC_VOLUME,
                           ((1, 1.0), (2, 0.18), (3, 0.06)), 2.2, 0.09)
        bass += note(root / 2, beat * len(arpeggio), MUSIC_VOLUME * 0.9,
                     ((1, 1.0), (2, 0.14)), 0.35, 0.25)

    return [pygame.mixer.Sound(buffer=bytes(melody)),
            pygame.mixer.Sound(buffer=bytes(bass))]


class Audio:
    """Holds sound effects and the two music layers."""

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

class SnakeGame:
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
        mid_x, mid_y = COLS // 2, ROWS // 2
        self.snake = [(mid_x - i, mid_y) for i in range(START_LENGTH)]
        self.direction = RIGHT
        self.pending_direction = RIGHT
        self.score = 0
        self.move_interval = self.mode["start_speed"]
        self.accumulator = 0
        self.food = self.spawn_food()
        self.game_over = False
        self.paused = False

    def spawn_food(self):
        free = [
            (x, y)
            for x in range(COLS)
            for y in range(ROWS)
            if (x, y) not in self.snake
        ]
        return random.choice(free) if free else None

    def turn(self, direction):
        # Ignore 180-degree reversals so the snake can't run into itself.
        if (direction[0] + self.direction[0], direction[1] + self.direction[1]) == (0, 0):
            return
        self.pending_direction = direction

    def step(self):
        """Advance one cell. Returns 'eat', 'die', or None."""
        self.direction = self.pending_direction
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        if self.mode["wrap"]:
            new_head = (new_head[0] % COLS, new_head[1] % ROWS)
        elif not (0 <= new_head[0] < COLS and 0 <= new_head[1] < ROWS):
            self.end_game()
            return "die"

        # Self collision (tail tip moves away, so it's fair to ignore it)
        body = self.snake if new_head == self.food else self.snake[:-1]
        if new_head in body:
            self.end_game()
            return "die"

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.move_interval = max(self.mode["min_speed"],
                                     self.move_interval - self.mode["speed_step"])
            self.food = self.spawn_food()
            if self.food is None:  # board filled: you win
                self.end_game()
            return "eat"

        self.snake.pop()
        return None

    def end_game(self):
        self.game_over = True
        if self.score > self.high_score:
            self.high_scores[self.mode["name"]] = self.score
            save_high_scores(self.high_scores)

    def update(self, dt):
        """Advance the simulation. Returns a list of sound events."""
        events = []
        if self.game_over or self.paused:
            return events

        self.accumulator += dt
        while self.accumulator >= self.move_interval and not self.game_over:
            self.accumulator -= self.move_interval
            result = self.step()
            if result == "eat":
                events.append("eat")
            elif result == "die":
                events.append("death")
        return events


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
    label_x = 60
    control_x = 250
    music_cy = 118
    game_cy = 162
    mute_cy = 206
    bg_cy = 250
    snake_cy = 294
    mode_cy = 338

    return {
        "label_x": label_x,
        "music_cy": music_cy,
        "game_cy": game_cy,
        "mute_cy": mute_cy,
        "bg_cy": bg_cy,
        "snake_cy": snake_cy,
        "mode_cy": mode_cy,
        "blurb_y": mode_cy + 24,
        "back": pygame.Rect(WIDTH - 132, 14, 92, 30),
        "slider": pygame.Rect(control_x, music_cy - 12, 150, 24),
        "game_slider": pygame.Rect(control_x, game_cy - 12, 150, 24),
        "percent_x": control_x + 164,
        "mute": pygame.Rect(control_x, mute_cy - 16, 104, 32),
        "bg_left": pygame.Rect(control_x, bg_cy - 15, 30, 30),
        "bg_right": pygame.Rect(control_x + 172, bg_cy - 15, 30, 30),
        "snake_left": pygame.Rect(control_x, snake_cy - 15, 30, 30),
        "snake_right": pygame.Rect(control_x + 172, snake_cy - 15, 30, 30),
        "mode_left": pygame.Rect(control_x, mode_cy - 15, 30, 30),
        "mode_right": pygame.Rect(control_x + 172, mode_cy - 15, 30, 30),
        "name_x": control_x + 101,
    }


# --- Rendering -------------------------------------------------------------

def draw_overlay(screen, title, lines, big_font):
    """Center a translucent panel over the play area."""
    overlay = pygame.Surface((WIDTH, HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR)
    screen.blit(overlay, (0, HUD_HEIGHT))

    rendered = [(big_font.render(title, True, TEXT_COLOR), 16)]
    for text, font, color in lines:
        rendered.append((font.render(text, True, color), 8))

    total = sum(surf.get_height() + gap for surf, gap in rendered) - rendered[-1][1]
    y = HUD_HEIGHT + (HEIGHT - HUD_HEIGHT - total) // 2
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
        # Play triangle
        pygame.draw.polygon(screen, TEXT_COLOR, [
            (cx - 6, cy - 8), (cx - 6, cy + 8), (cx + 8, cy),
        ])
    else:
        # Pause bars
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


def draw(screen, game, fonts, settings):
    font, big_font, small_font, label_font = fonts
    theme = settings.theme
    style = settings.snake_style

    screen.fill(theme["bg"])

    # Grid
    for x in range(COLS + 1):
        pygame.draw.line(screen, theme["grid"], (x * CELL, HUD_HEIGHT),
                         (x * CELL, HEIGHT))
    for y in range(ROWS + 1):
        pygame.draw.line(screen, theme["grid"], (0, HUD_HEIGHT + y * CELL),
                         (WIDTH, HUD_HEIGHT + y * CELL))

    # Food
    if game.food is not None:
        fx, fy = game.food
        rect = pygame.Rect(fx * CELL, HUD_HEIGHT + fy * CELL, CELL, CELL)
        pygame.draw.rect(screen, FOOD_COLOR, rect.inflate(-6, -6), border_radius=6)

    # Snake
    for index, (x, y) in enumerate(game.snake):
        color = style["head"] if index == 0 else style["body"]
        rect = pygame.Rect(x * CELL, HUD_HEIGHT + y * CELL, CELL, CELL)
        pygame.draw.rect(screen, color, rect.inflate(-3, -3), border_radius=5)

    # HUD
    pygame.draw.rect(screen, theme["hud"], (0, 0, WIDTH, HUD_HEIGHT))
    score_surf = font.render(f"Score  {game.score}", True, TEXT_COLOR)
    best_surf = font.render(f"Best  {game.high_score}", True, MUTED_COLOR)
    screen.blit(score_surf, (14, (HUD_HEIGHT - score_surf.get_height()) // 2))
    screen.blit(best_surf, (WIDTH - best_surf.get_width() - 14,
                            (HUD_HEIGHT - best_surf.get_height()) // 2))

    draw_pause_button(screen, game)
    draw_settings_button(screen, settings.open)

    # Overlays
    if game.game_over:
        draw_overlay(screen, "GAME OVER", [
            (f"Final score: {game.score}", font, TEXT_COLOR),
            (f"Best ({game.mode['name']}): {game.high_score}", small_font, MUTED_COLOR),
            (f"Mode: {game.mode['name']}", small_font, MUTED_COLOR),
            ("Press SPACE or R to retry", font, ACCENT_COLOR),
            (QUIT_HINT, small_font, MUTED_COLOR),
        ], big_font)
    elif game.paused:
        draw_overlay(screen, "PAUSED", [
            ("Press P or click the button to resume", font, ACCENT_COLOR),
            (QUIT_HINT, small_font, MUTED_COLOR),
        ], big_font)

    pygame.display.flip()


def draw_settings_screen(screen, settings, fonts):
    """The settings screen is a screen of its own, drawn over the whole window."""
    font, big_font, small_font, label_font = fonts
    layout = settings_layout()
    theme = settings.theme
    mouse = pygame.mouse.get_pos()

    screen.fill(theme["bg"])

    title = big_font.render("SETTINGS", True, TEXT_COLOR)
    screen.blit(title, title.get_rect(midtop=(WIDTH // 2, 6)))
    subtitle = small_font.render("Changes save automatically", True, MUTED_COLOR)
    screen.blit(subtitle, subtitle.get_rect(midtop=(WIDTH // 2, 60)))
    pygame.draw.line(screen, theme["grid"], (40, 84), (WIDTH - 40, 84), 2)

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

    track_color = tuple(min(255, channel + 30) for channel in theme["bg"])

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
    label("Background", layout["bg_cy"])
    choice_row(layout["bg_cy"], theme["name"], theme["bg"], (120, 128, 148),
               TEXT_COLOR, layout["bg_left"], layout["bg_right"])

    # --- Snake color ---
    label("Snake color", layout["snake_cy"])
    style = settings.snake_style
    choice_row(layout["snake_cy"], style["name"], style["body"], style["head"],
               style["head"], layout["snake_left"], layout["snake_right"])

    # --- Game mode ---
    label("Game mode", layout["mode_cy"])
    mode = settings.mode
    choice_row(layout["mode_cy"], mode["name"], ACCENT_COLOR, ACCENT_COLOR,
               ACCENT_COLOR, layout["mode_left"], layout["mode_right"])
    blurb = small_font.render(mode["blurb"], True, MUTED_COLOR)
    screen.blit(blurb, blurb.get_rect(midtop=(layout["name_x"], layout["blurb_y"])))

    hint = small_font.render("New mode starts on the next round  ·  ESC or O returns",
                             True, MUTED_COLOR)
    screen.blit(hint, hint.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10)))

    pygame.display.flip()


# --- Main loop -------------------------------------------------------------

def main():
    pygame.init()
    pygame.display.set_caption("Snake")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    fonts = (
        pygame.font.SysFont("consolas", 21, bold=True),
        pygame.font.SysFont("consolas", 42, bold=True),
        pygame.font.SysFont("consolas", 15),
        pygame.font.SysFont("consolas", 17, bold=True),
    )

    audio = Audio()
    settings = Settings()
    game = SnakeGame(settings.mode_index)
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
        dt = clock.tick(60)

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
                    elif layout["snake_left"].collidepoint(pos):
                        settings.cycle_snake(-1)
                    elif layout["snake_right"].collidepoint(pos):
                        settings.cycle_snake(1)
                    elif layout["mode_left"].collidepoint(pos):
                        settings.cycle_mode(-1)
                    elif layout["mode_right"].collidepoint(pos):
                        settings.cycle_mode(1)

                elif settings_button_rect().collidepoint(pos):
                    open_settings()

                elif not game.game_over and pause_button_rect().collidepoint(pos):
                    game.paused = not game.paused
                    audio.play("resume" if not game.paused else "pause")

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

                elif game.game_over:
                    if event.key in (pygame.K_SPACE, pygame.K_r, pygame.K_RETURN):
                        game.reset()

                elif event.key == pygame.K_p:
                    game.paused = not game.paused
                    audio.play("resume" if not game.paused else "pause")

                elif not game.paused:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        game.turn(UP)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        game.turn(DOWN)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        game.turn(LEFT)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        game.turn(RIGHT)

        if settings.open:
            # Picking a different mode starts a fresh round with it on return.
            if settings.mode_index != game.mode_index:
                game.mode_index = settings.mode_index
                game.reset()
        else:
            for name in game.update(dt):
                audio.play(name)

        # Music is silent on the settings screen, and while paused or dead.
        should_pause = game.game_over or game.paused or settings.open
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
