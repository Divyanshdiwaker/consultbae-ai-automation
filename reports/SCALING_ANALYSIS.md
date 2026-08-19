# Scaling Analysis — 5,000 Workers

## Scenario

Right now, the project uses Streamlit, SQLite, and local storage for audio files. This works well for the assignment, but if 5,000 workers use the app over one weekend, some parts would not scale well.

## What would be a problem?

### 1. Audio storage

Currently, audio files are stored on the local machine. This would become a problem because there could be a large number of recordings.

**What I would change:**
Use cloud storage such as S3 to store the audio files.

### 2. Too many uploads at the same time

If many workers upload audio at the same time, one Streamlit application may become slow.

**What I would change:**
Use a proper production server and separate the upload part from the audio processing.

### 3. Audio processing

The app currently calculates the audio details when the user submits the recording. With many users submitting at the same time, this could slow the application down.

**What I would change:**
Process audio in the background using workers or a queue.

### 4. SQLite

SQLite is good for this assignment because it is simple and local. I would not use it for thousands of users writing data at the same time.

**What I would change:**
Move the database to PostgreSQL.

### 5. Duplicate submissions

A worker might submit the same recording twice because of a network problem or by clicking submit again.

**What I would change:**
Give every submission a unique ID and make sure the same submission is not saved twice.

### 6. Failed uploads

Some uploads or audio processing jobs will probably fail.

**What I would change:**
Keep track of the submission status and allow failed processing to be retried.

## Final Architecture

For a larger version, I would use:

**Worker → Upload/Storage → Processing → PostgreSQL**

The current system is enough for the assignment, but before launching to 5,000 workers, I would mainly improve storage, database, upload handling, and background processing.
