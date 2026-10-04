# Fixes Applied - 2026-10-04

## Summary

Applied 3 fixes to the essay integrity checker:

| Fix | File | Status |
|-----|------|--------|
| GROBID `is_available` | `grobid_service.py` | ✅ |
| Consensus counting | `source.py` | ✅ |
| Web resource detection | `neuro_symbolic_checker.py` | ✅ |

---

## Fix #1: GROBID `is_available` Property

**File:** `src/integrity_checker/extraction/grobid_service.py`

**Problem:** `is_available` property returned `False` even when GROBID was running and responding. The property only checked the cached `_status` field which was never refreshed.

**Fix:**
```python
@property
def is_available(self) -> bool:
    """True nếu GROBID đang available.

    Refreshes status by calling check_health() to ensure we detect
    if GROBID became available after initialization.
    """
    self.check_health()  # Refresh status
    return self._status == GROBID_STATUS.AVAILABLE
```

**Result:** GROBID container now properly detected → reference extraction uses GROBID instead of regex fallback.

---

## Fix #2: Consensus Counting

**File:** `src/integrity_checker/models/source.py`

**Problem:** `consensus_count()` counted the number of sources with ANY candidate, not the number of sources agreeing on the SAME paper.

```python
# Before (WRONG):
def consensus_count(self) -> int:
    seen: set[str] = set()
    for c in self.candidates:
        if c.found and (c.doi or c.title):
            seen.add(c.fingerprint())
    return len(seen)  # Returns 3 even if 3 sources found DIFFERENT papers
```

**Fix:**
```python
def consensus_count(self) -> int:
    """Số nguồn đồng thuận trên cùng một paper.

    Đếm số nguồn TRÙNG NHAU trên cùng fingerprint (DOI hoặc title).
    - 3 nguồn cùng trả về DOI giống nhau → consensus = 3
    - 3 nguồn trả về 3 papers khác nhau → consensus = 1
    """
    from collections import Counter
    fingerprints = []
    for c in self.candidates:
        if c.found and (c.doi or c.title):
            fingerprints.append(c.fingerprint())

    if not fingerprints:
        return 0

    count_by_fp = Counter(fingerprints)
    return max(count_by_fp.values())
```

**Result:** Citation [5] V. A. Ho now shows `consensus=1` instead of `consensus=3` (3 sources found 3 different papers).

---

## Fix #3: Web Resource Detection

**File:** `src/integrity_checker/logic/neuro_symbolic_checker.py`

**Problem:** Citation "Google YouTube Data API v3" was classified as `metadata_error` instead of `resource`. The existing URL detection only matched citations starting with `https://` or `www.`.

**Fix:** Added new patterns to detect web resources/API citations in various formats:

```python
web_resource_patterns = [
    # Company, "Product/Service Name," Company
    re.compile(r'^(Google|Microsoft|Amazon|...)\s*...', re.IGNORECASE),

    # "Product/Service Name," Organization (title-first)
    re.compile(r'^["“](YouTube\s*Data\s*API|Google\s*API|...)', re.IGNORECASE),

    # Developer/Documentation keyword
    re.compile(r'(Google\s+for\s+Developers|Developer\s+Documentation|...)', re.IGNORECASE),

    # Company name + API/SDK/Tool keyword (short form from GROBID)
    # Ví dụ: "Google YouTube Data API v3", "Google Maps API", "AWS SDK"
    re.compile(r'^(Google|Amazon|Microsoft|GitHub|...)\s+(YouTube|Maps|AWS|...)', re.IGNORECASE),

    # Common API/SDK patterns
    re.compile(r'^(Google\s+YouTube\s+Data\s*API|YouTube\s+Data\s*API|...)', re.IGNORECASE),
]
```

**Result:** "Google YouTube Data API v3" now correctly classified as `resource` with `R-WEB-RESOURCE` rule.

---

## Test Results

| File | CIS | Verified | Unresolved | Resource | GROBID |
|------|-----|----------|-----------|----------|--------|
| TranThanhPhuoc | 81.4 | 16 | 14 | 1 | ✅ |
| VietDepression | 86.2 | 11 | 7 | 1 | ✅ |
| Thesis | 77.4 | 16 | 22 | 1 | ✅ |

### Changes from before fix:
- GROBID now working → better reference extraction
- Consensus counting now accurate → more realistic confidence scores
- Web resources properly classified as `resource` instead of `metadata_error`

---

## Files Changed

1. `src/integrity_checker/extraction/grobid_service.py`
2. `src/integrity_checker/models/source.py`
3. `src/integrity_checker/logic/neuro_symbolic_checker.py`
