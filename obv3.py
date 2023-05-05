import asyncio
import json
import time
import aiohttp
from aiohttp import web
import re
from typing import Any
import base64

ws_connections = {}
ws_url_b = "ws://58.39.114.244:25369"

async def main():
    app = web.Application()
    app.router.add_route("GET", "/ws", setup_connections)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 30004)
    print(f"WebSocket server is listening on 127.0.0.1:30004")
    await site.start()
    await asyncio.Future()  # Keep the server running indefinitely

async def setup_connections(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            # 如果 bot_id 不存在，就获取一下存起来
            if "a" not in ws_connections:
                print(ws)
                ws_connections["a"] = ws
                bot_id = extract_bot_id_from_message_a(msg.data)
                if bot_id:
                    ws_connections["a.bot_id"] = bot_id
                    asyncio.create_task(_setup_b( bot_id))
            # 如果 bot_id 已存在，就处理消息
            else:
                asyncio.create_task(recv_message_a(msg.data))
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print(f"WebSocket A connection closed: {ws.exception()}")
            break
    return ws

async def _setup_b(bot_id):
    async with aiohttp.ClientSession() as session:
        try:
            headers = {
                "User-Agent": "CQHttp/4.15.0",
                "X-Client-Role": "Universal",
                "X-Self-ID": str(bot_id)
            }
            async with session.ws_connect(ws_url_b, headers=headers) as ws_b:
                ws_connections["b"] = ws_b
                ws_connections["b.bot_id"] = bot_id
                message = {
                    "meta_event_type": "lifecycle",
                    "post_type": "meta_event",
                    "self_id": bot_id,
                    "sub_type": "connect",
                    "time": int(time.time())
                }
                await ws_b.send_str(json.dumps(message))
                async for msg in ws_b:
                    asyncio.create_task(recv_message_b(msg))
        except aiohttp.ClientError as e:
            print(f"Failed to connect websocket B: {e}")

def extract_bot_id_from_message_a(msg):
    message = json.loads(msg)
    if "CurrentQQ" in message:
        return message["CurrentQQ"]
    return None

async def recv_message_a(msg):
    message = json.loads(msg)
    print("从a收到了", message)
    transformed_message = transform_message_a_to_b(message)
    await send_to_ws_b(transformed_message)

async def recv_message_b(msg):
    message = json.loads(msg.data)
    print("从b收到了", message)
    await call_api_from_dict(message)

async def call_api_from_dict(message):
    async with aiohttp.ClientSession() as session:
        action = message['action']
        params = message.get('params', {})  # Use get() method to handle the case when 'params' key is not present
        botqq = params.get('botqq', ws_connections["a.bot_id"])
        url = f'http://127.0.0.1:8086/v1/LuaApiCaller?funcname=MagicCgiCmd&timeout=10&qq={botqq}'
        upload_url = f'http://127.0.0.1:8086/v1/upload?qq={botqq}'
        headers = {'Content-Type': 'application/json'}

        # Initialize variables
        content = ''
        at_uin_list_dicts = []
        images_dicts = []
        voice_dict = {}

        # Update action based on params keys
        if 'group_id' in params:
            action = 'send_group_msg'
        elif 'user_id' in params:
            action = 'send_private_msg'
            
        # Ensure that params['message'] is a list of segments
        message_segments = params['message']
        if isinstance(message_segments, dict):
            message_segments = [message_segments]

        # Process segments
        for segment in message_segments:
            if isinstance(segment, str):
                content += segment
                continue

            segment_type = segment['type']
            segment_data = segment['data']

            if segment_type == 'text':
                content += segment_data['text']
            elif segment_type == 'at':
                at_uin_list_dicts.append({"Uin": int(segment_data['qq'])})
            elif segment_type == 'image':
                img_data = segment_data['file']
                img_url = None  # Initialize the img_url variable here

                # Check if the image data is a local file path, URL, or base64-encoded string
                if img_data.startswith('file:///'):
                    img_path = img_data[8:]
                    with open(img_path, "rb") as f:
                        base64_encoded_str = base64.b64encode(f.read()).decode('utf-8')
                elif img_data.startswith('http://'):
                    img_url = img_data
                elif img_data.startswith('base64://'):
                    base64_encoded_str = img_data[9:]
                else:
                    print(f"Unsupported image data format: {img_data}")
                    continue

                # Upload the image
                command_id = 1 if action == "send_private_msg" else 2
                upload_payload = {
                    "CgiCmd": "PicUp.DataUp",
                    "CgiRequest": {
                        "CommandId": command_id,
                        "Base64Buf": base64_encoded_str
                    }
                }
                if img_url:
                    upload_payload["CgiRequest"]["FileUrl"] = img_url

                async with session.post(upload_url, headers=headers, json=upload_payload) as response:
                    response_json = await response.json()
                    response_json = {
                                    "FileId": response_json["ResponseData"]["FileId"],
                                    "FileMd5": response_json["ResponseData"]["FileMd5"],
                                    "FileSize": response_json["ResponseData"]["FileSize"]
                                   }
                    images_dicts.append(response_json)

        to_type = 1 if action == 'send_private_msg' else 2 if action == 'send_group_msg' else None
        if to_type is not None:
            to_uin_key = 'user_id' if action == 'send_private_msg' else 'group_id'
            to_uin = params[to_uin_key]
            payload = {
                "CgiCmd": "MessageSvc.PbSendMsg",
                "CgiRequest": {
                    "ToUin": int(to_uin),
                    "ToType": to_type,
                    "Content": content,
                    "AtUinLists": at_uin_list_dicts,
                    "Images": images_dicts,
                    **({"Voice": voice_dict} if voice_dict else {})
                }
            }
        else:
            print(f"Unsupported action: {action}")
            return

        print("提交的请求", payload)
        async with session.post(url, headers=headers, json=payload) as response:
            response_text = await response.text()
            print(response_text)


def transform_message_a_to_b(message: dict) -> dict:
    msg_head = message["CurrentPacket"]["EventData"]["MsgHead"]
    msg_body = message["CurrentPacket"]["EventData"]["MsgBody"]

    if msg_body is None:
        return None
    if msg_head["FromType"] == 1:
        message_type = "private"
    elif msg_head["FromType"] == 2:
        message_type = "group"
    else:
        return None

    sender = {
        "user_id": msg_head["SenderUin"],
        "nickname": msg_head["SenderNick"]
    }

    if message_type == "group":
        group_info = msg_head["GroupInfo"]
        sender.update({"card": group_info["GroupCard"]})
        raw_message = msg_body["Content"]
        at_uin_list = msg_body.get("AtUinLists", [])
        if at_uin_list is None:
            at_uin_list = []
        at_indices = []
        for at_uin in at_uin_list:
            at_indices.append((raw_message.find(f"@{at_uin['Nick']}"), f"[CQ:at,qq={at_uin['Uin']}]"))
            raw_message = raw_message.replace(f"@{at_uin['Nick']}", "")
        at_indices.sort(key=lambda x: x[0])
        images = msg_body.get("Images", [])
        if images is None:
            images = []
        message_segments = []
        cur_index = 0
        for at_index, at_code in at_indices:
            if at_index > cur_index:
                message_segments.append({"type": "text", "data": {"text": raw_message[cur_index:at_index]}})
            message_segments.append({"type": "at", "data": {"qq": at_code[8:-1]}})
            cur_index = at_index

        if cur_index < len(raw_message):
            message_segments.append({"type": "text", "data": {"text": raw_message[cur_index:]}})

        for image in images:
            message_segments.append({"type": "image", "data": {"file": f"{image['FileMd5']}.image", "subType": "0", "url": image["Url"]}})  
        return {
            "post_type": "message",
            "message_type": message_type,
            "group_id": msg_head["FromUin"],
            "user_id": msg_head["SenderUin"],
            "self_id": msg_head["ToUin"],
            "sender": sender,
            "message_seq": msg_head["MsgSeq"],
            "time": msg_head["MsgTime"],
            "message_id": str(msg_head["MsgUid"]),
            "raw_message": raw_message,
            "message": message_segments
        }
    elif message_type == "private":
        images = msg_body.get("Images", [])
        if images is None:
            images = []
        message_segments = []
        raw_message = msg_body["Content"]
        message_segments.append({"type": "text", "data": {"text": raw_message}})
        for image in images:
            message_segments.append({"type": "image", "data": {"file": f"{image['FileMd5']}.image", "subType": "0", "url": image["Url"]}})
        
        return {
            "post_type": "message",
            "message_type": message_type,
            "sub_type": "friend",
            "user_id": msg_head["SenderUin"],
            "self_id": msg_head["ToUin"],
            "sender": sender,
            "time": msg_head["MsgTime"],
            "message_id": str(msg_head["MsgUid"]),
            "raw_message": raw_message,
            "message": message_segments
        }
    else:
        return None

async def send_to_ws_b(message):
    if message == None:
       return
    bot_id = message["self_id"]
    ws_conn = ws_connections["b"]
    print("给b发送了",message)
    if ws_conn:
        try:
            await ws_conn.send_str(json.dumps(message))
        except ConnectionResetError:
            await ws_conn.close()
            async with aiohttp.ClientSession() as session:
                await _setup_b(bot_id)
            ws_conn = ws_connections["b"]
            await ws_conn.send_str(json.dumps(message))

if __name__ == "__main__":
    asyncio.run(main())