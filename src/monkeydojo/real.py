"""Real mode: after a right answer, run the real action for a moment, then undo it.

The dispatchers are the same ones Omarchy binds (see
/usr/share/omarchy/default/hypr/bindings/tiling.lua). Wrong answers are still
caught by the submap, so they never run anything.

Each action is (do, undo) as Lua dispatcher expressions. "{n}" is the workspace
number of the question, and S holds the window and workspace from before the action.

Apps are launched with Omarchy's own launcher; the window they open is found
by comparing the window list before and after, and only that window is closed.

Actions that cannot be undone safely (locking, closing windows, copy/paste) are
not here: real mode still asks them, but only checks the shortcut.
"""

import time

from monkeydojo.hyprland import lua

PAUSE = 0.8       # seconds the effect stays on screen
MENU_PAUSE = 1.5  # menus take a moment to open
APP_PAUSE = 1.5   # how long an app stays open once its window shows up
APP_TIMEOUT = 8   # give up waiting for an app window after this

TOGGLE_FULLSCREEN = 'hl.dsp.window.fullscreen({mode = "fullscreen"})'
TOGGLE_MAXIMIZED = 'hl.dsp.window.fullscreen({mode = "maximized"})'
TOGGLE_FLOAT = 'hl.dsp.window.float({action = "toggle"})'
TOGGLE_SCRATCHPAD = 'hl.dsp.workspace.toggle_special("scratchpad")'
BACK_TO_WORKSPACE = "hl.dsp.focus({workspace = tostring(S.ws)})"
BACK_TO_WINDOW = 'hl.dsp.focus({window = "address:" .. S.addr})'
CLOSE_MENU = 'hl.dsp.exec_cmd("omarchy-menu close")'


def run(command):
    return f'hl.dsp.exec_cmd("{command}")'


def shell_toggle(panel):
    return (run(f"omarchy-shell shell toggle {panel}"),) * 2


ACTIONS = {
    "Switch to workspace <number>": ('hl.dsp.focus({workspace = "{n}"})', BACK_TO_WORKSPACE),
    "Move window to workspace <number>": (
        'hl.dsp.window.move({workspace = "{n}"})',
        "hl.dsp.window.move({workspace = tostring(S.ws)})",
    ),
    "Full screen": (TOGGLE_FULLSCREEN, TOGGLE_FULLSCREEN),
    "Full width": (TOGGLE_MAXIMIZED, TOGGLE_MAXIMIZED),
    "Toggle window floating/tiling": (TOGGLE_FLOAT, TOGGLE_FLOAT),
    "Focus on left window": ('hl.dsp.focus({direction = "l"})', BACK_TO_WINDOW),
    "Focus on right window": ('hl.dsp.focus({direction = "r"})', BACK_TO_WINDOW),
    "Focus on above window": ('hl.dsp.focus({direction = "u"})', BACK_TO_WINDOW),
    "Focus on below window": ('hl.dsp.focus({direction = "d"})', BACK_TO_WINDOW),
    "Next workspace": ('hl.dsp.focus({workspace = "e+1"})', BACK_TO_WORKSPACE),
    "Previous workspace": ('hl.dsp.focus({workspace = "e-1"})', BACK_TO_WORKSPACE),
    "Former workspace": ('hl.dsp.focus({workspace = "previous"})', BACK_TO_WORKSPACE),
    "Toggle scratchpad": (TOGGLE_SCRATCHPAD, TOGGLE_SCRATCHPAD),
    "Toggle window split": ('hl.dsp.layout("togglesplit")',) * 2,
}

MENUS = {
    "Omarchy menu": (run("omarchy-menu toggle"), CLOSE_MENU),
    "Apps menu": (run("omarchy-menu toggle apps"), CLOSE_MENU),
    "System menu": (run("omarchy-menu toggle system"), CLOSE_MENU),
    "Theme menu": (run("omarchy-menu toggle theme"), CLOSE_MENU),
    "Keybindings": (run("omarchy-menu-keybindings"), CLOSE_MENU),
    "Emojis": shell_toggle("omarchy.emojis"),
    "Clipboard manager": shell_toggle("omarchy.clipboard"),
}
ACTIONS.update(MENUS)

# Same commands Omarchy binds ({ omarchy = "x" } runs omarchy-launch-x)
APPS = {
    "Terminal": "omarchy-launch-terminal",
    "Browser": "omarchy-launch-browser",
    "File manager": "omarchy-launch-nautilus",
    "Editor": "omarchy-launch-editor",
}


def has_effect(binding):
    return binding.source == "omarchy" and (binding.description in ACTIONS or binding.description in APPS)


def current_workspace():
    return int(lua("return hl.get_active_workspace().id"))


def show(binding, n=None):
    """Run the action, leave it on screen for a moment, then undo it."""
    if not has_effect(binding):
        return
    if binding.description in APPS:
        show_app(APPS[binding.description])
        return
    do, undo = ACTIONS[binding.description]
    do = do.replace("{n}", str(n))
    lua(
        "local w = hl.get_active_window()\n"
        "_G.monkeydojo.S = {addr = w and w.address, ws = hl.get_active_workspace().id}\n"
        f"hl.dispatch({do})\nreturn 'ok'"
    )
    try:
        time.sleep(MENU_PAUSE if binding.description in MENUS else PAUSE)
    finally:
        # Without a focused window there is nothing to focus back to
        guard = "S.addr" if "S.addr" in undo else "true"
        lua(f"local S = _G.monkeydojo.S\nif {guard} then hl.dispatch({undo}) end\nreturn 'ok'")


def windows():
    # "x" keeps the reply from being empty, which hyprctl reports as an error
    reply = lua('local t = {"x"} for _, w in ipairs(hl.get_windows()) do t[#t+1] = w.address end'
                ' return table.concat(t, " ")')
    return set(reply.split()[1:])


def show_app(command):
    """Launch an app, wait for its new window, leave it open a moment, then close only that window."""
    before = windows()
    lua("local w = hl.get_active_window()\n"
        "_G.monkeydojo.S = {addr = w and w.address}\n"
        f'hl.exec_cmd("{command}")\nreturn "ok"')
    new, start = None, time.monotonic()
    try:
        while not new and time.monotonic() - start < APP_TIMEOUT:
            time.sleep(0.1)
            new = next(iter(windows() - before), None)
        if new:
            time.sleep(APP_PAUSE)
    finally:
        if new:
            lua(f'hl.dispatch(hl.dsp.window.close({{window = "address:{new}"}}))\nreturn "ok"')
            time.sleep(0.2)  # let Hyprland pick a new focus before we set ours
        lua('local S = _G.monkeydojo.S\n'
            f'if S.addr then hl.dispatch({BACK_TO_WINDOW}) end\nreturn "ok"')
