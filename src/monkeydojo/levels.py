"""Which binding belongs to which level."""

LEVEL_NAMES = ("Essentials", "Daily use", "Advanced")

# Per source: one set of descriptions per level. Anything not listed is the last level.
LEVELS = {
    "omarchy": (
        {
            "Keybindings", "Omarchy menu", "System menu", "Terminal", "Browser",
            "File manager", "Close window", "Full screen", "Lock system",
            "Toggle window floating/tiling", "Toggle window split",
            "Switch to workspace <number>", "Move window to workspace <number>",
            "Focus on left window", "Focus on right window",
            "Focus on above window", "Focus on below window",
            "Universal copy", "Universal paste", "Screenshot",
        },
        {
            "Apps menu", "Theme menu", "Background switcher", "Clipboard manager",
            "Emojis", "Universal cut", "Screenrecording", "Color picker",
            "Capture menu", "Full width", "Pop window out (float & pin)",
            "Swap window to the left", "Swap window to the right",
            "Swap window up", "Swap window down",
            "Next workspace", "Previous workspace", "Former workspace",
            "Toggle scratchpad", "Move window to scratchpad", "Toggle window grouping",
            "Dismiss last notification", "Dismiss all notifications",
            "Toggle nightlight", "Toggle top bar", "Toggle window transparency",
            "Editor", "Calculator", "Audio", "Bluetooth", "Network", "Power",
        },
    ),
}

LAST_LEVEL = len(LEVEL_NAMES)


def level_of(binding):
    for i, descriptions in enumerate(LEVELS.get(binding.source, ()), start=1):
        if binding.description in descriptions:
            return i
    return LAST_LEVEL
