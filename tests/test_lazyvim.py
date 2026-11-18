from monkeydojo.sources.lazyvim import format_keys, parse


def test_format_leader():
    assert format_keys(" ff") == "Space f f"
    assert format_keys("<leader>ff") == "Space f f"
    assert format_keys("  ") == "Space Space"


def test_format_modifiers():
    assert format_keys("<C-S>") == "Ctrl + S"
    assert format_keys("<c-k>") == "Ctrl + K"
    assert format_keys("<a-n>") == "Alt + n"
    assert format_keys("<C-W>d") == "Ctrl + W d"
    assert format_keys("<C-/>") == "Ctrl + /"


def test_format_special_keys():
    assert format_keys("<Esc>") == "Esc"
    assert format_keys("<leader><Tab>d") == "Space Tab d"
    assert format_keys("gd") == "g d"


def test_parse_groups_and_cleans():
    data = {
        "lazyvim": True,
        "maps": [
            {"lhs": " ff", "desc": "Find Files (Root Dir)"},
            {"lhs": "  ", "desc": "Find Files (Root Dir)"},
            {"lhs": "&", "desc": ":help &-default"},
            {"lhs": "grn", "desc": "vim.lsp.buf.rename()"},
            {"lhs": " sn", "desc": "+noice"},
            {"lhs": "<Plug>(foo)", "desc": "Foo"},
        ],
        "lsp": [
            {"lhs": "gy", "desc": "Goto T[y]pe Definition"},
        ],
    }
    result = {b.description: b for b in parse(data)}
    assert set(result) == {"Find Files (Root Dir)", "Goto Type Definition"}
    assert result["Find Files (Root Dir)"].keys == ("Space Space", "Space f f")
    assert result["Goto Type Definition"].source == "lazyvim"


def test_parse_without_lazyvim():
    assert parse({"lazyvim": False, "maps": [{"lhs": "x", "desc": "X"}]}) == []
