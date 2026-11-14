import discord
from discord.ext import commands
import datetime
from collections import defaultdict, deque

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- AYARLAR VE LİSTELER ---
OWNER_ID = KENDI_DISCORD_IDIN # Kendi Discord ID'ni buraya yaz (rakam olarak)
LOG_CHANNEL_ID = 0            # Guard loglarının gideceği kanal ID'si (İstersen sonradan yazabilirsin)

# Anti-Nuke eşikleri (Örn: 5 saniyede 3'ten fazla silme yapılırsa)
DELETE_LIMIT = 3
TIME_WINDOW = 5.0 

deleted_channels = defaultdict(deque)
deleted_roles = defaultdict(deque)

async def send_log(guild, title, description, color=discord.Color.red()):
    print(f"[GUARD ALERT] {title} - {description}")
    if LOG_CHANNEL_ID:
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title=f"🛡️ Guard Alarmı | {title}", description=description, color=color, timestamp=datetime.datetime.utcnow())
            await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name} (Guard Modu Devrede)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Sunucu Güvenliği 🛡️"))

# 1. ANTİ-BOT KORUMASI (İzinsiz Bot Ekleme)
@bot.event
async def on_member_join(member):
    if member.bot:
        guild = member.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
            if entry.target.id == member.id:
                executor = entry.user
                if executor.id != guild.owner_id and executor.id != OWNER_ID:
                    try:
                        await guild.ban(member, reason="İzinsiz bot eklendi (Guard)")
                        await guild.ban(executor, reason="Sunucuya izinsiz bot eklediği için banlandı (Guard)")
                        await send_log(
                            guild, 
                            "İzinsiz Bot Eklendi!", 
                            f"**Eklenen Bot:** {member} (`{member.id}`)\n**Ekleyen Kişi:** {executor} (`{executor.id}`)\n*Her ikisi de sunucudan uzaklaştırıldı.*"
                        )
                    except Exception as e:
                        print(f"Anti-bot işlem hatası: {e}")
                break

# 2. ANTİ-NUKE: KANAL SİLME KORUMASI
@bot.event
async def on_guild_channel_delete(channel):
    guild = channel.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        executor = entry.user
        if executor.id == guild.owner_id or executor.id == OWNER_ID or executor.bot:
            return

        now = datetime.datetime.now().timestamp()
        user_deletes = deleted_channels[executor.id]
        while user_deletes and now - user_deletes[0] > TIME_WINDOW:
            user_deletes.popleft()
        user_deletes.append(now)
        
        if len(user_deletes) > DELETE_LIMIT:
            try:
                await guild.ban(executor, reason="Toplu kanal silme sınırı aşıldı (Anti-Nuke)")
                await send_log(
                    guild, 
                    "Anti-Nuke Tetiklendi (Kanal Silme)!", 
                    f"**Yetkili:** {executor} (`{executor.id}`)\n*Kısa sürede çok fazla kanal sildiği için banlandı.*"
                )
            except Exception as e:
                print(f"Kanal nuke koruma hatası: {e}")
        break

# 3. ANTİ-NUKE: ROL SİLME KORUMASI
@bot.event
async def on_guild_role_delete(role):
    guild = role.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        executor = entry.user
        if executor.id == guild.owner_id or executor.id == OWNER_ID or executor.bot:
            return

        now = datetime.datetime.now().timestamp()
        user_deletes = deleted_roles[executor.id]
        while user_deletes and now - user_deletes[0] > TIME_WINDOW:
            user_deletes.popleft()
        user_deletes.append(now)
        
        if len(user_deletes) > DELETE_LIMIT:
            try:
                await guild.ban(executor, reason="Toplu rol silme sınırı aşıldı (Anti-Nuke)")
                await send_log(
                    guild, 
                    "Anti-Nuke Tetiklendi (Rol Silme)!", 
                    f"**Yetkili:** {executor} (`{executor.id}`)\n*Kısa sürede çok fazla rol sildiği için banlandı.*"
                )
            except Exception as e:
                print(f"Rol nuke koruma hatası: {e}")
        break

bot.run("MTU3MTE1NTE0NDY4MTIwMTc4NQ.G3F1hx.hPq8P8IjxKFgwQUaTBsKt8Yukjv4t_yDtw2ucw")
