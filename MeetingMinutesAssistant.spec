# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['meeting_minutes_tool\\main.py'],
    pathex=['meeting_minutes_tool'],
    binaries=[],
    datas=[('meeting_minutes_tool\\resources\\icon.ico', 'resources')],
    hiddenimports=[
        # 应用模块
        'export_view', 'heatmap_view', 'statistics_view',
        'watcher', 'excel_utils', 'llm_utils', 'ocr_utils',
        '_stdlib_compat',  # 批量包含常用标准库模块
        'site',  # PyInstaller 默认排除，PaddleOCR 依赖链需要
        # 第三方依赖（显式声明避免遗漏）
        'uuid', 'zoneinfo', 'copy', 'struct', 'json', 'hashlib',
        'shutil', 'csv', 'configparser', 'dataclasses',
        'numbers', 'decimal', 'pprint',
        'openpyxl',
        'fitz',
        'watchdog', 'watchdog.events', 'watchdog.observers',
        'requests',
        # PIL/Pillow（C扩展，需显式声明）
        'PIL', 'PIL._imagingtk', 'PIL.ImageTk', 'PIL.ImageDraw',
        # 系统托盘（可选）
        'pystray',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook_site.py'],
    excludes=[
        # PaddleOCR 运行时动态下载，不打包进 EXE
        'paddleocr', 'paddle', 'paddlex',
        # Paddle 的依赖链（太大）
        'pandas', 'numpy', 'opencv_contrib_python',
        'cv2', 'shapely', 'pyclipper', 'pypdfium2',
        'modelscope', 'huggingface_hub',
        'aistudio_sdk', 'bce_python_sdk',
        'httpx', 'httpcore', 'anyio',
        'pydantic', 'pydantic_core',
        'ruamel', 'ruamel.yaml',
        'networkx', 'protobuf',
        'opt_einsum', 'safetensors',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MeetingMinutesAssistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['meeting_minutes_tool\\resources\\icon.ico'],
)
