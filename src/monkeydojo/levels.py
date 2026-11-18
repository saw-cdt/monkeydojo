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
    "lazyvim": (
        {
            "Find Files (Root Dir)", "Grep (Root Dir)", "Buffers",
            "Explorer NeoTree (Root Dir)", "Save File", "Quit All",
            "Delete Buffer", "Next Buffer", "Prev Buffer",
            "Go to Left Window", "Go to Right Window",
            "Go to Upper Window", "Go to Lower Window",
            "Split Window Right", "Split Window Below",
            "Goto Definition", "References", "Hover", "Code Action", "Rename",
            "Toggle comment line", "Terminal (Root Dir)", "Keymaps",
            "Lazygit (Root Dir)",
        },
        {
            "Recent", "Find Files (cwd)", "Switch to Other Buffer",
            "Delete Other Buffers", "Delete Window", "Toggle Zoom Mode",
            "Format", "Line Diagnostics", "Diagnostics (Trouble)",
            "Next Diagnostic", "Prev Diagnostic", "Next Error", "Prev Error",
            "Goto Implementation", "Goto Type Definition", "Signature Help",
            "LSP Symbols", "Rename File", "Search and Replace", "Help Pages",
            "Command History", "Undotree", "Flash", "Git Blame Line",
            "Git Status", "Notification History", "Escape and Clear hlsearch",
            "Toggle Line Numbers", "Toggle Wrap", "New File", "Lazy", "Mason",
        },
    ),
}

LAST_LEVEL = len(LEVEL_NAMES)


def level_of(binding):
    for i, descriptions in enumerate(LEVELS.get(binding.source, ()), start=1):
        if binding.description in descriptions:
            return i
    return LAST_LEVEL
