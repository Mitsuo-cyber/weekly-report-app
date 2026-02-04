
try:
    with open("debug_output.txt", "r", encoding="utf-16") as f:
        content = f.read()
except:
    try:
        with open("debug_output.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Read error: {e}")
        exit()

for line in content.splitlines():
    if "DEBUG" in line or "OCR" in line or "easyocr" in line.lower() or "tesseract" in line.lower():
        print(line)
