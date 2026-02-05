"""
Charité Forschungsdatenbank (research database) client.

Fetches publication data from the Charité research database JSON API at
forschungsdatenbank.charite.de. The SPA frontend loads data from REST
endpoints which we call directly — no browser needed.

API pattern discovered:
    /experts/expert/publications/pub_per_exp/{token}/FPS → publications
    /experts/expert/exp/co_per_exp/{token}/FPS           → co-authors
    /experts/expert/exp/info_per_exp/{token}              → profile info

Provides:
- Per-author publication fetching via API token
- Batch fetching across the CEIR team roster
- Full metadata: title, authors, year, DOI, journal, abstract, PubMed links
- Standardized output compatible with ExternalSource interface
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import httpx

from .base import ExternalSource

logger = logging.getLogger(__name__)

API_BASE = "https://forschungsdatenbank.charite.de/experts/expert"
DEFAULT_TIMEOUT = 30.0


@dataclass
class TeamMember:
    """A team member with their Charité API token."""
    name: str
    surname: str
    token: Optional[str] = None
    profile_url: Optional[str] = None
    orcid: Optional[str] = None


# CEIR team roster with API tokens discovered from the Forschungsdatenbank.
# Tokens are stable identifiers used by the backend API.
# Members without tokens don't have Charité-internal profiles (e.g. student
# assistants, external collaborators). Their publications appear as co-authors
# on other team members' profiles.
CEIR_TEAM: List[TeamMember] = [
    # Leadership
    TeamMember(
        name="Sylvia Thun",
        surname="Thun",
        token="F7C62FED63154D1D9C567E6394386C1F",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/sylvia_thun/de",
    ),
    # Team (alphabetical by surname)
    TeamMember(
        name="Alexander Bartschke",
        surname="Bartschke",
        token="851d2d2c374943f4aa0ed661b9dfa39e",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/alexander_bartschke/de",
    ),
    TeamMember(
        name="Munja Chahabadi",
        surname="Chahabadi",
    ),
    TeamMember(
        name="Thomas Debertshäuser",
        surname="Debertshäuser",
        token="85bcddc047444b8fad16b77bcf25ad8e",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/thomas_debertshaeuser/de",
    ),
    TeamMember(
        name="Claudia Finis",
        surname="Finis",
        orcid="0009-0004-0018-1312",
    ),
    TeamMember(
        name="Margaux Gatrio",
        surname="Gatrio",
        token="681a5eea8c8f4988afef105e6c9ab600",
        profile_url="https://forschungsdatenbank.charite.de/experts/expertenprofil.xhtml?id=681a5eea8c8f4988afef105e6c9ab600&type=ps&lang=de",
    ),
    TeamMember(
        name="Adam Graefe",
        surname="Graefe",
        orcid="0009-0004-8124-8864",
    ),
    TeamMember(
        name="Wiebke Hartung",
        surname="Hartung",
    ),
    TeamMember(
        name="Thimo-Andre Hölter",
        surname="Hölter",
        orcid="0000-0002-5949-5269",
    ),
    TeamMember(
        name="Miriam Rebecca Hübner",
        surname="Hübner",
        token="26b0f5b4da1b40308820c684854b3381",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/miriam-rebecca_huebner/de",
    ),
    TeamMember(
        name="Sophie Klopfenstein",
        surname="Klopfenstein",
        token="58ed0f17be6b4281bdcbf1630a9b1847",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/sophie_klopfenstein/de",
    ),
    TeamMember(
        name="Hanneke Leegwater",
        surname="Leegwater",
        orcid="0000-0001-6003-1544",
    ),
    TeamMember(
        name="Michael Rusongoza Muzoora",
        surname="Muzoora",
        token="5162a9a2c76647d4b676baa6a36408ca",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/michael_muzoora/de",
    ),
    TeamMember(
        name="Rasim Atakan Poyraz",
        surname="Poyraz",
        token="d68c44428d9445809d89b728fb5fe690",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/rasim-atakan_poyraz/de",
    ),
    TeamMember(
        name="Eugenia Rinaldi",
        surname="Rinaldi",
        token="b29459c137af460ca44312ecced5bae9",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/eugenia_rinaldi/de",
    ),
    TeamMember(
        name="Eduardo Salgado",
        surname="Salgado",
        token="19bdf2db5939424abe39a50b2146c666",
        profile_url="https://forschungsdatenbank.charite.de/experts/expertenprofil.xhtml?id=19bdf2db5939424abe39a50b2146c666&type=ps&lang=de",
    ),
    TeamMember(
        name="Julian Saß",
        surname="Saß",
        token="e6363d0ec17b4ee7bb22afa5a19660ef",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/julian_sass/de",
    ),
    TeamMember(
        name="Marco Schaarschmidt",
        surname="Schaarschmidt",
        token="6cda3395215948bdabb5fbd08a40a838",
        profile_url="https://forschungsdatenbank.charite.de/experts/expertenprofil.xhtml?id=6cda3395215948bdabb5fbd08a40a838&type=ps&lang=de",
    ),
    TeamMember(
        name="Lotte Schwiening",
        surname="Schwiening",
        orcid="0009-0009-3543-4793",
    ),
    TeamMember(
        name="Carina Vorisek",
        surname="Vorisek",
        token="d29dd756befd4385aacabab2920db213",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/carina-nina_vorisek/de",
    ),
    # Associated scientists
    TeamMember(
        name="Andrea Essenwanger",
        surname="Essenwanger",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/andrea_essenwanger/de",
    ),
    TeamMember(
        name="Caroline Stellmach",
        surname="Stellmach",
        profile_url="https://forschungsdatenbank.charite.de/experts/profile/caroline_stellmach/de",
    ),
]


class ChariteClient(ExternalSource):
    """
    Client for the Charité Forschungsdatenbank REST API.

    Fetches publication metadata directly from the JSON endpoints
    used by the SPA frontend. No browser or Playwright needed.
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize Charité client.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.source_name = "charite"
        self._http: Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        """Lazily create the HTTP client."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._http

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    # =========================================================================
    # ExternalSource Interface
    # =========================================================================

    async def search(
        self,
        query: str,
        max_results: int = 100,
        **kwargs
    ) -> List[Dict]:
        """
        Search across all team member publications for titles matching query.

        Args:
            query: Search string matched against publication titles
            max_results: Maximum results to return
            **kwargs:
                - members: Optional list of TeamMember to search

        Returns:
            List of publication dicts matching the query
        """
        members = kwargs.get("members", CEIR_TEAM)
        all_pubs = await self.fetch_team(members=members)

        query_lower = query.lower()
        matched = [
            p for p in all_pubs
            if query_lower in p.get("title", "").lower()
        ]
        return matched[:max_results]

    async def get_details(self, paper_id: str) -> Dict:
        """
        Get details for a publication by DOI.

        Args:
            paper_id: DOI of the publication

        Returns:
            Publication dict or error dict
        """
        all_pubs = await self.fetch_team()
        for pub in all_pubs:
            if pub.get("doi") == paper_id:
                return pub
        return {"error": f"Publication with DOI {paper_id} not found"}

    # =========================================================================
    # Core API Methods
    # =========================================================================

    async def fetch_publications(self, token: str) -> List[Dict]:
        """
        Fetch all publications for a person by their API token.

        Args:
            token: Charité Forschungsdatenbank person token

        Returns:
            List of standardized publication dicts
        """
        client = await self._client()
        url = f"{API_BASE}/publications/pub_per_exp/{token}/FPS"

        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch publications for token {token}: {e}")
            return []

        data = resp.json()
        raw_pubs = data.get("publikationen", [])

        publications = []
        for entry in raw_pubs:
            pub = self._normalize_publication(entry)
            if pub:
                publications.append(pub)

        return publications

    async def fetch_coauthors(self, token: str) -> List[Dict]:
        """
        Fetch co-author list for a person by their API token.

        Useful for discovering tokens of other team members.

        Args:
            token: Charité Forschungsdatenbank person token

        Returns:
            List of co-author dicts with name, token, publication count
        """
        client = await self._client()
        url = f"{API_BASE}/exp/co_per_exp/{token}/FPS"

        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch co-authors for token {token}: {e}")
            return []

        data = resp.json()
        coauthors = []

        for entry in data.get("autoren", []):
            ap = entry.get("autorenPerson")
            if not ap:
                continue
            person = ap.get("person") or {}
            coauthors.append({
                "name": ap.get("name", ""),
                "first_name": ap.get("vorname", ""),
                "token": person.get("token"),
                "type": person.get("type", ""),
                "publication_count": ap.get("anzahlPublikationen", 0),
            })

        return coauthors

    async def fetch_profile_info(self, token: str) -> Dict:
        """
        Fetch basic profile information for a person.

        Args:
            token: Charité Forschungsdatenbank person token

        Returns:
            Dict with name, group, ORCID, publication/co-author counts
        """
        client = await self._client()
        url = f"{API_BASE}/exp/info_per_exp/{token}"

        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch profile for token {token}: {e}")
            return {}

        data = resp.json()
        main = data.get("mainInfo", {})
        return {
            "first_name": main.get("vorname", ""),
            "last_name": main.get("nachname", ""),
            "group": main.get("gruppe", ""),
            "group_en": main.get("gruppeen", ""),
            "orcid": main.get("orcid", ""),
            "total_publications": data.get("publikationen", 0),
            "internal_coauthors": data.get("interneCoAutoren", {}).get("level1", 0),
            "total_coauthors": data.get("gesamt", {}).get("level1", 0),
        }

    # =========================================================================
    # Team-level Operations
    # =========================================================================

    async def fetch_member(self, member: TeamMember) -> List[Dict]:
        """
        Fetch all publications for a team member.

        Args:
            member: TeamMember with token set

        Returns:
            List of publication dicts
        """
        if not member.token:
            logger.debug(f"No API token for {member.name}, skipping")
            return []

        logger.info(f"Fetching publications for {member.name}")
        pubs = await self.fetch_publications(member.token)
        logger.info(f"  {len(pubs)} publications for {member.name}")
        return pubs

    async def fetch_team(
        self,
        members: Optional[List[TeamMember]] = None,
        delay_between: float = 0.3,
    ) -> List[Dict]:
        """
        Fetch publications from all team members with API tokens.

        Args:
            members: Team members to fetch (defaults to CEIR_TEAM)
            delay_between: Seconds between requests (rate limiting courtesy)

        Returns:
            Deduplicated list of all team publications
        """
        members = members or CEIR_TEAM
        fetchable = [m for m in members if m.token]

        logger.info(
            f"Fetching from {len(fetchable)} team members "
            f"({len(members) - len(fetchable)} without API tokens)"
        )

        all_pubs: List[Dict] = []

        for member in fetchable:
            pubs = await self.fetch_member(member)
            all_pubs.extend(pubs)
            if delay_between > 0:
                await asyncio.sleep(delay_between)

        deduplicated = self._deduplicate(all_pubs)
        logger.info(
            f"Total: {len(all_pubs)} raw, {len(deduplicated)} after deduplication"
        )
        return deduplicated

    async def fetch_member_by_name(self, name: str) -> List[Dict]:
        """
        Fetch publications for a specific team member by name.

        Args:
            name: Team member name (partial match, case-insensitive)

        Returns:
            List of publications
        """
        name_lower = name.lower()
        matches = [
            m for m in CEIR_TEAM
            if name_lower in m.name.lower() or name_lower in m.surname.lower()
        ]
        if not matches:
            logger.warning(f"No team member found matching '{name}'")
            return []

        member = matches[0]
        return await self.fetch_member(member)

    async def discover_tokens(self, seed_token: Optional[str] = None) -> Dict[str, str]:
        """
        Discover API tokens for team members by traversing co-author networks.

        Starting from a seed token (defaults to Thun), fetches co-author lists
        and matches surnames against the team roster.

        Args:
            seed_token: Starting token (defaults to Thun's token)

        Returns:
            Dict mapping surname -> token for discovered team members
        """
        team_surnames = {m.surname for m in CEIR_TEAM}

        # Start with known tokens
        discovered: Dict[str, str] = {}
        for m in CEIR_TEAM:
            if m.token:
                discovered[m.surname] = m.token

        seed = seed_token or "F7C62FED63154D1D9C567E6394386C1F"
        tokens_to_scan = [seed] + [m.token for m in CEIR_TEAM if m.token and m.token != seed]

        for token in tokens_to_scan:
            coauthors = await self.fetch_coauthors(token)
            for ca in coauthors:
                surname = ca["name"]
                ca_token = ca.get("token")
                if ca_token and surname in team_surnames and surname not in discovered:
                    discovered[surname] = ca_token
                    logger.info(f"Discovered token for {ca['first_name']} {surname}: {ca_token}")

            # Also check publication co-authors
            pubs = await self.fetch_publications(token)
            for pub in pubs:
                for author in pub.get("internal_authors", []):
                    surname = author.get("surname", "")
                    a_token = author.get("token")
                    if a_token and surname in team_surnames and surname not in discovered:
                        discovered[surname] = a_token
                        logger.info(
                            f"Discovered token for {author.get('first_name')} {surname}: {a_token}"
                        )

            await asyncio.sleep(0.3)

        missing = team_surnames - set(discovered.keys())
        if missing:
            logger.info(f"No tokens found for: {missing}")

        return discovered

    # =========================================================================
    # Normalization
    # =========================================================================

    def _normalize_publication(self, entry: Dict) -> Optional[Dict]:
        """
        Normalize a Charité API publication entry to standard format.

        Args:
            entry: Raw publication entry from the API

        Returns:
            Standardized publication dict or None
        """
        pub_data = entry.get("publikation", {})
        title = pub_data.get("titel", "")
        if not title:
            return None

        year = pub_data.get("publikationJahr")

        # Parse author string: "Last,First;Last,First;..."
        author_string = pub_data.get("autorenString", "")
        authors = []
        if author_string:
            for part in author_string.split(";"):
                part = part.strip()
                if "," in part:
                    last, first = part.split(",", 1)
                    authors.append(f"{first.strip()} {last.strip()}")
                elif part:
                    authors.append(part)

        # Extract DOI from links
        doi = None
        pubmed_url = None
        pmc_url = None
        fulltext_url = None

        for link in entry.get("links", []):
            url = link.get("url", "")
            label = link.get("en", "").lower()
            if "doi" in label:
                doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", url)
            elif "pubmed" in label:
                pubmed_url = url
            elif "pmc" in label:
                pmc_url = url
            elif "full text" in label or "volltext" in label:
                fulltext_url = url

        # Journal info
        source = pub_data.get("quelle", {})
        journal = source.get("langname") or source.get("name", "")

        # Volume/issue/pages
        volume = pub_data.get("quelleIdentifier")
        issue = pub_data.get("quelleIdentifier2")
        pages = pub_data.get("quelleLocation")

        # Internal (Charité) co-authors with their tokens
        internal_authors = []
        for ia in entry.get("interneAutoren", []):
            person = ia.get("person", {})
            internal_authors.append({
                "surname": ia.get("name", ""),
                "first_name": ia.get("vorname", ""),
                "token": person.get("token"),
                "type": person.get("type", ""),
            })

        return {
            "title": title.strip().rstrip("."),
            "authors": authors,
            "publication_date": str(year) if year else "",
            "publication_year": year,
            "doi": doi,
            "journal": journal,
            "journal_abbrev": source.get("name", ""),
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "abstract": pub_data.get("abriss", ""),
            "affiliation": pub_data.get("einrichtung", ""),
            "publication_type": pub_data.get("externPnTyp", ""),
            "book_title": pub_data.get("buchtitel", ""),
            "pubmed_url": pubmed_url,
            "pmc_url": pmc_url,
            "fulltext_url": fulltext_url,
            "open_access": entry.get("oaStatus"),
            "internal_authors": internal_authors,
            "source": "charite",
            "url": f"https://doi.org/{doi}" if doi else (pubmed_url or ""),
        }

    # =========================================================================
    # Utility
    # =========================================================================

    def _deduplicate(self, publications: List[Dict]) -> List[Dict]:
        """Deduplicate publications by DOI or normalized title."""
        seen_dois: set = set()
        seen_titles: set = set()
        unique: List[Dict] = []

        for pub in publications:
            doi = pub.get("doi")
            if doi:
                doi_key = doi.lower().strip()
                if doi_key in seen_dois:
                    continue
                seen_dois.add(doi_key)

            title = pub.get("title", "")
            title_key = re.sub(r"[^a-z0-9]", "", title.lower())[:50]
            if title_key and title_key in seen_titles:
                continue
            if title_key:
                seen_titles.add(title_key)

            unique.append(pub)

        return unique

    def get_team_roster(self) -> List[Dict]:
        """
        Get the current CEIR team roster.

        Returns:
            List of team member dicts
        """
        return [
            {
                "name": m.name,
                "surname": m.surname,
                "token": m.token,
                "profile_url": m.profile_url,
                "orcid": m.orcid,
                "has_api_token": m.token is not None,
            }
            for m in CEIR_TEAM
        ]
