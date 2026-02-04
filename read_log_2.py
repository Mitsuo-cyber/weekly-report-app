
try:
    with open("debug_output_2.txt", "r", encoding="utf-16") as f:
        content = f.read()
except:
    try:
        with open("debug_output_2.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Read error: {e}")
        exit()

for line in content.splitlines():
    if "DEBUG: OCR Text Repr:" in line:
        print(line)
