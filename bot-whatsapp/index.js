// bot-whatsapp/index.js

const venom = require('venom-bot');
const axios = require('axios');
const fs = require('fs');
const autorizados = JSON.parse(fs.readFileSync('./autorizados.json', 'utf8'));


// Função para formatar o relatório mensal
function formatarRelatorioMensal(data) {
  return `📊 Relatório do Mês:
- Ganhos: R$ ${data.ganhos.toFixed(2)}
- Gastos: R$ ${data.gastos.toFixed(2)}
- Saldo: R$ ${data.saldo.toFixed(2)}`;
}

// Função para formatar o relatório por categoria
function formatarRelatorioCategorias(data) {
  let texto = '📊 Gastos por Categoria:\n';
  for (const [categoria, valor] of Object.entries(data)) {
    texto += `- ${categoria}: R$ ${valor.toFixed(2)}\n`;
  }
  return texto;
}

// Função principal do bot
function start(client) {
  client.onMessage(async (message) => {
    if (message.isGroupMsg === false) {
      const usuario_id = message.from;
      const texto = message.body;

      if (!autorizados.includes(usuario_id)) {
        await client.sendText(
          message.from,
          "Seu número não está autorizado a usar este serviço."
        );
        return;
      }

      // RESET: apaga todos os dados do usuário
      if (texto.trim().toLowerCase() === "reset") {
        try {
          const resposta = await axios.delete('http://localhost:8000/reset_usuario', {
            params: { usuario_id: usuario_id }
          });
          await client.sendText(message.from, resposta.data.resposta);
        } catch (err) {
          await client.sendText(message.from, "Erro ao apagar seus dados.");
        }
        return; // Não processa mais nada depois do reset
      }

      // Registrar gasto/ganho com forma de pagamento
      if (
        /^.+\s+(pix|debito|d[eé]bito|credito|cr[eé]dito|vr)\s+[\d,.]+$/i.test(texto.trim())
      ) {
        try {
          const resposta = await axios.post('http://localhost:8000/processar', {
            texto: texto,
            usuario_id: usuario_id
          });
          await client.sendText(message.from, resposta.data.resposta);
        } catch (err) {
          await client.sendText(message.from, "Erro ao registrar gasto/ganho.");
        }
      }
      // Relatório mensal
      else if (texto.toLowerCase().includes("relatório mês") || texto.toLowerCase().includes("relatorio mes")) {
        try {
          const resposta = await axios.get('http://localhost:8000/relatorio/mensal', {
            params: { usuario_id: usuario_id }
          });
          await client.sendText(message.from, formatarRelatorioMensal(resposta.data));
        } catch (err) {
          await client.sendText(message.from, "Erro ao gerar relatório mensal.");
        }
      }
      // Relatório por categoria
      else if (texto.toLowerCase().includes("gastos por categoria")) {
        try {
          const resposta = await axios.get('http://localhost:8000/relatorio/categorias', {
            params: { usuario_id: usuario_id }
          });
          await client.sendText(message.from, formatarRelatorioCategorias(resposta.data));
        } catch (err) {
          await client.sendText(message.from, "Erro ao gerar relatório por categoria.");
        }
      }

      // Comando para saldo
      else if (texto.trim().toLowerCase() === "saldo") {
        try {
          const resposta = await axios.get('http://localhost:8000/saldo', {
            params: { usuario_id: usuario_id }
          });
          const saldos = resposta.data.saldos;
          let msg = "💰 Saldo por carteira:\n";
          msg += `- Débito/Pix: R$ ${saldos.debito.toFixed(2)}\n`;
          msg += `- Crédito: R$ ${saldos.credito.toFixed(2)}\n`;
          msg += `- VR: R$ ${saldos.vr.toFixed(2)}`;
          await client.sendText(message.from, msg);
        } catch (err) {
          await client.sendText(message.from, "Erro ao consultar seu saldo.");
        }
      }

      // Ajuda
      else {
        await client.sendText(
          message.from,
          "Comandos disponíveis:\n- Registrar gasto: 'Categoria forma_pagamento valor' (ex: comida vr 100)\n- Relatório mês\n- Gastos por categoria\n- reset (apaga todos os seus dados)\n- saldo (consulta seu saldo atual)\n- Ajuda (exibe esta mensagem)"
        );
      }
    }
  });
}

// Inicialização do Venom Bot com caminho do Chrome definido
venom
  .create({
    session: 'controle-gastos-session',
    browserArgs: ['--headless=new']
  })
  .then((client) => start(client))
  .catch((erro) => console.log(erro));
