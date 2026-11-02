from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader

BASE_DIR = Path(__file__).resolve().parent
SCHEME_DIR = BASE_DIR / "Mits-Data" / "Scheme"

pdf_files = [
    SCHEME_DIR / "CSE" / "CSE Scheme July 2025 Odd.pdf",
    SCHEME_DIR / "CSD" / "CSD Scheme July 25 Odd.pdf"
]

for pdf_path in pdf_files:

    print("\n" + "=" * 80)
    print("FILE:", pdf_path.name)
    print("=" * 80)

    if not pdf_path.exists():
        print("FILE NOT FOUND:", pdf_path)
        continue

    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()

    print("Total pages:", len(pages))

    for page in pages:

        content = page.page_content

        if "Subject Name" in content or "B. Tech." in content:

            print("\nPAGE:", page.metadata.get("page", "Unknown"))
            print("-" * 80)
            print(content[:5000])