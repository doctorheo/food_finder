import os
import sys
from bs4 import BeautifulSoup

def get_images_from_vendor_item(html_content: str) -> list[str]:
    """
    HTML 내용에서 지정된 CSS 셀렉터(vendor-item 상세 영역) 내부의 모든 이미지 URL을 추출합니다.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. 정밀한 지정 CSS 셀렉터
    target_selector = (
        "body > div:nth-child(5) > div > div.twc-flex.twc-max-w-full > main > "
        "div.product-btf-container.twc-pt-\\[10px\\] > div:nth-child(4) > "
        "div.product-detail-content.hide-overflow.product-detail-content-new > "
        "div.product-detail-content-inside > div"
    )
    
    container = soup.select_one(target_selector)
    
    # 2. 지정 셀렉터 미발견 시 범용 Fallback 셀렉터 적용
    if not container:
        fallback_selectors = [
            ".vendor-item",
            ".product-detail-content-new > .product-detail-content-inside > div",
            ".product-detail-content-inside > div",
            ".product-detail-content-inside"
        ]
        for sel in fallback_selectors:
            container = soup.select_one(sel)
            if container:
                break

    # 지정 영역이 없으면 전체 문서 탐색
    search_root = container if container else soup
    
    image_urls = []
    for img in search_root.find_all('img'):
        # src, data-src, lazy-src, data-original 등의 속성을 순서대로 체크
        src = (
            img.get('src') or 
            img.get('data-src') or 
            img.get('lazy-src') or 
            img.get('data-original')
        )
        if src:
            src = src.strip()
            # 프로토콜 상대 경로(//) 또는 상대 경로(/) 보정
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://www.coupang.com' + src
                
            # 중복 제거하며 순서 유지
            if src not in image_urls:
                image_urls.append(src)
                
    return image_urls

def print_vendor_item_images(file_path: str):
    """
    HTML 파일을 읽어 vendor-item 영역 내부의 이미지 URL들을 콘솔 화면에 출력합니다.
    """
    if not os.path.exists(file_path):
        print(f"[Error] 지정한 HTML 파일을 찾을 수 없습니다: {file_path}")
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    img_urls = get_images_from_vendor_item(html_content)
    
    print(f"\n=== vendor-item 영역 이미지 URL 목록 (총 {len(img_urls)}개) ===")
    for idx, url in enumerate(img_urls, start=1):
        print(f"[{idx}] {url}")

if __name__ == "__main__":
    # 명령행 인자로 파일 경로 지정 (기본값: extracted_vendor_item.html 또는 organica_juice.html)
    input_path = "extracted_vendor_item.html"
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    elif not os.path.exists(input_path) and os.path.exists("organica_juice.html"):
        input_path = "organica_juice.html"
        
    print_vendor_item_images(input_path)
