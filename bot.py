import discord
from discord.ext import commands, tasks
import socket

intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = "MTM2MDg2MTc3NDQyOTE2MzU1MA.G7Pvrg.U_sRbIOZ7dEA9Oira70oIRdSan1nkw1yrP0haQ"
REACTION_EMOJI = "✅"
AGREE_CHANNEL_NAME = "✅｜agree-to-join"
PLAYER_ROLE_NAME = "玩家"
UNVERIFIED_ROLE_NAME = "未驗證"

SERVER_STATUS_CHANNEL_NAME = "伺服器狀態"
SERVERS_TO_MONITOR = [
    {"name": "Login Server", "ip": "127.0.0.1", "port": 6900},
    {"name": "Char Server", "ip": "127.0.0.1", "port": 6121},
    {"name": "Map Server", "ip": "127.0.0.1", "port": 5121},
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
        # 建立頻道
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
