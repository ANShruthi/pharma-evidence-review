
import csv
from pathlib import Path
from collections import Counter

# Your project location
PROJECT = Path(__file__).resolve().parent

INPUT_FILE = PROJECT / "data" / "raw" / "pubmed_articles.csv"
OUTPUT_DIR = PROJECT / "data" / "processed"
REPORT_DIR = PROJECT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def classify_article(title, abstract):
    """Preliminary keyword-based classification; not verified study design."""
    text = (title + " " + abstract).lower()

    if any(word in text for word in [
        "systematic review", "meta-analysis", "meta analysis"
    ]):
        return "Possible systematic review/meta-analysis"

    if any(word in text for word in [
        "randomized controlled trial",
        "randomised controlled trial",
        "randomized trial",
        "randomised trial"
    ]):
        return "Possible randomized clinical trial"

    if any(word in text for word in [
        "retrospective cohort",
        "prospective cohort",
        "observational study",
        "real-world evidence",
        "real-world study",
        "claims database"
    ]):
        return "Possible observational/RWE study"

    if "review" in title.lower():
        return "Possible narrative review"

    return "Unclassified - manual review needed"


def main():
    if not INPUT_FILE.exists():
        print("ERROR: PubMed CSV file not found.")
        print(INPUT_FILE)
        return

    with INPUT_FILE.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        articles = list(csv.DictReader(file))

    if not articles:
        print("ERROR: The CSV file contains no articles.")
        return

    print("PHARMACEUTICAL EVIDENCE ANALYSIS")
    print("=" * 45)
    print("Total articles:", len(articles))

    results = []
    missing_abstracts = 0
    seen_pmids = set()
    duplicate_pmids = 0

    for article in articles:
        pmid = article.get("PMID", "").strip()
        title = article.get("Title", "").strip()
        abstract = article.get("Abstract", "").strip()

        if not abstract:
            missing_abstracts += 1

        if pmid in seen_pmids:
            duplicate_pmids += 1
        else:
            seen_pmids.add(pmid)

        category = classify_article(title, abstract)

        results.append({
            **article,
            "Preliminary_Study_Type": category,
            "Needs_Manual_Review": "Yes"
        })

    category_counts = Counter(
        row["Preliminary_Study_Type"]
        for row in results
    )

    output_file = OUTPUT_DIR / "classified_articles.csv"

    columns = list(results[0].keys())

    with output_file.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=columns
        )
        writer.writeheader()
        writer.writerows(results)

    report_file = REPORT_DIR / "evidence_summary.txt"

    with report_file.open("w", encoding="utf-8") as file:
        file.write("PHARMACEUTICAL EVIDENCE SUMMARY\n")
        file.write("=" * 45 + "\n")
        file.write(f"Total articles: {len(articles)}\n")
        file.write(f"Missing abstracts: {missing_abstracts}\n")
        file.write(f"Duplicate PMIDs: {duplicate_pmids}\n\n")
        file.write("Preliminary study categories:\n")

        for category, count in category_counts.items():
            file.write(f"{category}: {count}\n")

    print("\nDATA QUALITY")
    print("Missing abstracts:", missing_abstracts)
    print("Duplicate PMIDs:", duplicate_pmids)

    print("\nPRELIMINARY STUDY CLASSIFICATION")
    for category, count in category_counts.items():
        print(f"{category}: {count}")

    print("\nSUCCESS!")
    print("Classified articles:", output_file)
    print("Summary report:", report_file)
    print("\nNOTE: Categories are keyword-based and require manual verification.")


if __name__ == "__main__":
    main()
