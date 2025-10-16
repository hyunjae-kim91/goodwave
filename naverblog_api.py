import os
import sys
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET_KEY = os.getenv("NAVER_SECRET_KEY")

client_id = NAVER_CLIENT_ID
client_secret = NAVER_SECRET_KEY

def get_naver_blog_api(query: str):
    encText = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=100&start=1&sort=sim" # JSON 결과
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id",client_id)
    request.add_header("X-Naver-Client-Secret",client_secret)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if(rescode==200):
        response_body = response.read()
    else:
        print("Error Code:" + rescode)
    return json.loads(response_body.decode('utf-8'))

if __name__ == "__main__":
    response = get_naver_blog_api("일정관리")
    item_list = response.get('items')
    print(item_list)

### 답변 예시
### [
#   {
#       'title': '후순위아파트담보대출 DSR 예외 추가 한도 <b>일정 관리</b> 후기', 
#       'link': 'https://blog.naver.com/hot910918/223991195327', 
#       'description': '나누어 <b>관리</b>했어요. 부모님 집 보수에는 3천만원을, 재고 선결제에는 4천만원대 초반을 배정했고, 생활비 방어를 위한 소액 완충자금을 따로 두었어요. 집행과 동시에 자동이체 <b>일정</b>을 급여일 이후로 밀어 단기... ', 
#       'bloggername': '또이와 모리,포로리의 달달한♥', 
#       'bloggerlink': 'blog.naver.com/hot910918', 
#       'postdate': '20250901'
#   }
# ]

