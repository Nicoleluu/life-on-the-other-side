# Life on the Other Side

Nicole Lu · Data Visualization final project · Fall 2026

How do expectations, institutions and everyday conditions shape growing up in China, Japan, South Korea, the United States, Canada and the United Kingdom?

## Final project data submission

**[Read the data document](DATA_DOCUMENT.md)** — source provenance, dimensions, licenses, descriptive statistics, validation findings and remaining collection work.

The project follows seven chapters: gender expectations, school, food, work, money, migration and family. Country differences are investigated without treating East or West as a single culture.

## Repository contents

- [Data document](DATA_DOCUMENT.md): the assignment submission.
- [Raw data](data/raw): frozen public-source downloads.
- [Processed data](data/processed): tidy project extracts and derived tables.
- [Curated data](data/curated): source-linked marriage milestones.
- [Analysis](analysis): statistics, missingness, coverage and validation results.
- [Figures](figures): two exploratory comparisons.
- [Scripts](scripts): acquisition, analysis and report generation.

## Reproduce

Use Python 3.12 with the dependencies in `requirements.txt`:

```sh
python -m pip install -r requirements.txt
python scripts/analyze.py
python scripts/report.py
```

These commands use committed snapshots and do not require source APIs. See the data document for refresh instructions and limitations. Data retain source-specific licenses; see [data rights and attribution](DATA_RIGHTS.md).

The remaining data collection is part of developing the final visualization. No CourseWorks submission is performed by this repository.
