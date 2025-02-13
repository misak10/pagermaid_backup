import re
import time
import requests
import yaml
import base64
from typing import Dict, Optional, Tuple, List
from urllib.parse import unquote
from bs4 import BeautifulSoup
from pagermaid.enums import Message
from pagermaid.listener import listener
from pagermaid.utils import alias_command
from pagermaid.dependence import client as http_client

UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
NODE_PATTERNS = [
    'vmess://', 'trojan://', 'ss://', 'ssr://',
    'vless://', 'hy2://', 'hysteria://', 'hy://'
]
REGION_RULES = [
    ('香港', ['香港', 'hong kong', 'hongkong', 'hk', '🇭🇰']),
    ('台湾', ['台湾', 'taiwan', 'tw', '🇹🇼']),
    ('日本', ['日本', 'japan', 'jp', '🇯🇵']),
    ('新加坡', ['新加坡', 'singapore', 'sg', '🇸🇬']),
    ('美国', ['美国', 'united states', 'us', 'usa', '🇺🇸']),
    ('韩国', ['韩国', 'korea', 'kr', '🇰🇷']),
    ('德国', ['德国', 'germany', 'de', '🇩🇪']),
    ('英国', ['英国', 'united kingdom', 'uk', '🇬🇧'])
]

def format_size(size: int) -> str:
    """将字节大小转换为人类可读的格式"""
    def _format(integer: int, remainder: int, level: int) -> Tuple[int, int, int]:
        if integer >= 1024:
            remainder = integer % 1024
            integer //= 1024
            level += 1
            return _format(integer, remainder, level)
        return integer, remainder, level

    if size < 0:
        size = 0
    integer, remainder, level = _format(size, 0, 0)
    if level + 1 > len(UNITS):
        level = -1
    return f'{integer}.{remainder:>03d} {UNITS[level]}'

def format_time_remaining(seconds: int) -> str:
    """将秒数转换为天和小时的格式"""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    return f"{str(days).zfill(2)}天{str(hours).zfill(2)}小时"

def get_filename_from_url(url: str) -> str:
    """从URL中获取机场名称"""
    if "sub?target=" in url:
        pattern = r"url=([^&]*)"
        match = re.search(pattern, url)
        if match:
            return get_filename_from_url(unquote(match.group(1)))
            
    if "api/v1/client/subscribe?token" in url:
        url = f"{url}&flag=clash" if "&flag=clash" not in url else url
        try:
            response = requests.get(url)
            header = response.headers.get('Content-Disposition')
            if header:
                pattern = r"filename\*=UTF-8''(.+)"
                result = re.search(pattern, header)
                if result:
                    filename = unquote(result.group(1))
                    return filename.replace("%20", " ").replace("%2B", "+")
        except:
            return '未知'
            
    try:
        base_url = re.match(r'(https?://[^/]+)', url).group(1)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(f"{base_url}/auth/login", headers=headers, timeout=10)
        if response.status_code != 200:
            response = requests.get(base_url, headers=headers, timeout=1)
            
        soup = BeautifulSoup(response.content, 'html.parser')
        title = str(soup.title.string).replace('登录 — ', '')
        
        if "Attention Required! | Cloudflare" in title:
            return '该域名仅限国内IP访问'
        if "Access denied" in title or "404 Not Found" in title:
            return '该域名非机场面板域名'
        if "Just a moment" in title:
            return '该域名开启了5s盾'
        return title
    except:
        return '未知'

def get_node_info(url: str, headers: Dict) -> Optional[Dict]:
    """获取节点信息，包括数量、类型和地区分布"""
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            return None
            
        # 尝试解析为YAML格式
        try:
            config = yaml.safe_load(res.text)
            if config and 'proxies' in config:
                type_count = {}
                regions = {}
                
                for proxy in config['proxies']:
                    # 统计类型
                    proxy_type = proxy.get('type', '').lower()
                    type_count[proxy_type] = type_count.get(proxy_type, 0) + 1
                    
                    # 解析地区信息
                    name = proxy.get('name', '').lower()
                    for region_name, keywords in REGION_RULES:
                        if any(keyword in name for keyword in keywords):
                            regions[region_name] = regions.get(region_name, 0) + 1
                            break
                
                return {
                    'node_count': len(config['proxies']),
                    'type_count': {k: v for k, v in type_count.items() if v > 0},
                    'regions': {k: v for k, v in regions.items() if v > 0}
                }
        except yaml.YAMLError:
            pass
            
        # 如果不是YAML格式，尝试base64解码
        try:
            decoded_content = base64.b64decode(res.text).decode('utf-8')
            type_count = {pattern.replace('://', ''): 0 for pattern in NODE_PATTERNS}
            regions = {}
            node_count = 0
            
            for line in decoded_content.splitlines():
                if not line.strip():
                    continue
                    
                # 检测节点类型
                for pattern in NODE_PATTERNS:
                    if line.startswith(pattern):
                        type_count[pattern.replace('://', '')] += 1
                        node_count += 1
                        break
                        
                # 解析地区信息
                line_lower = line.lower()
                for region_name, keywords in REGION_RULES:
                    if any(keyword in line_lower for keyword in keywords):
                        regions[region_name] = regions.get(region_name, 0) + 1
                        break
                        
            return {
                'node_count': node_count,
                'type_count': {k: v for k, v in type_count.items() if v > 0},
                'regions': {k: v for k, v in regions.items() if v > 0}
            }
        except:
            return None
    except:
        return None

@listener(is_plugin=True, outgoing=True, command=alias_command("cha"),
          description='识别订阅链接并获取信息\n使用方法：使用该命令发送或回复一段带有一条或多条订阅链接的文本',
          parameters='<url>')
async def subinfo(_, msg: Message):
    """订阅信息查询主函数"""
    headers = {'User-Agent': 'ClashMeta'}
    
    try:
        message_raw = msg.reply_to_message and (msg.reply_to_message.caption or msg.reply_to_message.text) or (msg.caption or msg.text)
        url_list = re.findall(r"https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]", message_raw)
        
        final_output = []
        for url in url_list:
            try:
                res = await http_client.get(url, headers=headers, timeout=5)
                while res.status_code in (301, 302):
                    url = res.headers['location']
                    res = await http_client.get(url, headers=headers, timeout=5)
                    
                if res.status_code != 200:
                    final_output.append('无法访问')
                    continue
                    
                try:
                    info = res.headers['subscription-userinfo']
                    info_num = [int(x) for x in re.findall(r'\d+', info)]
                    time_now = int(time.time())
                    
                    # 获取节点信息
                    node_info = get_node_info(url, headers)
                    node_count = node_info['node_count'] if node_info else '未知'
                    
                    # 生成输出信息
                    output_lines = [
                        f'订阅链接：`{url}`',
                        f'机场名：`{get_filename_from_url(url)}`',
                        f'已用上行：`{format_size(info_num[0])}`',
                        f'已用下行：`{format_size(info_num[1])}`',
                        f'剩余：`{format_size(info_num[2] - info_num[1] - info_num[0])}`',
                        f'总共：`{format_size(info_num[2])}`',
                        f'使用比例：`{round((info_num[0] + info_num[1]) / info_num[2] * 100, 2)}%`',
                        f'节点数量：`{node_count}`'
                    ]
                    
                    if node_info:
                        if node_info['type_count']:
                            type_str = ', '.join(f'{k}:{v}' for k, v in node_info['type_count'].items())
                            output_lines.append(f'节点类型：`{type_str}`')
                        if node_info['regions']:
                            region_str = ', '.join(f'{k}:{v}' for k, v in node_info['regions'].items())
                            output_lines.append(f'节点地区：`{region_str}`')
                    
                    # 添加过期时间信息
                    if len(info_num) >= 4:
                        expire_time = time.strftime("%Y-%m-%d", time.localtime(info_num[3] + 28800))
                        if time_now <= info_num[3]:
                            remaining = format_time_remaining(info_num[3] - time_now)
                            output_lines.append(f'此订阅将于`{expire_time}`过期，剩余`{remaining}`')
                        else:
                            output_lines.append(f'此订阅已于`{expire_time}`过期！')
                    else:
                        output_lines.append('到期时间：`未知`')
                        
                    final_output.append('\n'.join(output_lines))
                except KeyError:
                    final_output.append(f'订阅链接：`{url}`\n机场名：`{get_filename_from_url(url)}`\n无流量信息')
            except:
                final_output.append('连接错误')
                
        await msg.edit('\n\n'.join(final_output))
    except Exception as e:
        await msg.edit(f'参数错误: {str(e)}')
