# Admin / Client: entregas incrementais

## Contrato
Admin opera o mês; Client consulta uma visão macro. Os dois usam a mesma fonte
financeira. Dinheiro atual nunca inclui receitas esperadas. Total até o fim do
mês inclui atrasados uma vez. Saldos desconhecidos permanecem desconhecidos.
Preservar stack, senhas, permissões, IDs e todos os registros. Não migrar o banco
para mudanças de apresentação. Não alterar dados para obter números de exemplo.

## Fases e commits
0. Plano e testes de referência (sem deploy).
1. Nomes Admin/Client, logins admin/client e compatibilidade temporária com os
   logins configurados; testes de autenticação e isolamento. Deploy 1.
2. Resumo financeiro comum e painel operacional Admin: três números, vencidos
   incluídos e lista simples; testes financeiros e HTTP. Deploy 2.
3. Client: cobertura do mês, alertas e detalhes recolhidos, sem ações de escrita;
   testes de permissões e gráficos, desktop e celular. Deploy 3.
4. Previsão acumulada mensal, traduções e acabamento; testes de limites,
   projeção e regressão. Deploy 4.

## Gates por deploy
CI, suíte completa, revisão do diff, validação visual com dados sintéticos,
backup recente e restauração comprovada em banco isolado. Registrar SHA,
verificações por registro e diferenças legítimas. Main dispara deploy: nunca
integrar antes dos gates. Rollback apenas de código compatível; jamais substituir
o banco por backup antigo. Nenhum deploy se faltarem evidências ou acesso.

## Aceitação
Admin entende quanto pagar, quanto tem e falta/sobra em poucos segundos.
Client entende cobertura e meses com insuficiência sem operar o cadastro.
Sem rolagem horizontal da página no celular, texto e cor para estados,
ações nomeadas, teclado e valores de gráficos disponíveis em texto.

## Estado
Implementação local em quatro fases, cada uma com branch release/admin-client-N.
As fases 2–4 dependem da fase anterior. Não integrar todas de uma vez.

Validação local: pytest, Ruff e ty; PostgreSQL concorrente requer CI/banco isolado.
Testes cobrem logins, sessões, Client sem operações, atrasados sem duplicação,
cobertura, previsão acumulada e preservação de todas as linhas após leituras e
migração repetida. Nenhuma alteração de esquema nesta entrega.

Bloqueios de publicação: restauração local PostgreSQL impedida pela sandbox
(shmget: Operation not permitted); backup/restauração de produção ainda não
verificados nesta execução. Main e Render não foram alterados.

A prévia em 127.0.0.1:8039 usa SQLite e dados sintéticos, PREVIEW_MODE=true.
As credenciais de demonstração são fornecidas separadamente e diferem do Render.
Produção mantém as senhas EDITOR_PASS/VIEWER_PASS. A nova versão adiciona nomes
admin/client e conserva os nomes configurados como aliases de transição.
Não renomear/remover chaves de senha nem SESSION_SECRET durante este release.

