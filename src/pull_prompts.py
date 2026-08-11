"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts.chat import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langsmith import Client

from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_NAME = os.getenv("SOURCE_PROMPT_NAME", "leonanluppi/bug_to_user_story_v1")
PROMPT_KEY = PROMPT_NAME.split("/")[-1]


def _represent_multiline_str(dumper, data):
    """
    Serializa strings multilinha como bloco literal (|), e não entre aspas.

    Mantém o YAML gerado no mesmo estilo do prompts/bug_to_user_story_v1.yml
    versionado, que é bem mais legível para revisar o texto do prompt.
    """
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _represent_multiline_str)


def extract_message_templates(prompt_template) -> dict:
    """
    Extrai os templates de system e user de um ChatPromptTemplate.

    Args:
        prompt_template: ChatPromptTemplate retornado pelo hub.pull

    Returns:
        Dicionário com as chaves system_prompt e user_prompt

    Raises:
        ValueError: Se o prompt não contiver mensagem de sistema
    """
    messages = getattr(prompt_template, "messages", [])
    templates = {"system_prompt": "", "user_prompt": ""}

    for message in messages:
        template = getattr(getattr(message, "prompt", None), "template", None)
        if template is None:
            continue

        if isinstance(message, SystemMessagePromptTemplate):
            templates["system_prompt"] = template
        elif isinstance(message, HumanMessagePromptTemplate):
            templates["user_prompt"] = template

    if not templates["system_prompt"]:
        encontradas = [type(m).__name__ for m in messages]
        raise ValueError(
            f"O prompt '{PROMPT_NAME}' não contém mensagem de sistema. "
            f"Mensagens encontradas: {encontradas}"
        )

    return templates


def fetch_prompt_metadata(prompt_name: str) -> dict:
    """
    Busca os metadados do prompt no LangSmith (descrição, tags, data de criação).

    O hub.pull devolve apenas o template; esses campos vêm da API de prompts.
    Falhas aqui não são fatais — o pull do template é o que importa.

    Args:
        prompt_name: Nome completo do prompt (owner/repo)

    Returns:
        Dicionário com description, tags e created_at
    """
    try:
        prompt = Client().get_prompt(prompt_name)
        created_at = getattr(prompt, "created_at", None)

        return {
            "description": getattr(prompt, "description", "") or "",
            "tags": list(getattr(prompt, "tags", []) or []),
            "created_at": created_at.date().isoformat() if created_at else "",
        }

    except Exception as e:
        print(f"   ⚠️  Não foi possível ler os metadados do prompt: {e}")
        return {"description": "", "tags": [], "created_at": ""}


def build_prompt_data(prompt_template, metadata: dict) -> dict:
    """
    Monta o dicionário no schema de prompts do projeto.

    Args:
        prompt_template: ChatPromptTemplate retornado pelo hub.pull
        metadata: Metadados vindos de fetch_prompt_metadata

    Returns:
        Dicionário pronto para ser serializado em YAML
    """
    templates = extract_message_templates(prompt_template)
    hub_metadata = getattr(prompt_template, "metadata", None) or {}

    return {
        PROMPT_KEY: {
            "description": metadata["description"],
            "system_prompt": templates["system_prompt"],
            "user_prompt": templates["user_prompt"],
            "version": "v1",
            "created_at": metadata["created_at"],
            "tags": metadata["tags"],
            "source": {
                "hub_owner": hub_metadata.get("lc_hub_owner", ""),
                "hub_repo": hub_metadata.get("lc_hub_repo", ""),
                "commit_hash": hub_metadata.get("lc_hub_commit_hash", ""),
                "pulled_at": date.today().isoformat(),
            },
        }
    }


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt inicial do LangSmith Hub e devolve os dados serializáveis.

    Returns:
        Dicionário no schema do projeto, ou None em caso de falha
    """
    print(f"Puxando prompt do LangSmith Hub: {PROMPT_NAME}")

    try:
        prompt_template = hub.pull(PROMPT_NAME)
        print(f"   ✓ Prompt carregado ({type(prompt_template).__name__})")

    except Exception as e:
        print(f"\n❌ Não foi possível carregar o prompt '{PROMPT_NAME}'")
        print(f"   {e}")
        return None

    metadata = fetch_prompt_metadata(PROMPT_NAME)
    prompt_data = build_prompt_data(prompt_template, metadata)

    variaveis = getattr(prompt_template, "input_variables", [])
    print(f"   ✓ Variáveis de entrada: {variaveis}")

    return prompt_data


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    prompt_data = pull_prompts_from_langsmith()

    if prompt_data is None:
        return 1

    output_path = Path(__file__).parent.parent / "prompts" / f"{PROMPT_KEY}.yml"

    if not save_yaml(prompt_data, str(output_path)):
        return 1

    print(f"\n✅ Prompt salvo em: {output_path}")

    commit_hash = prompt_data[PROMPT_KEY]["source"]["commit_hash"]
    if commit_hash:
        print(f"   Commit de origem: {commit_hash[:12]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
