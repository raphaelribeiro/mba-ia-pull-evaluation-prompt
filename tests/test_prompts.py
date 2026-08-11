"""
Testes automatizados para validação de prompts.
"""
import pytest
import yaml
import re
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"

# Formas usuais de definir persona: "Você é um...", "Você é uma...", "Atue como..."
PERSONA_REGEX = re.compile(r"(Você é um[a]?|Atue como)\s+\w+", re.IGNORECASE)

# Partes do template padrão de user story
USER_STORY_PARTS = ("Como um", "eu quero", "para que")


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    """Dados do prompt otimizado (v2)."""
    dados = load_prompts(str(PROMPT_PATH))
    assert dados, f"YAML vazio ou ilegível: {PROMPT_PATH}"
    assert PROMPT_KEY in dados, (
        f"Chave '{PROMPT_KEY}' não encontrada em {PROMPT_PATH.name}. "
        f"Chaves presentes: {list(dados)}"
    )
    return dados[PROMPT_KEY]


@pytest.fixture(scope="module")
def prompt_text(prompt_data):
    """system_prompt e user_prompt concatenados."""
    return f"{prompt_data.get('system_prompt', '')}\n{prompt_data.get('user_prompt', '')}"


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' ausente no YAML"

        system_prompt = prompt_data["system_prompt"]
        assert isinstance(system_prompt, str), (
            f"'system_prompt' deve ser texto, veio {type(system_prompt).__name__}"
        )
        assert system_prompt.strip(), "'system_prompt' está vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt_data.get("system_prompt", "")
        persona = PERSONA_REGEX.search(system_prompt)

        assert persona, (
            "Nenhuma persona definida no 'system_prompt'. "
            "Esperado algo como 'Você é um Product Manager' ou 'Atue como ...'"
        )

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt_data.get("system_prompt", "")

        tem_user_story = all(parte in system_prompt for parte in USER_STORY_PARTS)
        tem_markdown = "##" in system_prompt or "**" in system_prompt

        assert tem_user_story or tem_markdown, (
            "O prompt não exige formato de saída. Esperado o template de user story "
            f"({', '.join(USER_STORY_PARTS)}) ou marcação Markdown ('##', '**')"
        )

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt_data.get("system_prompt", "")

        entradas = system_prompt.count("Relato de Bug:")
        saidas = system_prompt.count("User Story gerada:")

        assert entradas >= 2, (
            f"Few-shot exige ao menos 2 exemplos de entrada, encontrados: {entradas}"
        )
        assert saidas >= 2, (
            f"Few-shot exige ao menos 2 exemplos de saída, encontrados: {saidas}"
        )

    def test_prompt_no_todos(self, prompt_text):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        assert "TODO" not in prompt_text.upper(), (
            "O prompt ainda contém TODO — preencha antes de publicar"
        )

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        assert "techniques_applied" in prompt_data, (
            "Campo 'techniques_applied' ausente nos metadados do YAML"
        )

        tecnicas = prompt_data["techniques_applied"]
        assert isinstance(tecnicas, list), (
            f"'techniques_applied' deve ser uma lista, veio {type(tecnicas).__name__}"
        )
        assert len(tecnicas) >= 2, (
            f"Mínimo de 2 técnicas requeridas, encontradas: {len(tecnicas)} ({tecnicas})"
        )

    def test_prompt_structure_is_valid(self, prompt_data):
        """Valida o prompt pelo mesmo gate que o push_prompts.py usa."""
        valido, erros = validate_prompt_structure(prompt_data)

        assert valido, "Prompt reprovado na validação de estrutura:\n- " + "\n- ".join(erros)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
