"""Game launcher — pick one of the games in the games folder and play it.

Run with:  python launcher.py     (from this folder)

Layout:
    code/
        launcher/     this app, its icon and the icon generator
        games/        one folder per game

Adding a game:
  * Drop a folder inside code/games/ that contains a main.py, and it shows up
    automatically (press R to rescan while the launcher is open).
  * Optionally add a game.json inside that folder:
        {"name": "My Game", "description": "What it is about", "accent": [r, g, b]}
  * Games run in their own folder, so their save files stay next to them.
"""

import ctypes
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pygame

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
GAMES_DIR = ROOT_DIR / "games"
STATS_FILE = APP_DIR / "stats.json"
TITLE = "Game Launcher"

WIDTH, HEIGHT = 720, 480
CARD_HEIGHT = 92
STATS_CARD_HEIGHT = 104
CARD_GAP = 12
HEADER_HEIGHT = 104
FOOTER_HEIGHT = 56

BG_COLOR = (16, 18, 24)
CARD_COLOR = (26, 30, 40)
CARD_HOVER = (36, 42, 56)
CARD_BORDER = (46, 52, 68)
TEXT_COLOR = (235, 238, 245)
MUTED_COLOR = (146, 154, 172)
ACCENT_COLOR = (255, 208, 100)
DANGER_COLOR = (240, 110, 110)


def read_high_scores(folder):
    """Best score per mode from a game's highscore.json, as {mode: score}."""
    score_file = Path(folder) / "highscore.json"
    try:
        data = json.loads(score_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}

    scores = {}
    stored = data.get("best")
    if isinstance(stored, dict):
        for name, value in stored.items():
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                scores[str(name)] = value

    # Old single-score files.
    legacy = data.get("high_score")
    if not scores and isinstance(legacy, int) and not isinstance(legacy, bool) and legacy >= 0:
        scores["Best"] = legacy
    return scores


def format_duration(seconds):
    """Compact playtime: 45s, 12m, 1h 05m."""
    seconds = max(0, int(round(seconds)))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def format_ago(timestamp):
    """How long ago a wall-clock timestamp was."""
    delta = max(0, time.time() - timestamp)
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    if delta < 86400 * 30:
        return f"{int(delta // 86400)}d ago"
    return time.strftime("%d %b %Y", time.localtime(timestamp))


class Stats:
    """Playtime and session counts, saved next to the launcher.

    Keyed by the game's folder name so renaming the display name in game.json
    does not lose its history.
    """

    def __init__(self):
        self.games = {}
        self.load()

    def load(self):
        try:
            data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return

        stored = data.get("games")
        if not isinstance(stored, dict):
            return
        for key, entry in stored.items():
            if not isinstance(entry, dict):
                continue
            plays = entry.get("plays", 0)
            seconds = entry.get("seconds", 0.0)
            last_played = entry.get("last_played", 0.0)
            if not isinstance(plays, int) or isinstance(plays, bool):
                plays = 0
            if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
                seconds = 0.0
            if not isinstance(last_played, (int, float)) or isinstance(last_played, bool):
                last_played = 0.0
            self.games[str(key)] = {
                "plays": max(0, plays),
                "seconds": max(0.0, float(seconds)),
                "last_played": max(0.0, float(last_played)),
            }

    def get(self, key):
        return self.games.get(key, {"plays": 0, "seconds": 0.0, "last_played": 0.0})

    def record(self, key, seconds):
        entry = self.games.setdefault(
            key, {"plays": 0, "seconds": 0.0, "last_played": 0.0})
        entry["plays"] += 1
        entry["seconds"] = round(entry["seconds"] + max(0.0, seconds), 3)
        entry["last_played"] = time.time()
        self.save()

    def save(self):
        try:
            STATS_FILE.write_text(json.dumps({"games": self.games}, indent=2),
                                  encoding="utf-8")
        except OSError:
            pass  # not fatal, just means no persistence


def discover_games():
    """One game per subfolder of games/ that contains a main.py."""
    games = []
    if not GAMES_DIR.is_dir():
        return games

    for entry in sorted(GAMES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        script = entry / "main.py"
        if not script.exists():
            continue

        meta = {}
        meta_file = entry / "game.json"
        if meta_file.exists():
            try:
                loaded = json.loads(meta_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    meta = loaded
            except (OSError, ValueError):
                meta = {}

        accent = meta.get("accent", (110, 170, 235))
        if not isinstance(accent, (list, tuple)) or len(accent) != 3:
            accent = (110, 170, 235)

        games.append({
            "key": entry.name,
            "name": str(meta.get("name") or entry.name.replace("_", " ").title()),
            "description": str(meta.get("description") or "A game in the games folder"),
            "path": script,
            "accent": tuple(int(channel) for channel in accent),
            "high_scores": read_high_scores(entry),
        })

    return games


def fit_text(font, text, max_width):
    """Trim text with an ellipsis so it fits in max_width pixels."""
    if font.size(text)[0] <= max_width:
        return text
    ellipsis = "..."
    trimmed = text
    while trimmed and font.size(trimmed + ellipsis)[0] > max_width:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + ellipsis


def restore_window():
    """Bring the launcher window back to the foreground after a game exits."""
    try:
        hwnd = pygame.display.get_wm_info().get("window")
    except pygame.error:
        return
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
    except (AttributeError, OSError):
        pass  # not on Windows; pygame's own re-init has already shown the window


class Launcher:
    def __init__(self):
        self.games = discover_games()
        self.stats = Stats()
        self.selected = 0
        self.scroll = 0
        self.hover = None
        self.toast = None
        self.toast_until = 0.0
        self.running = True
        self.view = "games"  # "games" or "stats"
        self.stats_scroll = 0

    # --- geometry ---
    @property
    def viewport(self):
        return pygame.Rect(40, HEADER_HEIGHT, WIDTH - 80,
                           HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT)

    def content_height(self):
        if not self.games:
            return 0
        return len(self.games) * (CARD_HEIGHT + CARD_GAP) - CARD_GAP

    def max_scroll(self):
        return max(0, self.content_height() - self.viewport.height)

    def card_rect(self, index):
        viewport = self.viewport
        return pygame.Rect(viewport.left,
                           viewport.top + index * (CARD_HEIGHT + CARD_GAP) - self.scroll,
                           viewport.width, CARD_HEIGHT)

    def index_at(self, pos):
        if not self.viewport.collidepoint(pos):
            return None
        for index in range(len(self.games)):
            if self.card_rect(index).collidepoint(pos):
                return index
        return None

    # --- statistics geometry ---
    def stats_content_height(self):
        if not self.games:
            return 0
        return len(self.games) * (STATS_CARD_HEIGHT + CARD_GAP) - CARD_GAP

    def stats_max_scroll(self):
        return max(0, self.stats_content_height() - self.viewport.height)

    def stats_card_rect(self, index):
        viewport = self.viewport
        return pygame.Rect(
            viewport.left,
            viewport.top + index * (STATS_CARD_HEIGHT + CARD_GAP) - self.stats_scroll,
            viewport.width, STATS_CARD_HEIGHT)

    # --- behaviour ---
    def set_toast(self, text):
        self.toast = text
        self.toast_until = time.monotonic() + 4.0

    def refresh_scores(self):
        for game in self.games:
            game["high_scores"] = read_high_scores(game["path"].parent)

    def open_stats(self):
        self.view = "stats"
        self.stats_scroll = 0
        self.refresh_scores()

    def scroll_stats_by(self, amount):
        self.stats_scroll = max(0, min(self.stats_max_scroll(),
                                       self.stats_scroll + amount))

    def scroll_by(self, amount):
        self.scroll = max(0, min(self.max_scroll(), self.scroll + amount))

    def ensure_visible(self, index):
        viewport = self.viewport
        top = index * (CARD_HEIGHT + CARD_GAP)
        if top - self.scroll < 0:
            self.scroll = top
        elif top + CARD_HEIGHT - self.scroll > viewport.height:
            self.scroll = top + CARD_HEIGHT - viewport.height
        self.scroll = max(0, min(self.max_scroll(), self.scroll))

    def select(self, index):
        if not self.games:
            return
        self.selected = max(0, min(len(self.games) - 1, index))
        self.ensure_visible(self.selected)

    def rescan(self):
        current = self.games[self.selected]["path"] if self.games else None
        self.games = discover_games()
        self.selected = 0
        for index, game in enumerate(self.games):
            if game["path"] == current:
                self.selected = index
                break
        self.scroll = 0
        self.ensure_visible(self.selected)
        self.set_toast(f"Found {len(self.games)} game{'s' if len(self.games) != 1 else ''}")

    def launch(self, index):
        if not (0 <= index < len(self.games)):
            return
        game = self.games[index]
        script = Path(game["path"])
        if not script.exists():
            self.set_toast(f"Missing file: {script.name}")
            return

        try:
            pygame.display.iconify()
        except pygame.error:
            pass

        result = 0
        elapsed = 0.0
        failed = False
        try:
            env = dict(os.environ, GAME_LAUNCHER="1")
            started = time.monotonic()
            result = subprocess.call([sys.executable, str(script)],
                                     cwd=str(script.parent), env=env)
            elapsed = time.monotonic() - started
        except OSError as exc:
            failed = True
            self.set_toast(f"Could not start {game['name']}: {exc}")
        finally:
            try:
                pygame.display.set_mode((WIDTH, HEIGHT))
                pygame.display.set_caption(TITLE)
                pygame.event.clear()
                restore_window()
            except pygame.error:
                pass

        if not failed:
            self.stats.record(game["key"], elapsed)
            self.refresh_scores()
        if result:
            self.set_toast(f"{game['name']} exited with code {result}")

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return

        if self.view == "stats":
            self.handle_stats_event(event)
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.select(self.selected + 1)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.select(self.selected - 1)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.launch(self.selected)
            elif event.key == pygame.K_t:
                self.open_stats()
            elif event.key == pygame.K_r:
                self.rescan()
            elif event.key == pygame.K_HOME:
                self.select(0)
            elif event.key == pygame.K_END:
                self.select(len(self.games) - 1)

        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_by(-event.y * 48)

        elif event.type == pygame.MOUSEMOTION:
            self.hover = self.index_at(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.index_at(event.pos)
            if index is not None:
                self.selected = index
                self.launch(index)

    def handle_stats_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_t):
                self.view = "games"
            elif event.key == pygame.K_q:
                self.running = False
            elif event.key == pygame.K_r:
                self.rescan()
                self.stats_scroll = 0
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.scroll_stats_by(48)
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.scroll_stats_by(-48)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_stats_by(self.viewport.height)
            elif event.key == pygame.K_PAGEUP:
                self.scroll_stats_by(-self.viewport.height)
            elif event.key == pygame.K_HOME:
                self.stats_scroll = 0
            elif event.key == pygame.K_END:
                self.stats_scroll = self.stats_max_scroll()
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll_stats_by(-event.y * 48)

    # --- shared drawing helpers ---
    def draw_toast(self, screen, subtitle_font):
        if not (self.toast and time.monotonic() < self.toast_until):
            return
        toast = subtitle_font.render(self.toast, True, TEXT_COLOR)
        box = toast.get_rect(midbottom=(WIDTH // 2, HEIGHT - FOOTER_HEIGHT - 6))
        box = box.inflate(28, 14)
        pygame.draw.rect(screen, (44, 30, 32), box, border_radius=8)
        pygame.draw.rect(screen, DANGER_COLOR, box, width=1, border_radius=8)
        screen.blit(toast, toast.get_rect(center=box.center))

    def draw_scrollbar(self, screen, content_height, scroll):
        maximum = max(0, content_height - self.viewport.height)
        if maximum <= 0:
            return
        viewport = self.viewport
        track = pygame.Rect(WIDTH - 28, viewport.top, 6, viewport.height)
        pygame.draw.rect(screen, (34, 38, 50), track, border_radius=3)
        ratio = viewport.height / content_height
        thumb_h = max(30, int(viewport.height * ratio))
        travel = viewport.height - thumb_h
        offset = int(travel * (scroll / maximum))
        thumb = pygame.Rect(track.left, viewport.top + offset, 6, thumb_h)
        pygame.draw.rect(screen, (90, 98, 120), thumb, border_radius=3)

    # --- drawing ---
    def draw(self, screen, fonts):
        title_font, subtitle_font, card_title_font, small_font = fonts
        mouse = pygame.mouse.get_pos()
        screen.fill(BG_COLOR)

        # Header
        title = title_font.render("GAME LAUNCHER", True, TEXT_COLOR)
        screen.blit(title, (40, 22))
        hint = subtitle_font.render("Pick a game and press Enter", True, MUTED_COLOR)
        screen.blit(hint, (40, 64))
        count = len(self.games)
        badge = small_font.render(
            f"{count} game{'s' if count != 1 else ''}", True, MUTED_COLOR)
        screen.blit(badge, badge.get_rect(topright=(WIDTH - 40, 30)))
        pygame.draw.line(screen, CARD_BORDER, (40, HEADER_HEIGHT - 14),
                         (WIDTH - 40, HEADER_HEIGHT - 14), 2)

        viewport = self.viewport
        old_clip = screen.get_clip()
        screen.set_clip(viewport)

        if not self.games:
            empty = subtitle_font.render(
                "No games found — add a folder with main.py to games/",
                True, MUTED_COLOR)
            screen.blit(empty, empty.get_rect(center=viewport.center))
        else:
            for index, game in enumerate(self.games):
                rect = self.card_rect(index)
                if rect.bottom < viewport.top or rect.top > viewport.bottom:
                    continue

                hovered = index == self.hover or self.card_rect(index).collidepoint(mouse)
                selected = index == self.selected
                accent = tuple(game.get("accent", ACCENT_COLOR))

                background = CARD_HOVER if (hovered or selected) else CARD_COLOR
                pygame.draw.rect(screen, background, rect, border_radius=12)
                border = accent if selected else (accent if hovered else CARD_BORDER)
                pygame.draw.rect(screen, border, rect, width=2 if selected else 1,
                                 border_radius=12)

                name = card_title_font.render(game["name"], True, TEXT_COLOR)
                screen.blit(name, (rect.left + 22, rect.top + 13))

                description = fit_text(subtitle_font, game["description"],
                                       rect.width - 130)
                desc_surf = subtitle_font.render(description, True, MUTED_COLOR)
                screen.blit(desc_surf, (rect.left + 22, rect.top + 46))

                try:
                    relative = game["path"].relative_to(ROOT_DIR)
                except ValueError:
                    relative = game["path"].name
                path_surf = small_font.render(str(relative), True, (110, 118, 138))
                screen.blit(path_surf, (rect.left + 22, rect.top + 70))

                # Play glyph
                cx, cy = rect.right - 44, rect.centery
                pygame.draw.circle(screen, (background[0] + 10, background[1] + 10,
                                           background[2] + 12), (cx, cy), 21)
                pygame.draw.polygon(screen, accent, [
                    (cx - 5, cy - 9), (cx - 5, cy + 9), (cx + 10, cy),
                ])

        screen.set_clip(old_clip)

        self.draw_scrollbar(screen, self.content_height(), self.scroll)
        self.draw_toast(screen, subtitle_font)

        # Footer
        pygame.draw.line(screen, CARD_BORDER, (40, HEIGHT - FOOTER_HEIGHT + 10),
                         (WIDTH - 40, HEIGHT - FOOTER_HEIGHT + 10), 2)
        hints = small_font.render(
            "Up / Down select   ·   Enter play   ·   T stats   ·   R rescan   ·   Esc quit",
            True, MUTED_COLOR)
        screen.blit(hints, (40, HEIGHT - 30))

        pygame.display.flip()

    def draw_stats(self, screen, fonts):
        title_font, subtitle_font, card_title_font, small_font = fonts
        screen.fill(BG_COLOR)

        title = title_font.render("STATISTICS", True, TEXT_COLOR)
        screen.blit(title, (40, 22))
        hint = subtitle_font.render("High scores and time played", True, MUTED_COLOR)
        screen.blit(hint, (40, 64))

        total_seconds = sum(self.stats.get(game["key"])["seconds"]
                            for game in self.games)
        badge = small_font.render(
            f"Total playtime  {format_duration(total_seconds)}", True, MUTED_COLOR)
        screen.blit(badge, badge.get_rect(topright=(WIDTH - 40, 30)))
        pygame.draw.line(screen, CARD_BORDER, (40, HEADER_HEIGHT - 14),
                         (WIDTH - 40, HEADER_HEIGHT - 14), 2)

        viewport = self.viewport
        old_clip = screen.get_clip()
        screen.set_clip(viewport)

        if not self.games:
            empty = subtitle_font.render(
                "No games found — add a folder with main.py to games/",
                True, MUTED_COLOR)
            screen.blit(empty, empty.get_rect(center=viewport.center))
        else:
            for index, game in enumerate(self.games):
                rect = self.stats_card_rect(index)
                if rect.bottom < viewport.top or rect.top > viewport.bottom:
                    continue

                accent = tuple(game.get("accent", ACCENT_COLOR))
                pygame.draw.rect(screen, CARD_COLOR, rect, border_radius=12)
                pygame.draw.rect(screen, CARD_BORDER, rect, width=1, border_radius=12)
                pygame.draw.rect(screen, accent,
                                 (rect.left + 16, rect.top + 14, 4,
                                  rect.height - 28), border_radius=2)

                entry = self.stats.get(game["key"])
                scores = game.get("high_scores") or {}
                best_value = max(scores.values(), default=0)
                best_mode = max(scores, key=scores.get) if scores else None

                name = fit_text(card_title_font, game["name"], rect.width - 280)
                screen.blit(card_title_font.render(name, True, accent),
                            (rect.left + 30, rect.top + 12))

                playtime = card_title_font.render(format_duration(entry["seconds"]),
                                                  True, TEXT_COLOR)
                screen.blit(playtime, playtime.get_rect(
                    topright=(rect.right - 22, rect.top + 12)))

                if best_value > 0:
                    best_text = f"Best {best_value}"
                    if best_mode:
                        best_text += f"  ·  {best_mode}"
                    best_color = TEXT_COLOR
                else:
                    best_text = "No score yet"
                    best_color = MUTED_COLOR
                best_surf = subtitle_font.render(best_text, True, best_color)
                screen.blit(best_surf, (rect.left + 30, rect.top + 45))

                plays = entry["plays"]
                if plays == 0:
                    plays_text = "Not played yet"
                else:
                    plays_text = f"{plays} play{'s' if plays != 1 else ''}"
                    if entry["last_played"]:
                        plays_text += f"  ·  last played {format_ago(entry['last_played'])}"
                plays_surf = small_font.render(plays_text, True, MUTED_COLOR)
                screen.blit(plays_surf, plays_surf.get_rect(
                    topright=(rect.right - 22, rect.top + 48)))

                if best_value > 0:
                    breakdown = "  ·  ".join(f"{mode} {value}"
                                             for mode, value in scores.items())
                else:
                    breakdown = "High scores appear here after your first round"
                breakdown = fit_text(small_font, breakdown, rect.width - 60)
                breakdown_surf = small_font.render(breakdown, True, MUTED_COLOR)
                screen.blit(breakdown_surf, (rect.left + 30, rect.top + 76))

        screen.set_clip(old_clip)

        self.draw_scrollbar(screen, self.stats_content_height(), self.stats_scroll)
        self.draw_toast(screen, subtitle_font)

        pygame.draw.line(screen, CARD_BORDER, (40, HEIGHT - FOOTER_HEIGHT + 10),
                         (WIDTH - 40, HEIGHT - FOOTER_HEIGHT + 10), 2)
        hints = small_font.render(
            "T / Esc back   ·   Up / Down scroll   ·   R refresh   ·   Q quit",
            True, MUTED_COLOR)
        screen.blit(hints, (40, HEIGHT - 30))

        pygame.display.flip()

    def run(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        clock = pygame.time.Clock()
        fonts = (
            pygame.font.SysFont("consolas", 30, bold=True),
            pygame.font.SysFont("consolas", 16),
            pygame.font.SysFont("consolas", 23, bold=True),
            pygame.font.SysFont("consolas", 13),
        )

        while self.running:
            clock.tick(60)
            for event in pygame.event.get():
                self.handle_event(event)
            if self.view == "stats":
                self.draw_stats(screen, fonts)
            else:
                self.draw(screen, fonts)

        pygame.quit()
        sys.exit(0)


def main():
    Launcher().run()


if __name__ == "__main__":
    main()
