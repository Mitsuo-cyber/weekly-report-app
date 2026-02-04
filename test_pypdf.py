
import sys

def test_pypdf():
    try:
        import pypdf
        print("pypdf is installed.")
        reader = pypdf.PdfReader("【ゾーン別】売上実績20260127.pdf")
        print(f"Number of pages: {len(reader.pages)}")
        page = reader.pages[0]
        text = page.extract_text()
        print("--- extracted text ---")
        print(text)
        print("----------------------")
    except ImportError:
        print("pypdf NOT installed.")
        try:
            import PyPDF2
            print("PyPDF2 is installed.")
            reader = PyPDF2.PdfFileReader("【ゾーン別】売上実績20260127.pdf")
            print(f"Number of pages: {reader.numPages}")
            page = reader.getPage(0)
            text = page.extractText()
            print("--- extracted text ---")
            print(text)
            print("----------------------")
        except ImportError:
            print("PyPDF2 NOT installed.")

if __name__ == "__main__":
    test_pypdf()
