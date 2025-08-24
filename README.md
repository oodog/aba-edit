ABA File Editor (Flask)

A tiny web app for safely editing Australian Bankers Association (ABA/Cemtex) batch payment files.

Primary use case: if you miss your bank’s midnight cutoff, open the exported ABA file, update the processing date (Type 0 header), optionally drop any transactions, and download a corrected, import-ready ABA file. The app also recalculates the file totals and record count in the trailer.

⚠️ Always validate the edited file with your bank before using it in production.

Features

Upload an ABA file and view parsed records

Edit Type 0 (Descriptive) fields, including processing date (DDMMYY)

Edit or remove individual Type 1 (Detail) records (uncheck to remove)

Recalculate Type 7 (File Total):

credit_total, debit_total, net_total = credits − debits

record_count = number of kept Type 1 records

Enforces fixed-width format: every record must be exactly 120 characters

Downloads a ready-to-import corrected.aba (CRLF line endings)

How it works (under the hood)

Parsing: Lines are split and validated to be 120 characters long.

Type 0 → header (descriptive)

Type 1 → one per transaction (detail)

Type 7 → trailer (file totals)

Editing: The HTML form renders all parsed fields; you can change Type 0 / Type 1 fields and remove any detail rows.

Totals logic:

Credits: 50, 53, 54, 55, 56, 57

Debits: 13

Any other transaction codes are ignored in totals.

Amounts are expected in cents (numeric). Non-numeric amounts are treated as 0 for totals.

Rebuild: Records are reassembled to fixed-width strings and joined with \r\n.

Requirements

Python 3.9+ (tested with 3.10+)

Pip packages: Flask, waitress

pip install Flask waitress

Run locally
python app.py
# or, explicitly with waitress inside the script:
# serve(app, host='0.0.0.0', port=5000)


Open: http://localhost:5000/

Usage

Upload your .aba (or .txt) file on the home page.

The app requires each line to be exactly 120 characters.

Edit fields:

Type 0: update the processing date (DDMMYY) and any other header fields.

Type 1: adjust fields as needed, or uncheck a row to remove it.

Type 7: totals are auto-recalculated; record_count becomes read-only.

Export the corrected file. You’ll receive corrected.aba for download (CRLF endings).

Validate with your bank (recommended).
A public validator is linked from the UI.

Endpoints

GET / – Upload page

POST /upload – Parses the file and renders the edit form

POST /process – Rebuilds the ABA, recalculates totals, and returns a download

Field coverage (summary)
Type 0 — Descriptive (Header)

reel_sequence (2)

fi_abbr (3)

user_name (26)

user_id (6)

description (12)

date (DDMMYY) (6)

Type 1 — Detail (Transaction)

bsb (XXX-XXX), account_number (9)

indicator (e.g., N, W, X, Y)

transaction_code (2) – totals use codes listed above

amount (10, cents)

account_title, lodgement_ref

trace_record (BSB), trace_account (9)

remitter_name, withholding_tax

Type 7 — File Total (Trailer)

bsb_filler (should be 999-999)

net_total, credit_total, debit_total (all 10, cents)

record_count (6, calculated)

The app preserves blank/filler fields so the 120-char width is maintained.

Validation notes & gotchas

120 chars per line: the upload step rejects files with any line not exactly 120 characters (excluding newline).

Character sets & alignment: Fields are padded/justified to spec when rebuilding.

Amounts: Must be numeric (in cents). Non-numeric amounts are treated as 0 for totals (the field text is still written back as entered).

BSB filler: The trailer’s bsb_filler is user-editable; many banks require 999-999.

Unknown transaction codes: They won’t contribute to totals; consider extending the mapping if needed.

Encoding: Files are decoded as UTF-8.

Extending

Add stricter validations (dates, BSB patterns, APCA IDs)

Support additional debit/credit codes or custom mappings

CSV import → ABA generation

Bank-specific linting rules

Automated tests (pytest) for parsers/formatters

Security & privacy

This app processes banking files containing sensitive information.

Run locally or in a trusted environment.

Do not upload to untrusted servers.

Delete generated files when finished.

Project structure (single file app)

app.py – Flask app, parsers/formatters, HTML templates and routes

parse_descriptive, parse_detail, parse_file_total

format_descriptive, format_detail, format_file_total

Simple Jinja templates rendered from strings

FAQ

Does the ABA format store individual transaction times?
No. Scheduling is controlled by the processing date in the Type 0 header for the whole batch.

Do I need to edit the trailer (Type 7)?
No—this app recalculates totals and record count automatically.

Can I remove a transaction?
Yes—uncheck it on the edit screen; totals and record count update accordingly.

License

Choose a license (e.g., MIT) and add it here.

Acknowledgements

ABA/Cemtex is a fixed-width, line-based format used by Australian financial institutions.
A link to a public validator is included in the UI for convenience.
