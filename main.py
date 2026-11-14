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
        print("| BTF | Turkish Armed Forces - Sistem Aktif.")

bot = BTFGuardBot()

MAIN_HEADQUARTER_GUILD_ID = None  
CENTRAL_LOG_CHANNEL_ID = None     
MESSAGE_LOG_CHANNEL_ID = None     

YASAKLI_KELIMELER = ["kufur1", "kufur2", "reklamlinki"]

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Destek Talebini Kapat", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Destek talebi kapatiliyor...", ephemeral=True)
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason="Destek kapatildi.")
        except:
            pass

class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Destek Talebi Ac", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        cat = discord.utils.get(guild.categories, name="DESTEK TALEPLERI") or await guild.create_category("DESTEK TALEPLERI")
        overwrites = {guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=cat, overwrites=overwrites)
        rol = discord.utils.get(guild.roles, name="yetkili")
        await ch.send(content=f"{rol.mention if rol else '@yetkili'} Yeni talep açıldı!", embed=discord.Embed(title="| BTF | Destek", description=f"Merhaba {interaction.user.mention}, yetkililer ilgilenecektir.", color=discord.Color.blue()), view=TicketCloseView())
        await interaction.response.send_message(f"Kanal: {ch.mention}", ephemeral=True)

class GlobalGuardActionView(discord.ui.View):
    def __init__(self, uid: int, reason: str, kanit: str, gorsel: str = None):
        super().__init__(timeout=None)
        self.uid, self.reason, self.kanit, self.gorsel = uid, reason, kanit, gorsel

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.green, custom_id="g_app")
    async def app(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator and not discord.utils.get(interaction.user.roles, name="Yasak Yetkilisi"):
            return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.add_field(name="Durum", value=f"Reddedildi - {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=emb)
        await interaction.response.send_message("İşlem iptal edildi.", ephemeral=True)

    @discord.ui.button(label="Tüm Sunuculardan Yasakla", style=discord.ButtonStyle.red, custom_id="g_ban")
    async def gban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator and not discord.utils.get(interaction.user.roles, name="Yasak Yetkilisi"):
            return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.dark_red()
        emb.add_field(name="Durum", value=f"Onaylandı ve Yasaklandı! - {interaction.user.mention}", inline=False)
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

class GenelkurmayGuardActionView(discord.ui.View):
    def __init__(self, uid: int, reason: str, kanit: str, gorsel: str = None):
        super().__init__(timeout=None)
        self.uid, self.reason, self.kanit, self.gorsel = uid, reason, kanit, gorsel

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.green, custom_id="gk_app")
    async def app(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator and not discord.utils.get(interaction.user.roles, name="Genelkurmay Başkanı"):
            return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.green()
        emb.add_field(name="Durum", value=f"Genelkurmay Reddedildi - {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=emb)
        await interaction.response.send_message("Genelkurmay emri reddetti.", ephemeral=True)

    @discord.ui.button(label="Genelkurmay Onayı İle Yasakla", style=discord.ButtonStyle.red, custom_id="gk_ban")
    async def gban(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator and not discord.utils.get(interaction.user.roles, name="Genelkurmay Başkanı"):
            return await interaction.response.send_message("Yetkiniz yok!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = interaction.message.embeds[0]
        emb.color = discord.Color.gold()
        emb.add_field(name="Durum", value=f"⭐ Genelkurmay Onayladı ve Yasaklandı! - {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=emb)
        count = 0
        for g in bot.guilds:
            try:
                m = await g.fetch_member(self.uid)
                if m:
                    try:
                        dm = discord.Embed(title="⭐ | BTF | Genelkurmay Kararı", description=f"Sebep: {self.reason}\nKanıt: {self.kanit}", color=discord.Color.gold())
                        if self.gorsel: dm.set_image(url=self.gorsel)
                        await m.send(embed=dm)
                    except: pass
                    await g.ban(m, reason=f"Genelkurmay Ban | {self.reason}")
                    count += 1
            except: pass
        await interaction.response.send_message(f"Genelkurmay emri uygulandı! {count} sunucudan yasaklandı.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="| BTF | Turkish Armed Forces"))

@bot.event
async def on_message_delete(message):
    if message.author.bot or not MESSAGE_LOG_CHANNEL_ID: return
    ch = bot.get_channel(MESSAGE_LOG_CHANNEL_ID)
    if ch:
        emb = discord.Embed(title="🗑️ | BTF | Silinen Mesaj", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
        emb.add_field(name="Kullanıcı", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        emb.add_field(name="Kanal", value=f"{message.channel.mention}", inline=False)
        if message.content: emb.add_field(name="İçerik", value=message.content[:1024], inline=False)
        if message.attachments:
            emb.set_image(url=message.attachments[0].url)
            emb.add_field(name="Görsel", value=message.attachments[0].url, inline=False)
        await ch.send(embed=emb)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(k in message.content.lower() for k in YASAKLI_KELIMELER):
        try:
            await message.delete()
            await message.author.send("| BTF | Yasaklı kelime engellendi!")
            await message.channel.send(f"{message.author.mention}, yasaklı kelime!", delete_after=4)
        except: pass
        return
    await bot.process_commands(message)

@bot.tree.command(name="merkezayarla", description="Log kanalını ayarlar.")
@app_commands.default_permissions(administrator=True)
async def merkezayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    global MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID
    MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID = interaction.guild.id, kanal.id
    await interaction.response.send_message(f"✅ Merkez: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="logayarla", description="Silinen mesaj log kanalını ayarlar.")
@app_commands.default_permissions(administrator=True)
async def logayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    global MESSAGE_LOG_CHANNEL_ID
    MESSAGE_LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"✅ Mesaj Log: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="sustur", description="Kullanıcıyı susturur.")
@app_commands.default_permissions(moderate_members=True)
async def sustur(interaction: discord.Interaction, uye: discord.Member, sure_dakika: int, sebep: str = "Belirtilmedi"):
    await uye.timeout(datetime.timedelta(minutes=sure_dakika), reason=sebep)
    await interaction.response.send_message(f"✅ {uye.mention} susturuldu.", ephemeral=True)

@bot.tree.command(name="susturmakaldir", description="Susturmayı kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def susturmakaldir(interaction: discord.Interaction, uye: discord.Member):
    await uye.timeout(None, reason="Susturma kaldırıldı")
    await interaction.response.send_message(f"✅ {uye.mention} susturması kaldırıldı.", ephemeral=True)

@bot.tree.command(name="tamyasakla", description="Yasak yetkilisi ban talebi.")
async def tamyasakla(interaction: discord.Interaction, uye_id: str, sebep: str, kanit_metni: str, kanit_gorsel_linki: str = None):
    if not interaction.user.guild_permissions.administrator and not discord.utils.get(interaction.user.roles, name="Yasak Yetkilisi"):
        return await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await interaction.followup.send("Geçersiz ID!", ephemeral=True)
    if not MAIN_HEADQUARTER_GUILD_ID or not CENTRAL_LOG_CHANNEL_ID:
        return await interaction.followup.send("Önce /merkezayarla yapın!", ephemeral=True)
    ch = bot.get_guild(MAIN_HEADQUARTER_GUILD_ID).get_channel(CENTRAL_LOG_CHANNEL_ID)
    emb = discord.Embed(title="🛡️ | BTF | Yasak Onay Talebi", description=f"ID: `{uid}`\nSebep: {sebep}\nKanıt: {kanit_metni}", color=discord.Color.orange())
    if kanit_gorsel_linki: emb.set_image(url=kanit_gorsel_linki)
    await ch.send(embed=emb, view=GlobalGuardActionView(uid, sebep, kanit_metni, kanit_gorsel_linki))
    await interaction.followup.send("✅ Talep merkeze gönderildi.", ephemeral=True)

@bot.tree.command(name="globalyasakla", description="⭐ Genelkurmay başkanı global ban emri.")
async def globalyasakla(interaction: discord.Interaction, uye_id: str, sebep: str, kanit_metni: str, kanit_gorsel_linki: str = None):
    if not interaction.user.guild_permissions.administrator and not discord.utils.get(interaction.user.roles, name="Genelkurmay Başkanı"):
        return await interaction.response.send_message("❌ Yalnızca Genelkurmay Başkanı kullanabilir!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await interaction.followup.send("Geçersiz ID!", ephemeral=True)
    if not MAIN_HEADQUARTER_GUILD_ID or not CENTRAL_LOG_CHANNEL_ID:
        return await interaction.followup.send("Önce /merkezayarla yapın!", ephemeral=True)
    ch = bot.get_guild(MAIN_HEADQUARTER_GUILD_ID).get_channel(CENTRAL_LOG_CHANNEL_ID)
    emb = discord.Embed(title="⭐ | BTF | Genelkurmay Yasak Emri", description=f"ID: `{uid}`\nSebep: {sebep}\nKanıt: {kanit_metni}", color=discord.Color.gold())
    if kanit_gorsel_linki: emb.set_image(url=kanit_gorsel_linki)
    await ch.send(embed=emb, view=GenelkurmayGuardActionView(uid, sebep, kanit_metni, kanit_gorsel_linki))
    await interaction.followup.send("⭐ Genelkurmay emri merkeze iletildi.", ephemeral=True)

@bot.tree.command(name="yasakkaldir", description="Yasağı kaldırır.")
@app_commands.default_permissions(ban_members=True)
async def yasakkaldir(interaction: discord.Interaction, uye_id: str):
    await interaction.response.defer(ephemeral=True)
    try: user = await bot.fetch_user(int(uye_id))
    except: return await interaction.followup.send("Kullanıcı bulunamadı.", ephemeral=True)
    count = 0
    for g in bot.guilds:
        try: await g.unban(user, reason="Global Unban"); count += 1
        except: pass
    await interaction.followup.send(f"✅ Yasak {count} sunucudan kaldırıldı.", ephemeral=True)

@bot.tree.command(name="rolver", description="Rol verir.")
@app_commands.default_permissions(manage_roles=True)
async def rolver(interaction: discord.Interaction, uye: discord.Member, rol: discord.Role):
    await uye.add_roles(rol, reason="Bot komutu")
    await interaction.response.send_message(f"✅ {uye.mention} adlı kişiye {rol.mention} verildi.", ephemeral=True)

@bot.tree.command(name="rolal", description="Rol alır.")
@app_commands.default_permissions(manage_roles=True)
async def rolal(interaction: discord.Interaction, uye: discord.Member, rol: discord.Role):
    await uye.remove_roles(rol, reason="Bot komutu")
    await interaction.response.send_message(f"✅ {uye.mention} adlı kişiden {rol.mention} alındı.", ephemeral=True)

@bot.tree.command(name="dm", description="DM gönderir.")
@app_commands.default_permissions(administrator=True)
async def dm(interaction: discord.Interaction, uye: discord.Member, mesaj: str):
    await uye.send(embed=discord.Embed(title="📢 | BTF | Bildiri", description=mesaj, color=discord.Color.gold()))
    await interaction.response.send_message("✅ Mesaj iletildi.", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Ticket paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def ticketkur(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(title="🛡️ | BTF | Destek Merkezi", description="Destek açmak için butona tıklayın.", color=discord.Color.dark_blue()), view=TicketCreateView())
    await interaction.response.send_message("✅ Panel kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
