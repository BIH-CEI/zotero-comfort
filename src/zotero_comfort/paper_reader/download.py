#!/usr/bin/env python3
"""
Download academic PDFs via hierarchical fallback strategy.

Strategy:
1. Unpaywall API (free OA versions)
2. PubMed Central (open access)
3. Direct DOI redirect (works on VPN)
4. Playwright headless browser (JS-heavy publishers, VPN required)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Optional

EMAIL = "thomas.debertshaeuser@bih-charite.de"
HEADERS = {"User-Agent": "paper-reader/1.0 (mailto:{})".format(EMAIL)}


def try_unpaywall(doi: str, output_dir: Path) -> Optional[str]:
    """Try Unpaywall API for open access PDF."""
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        # Check best OA location
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or best.get("url_for_landing_page")

        if not pdf_url:
            # Check all OA locations
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    pdf_url = loc["url_for_pdf"]
                    break

        if pdf_url and pdf_url.endswith(".pdf"):
            return _download_file(pdf_url, doi, output_dir, "unpaywall")
        elif pdf_url:
            # Try downloading even if URL doesn't end in .pdf
            return _download_file(pdf_url, doi, output_dir, "unpaywall")
    except Exception as e:
        print(f"  Unpaywall: {e}", file=sys.stderr)
    return None


def try_pmc(doi: str, output_dir: Path) -> Optional[str]:
    """Try PubMed Central for open access full text."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    try:
        # Search for DOI in PMC
        search_url = f"{base}/esearch.fcgi?db=pmc&term={urllib.parse.quote(doi)}[DOI]&retmode=json"
        req = urllib.request.Request(search_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        ids = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            # Try via PubMed -> PMC link
            pm_url = f"{base}/esearch.fcgi?db=pubmed&term={urllib.parse.quote(doi)}[DOI]&retmode=json"
            req = urllib.request.Request(pm_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as r:
                pm_data = json.loads(r.read())
            pm_ids = pm_data.get("esearchresult", {}).get("idlist", [])
            if pm_ids:
                link_url = f"{base}/elink.fcgi?dbfrom=pubmed&db=pmc&id={pm_ids[0]}&retmode=json"
                req = urllib.request.Request(link_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as r:
                    link_data = json.loads(r.read())
                for linkset in link_data.get("linksets", []):
                    for link_db in linkset.get("linksetdbs", []):
                        if link_db.get("dbto") == "pmc":
                            ids = [str(l["id"]) for l in link_db.get("links", [])]
                            break

        if not ids:
            return None

        pmc_id = ids[0]
        time.sleep(0.34)

        # Try PMC PDF endpoints
        pmc_urls = [
            f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/",
            f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/",
        ]
        for pmc_url in pmc_urls:
            result = _download_file(pmc_url, doi, output_dir, f"PMC{pmc_id}")
            if result:
                return result

    except Exception as e:
        print(f"  PMC: {e}", file=sys.stderr)
    return None


def try_doi_direct(doi: str, output_dir: Path) -> Optional[str]:
    """Try direct download via DOI redirect (works with VPN)."""
    doi_url = f"https://doi.org/{doi}"
    try:
        req = urllib.request.Request(doi_url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/pdf,*/*",
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")

            # Direct PDF response
            if "pdf" in content_type.lower():
                filepath = output_dir / _safe_filename(doi, "direct")
                with open(filepath, "wb") as f:
                    f.write(response.read())
                print(f"  Direct PDF: {filepath}")
                return str(filepath)

            # Try URL pattern transforms
            pdf_patterns = [
                final_url.replace("/abs/", "/pdf/"),
                final_url.replace("/article/", "/pdf/"),
                final_url + ".pdf",
                final_url.replace("html", "pdf"),
                final_url.replace("/full/", "/pdfdirect/"),
                final_url.replace("/article/", "/article/am-pdf/"),
            ]
            for pdf_url in pdf_patterns:
                if pdf_url == final_url:
                    continue
                result = _download_file(pdf_url, doi, output_dir, "direct")
                if result:
                    return result

    except Exception as e:
        print(f"  DOI direct: {e}", file=sys.stderr)
    return None


def try_playwright(doi: str, output_dir: Path) -> Optional[str]:
    """Try Playwright headless browser for JS-heavy publishers."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  Playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = context.new_page()

            # Navigate to DOI
            page.goto(f"https://doi.org/{doi}", wait_until="networkidle", timeout=30000)
            time.sleep(2)

            # Look for PDF download links
            pdf_links = page.query_selector_all('a[href*="pdf"], a[href*="PDF"]')
            for link in pdf_links:
                href = link.get_attribute("href")
                if href and ("pdf" in href.lower()):
                    # Make absolute URL
                    if href.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(page.url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"

                    # Try downloading via browser
                    with page.expect_download(timeout=15000) as download_info:
                        link.click()
                    download = download_info.value
                    filepath = output_dir / _safe_filename(doi, "playwright")
                    download.save_as(str(filepath))
                    print(f"  Playwright: {filepath}")
                    browser.close()
                    return str(filepath)

            browser.close()
    except Exception as e:
        print(f"  Playwright: {e}", file=sys.stderr)
    return None


def _download_file(url: str, doi: str, output_dir: Path, source: str) -> Optional[str]:
    """Download a file, verify it's a PDF."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/pdf,*/*",
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()

            # Verify it's actually a PDF
            if b"%PDF" in data[:1024] or "pdf" in content_type.lower():
                filepath = output_dir / _safe_filename(doi, source)
                with open(filepath, "wb") as f:
                    f.write(data)
                print(f"  {source}: {filepath}")
                return str(filepath)
    except Exception:
        pass
    return None


def _safe_filename(doi: str, suffix: str) -> str:
    """Create safe filename from DOI."""
    safe = doi.replace("/", "_").replace(".", "_")
    return f"{safe}_{suffix}.pdf"


def download(doi: str, output_dir: str = "./papers") -> Dict:
    """Download a paper PDF using hierarchical fallback strategy."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading: {doi}")

    strategies = [
        ("Unpaywall", try_unpaywall),
        ("PMC", try_pmc),
        ("DOI direct", try_doi_direct),
        ("Playwright", try_playwright),
    ]

    for name, fn in strategies:
        print(f"  Trying {name}...")
        result = fn(doi, out)
        if result:
            return {"doi": doi, "success": True, "method": name, "path": result}

    print(f"  FAILED: No method succeeded for {doi}")
    return {"doi": doi, "success": False, "method": None, "path": None}


def batch_download(dois: list, output_dir: str = "./papers") -> list:
    """Download multiple papers."""
    results = []
    success = 0
    for doi in dois:
        r = download(doi, output_dir)
        results.append(r)
        if r["success"]:
            success += 1
        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"Downloaded: {success}/{len(dois)}")
    failed = [r["doi"] for r in results if not r["success"]]
    if failed:
        print(f"Failed ({len(failed)}):")
        for d in failed:
            print(f"  - {d}")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  download_pdf.py DOI [--output DIR]")
        print("  download_pdf.py --batch DOI1 DOI2 ... [--output DIR]")
        sys.exit(1)

    output = "./papers"
    dois = []
    batch = False
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--output":
            output = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--batch":
            batch = True
            i += 1
        else:
            dois.append(sys.argv[i])
            i += 1

    if batch or len(dois) > 1:
        batch_download(dois, output)
    elif dois:
        download(dois[0], output)
