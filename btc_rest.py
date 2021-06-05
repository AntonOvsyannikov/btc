import asyncio
from decimal import Decimal
from typing import Optional, cast, Any

import ccxt
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from starlette.testclient import TestClient
from typing_extensions import Literal

SYMBOL = 'BTC/USDT'

exchange = ccxt.binance({'enableRateLimit': True})

exchange.load_markets()
market = exchange.market(SYMBOL)

amount_min = market['limits']['amount']['min']
amount_max = market['limits']['amount']['max']

# orderbook = exchange.fetch_order_book(SYMBOL)
# print(SYMBOL)
# print('bids - покупатели', orderbook['bids'][0], orderbook['bids'][1])
# print('asks - продавцы  ', orderbook['asks'][0], orderbook['asks'][1])


Side = Literal['BUY', 'SELL']


def get_usdt_amount(btc_amount: float, side: Side):
    if btc_amount < amount_min or btc_amount > amount_max:
        raise ValueError("This amount can not be exchanged")

    btc_amount = Decimal(exchange.amount_to_precision(SYMBOL, btc_amount))
    orderbook = exchange.fetch_order_book(SYMBOL)

    usdt_amount = 0
    for price, amount in orderbook['asks' if side == 'BUY' else 'bids']:
        price = Decimal(str(price))
        amount = Decimal(str(amount))

        step_amount = amount if amount <= btc_amount else btc_amount

        usdt_amount += step_amount * price

        btc_amount -= step_amount
        if not btc_amount: break
    else:
        raise ValueError("No enough orders in orderbook")

    return float(exchange.price_to_precision(SYMBOL, usdt_amount))


# print(get_usdt_amount(1, 'BUY'))
# print(get_usdt_amount(1, 'SELL'))


class Trade(BaseModel):
    amount: Optional[float]
    error: Optional[str]


app = FastAPI()


@app.get('/spendings', response_model=Trade, response_model_exclude_unset=True)
async def get_spendings(amount: float, side: Side) -> Trade:
    """ Returns amount of USDT to spend (when BUY) or receive (when SELL) for given amount of BTC. """
    try:
        return Trade(
            amount=await asyncio.get_event_loop().run_in_executor(None, get_usdt_amount, amount, side)
        )
    except Exception as e:
        return Trade(
            error=str(e)
        )


# cli = TestClient(app=app)
# print(cli.get('/spendings?amount=0.01&side=SELL').json())
# assert 'amount' in cli.get('/spendings?amount=0.01&side=SELL').json()
# assert 'error' in cli.get('/spendings?amount=100000&side=SELL').json()

print("Open browser and check the following examples")
print("http://127.0.0.1:20000/spendings?amount=0.01&side=SELL")
print("http://127.0.0.1:20000/spendings?amount=1000000&side=BUY")
print("Or use Swagger UI")
print("http://127.0.0.1:20000/docs")

uvicorn.run(cast(Any, app), host='0.0.0.0', port=20000)
