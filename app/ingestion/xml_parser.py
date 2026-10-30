"""Parser for NCBI PubMed XML and MEDLINE responses."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import List
from app.models import Paper

logger = logging.getLogger(__name__)


def parse_pubmed_xml(xml_content: str) -> List[Paper]:
    """Parses PubMed XML response from EFetch into structured Paper objects.
    
    Handles structured abstracts with section labels, inline markup tags (itertext),
    collective author names, and fallback publication dates.
    """
    papers: List[Paper] = []
    cleaned_xml = xml_content.strip()
    if not cleaned_xml:
        return papers

    try:
        root = ET.fromstring(cleaned_xml)
    except ET.ParseError as err:
        logger.warning("XML parsing failed for PubMed response: %s", err)
        raise

    for article in root.findall(".//PubmedArticle"):
        # 1. PMID
        pmid_el = article.find(".//MedlineCitation/PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else "unknown"

        # 2. Title (preserve inline tags via itertext)
        title_el = article.find(".//ArticleTitle")
        if title_el is not None:
            title = "".join(title_el.itertext()).strip()
        else:
            title = "Untitled Article"
        if not title:
            title = "Untitled Article"

        # 3. Abstract text extraction (support structured abstract labels and inline tags)
        abstract_parts = []
        abstract_nodes = article.findall(".//Abstract/AbstractText")
        if not abstract_nodes:
            abstract_nodes = article.findall(".//AbstractText")

        for ab in abstract_nodes:
            part_text = "".join(ab.itertext()).strip()
            if part_text:
                label = ab.get("Label")
                if label and not part_text.upper().startswith(f"{label.upper()}:"):
                    abstract_parts.append(f"{label}: {part_text}")
                else:
                    abstract_parts.append(part_text)

        abstract = " ".join(abstract_parts) if abstract_parts else "No abstract available."

        # 4. Journal
        journal_el = article.find(".//Journal/Title")
        if journal_el is None or not journal_el.text:
            journal_el = article.find(".//Journal/ISOAbbreviation")
        if journal_el is None or not journal_el.text:
            journal_el = article.find(".//MedlineJournalInfo/MedlineTA")
        journal = "".join(journal_el.itertext()).strip() if journal_el is not None else "PubMed Central"
        if not journal:
            journal = "PubMed Central"

        # 5. Authors (individual names or collective investigator names)
        authors_list = []
        for author in article.findall(".//AuthorList/Author"):
            collective = author.find("CollectiveName")
            if collective is not None and collective.text:
                authors_list.append(collective.text.strip())
                continue

            last = author.find("LastName")
            fore = author.find("ForeName")
            initials = author.find("Initials")
            if last is not None and last.text:
                last_name = last.text.strip()
                if fore is not None and fore.text:
                    first_initial = f"{fore.text.strip()[0]}."
                    authors_list.append(f"{first_initial} {last_name}")
                elif initials is not None and initials.text:
                    authors_list.append(f"{initials.text.strip()} {last_name}")
                else:
                    authors_list.append(last_name)

        authors = " · ".join(authors_list[:3]) if authors_list else "Unknown Authors"

        # 6. Date
        year_el = article.find(".//JournalIssue/PubDate/Year")
        if year_el is None or not year_el.text:
            year_el = article.find(".//JournalIssue/PubDate/MedlineDate")
        if year_el is None or not year_el.text:
            year_el = article.find(".//DateCompleted/Year")
        if year_el is None or not year_el.text:
            year_el = article.find(".//DateRevised/Year")
        year = year_el.text.strip() if year_el is not None and year_el.text else "2024"

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

    return papers
