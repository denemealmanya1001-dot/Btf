import os, datetime, asyncio, discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.guilds = intents.members = intents.message_content = intents.guild_messages = intents.moderation = True

class BTFGuardBot(commands.Bot):
    def __init__(self): super().__init__(command_prefix="!", intents=intents)
    async def setup_hook(self): await self.tree.sync(); print("| BTF | Turkish Armed Forces - Kararlı Sistem Aktif.")

bot = BTFGuardBot()
CFG = {"hq": None, "clog": None, "mlog": None, "ilog": None, "slog": None, "blog": None, "klog": None, "krol": None, "perms": {}, "tags": [], "gkb_bans": [], "limit": 3, "guard": True}
YASAKLI = ["kufur1", "reklamlinki"]
ROL_SILME = {}
TAG_UYARI = "Guild Tagını Kullanmakta Olduğunuz Sunucunun Bot Kullanımı Yasaklanmıştır. Botu Kullanmak İçin Tagı Değiştirin/Kaldırın !"

def is_admin(i: discord.Interaction) -> bool: return discord.utils.get(i.user.roles, name="Bot Yönetim +") is not None
def is_gkb(i: discord.Interaction) -> bool: return discord.utils.get(i.user.roles, name="Genelkurmay Başkanı") is not None or is_admin(i)
def has_perm(i: discord.Interaction, c: str) -> bool: return True if is_admin(i) else any(r.id in CFG["perms"].get(c, []) for r in i.user.roles)
def is_bl(m: discord.Member) -> bool:
    if not CFG["tags"]: return False
    s = f"{m.name} {m.display_name} {getattr(getattr(m, 'primary_guild', None), 'tag', '')}".lower()
    return any(t.lower() in s for t in CFG["tags"])

class RoleSelectCmd(discord.ui.RoleSelect):
    def __init__(self, cmd: str):
        self.cmd = cmd
        super().__init__(placeholder=f"/{cmd} için yetkili rolleri seçin...", min_values=1, max_values=10)
    async def callback(self, i: discord.Interaction):
        CFG["perms"][self.cmd] = [r.id for r in self.values]
        await i.response.send_message(f"✅ `/{self.cmd}` yetkileri güncellendi.", ephemeral=True)

class CmdSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Komut seçin...", options=[discord.SelectOption(label=x) for x in ["tam-yasak-at", "tam-yasak-kaldır", "sustur", "susturma-kaldır", "rol-ver", "rol-al"]])
    async def callback(self, i: discord.Interaction):
        v = discord.ui.View(timeout=60); v.add_item(RoleSelectCmd(self.values[0]))
        await i.response.send_message(f"🔐 `/{self.values[0]}` için rolleri seçin:", view=v, ephemeral=True)

class TagModal(discord.ui.Modal, title="Tag Kara Liste Yönetimi"):
    islem = discord.ui.TextInput(label="İşlem (ekle / sil)", placeholder="ekle", required=True)
    tag = discord.ui.TextInput(label="Yasaklanacak Guild / Klan Tagı", placeholder="BTF", required=True)
    async def on_submit(self, i: discord.Interaction):
        t = self.tag.value.strip()
        if self.islem.value.strip().lower() == "ekle":
            if t not in CFG["tags"]: CFG["tags"].append(t)
            await i.response.send_message(f"🚫 `{t}` kara listeye alındı.", ephemeral=True)
        else:
            if t in CFG["tags"]: CFG["tags"].remove(t)
            await i.response.send_message(f"✅ `{t}` listeden çıkarıldı.", ephemeral=True)

class GuardModal(discord.ui.Modal, title="Guard Limit Ayarı"):
    limit = discord.ui.TextInput(label="Ard Arda Rol Silme Limiti", placeholder="3", required=True)
    async def on_submit(self, i: discord.Interaction):
        try:
            CFG["limit"] = int(self.limit.value.strip())
            await i.response.send_message(f"✅ Guard limiti `{CFG['limit']}` olarak ayarlandı.", ephemeral=True)
        except: await i.response.send_message("❌ Geçersiz sayı!", ephemeral=True)

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
    @discord.ui.button(label="Guard Limitini Değiştir", style=discord.ButtonStyle.blurple, emoji="🛡️", custom_id="gp_lim")
    async def l(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        await i.response.send_modal(GuardModal())
    @discord.ui.button(label="Guard Aç/Kapat", style=discord.ButtonStyle.gray, emoji="🔄", custom_id="gp_tog")
    async def tog(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        CFG["guard"] = not CFG["guard"]
        await i.response.send_message(f"🛡️ Guard durumu: **{'Aktif' if CFG['guard'] else 'Pasif'}**", ephemeral=True)

class TicketClose(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Talebi Kapat", style=discord.ButtonStyle.danger, custom_id="c_t")
    async def close(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message("Kanal siliniyor...", ephemeral=True); await asyncio.sleep(3)
        try: await i.channel.delete()
        except: pass

class TicketCreate(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Destek Aç", style=discord.ButtonStyle.blurple, custom_id="o_t")
    async def create(self, i: discord.Interaction, b: discord.ui.Button):
        if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
        cat = discord.utils.get(i.guild.categories, name="DESTEK TALEPLERI") or await i.guild.create_category("DESTEK TALEPLERI")
        ov = {i.guild.default_role: discord.PermissionOverwrite(read_messages=False), i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True), i.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)}
        ch = await i.guild.create_text_channel(name=f"ticket-{i.user.name}", category=cat, overwrites=ov)
        rol = discord.utils.get(i.guild.roles, name="yetkili")
        await ch.send(content=f"{rol.mention if rol else '@yetkili'} Talep açıldı!", embed=discord.Embed(title="| BTF | Destek", description=f"Merhaba {i.user.mention}", color=discord.Color.blue()), view=TicketClose())
        await i.response.send_message(f"Kanal: {ch.mention}", ephemeral=True)

class BanOnayView(discord.ui.View):
    def __init__(self, uid: int, reason: str, kanit: str, gorsel: str):
        super().__init__(timeout=None); self.uid, self.reason, self.kanit, self.gorsel = uid, reason, kanit, gorsel
    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.green, custom_id="g_app")
    async def app(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        for c in self.children: c.disabled = True
        emb = i.message.embeds[0]; emb.color = discord.Color.green(); emb.add_field(name="Durum", value=f"Reddedildi - {i.user.mention}")
        await i.message.edit(view=self, embed=emb); await i.response.send_message("İptal edildi.", ephemeral=True)
    @discord.ui.button(label="Tüm Sunuculardan Yasakla", style=discord.ButtonStyle.red, custom_id="g_ban")
    async def gban(self, i: discord.Interaction, b: discord.ui.Button):
        if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        for c in self.children: c.disabled = True
        emb = i.message.embeds[0]; emb.color = discord.Color.dark_red(); emb.add_field(name="Durum", value=f"Yasaklandı! - {i.user.mention}")
        await i.message.edit(view=self, embed=emb); cnt = 0
        for g in bot.guilds:
            try:
                m = await g.fetch_member(self.uid)
                if m:
                    try:
                        dm = discord.Embed(title="🛑 | BTF | Global Ban", description=f"Sebep: {self.reason}\nKanıt: {self.kanit}", color=discord.Color.red())
                        if self.gorsel: dm.set_image(url=self.gorsel)
                        await m.send(embed=dm)
                    except: pass
                    await g.ban(m, reason=f"Global Ban | {self.reason}"); cnt += 1
            except: pass
        await i.response.send_message(f"✅ {cnt} sunucudan banlandı.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="| BTF | Turkish Armed Forces"))

@bot.event
async def on_member_join(m):
    if is_bl(m) and CFG["krol"]:
        rol = m.guild.get_role(CFG["krol"])
        if rol:
            try:
                await m.add_roles(rol, reason="Kara liste tag")
                if CFG["klog"]: await bot.get_channel(CFG["klog"]).send(f"🏴 {m.mention} yasaklı tag nedeniyle karantinaya alındı!")
            except: pass

@bot.event
async def on_member_unban(guild, user):
    if user.id in CFG["gkb_bans"]:
        for g in bot.guilds:
            try: await g.ban(user, reason="GKB Koruma - Kaldırma Engellendi")
            except: pass
        if CFG["blog"]:
            try: await bot.get_channel(CFG["blog"]).send(f"🚨 GKB Yasaklı kullanıcı ({user}) banı açılmaya çalışıldı! Bot tekrar banladı.")
            except: pass

@bot.event
async def on_member_update(before, after):
    if is_bl(after) and CFG["krol"]:
        rol = after.guild.get_role(CFG["krol"])
        if rol and rol not in after.roles:
            try: await after.add_roles(rol, reason="Tag güncellemesi")
            except: pass
    if before.timed_out_until and not after.timed_out_until:
        if CFG["slog"]:
            try: await bot.get_channel(CFG["slog"]).send(f"⚠️ {after.mention} susturması manuel kaldırıldı! Bot tekrar uyguladı.")
            except: pass
        try: await after.timeout(before.timed_out_until, reason="Koruma")
        except: pass
    if CFG["guard"] and len(before.roles) > len(after.roles):
        now = datetime.datetime.utcnow().timestamp()
        try:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                if entry.user.bot: return
                ROL_SILME.setdefault(entry.user.id, []).append(now)
                ROL_SILME[entry.user.id] = [t for t in ROL_SILME[entry.user.id] if now - t < 10]
                if len(ROL_SILME[entry.user.id]) > CFG["limit"] and CFG["krol"]:
                    m_act = after.guild.get_member(entry.user.id); k_rol = after.guild.get_role(CFG["krol"])
                    if m_act and k_rol and k_rol not in m_act.roles:
                        await m_act.add_roles(k_rol, reason="Guard")
                        if CFG["klog"]: await bot.get_channel(CFG["klog"]).send(f"🚨 {m_act.mention} karantinaya alındı!")
        except: pass

@bot.event
async def on_message_delete(m):
    if m.author.bot: return
    if m.attachments and CFG["ilog"]:
        try: await bot.get_channel(CFG["ilog"]).send(embed=discord.Embed(title="🖼️ Silinen Görsel", color=discord.Color.purple()).add_field(name="Kullanıcı", value=m.author.mention).set_image(url=m.attachments[0].url))
        except: pass
    if m.content and CFG["mlog"]:
        try: await bot.get_channel(CFG["mlog"]).send(embed=discord.Embed(title="🗑️ Silinen Mesaj", color=discord.Color.orange()).add_field(name="Kullanıcı", value=m.author.mention).add_field(name="İçerik", value=m.content[:1024]))
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

@bot.tree.command(name="gkb-yasakla", description="GKB global ban")
async def gkb_yasakla(i: discord.Interaction, uye_id: str, sebep: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not is_gkb(i): return await i.response.send_message("❌ Yalnızca Genelkurmay Başkanı kullanabilir!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await i.followup.send("Geçersiz ID!", ephemeral=True)
    if uid not in CFG["gkb_bans"]: CFG["gkb_bans"].append(uid)
    cnt = 0
    for g in bot.guilds:
        try:
            m = await g.fetch_member(uid)
            if m: await g.ban(m, reason=f"GKB | {sebep}"); cnt += 1
        except: pass
    if CFG["blog"]: await bot.get_channel(CFG["blog"]).send(embed=discord.Embed(title="⭐ GKB Yasak", description=f"ID: `{uid}`\nSebep: {sebep}", color=discord.Color.gold()))
    await i.followup.send(f"⭐ GKB emri uygulandı. {cnt} sunucuda banlandı.", ephemeral=True)

@bot.tree.command(name="tam-yasak-at", description="Ban talebi")
async def tam_yasak_at(i: discord.Interaction, uye_id: str, sebep: str, kanit_metni: str, kanit_gorsel: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "tam-yasak-at"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id)
    except: return await i.followup.send("Geçersiz ID!", ephemeral=True)
    if not CFG["hq"] or not CFG["clog"]: return await i.followup.send("Merkez yok!", ephemeral=True)
    emb = discord.Embed(title="🛡️ Yasak Talebi", description=f"ID: `{uid}`\nSebep: {sebep}", color=discord.Color.orange()).set_image(url=kanit_gorsel)
    await bot.get_guild(CFG["hq"]).get_channel(CFG["clog"]).send(embed=emb, view=BanOnayView(uid, sebep, kanit_metni, kanit_gorsel))
    await i.followup.send("✅ Merkeze gönderildi.", ephemeral=True)

@bot.tree.command(name="tam-yasak-kaldır", description="Yasak kaldır")
async def tam_yasak_kaldır(i: discord.Interaction, uye_id: str):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "tam-yasak-kaldır"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.defer(ephemeral=True)
    try: uid = int(uye_id); user = await bot.fetch_user(uid)
    except: return await i.followup.send("Bulunamadı.", ephemeral=True)
    if uid in CFG["gkb_bans"] and not is_gkb(i): return await i.followup.send("❌ Yalnızca GKB kaldırabilir!", ephemeral=True)
    if uid in CFG["gkb_bans"]: CFG["gkb_bans"].remove(uid)
    cnt = 0
    for g in bot.guilds:
        try: await g.unban(user); cnt += 1
        except: pass
    await i.followup.send(f"✅ {cnt} sunucudan kaldırıldı.", ephemeral=True)

@bot.tree.command(name="sustur", description="Sustur")
async def sustur(i: discord.Interaction, uye: discord.Member, sure_dakika: int, sebep: str = "Belirtilmedi"):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "sustur"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.timeout(datetime.timedelta(minutes=sure_dakika), reason=sebep)
    if CFG["slog"]: await bot.get_channel(CFG["slog"]).send(f"🔇 {uye.mention} susturuldu.")
    await i.response.send_message("✅ Susturuldu.", ephemeral=True)

@bot.tree.command(name="susturma-kaldır", description="Susturma kaldır")
async def susturma_kaldır(i: discord.Interaction, uye: discord.Member):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "susturma-kaldır"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.timeout(None); await i.response.send_message("✅ Kaldırıldı.", ephemeral=True)

@bot.tree.command(name="rol-ver", description="Rol ver")
async def rol_ver(i: discord.Interaction, uye: discord.Member, rol: discord.Role):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "rol-ver"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.add_roles(rol); await i.response.send_message("✅ Verildi.", ephemeral=True)

@bot.tree.command(name="rol-al", description="Rol al")
async def rol_al(i: discord.Interaction, uye: discord.Member, rol: discord.Role):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not has_perm(i, "rol-al"): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await uye.remove_roles(rol); await i.response.send_message("✅ Alındı.", ephemeral=True)

@bot.tree.command(name="ticket-kur", description="Ticket kur")
async def ticket_kur(i: discord.Interaction):
    if is_bl(i.user): return await i.response.send_message(TAG_UYARI, ephemeral=True)
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.channel.send(embed=discord.Embed(title="🛡️ Destek", color=discord.Color.dark_blue()), view=TicketCreate())
    await i.response.send_message("✅ Kuruldu.", ephemeral=True)

@bot.tree.command(name="merkez-onay-log", description="Merkez log")
async def merkez_onay_log(i: discord.Interaction, kanal: discord.TextChannel):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["hq"], CFG["clog"] = i.guild.id, kanal.id
    await i.response.send_message(f"✅ Merkez: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="log-ayarla", description="Log ayarla")
async def log_ayarla(i: discord.Interaction, mesaj_log: discord.TextChannel, gorsel_log: discord.TextChannel, susturma_log: discord.TextChannel, ban_log: discord.TextChannel, karantina_log: discord.TextChannel, karantina_rol: discord.Role):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    CFG["mlog"], CFG["ilog"], CFG["slog"], CFG["blog"], CFG["klog"], CFG["krol"] = mesaj_log.id, gorsel_log.id, susturma_log.id, ban_log.id, karantina_log.id, karantina_rol.id
    await i.response.send_message("✅ Loglar ayarlandı.", ephemeral=True)

@bot.tree.command(name="bot-yönetim-paneli", description="Yönetim paneli")
async def bot_yönetim_paneli(i: discord.Interaction):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    await i.response.send_message(embed=discord.Embed(title="⚙️ Yönetim", color=discord.Color.dark_blue()), view=YonetimView(), ephemeral=True)

@bot.tree.command(name="guard-yönetim-paneli", description="Guard paneli")
async def guard_yönetim_paneli(i: discord.Interaction):
    if not is_admin(i): return await i.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
    emb = discord.Embed(title="🛡️ Guard", description=f"Sınır: `{CFG['limit']}`\nDurum: `{'Aktif' if CFG['guard'] else 'Pasif'}`", color=discord.Color.dark_red())
    await i.response.send_message(embed=emb, view=GuardView(), ephemeral=True)

bot.run(os.getenv("TOKEN"))
        
