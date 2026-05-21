# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['meeting_minutes_tool\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('meeting_minutes_tool\\icon.ico', '.')],
    hiddenimports=['export_view', 'heatmap_view', 'statistics_view', 'watcher', 'excel_utils', 'llm_utils', 'ocr_utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    icon=['meeting_minutes_tool\\icon.ico'],
)
