"""Look up each DOI in dois.txt on OpenAlex and save the results.

Writes two files:
  citations.csv          one row per DOI: title, year, citations, and whether it was found
  citations_by_year.csv  one row per DOI per year: citations received that year
"""
import csv
import time

import requests

# Put your email here: OpenAlex answers faster and more reliably when you identify yourself.
MAILTO = "angelica@odissei-data.nl"

# Read the DOIs, ignoring blank lines and stray spaces or tabs.
with open("data/dois.txt") as file:
    dois = [line.strip() for line in file if line.strip()]

papers = []
cites_by_year = []

for doi in dois:
    row = {"doi": doi, "status": "", "openalex_id": "", "title": "", "year": "", "cited_by_count": ""}
    try:
        response = requests.get(
            "https://api.openalex.org/works/https://doi.org/" + doi,
            params={"mailto": MAILTO},
            timeout=30,
        )
        if response.status_code == 404:
            row["status"] = "not found on OpenAlex"
        else:
            response.raise_for_status()
            result = response.json()
            row["status"] = "ok"
            row["openalex_id"] = result["id"].replace("https://openalex.org/", "")
            row["title"] = result["display_name"]
            row["year"] = result["publication_year"]
            row["cited_by_count"] = result["cited_by_count"]
            for cby in result["counts_by_year"]:
                cites_by_year.append({"doi": doi, "year": cby["year"], "cited_by_count": cby["cited_by_count"]})
    except Exception as error:
        row["status"] = f"error: {error}"
    papers.append(row)
    time.sleep(0.1)  # stay well under OpenAlex's limit of 10 requests per second

with open("data/citations.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=list(papers[0].keys()))
    writer.writeheader()
    writer.writerows(papers)

with open("data/citations_by_year.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["doi", "year", "cited_by_count"])
    writer.writeheader()
    writer.writerows(cites_by_year)

# Summary, so problems are visible straight away.
found = [p for p in papers if p["status"] == "ok"]
print(f"{len(found)} of {len(papers)} DOIs found, {sum(p['cited_by_count'] for p in found)} citations in total")
for p in papers:
    if p["status"] != "ok":
        print(f"  {p['doi']}: {p['status']}")
