# ROM-driven dialog verification

Implementation: `runtime-core/firered-dialog.mjs` and `app/dialog.js`.

`createDialogOverlay(container)` returns `update(core, state)`, `report()`, `setVisible(visible)` and `destroy()`. The container must be positioned. The overlay never captures input: existing X/Z/arrows continue to the original ROM. `update` must run after the same source frame used to render the scene. No independent text timer exists.

The observer reads the matching FireRed US 1.0 symbols `sTextPrinters=0x02020034`, `gWindows=0x020204b4`, `gStringVar4=0x02021d18`, `gDisplayedStringBattle=0x0202298c`. Printer stride 36 and window stride 12 come from the matching source structs. Only bytes consumed by the actual text printer are displayed. Clear/scroll/wait controls preserve page timing; in-progress scrolling and unsupported glyph/layout codes retain original cropped window pixels.

An allocated window is not assumed visible. The observer checks hardware BG enable, BG size, source scroll registers and tilemap ownership. This matters in battle: windows 1/2 slide into view for the action menu, while main text window 0 moves offscreen. Oak tutorials use window 24. The dialog overlay covers windows 0/24 or another verified wide bottom text window, and excludes all battle ancillary menus. `battle.js` owns action/move menus. Overworld choices use their exact source-window pixels and cursor; no choice labels or selected states are invented.

## Checks run

`node outputs/pokemon-remake/verification/dialog/probe.mjs` creates observed fixtures from actual ROM checkpoints. The Pallet house sign is reached with controller input from the outdoor checkpoint. Other fixtures derive from the original tutorial/battle progression. The fixture scripts do not write game RAM.

`node outputs/pokemon-remake/verification/dialog/test.mjs` passed 13 checks: page clear timing, scroll fallback, unknown glyph fallback, consumed sign prefix, nonmutating/paused observation, full completed sign, dismissal, battle-menu exclusion, Oak tutorial printer24, exact fallback RGBA, bounded original yes/no choice, and stale UI removal after restoring the no-dialog checkpoint. See `results.json`.

The Electron test `browser.cjs` passed six fixtures and captured six overlay screenshots. DOM text matched semantic output exactly, completed/partial text was readable, no text overflow occurred, dismissal hid the card, battle action menu did not duplicate dialog, and the original YES/NO cursor was preserved. See `browser-results.json` and `*-overlay.png`. The visual harness uses a neutral scene background to isolate the dialog; these captures do not claim character/environment quality.

## Limits

Unknown string storage, Japanese/special glyphs, positional formatting and partial scroll animation use a tightly bounded source window crop. Source text color changes currently retain content in the common legible dialog style. Full-screen menus are outside this module's responsibility. Battle command/move UI is a separately coordinated module. The original scene is never used as a full-screen fallback here.
