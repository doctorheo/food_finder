import os
import sys
import time
import uuid
import base64
import requests
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드 (.env 파일은 열어보지 않는 보안 지침 준수)
load_dotenv()

CLOVA_OCR_SECRET = os.getenv("CLOVA_OCR_SECRET")
CLOVA_OCR_INVOKE_URL = os.getenv("CLOVA_OCR_INVOKE_URL")

def request_clova_ocr(image_input: str, max_retries: int = 3) -> str:
    """
    네이버 Clova OCR V1 API를 호출하여 이미지(URL 또는 파일 경로)의 글씨를 추출합니다.
    
    [핵심 타임아웃 해결 원인]
    1. Invoke URL이 http:// 로 되어 있을 경우 네이버 API Gateway(port 80)에서 무한 대기가 발생합니다.
       이를 https:// 로 강제 전환하여 TLS/SSL (port 443)로 전송합니다.
    2. Coupang CDN 차단 방지를 위해 로컬에서 이미지를 다운로드 후 Base64 'data'로 전달합니다.
    """
    if not CLOVA_OCR_SECRET or not CLOVA_OCR_INVOKE_URL:
        raise ValueError("환경 변수(CLOVA_OCR_SECRET, CLOVA_OCR_INVOKE_URL)가 .env 파일에 설정되어 있어야 합니다.")

    # HTTP 요청 무한 대기(port 80 timeout) 방지를 위해 HTTPS 프로토콜로 강제 전환
    invoke_url = CLOVA_OCR_INVOKE_URL.strip()
    if invoke_url.startswith("http://"):
        invoke_url = "https://" + invoke_url[len("http://"):]

    headers = {
        "X-OCR-SECRET": CLOVA_OCR_SECRET,
        "Content-Type": "application/json"
    }

    base64_data = None
    url_target = None
    fmt = "jpg"

    # 1. 로컬 이미지 파일인 경우
    if os.path.exists(image_input):
        ext = os.path.splitext(image_input)[1].replace(".", "").lower() or "jpg"
        fmt = "jpg" if ext in ["jpg", "jpeg"] else ext
        with open(image_input, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")

    # 2. 웹 이미지 URL인 경우 (로컬에서 1차 다운로드 후 base64 전환)
    elif image_input.startswith("http://") or image_input.startswith("https://"):
        ext = os.path.splitext(image_input.split("?")[0])[1].replace(".", "").lower() or "jpg"
        fmt = "jpg" if ext in ["jpg", "jpeg"] else ext
        
        req_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            download_res = requests.get(image_input, headers=req_headers, timeout=10)
            if download_res.status_code == 200:
                base64_data = base64.b64encode(download_res.content).decode("utf-8")
            else:
                url_target = image_input
        except Exception:
            url_target = image_input
    else:
        url_target = image_input

    # 이미지 전송 객체 구성 (data 우선, data가 없으면 url)
    image_obj = {
        "format": fmt if fmt in ["jpg", "png", "pdf", "tiff"] else "jpg",
        "name": "medium"
    }
    if base64_data:
        image_obj["data"] = base64_data
    elif url_target:
        image_obj["url"] = url_target

    # Clova OCR 공식 가이드 V1 Payload
    payload = {
        "images": [image_obj],
        "lang": "ko",
        "requestId": str(uuid.uuid4()),
        "resultType": "string",
        "timestamp": int(time.time() * 1000),
        "version": "V1"
    }

    # 타임아웃 및 재시도 로직 (HTTPS 사용으로 즉각 응답)
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                invoke_url, 
                headers=headers, 
                json=payload, 
                timeout=(10, 30)
            )
            response.raise_for_status()
            res_json = response.json()
            
            extracted_text_list = []
            for img_res in res_json.get("images", []):
                for field in img_res.get("fields", []):
                    text = field.get("inferText", "")
                    if text:
                        extracted_text_list.append(text)
                        
            return " ".join(extracted_text_list)

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
            if attempt < max_retries:
                wait_time = attempt * 2
                print(f"   ⚠️ Clova OCR 응답 지연 발생 ({attempt}/{max_retries}차 시도). {wait_time}초 후 재시도...")
                time.sleep(wait_time)
            else:
                raise err

def filter_images_by_keyword(image_inputs: list[str], target_keyword: str = "원재료명"):
    """
    입력받은 이미지 목록을 Naver Clova OCR V1 API로 분석하고,
    '원재료명' (또는 '원재료') 키워드가 포함된 이미지와 추출 텍스트를 출력합니다.
    """
    if not image_inputs:
        print("[Error] 분석할 이미지 URL 또는 파일 경로가 입력되지 않았습니다.")
        return

    print(f"\n========================================================")
    print(f"🔍 총 {len(image_inputs)}개 이미지에 대한 Naver Clova OCR (V1) 분석 시작")
    print(f"========================================================\n")

    matched_results = []

    for idx, item_input in enumerate(image_inputs, start=1):
        print(f"[{idx}/{len(image_inputs)}] OCR 분석 요청: {item_input}")
        try:
            extracted_text = request_clova_ocr(item_input)
            print(f"   📝 추출된 글씨: {extracted_text[:120]}..." if len(extracted_text) > 120 else f"   📝 추출된 글씨: {extracted_text}")
            
            if target_keyword in extracted_text or "원재료" in extracted_text:
                print(f"   ✅ '{target_keyword}' 글씨 발견!")
                matched_results.append({
                    "index": idx,
                    "target": item_input,
                    "text": extracted_text
                })
            else:
                print(f"   ❌ '{target_keyword}' 미포함")
            print("-" * 60)

        except Exception as e:
            print(f"   ⚠️ OCR 분석 오류: {e}")
            print("-" * 60)

    print("\n" + "=" * 60)
    print(f"🎉 ['{target_keyword}'] 글씨를 포함하는 최종 이미지 결과 (총 {len(matched_results)}개)")
    print("=" * 60)

    if matched_results:
        for res in matched_results:
            print(f"\n🖼️ [이미지 #{res['index']}]")
            print(f"🔗 Target: {res['target']}")
            print(f"📄 전체 글씨 텍스트:\n{res['text']}\n")
    else:
        print(f"⚠️ '{target_keyword}' 글씨를 포함하는 이미지를 찾지 못했습니다.")

if __name__ == "__main__":
    inputs = sys.argv[1:]
    if not inputs:
        print("[Notice] 사용법: python ocr_vendor_images.py <이미지_URL_또는_파일_1> <이미지_URL_또는_파일_2> ...")
    else:
        filter_images_by_keyword(inputs, target_keyword="원재료명")
