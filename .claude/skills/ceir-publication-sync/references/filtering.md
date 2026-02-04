# Publication Filtering Rules

## Include

- Papers where at least one CEIR team member is an author
- Papers published during the author's BIH/CEIR affiliation period
- All types: journal articles, conference papers, book chapters, editorials, preprints

## Exclude (flag for manual review)

Publications from team members that predate BIH affiliation or are unrelated clinical work.

### Known False Positives by Member

| Member | Topic to Exclude | Reason |
|--------|-----------------|--------|
| Bartschke | Hepatoblastoma, pediatric oncology | Pre-BIH clinical work |
| Klopfenstein | ICU alarm management (standalone) | Clinical research; include if tied to FHIR/interop |
| Salgado | HIV, transplant immunology | Pre-BIH clinical work |
| Gatrio | Fetal cardiology | Pre-BIH clinical work |
| Hübner | Fetal cardiology | Pre-BIH clinical work |

### Keyword Heuristic

Flag for manual review if **none** of these terms appear in title, abstract, or journal name:

```
FHIR, interoperability, SNOMED, LOINC, terminolog*, digital health,
standardiz*, COVID, GECCO, rare disease, phenopacket, FAIR,
health data, MII, NFDI, HL7, ICD, openEHR, OMOP
```

## Edge Cases

- **Consortium papers** ("et al."): Forschungsdatenbank catches team members via `internal_authors` field even when hidden behind "et al." on the BIH website
- **25 excluded papers** in `2026-02-04-publication-sync-plan.md`: Consortium papers where no CEIR surname was visible on the website but may appear in API results
- **Dual-affiliation papers**: Some members have clinical roles alongside CEIR — include if the paper relates to digital health / interoperability topics
