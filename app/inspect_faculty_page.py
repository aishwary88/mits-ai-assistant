import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://web.mitsgwalior.in/faculty-profiles-cse-2"

response = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=20
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

articles = soup.select("div.article")

print("Total profile containers:", len(articles))

for article in articles:
    header = article.select_one(".article-header")
    if not header:
        continue

    name = header.get_text(" ", strip=True)

    # Get the actual faculty photo, excluding research/social icons
    photo_url = None

    for img in article.find_all("img"):
        src = img.get("src") or img.get("data-src")

        if not src:
            continue

        if "/faculties/" in src or "/Departments/" in src:
            photo_url = urljoin(url, src)
            break

    profile_text = article.get_text(" ", strip=True)

    print("\n" + "=" * 70)
    print("NAME:", name)
    print("PHOTO:", photo_url)
    print("PROFILE DETAILS:")
    print(profile_text)