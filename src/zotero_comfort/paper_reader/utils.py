#!/usr/bin/env python3
"""Zotero utility functions for paper-reader skill."""
import json
import os
import sys
import time
import urllib.request
import urllib.parse

KEY = "ojPdCIX7AZFczh3zR1WSEYTD"
USER = "14728954"
API_BASE = f"https://api.zotero.org/users/{USER}"
ZOTERO_STORAGE = os.path.expanduser("~/Zotero/storage")


def _api(endpoint, method="GET", data=None):
    """Make a Zotero API request."""
    url = f"{API_BASE}/{endpoint}"
    if "?" in url:
        url += f"&key={KEY}"
    else:
        url += f"?key={KEY}"
    headers = {"Zotero-API-Key": KEY, "Content-Type": "application/json"}
    req = urllib.request.Request(url, headers=headers, method=method)
    if data:
        req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def get_pdf_path(parent_key):
    """Get local PDF path for a Zotero item by its parent key."""
    children = _api(f"items/{parent_key}/children?format=json")
    for c in children:
        if c["data"]["itemType"] == "attachment" and "pdf" in c["data"].get("contentType", "").lower():
            akey = c["key"]
            storage_dir = os.path.join(ZOTERO_STORAGE, akey)
            if os.path.exists(storage_dir):
                pdfs = [f for f in os.listdir(storage_dir) if f.endswith(".pdf")]
                if pdfs:
                    return os.path.join(storage_dir, pdfs[0])
    return None


def list_collection(collection_key):
    """List all items in a collection with PDF status."""
    items = _api(f"collections/{collection_key}/items?format=json&limit=100")
    parents = {}
    attachments = {}
    for i in items:
        if i["data"]["itemType"] == "note":
            continue
        if i["data"]["itemType"] == "attachment":
            parent = i["data"].get("parentItem", "")
            if parent:
                attachments[parent] = i["key"]
        else:
            parents[i["key"]] = i["data"].get("title", "")[:70]

    for pkey, title in parents.items():
        pdf_key = attachments.get(pkey, "NO_PDF")
        has_pdf = "PDF" if pdf_key != "NO_PDF" else "---"
        pdf_path = ""
        if pdf_key != "NO_PDF":
            path = os.path.join(ZOTERO_STORAGE, pdf_key)
            if os.path.exists(path):
                pdfs = [f for f in os.listdir(path) if f.endswith(".pdf")]
                pdf_path = os.path.join(path, pdfs[0]) if pdfs else "MISSING_LOCAL"
            else:
                pdf_path = "MISSING_LOCAL"
        print(f"{pkey}|{has_pdf}|{title}")


def post_note(parent_key, html_content, tags=None):
    """Create a child note on a Zotero item."""
    tags = tags or [{"tag": "cross-references"}]
    result = _api("items", method="POST", data=[{
        "itemType": "note",
        "parentItem": parent_key,
        "note": html_content,
        "tags": tags,
    }])
    if result.get("successful"):
        key = list(result["successful"].values())[0].get("key", "?")
        print(f"OK: {parent_key} -> note {key}")
    else:
        print(f"FAIL: {parent_key} -> {result.get('failed', {})}")
    return result


def import_doi(doi, collection_key):
    """Import a paper by DOI into a Zotero collection via Crossref."""
    crossref_url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(crossref_url, headers={"User-Agent": "paper-reader/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        meta = json.loads(r.read())["message"]

    item = {
        "itemType": "journalArticle",
        "title": meta.get("title", [""])[0] if meta.get("title") else "",
        "creators": [
            {"creatorType": "author", "firstName": a.get("given", ""), "lastName": a.get("family", "")}
            for a in meta.get("author", [])
        ],
        "publicationTitle": meta.get("container-title", [""])[0] if meta.get("container-title") else "",
        "volume": str(meta.get("volume", "")),
        "issue": str(meta.get("issue", "")),
        "pages": meta.get("page", ""),
        "date": str(meta.get("issued", {}).get("date-parts", [[""]])[0][0]),
        "DOI": meta.get("DOI", ""),
        "url": f"https://doi.org/{doi}",
        "collections": [collection_key],
    }

    result = _api("items", method="POST", data=[item])
    if result.get("successful"):
        print(f"OK: {doi}")
    else:
        print(f"FAIL: {doi} -> {result.get('failed', {})}")
    return result


def batch_import_dois(dois, collection_key):
    """Import multiple DOIs into a collection."""
    success = 0
    for doi in dois:
        try:
            import_doi(doi, collection_key)
            success += 1
        except Exception as e:
            print(f"ERR: {doi} -> {e}")
        time.sleep(0.1)
    print(f"\nImported {success}/{len(dois)}")


def create_collection(name, parent_key=None):
    """Create a new Zotero collection."""
    data = [{"name": name}]
    if parent_key:
        data[0]["parentCollection"] = parent_key
    result = _api("collections", method="POST", data=data)
    if result.get("successful"):
        key = list(result["successful"].values())[0].get("key", "?")
        print(f"Collection '{name}' created: {key}")
        return key
    else:
        print(f"FAIL: {result.get('failed', {})}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  zotero_utils.py list-collection COLLECTION_KEY")
        print("  zotero_utils.py pdf-path ITEM_KEY")
        print("  zotero_utils.py import-doi DOI COLLECTION_KEY")
        print("  zotero_utils.py create-collection NAME [PARENT_KEY]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list-collection":
        list_collection(sys.argv[2])
    elif cmd == "pdf-path":
        path = get_pdf_path(sys.argv[2])
        print(path or "NO_PDF")
    elif cmd == "import-doi":
        import_doi(sys.argv[2], sys.argv[3])
    elif cmd == "create-collection":
        parent = sys.argv[4] if len(sys.argv) > 4 else None
        create_collection(sys.argv[2], parent)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
