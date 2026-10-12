from pathlib import Path
from collections import Counter
import csv
import io
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import pandas as pd
import streamlit as st

from pathlib import Path

PROJECT = Path(__file__).resolve().parent
DATA_FILE = PROJECT / "evidence_matrix.csv"
st.set_page_config(page_title='Pharmaceutical Evidence Review', page_icon='💊', layout='wide')
st.sidebar.title('Pharma Evidence Platform')
page = st.sidebar.radio('Navigation', ['Evidence Dashboard', 'Literature Search', 'AI Evidence Extraction', 'HEOR Analytics'])
st.sidebar.divider()
st.sidebar.caption('SGLT2 Inhibitors | Type 2 Diabetes')

@st.cache_data

def load_data():
    if not DATA_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(DATA_FILE, dtype=str).fillna('')


def terms(text):
    return [x.strip() for x in str(text).split(';') if x.strip()]


def count_mentions(frame, field):
    counts = Counter()
    if field in frame:
        for value in frame[field]:
            counts.update(set(terms(value)))
    return pd.Series(dict(counts), dtype=int).sort_values(ascending=False)


def chart_counts(counts, empty_message='No mentions detected.'):
    if len(counts):
        st.bar_chart(counts)
    else:
        st.info(empty_message)


def downloadable_csv(frame, name, label='Download CSV'):
    st.download_button(label, frame.to_csv(index=False).encode('utf-8-sig'), file_name=name, mime='text/csv')


def pubmed_request(endpoint, params):
    url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/' + endpoint + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': 'PharmaEvidencePortfolio/1.0 (educational demo)'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()


def node_text(node):
    return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


@st.cache_data(ttl=3600, show_spinner=False)
def search_pubmed(query, limit):
    result = json.loads(pubmed_request('esearch.fcgi', {'db':'pubmed','term':query,'retmax':limit,'retmode':'json','sort':'relevance'}))
    ids = result.get('esearchresult', {}).get('idlist', [])
    rows = []
    if ids:
        root = ET.fromstring(pubmed_request('efetch.fcgi', {'db':'pubmed','id':','.join(ids),'retmode':'xml'}))
        for record in root.findall('.//PubmedArticle'):
            citation = record.find('MedlineCitation')
            if citation is None:
                continue
            article = citation.find('Article')
            if article is None:
                continue
            pmid = node_text(citation.find('PMID'))
            abstract = ' '.join(node_text(part) for part in article.findall('.//Abstract/AbstractText'))
            rows.append({'PMID':pmid,'Title':node_text(article.find('ArticleTitle')),
                         'Journal':node_text(article.find('Journal/Title')),
                         'Abstract':abstract,'PubMed_Link':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/'})
    return pd.DataFrame(rows, columns=['PMID','Title','Journal','Abstract','PubMed_Link']), int(result.get('esearchresult', {}).get('count', 0))


def preliminary_pico(text):
    if not text.strip():
        return {'Population':'Not available','Intervention':'Not available','Comparator':'Not established','Outcomes mentioned':'Not available','Effect estimate':'Not extracted','Verification':'Required'}
    lower = text.lower()
    population = []
    for name, phrases in {'Type 2 diabetes':['type 2 diabetes','t2dm','type ii diabetes'], 'Chronic kidney disease':['chronic kidney disease','ckd'], 'Heart failure':['heart failure','hfpef','hfref']}.items():
        if any(x in lower for x in phrases): population.append(name)
    drugs = [name for name in ['empagliflozin','dapagliflozin','canagliflozin','ertugliflozin'] if name in lower]
    outcomes = [name for name, phrases in {'HbA1c':['hba1c','glycated hemoglobin'], 'Heart failure':['heart failure'], 'Kidney outcomes':['renal','kidney','egfr','albuminuria'], 'Cardiovascular outcomes':['cardiovascular','stroke','myocardial infarction'], 'Adverse events':['adverse event','hypoglycemia','ketoacidosis']}.items() if any(x in lower for x in phrases)]
    return {'Population':'; '.join(population) or 'Not established', 'Intervention':'; '.join(drugs) or 'Not established',
            'Comparator':'Not established from keyword matching', 'Outcomes mentioned':'; '.join(outcomes) or 'Not detected',
            'Effect estimate':'Not extracted', 'Verification':'Required — keyword-based'}


def ai_extract(text, key):
    instructions = ('Extract only statements explicitly supported by the supplied scientific abstract. '
        'Return a JSON object with keys population, intervention, comparator, outcomes, effect_estimates, limitations. '
        'Each field must be a string; use "Not reported" when absent. '
        'Do not infer causal effects, study design, or numerical estimates. '
        'Do not fabricate citations. State when a conclusion requires full-text verification.')
    payload = {'model':'gpt-4.1-mini','instructions':instructions,'input':text,'text':{'format':{'type':'json_object'}}}
    req = urllib.request.Request('https://api.openai.com/v1/responses', data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read())
    pieces = [item.get('text','') for output in data.get('output',[]) for item in output.get('content',[]) if item.get('type') == 'output_text']
    if not pieces:
        raise ValueError('No text returned by the AI service.')
    return json.loads(''.join(pieces))


df = load_data()

if page == 'Evidence Dashboard':
    st.title('Pharmaceutical Evidence Review Dashboard')
    st.caption('SGLT2 Inhibitors in Type 2 Diabetes | PubMed Evidence')
    if df.empty:
        st.error('Evidence matrix not found. Upload evidence_matrix.csv to the repository root or data/processed/.')
        st.stop()
    c1,c2,c3 = st.columns(3)
    c1.metric('Total articles',len(df))
    c2.metric('Articles with abstracts',int(df.get('Abstract',pd.Series(['']*len(df))).astype(str).str.strip().ne('').sum()))
    c3.metric('Articles needing verification',int(df.get('Verified',pd.Series(['No']*len(df))).str.lower().ne('yes').sum()))
    st.subheader('Preliminary Study Classification')
    if 'Preliminary_Study_Type' in df:
        chart_counts(df['Preliminary_Study_Type'].value_counts())
    st.subheader('Clinical Outcome Mentions')
    chart_counts(count_mentions(df,'Outcome_Mentions'))
    st.subheader('Explore Research Articles')
    query = st.text_input('Search title, abstract, or drug')
    options = sorted(df['Preliminary_Study_Type'].unique()) if 'Preliminary_Study_Type' in df else []
    selected = st.multiselect('Preliminary study types',options,default=options)
    view = df[df['Preliminary_Study_Type'].isin(selected)].copy() if options else df.copy()
    if query:
        search_cols = [col for col in ['Title','Abstract','Drug_Mentions'] if col in view]
        mask = pd.Series(False,index=view.index)
        for col in search_cols:
            mask |= view[col].str.contains(query,case=False,regex=False,na=False)
        view = view[mask]
    st.write(f'Showing {len(view)} articles')
    columns = [col for col in ['PMID','Title','Preliminary_Study_Type','Drug_Mentions','Outcome_Mentions','Population_Mentions','PubMed_Link'] if col in view]
    st.dataframe(view[columns],width='stretch',hide_index=True)
    downloadable_csv(view,'filtered_pharma_evidence.csv','Download filtered evidence CSV')
    with st.expander('Methodology and limitations'):
        st.write('The current collection is a limited PubMed sample, not an exhaustive systematic review. Study designs are preliminary keyword-based labels; all require manual confirmation. Drug and outcome mentions are not treatment effects. Missing abstracts reduce extractability.')

elif page == 'Literature Search':
    st.title('Literature Search')
    st.caption('Live PubMed discovery using NCBI E-utilities; results are not automatically screened for eligibility.')
    with st.form('pubmed_search'):
        query = st.text_input('PubMed query',value='("SGLT2 inhibitors"[Title/Abstract] OR empagliflozin[Title/Abstract] OR dapagliflozin[Title/Abstract]) AND "type 2 diabetes"[Title/Abstract]')
        limit = st.slider('Maximum records to retrieve',5,100,25,5)
        submitted = st.form_submit_button('Search PubMed')
    if submitted:
        if not query.strip():
            st.warning('Enter a PubMed search query.')
        else:
            try:
                with st.spinner('Searching PubMed...'):
                    results, total = search_pubmed(query.strip(),limit)
                st.session_state['pubmed_results'] = results
                st.session_state['pubmed_total'] = total
            except Exception as exc:
                st.error(f'PubMed search failed: {exc}')
    if 'pubmed_results' in st.session_state:
        results = st.session_state['pubmed_results']
        st.metric('Total PubMed matches (not retrieved)',st.session_state['pubmed_total'])
        st.write(f'Retrieved {len(results)} records')
        st.dataframe(results[['PMID','Title','Journal','PubMed_Link']],width='stretch',hide_index=True)
        downloadable_csv(results,'pubmed_search_results.csv','Download retrieved PubMed records')
    st.info('PubMed results are a discovery set, not an eligible-study set. Search date, complete query, and inclusion criteria should be documented for research use.')

elif page == 'AI Evidence Extraction':
    st.title('AI Evidence Extraction')
    st.caption('Exploratory PICO extraction with source verification required.')
    st.info('The free baseline below uses transparent keyword rules, not AI. Optional AI extraction requires your own API key and explicit approval before sending text to an external service.')
    mode = st.radio('Extraction mode',['Local keyword-based PICO (no external transfer)','AI-assisted PICO (optional API)'])
    source = st.radio('Input source',['Paste abstract','Select saved article'])
    text = ''
    if source == 'Paste abstract':
        text = st.text_area('Abstract or study excerpt',height=210)
    elif not df.empty:
        choices = list(df.index)
        selected = st.selectbox('Select article',choices,format_func=lambda i: str(df.loc[i].get('Title','Article'))[:110])
        st.write('**PubMed:**',df.loc[selected].get('PubMed_Link',''))
        text = str(df.loc[selected].get('Abstract',''))
        if not text.strip():
            st.warning('This record has no abstract in the published dataset. Paste an excerpt instead.')
            text = st.text_area('Paste an excerpt for this article',height=170)
    else:
        st.warning('Evidence matrix not available. Paste an abstract instead.')
        text = st.text_area('Abstract or study excerpt',height=210)
    if mode.startswith('Local'):
        if st.button('Extract preliminary PICO'):
            if not text.strip(): st.warning('Provide an abstract or excerpt first.')
            else:
                st.table(pd.DataFrame(list(preliminary_pico(text).items()),columns=['Field','Preliminary extraction']))
                st.warning('Keyword matches are not validated PICO findings. Comparator and effect estimates require manual review.')
    else:
        key = st.text_input('OpenAI API key (not stored in the repository)',type='password')
        consent = st.checkbox('I confirm I have permission to send this text to an external AI service and understand API charges may apply.')
        if st.button('Run AI-assisted extraction'):
            if not text.strip(): st.warning('Provide an abstract or excerpt first.')
            elif not key.strip(): st.warning('Enter your API key.')
            elif not consent: st.warning('Explicit consent is required before sending text.')
            else:
                try:
                    with st.spinner('Extracting...'):
                        result = ai_extract(text,key.strip())
                    st.json(result)
                    st.download_button('Download AI extraction JSON',json.dumps(result,indent=2),file_name='pico_extraction.json',mime='application/json')
                    st.warning('AI output is unverified. Check every field and numeric estimate against the source before use.')
                except Exception as exc:
                    st.error(f'AI extraction failed: {exc}')
    st.caption('No clinical inference should be made from automated output alone.')

elif page == 'HEOR Analytics':
    st.title('HEOR Analytics & Evidence Gaps')
    st.caption('Descriptive evidence mapping, not cost-effectiveness modeling or a claims-based RWE study.')
    if df.empty:
        st.error('Evidence matrix not found.')
        st.stop()
    st.subheader('Evidence composition')
    if 'Preliminary_Study_Type' in df:
        chart_counts(df['Preliminary_Study_Type'].value_counts())
    left,right = st.columns(2)
    with left:
        st.subheader('Clinical outcome coverage')
        chart_counts(count_mentions(df,'Outcome_Mentions'))
    with right:
        st.subheader('Drug mention coverage')
        chart_counts(count_mentions(df,'Drug_Mentions'))
    st.subheader('HEOR-relevant evidence-gap signals')
    markers = {
        'Cost or economic terms':['cost','economic','budget impact','cost-effectiveness','payer'],
        'Healthcare utilization':['hospitalization','utilization','emergency department','resource use'],
        'Quality of life / PRO':['quality of life','patient-reported','eq-5d','utility'],
        'Real-world / observational terms':['real-world','observational','cohort','claims database'],
        'Comparative effectiveness terms':['comparative effectiveness','head-to-head','active comparator']
    }
    combined = (df.get('Title',pd.Series(['']*len(df))).astype(str) + ' ' + df.get('Abstract',pd.Series(['']*len(df))).astype(str)).str.lower()
    summary = []
    for label, keywords in markers.items():
        n = int(combined.apply(lambda t:any(re.search(r'(?<!\w)'+re.escape(word)+r'(?!\w)',t) for word in keywords)).sum())
        summary.append({'Research domain':label,'Articles with keyword mentions':n,'Articles without detected mentions':len(df)-n})
    gap = pd.DataFrame(summary)
    st.dataframe(gap,width='stretch',hide_index=True)
    downloadable_csv(gap,'heor_evidence_gap_signals.csv','Download evidence-gap summary')
    st.warning('These are exploratory keyword signals from the available titles and abstracts. A missing term does not establish an evidence gap. No cost, QALY, ICER, utilization rate, or comparative effectiveness estimate has been calculated.')
    st.subheader('Next-stage HEOR research questions')
    st.markdown('**Feasibility:** Which public or licensed RWD sources capture SGLT2 treatment, outcomes, utilization, and cost?\n\n**Comparative evidence:** Which populations and comparators have human-verified evidence?\n\n**Economic evidence:** Which studies report resource use, quality of life, or cost-effectiveness?')

st.sidebar.caption('Research prototype · Human verification required')
