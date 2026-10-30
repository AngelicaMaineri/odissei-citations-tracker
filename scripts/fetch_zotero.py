"""Read the ODISSEI papers from Zotero and write their DOIs to data/dois.txt.

Run from the top folder of the repository: python scripts/fetch_zotero.py

Settings come from environment variables (set in GitHub under Settings -> Secrets and variables):
  ZOTERO_LIBRARY_ID      e.g. 4530732
  ZOTERO_LIBRARY_TYPE    "group" or "user"
  ZOTERO_COLLECTION_KEY  optional, e.g. HG37SSWU; its subcollections are included too
                         (leave empty to read the whole library)
  ZOTERO_API_KEY         optional for public libraries, needed for private ones
  ZOTERO_ITEM_TYPES      optional, e.g. journalArticle,thesis,book (leave empty to keep every type)

Writes three files:
  data/dois.txt                 one DOI per line, used by fetch_citations.py
  data/zotero_items.csv         every item: DOI, item type, title, authors, year, journal, folders
  data/zotero_missing_doi.csv   Zotero items without a DOI, so you can fix them in Zotero
"""
import csv
import os
import re
import sys

import requests

LIBRARY_ID = os.environ.get("ZOTERO_LIBRARY_ID", "")
LIBRARY_TYPE = os.environ.get("ZOTERO_LIBRARY_TYPE") or "group"
COLLECTION_KEY = os.environ.get("ZOTERO_COLLECTION_KEY", "")
API_KEY = os.environ.get("ZOTERO_API_KEY", "")
ITEM_TYPES = {t.strip() for t in os.environ.get("ZOTERO_ITEM_TYPES", "").split(",") if t.strip()}

if not LIBRARY_ID:
    sys.exit("ZOTERO_LIBRARY_ID is not set")

base = f"https://api.zotero.org/{LIBRARY_TYPE}s/{LIBRARY_ID}"
headers = {"Zotero-API-Version": "3"}
if API_KEY:
    headers["Zotero-API-Key"] = API_KEY


def get_all(url):
    """Zotero returns at most 100 results per request, so ask page by page."""
    results = []
    while True:
        response = requests.get(url, headers=headers, timeout=60,
                                params={"format": "json", "limit": 100, "start": len(results)})
        response.raise_for_status()
        page = response.json()
        results.extend(page)
        if len(page) < 100:
            return results


def collection_and_subcollections(key, name, depth=0):
    """Return [(key, name, depth)] for this collection and every subcollection below it."""
    found = [(key, name, depth)]
    for sub in get_all(f"{base}/collections/{key}/collections"):
        found += collection_and_subcollections(sub["key"], sub["data"]["name"], depth + 1)
    return found


items = {}  # keyed by Zotero item key, so an item filed in several folders counts once
folders = {}  # item key -> names of the folders it is filed in
if COLLECTION_KEY:
    response = requests.get(f"{base}/collections/{COLLECTION_KEY}", headers=headers, timeout=60)
    response.raise_for_status()
    top_name = response.json()["data"]["name"]
    print("Collections read:")
    for key, name, depth in collection_and_subcollections(COLLECTION_KEY, top_name):
        # "items/top" = the items in that folder, without their attachments and notes
        folder_items = get_all(f"{base}/collections/{key}/items/top")
        print(f"  {'  ' * depth}{name}: {len(folder_items)} items")
        for item in folder_items:
            items[item["key"]] = item
            folders.setdefault(item["key"], []).append(name)
else:
    for item in get_all(f"{base}/items/top"):
        items[item["key"]] = item
items = list(items.values())

DOI_PATTERN = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)


def find_doi(data):
    """Look for a DOI in the DOI field, then in Extra ("DOI: ..."), then in the URL."""
    candidates = [data.get("DOI", "")]
    candidates += [line for line in data.get("extra", "").splitlines() if line.lower().startswith("doi:")]
    if "doi.org" in data.get("url", ""):
        candidates.append(data["url"])
    for text in candidates:
        match = DOI_PATTERN.search(text or "")
        if match:
            return match.group(0).rstrip(".,;")
    return ""


def authors(creators):
    names = [c.get("lastName") or c.get("name") or "" for c in creators if c.get("creatorType") == "author"]
    names = [n for n in names if n]
    return f"{names[0]} et al." if len(names) > 3 else ", ".join(names)


VENUE_FIELDS = ("publicationTitle", "bookTitle", "proceedingsTitle", "university",
                "institution", "repository", "websiteTitle", "publisher")

dois, missing, seen, table = [], [], set(), []
kept_types, skipped_types = {}, {}
for item in items:
    data = item["data"]
    item_type = data.get("itemType", "")
    if item_type in ("attachment", "note", "annotation"):
        continue
    if ITEM_TYPES and item_type not in ITEM_TYPES:
        skipped_types[item_type] = skipped_types.get(item_type, 0) + 1
        continue
    kept_types[item_type] = kept_types.get(item_type, 0) + 1
    doi = find_doi(data)
    year = re.search(r"\b(19|20)\d{2}\b", data.get("date", ""))
    table.append({
        "zotero_key": data["key"],
        "doi": doi,
        "item_type": item_type,
        "title": data.get("title", ""),
        "authors": authors(data.get("creators", [])),
        "year": year.group(0) if year else "",
        "venue": next((data[f] for f in VENUE_FIELDS if data.get(f)), ""),
        "folders": "; ".join(folders.get(data["key"], [])),
    })
    if not doi:
        missing.append({"zotero_key": data["key"], "title": data.get("title", ""), "item_type": data.get("itemType", "")})
    elif doi.lower() not in seen:  # DOIs are case-insensitive; skip duplicates
        seen.add(doi.lower())
        dois.append(doi)

# Safety check: never replace the DOI list with an empty one because of a problem in Zotero.
if not dois:
    sys.exit(f"Zotero returned {len(items)} items but no DOIs; leaving data/dois.txt unchanged")

with open("data/dois.txt", "w", encoding="utf-8") as file:
    file.write("\n".join(dois) + "\n")

with open("data/zotero_items.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=list(table[0].keys()))
    writer.writeheader()
    writer.writerows(table)

with open("data/zotero_missing_doi.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["zotero_key", "title", "item_type"])
    writer.writeheader()
    writer.writerows(missing)

print("Item types kept:   " + ", ".join(f"{t} {n}" for t, n in sorted(kept_types.items())))
if skipped_types:
    print("Item types skipped: " + ", ".join(f"{t} {n}" for t, n in sorted(skipped_types.items())))
print(f"{sum(kept_types.values())} items kept: {len(dois)} with a DOI, {len(missing)} without")
for m in missing:
    print(f"  no DOI: {m['title'][:90]}")
