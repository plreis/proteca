# ADR 0004 — Tela da turma sem coleta de dados

- **Status:** aceita
- **Data:** 24/11/2026
- **Complementa:** ADR 0002

O propósito do Proteca pede que a turma veja o mascote, e não só o professor. Pedir que cada estudante aceite cookies ou um termo, por solicitação do professor, não daria um consentimento livre (há assimetria de poder e, abaixo de 12 anos, a LGPD exige o consentimento do responsável), e um site não enxerga outras abas ou aplicativos de qualquer forma. Por isso a turma acessa uma tela pública aberta pelo código da sessão, sem login, sem cookies e sem enviar nada à API: a tela só mostra a intervenção que o professor decidiu enviar e toca a voz do Proteca.

## Consequências

- A adesão de cada dispositivo à sessão e o sinal de foco da aba ficam como trabalho futuro e exigem uma nova decisão sobre a base legal antes de serem construídos.
- O papel de Gestor fica fora do escopo desta entrega: o código não tem regras diferentes para ele, e uma funcionalidade pela metade não seria pontuada.
- O código da turma só expõe o objetivo da aula e a intervenção enviada, nada sobre dispositivos, ocorrências ou estudantes.
