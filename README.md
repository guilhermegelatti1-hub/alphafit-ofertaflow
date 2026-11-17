# AlphaFit OfertaFlow — Streamlit Community Cloud

**Aplicação em Streamlit**, para operar a partir de um navegador. Não utilize os arquivos antigos de FastAPI/Uvicorn no Streamlit Community Cloud.

## 1. Publicar

1. O repositório pode ser público para implantação, mas não faça commits de senhas, tokens, `.env` ou `.streamlit/secrets.toml`.
2. Em https://share.streamlit.io/deploy, conecte o GitHub e escolha:
   - **Repository:** `guilhermegelatti1-hub/alphafit-ofertaflow`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **Custom subdomain:** escolha, se disponível, `alphafit-ofertaflow` (o endereço definitivo é o informado pelo Streamlit).
3. Em **Advanced settings → Secrets**, informe os campos do exemplo `secrets.example.toml`, substituindo os placeholders:

```toml
APP_PASSWORD = "SUA_SENHA_FORTE_EXCLUSIVA_DO_PAINEL"
APP_STATE_SECRET = "UM_SEGREDO_ALEATORIO_COM_32_OU_MAIS_CARACTERES"
ML_CLIENT_ID = "6224034969171582"
ML_CLIENT_SECRET = "A_CHAVE_NOVA_RENOVADA_NO_MERCADO_LIVRE"
ML_REDIRECT_URI = "https://SEU-SUBDOMINIO.streamlit.app/"
```

**NUNCA adicione um `secrets.toml` com valores reais ao GitHub e NUNCA envie o Client Secret por chat.** A chave que apareceu numa captura anterior deve ter sido renovada.

**Se você ainda não sabe a URL:** publique primeiro com a URL indicada na tela do Streamlit; depois ajuste `ML_REDIRECT_URI` em Secrets para o endereço **real e exato** de seu app com `/` no final, e reinicie o app.

## 2. Configurar OAuth no Mercado Livre

No Mercado Livre DevCenter, edite o aplicativo **Alphafit**. Em **URIs de redirect**, cadastre a **URL raiz do Streamlit**, por exemplo:

```text
https://SEU-SUBDOMINIO.streamlit.app/
```

**Não use `/oauth/callback`:** isso era exclusivo do servidor FastAPI/Render. O Streamlit processa o código de autorização pelos parâmetros `?code=...&state=...` na própria URL do aplicativo.

Permissões necessárias: fluxo Authorization Code, Refresh Token, negócio Mercado Livre, escopos de leitura de usuários/anúncios autorizados. Não habilite permissões de escrita, faturamento e vendas sem necessidade.

A conexão OAuth permite consultar informações da conta pela API, dependendo dos escopos e permissões efetivamente disponíveis. **Ela não gera links de afiliado.**

## 3. Busca e filtros automáticos

A aba **Buscar produtos** usa a API oficial do Mercado Livre Brasil para buscar anúncios por palavras-chave, após autorização da conta. Filtros básicos: **categoria, ID do vendedor, preço mínimo/máximo, condição (novo/usado), frete grátis, desconto mínimo informado e ordenação**. A busca usa até 50 anúncios por consulta e filtra somente essa amostra; ela não representa necessariamente todo o mercado.

Quando a busca geral é bloqueada pela API com **HTTP 403**, o aplicativo tenta uma consulta limitada ao catálogo oficial de produtos (sem filtro de vendedor/categoria) e aceita apenas ofertas vencedoras com anúncio e preço identificados; produtos de catálogo sem oferta real são descartados. Preços anteriores e descontos não são inferidos. Caso também não seja possível, o aplicativo explica o erro e abre a pesquisa no próprio Mercado Livre. A documentação oficial contempla os endpoints de busca e catálogo, mas algumas contas podem receber HTTP 403.

A opção **Atualizar a cada 15 minutos** funciona **somente com a sessão aberta no navegador**; não é monitoramento contínuo em segundo plano.

**Proteção do afiliado:** o produto pesquisado é salvo sem link de afiliado. Uma publicação de WhatsApp somente pode ser gerada depois que você informar um link válido produzido na sua conta. Links existentes são preservados ao buscar novamente.

## 4. Uso

- Adicione produtos manualmente pelo ID do anúncio `MLB...` ou URL oficial; com OAuth ativo, o programa tenta consultar dados do anúncio pela API.
- Cole **seu próprio link de afiliado**, gerado no portal oficial do Mercado Livre, e confirme sua origem.
- Gere mensagens e abra o WhatsApp. O app **não envia mensagens automaticamente a grupos**.
- Importe ou **exporte CSV após cada mudança**; o Streamlit Community Cloud não garante persistência do armazenamento local nem da sessão.
- Um link com formato válido **não prova** a titularidade, comissão ou atribuição. Confira no Portal do Afiliado.

## 5. Limitações desta primeira versão Streamlit

- Produtos e tokens OAuth ficam **apenas na sessão ativa**. Depois de um reinício, logout ou perda de sessão, será necessário importar o CSV novamente e autorizar o Mercado Livre novamente. A versão **não é adequada para dados que precisam de retenção automática** sem adicionar armazenamento externo.
- A conta protegida é de **uso pessoal**; configure a aplicação Streamlit como **privada**, além da senha forte do painel.
- Comissões e clique/venda não são auditados automaticamente; o programa não tem integração pública ao gerador de links de afiliado do Mercado Livre.
- O app utiliza autenticação OAuth com `state` assinado e expirável. Para uma futura versão multiusuário, seria necessário adicionar armazenamento persistente e vinculação de estados OAuth a sessões individuais com controles adicionais.

## 6. Testes locais

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q tests
streamlit run streamlit_app.py
```

Documentação oficial: [Deploy Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [Streamlit Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), [Streamlit armazenamento local](https://docs.streamlit.io/develop/concepts/connections/connecting-to-data).
