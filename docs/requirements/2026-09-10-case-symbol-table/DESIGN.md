# Design: Case Symbol Table (tier 1 only)

**Date:** 2026-09-10

The original 513-line file is gone. Reconstruct from ARCHITECTURE + the
pre-governance inventory, not from memory of unreadable bytes.

```python
@dataclass
class SymbolSite:
    document_id: str
    text: str          # verbatim
    kind: str          # PERSON | ORG | AMOUNT | PROVISION | CASE_NUMBER
    span: tuple[int, int]
    page: int | None

@dataclass
class Symbol:
    key: str
    kind: str
    sites: list[SymbolSite]   # [0] is the definition site
    aliases: list[str]

class SymbolTable:
    def add(self, site: SymbolSite) -> str: ...
    def go_to_definition(self, key: str) -> SymbolSite | None: ...
    def find_all_references(self, key: str) -> list[SymbolSite]: ...
    def merge_from(self, other: "SymbolTable") -> None: ...
```

`normalize_name`: casefold, collapse whitespace, strip legal suffixes via the
same idea as `casemap_pipeline._canonical_key` (import that function to avoid
two keys for the same company).

`normalize_amount`: digits-only integer rupees from `Rs./₹/INR` strings;
optional lakh/crore multiplier. `amount_from_words`: Indian numbering words
→ same integer; return None if unparseable (do not guess).

Build table from existing extractors only (`extract_deterministic`,
`extract_entities` / party names) — no second extraction path.
