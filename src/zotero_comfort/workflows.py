"""
Smart Workflows (B) - High-level research automation.

Orchestrates multiple MCP calls into researcher-friendly workflows:
- build_reading_list: Search + filter + create collection
- smart_add_paper: DOI resolution + duplicate check + collection suggestion
- export_bibliography: Gather collection items + format as BibTeX
"""

import logging
import re
from typing import Any, Dict, List, Optional

from .client import ZoteroMCPClient

logger = logging.getLogger(__name__)


class ZoteroWorkflows:
    """
    Smart workflow orchestrations for research tasks.

    These methods combine multiple operations into high-level workflows
    that handle common research patterns automatically.
    """

    def __init__(self, client: Optional[ZoteroMCPClient] = None):
        """Initialize workflows.

        Args:
            client: ZoteroMCPClient instance (created with defaults if not provided)
        """
        self.client = client or ZoteroMCPClient()

    # Collection suggestion based on keywords

    COLLECTION_KEYWORDS = {
        "fhir": "FHIR",
        "hl7": "FHIR",
        "healthcare interoperability": "FHIR",
        "snomed": "Terminology",
        "loinc": "Terminology",
        "icd": "Terminology",
        "ontology": "Terminology",
        "machine learning": "ML",
        "deep learning": "ML",
        "neural network": "ML",
        "nlp": "NLP",
        "natural language": "NLP",
        "clinical": "Clinical",
        "patient": "Clinical",
        "ehr": "Clinical",
        "electronic health": "Clinical",
    }

    def _suggest_collection(self, title: str) -> str:
        """Suggest a collection based on paper title keywords.

        Args:
            title: Paper title

        Returns:
            Suggested collection name
        """
        title_lower = title.lower()

        for keyword, collection in self.COLLECTION_KEYWORDS.items():
            if keyword in title_lower:
                logger.debug(f"Matched keyword '{keyword}' -> collection '{collection}'")
                return collection

        return "Uncategorized"

    def build_reading_list(
        self,
        topic: str,
        max_papers: int = 20,
        min_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build a reading list for a research topic.

        Searches the library, filters results, and returns a curated list.

        Args:
            topic: Research topic to search for
            max_papers: Maximum papers to include
            min_year: Only include papers from this year or later

        Returns:
            {
                'topic': str,
                'papers_found': int,
                'papers_included': int,
                'papers': [
                    {'key': str, 'title': str, 'year': str, 'creators': list}
                ],
                'suggested_collection': str
            }
        """
        logger.info(f"Building reading list for topic: {topic}")

        # Search for papers
        all_papers = self.client.search_items(topic, limit=100)
        logger.info(f"Found {len(all_papers)} papers for '{topic}'")

        # Filter by year if specified
        filtered = all_papers
        if min_year:
            filtered = [
                p for p in all_papers
                if self._extract_year(p.get("date", "")) >= min_year
            ]
            logger.info(f"After year filter ({min_year}+): {len(filtered)} papers")

        # Take top N
        selected = filtered[:max_papers]

        # Format output
        papers = [
            {
                "key": p.get("key", ""),
                "title": p.get("title", "Untitled"),
                "year": self._extract_year_str(p.get("date", "")),
                "creators": self._format_creators(p.get("creators", [])),
            }
            for p in selected
        ]

        return {
            "topic": topic,
            "papers_found": len(all_papers),
            "papers_included": len(papers),
            "papers": papers,
            "suggested_collection": self._suggest_collection(topic),
        }

    def smart_add_paper(
        self,
        doi: str,
        check_duplicates: bool = True,
        suggest_collection: bool = True,
    ) -> Dict[str, Any]:
        """
        Intelligently add a paper from DOI.

        Checks for duplicates, resolves metadata, and suggests collection placement.

        Args:
            doi: Paper DOI (e.g., "10.1234/example.2024")
            check_duplicates: Whether to check if paper already exists
            suggest_collection: Whether to suggest a collection

        Returns:
            {
                'status': 'success' | 'duplicate' | 'error',
                'doi': str,
                'title': str (if resolved),
                'suggested_collection': str (if suggest_collection=True),
                'duplicate_key': str (if duplicate found),
                'message': str
            }
        """
        logger.info(f"Smart add paper: {doi}")

        # Normalize DOI
        doi = self._normalize_doi(doi)
        if not doi:
            return {
                "status": "error",
                "doi": doi,
                "message": "Invalid DOI format",
            }

        # Check for duplicates by searching for DOI
        if check_duplicates:
            existing = self.client.search_items(doi, limit=5)
            for paper in existing:
                paper_doi = self._extract_doi(paper)
                if paper_doi and paper_doi.lower() == doi.lower():
                    return {
                        "status": "duplicate",
                        "doi": doi,
                        "title": paper.get("title", ""),
                        "duplicate_key": paper.get("key", ""),
                        "message": "Paper already exists in library",
                    }

        # Note: Actual DOI resolution and item creation would require write access
        # to Zotero, which depends on MCP server configuration. This workflow
        # prepares the metadata and suggestion but may not complete the add.

        return {
            "status": "ready",
            "doi": doi,
            "message": "DOI validated, no duplicates found. Manual add recommended.",
            "suggested_collection": self._suggest_collection(doi) if suggest_collection else None,
        }

    def export_bibliography(
        self,
        collection_name: Optional[str] = None,
        tag: Optional[str] = None,
        format: str = "bibtex",
    ) -> Dict[str, Any]:
        """
        Export papers as formatted bibliography.

        Args:
            collection_name: Export from this collection (optional)
            tag: Export papers with this tag (optional)
            format: Output format ('bibtex' supported)

        Returns:
            {
                'status': 'success' | 'error',
                'format': str,
                'count': int,
                'bibliography': str
            }
        """
        logger.info(f"Exporting bibliography: collection={collection_name}, tag={tag}")

        papers = []

        # Get papers from collection or tag
        if collection_name:
            collections = self.client.list_collections()
            collection = next(
                (c for c in collections if c.get("name") == collection_name), None
            )
            if collection:
                papers = self.client.get_collection_items(collection["key"])
            else:
                return {
                    "status": "error",
                    "message": f"Collection not found: {collection_name}",
                }
        elif tag:
            papers = self.client.search_by_tag(tag)
        else:
            return {
                "status": "error",
                "message": "Specify collection_name or tag",
            }

        if not papers:
            return {
                "status": "success",
                "format": format,
                "count": 0,
                "bibliography": f"% No papers found\n",
            }

        # Generate BibTeX
        if format == "bibtex":
            bibtex_entries = []
            for paper in papers:
                entry = self._to_bibtex(paper)
                if entry:
                    bibtex_entries.append(entry)

            bibliography = "\n\n".join(bibtex_entries)
        else:
            return {
                "status": "error",
                "message": f"Unsupported format: {format}",
            }

        return {
            "status": "success",
            "format": format,
            "count": len(bibtex_entries),
            "bibliography": bibliography,
        }

    def find_related_papers(
        self,
        item_key: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Find papers related to a given paper.

        Uses semantic search based on the paper's title and abstract.

        Args:
            item_key: Zotero key of the source paper
            limit: Maximum related papers to return

        Returns:
            {
                'source': {'key': str, 'title': str},
                'related': [{'key': str, 'title': str, 'relevance': float}]
            }
        """
        logger.info(f"Finding papers related to: {item_key}")

        # Get source paper
        source = self.client.get_item(item_key)
        if "error" in source:
            return {"status": "error", "message": f"Paper not found: {item_key}"}

        title = source.get("title", "")
        abstract = source.get("abstractNote", "")

        # Build search query from title and key terms
        query = title
        if abstract:
            # Add first sentence of abstract for better semantic matching
            first_sentence = abstract.split(".")[0] if "." in abstract else abstract[:200]
            query = f"{title}. {first_sentence}"

        # Semantic search
        related = self.client.semantic_search(query, limit=limit + 1)

        # Filter out the source paper itself
        related = [p for p in related if p.get("key") != item_key][:limit]

        return {
            "status": "success",
            "source": {"key": item_key, "title": title},
            "related": [
                {
                    "key": p.get("key", ""),
                    "title": p.get("title", ""),
                    "creators": self._format_creators(p.get("creators", [])),
                }
                for p in related
            ],
        }

    # Helper methods

    def _normalize_doi(self, doi: str) -> Optional[str]:
        """Extract and normalize DOI from various formats."""
        # Handle full URLs
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        doi = doi.replace("doi:", "").strip()

        # Validate DOI pattern (basic check)
        if re.match(r"^10\.\d{4,}/", doi):
            return doi
        return None

    def _extract_doi(self, paper: Dict) -> Optional[str]:
        """Extract DOI from paper metadata."""
        doi = paper.get("DOI") or paper.get("doi")
        if doi:
            return self._normalize_doi(doi)
        return None

    def _extract_year(self, date_str: str) -> int:
        """Extract year as integer from date string."""
        match = re.search(r"(\d{4})", date_str)
        return int(match.group(1)) if match else 0

    def _extract_year_str(self, date_str: str) -> str:
        """Extract year as string from date string."""
        match = re.search(r"(\d{4})", date_str)
        return match.group(1) if match else ""

    def _format_creators(self, creators: List[Dict]) -> str:
        """Format creator list as string."""
        if not creators:
            return ""

        names = []
        for c in creators[:3]:  # Limit to first 3
            if "lastName" in c:
                names.append(c["lastName"])
            elif "name" in c:
                names.append(c["name"])

        result = ", ".join(names)
        if len(creators) > 3:
            result += " et al."
        return result

    def _to_bibtex(self, paper: Dict) -> Optional[str]:
        """Convert paper to BibTeX entry."""
        key = paper.get("key", "unknown")
        title = paper.get("title", "")
        if not title:
            return None

        # Determine entry type
        item_type = paper.get("itemType", "article")
        bibtex_type = {
            "journalArticle": "article",
            "book": "book",
            "bookSection": "incollection",
            "conferencePaper": "inproceedings",
            "thesis": "phdthesis",
            "report": "techreport",
        }.get(item_type, "misc")

        # Build entry
        lines = [f"@{bibtex_type}{{{key},"]
        lines.append(f"  title = {{{title}}},")

        # Authors
        creators = paper.get("creators", [])
        if creators:
            authors = " and ".join(
                f"{c.get('lastName', '')}, {c.get('firstName', '')}"
                for c in creators
                if c.get("creatorType") == "author"
            )
            if authors:
                lines.append(f"  author = {{{authors}}},")

        # Year
        date = paper.get("date", "")
        year = self._extract_year_str(date)
        if year:
            lines.append(f"  year = {{{year}}},")

        # Journal/Publisher
        if journal := paper.get("publicationTitle"):
            lines.append(f"  journal = {{{journal}}},")
        if publisher := paper.get("publisher"):
            lines.append(f"  publisher = {{{publisher}}},")

        # DOI
        if doi := paper.get("DOI"):
            lines.append(f"  doi = {{{doi}}},")

        lines.append("}")
        return "\n".join(lines)
