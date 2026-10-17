# Business model

## Who pays, and why

| Segment | Pain | What they value | Willingness to pay |
|---------|------|-----------------|--------------------|
| **People with limited mobility** (RSI, ALS, MS, spinal injuries, temporary injuries) | Mouse/keyboard are painful or impossible | Head gestures, head pointer, reliability, privacy | Often low personally, but funded by insurers, NGOs, employers' accommodation budgets |
| **Presenters, teachers, lecturers** | Clickers get lost; walking back to the laptop | Slide control, black screen, phone as remote camera | Moderate, one-time |
| **Cooks, makers, musicians, mechanics** | Dirty or busy hands | Scroll recipes/manuals, turn sheet music | Low–moderate |
| **Clinics, labs, sterile rooms, kiosks** | Touching shared screens spreads contamination | Touch-free control, offline, no data leaves the device | High (B2B), per site |
| **Streamers & gamers** | More inputs, accessibility | Custom shortcuts, head pointer | Moderate |

## Model: generous free core + one-time Pro + B2B

| Tier | Price idea | Includes |
|------|-----------|----------|
| **Free** | $0 | All hand and head gestures, default profiles, EN/AR, light/dark, HUD, browser helper, Android & iOS basics |
| **Pro (one-time)** | $19–29 per user, all desktop platforms | Custom profiles & auto-switching, custom keyboard shortcuts, head pointer & air mouse, phone remote camera, priority updates |
| **Accessibility licence** | Free on request | Pro for anyone who needs it for disability access, verified lightly (honour system + NGO partners) |
| **Education** | Free for teachers & students; site licence for institutions | Pro + deployment guide |
| **Business / kiosk** | Per device per year | Pro + locked-down kiosk mode, MSI/PKG deployment, central config file, support SLA |

Why not a subscription for individuals: competitors charge monthly and reviews show fatigue; a one-time price
is a selling point, and the app has no server costs (everything runs on the device).
Why not ads or data: the privacy promise *is* the product.

## Distribution

- Direct download (GitHub Releases now; own site later) with Paddle/Lemon Squeezy for licence keys.
- Microsoft Store (MSIX), Mac App Store (needs sandbox work for Accessibility), Snap/Flathub.
- Google Play (Accessibility declaration + disclosure in place) and the App Store (viewer + remote).
- Partnerships: assistive-technology resellers, rehabilitation centres, Arabic-speaking universities (native Arabic UI is a unique advantage in MENA).
- Grants and awards for accessibility (e.g. Zero Project, regional digital-inclusion funds).

## Costs

Near-zero marginal cost: no servers, no cloud inference. Main costs are code-signing certificates
(Apple Developer $99/yr, Windows EV/OV certificate), store fees, and support time.

## Metrics (privacy-preserving)

No telemetry is collected. Measure through store downloads, licence activations (count only), opt-in surveys,
and support tickets.

## Roadmap levers for revenue

1. Kiosk mode (fullscreen app allow-list, gesture-only navigation) for B2B.
2. Custom gesture recording (few-shot, on device) — Pro.
3. Integrations: OBS scenes, Zoom/Teams native mute APIs, Spotify — Pro.
4. Smart-TV / Raspberry Pi build for touch-free signage.
