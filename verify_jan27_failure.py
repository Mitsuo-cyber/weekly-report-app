
import pdfplumber
import os

def analyze_pdf():
    file = "【ゾーン別】売上実績20260127.pdf"
    if not os.path.exists(file):
        print(f"File {file} not found.")
        return

    try:
        with pdfplumber.open(file) as pdf:
            print(f"File: {file}")
            print(f"Pages: {len(pdf.pages)}")
            if len(pdf.pages) > 0:
                p = pdf.pages[0]
                print(f"Chars: {len(p.chars)}")
                print(f"Images: {len(p.images)}")
                print(f"Lines: {len(p.lines)}")
                print(f"Rects: {len(p.rects)}")
                print(f"Curves: {len(p.curves)}")
                print(f"Width: {p.width}, Height: {p.height}")
    except Exception as e:
        print(f"Error opening PDF: {e}")

if __name__ == "__main__":
    analyze_pdf()
