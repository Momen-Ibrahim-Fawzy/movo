# Imaa user guide

[العربية](USER_GUIDE.ar.md)

## 1. Install

### Windows 10 / 11
1. Download **Imaa-Setup-x.y.z.exe** from the Releases page and run it (no administrator rights needed).
   Prefer no installer? Download **Imaa-Windows-x64-portable.zip**, right-click → *Extract All*, and open `Imaa.exe`.
2. If Windows shows *"Windows protected your PC"*, click **More info → Run anyway** (shown until the app is code-signed).

### macOS 12 or newer
1. Download the `.dmg` for your Mac (**arm64** for Apple Silicon, **x86_64** for Intel), open it and drag **Imaa** into **Applications**.
2. Open Imaa from Applications. If macOS says it can't verify the app, open **System Settings → Privacy & Security** and click **Open Anyway**.
3. Allow **Camera** when asked.
4. Imaa shows a yellow banner if it can't press keys yet: click **Open Settings** and switch Imaa on under **Accessibility**, then quit and reopen Imaa.
5. For screenshots, also allow **Screen Recording** when asked.

> Updating on a Mac: replace the app in Applications, then remove and re-add Imaa under Accessibility.

### Linux
- **AppImage**: `chmod +x Imaa-Linux-x86_64.AppImage && ./Imaa-Linux-x86_64.AppImage`
- **tar.gz**: extract and run `Imaa/Imaa`.
- Works best on an **X11** session. On Wayland, keyboard shortcuts need `ydotool`; volume and microphone use `pactl` (PulseAudio/PipeWire).

### Android 8+
1. Install **Imaa-Android.apk** (allow installs from your browser/files app if asked).
2. Open Imaa and tap the power button; allow the camera and notifications.
3. Tap **Turn on** under *Phone control*, read how Imaa uses Accessibility, then switch on **Imaa gesture control** in the Accessibility settings.

### iPhone / iPad
Build from `mobile/ios` with Xcode (`xcodegen && open Imaa.xcodeproj`). iOS does not allow apps to control
other apps, so on iOS Imaa controls its own **Viewer** (PDFs, photos) and can act as a **remote camera** for your computer.

## 2. First start

The welcome screen lets you pick **language** (English / العربية) and **theme** (light / dark / system), explains privacy,
and shows your first gestures. Press the big **power button** to start; press it again to stop.

- **Pause** without stopping: the *Pause* button, the 🤘 gesture (hold a little longer), the tray menu, or **Ctrl + Alt + G**.
- Closing the window keeps Imaa running in the tray (menu bar on macOS). Use **Quit Imaa** in the tray menu to exit.

## 3. Gestures

Hold each pose for a moment. Keep your hand 40–100 cm from the camera, palm towards it.

| Gesture | Default action |
|---------|----------------|
| 👍 Thumb up (hold) | Volume up — keeps going |
| 👎 Thumb down (hold) | Volume down — keeps going |
| 👉 / 👈 Point right / left | Next / previous (→ / ←) — slides, photos, videos |
| 🤏 Pinch (quick) | Play / pause |
| ☝️ Index up, then move up/down | Scroll — move further to scroll faster |
| 🤏 Pinch and hold, then move up/down | Zoom in / out |
| ✋ Swipe right / left | Next / previous tab |
| ✌️ Victory | Screenshot (saved to *Pictures/Imaa* and copied) |
| 🤙 Call sign | Microphone on / off |
| ✊ Fist | Skip ad |
| 🤘 Rock sign (hold ~1 s) | Pause / resume Imaa |

**Head gestures** (turn on in *Head gestures* or Home → Quick switches): nod = play/pause, shake = skip ad,
tilt right/left = next/previous, look up/down = scroll, turn right/left = next/previous tab.
In **Accurate** mode: open mouth = microphone, smile = screenshot, raise eyebrows = free to assign.
Press **Recalibrate head** while looking straight at the screen if head gestures feel off.

### Change what a gesture does
*Hand gestures* or *Head gestures* page → pick the profile to edit → choose an action in **Does**. Choose
**Custom shortcut…** to send any key combination (e.g. `ctrl+shift+m`). Switch a gesture off with its toggle.

### Practice mode
Home → *Practice mode*: Imaa highlights the gesture it sees and shows its name, but doesn't do anything.

## 4. Profiles

Profiles hold different bindings for different apps. Built-in: **General**, **Presentation** (PowerPoint, Keynote,
Impress, PDF readers), **Media** (VLC, Spotify, Music…), **Browser**, **Meeting** (Zoom, Teams, Webex, Slack, Discord).
With *Switch profiles automatically* on, Imaa uses a profile while one of its apps is in front.
Add your own on the *Profiles* page and list app process names (e.g. `chrome, firefox`).

## 5. Air mouse and head pointer

- **Air mouse**: your index knuckle moves the cursor; pinch = click, pinch and hold = drag, thumb + middle finger = right click.
- **Head pointer**: turn your head to move the cursor (further = faster); open mouth = click; raise eyebrows = right click.

## 6. Skipping ads

The ✊ gesture presses a visible **Skip** button. For the most reliable results install the **browser helper**:
1. Settings → Integrations → *How to install* (opens the helper folder).
2. In Chrome/Edge/Brave open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, choose the folder.
   In Firefox open `about:debugging` → *This Firefox* → **Load Temporary Add-on** → choose `manifest.json`.
3. The helper's icon shows a red **!** until Imaa is running.

On Windows, Imaa can also find Skip buttons through UI Automation without the helper. On Android it works through the Accessibility service.

## 7. Phone as a remote camera

1. Desktop: Settings → Integrations → turn on **Use my phone as a remote camera**. A QR code and a 6-digit pairing code appear.
2. Phone: scan the QR code with the camera app (or open Imaa → *Remote* and type the address and code), then turn on **Send gestures to the computer**.
3. Start Imaa on the phone. Gestures made in front of the phone now control the computer. Only gesture names travel over your Wi-Fi.

## 8. Settings worth knowing

| Setting | Tip |
|---------|-----|
| Power mode | *Eco* for old laptops or on battery; Imaa also rests at 5 fps when nobody is in view |
| Resolution | 640 × 480 is plenty; lower it on slow machines |
| Hold time | Slide left for faster reactions, right for fewer accidental triggers |
| Show camera | Turning the preview off saves CPU; gestures still work |
| Open when I sign in | Starts Imaa quietly in the tray |
| Export / Import | Move your settings to another computer |

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| "The camera could not be opened" | Close Zoom/Teams/Camera, pick another camera in Settings, then start again |
| Keys don't reach my app | Click the target window once; on macOS allow Accessibility and restart Imaa |
| Too many accidental actions | Increase hold time, switch off gestures you don't use, or pause with 🤘 |
| Gestures not recognised | Add light in front of you, keep the whole hand in view, avoid diagonal pointing |
| Head gestures drift | Press *Recalibrate head* while looking straight ahead |
| Microphone gesture does nothing on Linux | Install `pulseaudio-utils` (`pactl`) |
