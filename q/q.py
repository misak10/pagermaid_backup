from asyncio import sleep
from typing import Union, List, Optional

from pyrogram.errors import Flood
from pyrogram.errors.exceptions.bad_request_400 import ChatForwardsRestricted

from pagermaid.listener import listener
from pagermaid.enums import Client, Message


@listener(command="q",
         description="将回复的消息转换成语录并制作贴纸",
         parameters="[数量]")
async def quote(bot: Client, message: Message):
    """将回复的消息转换成语录并制作贴纸"""
    quote_bot = "QuotLyBot"
    sticker_bot = "fStikBot"
    
    if not message.reply_to_message:
        return await message.edit('你需要回复一条消息。')
        
    message_ids = await get_message_ids(message)
    if isinstance(message_ids, str):
        return await message.edit(message_ids)
        
    try:
        await bot.unblock_user(quote_bot)
        await bot.unblock_user(sticker_bot)
        
        async with bot.conversation(quote_bot) as conv:
            try:
                await bot.forward_messages(
                    chat_id=quote_bot,
                    from_chat_id=message.chat.id,
                    message_ids=message_ids
                )
            except ChatForwardsRestricted:
                return await message.edit('群组消息不允许被转发。')
                
            quote_response = await conv.get_response()
            await conv.mark_as_read()
            
            await send_quote(quote_response, message)
            
            if quote_response:
                await quote_response.forward(sticker_bot, disable_notification=True)
        
    except Exception:
        pass
        
    await message.safe_delete()


async def get_message_ids(message: Message) -> Union[List[int], str]:
    """获取需要转换的消息ID列表"""
    reply_id = message.reply_to_message_id or message.reply_to_top_message_id
    
    if not message.parameter:
        return reply_id
        
    try:
        count = int(message.arguments)
        return [reply_id + i for i in range(count)]
    except ValueError:
        return "请输入有效的数字。"


async def send_quote(response: Message, original_msg: Message) -> Optional[Message]:
    """发送语录到聊天并返回发送的消息"""
    try:
        sent = await response.copy(
            original_msg.chat.id,
            reply_to_message_id=original_msg.reply_to_message_id or original_msg.reply_to_top_message_id
        )
        return sent
    except Flood as e:
        await sleep(e.value + 1)
        sent = await response.copy(
            original_msg.chat.id,
            reply_to_message_id=original_msg.reply_to_message_id or original_msg.reply_to_top_message_id
        )
        return sent
    except Exception:
        return None
