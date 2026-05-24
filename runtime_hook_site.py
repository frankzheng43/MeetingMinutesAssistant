# -*- coding: utf-8 -*-
"""
PyInstaller runtime hook: 在冻结环境下提供 site 模块兼容
PaddleOCR 的某些依赖链需要 import site
"""
import sys
import os

# 在 PyInstaller 冻结环境中，Python 以 -S 启动，site 模块不可用
# 创建一个最小化的 site 模块兼容，满足 paddlepaddle 等库的导入需求
if 'site' not in sys.modules:
    import types
    site_module = types.ModuleType('site')
    
    # site.ENABLE_USER_SITE - 是否启用用户 site-packages
    site_module.ENABLE_USER_SITE = None
    
    # site.USER_SITE - 用户 site-packages 路径
    site_module.USER_SITE = None
    
    # site.USER_BASE - 用户基础目录
    site_module.USER_BASE = None
    
    # 注册模块
    site_module.__file__ = os.path.join(os.path.dirname(__file__), 'site.py')
    site_module.__package__ = None
    sys.modules['site'] = site_module
