# Design system

## Brand

- **Name**: Imaa — Arabic *إيماءة* ("a gesture", "a nod"). Short, easy to say in both languages, and it names both input modes.
- **Logo**: an open hand with two motion arcs — "a wave" — in white on a violet → teal gradient squircle.
  Source: [`branding/logo.svg`](../branding/logo.svg); exports from 16 to 1024 px, `.ico`, `.icns`, Android adaptive icon and iOS app icon.
- **Gradient**: `#7C5CFF` → `#00C9A7` (135°). Violet = human/personal, teal = calm/technology.

## Tokens

| Token | Light | Dark |
|-------|-------|------|
| Background | `#F5F6FA` | `#0E1016` |
| Sidebar / surface | `#FFFFFF` | `#13161F` / `#181B26` |
| Surface alt | `#F0F1F7` | `#222636` |
| Border | `#E3E5EE` | `#2A2F3E` |
| Text | `#161A26` | `#ECEEF5` |
| Muted text | `#5F6678` | `#9AA2B5` |
| Accent | `#6A4DF5` | `#8B74FF` |
| Success / warning / danger | `#0E9F6E` / `#C27803` / `#E02D3C` | `#34D399` / `#FBBF24` / `#F87171` |

Radii: 16 px cards, 10 px controls, pills fully rounded. Spacing: 8-point grid; pages have 32 px side margins on desktop, 18 dp on phones.

## Principles

1. **One big obvious control.** The power button is the first thing you see; its state (idle grey / gradient with breathing rings / spinner while starting) is readable from across a room.
2. **Always show what the camera sees and what just happened.** Live pose overlay on the preview, a recent-actions feed, and a click-through HUD bubble for actions performed while the window is hidden.
3. **Learn by doing.** Practice mode lights up the matching gesture card without triggering anything; onboarding ends with a gesture tour.
4. **Safe by default.** Deliberate hold times, the 🤘 pause gesture, a global pause shortcut, and closing the window keeps the app in the tray — quitting is explicit.
5. **Bilingual from day one.** Every string is translated; Arabic switches the whole layout to right-to-left, including custom-painted switches.
6. **Respect resources.** Preview only while visible; idle mode when nobody is in view; power modes explained in plain words.

## Desktop layout

```
┌──────────┬───────────────────────────────────────────────┐
│ ◉ Imaa   │  Welcome back                                 │
│          │  ┌─────────────┐ ┌──────────────────────────┐ │
│ ⌂ Home   │  │   ( ⏻ )     │ │  Camera preview   [on]   │ │
│ ✋ Hand   │  │  ● Watching │ │                          │ │
│ ☺ Head   │  │ Pause  Recal│ │      👍 Thumb up          │ │
│ ≋ Profile│  │ Profile [▾] │ └──────────────────────────┘ │
│ ⚙ Settings│ └─────────────┘                              │
│ ⓘ About  │  Quick switches (hand · head · air mouse …)   │
│          │  Recent actions                               │
│ ● Watching│ 🔒 Your camera picture stays on this device   │
│ ☾  ع     │                                               │
└──────────┴───────────────────────────────────────────────┘
```

The sidebar footer has a live status dot, a one-click theme switch and a one-click language switch.
In Arabic the sidebar moves to the right and every row mirrors.

## Mobile

- **Android**: Material 3 with the brand palette (no dynamic colour, so the brand stays recognisable), bottom navigation (Home · Gestures · Remote · Settings), status bubble drawn by the Accessibility service, ongoing notification with Pause/Stop.
- **iOS**: native SwiftUI tab bar (Home · Viewer · Remote · Settings), SF Symbols, grouped backgrounds, system tint from the accent colour.

## Screenshots

| | |
|---|---|
| ![Home light](screenshots/en-light-home.png) | ![Home dark](screenshots/en-dark-home.png) |
| ![Hand gestures](screenshots/en-light-hand.png) | ![Head gestures](screenshots/en-dark-head.png) |
| ![Arabic light](screenshots/ar-light-home.png) | ![Arabic about](screenshots/ar-light-about.png) |
| ![Profiles](screenshots/en-light-profiles.png) | ![Settings](screenshots/en-dark-settings.png) |

Regenerate with `python desktop/scripts/screenshots.py`.
