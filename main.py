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

class GlobalGuardBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("BTF Kara Kuvvetleri Güvenlik ve Moderasyon Sistemi Senkronize Edildi.")

bot = GlobalGuardBot()

MAIN_HEADQUARTER_GUILD_ID = 0  
CENTRAL_LOG_CHANNEL_ID = 0     

YASAKLI_KELIMELER = ["kufur1", "kufur2", "reklamlinki"]

# --- TICKET KAPATMA ---
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Destek Talebini Kapat", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Destek talebi kapatiliyor, kanal 5 saniye icinde silinecektir...", ephemeral=True)
        await asyncio_sleep_and_delete(interaction.channel)

async def asyncio_sleep_and_delete(channel):
    import asyncio
    await asyncio.sleep(5)
    try:
        await channel.delete(reason="Destek talebi kapatildi.")
    except:
        pass

# --- TICKET AÇMA ---
class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Destek Talebi Ac (Ticket)", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="DESTEK TALEPLERI")
        if not category:
            category = await guild.create_category("DESTEK TALEPLERI")

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

        yetkili_rol = discord.utils.get(guild.roles, name="yetkili")
        etiket_metni = yetkili_rol.mention if yetkili_rol else "@yetkili"

        embed = discord.Embed(
            title="BTF Karargah Destek Hatti",
            description=f"Merhaba {interaction.user.mention}, yetkililer kisa sure icinde sizinle ilgilenecektir.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=f"{etiket_metni} Yeni bir destek talebi açıldı!", embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Destek kanaliniz olusturuldu: {ticket_channel.mention}", ephemeral=True)

# --- MERKEZİ ONAY / RED / GLOBAL YASAKLAMA ---
class GlobalGuardActionView(discord.ui.View):
    def __init__(self, target_user_id: int, action_reason: str, kanit: str):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.action_reason = action_reason
        self.kanit = kanit

    @discord.ui.button(label="Onayla (Serbest Birak)", style=discord.ButtonStyle.green, custom_id="global_approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yonetici yetkin olmali!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Durum", value=f"Onaylandi / Serbest Birakildi - Yetkili: {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=embed)
        await interaction.response.send_message("Islem onaylandi.", ephemeral=True)

    @discord.ui.button(label="Tum Bot Sunucularindan Tam Yasakla", style=discord.ButtonStyle.red, custom_id="global_ban")
    async def global_ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yonetici yetkin olmali!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.dark_red()
        embed.add_field(name="Durum", value=f"Tum Sunuculardan Tam Yasaklandi! - Yetkili: {interaction.user.mention}", inline=False)
        await interaction.message.edit(view=self, embed=embed)

        success_count = 0
        for guild in bot.guilds:
            try:
                member = await guild.fetch_member(self.target_user_id)
                if member:
                    try:
                        dm_embed = discord.Embed(
                            title="🛑 BTF Kara Kuvvetleri - Global Yasaklama Karari",
                            description=f"**Sunucu:** {guild.name}\n**Sebep:** {self.action_reason}\n**Kanit:** {self.kanit}\n\n*Botun bagli oldugu tum sunuculardan kalici olarak izole edildiniz.*",
                            color=discord.Color.red()
                        )
                        await member.send(embed=dm_embed)
                    except:
                        pass
                    
                    await guild.ban(member, reason=f"Global Tam Yasak | Sebep: {self.action_reason} | Kanit: {self.kanit}")
                    success_count += 1
            except:
                pass

        await interaction.response.send_message(f"Islem basarili! Kullanici {success_count} sunucudan tamamen yasaklandi.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="BTF Askeri Guvenlik")
    )

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
                    await message.author.send("Yasakli kelime kullandiginiz icin mesajiniz engellendi!")
                except:
                    pass
                await message.channel.send(f"{message.author.mention}, bu kelime yasak!", delete_after=4)
            except Exception as e:
                print(f"Filtre hata: {e}")
            return

    await bot.process_commands(message)


# ==========================================
# MODERASYON VE YÖNETİM KOMUTLARI
# ==========================================

@bot.tree.command(name="merkezayarla", description="Global log ve onay kanalini belirler.")
@app_commands.default_permissions(administrator=True)
async def slash_merkezayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    global MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID
    MAIN_HEADQUARTER_GUILD_ID = interaction.guild.id
    CENTRAL_LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"Merkez Karargah ve Log Kanali ayarlandi: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="sustur", description="Bir kullanıcıyı belirtilen süreyle susturur.")
@app_commands.default_permissions(moderate_members=True)
async def slash_sustur(interaction: discord.Interaction, uye: discord.Member, sure_dakika: int, sebep: str = "Belirtilmedi"):
    duration = datetime.timedelta(minutes=sure_dakika)
    try:
        await uye.timeout(duration, reason=sebep)
        await interaction.response.send_message(f"✅ {uye.mention} adlı kullanıcı {sure_dakika} dakika süreyle susturuldu. Sebep: {sebep}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Susturma islemi basarisiz: {e}", ephemeral=True)

@bot.tree.command(name="susturmakaldir", description="Bir kullanıcının susturmasını (timeout) kaldırır.")
@app_commands.default_permissions(moderate_members=True)
async def slash_susturmakaldir(interaction: discord.Interaction, uye: discord.Member):
    try:
        await uye.timeout(None, reason=f"Susturma Kaldırıldı - Yetkili: {interaction.user}")
        await interaction.response.send_message(f"✅ {uye.mention} adlı kullanıcının susturması kaldırıldı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ İşlem başarısız: {e}", ephemeral=True)

@bot.tree.command(name="tamyasakla", description="Kullaniciyi kanit ve sebebiyle tum sunuculardan banlar, merkeze onay paneli duser.")
@app_commands.default_permissions(ban_members=True)
async def slash_tamyasakla(interaction: discord.Interaction, uye_id: str, sebep: str, kanit: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        target_id = int(uye_id)
    except ValueError:
        await interaction.followup.send("❌ Gecersiz ID!", ephemeral=True)
        return

    if MAIN_HEADQUARTER_GUILD_ID and CENTRAL_LOG_CHANNEL_ID:
        hq_guild = bot.get_guild(MAIN_HEADQUARTER_GUILD_ID)
        if hq_guild:
            log_channel = hq_guild.get_channel(CENTRAL_LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="🛡️ BTF Karargah - Global Yasaklama Onay Talebi",
                    description=f"**Hedef Kullanıcı ID:** `{target_id}`\n**Sebep:** {sebep}\n**Kanıt:** {kanit}\n**İşlemi Başlatan:** {interaction.user.mention}",
                    color=discord.Color.orange(),
                    timestamp=datetime.datetime.utcnow()
                )
                view = GlobalGuardActionView(target_user_id=target_id, action_reason=sebep, kanit=kanit)
                await log_channel.send(embed=embed, view=view)

    success_count = 0
    for guild in bot.guilds:
        try:
            member = await guild.fetch_member(target_id)
            if member:
                try:
                    dm_embed = discord.Embed(
                        title="🛑 BTF Kara Kuvvetleri - Global Yasaklama",
                        description=f"**Sebep:** {sebep}\n**Kanıt:** {kanit}\n\n*Botun bagli oldugu sunuculardan yasaklandiniz.*",
                        color=discord.Color.dark_red()
                    )
                    await member.send(embed=dm_embed)
                except:
                    pass
                
                await guild.ban(member, reason=f"Global Tam Yasak | Sebep: {sebep} | Kanit: {kanit}")
                success_count += 1
        except:
            pass

    await interaction.followup.send(f"✅ Islem baslatildi! {success_count} sunucuda uygulandı ve merkeze onay paneli gönderildi.", ephemeral=True)

@bot.tree.command(name="yasakkaldir", description="Global yasagi tum sunuculardan kaldirir.")
@app_commands.default_permissions(ban_members=True)
async def slash_yasakkaldir(interaction: discord.Interaction, uye_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        target_id = int(uye_id)
        user = await bot.fetch_user(target_id)
    except:
        await interaction.followup.send("❌ Gecerli bir kullanici bulunamadi.", ephemeral=True)
        return

    unban_count = 0
    for guild in bot.guilds:
        try:
            await guild.unban(user, reason=f"Global Yasak Kaldirma | Yetkili: {interaction.user}")
            unban_count += 1
        except:
            pass

    await interaction.followup.send(f"✅ Kullanicinin yasagi {unban_count} sunucudan kaldirildi.", ephemeral=True)

@bot.tree.command(name="yasaksifirla", description="Sunucudaki tum yasaklari sifirlar (kaldirir).")
@app_commands.default_permissions(administrator=True)
async def slash_yasaksifirla(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    count = 0
    async for ban_entry in interaction.guild.bans():
        try:
            await interaction.guild.unban(ban_entry.user, reason=f"Toplu Yasak Sifirlama | Yetkili: {interaction.user}")
            count += 1
        except:
            pass
    await interaction.followup.send(f"✅ Sunucudaki toplam {count} ban (yasak) kaldırıldı.", ephemeral=True)

@bot.tree.command(name="yasaksorgu", description="Bir kullanicinin bu sunucudaki ban/yasak durumunu sorgular.")
@app_commands.default_permissions(ban_members=True)
async def slash_yasaksorgu(interaction: discord.Interaction, uye_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        target_id = int(uye_id)
        user = await bot.fetch_user(target_id)
        ban_entry = await interaction.guild.fetch_ban(user)
        embed = discord.Embed(title="🔍 Yasak Sorgulama Sonucu", color=discord.Color.red())
        embed.add_field(name="Kullanıcı", value=f"{user} (`{user.id}`)", inline=False)
        embed.add_field(name="Yasak Sebebi", value=ban_entry.reason or "Sebep belirtilmemiş", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except discord.NotFound:
        await interaction.followup.send("✅ Bu kullanıcı bu sunucuda banlı değil.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Sorgulama sırasında hata oluştu: {e}", ephemeral=True)


# ==========================================
# ROL YÖNETİM KOMUTLARI
# ==========================================

@bot.tree.command(name="rolver", description="Bir kullanıcıya rol verir.")
@app_commands.default_permissions(manage_roles=True)
async def slash_rolver(interaction: discord.Interaction, uye: discord.Member, rol: discord.Role):
    try:
        await uye.add_roles(rol, reason=f"Yetkili: {interaction.user}")
        await interaction.response.send_message(f"✅ {uye.mention} adlı kullanıcıya {rol.mention} rolü verildi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Rol verme başarısız: {e}", ephemeral=True)

@bot.tree.command(name="rolal", description="Bir kullanıcıdan rol alır.")
@app_commands.default_permissions(manage_roles=True)
async def slash_rolal(interaction: discord.Interaction, uye: discord.Member, rol: discord.Role):
    try:
        await uye.remove_roles(rol, reason=f"Yetkili: {interaction.user}")
        await interaction.response.send_message(f"✅ {uye.mention} adlı kullanıcıdan {rol.mention} rolü alındı.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Rol alma başarısız: {e}", ephemeral=True)

@bot.tree.command(name="rutbedegistir", description="Bir kullanıcının unvan/rütbe rolünü değiştirir.")
@app_commands.default_permissions(manage_roles=True)
async def slash_rutbedegistir(interaction: discord.Interaction, uye: discord.Member, yeni_rutbe_rolu: discord.Role):
    try:
        await uye.add_roles(yeni_rutbe_rolu, reason=f"Rütbe Değişikliği - {interaction.user}")
        await interaction.response.send_message(f"✅ {uye.mention} adlı kullanıcının rolü {yeni_rutbe_rolu.mention} olarak güncellendi.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Rol değiştirilemedi: {e}", ephemeral=True)

@bot.tree.command(name="rutbesorgu", description="Bir kullanıcının üzerindeki rolleri sorgular.")
@app_commands.default_permissions(manage_roles=True)
async def slash_rutbesorgu(interaction: discord.Interaction, uye: discord.Member):
    roller = [r.mention for r in uye.roles if r != interaction.guild.default_role]
    roller_str = ", ".join(roller) if roller else "Hiç rolü yok"
    embed = discord.Embed(title=f"🎖️ {uye.display_name} - Rol Sorgusu", description=roller_str, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# GENEL DİĞER KOMUTLAR
# ==========================================

@bot.tree.command(name="dm", description="Bot üzerinden kullanıcıya özel mesaj gönderir.")
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
        await interaction.followup.send(f"✅ Mesaj {uye.mention} adlı kullanıcıya iletildi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Mesaj atılamadı: {e}", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Destek paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def slash_ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛡️ BTF Kara Kuvvetleri Destek ve İletişim Merkezi",
        description="Yetkililerle iletişime geçmek için aşağıdaki **Destek Talebi Aç** butonuna tıklayınız.",
        color=discord.Color.dark_blue()
    )
    await interaction.channel.send(embed=embed, view=TicketCreateView())
    await interaction.response.send_message("✅ Destek paneli kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
        
