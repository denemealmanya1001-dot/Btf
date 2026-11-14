import os
import discord
from discord.ext import commands
from discord import app_commands
import datetime

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.guild_messages = True
intents.moderation = True

class BTFGuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self):
        await self.tree.sync()
        print("| BTF | Kesin Yetki ve Koruma Sistemi Aktif.")

bot = BTFGuardBot()

MAIN_HEADQUARTER_GUILD_ID = None  
CENTRAL_LOG_CHANNEL_ID = None     
MESSAGE_LOG_CHANNEL_ID = None     
KARANTINA_LOG_CHANNEL_ID = None   
KARANTINA_ROL_ID = None           

YASAKLI_KELIMELER = ["kufur1", "reklamlinki"]
ROL_SILME_KONTROL = {}
KOMUT_IZINLERI = {}

# Sadece ve sadece "Bot Yönetim +" rolü olanlar işlem yapabilir (Adminler bile geçemez)
def bot_yonetim_kontrol(interaction: discord.Interaction) -> bool:
    return discord.utils.get(interaction.user.roles, name="Bot Yönetim +") is not None

class TicketCloseView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Talebi Kapat", style=discord.ButtonStyle.danger, custom_id="c_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Kanal siliniyor...", ephemeral=True)
        import asyncio; await asyncio.sleep(3)
        try: await interaction.channel.delete()
        except: pass

class TicketCreateView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Destek Aç", style=discord.ButtonStyle.blurple, custom_id="op_ticket")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        cat = discord.utils.get(guild.categories, name="DESTEK TALEPLERI") or await guild.create_category("DESTEK TALEPLERI")
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=cat, overwrites=overwrites)
        rol = discord.utils.get(guild.roles, name="yetkili")
        await ch.send(content=f"{rol.mention if rol else '@yetkili'} Talep açıldı!", embed=discord.Embed(title="| BTF | Destek", description=f"Merhaba {interaction.user.mention}", color=discord.Color.blue()), view=TicketCloseView())
        await interaction.response.send_message(f"Kanal: {ch.mention}", ephemeral=True)

class GlobalGuardActionView(discord.ui.View):
    def __init__(self, uid: int, reason: str, kanit: str, gorsel: str):
        super().__init__(timeout=None)
        self.uid, self.reason, self.kanit, self.gorsel = uid, reason, kanit, gorsel

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.green, custom_id="g_app")
    async def app(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** rolüne sahip olanlar onaylayabilir!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = interaction.message.embeds[0]; emb.color = discord.Color.green(); emb.add_field(name="Durum", value=f"Reddedildi - {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=emb)
        await interaction.response.send_message("İşlem iptal edildi.", ephemeral=True)

    @discord.ui.button(label="Tüm Sunuculardan Yasakla", style=discord.ButtonStyle.red, custom_id="g_ban")
    async def gban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** rolüne sahip olanlar onaylayabilir!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = interaction.message.embeds[0]; emb.color = discord.Color.dark_red(); emb.add_field(name="Durum", value=f"Onaylandı ve Yasaklandı! - {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=emb)
        count = 0
        for g in bot.guilds:
            try:
                m = await g.fetch_member(self.uid)
                if m:
                    try:
                        dm = discord.Embed(title="🛑 | BTF | Global Yasaklama", description=f"Sebep: {self.reason}\nKanıt: {self.kanit}", color=discord.Color.red())
                        if self.gorsel: dm.set_image(url=self.gorsel)
                        await m.send(embed=dm)
                    except: pass
                    await g.ban(m, reason=f"Global Ban | {self.reason}")
                    count += 1
            except: pass
        await interaction.response.send_message(f"Başarılı! {count} sunucudan yasaklandı.", ephemeral=True)

class KomutSecimSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="tamyasakla", description="Global ban talebi komutu", emoji="🛡️"),
            discord.SelectOption(label="sustur", description="Kullanıcı susturma komutu", emoji="🔇"),
            discord.SelectOption(label="karantinakaldir", description="Karantina kaldırma komutu", emoji="🔓")
        ]
        super().__init__(placeholder="Yönetmek istediğiniz komutu seçin...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"📌 `{self.values[0]}` komutu için yetki ayar paneli aktif.", ephemeral=True)

class KomutYetkiPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(KomutSecimSelect())

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="| BTF | Turkish Armed Forces"))

@bot.event
async def on_member_update(before, after):
    if before.timed_out_until and not after.timed_out_until:
        if KARANTINA_LOG_CHANNEL_ID:
            ch = bot.get_channel(KARANTINA_LOG_CHANNEL_ID)
            if ch: await ch.send(f"⚠️ Dikkat! {after.mention} adlı kullanıcının susturması manuel kaldırıldı! Bot tekrar uyguluyor.")
        try: await after.timeout(before.timed_out_until, reason="Manuel susturma kaldırma engellendi.")
        except: pass

    if len(before.roles) > len(after.roles):
        now = datetime.datetime.utcnow().timestamp()
        guild = after.guild
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                actor = entry.user
                if actor.bot: return
                uid = actor.id
                ROL_SILME_KONTROL.setdefault(uid, []).append(now)
                ROL_SILME_KONTROL[uid] = [t for t in ROL_SILME_KONTROL[uid] if now - t < 10]
                if len(ROL_SILME_KONTROL[uid]) > 3 and KARANTINA_ROL_ID:
                    member_actor = guild.get_member(uid)
                    kar_rol = guild.get_role(KARANTINA_ROL_ID)
                    if member_actor and kar_rol and kar_rol not in member_actor.roles:
                        await member_actor.add_roles(kar_rol, reason="Ard arda 3'ten fazla rol silme limiti aşıldı.")
                        if KARANTINA_LOG_CHANNEL_ID:
                            ch = bot.get_channel(KARANTINA_LOG_CHANNEL_ID)
                            if ch: await ch.send(f"🚨 Güvenlik Uyarısı: {member_actor.mention} çok fazla rol sildiği için karantinaya alındı!")
        except: pass

@bot.event
async def on_message_delete(message):
    if message.author.bot or not MESSAGE_LOG_CHANNEL_ID: return
    ch = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if ch:
        emb = discord.Embed(title="🗑️ | BTF | Silinen Mesaj", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
        emb.add_field(name="Kullanıcı", value=f"{message.author.mention}", inline=False)
        if message.content: emb.add_field(name="İçerik", value=message.content[:1024], inline=False)
        if message.attachments: emb.set_image(url=message.attachments[0].url)
        await ch.send(embed=emb)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(k in message.content.lower() for k in YASAKLI_KELIMELER):
        try: await message.delete(); await message.author.send("Yasaklı kelime!"); await message.channel.send(f"{message.author.mention} yasak!", delete_after=3)
        except: pass
        return
    await bot.process_commands(message)

@bot.tree.command(name="komutyetki", description="⭐ Komutların kimler tarafından kullanılabileceğini ayarlama paneli.")
async def komutyetki(interaction: discord.Interaction):
    if not bot_yonetim_kontrol(interaction):
        return await interaction.response.send_message("❌ Bu paneli yalnızca **Bot Yönetim +** rolüne sahip olanlar açabilir!", ephemeral=True)
    
    emb = discord.Embed(
        title="⚙️ | BTF | Komut Erişim ve Yetki Paneli",
        description="Aşağıdaki menüden hangi komutun yetkilerini yapılandırmak istediğinizi seçin.\n*(Yalnızca Bot Yönetim + yetkilileri erişebilir)*",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=emb, view=KomutYetkiPanelView(), ephemeral=True)

@bot.tree.command(name="merkezayarla", description="Merkez log.")
@app_commands.default_permissions(administrator=True)
async def merkezayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** kullanabilir!", ephemeral=True)
    global MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID
    MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID = interaction.guild.id, kanal.id
    await interaction.response.send_message(f"✅ Merkez: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="logayarla", description="Mesaj log.")
@app_commands.default_permissions(administrator=True)
async def logayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** kullanabilir!", ephemeral=True)
    global MESSAGE_LOG_CHANNEL_ID
    MESSAGE_LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"✅ Mesaj Log: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="karantinaayarla", description="Karantina log ve rolü ayarlar.")
@app_commands.default_permissions(administrator=True)
async def karantinaayarla(interaction: discord.Interaction, kanal: discord.TextChannel, rol: discord.Role):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** kullanabilir!", ephemeral=True)
    global KARANTINA_LOG_CHANNEL_ID, KARANTINA_ROL_ID
    KARANTINA_LOG_CHANNEL_ID, KARANTINA_ROL_ID = kanal.id, rol.id
    await interaction.response.send_message(f"✅ Karantina Kanal: {kanal.mention} | Rol: {rol.mention}", ephemeral=True)

@bot.tree.command(name="karantinakaldir", description="Karantinayı sadece Bot Yönetim + kaldırabilir.")
async def karantinakaldir(interaction: discord.Interaction, uye: discord.Member):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Bu komutu yalnızca **Bot Yönetim +** yetkilileri kullanabilir!", ephemeral=True)
    if KARANTINA_ROL_ID:
        rol = interaction.guild.get_role(KARANTINA_ROL_ID)
        if rol in uye.roles:
            await uye.remove_roles(rol, reason=f"Bot Yönetim Tarafından Kaldırıldı: {interaction.user}")
            return await interaction.response.send_message(f"✅ {uye.mention} karantinadan çıkarıldı.", ephemeral=True)
    await interaction.response.send_message("❌ Kullanıcı karantinada değil veya rol bulunamadı.", ephemeral=True)

@bot.tree.command(name="sustur", description="Susturur.")
@app_commands.default_permissions(moderate_members=True)
async def sustur(interaction: discord.Interaction, uye: discord.Member, sure_dakika: int, sebep: str = "Belirtilmedi"):
    await uye.timeout(datetime.timedelta(minutes=sure_dakika), reason=sebep)
    await interaction.response.send_message(f"✅ {uye.mention} susturuldu.", ephemeral=True)

@bot.tree.command(name="susturmakaldir", description="Susturmayı kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def susturmakaldir(interaction: discord.Interaction, uye: discord.Member):
    await uye.timeout(None, reason="Susturma kaldırıldı")
    await interaction.response.send_message(f"✅ {uye.mention} susturması kaldırıldı.", ephemeral=True)

@bot.tree.command(name="tamyasakla", description="Zorunlu kanıt ve görsel ile ban.")
async def tamyasakla(interaction: discord.Interaction, uye_id: str, sebep: str, kanit_metni: str, kanit_gorsel: str):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Bu komutu yalnızca **Bot Yönetim +** kullanabilir!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await interaction.followup.send("Geçersiz ID!", ephemeral=True)
    if not MAIN_HEADQUARTER_GUILD_ID or not CENTRAL_LOG_CHANNEL_ID:
        return await interaction.followup.send("Önce /merkezayarla yapın!", ephemeral=True)
    ch = bot.get_guild(MAIN_HEADQUARTER_GUILD_ID).get_channel(CENTRAL_LOG_CHANNEL_ID)
    emb = discord.Embed(title="🛡️ | BTF | Yasak Talebi", description=f"ID: `{uid}`\nSebep: {sebep}\nKanıt: {kanit_metni}", color=discord.Color.orange())
    emb.set_image(url=kanit_gorsel)
    await ch.send(embed=emb, view=GlobalGuardActionView(uid, sebep, kanit_metni, kanit_gorsel))
    await interaction.followup.send("✅ Merkeze gönderildi.", ephemeral=True)

@bot.tree.command(name="yasakkaldir", description="Yasağı kaldırır.")
@app_commands.default_permissions(ban_members=True)
async def yasakkaldir(interaction: discord.Interaction, uye_id: str):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** kullanabilir!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try: user = await bot.fetch_user(int(uye_id))
    except: return await interaction.followup.send("Kullanıcı bulunamadı.", ephemeral=True)
    count = 0
    for g in bot.guilds:
        try: await g.unban(user, reason="Unban"); count += 1
        except: pass
    await interaction.followup.send(f"✅ {count} sunucudan kaldırıldı.", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Ticket paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def ticketkur(interaction: discord.Interaction):
    if not bot_yonetim_kontrol(interaction): return await interaction.response.send_message("❌ Yalnızca **Bot Yönetim +** kullanabilir!", ephemeral=True)
    await interaction.channel.send(embed=discord.Embed(title="🛡️ | BTF | Destek Merkezi", description="Destek için tıklayın.", color=discord.Color.dark_blue()), view=TicketCreateView())
    await interaction.response.send_message("✅ Panel kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
                
