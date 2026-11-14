import os
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
        print("BTF Kara Kuvvetleri Global Guvenlik ve Ticket Sistemi Senkronize Edildi.")

bot = GlobalGuardBot()

MAIN_HEADQUARTER_GUILD_ID = 0  
CENTRAL_LOG_CHANNEL_ID = 0     

YASAKLI_KELIMELER = ["kufur1", "kufur2", "reklamlinki"]

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

        embed = discord.Embed(
            title="BTF Karargah Destek Hatti",
            description=f"Merhaba {interaction.user.mention}, yetkililer kisa sure icinde sizinle ilgilenecektir.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Destek kanaliniz olusturuldu: {ticket_channel.mention}", ephemeral=True)

class GlobalGuardActionView(discord.ui.View):
    def __init__(self, target_user_id: int, action_reason: str):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.action_reason = action_reason

    @discord.ui.button(label="Onayla (Serbest Birak)", style=discord.ButtonStyle.green, custom_id="global_approve")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Yonetici yetkin olmali!", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Durum", value=f"Onaylandi - Yetkili: {interaction.user.mention}", inline=False)
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
        embed.add_field(name="Durum", value=f"Tum Sunuculardan Tam Yasaklandi!", inline=False)
        await interaction.message.edit(view=self, embed=embed)

        success_count = 0
        for guild in bot.guilds:
            try:
                member = await guild.fetch_member(self.target_user_id)
                if member:
                    try:
                        dm_embed = discord.Embed(
                            title="BTF Kara Kuvvetleri - Global Yasaklama",
                            description=f"Sebep: {self.action_reason}",
                            color=discord.Color.red()
                        )
                        await member.send(embed=dm_embed)
                    except:
                        pass
                    
                    await guild.ban(member, reason=self.action_reason)
                    success_count += 1
            except:
                pass

        await interaction.response.send_message(f"Islem basarili! {success_count} sunucudan yasaklandi.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="BTF Askeri Guvenlik"))

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

@bot.tree.command(name="merkezayarla", description="Global log kanalini belirler.")
@app_commands.default_permissions(administrator=True)
async def slash_merkezayarla(interaction: discord.Interaction, kanal: discord.TextChannel):
    global MAIN_HEADQUARTER_GUILD_ID, CENTRAL_LOG_CHANNEL_ID
    MAIN_HEADQUARTER_GUILD_ID = interaction.guild.id
    CENTRAL_LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"Merkez Karargah ayarlandi: {kanal.mention}", ephemeral=True)

@bot.tree.command(name="tamyasakla", description="Kullaniciyi tum sunuculardan banlar.")
@app_commands.default_permissions(ban_members=True)
async def slash_tamyasakla(interaction: discord.Interaction, uye_id: str, sebep: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        target_id = int(uye_id)
    except ValueError:
        await interaction.followup.send("Gecersiz ID!", ephemeral=True)
        return

    success_count = 0
    for guild in bot.guilds:
        try:
            member = await guild.fetch_member(target_id)
            if member:
                try:
                    dm_embed = discord.Embed(
                        title="BTF Kara Kuvvetleri - Global Yasaklama",
                        description=f"Sebep: {sebep}",
                        color=discord.Color.dark_red()
                    )
                    await member.send(embed=dm_embed)
                except:
                    pass
                
                await guild.ban(member, reason=sebep)
                success_count += 1
        except:
            pass

    await interaction.followup.send(f"Islem tamam! {success_count} sunucudan yasaklandi.", ephemeral=True)

@bot.tree.command(name="yasakkaldir", description="Global yasagi kaldirir.")
@app_commands.default_permissions(ban_members=True)
async def slash_yasakkaldir(interaction: discord.Interaction, uye_id: str):
    await interaction.response.defer(ephemeral=True)
    try:
        target_id = int(uye_id)
        user = await bot.fetch_user(target_id)
    except:
        await interaction.followup.send("Kullanici bulunamadi.", ephemeral=True)
        return

    unban_count = 0
    for guild in bot.guilds:
        try:
            await guild.unban(user, reason="Global Yasak Kaldirma")
            unban_count += 1
        except:
            pass

    await interaction.followup.send(f"Yasagi {unban_count} sunucudan kaldirildi.", ephemeral=True)

@bot.tree.command(name="dm", description="Kullaniciya ozel mesaj gonderir.")
@app_commands.default_permissions(administrator=True)
async def slash_dm(interaction: discord.Interaction, uye: discord.Member, mesaj: str):
    await interaction.response.defer(ephemeral=True)
    try:
        dm_embed = discord.Embed(
            title="BTF Karargah Resmi Bildirimi",
            description=mesaj,
            color=discord.Color.gold()
        )
        await uye.send(embed=dm_embed)
        await interaction.followup.send(f"Mesaj {uye.mention} adli kullaniciya iletildi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Mesaj atilamadi: {e}", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Destek paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def slash_ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="BTF Kara Kuvvetleri Destek Merkezi",
        description="Destek talebi acmak icin asagidaki butona tiklayiniz.",
        color=discord.Color.dark_blue()
    )
    await interaction.channel.send(embed=embed, view=TicketCreateView())
    await interaction.response.send_message("Destek paneli kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
li: {interaction.user}")
        await uye.send(embed=dm_embed)
        await interaction.followup.send(f"Mesaj {uye.mention} adli kullaniciya ozelden iletildi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Kullaniciya mesaj atilamadi: {e}", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Destek talebi acilabilecek paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def slash_ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="BTF Kara Kuvvetleri Destek ve Iletisim Merkezi",
        description="Yetkililerle iletisime gecmek icin asagidaki Destek Talebi Ac butonuna tiklayiniz.",
        color=discord.Color.dark_blue()
    )
    await interaction.channel.send(embed=embed, view=TicketCreateView())
    await interaction.response.send_message("Destek paneli bu kanala basariyla kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
li: {interaction.user}")
        await uye.send(embed=dm_embed)
        await interaction.followup.send(f"Mesaj {uye.mention} adli kullaniciya ozelden iletildi.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Kullaniciya mesaj atilamadi: {e}", ephemeral=True)

@bot.tree.command(name="ticketkur", description="Destek talebi acilabilecek paneli kurar.")
@app_commands.default_permissions(administrator=True)
async def slash_ticketkur(interaction: discord.Interaction):
    embed = discord.Embed(
        title="BTF Kara Kuvvetleri Destek ve Iletisim Merkezi",
        description="Yetkililerle iletisime gecmek icin asagidaki Destek Talebi Ac butonuna tiklayiniz.",
        color=discord.Color.dark_blue()
    )
    await interaction.channel.send(embed=embed, view=TicketCreateView())
    await interaction.response.send_message("Destek paneli bu kanala basariyla kuruldu!", ephemeral=True)

bot.run(os.getenv("TOKEN"))
              await guild.ban(member, reason=f"Global Tam Yasakla Komutu | Sebep: {sebep} | Yetkili: {interaction.user}")
                success_count += 1
        except:
            pass

    await interaction.followup.send(f"🚨 İşlem tamam! Belirtilen kullanıcı botun bağlı olduğu **{success_count}** farklı sunucudan tamamen yasaklandı.", ephemeral=True)

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

# Bot tokenini Railway gizli değişkeninden güvenli bir şekilde alır
bot.run(os.getenv("TOKEN"))
asaklama",
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
