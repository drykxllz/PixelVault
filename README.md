# Desktop games

A small pygame project with a shared launcher and one folder per game.

## Layout

```
code/
  launcher/          the launcher app
    launcher.py      game picker / process runner / statistics
    make_icon.py     generates the desktop icon (styles a, b, c)
    icon.ico         app icon
    icon_b.ico       icon the desktop shortcut points at
    stats.json       playtime and session counts (created on first play)
  games/
    snake/
      main.py        the game
      game.json      name, description and accent color for the launcher
      settings.json  volumes, theme, snake color, mode
      highscore.json best score per mode
    flappy/
      main.py        the game
      game.json      name, description and accent color for the launcher
      settings.json  volumes, theme, bird color, mode
      highscore.json best score per mode
```

## Run it

- Double-click **Game Launcher** on the Desktop, or
- From a terminal:

```
cd C:\Users\steph\Desktop\code\launcher
python launcher.py
```

Requires Python with `pygame` (`pygame-ce`) installed.

## Statistics

Press **T** in the launcher to open the statistics screen. For each game it
shows:

- the best score and the per-mode scores, read from the game's
  `highscore.json`
- total playtime and number of sessions, plus when it was last played

Playtime is measured by the launcher while a game is running and saved to
`launcher\stats.json`, so keep launching games from the launcher to keep the
numbers accurate. Running `python main.py` directly does not add playtime.
Press **T** or **Esc** to go back, **R** to refresh the scores, and **Up** /
**Down** or the mouse wheel to scroll.

## Add a game

1. Create `code\games\<name>\main.py`.
2. Optionally create `game.json` in the same folder:

```json
{"name": "Astro Pong", "description": "Pong, but in space", "accent": [120, 200, 255]}
```

3. Start the launcher (or press **R** in it) and the game appears.

Each game is launched with its own folder as the working directory, so save
files written next to `main.py` stay with that game. Quitting a game returns
to the launcher.

## Regenerate the icon

```
cd C:\Users\steph\Desktop\code\launcher
python make_icon.py b        # a = glass card, b = neon glyph, c = bento tiles
python make_icon.py compare  # side-by-side preview in the temp folder
```

After regenerating, point the shortcut at the new icon if Explorer keeps
showing a cached one.
