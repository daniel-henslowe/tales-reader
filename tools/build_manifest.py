#!/usr/bin/env python3
"""Parse all issue_*.txt files and generate data/manifest.json."""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ISSUES_DIR = REPO_ROOT / "issues"
OUTPUT = REPO_ROOT / "data" / "manifest.json"

MONTH_MAP = {
    "jan": "January", "feb": "February", "mar": "March", "apr": "April",
    "may": "May", "jun": "June", "jul": "July", "aug": "August",
    "sep": "September", "oct": "October", "nov": "November", "dec": "December",
}


def parse_filename(fname):
    """Extract issue number, month, year from filename like issue_001_jan_1953.txt."""
    m = re.match(r"issue_(\d{3})_([a-z]{3})_(\d{4})\.txt", fname)
    if not m:
        return None
    return {
        "number": int(m.group(1)),
        "month_abbr": m.group(2),
        "month": MONTH_MAP[m.group(2)],
        "year": int(m.group(3)),
    }


def parse_header(lines):
    """Parse the header block between the first two === dividers."""
    info = {}
    for line in lines:
        line = line.strip()
        if m := re.match(r"Issue\s+#(\d+)\s*—\s*(.+)", line):
            info["date_line"] = m.group(2).strip()
        elif m := re.match(r"Published by\s+(.+)", line):
            info["publisher"] = m.group(1).strip()
        elif m := re.match(r"Editors?:\s*(.+)", line):
            info["editors"] = m.group(1).strip()
        elif m := re.match(r"Cover Price:\s*(.+)", line):
            info["cover_price"] = m.group(1).strip()
    return info


def parse_cover_art(lines):
    """Parse cover art line(s) between second and third === dividers."""
    for line in lines:
        line = line.strip()
        if m := re.match(r'Cover Art:\s*"(.+?)"\s*by\s+(.+)', line):
            return {"title": m.group(1), "artist": m.group(2).strip()}
    return None


def parse_toc(lines):
    """Parse numbered story entries and feature entries from TABLE OF CONTENTS block."""
    stories = []
    features = []
    in_features = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("Features:"):
            in_features = True
            i += 1
            continue

        if in_features:
            # Feature line: title .... p. NNN
            if m := re.match(r'\s+(.+?)\s*\.{2,}\s*p\.\s*(\d+)', line):
                features.append({"title": m.group(1).strip(), "page": int(m.group(2))})
            i += 1
            continue

        # Numbered story entry - may span multiple lines
        if m := re.match(r'\s*(\d+)\.\s+(.+)', stripped):
            entry_num = int(m.group(1))
            rest = m.group(2)

            # Collect continuation lines (indented, starting with "by" or part of title)
            full_text = rest
            while i + 1 < len(lines):
                next_line = lines[i + 1]
                next_stripped = next_line.strip()
                # Stop if next line is a new numbered entry, Features:, or empty leading to new section
                if re.match(r'\d+\.', next_stripped) or next_stripped.startswith("Features:"):
                    break
                if next_stripped == "" and i + 2 < len(lines) and (re.match(r'\d+\.', lines[i + 2].strip()) or lines[i + 2].strip().startswith("Features:")):
                    break
                if next_stripped == "":
                    break
                full_text += " " + next_stripped
                i += 1

            # Parse title and author from combined text
            # Patterns: "Title" by Author .... p. N
            #           "Title, Part II" by Author .... p. N
            story_match = re.match(
                r'"(.+?)"\s*(?:\n\s*)?by\s+(.+?)\s*\.{2,}\s*p\.\s*(\d+)',
                full_text
            )
            if story_match:
                stories.append({
                    "number": entry_num,
                    "title": story_match.group(1).strip(),
                    "author": story_match.group(2).strip(),
                    "page": int(story_match.group(3)),
                })
            else:
                # Try without page number
                story_match2 = re.match(r'"(.+?)"\s*by\s+(.+)', full_text)
                if story_match2:
                    author_part = story_match2.group(2).strip()
                    # Strip trailing dots and page number
                    author_part = re.sub(r'\s*\.{2,}\s*p\.\s*\d+', '', author_part)
                    stories.append({
                        "number": entry_num,
                        "title": story_match2.group(1).strip(),
                        "author": author_part.strip(),
                        "page": 0,
                    })
        i += 1

    return stories, features


def find_dividers(text_lines):
    """Find all line indices that are === divider lines."""
    dividers = []
    for i, line in enumerate(text_lines):
        if re.match(r'^={10,}\s*$', line.strip()):
            dividers.append(i)
    return dividers


def parse_issue(filepath):
    """Parse a single issue .txt file into metadata dict."""
    fname = os.path.basename(filepath)
    file_info = parse_filename(fname)
    if not file_info:
        print(f"WARNING: could not parse filename: {fname}", file=sys.stderr)
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Strip trailing newlines from lines for easier matching
    raw_lines = [l.rstrip('\n') for l in lines]
    dividers = find_dividers(raw_lines)

    if len(dividers) < 3:
        print(f"WARNING: not enough dividers in {fname}", file=sys.stderr)
        return None

    # Header block: between dividers[0] and dividers[1]
    header = parse_header(raw_lines[dividers[0]+1:dividers[1]])

    # Cover art: between dividers[1] and dividers[2]
    cover_art = parse_cover_art(raw_lines[dividers[1]+1:dividers[2]])

    # TOC: between dividers[2] and dividers[3]
    toc_start = dividers[2] + 1
    toc_end = dividers[3] if len(dividers) > 3 else len(raw_lines)

    # Find actual TOC content (skip "TABLE OF CONTENTS" header)
    toc_lines = raw_lines[toc_start:toc_end]
    # Skip blank lines and the "TABLE OF CONTENTS" header
    content_start = 0
    for j, line in enumerate(toc_lines):
        if re.match(r'\s*1\.', line):
            content_start = j
            break

    stories, features = parse_toc(toc_lines[content_start:])

    era = "I" if file_info["number"] <= 48 else "II"

    issue = {
        "number": file_info["number"],
        "number_padded": f"{file_info['number']:03d}",
        "month": file_info["month"],
        "month_abbr": file_info["month_abbr"],
        "year": file_info["year"],
        "date": f"{file_info['month']} {file_info['year']}",
        "era": era,
        "filename": fname,
        "publisher": header.get("publisher", ""),
        "editors": header.get("editors", ""),
        "cover_price": header.get("cover_price", ""),
        "cover_art": cover_art,
        "stories": stories,
        "features": features,
        "story_count": len(stories),
    }
    return issue


def main():
    files = sorted(ISSUES_DIR.glob("issue_*.txt"))
    if not files:
        print("ERROR: No issue files found in", ISSUES_DIR, file=sys.stderr)
        sys.exit(1)

    issues = []
    for f in files:
        issue = parse_issue(f)
        if issue:
            issues.append(issue)

    manifest = {
        "title": "Tales from the Future and Beyond",
        "total_issues": len(issues),
        "era_i_count": sum(1 for i in issues if i["era"] == "I"),
        "era_ii_count": sum(1 for i in issues if i["era"] == "II"),
        "years": sorted(set(i["year"] for i in issues)),
        "issues": issues,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Generated {OUTPUT} with {len(issues)} issues")
    for issue in issues:
        print(f"  #{issue['number_padded']} - {issue['date']} - {issue['story_count']} stories")


if __name__ == "__main__":
    main()
