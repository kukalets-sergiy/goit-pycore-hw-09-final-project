"""Tests for the personal assistant's main features and persistence."""

import tempfile
import unittest
import warnings
from datetime import date
from pathlib import Path

from contact_book import AddressBook, Record
from main import (
    PersonalAssistant,
    add_contact,
    add_note,
    add_tag,
    change_contact,
    delete_contact,
    delete_note,
    edit_note,
    load_data,
    parse_input,
    save_data,
    search_notes,
    search_tag,
)
from notes import Note, NoteBook


class PersonalAssistantTests(unittest.TestCase):
    def test_corrupted_file_loads_as_empty_assistant(self):
        """Test that loading a corrupted file results in an empty PersonalAssistant instance."""
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "assistant.pkl"
            filename.write_bytes(b"not a pickle")

            with warnings.catch_warnings(record=True) as caught:
                assistant = load_data(filename)

            self.assertIsInstance(assistant, PersonalAssistant)
            self.assertEqual(len(assistant.contacts), 0)
            self.assertTrue(caught)

    def test_extra_arguments_are_rejected(self):
        """Test that providing extra arguments to add_note is rejected."""
        assistant = PersonalAssistant()

        result = add_note(["title", "text", "unexpected"], assistant)

        self.assertEqual(result, 'Usage: add-note "TITLE" "TEXT"')
        self.assertEqual(len(assistant.notes), 0)

    def test_saved_data_can_be_loaded_after_atomic_write(self):
        """Test that data saved to disk can be loaded correctly."""
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "assistant.pkl"
            assistant = PersonalAssistant()
            self.assertEqual(add_note(["title", "text"], assistant), "Note saved.")

            save_data(assistant, filename)
            loaded = load_data(filename)

            self.assertEqual(loaded.notes.find("TITLE").text, "text")

    def test_contact_can_be_added_changed_and_deleted(self):
        """Test that a contact can be added, changed, and deleted."""
        assistant = PersonalAssistant()

        self.assertEqual(
            add_contact(["Alice", "1234567890"], assistant),
            "Contact added.",
        )
        self.assertEqual(
            change_contact(["alice", "1234567890", "0987654321"], assistant),
            "Contact updated.",
        )
        self.assertEqual(
            assistant.contacts.find("ALICE").phones[0].value,
            "0987654321",
        )
        self.assertEqual(delete_contact(["Alice"], assistant), "Contact deleted.")
        self.assertIsNone(assistant.contacts.find("Alice"))

    def test_contact_fields_reject_invalid_values(self):
        """Test that invalid values for contact fields raise ValueError."""
        with self.assertRaises(ValueError):
            Record("")
        with self.assertRaises(ValueError):
            Record("Alice").add_phone("123")
        with self.assertRaises(ValueError):
            Record("Alice").add_birthday("31.02.2000")

    def test_upcoming_birthdays_include_weekend_adjustment(self):
        """Test that upcoming birthdays are correctly calculated, including weekend adjustments."""
        book = AddressBook()
        record = Record("Alice")
        record.add_birthday("31.10.1990")
        book.add_record(record)

        upcoming = book.get_upcoming_birthdays(today=date(2026, 10, 25))

        self.assertEqual(
            upcoming,
            [{"name": "Alice", "congratulation_date": "02.11.2026"}],
        )

    def test_notes_can_be_searched_and_filtered_by_tag(self):
        """Test that notes can be searched by text and filtered by tag."""
        assistant = PersonalAssistant()
        self.assertEqual(
            add_note(["Shopping", "Milk and bread"], assistant),
            "Note saved.",
        )
        self.assertEqual(add_tag(["Shopping", "Important"], assistant), "Tag added.")

        self.assertIn("Shopping: Milk and bread", search_notes(["bread"], assistant))
        self.assertIn("Shopping: Milk and bread", search_tag(["important"], assistant))

    def test_note_can_be_edited_and_deleted(self):
        """Test that a note can be edited and deleted."""
        assistant = PersonalAssistant()
        add_note(["Task", "Old text"], assistant)

        self.assertEqual(
            edit_note(["Task", "New text"], assistant),
            "Note updated.",
        )
        self.assertEqual(assistant.notes.find("task").text, "New text")
        self.assertEqual(delete_note(["missing"], assistant), "Item not found.")

    def test_parser_supports_quoted_arguments_and_invalid_quotes(self):
        """Test that the parser correctly handles quoted arguments and invalid quotes."""
        self.assertEqual(
            parse_input('add-note "Shopping list" "Milk and bread"'),
            ("add-note", ["Shopping list", "Milk and bread"]),
        )
        self.assertEqual(parse_input('add-note "unfinished'), ("", []))

    def test_note_models_validate_and_search_case_insensitively(self):
        """Test that note models validate input and search is case-insensitive."""
        notebook = NoteBook()
        notebook.add(Note("Ideas", "Build an app", ["Python"]))

        self.assertIsNotNone(notebook.find("ideas"))
        self.assertEqual(len(notebook.search("BUILD")), 1)
        self.assertEqual(len(notebook.by_tag("python")), 1)


if __name__ == "__main__":
    unittest.main()
