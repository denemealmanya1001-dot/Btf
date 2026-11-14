import discord
from discord.ext import commands
from discord import app_commands
import datetime
from collections import defaultdict, deque

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.moderation = True
intents.guild_messages = True
intents.message_content = True

class GlobalGuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("🚀 BTF Kara Kuvvetleri Global Güvenlik ve Ticket Sistemi Senkronize Edildi.")

bot = GlobalGuardBot()

# --- AYARLAR VE YAPILANDIRMA ---
OWNER_ID = 123456789012345678          # Kendi Discord ID'ni buraya yaz
MAIN_HEADQUARTER_GUILD_ID = 0  # Ana Karargah (Merkez Log) Sunucu ID'si
CENTRAL_LOG_CHANNEL_ID = 0     # Merkez logların düşeceği kanal ID'si

YASAKLI_KELIMELER = ["küfür1", "küfür2", "reklamlinki"]
DELETE_LIMIT = 3
TIME_WINDOW = 5.0 

deleted_channels = defaultdict(deque)
deleted_roles = defaultdict(deque)

# --- 1. TICKET (DESTEK) AÇMA VE YÖNETİM PANELİ ---
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Destek Talebini Kapat", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Destek talebi kapatılıyor, kanal 5 saniye içinde silinecektir...", ephemeral=True)
        await asyncio_sleep_and_delete(interaction.channel)

async def asyncio_sleep_and_delete(channel):
    import asyncio
    await asyncio.sleep(5)
    try:
        await channel.delete(reason="Destek talebi kapatıldı.")
    except:
        pass

class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Destek Talebi Aç (Ticket)", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="DESTEK TALEPLERI")
        if not category:
            category = await guild.create_category("DESTEK TALEPLERI")

        # Kullanıcıya özel kanal oluştur
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🛡️ BTF Karargah Destek Hattı",
            description=f"Merhaba {interaction.user.mention}, yetkililer kısa süre içinde sizinle ilgilenecektir.\nTalebi kapatmak için aşağıdaki butonu kullanabilirsiniz.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Destek kanalınız oluşturuldu: {ticket_channel.mention}", ephemeral=True)


# --- 2. MERKEZİ ONAY / RED / GLOBAL YASAKLA BUTONLARI ---
class GlobalGuardActionView(discord.ui.View):
    def __init__(self, target_user_id: int, action_reason: str):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.action_reason = action_reason

    @discord.ui.button(label="Onayla (Serbest Bırak)", style=discord.ButtonStyle.green, custom_id="global_approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Yönetici yetkin olmalı!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Durum", value=f"✅ **Onaylandı** - Yetkili: {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=embed)
        await interaction.response.send_message("✅ İşlem onaylandı.", ephemeral=True)

    @discord.ui.button(label="🚨 Tüm Bot Sunucularından Tam Yasakla", style=discord.ButtonStyle.red, custom_id="global_ban")
    async def global_ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Yönetici yetkin olmalı!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_red()
        embed.add_field(name="Durum", value=f"🚨 **Tüm Sunuculardan Tam Yasaklandı!** - Yetkili: {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=embed)

        # Botun olduğu TÜM sunuculardan kullanıcıyı banla ve DM at
        success_count = 0
        for guild in bot.guilds:
            try:
                member = await guild.fetch_member(self.target_user_id)
                if member:
                    # DM Gönder
                    try:
                        dm_embed = discord.Embed(
                            title="🛑 BTF Kara Kuvvetleri - Global Yasaklama Kararı",
                            description=f"**Sunucu:** {guild.name}\n**Sebep / Kanıt:** {self.action_reason}\n\n*Botun bağlı olduğu tüm askeri/sivil sunuculardan kalıcı olarak izole edildiniz.*",
                            color=discord.Color.red()
                        )
                        await member.send(embed=dm_embed)
                    except:
                        pass
                    
                    await guild.ban(member, reason=f"Global Tam Yasaklama: {self.action_reason} (Merkez Yetkili: {interaction.user})")
                    success_count += 1
            except:
                pass

        await interaction.response.send_message(f"🚨 İşlem başarılı! Kullanıcı botun bağlı olduğu **{success_count}** farklı sunucudan tamamen yasaklandı ve bilgilendirildi.", ephemeral=True)


async def send_central_log(title, description, culprit_id: int, color=discord.Color.red()):
    """Tüm sunuculardaki olayları belirlenen ana karargah kanalına düşürür."""
    if MAIN_HEADQUARTER_GUILD_ID and CENTRAL_LOG_CHANNEL_ID:
        hq_guild = bot.get_guild(MAIN_HEADQUARTER_GUILD_ID)
        if hq_guild:
            log_channel = hq_guild.get_channel(CENTRAL_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title=f"🛡️ BTF Karargah Güvenlik Raporu | {title}",
                    description=description,
                    color=color,
                    timestamp=datetime.datetime.utcnow()
                )
                view = GlobalGuardActionView(target_user_id=culprit_id, action_reason=title)
                await log_channel.send(embed=embed, view=view)


@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name} (Global Karargah & Ticket Sistemleri Devrede)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="BTF Askeri Güvenlik 🛡️"))


# ==========================================
# 3. KÜFÜR VE REKLAM FİLTRESİ + UYARI DM
# ==========================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    mesaj_icerigi = message.content.lower()
    for kelime in YASAKLI_KELIMELER:
        if kelime in mesaj_icerigi:
            try:
                await message.delete()
                try:
                    await message.author.send(f"⚠️ **{message.guild.name}** sunucusunda yasaklı kelime kullandığınız için mesajınız engellendi!")
                except:
                    pass
                await message.channel.send(f"{message.author.mention}, bu kelime/bağlantı yasak!", delete_after=4)
            except Exception as e:
                print(f"Filtre hata: {e}")
            return

    await bot.process_commands(message)


# ==========================================
# 4. SLASH (/) KOMUTLARI
# ==========================================

# 1. Merkez Karargah Log Kanalını Ayarla
@bot.tree.command(name="merkezayarla", description="Global logların gideceği ana karargah kanalını belirler.")
@app_commands.default_permissions(administrator=True)
async def slash_merkezayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    global MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID
    MAIN_HEADQUARTER_GUILD_ID = interaction.guild.id
    CENTRAL_LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"✅ Merkez Karargah ve Log Kanalı başarıyla {kanal.mention} olarak ayarlandı!", ephemeral=True)

# 2. Global Tam Yasakla (Tüm Sunuculardan Ban + DM + Kanıt)
@bot.tree.command(name="tamyasakla", description="Bir kullanıcıyı botun bağlı olduğu TÜM sunuculardan kanıt/sebebiyle banlar.")
@app_commands.default_permissions(ban_members=True)
async def slash_tamyasakla(interaction: discord.Interaction, uye_id: str, sebep: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        target_id = int(uye_id)
    except ValueError:
        await interaction.followup.send("❌ Geçersiz kullanıcı ID'si!", ephemeral=True)
        return

    success_count = 0
    for guild in bot.guilds:
        try:
            member = await guild.fetch_member(target_id)
            if member:
                try:
                    dm_embed = discord.Embed(
                        title="🛑 BTF Kara Kuvvetleri - Global Tam Yasaklama",
                        description=f"**Yetkili:** {interaction.user}\n**Sebep / Kanıt:** {sebep}",
                        color=discord.Color.dark_red()
                    )
                    await member.send(embed=dm_embed)
                except:
                    pass
                
                await guild.ban(member, reason=f"Global Tam Yasakla Komutu | Sebep: {sebep} | Yetkili: {interaction.user}")
                success_count += 1
        except:
            pass

    await interaction.followup.send(f"🚨 İşlem tamam! Belirtilen kullanıcı botun bağlı olduğu **{success_count}** farklı sunucudan tamamen yasaklandı.", ephemeral=True)

# 3. Global Yasak Kaldır (/yasakkaldir)
@bot.tree.command(name="yasakkaldir", description="Banlanan bir kullanıcının global yasağını ID ile kaldırır.")
@app_commands.default_permissions(ban_members=True)
async def slash_yasakkaldir(interaction: discord.Interaction, uye_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        target_id = int(uye_id)
        user = await bot.fetch_user(target_id)
    except:
        await interaction.followup.send("❌ Geçerli bir kullanıcı bulunamadı.", ephemeral=True)
        return

    unban_count = 0
    for guild in bot.guilds:
        try:
            await guild.unban(user, reason=f"Global Yasak Kaldırma | Yetkili: {interaction.user}")
            unban_count += 1
        except:
            pass

    await interaction.followup.send(f"✅ {user} adlı kullanıcının yasağı **{unban_count}** sunucudan kaldırıldı.", ephemeral=True)

# 4. Bot Üzerinden Özel Mesaj (DM) Gönderme Komutu (/dm)
@bot.tree.command(name="dm", description="Bot üzerinden dilediğiniz kullanıcıya özel mesaj (DM) gönderir.")
@app_commands.default_permissions(administrator=True)
async def slash_dm(interaction: discord.Interaction, uye: discord.Member, mesaj: str):
    await interaction.response.defer(ephemeral=True)
    try:
        dm_embed = discord.Embed(
            title="📢 BTF Karargah Resmi Bildirimi",
            description=mesaj,
            color=discord.Color.gold()
        )
        dm_embed.set_footer(text=f"Gönderen Yetkili: {interaction.user}")
        await uye.send(embed=dm_embed)
        await interaction.followup.send(f"✅ Mesaj başarıyla {uye.mention} adlı kullanıcıya özelden iletildi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Kullanıcıya mesaj atılamadı (DM kutusu kapalı olabilir): {e}", ephemeral=True)

# 5. Ticket (Destek) Paneli Kurulum Komutu
@bot.tree.command(name="ticketkur", description="Kullanıcıların destek talebi açabileceği butonlu paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def slash_ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ BTF Kara Kuvvetleri Destek ve İletişim Merkezi",
        description="Yetkililerle iletişime geçmek, sorun bildirmek veya destek almak için aşağıdaki **Destek Talebi Aç** butonuna tıklayınız.",
        color=discord.Color.dark_blue()
    )
    await interaction.channel.send(embed=embed, view=TicketCreateView())
    await interaction.response.send_message("✅ Destek paneli bu kanala başarıyla kuruldu!", ephemeral=True)


# Bot tokenini buraya yapıştır
bot.run("TOKEN")
