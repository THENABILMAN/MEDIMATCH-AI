"""One spelling for each city, so "Chittagong" and "Chattogram" find the same doctors."""

CITY_ALIASES: dict[str, str] = {
    "dhaka": "Dhaka",
    "chattogram": "Chattogram",
    "chittagong": "Chattogram",
    "ctg": "Chattogram",
    "sylhet": "Sylhet",
    "rajshahi": "Rajshahi",
    "khulna": "Khulna",
    "barishal": "Barishal",
    "barisal": "Barishal",
    "rangpur": "Rangpur",
    "mymensingh": "Mymensingh",
    "cumilla": "Cumilla",
    "comilla": "Cumilla",
    "gazipur": "Gazipur",
    "narayanganj": "Narayanganj",
    "bogura": "Bogura",
    "bogra": "Bogura",
    "cox's bazar": "Cox's Bazar",
    "coxs bazar": "Cox's Bazar",
    "cox’s bazar": "Cox's Bazar",
    "jashore": "Jashore",
    "jessore": "Jashore",
    "dinajpur": "Dinajpur",
    "faridpur": "Faridpur",
    "tangail": "Tangail",
    "pabna": "Pabna",
    "noakhali": "Noakhali",
    "feni": "Feni",
    "kushtia": "Kushtia",
    "savar": "Savar",
    "sirajganj": "Sirajganj",
    "jamalpur": "Jamalpur",
    "kishoreganj": "Kishoreganj",
    "netrokona": "Netrokona",
    "sherpur": "Sherpur",
    "habiganj": "Habiganj",
    "moulvibazar": "Moulvibazar",
    "sunamganj": "Sunamganj",
    "brahmanbaria": "Brahmanbaria",
    "chandpur": "Chandpur",
    "lakshmipur": "Lakshmipur",
    "naogaon": "Naogaon",
    "natore": "Natore",
    "chapainawabganj": "Chapainawabganj",
    "joypurhat": "Joypurhat",
    "satkhira": "Satkhira",
    "bagerhat": "Bagerhat",
    "jhenaidah": "Jhenaidah",
    "magura": "Magura",
    "narail": "Narail",
    "chuadanga": "Chuadanga",
    "meherpur": "Meherpur",
    "patuakhali": "Patuakhali",
    "bhola": "Bhola",
    "pirojpur": "Pirojpur",
    "jhalokathi": "Jhalokathi",
    "barguna": "Barguna",
    "kurigram": "Kurigram",
    "gaibandha": "Gaibandha",
    "nilphamari": "Nilphamari",
    "lalmonirhat": "Lalmonirhat",
    "thakurgaon": "Thakurgaon",
    "panchagarh": "Panchagarh",
    "manikganj": "Manikganj",
    "munshiganj": "Munshiganj",
    "narsingdi": "Narsingdi",
    "madaripur": "Madaripur",
    "shariatpur": "Shariatpur",
    "gopalganj": "Gopalganj",
    "rajbari": "Rajbari",
    "rangamati": "Rangamati",
    "khagrachari": "Khagrachari",
    "bandarban": "Bandarban",
    "ঢাকা": "Dhaka",
    "চট্টগ্রাম": "Chattogram",
    "সিলেট": "Sylhet",
    "রাজশাহী": "Rajshahi",
    "খুলনা": "Khulna",
    "বরিশাল": "Barishal",
    "রংপুর": "Rangpur",
    "ময়মনসিংহ": "Mymensingh",
    "কুমিল্লা": "Cumilla",
}

ANYWHERE = "bangladesh"


def city_spellings(city: str | None) -> list[str]:
    """Every known way of writing the city, including the one given. Empty for no city."""
    canonical = normalize_city(city)
    if not canonical:
        return []
    spellings = {canonical}
    spellings |= {alias for alias, name in CITY_ALIASES.items() if name == canonical}
    return sorted(spellings, key=str.lower)


def normalize_city(city: str | None) -> str | None:
    """The stored spelling of a city. A name we do not know is kept as written."""
    if city is None:
        return None
    cleaned = " ".join(city.split())
    if not cleaned:
        return None
    return CITY_ALIASES.get(cleaned.lower(), cleaned)
