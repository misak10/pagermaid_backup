""" PagerMaid 模块用于查看用户或群组信息 """

from pyrogram import Client
from pyrogram.enums import MessageEntityType
from pyrogram.errors import UsernameNotOccupied, UsernameInvalid
from pyrogram.types import User, Chat
from os import remove
from datetime import datetime
from typing import Optional

from pagermaid.listener import listener
from pagermaid.utils import lang
from pagermaid.enums import Message

def format_date(timestamp) -> str:
    """格式化时间戳为易读格式"""
    if not timestamp:
        return None
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

@listener(
    is_plugin=True,
    outgoing=True,
    command="kk",
    description="查看用户或群组详细信息\n"
    "用法：直接使用 kk 查看当前聊天信息，kk 回复某条消息查看用户信息，或者使用 kk [用户名/用户ID/群组ID]",
    parameters="[username/uid/gid]",
)
async def kk(client: Client, context: Message):
    if not context.reply_to_message and not context.parameter:
        if context.chat.type.value in ["group", "supergroup", "channel"]:
            user = context.chat
        elif context.chat.type.value == "private":
            try:
                user = await client.get_users(context.chat.id)
            except Exception:
                user = context.chat
        else:
            if context.from_user:
                user = context.from_user
            else:
                user = context.sender_chat
    elif context.reply_to_message:
        if context.reply_to_message.from_user:
            user = context.reply_to_message.from_user
        else:
            user = context.reply_to_message.sender_chat
        if not user:
            return await context.edit(f"{lang('error_prefix')}{lang('profile_e_no')}")
    else:
        if len(context.parameter) == 1:
            user = context.parameter[0]
            if user.isdigit():
                user = int(user)
        else:
            if context.from_user:
                user = context.from_user
            else:
                user = context.sender_chat
        if context.entities is not None:
            if context.entities[0].type == MessageEntityType.TEXT_MENTION:
                user = context.entities[0].user
            elif context.entities[0].type == MessageEntityType.PHONE_NUMBER:
                user = int(context.parameter[0])
            elif context.entities[0].type == MessageEntityType.BOT_COMMAND:
                if context.from_user:
                    user = context.from_user
                else:
                    user = context.sender_chat
            else:
                return await context.edit(f"{lang('error_prefix')}{lang('arg_error')}")

        if not (isinstance(user, User) or isinstance(user, Chat)):
            try:
                try:
                    user = await client.get_users(user)
                except IndexError:
                    user = await client.get_chat(user)
            except (UsernameNotOccupied, UsernameInvalid):
                return await context.edit(f"{lang('error_prefix')}{lang('profile_e_nou')}")
            except OverflowError:
                return await context.edit(f"{lang('error_prefix')}{lang('profile_e_long')}")
            except Exception as exception:
                return await context.edit(f"{lang('error_prefix')}{lang('profile_e_nof')}")

    info_text = ""
    link = ""

    if isinstance(user, User):
        # 用户基本信息
        info_text = "👤 **用户信息**\n\n"
        info_text += f"**基本信息**\n"
        info_text += f"🆔 **ID** » `{user.id}`\n"
        info_text += f"📋 **名字** » {user.first_name}"
        if user.last_name:
            info_text += f"\n📝 **姓氏** » {user.last_name}"
        if user.username:
            info_text += f"\n🔰 **用户名** » @{user.username}"
        
        try:
            common_chats = await client.get_common_chats(user.id)
            if common_chats:
                info_text += f"\n👥 **共同群组** » {len(common_chats)} 个"
        except Exception:
            pass
        
        if context.chat.type.value in ["group", "supergroup"]:
            try:
                chat_member = await client.get_chat_member(context.chat.id, user.id)
                if chat_member:
                    status_map = {
                        "ChatMemberStatus.OWNER": "👑 群主",
                        "ChatMemberStatus.ADMINISTRATOR": "⭐️ 管理员",
                        "ChatMemberStatus.MEMBER": "👤 成员",
                        "ChatMemberStatus.RESTRICTED": "⚠️ 受限制",
                        "ChatMemberStatus.LEFT": "💨 已离开",
                        "ChatMemberStatus.BANNED": "❌ 被封禁"
                    }
                    info_text += f"\n💫 **群内身份** » {status_map.get(str(chat_member.status), str(chat_member.status))}"
                    
                    if str(chat_member.status) == "ChatMemberStatus.ADMINISTRATOR":
                        admin_rights = []
                        if chat_member.privileges:
                            if chat_member.privileges.can_change_info:
                                admin_rights.append("更改信息")
                            if chat_member.privileges.can_delete_messages:
                                admin_rights.append("删除消息")
                            if chat_member.privileges.can_restrict_members:
                                admin_rights.append("封禁用户")
                            if chat_member.privileges.can_invite_users:
                                admin_rights.append("邀请用户")
                            if chat_member.privileges.can_pin_messages:
                                admin_rights.append("置顶消息")
                            if chat_member.privileges.can_promote_members:
                                admin_rights.append("添加管理")
                            if chat_member.privileges.can_manage_video_chats:
                                admin_rights.append("管理语音")
                        if admin_rights:
                            info_text += f"\n🛡 **管理权限** » {' | '.join(admin_rights)}"
                            
                    if hasattr(chat_member, 'joined_date') and chat_member.joined_date:
                        info_text += f"\n📅 **加入时间** » {format_date(chat_member.joined_date)}"
            except Exception as e:
                print(f"Error getting chat member info: {e}")
                pass
        
        # 用户状态
        status_info = []
        if user.is_bot:
            status_info.append("🤖 机器人")
        if user.is_verified:
            status_info.append("✨ 官方认证")
        if user.is_scam:
            status_info.append("⛔️ 诈骗用户")
        if user.is_fake:
            status_info.append("🚫 虚假用户")
        if user.is_premium:
            status_info.append("💎 高级用户")
        if hasattr(user, 'restrictions') and user.restrictions:
            status_info.append("🔒 账户受限")
            
        if status_info:
            info_text += "\n\n**用户状态**\n"
            info_text += " | ".join(status_info)
        
        # 其他信息
        other_info = []
        if user.language_code:
            other_info.append(f"🌐 **语言** » {user.language_code.upper()}")
        if user.dc_id:
            other_info.append(f"🌍 **数据中心** » DC{user.dc_id}")
        if user.phone_number:
            other_info.append(f"📱 **电话** » `{user.phone_number}`")
        if user.status:
            status_map = {
                "online": "在线",
                "offline": "离线",
                "recently": "最近在线",
                "last_week": "一周内在线",
                "last_month": "一月内在线",
                "long_time_ago": "很久以前在线"
            }
            other_info.append(f"💡 **状态** » {status_map.get(user.status.value, user.status.value)}")
        if user.last_online_date:
            other_info.append(f"⏰ **最后在线** » {format_date(user.last_online_date)}")
            
        try:
            full_user = await client.get_chat(user.id)
            if full_user.bio:
                other_info.append(f"ℹ️ **个性签名** » {full_user.bio}")
        except Exception:
            pass
            
        if other_info:
            info_text += "\n\n**其他信息**\n"
            info_text += "\n".join(other_info)
        
        # 链接信息
        first_name = user.first_name.replace("\u2060", "")
        if user.username:
            info_text += (
                f"\n\n**链接**\n"
                f"🔗 [{first_name}](tg://user?id={user.id}) (@{user.username})"
            )
        else:
            info_text += (
                f"\n\n**链接**\n"
                f"🔗 [{first_name}](tg://user?id={user.id})"
            )

        if not context.entities:
            context.entities = []
        context.entities.append({
            "_": "messageEntityMentionName",
            "offset": len(info_text) - len(first_name),
            "length": len(first_name),
            "user_id": user.id
        })

        try:
            if user.photo and not user.is_bot:
                photo = await client.download_media(user.photo.big_file_id)
                await client.send_photo(
                    context.chat.id,
                    photo,
                    caption=info_text
                )
                remove(photo)
                await context.delete()
                return
        except Exception:
            pass

    elif isinstance(user, Chat):
        # 群组基本信息
        chat_type = {
            "private": "私聊",
            "bot": "机器人", 
            "group": "群组",
            "supergroup": "超级群组",
            "channel": "频道"
        }.get(user.type.value, user.type.value)
        
        info_text = f"📢 **{chat_type}信息**\n\n"
        info_text += f"**基本信息**\n"
        info_text += f"🆔 **ID** » `{user.id}`\n"
        info_text += f"📋 **标题** » {user.title}"
        if user.username:
            info_text += f"\n🔰 **用户名** » @{user.username}"
        if user.members_count:
            info_text += f"\n👥 **成员数** » {user.members_count}"
            
        try:
            if context.from_user:
                chat_member = await client.get_chat_member(user.id, context.from_user.id)
                if chat_member.status == "creator":
                    info_text += f"\n👑 **身份** » 群主"
                elif chat_member.status == "administrator":
                    info_text += f"\n⭐️ **身份** » 管理员"
        except Exception:
            pass
        
        # 群组状态
        status_info = []
        if user.is_verified:
            status_info.append("✨ 官方认证")
        if user.is_scam:
            status_info.append("⛔️ 诈骗群组")
        if user.is_fake:
            status_info.append("🚫 虚假群组")
        if user.is_restricted:
            status_info.append("⚠️ 受限群组")
        if user.has_protected_content:
            status_info.append("🔒 受保护内容")
        if user.available_reactions:
            status_info.append("💫 允许反应")
        if user.is_forum:
            status_info.append("📑 话题群组")
            
        if status_info:
            info_text += "\n\n**群组状态**\n"
            info_text += " | ".join(status_info)
        
        # 其他信息
        other_info = []
        if user.dc_id:
            other_info.append(f"🌍 **数据中心** » DC{user.dc_id}")
        if hasattr(user, 'slow_mode_delay') and user.slow_mode_delay:
            other_info.append(f"⏱ **慢速模式** » {user.slow_mode_delay}秒")
        if hasattr(user, 'can_set_sticker_set') and user.can_set_sticker_set:
            other_info.append("🎨 **可设置贴纸**")
        if user.description:
            other_info.append(f"📝 **简介** » {user.description}")
            
        if other_info:
            info_text += "\n\n**其他信息**\n"
            info_text += "\n".join(other_info)
        
        # 链接信息
        links = []
        title = user.title.replace("\u2060", "")
        if user.type.value in ["channel", "supergroup"]:
            if user.username:
                links.append(f"🔗 [{title}](https://t.me/{user.username})")
            else:
                links.append(f"🔗 [{title}](https://t.me/c/{str(user.id)[4:]})")
        else:
            if user.username:
                links.append(f"🔗 [{title}](https://t.me/{user.username})")
            else:
                links.append(f"🔗 [{title}](tg://chat?id={user.id})")

        if user.invite_link:
            links.append(f"📨 [邀请链接]({user.invite_link})")
        if user.linked_chat:
            links.append(f"🔗 **关联群组** » {user.linked_chat.title}")
            
        if links:
            info_text += "\n\n**链接**\n"
            info_text += "\n".join(links)

        if not context.entities:
            context.entities = []
        context.entities.append({
            "_": "messageEntityMentionName",
            "offset": info_text.rindex(title),
            "length": len(title),
            "user_id": user.id
        })

        try:
            if user.photo:
                photo = await client.download_media(user.photo.big_file_id)
                await client.send_photo(
                    context.chat.id,
                    photo,
                    caption=info_text
                )
                remove(photo)
                await context.delete()
                return
        except Exception:
            pass

    await context.edit(info_text)

