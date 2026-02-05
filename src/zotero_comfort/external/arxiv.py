"""
arXiv client for literature search and retrieval.

Implements arXiv API access using the arxiv Python library.
Provides search, paper retrieval, and metadata extraction.
"""

import logging
from typing import Dict, List, Optional

import arxiv

from .base import ExternalSource

logger = logging.getLogger(__name__)


class ArXivClient(ExternalSource):
    """
    arXiv API client implementing ExternalSource interface.

    Provides access to arXiv preprints and papers across all scientific disciplines.
    """

    def __init__(self):
        """Initialize arXiv client."""
        self.client = arxiv.Client()
        logger.info("Initialized arXiv client")

    async def search(
        self,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> List[Dict]:
        """
        Search arXiv for papers.

        Args:
            query: Search query (can use field prefixes like ti:, au:, cat:)
            max_results: Maximum papers to return
            **kwargs: Additional parameters:
                - sort_by: arxiv.SortCriterion (relevance, lastUpdatedDate, submittedDate)
                - sort_order: arxiv.SortOrder (ascending, descending)
                - categories: List of arXiv category strings to filter

        Returns:
            List of paper dicts with standardized fields

        Examples:
            # Simple keyword search
            papers = await client.search("quantum computing", max_results=10)

            # Search by title
            papers = await client.search("ti:deep learning", max_results=20)

            # Search by author
            papers = await client.search("au:lecun", max_results=15)

            # Filter by category
            papers = await client.search(
                "machine learning",
                max_results=50,
                categories=["cs.LG", "cs.AI"]
            )
        """
        logger.info(f"Searching arXiv: query={query!r}, max_results={max_results}")

        # Build search with optional parameters
        sort_by = kwargs.get("sort_by", arxiv.SortCriterion.Relevance)
        sort_order = kwargs.get("sort_order", arxiv.SortOrder.Descending)

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Filter by categories if specified
        categories = kwargs.get("categories", [])
        if categories:
            # Append category filter to query
            cat_filter = " OR ".join([f"cat:{cat}" for cat in categories])
            search.query = f"({query}) AND ({cat_filter})"

        results = []
        for result in self.client.results(search):
            paper = self._result_to_dict(result)
            results.append(paper)

        logger.info(f"Found {len(results)} arXiv papers")
        return results

    async def get_details(self, paper_id: str) -> Dict:
        """
        Get full details for a specific arXiv paper.

        Args:
            paper_id: arXiv ID (e.g., "2103.15348" or "cs/0703039")

        Returns:
            Paper dict with full metadata

        Example:
            details = await client.get_details("2103.15348")
        """
        logger.info(f"Fetching arXiv paper details: {paper_id}")

        search = arxiv.Search(id_list=[paper_id])
        results = list(self.client.results(search))

        if not results:
            raise ValueError(f"arXiv paper not found: {paper_id}")

        return self._result_to_dict(results[0])

    def _result_to_dict(self, result: arxiv.Result) -> Dict:
        """
        Convert arxiv.Result to standardized paper dict.

        Args:
            result: arxiv.Result object

        Returns:
            Standardized paper dict
        """
        # Extract ID from URL and strip version suffix (e.g., "2103.15348v2" -> "2103.15348")
        full_id = result.entry_id.split("/")[-1]
        arxiv_id = full_id.split("v")[0] if "v" in full_id else full_id

        return {
            "id": arxiv_id,
            "arxiv_id": arxiv_id,
            "title": result.title.strip(),
            "abstract": result.summary.strip(),
            "authors": [author.name for author in result.authors],
            "publication_date": result.published.strftime("%Y-%m-%d"),
            "updated_date": result.updated.strftime("%Y-%m-%d"),
            "doi": result.doi if result.doi else None,
            "url": result.entry_id,
            "pdf_url": result.pdf_url,
            "primary_category": result.primary_category,
            "categories": result.categories,
            "comment": result.comment,
            "journal_ref": result.journal_ref,
            "source": "arxiv"
        }

    async def search_by_author(
        self,
        author: str,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Search for papers by author name.

        Args:
            author: Author name (last name or full name)
            max_results: Maximum results

        Returns:
            List of papers by this author

        Example:
            papers = await client.search_by_author("bengio", max_results=20)
        """
        query = f"au:{author}"
        return await self.search(query, max_results=max_results)

    async def search_by_category(
        self,
        category: str,
        query: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Search within a specific arXiv category.

        Args:
            category: arXiv category code (e.g., "cs.AI", "math.CO", "q-bio.GN")
            query: Optional additional search terms
            max_results: Maximum results

        Returns:
            List of papers in this category

        Example:
            # Get recent cs.AI papers
            papers = await client.search_by_category("cs.AI", max_results=50)

            # Search for "attention" in cs.LG
            papers = await client.search_by_category(
                "cs.LG",
                query="attention mechanism",
                max_results=30
            )
        """
        if query:
            search_query = f"cat:{category} AND {query}"
        else:
            search_query = f"cat:{category}"

        return await self.search(
            search_query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )

    async def get_recent_papers(
        self,
        category: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict]:
        """
        Get recently submitted papers.

        Args:
            category: Optional category to filter by
            max_results: Maximum results

        Returns:
            List of recent papers, newest first

        Example:
            # Recent papers across all categories
            recent = await client.get_recent_papers(max_results=20)

            # Recent cs.LG papers
            recent_ml = await client.get_recent_papers(category="cs.LG", max_results=30)
        """
        if category:
            query = f"cat:{category}"
        else:
            query = "all:*"  # Match all papers

        return await self.search(
            query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )

    async def download_pdf(
        self,
        paper_id: str,
        dirpath: str = "./",
        filename: Optional[str] = None
    ) -> str:
        """
        Download PDF for a paper.

        Args:
            paper_id: arXiv ID
            dirpath: Directory to save PDF
            filename: Optional custom filename (defaults to arxiv_id.pdf)

        Returns:
            Path to downloaded PDF

        Example:
            pdf_path = await client.download_pdf("2103.15348", dirpath="./papers/")
        """
        logger.info(f"Downloading PDF for arXiv:{paper_id}")

        search = arxiv.Search(id_list=[paper_id])
        results = list(self.client.results(search))

        if not results:
            raise ValueError(f"arXiv paper not found: {paper_id}")

        paper = results[0]
        filename = filename or f"{paper_id}.pdf"
        pdf_path = paper.download_pdf(dirpath=dirpath, filename=filename)

        logger.info(f"Downloaded PDF to {pdf_path}")
        return pdf_path

    async def export_bibtex(self, paper_id: str) -> str:
        """
        Export citation in BibTeX format.

        Args:
            paper_id: arXiv ID

        Returns:
            BibTeX citation string

        Example:
            bibtex = await client.export_bibtex("2103.15348")
        """
        paper = await self.get_details(paper_id)

        # Generate BibTeX entry
        cite_key = f"arxiv_{paper['arxiv_id'].replace('.', '_')}"
        authors_str = " and ".join(paper['authors'])
        year = paper['publication_date'][:4]

        bibtex = f"""@article{{{cite_key},
    title = {{{paper['title']}}},
    author = {{{authors_str}}},
    year = {{{year}}},
    eprint = {{{paper['arxiv_id']}}},
    archivePrefix = {{arXiv}},
    primaryClass = {{{paper['primary_category']}}},
    url = {{{paper['url']}}},
    abstract = {{{paper['abstract']}}}
}}"""

        if paper['doi']:
            bibtex = bibtex.replace("}", f",\n    doi = {{{paper['doi']}}}\n}}", 1)

        if paper['journal_ref']:
            bibtex = bibtex.replace("}", f",\n    journal = {{{paper['journal_ref']}}}\n}}", 1)

        return bibtex


# Common arXiv category reference
ARXIV_CATEGORIES = {
    # Computer Science
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation and Language",
    "cs.CV": "Computer Vision and Pattern Recognition",
    "cs.LG": "Machine Learning",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.RO": "Robotics",

    # Mathematics
    "math.CO": "Combinatorics",
    "math.LO": "Logic",
    "math.ST": "Statistics Theory",

    # Physics
    "physics.bio-ph": "Biological Physics",
    "physics.comp-ph": "Computational Physics",
    "physics.med-ph": "Medical Physics",

    # Quantitative Biology
    "q-bio.BM": "Biomolecules",
    "q-bio.GN": "Genomics",
    "q-bio.NC": "Neurons and Cognition",
    "q-bio.QM": "Quantitative Methods",

    # Statistics
    "stat.AP": "Applications",
    "stat.CO": "Computation",
    "stat.ME": "Methodology",
    "stat.ML": "Machine Learning",
}
