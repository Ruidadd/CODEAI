#!/usr/bin/env python3
"""
简单的项目结构验证脚本
"""
import os
import sys
from pathlib import Path

def test_structure():
    """验证项目结构"""
    print("=" * 50)
    print("项目结构验证")
    print("=" * 50)

    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        'config/config.yaml',
        '.env.example',
        '.gitignore',
    ]

    required_dirs = [
        'src',
        'src/collectors',
        'src/analyzers',
        'src/storage',
        'src/visualizers',
        'src/utils',
        'data',
        'data/charts',
        'config',
    ]

    print("\n检查必需文件:")
    for file in required_files:
        exists = os.path.exists(file)
        status = "✓" if exists else "✗"
        print(f"  {status} {file}")

    print("\n检查必需目录:")
    for dir in required_dirs:
        exists = os.path.isdir(dir)
        status = "✓" if exists else "✗"
        print(f"  {status} {dir}")

    print("\n检查源代码模块:")
    modules = [
        'src/__init__.py',
        'src/collectors/__init__.py',
        'src/collectors/news_collector.py',
        'src/analyzers/__init__.py',
        'src/analyzers/sentiment_analyzer.py',
        'src/storage/__init__.py',
        'src/storage/data_storage.py',
        'src/visualizers/__init__.py',
        'src/visualizers/sentiment_visualizer.py',
        'src/utils/__init__.py',
        'src/utils/config_loader.py',
        'src/utils/logger.py',
    ]

    for module in modules:
        exists = os.path.exists(module)
        status = "✓" if exists else "✗"
        print(f"  {status} {module}")

    print("\n" + "=" * 50)
    print("验证完成")
    print("=" * 50)

def test_config():
    """验证配置文件"""
    print("\n配置文件验证:")
    try:
        import yaml
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        print("  ✓ 配置文件格式正确")
        print(f"  ✓ 跟踪股票: {', '.join(config['data_collection']['stock_symbols'])}")
        print(f"  ✓ 新闻源数量: {len(config['data_collection']['news_sources'])}")
        print(f"  ✓ 情感分析器: {config['sentiment_analysis']['analyzer']}")
        print(f"  ✓ 存储类型: {config['storage']['type']}")
        return True
    except Exception as e:
        print(f"  ✗ 配置文件错误: {e}")
        return False

if __name__ == '__main__':
    test_structure()
    test_config()
    print("\n项目已成功创建!")
    print("\n下一步:")
    print("  1. 安装依赖: pip install -r requirements.txt")
    print("  2. 运行数据收集: python main.py collect")
    print("  3. 查看统计: python main.py stats")
    print("  4. 生成可视化: python main.py visualize")
