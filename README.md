# 会议纪要助手 📝

> 自动识别 PDF 会议纪要，提取结构化信息，汇总到 Excel

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

---

## 概述

会议纪要助手是一款桌面工具，能够自动监控指定文件夹中的 PDF 格式会议纪要文件，通过 **OCR 识别 → AI 提取 → Excel 汇总** 全自动管线，将非结构化的 PDF 文件转化为结构化的数据表格。

### 支持的会议类型

| 类型 | 提取内容 |
|------|----------|
| 党委会 | 议定事项、传达学习等 |
| 董事会 | 议案、投票结果等（含党委意见） |
| 总经办 | 督查落实、研究事项等 |

### 核心特性

- 🔍 **文件监控** — 自动检测新增/修改/删除的 PDF，实时处理
- ⚡ **缓存加速** — 已处理的文件自动缓存，重复运行秒级跳过
- 🔄 **断点续传** — 意外中断后重启，已处理文件不重复
- 💾 **自动备份** — Excel 每次写入前自动备份到 `_excel_backup/`
- 📊 **热力图** — 50 号网格可视化纪要分布
- 📈 **统计视图** — 按年份 × 会议类型交叉统计

---

## 快速开始

### 前置准备

1. 申请 [百度 OCR API](https://console.bce.baidu.com/)（免费额度充足）
2. 申请 [DeepSeek API](https://platform.deepseek.com/)（费用很低，需充值）

### 安装

**Windows — 下载 EXE：**

从 [Releases 页面](https://github.com/frankzheng43/MeetingMinutesAssistant/releases) 下载 `MeetingMinutesAssistant.exe`，双击运行。

**Linux — DEB 包：**

```bash
sudo dpkg -i meeting-minutes-tool_1.0.0_all.deb
sudo apt-get install -f
meeting-minutes-tool
```

**源码运行：**

```bash
pip install -r meeting_minutes_tool/requirements.txt
python meeting_minutes_tool/main.py
```

### 目录结构要求

监听文件夹建议按以下结构组织：

```
监听目录/
├── 2026/                    ← 年份文件夹
│   ├── 党委会/              ← 会议类型文件夹
│   │   ├── 党委会〔2026〕1号.pdf
│   │   └── 党委会〔2026〕2号.pdf
│   ├── 董事会/
│   │   └── 董事会〔2026〕1号.pdf
│   └── 总经办/
│       └── 总经办〔2026〕1号.pdf
├── 2025/
│   └── ...
```

> 软件根据路径中的关键词（"党委"、"董事"、"总经办"）自动判断会议类型。

### 使用步骤

```
1. 启动软件 → 2. 填写配置（监听目录/API密钥等）
→ 3. 保存配置 → 4. 点击"开始监听"
→ 5. 等待处理完成 → 6. 查看 Excel 输出
```

**Excel 输出文件：** `会议纪要汇总_YYYYMMDD_HHmmss.xlsx`

包含三个 Sheet（党委会/董事会/总经办），表头字段：

| 纪要编号 | 会议日期 | 主持人 | 年份 | 议题序号 | 议题标题 | 议题详细内容 | 印发时间 | 来源文件 |

数据按 **年份升序 + 纪要号升序** 自动排列。

---

## 数据流

```
PDF 文件放入监听目录
       ↓
自动检测新增文件
       ↓
OCR 识别（百度 API）── 数据经第三方服务器
       ↓
AI 提取（DeepSeek API）── 数据经第三方服务器
       ↓
写入本地 Excel 文件
```

> ⚠️ 会议纪要内容会经过百度 OCR 和 DeepSeek 的第三方服务器。
> 涉及敏感信息的文件请勿使用本软件处理。

---

## 用户文档

完整的使用说明和常见问题解答请参阅：
- [用户文档](meeting_minutes_tool/用户文档.md)

## 开发者文档

架构说明、模块规格和构建指南请参阅：
- [开发者文档](meeting_minutes_tool/开发者文档.md)

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 界面 | Python tkinter |
| PDF 处理 | PyMuPDF (fitz) |
| OCR | 百度 OCR API |
| AI 提取 | DeepSeek API |
| Excel | openpyxl |
| 文件监控 | watchdog |
| 打包 | PyInstaller (Win) / dpkg-deb (Linux) |

## 许可证

[GPL-3.0](LICENSE)
