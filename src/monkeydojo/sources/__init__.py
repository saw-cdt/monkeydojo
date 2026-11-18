"""Where bindings come from. Each source is a module with a load() function."""

from monkeydojo.sources import omarchy


class SourceError(Exception):
    pass


SOURCES = {
    "omarchy": omarchy.load,
}


def load_all():
    bindings = []
    for name, load in SOURCES.items():
        try:
            bindings.extend(load())
        except (FileNotFoundError, OSError, RuntimeError) as error:
            raise SourceError(f"Could not read {name} keybindings: {error}") from error
    return bindings
