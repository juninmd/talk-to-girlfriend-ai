# Telegram AI Agent (Português)

Um agente de Telegram inteligente e modular, projetado para auxiliar em conversas, gerenciar memória de longo prazo e fornecer insights diários.

O projeto combina um **Backend Python** robusto (FastAPI, Telethon, Google Gemini) com um **Agente CLI TypeScript** (opcional) para interações avançadas via terminal.

## Funcionalidades Principais

*   **Respostas Naturais com IA:** Utiliza **Google Gemini** para gerar respostas contextuais, engraçadas ou sérias, baseadas no histórico da conversa.
*   **Memória de Longo Prazo:** O `LearningService` analisa conversas passadas para extrair e armazenar fatos importantes (preferências, datas, nomes) automaticamente.
*   **Relatórios Diários:** O `ReportingService` gera resumos diários ("Newsletter") das suas conversas, destacando pontos importantes e tarefas.
*   **Integração Completa:** Funciona como um cliente de Telegram real (Userbot) capaz de ler e enviar mensagens, reagir e gerenciar chats.
*   **Servidor MCP (Model Context Protocol):** Expõe funcionalidades do Telegram para ferramentas compatíveis com MCP (como Claude Desktop ou Cursor).

## Atualizações 2026

*   **Backend Otimizado:** Refatorado para Python 3.12+ com suporte a tipagem estrita e linting rigoroso.
*   **IA Aprimorada:** Migração completa para modelos Gemini mais recentes (1.5 Flash) para melhor contexto e velocidade.
*   **Segurança:** Implementação de checks automáticos em CI/CD para garantir qualidade de código e segurança.

## Arquitetura

O núcleo do sistema é um backend Python modular:

*   **`backend/services/ai.py`**: Gerencia interações com o Google Gemini (Chat, Resumo, Extração de Fatos). Consulte [GEMINI.md](GEMINI.md) para detalhes.
*   **`backend/services/learning.py`**: Processa mensagens em background para "aprender" sobre os contatos.
*   **`backend/services/reporting.py`**: Gera estatísticas e resumos diários.
*   **`backend/services/telegram.py`**: Abstração da API do Telegram (Telethon).

## Pré-requisitos

*   Python 3.10+
*   Conta no Telegram (API ID e Hash)
*   Google Gemini API Key

## Configuração

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/seu-repo.git
    cd seu-repo
    ```

2.  **Variáveis de Ambiente:**
    Copie o exemplo e edite:
    ```bash
    cp .env.example .env
    ```
    Preencha:
    *   `TELEGRAM_API_ID` e `TELEGRAM_API_HASH`: Obtenha em [my.telegram.org](https://my.telegram.org).
    *   `GOOGLE_API_KEY`: Chave da API do Google Gemini AI Studio.
    *   `TELEGRAM_SESSION_STRING`: (Opcional) Gerada via script auxiliar.

3.  **Instalação (Python):**
    ```bash
    pip install -r requirements.txt
    ```

## Como Rodar

### Backend (Servidor Principal)

Para iniciar o servidor MCP e a API:

```bash
python main.py
```

### Agente TypeScript (CLI)

O agente CLI oferece uma interface de terminal interativa.

```bash
cd agent
bun install
bun run dev
```

## Documentação Adicional

*   **[GEMINI.md](GEMINI.md):** Boas práticas e detalhes da implementação do Google Gemini.
*   **[EXPLICAÇÃO_DO_CÓDIGO.md](EXPLICAÇÃO_DO_CÓDIGO.md):** Visão detalhada da estrutura do código (pode estar desatualizado em relação à arquitetura Gemini recente).

## Desenvolvimento e Testes

O projeto visa 100% de cobertura de testes.

```bash
# Rodar testes
python -m pytest
```

## Contribuição

Siga os princípios de Clean Code, DRY (Don't Repeat Yourself) e KISS (Keep It Simple, Stupid). O código deve ser mantido em inglês, mas a documentação e prompts em Português.
