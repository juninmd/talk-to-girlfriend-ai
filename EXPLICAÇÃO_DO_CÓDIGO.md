# Explicação do Código

Este documento fornece uma visão detalhada da estrutura e funcionamento do código do projeto **Telegram AI Dating Agent**.

## Visão Geral da Arquitetura

O projeto é dividido em duas partes principais:
1.  **Backend (Python)**: Lida com a conexão direta com a API do Telegram usando a biblioteca `Telethon`. Ele expõe funcionalidades do Telegram de duas maneiras: como um servidor MCP (`main.py`) e como uma API REST (`telegram_api.py`).
2.  **Frontend/Agente (TypeScript)**: Uma aplicação de linha de comando (`agent/`) que interage com o usuário, processa comandos em linguagem natural usando IA (Google Gemini) e executa ações no Telegram através da API REST do backend.

---

## 1. Backend (Python)

### `telegram_api.py`
Este é o arquivo que você deve executar para que o agente (CLI) funcione. Ele cria uma ponte entre o agente e o Telegram.

*   **FastAPI**: Utiliza o framework FastAPI para criar um servidor web.
*   **Telethon**: Biblioteca Python usada para interagir com a API do Telegram (MTProto).
*   **Endpoints**: Define rotas HTTP (como `/chats`, `/messages`, `/send_message`) que o agente chama.
    *   Exemplo: Quando o agente quer enviar uma mensagem, ele faz uma requisição POST para `/chats/{chat_id}/messages`. O `telegram_api.py` recebe essa requisição e usa `client.send_message()` do Telethon para realmente enviar a mensagem no Telegram.
*   **Gerenciamento de Sessão**: Usa `TELEGRAM_SESSION_STRING` do arquivo `.env` para autenticar sem precisar escanear QR code a cada vez.

### `main.py` (Atualizado 2026)
Este arquivo implementa um servidor **MCP (Model Context Protocol)** robusto e tipado.

*   **MCP Server**: Permite que clientes MCP (como editores de código ou desktops de IA) se conectem diretamente ao seu Telegram.
*   **Ferramentas (Tools)**: Define funções decoradas com `@mcp.tool` (ex: `get_chats`, `send_message`). Essas funções são expostas para o modelo de IA, que pode decidir chamá-las com base no pedido do usuário.
*   **Logging e Validação**: Inclui tratamento robusto de erros e logs em `mcp_errors.log`.

### `session_string_generator.py`
Script utilitário para gerar a `TELEGRAM_SESSION_STRING`. Você roda isso uma vez para fazer login no Telegram e obter a string que será salva no `.env`.

---

## 2. Frontend/Agente (TypeScript - pasta `agent/`)

Esta é a "mente" do projeto, onde a IA reside.

### `agent/src/index.ts`
O ponto de entrada da aplicação CLI.
*   **Interface**: Usa bibliotecas como `@clack/prompts` para criar uma interface de linha de comando bonita e interativa.
*   **Loop Principal**: Fica em um loop esperando entrada do usuário. Quando você digita algo, ele envia para a função `chat` em `agent.ts`.
*   **Verificação de Saúde**: Verifica se o backend (`telegram_api.py`) está rodando antes de iniciar.

### `agent/src/agent.ts`
O núcleo da lógica de IA.
*   **Vercel AI SDK**: Usa `streamText` da biblioteca `ai` para se comunicar com o modelo de linguagem (Google Gemini).
*   **System Prompt**: Define a personalidade do agente ("wingman charmoso"), regras de comportamento e como usar as ferramentas.
*   **Ferramentas**: Combina ferramentas de diferentes fontes:
    *   `telegramTools`: Para interagir com o Telegram (definidas em `tools/telegram.ts`).
    *   `niaTools`: Para buscar conhecimento e cantadas (definidas em `tools/nia.ts`).
    *   `aiifyTools`: Para melhorar mensagens (definidas em `tools/aiify.ts`).
*   **Fluxo**:
    1.  Recebe mensagem do usuário.
    2.  Envia histórico para o Agente.
    3.  A IA decide se precisa chamar uma ferramenta (ex: ler mensagens, buscar cantada).
    4.  Se chamar ferramenta, o código executa a função correspondente (que chama a API do Python) e devolve o resultado para a IA.
    5.  A IA gera a resposta final para o usuário.

### `agent/src/tools/telegram.ts`
Define as ferramentas que o modelo de IA pode usar para controlar o Telegram.
*   Cada ferramenta (ex: `getChats`, `sendMessage`) faz uma requisição `fetch` para o servidor rodando em `localhost:8765` (o `telegram_api.py`).

### `agent/src/tools/nia.ts`
Integração com a plataforma **Nia** (trynia.ai) para busca semântica.
*   Permite que o agente pesquise em uma base de conhecimento de cantadas e conselhos de namoro.

---

## Fluxo de Dados Exemplo

1.  **Usuário** digita no CLI: "Leia as últimas mensagens da Maria".
2.  **`agent/src/index.ts`** envia o texto para `agent.ts`.
3.  **Agente** (em `agent.ts`) analisa o texto e decide chamar a ferramenta `getChats` ou `getMessages`.
4.  **`agent/src/tools/telegram.ts`** faz uma requisição HTTP GET para `http://localhost:8765/chats/...`.
5.  **`telegram_api.py`** recebe a requisição, usa o `Telethon` para buscar dados nos servidores do Telegram e retorna o JSON.
6.  **Agente** recebe o JSON, interpreta as mensagens e gera uma resposta em texto: "A última mensagem da Maria foi 'Oi, tudo bem?'".
7.  **`agent/src/index.ts`** exibe a resposta no terminal.
