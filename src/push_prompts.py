"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate

from utils import (
    check_env_vars,
    load_yaml,
    print_section_header,
    validate_prompt_structure,
)

load_dotenv()

PROMPT_KEY = "bug_to_user_story_v2"


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    return validate_prompt_structure(prompt_data)


def build_chat_prompt(prompt_data: dict) -> ChatPromptTemplate:
    """
    Monta o ChatPromptTemplate a partir dos campos do YAML.

    Mensagens vazias são descartadas: publicar uma mensagem sem conteúdo
    faria o modelo receber um turno em branco durante a avaliação.

    Args:
        prompt_data: Dados do prompt

    Returns:
        ChatPromptTemplate pronto para publicação

    Raises:
        ValueError: Se não houver nenhuma mensagem com conteúdo
    """
    campos = [("system", "system_prompt"), ("human", "user_prompt")]
    mensagens = [
        (papel, prompt_data[campo])
        for papel, campo in campos
        if prompt_data.get(campo, "").strip()
    ]

    if not mensagens:
        raise ValueError("O prompt não contém system_prompt nem user_prompt.")

    return ChatPromptTemplate.from_messages(mensagens)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"\nPublicando prompt: {prompt_name}")

    try:
        template = build_chat_prompt(prompt_data)
        tecnicas = list(prompt_data.get("techniques_applied", []))

        tags = list(prompt_data.get("tags", []))
        for tecnica in tecnicas:
            if tecnica not in tags:
                tags.append(tecnica)

        url = hub.push(
            prompt_name,
            template,
            new_repo_is_public=True,
            new_repo_description=prompt_data.get("description", ""),
            readme=f"Técnicas aplicadas: {', '.join(tecnicas)}",
            tags=tags,
        )

        papeis = [type(m).__name__ for m in template.messages]
        print(f"   ✓ Mensagens: {papeis}")
        print(f"   ✓ Variáveis: {template.input_variables}")
        print(f"   ✓ Técnicas: {', '.join(tecnicas)}")
        print(f"\n✅ Publicado como público: {url}")

        return True

    except Exception as e:
        # O LangSmith recusa commit sem alteração. O prompt já está publicado
        # e atualizado, então é sucesso — não falha.
        if "nothing to commit" in str(e).lower():
            print("   ✓ Prompt já está atualizado no Hub, nada a publicar")
            return True

        print(f"\n❌ Não foi possível publicar o prompt '{prompt_name}'")
        print(f"   {e}")
        return False


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS PARA O LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    yaml_path = Path(__file__).parent.parent / "prompts" / f"{PROMPT_KEY}.yml"
    dados = load_yaml(str(yaml_path))

    if not dados:
        return 1

    prompt_data = dados.get(PROMPT_KEY)

    if not prompt_data:
        print(f"❌ Chave '{PROMPT_KEY}' não encontrada em {yaml_path}")
        return 1

    valido, erros = validate_prompt(prompt_data)

    if not valido:
        print("❌ Prompt inválido:")
        for erro in erros:
            print(f"   - {erro}")
        return 1

    print(f"   ✓ Validação OK: {yaml_path.name}")

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    prompt_name = f"{username}/{PROMPT_KEY}"

    if not push_prompt_to_langsmith(prompt_name, prompt_data):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
