# School Management System

A single-school desktop management application built with **Python 3.10+, Tkinter/ttk, and SQLite**.

The application provides tools for managing students, staff, academic records, transportation, finance, documents, and database backups.

The database schema includes a `schools` table to support a possible future multi-school architecture through controlled migrations. The current application is designed for a single school.

## Features

### Administration
- Initial administrator account setup.
- User account management.
- Role-based access permissions.
- Dashboard and application settings.

### Student and Staff Management
- Student records and profiles.
- Teacher and employee records.
- Transport staff records.
- Student enrollment management.

### Academic Management
- Academic year management.
- Classes and sections.
- Subjects and teacher-subject assignments.
- Grading schemes and grade bands.
- Assessment periods.
- Student results and report cards.
- PDF report generation.

### Transportation
- Vehicle management.
- Transport route and stop management.
- Driver and attendant records.
- Student transport assignments.

### Finance
- Student fee charges and payments.
- Payment receipts.
- Transaction reports.
- Salary records and salary slips.

### Documents
- Attach documents to student, teacher, and transport staff records.
- Supported formats: PDF, JPG, JPEG, and PNG.
- Maximum upload size: 10 MiB.
- Document metadata stored in SQLite; document files stored separately.
- Archive documents without permanently deleting them.

### Backup and Restore
- Create application backups.
- Include the SQLite database and stored documents.
- Validate backup contents before restoration.
- Restore through the application settings.

## Requirements

- Python 3.10 or newer.
- Tkinter/ttk.
- SQLite (included with Python).
- Packages listed in `requirements.txt`.

The application has been developed and tested on Ubuntu with Python 3.10.12. Windows installation instructions are provided below, but Windows compatibility still requires independent verification.

## Installation

### Ubuntu

Install the system dependencies:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk
```

Clone or download the project, then enter its directory:

```bash
cd SchoolManagementSystem
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Launch the application:

```bash
python main.py
```

### Windows — PowerShell

Install Python 3.10 or newer and ensure the Python installation includes Tcl/Tk support.

Open PowerShell in the project directory:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell prevents virtual environment activation, consult the Python and PowerShell documentation for the appropriate execution policy for your environment.

## First Launch

On first launch, the application provides an initial administrator setup process when no user account exists.

There is no default `admin/admin` account. Create the initial administrator through the setup interface.

## Application Data

Application data is stored locally:

| Path | Purpose |
|---|---|
| `data/school_management.db` | SQLite database |
| `data/documents/` | Uploaded documents |
| `backups/` | Local backup files |
| `.venv/` | Python virtual environment |

The database and uploaded documents may contain confidential student, employee, and financial information.

**Do not commit application databases, uploaded documents, receipts, backups, or other private records to a public repository.**

The repository's `.gitignore` excludes the main local data and generated files.

## Running Tests

Activate the virtual environment, then run:

```bash
python -m unittest discover -s tests -v
```

The current development test suite has passed **922 tests** in the Ubuntu development environment.

This result does not replace fresh-install testing or verification on other operating systems.

## Project Status

The application has implemented its core management modules, document management, and backup/restore functionality.

### Verification

- 922 automated tests passed.
- Clean dependency installation verified.
- Fresh database initialization verified.
- First-launch administrator setup verified.
- Administrator creation, login, and dashboard startup verified.
- Fresh-install testing completed on Ubuntu with Python 3.10.12.

### Remaining Release Work

- Windows compatibility testing.
- Final repository and staged-file review.
- GitHub publication.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
