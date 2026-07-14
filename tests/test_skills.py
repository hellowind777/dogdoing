"""Dogdoing 与 dogfood 双平台 Skill 内容测试。"""

import re
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "dogdoing"
DOGDOING_SKILL = PLUGIN_ROOT / "skills" / "dogdoing" / "SKILL.md"
DOGFOOD_SKILL = PLUGIN_ROOT / "skills" / "dogfood" / "SKILL.md"
CODEX_INJECTION = PLUGIN_ROOT / "INJECT_SUBAGENT_CODEX.md"
CLAUDE_AGENT = PLUGIN_ROOT / "agents" / "dogdoing.md"
PROMPT_FILES = (
    PLUGIN_ROOT / "INJECT.md",
    PLUGIN_ROOT / "INJECT_SUBAGENT.md",
    CODEX_INJECTION,
    PLUGIN_ROOT / "INJECT_CHEER.md",
    PLUGIN_ROOT / "INJECT_DROG.md",
    CLAUDE_AGENT,
    DOGDOING_SKILL,
)


# 功能：验证两个 Skill 和代理人格在 Claude 与 Codex 中行为等价
class SkillCompatibilityTests(unittest.TestCase):
    # 功能：读取指定 UTF-8 文本资源
    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    # 功能：验证共享 Skill 仅使用两端都能解析的核心元数据
    def test_skill_frontmatter_avoids_claude_only_fields(self):
        for path in (DOGDOING_SKILL, DOGFOOD_SKILL):
            with self.subTest(path=path):
                content = self.read_text(path)
                frontmatter = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
                self.assertIsNotNone(frontmatter)
                metadata = frontmatter.group(1)
                self.assertIn("name:", metadata)
                self.assertIn("description:", metadata)
                self.assertNotIn("allowed-tools:", metadata)
                self.assertNotIn("disable-model-invocation:", metadata)
                self.assertNotIn("argument_description:", metadata)

    # 功能：验证手动召唤技能包含两种宿主的真实代理调用方式
    def test_dogdoing_skill_supports_both_hosts(self):
        content = self.read_text(DOGDOING_SKILL)
        self.assertIn("collaboration.spawn_agent", content)
        self.assertIn("collaboration.wait_agent", content)
        self.assertIn("fork_turns=\"all\"", content)
        self.assertIn('Agent(subagent_type="dogdoing:dogdoing"', content)
        self.assertIn("$ARGUMENTS", content)
        self.assertIn("所有输出使用简体中文", content)
        self.assertNotIn("英文：", content)

    # 功能：验证没有多代理工具时 Skill 仍要求完成同等深度分析
    def test_dogdoing_skill_has_local_fallback(self):
        content = self.read_text(DOGDOING_SKILL)
        self.assertIn("多代理工具不可用", content)
        self.assertIn("主代理", content)

    # 功能：验证自检 Skill 覆盖两种清单和两套 Hook 配置
    def test_dogfood_skill_reviews_both_platforms(self):
        content = self.read_text(DOGFOOD_SKILL)
        for required in (
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
            "hooks.json",
            "hooks/hooks.json",
            ".agents/plugins/marketplace.json",
            ".claude-plugin/marketplace.json",
        ):
            with self.subTest(required=required):
                self.assertIn(required, content)

    # 功能：验证自检 Skill 与全中文输出契约保持一致
    def test_dogfood_skill_keeps_chinese_contract(self):
        content = self.read_text(DOGFOOD_SKILL)
        self.assertIn("所有上下文使用简体中文输出", content)
        self.assertNotIn("中英双语", content)
        self.assertNotIn("其他上下文用英文", content)

    # 功能：验证 Codex 自动分工要求等待并汇总刀盾狗结果
    def test_codex_injection_collects_agent_result(self):
        content = self.read_text(CODEX_INJECTION)
        self.assertIn("collaboration.spawn_agent", content)
        self.assertIn("等待刀盾狗完成", content)
        self.assertIn("具体且边界清晰的子任务", content)

    # 功能：验证 Claude 注册代理保持全中文提示和有用工作要求
    def test_claude_agent_keeps_persona_contract(self):
        content = self.read_text(CLAUDE_AGENT)
        self.assertIn("简体中文", content)
        self.assertIn("所有输出使用简体中文", content)
        self.assertIn("完成分配的实际工作", content)
        self.assertIn("旺", content)
        self.assertNotIn("Wow", content)

    # 功能：验证注入和代理人格不再包含面向人的英文提示句
    def test_prompt_prose_is_chinese(self):
        forbidden_phrases = (
            "You have a loyal",
            "When the user types",
            "MUST participate",
            "For every user request",
            "Collect the result",
            "If Dogdoing cannot",
            "What Dogdoing can do",
            "You are Dogdoing",
        )
        for path in PROMPT_FILES:
            with self.subTest(path=path):
                content = self.read_text(path)
                self.assertIn("刀盾狗", content)
                for phrase in forbidden_phrases:
                    self.assertNotIn(phrase, content)


if __name__ == "__main__":
    unittest.main()
