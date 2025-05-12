import time
import hmac
import hashlib
import base64
import requests
import json
import os
import logging
from dotenv import load_dotenv

load_dotenv()


def feishu(title: str, post_content_elements: list) -> dict:
    """
    发送飞书机器人消息

    Args:
        webhook_url: 飞书机器人的webhook地址 (注：此参数已通过环境变量读取，实际未使用)
        secret: 安全设置中的签名校验密钥 (注：此参数已通过环境变量读取，实际未使用)
        title: 消息标题
        post_content_elements: 消息内容，为一个列表，符合飞书富文本 post 类型中 content.post.zh_cn.content 的结构。
                             例如: [[{"tag": "text", "text": "第一行内容"}], [{"tag": "a", "text": "链接", "href": "https://www.feishu.cn"}]]

    Returns:
        dict: 接口返回结果
    """
    # 环境变量
    FEISHU_BOT_URL = os.environ.get("FEISHU_BOT_URL")
    FEISHU_BOT_SECRET = os.environ.get("FEISHU_BOT_SECRET")

    feishu_webhook = FEISHU_BOT_URL
    feishu_secret = FEISHU_BOT_SECRET
    timestamp = str(int(time.time()))

    # 计算签名
    string_to_sign = f"{timestamp}\n{feishu_secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")

    # 构建请求头
    headers = {"Content-Type": "application/json"}

    # 构建消息内容
    msg = {
        "timestamp": timestamp,
        "sign": sign,
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": post_content_elements,
                }
            }
        },
    }

    # 发送请求
    try:
        if not isinstance(feishu_webhook, str):
            logging.error(f"飞书webhook未配置")
            return {"error": "飞书webhook未配置"}
        response = requests.post(feishu_webhook, headers=headers, data=json.dumps(msg))
        logging.info(f"飞书发送通知消息成功🎉\n{response.json()}")
        return response.json()
    except Exception as e:
        logging.error(f"飞书发送通知消息失败😞\n{e}")
        return {"error": str(e)}
