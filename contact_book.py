"""Data models for the console address book."""

import re
from collections import UserDict
from datetime import datetime, timedelta


class Field:
    """A base class for fields in a contact record."""

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """A required contact name."""

    def __init__(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Name must be a non-empty string.")
        super().__init__(value.strip())


class Phone(Field):
    """A phone number containing exactly 10 digits."""

    def __init__(self, value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{10}", value):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    """A birthday stored as a datetime value."""

    def __init__(self, value):
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", value
        ):
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        try:
            birthday = datetime.strptime(value, "%d.%m.%Y")
        except ValueError as error:
            raise ValueError("Invalid date format. Use DD.MM.YYYY") from error
        super().__init__(birthday)


class Record:
    """A contact record containing phones and an optional birthday."""

    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone) -> Phone:
        phone = Phone(phone)
        self.phones.append(phone)
        return phone

    def find_phone(self, phone) -> Phone | None:
        return next((item for item in self.phones if item.value == phone), None)

    def remove_phone(self, phone) -> None:
        found_phone = self.find_phone(phone)
        if found_phone is None:
            raise ValueError(f"Phone number {phone} not found.")
        self.phones.remove(found_phone)

    def edit_phone(self, old_phone, new_phone) -> Phone:
        found_phone = self.find_phone(old_phone)
        if found_phone is None:
            raise ValueError(f"Phone number {old_phone} not found.")
        replacement = Phone(new_phone)
        self.phones[self.phones.index(found_phone)] = replacement
        return replacement

    def add_birthday(self, birthday) -> Birthday:
        self.birthday = birthday if isinstance(birthday, Birthday) else Birthday(birthday)
        return self.birthday

    def __str__(self):
        phones = "; ".join(str(phone) for phone in self.phones) or "no phones"
        birthday = (
            f", birthday: {self.birthday.value.strftime('%d.%m.%Y')}"
            if self.birthday else ""
        )
        return f"Contact name: {self.name.value}, phones: {phones}{birthday}"


class AddressBook(UserDict):
    """A collection of contact records with case-insensitive name lookup."""

    def add_record(self, record) -> None:
        existing = self.find(record.name.value)
        if existing is not None:
            record.name = existing.name
            self.data[existing.name.value] = record
            return
        self.data[record.name.value] = record

    def find(self, name) -> Record | None:
        if not isinstance(name, str):
            return None
        normalized_name = name.strip().casefold()
        return next(
            (record for record in self.data.values()
             if record.name.value.casefold() == normalized_name),
            None,
        )

    def delete(self, name) -> None:
        record = self.find(name)
        if record is None:
            raise KeyError(name)
        del self.data[record.name.value]

    def get_upcoming_birthdays(self, today=None):
        today = today or datetime.today().date()
        upcoming = []
        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday_date = record.birthday.value.date()
            birthday_this_year = None
            for year in range(today.year, today.year + 5):
                try:
                    candidate = birthday_date.replace(year=year)
                except ValueError:
                    continue
                if candidate >= today:
                    birthday_this_year = candidate
                    break
            if birthday_this_year is None:
                continue

            days_until_birthday = (birthday_this_year - today).days
            if not 0 <= days_until_birthday <= 7:
                continue

            congratulation_date = birthday_this_year
            if congratulation_date.weekday() == 5:
                congratulation_date += timedelta(days=2)
            elif congratulation_date.weekday() == 6:
                congratulation_date += timedelta(days=1)

            upcoming.append({
                "name": record.name.value,
                "congratulation_date": congratulation_date.strftime("%d.%m.%Y"),
            })

        return sorted(
            upcoming,
            key=lambda item: datetime.strptime(
                item["congratulation_date"], "%d.%m.%Y"
            ),
        )
