# -*- coding: utf-8 -*-
"""
会议纪要助手 v1.0 - 主程序入口
提供图形界面，用于配置参数、启动/停止文件监控、查看运行日志
"""

import json
import logging
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
from PIL import Image, ImageDraw, ImageTk

# 配置日志 - 文件日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)

logger = logging.getLogger(__name__)

# 配置文件路径
# 判断是否作为 deb 包安装（可通过启动脚本传入的环境变量）
_INSTALLED_PATH = "/usr/lib/meeting-minutes-tool"
if os.path.dirname(os.path.abspath(__file__)) == _INSTALLED_PATH or \
   os.path.dirname(os.path.abspath(sys.argv[0])) == "/usr/bin":
    # deb 包安装模式：配置文件保存在 ~/.config/meeting-minutes-tool/
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "meeting-minutes-tool")
elif hasattr(sys, 'frozen') and getattr(sys, 'frozen', False):
    # PyInstaller 打包的 EXE 模式：配置文件保存在 EXE 同目录
    CONFIG_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 开发模式：配置文件保存在主程序根目录
    CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 确保配置目录存在
os.makedirs(CONFIG_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 系统托盘相关
_HAS_TRAY = False
try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except ImportError:
    logger.warning("pystray 未安装，系统托盘功能不可用")
    _HAS_TRAY = False


class TextHandler(logging.Handler):
    """自定义日志处理器，将日志输出到 tkinter 的 ScrolledText 组件"""

    def __init__(self, text_widget: scrolledtext.ScrolledText):
        """
        初始化日志处理器

        :param text_widget: ScrolledText 组件
        """
        super().__init__()
        self.text_widget = text_widget
        # 设置日志格式
        formatter = logging.Formatter(
            "%(asctime)s - %(message)s", datefmt="%H:%M:%S"
        )
        self.setFormatter(formatter)

    def emit(self, record):
        """
        输出日志记录到文本框

        :param record: 日志记录
        """
        msg = self.format(record)
        self.text_widget.after(0, self._append_text, msg)

    def _append_text(self, msg: str):
        """在 GUI 线程中追加文本"""
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)  # 自动滚动到底部
        self.text_widget.configure(state="disabled")


class Application:
    """会议纪要助手主应用程序类"""

    def __init__(self, root: tk.Tk):
        """
        初始化应用程序

        :param root: tkinter 根窗口
        """
        self.root = root
        self.root.title("会议纪要助手 v1.0")
        self.root.geometry("800x650")
        self.root.resizable(True, True)

        # 生成并设置窗口图标
        self._set_window_icon()

        # 监控服务实例
        self.watcher_service = None

        # 配置数据
        self.config = {}

        # 系统托盘相关
        self.tray_icon = None
        self.tray_thread = None

        # 加载配置
        self.load_config()

        # 创建界面
        self._create_widgets()

    def _set_window_icon(self):
        """设置程序窗口图标（使用 icon.ico）"""
        try:
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
            if os.path.exists(ico_path):
                # 1. iconbitmap 设置标题栏图标（Windows 桌面）
                self.root.iconbitmap(default=ico_path)

                # 2. iconphoto 设置任务栏图标
                img = Image.open(ico_path)
                photo = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, photo)
                self._icon_photo = photo  # 保持引用

                logger.info("窗口图标已设置")
            else:
                logger.warning(f"图标文件不存在: {ico_path}")
        except Exception as e:
            logger.warning(f"设置窗口图标失败: {e}")

    def _create_widgets(self):
        """创建界面组件"""
        # ========== 创建标签页 ==========
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ---- 标签页1: 热力图 ----
        self.tab_heatmap = tk.Frame(self.notebook)
        self.notebook.add(self.tab_heatmap, text="  📊 热力图 ")

        # ---- 标签页2: 统计页 ----
        self.tab_statistics = tk.Frame(self.notebook)
        self.notebook.add(self.tab_statistics, text="  📈 统计页 ")

        # ---- 标签页3: 导出页 ----
        self.tab_export = tk.Frame(self.notebook)
        self.notebook.add(self.tab_export, text="  📤 导出页 ")

        # ---- 标签页4: 配置页 ----
        self.tab_monitor = tk.Frame(self.notebook)
        self.notebook.add(self.tab_monitor, text="  ⚙️ 配置页 ")

        # ========== 构建热力图标签页 ==========
        self._build_heatmap_tab()

        # ========== 构建统计视图标签页 ==========
        self._build_statistics_tab()

        # ========== 构建导出标签页 ==========
        self._build_export_tab()

        # ========== 构建监控管理标签页 ==========
        self._build_monitor_tab()

        # 设置窗口关闭事件处理（最小化到托盘）
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_monitor_tab(self):
        """构建监控管理标签页"""
        main_frame = tk.Frame(self.tab_monitor, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 配置区域 ==========
        config_frame = tk.LabelFrame(
            main_frame, text="配置信息", padx=10, pady=10
        )
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # 监听文件夹
        row = 0
        tk.Label(config_frame, text="监听文件夹：", width=14, anchor="e").grid(
            row=row, column=0, sticky="e", padx=(0, 5), pady=5
        )
        self.folder_var = tk.StringVar(value=self.config.get("watch_folder", ""))
        self.folder_entry = tk.Entry(
            config_frame, textvariable=self.folder_var, width=50
        )
        self.folder_entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=5)
        tk.Button(
            config_frame,
            text="选择...",
            command=self._select_folder,
            width=8,
        ).grid(row=row, column=2, padx=(0, 5), pady=5)

        # 输出目录
        row = 1
        tk.Label(config_frame, text="输出目录：", width=14, anchor="e").grid(
            row=row, column=0, sticky="e", padx=(0, 5), pady=5
        )
        self.output_var = tk.StringVar(value=self.config.get("output_dir", ""))
        self.output_entry = tk.Entry(
            config_frame, textvariable=self.output_var, width=50
        )
        self.output_entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=5)
        tk.Button(
            config_frame,
            text="选择...",
            command=self._select_output_dir,
            width=8,
        ).grid(row=row, column=2, padx=(0, 5), pady=5)

        # 百度 OCR AK
        row = 2
        tk.Label(config_frame, text="百度 OCR AK：", width=14, anchor="e").grid(
            row=row, column=0, sticky="e", padx=(0, 5), pady=5
        )
        self.ak_var = tk.StringVar(value=self.config.get("api_key", ""))
        self.ak_entry = tk.Entry(
            config_frame, textvariable=self.ak_var, width=50, show="*"
        )
        self.ak_entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=5)

        # 百度 OCR SK
        row = 3
        tk.Label(config_frame, text="百度 OCR SK：", width=14, anchor="e").grid(
            row=row, column=0, sticky="e", padx=(0, 5), pady=5
        )
        self.sk_var = tk.StringVar(value=self.config.get("secret_key", ""))
        self.sk_entry = tk.Entry(
            config_frame, textvariable=self.sk_var, width=50, show="*"
        )
        self.sk_entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=5)

        # DeepSeek Key
        row = 4
        tk.Label(config_frame, text="DeepSeek Key：", width=14, anchor="e").grid(
            row=row, column=0, sticky="e", padx=(0, 5), pady=5
        )
        self.ds_var = tk.StringVar(value=self.config.get("deepseek_key", ""))
        self.ds_entry = tk.Entry(
            config_frame, textvariable=self.ds_var, width=50, show="*"
        )
        self.ds_entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=5)

        # 配置区域列权重
        config_frame.columnconfigure(1, weight=1)

        # ========== 按钮区域 ==========
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.save_btn = tk.Button(
            button_frame,
            text="保存配置",
            command=self._save_config,
            width=12,
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.import_btn = tk.Button(
            button_frame,
            text="导入配置",
            command=self._import_config,
            width=10,
        )
        self.import_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.export_btn = tk.Button(
            button_frame,
            text="导出配置",
            command=self._export_config,
            width=10,
        )
        self.export_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.start_btn = tk.Button(
            button_frame,
            text="开始监听",
            command=self._start_monitor,
            width=12,
            bg="#4CAF50",
            fg="white",
            font=("", 10, "bold"),
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = tk.Button(
            button_frame,
            text="停止监听",
            command=self._stop_monitor,
            width=12,
            bg="#F44336",
            fg="white",
            font=("", 10, "bold"),
            state="disabled",
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.exit_btn = tk.Button(
            button_frame,
            text="退出",
            command=self._on_closing,
            width=12,
        )
        self.exit_btn.pack(side=tk.RIGHT)

        # ========== 日志区域 ==========
        log_frame = tk.LabelFrame(
            main_frame, text="运行日志", padx=5, pady=5
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            state="disabled",
            font=("Consolas", 9),
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="white",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 添加自定义日志处理器
        self._setup_logging()

    def _build_heatmap_tab(self):
        """构建热力图标签页"""
        from heatmap_view import HeatmapView

        self.heatmap_view = HeatmapView(
            self.tab_heatmap,
            config_callback=lambda: self.config
        )
        self.heatmap_view.pack(fill=tk.BOTH, expand=True)

    def _build_statistics_tab(self):
        """构建统计视图标签页"""
        from statistics_view import StatisticsView

        self.statistics_view = StatisticsView(
            self.tab_statistics,
            config_callback=lambda: self.config
        )
        self.statistics_view.pack(fill=tk.BOTH, expand=True)

    def _build_export_tab(self):
        """构建导出标签页"""
        from export_view import ExportView

        self.export_view = ExportView(
            self.tab_export,
            config_callback=lambda: self.config
        )
        self.export_view.pack(fill=tk.BOTH, expand=True)

    def _setup_logging(self):
        """设置日志系统，添加 GUI 日志处理器"""
        text_handler = TextHandler(self.log_text)
        text_handler.setLevel(logging.INFO)
        # 添加到根日志记录器
        logging.getLogger().addHandler(text_handler)

    def _select_folder(self):
        """选择监听文件夹"""
        folder = filedialog.askdirectory(title="选择监听文件夹")
        if folder:
            self.folder_var.set(folder)

    def _select_output_dir(self):
        """选择输出目录"""
        folder = filedialog.askdirectory(title="选择输出目录（将自动生成党委会.xlsx、董事会.xlsx、总经办.xlsx）")
        if folder:
            self.output_var.set(folder)

    def _get_config_from_ui(self) -> dict:
        """从界面获取配置数据"""
        return {
            "watch_folder": self.folder_var.get().strip(),
            "output_dir": self.output_var.get().strip(),
            "api_key": self.ak_var.get().strip(),
            "secret_key": self.sk_var.get().strip(),
            "deepseek_key": self.ds_var.get().strip(),
        }

    def _save_config(self):
        """保存配置到文件"""
        try:
            config = self._get_config_from_ui()
            # 保存统计视图的"统计页数"复选框状态
            if hasattr(self, 'statistics_view'):
                config["count_pages"] = self.statistics_view.get_count_pages_state()
            else:
                config["count_pages"] = True

            config_dir = os.path.dirname(os.path.abspath(CONFIG_FILE))
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            self.config = config
            logger.info("配置已保存")
            messagebox.showinfo("提示", "配置保存成功！")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            messagebox.showerror("错误", f"保存配置失败：{e}")

    def _import_config(self):
        """从文件导入配置"""
        try:
            file_path = filedialog.askopenfilename(
                title="选择配置文件",
                filetypes=[("JSON 配置文件", "*.json"), ("所有文件", "*.*")]
            )
            if not file_path:
                return

            with open(file_path, "r", encoding="utf-8") as f:
                imported_config = json.load(f)

            # 回填到界面
            self.folder_var.set(imported_config.get("watch_folder", ""))
            self.output_var.set(imported_config.get("output_dir", ""))
            self.ak_var.set(imported_config.get("api_key", ""))
            self.sk_var.set(imported_config.get("secret_key", ""))
            self.ds_var.set(imported_config.get("deepseek_key", ""))

            # 更新内存配置
            self.config = imported_config

            logger.info(f"配置已从 {file_path} 导入")
            messagebox.showinfo("提示", "配置导入成功！请检查各项配置是否正确，然后点击「保存配置」持久化。")
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            messagebox.showerror("错误", f"导入配置失败：{e}")

    def _export_config(self):
        """导出配置到文件"""
        try:
            config = self._get_config_from_ui()
            if not any(config.values()):
                messagebox.showwarning("提示", "当前配置为空，请先填写配置信息。")
                return

            file_path = filedialog.asksaveasfilename(
                title="导出配置文件",
                defaultextension=".json",
                filetypes=[("JSON 配置文件", "*.json"), ("所有文件", "*.*")],
                initialfile="config.json"
            )
            if not file_path:
                return

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"配置已导出到 {file_path}")
            messagebox.showinfo("提示", f"配置已导出到：\n{file_path}")
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            messagebox.showerror("错误", f"导出配置失败：{e}")

    def load_config(self):
        """从文件加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                logger.info("配置已加载")
            else:
                self.config = {}
                logger.info("配置文件不存在，使用默认配置")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self.config = {}

    def _validate_config(self, config: dict) -> bool:
        """
        验证配置是否完整

        :param config: 配置字典
        :return: 是否通过验证
        """
        missing_fields = []
        if not config.get("watch_folder"):
            missing_fields.append("监听文件夹")
        if not config.get("output_dir"):
            missing_fields.append("输出目录")
        if not config.get("api_key"):
            missing_fields.append("百度 OCR AK")
        if not config.get("secret_key"):
            missing_fields.append("百度 OCR SK")
        if not config.get("deepseek_key"):
            missing_fields.append("DeepSeek Key")

        if missing_fields:
            messagebox.showwarning(
                "配置不完整",
                f"请填写以下必填项：\n" + "\n".join(f"  • {f}" for f in missing_fields),
            )
            return False
        return True

    def _start_monitor(self):
        """启动文件监控"""
        config = self._get_config_from_ui()

        if not self._validate_config(config):
            return

        # 先保存配置
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.config = config
        except Exception as e:
            logger.error(f"保存配置失败: {e}")

        try:
            # 导入监控服务
            from watcher import WatcherService

            # 创建并启动监控服务
            self.watcher_service = WatcherService(
                folder=config["watch_folder"],
                config=config,
                log_func=lambda msg: logger.info(msg),
            )
            self.watcher_service.start()

            # 更新按钮状态
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.save_btn.configure(state="disabled")

            logger.info("监控服务已启动")

        except Exception as e:
            logger.error(f"启动监控服务失败: {e}")
            messagebox.showerror("错误", f"启动监控服务失败：{e}")

    def _stop_monitor(self):
        """停止文件监控"""
        if self.watcher_service:
            try:
                self.watcher_service.stop()
                self.watcher_service = None

                # 更新按钮状态
                self.start_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
                self.save_btn.configure(state="normal")

                logger.info("监控服务已停止")
            except Exception as e:
                logger.error(f"停止监控服务失败: {e}")
                messagebox.showerror("错误", f"停止监控服务失败：{e}")

    # ========== 系统托盘相关方法 ==========

    def _create_tray_icon(self):
        """创建系统托盘图标（使用 icon.ico，在后台线程中运行）"""
        if not _HAS_TRAY:
            return

        # 从 .ico 文件加载图片作为托盘图标
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
        if os.path.exists(ico_path):
            image = Image.open(ico_path)
        else:
            # 如果 .ico 不存在，回退生成一个简单图标
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.ellipse([4, 4, 60, 60], fill="#4472C4")

        # 创建菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示主窗口", self._show_window, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出程序", self._quit_app),
        )

        self.tray_icon = pystray.Icon(
            "meeting_minutes_tool",
            image,
            "会议纪要助手",
            menu,
        )

        # 运行托盘（阻塞，在独立线程中）
        self.tray_icon.run()

    def _show_window(self):
        """显示主窗口（从托盘恢复）"""
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        """恢复窗口显示"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _hide_to_tray(self):
        """隐藏到系统托盘"""
        if not _HAS_TRAY:
            # 如果没有托盘支持，直接退出
            self._force_quit()
            return

        # 隐藏窗口
        self.root.withdraw()

        # 如果托盘图标未创建，在后台线程中创建
        if self.tray_icon is None:
            self.tray_thread = threading.Thread(target=self._create_tray_icon, daemon=True)
            self.tray_thread.start()
        else:
            # 托盘已在运行，只需确保图标可见
            try:
                self.tray_icon.visible = True
            except Exception:
                pass

    def _on_closing(self):
        """点击关闭按钮事件 - 最小化到系统托盘"""
        self._hide_to_tray()

    def _quit_app(self):
        """从托盘菜单选择退出时调用"""
        logger.info("用户通过托盘菜单选择退出程序...")
        self.root.after(0, self._force_quit)

    def _force_quit(self):
        """强制退出程序"""
        # 停止托盘图标
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        # 停止监控
        if self.watcher_service:
            try:
                self.watcher_service.stop()
            except Exception:
                pass
        # 强制退出
        try:
            sys.stdout.flush()
        except Exception:
            pass
        try:
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(0)


def main():
    """程序入口函数"""
    root = tk.Tk()
    app = Application(root)
    root.mainloop()


if __name__ == "__main__":
    main()