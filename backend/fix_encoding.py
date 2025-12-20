#!/usr/bin/env python
# -*- coding: utf-8 -*-

with open("main.py", "rb") as f:
    content = f.read()

# Fix line with 'After executing tools'
# Replace corrupted G\ufffd\ufffd/G\ufffd\ufffd with ✓ Success/✗ Failed
content = content.replace(
    b"After executing tools, output status lines (G\xef\xbf\xbd\xef\xbf\xbd/G\xef\xbf\xbd\xef\xbf\xbd) before explanation.",
    b"After executing tools, output status lines (\xc3\x89\xc2\xa3 Success/\xc3\x89\xc2\xa7 Failed) before explanation.",
)

# Fix line with 'Setelah eksekusi tool'
# Replace corrupted G\ufffd\ufffd/G\ufffd\ufffd with ✓ Berhasil/✗ Gagal
content = content.replace(
    b"Setelah eksekusi tool tampilkan baris status (G\xef\xbf\xbd\xef\xbf\xbd/G\xef\xbf\xbd\xef\xbf\xbd) sebelum penjelasan.",
    b"Setelah eksekusi tool tampilkan baris status (\xc3\x89\xc2\xa3 Berhasil/\xc3\x89\xc2\xa7 Gagal) sebelum penjelasan.",
)

with open("main.py", "wb") as f:
    f.write(content)

print("✓ Fixed corrupted characters")
