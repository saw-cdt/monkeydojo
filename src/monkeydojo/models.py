"""Data shared by every part of the app."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Binding:
    source: str          # "omarchy", "lazyvim", ...
    description: str     # "Close window"
    keys: tuple[str, ...]  # ("SUPER + W",)

    @property
    def id(self):
        """Unique across sources, used to store progress."""
        return f"{self.source}:{self.description}"


@dataclass(frozen=True)
class Question:
    binding: Binding
    kind: str            # "keys_to_action" or "action_to_keys"
    subject: str         # what the question shows (a key or a description)
    options: tuple[str, ...]
    correct_index: int
