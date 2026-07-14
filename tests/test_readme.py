"""README 与发布说明完整性测试。"""

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
PACKAGE_JSON = REPO_ROOT / "package.json"
NPM_IGNORE = REPO_ROOT / ".npmignore"
SCRIPT_NPM_IGNORE = REPO_ROOT / "plugins" / "dogdoing" / "scripts" / ".npmignore"


# 功能：验证用户文档覆盖 V1 双平台安装和全部功能入口
class ReadmeTests(unittest.TestCase):
    # 功能：读取 README 的 UTF-8 内容
    def readme(self) -> str:
        return README.read_text(encoding="utf-8")

    # 功能：验证 Codex 的远程和本地 Marketplace 安装命令完整
    def test_codex_installation_commands_are_documented(self):
        content = self.readme()
        self.assertIn("codex plugin marketplace add hellowind777/dogdoing", content)
        self.assertIn("codex plugin marketplace add .", content)
        self.assertIn("codex plugin add dogdoing@dogdoing", content)

    # 功能：验证 Codex Desktop 升级插件后会提示完全重启应用而不是只新建任务
    def test_codex_desktop_restart_is_documented(self):
        content = self.readme()
        self.assertIn("完全退出并重新启动 Codex Desktop", content)
        self.assertIn("仅新建任务不会刷新", content)

    # 功能：验证 Claude Code 的既有安装命令继续保留
    def test_claude_installation_commands_are_documented(self):
        content = self.readme()
        self.assertIn("claude plugin marketplace add hellowind777/dogdoing", content)
        self.assertIn("claude plugin install dogdoing", content)
        self.assertIn("claude --plugin-dir", content)

    # 功能：验证两个宿主的手动 Skill 语法都有明确说明
    def test_manual_skill_syntax_is_documented(self):
        content = self.readme()
        for trigger in ("$dogdoing", "$dogfood", "/dogdoing", "/dogfood", "~dogdoing", "~drog"):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, content)

    # 功能：验证 V1 的全部用户可见功能仍在文档清单中
    def test_all_v1_features_are_documented(self):
        content = self.readme()
        for feature in (
            "自动分工",
            "多代理",
            "喝彩",
            "桌面通知",
            "语音",
            "成就",
            "连击",
            "This is Fine",
            "Drog",
            "自检",
            "全中文提示",
            "Windows",
            "macOS",
            "Linux",
        ):
            with self.subTest(feature=feature):
                self.assertIn(feature, content)

    # 功能：验证 npm 发布包包含双平台 Marketplace 和共享插件目录
    def test_package_includes_dual_platform_layout(self):
        package = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
        self.assertEqual("1.1.0", package["version"])
        self.assertIn(".agents/", package["files"])
        self.assertIn(".claude-plugin/", package["files"])
        self.assertIn("plugins/", package["files"])
        self.assertIn("codex", package["keywords"])

    # 功能：验证 npm 发布包不会携带 Python 字节码和测试缓存
    def test_package_excludes_python_cache(self):
        root_patterns = NPM_IGNORE.read_text(encoding="utf-8")
        script_patterns = SCRIPT_NPM_IGNORE.read_text(encoding="utf-8")
        self.assertIn("**/__pycache__/**", root_patterns)
        self.assertIn("__pycache__/", script_patterns)
        self.assertIn("*.pyc", script_patterns)


if __name__ == "__main__":
    unittest.main()
