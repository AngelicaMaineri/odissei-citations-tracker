"""Read the ODISSEi papers from Zotero and write their DOIs to data/dois.txt.

Run from the top folder of the repository: python scripts/fetch_zotero.py

Settings come from environment variables (set in GitHub under Settings -> Secrets and variables):
  ZOTERO_LIBRARY_ID      e.g. 4530732
  ZOTERO_LIBRARY_TYPE    "group" or "user"
  ZOTERO_COLLECTION_KEY  optional, e.g. HG37SSWU (leave empty to read the whole library)
  ZOTERO_API_KEY         optional for public libraries, needed for private ones

Writes two files:
  data/dois.txt                 one DOI per line, used by fetch_citations.py
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

if not LIBRARY_ID:
    sys.exit("ZOTERO_LIBRARY_ID is not set")

# "groups/4530732/collections/HG37SSWU/items/top" = the items in that collection,
# without their attachments and notes.
url = f"https://api.zotero.org/{LIBRARY_TYPE}s/{LIBRARY_ID}"
if COLLECTION_KEY:
    url += f"/collections/{COLLECTION_KEY}"
url += "/items/top"
headers = {"Zotero-API-Version": "3"}
if API_KEY:
    headers["Zotero-API-Key"] = API_KEY

# Zotero returns at most 100 items per request, so ask page by page.
items = []
while True:
    response = requests.get(url, headers=headers, timeout=60,
                            params={"format": "json", "limit": 100, "start": len(items)})
    response.raise_for_status()
    page = response.json()
    items.extend(page)
    if len(page) < 100:
        break

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


dois, missing, seen = [], [], set()
for item in items:
    data = item["data"]
    if data.get("itemType") in ("attachment", "note", "annotation"):
        continue
    doi = find_doi(data)
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

with open("data/zotero_missing_doi.csv", "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["zotero_key", "title", "item_type"])
    writer.writeheader()
    writer.writerows(missing)

print(f"{len(items)} items in Zotero: {len(dois)} with a DOI, {len(missing)} without")
for m in missing:
    print(f"  no DOI: {m['title'][:90]}")
