#!/usr/bin/env python3
"""
Convert SQLite placeholders (?) to PostgreSQL placeholders (%s)
"""

import re

with open("main.py", "r") as f:
    content = f.read()

# Count before
count_before = content.count("?")
print(f"Total ? placeholders found: {count_before}")

# Replace in SQL queries - be careful to only replace in query strings
# Pattern: "SELECT ... WHERE id = ?" -> "SELECT ... WHERE id = %s"

# Replace db.execute and db.cursor calls with ? placeholders
content = re.sub(
    r'db\.execute\((["\'])([^"\']*?)\?([^"\']*?)\1',
    lambda m: f"db.execute({m.group(1)}{m.group(2)}%s{m.group(3)}{m.group(1)}",
    content,
)

# Also handle cases with multiple lines
lines = content.split("\n")
new_lines = []

for line in lines:
    # Skip comment lines
    if line.strip().startswith("#"):
        new_lines.append(line)
        continue

    # Replace ? with %s but only in SQL strings within db.execute/db.cursor
    if (
        "db.execute" in line
        or "db.cursor" in line
        or "VALUES" in line
        or "INSERT" in line
        or "UPDATE" in line
        or "SELECT" in line
        or "DELETE" in line
    ):
        # Simple replacement within quotes
        if "?" in line:
            # Replace ? with %s in the line
            # Be careful: only in SQL strings
            in_string = False
            string_char = None
            result = []
            i = 0
            while i < len(line):
                char = line[i]

                # Track string state
                if char in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

                # Replace ? only within strings
                if char == "?" and in_string:
                    result.append("%s")
                else:
                    result.append(char)

                i += 1

            line = "".join(result)

    new_lines.append(line)

content = "\n".join(new_lines)

# Count after
count_after = content.count("?")
print(f"? placeholders remaining: {count_after}")
print(f"Converted: {count_before - count_after} placeholders")

with open("main.py", "w") as f:
    f.write(content)

print("✅ Conversion complete!")
