"""The rules that turn a directory listing into MediMatch fields. No database or network."""

import pytest

from app.search.cities import normalize_city
from scripts.directory_rules import (
    classify_specialties,
    detect_city,
    parse_bmdc,
    parse_years,
    split_qualifications,
    strip_contacts,
)
from scripts.import_directory import to_doctor


@pytest.mark.parametrize(
    ("listing", "expected"),
    [
        ("Medicine Specialist", ["General Medicine"]),
        ("ENT (Ear, Nose, Throat) Specialist & Head Neck Surgeon", ["ENT"]),
        ("Gynecology, Obstetrics Specialist & Surgeon", ["Gynecology & Obstetrics"]),
        ("Newborn, Adolescent & Child Diseases Specialist", ["Pediatrics"]),
        ("Eye Specialist & Phaco Surgeon", ["Ophthalmology"]),
        ("Oral & Dental Surgeon", ["Dentistry"]),
        ("Skin, Allergy & Sexual Diseases Specialist", ["Dermatology"]),
        ("Diabetes, Thyroid & Hormone Specialist", ["Endocrinology"]),
        ("Kidney Diseases, Dialysis & Medicine Specialist", ["Nephrology", "General Medicine"]),
        ("Psychiatry & Mental Health Specialist", ["Psychiatry"]),
        ("Neurosurgery Specialist", ["Neurosurgery"]),
        ("Pediatric Surgery Specialist", ["Pediatric Surgery"]),
        ("Orthopedics & Rheumatology Specialist", ["Orthopedics", "Rheumatology"]),
    ],
)
def test_listings_map_to_specialties(listing, expected):
    assert classify_specialties(listing) == expected


@pytest.mark.parametrize(
    ("listing", "wrong"),
    [
        # Each of these was a real mistake found while measuring the full directory
        ("Neurology (Brain, Nerve, Stroke, Headache) & Medicine Specialist", "Urology"),
        ("Cardiology & Heart Diseases Specialist", "ENT"),
        ("Oral Surgery, Root canal, Orthodontics, Pediatric Dentistry", "Pediatrics"),
        ("Physical Medicine (Pain, Arthritis, Stroke, Paralysis, Sports Injury)", "Neurology"),
        ("Orthopedic (Bone, Joint, Arthritis, Trauma, Paralysis) Specialist", "Rheumatology"),
        ("Kidney & Hypertension Specialist", "Cardiology"),
        ("Nuclear Medicine, Ultrasound, Color Doppler, Thyroid Specialist", "General Medicine"),
        ("Cardiology (Heart Diseases, Hypertension & Rheumatic Fever) Specialist", "Rheumatology"),
        ("Oral, Dental Surgeon, Orthodontics & Dentofacial Orthopedics", "Orthopedics"),
        ("ENT, Head & Neck Surgery Specialist", "General Surgery"),
    ],
)
def test_words_inside_other_words_do_not_add_a_specialty(listing, wrong):
    assert wrong not in classify_specialties(listing)


@pytest.mark.parametrize(
    "listing", ["Homeopathic Doctor", "Anesthesiologist", "Radiology Specialist"]
)
def test_listings_not_suited_to_symptoms_get_no_specialty(listing):
    assert classify_specialties(listing) == []


@pytest.mark.parametrize(
    ("workplace", "city"),
    [
        ("Rajshahi Medical College & Hospital", "Rajshahi"),
        ("Chittagong 250 Bed General Hospital, Chattogram", "Chattogram"),
        ("Bangladesh Medical University (Ex. PG Hospital)", "Dhaka"),
        ("Labaid Specialized Hospital, Dhanmondi", "Dhaka"),
        ("Comilla Medical College", "Cumilla"),
        ("Popular Diagnostic Centre", None),
    ],
)
def test_city_comes_only_from_the_listing(workplace, city):
    assert detect_city(workplace) == city


def test_city_names_share_one_spelling():
    assert normalize_city("chittagong") == normalize_city("Chattogram") == "Chattogram"
    assert normalize_city("  Dhaka ") == "Dhaka"
    assert normalize_city("ঢাকা") == "Dhaka"
    assert normalize_city("Somewhere New") == "Somewhere New"
    assert normalize_city("") is None


def test_phone_numbers_are_removed_from_workplaces():
    assert strip_contacts("Ashiyan Hospital Cell: 01410-375875, 01568-404870") == "Ashiyan Hospital"
    assert strip_contacts("CMCH Helpline: 01782666066") == "CMCH"
    assert strip_contacts("General Hospital, Chattogram Appointment: 01617-654525") == (
        "General Hospital, Chattogram"
    )


def test_numbers_are_read_only_when_written():
    assert parse_years("13+ Years of Experience") == 13
    assert parse_years(None) is None
    assert parse_bmdc("BMDC Reg. No: A-41157") == "A-41157"
    assert parse_bmdc(None) is None
    assert split_qualifications("MBBS (Dhaka), MS (Urology, BSMMU), FACS (USA)") == [
        "MBBS (Dhaka)",
        "MS (Urology, BSMMU)",
        "FACS (USA)",
    ]


def test_a_listing_leaves_unknown_fields_empty():
    doctor = to_doctor(
        {
            "Doctor Name": "Dr. Example",
            "BMDC Reg. No": None,
            "Degree": "MBBS, FCPS (Medicine)",
            "Training": None,
            "Experience": None,
            "Specialty": "Medicine Specialist",
            "Specialist": None,
            "Designation": "Consultant",
            "Workplace": "Popular Diagnostic Centre Appointment: 01617-654525",
            "Profile URL": "https://example.test/dr-example/",
        }
    )
    assert doctor is not None
    assert doctor["years_experience"] is None
    assert doctor["bmdc_number"] is None
    assert doctor["city"] is None
    assert "01617" not in doctor["clinic_name"]
    assert doctor["specialties"] == ["General Medicine"]


def test_a_listing_without_a_name_or_link_is_skipped():
    empty = dict.fromkeys(
        [
            "Doctor Name",
            "BMDC Reg. No",
            "Degree",
            "Training",
            "Experience",
            "Specialty",
            "Specialist",
            "Designation",
            "Workplace",
            "Profile URL",
        ]
    )
    assert to_doctor(empty) is None
    assert to_doctor({**empty, "Doctor Name": "Dr. X"}) is None
