/**
 * AI Agent for Telegram
 * Uses Gemini via Google AI SDK with tools
 */

import { streamText, stepCountIs } from "ai";
import { google } from "@ai-sdk/google";
import pc from "picocolors";
import { config } from "./config";
import { telegramTools } from "./tools/telegram";
import { niaTools } from "./tools/nia";
import { aiifyTools } from "./tools/aiify";

// Combine all tools
export const tools = {
  ...telegramTools,
  ...niaTools,
  ...aiifyTools,
};

// System prompt that defines the agent's behavior
export const SYSTEM_PROMPT = `Você é um assistente de IA charmoso ajudando um usuário a se comunicar no Telegram. Você tem acesso a ferramentas para:

1. **Telegram** - Ler e enviar mensagens
2. **searchPickupLines** - SUA FERRAMENTA PRINCIPAL para cantadas, conselhos de namoro e dicas de relacionamento (busca na base indexada)
3. **niaSearch** - Busca geral (apenas se searchPickupLines não ajudar)
4. **AI-ify** - Transformar mensagens em respostas inteligentes

## Sua Personalidade
- Espirituoso e charmoso, mas não brega (cringe)
- Energia de "wingman" (parceiro) solidário
- Saiba quando ser romântico vs engraçado
- Nunca soe robótico ou genérico

## Como Ajudar
- Quando solicitado a ler mensagens, use getChats primeiro para encontrar o chat certo, depois getMessages
- Ao criar respostas, SEMPRE use searchPickupLines PRIMEIRO para inspiração
- Ao enviar mensagens, confirme com o usuário antes de enviar, a menos que ele tenha dito explicitamente para enviar
- Combine com a energia e o tom da conversa

## Regras Importantes
1. SEMPRE use ferramentas para obter dados reais - não invente conteúdo de mensagens
2. **USE searchPickupLines** para QUALQUER pergunta sobre relacionamento/namoro/flerte!
3. Seja conciso em suas explicações
4. Se algo falhar, explique o que deu errado claramente em português
5. Nunca envie uma mensagem sem confirmação do usuário (a menos que ele tenha dito "envie")

## Estilo de Resposta
- Mantenha as respostas naturais e conversacionais (em Português)
- NÃO use formatação markdown (sem **, sem ##, sem bullet points com -)
- Use apenas texto simples, pois este é um CLI de terminal
- Use emojis com moderação para dicas visuais
- Ao sugerir mensagens, coloque-as entre aspas, como: "oi, tudo bem?"
- Mantenha breve e fácil de ler
- IMPORTANTE: Todas as mensagens sugeridas para envio devem ser minúsculas (lowercase), nunca maiúsculas. Digite como uma pessoa normal enviando mensagens, não formal.`;

// Message history for the conversation
let messageHistory: Array<{ role: "user" | "assistant"; content: string }> = [];

/**
 * Process a user message and stream the response
 */
export async function chat(userMessage: string): Promise<AsyncIterable<string>> {
  // Add user message to history
  messageHistory.push({
    role: "user",
    content: userMessage,
  });

  // Create the streaming response using Google's Gemini
  const result = streamText({
    model: google(config.model),
    system: SYSTEM_PROMPT,
    messages: messageHistory,
    tools,
    maxSteps: 10, // Replaced stopWhen: stepCountIs(10) with maxSteps (current AI SDK API)
    onStepFinish: ({ toolCalls, toolResults }) => {
      // Log tool usage with clean formatting
      if (toolCalls && toolCalls.length > 0) {
        for (const call of toolCalls) {
          const argsObj = ('args' in call ? call.args : {}) as Record<string, unknown>;
          const argPreview = Object.entries(argsObj)
            .slice(0, 2)
            .map(([k, v]) => typeof v === 'string' ? v.slice(0, 30) : JSON.stringify(v))
            .join(', ');
          console.log(`  ${pc.dim('→')} ${pc.yellow(call.toolName)} ${pc.dim(`(${argPreview})`)}`);
        }
      }
      // Log tool results - clean summary only
      if (toolResults && toolResults.length > 0) {
        for (const res of toolResults) {
          const result = ('result' in res ? res.result : res) as Record<string, unknown>;
          let summary = '';
          if (result && typeof result === 'object') {
            if ('results' in result && Array.isArray(result.results)) {
              summary = `${result.results.length} results`;
            } else if ('chats' in result && Array.isArray(result.chats)) {
              summary = `${result.chats.length} chats`;
            } else if ('messages' in result && Array.isArray(result.messages)) {
              summary = `${result.messages.length} messages`;
            } else if ('contacts' in result && Array.isArray(result.contacts)) {
              summary = `${result.contacts.length} contacts`;
            } else if ('success' in result) {
              summary = result.success ? 'done' : 'failed';
            } else if ('error' in result) {
              summary = `error: ${result.error}`;
            } else if ('status' in result) {
              summary = `status: ${result.status}`;
            }
          }
          if (summary) {
            console.log(`  ${pc.green('✓')} ${pc.dim(summary)}`);
          }
        }
      }
    },
  });

  // Return an async generator that yields text chunks
  return (async function* () {
    let fullResponse = "";

    for await (const chunk of result.textStream) {
      fullResponse += chunk;
      yield chunk;
    }

    // Add assistant response to history
    messageHistory.push({
      role: "assistant",
      content: fullResponse,
    });
  })();
}

/**
 * Clear conversation history
 */
export function clearHistory() {
  messageHistory = [];
}

/**
 * Get current message count
 */
export function getHistoryLength(): number {
  return messageHistory.length;
}
