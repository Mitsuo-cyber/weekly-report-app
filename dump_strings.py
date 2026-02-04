
import re

def dump_strings():
    filename = "【ゾーン別】売上実績20260127.pdf"
    try:
        with open(filename, 'rb') as f:
            content = f.read()
            # Find all sequences of printable characters (length >= 3)
            # This covers ASCII. For UTF-16, it's harder in binary dump but we look for ASCII numbers first.
            strings = re.findall(b'[ -~]{3,}', content)
            
            print(f"--- Strings found in {filename} ---")
            for s in strings:
                try:
                    decoded = s.decode('utf-8')
                    # Filter for interesting strings (numbers, dates, zones)
                    if any(c.isdigit() for c in decoded) or "Sales" in decoded or "Zone" in decoded:
                         print(decoded)
                except:
                    pass
    except FileNotFoundError:
        print("File not found.")

if __name__ == "__main__":
    dump_strings()
