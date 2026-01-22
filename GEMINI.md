# Guia de Boas Práticas - Google Gemini

Este documento descreve as práticas recomendadas e a implementação do Google Gemini neste projeto. O `AIService` (`backend/services/ai.py`) é o componente central responsável por interagir com a API do Gemini.

## 1. Configuração e Modelos

### Modelo Utilizado
Atualmente, o projeto utiliza o modelo **`gemini-pro`** através da biblioteca `google-generativeai`.

*   **Por que `gemini-pro`?** Oferece um equilíbrio ideal entre custo, velocidade e capacidade de raciocínio para tarefas de conversação e extração de dados.
*   **Instanciação:** O modelo é instanciado apenas se a `GOOGLE_API_KEY` estiver presente, evitando falhas na inicialização do serviço.

### Gerenciamento de Chaves
A chave da API (`GOOGLE_API_KEY`) é carregada via variáveis de ambiente (`backend/config.py`). Nunca commite chaves hardcoded.

## 2. Engenharia de Prompt (Prompt Engineering)

Os prompts são definidos como constantes em `backend/services/ai.py` e são escritos inteiramente em **Português do Brasil** para garantir alinhamento cultural e linguístico.

### Estrutura dos Prompts
Utilizamos uma abordagem de **Prompt System Dinâmico**, onde o contexto é injetado em tempo de execução.

#### Exemplo: `CONVERSATION_SYSTEM_PROMPT`
O prompt de conversação é estruturado em três partes principais:
1.  **Persona e Diretrizes:** Define quem é o bot (amigo, útil, natural) e regras (não ser robótico).
2.  **Fatos Conhecidos:** Injeta memória de longo prazo (fatos extraídos do banco de dados).
3.  **Histórico Recente:** Injeta as últimas 20 mensagens para manter o fluxo da conversa.

**Dica:** Ao modificar prompts, sempre inclua exemplos claros de saída desejada (Few-Shot Prompting), como feito em `FACT_EXTRACTION_PROMPT`.

## 3. Gerenciamento de Contexto e Memória

O Gemini possui uma janela de contexto grande, mas para otimizar latência e custos, filtramos o que é enviado:

*   **Histórico de Chat:** Limitado às últimas **20 mensagens**. Isso é suficiente para entender o tópico atual sem sobrecarregar o modelo.
*   **Fatos:** Limitado aos **30 fatos mais recentes** extraídos.
*   **Formatação:** As mensagens são formatadas com timestamp e nome do remetente: `[DD/MM HH:MM] Nome: Mensagem`. Isso ajuda o modelo a entender a cronologia e quem está falando.

## 4. Extração de Dados Estruturados (JSON)

Para extrair fatos (`extract_facts`), instruímos o modelo a retornar um **JSON array**.

### Tratamento de Saída
O modelo pode retornar o JSON envolvido em blocos de código Markdown (ex: \`\`\`json ... \`\`\`).
**Prática Implementada:**
*   Sempre remova tags Markdown (`replace("```json", "")`).
*   Faça o parsing do JSON dentro de um bloco `try/except`.
*   Localize os colchetes `[` e `]` para isolar o JSON válido caso o modelo adicione texto explicativo antes ou depois.

## 5. Assincronismo e Performance

Todas as chamadas à API do Gemini (`generate_content_async`) e ao banco de dados são assíncronas.

*   **Não Bloquear o Event Loop:** Operações de banco de dados (`_get_context`) são executadas em threads separadas usando `asyncio.to_thread`.
*   **Batch Processing:** O serviço de aprendizado (`LearningService`) deve processar mensagens em lotes para evitar atingir os limites de taxa (Rate Limits) da API do Gemini.

## 6. Tratamento de Erros

A API do Gemini pode falhar por diversos motivos (rede, filtros de segurança, sobrecarga).

*   **Falha Graciosa:** O `AIService` captura exceções genéricas e retorna mensagens de fallback ("Desculpe, não consegui processar isso agora") ou listas vazias, garantindo que o bot nunca trave por causa da IA.
*   **Logs:** Erros são logados com `logger.error` para monitoramento.

## 7. Privacidade e Segurança

*   **Filtros:** O Gemini possui filtros de segurança nativos. Se uma resposta for bloqueada, o método `generate_content_async` pode lançar uma exceção ou retornar um objeto vazio. O código deve estar preparado para lidar com `response.text` vazio.
*   **Dados Sensíveis:** Evite enviar senhas ou chaves privadas no histórico da conversa para a API.
