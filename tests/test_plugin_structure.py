"""双平台插件目录与清单测试。"""

import hashlib
import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "dogdoing"
CLAUDE_MARKETPLACE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
CODEX_MARKETPLACE = REPO_ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
CODEX_MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
PACKAGE_JSON = REPO_ROOT / "package.json"


# 功能：校验 Dogdoing 的双平台插件目录和元数据契约
class PluginStructureTests(unittest.TestCase):
    # 功能：读取 JSON 文件并在格式错误时给出明确测试位置
    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    # 功能：验证 Claude 与 Codex 的 Marketplace 指向同一插件目录
    def test_marketplaces_point_to_shared_plugin(self):
        for path in (CLAUDE_MARKETPLACE, CODEX_MARKETPLACE):
            with self.subTest(path=path):
                data = self.read_json(path)
                entry = data["plugins"][0]
                source = entry["source"]
                source_path = source["path"] if isinstance(source, dict) else source
                self.assertEqual("./plugins/dogdoing", source_path)

    # 功能：验证 Codex Marketplace 包含安装策略和分类信息
    def test_codex_marketplace_has_required_policy(self):
        data = self.read_json(CODEX_MARKETPLACE)
        entry = data["plugins"][0]
        self.assertEqual("dogdoing", data["name"])
        self.assertEqual("dogdoing", entry["name"])
        self.assertEqual("local", entry["source"]["source"])
        self.assertEqual("AVAILABLE", entry["policy"]["installation"])
        self.assertEqual("ON_INSTALL", entry["policy"]["authentication"])
        self.assertEqual("Developer Tools", entry["category"])

    # 功能：验证两种宿主清单和 npm 包使用同一个发布版本
    def test_manifests_share_one_version(self):
        claude_version = self.read_json(CLAUDE_MANIFEST)["version"]
        codex_version = self.read_json(CODEX_MANIFEST)["version"]
        package_version = self.read_json(PACKAGE_JSON)["version"]
        self.assertEqual("1.1.0", package_version)
        self.assertEqual(package_version, claude_version)
        self.assertEqual(package_version, codex_version.split("+", 1)[0])
        if "+" in codex_version:
            self.assertRegex(
                codex_version,
                re.compile(r"^1\.1\.0\+codex\.[a-z0-9]+(?:-[a-z0-9]+)*$"),
            )

    # 功能：验证 Codex 清单字段可被官方插件加载器接受
    def test_codex_manifest_is_installable(self):
        data = self.read_json(CODEX_MANIFEST)
        self.assertEqual("dogdoing", data["name"])
        self.assertNotIn("hooks", data)
        self.assertEqual("./skills/", data["skills"])
        self.assertTrue((PLUGIN_ROOT / data["skills"]).is_dir())
        interface = data["interface"]
        for key in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "defaultPrompt",
            "composerIcon",
            "logo",
        ):
            with self.subTest(key=key):
                self.assertIn(key, interface)
        self.assertTrue((PLUGIN_ROOT / interface["composerIcon"]).is_file())
        self.assertTrue((PLUGIN_ROOT / interface["logo"]).is_file())

    # 功能：验证插件商店与插件详情中的用户可见提示以中文呈现
    def test_plugin_interface_prompts_are_chinese(self):
        codex_manifest = self.read_json(CODEX_MANIFEST)
        claude_manifest = self.read_json(CLAUDE_MANIFEST)
        codex_marketplace = self.read_json(CODEX_MARKETPLACE)
        claude_marketplace = self.read_json(CLAUDE_MARKETPLACE)
        interface = codex_manifest["interface"]

        self.assertEqual("刀盾狗", interface["displayName"])
        self.assertEqual("刀盾狗", codex_marketplace["interface"]["displayName"])
        for prompt in interface["defaultPrompt"]:
            self.assertIn("刀盾狗", prompt)
        for description in (
            codex_manifest["description"],
            interface["shortDescription"],
            interface["longDescription"],
            claude_manifest["description"],
            claude_marketplace["metadata"]["description"],
            claude_marketplace["plugins"][0]["description"],
        ):
            with self.subTest(description=description):
                self.assertRegex(description, "[一-龥]")
                self.assertNotIn("shield-dog", description)

    # 功能：验证共享插件内包含全部现有功能组件
    def test_plugin_contains_all_feature_components(self):
        expected_paths = (
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            "agents/dogdoing.md",
            "assets/icons/dogdoing.png",
            "assets/sounds/complete.wav",
            "hooks/claude-failure.json",
            "hooks/hooks.json",
            "scripts/hook_router_windows.cmd",
            "scripts/hook_router_windows_error.txt",
            "scripts/notify.py",
            "scripts/tracker.py",
            "skills/dogdoing/SKILL.md",
            "skills/dogfood/SKILL.md",
            "INJECT.md",
            "INJECT_SUBAGENT.md",
            "INJECT_CHEER.md",
            "INJECT_DROG.md",
            "settings.json",
        )
        for relative_path in expected_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue((PLUGIN_ROOT / relative_path).exists())

    # 功能：验证任务完成音频与上游原始语音完全一致
    def test_complete_sound_matches_original_asset(self):
        content = (PLUGIN_ROOT / "assets" / "sounds" / "complete.wav").read_bytes()
        self.assertEqual(
            "B51A0023049E0A90620C2EF1E7821429E69C798ED85014ABF94C376D32B1DAD0",
            hashlib.sha256(content).hexdigest().upper(),
        )


if __name__ == "__main__":
    unittest.main()
