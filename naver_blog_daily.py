import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import json

def get_naver_blog_visitors(api_url: str) -> str:
    """
    Naver Blog visitor API(XML)를 호출하고
    { "YYYY-MM-DD": 방문자수, ... } 형태의 JSON string 반환
    """
    resp = requests.get(api_url)
    resp.raise_for_status()
    text = resp.text.strip()

    root = ET.fromstring(text)

    result = {}
    for vc in root.findall("visitorcnt"):
        date_str = vc.attrib.get("id")
        cnt = vc.attrib.get("cnt")

        if date_str and cnt:
            try:
                dt = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
                result[dt] = int(cnt)
            except Exception:
                continue

    # JSON 변환 (indent는 보기 좋게 출력용)
    return json.dumps(result, ensure_ascii=False, indent=2)


# === 테스트 ===
if __name__ == "__main__":
    url = "https://blog.naver.com/NVisitorgp4Ajax.nhn?blogId=ybgenius"
    print(get_naver_blog_visitors(url))

