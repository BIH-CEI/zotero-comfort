"""
Complete PubMed client implementing all 16 Augmented-Nature MCP tools.

Uses Biopython (Bio.Entrez) - the same library that PubMed MCP servers use.
Provides feature parity with @augmented-nature/pubmed-mcp-server.

Tools organized into 4 categories:
1. Search & Discovery (6 tools)
2. Article Retrieval (4 tools)
3. Citation & References (4 tools)
4. Utility (2 tools)
"""

import logging
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

try:
    from Bio import Entrez, Medline
    BIOPYTHON_AVAILABLE = True
except ImportError:
    BIOPYTHON_AVAILABLE = False
    logging.warning(
        "Biopython not installed. PubMed functionality will be disabled. "
        "Install with: pip install biopython"
    )

from .base import ExternalSource

logger = logging.getLogger(__name__)


class PubMedClient(ExternalSource):
    """
    Complete PubMed client with all 16 MCP tools.

    Implements NCBI E-utilities API via Biopython:
    - esearch: Search for PMIDs
    - efetch: Fetch article details
    - elink: Get related articles, citations, references
    - esummary: Get article summaries
    """

    def __init__(self, api_key: Optional[str] = None, email: str = ""):
        """
        Initialize PubMed client.

        Args:
            api_key: NCBI API key (optional, increases rate limit to 10 req/sec)
            email: Email address (required by NCBI)
        """
        if not BIOPYTHON_AVAILABLE:
            raise ImportError("Biopython is required for PubMed. Install: pip install biopython")

        if not email:
            logger.warning(
                "NCBI requires an email address. Set via PUBMED_EMAIL environment variable."
            )

        Entrez.email = email
        if api_key:
            Entrez.api_key = api_key
            logger.info("Using NCBI API key (10 req/sec rate limit)")
        else:
            logger.info("No API key provided (3 req/sec rate limit)")

        self.source_name = "pubmed"

    # =========================================================================
    # ExternalSource Interface Implementation
    # =========================================================================

    async def search(
        self,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> List[Dict]:
        """Search PubMed (implements abstract method)."""
        return await self.search_articles(query, max_results=max_results)

    async def get_details(self, paper_id: str) -> Dict:
        """Get article details by PMID (implements abstract method)."""
        return await self.get_article_details(paper_id)

    # =========================================================================
    # SEARCH & DISCOVERY (6 tools)
    # =========================================================================

    async def search_articles(
        self,
        query: str,
        max_results: int = 100,
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
        sort: str = "relevance"
    ) -> List[Dict]:
        """
        1/16: Search PubMed by keywords, authors, journals, dates, MeSH terms.

        Args:
            query: Search query (supports PubMed query syntax)
            max_results: Maximum number of results
            min_date: Minimum date (format: YYYY/MM/DD)
            max_date: Maximum date (format: YYYY/MM/DD)
            sort: Sort order ('relevance', 'pub_date', 'recently_added')

        Returns:
            List of paper dicts with metadata

        Example:
            papers = await client.search_articles(
                "patient reported outcomes",
                max_results=50,
                min_date="2020/01/01"
            )
        """
        logger.info(f"Searching PubMed: {query} (max_results={max_results})")

        # Build date range filter
        date_filter = ""
        if min_date or max_date:
            min_d = min_date or "1900/01/01"
            max_d = max_date or datetime.now().strftime("%Y/%m/%d")
            date_filter = f" AND {min_d}:{max_d}[pdat]"

        # Search for PMIDs
        handle = Entrez.esearch(
            db="pubmed",
            term=query + date_filter,
            retmax=max_results,
            sort=sort
        )
        record = Entrez.read(handle)
        handle.close()

        pmids = record.get("IdList", [])
        logger.info(f"Found {len(pmids)} PMIDs")

        if not pmids:
            return []

        # Fetch full details
        return await self.batch_article_lookup(pmids)

    async def advanced_search(
        self,
        title: Optional[str] = None,
        author: Optional[str] = None,
        journal: Optional[str] = None,
        mesh_terms: Optional[List[str]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        article_type: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        2/16: Complex queries with field-specific searches and boolean operators.

        Args:
            title: Search in title field
            author: Search in author field
            journal: Search in journal field
            mesh_terms: MeSH terms to include
            date_range: (min_date, max_date) tuple
            article_type: Publication type (e.g., "Review", "Clinical Trial")
            max_results: Maximum results

        Returns:
            List of paper dicts

        Example:
            papers = await client.advanced_search(
                title="FHIR",
                journal="Journal of Medical Internet Research",
                mesh_terms=["Electronic Health Records"],
                date_range=("2020/01/01", "2023/12/31")
            )
        """
        query_parts = []

        if title:
            query_parts.append(f"{title}[Title]")
        if author:
            query_parts.append(f"{author}[Author]")
        if journal:
            query_parts.append(f"{journal}[Journal]")
        if mesh_terms:
            mesh_query = " OR ".join([f"{term}[MeSH Terms]" for term in mesh_terms])
            query_parts.append(f"({mesh_query})")
        if article_type:
            query_parts.append(f"{article_type}[Publication Type]")

        if not query_parts:
            raise ValueError("At least one search field must be provided")

        query = " AND ".join(query_parts)
        logger.info(f"Advanced search: {query}")

        min_date, max_date = date_range if date_range else (None, None)
        return await self.search_articles(
            query,
            max_results=max_results,
            min_date=min_date,
            max_date=max_date
        )

    async def search_by_author(
        self,
        author: str,
        affiliation: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        3/16: Find articles by specific authors with optional affiliation filtering.

        Args:
            author: Author name (e.g., "Smith J" or "Smith, John")
            affiliation: Filter by affiliation (e.g., "Harvard")
            max_results: Maximum results

        Returns:
            List of paper dicts

        Example:
            papers = await client.search_by_author(
                "Mandl KD",
                affiliation="Boston Children's Hospital"
            )
        """
        query = f"{author}[Author]"
        if affiliation:
            query += f" AND {affiliation}[Affiliation]"

        logger.info(f"Searching by author: {query}")
        return await self.search_articles(query, max_results=max_results)

    async def search_by_journal(
        self,
        journal: str,
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        4/16: Search within specific journals with date range filtering.

        Args:
            journal: Journal name
            min_date: Minimum publication date (YYYY/MM/DD)
            max_date: Maximum publication date (YYYY/MM/DD)
            max_results: Maximum results

        Returns:
            List of paper dicts

        Example:
            papers = await client.search_by_journal(
                "Nature",
                min_date="2023/01/01"
            )
        """
        query = f"{journal}[Journal]"
        logger.info(f"Searching journal: {journal}")

        return await self.search_articles(
            query,
            max_results=max_results,
            min_date=min_date,
            max_date=max_date
        )

    async def search_by_mesh_terms(
        self,
        mesh_terms: List[str],
        major_topic_only: bool = False,
        max_results: int = 100
    ) -> List[Dict]:
        """
        5/16: Search using Medical Subject Headings (MeSH) with major topic filtering.

        Args:
            mesh_terms: List of MeSH terms
            major_topic_only: If True, only match major topics
            max_results: Maximum results

        Returns:
            List of paper dicts

        Example:
            papers = await client.search_by_mesh_terms(
                ["Electronic Health Records", "Interoperability"],
                major_topic_only=True
            )
        """
        if not mesh_terms:
            raise ValueError("At least one MeSH term required")

        tag = "[MeSH Major Topic]" if major_topic_only else "[MeSH Terms]"
        query = " OR ".join([f"{term}{tag}" for term in mesh_terms])

        logger.info(f"Searching MeSH: {query}")
        return await self.search_articles(query, max_results=max_results)

    async def get_trending_articles(
        self,
        field: str,
        days_back: int = 7,
        max_results: int = 50
    ) -> List[Dict]:
        """
        6/16: Retrieve recently published articles in specific fields.

        Args:
            field: Research field or topic
            days_back: Number of days to look back
            max_results: Maximum results

        Returns:
            List of paper dicts sorted by publication date

        Example:
            papers = await client.get_trending_articles(
                "artificial intelligence",
                days_back=30
            )
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        logger.info(f"Getting trending articles: {field} (last {days_back} days)")

        return await self.search_articles(
            query=field,
            max_results=max_results,
            min_date=start_date.strftime("%Y/%m/%d"),
            max_date=end_date.strftime("%Y/%m/%d"),
            sort="pub_date"
        )

    # =========================================================================
    # ARTICLE RETRIEVAL (4 tools)
    # =========================================================================

    async def get_article_details(self, pmid: str) -> Dict:
        """
        7/16: Get comprehensive metadata and abstract for a specific PMID.

        Args:
            pmid: PubMed ID

        Returns:
            Paper dict with full metadata

        Example:
            details = await client.get_article_details("32634507")
        """
        logger.info(f"Fetching article details: PMID {pmid}")

        handle = Entrez.efetch(
            db="pubmed",
            id=pmid,
            rettype="medline",
            retmode="text"
        )
        records = list(Medline.parse(handle))
        handle.close()

        if not records:
            return {"error": f"PMID {pmid} not found"}

        record = records[0]

        return {
            "pmid": pmid,
            "title": record.get("TI", ""),
            "abstract": record.get("AB", ""),
            "authors": record.get("AU", []),
            "journal": record.get("JT", ""),
            "journal_abbrev": record.get("TA", ""),
            "publication_date": record.get("DP", ""),
            "publication_year": self._extract_year(record.get("DP", "")),
            "doi": self._extract_doi(record),
            "pmcid": self._extract_pmcid(record),
            "mesh_terms": record.get("MH", []),
            "keywords": record.get("OT", []),
            "publication_types": record.get("PT", []),
            "issn": record.get("IS", ""),
            "language": record.get("LA", []),
            "source": "pubmed",
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        }

    async def get_abstract(self, pmid: str) -> str:
        """
        8/16: Retrieve article abstract by PMID with basic metadata.

        Args:
            pmid: PubMed ID

        Returns:
            Abstract text

        Example:
            abstract = await client.get_abstract("32634507")
        """
        details = await self.get_article_details(pmid)
        return details.get("abstract", "")

    async def get_full_text(self, pmid: str) -> Optional[Dict]:
        """
        9/16: Retrieve full text from PubMed Central (PMC) when available.

        Args:
            pmid: PubMed ID

        Returns:
            Dict with full text XML and metadata, or None if not available

        Example:
            full_text = await client.get_full_text("32634507")
        """
        logger.info(f"Fetching full text for PMID {pmid}")

        # Get PMCID via elink
        handle = Entrez.elink(
            dbfrom="pubmed",
            id=pmid,
            linkname="pubmed_pmc"
        )
        record = Entrez.read(handle)
        handle.close()

        try:
            pmcid = record[0]["LinkSetDb"][0]["Link"][0]["Id"]
            logger.info(f"Found PMCID: {pmcid}")
        except (IndexError, KeyError):
            logger.info(f"No PMC full text available for PMID {pmid}")
            return None

        # Fetch full text XML
        handle = Entrez.efetch(
            db="pmc",
            id=pmcid,
            rettype="full",
            retmode="xml"
        )
        full_text_xml = handle.read()
        handle.close()

        return {
            "pmid": pmid,
            "pmcid": pmcid,
            "full_text_xml": full_text_xml.decode("utf-8") if isinstance(full_text_xml, bytes) else full_text_xml,
            "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/"
        }

    async def batch_article_lookup(self, pmids: List[str]) -> List[Dict]:
        """
        10/16: Retrieve multiple articles efficiently (up to 200 PMIDs).

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of paper dicts

        Example:
            papers = await client.batch_article_lookup(
                ["32634507", "33040160", "31778144"]
            )
        """
        if not pmids:
            return []

        # NCBI allows up to 200 IDs per request
        pmids_chunk = pmids[:200]
        logger.info(f"Batch lookup for {len(pmids_chunk)} PMIDs")

        handle = Entrez.efetch(
            db="pubmed",
            id=",".join(pmids_chunk),
            rettype="medline",
            retmode="text"
        )
        records = list(Medline.parse(handle))
        handle.close()

        results = []
        for record in records:
            pmid = record.get("PMID", "")
            results.append({
                "pmid": pmid,
                "title": record.get("TI", ""),
                "abstract": record.get("AB", ""),
                "authors": record.get("AU", []),
                "journal": record.get("JT", ""),
                "publication_date": record.get("DP", ""),
                "publication_year": self._extract_year(record.get("DP", "")),
                "doi": self._extract_doi(record),
                "pmcid": self._extract_pmcid(record),
                "source": "pubmed",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })

        return results

    # =========================================================================
    # CITATION & REFERENCES (4 tools)
    # =========================================================================

    async def get_cited_by(self, pmid: str, max_results: int = 100) -> List[Dict]:
        """
        11/16: Find articles that cite a specific PMID.

        Args:
            pmid: PubMed ID
            max_results: Maximum citing articles to return

        Returns:
            List of citing paper dicts

        Example:
            citing = await client.get_cited_by("32634507", max_results=50)
        """
        logger.info(f"Finding articles citing PMID {pmid}")

        handle = Entrez.elink(
            dbfrom="pubmed",
            id=pmid,
            linkname="pubmed_pubmed_citedin",
            retmax=max_results
        )
        record = Entrez.read(handle)
        handle.close()

        try:
            citing_pmids = [link["Id"] for link in record[0]["LinkSetDb"][0]["Link"]]
            logger.info(f"Found {len(citing_pmids)} citing articles")
            return await self.batch_article_lookup(citing_pmids)
        except (IndexError, KeyError):
            logger.info(f"No citing articles found for PMID {pmid}")
            return []

    async def get_references(self, pmid: str) -> List[Dict]:
        """
        12/16: Get reference list for an article.

        Args:
            pmid: PubMed ID

        Returns:
            List of referenced paper dicts

        Example:
            refs = await client.get_references("32634507")
        """
        logger.info(f"Fetching references for PMID {pmid}")

        handle = Entrez.elink(
            dbfrom="pubmed",
            id=pmid,
            linkname="pubmed_pubmed_refs"
        )
        record = Entrez.read(handle)
        handle.close()

        try:
            ref_pmids = [link["Id"] for link in record[0]["LinkSetDb"][0]["Link"]]
            logger.info(f"Found {len(ref_pmids)} references")
            return await self.batch_article_lookup(ref_pmids)
        except (IndexError, KeyError):
            logger.info(f"No references found for PMID {pmid}")
            return []

    async def get_similar_articles(self, pmid: str, max_results: int = 20) -> List[Dict]:
        """
        13/16: Find related articles based on content similarity.

        Args:
            pmid: PubMed ID
            max_results: Maximum similar articles

        Returns:
            List of similar paper dicts

        Example:
            similar = await client.get_similar_articles("32634507", max_results=10)
        """
        logger.info(f"Finding similar articles to PMID {pmid}")

        handle = Entrez.elink(
            dbfrom="pubmed",
            id=pmid,
            linkname="pubmed_pubmed",
            retmax=max_results + 1  # +1 to account for original article
        )
        record = Entrez.read(handle)
        handle.close()

        try:
            similar_pmids = [link["Id"] for link in record[0]["LinkSetDb"][0]["Link"]]
            # Exclude the original article
            similar_pmids = [pid for pid in similar_pmids if pid != pmid]
            # Limit to max_results
            similar_pmids = similar_pmids[:max_results]
            logger.info(f"Found {len(similar_pmids)} similar articles")
            return await self.batch_article_lookup(similar_pmids)
        except (IndexError, KeyError):
            logger.info(f"No similar articles found for PMID {pmid}")
            return []

    async def export_citation(
        self,
        pmid: str,
        format: str = "bibtex"
    ) -> str:
        """
        14/16: Export citations in various formats.

        Args:
            pmid: PubMed ID
            format: Citation format (bibtex, apa, mla, chicago, ris)

        Returns:
            Formatted citation string

        Example:
            citation = await client.export_citation("32634507", format="bibtex")
        """
        details = await self.get_article_details(pmid)

        if "error" in details:
            return f"Error: {details['error']}"

        if format == "bibtex":
            return self._format_bibtex(details)
        elif format == "apa":
            return self._format_apa(details)
        elif format == "mla":
            return self._format_mla(details)
        elif format == "chicago":
            return self._format_chicago(details)
        elif format == "ris":
            return self._format_ris(details)
        else:
            raise ValueError(f"Unsupported format: {format}. Use: bibtex, apa, mla, chicago, ris")

    # =========================================================================
    # UTILITY (2 tools)
    # =========================================================================

    async def validate_pmid(self, pmid: str) -> Dict[str, bool]:
        """
        15/16: Validate PubMed ID format and check if article exists.

        Args:
            pmid: PubMed ID to validate

        Returns:
            Dict with 'valid_format' and 'exists' booleans

        Example:
            validation = await client.validate_pmid("32634507")
            # {"valid_format": True, "exists": True}
        """
        # Check format (PMIDs are numeric)
        is_valid_format = bool(re.match(r'^\d+$', pmid))

        if not is_valid_format:
            return {"valid_format": False, "exists": False}

        # Check existence
        try:
            handle = Entrez.esummary(db="pubmed", id=pmid)
            record = Entrez.read(handle)
            handle.close()
            exists = len(record) > 0 and "error" not in record[0]
        except Exception as e:
            logger.warning(f"Error validating PMID {pmid}: {e}")
            exists = False

        return {"valid_format": True, "exists": exists}

    async def convert_identifiers(
        self,
        identifier: str,
        source_type: str,
        target_type: str
    ) -> Optional[str]:
        """
        16/16: Convert between PMID, DOI, and PMC ID.

        Args:
            identifier: ID to convert
            source_type: Source ID type ("pmid", "doi", "pmcid")
            target_type: Target ID type ("pmid", "doi", "pmcid")

        Returns:
            Converted identifier or None if not found

        Example:
            doi = await client.convert_identifiers(
                "32634507",
                source_type="pmid",
                target_type="doi"
            )
        """
        if source_type == target_type:
            return identifier

        logger.info(f"Converting {source_type} to {target_type}: {identifier}")

        # Use NCBI ID Converter API
        try:
            import httpx
            converter_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
            params = {
                "ids": identifier,
                "format": "json",
                "idtype": source_type
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(converter_url, params=params)
                data = response.json()

                if data.get("records"):
                    record = data["records"][0]
                    result = record.get(target_type)
                    logger.info(f"Converted to: {result}")
                    return result
                else:
                    logger.info(f"No conversion found")
                    return None
        except Exception as e:
            logger.error(f"ID conversion error: {e}")
            return None

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _extract_doi(self, record: Dict) -> Optional[str]:
        """Extract DOI from Medline record."""
        aids = record.get("AID", [])
        for aid in aids:
            if "[doi]" in aid:
                return aid.replace(" [doi]", "")
        return None

    def _extract_pmcid(self, record: Dict) -> Optional[str]:
        """Extract PMCID from Medline record."""
        aids = record.get("AID", [])
        for aid in aids:
            if "[pmc]" in aid.lower():
                return aid.replace(" [pmc]", "").replace("PMC", "")
        return None

    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from publication date string."""
        if not date_str:
            return None
        match = re.search(r'\d{4}', date_str)
        return int(match.group(0)) if match else None

    def _format_bibtex(self, details: Dict) -> str:
        """Format article as BibTeX."""
        pmid = details.get("pmid", "")
        title = details.get("title", "")
        authors = details.get("authors", [])
        journal = details.get("journal", "")
        year = details.get("publication_year", "")
        doi = details.get("doi", "")

        # Format authors
        author_str = " and ".join(authors) if authors else ""

        bibtex = f"""@article{{pmid{pmid},
  title = {{{title}}},
  author = {{{author_str}}},
  journal = {{{journal}}},
  year = {{{year}}},"""

        if doi:
            bibtex += f"\n  doi = {{{doi}}},"

        bibtex += f"\n  pmid = {{{pmid}}}\n}}"

        return bibtex

    def _format_apa(self, details: Dict) -> str:
        """Format article as APA."""
        authors = details.get("authors", [])
        year = details.get("publication_year", "n.d.")
        title = details.get("title", "")
        journal = details.get("journal", "")
        doi = details.get("doi", "")

        # Format authors (APA style: Last, F. M.)
        if authors:
            author_str = ", ".join(authors[:7])  # APA limits to 7 authors
            if len(authors) > 7:
                author_str += ", et al."
        else:
            author_str = "Author Unknown"

        citation = f"{author_str} ({year}). {title}. {journal}."

        if doi:
            citation += f" https://doi.org/{doi}"

        return citation

    def _format_mla(self, details: Dict) -> str:
        """Format article as MLA."""
        authors = details.get("authors", [])
        title = details.get("title", "")
        journal = details.get("journal", "")
        year = details.get("publication_year", "")

        if authors:
            first_author = authors[0]
            if len(authors) > 1:
                author_str = f"{first_author}, et al."
            else:
                author_str = first_author
        else:
            author_str = "Unknown"

        return f'{author_str}. "{title}." {journal}, {year}.'

    def _format_chicago(self, details: Dict) -> str:
        """Format article as Chicago."""
        authors = details.get("authors", [])
        year = details.get("publication_year", "")
        title = details.get("title", "")
        journal = details.get("journal", "")

        if authors:
            author_str = ", ".join(authors)
        else:
            author_str = "Unknown"

        return f'{author_str}. {year}. "{title}." {journal}.'

    def _format_ris(self, details: Dict) -> str:
        """Format article as RIS."""
        ris = "TY  - JOUR\n"
        ris += f"TI  - {details.get('title', '')}\n"

        for author in details.get("authors", []):
            ris += f"AU  - {author}\n"

        ris += f"JO  - {details.get('journal', '')}\n"
        ris += f"PY  - {details.get('publication_year', '')}\n"

        if details.get("doi"):
            ris += f"DO  - {details['doi']}\n"

        ris += f"UR  - https://pubmed.ncbi.nlm.nih.gov/{details.get('pmid', '')}/\n"
        ris += "ER  - \n"

        return ris
