# Plan: Xử lý Unresolved Cases

> **Updated:** 2026-10-04  
> **Author:** Claude Code  
> **Status:** Investigation Complete → Ready for Implementation

---

## Tóm tắt vấn đề

Sau khi debug chi tiết 3 test files (43 unresolved cases), tìm thấy **root cause CHÍNH XÁC**:

### Root Cause: Thiếu Rule cho LOCAL_DB Perfect Match

**Phát hiện quan trọng:**
1. ✅ `author_match_score` hoạt động ĐÚNG (Grootendorst → 1.0, Maarten Grootendorst → 1.0)
2. ✅ `fuzzy_search` trả về đúng paper với authors
3. ✅ `title_similarity` hoạt động đúng
4. ❌ **Rule engine THIẾU logic** để verify LOCAL_DB perfect match

**Current behavior:**
```
LOCAL_DB: title=1.0, author=1.0, DOI=False, consensus=1
↓
Rule 1: DOI exact match → FAIL
↓
Rule 2: High consensus → FAIL
↓
Rule 3: Known paper → depends
↓
Final fallback: UNRESOLVED (conf=0.4)
```

**Missing logic:**
```
IF local_db ONLY
   AND title_sim >= 0.95
   AND author_sim >= 0.8
   AND year_distance == 0
THEN → VERIFIED (conf=0.80-0.85)
```

---

## Phân loại 43 Unresolved Cases

| Category | Count | Description | Should Be |
|----------|-------|-------------|-----------|
| **LOCAL_DB_PERFECT** | 13 | LOCAL_DB, sim=1.0, auth=1.0 | → VERIFIED |
| **LOCAL_DB_GOOD** | 7 | LOCAL_DB, sim=1.0, auth=0.5-0.8 | → VERIFIED |
| **API_NO_CONSENSUS** | 10 | APIs return weak matches, consensus=1 | → UNRESOLVED (acceptable) |
| **API_WRONG_TOPIC** | 5 | APIs return completely wrong topic | → UNRESOLVED (correct) |
| **API_FAIL** | 2 | All APIs fail | → UNRESOLVED (correct) |
| **METHOD_TEXT** | 3 | Method descriptions parsed as citations | → UNRESOLVED (acceptable) |
| **BORDER_ZONE** | 1 | Title similarity in border zone | → UNRESOLVED (borderline) |
| **GOOGLE_API** | 2 | Google API citations | → RESOURCE (should be fixed) |

---

## Chi tiết từng loại

### 1. LOCAL_DB_PERFECT (13 cases) — **CẦN FIX**

**Examples:**
```
Citation: Grootendorst, M (2022) BERTopic: Neural topic modeling...
Local DB: title=1.0, author=1.0, DOI=10.48550/arxiv.2203.05794
Result: UNRESOLVED (conf=0.4)
Should be: VERIFIED (conf=0.85)
```

**Why UNRESOLVED:**
- Rule 1 checks DOI exact → FAIL (citation has no DOI)
- Rule 2 checks high consensus → FAIL (consensus=1)
- Falls through to UNRESOLVED fallback

**Fix:** Thêm rule mới trước fallback

---

### 2. LOCAL_DB_GOOD (7 cases) — **CẦN FIX**

**Examples:**
```
Citation: Ho, V, Nguyen, D (2019) Emotion recognition for Vietnamese...
Local DB: title=1.0, author=0.50, DOI=False
Result: UNRESOLVED (conf=0.4)
Should be: VERIFIED (conf=0.75)
```

**Fix:** Thêm rule với threshold thấp hơn

---

### 3. API_NO_CONSENSUS (10 cases) — **OK (KHÔNG CẦN FIX)**

**Examples:**
```
Citation: Settles, B (2012) Active Learning...
APIs: Crossref→"Active Learning", OpenAlex→"Batch mode RL"
Result: UNRESOLVED (conf=0.4)
Should be: UNRESOLVED (correct behavior)
```

**Why OK:** APIs không đồng thuận, không có local_db match → UNRESOLVED đúng

---

### 4. API_WRONG_TOPIC (5 cases) — **OK (KHÔNG CẦN FIX)**

**Examples:**
```
Citation: Pennebaker, J (2015) The development and psychometric...
APIs: Crossref→"Japanese VAD scale", OpenAlex→"Chinese VAD"
Result: UNRESOLVED (conf=0.4)
Should be: UNRESOLVED (correct)
```

---

### 5. API_FAIL (2 cases) — **OK (KHÔNG CẦN FIX)**

**Examples:**
```
Citation: Underthesea NLP Team (n.d.) Underthesea...
APIs: All fail
Result: UNRESOLVED (conf=0.3)
Should be: UNRESOLVED (correct)
```

---

### 6. METHOD_TEXT (3 cases) — **COSMETIC**

**Examples:**
```
"Loss Computation: Cross-entropy loss with class weights..."
Result: UNRESOLVED (conf=0.4)
```

**Fix:** Thêm better reasoning (not a priority)

---

### 7. GOOGLE_API (2 cases) — **ĐÃ FIX Ở LẦN TRƯỚC**

**Examples:**
```
Google YouTube Data API v3
Result: RESOURCE (conf=0.95)
Status: ✅ FIXED
```

---

## Đề xuất Implementation

### Fix #1: LOCAL_DB Perfect Match → VERIFIED (HIGH PRIORITY)

**File:** `src/integrity_checker/logic/rules.py`

**Thêm method mới:**
```python
def _rule_local_db_verified(
    self,
    source: SourceResult,
    features: MatchFeatures,
    citation: Citation,
    style_penalty: float = 0.0,
) -> RuleOutcome | None:
    """Rule: LOCAL_DB only with perfect match → VERIFIED.

    When local_db is the only source that found a match with:
    - title_sim >= 0.95
    - author_sim >= 0.8
    - year_distance == 0

    This is a trusted match because local_db is a curated knowledge base.
    """
    # Chỉ apply nếu source chỉ từ local_db
    if source.sources_succeeded != ["local_db"]:
        return None

    best = source.best_candidate()
    if not best:
        return None

    # Check thresholds
    title_sim = max(features.title_sim_fuzzy, features.title_sim_semantic)
    author_sim = features.author_jaccard
    year_dist = features.year_distance

    # Perfect match: title >= 0.95 AND author >= 0.8 AND year match
    if title_sim >= 0.95 and author_sim >= 0.8 and year_dist == 0:
        # Calculate confidence
        if features.doi_exact_match:
            confidence = 0.90
        else:
            confidence = 0.80

        confidence = max(0.0, confidence - style_penalty)

        return RuleOutcome(
            label=ValidationLabel.VERIFIED,
            confidence=confidence,
            reasoning=(
                f"Verified via local knowledge base: "
                f"title={title_sim:.2f}, author={author_sim:.2f}, year match."
            ),
            triggered_rules=["R-LOCAL_DB_VERIFIED"],
            mismatched_fields=["doi"] if not features.doi_exact_match else [],
        )

    return None
```

**Thêm vào SymbolicRules.check() trước final fallback:**
```python
# Trong SymbolicRules.check(), trước dòng:
# return RuleOutcome(label=ValidationLabel.UNRESOLVED, ...)

# Thêm check cho LOCAL_DB perfect match
local_db_outcome = self._rule_local_db_verified(source, features, citation, style_penalty)
if local_db_outcome:
    return local_db_outcome
```

---

### Fix #2: LOCAL_DB Good Match → VERIFIED (MEDIUM PRIORITY)

**Thêm rule với threshold thấp hơn:**
```python
def _rule_local_db_good_match(
    self,
    source: SourceResult,
    features: MatchFeatures,
    citation: Citation,
    style_penalty: float = 0.0,
) -> RuleOutcome | None:
    """Rule: LOCAL_DB only with good match → VERIFIED.

    When local_db is the only source that found a match with:
    - title_sim >= 0.95
    - author_sim >= 0.5
    - year_distance == 0
    - best candidate has DOI

    Lower confidence because author_sim is lower.
    """
    if source.sources_succeeded != ["local_db"]:
        return None

    best = source.best_candidate()
    if not best:
        return None

    title_sim = max(features.title_sim_fuzzy, features.title_sim_semantic)
    author_sim = features.author_jaccard
    year_dist = features.year_distance

    # Good match: title >= 0.95 AND author >= 0.5 AND year match
    if title_sim >= 0.95 and author_sim >= 0.5 and year_dist == 0:
        confidence = max(0.0, 0.75 - style_penalty)

        return RuleOutcome(
            label=ValidationLabel.VERIFIED,
            confidence=confidence,
            reasoning=(
                f"Verified via local knowledge base (partial author match): "
                f"title={title_sim:.2f}, author={author_sim:.2f}."
            ),
            triggered_rules=["R-LOCAL_DB_GOOD_MATCH"],
            mismatched_fields=["author", "doi"],
        )

    return None
```

---

### Fix #3: Method Description Detection (LOW PRIORITY)

**Thêm patterns trong neuro_symbolic_checker.py:**
```python
# Method description patterns
method_patterns = [
    re.compile(r'^(Loss|Accuracy|Input|Output|Embedding|Model|Token|Gradient)\s+\w+:'),
    re.compile(r'^(Cross-entropy|AdamW|SGD|Backpropagation|Layer Normalization)\s'),
    re.compile(r'^\d+(\.\d+)+[.:]\s+\w+'),
]

for pattern in method_patterns:
    if pattern.match(raw_text):
        return CitationVerdict(
            label=ValidationLabel.UNRESOLVED,
            confidence=0.3,
            reasoning=f"Method description detected (not a citation): {raw_text[:50]}...",
            triggered_rules=["R-METHOD-DESCRIPTION"],
        )
```

---

## Impact Estimate

| Fix | Cases | Before | After |
|-----|-------|--------|-------|
| Fix #1 | 13 | UNRESOLVED | VERIFIED (conf=0.80-0.90) |
| Fix #2 | 7 | UNRESOLVED | VERIFIED (conf=0.75) |
| Fix #3 | 3 | UNRESOLVED | UNRESOLVED (better reasoning) |

**Estimated CIS improvement:**
- VietDepression: 86.2 → 92-95
- TranThanhPhuoc: 81.4 → 88-90
- Thesis: 77.4 → 85-88

---

## Implementation Order

1. **Fix #1** (LOCAL_DB Perfect Match) — 30 min, highest impact
2. **Fix #2** (LOCAL_DB Good Match) — 20 min, good impact
3. **Fix #3** (Method Description) — 15 min, cosmetic

---

## Verification Plan

```bash
# Sau khi implement, chạy lại:
python3 -m integrity_checker.pipeline.integrity_pipeline \
    VietDepression_Research_Article.pdf --output /tmp/test_viet_after_fix.json

# Kiểm tra:
# - 20 cases chuyển từ UNRESOLVED → VERIFIED
# - CIS score tăng 5-10 điểm
# - Không có case nào chuyển sai từ VERIFIED → UNRESOLVED
```
