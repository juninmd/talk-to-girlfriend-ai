# Telegram AI Dating Agent (Português)

Um agente de Telegram alimentado por IA que ajuda você a criar mensagens espirituosas e envolventes para suas conversas. Construído com Claude Sonnet, busca semântica [Nia](https://trynia.ai) e uma integração completa do Telegram MCP.

## O Que Ele Faz

- **Sugestões de Respostas Inteligentes**: Obtenha sugestões de resposta alimentadas por IA com base no contexto da conversa.
- **500+ Cantadas (Pickup Lines)**: Busca semântica através de uma coleção curada de cantadas indexadas com Nia.
- **Guias de Namoro**: Pesquise em guias sobre como conversar com mulheres, iniciadores de conversa e dicas de paquera.
- **Melhoria de Mensagens**: Transforme mensagens chatas em espirituosas e envolventes.
- **Acesso Completo ao Telegram**: Leia mensagens, envie respostas, gerencie chats - tudo através de linguagem natural.

## Alimentado por Nia

Este agente usa [Nia](https://trynia.ai) como seu mecanismo de recuperação de conhecimento. Nia indexa e pesquisa em:
- 500+ cantadas curadas (engraçadas, bregas, inteligentes, românticas)
- Guias sobre técnicas de conversação
- Dicas para manter conversas envolventes

Você pode indexar seu próprio conteúdo criando uma fonte em [trynia.ai](https://trynia.ai).

## Arquitetura

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   CLI Agent      │────▶│  Telegram API    │────▶│    Telegram      │
│  (TypeScript)    │     │   Bridge (Py)    │     │    Servers       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         │
         ▼
┌──────────────────┐     ┌──────────────────┐
│  Claude Sonnet   │     │    Nia API       │
│   (AI Gateway)   │     │ (trynia.ai)      │
└──────────────────┘     └──────────────────┘
                         - 500+ cantadas
                         - Guias de namoro
                         - Dicas de conversa
```

## Guia de Início Rápido

### 1. Obter Credenciais da API do Telegram

Obtenha suas credenciais de API em [my.telegram.org/apps](https://my.telegram.org/apps).

### 2. Instalar e Configurar

```bash
# Clonar o repositório
git clone https://github.com/arlanrakh/talk-to-girlfriend-ai.git
cd talk-to-girlfriend-ai

# Instalar dependências Python
uv sync

# Gerar string de sessão do Telegram
uv run session_string_generator.py

# Configurar ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

### 3. Iniciar a Ponte da API do Telegram

```bash
python telegram_api.py
```

Isso executa um servidor FastAPI na porta 8765 que conecta o agente TypeScript ao Telegram.

### 4. Executar o Agente de IA

```bash
cd agent
bun install
bun run dev
```

## Exemplos de Uso

Uma vez em execução, interaja com linguagem natural (você pode falar em português):

```
# Lendo e Enviando
> Mostre-me mensagens de @nome_dela
> Envie "Ei, estava pensando em você" para @nome_dela
> Responda à última mensagem dela com algo espirituoso

# Reações
> Reaja à última mensagem dela com ❤️
> Envie uma reação de 🔥 para a mensagem 123

# Pesquisa e Histórico
> Pesquise em nosso chat por "jantar"
> Mostre-me as últimas 50 mensagens com ela
> Encontre uma cantada engraçada sobre pizza

# Assistência de IA
> O que devo responder à mensagem dela sobre café?
> Torne esta mensagem mais sedutora: "quer sair amanhã?"
> Pesquise dicas sobre como manter uma conversa fluindo

# Informações do Usuário
> Ela está online agora?
> Verifique o status dela

# Gerenciamento de Mensagens
> Edite minha última mensagem para corrigir o erro de digitação
> Apague a mensagem 456
> Encaminhe aquele meme para @amigo
```

### Comandos do Agente

- `/help` - Mostrar ajuda
- `/clear` - Limpar histórico de conversa
- `/status` - Verificar status da conexão
- `/quit` - Sair

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Telegram API (Obrigatório)
TELEGRAM_API_ID=seu_api_id
TELEGRAM_API_HASH=seu_api_hash
TELEGRAM_SESSION_STRING=sua_session_string

# Serviços de IA (Obrigatório para o agente)
AI_GATEWAY_API_KEY=sua_chave_vercel_ai_gateway
NIA_API_KEY=sua_chave_nia_api
NIA_CODEBASE_SOURCE=uuid_da_sua_fonte_de_cantadas
```

## Alternativa: Usar como Servidor MCP

Você também pode usar isso como um servidor MCP autônomo com Claude Desktop ou Cursor, sem o agente de IA.

Adicione à sua configuração MCP (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "telegram": {
      "command": "uv",
      "args": ["--directory", "/caminho/para/telegram-mcp", "run", "main.py"]
    }
  }
}
```

Isso expõe mais de 60 ferramentas do Telegram, incluindo mensagens, contatos, grupos, canais, reações e muito mais.

## Docker

```bash
docker build -t telegram-mcp:latest .
docker compose up --build
```

## Solução de Problemas

- **Erros de bloqueio de banco de dados**: Use autenticação por string de sessão em vez de baseada em arquivo.
- **Erros de autenticação**: Gere novamente a string de sessão com `uv run session_string_generator.py`.
- **Problemas de conexão**: Verifique se `telegram_api.py` está rodando na porta 8765.
- **Logs de erro**: Verifique `mcp_errors.log` para erros detalhados.

## Segurança

- Nunca faça commit do seu `.env` ou string de sessão.
- String de sessão = acesso total à conta do Telegram.
- Todo o processamento é local, os dados vão apenas para a API do Telegram.

## Para explicações detalhadas do código, consulte [EXPLICAÇÃO_DO_CÓDIGO.md](EXPLICAÇÃO_DO_CÓDIGO.md).
