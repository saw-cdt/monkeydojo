"""Catch Omarchy shortcuts with a temporary Hyprland submap.

A submap is defined once with every Omarchy shortcut in it. While a question is
open, Hyprland switches to that submap, where:

- each shortcut sends the event "monkeydojo key <n>" (its index), and its real
  action never runs
- Escape sends "monkeydojo quit"
- a modifier on its own sends "monkeydojo mod"
- a catchall sends "monkeydojo wrong" for every key press. It needs ignore_mods,
  or it only fires when no modifier is held, and it also fires when another
  bind matched. Events from the same instant are grouped and judged together.

Binds are never removed: Keybind:remove() also deletes the user's own binds with
the same keys. The submap just sits unused between questions and goes away with
the next config reload. Its name includes a hash of the shortcuts, so a changed
config gets a new submap instead of a mismatched one.

If the program dies inside the submap, a watchdog timer in Hyprland switches
back after WATCHDOG seconds.
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time

PREFIX = "monkeydojo"
WATCHDOG = 30
# Events closer than this come from the same key press
GROUP_WINDOW = 0.05
# Keys still held from the previous answer show up right after arming. Nobody can
# read a new question and react this fast, so events in this time are ignored.
GRACE = 0.3
MODIFIER_KEYS = ("Super_L", "Super_R", "Shift_L", "Shift_R",
                 "Control_L", "Control_R", "Alt_L", "Alt_R")

SETUP = """
local M = _G.monkeydojo or {defined = {}}
_G.monkeydojo = M

function M.disarm()
  M.deadline = nil
  if hl.get_current_submap():sub(1, #"%(prefix)s") == "%(prefix)s" then
    hl.dispatch(hl.dsp.submap("reset"))
  end
end

function M.arm(name)
  M.deadline = os.time() + %(watchdog)d
  hl.dispatch(hl.dsp.submap(name))
end

function M.define(name, combos)
  if M.defined[name] then return end
  hl.define_submap(name, function()
    local function event(text) return hl.dsp.event("%(prefix)s " .. text) end
    for i, keys in ipairs(combos) do hl.bind(keys, event("key " .. i)) end
    hl.bind("ESCAPE", event("quit"))
    -- Pressing a modifier on its own is the start of a shortcut, not a mistake
    for _, key in ipairs(%(modifiers)s) do hl.bind(key, event("mod"), {ignore_mods = true}) end
    hl.bind("catchall", event("wrong"), {ignore_mods = true})
  end)
  M.defined[name] = true
end

if not M.watchdog then
  M.watchdog = hl.timer(function()
    if M.deadline and os.time() > M.deadline then M.disarm() end
  end, {timeout = 1000, type = "repeat"})
end
"""


class HyprlandError(RuntimeError):
    pass


def available():
    return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")) and shutil.which("hyprctl")


def to_bind_keys(keys):
    """'SUPER SHIFT + RETURN' -> 'SUPER + SHIFT + RETURN'."""
    mods, _, key = keys.rpartition(" + ")
    return " + ".join(mods.split() + [key])


def lua(code):
    result = subprocess.run(["hyprctl", "repl", code], capture_output=True, text=True, timeout=5)
    output = result.stdout.strip()
    if result.returncode != 0 or output.startswith("error"):
        raise HyprlandError(output or result.stderr.strip() or "hyprctl failed")
    return output


def setup_code(name, combos):
    params = {"prefix": PREFIX, "watchdog": WATCHDOG, "modifiers": lua_list(MODIFIER_KEYS)}
    return SETUP % params + f"M.define({json.dumps(name)}, {lua_list(combos)})\nreturn 'ready'"


def submap_name(combos):
    digest = hashlib.sha1("\n".join(combos).encode()).hexdigest()[:8]
    return f"{PREFIX}-{digest}"


class Trap:
    """Context manager: listens to Hyprland events and always leaves the submap on exit.

    `combos` is every shortcut that will be asked, in hl.bind format.
    """

    def __init__(self, combos):
        self.combos = sorted(set(combos))
        self.index = {c: i for i, c in enumerate(self.combos, start=1)}
        self.name = submap_name(self.combos)

    def __enter__(self):
        runtime = os.environ["XDG_RUNTIME_DIR"]
        signature = os.environ["HYPRLAND_INSTANCE_SIGNATURE"]
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.connect(f"{runtime}/hypr/{signature}/.socket2.sock")
        self.buffer = b""
        lua(setup_code(self.name, self.combos))
        return self

    def __exit__(self, *exc):
        try:
            lua("_G.monkeydojo.disarm() return 'ok'")
        finally:
            self.sock.close()

    def ask(self, targets, timeout):
        """Wait for one answer to a question whose right shortcuts are `targets`.

        Return (verdict, combo, seconds): verdict is 'ok', 'wrong', 'quit' or
        'timeout', and combo is the shortcut that was pressed, if it is one we know.
        """
        wanted = {self.index[t] for t in targets}
        self._drain()
        lua(f"_G.monkeydojo.arm({json.dumps(self.name)}) return 'ok'")
        start = time.monotonic()
        try:
            self._collect(GRACE)
            while (left := timeout - (time.monotonic() - start)) > 0:
                first = self._next_event(left)
                if not first:
                    continue
                seconds = time.monotonic() - start
                verdict = judge([first] + self._collect(GROUP_WINDOW), wanted)
                if verdict:
                    kind, index = verdict
                    return kind, self.combos[index - 1] if index else None, seconds
            return "timeout", None, timeout
        finally:
            lua("_G.monkeydojo.disarm() return 'ok'")

    def _collect(self, window):
        events, end = [], time.monotonic() + window
        while (left := end - time.monotonic()) > 0:
            event = self._next_event(left)
            if event:
                events.append(event)
        return events

    def _next_event(self, timeout):
        self.sock.settimeout(timeout)
        while b"\n" not in self.buffer:
            try:
                data = self.sock.recv(4096)
            except socket.timeout:
                return None
            if not data:
                raise HyprlandError("Hyprland closed the event socket")
            self.buffer += data
        line, self.buffer = self.buffer.split(b"\n", 1)
        prefix = f"custom>>{PREFIX} "
        text = line.decode(errors="replace")
        return text[len(prefix):] if text.startswith(prefix) else None

    def _drain(self):
        self.sock.setblocking(False)
        try:
            while self.sock.recv(4096):
                pass
        except BlockingIOError:
            pass
        self.buffer = b""


def judge(events, wanted):
    """Decide what a group of events from one moment means.

    Return ('ok', index), ('quit', None), ('wrong', index or None) or None to keep
    waiting. A wrong index is the known shortcut that was pressed instead.
    Every press sends 'wrong' (catchall) plus its own event if it has one, so a
    lone modifier ('mod' + 'wrong') is not a mistake.
    """
    pressed = [int(e.split()[1]) for e in events if e.startswith("key ")]
    for index in pressed:
        if index in wanted:
            return "ok", index
    if "quit" in events:
        return "quit", None
    if pressed:
        return "wrong", pressed[0]
    if events.count("wrong") > events.count("mod"):
        return "wrong", None
    return None


def lua_list(strings):
    # JSON strings are valid Lua strings for plain ASCII text
    return "{" + ", ".join(json.dumps(s) for s in strings) + "}"
