from pydantic import BaseModel
from typing import List
from typing import Optional
from decimal import Decimal
from enum import Enum

class NewsAnalysisRequestDto(BaseModel):
    query: str
    urls: List[str]

class StockAnalysisRequestDto(BaseModel):
    stockCode: Optional[str] = None
    ticker: Optional[str] = None

class StockType(str, Enum):
    KOREA = "KOREA"
    USA = "USA"
    UNKNOWN = "UNKNOWN"

class StockInfo(BaseModel):
    stockCode : str
    avgPrice : float
    quantity : float
    totalAmount : float
    type: StockType
    currentPrice:float
    changePrice:float
    changeRate:float
    marketCap:float
    
class RagMyStockRequestDto(BaseModel):
    memberStock:List[StockInfo]
    