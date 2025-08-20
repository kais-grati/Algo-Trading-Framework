from data.data_provider import BaseDataProvider, CSVDataProvider, BinanceDataProvider
from core.base_strategy import BaseStrategy
from core.position_manager import BasePositionManager
import asyncio, os
from dotenv import load_dotenv
from data.base_candle import BaseCandle

load_dotenv()

pm = BasePositionManager()


class Printer(BaseStrategy):
    signal = 1
    def update(self, candle: BaseCandle) -> None:
        print(candle)
        if self.signal < 3:
            pm.long(candle, 100)
            self.signal += 1
        else:
            pm.close(candle)
            print(pm.get_unrealized_pnl(candle))
            

provider = CSVDataProvider("xrp_5m_last_year.csv", 5)
# provider = BinanceDataProvider('XRPUSDT', '1m', key=os.getenv('API_KEY'), secret=os.getenv('API_SECRET'))

Printer(provider)

async def main():
    await provider.run() 

if __name__ == "__main__":
    asyncio.run(main())