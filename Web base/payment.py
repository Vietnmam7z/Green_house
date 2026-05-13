import os
import time
import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

partner_code = os.getenv("MOMO_PARTNER_CODE")
access_key = os.getenv("MOMO_ACCESS_KEY")
secret_key = os.getenv("MOMO_SECRET_KEY")

BASE_URL = "https://test-payment.momo.vn"
FRONTEND_URL = "http://localhost:5500"
BACKEND_URL = "http://localhost:5000"


def create_momo_payment(amount):
    order_id = str(int(time.time() * 1000))
    request_id = order_id
    order_info = "Thanh toan test"
    redirect_url = f"{FRONTEND_URL}/payment-result"
    ipn_url = f"{BACKEND_URL}/ipn"

    raw_signature = (
        f"accessKey={access_key}"
        f"&amount={amount}"
        f"&extraData="
        f"&ipnUrl={ipn_url}"
        f"&orderId={order_id}"
        f"&orderInfo={order_info}"
        f"&partnerCode={partner_code}"
        f"&redirectUrl={redirect_url}"
        f"&requestId={request_id}"
        f"&requestType=captureWallet"
    )

    signature = hmac.new(
        secret_key.encode("utf-8"),
        raw_signature.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    body = {
        "partnerCode": partner_code,
        "accessKey": access_key,
        "requestId": request_id,
        "amount": str(amount),
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "extraData": "",
        "requestType": "captureWallet",
        "signature": signature,
        "lang": "vi"
    }

    response = requests.post(
        f"{BASE_URL}/v2/gateway/api/create",
        json=body
    )

    return response.json(), order_id, request_id


def query_momo_payment(order_id):
    request_id = order_id

    raw_signature = (
        f"accessKey={access_key}"
        f"&orderId={order_id}"
        f"&partnerCode={partner_code}"
        f"&requestId={request_id}"
    )

    signature = hmac.new(
        secret_key.encode("utf-8"),
        raw_signature.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    body = {
        "partnerCode": partner_code,
        "requestId": request_id,
        "orderId": order_id,
        "signature": signature,
        "lang": "vi"
    }

    response = requests.post(
        f"{BASE_URL}/v2/gateway/api/query",
        json=body
    )

    return response.json()
