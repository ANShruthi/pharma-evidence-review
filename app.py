
from pathlib import Path
from collections import Counter

import pandas as pd
import streamlit as st

PROJECT = Path(__file__).resolve().parent
DATA_FILE = PROJECT / "data" / "processed" / "evidence_matrix.csv"

st.set_page_config(
    page_title="Pharmaceutical Evidence Review",
    page_icon="💊",
    layout="wide"
)
st.sidebar.title("Pharma Evidence Platform")

page = st.sidebar.radio(
    "Navigation",
    [
        "Evidence Dashboard",
        "Literature Search",
        "AI Evidence Extraction",
        "HEOR Analytics"
    ]
)

st.sidebar.divider()
st.sidebar.caption("SGLT2 Inhibitors | Type 2 Diabetes")
st.title("Pharmaceutical Evidence Review Dashboard")
st.caption("SGLT2 Inhibitors in Type 2 Diabetes | PubMed Evidence")

if not DATA_FILE.exists():
    st.error("Evidence matrix not found. Run extract_evidence.py first.")
    st.stop()

df = pd.read_csv(DATA_FILE).fillna("")

st.subheader("Evidence Overview")

col1, col2, col3 = st.columns(3)

col1.metric("Total Articles", len(df))
col2.metric(
    "Articles With Abstracts",
    (df["Abstract"].astype(str).str.strip() != "").sum()
)
col3.metric(
    "Articles Needing Review",
    (df["Verified"].astype(str).str.lower() != "yes").sum()
)

st.divider()

st.subheader("Preliminary Study Classification")

if "Preliminary_Study_Type" in df.columns:
    study_counts = df["Preliminary_Study_Type"].value_counts()
    st.bar_chart(study_counts)

st.subheader("Clinical Outcome Mentions")

outcome_counter = Counter()

for value in df["Outcome_Mentions"]:
    for outcome in str(value).split("; "):
        if outcome.strip():
            outcome_counter[outcome.strip()] += 1

if outcome_counter:
    outcome_df = pd.DataFrame(
        outcome_counter.items(),
        columns=["Outcome", "Articles"]
    ).set_index("Outcome")

    st.bar_chart(outcome_df)
else:
    st.info("No outcome mentions found.")

st.divider()

st.subheader("Explore Research Articles")

search = st.text_input(
    "Search by article title, abstract, or drug name"
)

study_types = sorted(
    df["Preliminary_Study_Type"].unique().tolist()
)

selected_types = st.multiselect(
    "Filter by preliminary study type",
    options=study_types,
    default=study_types
)

filtered = df[
    df["Preliminary_Study_Type"].isin(selected_types)
].copy()

if search:
    mask = (
        filtered["Title"].str.contains(
            search, case=False, regex=False, na=False
        )
        | filtered["Abstract"].str.contains(
            search, case=False, regex=False, na=False
        )
        | filtered["Drug_Mentions"].str.contains(
            search, case=False, regex=False, na=False
        )
    )
    filtered = filtered[mask]

st.write(f"Showing {len(filtered)} articles")

columns = [
    "PMID",
    "Title",
    "Preliminary_Study_Type",
    "Drug_Mentions",
    "Outcome_Mentions",
    "Population_Mentions",
    "PubMed_Link"
]

st.dataframe(filtered[columns], width="stretch", hide_index=True)

st.download_button(
    "Download Filtered Evidence CSV",
    data=filtered.to_csv(index=False).encode("utf-8-sig"),
    file_name="filtered_pharma_evidence.csv",
    mime="text/csv"
)

st.divider()

st.warning(
    "Study categories and evidence mentions are automated "
    "preliminary labels. They require scientific verification. "
    "Mention counts do not represent treatment effectiveness."
)
