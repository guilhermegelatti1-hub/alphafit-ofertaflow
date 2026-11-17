import pytest
from market_search import search_params, normalize_listing, filter_listings, catalog_winner_listing, marketplace_search_url


def listing(id='MLB1234567890', **kwargs):
    data={'id':id,'title':'Tênis corrida','price':99.9,'original_price':149.9,
          'currency_id':'BRL','status':'active','shipping':{'free_shipping':True},
          'condition':'new','thumbnail':'http://http2.mlstatic.com/a.jpg',
          'permalink':'https://www.mercadolivre.com.br/item'}
    data.update(kwargs)
    return data


def test_query_input():
    assert search_params('creatina',category='MLB1234',seller_id='123')['category']=='MLB1234'
    for q in ('','a','x'*121):
        with pytest.raises(ValueError):
            search_params(q)
    with pytest.raises(ValueError):
        search_params('creatina',seller_id='invalid')


def test_normalizes_only_real_listings_without_affiliate_url():
    data=normalize_listing(listing())
    assert data['discount']==33
    assert data['image_url'].startswith('https://')
    assert data['affiliate_url']==''
    assert normalize_listing(listing(currency_id='USD')) is None
    assert normalize_listing(listing(price=float('nan'))) is None
    assert normalize_listing(listing(original_price=None))['discount']==0


def test_local_filters():
    items=[listing('MLB1234567890'),
           listing('MLB1234567891',price=50,original_price=None,
                   shipping={'free_shipping':False},condition='used'),
           listing('MLB1234567892',price=119,original_price=249)]
    discounted=filter_listings(items,min_discount=30,free_shipping=True,order='Maior desconto')
    assert [x['item_id'] for x in discounted]==['MLB1234567892','MLB1234567890']
    cheap=filter_listings(items,max_price=100,order='Menor preço')
    assert cheap[0]['price']==50
    assert len(filter_listings(items,condition='Usados'))==1
    with pytest.raises(ValueError):
        filter_listings(items,min_price=150,max_price=50)


def test_catalog_requires_actual_buybox():
    detail={'status':'active','name':'Whey protein',
            'permalink':'https://www.mercadolivre.com.br/produto/p/MLB123',
            'buy_box_winner':{'item_id':'MLB1234567890','currency_id':'BRL',
                              'price':89.90,'seller_id':12345}}
    winner=catalog_winner_listing(detail)
    assert normalize_listing(winner)['price']==89.90
    assert winner['original_price'] is None
    detail['buy_box_winner']=None
    assert catalog_winner_listing(detail) is None


def test_external_search_url_escapes_input():
    assert '%26' in marketplace_search_url('notebook & teclado')
