"""AlphaFit OfertaFlow — Streamlit Community Cloud edition.

Deliberately session-only: Community Cloud has no durable local storage.
Do not persist OAuth tokens or real credentials into GitHub.
"""
import hashlib
import hmac
import secrets as pysecrets
import time
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx
import streamlit as st

from ofertas_core import affiliate_format, clean_price, dump_csv, item_id, load_csv, message, whatsapp_url

st.set_page_config(page_title='AlphaFit | OfertaFlow', page_icon='🏷️', layout='wide')
st.markdown('''<style>
  [data-testid="stAppViewContainer"] { background: #0d1117; }
  .big-title { font-size: 2.1rem; font-weight: 800; margin-bottom:0; }
  .accent { color: #ec3345; }
  .muted { color:#abb2bd; font-size:.9rem; }
  div[data-testid="stMetric"] {border:1px solid #303845;border-radius:14px;padding:14px;background:#161b22}
</style>''', unsafe_allow_html=True)

AUTH='https://auth.mercadolivre.com.br/authorization'
API='https://api.mercadolibre.com'


def config(name):
    try:
        value=st.secrets.get(name,'')
    except Exception:
        return ''
    return str(value).strip()


def state_signature(data):
    return hmac.new(config('APP_STATE_SECRET').encode(),data.encode(),hashlib.sha256).hexdigest()


def make_state():
    text=f'{int(time.time())}.{pysecrets.token_urlsafe(20)}'
    return f'{text}.{state_signature(text)}'


def verified_state(value):
    try:
        timestamp, random_string, sig = value.split('.',2)
        data=f'{timestamp}.{random_string}'
        return (abs(int(time.time())-int(timestamp))<600
                and bool(random_string)
                and hmac.compare_digest(state_signature(data),sig))
    except (ValueError,TypeError,AttributeError):
        return False


def secrets_complete():
    required=['APP_PASSWORD','APP_STATE_SECRET','ML_CLIENT_ID','ML_CLIENT_SECRET','ML_REDIRECT_URI']
    return all(config(k) and not config(k).startswith(('SUBSTITUA','CHAVE_RENOVADA','https://SEU')) for k in required) and len(config('APP_STATE_SECRET'))>=32


def oauth_url():
    return AUTH+'?'+urlencode({'response_type':'code','client_id':config('ML_CLIENT_ID'),
                               'redirect_uri':config('ML_REDIRECT_URI'), 'state':make_state()})


def api_request(method,path,*,params=None,data=None,token=None):
    headers={'Accept':'application/json'}
    if token:headers['Authorization']=f'Bearer {token}'
    try:
        with httpx.Client(timeout=18.0,follow_redirects=False) as client:
            resp=client.request(method,API+path,params=params,data=data,headers=headers)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError,ValueError) as exc:
        code=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
        raise RuntimeError(f'Mercado Livre não respondeu à solicitação{f" (HTTP {code})" if code else ""}.') from None


def authorize_callback(code,state):
    if not verified_state(state):
        raise ValueError('Estado OAuth inválido ou expirado. Inicie a autorização novamente.')
    tokens=api_request('POST','/oauth/token',data={
        'grant_type':'authorization_code', 'client_id':config('ML_CLIENT_ID'),
        'client_secret':config('ML_CLIENT_SECRET'),
        'redirect_uri':config('ML_REDIRECT_URI'),'code':code})
    if not tokens.get('access_token'):
        raise RuntimeError('O Mercado Livre não retornou o token de acesso.')
    profile=api_request('GET','/users/me',token=tokens['access_token'])
    tokens['saved_at']=time.time()
    st.session_state['meli_tokens']=tokens
    st.session_state['meli_user']=str(profile.get('nickname') or profile.get('id') or 'Conectado')


def access_token():
    tokens=st.session_state.get('meli_tokens')
    if not tokens:
        raise ValueError('Conecte a conta do Mercado Livre nesta sessão primeiro.')
    if time.time() < float(tokens.get('saved_at',0))+int(tokens.get('expires_in',21600))-120:
        return tokens['access_token']
    if not tokens.get('refresh_token'):
        st.session_state.pop('meli_tokens',None)
        raise ValueError('A sessão expirou. Reconecte sua conta.')
    renewed=api_request('POST','/oauth/token',data={
        'grant_type':'refresh_token','client_id':config('ML_CLIENT_ID'),
        'client_secret':config('ML_CLIENT_SECRET'),'refresh_token':tokens['refresh_token']})
    renewed['saved_at']=time.time()
    st.session_state['meli_tokens']=renewed
    return renewed['access_token']


def fetch_item(code):
    data=api_request('GET','/items/'+code,token=access_token())
    if data.get('id')!=code or data.get('currency_id','BRL')!='BRL':
        raise ValueError('Anúncio não corresponde ao código consultado ou não está em reais.')
    image=data.get('thumbnail','')
    if image.startswith('http://'):
        image='https://'+image[7:]
    return {'item_id':code,'title':data.get('title') or code,'price':data.get('price'),
            'original_price':data.get('original_price'),'affiliate_url':'',
            'image_url':image,'permalink':data.get('permalink',''),'source':'api'}


def save_product(product):
    key=product['item_id']
    current=st.session_state['products'].get(key,{})
    # Never overwrite a registered affiliate link on API refresh.
    new={**current,**product}
    if not product.get('affiliate_url') and current.get('affiliate_url'):
        new['affiliate_url']=current['affiliate_url']
    st.session_state['products'][key]=new


if 'products' not in st.session_state:st.session_state['products']={}
if 'authenticated' not in st.session_state:st.session_state['authenticated']=False

# Security guard: no publicly usable dashboard without configured secrets.
if not secrets_complete():
    st.error('A configuração segura do aplicativo ainda não foi concluída.')
    st.info('No Streamlit Cloud, abra Advanced settings → Secrets e configure APP_PASSWORD, APP_STATE_SECRET, ML_CLIENT_ID, ML_CLIENT_SECRET e ML_REDIRECT_URI. Consulte o README do projeto.')
    st.stop()

redirect=urlsplit(config('ML_REDIRECT_URI'))
if redirect.scheme!='https' or not redirect.hostname or not redirect.hostname.endswith('.streamlit.app') or redirect.query or redirect.fragment or redirect.path not in ('','/'):
    st.error('ML_REDIRECT_URI deve ser a URL HTTPS exata do aplicativo Streamlit, terminando com /, sem parâmetros.')
    st.stop()

if not st.session_state['authenticated']:
    left,center,right=st.columns([1,1.5,1])
    with center:
        st.markdown('<div class="big-title">ALPHA<span class="accent">FIT</span> OfertaFlow</div>',unsafe_allow_html=True)
        st.caption('Painel privado de promoções e links de afiliado')
        with st.form('login'):
            pwd=st.text_input('Senha do painel',type='password')
            enter=st.form_submit_button('Entrar',use_container_width=True)
        if enter:
            if hmac.compare_digest(pwd,config('APP_PASSWORD')):
                st.session_state['authenticated']=True
                st.rerun()
            else:
                st.error('Senha incorreta.')
    st.stop()

with st.sidebar:
    st.markdown('### ALPHA<span style="color:#ef3346">FIT</span> OfertaFlow',unsafe_allow_html=True)
    st.caption('Administração de ofertas • versão Streamlit')
    if st.button('Sair',use_container_width=True):
        for key in ('authenticated','meli_tokens','meli_user'):
            st.session_state.pop(key,None)
        st.query_params.clear()
        st.rerun()
    st.divider()
    st.warning('Armazenamento temporário: exporte CSV para não perder as ofertas quando a sessão ou o servidor reiniciar.')

# OAuth code comes back in URL query parameters, not in a FastAPI /oauth/callback endpoint.
if 'code' in st.query_params or 'error' in st.query_params:
    code=str(st.query_params.get('code',''))
    state=str(st.query_params.get('state',''))
    error=str(st.query_params.get('error',''))
    if error:
        st.error('A autorização foi cancelada ou recusada pelo Mercado Livre.')
    elif code:
        try:
            authorize_callback(code,state)
            st.success('Conta do Mercado Livre autorizada nesta sessão.')
        except (RuntimeError,ValueError) as exc:
            st.error(str(exc))
    st.query_params.clear()

st.markdown('<div class="big-title">ALPHA<span class="accent">FIT</span> | Ofertas</div>',unsafe_allow_html=True)
st.caption('Mercado Livre • organização de ofertas e divulgação por links de afiliado')
products=st.session_state['products']
ready=sum(1 for p in products.values() if affiliate_format(p.get('affiliate_url','')))
c1,c2,c3=st.columns(3)
c1.metric('Produtos cadastrados',len(products))
c2.metric('Com link cadastrado',ready)
c3.metric('Aguardando link',len(products)-ready)

tab_offers,tab_add,tab_import,tab_meli=st.tabs(['Ofertas','Adicionar produto','CSV / Backup','Conta Mercado Livre'])

with tab_offers:
    if not products:st.info('Nenhum produto cadastrado. Adicione um anúncio ou importe um CSV.')
    for key,p in list(products.items()):
        with st.expander(f"{p['title']} — {key}" + (' | Link cadastrado' if affiliate_format(p.get('affiliate_url','')) else ' | Aguardando link')):
            left,right=st.columns([1,2])
            with left:
                if p.get('image_url','').startswith('https://'):
                    st.image(p['image_url'],width=160)
                if p.get('price') is not None:st.metric('Preço',f"R$ {p['price']:.2f}".replace('.',','))
            with right:
                with st.form(f'edit-{key}'):
                    new_title=st.text_input('Produto',value=p.get('title',''))
                    new_price=st.text_input('Preço atual (R$)',value='' if p.get('price') is None else str(p['price']))
                    old_price=st.text_input('Preço anterior (R$)',value='' if p.get('original_price') is None else str(p['original_price']))
                    link=st.text_input('Seu link de afiliado',value=p.get('affiliate_url',''))
                    claimed=st.checkbox('Confirmo que gerei este link na minha conta de afiliado',key=f'claim-{key}')
                    submitted=st.form_submit_button('Salvar alterações')
                if submitted:
                    try:
                        if link and (not claimed or not affiliate_format(link)):
                            raise ValueError('Confirme a titularidade e informe um link com formato reconhecido.')
                        if not new_title.strip():raise ValueError('Título obrigatório.')
                        save_product({**p,'title':new_title.strip(),'price':clean_price(new_price),
                                      'original_price':clean_price(old_price),'affiliate_url':link.strip()})
                        st.success('Produto atualizado.')
                        st.rerun()
                    except ValueError as exc:st.error(str(exc))
                if affiliate_format(p.get('affiliate_url','')):
                    msg=message(p)
                    st.text_area('Mensagem para WhatsApp',msg,height=220,key=f'msg-{key}')
                    st.link_button('Abrir no WhatsApp',whatsapp_url(msg))
                    st.caption('Copie a mensagem ou abra o WhatsApp; o envio em grupos não é automático.')
                else:
                    st.warning('Mensagem bloqueada até cadastrar seu link de afiliado.')
                col_refresh,col_delete=st.columns(2)
                with col_refresh:
                    if st.button('Atualizar pela API',key=f'refresh-{key}'):
                        try:
                            item=fetch_item(key)
                            save_product(item)
                            st.success('Preço consultado pela API; link preservado.')
                            st.rerun()
                        except (RuntimeError,ValueError) as exc:st.error(str(exc))
                with col_delete:
                    if st.button('Remover produto',key=f'delete-{key}'):
                        del st.session_state['products'][key]
                        st.rerun()

with tab_add:
    with st.form('new-product'):
        url=st.text_input('ID MLB ou URL do anúncio',placeholder='MLB1234567890')
        title=st.text_input('Título (necessário para cadastro manual)')
        col1,col2=st.columns(2)
        with col1:price=st.text_input('Preço atual',placeholder='69,90')
        with col2:original_price=st.text_input('Preço anterior',placeholder='99,90')
        aff=st.text_input('Link gerado pelo seu portal de afiliados (opcional)')
        confirm=st.checkbox('Confirmo que o link foi gerado pela minha própria conta')
        submit=st.form_submit_button('Adicionar oferta')
    if submit:
        key=item_id(url)
        if not key:st.error('Use o ID MLB do anúncio ou uma URL oficial do anúncio.')
        elif aff and (not confirm or not affiliate_format(aff)):
            st.error('Link não reconhecido ou confirmação de titularidade ausente.')
        else:
            try:
                if st.session_state.get('meli_tokens'):
                    try:data=fetch_item(key)
                    except (RuntimeError,ValueError):
                        if not title.strip():raise
                        data={'item_id':key,'title':title.strip(),'price':clean_price(price),
                              'original_price':clean_price(original_price),'source':'manual'}
                else:
                    if not title.strip():raise ValueError('Preencha o título ou conecte sua conta para consultar pela API.')
                    data={'item_id':key,'title':title.strip(),'price':clean_price(price),
                          'original_price':clean_price(original_price),'source':'manual'}
                if aff:data['affiliate_url']=aff.strip()
                save_product(data)
                st.success('Produto cadastrado. O sistema somente libera mensagens com link de afiliado.')
            except (RuntimeError,ValueError) as exc:st.error(str(exc))

with tab_import:
    st.info('O CSV funciona como backup manual. Faça download sempre que cadastrar ou atualizar suas ofertas.')
    st.download_button('Exportar meus produtos em CSV',dump_csv(products),file_name='alphafit_ofertas.csv',mime='text/csv',disabled=not bool(products))
    sample='item_id,title,price,original_price,affiliate_url\nMLB1234567890,Produto exemplo,69.90,99.90,https://meli.la/SEU_LINK_REAL\n'
    st.download_button('Modelo de CSV',sample.encode('utf-8'),file_name='modelo_ofertas.csv',mime='text/csv')
    file=st.file_uploader('Importar CSV com seus links',type=['csv'])
    own=st.checkbox('Confirmo que os links no CSV foram gerados pela minha conta de afiliado')
    if st.button('Importar ofertas',disabled=not bool(file)):
        if not own:st.error('Confirme a origem dos links antes da importação.')
        else:
            try:
                data,count,errors=load_csv(file.getvalue(),products)
                st.session_state['products']=data
                st.success(f'{count} produto(s) importado(s).')
                if errors:st.warning('\n'.join(errors[:15]))
            except (ValueError,UnicodeError) as exc:st.error(str(exc))

with tab_meli:
    st.markdown('#### Conexão autorizada com Mercado Livre')
    if st.session_state.get('meli_tokens'):
        st.success('Conectado nesta sessão como: '+st.session_state.get('meli_user','Conta Mercado Livre'))
        if st.button('Desconectar'):
            st.session_state.pop('meli_tokens',None)
            st.session_state.pop('meli_user',None)
            st.rerun()
    else:
        st.link_button('Conectar minha conta',oauth_url())
        st.caption('Você será levado ao site oficial do Mercado Livre para autorizar a aplicação AlphaFit.')
    st.code(config('ML_REDIRECT_URI'),language='text')
    st.caption('Cadastre exatamente a URL acima em Alphafit → URIs de redirect, no DevCenter.')
    st.warning('A conexão OAuth e os produtos ficam apenas nesta sessão do Streamlit. O Mercado Livre não oferece uma API pública de geração automática de links de afiliado para este fluxo. A titularidade/atribuição das comissões não é verificável automaticamente.')