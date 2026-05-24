#!/usr/bin/env python
"""测试 PaddleOCR 依赖链，找出所有缺失模块"""
import sys
import os
import importlib
import types
import pkgutil

# 模拟 EXE 环境
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dist', 'paddle_deps'))

# 模拟 site 模块
if 'site' not in sys.modules:
    site_module = types.ModuleType('site')
    site_module.ENABLE_USER_SITE = None
    site_module.USER_SITE = None
    site_module.USER_BASE = None
    def getsitepackages(): return [p for p in sys.path if 'site-packages' in p]
    def getusersitepackages(): return None
    def getuserbase(): return None
    def addsitedir(sitedir, known_paths=None):
        if sitedir not in sys.path: sys.path.append(sitedir)
        return known_paths
    def check_enableusersite(): return None
    site_module.getsitepackages = getsitepackages
    site_module.getusersitepackages = getusersitepackages
    site_module.getuserbase = getuserbase
    site_module.addsitedir = addsitedir
    site_module.check_enableusersite = check_enableusersite
    site_module.__file__ = __file__
    site_module.__package__ = None
    sys.modules['site'] = site_module

missing = set()
visited = set()

def try_import(mod_name):
    if mod_name in visited or mod_name in sys.modules:
        return
    visited.add(mod_name)
    try:
        importlib.import_module(mod_name)
        mod = sys.modules[mod_name]
        if hasattr(mod, '__path__'):
            for imp, name, ispkg in pkgutil.iter_modules(mod.__path__, mod_name + '.'):
                try_import(name)
    except ImportError as e:
        missing.add(str(e))

print("正在扫描 paddleocr 依赖链...")
try_import('paddleocr')

if missing:
    print(f"\n[ERR] 发现 {len(missing)} 个缺失模块:")
    for m in sorted(missing):
        name = m.replace("No module named '", "").rstrip("'")
        if name and name != m:
            print(f"  import {name}")
        else:
            print(f"  {m}")
else:
    print("\n[OK] 所有依赖都已就绪")
