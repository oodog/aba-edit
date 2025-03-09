from flask import Flask, request, render_template_string, Response

app = Flask(__name__)
# Make the built-in enumerate function available in templates.
app.jinja_env.globals.update(enumerate=enumerate)

# --- Parsing Functions ---
# Note: Field positions are 1-indexed per the specification; Python slices use 0-index.

def parse_descriptive(line):
    # Descriptive Record (Type 0)
    return {
        "record_type": line[0],                         # Pos 1: Must be '0'
        "blanks": line[1:18],                           # Pos 2-18: Blank (17 chars)
        "reel_sequence": line[18:20].strip(),           # Pos 19-20: Sequence Number (2 chars)
        "fi_abbr": line[20:23].strip(),                 # Pos 21-23: Financial Institution Abbreviation (3 chars)
        "blank2": line[23:30],                          # Pos 24-30: Blank (7 chars)
        "user_name": line[30:56].strip(),               # Pos 31-56: User Name (26 chars)
        "user_id": line[56:62].strip(),                 # Pos 57-62: User ID (6 chars)
        "description": line[62:74].strip(),             # Pos 63-74: Description (12 chars)
        "date": line[74:80].strip(),                    # Pos 75-80: Processing Date (6 chars, DDMMYY)
        "blank3": line[80:120]                          # Pos 81-120: Blank (40 chars)
    }

def parse_detail(line):
    # Detail Record (Type 1)
    return {
        "record_type": line[0],                         # Pos 1: Must be '1'
        "bsb": line[1:8].strip(),                       # Pos 2-8: Bank/State/Branch (7 chars, hyphen at pos 5)
        "account_number": line[8:17].strip(),           # Pos 9-17: Account Number (9 chars)
        "indicator": line[17].strip(),                  # Pos 18: Indicator (1 char)
        "transaction_code": line[18:20].strip(),        # Pos 19-20: Transaction Code (2 chars)
        "amount": line[20:30].strip(),                  # Pos 21-30: Amount in cents (10 chars)
        "account_title": line[30:62].strip(),           # Pos 31-62: Account Title (32 chars)
        "lodgement_ref": line[62:80].strip(),           # Pos 63-80: Lodgement Reference (18 chars)
        "trace_record": line[80:87].strip(),            # Pos 81-87: Trace BSB (7 chars)
        "trace_account": line[87:96].strip(),           # Pos 88-96: Trace Account Number (9 chars)
        "remitter_name": line[96:112].strip(),          # Pos 97-112: Remitter Name (16 chars)
        "withholding_tax": line[112:120].strip()        # Pos 113-120: Withholding Tax Amount (8 chars)
    }

def parse_file_total(line):
    # File Total Record (Type 7)
    return {
        "record_type": line[0],                         # Pos 1: Must be '7'
        "bsb_filler": line[1:8].strip(),                # Pos 2-8: Must be '999-999'
        "blank1": line[8:20],                           # Pos 9-20: Blank (12 chars)
        "net_total": line[20:30].strip(),               # Pos 21-30: Net Total Amount (10 chars)
        "credit_total": line[30:40].strip(),            # Pos 31-40: Credit Total Amount (10 chars)
        "debit_total": line[40:50].strip(),             # Pos 41-50: Debit Total Amount (10 chars)
        "blank2": line[50:74],                          # Pos 51-74: Blank (24 chars)
        "record_count": line[74:80].strip(),            # Pos 75-80: Count of Detail Records (6 chars)
        "blank3": line[80:120]                          # Pos 81-120: Blank (40 chars)
    }

# --- Formatting Functions ---
# These functions rebuild each record as a fixed-width 120-character string.

def format_descriptive(rec):
    return (
        rec["record_type"] +
        rec.get("blanks", " " * 17) +
        rec["reel_sequence"].rjust(2, "0") +
        rec["fi_abbr"].ljust(3) +
        rec.get("blank2", " " * 7) +
        rec["user_name"].ljust(26) +
        rec["user_id"].rjust(6, "0") +
        rec["description"].ljust(12) +
        rec["date"].rjust(6, "0") +
        rec.get("blank3", " " * 40)
    )

def format_detail(rec):
    return (
        rec["record_type"] +
        rec["bsb"].ljust(7) +
        rec["account_number"].rjust(9) +
        rec["indicator"].ljust(1) +
        rec["transaction_code"].rjust(2, "0") +
        rec["amount"].rjust(10, "0") +
        rec["account_title"].ljust(32) +
        rec["lodgement_ref"].ljust(18) +
        rec["trace_record"].ljust(7) +
        rec["trace_account"].rjust(9) +
        rec["remitter_name"].ljust(16) +
        rec["withholding_tax"].rjust(8, "0")
    )

def format_file_total(rec):
    return (
        rec["record_type"] +
        rec["bsb_filler"].ljust(7) +
        rec.get("blank1", " " * 12) +
        rec["net_total"].rjust(10, "0") +
        rec["credit_total"].rjust(10, "0") +
        rec["debit_total"].rjust(10, "0") +
        rec.get("blank2", " " * 24) +
        rec["record_count"].rjust(6, "0") +
        rec.get("blank3", " " * 40)
    )

# --- HTML Templates ---

UPLOAD_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <title>Upload ABA File</title>
  </head>
  <body>
    <h1>Upload ABA File</h1>
    <form method="POST" action="/upload" enctype="multipart/form-data">
      <input type="file" name="file" accept=".aba,.txt" required>
      <input type="submit" value="Upload">
    </form>
    <p>
      Want to test your ABA file? 
      <a href="https://www.bcu.com.au/business-banking/payments/internet-banking/aba-file-validator/" target="_blank">
        Click here to validate your ABA file
      </a>.
    </p>
  </body>
</html>
"""

EDIT_TEMPLATE = """
<!doctype html>
<html>
  <head>
    <title>Edit ABA File</title>
    <style>
      .record { border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
    </style>
  </head>
  <body>
    <h1>Edit ABA File</h1>
    <form method="POST" action="/process">
      <h2>Descriptive Record (Type 0)</h2>
      <div class="record">
        Record Type: <input type="text" name="desc_record_type" value="{{ desc.record_type }}" readonly><br>
        Reel Sequence Number: <input type="text" name="desc_reel_sequence" value="{{ desc.reel_sequence }}" maxlength="2" required><br>
        FI Abbreviation: <input type="text" name="desc_fi_abbr" value="{{ desc.fi_abbr }}" maxlength="3" required><br>
        User Name: <input type="text" name="desc_user_name" value="{{ desc.user_name }}" maxlength="26" required><br>
        User ID: <input type="text" name="desc_user_id" value="{{ desc.user_id }}" maxlength="6" required><br>
        Description: <input type="text" name="desc_description" value="{{ desc.description }}" maxlength="12" required><br>
        Date (DDMMYY): <input type="text" name="desc_date" value="{{ desc.date }}" maxlength="6" required><br>
      </div>
      
      <h2>Detail Records (Type 1)</h2>
      <p>Uncheck any record to remove it.</p>
      {% for i, d in enumerate(details) %}
        <div class="record">
          <input type="checkbox" name="keep_{{ i }}" checked> Keep this record<br>
          Record Type: <input type="text" name="detail_{{ i }}_record_type" value="{{ d.record_type }}" readonly><br>
          BSB: <input type="text" name="detail_{{ i }}_bsb" value="{{ d.bsb }}" maxlength="7" required><br>
          Account Number: <input type="text" name="detail_{{ i }}_account_number" value="{{ d.account_number }}" maxlength="9" required><br>
          Indicator: <input type="text" name="detail_{{ i }}_indicator" value="{{ d.indicator }}" maxlength="1"><br>
          Transaction Code: <input type="text" name="detail_{{ i }}_transaction_code" value="{{ d.transaction_code }}" maxlength="2" required><br>
          Amount (in cents): <input type="text" name="detail_{{ i }}_amount" value="{{ d.amount }}" maxlength="10" required><br>
          Account Title: <input type="text" name="detail_{{ i }}_account_title" value="{{ d.account_title }}" maxlength="32" required><br>
          Lodgement Reference: <input type="text" name="detail_{{ i }}_lodgement_ref" value="{{ d.lodgement_ref }}" maxlength="18" required><br>
          Trace BSB: <input type="text" name="detail_{{ i }}_trace_record" value="{{ d.trace_record }}" maxlength="7" required><br>
          Trace Account Number: <input type="text" name="detail_{{ i }}_trace_account" value="{{ d.trace_account }}" maxlength="9" required><br>
          Remitter Name: <input type="text" name="detail_{{ i }}_remitter_name" value="{{ d.remitter_name }}" maxlength="16" required><br>
          Withholding Tax: <input type="text" name="detail_{{ i }}_withholding_tax" value="{{ d.withholding_tax }}" maxlength="8"><br>
        </div>
      {% endfor %}
      <input type="hidden" name="detail_count" value="{{ details|length }}">
      
      <h2>File Total Record (Type 7)</h2>
      <div class="record">
        Record Type: <input type="text" name="total_record_type" value="{{ total.record_type }}" readonly><br>
        BSB Filler: <input type="text" name="total_bsb_filler" value="{{ total.bsb_filler }}" maxlength="7" required><br>
        Net Total: <input type="text" name="total_net_total" value="{{ total.net_total }}" maxlength="10" required><br>
        Credit Total: <input type="text" name="total_credit_total" value="{{ total.credit_total }}" maxlength="10" required><br>
        Debit Total: <input type="text" name="total_debit_total" value="{{ total.debit_total }}" maxlength="10" required><br>
        Record Count: <input type="text" name="total_record_count" value="{{ total.record_count }}" maxlength="6" readonly><br>
      </div>
      
      <!-- Preserve the unused blank fields as hidden values -->
      <input type="hidden" name="desc_blanks" value="{{ desc.blanks }}">
      <input type="hidden" name="desc_blank2" value="{{ desc.blank2 }}">
      <input type="hidden" name="desc_blank3" value="{{ desc.blank3 }}">
      <input type="hidden" name="total_blank1" value="{{ total.blank1 }}">
      <input type="hidden" name="total_blank2" value="{{ total.blank2 }}">
      <input type="hidden" name="total_blank3" value="{{ total.blank3 }}">
      
      <button type="submit">Export Corrected ABA File</button>
    </form>
  </body>
</html>
"""

# --- Routes ---

@app.route('/')
def index():
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file:
        return "No file uploaded", 400

    content = file.read().decode('utf-8')
    # Split using universal newlines (each record should be 120 characters)
    lines = content.splitlines()
    
    if len(lines) < 3:
        return "File format error: must contain a descriptive record, at least one detail record, and a total record.", 400

    # Validate each record is exactly 120 characters long.
    for line in lines:
        if len(line) != 120:
            return "Each record must be exactly 120 characters long.", 400

    # Parse the records.
    desc = parse_descriptive(lines[0])
    total = parse_file_total(lines[-1])
    details = [parse_detail(line) for line in lines[1:-1]]
    
    return render_template_string(EDIT_TEMPLATE, desc=desc, details=details, total=total)

@app.route('/process', methods=['POST'])
def process():
    # Reassemble the descriptive record from form fields.
    desc = {
        "record_type": request.form.get("desc_record_type"),
        "blanks": request.form.get("desc_blanks"),
        "reel_sequence": request.form.get("desc_reel_sequence"),
        "fi_abbr": request.form.get("desc_fi_abbr"),
        "blank2": request.form.get("desc_blank2"),
        "user_name": request.form.get("desc_user_name"),
        "user_id": request.form.get("desc_user_id"),
        "description": request.form.get("desc_description"),
        "date": request.form.get("desc_date"),
        "blank3": request.form.get("desc_blank3")
    }
    
    # Reassemble detail records (only keep those whose checkbox is checked).
    detail_count = int(request.form.get("detail_count"))
    details = []
    for i in range(detail_count):
        if request.form.get(f"keep_{i}") is not None:
            detail = {
                "record_type": request.form.get(f"detail_{i}_record_type"),
                "bsb": request.form.get(f"detail_{i}_bsb"),
                "account_number": request.form.get(f"detail_{i}_account_number"),
                "indicator": request.form.get(f"detail_{i}_indicator"),
                "transaction_code": request.form.get(f"detail_{i}_transaction_code"),
                "amount": request.form.get(f"detail_{i}_amount"),
                "account_title": request.form.get(f"detail_{i}_account_title"),
                "lodgement_ref": request.form.get(f"detail_{i}_lodgement_ref"),
                "trace_record": request.form.get(f"detail_{i}_trace_record"),
                "trace_account": request.form.get(f"detail_{i}_trace_account"),
                "remitter_name": request.form.get(f"detail_{i}_remitter_name"),
                "withholding_tax": request.form.get(f"detail_{i}_withholding_tax")
            }
            details.append(detail)
    
    # --- Recalculate Totals ---
    # Here we assume that transaction codes "50", "53", "54", "55", "56", "57" indicate credit transactions,
    # while transaction code "13" indicates a debit.
    credit_total = 0
    debit_total = 0
    for d in details:
        try:
            amt = int(d["amount"])
        except ValueError:
            amt = 0
        tc = d["transaction_code"]
        if tc in ("50", "53", "54", "55", "56", "57"):
            credit_total += amt
        elif tc == "13":
            debit_total += amt
    net_total = credit_total - debit_total
    
    # Format totals as 10-digit, zero-filled numbers.
    credit_total_str = str(credit_total).rjust(10, "0")
    debit_total_str = str(debit_total).rjust(10, "0")
    net_total_str = str(net_total).rjust(10, "0")
    
    # Reassemble the file total record with recalculated totals.
    total = {
        "record_type": request.form.get("total_record_type"),
        "bsb_filler": request.form.get("total_bsb_filler"),
        "blank1": request.form.get("total_blank1"),
        "net_total": net_total_str,
        "credit_total": credit_total_str,
        "debit_total": debit_total_str,
        "blank2": request.form.get("total_blank2"),
        # Update the record count to match the number of kept detail records.
        "record_count": str(len(details)).rjust(6, "0"),
        "blank3": request.form.get("total_blank3")
    }
    
    # Reassemble each record into a 120-character string.
    new_file = []
    new_file.append(format_descriptive(desc))
    for d in details:
        new_file.append(format_detail(d))
    new_file.append(format_file_total(total))
    
    # Join records with CRLF and send as a downloadable file.
    new_file_content = "\r\n".join(new_file) + "\r\n"
    
    return Response(new_file_content,
                    mimetype="text/plain",
                    headers={"Content-Disposition": "attachment;filename=corrected.aba"})

if __name__ == '__main__':
    from waitress import serve
    # Run the Flask app with Waitress on port 5000.
    serve(app, host='0.0.0.0', port=5000)
