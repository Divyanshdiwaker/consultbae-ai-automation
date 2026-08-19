from __future__ import annotations

import sqlite3
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "consultbae.db"


st.set_page_config(
    page_title="ConsultBae Submissions",
    page_icon="📋",
    layout="wide",
)

st.title("ConsultBae Audio Submissions")
st.caption("Internal submissions/admin view")


def get_submissions() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            """
            SELECT
                submission_id,
                person_id,
                name,
                phone,
                file_path,
                duration_seconds,
                sample_rate_khz,
                bitrate_kbps,
                loudness_db,
                created_at
            FROM audio_submissions
            ORDER BY submission_id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


submissions = get_submissions()

if not submissions:
    st.info("No audio submissions yet.")
    st.stop()


for submission in submissions:
    st.markdown("---")

    left, right = st.columns([2, 1])

    with left:
        st.subheader(
            f"{submission['name']} "
            f"(Person ID: {submission['person_id']})"
        )

        st.write(f"Phone: {submission['phone']}")

        audio_path = Path(submission["file_path"])

        if audio_path.exists():
            st.audio(str(audio_path))
        else:
            st.warning("Audio file is missing.")

        st.caption(
            f"Submitted: {submission['created_at']}"
        )

    with right:
        st.write(
            f"**Duration:** "
            f"{submission['duration_seconds']:.3f} s"
        )

        st.write(
            f"**Sample rate:** "
            f"{submission['sample_rate_khz']:.3f} kHz"
        )

        bitrate = submission["bitrate_kbps"]

        if bitrate is not None:
            st.write(
                f"**Bitrate:** "
                f"{bitrate:.2f} kbps"
            )

        loudness = submission["loudness_db"]

        if loudness is not None:
            st.write(
                f"**Loudness:** "
                f"{loudness:.2f} dB"
            )