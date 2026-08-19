# ConsultBae Data Quality Report

## 1. Blank row in Gig Workers

**Source:** `source2_gig_workers.csv`

**Issue:**  
The CSV contains one completely blank data row.

**Impact:**  
There are 105 physical data rows across the three CSV files, but only 104 meaningful records.

**Handling:**  
The ingestion pipeline detects rows where every field is empty and skips them.

**Result:**

- Physical rows: 105
- Blank rows: 1
- Meaningful records: 104

---

## 2. Malformed field alignment in Gig Workers

**Source:** `source2_gig_workers.csv`

**Issue:**  
One Gig Workers row has values shifted into the wrong columns. The skills list appears in the email field, the email appears in the worker-name field, and subsequent fields are shifted.

**Handling:**  
The pipeline detects the unusual field pattern and reconstructs the intended values.

The recovered record is associated with Isha Chopra.

**Flags recorded:**

- `malformed_field_alignment`
- `recovered_shifted_row`

The original raw row is preserved in `source_records`.

---

## 3. Duplicate Isha Chopra record

**Source:** `source2_gig_workers.csv`

**Rows:** 7 and 20

**Issue:**  
Isha Chopra appears twice in the Gig Workers source. Row 20 is also the malformed/shifted row described above.

**Handling:**  
Both records resolve to the same person using the normalized email address.

The database contains one master person record while preserving both source records for traceability.

---

## 4. Duplicate Rohit Verma records

**Source:** `source1_naukri_applicants.csv`

**Rows:** 25 and 31

**Issue:**  
Two Naukri records refer to the same person. One uses the name `R. Verma`, while another uses `Rohit Verma`.

**Handling:**  
The records were matched using the same normalized email address.

They are represented by one master person record, with both original source rows retained.

---

## 5. Duplicate Nikhil Chopra records

**Source:** `source1_naukri_applicants.csv`

**Rows:** 27 and 37

**Issue:**  
Two Naukri records contain the same person information but use different email representations.

**Handling:**  
The records were linked using strong identity evidence:

- Same normalized phone number
- Same name
- Same supporting applicant information

They are represented by one master person record.

---

## 6. Inconsistent phone number formats

**Sources:** All three sources

**Issue:**  
Phone numbers appear in different formats, including:

- `+91-XXXXXXXXXX`
- `+91XXXXXXXXXX`
- `91XXXXXXXXXX`
- `0XXXXXXXXXX`
- `XXXXXXXXXX`

**Handling:**  
Phone numbers are normalized before matching so formatting differences do not prevent identification.

The normalized phone is stored separately from the original value.

---

## 7. Inconsistent capitalization

**Sources:** All three sources

**Issue:**  
Values such as cities, statuses and names use inconsistent capitalization.

Examples include:

- `PUNE`
- `Pune`
- `pune`

and:

- `ACTIVE`
- `Active`
- `active`

**Handling:**  
Values are normalized for comparison while the original source data is preserved.

---

## 8. Inconsistent city names

**Sources:** All three sources

**Issue:**  
Some cities use different representations, such as:

- `Bangalore`
- `Bengaluru`

and:

- `Gurgaon`
- `Gurugram`

**Handling:**  
Known city aliases are mapped to canonical city names during normalization.

Ambiguous geographic labels are not automatically changed.

---

## 9. Inconsistent CTC representation

**Source:** `source1_naukri_applicants.csv`

**Issue:**  
Current CTC values are represented using different formats, including large numeric values and lakh-style values such as `4.2`, `8.3`, etc.

**Handling:**  
CTC values are normalized into an INR representation.

The conversion rule is documented as an assumption because the source does not explicitly specify the unit for every value.

---

## 10. Inconsistent gig-worker rate formats

**Source:** `source2_gig_workers.csv`

**Issue:**  
Rates use different units, for example:

- `1415/hr`
- `403/hr`
- `15k/month`
- `72k/month`

**Handling:**  
The pipeline stores the numeric amount and unit separately.

Hourly rates are not converted into monthly rates because doing so would require assumptions about working hours.

---

## 11. Inconsistent status values

**Source:** `source2_gig_workers.csv`

**Issue:**  
Worker statuses have inconsistent capitalization and formatting.

**Handling:**  
Statuses are normalized into canonical values such as:

- `active`
- `inactive`
- `paused`

---

## 12. Inconsistent boolean values

**Source:** `source3_cbnexus_contacts.csv`

**Issue:**  
Verification values use different representations such as:

- `Y`
- `Yes`
- `yes`
- `N`
- `No`

**Handling:**  
These values are normalized into boolean representations.

---

## 13. Repeated header row

**Source:** `source3_cbnexus_contacts.csv`

**Issue:**  
A header row appears inside the actual data.

**Handling:**  
The pipeline detects the repeated header and rejects it as a data record.

The rejected row is still recorded in `source_records` with the flag:

`repeated_header_row`

---

## 14. Ambiguous identity: Arjun Mehta

**Sources:** All three sources

**Issue:**  
Multiple records use the name `Arjun Mehta`, but they contain conflicting identifying information.

Examples include different email addresses and phone numbers.

**Handling:**  
The system does not merge records based on name alone.

Records with conflicting identity evidence are kept as separate people unless a strong identifier such as normalized email or phone establishes a match.

This reduces the risk of incorrectly merging two different people.

---

## Matching Strategy

The identity-resolution strategy prioritizes strong deterministic identifiers:

1. Exact normalized email
2. Exact normalized phone
3. New person when no strong identifier matches

Name similarity alone is not sufficient to merge records.

When a match is found, the original source record is preserved in `source_records` together with:

- Source name
- Source row number
- Match method
- Match confidence
- Data-quality flags

This provides traceability for identity-resolution decisions.

---

## Final Audit Numbers

Current database state:

| Metric                               | Count |
| ------------------------------------ | ----: |
| Physical CSV rows                    |   105 |
| Blank rows                           |     1 |
| Meaningful source records            |   104 |
| Unique people                        |    60 |
| Applicant records                    |    40 |
| Gig-worker records                   |    30 |
| CBNexus records                      |    30 |
| People appearing in multiple sources |    25 |
| Same-source duplicate groups         |     3 |
| Rejected records                     |     1 |

The database therefore contains a unified `people` table while preserving source-specific information and source provenance.
