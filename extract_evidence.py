
import csv
import re
from pathlib import Path
from collections import Counter

PROJECT = Path(__file__).resolve().parent

INPUT_FILE = PROJECT / "data" / "processed" / "classified_articles.csv"
OUTPUT_FILE = PROJECT / "data" / "processed" / "evidence_matrix.csv"
REPORT_FILE = PROJECT / "reports" / "extraction_summary.txt"

DRUGS = {
    "Empagliflozin": ["empagliflozin", "jardiance"],
    "Dapagliflozin": ["dapagliflozin", "farxiga", "forxiga"],
    "Canagliflozin": ["canagliflozin", "invokana"],
    "Ertugliflozin": ["ertugliflozin", "steglatro"],
}

OUTCOMES = {
    "HbA1c": ["hba1c", "glycated hemoglobin", "glycaemic control"],
    "Heart Failure": ["heart failure", "hospitalization for heart failure"],
    "Kidney Outcomes": [
        "kidney disease", "renal outcome", "egfr",
        "chronic kidney disease", "albuminuria"
    ],
    "Cardiovascular Events": [
        "cardiovascular death", "myocardial infarction",
        "stroke", "mace"
    ],
    "Adverse Events": [
        "adverse event", "hypoglycemia",
        "ketoacidosis", "genital infection"
    ],
    "Mortality": ["all-cause mortality", "overall mortality"],
}

POPULATIONS = {
    "Type 2 Diabetes": ["type 2 diabetes", "t2dm", "type ii diabetes"],
    "Chronic Kidney Disease": ["chronic kidney disease", "ckd"],
    "Heart Failure": ["heart failure", "hfpef", "hfref"],
}


def find_terms(text, dictionary):
    """Detect keyword mentions; does not establish clinical findings."""
    matches = []

    for label, keywords in dictionary.items():
        for keyword in keywords:
            pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
            if re.search(pattern, text, flags=re.IGNORECASE):
                matches.append(label)
                break

    return "; ".join(matches)


def main():
    if not INPUT_FILE.exists():
        print("ERROR: Input file not found:")
        print(INPUT_FILE)
        return

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        articles = list(csv.DictReader(file))

    if not articles:
        print("ERROR: No articles found.")
        return

    results = []
    drug_counts = Counter()
    outcome_counts = Counter()

    for article in articles:
        title = article.get("Title", "")
        abstract = article.get("Abstract", "")
        text = title + " " + abstract

        drugs = find_terms(text, DRUGS)
        outcomes = find_terms(text, OUTCOMES)
        populations = find_terms(text, POPULATIONS)

        for drug in drugs.split("; "):
            if drug:
                drug_counts[drug] += 1

        for outcome in outcomes.split("; "):
            if outcome:
                outcome_counts[outcome] += 1

        results.append({
            **article,
            "Drug_Mentions": drugs,
            "Outcome_Mentions": outcomes,
            "Population_Mentions": populations,
            "Extraction_Method": "Keyword-based",
            "Verified": "No",
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=list(results[0].keys())
        )
        writer.writeheader()
        writer.writerows(results)

    with REPORT_FILE.open("w", encoding="utf-8") as file:
        file.write("PHARMACEUTICAL EVIDENCE EXTRACTION\n")
        file.write("=" * 45 + "\n")
        file.write(f"Articles processed: {len(results)}\n\n")

        file.write("DRUG MENTIONS\n")
        for drug, count in drug_counts.most_common():
            file.write(f"{drug}: {count}\n")

        file.write("\nOUTCOME MENTIONS\n")
        for outcome, count in outcome_counts.most_common():
            file.write(f"{outcome}: {count}\n")

    print("PHARMACEUTICAL EVIDENCE EXTRACTION")
    print("=" * 45)
    print("Articles processed:", len(results))

    print("\nDRUG MENTIONS")
    for drug, count in drug_counts.most_common():
        print(f"{drug}: {count}")

    print("\nOUTCOME MENTIONS")
    for outcome, count in outcome_counts.most_common():
        print(f"{outcome}: {count}")

    print("\nSUCCESS!")
    print("Evidence matrix:", OUTPUT_FILE)
    print("Extraction report:", REPORT_FILE)
    print("\nNOTE: Mentions do not prove treatment effects.")


if __name__ == "__main__":
    main()
