from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle

load_dotenv()

class Printer(BaseStrategy):
    def update(self, candle: BaseCandle) -> None:
        print(candle)

# provider = CSVDataProvider("xrp_5m_last_year.csv", 0.5)
provider = BinanceDataProvider('XRPUSDT', '1m', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

Printer(provider)

async def main():
    await provider.run() 

if __name__ == "__main__":
    asyncio.run(main())