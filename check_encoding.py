import os
import glob

print("🔍 Scanning all Python files for UTF-8 corruption...\n")

bad_files = []
for py_file in glob.glob("backend/**/*.py", recursive=True):
    try:
        with open(py_file, "rb") as f:
            content = f.read()

        # Check for replacement character
        ufffd_count = content.count(b"\xff\xfd")

        # Try to decode as UTF-8
        try:
            content.decode("utf-8")
            utf8_valid = True
        except UnicodeDecodeError as e:
            utf8_valid = False
            bad_files.append((py_file, f"Invalid UTF-8 at {e.start}: {e.reason}"))

        if ufffd_count > 0:
            bad_files.append((py_file, f"Contains {ufffd_count} U+FFFD character(s)"))
        elif not utf8_valid:
            bad_files.append((py_file, "Invalid UTF-8 sequence"))
        else:
            print(f"✅ {py_file}")
    except Exception as e:
        print(f"⚠️  {py_file}: {e}")

if bad_files:
    print(f"\n⚠️  Found {len(bad_files)} problematic file(s):")
    for f, msg in bad_files:
        print(f"  ❌ {f}: {msg}")
else:
    print("\n✅ All Python files are clean!")
