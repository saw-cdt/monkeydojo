# Real mode: actions without an effect yet

In `--real`, every Omarchy action is asked. The ones listed here only check the
shortcut: a right answer does not run the action yet. Effects live in
`src/monkeydojo/real.py`.

Tick an action once its effect is added and tested.

## How an effect is added

Find what Omarchy binds in `/usr/share/omarchy/default/hypr/bindings/*.lua`,
then pick the method that fits:

| Method | How it is undone | Examples already working |
|---|---|---|
| Dispatcher | a second dispatcher (`ACTIONS`) | workspaces, fullscreen, focus |
| Toggle twice | the same command again (`ACTIONS`) | split, scratchpad, Emojis |
| Menu | `omarchy-menu close` (`MENUS`) | Omarchy menu, System menu |
| App | close only the new window (`APPS`) | Terminal, Browser, File manager |

Before adding one, check that the action really goes back to how it was, and
that it does not touch anything outside the dojo (files, notifications, system
settings that persist).

## Never (cannot be undone safely)

These stay as shortcut-only on purpose.

| Action | Keys | Why |
|---|---|---|
| Close window | SUPER + W | would close the dojo terminal |
| Close all windows | CTRL ALT + DELETE | closes every window |
| Lock system | SUPER CTRL + L | locks the screen |
| Power | SUPER CTRL + P | power menu (shutdown, reboot) |
| Toggle locking on idle | SUPER CTRL + I | changes when the screen locks |
| Dismiss last notification | SUPER + COMMA | deletes a real notification |
| Dismiss all notifications | SUPER SHIFT + COMMA | deletes real notifications |
| Toggle laptop display | SUPER CTRL + Delete | can turn off the screen you are using |
| Toggle laptop display mirroring | SUPER CTRL ALT + Delete | rearranges monitors |

## Level 1: Essentials

- [ ] Screenshot · PRINT (waits for you to select an area; maybe open and cancel)
- [ ] Universal copy · SUPER + C (nothing visible; probably shortcut-only)
- [ ] Universal paste · SUPER + V (would paste into the dojo; probably shortcut-only)

## Level 2: Daily use

### Menus and panels (open, then close)
- [ ] Audio · SUPER CTRL + A
- [ ] Bluetooth · SUPER CTRL + B
- [ ] Network · SUPER CTRL + W
- [ ] Background switcher · SUPER CTRL + SPACE
- [ ] Capture menu · SUPER CTRL + C
- [ ] Calculator · SUPER CTRL + Q (app: close its window)

### Toggles (apply twice)
- [ ] Toggle nightlight · SUPER CTRL + N
- [ ] Toggle top bar · SUPER SHIFT + SPACE
- [ ] Toggle window transparency · SUPER + BACKSPACE
- [ ] Toggle window grouping · SUPER + G

### Windows (undo needs care)
- [ ] Swap window to the left · SUPER SHIFT + LEFT (swap back the other way; check the layout is restored)
- [ ] Swap window to the right · SUPER SHIFT + RIGHT
- [ ] Swap window up · SUPER SHIFT + UP
- [ ] Swap window down · SUPER SHIFT + DOWN
- [ ] Move window to scratchpad · SUPER ALT + S (move it back to its workspace)
- [ ] Pop window out (float & pin) · SUPER + O (unpin and tile again)

### Tricky
- [ ] Screenrecording · ALT + PRINT (starts a recording; probably shortcut-only)
- [ ] Color picker · SUPER + PRINT (waits for a click; probably shortcut-only)
- [ ] Universal cut · SUPER + X (nothing visible; probably shortcut-only)

## Level 3: Advanced

None have an effect yet. Grouped by the method that would fit.

### Apps and web apps (close the new window)
- [ ] Activity · SUPER CTRL + T
- [ ] Browser (private) · SUPER SHIFT ALT + B
- [ ] Calendar · SUPER CTRL ALT + D, SUPER SHIFT + C
- [ ] ChatGPT · SUPER SHIFT + A
- [ ] Docker · SUPER SHIFT + D
- [ ] Email · SUPER SHIFT + E
- [ ] File manager (cwd) · SUPER SHIFT ALT + F
- [ ] Google Maps · SUPER SHIFT + S
- [ ] Google Messages · SUPER SHIFT CTRL + G
- [ ] Google Photos · SUPER SHIFT + P
- [ ] Grok · SUPER SHIFT ALT + A
- [ ] Herdr · SUPER CTRL + RETURN
- [ ] Music · SUPER SHIFT + M
- [ ] Music TUI · SUPER SHIFT ALT + M
- [ ] New email · SUPER SHIFT ALT + E
- [ ] Obsidian · SUPER SHIFT + O
- [ ] Omawrite · SUPER SHIFT + W
- [ ] Passwords · SUPER SHIFT + SLASH
- [ ] Signal · SUPER SHIFT + G
- [ ] Tmux · SUPER ALT + RETURN
- [ ] WhatsApp · SUPER SHIFT ALT + G
- [ ] X · SUPER SHIFT + X
- [ ] X Post · SUPER SHIFT ALT + X
- [ ] YouTube · SUPER SHIFT + Y

### Menus and panels (open, then close)
- [ ] Bar panel <number> · SUPER CTRL + <number>
- [ ] Display · SUPER CTRL + D
- [ ] Hardware menu · SUPER CTRL + H
- [ ] Herdr keybindings · SUPER CTRL + K
- [ ] Open notification history · SUPER SHIFT ALT + COMMA
- [ ] Share · SUPER CTRL + S
- [ ] Show battery remaining · SUPER CTRL ALT + B
- [ ] Show reminders · SUPER CTRL ALT + R
- [ ] Show time · SUPER CTRL ALT + T
- [ ] Tmux keybindings · SUPER ALT + K
- [ ] Toggle menu · SUPER CTRL + O
- [ ] Toggle weather · SUPER CTRL ALT + W

### Window size (resize back)
- [ ] Expand window down · SUPER SHIFT + EQUAL
- [ ] Expand window down a little · SUPER SHIFT ALT + EQUAL
- [ ] Expand window down a lot · SUPER SHIFT CTRL + EQUAL
- [ ] Expand window left · SUPER + MINUS
- [ ] Expand window left a little · SUPER ALT + MINUS
- [ ] Expand window left a lot · SUPER CTRL + MINUS
- [ ] Pseudo window · SUPER + P
- [ ] Restore window width · SUPER + Home
- [ ] Save window width · SUPER ALT + Home
- [ ] Shrink window left · SUPER + EQUAL
- [ ] Shrink window left a little · SUPER ALT + EQUAL
- [ ] Shrink window left a lot · SUPER CTRL + EQUAL
- [ ] Shrink window up · SUPER SHIFT + MINUS
- [ ] Shrink window up a little · SUPER SHIFT ALT + MINUS
- [ ] Shrink window up a lot · SUPER SHIFT CTRL + MINUS
- [ ] Tiled full screen · SUPER CTRL + F
- [ ] Toggle single-window square aspect · SUPER CTRL + BACKSPACE

### Groups
- [ ] Move active window out of group · SUPER ALT + G
- [ ] Move grouped window focus left · SUPER CTRL + LEFT
- [ ] Move grouped window focus right · SUPER CTRL + RIGHT
- [ ] Move window to group on bottom · SUPER ALT + DOWN
- [ ] Move window to group on left · SUPER ALT + LEFT
- [ ] Move window to group on right · SUPER ALT + RIGHT
- [ ] Move window to group on top · SUPER ALT + UP
- [ ] Next window in group · SUPER ALT + TAB
- [ ] Previous window in group · SUPER SHIFT ALT + TAB
- [ ] Switch to group window <number> · SUPER ALT + <number>

### Focus, workspaces and monitors
- [ ] Focus on next monitor · CTRL ALT + TAB
- [ ] Focus on next window · ALT + TAB
- [ ] Focus on previous monitor · SHIFT CTRL ALT + TAB
- [ ] Focus on previous window · SHIFT ALT + TAB
- [ ] Move window silently to workspace <number> · SUPER SHIFT ALT + <number>
- [ ] Move workspace to down monitor · SUPER SHIFT ALT + DOWN
- [ ] Move workspace to left monitor · SUPER SHIFT ALT + LEFT
- [ ] Move workspace to right monitor · SUPER SHIFT ALT + RIGHT
- [ ] Move workspace to up monitor · SUPER SHIFT ALT + UP
- [ ] Reveal active window on top · ALT + TAB, SHIFT ALT + TAB

### Toggles (apply twice)
- [ ] Make webcam overlay larger · SUPER ALT + BRACKETRIGHT
- [ ] Make webcam overlay smaller · SUPER ALT + BRACKETLEFT
- [ ] Monitor scaling down · SUPER ALT + SLASH
- [ ] Monitor scaling up · SUPER + SLASH
- [ ] Reset zoom · SUPER CTRL ALT + Z
- [ ] Toggle silencing notifications · SUPER CTRL + COMMA
- [ ] Toggle window gaps · SUPER SHIFT + BACKSPACE
- [ ] Toggle workspace layout · SUPER + L
- [ ] Zoom in · SUPER CTRL + Z

### Probably shortcut-only
- [ ] Agent · SUPER SHIFT CTRL + A
- [ ] Clear reminders · SUPER SHIFT CTRL + R
- [ ] Copy URL from Web App · SHIFT ALT + L
- [ ] Download Video from Web App · SHIFT ALT + D
- [ ] Extract text (OCR) from screenshot · SUPER CTRL + PRINT
- [ ] Invoke last notification · SUPER ALT + COMMA
- [ ] Set reminder · SUPER CTRL + R
- [ ] Start dictation (push-to-talk) · F9
- [ ] Stop dictation (push-to-talk) · F9
- [ ] Toggle dictation · SUPER CTRL + X
- [ ] Transcode · SUPER CTRL + PERIOD
