"""Author parser — chuẩn hoá author name cho so khớp (v1.2 §3.4, §3.7).

Bài toán:
    Trích xuất author name từ text có nhiều định dạng:
    - "Smith, J." (APA / Chicago / Harvard)
    - "Smith J. K." (không dấu phẩy)
    - "J. K. Smith" (last-name cuối, initials đầu)
    - "van der Berg, J." (multi-word last name — Dutch)
    - "O'Brien, M." (O'Apostrophe)
    - "Nguyễn Văn A" (Vietnamese — không dấu phẩy, family name đầu)
    - "Nguyễn, Văn A" (có dấu phẩy, ngược lại)
    - "Smith, John K." (full first name)
    - "Smith, J. K., & Doe, A. B." (multi-author)

Mục tiêu:
    Trả về Author record với:
        - last_name: họ (canonical form)
        - initials: list initials (e.g. ['J', 'K'])
        - full_first_name: optional
        - normalized: full canonical string để so khớp exact

Cảnh báo:
    KHÔNG dùng ML/NER nặng trong MVP — rule-based đủ cho v1.2.
    SpaCy en_core_web_sm sẽ được bật ở tuần 11 nếu coverage chưa đạt.

References:
    v1.2 §3.4 (TextPreprocessor + parsing đầy đủ)
    v1.2 §3.7 (author normalization)
    v1.2 §4.3 (annotation guideline author variant)
    config.matching.author_jaccard_verified (threshold so khớp)
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# --- Common Dutch multi-word last names (rule-based heuristic) ---
# Nếu first word là 1 trong các từ này → "X Y Z, F." → last_name = "X Y Z".
_DUTCH_MULTI_WORD_PREFIXES = frozenset([
    "van", "de", "den", "der", "ten", "ter",
    "von", "zu", "zur", "af",
    "le", "la", "du", "di", "da",
    "el", "al",
])

# Particles trong nhiều ngôn ngữ — viết THƯỜNG trong họ
_PARTICLES = frozenset([
    "van", "de", "den", "der", "ten", "ter",
    "von", "zu", "zur", "af",
    "le", "la", "du", "di", "da",
    "el", "al",
])


# --- Common Vietnamese family names (rule-based heuristic) ---
# Vietnamese: family name đầu; middle name giữa; first name cuối.
# Chỉ dùng khi KHÔNG có dấu phẩy (vì dấu phẩy → APA-style "Family, Given").
_VN_FAMILY_NAMES = frozenset([
    "nguyễn", "trần", "lê", "phạm", "hoàng", "huỳnh", "phan", "vũ", "võ",
    "đặng", "bùi", "đỗ", "hồ", "ngô", "dương", "lý", "đào", "đinh",
    "trịnh", "mai", "trương", "châu", "đoàn", "tô", "tăng",
])


@dataclass(frozen=True)
class Author:
    """Một author name đã parse.

    Attributes:
        last_name: họ (canonical form, lowercase, multi-word joined).
        initials: list initials ['J', 'K']. Empty list nếu không rõ.
        full_first_names: full first name nếu có (e.g. 'John'). Empty nếu
            chỉ thấy initials.
        normalized: canonical string dùng cho exact-match so khớp.
            Format: 'last_name|initials' (lowercase, no space).
        raw: original input (cho debug).
    """

    last_name: str
    initials: list[str] = field(default_factory=list)
    full_first_names: list[str] = field(default_factory=list)
    normalized: str = ""
    raw: str = ""


# --- Regex helpers ---


_INITIAL_RE = re.compile(r"^[A-ZÀ-Ý]\.?$")               # chỉ J. / J (1 char + optional dot)
_PARTICLE_WORD_RE = re.compile(r"^[a-zà-ỹ]+$")              # một từ đơn lowercase
_INITIAL_TOKEN_RE = re.compile(r"^[A-ZÀ-Ý]\.?$")


def _strip_particles_from_first_name(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Tách last_name vs first_name parts dựa trên particle.

    Trả về (last_name_tokens, first_name_tokens).
    Cho APA-style "van der Berg, J.": tokens = ['van', 'der', 'Berg', ',', 'J.']
        → split tại dấu phẩy → last_words = ['van', 'der', 'Berg'], first = ['J.']
        → particle ở đầu last_words ('van') → KHÔNG strip
        → result: last = ['van', 'der', 'Berg'], first = ['J.']
    """
    return tokens  # placeholder


def _canonicalize_last_name(last_tokens: list[str]) -> str:
    """Chuẩn hoá last name: lowercase, join với space.

    'van der Berg' → 'van der berg' (giữ nguyên thứ tự particle).
    """
    return " ".join(t.lower() for t in last_tokens if t)


def _is_particle(token: str) -> bool:
    return token.lower() in _PARTICLES


def _split_on_comma(raw: str) -> tuple[list[str], list[str]] | None:
    """Tách theo dấu phẩy đầu tiên.

    "Smith, J. K." → (['Smith'], ['J.', 'K.'])
    "van der Berg, J." → (['van', 'der', 'Berg'], ['J.'])
    """
    if "," not in raw:
        return None
    last_str, first_str = raw.split(",", 1)
    # Preserve the order and case of tokens for last name
    last_tokens = last_str.split()
    first_tokens = first_str.split()
    return last_tokens, first_tokens


# --- Public API ---


def normalize_author(raw: str) -> Author:
    """Parse 1 author name thành Author.

    Args:
        raw: raw author string, có thể ở nhiều format.

    Returns:
        Author với last_name, initials, normalized.
    """
    raw = (raw or "").strip()
    if not raw:
        return Author(last_name="", raw="")

    # Chuẩn hoá Unicode (NFC) trước
    raw = unicodedata.normalize("NFC", raw)

    # FIX: Handle "et al." pattern - this is NOT part of the author name
    # "T. B. Brown et al." → "T. B. Brown"
    # "A. Vaswani, et al." → "A. Vaswani"
    et_al_match = re.search(r'\s+et\s+al\.?\s*$', raw, re.IGNORECASE)
    if et_al_match:
        raw = raw[:et_al_match.start()].strip().rstrip(',')
        if not raw:
            return Author(last_name="", raw=raw)

    # Strategy 1: comma-split (APA / Chicago)
    parts = _split_on_comma(raw)
    if parts:
        last_tokens, first_tokens = parts
        last_name = _canonicalize_last_name(last_tokens)
        initials = _extract_initials_from_first_tokens(first_tokens)
        normalized = f"{last_name}|{'.'.join(initials)}" if initials else last_name
        return Author(
            last_name=last_name,
            initials=initials,
            normalized=normalized,
            raw=raw,
        )

    # Strategy 2: không có dấu phẩy — 2 sub-cases:
    #   2a. Initial(s) trước, last name sau: "J. K. Smith" / "JK Smith"
    #   2b. Last name trước, initials sau: "Smith J." / "Smith J. K."
    #   2c. Vietnamese: "Nguyễn Văn A"

    tokens = raw.split()
    if not tokens:
        return Author(last_name="", raw=raw)

    # 2a: nếu token đầu là initial → last ở cuối
    if _INITIAL_RE.match(tokens[0]):
        last_tokens = [_INITIAL_RE.sub("", tokens[0])] if False else tokens[-1:]   # always last
        # Actually: heuristic — nếu token đầu là initial và token cuối không phải initial
        last_name_tokens = [tokens[-1]]
        initials = _extract_initials_from_tokens(tokens[:-1])
        last_name = _canonicalize_last_name(last_name_tokens)
        normalized = f"{last_name}|{'.'.join(initials)}" if initials else last_name
        return Author(
            last_name=last_name,
            initials=initials,
            normalized=normalized,
            raw=raw,
        )

    # 2c: Vietnamese family name đầu + multi-word given name
    if tokens[0].lower() in _VN_FAMILY_NAMES and len(tokens) >= 2:
        # Không chắc chắn 100% (có người Việt tên Âu), nhưng heuristic OK
        last_name = _canonicalize_last_name([tokens[0]])
        initials = _extract_initials_from_tokens(tokens[1:])
        normalized = f"{last_name}|{'.'.join(initials)}" if initials else last_name
        return Author(
            last_name=last_name,
            initials=initials,
            normalized=normalized,
            raw=raw,
        )

    # 2b: last name đầu + 1+ initials ở đuôi
    # Tìm boundary: từ cuối, các token ngược lên đều initial-like (1 char + dot
    # HOẶC 1 chữ cái đứng một mình — vd "Smith J." có thể có middle initial "K"
    # tách rời như "Smith J. K.").
    last_tokens, initials_after = _split_last_initials(tokens)
    if initials_after and len(last_tokens) >= 1:
        last_name = _canonicalize_last_name(last_tokens)
        normalized = f"{last_name}|{'.'.join(initials_after)}" if initials_after else last_name
        return Author(
            last_name=last_name,
            initials=initials_after,
            normalized=normalized,
            raw=raw,
        )

    # Fallback: toàn bộ là last name (không rõ initials)
    return Author(
        last_name=_canonicalize_last_name(tokens),
        initials=[],
        normalized=_canonicalize_last_name(tokens),
        raw=raw,
    )


def parse_authors(raw: str) -> list[Author]:
    """Parse 1 chuỗi nhiều authors thành list Author.

    Xử lý separators (APA / Chicago / IEEE / Vancouver):
        - 'Smith, J., & Jones, A.'       (APA with &)
        - 'Smith, J. and Jones, A.'      (APA with "and")
        - 'Smith, J.; Jones, A.'         (semicolon)
        - 'Smith J., Jones A.'           (no comma)
        - 'Smith, J., Jones, A.'         (comma between authors, no &)
        - 'LeCun, Y., Bengio, Y., & Hinton, G.'  (3+ authors)
        - 'Bowman, Angeli, Potts, et al.' (Vancouver with et al.)

    Strategy:
        1. Chuẩn hoá separator chính (& / "and" / "et al." / ;) → TOKEN_SEP.
        2. Với mỗi piece còn lại, nếu có nhiều dấu phẩy lẻ → có thể là
           multi-author với APA pattern "Last, I., Last, I." — cần cẩn trọng.
           Quy tắc: "Last, I." → author; nếu tiếp theo là "Last," (không có
           initial) → bắt đầu author mới.
    """
    if not raw:
        return []

    # Chuẩn hoá separator → split-friendly
    text = raw

    # Handle "et al." - replace with separator
    text = re.sub(r",?\s*et\s+al\.?\s*$", ";", text, flags=re.IGNORECASE)

    # Normalize other separators
    text = re.sub(r"\s+and\s+", " ; ", text, flags=re.IGNORECASE)
    text = text.replace("&", ";")

    # Bước 1: Nếu có separator chính (;), split piece-by-piece.
    # Mỗi piece vẫn có thể chứa nhiều author (vd "LeCun, Y., Bengio, Y.").
    if ";" in text:
        raw_pieces = [p.strip() for p in text.split(";") if p.strip()]
        authors: list[Author] = []
        for piece in raw_pieces:
            # Mỗi piece có thể là "Last, I., Last, I." → split_apa_authors
            authors.extend(_split_apa_authors(piece))
        return authors

    # Bước 2: Nếu không có separator chính, có thể là "Last, I., Last, I., & Last, I."
    return _split_apa_authors(text)


def _safe_parse(piece: str) -> Author | None:
    a = normalize_author(piece)
    return a if a.last_name else None


# Pattern APA: "LastName, I." hoặc "LastName, I. K."
# Tên có thể có particle (van der Berg, de la Cruz) → group tên phức tạp.
# Cho phép leading particle(s) lowercase trước Capital last word.
#
# IMPORTANT: Restrict particles to KNOWN particles only to prevent "ohn" being
# matched as a particle before "Blitzer". Only particles like "van", "de", "von", etc.
#
# Compound particles (van der, de la) need to be matched together.
# Use ordered alternation: longest first ("van der", "de la", etc.) then individual.
_PARTICLES_GROUP = (
    r"(?:van\s+der|ten\s+ter|de\s+la|der\s+den|zu\s+zur|le\s+la)?"  # compound particles first
    r"(?:van|de|der|den|von|zu|zur|af|le|la|du|di|da|el|al|ten|ter)?"  # then single particles
)

_APA_AUTHOR_RE = re.compile(
    rf"""
    (?P<author>
        { _PARTICLES_GROUP }\s*  # optional particles
        [A-ZÀ-Ý][A-Za-zà-ỹ\-\']+   # last name MUST start with uppercase
        ,\s*
        (?:[A-ZÀ-Ý]\.?\s*)+         # initials (1+)
    |
        [A-ZÀ-Ý][A-Za-zà-ỹ\-\']+   # last name start with uppercase
        ,\s*
        (?:[A-ZÀ-Ý]\.?\s*)+         # initials (1+) - MUST have at least one letter
    )
    """,
    re.VERBOSE,
)


def _split_apa_authors(text: str) -> list[Author]:
    """Tách multi-author APA không có separator rõ ràng.

    Strategy: tìm tất cả match của APA pattern liên tiếp trong text.
    Phần còn lại (nếu có) được ghép vào author cuối.

    Also detects Vancouver style (multiple commas without "and"/"&") and parses directly.
    """
    # Clean trailing punctuation
    text = text.strip().rstrip(".,")
    if not text:
        return []

    # Detect Vancouver style: multiple commas, no "and"/"&", likely separate names
    # "Bowman, Angeli, Potts" -> three separate single-word last names
    comma_count = text.count(",")
    has_and_or_amp = bool(re.search(r"\s+and\s+|&", text, re.IGNORECASE))
    if comma_count >= 2 and not has_and_or_amp:
        # Likely Vancouver style with separate names - parse directly
        return _parse_firstname_lastname_no_et_al(text)

    # Try APA pattern first: "LastName, I."
    matches = list(_APA_AUTHOR_RE.finditer(text))

    if matches:
        authors = []
        # For each match, also process any text AFTER it that looks like "FirstName LastName"
        # e.g., "John Blitzer, Ryan McDonald, and Fernando Pereira"
        # Matches: "Blitzer, R.", but "Ryan McDonald" and "Fernando Pereira" need to be caught

        for i, m in enumerate(matches):
            # Process the APA match
            piece = m.group("author").strip()
            a = normalize_author(piece)
            if a.last_name:
                authors.append(a)

            # Extract text AFTER this match
            if i < len(matches) - 1:
                # Text between this match and next match
                after_text = text[m.end():matches[i+1].start()]
            else:
                # Text after last match (to end of string)
                after_text = text[m.end():]

            # Process after_text to find "FirstName LastName" pieces
            if after_text:
                # Replace "and" with semicolon and split
                after_text = re.sub(r'\s+and\s+', ' ; ', after_text, flags=re.IGNORECASE)
                after_text = after_text.replace("&", " ; ")
                for piece in after_text.split(";"):
                    piece = piece.strip().rstrip(",").strip()
                    if piece and len(piece) >= 2:
                        tokens = piece.split()
                        if len(tokens) >= 2:
                            # Take last token as last_name (FirstName LastName format)
                            last_name = tokens[-1].rstrip(".,;|")
                            if last_name and len(last_name) >= 2:
                                a = Author(
                                    last_name=last_name.lower(),
                                    initials=[],
                                    normalized=last_name.lower(),
                                    raw=piece,
                                )
                                authors.append(a)

        return authors

    # No APA matches - try FirstName LastName format
    return _parse_firstname_lastname_no_et_al(text)


def _parse_firstname_lastname_no_et_al(text: str) -> list[Author]:
    """Parse FirstName LastName without et al.

    Handles:
    - "FirstName LastName, FirstName LastName, and LastName" (multiple authors)
    - "LastName, LastName, LastName" (Vancouver style - single-word last names)
    - "Smith J" (Vancouver: LastName Initial)
    - "Bowman, Angeli, Potts, and Manning" (Vancouver with "and" before last author)

    IMPORTANT: Handle "and" BEFORE comma split for correct parsing of
    "John Blitzer, Ryan McDonald, and Fernando Pereira"
    """
    # Replace " and " with semicolon separator FIRST, before splitting by comma
    # This handles "John Blitzer, Ryan McDonald, and Fernando Pereira" correctly
    # where "and Fernando Pereira" needs to be separated from "Ryan McDonald,"
    normalized = text.replace(" and ", " ; ").replace("&", " ; ")

    # Split by semicolon (our "and" replacement) and comma
    # Each semicolon-separated piece may contain comma-separated author groups
    semicolon_parts = [s.strip() for s in normalized.split(";") if s.strip()]

    authors = []
    for sem_part in semicolon_parts:
        # Split each semicolon part by comma
        comma_parts = [p.strip() for p in sem_part.split(",") if p.strip()]

        for part in comma_parts:
            if not part or len(part) < 2:
                continue

            tokens = part.split()

            if len(tokens) >= 2:
                # Check if last token is a single letter (likely initial)
                # "Smith J" -> last_name=Smith, initial=J
                if len(tokens[-1]) == 1 and tokens[-1].isalpha():
                    # Format: "LastName Initial"
                    last_name = " ".join(tokens[:-1]).rstrip(".,;|")
                    initials = [tokens[-1].rstrip(".").upper()]
                else:
                    # Format: "FirstName LastName" or "FirstName Middle LastName"
                    last_name = tokens[-1].rstrip(".,;|")
                    first_names = " ".join(tokens[:-1]).rstrip(".,;|")
                    initials = [t[0] + "." for t in first_names.split() if t and t[0].isupper()]

                if last_name and len(last_name) >= 2:
                    author = Author(
                        last_name=last_name.lower(),  # Consistent lowercase
                        initials=initials if initials else [],
                        normalized=f"{last_name.lower()}|{''.join(initials).lower()}" if initials else last_name.lower(),
                        raw=part,
                    )
                    authors.append(author)
            else:
                # Single word: just a last name (Vancouver style)
                last_name = part.rstrip(".,;|")
                if last_name and len(last_name) >= 2:
                    author = Author(
                        last_name=last_name.lower(),  # Lowercase for single-word names
                        initials=[],
                        normalized=last_name.lower(),
                        raw=last_name,
                    )
                    authors.append(author)

    return authors


# --- Internals ---


def _extract_initials_from_first_tokens(tokens: list[str]) -> list[str]:
    """Từ list tokens phía sau dấu phẩy APA → initials.

    ['J.'] → ['J']
    ['J.', 'K.'] → ['J', 'K']
    ['John', 'K.'] → ['J', 'K']   # full first name → lấy J từ John
    ['John', 'K.', 'Smith'] → ['J', 'K']   # author bị trộn (edge case)
    """
    return _extract_initials_from_tokens(tokens)


def _is_initial_like(tok: str) -> bool:
    """True nếu token trông giống initial.

    'J.' → True
    'J' → True
    'John' → True (full first name, lấy chữ cái đầu)
    'Smith' → True (chữ cái đầu uppercase)
    'van' / 'der' / 'de' → False (particle — viết thường hết, không phải initial)
    'Jr.' → False (suffix)
    """
    tok = tok.strip(".,;")
    if not tok:
        return False
    # Particles viết thường (van / der / de / von...) KHÔNG phải initial
    if tok.lower() in _PARTICLES:
        return False
    if _INITIAL_RE.match(tok):
        return True
    if len(tok) <= 4 and tok[0].isupper() and tok[1:].islower():
        return True
    return False


def _extract_initials_from_tokens(tokens: list[str]) -> list[str]:
    """Từ list tokens → list initials (lowercase).

    'J.' → 'j'
    'J. K.' → 'j', 'k'
    'John' → 'j'  (full first name lấy chữ cái đầu)
    'Smith' → 's' (cũng lấy chữ cái đầu — không chắc chắn last vs first)
    'Jr.' → bỏ qua (suffix không phải initial)
    """
    initials: list[str] = []
    for tok in tokens:
        tok_clean = tok.strip(".,;")
        if not tok_clean:
            continue
        if _INITIAL_RE.match(tok_clean):
            initials.append(tok_clean[0].lower())
        elif _is_initial_like(tok_clean):
            initials.append(tok_clean[0].lower())
    return initials


def _split_last_initials(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Tách boundary giữa last name và initials ở cuối.

    'Smith J.' → (['Smith'], ['J'])
    'Smith J. K.' → (['Smith'], ['J', 'K'])
    'van der Berg J.' → (['van', 'der', 'Berg'], ['J'])   # particles giữ nguyên
    'Smith John' → (['Smith'], ['John'])   # full first name treated as initial
    'J. K. Smith' → ([], [])  # không áp dụng (last ở cuối → sang 2a)

    Returns:
        (last_tokens, initials) — initials là list đã extract.
        Nếu không tìm được boundary hợp lệ → ([], []).
    """
    if len(tokens) < 2:
        return [], []

    # Từ cuối, đếm ngược các token initial-like
    i = len(tokens) - 1
    init_count = 0
    while i >= 0 and _is_initial_like(tokens[i]):
        i -= 1
        init_count += 1

    # Cần ít nhất 1 initial ở cuối, và last_tokens phải có ít nhất 1 token
    if init_count == 0:
        return [], []
    last_tokens = tokens[: len(tokens) - init_count]
    if not last_tokens:
        return [], []

    initial_tokens = tokens[len(tokens) - init_count:]
    return last_tokens, _extract_initials_from_tokens(initial_tokens)


def _split_initials_last(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Tách initials đầu + last name cuối.

    'J. K. Smith' → (['J.', 'K.'], ['Smith'])
    'Smith' → ([], ['Smith'])   # không phân biệt được
    'Smith J.' → ([], ['Smith', 'J.'])   # last ở đầu, không áp dụng
    """
    if len(tokens) < 2:
        return [], tokens

    # Từ đầu, đếm xuôi các token initial-like
    i = 0
    init_count = 0
    while i < len(tokens) and _is_initial_like(tokens[i]):
        i += 1
        init_count += 1

    if init_count == 0:
        return [], tokens

    last_tokens = tokens[init_count:]
    if not last_tokens:
        return [], tokens

    initial_tokens = tokens[:init_count]
    return initial_tokens, last_tokens


# --- Helpers cho test + debug ---


def jaccard_similarity(a: list[str], b: list[str]) -> float:
    """Jaccard similarity trên 2 list last names.

    |A ∩ B| / |A ∪ B|.

    Dùng cho AuthorList matching: trích author list từ citation, trích
    author list từ candidate, đo Jaccard trên last names (lowercase).
    """
    if not a and not b:
        return 1.0
    set_a = {x.lower() for x in a if x}
    set_b = {x.lower() for x in b if x}
    if not set_a and not set_b:
        return 1.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0