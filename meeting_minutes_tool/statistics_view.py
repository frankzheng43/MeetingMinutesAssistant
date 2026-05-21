# -*- coding: utf-8 -*-
"""
统计视图模块
提供会议纪要统计表格，按年份（行）× 会议类型（列）展示 PDF 文件数量和页数
"""

import logging
import os
import re
import tkinter as tk
from tkinter import ttk

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# 会议类型列表（与项目其他模块保持一致）
MEETING_TYPES = ["党委会", "董事会", "总经办"]

# 样式常量
BG_COLOR = "#F5F5F5"
HEADER_BG = "#4472C4"
HEADER_FG = "#FFFFFF"
TOTAL_BG = "#D6E4F0"
EVEN_ROW_BG = "#FFFFFF"
ODD_ROW_BG = "#F2F7FB"
FONT = ("微软雅黑", 10)
FONT_BOLD = ("微软雅黑", 10, "bold")
FONT_HEADER = ("微软雅黑", 11, "bold")
FONT_TITLE = ("微软雅黑", 14, "bold")


class StatisticsView(tk.Frame):
    """统计视图"""

    def __init__(self, parent, config_callback):
        """
        :param parent: 父容器
        :param config_callback: 获取配置的回调函数
        """
        super().__init__(parent)
        self.config_callback = config_callback
        self._create_widgets()

    def _get_config(self) -> dict:
        """获取当前配置"""
        try:
            return self.config_callback()
        except Exception:
            return {}

    def get_count_pages_state(self) -> bool:
        """获取当前"统计页数"复选框的状态"""
        return self.count_pages_var.get()

    def _create_widgets(self):
        """创建界面组件"""
        # ========== 顶部控制栏 ==========
        control_frame = tk.Frame(self, bg=BG_COLOR, padx=15, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Label(
            control_frame, text="📊 统计视图",
            bg=BG_COLOR, font=FONT_TITLE
        ).pack(side=tk.LEFT, padx=(0, 20))

        self.refresh_btn = tk.Button(
            control_frame, text="🔄 刷新", command=self._refresh,
            bg="#3498DB", fg="white", font=("微软雅黑", 10, "bold"),
            padx=12, pady=2, cursor="hand2"
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))

        # 是否统计页数复选框
        config = self._get_config()
        self.count_pages_var = tk.BooleanVar(value=config.get("count_pages", True))
        self.count_pages_cb = tk.Checkbutton(
            control_frame, text="统计页数", variable=self.count_pages_var,
            bg=BG_COLOR, font=FONT, cursor="hand2",
            command=self._refresh
        )
        self.count_pages_cb.pack(side=tk.LEFT, padx=(5, 10))

        self.summary_label = tk.Label(
            control_frame, text="", bg=BG_COLOR,
            font=("微软雅黑", 10), fg="#666666"
        )
        self.summary_label.pack(side=tk.RIGHT, padx=(10, 0))

        # 分隔线
        separator = tk.Frame(self, height=2, bg="#DDDDDD")
        separator.pack(fill=tk.X)

        # ========== 表格区域（带滚动条） ==========
        table_frame = tk.Frame(self, bg="white")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # 使用 Canvas + Frame 实现可滚动
        self.canvas = tk.Canvas(table_frame, bg="white", highlightthickness=0)
        scrollbar = tk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        self._bind_mousewheel()

        # 绑定画布大小变化
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # ========== 初始加载 ==========
        self._refresh()

    def _bind_mousewheel(self):
        """绑定鼠标滚轮事件"""
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _on_canvas_configure(self, event):
        """画布大小变化时调整内部 frame 宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _refresh(self):
        """刷新统计数据"""
        # 清除旧内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        config = self._get_config()
        watch_folder = config.get("watch_folder", "")

        if not watch_folder or not os.path.exists(watch_folder):
            self._render_empty("监听目录未配置或不存在")
            self.summary_label.config(text="请先配置监听目录")
            return

        # 扫描统计数据
        try:
            stats = self._scan_statistics(watch_folder)
            self._render_table(stats, watch_folder)
        except Exception as e:
            logger.error(f"统计数据失败: {e}")
            self._render_empty(f"统计数据失败: {e}")

    def _scan_statistics(self, watch_folder: str) -> dict:
        """
        扫描监听目录下所有年份/会议类型的 PDF 文件，统计数量和页数
        :return: {
            "years": {"2024": {"党委会": (count, pages), "董事会": (count, pages), ...}, ...},
            "totals": {"党委会": (count, pages), ...},
            "grand_total": (count, pages)
        }
        """
        result = {
            "years": {},
            "totals": {mt: (0, 0) for mt in MEETING_TYPES},
            "grand_total": (0, 0),
        }

        # 获取是否统计页数
        count_pages = self.count_pages_var.get()

        # 扫描年份子目录
        if not os.path.exists(watch_folder):
            return result

        for year_dir in sorted(os.listdir(watch_folder)):
            year_path = os.path.normpath(os.path.join(watch_folder, year_dir))
            if not os.path.isdir(year_path):
                continue
            # 只匹配 4 位数字年份
            if not re.match(r'^20\d{2}$', year_dir):
                continue

            year = year_dir
            year_data = {}

            # 扫描每个会议类型子目录
            for mt in MEETING_TYPES:
                mt_path = os.path.join(year_path, mt)
                count, pages = self._count_pdfs(mt_path, count_pages)
                year_data[mt] = (count, pages)

                # 累加到总计
                tc, tp = result["totals"][mt]
                result["totals"][mt] = (tc + count, tp + pages)

            result["years"][year] = year_data

        # 计算总合计
        grand_count = sum(c for c, p in result["totals"].values())
        grand_pages = sum(p for c, p in result["totals"].values())
        result["grand_total"] = (grand_count, grand_pages)

        return result

    @staticmethod
    def _count_pdfs(directory: str, count_pages: bool = True) -> tuple:
        """
        统计指定目录下的 PDF 文件数量和总页数

        :param directory: 目录路径
        :param count_pages: 是否统计页数（False 时只数文件个数，返回页数为 0）
        :return: (文件数量, 总页数)
        """
        if not os.path.exists(directory):
            return (0, 0)

        count = 0
        pages = 0
        for f in os.listdir(directory):
            if not f.lower().endswith(".pdf"):
                continue
            pdf_path = os.path.join(directory, f)
            if count_pages:
                try:
                    doc = fitz.open(pdf_path)
                    pages += doc.page_count
                    count += 1
                    doc.close()
                except Exception as e:
                    logger.warning(f"无法打开 PDF: {pdf_path}, 错误: {e}")
            else:
                # 不统计页数，只计数
                count += 1

        return (count, pages)

    def _render_empty(self, message: str):
        """渲染空状态提示"""
        label = tk.Label(
            self.scrollable_frame,
            text=message,
            font=("微软雅黑", 12),
            fg="#999999",
            bg="white",
            pady=50,
        )
        label.pack()

    def _render_table(self, stats: dict, watch_folder: str):
        """渲染统计表格"""
        years = sorted(stats["years"].keys(), reverse=True)
        grand_count, grand_pages = stats["grand_total"]

        # ========== 顶部摘要 ==========
        self.summary_label.config(
            text=f"总计 {grand_count} 份, 共 {grand_pages} 页 | 监听目录: {watch_folder}"
        )

        if not years:
            label = tk.Label(
                self.scrollable_frame,
                text="未找到任何 PDF 文件",
                font=("微软雅黑", 12),
                fg="#999999",
                bg="white",
                pady=50,
            )
            label.pack()
            return

        # ========== 构建表格容器 ==========
        table_inner = tk.Frame(self.scrollable_frame, bg="white", padx=2, pady=2)
        table_inner.pack(fill=tk.BOTH, expand=True)

        # === 表头行 ===
        # 列: 年份 | 党委会 | 董事会 | 总经办 | 小计(份) | 小计(页)
        headers = ["年份"] + MEETING_TYPES + ["小计(份)", "小计(页)"]
        col_widths = [80, 100, 100, 100, 100, 100]

        for col_idx, (header, width) in enumerate(zip(headers, col_widths)):
            lbl = tk.Label(
                table_inner,
                text=header,
                font=FONT_HEADER,
                bg=HEADER_BG,
                fg=HEADER_FG,
                width=width // 8,
                height=2,
                relief=tk.RAISED,
                borderwidth=1,
            )
            lbl.grid(row=0, column=col_idx, sticky="nsew")

        # === 数据行 ===
        for row_idx, year in enumerate(years):
            bg_color = EVEN_ROW_BG if row_idx % 2 == 0 else ODD_ROW_BG
            year_data = stats["years"][year]

            # 年份列
            lbl = tk.Label(
                table_inner,
                text=year,
                font=FONT_BOLD,
                bg=bg_color,
                fg="#333333",
                width=col_widths[0] // 8,
                height=2,
                relief=tk.RIDGE,
                borderwidth=1,
            )
            lbl.grid(row=row_idx + 1, column=0, sticky="nsew")

            # 各会议类型列
            year_total_count = 0
            year_total_pages = 0
            for mt_idx, mt in enumerate(MEETING_TYPES):
                count, pages = year_data.get(mt, (0, 0))
                year_total_count += count
                year_total_pages += pages
                text = f"{count}" if count > 0 else "-"
                lbl = tk.Label(
                    table_inner,
                    text=text,
                    font=FONT,
                    bg=bg_color,
                    fg="#333333" if count > 0 else "#CCCCCC",
                    width=col_widths[mt_idx + 1] // 8,
                    height=2,
                    relief=tk.RIDGE,
                    borderwidth=1,
                )
                lbl.grid(row=row_idx + 1, column=mt_idx + 1, sticky="nsew")

            # 小计(份)
            lbl = tk.Label(
                table_inner,
                text=str(year_total_count),
                font=FONT_BOLD,
                bg=bg_color,
                fg="#333333",
                width=col_widths[4] // 8,
                height=2,
                relief=tk.RIDGE,
                borderwidth=1,
            )
            lbl.grid(row=row_idx + 1, column=4, sticky="nsew")

            # 小计(页)
            lbl = tk.Label(
                table_inner,
                text=str(year_total_pages),
                font=FONT_BOLD,
                bg=bg_color,
                fg="#333333",
                width=col_widths[5] // 8,
                height=2,
                relief=tk.RIDGE,
                borderwidth=1,
            )
            lbl.grid(row=row_idx + 1, column=5, sticky="nsew")

        # === 合计行 ===
        total_row = len(years) + 1
        # 合计标签
        lbl = tk.Label(
            table_inner,
            text="合计",
            font=FONT_BOLD,
            bg=TOTAL_BG,
            fg="#333333",
            width=col_widths[0] // 8,
            height=2,
            relief=tk.RIDGE,
            borderwidth=2,
        )
        lbl.grid(row=total_row, column=0, sticky="nsew")

        # 各类型合计
        for mt_idx, mt in enumerate(MEETING_TYPES):
            total_count, total_pages = stats["totals"].get(mt, (0, 0))
            text = f"{total_count} / {total_pages}页"
            lbl = tk.Label(
                table_inner,
                text=text,
                font=FONT_BOLD,
                bg=TOTAL_BG,
                fg="#333333",
                width=col_widths[mt_idx + 1] // 8,
                height=2,
                relief=tk.RIDGE,
                borderwidth=2,
            )
            lbl.grid(row=total_row, column=mt_idx + 1, sticky="nsew")

        # 总计(份)
        lbl = tk.Label(
            table_inner,
            text=str(grand_count),
            font=FONT_BOLD,
            bg=TOTAL_BG,
            fg="#333333",
            width=col_widths[4] // 8,
            height=2,
            relief=tk.RIDGE,
            borderwidth=2,
        )
        lbl.grid(row=total_row, column=4, sticky="nsew")

        # 总计(页)
        lbl = tk.Label(
            table_inner,
            text=str(grand_pages),
            font=FONT_BOLD,
            bg=TOTAL_BG,
            fg="#333333",
            width=col_widths[5] // 8,
            height=2,
            relief=tk.RIDGE,
            borderwidth=2,
        )
        lbl.grid(row=total_row, column=5, sticky="nsew")

        # 配置列权重
        for col_idx in range(len(headers)):
            table_inner.columnconfigure(col_idx, weight=1)