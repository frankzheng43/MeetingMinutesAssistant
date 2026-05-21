import os
import fitz  # PyMuPDF
import re

folder = r"F:\共享文件夹\公用\@存档区\2018年以来三会纪要"

by_year = {}

pdf_count = 0
total_pages = 0

for root, dirs, files in os.walk(folder):
    for file in files:
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(root, file)
            try:
                doc = fitz.open(pdf_path)
                pages = doc.page_count
                total_pages += pages
                pdf_count += 1
                doc.close()
            except Exception as e:
                pages = 0
                print(f"  [!] 无法打开 {file}: {e}")

            # 从文件名提取年份（优先取路径中带年份的子目录名，其次从文件名正则提取）
            rel_dir = os.path.relpath(root, folder)
            year_match = re.search(r'(20\d{2})', rel_dir)
            if not year_match:
                year_match = re.search(r'[［\[【(（]?(20\d{2})[年］\]】)）]?', file)
            year = year_match.group(1) if year_match else "未知"

            by_year.setdefault(year, {"count": 0, "pages": 0})
            by_year[year]["count"] += 1
            by_year[year]["pages"] += pages

print("=" * 50)
print(f"目录：{folder}")
print("=" * 50)
print(f"{'年份':>6}  {'数量':>6}  {'页数':>6}")
print("-" * 26)
grand_count = 0
grand_pages = 0
for year in sorted(by_year.keys()):
    c = by_year[year]["count"]
    p = by_year[year]["pages"]
    print(f"{year:>6}  {c:>6}  {p:>6}")
    grand_count += c
    grand_pages += p
print("-" * 26)
print(f"{'合计':>6}  {grand_count:>6}  {grand_pages:>6}")
print("=" * 50)