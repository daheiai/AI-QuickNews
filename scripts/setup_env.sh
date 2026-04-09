#!/bin/bash
# 环境配置脚本

echo "正在配置环境..."

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# 安装依赖
echo "安装 Python 依赖..."
pip3 install -r requirements.txt

# 创建 .env 文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件填入你的配置"
else
    echo ".env 文件已存在"
fi

# 创建数据目录
echo "创建数据目录..."
mkdir -p data/tweets data/reports data/logs

echo "环境配置完成！"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件填入你的 API 密钥"
echo "2. 运行测试: python main.py --mode quick"
