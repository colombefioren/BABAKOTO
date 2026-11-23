# babakoto-malagasy-text

Turns written text into text a TTS model can read aloud in Malagasy.

```python
from malagasy_text import normalize

normalize("Mitentina 15000 Ar ny entana")
# "Mitentina dimy ambin'ny folo arivo ariary ny entana"
```

Handles integers and decimals, Ariary (`Ar`, `Ariary`, `MGA`), percentages, times (`14:30`,
`8h`), dates (`25/12/2024`), phone numbers (read digit by digit), a few units and common
abbreviations. Other text, including French, passes through unchanged.

All number words and abbreviation expansions await native-speaker review; test cases that depend
on them carry a `# NEEDS_REVIEW` comment. See `docs/NEEDS_NATIVE_REVIEW.md` and ADR-0013.
