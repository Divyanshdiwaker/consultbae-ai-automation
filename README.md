# ConsultBae AI Automation Assignment

A take-home project for ConsultBae's AI Automation role.

The project combines data from three different CSV sources into one SQLite database, adds an n8n automation for CSV-based duplicate checking, and provides an audio collection app for recording or uploading audio.

## What I built

### Task 1 — Merge the data

I used SQLite as the main database because it is simple and works well for this assignment.

The three source files are:

- `source1_naukri_applicants.csv`
- `source2_gig_workers.csv`
- `source3_cbnexus_contacts.csv`

The ingestion pipeline:

1. Reads all three CSV files.
2. Cleans and normalizes the data.
3. Matches people using normalized email and phone.
4. Creates one master person record.
5. Keeps the original source records for traceability.

I did not merge people using name alone because the same name can belong to different people.

### Final audit

- Physical CSV rows: 105
- Blank rows: 1
- Meaningful source records: 104
- Unique people: 60
- Applicant records: 40
- Gig-worker records: 30
- CBNexus records: 30
- People appearing in multiple sources: 25

More details are available in [`DATA_ISSUES.md`](DATA_ISSUES.md).

## Matching logic

The matching order is:

1. Exact normalized email
2. Exact normalized phone
3. Create a new person if no strong identifier matches

Name similarity alone is not enough to merge two records.

This was important for cases such as multiple `Arjun Mehta` records with different identifying information. In those cases I preferred keeping records separate rather than incorrectly merging two people.

## Task 2 — n8n automation

I used n8n to build a CSV-based duplicate checking workflow.

The workflow receives a CSV through a webhook, extracts the CSV rows, checks each person against the existing database, and then either sends a duplicate alert or creates a new person.

The final workflow is:

```text
Webhook
   ↓
Extract from File
   ↓
GET /people/lookup
   ↓
IF
 ├── Existing person → Duplicate Alert
 │
 └── New person → POST /people → Create person
```

### How it works

The CSV contains:

```text
full_name
email
phone
city
```

The Webhook receives the CSV as a file.

`Extract from File` converts the CSV into individual rows.

For each row, n8n calls:

```text
GET /people/lookup
```

using the person's email and phone.

If the person already exists:

```text
found = true
```

and n8n sends a duplicate alert.

If the person does not exist:

```text
found = false
```

and n8n sends the person details to:

```text
POST /people
```

to create the new person.

The exported workflow is:

`n8n/consultbae_Final_workflow.json`

The assignment specifically requires the n8n workflow to be exported into the repository.

## Task 3 — Audio collection app

The user-facing audio application is built with Streamlit.

A user can:

- Enter their name
- Enter their phone number
- Record audio directly in the browser
- Or upload an audio file
- Submit the recording

For each submission, the application automatically extracts:

- Duration
- Sample rate
- Bitrate
- Loudness

The audio file is saved locally and the metadata is stored in the `audio_submissions` table.

The database already contains fields for duration, sample rate, bitrate, and loudness.

There is also a separate internal submissions page where saved recordings can be played back and their metadata can be reviewed.

The assignment requires the audio app to support audio submission, metadata extraction, storage, and a submissions/playback view.

## Project structure

```text
consultbae-ai-automation/
│
├── app/
│   ├── app.py
│   ├── audio_utils.py
│   ├── submissions.py
│   └── audio/
│
├── data/
│   ├── source1_naukri_applicants.csv
│   ├── source2_gig_workers.csv
│   └── source3_cbnexus_contacts.csv
│
├── n8n/
│   └── consultbae_Final_workflow.json
│
├── reports/
│   └── SCALING_ANALYSIS.md
│
├── src/
│   ├── api.py
│   ├── audit.py
│   ├── database.py
│   ├── duplicate_audit.py
│   ├── ingest.py
│   ├── matching_audit.py
│   ├── normalize.py
│   └── pipeline.py
│
├── tests/
│
├── DATA_ISSUES.md
├── README.md
├── requirements.txt
└── .gitignore
```

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Divyanshdiwaker/consultbae-ai-automation
cd consultbae-ai-automation
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

## Run the data pipeline

From the project root:

```bash
python -m src.pipeline
```

This creates the SQLite database:

```text
consultbae.db
```

## Run the tests

```bash
python -m pytest
```

The tests cover normalization and important database/matching cases.

## Run the audit

```bash
python -m src.audit
```

The audit prints the CSV row counts and database counts.

## Run FastAPI

Start the API with:

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Run the audio submission app

With FastAPI running, open another terminal and run:

```bash
python -m streamlit run app/app.py --server.port 8501
```

The user-facing app allows the user to record audio in the browser or upload an audio file.

## Run the internal submissions page

```bash
python -m streamlit run app/submissions.py --server.port 8502
```

This page is for internal review of saved audio submissions.

## Data quality issues

The source data contained several problems that had to be handled during ingestion.

### Blank row

There was one completely blank row in the Gig Workers file.

It is detected and skipped.

### Malformed Gig Worker row

One Gig Worker row had values shifted into the wrong columns.

The pipeline detects the pattern, reconstructs the intended values, and keeps the original raw row for traceability.

### Duplicate records

There were duplicate records for people such as Isha Chopra, Rohit Verma, and Nikhil Chopra.

These were linked to one master person using strong identity evidence.

### Phone formatting

Phone numbers appeared in different formats such as:

```text
+91-XXXXXXXXXX
+91XXXXXXXXXX
91XXXXXXXXXX
0XXXXXXXXXX
XXXXXXXXXX
```

They are normalized before matching.

### Capitalization

Values such as cities, names, and statuses had inconsistent capitalization.

They are normalized for comparison while the original source data is preserved.

### City aliases

Examples include:

```text
Bangalore / Bengaluru
Gurgaon / Gurugram
```

Known aliases are converted to canonical values.

### CTC formatting

Current CTC values appeared in different formats.

Values are normalized to INR using a documented assumption that values below 100 represent lakhs.

### Gig-worker rates

Rates appeared as both hourly and monthly values.

The amount and unit are stored separately rather than making assumptions about working hours.

### Boolean values

Verification values appeared in formats such as:

```text
Y / Yes / yes
N / No
```

These are normalized into boolean values.

### Repeated header row

A header row appeared inside the CBNexus data.

It is detected and rejected instead of being inserted as a person.

### Ambiguous identities

Multiple records named `Arjun Mehta` had conflicting identifying information.

These records are kept separate unless strong email or phone evidence establishes a match.

## Idempotency

One issue I found during testing was that running the ingestion pipeline twice initially increased `source_records` from 104 to 208.

This showed that the pipeline was inserting the same source rows again.

I changed the source-record handling so that a source record is identified by:

```text
source_name + source_row_number
```

and the existing record is replaced before the current version is inserted.

The expected result is now:

```text
Run 1 → 104
Run 2 → 104
Run 3 → 104
```

instead of:

```text
104 → 208 → 312
```

This made the ingestion idempotent.

## Stuck log

### 1. Malformed CSV row

One Gig Worker row had its values shifted into different columns.

I first found that normal CSV parsing did not give the correct person data. I inspected the row pattern and added logic to detect the shifted fields and recover the intended values.

I also kept the raw source row so the decision is traceable.

### 2. Duplicate records after repeated ingestion

When I first ran the ingestion pipeline more than once, the source record count doubled.

This helped me identify that the pipeline was not idempotent.

I changed the source-record handling to use the source name and source row number so running the pipeline again does not create another copy of the same source record.

### 3. Learning n8n

This was my first time using n8n.

The main challenge was understanding how data moves between nodes and how to handle existing versus new people.

I first built and tested the lookup and IF branches, then changed the input to a CSV Webhook so that the workflow receives real CSV data instead of manually entered test data.

The final workflow was tested with one existing person and one new person.

## Scaling to 5,000 workers

The current project is designed as a simple take-home implementation.

For 5,000 workers, I would mainly improve:

- Audio storage: move from local storage to cloud object storage.
- Database: move from SQLite to PostgreSQL.
- Audio processing: move processing to background workers.
- Reliability: add retry handling and duplicate protection.

The full scaling analysis is available in [`reports/SCALING_ANALYSIS.md`](reports/SCALING_ANALYSIS.md).

## Key design decisions

### Conservative identity matching

I preferred a false negative over a false positive when identity information conflicted.

Name alone was not strong enough to merge records.

### SQLite for the assignment

SQLite was chosen because it is simple, local, and does not require a separate database server.

For a larger production deployment I would move to PostgreSQL.

### FastAPI between n8n and SQLite

n8n talks to the database through FastAPI instead of directly accessing SQLite.

This keeps the database logic in one place and allows the same lookup/create logic to be reused by the automation and audio application.

## Final result

The project now includes:

- A working data ingestion and matching pipeline
- Data quality handling and audit reports
- A CSV-based n8n automation
- Duplicate detection and alerting
- New-person creation
- Browser audio recording
- Audio file upload
- Automatic audio metadata extraction
- Audio submission storage
- Internal submission review and playback
- Scaling analysis for a larger deployment
