import discord
from discord.ext import commands, tasks
import socket
import os
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

REACTION_EMOJI = "✅"
AGREE_CHANNEL_NAME = "✅｜agree-to-join"
PLAYER_ROLE_NAME = "玩家"
UNVERIFIED_ROLE_NAME = "未驗證"

SERVER_STATUS_CHANNEL_NAME = "伺服器狀態"
SERVERS_TO_MONITOR = [
    {"name": "Login Server", "ip": "maplewaltzro.servegame.com", "port": 6900},
    {"name": "Char Server", "ip": "maplewaltzro.servegame.com", "port": 6121},
    {"name": "Map Server", "ip": "maplewaltzro.servegame.com", "port": 5121},
]

last_statuses = {}
status_message_id = None

@bot.event
async def on_ready():
    print(f"登入成功：{bot.user.name}")
    check_servers.start()

@tasks.loop(seconds=60)
async def check_servers():
    global last_statuses, status_message_id

    guild = bot.guilds[0]
    channel = discord.utils.get(guild.text_channels, name=SERVER_STATUS_CHANNEL_NAME)
    if channel is None:
        category = discord.utils.get(guild.categories, name="📢｜官方專區")
        if category:
            channel = await guild.create_text_channel(SERVER_STATUS_CHANNEL_NAME, category=category)
        else:
            channel = await guild.create_text_channel(SERVER_STATUS_CHANNEL_NAME)

    status_messages = []
    changed = False
    new_statuses = {}

    for server in SERVERS_TO_MONITOR:
        name, ip, port = server["name"], server["ip"], server["port"]
        is_up = False
        try:
            with socket.create_connection((ip, port), timeout=2):
                is_up = True
        except:
            is_up = False

        new_statuses[name] = is_up
        old_status = last_statuses.get(name)

        if old_status is not None and old_status != is_up:
            changed = True

        status = "🟢 上線" if is_up else "🔴 離線"
        status_messages.append(f"**{name}**：{status}")

    last_statuses = new_statuses.copy()

    if changed or status_message_id is None:
        embed = discord.Embed(title="伺服器狀態檢查", description="\n".join(status_messages), color=0x00ff00)

        if status_message_id:
            try:
                msg = await channel.fetch_message(status_message_id)
                await msg.edit(embed=embed)
                return
            except:
                pass

        msg = await channel.send(embed=embed)
        status_message_id = msg.id

@bot.command()
@commands.has_permissions(administrator=True)
async def 建置頻道(ctx):
    guild = ctx.guild

    roles = {
        UNVERIFIED_ROLE_NAME: discord.Permissions.none(),
        PLAYER_ROLE_NAME: discord.Permissions(send_messages=True, read_messages=True),
        "VIP玩家": discord.Permissions(send_messages=True, read_messages=True),
        "GM": discord.Permissions(administrator=True),
        "Bot": discord.Permissions(send_messages=True, read_messages=True),
    }

    created_roles = {}
    for name, perms in roles.items():
        existing = discord.utils.get(guild.roles, name=name)
        if existing:
            created_roles[name] = existing
        else:
            role = await guild.create_role(name=name, permissions=perms)
            created_roles[name] = role

    channel_structure = {
        "⚔️｜歡迎區": [
            ("📜｜welcome", False),
            (AGREE_CHANNEL_NAME, False),
        ],
        "📢｜官方專區": [
            ("📢｜official-announcements", True),
            ("🛠️｜update-log", True),
            ("🧾｜event-info", True),
            ("⚠️｜maintenance", True),
            (SERVER_STATUS_CHANNEL_NAME, True),
        ],
        "💬｜玩家討論區": [
            ("💬｜general-chat", True),
            ("❓｜newbie-questions", True),
            ("⚔️｜class-discussion", True),
            ("🧙｜wizard-hall", True),
        ],
        "🛠｜技術支援": [
            ("🐛｜bug-report", True),
            ("🆘｜support-ticket", True),
        ],
        "🔒｜GM專區": [
            ("🔧｜gm-chat", False),
            ("🗂️｜staff-docs", False),
        ],
    }

    for category_name, channels in channel_structure.items():
        category = await guild.create_category(category_name)
        for channel_name, is_visible in channels:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=is_visible),
                created_roles[PLAYER_ROLE_NAME]: discord.PermissionOverwrite(read_messages=True),
                created_roles["GM"]: discord.PermissionOverwrite(read_messages=True),
                created_roles["Bot"]: discord.PermissionOverwrite(read_messages=True),
            }
            if "gm" in channel_name or "staff" in channel_name:
                overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)
                overwrites[created_roles[PLAYER_ROLE_NAME]] = discord.PermissionOverwrite(read_messages=False)

            channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)

            if channel.name == AGREE_CHANNEL_NAME:
                msg = await channel.send("請閱讀規章後點擊下方✅以取得身分組")
                await msg.add_reaction(REACTION_EMOJI)
            if channel.name == "📜｜welcome":
                await channel.send("""
📜【伺服器免責聲明】📜

本伺服器為 非官方私有伺服器，僅供玩家娛樂、研究與技術交流用途，不涉及任何營利行為，亦與 Gravity 官方無任何關聯。

玩家於本伺服器中的所有行為（包括但不限於遊戲內購買、交易、互動）皆屬自願性參與，若因此導致任何損失，本團隊將不承擔法律責任。

本伺服器有權依據運營需求，隨時調整遊戲內容、封鎖帳號、刪除資料等，恕不另行通知，亦不提供任何形式之補償。

使用本伺服器即表示您已閱讀並同意本免責聲明之所有條款。若您不同意，請勿登入或使用本伺服器。

本伺服器僅對系統異常或 BUG 提供修正協助，對玩家個人電腦問題、網路狀況或第三方工具導致之錯誤，不提供支援。

🔒 本聲明內容如有更新，將於官方公告區發佈，恕不另行通知。

本服務為非營利開發測試環境，任何資料可能隨時清除。 「所有資料僅供測試與技術研究，不代表實際遊戲內容」

✅ 點選下方 `✅` 表示你已閱讀並同意上述規章，即可獲得玩家身分。
                """)
    await ctx.send("頻道與角色建置完成 ✅")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.emoji.name != REACTION_EMOJI:
        return

    guild = discord.utils.get(bot.guilds, id=payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member is None or member.bot:
        return

    channel = discord.utils.get(guild.text_channels, name=AGREE_CHANNEL_NAME)
    if payload.channel_id != channel.id:
        return

    player_role = discord.utils.get(guild.roles, name=PLAYER_ROLE_NAME)
    unverified_role = discord.utils.get(guild.roles, name=UNVERIFIED_ROLE_NAME)
    if player_role:
        await member.add_roles(player_role)
    if unverified_role:
        await member.remove_roles(unverified_role)
    try:
        await member.send("✅ 你已成功同意規章，並獲得玩家身份！")
    except:
        pass

bot.run(TOKEN)
