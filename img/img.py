""" PagerMaid 模块用于通过API获取图片 """

import json
import os
import httpx
from typing import Dict, List, Optional
from pyrogram import Client
from pagermaid.listener import listener
from pagermaid.utils import lang, alias_command
from pagermaid.enums import Message

# 配置文件路径
CONFIG_DIR = "data/img"
CONFIG_FILE = f"{CONFIG_DIR}/api_config.json"

# 确保配置目录存在
os.makedirs(CONFIG_DIR, exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    "apis": {}
}

def load_config() -> Dict:
    """加载配置文件"""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG

def save_config(config: Dict) -> None:
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置文件失败: {e}")

async def download_image(url: str) -> Optional[str]:
    """下载图片并返回文件路径"""
    try:
        filename = f"{CONFIG_DIR}/temp_img.jpg"
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            response = await http_client.get(url, timeout=15.0)
            if response.status_code != 200:
                return None
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            return filename
    except Exception as e:
        print(f"下载图片失败: {e}")
        return None

def safe_remove(path: str) -> None:
    """安全删除文件"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"删除文件失败: {e}")

@listener(
    is_plugin=True,
    outgoing=True,
    command="img",
    description="通过API获取图片\n"
    "用法：`img [关键词]`获取指定API的图片\n"
    "`img [关键词] [API地址]`添加/更新API\n"
    "`img [关键词] delete`删除API\n"
    "`img list`列出所有已添加API",
    parameters="[关键词] (API地址/delete/list)"
)
async def img(client: Client, context: Message):
    config = load_config()
    
    if not context.parameter:
        return await context.edit("**使用方法**：\n"
                                 "`img [关键词]` - 获取图片\n"
                                 "`img [关键词] [API地址]` - 添加/更新API\n"
                                 "`img [关键词] delete` - 删除API\n"
                                 "`img list` - 列出所有API")
    
    # 列出所有API
    if context.parameter[0] == "list":
        if not config["apis"]:
            return await context.edit("⚠️ **尚未添加任何API**")
        
        text = "📋 **已添加的API列表**：\n\n"
        for keyword, api_url in config["apis"].items():
            text += f"🔸 **{keyword}** - `{api_url}`\n"
        
        return await context.edit(text)
    
    keyword = context.parameter[0]
    
    # 删除API
    if len(context.parameter) > 1 and context.parameter[1] == "delete":
        if keyword not in config["apis"]:
            return await context.edit(f"⚠️ **关键词 `{keyword}` 不存在**")
        
        del config["apis"][keyword]
        save_config(config)
        return await context.edit(f"✅ **已删除关键词 `{keyword}` 对应的API**")
    
    # 添加/更新API
    if len(context.parameter) > 1:
        api_url = context.parameter[1]
        config["apis"][keyword] = api_url
        save_config(config)
        return await context.edit(f"✅ **已添加/更新关键词 `{keyword}` 对应的API**：\n`{api_url}`")
    
    # 获取图片
    if keyword not in config["apis"]:
        return await context.edit(f"⚠️ **关键词 `{keyword}` 不存在，请先添加对应的API**")
    
    api_url = config["apis"][keyword]
    await context.edit(f"🔍 **正在获取 `{keyword}` 图片...**")
    
    try:
        # 下载图片
        async with httpx.AsyncClient(follow_redirects=True) as http_client:
            response = await http_client.get(api_url, timeout=15.0)
            
            if response.status_code != 200:
                return await context.edit(f"⚠️ **API请求失败 ({response.status_code})**")
            
            # 如果是重定向API，直接获取最终URL
            final_url = str(response.url)
            
            # 判断是否直接是图片
            content_type = response.headers.get("content-type", "")
            is_image = content_type.startswith("image/")
            
            # 如果是图片类型或URL以图片扩展名结尾，直接下载
            if is_image or any(final_url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                img_url = final_url
            else:
                # 尝试解析JSON响应或直接使用图片URL
                try:
                    # 先尝试解析为JSON，获取图片URL
                    json_data = response.json()
                    
                    # 常见API返回格式兼容处理
                    img_url = None
                    if isinstance(json_data, dict):
                        # 尝试多种常见API返回格式
                        possible_keys = ['url', 'data', 'imgurl', 'img_url', 'image', 'pic', 'src']
                        for key in possible_keys:
                            if key in json_data:
                                value = json_data[key]
                                if isinstance(value, str):
                                    img_url = value
                                    break
                                elif isinstance(value, dict) and 'url' in value:
                                    img_url = value['url']
                                    break
                                elif isinstance(value, list) and value and isinstance(value[0], dict) and 'url' in value[0]:
                                    img_url = value[0]['url']
                                    break
                    
                    # 如果无法找到图片URL，则直接使用最终重定向的URL
                    if not img_url:
                        img_url = final_url
                except:
                    # 不是JSON格式，可能直接返回图片，使用最终URL
                    img_url = final_url
            
            # 下载图片
            photo_path = await download_image(img_url)
            if not photo_path:
                return await context.edit("⚠️ **下载图片失败**")
            
            # 使用Pyrogram客户端发送图片
            await client.send_photo(
                context.chat.id,
                photo_path,
                caption=f"🖼 **{keyword}** 图片"
            )
            
            # 删除临时文件
            safe_remove(photo_path)
            await context.delete()
            
    except Exception as e:
        await context.edit(f"⚠️ **获取图片失败**：`{str(e)}`")
