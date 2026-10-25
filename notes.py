"""Data models for the console notes manager."""

from collections import UserDict


class Note:
    """A note with a title, text and optional tags."""

    def __init__(self, title: str, text: str, tags=None):
        self.title = self._validate_text(title, "Title")
        self.text = self._validate_text(text, "Note text")
        self.tags = {self._validate_text(tag, "Tag").casefold() for tag in (tags or [])}

    @staticmethod
    def _validate_text(value, field_name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")
        return value.strip()

    def add_tag(self, tag):
        self.tags.add(self._validate_text(tag, "Tag").casefold())

    def remove_tag(self, tag):
        normalized = self._validate_text(tag, "Tag").casefold()
        if normalized not in self.tags:
            raise ValueError(f"Tag '{tag}' not found.")
        self.tags.remove(normalized)

    def __str__(self):
        tags = f" [{', '.join(sorted(self.tags))}]" if self.tags else ""
        return f"{self.title}: {self.text}{tags}"


class NoteBook(UserDict):
    """A collection of notes with case-insensitive title lookup."""

    def add(self, note: Note):
        existing = self.find(note.title)
        if existing is not None:
            del self.data[existing.title]
        self.data[note.title] = note

    def find(self, title: str):
        if not isinstance(title, str):
            return None
        normalized = title.strip().casefold()
        return next(
            (note for note in self.data.values()
             if note.title.casefold() == normalized),
            None,
        )

    def delete(self, title: str):
        note = self.find(title)
        if note is None:
            raise KeyError(title)
        del self.data[note.title]

    def search(self, query: str):
        query = Note._validate_text(query, "Search query").casefold()
        return [
            note for note in self.data.values()
            if query in note.title.casefold()
            or query in note.text.casefold()
            or any(query in tag for tag in note.tags)
        ]

    def by_tag(self, tag: str):
        tag = Note._validate_text(tag, "Tag").casefold()
        return [note for note in self.data.values() if tag in note.tags]
