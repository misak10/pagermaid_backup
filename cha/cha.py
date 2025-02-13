import re
import time
import requests
import yaml
import base64
from pagermaid.utils import pip_install

try:
    from bs4 import BeautifulSoup
except Exception as e:
    print(f"捕获到异常: {e}")
    
    
def install_if_missing(package_name):
    try:
        __import__(package_name)
        print(f"{package_name} 已经安装。")
    except ImportError:
        print(f"未找到 {package_name}，正在安装...")
        subprocess.run(["pip3", "install", package_name], check=True)
        print(f"{package_name} 已安装。")

install_if_missing("bs4")

from bs4 import BeautifulSoup
from urllib import parse
from pagermaid.enums import Message
from urllib.parse import unquote
from pagermaid.listener import listener
from pagermaid.utils import alias_command
from pagermaid.dependence import client as http_client

# 此版本是修改版的修改版， @fffffx2 修改后, @xream 修改
# 修复了在非venv环境下使用pip install报错的情况 @MintAby
def get_filename_from_url(url):
    if "sub?target=" in url:
        pattern = r"url=([^&]*)"
        match = re.search(pattern, url)
        if match:
            encoded_url = match.group(1)
            decoded_url = unquote(encoded_url)
            return get_filename_from_url(decoded_url)
    elif "api/v1/client/subscribe?token" in url:
        if "&flag=clash" not in url:
            url = url + "&flag=clash"
        else:
            pass
        try:
            response = requests.get(url)
            header = response.headers.get('Content-Disposition')
            if header:
                pattern = r"filename\*=UTF-8''(.+)"
                result = re.search(pattern, header)
                if result:
                    filename = result.group(1)
                    filename = parse.unquote(filename)  # 对文件名进行解码
                    airport_name = filename.replace("%20", " ").replace("%2B", "+")
                    return airport_name
        except:
            return '未知'
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (HTML, like Gecko) '
                          'Chrome/108.0.0.0'
                          'Safari/537.36'}
        try:
            pattern = r'(https?://)([^/]+)'
            match = re.search(pattern, url)
            base_url = None
            if match:
                base_url = match.group(1) + match.group(2)
            response = requests.get(url=base_url + '/auth/login', headers=headers, timeout=10)
            if response.status_code != 200:
                response = requests.get(base_url, headers=headers, timeout=1)
            html = response.content
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string
            title = str(title).replace('登录 — ', '')
            if "Attention Required! | Cloudflare" in title:
                title = '该域名仅限国内IP访问'
            elif "Access denied" in title or "404 Not Found" in title:
                title = '该域名非机场面板域名'
            elif "Just a moment" in title:
                title = '该域名开启了5s盾'
            else:
                pass
            return title
        except:
            return '未知'


def convert_time_to_str(ts):
    return str(ts).zfill(2)


def sec_to_data(y):
    h = int(y // 3600 % 24)
    d = int(y // 86400)
    h = convert_time_to_str(h)
    d = convert_time_to_str(d)
    return d + "天" + h + "小时"


def StrOfSize(size):
    def strofsize(integer, remainder, level):
        if integer >= 1024:
            remainder = integer % 1024
            integer //= 1024
            level += 1
            return strofsize(integer, remainder, level)
        elif integer < 0:
            integer = 0
            return strofsize(integer, remainder, level)
        else:
            return integer, remainder, level

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    integer, remainder, level = strofsize(size, 0, 0)
    if level + 1 > len(units):
        level = -1
    return ('{}.{:>03d} {}'.format(integer, remainder, units[level]))


def get_node_count(url, headers):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            try:
                # 尝试解析为YAML格式
                config = yaml.safe_load(res.text)
                if config and 'proxies' in config:
                    return len(config['proxies'])
            except:
                # 如果不是YAML格式，尝试计算节点数量
                node_patterns = [
                    'vmess://', 'trojan://', 'ss://', 'ssr://',
                    'vless://', 'hy2://', 'hysteria://', 'hy://'
                ]
                node_count = sum(len(re.findall(pattern, res.text)) for pattern in node_patterns)
                return node_count if node_count > 0 else '未知'
    except:
        return '未知'
    return '未知'


def calculate_percentage(used, total):
    if total == 0:
        return 0
    return round((used / total) * 100, 2)


def parse_subscription_info(url, headers):
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            # 首先尝试作为Clash配置解析
            try:
                config = yaml.safe_load(res.text)
                if config and 'proxies' in config:
                    # 统计节点类型
                    type_count = {}
                    regions = {}
                    
                    for proxy in config['proxies']:
                        # 统计类型
                        proxy_type = proxy.get('type', '').lower()
                        type_count[proxy_type] = type_count.get(proxy_type, 0) + 1
                        
                        # 解析地区信息
                        name = proxy.get('name', '').lower()
                        # 地区匹配规则
                        region_rules = [
                            ('香港', ['香港', 'hong kong', 'hongkong', 'hk', '🇭🇰']),
                            ('台湾', ['台湾', 'taiwan', 'tw', '🇹🇼']),
                            ('日本', ['日本', 'japan', 'jp', '🇯🇵']),
                            ('新加坡', ['新加坡', 'singapore', 'sg', '🇸🇬']),
                            ('美国', ['美国', 'united states', 'us', 'usa', '🇺🇸']),
                            ('韩国', ['韩国', 'korea', 'kr', '🇰🇷']),
                            ('德国', ['德国', 'germany', 'de', '🇩🇪']),
                            ('英国', ['英国', 'united kingdom', 'uk', '🇬🇧'])
                        ]
                        
                        for region_name, keywords in region_rules:
                            if any(keyword in name for keyword in keywords):
                                regions[region_name] = regions.get(region_name, 0) + 1
                                break
                    
                    return {
                        'type_count': type_count,
                        'regions': regions
                    }
            except yaml.YAMLError:
                pass
            
            # 如果不是Clash配置，尝试base64解码
            try:
                decoded_content = base64.b64decode(res.text).decode('utf-8')
            except:
                return None
            
            # 统计节点类型
            type_count = {
                'vmess': 0,
                'ss': 0,
                'ssr': 0,
                'trojan': 0,
                'vless': 0,
                'hy2': 0,
                'hysteria': 0,
                'hy': 0
            }
            
            # 解析地区信息
            regions = {}
            
            # 分析每一行
            lines = decoded_content.split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                # 检测节点类型
                if line.startswith('vmess://'):
                    type_count['vmess'] += 1
                    try:
                        vmess_info = base64.b64decode(line[8:]).decode('utf-8')
                        line = vmess_info
                    except:
                        pass
                elif line.startswith('ss://'):
                    type_count['ss'] += 1
                elif line.startswith('ssr://'):
                    type_count['ssr'] += 1
                    try:
                        ssr_info = base64.b64decode(line[6:]).decode('utf-8')
                        line = ssr_info
                    except:
                        pass
                elif line.startswith('trojan://'):
                    type_count['trojan'] += 1
                elif line.startswith('vless://'):
                    type_count['vless'] += 1
                elif line.startswith('hy2://'):
                    type_count['hy2'] += 1
                elif line.startswith('hysteria://'):
                    type_count['hysteria'] += 1
                elif line.startswith('hy://'):
                    type_count['hy'] += 1
                
                # 解析地区信息
                line_lower = line.lower()
                region_rules = [
                    ('香港', ['香港', 'hong kong', 'hongkong', 'hk', '🇭🇰']),
                    ('台湾', ['台湾', 'taiwan', 'tw', '🇹🇼']),
                    ('日本', ['日本', 'japan', 'jp', '🇯🇵']),
                    ('新加坡', ['新加坡', 'singapore', 'sg', '🇸🇬']),
                    ('美国', ['美国', 'united states', 'us', 'usa', '🇺🇸']),
                    ('韩国', ['韩国', 'korea', 'kr', '🇰🇷']),
                    ('德国', ['德国', 'germany', 'de', '🇩🇪']),
                    ('英国', ['英国', 'united kingdom', 'uk', '🇬🇧'])
                ]
                
                for region_name, keywords in region_rules:
                    if any(keyword in line_lower for keyword in keywords):
                        regions[region_name] = regions.get(region_name, 0) + 1
                        break
            
            # 过滤掉数量为0的类型和地区
            type_count = {k: v for k, v in type_count.items() if v > 0}
            regions = {k: v for k, v in regions.items() if v > 0}
            
            return {
                'type_count': type_count,
                'regions': regions
            }
    except Exception as e:
        print(f"解析错误: {str(e)}")
        return None


@listener(is_plugin=True, outgoing=True, command=alias_command("cha"),
          description='识别订阅链接并获取信息\n使用方法：使用该命令发送或回复一段带有一条或多条订阅链接的文本',
          parameters='<url>')
async def subinfo(_, msg: Message):
    headers = {
        'User-Agent': 'ClashforWindows/0.18.1'
    }
    output_text = None
    try:
        message_raw = msg.reply_to_message and (msg.reply_to_message.caption or msg.reply_to_message.text) or (
                    msg.caption or msg.text)
        final_output = ''
        url_list = re.findall("https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]",
                              message_raw)
        for url in url_list:
            try:
                res = await http_client.get(url, headers=headers, timeout=5)
                while res.status_code == 301 or res.status_code == 302:
                    url1 = res.headers['location']
                    res = await http_client.get(url1, headers=headers, timeout=5)
            except:
                final_output = final_output + '连接错误' + '\n\n'
                continue
            if res.status_code == 200:
                try:
                    info = res.headers['subscription-userinfo']
                    info_num = re.findall('\d+', info)
                    time_now = int(time.time())
                    
                    # 计算使用百分比
                    used_traffic = int(info_num[0]) + int(info_num[1])
                    total_traffic = int(info_num[2])
                    usage_percent = calculate_percentage(used_traffic, total_traffic)
                    
                    # 获取节点数量
                    node_count = get_node_count(url, headers)
                    
                    # 获取订阅更新时间
                    last_modified = res.headers.get('last-modified', '未知')
                    
                    # 获取节点类型和地区信息
                    sub_info = parse_subscription_info(url, headers)
                    type_info = ''
                    region_info = ''
                    
                    if sub_info:
                        # 生成节点类型信息
                        type_counts = sub_info['type_count']
                        type_strings = []
                        for node_type, count in type_counts.items():
                            if count > 0:
                                type_strings.append(f'{node_type}:{count}')
                        type_info = '节点类型：`' + ', '.join(type_strings) + '`\n'
                        
                        # 生成地区信息
                        region_counts = sub_info['regions']
                        region_strings = []
                        for region, count in region_counts.items():
                            region_strings.append(f'{region}:{count}')
                        region_info = '节点地区：`' + ', '.join(region_strings) + '`\n'
                    
                    output_text_head = (
                        f'订阅链接：`{url}`\n'
                        f'机场名：`{get_filename_from_url(url)}`\n'
                        f'已用上行：`{StrOfSize(int(info_num[0]))}`\n'
                        f'已用下行：`{StrOfSize(int(info_num[1]))}`\n'
                        f'剩余：`{StrOfSize(int(info_num[2]) - int(info_num[1]) - int(info_num[0]))}`\n'
                        f'总共：`{StrOfSize(int(info_num[2]))}`\n'
                        f'使用比例：`{usage_percent}%`\n'
                        f'节点数量：`{node_count}`\n'
                        f'{type_info}'
                        f'{region_info}'
                    )
                    
                    if len(info_num) >= 4:
                        timeArray = time.localtime(int(info_num[3]) + 28800)
                        dateTime = time.strftime("%Y-%m-%d", timeArray)
                        if time_now <= int(info_num[3]):
                            lasttime = int(info_num[3]) - time_now
                            output_text = output_text_head + '\n此订阅将于`' + dateTime + '`过期' + '，剩余`' + sec_to_data(
                                lasttime) + '`'
                        elif time_now > int(info_num[3]):
                            output_text = output_text_head + '\n此订阅已于`' + dateTime + '`过期！'
                    else:
                        output_text = output_text_head + '\n到期时间：`未知`'
                except:
                    output_text = '订阅链接：`' + url + '`\n机场名：`' + get_filename_from_url(url) + '`\n无流量信息'
            else:
                output_text = '无法访问'
            final_output = final_output + output_text + '\n\n'
        await msg.edit(final_output)
    except:
        await msg.edit('参数错误')
