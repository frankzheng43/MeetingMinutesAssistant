#!/bin/bash
# ==========================================
# 会议纪要助手 deb 打包脚本
# 在 Debian/Ubuntu 系统上运行此脚本
# ==========================================

set -e

# 版本号
VERSION="1.0.0"
PACKAGE_NAME="meeting-minutes-tool"
BUILD_DIR="deb_build"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo "会议纪要助手 - Debian 打包脚本"
echo "Version: ${VERSION}"
echo "=========================================="

# 清理旧的构建目录
if [ -d "${BUILD_DIR}" ]; then
    echo "清理旧的构建目录..."
    rm -rf "${BUILD_DIR}"
fi

# 创建目录结构
echo "创建目录结构..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps"

# ========== 复制 Python 源码 ==========
echo "复制 Python 源码..."
cp "${PROJECT_DIR}/main.py" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
cp "${PROJECT_DIR}/watcher.py" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
cp "${PROJECT_DIR}/ocr_utils.py" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
cp "${PROJECT_DIR}/llm_utils.py" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
cp "${PROJECT_DIR}/excel_utils.py" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"
cp "${PROJECT_DIR}/requirements.txt" "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/"

# 创建 __init__.py
touch "${BUILD_DIR}/usr/lib/${PACKAGE_NAME}/__init__.py"

# ========== 创建启动脚本 ==========
echo "创建启动脚本..."
cat > "${BUILD_DIR}/usr/bin/${PACKAGE_NAME}" << 'SCRIPT'
#!/bin/bash
# 会议纪要助手 - 启动脚本

APP_DIR="/usr/lib/meeting-minutes-tool"
CONFIG_DIR="${HOME}/.config/meeting-minutes-tool"

# 确保配置目录存在
mkdir -p "${CONFIG_DIR}"

# 切换到配置目录（config.json 将保存在这里）
cd "${CONFIG_DIR}"

# 运行主程序
exec python3 "${APP_DIR}/main.py"
SCRIPT

chmod +x "${BUILD_DIR}/usr/bin/${PACKAGE_NAME}"

# ========== 创建 .desktop 文件 ==========
echo "创建 .desktop 文件..."
cat > "${BUILD_DIR}/usr/share/applications/${PACKAGE_NAME}.desktop" << DESKTOPFILE
[Desktop Entry]
Name=会议纪要助手
Name[zh_CN]=会议纪要助手
Comment=会议纪要PDF自动OCR识别与Excel汇总工具
Comment[zh_CN]=会议纪要PDF自动OCR识别与Excel汇总工具
Exec=meeting-minutes-tool
Icon=meeting-minutes-tool
Terminal=false
Type=Application
Categories=Office;Utility;
Keywords=meeting;minutes;OCR;excel;
DESKTOPFILE

# ========== 创建 DEBIAN/control ==========
echo "创建 DEBIAN/control..."
cat > "${BUILD_DIR}/DEBIAN/control" << CONTROL
Package: meeting-minutes-tool
Version: ${VERSION}
Section: office
Priority: optional
Architecture: all
Essential: no
Installed-Size: $(du -s "${BUILD_DIR}/usr" | cut -f1)
Maintainer: Developer <developer@example.com>
Description: 会议纪要助手 - 会议纪要PDF自动OCR识别与Excel汇总工具
 自动监控指定文件夹中的PDF文件，通过百度OCR识别文字，
 调用DeepSeek API提取结构化会议纪要信息，自动写入Excel汇总表。
 支持党委会、董事会、总经办三种会议类型。
Depends: python3 (>= 3.8), python3-tk, python3-pip, python3-requests, python3-pil
CONTROL

# ========== 创建版权文件 ==========
echo "创建版权文件..."
cat > "${BUILD_DIR}/usr/share/doc/${PACKAGE_NAME}/copyright" << COPYRIGHT
Copyright: 2026 Developer <developer@example.com>
License: GPL-3.0+
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 .
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.
 .
 You should have received a copy of the GNU General Public License
 along with this program. If not, see <https://www.gnu.org/licenses/>.
COPYRIGHT

# ========== 创建 postinst 脚本（安装后自动安装pip依赖） ==========
echo "创建 postinst 脚本..."
cat > "${BUILD_DIR}/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
# 安装后自动安装 Python 依赖

APP_DIR="/usr/lib/meeting-minutes-tool"

echo "会议纪要助手：正在安装 Python 依赖..."

# 检查 pip3
if command -v pip3 &> /dev/null; then
    pip3 install --upgrade pip -q
    pip3 install -r "${APP_DIR}/requirements.txt" -q
    echo "会议纪要助手：Python 依赖安装完成"
elif command -v pip &> /dev/null; then
    pip install --upgrade pip -q
    pip install -r "${APP_DIR}/requirements.txt" -q
    echo "会议纪要助手：Python 依赖安装完成"
else
    echo "警告：未找到 pip/pip3，请手动安装依赖："
    echo "  pip install -r ${APP_DIR}/requirements.txt"
fi

# 更新桌面数据库
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database 2>/dev/null || true
fi

# 更新图标缓存
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true
fi

exit 0
POSTINST

chmod +x "${BUILD_DIR}/DEBIAN/postinst"

# ========== 创建 prerm 脚本 ==========
echo "创建 prerm 脚本..."
cat > "${BUILD_DIR}/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
# 卸载前脚本

echo "会议纪要助手：正在卸载..."

# 不再需要额外操作
exit 0
PRERM

chmod +x "${BUILD_DIR}/DEBIAN/prerm"

# ========== 生成应用图标（SVG格式） ==========
# 生成一个简单的 PNG 图标（需要 Python 和 Pillow）
echo "生成应用图标..."
python3 -c "
from PIL import Image, ImageDraw, ImageFont
import os

size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 绘制一个蓝色圆角矩形背景
draw.rounded_rectangle([(10, 10), (246, 246)], radius=40, fill='#4472C4')

# 绘制一个文档图标样式
# 白色文档形状
draw.rounded_rectangle([(68, 40), (188, 216)], radius=8, fill='white')

# 文档上的装饰线条
for y_offset in [80, 110, 140, 170]:
    draw.rectangle([(88, y_offset), (168, y_offset + 4)], fill='#4472C4', outline=None)

# 文档底部的粗线条（代表文字）
draw.rectangle([(88, 195), (168, 199)], fill='#4472C4', outline=None)

# 保存图标
icon_path = '${BUILD_DIR}/usr/share/icons/hicolor/256x256/apps/meeting-minutes-tool.png'
img.save(icon_path, 'PNG')
print(f'图标已生成: {icon_path}')
"

# ========== 构建 deb 包 ==========
echo "构建 deb 包..."
DEB_FILE="${PROJECT_DIR}/${PACKAGE_NAME}_${VERSION}_all.deb"

# 修正 Installed-Size（dpkg-gencontrol 会用，但我们是手动构建，需要重新计算）
INSTALLED_SIZE=$(du -sk "${BUILD_DIR}/usr" | cut -f1)
sed -i "s/Installed-Size:.*/Installed-Size: ${INSTALLED_SIZE}/" "${BUILD_DIR}/DEBIAN/control"

# 使用 dpkg-deb 构建
dpkg-deb --build "${BUILD_DIR}" "${DEB_FILE}"

echo "=========================================="
echo "构建完成！"
echo "包文件: ${DEB_FILE}"
echo ""
echo "安装命令："
echo "  sudo dpkg -i ${DEB_FILE}"
echo "  sudo apt-get install -f  # 安装依赖"
echo ""
echo "卸载命令："
echo "  sudo dpkg -r ${PACKAGE_NAME}"
echo "=========================================="