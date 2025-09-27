# ABA File Editor (Flask)

_Edit Australian Bankers Association (ABA/Cemtex) batch payment files safely and quickly._

**Primary use case:** If you miss your bank’s midnight cutoff, upload the exported ABA file, update the **processing date** (Type 0 header), optionally remove transactions, and download a corrected, import-ready ABA file. The app recalculates trailer **totals** and **record count** automatically.

> ⚠️ Always validate your edited file in your bank’s portal/sandbox before using it in production.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Run Locally](#run-locally)
- [Usage](#usage)
- [Endpoints](#endpoints)
- [ABA Format Crash Course](#aba-format-crash-course)
- [Field Reference](#field-reference)
- [Validation Notes & Gotchas](#validation-notes--gotchas)
- [Extending](#extending)
- [Security & Privacy](#security--privacy)
- [Project Structure](#project-structure)
- [FAQ](#faq)
- [License](#license)

---

## Features

- ✅ Upload an ABA file and view parsed records  
- ✏️ Edit **Type 0 (Descriptive)** fields, including **processing date (DDMMYY)**  
- 🗂️ Edit or **remove** individual **Type 1 (Detail)** records (uncheck to remove)  
- 🔢 Auto-recalculate **Type 7 (File Total)**:
  - `credit_total`, `debit_total`, `net_total = credits − debits`
  - `record_count` = number of kept Type 1 records
- 📏 Enforces **fixed width**: every record must be **exactly 120 characters**
- ⬇️ Downloads an import-ready **`corrected.aba`** (CRLF line endings)

---

## Quick Start
# Make sure venv is installed
sudo apt update
sudo apt install python3-venv

# Create a venv inside your project folder
cd ~/xero
python3 -m venv venv

# Activate it
source venv/bin/activate


```bash
# 1) Install dependencies
pip install Flask waitress

# 2) Run the app
python app.py

# 3) Open in your browser
# http://localhost:5000/
```

---

## Run Locally

This project is a single-file Flask app that serves via Waitress when run directly.

```bash
# Install dependencies (if not already installed)
pip install Flask waitress

# Start the server
python app.py

# App will be available at:
# http://localhost:5000/
```

**Requirements**
- Python 3.9+ (tested with 3.10+)
- Packages: `Flask`, `waitress`

---

## Usage

1. **Upload** your `.aba` (or `.txt`) file on the home page.  
   - The app requires each line to be **exactly 120 characters** (excluding newline).
2. **Edit** fields:
   - **Type 0**: update the **processing date** (`DDMMYY`) and other header fields as needed.
   - **Type 1**: adjust fields or **uncheck** a row to remove it from the batch.
   - **Type 7**: totals are auto-recalculated; `record_count` is read-only.
3. **Export** the corrected file—downloaded as `corrected.aba` with CRLF endings.
4. **Validate** with your bank (recommended). A public validator link is included in the UI:
   - [BCU ABA File Validator](https://www.bcu.com.au/business-banking/payments/internet-banking/aba-file-validator/)

---

## Endpoints

- **GET /** – Upload page  
- **POST /upload** – Parses the file and renders the edit form  
- **POST /process** – Rebuilds the ABA, recalculates totals, and returns a download

---

## ABA Format Crash Course

An ABA file is a fixed-width, 120-character, line-based format:

- **Type 0 — Descriptive (Header):** file metadata and the **processing date** (controls when banks release transactions).
- **Type 1 — Detail:** one line per transaction.
- **Type 7 — File Total (Trailer):** control totals and count of Type 1 records.

Each line is **exactly 120 characters** (excluding newline). The **first character** on each line is the record type (`0`, `1`, or `7`).

**Examples**

_Type 0 (Descriptive)_
```
0                 01BQL       MY NAME                   1111111004231633  230410
```
→ `230410` = processing date `10/04/2023` (DDMMYY)

_Type 1 (Detail)_
```
1000-000157108231 530000001234S R SMITH                       TEST BATCH        062-000 12223123MY ACCOUNT      00001200
```
Transaction code `53`; fictitious account details.

_Type 7 (File Total)_
```
7999-999            000312924700031292470000000000                        000004
```
`000004` = count of Type 1 records (example shows 4).

---

## Field Reference

### Type 0 — Descriptive (Header)
| Pos | Size | Field                                   | Rules (summary)                                        |
|----:|-----:|-----------------------------------------|--------------------------------------------------------|
| 1   | 1    | Record Type                             | Must be `0`                                            |
| 2–18| 17   | Blank                                   | Space filled                                           |
| 19–20| 2   | Reel Sequence No.                       | Numeric, starts at `01`, right-justified, zero-filled  |
| 21–23| 3   | User’s FI Abbrev                        | Bank abbreviation (e.g., `BQL`, `WBC`)                 |
| 24–30| 7   | Blank                                   | Space filled                                           |
| 31–56| 26  | Name of User supplying file             | Left-justified, blank-filled; not all blanks           |
| 57–62| 6   | User ID (APCA)                          | Numeric, right-justified, zero-filled                  |
| 63–74| 12  | File description (e.g., `PAYROLL`)      | Left-justified, blank-filled; not all blanks           |
| 75–80| 6   | **Processing date**                     | `DDMMYY`, valid date                                   |
| 81–120| 40 | Blank                                   | Space filled                                           |

### Type 1 — Detail (Transaction)
| Pos | Size | Field                 | Rules (summary)                                                                 |
|----:|-----:|-----------------------|---------------------------------------------------------------------------------|
| 1   | 1    | Record Type           | Must be `1`                                                                     |
| 2–8 | 7    | BSB                   | Numeric with hyphen at pos 5 (e.g., `062-000`)                                  |
| 9–17| 9    | Account Number        | Numeric/hyphens/blanks; not all blanks/zeros; right-justified, blank-filled     |
| 18  | 1    | Indicator             | `N`, or withholding: `W`, `X`, `Y`                                              |
| 19–20| 2   | Transaction Code      | Usually `53` (see codes below)                                                  |
| 21–30| 10  | Amount (cents)        | Numeric only, > 0, right-justified, zero-filled                                 |
| 31–62| 32  | Account Title         | Left-justified, blank-filled; not all blanks                                    |
| 63–80| 18  | Lodgement Reference   | Left-justified; no leading spaces/zeros/hyphens                                  |
| 81–87| 7   | Trace BSB             | User’s BSB in `XXX-XXX`                                                         |
| 88–96| 9   | Trace Account Number  | Right-justified, blank-filled                                                   |
| 97–112|16  | Name of Remitter      | Left-justified, blank-filled; not all blanks                                    |
| 113–120|8  | Withholding Tax       | Numeric only; cents; right-justified, zero-filled                               |

**Common Transaction Codes**  
`13` debit; `50` credit; **`53` pay**; `54` pension; `55` allotment; `56` dividend; `57` debenture/note interest.  
_Employee Benefits Card payments_: BSB `032-898`; Account `999999`; Lodgement Ref = 16-digit card number.

### Type 7 — File Total (Trailer)
| Pos | Size | Field                         | Rules (summary)                                    |
|----:|-----:|--------------------------------|----------------------------------------------------|
| 1   | 1    | Record Type                   | Must be `7`                                        |
| 2–8 | 7    | BSB Filler                    | Must be `999-999`                                  |
| 9–20| 12   | Blank                         | Space filled                                       |
| 21–30|10   | Net Total (cents)             | Credits − Debits; right-justified, zero-filled     |
| 31–40|10   | Credit Total (cents)          | Sum of credit amounts                              |
| 41–50|10   | Debit Total (cents)           | Sum of debit amounts                               |
| 51–74|24   | Blank                         | Space filled                                       |
| 75–80| 6   | Count of Type 1 Records       | Number of `1` records; right-justified, zero-filled|
| 81–120|40  | Blank                         | Space filled                                       |

---

## Validation Notes & Gotchas

- **120 chars per line**: Upload rejects files with any non-120-char line.
- **Alignment & padding**: Fields are padded/justified to spec on rebuild.
- **Amounts in cents**: Must be numeric. Non-numeric inputs are treated as `0` for totals (the text is still written back as entered).
- **BSB filler**: Many banks require trailer `bsb_filler = 999-999`.
- **Unknown transaction codes**: Ignored in totals; extend the mapping if needed.
- **Encoding**: Files are decoded as UTF-8.

---

## Extending

- Stricter validation (dates, BSB regex, APCA IDs)
- Custom debit/credit code mappings per bank
- CSV → ABA generation
- Bank-specific linting rules & hints
- Automated tests (pytest) for parse/format logic

---

## Security & Privacy

This app processes sensitive banking data.  
- Run locally or in a trusted environment.  
- Don’t upload to untrusted servers.  
- Delete generated files when finished.

---

## Project Structure

```
app.py
  ├─ parse_descriptive / parse_detail / parse_file_total
  ├─ format_descriptive / format_detail / format_file_total
  ├─ Inline Jinja templates (upload & edit screens)
  └─ Routes: /, /upload, /process
```

---

## FAQ

**Does the ABA format store individual transaction times?**  
No. Scheduling is controlled by the **processing date** in the **Type 0** header for the whole batch.

**Do I need to edit the trailer (Type 7)?**  
No—this app recalculates totals and record count automatically.

**Can I remove a transaction?**  
Yes—uncheck it on the edit screen; totals and record count update accordingly.

---

## License

Add your preferred license (e.g., MIT).
