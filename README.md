Pharmaceutical Evidence Review Dashboard
Overview
A Python and Streamlit portfolio project exploring published evidence on SGLT2 inhibitors in type 2 diabetes using PubMed records.
The project demonstrates literature retrieval, preliminary study classification, keyword-based evidence extraction, and interactive evidence exploration.
Current Features
• PubMed literature dataset containing 50 articles
• Preliminary classification of study designs
• Identification of drug, population, and clinical outcome mentions
• Interactive Streamlit dashboard
• Article search and filtering
• Downloadable evidence matrix
Data Source
PubMed, accessed through the National Center for Biotechnology Information (NCBI).
https://pubmed.ncbi.nlm.nih.gov/
Methods and Limitations
Study classifications are generated using keyword-based rules and require manual verification.
Drug and outcome mentions do not establish clinical effectiveness, comparative treatment effects, or causality.
The current version does not perform validated AI-based extraction, systematic review screening, meta-analysis, or health economic modeling.
Technology
• Python
• Pandas
• Streamlit
• PubMed E-utilities
Run Locally
Install dependencies:
pip install -r requirements.txt
Launch the dashboard:
streamlit run app.py
Project Status
Exploratory evidence review and visualization prototype. Further work will focus on structured evidence extraction, human validation, and HEOR-relevant research applications.
Disclaimer
This project is intended for research demonstration and professional portfolio purposes. It is not a clinical decision-support tool. The dataset and automated classifications should be independently verified before research or clinical use.

