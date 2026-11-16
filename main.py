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
        print("| BTF | Turkish Armed Forces - Koruma ve GKB Sistemi Aktif.")

bot = BTFGuardBot()
CFG = {"hq_guild": None, "central_log": None, "msg_log": None, "img_log": None, "mute_log": None, "ban_log": None, "karantina_log": None, "karantina_rol": None, "cmd_perms": {}, "tag_blacklist": [], "gkb_banli_idler": []}
YASAKLI_KELIMELER = ["kufur1", "reklamlinki"]
ROL_SILME_KONTROL = {}

def is_bot_admin(i: discord.Interaction) -> bool:
    return discord.utils.get(i.user.roles, name="Bot Yönetim +") is not None

def is_gkb(i: discord.Interaction) -> bool:
    return discord.utils.get(i.user.roles, name="Genelkurmay Başkanı") is not None or is_bot_admin(i)

def has_cmd_access(i: discord.Interaction, c: str) -> bool:
    if is_bot_admin(i): return True
    return any(r.id in CFG["cmd_perms"].get(c, []) for r in i.user.roles)

def is_blacklisted_user(m: discord.Member) -> bool:
    if not CFG["tag_blacklist"]: return False
    s = f"{m.name} {m.display_name} {getattr(getattr(m, 'primary_guild', None), 'tag', '')}".lower()
    return any(t.lower() in s for t in CFG["tag_blacklist"])

class RoleSelectForCommand(discord.ui.RoleSelect):
    def __init__(self, cmd: str):
        self.cmd = cmd
        super().__init__(placeholder=f"/{cmd} için yetkili rolleri seçin...", min_values=1, max_values=10)
    async def callback(self, i: discord.Interaction):
        CFG["cmd_perms"][self.cmd] = [r.id for r in self.values]
        await i.response.send_message(f"✅ `/{self.cmd}` komutu güncellendi.", ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self, c: str): super().__init__(timeout=60); self.add_item(RoleSelectForCommand(c))

class CmdSelectDropdown(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Komut seçin...", min_values=1, max_values=1, options=[
            discord.SelectOption(label="tamyasakla", description="Global ban talebi"),
            discord.SelectOption(label="sustur", description="Susturma komutu"),
            discord.SelectOption(label="susturmakaldir", description="Susturma kaldırma"),
            discord.SelectOption(label="rolver", description="Rol verme"),
            discord.SelectOption(label="rolal", description="Rol alma"),
            discord.SelectOption(label="karantinakaldir", description="Karantina kaldırma")
        ])
    async def callback(self, i: discord.Interaction):
        await i.response.send_message(embed=discord.Embed(title=f"🔐 `/{self.values[0]}` İzin Ayarı", description="Rolleri seçin:", color=discord.Color.blue()), view=RoleSelectView(self.values[0]), ephemeral=True)

class TagBlacklistModal(discord.ui.Modal, title="Tag Kara Liste Yönetimi"):
    islem = discord.ui.TextInput(label="İşlem Yazın (ekle / sil)", placeholder="ekle", required=True)
    tag = discord.ui.TextInput(label="Yasaklanacak Guild / Klan Tagı", placeholder="BTF", required=True)
    async def on_submit(self, i: discord.Interaction):
        t = self.tag.value.strip()
        if self.islem.value.strip().lower() == "ekle":
            if t not in CFG["tag_blacklist"]: CFG["tag_blacklist"].append(t)
            await i.response.send_message(f"🚫 `{t}` tagı kara listeye alındı.", ephemeral=True)
        else:
            if t in CFG["tag_blacklist"]: CFG["tag_blacklist"].remove(t)
            await i.response.send_message(f"✅ `{t}` tagı listeden çıkarıldı.", ephemeral=True)

class YonetimPanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Komut Yetkileri", style=discord.ButtonStyle.blurple, emoji="🔐", custom_id="yp_cmd")
    async def c(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        v = discord.ui.View(); v.add_item(CmdSelectDropdown())
        await i.response.send_message("Komut seçin:", view=v, ephemeral=True)
    @discord.ui.button(label="Tag Kara Liste", style=discord.ButtonStyle.danger, emoji="🏴", custom_id="yp_tag")
    async def t(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        await i.response.send_modal(TagBlacklistModal())

class TicketCloseView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Talebi Kapat", style=discord.ButtonStyle.danger, custom_id="c_ticket")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message("Kanal siliniyor...", ephemeral=True)
        import asyncio; await asyncio.sleep(3)
        try: await i.channel.delete()
        except: pass

class TicketCreateView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Destek Aç", style=discord.ButtonStyle.blurple, custom_id="op_ticket")
    async def create(self, i: discord.Interaction, b: discord.ui.Button):
        if is_blacklisted_user(i.user): return await i.response.send_message("🚫 Yasaklı bir guild tagına sahip olduğunuz için bota erişemezsiniz!", ephemeral=True)
        cat = discord.utils.get(i.guild.categories, name="DESTEK TALEPLERI") or await i.guild.create_category("DESTEK TALEPLERI")
        ov = {i.guild.default_role: discord.PermissionOverwrite(read_messages=False), i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), i.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await i.guild.create_text_channel(name=f"ticket-{i.user.name}", category=cat, overwrites=ov)
        rol = discord.utils.get(i.guild.roles, name="yetkili")
        await ch.send(content=f"{rol.mention if rol else '@yetkili'} Talep açıldı!", embed=discord.Embed(title="| BTF | Destek", description=f"Merhaba {i.user.mention}", color=discord.Color.blue()), view=TicketCloseView())
        await i.response.send_message(f"Kanal: {ch.mention}", ephemeral=True)

class GlobalGuardActionView(discord.ui.View):
    def __init__(self, uid: int, reason: str, kanit: str, gorsel: str):
        super().__init__(timeout=None)
        self.uid, self.reason, self.kanit, self.gorsel = uid, reason, kanit, gorsel
    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.green, custom_id="g_app")
    async def app(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_bot_admin(i): return await i.response.send_message("Yetkiniz yok!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = i.message.embeds[0]; emb.color = discord.Color.green(); emb.add_field(name="Durum", value=f"Reddedildi - {i.user.mention}", inline=False)
        await i.message.edit(view=self, embed=emb); await i.response.send_message("İptal edildi.", ephemeral=True)
    @discord.ui.button(label="Tüm Sunuculardan Yasakla", style=discord.ButtonStyle.red, custom_id="g_ban")
    async def gban(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_bot_admin(i): return await i.response.send_message("Yetkiniz yok!", ephemeral=True)
        for child in self.children: child.disabled = True
        emb = i.message.embeds[0]; emb.color = discord.Color.dark_red(); emb.add_field(name="Durum", value=f"Yasaklandı! - {i.user.mention}", inline=False)
        await i.message.edit(view=self, embed=emb)
        cnt = 0
        for g in bot.guilds:
            try:
                m = await g.fetch_member(self.uid)
                if m:
                    try:
                        dm = discord.Embed(title="🛑 Global Ban", description=f"Sebep: {self.reason}\nKanıt: {self.kanit}", color=discord.Color.red())
                        if self.gorsel: dm.set_image(url=self.gorsel)
                        await m.send(embed=dm)
                    except: pass
                    await g.ban(m, reason=f"Global Ban | {self.reason}"); cnt += 1
            except: pass
        await i.response.send_message(f"Başarılı! {cnt} sunucudan banlandı.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="| BTF | Turkish Armed Forces"))

@bot.event
async def on_member_join(m):
    if is_blacklisted_user(m) and CFG["karantina_rol"]:
        rol = m.guild.get_role(CFG["karantina_rol"])
        if rol:
            try:
                await m.add_roles(rol, reason="Kara liste tag")
                if CFG["karantina_log"]: await bot.get_channel(CFG["karantina_log"]).send(f"🏴 {m.mention} yasaklı guild tagı nedeniyle karantinaya alındı!")
            except: pass

@bot.event
async def on_member_ban(guild, user):
    if user.id in CFG["gkb_banli_idler"]:
        for g in bot.guilds:
            try:
                await g.ban(user, reason="GKB Yasaklı Kullanıcı - Manuel/Farklı Bot Kaldırma Girişimi Engellendi")
                m = await g.fetch_member(user.id)
                if m and CFG["karantina_rol"]:
                    rol = g.get_role(CFG["karantina_rol"])
                    if rol: await m.add_roles(rol, reason="GKB Ban Koruma Karantinası")
            except: pass
        if CFG["ban_log"]:
            ch = bot.get_channel(CFG["ban_log"])
            if ch: await ch.send(f"🚨 GKB Yasaklı kullanıcı ({user}) banı açılmaya çalışıldı! Bot tarafından tekrar banlandı ve karantinaya alındı.")

@bot.event
async def on_member_update(before, after):
    if is_blacklisted_user(after) and CFG["karantina_rol"]:
        rol = after.guild.get_role(CFG["karantina_rol"])
        if rol and rol not in after.roles:
            try: await after.add_roles(rol, reason="Tag güncellemesi")
            except: pass
    if before.timed_out_until and not after.timed_out_until:
        if CFG["mute_log"]: await bot.get_channel(CFG["mute_log"]).send(f"⚠️ {after.mention} susturması manuel kaldırıldı! Bot tekrar uyguladı.")
        try: await after.timeout(before.timed_out_until, reason="Koruma")
        except: pass

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    if message.attachments and CFG["img_log"]:
        await bot.get_channel(CFG["img_log"]).send(embed=discord.Embed(title="🖼️ Silinen Görsel", color=discord.Color.purple()).add_field(name="Kullanıcı", value=message.author.mention).set_image(url=message.attachments[0].url))
    if message.content and CFG["msg_log"]:
        await bot.get_channel(CFG["msg_log"]).send(embed=discord.Embed(title="🗑️ Silinen Mesaj", color=discord.Color.orange()).add_field(name="Kullanıcı", value=message.author.mention).add_field(name="İçerik", value=message.content[:1024]))

@bot.event
async def on_message(message):
    if message.author.bot: return
    if is_blacklisted_user(message.author):
        try:
            await message.delete()
            await message.channel.send(f"🚫 {message.author.mention}, yasaklı guild/klan tagına sahip olduğunuz için botu ve komutları kullanmanıza izin verilmemektedir.", delete_after=5)
        except: pass
        return
    if any(k in message.content.lower() for k in YASAKLI_KELIMELER):
        try: await message.delete(); await message.channel.send(f"{message.author.mention} yasaklı kelime!", delete_after=3)
        except: pass
        return
    await bot.process_commands(message)

@bot.tree.command(name="yonetim", description="Genel yönetim paneli.")
async def yonetim(i: discord.Interaction):
    if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.send_message(embed=discord.Embed(title="⚙️ Yönetim Paneli", description="Aşağıdaki butonları kullanın.", color=discord.Color.dark_blue()), view=YonetimPanelView(), ephemeral=True)

@bot.tree.command(name="logayarla", description="Log kanallarını ayarlar.")
async def logayarla(i: discord.Interaction, mesaj_log: discord.TextChannel, gorsel_log: discord.TextChannel, susturma_log: discord.TextChannel, ban_log: discord.TextChannel):
    if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["msg_log"], CFG["img_log"], CFG["mute_log"], CFG["ban_log"] = mesaj_log.id, gorsel_log.id, susturma_log.id, ban_log.id
    await i.response.send_message("✅ Loglar başarıyla ayarlandı.", ephemeral=True)

@bot.tree.command(name="merkezayarla", description="Merkez onay kanalını ayarlar.")
async def merkezayarla(i: discord.Interaction, kanal: discord.TextChannel):
    if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["hq_guild"], CFG["central_log"] = i.guild.id, kanal.id
    await i.response.send_message(f"✅ Merkez onay kanalı: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="karantinaayarla", description="Karantina ayarlar.")
async def karantinaayarla(i: discord.Interaction, kanal: discord.TextChannel, rol: discord.Role):
    if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["karantina_log"], CFG["karantina_rol"] = kanal.id, rol.id
    await i.response.send_message("✅ Karantina ayarlandı.", ephemeral=True)

@bot.tree.command(name="gkbyasakla", description="⭐ Yalnızca Genelkurmay Başkanı global ban atabilir.")
async def gkbyasakla(i: discord.Interaction, uye_id: str, sebep: str):
    if not is_gkb(i): return await i.response.send_message("❌ Bu komutu yalnızca **Genelkurmay Başkanı** kullanabilir!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await i.followup.send("Geçersiz ID!", ephemeral=True)
    
    if uid not in CFG["gkb_banli_idler"]: CFG["gkb_banli_idler"].append(uid)
    cnt = 0
    for g in bot.guilds:
        try:
            m = await g.fetch_member(uid)
            if m:
                await g.ban(m, reason=f"GKB Ban | {sebep}")
                if CFG["karantina_rol"]:
                    rol = g.get_role(CFG["karantina_rol"])
                    if rol: await m.add_roles(rol, reason="GKB Ban Karantinası")
                cnt += 1
        except: pass
    
    if CFG["ban_log"]:
        ch = bot.get_channel(CFG["ban_log"])
        if ch: await ch.send(embed=discord.Embed(title="⭐ GKB Yasaklama Emri", description=f"**Hedef ID:** `{uid}`\n**Sebep:** {sebep}\n**Emri Veren:** {i.user.mention}", color=discord.Color.gold()))
    await i.followup.send(f"⭐ GKB emri uygulandı. {cnt} sunucuda banlandı ve karantinaya alındı.", ephemeral=True)

@bot.tree.command(name="tamyasakla", description="Global ban talebi.")
async def tamyasakla(i: discord.Interaction, uye_id: str, sebep: str, kanit_metni: str, kanit_gorsel: str):
    if is_blacklisted_user(i.user) or not has_cmd_access(i, "tamyasakla"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await i.followup.send("Geçersiz ID!", ephemeral=True)
    if not CFG["hq_guild"] or not CFG["central_log"]: return await i.followup.send("Merkez ayarlanmamış!", ephemeral=True)
    ch = bot.get_guild(CFG["hq_guild"]).get_channel(CFG["central_log"])
    emb = discord.Embed(title="🛡️ Yasak Talebi", description=f"ID: `{uid}`\nSebep: {sebep}\nKanıt: {kanit_metni}", color=discord.Color.orange())
    emb.set_image(url=kanit_gorsel)
    await ch.send(embed=emb, view=GlobalGuardActionView(uid, sebep, kanit_metni, kanit_gorsel))
    await i.followup.send("✅ Merkeze gönderildi.", ephemeral=True)

@bot.tree.command(name="sustur", description="Susturur.")
async def sustur(i: discord.Interaction, uye: discord.Member, sure_dakika: int, sebep: str = "Belirtilmedi"):
    if is_blacklisted_user(i.user) or not has_cmd_access(i, "sustur"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.timeout(datetime.timedelta(minutes=sure_dakika), reason=sebep)
    if CFG["mute_log"]: await bot.get_channel(CFG["mute_log"]).send(f"🔇 {uye.mention} susturuldu.")
    await i.response.send_message("✅ Susturuldu.", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Ticket paneli kurar.")
async def ticketkur(i: discord.Interaction):
    if not is_bot_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.channel.send(embed=discord.Embed(title="🛡️ Destek Merkezi", color=discord.Color.dark_blue()), view=TicketCreateView())
    await i.response.send_message("✅ Panel kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
        
