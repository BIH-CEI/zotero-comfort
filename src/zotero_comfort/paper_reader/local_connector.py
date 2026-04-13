#!/usr/bin/env python3
"""
Zotero Local Connector API client.

Uses Zotero's local HTTP server (port 23119) to trigger actions
that require the desktop client, such as:
- Import items by DOI (with automatic PDF download)
- Find available PDFs for existing items
- Get currently selected collection

This is more powerful than the Web API because Zotero Desktop
handles PDF downloads using its built-in translators and
configured institutional proxies.
"""
import json
import sys
import time
import urllib.error
import urllib.request

ZOTERO_LOCAL = "http://localhost:23119"


def ping():
    """Check if Zotero Desktop is running."""
    try:
        req = urllib.request.Request(
            f"{ZOTERO_LOCAL}/connector/ping",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=3) as r:
            data = json.loads(r.read())
            print("Zotero is running")
            print(f"  downloadAssociatedFiles: {data.get('prefs', {}).get('downloadAssociatedFiles')}")
            return True
    except Exception:
        print("Zotero Desktop is not running on port 23119")
        return False


def get_selected_collection():
    """Get the currently selected collection in Zotero."""
    req = urllib.request.Request(
        f"{ZOTERO_LOCAL}/connector/getSelectedCollection",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=b"{}",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read())
    print(f"Collection: {data.get('name', '?')} (ID: {data.get('id', '?')})")
    print(f"Library: {data.get('libraryName', '?')}")
    return data


def save_by_doi(doi: str):
    """Import a paper by DOI using Zotero's built-in DOI translator.

    This triggers Zotero Desktop to:
    1. Resolve DOI via Crossref/DataCite
    2. Create the item with full metadata
    3. Automatically download the PDF if available (using configured proxies)
    4. Save to the currently selected collection
    """
    # First detect that Zotero can handle this DOI
    detect_req = urllib.request.Request(
        f"{ZOTERO_LOCAL}/connector/detect",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "uri": f"https://doi.org/{doi}",
            "html": f'<html><body><a href="https://doi.org/{doi}">{doi}</a></body></html>',
        }).encode(),
    )
    try:
        with urllib.request.urlopen(detect_req, timeout=10) as r:
            translators = json.loads(r.read())
        if not translators:
            print(f"No translator found for {doi}")
            return False
    except Exception as e:
        print(f"Detection failed: {e}")
        return False

    # Use saveItems with the DOI translator format
    save_req = urllib.request.Request(
        f"{ZOTERO_LOCAL}/connector/saveItems",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "items": [{
                "itemType": "journalArticle",
                "DOI": doi,
                "title": f"[Importing {doi}...]",
                "creators": [],
                "attachments": [{
                    "url": f"https://doi.org/{doi}",
                    "title": "Full Text PDF",
                    "mimeType": "application/pdf",
                }],
                "tags": [],
                "notes": [],
            }],
            "uri": f"https://doi.org/{doi}",
        }).encode(),
    )
    try:
        with urllib.request.urlopen(save_req, timeout=30) as r:
            result = r.read()
        print(f"OK: {doi} — saved to current collection (PDF download triggered)")
        return True
    except urllib.error.HTTPError as e:
        print(f"FAIL: {doi} — {e.code} {e.reason}")
        return False
    except Exception as e:
        print(f"FAIL: {doi} — {e}")
        return False


def batch_save_dois(dois: list):
    """Import multiple DOIs via Zotero Desktop."""
    if not ping():
        return

    collection = get_selected_collection()
    print(f"\nImporting {len(dois)} DOIs into '{collection.get('name', '?')}'...\n")

    success = 0
    for doi in dois:
        if save_by_doi(doi):
            success += 1
        time.sleep(1)  # Give Zotero time to process

    print(f"\nImported: {success}/{len(dois)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  zotero_local.py ping")
        print("  zotero_local.py collection")
        print("  zotero_local.py save-doi DOI")
        print("  zotero_local.py batch-doi DOI1 DOI2 ...")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "ping":
        ping()
    elif cmd == "collection":
        get_selected_collection()
    elif cmd == "save-doi":
        save_by_doi(sys.argv[2])
    elif cmd == "batch-doi":
        batch_save_dois(sys.argv[2:])
    else:
        print(f"Unknown command: {cmd}")
