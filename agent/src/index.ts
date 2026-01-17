#!/usr/bin/env bun
/**
 * Telegram AI Agent CLI
 * Interactive chatbox for communicating via Telegram with AI assistance
 */

import * as p from "@clack/prompts";
import pc from "picocolors";
import { chat, clearHistory, getHistoryLength } from "./agent";
import { config, validateConfig } from "./config";

// ASCII art banner
const BANNER = `
${pc.cyan("╔════════════════════════════════════════════╗")}
${pc.cyan("║")}  ${pc.bold(pc.magenta("🤖 Telegram AI Agent"))}                     ${pc.cyan("║")}
${pc.cyan("║")}  ${pc.dim("Seu Assistente de IA para Telegram")}         ${pc.cyan("║")}
${pc.cyan("╚════════════════════════════════════════════╝")}
`;

// Help text
const HELP_TEXT = `
${pc.bold("Comandos:")}
  ${pc.yellow("/help")}     - Mostrar esta ajuda
  ${pc.yellow("/clear")}    - Limpar histórico da conversa
  ${pc.yellow("/status")}   - Verificar conexão
  ${pc.yellow("/quit")}     - Sair do agente

${pc.bold("Exemplos de prompts:")}
  ${pc.dim("• Mostre meus chats recentes")}
  ${pc.dim("• Leia as últimas 5 mensagens de @usuario")}
  ${pc.dim("• O que devo responder sobre o café?")}
  ${pc.dim("• Envie 'Bom dia linda ☀️' para @usuario")}
  ${pc.dim("• Melhore a mensagem 'Saudades' de um jeito romântico")}
`;

async function checkTelegramConnection(): Promise<boolean> {
  try {
    const response = await fetch(`${config.telegramApiUrl}/health`);
    if (response.ok) {
      const data = await response.json();
      return data.connected === true;
    }
    return false;
  } catch {
    return false;
  }
}

async function main() {
  console.clear();
  console.log(BANNER);

  // Validate configuration
  validateConfig();

  p.intro(pc.bgCyan(pc.black(" Bem-vindo ao seu Agente Telegram com IA ")));

  // Check Telegram connection
  const connectionSpinner = p.spinner();
  connectionSpinner.start("Verificando conexão com Telegram...");

  const isConnected = await checkTelegramConnection();

  if (isConnected) {
    connectionSpinner.stop(pc.green("✓ Telegram conectado"));
  } else {
    connectionSpinner.stop(pc.yellow("⚠ API do Telegram não conectada"));
    p.note(
      `Inicie a ponte da API do Telegram primeiro:\n${pc.cyan("python telegram_api.py")}`,
      "Configuração Necessária"
    );
  }

  // Show config status
  const configStatus = [
    `Modelo: ${pc.cyan(config.model)}`,
    `API Telegram: ${pc.cyan(config.telegramApiUrl)}`,
    `Fonte Nia: ${config.niaCodebaseSource ? pc.green("✓ Configurado") : pc.yellow("Não definido")}`,
  ].join("\n");

  p.note(configStatus, "Configuração");

  console.log(HELP_TEXT);

  // Main chat loop
  while (true) {
    const input = await p.text({
      message: pc.cyan("Você"),
      placeholder: "Digite sua mensagem ou /help para comandos...",
    });

    // Handle cancellation (Ctrl+C)
    if (p.isCancel(input)) {
      p.outro(pc.dim("Até logo! 👋"));
      process.exit(0);
    }

    const message = (input as string).trim();

    if (!message) continue;

    // Handle commands
    if (message.startsWith("/")) {
      const command = message.toLowerCase();

      switch (command) {
        case "/help":
          console.log(HELP_TEXT);
          continue;

        case "/clear":
          clearHistory();
          p.log.success("Histórico da conversa limpo");
          continue;

        case "/status":
          const connected = await checkTelegramConnection();
          p.log.info(
            connected
              ? pc.green("Telegram: Conectado ✓")
              : pc.red("Telegram: Não conectado ✗")
          );
          p.log.info(`Mensagens no histórico: ${getHistoryLength()}`);
          continue;

        case "/quit":
        case "/exit":
        case "/q":
          p.outro(pc.dim("Até logo! 👋"));
          process.exit(0);

        default:
          p.log.warn(`Comando desconhecido: ${command}. Digite /help para comandos disponíveis.`);
          continue;
      }
    }

    // Process with AI agent
    const spinner = p.spinner();
    spinner.start(pc.dim("Pensando..."));

    try {
      const stream = await chat(message);
      spinner.stop(pc.magenta("Agente"));

      // Stream the response
      let response = "";
      process.stdout.write(pc.dim("  "));

      for await (const chunk of stream) {
        process.stdout.write(chunk);
        response += chunk;
      }

      console.log("\n");
    } catch (error: any) {
      spinner.stop(pc.red("Error"));

      if (error.message?.includes("Telegram API")) {
        p.log.error(
          `Telegram API error. Make sure the bridge is running:\n${pc.cyan("python telegram_api.py")}`
        );
      } else if (error.message?.includes("AI_GATEWAY")) {
        p.log.error("AI Gateway error. Check your AI_GATEWAY_API_KEY.");
      } else {
        p.log.error(error.message || "An unexpected error occurred");
      }
    }
  }
}

// Run
main().catch((error) => {
  console.error(pc.red("Fatal error:"), error);
  process.exit(1);
});
