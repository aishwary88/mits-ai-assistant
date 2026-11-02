import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

JSON_PATH = BASE_DIR / "faculty-data" / "cse_faculty.json"

PROFILE_URL = "https://web.mitsgwalior.in/faculty-profiles-cse-2"

PHOTO_URLS = {
    "Dr. Manish Dixit": "https://web.mitsgwalior.in/images/faculties/CSE/md.jpeg",
    "Dr. R. K. Gupta": "https://web.mitsgwalior.in/images/faculties/CSE/rkg.jpg",
    "Dr. Khushboo Agarwal": "https://web.mitsgwalior.in/images/faculties/CSE/ka.jpg",
    "Jaimala Jha": "https://web.mitsgwalior.in/images/Departments/Computer-Science/jj2020%20-%201.jpg",
    "Amit Kumar Manjhvar": "https://web.mitsgwalior.in/images/Departments/Computer-Science/AKM1.jpg",
    "Dr. Ranjeet Kumar Singh": "https://web.mitsgwalior.in/images/faculties/CSE/1cserf2102.jpg",
    "Dr. Smita Parte": "https://web.mitsgwalior.in/images/faculties/CSE/rfsmitacs%20-%201.jpg",
    "Dr. Praphula Kumar Jain": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/IMG_20240709_163958.jpg",
    "Dr. Kirti Raj Bhatele": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/kirtiraj.jpg",
    "Dr. Saurabh Agarwal": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/sauagra.jpeg",
    "Dr. Pooja Mishra": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/WhatsApp%20Image%202025-08-18%20at%2015.29.00.jpeg",
    "Dr. Lalita Agrawal": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/WhatsApp%20Image%202026-07-31%20at%2017.41.06.jpeg",
    "Mona Pandey Sharma": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/Mona%201.jpg",
    "Manisha Pathak": "https://web.mitsgwalior.in/images/Departments/Computer-Science/Faculty%20Images/Manisha.jpg",
    "Yamini Richhariya": "https://web.mitsgwalior.in/images/Departments/Computer-Science/yamini.jpeg",
}

with open(JSON_PATH, "r", encoding="utf-8") as file:
    faculty = json.load(file)

for member in faculty:
    name = member["name"]

    if name in PHOTO_URLS:
        member["profile_url"] = PROFILE_URL
        member["photo_url"] = PHOTO_URLS[name]
    else:
        print("No photo mapping found:", name)

with open(JSON_PATH, "w", encoding="utf-8") as file:
    json.dump(faculty, file, indent=2, ensure_ascii=False)

print("Faculty records:", len(faculty))
print("Photos assigned:", sum(bool(x.get("photo_url")) for x in faculty))
print("CSE faculty JSON enriched successfully.")