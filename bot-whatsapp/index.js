// bot-whatsapp/index.js

const venom = require('venom-bot');
const axios = require('axios');

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
    console.log(message); // Adicione esta linha
    if (message.isGroupMsg === false) {
      const texto = message.body.toLowerCase();

      // Relatório mensal
      if (texto.includes("relatório mês") || texto.includes("relatorio mes")) {
        try {
          const resposta = await axios.get('http://localhost:8000/relatorio/mensal');
          await client.sendText(message.from, formatarRelatorioMensal(resposta.data));
        } catch (err) {
          await client.sendText(message.from, "Erro ao gerar relatório mensal.");
        }
      }
      // Relatório por categoria
      else if (texto.includes("gastos por categoria")) {
        try {
          const resposta = await axios.get('http://localhost:8000/relatorio/categorias');
          await client.sendText(message.from, formatarRelatorioCategorias(resposta.data));
        } catch (err) {
          await client.sendText(message.from, "Erro ao gerar relatório por categoria.");
        }
      }
      // Registrar gasto/ganho
      else if (texto.includes("-")) {
        try {
          const resposta = await axios.post('http://localhost:8000/processar', {
            texto: message.body,
          });
          await client.sendText(message.from, resposta.data.resposta);
        } catch (err) {
          await client.sendText(message.from, "Erro ao registrar gasto/ganho.");
        }
      }
      // Ajuda ou comando desconhecido
      else {
        await client.sendText(
          message.from,
          "Comandos disponíveis:\n- Registrar gasto: 'Categoria - valor'\n- Relatório mês\n- Gastos por categoria"
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
