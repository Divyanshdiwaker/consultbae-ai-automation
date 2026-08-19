from __future__ import annotations


import sqlite3
import uuid
from pathlib import Path

import requests
import streamlit as st
from streamlit_mic_recorder import mic_recorder

from audio_utils import analyze_audio


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = PROJECT_ROOT / "app" / "audio"
API_URL = "http://127.0.0.1:8000"

AUDIO_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(
    page_title="ConsultBae Audio Collection",
    page_icon="🎙️",
    layout="centered",
)

st.title("ConsultBae Audio Submission")
st.write("Enter your details and submit your audio recording.")


def lookup_person(phone_number: str) -> dict:
    response = requests.get(
        f"{API_URL}/people/lookup",
        params={"phone": phone_number},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def create_person(name_value: str, phone_value: str) -> dict:
    response = requests.post(
        f"{API_URL}/people",
        json={
            "full_name": name_value,
            "phone": phone_value,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def save_submission(
    person_id: int,
    name_value: str,
    phone_value: str,
    file_path: Path,
    metadata: dict,
) -> None:
    db_path = PROJECT_ROOT / "consultbae.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO audio_submissions (
                person_id,
                name,
                phone,
                file_path,
                duration_seconds,
                sample_rate_khz,
                bitrate_kbps,
                loudness_db
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                name_value,
                phone_value,
                str(file_path),
                metadata["duration_seconds"],
                metadata["sample_rate_khz"],
                metadata["bitrate_kbps"],
                metadata["loudness_db"],
            ),
        )
        conn.commit()


name = st.text_input("Name")
phone = st.text_input("Phone Number")

st.subheader("Audio")

input_method = st.radio(
    "Choose how you want to provide your audio:",
    ["Record Audio", "Upload Audio"],
    horizontal=True,
)

recorded_audio = None
uploaded_file = None

if input_method == "Record Audio":
    st.write("Click start, speak, then click stop.")

    recorded_audio = mic_recorder(
        start_prompt="🎙️ Start Recording",
        stop_prompt="⏹️ Stop Recording",
        just_once=False,
        use_container_width=True,
        format="wav",
        key="audio_recorder",
    )

    if recorded_audio:
        st.audio(
            recorded_audio["bytes"],
            format="audio/wav",
        )

else:
    uploaded_file = st.file_uploader(
        "Upload Audio",
        type=["wav", "mp3", "flac", "ogg", "m4a"],
    )

    if uploaded_file is not None:
        st.audio(
            uploaded_file,
            format=uploaded_file.type or "audio/wav",
        )


submit = st.button(
    "Submit Audio",
    type="primary",
    use_container_width=True,
)


if submit:
    if not name.strip():
        st.error("Please enter your name.")
        st.stop()

    if not phone.strip():
        st.error("Please enter your phone number.")
        st.stop()

    if input_method == "Record Audio":
        if not recorded_audio:
            st.error("Please record an audio clip first.")
            st.stop()

        audio_bytes = recorded_audio["bytes"]
        extension = ".wav"

    else:
        if uploaded_file is None:
            st.error("Please upload an audio file.")
            st.stop()

        audio_bytes = uploaded_file.getvalue()
        extension = Path(uploaded_file.name).suffix.lower()

        if not extension:
            extension = ".wav"

    try:
        # Find existing person by phone.
        lookup = lookup_person(phone.strip())

        if lookup.get("found"):
            person = lookup["person"]
            person_id = int(person["person_id"])

        else:
            # Create person if not already present.
            created = create_person(
                name.strip(),
                phone.strip(),
            )

            if not created.get("created"):
                person = created.get("person")

                if not person:
                    st.error(
                        "Could not create or identify the person."
                    )
                    st.stop()

                person_id = int(person["person_id"])

            else:
                person = created["person"]
                person_id = int(person["person_id"])

        # Save audio file.
        filename = f"{uuid.uuid4().hex}{extension}"
        destination = AUDIO_DIR / filename

        destination.write_bytes(audio_bytes)

        # Extract metadata.
        metadata = analyze_audio(destination)

        # Save submission to SQLite.
        save_submission(
            person_id=person_id,
            name_value=name.strip(),
            phone_value=phone.strip(),
            file_path=destination,
            metadata=metadata,
        )

        st.success("Audio submitted successfully.")

        st.subheader("Audio Details")

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Duration",
                f"{metadata['duration_seconds']} s",
            )

            st.metric(
                "Sample Rate",
                f"{metadata['sample_rate_khz']} kHz",
            )

        with col2:
            st.metric(
                "Bitrate",
                f"{metadata['bitrate_kbps']} kbps",
            )

            st.metric(
                "Loudness",
                f"{metadata['loudness_db']} dB",
            )

    except requests.RequestException as exc:
        st.error(f"Database/API connection failed: {exc}")

    except Exception as exc:
        st.error(f"Audio submission failed: {exc}")