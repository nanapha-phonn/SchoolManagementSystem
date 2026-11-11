from dataclasses import dataclass


VALID_SUBJECT_STATUSES = {
    "active",
    "inactive",
}


@dataclass
class Subject:
    subject_code: str
    name: str
    description: str = ""
    status: str = "active"

    def validate(self):
        if not isinstance(self.subject_code, str):
            raise ValueError("Subject code must be text.")

        if not isinstance(self.name, str):
            raise ValueError("Subject name must be text.")

        self.subject_code = self.subject_code.strip().upper()
        self.name = self.name.strip()

        if not self.subject_code:
            raise ValueError("Subject code is required.")

        if len(self.subject_code) > 30:
            raise ValueError(
                "Subject code cannot exceed 30 characters."
            )

        if not self.name:
            raise ValueError("Subject name is required.")

        if len(self.name) > 150:
            raise ValueError(
                "Subject name cannot exceed 150 characters."
            )

        if not isinstance(self.description, str):
            raise ValueError("Subject description must be text.")

        self.description = self.description.strip()

        if len(self.description) > 500:
            raise ValueError(
                "Subject description cannot exceed 500 characters."
            )

        if not isinstance(self.status, str):
            raise ValueError("Invalid subject status.")

        self.status = self.status.strip().lower()

        if self.status not in VALID_SUBJECT_STATUSES:
            raise ValueError("Invalid subject status.")

        return self
