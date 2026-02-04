
import pdfplumber
import os

def inspect_pdf():
    filename = "【ゾーン別】売上実績20260127.pdf"
    if not os.path.exists(filename):
        print(f"{filename} not found.")
        return

    print(f"--- Inspecting {filename} ---")
    with pdfplumber.open(filename) as pdf:
        print(f"Number of pages: {len(pdf.pages)}")
        for i, page in enumerate(pdf.pages):
            print(f"\n--- Page {i+1} ---")
            text = page.extract_text()
            print(f"Text length: {len(text) if text else 0}")
            if text:
                print("Text snippet (first 200 chars):")
                print(text[:200])
            else:
                print("No text extracted.")
            
            tables = page.extract_table()
            if tables:
                print("Table detected.")
                print(tables[:2])
            else:
                print("No table detected.")
                
            print(f"Number of images: {len(page.images)}")
            if page.images:
                print("Images found on page.")

if __name__ == "__main__":
    inspect_pdf()
