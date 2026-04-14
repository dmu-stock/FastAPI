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
    avgPrice : Decimal
    quantity : Decimal
    totalAmount : str
    type: StockType
    
class RagMyStockRequestDto(BaseModel):
    memberStock:List[StockInfo]
    newsForRag:List[str]