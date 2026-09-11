# Crowdsourced Protein CCS Database

This is Streamlit web application for logging protein CCS values from literature. The aim is not for this database to be a collection of 'perfect' native CCS values, but to represent the full spread of reported CCS values across drift gases, IMS types and experimental conditions.

Generally, this tool is intended to be used as and when users come across CCS values in the literature, i.e. when you see a paper with a CCS value for a biomacromolecule, log it. Users can add papers that are not yet in the database. To speed things up in the early stages, a database of papers in the field of native ion mobility mass spectrometry is also provided (`native_IM_MS_papers_20251215.csv`). Users can select a paper at random to log.

There is a list of approved email addresses stored in Streamlit secrets - if you would like to be added to the list please contact me at ana.bathalen@manchester.ac.uk or Perdi at perdita.barran@manchester.ac.uk. Accounts are created when an approved email signs in and chooses a nickname.

## Tests

Run:

```bash
python -m unittest discover -s tests
```
