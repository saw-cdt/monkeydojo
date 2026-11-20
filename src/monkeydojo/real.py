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

import json
import os
import shutil
import sys
import time
from pathlib import Path

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


def show(binding, n=None, sandbox=None):
    """Run the action, leave it on screen for a moment, then undo it.

    With a sandbox, the grid of windows is checked afterwards and rebuilt if broken.
    """
    if not has_effect(binding):
        return
    try:
        if binding.description in APPS:
            show_app(APPS[binding.description])
        elif sandbox and sandbox.workspace and binding.description == "Move window to workspace <number>":
            # Coming back into dwindle splits whatever has focus, so put the dojo back in its corner
            lua(f'hl.dispatch(hl.dsp.window.move({{workspace = "{n}"}}))\nreturn "ok"')
            try:
                time.sleep(PAUSE)
            finally:
                sandbox.return_dojo()
        else:
            dispatch_and_undo(binding, n)
    finally:
        if sandbox:
            sandbox.repair()


def dispatch_and_undo(binding, n):
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


def active_window():
    reply = lua('local w = hl.get_active_window() return "x " .. (w and w.address or "")')
    return reply[2:] or None


def launch(command, timeout=APP_TIMEOUT):
    """Run a command and return the address of the window it opens (None if none shows up)."""
    before = windows()
    lua(f"hl.exec_cmd({json.dumps(command)})\nreturn 'ok'")
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        time.sleep(0.1)
        new = windows() - before
        if new:
            return new.pop()
    return None


def close_window(address):
    lua(f'hl.dispatch(hl.dsp.window.close({{window = "address:{address}"}}))\nreturn "ok"')


def focus_window(address):
    lua(f'hl.dispatch(hl.dsp.focus({{window = "address:{address}"}}))\nreturn "ok"')


# Apps open floating and centered, like the menus, so they do not reflow the windows
APP_SIZE = (0.6, 0.7)  # fraction of the monitor


def float_new_windows(enabled):
    """Turn on or off a rule that floats new windows on the current workspace.

    One rule per workspace is created the first time and then only enabled or
    disabled, so nothing piles up. It goes away with the next config reload.
    """
    width, height = APP_SIZE
    lua(
        "local M = _G.monkeydojo\n"
        "M.float_rules = M.float_rules or {}\n"
        "local ws = tostring(hl.get_active_workspace().id)\n"
        "local rule = M.float_rules[ws]\n"
        "if not rule then\n"
        "  local m = hl.get_active_monitor()\n"
        f"  local size = {{math.floor(m.width / m.scale * {width}), math.floor(m.height / m.scale * {height})}}\n"
        '  rule = hl.window_rule({name = "monkeydojo-float-" .. ws, match = {workspace = ws},'
        " float = true, center = true, size = size, enabled = false})\n"
        "  M.float_rules[ws] = rule\n"
        "end\n"
        f"rule:set_enabled({'true' if enabled else 'false'})\n"
        "return 'ok'"
    )


def show_app(command):
    """Launch an app floating, leave it open a moment, then close only its window."""
    previous = active_window()
    new = None
    try:
        float_new_windows(True)
        try:
            new = launch(command)
        finally:
            float_new_windows(False)
        if new:
            time.sleep(APP_PAUSE)
    finally:
        if new:
            close_window(new)
            time.sleep(0.2)  # let Hyprland pick a new focus before we set ours
        if previous:
            focus_window(previous)


LAYOUTS_DIR = Path.home() / ".local/state/omarchy/workspace-layouts"
FILLER_SCRIPT = Path(__file__).with_name("sandbox_window.py")
# A 2x2 grid with the dojo top left. Each filler is opened next to a window
# that is already there: (letter, window to split, side of it to open on).
#   dojo | A
#   B    | C
FILLERS = (("A", "dojo", "r"), ("B", "dojo", "d"), ("C", "A", "d"))


def free_workspace():
    """Highest workspace (10..1) with no windows and no saved Omarchy layout, so it is plain dwindle."""
    used = lua('local t = {"x"} for _, w in ipairs(hl.get_windows()) do'
               ' t[#t+1] = tostring(w.workspace and w.workspace.id) end return table.concat(t, " ")')
    occupied = set(used.split()[1:])
    for n in range(10, 0, -1):
        if str(n) not in occupied and not (LAYOUTS_DIR / f"{n}.lua").exists():
            return n
    return None


def filler_command(letter):
    script = f"{sys.executable} -I {FILLER_SCRIPT} {letter} {os.getpid()}"
    if shutil.which("ghostty"):
        return f"ghostty --font-size=96 --title=monkeydojo-{letter} -e {script}"
    return f"xdg-terminal-exec {script}"


class Sandbox:
    """Move the dojo terminal to an empty workspace with a few filler windows around it.

    On exit only the windows it opened are closed and the dojo goes back home.
    Filler windows also close by themselves if the dojo process dies.
    """

    def __enter__(self):
        self.fillers = []
        self.placed = {}
        self.dojo = active_window()
        self.home = current_workspace()
        self.workspace = free_workspace()
        if not self.dojo or not self.workspace:
            self.workspace = None
            return self
        try:
            lua(f'hl.dispatch(hl.dsp.window.move({{workspace = "{self.workspace}"}}))\nreturn "ok"')
            self._open_fillers()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def return_dojo(self):
        """Put the dojo back top left: its spot was taken by B, so split B upwards."""
        b = self.placed.get("B")
        if b and b in windows():
            focus_window(b)
            lua(f'hl.dispatch(hl.dsp.layout("preselect u"))\nreturn "ok"')
        lua(f'hl.dispatch(hl.dsp.window.move({{workspace = "{self.workspace}",'
            f' window = "address:{self.dojo}", follow = false}}))\nreturn "ok"')
        focus_window(self.dojo)

    def grid_ok(self):
        """True if dojo, A, B and C are tiled in their corners on the sandbox workspace."""
        names = ["dojo", "A", "B", "C"]
        if any(name not in self.placed for name in names):
            return True  # a filler failed to open: nothing to compare against
        rows = {}
        for name in names:
            reply = lua(f'local w = hl.get_window("address:{self.placed[name]}")\n'
                        'if not w then return "x missing" end\n'
                        'return "x " .. w.workspace.id .. " " .. tostring(w.floating) .. " "'
                        ' .. tostring(w.fullscreen) .. " " .. w.at.x .. " " .. w.at.y')
            parts = reply.split()[1:]
            if parts[0] == "missing" or parts[0] != str(self.workspace) or parts[1] != "false":
                return False
            if parts[2] not in ("0", "false"):
                return False
            rows[name] = (float(parts[3]), float(parts[4]))
        (dx, dy), (ax, ay), (bx, by), (cx, cy) = (rows[n] for n in names)
        return ax > dx and ay == dy and bx == dx and by > dy and cx > dx and cy > dy

    def repair(self):
        """Rebuild the grid if an action left it broken."""
        if not self.workspace or self.grid_ok():
            return
        for address in self.fillers:
            close_window(address)
        time.sleep(0.3)
        if self.dojo in windows():
            lua(f'hl.dispatch(hl.dsp.window.move({{workspace = "{self.workspace}",'
                f' window = "address:{self.dojo}", follow = false}}))\nreturn "ok"')
            focus_window(self.dojo)
        self._open_fillers()

    def _open_fillers(self):
        self.placed = {"dojo": self.dojo}
        self.fillers = []
        for letter, beside, side in FILLERS:
            if beside not in self.placed:
                continue
            # Dwindle splits the focused window; preselect picks the side of the split
            focus_window(self.placed[beside])
            lua(f'hl.dispatch(hl.dsp.layout("preselect {side}"))\nreturn "ok"')
            address = launch(filler_command(letter))
            if address:
                self.placed[letter] = address
                self.fillers.append(address)
        focus_window(self.dojo)

    def __exit__(self, *exc):
        if not self.workspace:
            return
        for address in self.fillers:
            close_window(address)
        if self.dojo and self.dojo in windows():
            focus_window(self.dojo)
            lua(f'hl.dispatch(hl.dsp.window.move({{workspace = "{self.home}"}}))\nreturn "ok"')
