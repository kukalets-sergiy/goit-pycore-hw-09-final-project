"""Console assistant for managing contacts, birthdays, and notes."""

import pickle
import shlex
import os
import tempfile
import warnings
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

from contact_book import AddressBook, Record
from notes import Note, NoteBook


DATA_FILE = Path.home() / ".personal_assistant.pkl"


@dataclass
class PersonalAssistant:
    """Application data composed of contacts and notes."""

    contacts: AddressBook = field(default_factory=AddressBook)
    notes: NoteBook = field(default_factory=NoteBook)


def save_data(assistant, filename=DATA_FILE):
    """Save the complete assistant state to disk atomically."""
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=filename.parent, prefix=f".{filename.name}.", delete=False
        ) as file:
            temporary_name = file.name
            pickle.dump(assistant, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_name, filename)
        temporary_name = None
        directory_fd = os.open(filename.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def load_data(filename=DATA_FILE):
    """Load assistant data, including legacy AddressBook files."""
    try:
        with open(filename, "rb") as file:
            saved = pickle.load(file)
    except FileNotFoundError:
        return PersonalAssistant()
    except (
        AttributeError,
        EOFError,
        ImportError,
        OSError,
        pickle.UnpicklingError,
        ValueError,
    ) as error:
        warnings.warn(
            f"Could not load saved data from {filename}: {error}. "
            "Starting with empty data.",
            RuntimeWarning,
        )
        return PersonalAssistant()

    if isinstance(saved, PersonalAssistant):
        return saved
    if isinstance(saved, AddressBook):
        return PersonalAssistant(contacts=saved)
    warnings.warn(
        f"Saved data in {filename} has an unsupported format. "
        "Starting with empty data.",
        RuntimeWarning,
    )
    return PersonalAssistant()


def input_error(expected_args, usage):
    """Validate command arguments and turn expected errors into messages."""
    def decorator(func):
        @wraps(func)
        def inner(args, assistant):
            if len(args) != expected_args:
                return usage
            try:
                return func(args, assistant)
            except (KeyError, LookupError):
                return "Item not found."
            except ValueError as error:
                return str(error)
        return inner
    return decorator


def parse_input(user_input):
    """Parse a command line, supporting quoted arguments."""
    try:
        parts = shlex.split(user_input)
    except ValueError:
        return "", []
    return (parts[0].lower(), parts[1:]) if parts else ("", [])


@input_error(2, "Usage: add NAME PHONE")
def add_contact(args, assistant):
    name, phone = args
    record = assistant.contacts.find(name)
    if record is None:
        record = Record(name)
        assistant.contacts.add_record(record)
    record.add_phone(phone)
    return "Contact added."


@input_error(3, "Usage: change NAME OLD_PHONE NEW_PHONE")
def change_contact(args, assistant):
    name, old_phone, new_phone = args
    record = assistant.contacts.find(name)
    if record is None:
        return "Contact not found."
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."


@input_error(1, "Usage: phone NAME")
def show_phone(args, assistant):
    record = assistant.contacts.find(args[0])
    if record is None:
        return "Contact not found."
    return "; ".join(str(phone) for phone in record.phones) or "No phone numbers saved."


def show_all_contacts(assistant):
    return "\n".join(map(str, assistant.contacts.data.values())) or "No contacts saved."


@input_error(1, "Usage: delete NAME")
def delete_contact(args, assistant):
    assistant.contacts.delete(args[0])
    return "Contact deleted."


@input_error(2, "Usage: add-birthday NAME DD.MM.YYYY")
def add_birthday(args, assistant):
    record = assistant.contacts.find(args[0])
    if record is None:
        return "Contact not found."
    record.add_birthday(args[1])
    return "Birthday added."


@input_error(1, "Usage: show-birthday NAME")
def show_birthday(args, assistant):
    record = assistant.contacts.find(args[0])
    if record is None:
        return "Contact not found."
    return (
        record.birthday.value.strftime("%d.%m.%Y")
        if record.birthday else "Birthday not set."
    )


def show_birthdays(assistant):
    upcoming = assistant.contacts.get_upcoming_birthdays()
    return "\n".join(
        f"{item['name']}: {item['congratulation_date']}" for item in upcoming
    ) or "No birthdays in the next 7 days."


@input_error(2, 'Usage: add-note "TITLE" "TEXT"')
def add_note(args, assistant):
    assistant.notes.add(Note(*args))
    return "Note saved."


@input_error(2, 'Usage: edit-note "TITLE" "NEW TEXT"')
def edit_note(args, assistant):
    note = assistant.notes.find(args[0])
    if note is None:
        return "Note not found."
    note.text = Note._validate_text(args[1], "Note text")
    return "Note updated."


@input_error(1, 'Usage: delete-note "TITLE"')
def delete_note(args, assistant):
    assistant.notes.delete(args[0])
    return "Note deleted."


@input_error(1, 'Usage: search-notes "QUERY"')
def search_notes(args, assistant):
    return "\n".join(map(str, assistant.notes.search(args[0]))) or "No notes found."


@input_error(2, 'Usage: add-tag "TITLE" TAG')
def add_tag(args, assistant):
    note = assistant.notes.find(args[0])
    if note is None:
        return "Note not found."
    note.add_tag(args[1])
    return "Tag added."


@input_error(2, 'Usage: remove-tag "TITLE" TAG')
def remove_tag(args, assistant):
    note = assistant.notes.find(args[0])
    if note is None:
        return "Note not found."
    note.remove_tag(args[1])
    return "Tag removed."


@input_error(1, "Usage: search-tag TAG")
def search_tag(args, assistant):
    return "\n".join(map(str, assistant.notes.by_tag(args[0]))) or "No notes found."


def show_all_notes(assistant):
    return "\n".join(map(str, assistant.notes.data.values())) or "No notes saved."


def main():
    assistant = load_data()
    handlers = {
        "add": add_contact, "change": change_contact, "phone": show_phone,
        "delete": delete_contact,
        "all": lambda args, app: show_all_contacts(app),
        "add-birthday": add_birthday, "show-birthday": show_birthday,
        "birthdays": lambda args, app: show_birthdays(app),
        "add-note": add_note, "edit-note": edit_note, "delete-note": delete_note,
        "all-notes": lambda args, app: show_all_notes(app),
        "search-notes": search_notes, "add-tag": add_tag,
        "remove-tag": remove_tag, "search-tag": search_tag,
    }
    print("Welcome to the personal assistant!")
    try:
        while True:
            try:
                command, args = parse_input(input("Enter a command: "))
            except (EOFError, KeyboardInterrupt):
                print("\nGood bye!")
                break
            if command in ("close", "exit"):
                print("Good bye!")
                break
            if command == "hello":
                print("How can I help you?")
            elif command == "help":
                print("Commands: add, change, phone, all, add-birthday, "
                      "show-birthday, birthdays, add-note, edit-note, "
                      "delete-note, all-notes, search-notes, add-tag, "
                      "remove-tag, search-tag, close")
            elif command in handlers:
                print(handlers[command](args, assistant))
                save_data(assistant)
            else:
                print("Invalid command. Type 'help' to see available commands.")
    finally:
        save_data(assistant)


if __name__ == "__main__":
    main()
