
import pdfplumber
import glob
import os

def check_pages():
    pdf_files = glob.glob("*.pdf")
    for f in pdf_files:
        try:
            with pdfplumber.open(f) as pdf:
                print(f"{f}: {len(pdf.pages)} pages")
        except Exception as e:
            print(f"{f}: Error {e}")

if __name__ == "__main__":
    check_pages()
