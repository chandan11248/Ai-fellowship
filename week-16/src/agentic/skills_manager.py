"""
Skills Manager with Progressive Disclosure.
Context engineering technique: initially discloses only concise metadata for available skills,
loading full operational instructions into context strictly on-demand when the agent determines relevance.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional


class SkillMetadata:
    def __init__(self, name: str, description: str, triggers: List[str], full_path: Path):
        self.name = name
        self.description = description
        self.triggers = triggers
        self.full_path = full_path
        self._content: Optional[str] = None

    @property
    def full_instructions(self) -> str:
        if self._content is None:
            self._content = self.full_path.read_text(encoding="utf-8")
        return self._content


class SkillsManager:
    """Manages skill discovery, concise prompt catalogs, and on-demand disclosure."""

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or (Path(__file__).resolve().parent.parent.parent / "skills")
        self._skills: Dict[str, SkillMetadata] = {}
        self._discovered = False
        self.discover_skills()

    def discover_skills(self):
        """Scans the skills directory for SKILL.md files and parses YAML metadata."""
        if not self.skills_dir.exists():
            return

        for skill_folder in self.skills_dir.iterdir():
            if skill_folder.is_dir():
                skill_file = skill_folder / "SKILL.md"
                if skill_file.exists():
                    self._parse_skill_file(skill_file)
        self._discovered = True

    def _parse_skill_file(self, skill_file: Path):
        content = skill_file.read_text(encoding="utf-8")
        # Extract YAML frontmatter
        name = skill_file.parent.name
        description = "Specialized domain procedure."
        triggers: List[str] = []

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                for line in frontmatter.strip().splitlines():
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip()
                    elif line.strip().startswith("- "):
                        triggers.append(line.strip()[2:].strip())

        self._skills[name] = SkillMetadata(
            name=name,
            description=description,
            triggers=triggers,
            full_path=skill_file
        )

    def get_concise_manifest(self) -> str:
        """
        Produces a lightweight skill directory for initial context injection.
        Loads names and 1-line descriptions without burning tokens on full instructions.
        """
        if not self._skills:
            return "No specialized procedural skills currently registered."

        manifest_lines = [
            "### [AVAILABLE PROCEDURAL SKILLS (Call 'load_skill' to inspect full SOP)]"
        ]
        for name, meta in self._skills.items():
            manifest_lines.append(f"- **{name}**: {meta.description}")
        return "\n".join(manifest_lines)

    def load_skill(self, skill_name: str) -> Dict[str, Any]:
        """Dynamically retrieves full instructions for a requested skill."""
        clean_name = skill_name.strip().lower()
        if clean_name not in self._skills:
            return {
                "success": False,
                "error": f"Skill '{clean_name}' not found. Available skills: {list(self._skills.keys())}"
            }

        meta = self._skills[clean_name]
        return {
            "success": True,
            "skill_name": meta.name,
            "instructions": meta.full_instructions,
            "message": f"Successfully loaded full procedural guidelines for skill '{meta.name}'."
        }

    def list_available_skill_names(self) -> List[str]:
        return list(self._skills.keys())


# Global default instance
skills_manager = SkillsManager()
