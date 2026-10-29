"""Parser for NCBI PubMed XML and MEDLINE responses."""

import xml.etree.ElementTree as ET
from typing import List, Optional
from app.models import Paper


def parse_pubmed_xml(xml_content: str) -> List[Paper]:
    """Parses PubMed XML response from EFetch into structured Paper objects."""
    papers: List[Paper] = []
    if not xml_content.strip():
        return papers

    try:
        root = ET.fromstring(xml_content)
        for article in root.findall(".//PubmedArticle"):
            pmid_el = article.find(".//MedlineCitation/PMID")
            pmid = pmid_el.text if pmid_el is not None else ""

            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None else "Untitled Article"

            # Abstract text extraction
            abstract_parts = []
            for ab in article.findall(".//AbstractText"):
                if ab.text:
                    abstract_parts.append(ab.text.strip())
            abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available."

            # Journal
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else "PubMed Central"

            # Authors
            authors_list = []
            for author in article.findall(".//AuthorList/Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None and last.text:
                    initial = f"{fore.text[0]}." if fore is not None and fore.text else ""
                    authors_list.append(f"{initial} {last.text}".strip())
            authors = " · ".join(authors_list[:3]) if authors_list else "Unknown Authors"

            # Date
            year_el = article.find(".//JournalIssue/PubDate/Year")
            year = year_el.text if year_el is not None else "2024"

            papers.append(
                Paper(
                    id=f"pmid_{pmid}",
                    title=title,
                    authors=authors,
                    journal=journal,
                    date=year,
                    type="PubMed Indexed",
                    source="PubMed",
                    tag="High traceability",
                    tone="lilac",
                    abstract=abstract,
                    pmid_doi=f"PMID · {pmid}",
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
    except Exception:
        pass

    return papers

