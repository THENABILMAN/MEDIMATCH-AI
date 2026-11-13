"""Rules that turn a public directory listing into MediMatch fields.

Only facts in the listing are used. A specialty or city the rules cannot find is left out rather
than guessed, so a listing with no detected city only appears in searches across all of Bangladesh.
A clinician should review the specialty rules, as with backend/app/ai/data/specialty_map.yaml.
"""

import re

from app.search.cities import CITY_ALIASES

# Order matters only for readability. A listing can match several specialties
SPECIALTY_RULES: list[tuple[str, str]] = [
    (
        "Pediatric Surgery",
        r"(child|pediatric|paediatric|neonatal)\w*\W+(\w+\W+){0,3}surg|pediatric surg|paediatric surg",
    ),
    (
        "Pediatrics",
        r"\bchild(?!\s+dermatolog)|\bp(a)?ediatric(?!\s+dent)|newborn|neonat|adolescent|\bnicu\b",
    ),
    ("Gynecology & Obstetrics", r"gyn|obstet|infertil|maternal|fetal|\bivf\b|women|female"),
    ("ENT", r"\bent\b|\bear\b|\bnose\b|throat|otolaryng|otorhino|head\s*(&|and)?\s*neck"),
    ("Ophthalmology", r"\beyes?\b|ophthal|retina|cornea|phaco|glaucoma|vitreo|squint|lasik|oculo"),
    (
        "Dentistry",
        r"dental|dentist|\boral\b|maxillofacial|tooth|teeth|orthodont|endodont|periodont|prosthodont",
    ),
    ("Dermatology", r"\bskin|derma|venere|leprosy|\bhair\b|cosmetolog|sexual"),
    (
        "Cardiac & Vascular Surgery",
        r"cardiac surg|heart surg|cardiothoracic|cardio.thoracic|cardiovascular surg|vascular surg|thoracic surg",
    ),
    ("Cardiology", r"cardio(?!thoracic|.thoracic|vascular surg)|heart|cardiac(?! surg)"),
    ("Neurosurgery", r"neuro.?surg|brain\W+(\w+\W+){0,3}surg|spine surg|spinal surg"),
    ("Neurology", r"neuro(?!.?surg|.?develop)|brain|stroke|epilep|nerve|headache|migraine"),
    ("Psychiatry", r"psychiat|mental|drug addict|addiction|de.?addiction"),
    ("Clinical Psychology", r"psycholog|psychotherap"),
    ("Counselling", r"counsel"),
    (
        "Orthopedics",
        r"(?<!dentofacial\s)ortho(?!dont)|bone|joint|trauma|fracture|arthroscop|sports injur|spine(?! surg)",
    ),
    (
        "Physical Medicine & Rehabilitation",
        r"physical medicine|rehabilit|physiother|physiatr|\bpain\b",
    ),
    ("Rheumatology", r"rheumat(?!ic\s+fever)|arthritis|\bgout\b|lupus"),
    ("Urology", r"\burolog|androlog|prostate|kidney stone|urinary"),
    ("Nephrology", r"nephro|kidney(?! stone)|renal|dialysis"),
    (
        "Gastroenterology & Hepatology",
        r"gastro|liver|hepat|digest|endoscop|stomach|pancrea|biliary|colon(?!y)|bowel",
    ),
    ("Endocrinology", r"endocrin|diabet|thyroid|hormon|obesity|metaboli"),
    ("Pulmonology", r"\bchest|\blungs?\b|respirat|asthma|pulmon|tubercul|\btb\b|sleep apnea"),
    ("Oncology", r"cancer|oncolog|tumou?r|radiotherap|chemotherap"),
    ("Hematology", r"hemato|haemato|\bblood|thalass|hemophil"),
    ("Plastic Surgery", r"plastic|burn|reconstruct|aesthetic surg|cosmetic surg"),
    (
        "General Surgery",
        r"general\W+(\w+\W+){0,2}surg|laparoscop|hernia|colorectal|breast|hepatobiliary|appendix|piles|fistula|^\W*(surgery specialist|surgeon)\b",
    ),
    (
        "General Medicine",
        r"(?<!nuclear\s)(?<!physical\s)medicine|internal|physician|general practi|family medicine|infectious",
    ),
    ("Nutrition", r"nutrition|dietit|dietic|diet\b"),
]

_COMPILED = [(name, re.compile(rule, re.IGNORECASE)) for name, rule in SPECIALTY_RULES]

# Specialties that only appear because a broader word matched inside a more specific one
_SUPERSEDED = {
    "Pediatric Surgery": {"General Surgery", "Pediatrics"},
    "Cardiac & Vascular Surgery": {"Cardiology", "General Surgery"},
    "Neurosurgery": {"Neurology", "General Surgery"},
    "Physical Medicine & Rehabilitation": {"General Medicine"},
}


# Physical medicine and orthopedic listings name conditions such as stroke or arthritis that belong
# to a neighbouring field too. That field is kept only when the listing names it outright
_NEIGHBOURS = {
    "Physical Medicine & Rehabilitation": ("Neurology", "Orthopedics", "Rheumatology"),
    "Orthopedics": ("Neurology", "Rheumatology"),
}
_NAMED_OUTRIGHT = {
    "Neurology": re.compile(r"neurolog|neuro\s*medicine|neuro\W", re.IGNORECASE),
    "Orthopedics": re.compile(r"orthop", re.IGNORECASE),
    "Rheumatology": re.compile(r"rheumat(?!ic\s+fever)", re.IGNORECASE),
}


def classify_specialties(*texts: str | None) -> list[str]:
    """The specialties a listing names, most specific first. Empty if none can be found."""
    text = " ".join(t for t in texts if t)
    found = [name for name, pattern in _COMPILED if pattern.search(text)]
    dropped = {lesser for name in found for lesser in _SUPERSEDED.get(name, set())}
    for main, neighbours in _NEIGHBOURS.items():
        if main in found:
            dropped |= {n for n in neighbours if n != main and not _NAMED_OUTRIGHT[n].search(text)}
    return [name for name in found if name not in dropped]


# Areas and institutions that exist only in Dhaka. Chains with branches in other cities are left out
DHAKA_ONLY = [
    "dhanmondi",
    "mirpur",
    "uttara",
    "gulshan",
    "banani",
    "mohakhali",
    "shyamoli",
    "motijheel",
    "malibagh",
    "mohammadpur",
    "panthapath",
    "green road",
    "farmgate",
    "badda",
    "rampura",
    "bashundhara",
    "baridhara",
    "khilgaon",
    "jatrabari",
    "lalbagh",
    "wari",
    "shahbagh",
    "kalabagan",
    "tejgaon",
    "agargaon",
    "sher-e-bangla nagar",
    "segunbagicha",
    "paltan",
    "moghbazar",
    "elephant road",
    "azimpur",
    "keraniganj",
    "demra",
    "kafrul",
    "cantonment, dhaka",
    "bangladesh medical university",
    "bsmmu",
    "pg hospital",
    "birdem",
    "mitford",
    "sir salimullah",
    "shaheed suhrawardy",
    "holy family",
    "kurmitola",
    "nicvd",
    "nins",
    "national institute of cardiovascular",
    "national institute of neurosciences",
    "national institute of kidney",
    "national institute of cancer",
    "nicrh",
    "national institute of mental health",
    "nimh",
    "national institute of ophthalmology",
    "national institute of traumatology",
    "nitor",
    "pangu",
    "national institute of ent",
    "national institute of diseases of the chest",
    "nidch",
    "shishu hospital, dhaka",
    "dhaka shishu",
    "icddr",
    "square hospital",
    "evercare hospital dhaka",
    "united hospital",
    "bangabandhu sheikh mujib medical university",
    "mugda",
    "kuwait bangladesh",
    "shaheed tajuddin",
    "national heart foundation",
]


def detect_city(*texts: str | None) -> str | None:
    """The city a listing names. The earliest mention wins. None if no city is named."""
    text = " ".join(t for t in texts if t).lower()
    best: tuple[int, str] | None = None
    for alias, city in CITY_ALIASES.items():
        if not alias.isascii():
            continue
        match = re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", text)
        if match and (best is None or match.start() < best[0]):
            best = (match.start(), city)
    if best:
        return best[1]
    if any(marker in text for marker in DHAKA_ONLY):
        return "Dhaka"
    return None


_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*years?", re.IGNORECASE)
_BMDC = re.compile(r"BMDC\s*Reg\.?\s*No\.?\s*[:\-]?\s*([A-Za-z]?[\s\-]?\d{2,7})", re.IGNORECASE)


def parse_years(text: str | None) -> int | None:
    match = _YEARS.search(text or "")
    return int(match.group(1)) if match else None


def parse_bmdc(text: str | None) -> str | None:
    match = _BMDC.search(text or "")
    return re.sub(r"\s+", "", match.group(1)).upper() if match else None


# Phone numbers in a workplace line are left out: patients are pointed to the hospital, not a number
_CONTACT = re.compile(
    r"(appointment|cell|call|phone|mobile|hot\s*line|help\s*line|contact|serial|tel)\s*(no\.?|number)?\s*[:\-]?\s*"
    r"[\d+][\d\s,/\-]{6,}|\+?88[\s\-]?0\d{2,4}[\s\-]?\d{3}[\s\-]?\d{3,4}|\b0\d{2,4}[\s\-]?\d{6,8}\b",
    re.IGNORECASE,
)


def strip_contacts(text: str | None) -> str | None:
    cleaned = _CONTACT.sub(" ", text or "")
    cleaned = re.sub(r"\s+([,.;])", r"\1", " ".join(cleaned.split())).strip(" ,;-")
    return cleaned or None


def split_qualifications(text: str | None) -> list[str]:
    """Degrees split at commas outside brackets: "MBBS, MS (Urology, BSMMU)" gives two."""
    parts, depth, current = [], 0, ""
    for char in text or "":
        depth += char == "("
        depth -= char == ")" and depth > 0
        if char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)
    return [" ".join(p.split()) for p in parts if p.strip()]
