import sys
import subprocess
import os

def scrape_to_html_with_firecrawl_cli(target_url: str, output_file: str = "scraped_product.html") -> bool:
    """
    Firecrawl CLI (`firecrawl scrape`)를 실행하여 웹페이지의 HTML을 직접 내보냅니다.
    추출된 HTML 파일은 이전 파이썬 분석 코드(extract_vendor_item.py)와 직접 호환됩니다.
    """
    # 출력 파일 확장자가 .html이 아니면 자동 보정
    if not output_file.endswith(".html"):
        output_file = f"{output_file}.html"

    # Firecrawl CLI 명령어 구성 (-f html로 지정하여 순수 HTML 추출)
    cmd = [
        "firecrawl",
        "scrape",
        target_url,
        "-f", "html",
        "--wait-for", "3000",
        "-o", output_file
    ]
    
    print(f"[Info] Firecrawl CLI 명령어 구동 준비:")
    print(f"       Command: {' '.join(cmd)}")
    
    try:
        # CLI 프로세스 실행
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[Success] HTML 스크랩 완료! 저장 파일: {output_file}")
        if result.stdout:
            print(f"[CLI Output]\n{result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[Error] Firecrawl CLI 실행 실패 (Exit Code: {e.returncode})")
        if e.stderr:
            print(f"[Stderr]\n{e.stderr}")
        return False

    except FileNotFoundError:
        print("[Error] 'firecrawl' CLI를 찾을 수 없습니다. 전역 설치(npm i -g firecrawl-cli)를 확인해 주세요.")
        return False

if __name__ == "__main__":
    # 기본 쿠팡 상품 URL 및 기본 출력 HTML 파일명 설정
    default_url = "https://www.coupang.com/vp/products/9096188506?itemId=26736785159&vendorItemId=93681363718&q=%EC%A7%9C%EC%9A%94%EC%A7%9C%EC%9A%94&searchId=bed6872a11730168&sourceType=search&itemsCount=60&searchRank=2&rank=2&traceId=mrzx0oe4"
    
    url_arg = sys.argv[1] if len(sys.argv) > 1 else default_url
    output_arg = sys.argv[2] if len(sys.argv) > 2 else "scraped_product.html"
    
    scrape_to_html_with_firecrawl_cli(url_arg, output_arg)
