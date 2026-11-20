from monkeydojo.ui import ninja, theme


def test_sprite_rows_have_the_same_width_and_every_face_works():
    assert {len(r) for r in ninja.SPRITE} == {ninja.WIDTH}
    for face in ninja.FACES:
        cells = ninja.cells(face)
        assert len(cells) == ninja.HEIGHT
        assert all(len(row) == ninja.WIDTH for row in cells)


def test_faces_only_draw_on_the_face():
    for face, pixels in ninja.FACES.items():
        for y, x in pixels:
            assert ninja.SPRITE[y][x] == "S", (face, y, x)


def test_parse_colors_toml():
    values = theme.parse('mode = "light"\n# comment\nbrown = "#67402b"\norange="#cf8057"\n')
    assert values == {"mode": "light", "brown": "#67402b", "orange": "#cf8057"}


def test_hex_to_256():
    assert theme.to_256("#000000") == 16
    assert theme.to_256("#ffffff") == 231
    assert theme.to_256("#875f5f") == 95
    assert theme.to_256("#7b5b55") == 95  # Catppuccin brown


def test_load_falls_back_without_a_theme(tmp_path):
    t = theme.load(tmp_path / "missing.toml")
    assert not t.light and t.brown == theme.to_256(theme.DEFAULTS["brown"])
    (tmp_path / "c.toml").write_text('mode = "light"\nbrown = "nope"\n')
    t = theme.load(tmp_path / "c.toml")
    assert t.light and t.brown == theme.to_256(theme.DEFAULTS["brown"])
