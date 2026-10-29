"""Combine the Zotero and OpenAlex data into dashboard/data.json.

Run from the top folder of the repository: python scripts/build_dashboard_data.py

Each paper appears once, even when:
  - the same DOI is entered in several Zotero items (e.g. filed in two folders), or
  - a preprint and its published version have different DOIs but OpenAlex treats them as one work.
Every paper keeps all its Zotero item types and folders, so the dashboard can filter on them.
"""
import csv
import datetime
import json
import os


def read(path):
    with open(path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


zotero = read("data/zotero_items.csv")
citations = read("data/citations.csv")
by_year_rows = read("data/citations_by_year.csv")
history_rows = read("data/citations_history.csv")

# DOIs are case-insensitive, and Zotero and OpenAlex don't always agree on case.
zotero_by_doi = {}
for item in zotero:
    if item["doi"]:
        zotero_by_doi.setdefault(item["doi"].lower(), []).append(item)

# Group DOIs into works: same OpenAlex ID = same work.
works = {}
for row in citations:
    doi = row["doi"].lower()
    key = row["openalex_id"] or "doi:" + doi  # DOIs not found on OpenAlex stay on their own
    work = works.setdefault(key, {"dois": [], "openalex": [], "items": []})
    work["dois"].append(doi)
    work["openalex"].append(row)
    work["items"] += zotero_by_doi.get(doi, [])

by_year = {}
for row in by_year_rows:
    by_year.setdefault(row["doi"].lower(), {})[row["year"]] = number(row["cited_by_count"])

dates = sorted({row["date"] for row in history_rows})
history = {}
for row in history_rows:
    history.setdefault(row["doi"].lower(), {})[row["date"]] = number(row["cited_by_count"])

PREFERRED_TYPES = ["journalArticle", "book", "bookSection", "thesis", "conferencePaper", "report"]


def best_item(items):
    """Prefer the published version's Zotero record for title, authors and journal."""
    ranked = sorted(items, key=lambda i: PREFERRED_TYPES.index(i["item_type"])
                    if i["item_type"] in PREFERRED_TYPES else len(PREFERRED_TYPES))
    return ranked[0] if ranked else {}


papers = []
for key, work in works.items():
    found = [r for r in work["openalex"] if r["status"] == "ok"]
    main = max(found, key=lambda r: number(r["cited_by_count"])) if found else None
    item = best_item(work["items"])
    doi_for_counts = main["doi"].lower() if main else work["dois"][0]
    papers.append({
        "openalex_id": main["openalex_id"] if main else "",
        "dois": work["dois"],
        "title": item.get("title") or (main["title"] if main else ""),
        "authors": item.get("authors", ""),
        # Many Zotero items have no date, so fall back to OpenAlex's publication year.
        "year": number(item.get("year")) or (number(main["year"]) if main else 0) or None,
        "venue": item.get("venue", ""),
        "types": sorted({i["item_type"] for i in work["items"]}),
        "folders": sorted({f for i in work["items"] for f in i["folders"].split("; ") if f}),
        "found": main is not None,
        "citations": number(main["cited_by_count"]) if main else None,
        "by_year": by_year.get(doi_for_counts, {}),
        # One number per date in "dates": the highest count among this work's DOIs.
        "history": [max((history.get(d, {}).get(date) for d in work["dois"]
                         if date in history.get(d, {})), default=None) for date in dates],
    })

papers.sort(key=lambda p: -(p["citations"] or -1))
updated = dates[-1] if dates else datetime.date.today().isoformat()

os.makedirs("dashboard", exist_ok=True)
with open("dashboard/data.json", "w", encoding="utf-8") as file:
    json.dump({
        "updated": updated,
        "current_year": int(updated[:4]),
        "dates": dates,
        "items_without_doi": sum(1 for i in zotero if not i["doi"]),
        "papers": papers,
    }, file, ensure_ascii=False, separators=(",", ":"))

total = sum(p["citations"] or 0 for p in papers)
print(f"{len(citations)} DOIs -> {len(papers)} papers, {total} citations (each OpenAlex work counted once)")
