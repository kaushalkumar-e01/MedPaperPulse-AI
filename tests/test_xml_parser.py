"""Unit tests for PubMed XML and MEDLINE parsing."""

import xml.etree.ElementTree as ET
import pytest
from app.ingestion.xml_parser import parse_pubmed_xml


SAMPLE_VALID_XML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE">
      <PMID Version="1">39240188</PMID>
      <Article PubModel="Print">
        <Journal>
          <Title>Nature Digital Medicine</Title>
          <JournalIssue>
            <PubDate><Year>2024</Year></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Neurosymbolic reasoning for <i>multimodal</i> oncology decision support.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Neurosymbolic architectures combine learned representations.</AbstractText>
          <AbstractText Label="METHODS">We evaluated a hybrid architecture across 12 cancer types.</AbstractText>
          <AbstractText Label="RESULTS">The hybrid model improved evidence alignment by 18.6 percentage points.</AbstractText>
          <AbstractText Label="CONCLUSIONS">Clinicians rated explanations as more actionable.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Mehta</LastName>
            <ForeName>Aarav</ForeName>
          </Author>
          <Author>
            <LastName>Solberg</LastName>
            <ForeName>Lars</ForeName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

SAMPLE_COLLECTIVE_AUTHOR_XML = """<?xml version="1.0" encoding="utf-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>35658000</PMID>
      <Article>
        <Journal><Title>The Lancet</Title><JournalIssue><PubDate><MedlineDate>2023 Nov-Dec</MedlineDate></PubDate></JournalIssue></Journal>
        <ArticleTitle>Tirzepatide Clinical Outcomes in Obesity</ArticleTitle>
        <Abstract>
          <AbstractText>Weight loss was significant across all dosage cohorts.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <CollectiveName>The SURMOUNT-1 Study Group</CollectiveName>
          </Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""

SAMPLE_MISSING_ABSTRACT_XML = """<?xml version="1.0" encoding="utf-8"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>11223344</PMID>
      <Article>
        <Journal><Title>BMJ</Title><JournalIssue><PubDate><Year>2022</Year></PubDate></JournalIssue></Journal>
        <ArticleTitle>Letter to the Editor on Primary Care Guidelines</ArticleTitle>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_parse_pubmed_xml_valid():
    papers = parse_pubmed_xml(SAMPLE_VALID_XML)
    assert len(papers) == 1
    p = papers[0]
    assert p.id == "pmid_39240188"
    assert "Neurosymbolic reasoning for multimodal oncology" in p.title
    assert "Nature Digital Medicine" in p.journal
    assert "2024" in p.date
    assert "A. Mehta" in p.authors
    assert "BACKGROUND:" in p.abstract
    assert "RESULTS:" in p.abstract
    assert "18.6 percentage points" in p.abstract


def test_parse_pubmed_xml_collective_author_and_medline_date():
    papers = parse_pubmed_xml(SAMPLE_COLLECTIVE_AUTHOR_XML)
    assert len(papers) == 1
    p = papers[0]
    assert p.id == "pmid_35658000"
    assert p.authors == "The SURMOUNT-1 Study Group"
    assert "2023 Nov-Dec" in p.date


def test_parse_pubmed_xml_missing_abstract():
    papers = parse_pubmed_xml(SAMPLE_MISSING_ABSTRACT_XML)
    assert len(papers) == 1
    assert papers[0].abstract == "No abstract available."


def test_parse_pubmed_xml_empty_input():
    assert parse_pubmed_xml("") == []
    assert parse_pubmed_xml("   ") == []


def test_parse_pubmed_xml_malformed_raises():
    with pytest.raises(ET.ParseError):
        parse_pubmed_xml("<PubmedArticleSet><UnclosedTag>")
