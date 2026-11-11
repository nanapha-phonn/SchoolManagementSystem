from dataclasses import dataclass


@dataclass
class Section:
    class_id: int
    name: str

    def validate(self):
        if isinstance(self.class_id, bool):
            raise ValueError(
                "Class ID must be a positive integer."
            )

        try:
            self.class_id = int(self.class_id)
        except (TypeError, ValueError):
            raise ValueError(
                "Class ID must be a positive integer."
            )

        if self.class_id <= 0:
            raise ValueError(
                "Class ID must be a positive integer."
            )

        if not isinstance(self.name, str):
            raise ValueError("Section name must be text.")

        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Section name is required.")

        if len(self.name) > 100:
            raise ValueError(
                "Section name cannot exceed 100 characters."
            )

        return self
