from dataclasses import dataclass


@dataclass
class SchoolClass:
    name: str
    description: str = ""

    def validate(self):
        if not isinstance(self.name, str):
            raise ValueError("Class name must be text.")

        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Class name is required.")

        if len(self.name) > 100:
            raise ValueError(
                "Class name cannot exceed 100 characters."
            )

        self.description = str(self.description or "").strip()

        if len(self.description) > 500:
            raise ValueError(
                "Class description cannot exceed 500 characters."
            )

        return self
