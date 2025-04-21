#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from dotenv import load_dotenv
import sys
import json

# 환경 변수 로드
load_dotenv()

# MCP 서버 생성
mcp = FastMCP("Price Monitor")

# def get_db_connection():
#     """데이터베이스 연결을 생성합니다."""
#     return psycopg2.connect(
#         host=os.getenv("DB_HOST"),
#         port=os.getenv("DB_PORT"),
#         dbname=os.getenv("DB_NAME"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         cursor_factory=RealDictCursor
#     )

# DB 연결 도구
@mcp.tool()
def get_db_price(product_code: str) -> dict:
    """DB에서 상품의 기준 가격을 조회합니다."""
    return {
        "success": True,
        "price": 29000,
        "updated_at": '2025-04-20'
    }
    # try:
    #     with get_db_connection() as conn:
    #         query = """
    #             SELECT 
    #                 product_cd as product_code,
    #                 price,
    #                 updated_at::text
    #             FROM product.product_prices 
    #             WHERE product_cd = %s
    #         """
    #         with conn.cursor() as cur:
    #             cur.execute(query, (product_code,))
    #             result = cur.fetchone()
                
    #             if result:
    #                 return {
    #                     "success": True,
    #                     "price": result["price"],
    #                     "updated_at": result["updated_at"]
    #                 }
    #             return {
    #                 "success": False,
    #                 "message": "가격 정보를 찾을 수 없습니다."
    #             }
    # except Exception as e:
    #     return {
    #         "success": False,
    #         "message": f"DB 조회 중 오류 발생: {str(e)}"
    #     }

# Firecrawl import 및 인스턴스 생성 try/except로 감싸기
try:
    from firecrawl import FirecrawlApp, JsonConfig
    print("[크롤러] Firecrawl import 성공", file=sys.stderr)
    FIRECRAWL_API_KEY = "fc-175cdecea42d438eb340fd4b96293591"
    firecrawl_client = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    print("[크롤러] FirecrawlApp 인스턴스 생성 성공", file=sys.stderr)
except Exception as e:
    print(f"[크롤러] Firecrawl import/초기화 실패: {e}", file=sys.stderr)
    firecrawl_client = None

@mcp.tool()
def crawl_gmarket_price(product_code: str) -> dict:
    """G마켓 크롤링 도구 """
    print("[크롤러] 함수 진입", file=sys.stderr)
    try:
        print(f"[크롤러] G마켓 크롤링 시작: product_code={product_code}", file=sys.stderr)
        url = f"https://www.gmarket.co.kr/n/search?keyword={product_code}&s=1"
        print(f"[크롤러] 검색 URL 생성: {url}", file=sys.stderr)
        json_config = JsonConfig(
            extractionSchema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number"},
                        "seller": {"type": "string"},
                        "url": {"type": "string"},
                        "title": {"type": "string"}
                    },
                    "required": ["price", "seller", "url"]
                }
            },
            mode="llm-extraction",
            prompt='''\n검색 결과 페이지에서 각 상품의 정보를 추출해주세요:\n- price: 판매가격 (숫자만)\n- seller: 판매자명\n- url: 상품 상세 페이지 링크\n- title: 상품명 (있는 경우)\n''',
            pageOptions={
                "onlyMainContent": True,
                "timeout": 180000  # 60초 타임아웃
            }
        )
        print(f"[크롤러] Firecrawl 크롤링 시작", file=sys.stderr)
        if firecrawl_client is None:
            print("[크롤러] firecrawl_client가 None입니다. 초기화 실패", file=sys.stderr)
            return {
                "success": False,
                "message": "Firecrawl 클라이언트 초기화 실패"
            }
        result = firecrawl_client.scrape_url(
            url,
            formats=["json"],
            json_options=json_config
        )
        
        print(f"[크롤러] Firecrawl 크롤링 완료, 결과: {result}", file=sys.stderr)
        print(f"[크롤러] Firecrawl 결과 전체: {result.json}", file=sys.stderr)
        if not result or not result.json:
            print(f"[크롤러] 크롤링 결과 없음", file=sys.stderr)
            return {
                "success": False,
                "message": "크롤링 결과가 없습니다."
            }
        # 결과 타입에 따라 offers 추출 방식 분기
        if isinstance(result.json, list):
            offers = result.json
        elif isinstance(result.json, dict):
            offers = result.json.get('products', [])
        else:
            offers = []
        
        print(f"[크롤러] offers 추출: {offers}", file=sys.stderr)
        if not offers:
            print(f"[크롤러] 상품 정보 없음", file=sys.stderr)
            return {
                "success": False,
                "message": "상품 정보를 찾을 수 없습니다."
            }
        sorted_offers = sorted(offers, key=lambda x: x["price"])
        print(f"[크롤러] 가격순 정렬 완료", file=sys.stderr)
        return {
            "success": True,
            "data":  json.dumps(sorted_offers)
        }
    except Exception as e:
        print(f"[크롤러] 예외 발생: {e}", file=sys.stderr)
        return {
            "success": False,
            "message": f"크롤링 중 오류 발생: {str(e)}"
        }

# Slack 알림 도구
@mcp.tool()
def send_slack_alert(message: dict) -> dict:
    """Slack으로 가격 하락 알림을 전송합니다."""
    try:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("Slack webhook URL이 설정되지 않았습니다.")
            
        formatted_message = (
            f"📉 가격 하락 감지!\n"
            f"상품명: {message['product_name']}\n"
            f"DB 가격: {message['db_price']:,}원\n"
            f"현재가격: {message['current_price']:,}원\n"
            f"가격차이: {message['price_diff']:,}원 (-{message['discount_rate']:.1f}%)\n"
            f"판매자: {message['seller']}\n"
            f"URL: {message['url']}\n"
            f"감지시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        response = requests.post(
            webhook_url,
            json={"text": formatted_message}
        )
        response.raise_for_status()
        
        return {
            "success": True,
            "message": "알림 전송 완료"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"알림 전송 중 오류 발생: {str(e)}"
        }

# 가격 모니터링 프롬프트
@mcp.prompt()
def monitor_price(product_code: str) -> str:
    """상품 가격을 모니터링하고 필요시 알림을 보내는 프롬프트"""
    return f"""
    다음 단계를 수행하여 상품 코드 {product_code}의 가격을 모니터링하세요:
    
    1. get_db_price 도구를 사용하여 DB에서 기준 가격을 조회하세요.
    2. crawl_gmarket_price 도구를 사용하여 현재 판매 가격을 확인하세요.
    3. 현재 판매 가격이 DB 가격보다 낮은 경우:
       - 가격 차이와 할인율을 계산하세요
       - send_slack_alert 도구를 사용하여 알림을 전송하세요
    4. 결과를 요약하여 보고하세요.
    
    오류가 발생하면 적절히 처리하고 사용자에게 알려주세요.
    """

@mcp.tool()
def monitor_price_workflow(product_code: str) -> dict:
    """상품 가격 모니터링 전체 자동 워크플로우"""
    # 1. DB 가격 조회
    db_result = get_db_price(product_code)
    if not db_result.get("success"):
        return {"success": False, "step": "get_db_price", "message": db_result.get("message", "DB 조회 실패")}

    db_price = db_result["price"]

    # 2. G마켓 가격 크롤링
    crawl_result = crawl_gmarket_price(product_code)
    if not crawl_result.get("success"):
        return {"success": False, "step": "crawl_gmarket_price", "message": crawl_result.get("message", "크롤링 실패")}

    # 크롤링 결과에서 최저가 상품 추출
    import json
    offers = []
    try:
        offers = json.loads(crawl_result["data"])
    except Exception as e:
        return {"success": False, "step": "parse_crawl_result", "message": f"크롤링 결과 파싱 실패: {e}"}

    if not offers:
        return {"success": False, "step": "crawl_gmarket_price", "message": "상품 정보 없음"}

    best_offer = offers[0]
    current_price = best_offer["price"]
    seller = best_offer["seller"]
    url = best_offer["url"]
    title = best_offer.get("title", "")

    # 3. 가격 비교 및 슬랙 알림
    price_diff = db_price - current_price
    discount_rate = (price_diff / db_price) * 100 if db_price else 0

    alert_result = None
    if current_price < db_price:
        alert_message = {
            "product_name": title,
            "db_price": db_price,
            "current_price": current_price,
            "price_diff": price_diff,
            "discount_rate": discount_rate,
            "seller": seller,
            "url": url
        }
        alert_result = send_slack_alert(alert_message)

    # 4. 결과 요약
    return {
        "success": True,
        "db_price": db_price,
        "current_price": current_price,
        "price_diff": price_diff,
        "discount_rate": discount_rate,
        "seller": seller,
        "url": url,
        "product_name": title,
        "slack_alert_sent": bool(alert_result and alert_result.get("success")),
        "slack_alert_result": alert_result
    }

if __name__ == "__main__":
    mcp.run() 
    