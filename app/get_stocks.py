import pandas_datareader.data as web
import pandas as pd

def get_all_us_stocks():
    print("==== 미국 전 종목 리스트 불러오는 중... (잠시만 기다려주세요) ====")
    
    # 나스닥(NASDAQ)에서 제공하는 전체 종목 리스트를 가져옵니다.
    # 여기에는 NYSE, AMEX 종목도 포함되어 있어요!
    try:
        df = web.get_data_nasdaqsymbols()
        
        # 필요한 컬럼만 추출 (Symbol: 티커, Security Name: 종목명)
        # 지호님 프로젝트 형식에 맞게 'code', 'name'으로 이름을 바꿀게요.
        full_list = df[['Symbol', 'Security Name']].copy()
        full_list.columns = ['code', 'name']
        
        # ETF나 불필요한 테스트 종목 제외 (옵션)
        full_list = full_list[full_list['code'].str.contains('\$') == False]
        
        # CSV 파일로 저장 (스프링에서 읽기 좋게 utf-8로!)
        full_list.to_csv('us_full_stocks.csv', index=False, encoding='utf-8-sig')
        
        print(f"==== 완료! 총 {len(full_list)}개의 종목을 찾았습니다. ====")
        print("파일 이름: us_full_stocks.csv")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    get_all_us_stocks()