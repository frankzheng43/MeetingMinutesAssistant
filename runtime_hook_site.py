# -*- coding: utf-8 -*-
"""
PyInstaller runtime hook: 在冻结环境下提供 site 模块兼容
PaddleOCR/paddlepaddle 的依赖链中部分代码会 import site
"""
import sys
import os

if 'site' not in sys.modules:
    import types
    site_module = types.ModuleType('site')

    # ---- 常用属性 ----
    site_module.ENABLE_USER_SITE = None
    site_module.USER_SITE = None
    site_module.USER_BASE = None

    # ---- 常用函数 ----

    def getsitepackages():
        """返回 site-packages 目录列表"""
        return [p for p in sys.path if 'site-packages' in p]

    def getusersitepackages():
        """返回用户 site-packages 目录"""
        return None

    def getuserbase():
        """返回用户基础目录"""
        return None

    def addsitedir(sitedir, known_paths=None):
        """添加目录到 sys.path（简化版）"""
        if sitedir not in sys.path:
            sys.path.append(sitedir)
        return known_paths

    def check_enableusersite():
        return None

    site_module.getsitepackages = getsitepackages
    site_module.getusersitepackages = getusersitepackages
    site_module.getuserbase = getuserbase
    site_module.addsitedir = addsitedir
    site_module.check_enableusersite = check_enableusersite

    # 注册模块
    site_module.__file__ = __file__
    site_module.__package__ = None
    sys.modules['site'] = site_module
