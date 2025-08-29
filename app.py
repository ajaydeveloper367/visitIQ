import streamlit as st
import pandas as pd
from src.prioritizer import rag_prioritize, build_vectorstore_from_csv
from src.optimizer import optimize_allocation

st.set_page_config(page_title='Visit Prioritization Demo', layout='wide')
st.title('Visit Prioritization — Demo (Diabetic Patients)')

st.markdown('Upload a CSV of patient records or use the sample provided.')

uploaded = st.file_uploader('Upload patients CSV', type=['csv'])
if uploaded is not None:
    df = pd.read_csv(uploaded)
else:
    df = pd.read_csv('data/patients.csv')
    st.info('Loaded sample patient dataset (data/patients.csv)')

st.dataframe(df)

st.sidebar.header('Options')
build_vs = st.sidebar.button('Build/Refresh Vectorstore')
if build_vs:
    with st.spinner('Building embeddings and vectorstore...'):
        build_vectorstore_from_csv('data/patients.csv', persist_directory='chroma_db')
        st.success('Vectorstore built.')

st.sidebar.header('Views')
view = st.sidebar.radio('Choose view', ['Prioritization', 'Resource Allocation'])

if view == 'Prioritization':
    st.subheader('Prioritization')
    n_show = st.sidebar.slider('Show top N by priority (0 = show all)', 0, 10, 0)

    # Compute priorities
    results = []
    for _, row in df.iterrows():
        r = rag_prioritize(row)
        res = {
            'patient_id': row['patient_id'],
            'name': row['name'],
            'priority': r.get('priority_level','Unknown'),
            'score': r.get('score', 0),
            'reasons': '; '.join(r.get('reasons', [])) if isinstance(r.get('reasons', []), list) else str(r.get('reasons',''))
        }
        results.append(res)

    res_df = pd.DataFrame(results)
    priority_order = {'Emergency':0, 'High':1, 'Medium':2, 'Low':3, 'Unknown':4}
    res_df['order'] = res_df['priority'].map(priority_order).fillna(10)
    
    # Ensure score is numeric and handle None values
    res_df['score'] = pd.to_numeric(res_df['score'], errors='coerce').fillna(0)
    
    # Sort by priority order (ascending), then by score (descending for higher priority first)
    res_df = res_df.sort_values(['order','score'], ascending=[True, False])

    if n_show > 0:
        res_df = res_df.head(n_show)

    st.table(res_df[['patient_id','name','priority','score','reasons']])
else:
    st.subheader('Resource Allocation')
    partners = pd.read_csv('data/partners.csv')
    st.markdown('### Partners / Capacities')
    st.dataframe(partners)

    st.markdown('### Current patient priorities (computed via RAG)')
    # compute priorities
    patients = []
    for _, row in df.iterrows():
        r = rag_prioritize(row)
        priority_level = r.get('priority_level','Low')
        patients.append({
            'patient_id': int(row['patient_id']),
            'name': row['name'],
            'priority_level': priority_level,
            'score': r.get('score', 0),  # Include score for better visibility
            # Enhanced demand calculation based on priority and vitals
            'demand_icu': 1 if priority_level == 'Emergency' else 0,
            'demand_general': 1,
            'nurse_need': 2 if priority_level in ['Emergency', 'High'] else 1
        })
    st.dataframe(pd.DataFrame(patients))

    st.markdown('### Compute optimal assignment given capacities')
    if st.button('Run Optimizer'):
        assigns = optimize_allocation(patients, partners.to_dict(orient='records'))
        if assigns:
            st.success('Assignments computed')
            st.dataframe(pd.DataFrame(assigns))
        else:
            st.warning('No feasible assignments found (check capacities).')