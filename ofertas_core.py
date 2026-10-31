"""Pure helpers shared by the Streamlit app and its tests."""
import csv
import io
import math
import re
from urllib.parse import urlsplit, parse_qs, urlencode


def item_id(value):
    value = str(value or '').strip()
    if re.fullmatch(r'MLB\d{7,15}',value,re.I):
        return value.upper()
    try:
        part = urlsplit(value)
        if part.scheme != 'https' or (part.hostname or '').lower() not in {
            'mercadolivre.com.br','www.mercadolivre.com.br','produto.mercadolivre.com.br',
            'mercadolivre.com','www.mercadolivre.com'
        }:
            return None
        if re.search(r'/p/MLB\d+',part.path,re.I):
            return None
        match=re.search(r'(?:^|[/\-_])MLB-?(\d{7,15})(?=[/\-_\.]|$)',part.path,re.I)
        return f'MLB{match.group(1)}' if match else None
    except ValueError:
        return None


def affiliate_format(url):
    """Recognizes common ML affiliate formats but DOES NOT prove ownership/commission."""
    if not isinstance(url,str) or len(url)>2048:
        return False
    try:
        p=urlsplit(url.strip())
        if p.scheme!='https' or p.username or p.password or p.port or p.fragment:
            return False
        host=(p.hostname or '').lower()
        path=p.path.strip('/')
        if host in {'meli.la','www.meli.la'}:
            return bool(re.fullmatch(r'[A-Za-z0-9_-]{3,200}',path))
        if host in {'mercadolivre.com.br','www.mercadolivre.com.br','mercadolivre.com','www.mercadolivre.com'}:
            if re.fullmatch(r'(?:sec|social)/[A-Za-z0-9_-]{3,200}',path):
                return True
            is_product=bool(re.search(r'(?:^|/)MLB-?\d{7,15}(?:[/\-_\.]|$)',p.path,re.I) or re.search(r'^/p/MLB\d{7,15}(?:/|$)',p.path,re.I))
            query={k.lower():v for k,v in parse_qs(p.query).items()}
            return bool(is_product and query.get('matt_tool') and query.get('matt_word') and query['matt_word'][0])
    except (ValueError,UnicodeError):
        return False
    return False


def clean_price(text):
    if text in (None,''): return None
    if isinstance(text,(float,int)):value=float(text)
    else:
        s=str(text).strip().replace('R$','').replace(' ','')
        if not s:return None
        if ',' in s:s=s.replace('.','').replace(',','.')
        value=float(s)
    if not math.isfinite(value) or value<0 or value>100000000:
        raise ValueError('Preço inválido')
    return value


def money(v):
    return f'R$ {v:,.2f}'.replace(',','X').replace('.',',').replace('X','.')


def message(product):
    link=(product.get('affiliate_url') or '').strip()
    if not affiliate_format(link):
        raise ValueError('Oferta bloqueada: cadastre seu link de afiliado, gerado no portal oficial.')
    title=re.sub(r'[\r\n\t*]+',' ',str(product.get('title',''))).strip()
    if not title:
        raise ValueError('Produto sem título')
    p=clean_price(product.get('price'))
    previous=clean_price(product.get('original_price'))
    msg=f'🔥 *OFERTA DO DIA*\n\n🛍️ *{title}*\n'
    if p is not None:
        if previous is not None and previous>p:
            msg+=f'\n❌ De: ~{money(previous)}~\n✅ *Por: {money(p)}*\n🏷️ {round((previous-p)*100/previous)}% OFF\n'
        else:
            msg+=f'\n💰 *Preço: {money(p)}*\n'
    return msg+'\n🛒 *Ver oferta:*\n'+link+'\n\n📌 Link de afiliado. Preço e disponibilidade sujeitos a alteração.'


def load_csv(data, existing=None, limit=300):
    existing=dict(existing or {})
    if isinstance(data,bytes):data=data.decode('utf-8-sig')
    reader=csv.DictReader(io.StringIO(data.lstrip('\ufeff')))
    if not reader.fieldnames or not {'item_id','affiliate_url'}.issubset(reader.fieldnames):
        raise ValueError('O CSV precisa conter item_id e affiliate_url.')
    errors=[];count=0
    for n,row in enumerate(reader,2):
        if n>limit+1:break
        key=item_id(row.get('item_id'))
        link=(row.get('affiliate_url') or '').strip()
        if not key or not affiliate_format(link):
            errors.append(f'Linha {n}: anúncio/link inválido')
            continue
        old=existing.get(key,{})
        title=(row.get('title') or old.get('title') or '').strip()
        if not title:
            errors.append(f'Linha {n}: produto novo requer título')
            continue
        try:
            price=clean_price(row.get('price')) if row.get('price') not in (None,'') else old.get('price')
            original=clean_price(row.get('original_price')) if row.get('original_price') not in (None,'') else old.get('original_price')
        except ValueError:
            errors.append(f'Linha {n}: preço inválido')
            continue
        existing[key]={**old,'item_id':key,'title':title[:220],'price':price,
                       'original_price':original,'affiliate_url':link,
                       'source':old.get('source','csv'), 'permalink':old.get('permalink','')}
        count+=1
    return existing,count,errors


def dump_csv(products):
    out=io.StringIO(); writer=csv.DictWriter(out,fieldnames=['item_id','title','price','original_price','affiliate_url'])
    writer.writeheader()
    for p in products.values():writer.writerow({k:p.get(k,'') for k in writer.fieldnames})
    return out.getvalue().encode('utf-8-sig')


def whatsapp_url(msg):
    return 'https://wa.me/?'+urlencode({'text':msg})