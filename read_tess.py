
try:
    with open("tess_debug.txt", "r", encoding="utf-16") as f:
        content = f.read()
except:
    try:
        with open("tess_debug.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Read error: {e}")
        exit()

for line in content.splitlines():
    if "DEBUG_TESS" in line:
        print(line)
