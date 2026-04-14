import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import io

def fix_and_filter_dart(input_path, output_path):
    try:
        #  Zip 파일로 열기
        with zipfile.ZipFile(input_path, 'r') as z:
            # 압축 파일 안에 들어있는 첫 번째 파일 이름을 가져옴
            filename = z.namelist()[0]
            with z.open(filename) as f:
                # 압축 해제된 데이터를 바로 XML로 파싱
                xml_content = f.read()
                root = ET.fromstring(xml_content)

        # 데이터 추출 (상장사만)
        data = []
        for item in root.findall('list'):
            stock_code = item.find('stock_code').text
            if stock_code and stock_code.strip():
                data.append({
                    'corp_code': item.find('corp_code').text,
                    'corp_name': item.find('corp_name').text,
                    'stock_code': stock_code.strip()
                })

        # CSV로 저장
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"상장사 {len(df)}건을 '{output_path}'에 저장했습니다.")

    except zipfile.BadZipFile:
        print("에러: 이 파일은 Zip 형식이 아닙니다. 이미 압축이 풀린 XML인지 확인하세요.")
    except Exception as e:
        print(f"에러 발생: {e}")

fix_and_filter_dart('CORPCODE.xml', 'CORPCODE_FILTERED.csv')