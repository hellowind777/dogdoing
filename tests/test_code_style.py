"""Python 代码注释和语法约束测试。"""

import ast
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCRIPTS = REPO_ROOT / "plugins" / "dogdoing" / "scripts"
TESTS_DIR = REPO_ROOT / "tests"
CHINESE_COMMENT = re.compile(r"^# 功能：.*[\u4e00-\u9fff]")


# 功能：验证全部 Python 定义遵守项目中文功能注释约定
class PythonStyleTests(unittest.TestCase):
    # 功能：枚举插件与测试目录中的所有 Python 源文件
    def python_files(self):
        return sorted(PLUGIN_SCRIPTS.glob("*.py")) + sorted(TESTS_DIR.glob("*.py"))

    # 功能：验证每个 Python 文件都能被 AST 正确解析
    def test_python_files_are_valid_syntax(self):
        for path in self.python_files():
            with self.subTest(path=path):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    # 功能：验证每个函数和类定义前都有描述用途的中文注释
    def test_python_definitions_have_chinese_function_comments(self):
        missing = []
        for path in self.python_files():
            lines = path.read_text(encoding="utf-8").splitlines()
            tree = ast.parse("\n".join(lines), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue
                previous = lines[node.lineno - 2].strip() if node.lineno > 1 else ""
                if not CHINESE_COMMENT.match(previous):
                    relative = path.relative_to(REPO_ROOT)
                    missing.append(f"{relative}:{node.lineno} {node.name}")
        self.assertEqual([], missing, "缺少中文功能注释：\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
