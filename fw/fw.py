""" PagerMaid forward plugin. """

from pyrogram.errors import RPCError, ChannelPrivate, UserNotParticipant, ChatWriteForbidden
from pagermaid.listener import listener
from pagermaid.enums import Message, Client
from pagermaid.utils import lang
from pagermaid.utils.bot_utils import log
from pagermaid.dependence import sqlite

@listener(
    is_plugin=True,
    outgoing=True,
    command="fw",
    description="将消息转发到指定目标\n"
    "可选：使用 fw -id <target_id> 转发到指定ID\n"
    "使用 fw -set <target_id> 设置默认转发目标\n"
    "使用 fw -del 删除默认转发目标\n"
    "直接使用 fw 转发到默认目标",
    parameters="[-id/-set/-del] [target_id]",
)
async def forward(client: Client, message: Message):
    """转发消息到指定目标"""
    if not message.reply_to_message:
        return await message.edit("请回复需要转发的消息")
    
    # 检查参数
    if len(message.parameter) == 0:
        # 使用默认转发目标
        default_target = sqlite.get("forward.default-target", None)
        if not default_target:
            return await message.edit("未设置默认转发目标，请使用 -fw -set <target_id> 设置")
        try:
            if isinstance(default_target, bytes):
                default_target = default_target.decode()
            target_id = int(str(default_target).strip())
        except:
            return await message.edit("默认转发目标格式错误，请重新设置")
    elif len(message.parameter) == 2:
        if message.parameter[0] == "-id":
            try:
                target_id = int(message.parameter[1].strip())
            except ValueError:
                return await message.edit("目标ID格式错误，请确保输入的是有效的数字ID")
        elif message.parameter[0] == "-set":
            try:
                target_id = int(message.parameter[1].strip())
                sqlite["forward.default-target"] = str(target_id).encode()  # 将ID转换为字节存储
                await message.edit(f"已设置默认转发目标为：{target_id}")
                return
            except ValueError:
                return await message.edit("目标ID格式错误，请确保输入的是有效的数字ID")
        elif message.parameter[0] == "-del":
            del sqlite["forward.default-target"]
            await message.edit("已删除默认转发目标")
            return
        else:
            return await message.edit("参数错误，请使用 -id/-set/-del")
    else:
        return await message.edit("参数错误，格式：-fw -id <target_id> 或 -fw -set <target_id>")
    
    try:
        # 尝试转发消息
        await message.reply_to_message.forward(
            chat_id=target_id
        )
        # 删除命令消息
        await message.delete()
    except ChannelPrivate:
        await message.edit("无法转发到该频道，可能是因为您不是频道成员")
    except UserNotParticipant:
        await message.edit("无法转发到该群组，可能是因为您不是群组成员")
    except ChatWriteForbidden:
        await message.edit("无法转发到该目标，可能是因为您没有发言权限")
    except RPCError as e:
        await message.edit(f"转发失败: {str(e)}")
        await log(f"转发消息到 {target_id} 失败: {str(e)}")
    except Exception as e:
        await message.edit(f"发生未知错误: {str(e)}")
        await log(f"转发消息时发生未知错误: {str(e)}") 