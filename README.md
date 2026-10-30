# ODISSEI citations tracker (PROTOTYPE)

This repository tracks publications linked to [ODISSEI](https://odissei-data.nl) and the citations they receive. It reads the list of publications from the ODISSEI Zotero group library, looks up their citation counts on [OpenAlex](https://openalex.org), and publishes the results as a dashboard:

**Dashboard: https://angelicamaineri.github.io/odissei-citations-tracker/**

Everything runs automatically on GitHub every Monday. Each run saves the latest numbers in this repository, so the repository's history is also a record of how citations have grown over time.

## How it works

Every Monday at 06:00 UTC, the workflow in `.github/workflows/update-citations.yml` runs four steps:

1. **Read the publications from Zotero.** `scripts/fetch_zotero.py` reads every item in the tracked Zotero folder and all of its subfolders. It collects each item's DOI, looking in the DOI field, the Extra field and the URL, and writes the DOIs to `data/dois.txt`. Items without a DOI are listed in `data/zotero_missing_doi.csv`.
2. **Look up citations on OpenAlex.** `scripts/fetch_citations.py` looks up each DOI on OpenAlex and records its citation count and its citations per year. It also adds that day's counts to `data/citations_history.csv`.
3. **Prepare the dashboard data.** `scripts/build_dashboard_data.py` combines the Zotero and OpenAlex data into `dashboard/data.json`, with one entry per publication.
4. **Save and publish.** The workflow commits the updated files to the repository and publishes the `dashboard` folder on GitHub Pages.

## What's in the repository

| Path | Contents |
|---|---|
| `scripts/fetch_zotero.py` | Reads the publications from Zotero |
| `scripts/fetch_citations.py` | Looks up citation counts on OpenAlex |
| `scripts/build_dashboard_data.py` | Prepares the data for the dashboard |
| `dashboard/index.html` | The dashboard page |
| `dashboard/data.json` | The dashboard's data, rebuilt on every run |
| `.github/workflows/update-citations.yml` | The workflow that runs everything |
| `requirements.txt` | The Python package the scripts need (`requests`) |

### Data files

All data files are rewritten on every run, except `citations_history.csv`, which grows.

| File | One row per | Contents |
|---|---|---|
| `data/zotero_items.csv` | Zotero item | DOI, item type, title, authors, year, journal, and the Zotero folders the item is filed in |
| `data/zotero_missing_doi.csv` | Zotero item without a DOI | Items that can't be tracked until a DOI is added in Zotero |
| `data/dois.txt` | DOI | The unique DOIs read from Zotero |
| `data/citations.csv` | DOI | OpenAlex ID, title, publication year, total citations, and whether OpenAlex found the DOI |
| `data/citations_by_year.csv` | DOI and year | Citations received in each calendar year |
| `data/citations_history.csv` | DOI and run date | Total citations on each date the tracker ran |

## The dashboard

The dashboard shows the total number of publications and citations, citations per year with a running total, the growth in total citations across weekly runs, publications per year, the most cited publications, and a searchable list of all publications.

The **item type** and **Zotero folder** filters apply to everything on the page. Clicking a filter shows only that type or folder; clicking others adds them to the selection.

## How publications are counted

- **Each publication counts once.** A DOI entered in several Zotero items, for example in two folders, is counted once. A preprint and its published version are also counted once when OpenAlex treats them as the same work, even if they have different DOIs.
- **Citations come from OpenAlex.** OpenAlex counts usually differ from Google Scholar, which is typically higher, and from Scopus or Web of Science.
- **Citations per year cover recent years only.** OpenAlex reports citations per year for roughly the last ten years. Older citations are included in the totals and in the starting point of the running-total line.
- **Publication year.** The year comes from Zotero. If the Zotero item has no date, the publication year from OpenAlex is used.
- **Items without a DOI aren't tracked.** They're listed in `data/zotero_missing_doi.csv`.

## Maintaining the tracker

**Adding a publication.** Add it to the tracked Zotero folder, or one of its subfolders, with its DOI. It's picked up on the next run.

**Removing a publication.** Remove it from the tracked folder in Zotero. It disappears from the dashboard on the next run, but its earlier counts remain in `citations_history.csv`.

**Fixing items without a DOI.** Check `data/zotero_missing_doi.csv` from time to time, and add DOIs in Zotero where they exist. For item types without a DOI field, such as preprints and reports, you can put `DOI: 10.xxxx/...` in the Extra field.

**Running an update right away.** Go to the *Actions* tab, choose *Update citations*, and click *Run workflow*. Do this after editing `dashboard/index.html` too, so the change is published.

**Checking a run.** Each run's log shows which Zotero folders were read, how many items have a DOI, and any DOIs OpenAlex couldn't find. A red cross in the *Actions* tab means a run failed; open it to see which step stopped.

## Setup

These settings are already in place. They're documented here in case the repository is copied or something needs to change.

### Repository settings

Under *Settings → Secrets and variables → Actions*:

| Kind | Name | Value |
|---|---|---|
| Secret | `ZOTERO_API_KEY` | A Zotero API key with read-only access to the ODISSEI group |
| Variable | `ZOTERO_LIBRARY_ID` | `4530732`, the ODISSEI group library |
| Variable | `ZOTERO_LIBRARY_TYPE` | `group` |
| Variable | `ZOTERO_COLLECTION_KEY` | The key of the tracked Zotero folder, currently `QBDS8NIB`. Its subfolders are included. |

The optional variable `ZOTERO_ITEM_TYPES`, a comma-separated list such as `journalArticle,book`, restricts tracking to those Zotero item types. It isn't set, so all types are tracked and filtering happens on the dashboard instead.

Under *Settings → Pages*, *Source* is set to **GitHub Actions**.

### Zotero API key

Create keys at [zotero.org/settings/keys](https://www.zotero.org/settings/keys). The key needs read-only access to the ODISSEI group. Under *Default Group Permissions*, choose *Read Only*, or give the group read access specifically. If the key is replaced, update the `ZOTERO_API_KEY` secret.

### Changing the tracked Zotero folder

Open the folder in the Zotero web library. Its key is the eight characters after `/collections/` in the address. Put that key in the `ZOTERO_COLLECTION_KEY` variable.

### OpenAlex

`scripts/fetch_citations.py` includes a contact email in its requests to OpenAlex, as OpenAlex asks. To change it, edit the `MAILTO` line at the top of the script.

## Running the scripts on your own computer

You need Python 3 and the `requests` package (`pip install -r requirements.txt`). From the top folder of the repository:

```bash
export ZOTERO_LIBRARY_ID=4530732 ZOTERO_LIBRARY_TYPE=group ZOTERO_COLLECTION_KEY=QBDS8NIB ZOTERO_API_KEY=your-key
python scripts/fetch_zotero.py
python scripts/fetch_citations.py
python scripts/build_dashboard_data.py
python -m http.server -d dashboard 8000
```

Then open http://localhost:8000 to see the dashboard. On Windows, set the variables with `set NAME=value` instead of `export`.

## License

GNU General Public License v2.0. See [LICENSE](LICENSE).
