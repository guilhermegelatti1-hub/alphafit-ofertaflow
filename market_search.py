"""Busca de anúncios do Mercado Livre Brasil e filtros locais.

A disponibilidade de /sites/MLB/search depende das permissões da API.
Os dados retornados não são links de afiliado do usuário.
"""
import math
import re
from urllib.parse import quote

SITE_ID = 'MLB'
MAX_RESULTS = 50
SORT_OPTIONS = ('Relevância', 'Menor preço', 'Maior preço', 'Maior desconto')


def search_params(query, category='', seller_id='', limit=MAX_RESULTS):
    query = re.sub(r'\s+', ' ', str(query or '')).strip()
    if not 2 <= len(query) <= 120:
        raise ValueError('Informe pelo menos 2 e no máximo 120 caracteres na busca.')
    if not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError('Limite de resultados inválido.')
    params = {'q': query, 'limit': limit, 'offset': 0}
    if category:
        if not re.fullmatch(r'MLB\d{2,10}', str(category)):
            raise ValueError('Categoria inválida.')
        params['category'] = category
    if seller_id:
        if not re.fullmatch(r'\d{1,15}', str(seller_id)):
            raise ValueError('O código do vendedor deve conter apenas números.')
        params['seller_id'] = str(seller_id)
    return params


def normalize_listing(item):
    if not isinstance(item, dict):
        return None
    item_id = str(item.get('id') or '')
    if not re.fullmatch(r'MLB\d{7,15}', item_id):
        return None
    if item.get('currency_id') not in (None, 'BRL'):
        return None
    if item.get('status') not in (None, 'active'):
        return None
    try:
        price = float(item['price'])
        if not math.isfinite(price) or price <= 0:
            return None
        previous = item.get('original_price')
        previous = float(previous) if previous is not None else None
        if previous is not None and (not math.isfinite(previous) or previous <= price):
            previous = None
    except (TypeError, KeyError, ValueError, OverflowError):
        return None
    link = str(item.get('permalink') or '')
    if not link.startswith('https://'):
        link = ''
    image = str(item.get('thumbnail') or '')
    if image.startswith('http://'):
        image = 'https://' + image[len('http://'):]
    if not image.startswith('https://'):
        image = ''
    seller = item.get('seller') or {}
    shipping = item.get('shipping') or {}
    discount = round((previous-price) * 100/previous) if previous else 0
    return {
        'item_id': item_id,
        'title': str(item.get('title') or item_id).strip()[:220],
        'price': price,
        'original_price': previous,
        'discount': max(0, discount),
        'image_url': image,
        'permalink': link,
        'category_id': str(item.get('category_id') or ''),
        'seller_id': str(seller.get('id') or ''),
        'condition': str(item.get('condition') or ''),
        'free_shipping': bool(shipping.get('free_shipping')),
        'source': 'mercado_livre_search',
        'affiliate_url': '',
    }


def filter_listings(items, min_price=0, max_price=0, min_discount=0,
                    free_shipping=False, condition='Todos', order='Relevância'):
    if order not in SORT_OPTIONS:
        raise ValueError('Ordenação inválida.')
    if condition not in ('Todos', 'Novos', 'Usados'):
        raise ValueError('Condição inválida.')
    if min_price < 0 or max_price < 0 or (max_price and max_price < min_price):
        raise ValueError('Faixa de preços inválida.')
    if not 0 <= min_discount <= 100:
        raise ValueError('Desconto inválido.')
    normalized = [x for item in items if (x := normalize_listing(item))]
    results = [p for p in normalized
               if p['price'] >= min_price
               and (not max_price or p['price'] <= max_price)
               and p['discount'] >= min_discount
               and (not free_shipping or p['free_shipping'])
               and (condition == 'Todos' or p['condition'] == ('new' if condition == 'Novos' else 'used'))]
    if order == 'Menor preço':
        results.sort(key=lambda x: x['price'])
    elif order == 'Maior preço':
        results.sort(key=lambda x: -x['price'])
    elif order == 'Maior desconto':
        results.sort(key=lambda x: (-x['discount'], x['price']))
    return results


def marketplace_search_url(query):
    query = re.sub(r'\s+', ' ', str(query or '')).strip()
    return 'https://www.mercadolivre.com.br/jm/search?as_word=' + quote(query, safe='')


def catalog_winner_listing(product):
    """Converte somente uma oferta vencedora real; nunca inventa desconto ou comissão."""
    if not isinstance(product, dict) or product.get('status') != 'active':
        return None
    winner = product.get('buy_box_winner')
    if not isinstance(winner, dict) or str(winner.get('currency_id')) != 'BRL':
        return None
    pictures = product.get('pictures') or []
    picture = pictures[0] if pictures and isinstance(pictures[0], dict) else {}
    item = {
        'id': winner.get('item_id'),
        'title': product.get('name') or product.get('family_name'),
        'price': winner.get('price'),
        'original_price': None,
        'currency_id': winner.get('currency_id'),
        'status': 'active',
        'category_id': winner.get('category_id'),
        'seller': {'id': winner.get('seller_id')},
        'shipping': winner.get('shipping') or {},
        'condition': 'new',
        'thumbnail': picture.get('url') or picture.get('secure_url') or '',
        'permalink': product.get('permalink') or '',
    }
    return item if normalize_listing(item) else None
