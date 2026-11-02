
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

JSON_PATH = BASE_DIR / "faculty-data" / "csd_faculty.json"

# Only verified individual profile URLs
PROFILE_URLS = {
    "Dr. Mahesh Parmar":
        "https://web.mitsgwalior.in/faculty-profiles-cse-2/mahesh-parmar-2",

    "Dr. Devesh Kumar Lal":
        "https://web.mitsgwalior.in/faculty-profiles-cse-2/dr-devesh-kumar-lal",
}

# Verified photo URL
PHOTO_URLS = {
    "Dr. Mahesh Parmar":
        "https://web.mitsgwalior.in/images/faculties/CSE/mp1.webp",
}

with open(JSON_PATH, "r", encoding="utf-8") as file:
    faculty = json.load(file)

for member in faculty:
    name = member["name"]

    if name in PROFILE_URLS:
        member["profile_url"] = PROFILE_URLS[name]

    if name in PHOTO_URLS:
        member["photo_url"] = PHOTO_URLS[name]

with open(JSON_PATH, "w", encoding="utf-8") as file:
    json.dump(faculty, file, indent=2, ensure_ascii=False)

print("CSD faculty records:", len(faculty))
print("Photos assigned:", sum(bool(x.get("photo_url")) for x in faculty))
print("Profile URLs assigned:", sum(bool(x.get("profile_url")) for x in faculty))
print("CSD faculty JSON enrichment completed.")
