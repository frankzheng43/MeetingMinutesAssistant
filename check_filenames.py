#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查 F 盘会议纪要 PDF 文件名是否符合程序输入要求
输出文件：检查报告.md（与脚本同目录）
"""

import os
import re
import sys

# 输出文件路径（保存在脚本同目录）
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "检查报告.md")

WATCH_FOLDER = r"F:\共享文件夹\公用\@存档区\2018年以来三会纪要"

# ====== 程序中的规则 ======

MEETING_TYPE_KEYWORDS = {
    "党委会": ["党委"],
    "董事会": ["董事"],
    "总经办": ["总经办", "总经理"],
}

RECORD_PATTERN = re.compile(r'^(.+?)[〔【\[（(]\s*(\d{4})\s*[〕】\]））]\s*(第)?\s*(\d+)\s*(号|期)$')

BRACKET_MAP = str.maketrans({
    '【': '〔', '】': '〕',
    '[': '〔', ']': '〕',
    '（': '〔', '）': '〕',
    '(': '〔', ')': '〕',
})


def detect_meeting_type_from_path(file_path: str):
    path_lower = file_path.lower()
    for meeting_type, keywords in MEETING_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in path_lower:
                return meeting_type
    return None


def detect_year_from_path(file_path: str):
    parts = file_path.replace("\\", "/").split("/")
    for part in parts:
        if re.match(r'^\d{4}$', part):
            return part
    return None


def extract_record_number(filename: str):
    name_no_ext = os.path.splitext(filename)[0]
    match = RECORD_PATTERN.match(name_no_ext)
    if match:
        prefix = match.group(1)
        year = match.group(2)
        number = match.group(4)   # 跳过第3组"第"
        suffix = match.group(5)   # 号 或 期
        return f"{prefix}〔{year}〕{number}{suffix}"
    return None


def normalize_brackets(filename: str) -> str:
    name_no_ext, ext = os.path.splitext(filename)
    name_no_ext = name_no_ext.translate(BRACKET_MAP)
    return name_no_ext + ext


# ====== 统计 ======

if not os.path.exists(WATCH_FOLDER):
    # 目录不存在时也输出到文件
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 目录不存在\n\n`{WATCH_FOLDER}`\n\n请确认路径是否正确。\n")
    print(f"❌ 目录不存在，报告已生成：{OUTPUT_FILE}")
    exit(1)

# 输出重定向到 Markdown 文件
os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
sys.stdout = open(OUTPUT_FILE, "w", encoding="utf-8")

by_year = {}        # year -> { meeting_type -> count }
issues = []
ok_count = 0
total_count = 0

for root, dirs, files in os.walk(WATCH_FOLDER):
    for f in sorted(files):
        if not f.lower().endswith(".pdf"):
            continue

        total_count += 1
        full_path = os.path.join(root, f)
        rel_path = os.path.relpath(full_path, WATCH_FOLDER)
        file_issues = []

        meeting_type = detect_meeting_type_from_path(full_path)
        if not meeting_type:
            file_issues.append("meeting_type")
            meeting_type = "无法识别"

        year = detect_year_from_path(full_path)
        if not year:
            file_issues.append("year")
            year = "未知"

        record_number = extract_record_number(f)
        if not record_number:
            file_issues.append("record_number")

        normalized = normalize_brackets(f)
        if normalized != f:
            file_issues.append("brackets")

        fname_lower = f.lower()
        has_type_in_filename = any(
            kw in fname_lower
            for type_kws in MEETING_TYPE_KEYWORDS.values()
            for kw in type_kws
        )
        if meeting_type != "无法识别" and record_number and not has_type_in_filename:
            file_issues.append("prefix")

        # 统计
        by_year.setdefault(year, {})
        by_year[year].setdefault(meeting_type, 0)
        by_year[year][meeting_type] += 1

        if file_issues:
            issues.append((rel_path, meeting_type, year, file_issues))
        else:
            ok_count += 1

# ====== 输出 ======

print(f"# 会议纪要文件名合规检查报告\n")
print(f"**扫描目录：** `{WATCH_FOLDER}`\n")
print(f"**共扫描：** {total_count} 个 PDF 文件\n")

print("---\n")

# 概览
print("## 📊 总览\n")
print("| 状态 | 数量 | 占比 |")
print("|------|------|------|")
print(f"| ✅ 完全合规 | {ok_count} | {ok_count/total_count*100:.1f}% |")
print(f"| ⚠️  存在问题 | {len(issues)} | {len(issues)/total_count*100:.1f}% |")
print()

# 按年份 × 类型统计
print("## 📁 文件分布（年份 × 会议类型）\n")
print("| 年份 | 党委会 | 董事会 | 总经办 | 无法识别 | 合计 |")
print("|------|--------|--------|--------|----------|------|")
all_types = ["党委会", "董事会", "总经办", "无法识别"]
grand_total = 0
for year in sorted(by_year.keys()):
    row = [year]
    row_total = 0
    for t in all_types:
        cnt = by_year[year].get(t, 0)
        row.append(str(cnt))
        row_total += cnt
    row.append(str(row_total))
    grand_total += row_total
    print("| " + " | ".join(row) + " |")
# 合计行
type_totals = {}
for y in by_year:
    for t, c in by_year[y].items():
        type_totals[t] = type_totals.get(t, 0) + c
type_total_str = " | ".join(str(type_totals.get(t, 0)) for t in all_types)
print(f"| **合计** | {type_total_str} | **{grand_total}** |")
print()

print("---\n")

# 问题文件清单
print("## ❌ 存在问题的文件\n")
if not issues:
    print("_全部合规，无问题。_\n")
else:
    for rel_path, meeting_type, year, file_issues in issues:
        symbols = []
        if "meeting_type" in file_issues:
            symbols.append("❌ 无法检测会议类型")
        if "year" in file_issues:
            symbols.append("❌ 无法检测年份")
        if "record_number" in file_issues:
            symbols.append("⚠️  纪要编号将由 AI 提取")
        if "brackets" in file_issues:
            symbols.append("ℹ️  括号将自动统一")
        if "prefix" in file_issues:
            symbols.append("ℹ️  纪要编号前缀可能不完整")

        print(f"### 📄 `{rel_path}`\n")
        print(f"- 检测到：`{meeting_type}` / `{year}`")
        for s in symbols:
            print(f"- {s}")
        print()
        print("检查结果：\n")
        checks = []
        checks.append(f"- **会议类型**：{'✅' if 'meeting_type' not in file_issues else '❌'} {meeting_type}")
        checks.append(f"- **年份**：{'✅' if 'year' not in file_issues else '❌'} {year}")
        checks.append(f"- **纪要编号**：{'✅' if 'record_number' not in file_issues else '⚠️  将由 AI 从内容提取'}")
        checks.append(f"- **括号格式**：{'✅' if 'brackets' not in file_issues else 'ℹ️  启动时将自动统一'}")
        for c in checks:
            print(c)
        print()

print("---\n")

# 规则说明
print("## 📋 程序预期的命名规则\n")
print("### 目录结构\n")
print("```")
print("监听目录/")
print("├── 2026/              ← 年份（4位数字）")
print("│   ├── 党委会/        ← 会议类型")
print("│   │   ├── 党委会〔2026〕1号.pdf")
print("│   │   └── 党委会〔2026〕2号.pdf")
print("│   ├── 董事会/")
print("│   └── 总经办/")
print("├── 2025/")
print("└── ...")
print("```\n")
print("### 文件名格式\n")
print("`会议类型〔年份〕序号号.pdf`，如 `党委会〔2026〕4号.pdf`\n")
print("### 关键词识别规则\n")
print("| 会议类型 | 关键词 |")
print("|----------|--------|")
print("| 党委会 | 党委 |")
print("| 董事会 | 董事 |")
print("| 总经办 | 总经办、总经理 |\n")
print("### 处理策略\n")
print("| 情况 | 处理方式 |")
print("|------|----------|")
print("| 会议类型无法检测 | ❌ 文件被跳过，不处理 |")
print("| 年份无法检测 | ⚠️ 年份为空，数据不完整 |")
print("| 文件名不规范 | ⚠️ 纪要编号改由 AI 从内容提取（较慢） |")
print("| 括号格式不规范 | ✅ 启动时自动统一为「〔〕」 |")

# 关闭文件，恢复 stdout
sys.stdout.close()
sys.stdout = sys.__stdout__

print(f"✅ 检查报告已生成：{OUTPUT_FILE}")
