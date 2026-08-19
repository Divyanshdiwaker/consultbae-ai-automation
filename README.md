# ConsultBae AI Automation Assignment

A take-home project for ConsultBae's AI Automation role.

The project combines data from 3 different CSV files into one SQLite database, adds an n8n automation for duplicate checking, and provides a small audio collection app.

## What I built

### Task 1 — Merge the data

I used SQLite as the main database.

The three CSV files are:

- `source1_naukri_applicants.csv`
- `source2_gig_workers.csv`
- `source3_cbnexus_contacts.csv`

The pipeline:

1. Reads all three CSV files.
2. Cleans and normalizes the data.
3. Matches people using normalized email and phone.
4. Stores one master person in the `people` table.
5. Keeps the original source records for traceability.

I chose not to merge people using name alone because the same name can belong to different people.

Final audit:

- Physical rows: 105
- Blank rows: 1
- Meaningful records: 104
- Unique people: 60
- Applicant records: 40
- Gig worker records: 30
- CBNexus records: 30
- People appearing in multiple sources: 25

More details are in [`DATA_ISSUES.md`](DATA_ISSUES.md).

## Matching logic

The matching order is:

1. Exact normalized email
2. Exact normalized phone
3. Create a new person if no strong match is found

This was intentionally kept conservative to avoid incorrectly merging two different people.

## Task 2 — n8n automation

I used n8n for the no-code/low-code automation.

The workflow is:

```text
Manual Trigger
      ↓
Edit Fields
      ↓
GET /people/lookup
      ↓
IF
 ├── Existing person → Duplicate Alert
 │
 └── New person → POST /people → Created person
```

n8n communicates with the database through the FastAPI API.

For an existing person, the workflow sends a duplicate alert to a webhook.

For a new person, it creates the person through the API.

The exported workflow is:

`n8n/consultbae_duplicate_alert.json`

## Task 3 — Audio collection app

The audio application is built with Streamlit.

A user can:

- Enter their name
- Enter their phone number
- Record audio directly in the browser
- Or upload an audio file
- Submit the recording

For each submission, the application extracts:

- Duration
- Sample rate
- Bitrate
- Loudness

The audio file is stored locally and the metadata is stored in the `audio_submissions` table.

There is also a separate internal submissions page where saved recordings can be played back and their metadata can be viewed.

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
│   └── consultbae_duplicate_alert.json
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

Activate it on Windows:

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

The pipeline creates/updates:

```text
consultbae.db
```

## Run the tests

```bash
python -m pytest
```

The current test suite covers normalization, database creation, matching behaviour, and important data-quality cases.

## Run the FastAPI API

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

API health check:

```text
http://127.0.0.1:8000/health
```

## Run the audio app

With FastAPI running, open another terminal and run:

```bash
python -m streamlit run app/app.py --server.port 8501
```

The user-facing audio submission app will open in the browser.

## Run the internal submissions page

```bash
python -m streamlit run app/submissions.py --server.port 8502
```

This page is for reviewing saved submissions and playing the recordings.

## Important data decisions

### Phone normalization

Different Indian phone formats are converted into a common 10-digit format before matching.

### Email normalization

Emails are trimmed and converted to lowercase.

### City normalization

Known aliases such as Bangalore/Bengaluru and Gurgaon/Gurugram are converted to a common value.

### CTC

The source contains both INR-looking values and lakh-style values. Values below 100 were treated as lakhs. This is documented as an assumption.

### Gig-worker rates

Hourly and monthly rates are kept as separate units instead of converting between them.

### Ambiguous identities

Records with the same name but conflicting identity information are kept separate unless there is strong email or phone evidence.

## Stuck log

### 1. Malformed CSV row

One Gig Worker row had values shifted into the wrong columns. At first, treating the CSV normally produced incorrect person data.

I checked the row pattern and added logic to detect the unusual values and move them back into the expected fields. I also kept the original raw row for traceability.

### 2. Duplicate source records on repeated pipeline runs

When I ran the ingestion pipeline more than once, `source_records` increased from 104 to 208.

This showed that the ingestion was not idempotent.

I changed the source-record handling so that the same `source_name + source_row_number` is replaced instead of inserted again.

After the fix, repeated runs keep the count at 104.

### 3. Building the n8n workflow

This was my first time using n8n.

The main challenge was understanding how data moves between nodes and how the IF node should handle an existing person versus a new person.

I used the FastAPI lookup endpoint so n8n could check the database without putting the database logic directly into n8n. I then tested both branches separately and added a webhook duplicate alert.

## Scaling to 5,000 workers

The current project is designed as a simple take-home implementation.

For 5,000 workers, I would change the architecture mainly in four areas:

- Move audio files from local storage to cloud object storage.
- Move from SQLite to PostgreSQL.
- Process audio in the background instead of during the request.
- Add retry and duplicate protection for submissions.

More detail is in [`reports/SCALING_ANALYSIS.md`](reports/SCALING_ANALYSIS.md).

## Final note

The main goal of this project was to build something working end-to-end and make sensible decisions around messy data, matching, automation, and audio collection.
