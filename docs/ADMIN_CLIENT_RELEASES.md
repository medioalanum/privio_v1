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
Planejamento criado; implementação e verificações serão registradas por fase.
