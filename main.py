import os, datetime, asyncio, json, discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.guilds = intents.members = intents.message_content = intents.guild_messages = intents.moderation = True

CONFIG_FILE = "config.json"
DEFAULT_CFG = {
    "hq": None, "clog": None, "mlog": None, "ilog": None, "slog": None, "blog": None, "klog": None,
    "perms": {}, "tags": [], "gkb_bans": [], "limit": 3, "guard": True, "chan_limit": 2, "admin_guard": True,
    "ticket_title": "Destek Merkezi", "ticket_desc": "Destek açmak için aşağıdaki butona tıklayın.", "ticket_cats": {}, "ticket_roles": {},
    "master_users": ["metexl0", "nexon"], "ban_records": {}
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_CFG.items():
                    if k not in data: data[k] = v
                return data
        except: pass
    return DEFAULT_CFG.copy()

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(CFG, f, ensure_ascii=False, indent=4)
    except: pass

CFG = load_config()

class BTFGuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self): await self.tree.sync(); print("| BTF | Turkish Armed Forces - Doğal Süre ve Kanıtlı Susturma Aktif.")

bot = BTFGuardBot()
YASAKLI = ["kufur1", "reklamlinki"]
ROL_SILME = {}
KANAL_SILME = {}
TAG_UYARI = "Guild Tagını Kullanmakta Olduğunuz Sunucunun Bot Kullanımı Yasaklanmıştır. Botu Kullanmak İçin Tagı Değiştirin/Kaldırın !"

def parse_time(time_str: str) -> int:
    time_str = time_str.lower().strip()
    total_minutes = 0
    parts = time_str.split()
    i = 0
    while i < len(parts):
        try:
            val = int(parts[i])
            if i + 1 < len(parts):
                unit = parts[i+1]
                if "dakika" in unit or unit.startswith("d") or unit == "m": total_minutes += val
                elif "saat" in unit or unit.startswith("s") or unit == "h": total_minutes += val * 60
                elif "gün" in unit or unit.startswith("g") or unit == "d": total_minutes += val * 1440
                elif "hafta" in unit or unit.startswith("h") or unit == "w": total_minutes += val * 10080
                elif "ay" in unit or unit.startswith("a"): total_minutes += val * 43200
                i += 2
            else:
                total_minutes += val; i += 1
        except: i += 1
    return total_minutes if total_minutes > 0 else 60

def is_master(u: discord.User) -> bool: return u.name.lower() in CFG["master_users"]
def is_admin(i: discord.Interaction) -> bool:
    if is_master(i.user): return True
    return discord.utils.get(i.user.roles, name="Bot Yönetim +") is not None
def is_gkb(i: discord.Interaction) -> bool:
    if is_master(i.user): return True
    return discord.utils.get(i.user.roles, name="Genelkurmay Başkanı") is not None or is_admin(i)
def has_perm(i: discord.Interaction, c: str) -> bool:
    if is_master(i.user) or is_admin(i): return True
    return any(r.id in CFG["perms"].get(c, []) for r in i.user.roles)
def is_bl(m: discord.Member) -> bool:
    if is_master(m): return False
    if not CFG["tags"]: return False
    s = f"{m.name} {m.display_name} {getattr(getattr(m, 'primary_guild', None), 'tag', '')}".lower()
    return any(t.lower() in s for t in CFG["tags"])

class RoleSelectCmd(discord.ui.RoleSelect):
    def __init__(self, cmd: str):
        self.cmd = cmd
        super().__init__(placeholder=f"/{cmd} için yetkili rolleri seçin...", min_values=1, max_values=10)
    async def callback(self, i: discord.Interaction):
        CFG["perms"][self.cmd] = [r.id for r in self.values]; save_config()
        await i.response.send_message(f"✅ `/{self.cmd}` yetkileri güncellendi.", ephemeral=True)

class CmdSelect(discord.ui.Select):
    def __init__(self):
        opts = [discord.SelectOption(label=x) for x in ["tam-yasak-at", "tam-yasak-kaldır", "sustur", "susturma-kaldır", "rol-ver", "rol-al", "yasak-sorgu", "dm-mesaj", "duyur"]]
        super().__init__(placeholder="Komut seçin...", options=opts)
    async def callback(self, i: discord.Interaction):
        v = discord.ui.View(timeout=60); v.add_item(RoleSelectCmd(self.values[0]))
        await i.response.send_message(f"🔐 `/{self.values[0]}` için rolleri seçin:", view=v, ephemeral=True)

class TagModal(discord.ui.Modal, title="Tag Kara Liste Yönetimi"):
    islem = discord.ui.TextInput(label="İşlem (ekle / sil)", placeholder="ekle", required=True)
    tag = discord.ui.TextInput(label="Yasaklanacak Guild / Klan Tagı", placeholder="BTF", required=True)
    async def on_submit(self, i: discord.Interaction):
        t = self.tag.value.strip()
        if self.islem.value.strip().lower() == "ekle":
            if t not in CFG["tags"]: CFG["tags"].append(t); save_config()
            await i.response.send_message(f"🚫 `{t}` kara listeye alındı.", ephemeral=True)
        else:
            if t in CFG["tags"]: CFG["tags"].remove(t); save_config()
            await i.response.send_message(f"✅ `{t}` listeden çıkarıldı.", ephemeral=True)

class GuardModal(discord.ui.Modal, title="Guard Limit Ayarları"):
    kan_lim = discord.ui.TextInput(label="Kanal Silme Sınırı", placeholder="2", required=True)
    async def on_submit(self, i: discord.Interaction):
        try:
            CFG["chan_limit"] = int(self.kan_lim.value.strip()); save_config()
            await i.response.send_message("✅ Guard sınırları güncellendi.", ephemeral=True)
        except: await i.response.send_message("❌ Geçersiz sayı!", ephemeral=True)

class DuyuruModal(discord.ui.Modal, title="Resmi Duyuru Paneli"):
    baslik = discord.ui.TextInput(label="Başlık", placeholder="Duyuru Başlığı", required=True)
    duyuru_metni = discord.ui.TextInput(label="Duyuru", placeholder="Duyuru içeriği...", style=discord.TextStyle.paragraph, required=True)
    tag = discord.ui.TextInput(label="Tag", placeholder="[BTF]", required=True)
    unvan = discord.ui.TextInput(label="Atayanın Unvanı", placeholder="Genelkurmay Başkanı", required=True)
    def __init__(self, kanal: discord.TextChannel): super().__init__(); self.kanal = kanal
    async def on_submit(self, i: discord.Interaction):
        emb = discord.Embed(title=f"📢 {self.baslik.value}", description=self.duyuru_metni.value, color=discord.Color.gold())
        emb.add_field(name="Tag / Unvan", value=f"`{self.tag.value}` - **{self.unvan.value}**", inline=False)
        emb.set_footer(text=f"Yayınlayan: {i.user.name}", icon_url=i.user.display_avatar.url)
        await self.kanal.send(content="@everyone", embed=emb)
        await i.response.send_message(f"✅ Duyuru başarıyla {self.kanal.mention} kanalına gönderildi.", ephemeral=True)

class YonetimView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Komut Yetkileri", style=discord.ButtonStyle.blurple, emoji="🔐", custom_id="yp_cmd")
    async def c(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        v = discord.ui.View(); v.add_item(CmdSelect())
        await i.response.send_message("Komut seçin:", view=v, ephemeral=True)
    @discord.ui.button(label="Tag Kara Liste", style=discord.ButtonStyle.danger, emoji="🏴", custom_id="yp_tag")
    async def t(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        await i.response.send_modal(TagModal())

class GuardView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Guard Limitlerini Değiştir", style=discord.ButtonStyle.blurple, emoji="🛡️", custom_id="gp_lim")
    async def l(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        await i.response.send_modal(GuardModal())
    @discord.ui.button(label="Yönetici Rol Koruması", style=discord.ButtonStyle.gray, emoji="⚡", custom_id="gp_adm")
    async def adm(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        CFG["admin_guard"] = not CFG["admin_guard"]; save_config()
        await i.response.send_message(f"⚡ Yönetici Koruması: **{'Aktif' if CFG['admin_guard'] else 'Pasif'}**", ephemeral=True)

class TicketClose(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Talebi Kapat", style=discord.ButtonStyle.danger, custom_id="c_t")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message("Kanal siliniyor...", ephemeral=True); await asyncio.sleep(3)
        try: await i.channel.delete()
        except: pass

class TicketCreateSelect(discord.ui.Select):
    def __init__(self):
        opts = [discord.SelectOption(label=cat, description=desc[:50]) for cat, desc in CFG["ticket_cats"].items()] if CFG["ticket_cats"] else [discord.SelectOption(label="Genel Destek", description="Destek talebi.")]
        super().__init__(placeholder="Kategori seçin...", options=opts)
    async def callback(self, i: discord.Interaction):
        if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
        cat_name = self.values[0]; guild = i.guild
        parent = discord.utils.get(guild.categories, name="DESTEK TALEPLERI") or await guild.create_category("DESTEK TALEPLERI")
        ov = {guild.default_role: discord.PermissionOverwrite(read_messages=False), i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await guild.create_text_channel(name=f"ticket-{i.user.name}", category=parent, overwrites=ov)
        roles = " ".join([guild.get_role(r).mention for r in CFG["ticket_roles"].get(cat_name, []) if guild.get_role(r)])
        await ch.send(content=f"{roles} Talep açıldı!", embed=discord.Embed(title=f"| BTF | {cat_name}", description=f"Merhaba {i.user.mention}", color=discord.Color.blue()), view=TicketClose())
        await i.response.send_message(f"Kanal: {ch.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None); self.add_item(TicketCreateSelect())

class BanOnayView(discord.ui.View):
    def __init__(self, uid: int, reason: str, kanit: str, gorsel: str, source_guild: str, admin_user: str):
        super().__init__(timeout=None); self.uid, self.reason, self.kanit, self.gorsel, self.source_guild, self.admin_user = uid, reason, kanit, gorsel, source_guild, admin_user
    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.green, custom_id="g_app")
    async def app(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        for c in self.children: c.disabled = True
        emb = i.message.embeds[0]; emb.color = discord.Color.green(); emb.add_field(name="Durum", value=f"Reddedildi - {i.user.mention}")
        await i.message.edit(view=self, embed=emb); await i.response.send_message("İşlem iptal edildi.", ephemeral=True)
    @discord.ui.button(label="Tüm Sunuculardan Yasakla & Karantina", style=discord.ButtonStyle.red, custom_id="g_ban")
    async def gban(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        for c in self.children: c.disabled = True
        CFG["ban_records"][str(self.uid)] = {"reason": self.reason, "admin": self.admin_user, "proof": self.gorsel}
        save_config()
        emb = i.message.embeds[0]; emb.color = discord.Color.dark_red(); emb.add_field(name="Durum", value=f"Onaylandı ({self.source_guild}) - {i.user.mention}")
        await i.message.edit(view=self, embed=emb); cnt = 0
        for g in bot.guilds:
            try:
                m = await g.fetch_member(self.uid)
                if m:
                    try:
                        dm = discord.Embed(title="🛑 Global Ban", description=f"Sebep: {self.reason}\nKanıt: {self.kanit}", color=discord.Color.red())
                        if self.gorsel: dm.set_image(url=self.gorsel)
                        await m.send(embed=dm)
                    except: pass
                    await g.ban(m, reason=f"Global Ban | {self.reason}")
                    if CFG["krol"]:
                        rol = g.get_role(CFG["krol"])
                        if rol: await m.add_roles(rol, reason="Merkez Onaylı Karantina")
                    cnt += 1
            except: pass
        await i.response.send_message(f"✅ {cnt} sunucudan banlandı.", ephemeral=True)

class UnbanOnayView(discord.ui.View):
    def __init__(self, uid: int, user_str: str, source_guild: str, admin_user: str):
        super().__init__(timeout=None); self.uid, self.user_str, self.source_guild, self.admin_user = uid, user_str, source_guild, admin_user
    @discord.ui.button(label="Unbanı Reddet", style=discord.ButtonStyle.green, custom_id="u_app")
    async def app(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        for c in self.children: c.disabled = True
        emb = i.message.embeds[0]; emb.color = discord.Color.green(); emb.add_field(name="Durum", value=f"Unban Reddedildi - {i.user.mention}")
        await i.message.edit(view=self, embed=emb); await i.response.send_message("Unban talebi reddedildi.", ephemeral=True)
    @discord.ui.button(label="Tüm Sunuculardan Unban At", style=discord.ButtonStyle.red, custom_id="u_ban")
    async def gban(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        for c in self.children: c.disabled = True
        if str(self.uid) in CFG["ban_records"]: del CFG["ban_records"][str(self.uid)]; save_config()
        emb = i.message.embeds[0]; emb.color = discord.Color.blue(); emb.add_field(name="Durum", value=f"Unban Onaylandı ({self.source_guild}) - {i.user.mention}")
        await i.message.edit(view=self, embed=emb); cnt = 0
        try: user = await bot.fetch_user(self.uid)
        except: user = None
        if user:
            for g in bot.guilds:
                try: await g.unban(user, reason="Merkez Onaylı Unban"); cnt += 1
                except: pass
        await i.response.send_message(f"✅ {cnt} sunucudan yasak kaldırıldı.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="| BTF | Turkish Armed Forces"))

@bot.event
async def on_member_join(m):
    if is_bl(m) and CFG["krol"]:
        rol = m.guild.get_role(CFG["krol"])
        if rol:
            try: await m.add_roles(rol, reason="Kara liste tag")
            except: pass

@bot.event
async def on_guild_channel_delete(channel):
    if not CFG["guard"]: return
    now = datetime.datetime.utcnow().timestamp()
    try:
        async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            if entry.user.bot: return
            KANAL_SILME.setdefault(entry.user.id, []).append(now)
            KANAL_SILME[entry.user.id] = [t for t in KANAL_SILME[entry.user.id] if now - t < 10]
            if len(KANAL_SILME[entry.user.id]) > CFG["chan_limit"] and CFG["krol"]:
                m_act = channel.guild.get_member(entry.user.id); k_rol = channel.guild.get_role(CFG["krol"])
                if m_act and k_rol and k_rol not in m_act.roles:
                    await m_act.add_roles(k_rol, reason="Guard")
                    if CFG["klog"]: 
                        ch = bot.get_channel(CFG["klog"])
                        if ch: await ch.send(f"🚨 **[{channel.guild.name}]** {m_act.mention} karantinaya alındı!")
    except: pass

@bot.event
async def on_message_delete(m):
    if m.author.bot: return
    zaman = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    sunucu = m.guild.name if m.guild else "Bilinmeyen Sunucu"
    user_str = f"{m.author.id} ({m.author.name}#{m.author.discriminator})"
    if m.attachments and CFG["ilog"]:
        try: 
            ch = bot.get_channel(CFG["ilog"])
            if ch: await ch.send(f"[{zaman}] [{sunucu}] {m.attachments[0].url} | {user_str}")
        except: pass
    elif m.content and CFG["mlog"]:
        try: 
            ch = bot.get_channel(CFG["mlog"])
            if ch: await ch.send(f"[{zaman}] [{sunucu}] {m.content} | {user_str}")
        except: pass

@bot.event
async def on_message(m):
    if m.author.bot: return
    if is_bl(m.author):
        try: await m.delete(); await m.channel.send(TAG_UYARI, delete_after=6)
        except: pass
        return
    if any(k in m.content.lower() for k in YASAKLI):
        try: await m.delete(); await m.channel.send(f"{m.author.mention} yasaklı kelime!", delete_after=3)
        except: pass
        return
    await bot.process_commands(m)

@bot.tree.command(name="bot-yetkili-ayarla", description="Master bot yetkilisi ekler/kaldırır.")
async def bot_yetkili_ayarla(i: discord.Interaction, islem: str, kullanici_adi: str):
    if not is_master(i.user): return await i.response.send_message("❌ Yalnızca master yetkililer kullanabilir!", ephemeral=True)
    username = kullanici_adi.strip().lower()
    if islem.strip().lower() == "ekle":
        if username not in CFG["master_users"]: CFG["master_users"].append(username); save_config()
        await i.response.send_message(f"✅ `{username}` master yetkili olarak eklendi.", ephemeral=True)
    else:
        if username in CFG["master_users"]: CFG["master_users"].remove(username); save_config()
        await i.response.send_message(f"✅ `{username}` master yetkisi kaldırıldı.", ephemeral=True)

@bot.tree.command(name="gkb-yasakla", description="GKB global ban")
async def gkb_yasakla(i: discord.Interaction, uye_id: str, sebep: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not is_gkb(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await i.followup.send("Geçersiz ID!", ephemeral=True)
    if uid not in CFG["gkb_bans"]: CFG["gkb_bans"].append(uid)
    CFG["ban_records"][str(uid)] = {"reason": sebep, "admin": str(i.user), "proof": None}; save_config()
    cnt = 0
    for g in bot.guilds:
        try:
            m = await g.fetch_member(uid)
            if m: await g.ban(m, reason=f"GKB | {sebep}"); cnt += 1
        except: pass
    if CFG["blog"]: 
        ch = bot.get_channel(CFG["blog"])
        if ch: await ch.send(f"⭐ GKB Yasak | {uid} - Sebep: {sebep} [{i.guild.name}]")
    await i.followup.send(f"⭐ GKB emri uygulandı. {cnt} sunucuda banlandı.", ephemeral=True)

@bot.tree.command(name="tam-yasak-at", description="Merkez onaylı ban talebi")
async def tam_yasak_at(i: discord.Interaction, uye_id: str, sebep: str, kanit_metni: str, kanit_gorsel: discord.Attachment):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "tam-yasak-at"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await i.followup.send("Geçersiz ID!", ephemeral=True)
    if not CFG["hq"] or not CFG["clog"]: return await i.followup.send("Merkez log ayarlanmamış!", ephemeral=True)
    emb = discord.Embed(title=f"🛡️ Merkez Onaylı Yasak Talebi [{i.guild.name}]", description=f"ID: `{uid}`\nSebep: {sebep}\nKanıt: {kanit_metni}\nTalep Eden: {i.user.mention}", color=discord.Color.orange())
    emb.set_image(url=kanit_gorsel.url)
    terminal_ch = bot.get_guild(CFG["hq"]).get_channel(CFG["clog"])
    if terminal_ch:
        await terminal_ch.send(embed=emb, view=BanOnayView(uid, f"{sebep} | Kanıt: {kanit_metni}", kanit_metni, kanit_gorsel.url, i.guild.name, str(i.user)))
        await i.followup.send("✅ Yasak talebi terminal sunucusuna gönderildi.", ephemeral=True)
    else: await i.followup.send("❌ Terminal kanal bulunamadı!", ephemeral=True)

@bot.tree.command(name="tam-yasak-kaldır", description="Merkez onaylı ban kaldırma talebi")
async def tam_yasak_kaldır(i: discord.Interaction, uye_id: str, sebep: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "tam-yasak-kaldır"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id); user = await bot.fetch_user(uid)
    except: return await i.followup.send("Kullanıcı bulunamadı.", ephemeral=True)
    if not CFG["hq"] or not CFG["clog"]: return await i.followup.send("Merkez log ayarlanmamış!", ephemeral=True)
    emb = discord.Embed(title=f"🔓 Merkez Onaylı Unban Talebi [{i.guild.name}]", description=f"Kullanıcı: {user} (`{uid}`)\nSebep: {sebep}\nTalep Eden: {i.user.mention}", color=discord.Color.blue())
    terminal_ch = bot.get_guild(CFG["hq"]).get_channel(CFG["clog"])
    if terminal_ch:
        await terminal_ch.send(embed=emb, view=UnbanOnayView(uid, str(user), i.guild.name, str(i.user)))
        await i.followup.send("✅ Unban talebi terminal sunucusuna merkez onaya gönderildi.", ephemeral=True)
    else: await i.followup.send("❌ Terminal kanal bulunamadı!", ephemeral=True)

@bot.tree.command(name="sustur", description="Kullanıcıyı süreli susturur (Örn: 28 gün)")
async def sustur(i: discord.Interaction, uye: discord.Member, sure: str, sebep: str, kanit_gorsel: discord.Attachment):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "sustur"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    
    total_minutes = parse_time(sure)
    await uye.timeout(datetime.timedelta(minutes=total_minutes), reason=sebep)
    
    if CFG["slog"]:
        ch = bot.get_channel(CFG["slog"])
        if ch:
            emb = discord.Embed(title="🎙️ Susturma İşlemi", description=f"{i.user.mention} (`@{i.user.name}`) tarafından\n{uye.mention} (`@{uye.name}`) kullanıcısı\n{sebep} sebebiyle **{sure}** susturuldu.", color=discord.Color.dark_embed())
            emb.add_field(name="Görsel Kanıt", value="\u200b", inline=False)
            emb.set_image(url=kanit_gorsel.url)
            await ch.send(embed=emb)
            
    await i.followup.send(f"✅ {uye.mention} başarıyla {sure} süreyle susturuldu.", ephemeral=True)

@bot.tree.command(name="susturma-kaldır", description="Susturma kaldır")
async def susturma_kaldır(i: discord.Interaction, uye: discord.Member):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "susturma-kaldır"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.timeout(None); await i.response.send_message("✅ Susturma kaldırıldı.", ephemeral=True)

@bot.tree.command(name="rol-ver", description="Rol ver")
async def rol_ver(i: discord.Interaction, uye: discord.Member, rol: discord.Role):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "rol-ver"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.add_roles(rol); await i.response.send_message("✅ Rol verildi.", ephemeral=True)

@bot.tree.command(name="rol-al", description="Rol al")
async def rol_al(i: discord.Interaction, uye: discord.Member, rol: discord.Role):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "rol-al"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.remove_roles(rol); await i.response.send_message("✅ Rol alındı.", ephemeral=True)

@bot.tree.command(name="yasak-sorgu", description="Kullanıcı ban durumunu sorgula")
async def yasak_sorgu(i: discord.Interaction, uye_id: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "yasak-sorgu"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id); user = await bot.fetch_user(uid)
    except: return await i.followup.send("Kullanıcı bulunamadı.", ephemeral=True)
    yasaklar = []
    for g in bot.guilds:
        try: await g.fetch_ban(user); yasaklar.append(g.name)
        except: pass
    record = CFG["ban_records"].get(str(uid))
    emb = discord.Embed(title="🔍 Detaylı Yasak Sorgulama", description=f"Kullanıcı: {user} (`{user.id}`)", color=discord.Color.red() if yasaklar else discord.Color.green())
    emb.add_field(name="Yasaklı Olduğu Sunucular", value=", ".join(yasaklar) if yasaklar else "Hiçbir sunucuda yasağı yok.", inline=False)
    if record:
        emb.add_field(name="Ban Sebebi", value=record.get("reason", "Belirtilmedi"), inline=False)
        emb.add_field(name="Yasaklayan Yetkili", value=record.get("admin", "Bilinmiyor"), inline=False)
        if record.get("proof"): emb.set_image(url=record["proof"])
    else: emb.add_field(name="Not", value="Kayıt bulunamadı.", inline=False)
    await i.followup.send(embed=emb, ephemeral=True)

@bot.tree.command(name="dm-mesaj", description="DM gönder")
async def dm_mesaj(i: discord.Interaction, uye: discord.Member, mesaj: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "dm-mesaj"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    try:
        await uye.send(embed=discord.Embed(title="📢 Resmi Bildiri", description=mesaj, color=discord.Color.gold()))
        await i.response.send_message("✅ DM iletildi.", ephemeral=True)
    except: await i.response.send_message("❌ DM kutusu kapalı!", ephemeral=True)

@bot.tree.command(name="duyur", description="Duyuru gönder")
async def duyur(i: discord.Interaction, kanal: discord.TextChannel):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "duyur"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.send_modal(DuyuruModal(kanal))

@bot.tree.command(name="ticket-kur", description="Ticket kur")
async def ticket_kur(i: discord.Interaction):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    emb = discord.Embed(title=CFG["ticket_title"], description=CFG["ticket_desc"], color=discord.Color.dark_blue())
    await i.channel.send(embed=emb, view=TicketView())
    await i.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="ticket-yönetim-paneli", description="Ticket ayarla")
async def ticket_yönetim_paneli(i: discord.Interaction, baslik: str, aciklama: str, kategori_adi: str, etiketlenecek_roller: str):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["ticket_title"] = baslik; CFG["ticket_desc"] = aciklama; CFG["ticket_cats"][kategori_adi] = aciklama
    try:
        r_ids = [int(x.strip().replace("<@&","").replace(">","")) for x in etiketlenecek_roller.split(",") if x.strip()]
        CFG["ticket_roles"][kategori_adi] = r_ids
    except: pass
    save_config()
    await i.response.send_message(f"✅ `{kategori_adi}` kategorisi eklendi.", ephemeral=True)

@bot.tree.command(name="merkez-onay-log", description="Merkez onay kanalını seç")
async def merkez_onay_log(i: discord.Interaction, kanal: discord.TextChannel):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["hq"], CFG["clog"] = kanal.guild.id, kanal.id
    save_config()
    await i.response.send_message(f"✅ Merkez onay kanalı {kanal.mention} olarak ayarlandı.", ephemeral=True)

@bot.tree.command(name="log-ayarla", description="Log kanallarını seç")
async def log_ayarla(i: discord.Interaction, mesaj_log: discord.TextChannel, gorsel_log: discord.TextChannel, susturma_log: discord.TextChannel, ban_log: discord.TextChannel, karantina_log: discord.TextChannel):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["mlog"], CFG["ilog"], CFG["slog"], CFG["blog"], CFG["klog"] = mesaj_log.id, gorsel_log.id, susturma_log.id, ban_log.id, karantina_log.id
    save_config()
    await i.response.send_message("✅ Tüm terminal log kanalları başarıyla ayarlandı.", ephemeral=True)

@bot.tree.command(name="bot-yönetim-paneli", description="Yönetim paneli")
async def bot_yönetim_paneli(i: discord.Interaction):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.send_message(embed=discord.Embed(title="⚙️ Yönetim", color=discord.Color.dark_blue()), view=YonetimView(), ephemeral=True)

@bot.tree.command(name="guard-yönetim-paneli", description="Guard paneli")
async def guard_yönetim_paneli(i: discord.Interaction):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    emb = discord.Embed(title="🛡️ Guard", description=f"Kanal Sınırı: `{CFG['chan_limit']}`\nYönetici Koruması: `{'Aktif' if CFG['admin_guard'] else 'Pasif'}`", color=discord.Color.dark_red())
    await i.response.send_message(embed=emb, view=GuardView(), ephemeral=True)

bot.run(os.getenv("TOKEN"))
