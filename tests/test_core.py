from ofertas_core import item_id, affiliate_format, message, load_csv, dump_csv

def test_ids():
    assert item_id('MLB1234567890') == 'MLB1234567890'
    assert item_id('https://produto.mercadolivre.com.br/MLB-1234567890-exemplo-_JM') == 'MLB1234567890'
    assert item_id('https://evil.example/MLB1234567890') is None
    assert item_id('https://www.mercadolivre.com.br/p/MLB1234567890') is None

def test_links():
    assert affiliate_format('https://meli.la/abcDEF23')
    assert not affiliate_format('https://mercadolivre.com.br/MLB-1234567890-produto')
    assert not affiliate_format('https://meli.la.evil.test/path')
    assert not affiliate_format('http://meli.la/abcDEF23')

def test_message():
    p={'item_id':'MLB1234567890','title':'Creatina 300g','price':79.9,'original_price':99.9,'affiliate_url':'https://meli.la/abcDEF23'}
    assert 'https://meli.la/abcDEF23' in message(p)
    assert '20% OFF' in message(p)
    p['affiliate_url']='https://mercadolivre.com.br/MLB-1234567890-produto'
    try:message(p)
    except ValueError:pass
    else:assert False,'deve bloquear link comum'

def test_csv_roundtrip():
    rows='item_id,title,price,original_price,affiliate_url\nMLB1234567890,Creatina,79.90,100,https://meli.la/abcDEF23\n'
    data,count,errors=load_csv(rows)
    assert count==1 and not errors
    data2,count2,errors2=load_csv(dump_csv(data))
    assert data2==data

def test_csv_bad_link():
    data,count,errors=load_csv('item_id,title,affiliate_url\nMLB1234567890,Teste,https://google.com/a\n')
    assert count==0 and errors