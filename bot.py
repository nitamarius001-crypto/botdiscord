import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import os
import random

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

conn = sqlite3.connect("pubg.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    rank TEXT,
    kd REAL,
    pubg_id TEXT
)
""")
conn.commit()

welcome_channel_id = None
ann_channel_id = None
reminders_channel_id = None

RANKS = [
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
    "Diamond",
    "Crown",
    "Ace",
    "Ace Master",
    "Ace Dominator",
    "Conqueror"
]

RANK_STYLES = {
    "Bronze":        {"color": 0xcd7f32, "emoji": "🥉"},
    "Silver":        {"color": 0xaab7b8, "emoji": "🪙"},
    "Gold":          {"color": 0xf1c40f, "emoji": "🥇"},
    "Platinum":      {"color": 0x1abc9c, "emoji": "💠"},
    "Diamond":       {"color": 0x3498db, "emoji": "💎"},
    "Crown":         {"color": 0x9b59b6, "emoji": "👑"},
    "Ace Dominator": {"color": 0xc0392b, "emoji": "💀"},
    "Ace Master":    {"color": 0xd35400, "emoji": "🔥"},
    "Ace":           {"color": 0xe67e22, "emoji": "🎖️"},
    "Conqueror":     {"color": 0xe74c3c, "emoji": "🏆"},
}

def get_rank_style(rank: str) -> dict:
    if rank in RANK_STYLES:
        return RANK_STYLES[rank]
    for tier, style in RANK_STYLES.items():
        if rank.startswith(tier):
            return style
    return {"color": 0x95a5a6, "emoji": "❓"}

def set_player(user_id, field, value):
    c.execute("INSERT OR IGNORE INTO players (id, rank, kd, pubg_id) VALUES (?, '', 0, '')", (user_id,))
    c.execute(f"UPDATE players SET {field}=? WHERE id=?", (value, user_id))
    conn.commit()

def get_player(user_id):
    c.execute("SELECT rank, kd, pubg_id FROM players WHERE id=?", (user_id,))
    return c.fetchone()

# ─── 4-HOUR REMINDER TASK ───────────────────────────────────────────────────

@tasks.loop(hours=4)
async def send_reminder():
    if not reminders_channel_id:
        return
    channel = bot.get_channel(reminders_channel_id)
    if not channel:
        return
    embed = discord.Embed(
        title="📋 COMENZI BOT — Actualizează-ți profilul!",
        description="Folosiți comenzile de mai jos pentru a vă configura profilul în clan! 💪",
        color=0x3498db
    )
    embed.add_field(
        name="👤 Profil personal",
        value=(
            "`/setrank` — Setează rankul tău PUBG (Bronze → Conqueror)\n"
            "`/setkd` — Setează KD-ul tău (ex: `4.50` sau `4,50`)\n"
            "`/setid` — Setează ID-ul tău din joc\n"
            "`/profile` — Vizualizează profilul tău complet"
        ),
        inline=False
    )
    embed.add_field(
        name="🏆 Statistici & Comparații",
        value=(
            "`/leaderboard` — Top 10 jucători după KD\n"
            "`/compare @user1 @user2` — Compară KD și rank între doi jucători"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Social & Distracție",
        value=(
            "`/squad` — Anunță că ești în căutare de squad\n"
            "`/invite @user <hartă>` — Invită un jucător pe o hartă\n"
            "`/clanta @user` — Dă la clantă cuiva 🤣\n"
            "`/ask <întrebare>` — Întrebări despre PUBG (arme, sens, locuri, tips...)"
        ),
        inline=False
    )
    embed.set_footer(text="💡 Scrie / în chat pentru a vedea toate comenzile disponibile!")
    await channel.send(embed=embed)

# ─── EVENTS ─────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"BOT ONLINE: {bot.user}")
    await bot.tree.sync()
    if not send_reminder.is_running():
        send_reminder.start()

@bot.event
async def on_member_join(member):
    data = get_player(member.id)
    rank = data[0] if data else "New"
    kd = data[1] if data else 0

    channel = None
    if welcome_channel_id:
        channel = member.guild.get_channel(welcome_channel_id)
    else:
        channel = member.guild.system_channel

    if channel:
        embed = discord.Embed(
            title="👋 WELCOME TO PUBG CLAN",
            description=f"👤 Player: {member.name}\n🏆 Rank: {rank}\n💀 KD: {kd}\n\n🔥 Good luck & have fun!",
            color=0x00ff00
        )
        await channel.send(embed=embed)

# ─── ADMIN COMMANDS (ephemeral, admin only) ──────────────────────────────────

@bot.tree.command(name="setwelcomech", description="[ADMIN] Set welcome channel")
@app_commands.checks.has_permissions(administrator=True)
async def setwelcomech(interaction: discord.Interaction, channel: discord.TextChannel):
    global welcome_channel_id
    welcome_channel_id = channel.id
    embed = discord.Embed(
        title="👋 WELCOME CHANNEL SET",
        description=f"Channel: {channel.mention}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="setannch", description="[ADMIN] Set announcements channel")
@app_commands.checks.has_permissions(administrator=True)
async def setannch(interaction: discord.Interaction, channel: discord.TextChannel):
    global ann_channel_id
    ann_channel_id = channel.id
    embed = discord.Embed(
        title="📢 ANNOUNCEMENTS CHANNEL SET",
        description=f"Channel: {channel.mention}",
        color=0xff0000
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="randoms", description="[ADMIN] Set channel for 4h command reminders")
@app_commands.checks.has_permissions(administrator=True)
async def randoms(interaction: discord.Interaction, channel: discord.TextChannel):
    global reminders_channel_id
    reminders_channel_id = channel.id
    embed = discord.Embed(
        title="📋 REMINDER CHANNEL SET",
        description=f"Botul va trimite lista comenzilor la fiecare **4 ore** în {channel.mention}",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="announce", description="[ADMIN] Send an announcement to the announcements channel")
@app_commands.checks.has_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str):
    if not ann_channel_id:
        await interaction.response.send_message(
            "❌ Announcements channel not set! Use `/setannch` first.",
            ephemeral=True
        )
        return
    channel = bot.get_channel(ann_channel_id)
    if not channel:
        await interaction.response.send_message(
            "❌ Could not find the announcements channel.",
            ephemeral=True
        )
        return
    embed = discord.Embed(
        title="📢 ANNOUNCEMENT",
        description=message,
        color=0xff0000
    )
    embed.set_footer(text=f"By {interaction.user.display_name}")
    await channel.send(embed=embed)
    await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)

@bot.tree.command(name="staffan", description="[ADMIN] Call all staff to STAFF ONLY channel")
@app_commands.checks.has_permissions(administrator=True)
async def staffan(interaction: discord.Interaction):
    if not ann_channel_id:
        await interaction.response.send_message(
            "❌ Announcements channel not set! Use `/setannch` first.",
            ephemeral=True
        )
        return
    channel = bot.get_channel(ann_channel_id)
    if not channel:
        await interaction.response.send_message(
            "❌ Could not find the announcements channel.",
            ephemeral=True
        )
        return
    embed = discord.Embed(
        title="📢 STAFF ANNOUNCEMENT",
        description="Laderul roaga tot stafful sa urce sus la canalul **\"STAFF ONLY\"** pentru sedinta!!!",
        color=0xff0000
    )
    embed.set_footer(text=f"By {interaction.user.display_name}")
    await channel.send("@everyone", embed=embed)
    await interaction.response.send_message("✅ Staff announcement sent!", ephemeral=True)

class MatchView(discord.ui.View):
    def __init__(self, harta: str, ora: str, locuri: int):
        super().__init__(timeout=None)
        self.harta = harta
        self.ora = ora
        self.locuri = locuri
        self.ready_users: list[str] = []

    def build_embed(self) -> discord.Embed:
        count = len(self.ready_users)
        full = count >= self.locuri

        embed = discord.Embed(
            title="🎮 MECI ANUNȚAT!",
            color=0x00ff00 if full else 0xe74c3c
        )
        embed.add_field(name="🗺️ Hartă", value=self.harta, inline=True)
        embed.add_field(name="⏰ Ora", value=self.ora, inline=True)

        lines = []
        for i in range(self.locuri):
            if i < count:
                lines.append(f"✅ **Loc {i+1}** — {self.ready_users[i]}")
            else:
                lines.append(f"⬜ **Loc {i+1}** — *Liber*")
        slots_text = "\n".join(lines)

        bar_filled = "🟩" * count
        bar_empty  = "⬜" * (self.locuri - count)
        progress   = f"{bar_filled}{bar_empty}  **{count}/{self.locuri}**"

        embed.add_field(name=f"👥 Squad — {progress}", value=slots_text, inline=False)

        status = "✅ Squad FULL — Gata de meci!" if full else "Apasă Ready dacă ești pregătit!"
        embed.set_footer(text=status)
        return embed

    def update_button(self):
        count = len(self.ready_users)
        full = count >= self.locuri
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.label = f"✅ Ready ({count}/{self.locuri})"
                child.style = discord.ButtonStyle.secondary if full else discord.ButtonStyle.success
                child.disabled = full

    @discord.ui.button(label="✅ Ready (0/?)", style=discord.ButtonStyle.success)
    async def ready_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        mention = interaction.user.mention
        name = interaction.user.display_name
        if mention in self.ready_users:
            await interaction.response.send_message("⚠️ Ești deja ready!", ephemeral=True)
            return
        self.ready_users.append(mention)
        self.update_button()
        await interaction.message.edit(embed=self.build_embed(), view=self)
        count = len(self.ready_users)
        if count >= self.locuri:
            await interaction.response.send_message(f"✅ {name} e ready! 🎉 **Squad complet — {count}/{self.locuri}!**", ephemeral=True)
        else:
            await interaction.response.send_message(f"✅ {name} e ready! **{count}/{self.locuri}** locuri ocupate.", ephemeral=True)

@bot.tree.command(name="startm", description="[ADMIN] Anunță un meci cu hartă, oră și locuri în squad")
@app_commands.checks.has_permissions(administrator=True)
async def startm(interaction: discord.Interaction, harta: str, ora: str, locuri: int):
    await interaction.response.defer(ephemeral=True)
    view = MatchView(harta=harta, ora=ora, locuri=locuri)
    view.ready_users.append(interaction.user.mention)
    view.update_button()
    embed = view.build_embed()
    if ann_channel_id:
        channel = bot.get_channel(ann_channel_id)
        if channel:
            await channel.send("@everyone", embed=embed, view=view)
            await interaction.followup.send(f"✅ Meciul a fost anunțat! Ești deja ready — **1/{locuri}**.", ephemeral=True)
            return
    await interaction.followup.send(embed=embed, view=view)

# ─── PUBLIC COMMANDS ─────────────────────────────────────────────────────────

@bot.tree.command(name="profile", description="View PUBG profile")
async def profile(interaction: discord.Interaction):
    data = get_player(interaction.user.id)
    if not data:
        await interaction.response.send_message("❌ Nu ai profil!")
        return
    rank, kd, pid = data
    style = get_rank_style(rank) if rank else {"color": 0x3498db, "emoji": "🎮"}
    embed = discord.Embed(title=f"{style['emoji']} PUBG PROFILE", color=style["color"])
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="🏆 Rank", value=f"{style['emoji']} **{rank}**" if rank else "*Not set*", inline=False)
    embed.add_field(name="💀 KD", value=f"**{kd}**", inline=True)
    embed.add_field(name="🆔 PUBG ID", value=pid or "*Not set*", inline=True)
    await interaction.response.send_message(embed=embed)

async def rank_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=f"{RANK_STYLES[r]['emoji']} {r}", value=r)
        for r in RANKS if current.lower() in r.lower()
    ]

@bot.tree.command(name="setrank", description="Set your PUBG rank")
@app_commands.autocomplete(rank=rank_autocomplete)
async def setrank(interaction: discord.Interaction, rank: str):
    set_player(interaction.user.id, "rank", rank)
    style = get_rank_style(rank)
    embed = discord.Embed(
        title=f"{style['emoji']} RANK UPDATED",
        description=f"{interaction.user.mention} a setat rankul la **{rank}**",
        color=style["color"]
    )
    embed.add_field(name="🏆 Rank", value=f"{style['emoji']} **{rank}**", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setkd", description="Set KD (ex: 4.50 sau 4,50)")
async def setkd(interaction: discord.Interaction, kd: str):
    try:
        kd_value = float(kd.replace(",", "."))
        if kd_value < 0 or kd_value > 100:
            raise ValueError
    except ValueError:
        await interaction.response.send_message(
            "❌ KD invalid! Folosește format: `4.50` sau `4,50`",
            ephemeral=True
        )
        return
    set_player(interaction.user.id, "kd", kd_value)
    embed = discord.Embed(
        title="💀 KD UPDATED",
        description=f"New KD: **{kd_value:.2f}**",
        color=0x3498db
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="setid", description="Set your PUBG in-game ID")
async def setid(interaction: discord.Interaction, pid: str):
    set_player(interaction.user.id, "pubg_id", pid)
    embed = discord.Embed(
        title="🆔 ID SAVED",
        description=f"PUBG ID: **{pid}**",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="invite", description="Invite a player to a map")
async def invite(interaction: discord.Interaction, user: discord.Member, map: str):
    await user.send(f"🎮 {interaction.user.name} te invită pe **{map}**")
    embed = discord.Embed(
        title="📩 INVITE SENT",
        description=f"{user.name} a fost invitat pe {map}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

CLANTA_GIFS = [
    "https://media.tenor.com/wT5_OPbFfZQAAAAC/anime-slap.gif",
    "https://media.tenor.com/GDPodJbMEyYAAAAC/slap-anime.gif",
    "https://media.tenor.com/e_CIiWB1NJEAAAAC/baka-anime-slap.gif",
    "https://media.tenor.com/2PFJQdnpRu8AAAAC/slap-cat.gif",
    "https://media.tenor.com/BoGRECqS1YIAAAAC/slap-slap-hard.gif",
]

@bot.tree.command(name="clanta", description="Da la clanta cuiva")
async def clanta(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer(ephemeral=True)
    gif = random.choice(CLANTA_GIFS)
    embed = discord.Embed(
        title="🤣 CLANTA!",
        description=f"{interaction.user.mention} i-a dat la clanta lui {user.mention} 🤣",
        color=0xff9900
    )
    embed.set_image(url=gif)
    if ann_channel_id:
        channel = bot.get_channel(ann_channel_id)
        if channel:
            await channel.send(embed=embed)
            await interaction.followup.send("✅ Clanta trimisă!", ephemeral=True)
            return
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="squad", description="Announce you're looking for a squad")
async def squad(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 SQUAD REQUEST",
        description=f"{interaction.user.name} caută squad! @everyone",
        color=0x9b59b6
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="compare", description="Compară KD și rank între doi jucători")
async def compare(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    data1 = get_player(user1.id)
    data2 = get_player(user2.id)

    if not data1 and not data2:
        await interaction.response.send_message("❌ Niciunul dintre jucători nu are profil!", ephemeral=True)
        return
    if not data1:
        await interaction.response.send_message(f"❌ {user1.display_name} nu are profil!", ephemeral=True)
        return
    if not data2:
        await interaction.response.send_message(f"❌ {user2.display_name} nu are profil!", ephemeral=True)
        return

    rank1, kd1, _ = data1
    rank2, kd2, _ = data2

    rank1_idx = RANKS.index(rank1) if rank1 in RANKS else -1
    rank2_idx = RANKS.index(rank2) if rank2 in RANKS else -1

    if kd1 > kd2:
        kd_winner = f"🏆 {user1.display_name}"
        kd_loser  = f"💀 {user2.display_name}"
    elif kd2 > kd1:
        kd_winner = f"🏆 {user2.display_name}"
        kd_loser  = f"💀 {user1.display_name}"
    else:
        kd_winner = "🤝 Egal"
        kd_loser  = ""

    if rank1_idx > rank2_idx:
        rank_winner = f"🏆 {user1.display_name}"
    elif rank2_idx > rank1_idx:
        rank_winner = f"🏆 {user2.display_name}"
    else:
        rank_winner = "🤝 Egal"

    if kd1 > kd2 and rank1_idx > rank2_idx:
        overall = f"👑 {user1.display_name} e mai bun!"
    elif kd2 > kd1 and rank2_idx > rank1_idx:
        overall = f"👑 {user2.display_name} e mai bun!"
    else:
        overall = "⚔️ Prea strâns — greu de zis!"

    embed = discord.Embed(
        title=f"⚔️ {user1.display_name}  vs  {user2.display_name}",
        color=0xe74c3c
    )
    embed.add_field(
        name="💀 KD",
        value=f"`{user1.display_name}` → **{kd1}**\n`{user2.display_name}` → **{kd2}**\n{kd_winner}",
        inline=True
    )
    embed.add_field(
        name="🏆 Rank",
        value=f"`{user1.display_name}` → **{rank1 or 'N/A'}**\n`{user2.display_name}` → **{rank2 or 'N/A'}**\n{rank_winner}",
        inline=True
    )
    embed.add_field(name="🎯 Verdict", value=overall, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Top 10 players ranked by KD")
async def leaderboard(interaction: discord.Interaction):
    c.execute("SELECT id, rank, kd FROM players WHERE kd > 0 ORDER BY kd DESC LIMIT 10")
    rows = c.fetchall()

    if not rows:
        embed = discord.Embed(
            title="🏆 LEADERBOARD",
            description="❌ Nu există jucători în leaderboard încă!",
            color=0xffd700
        )
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(title="🏆 PUBG LEADERBOARD — Top KD", color=0xffd700)

    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (user_id, rank, kd) in enumerate(rows):
        medal = medals[i] if i < 3 else f"`#{i+1}`"
        try:
            user = await bot.fetch_user(user_id)
            name = user.display_name
        except Exception:
            name = f"Player {user_id}"
        rank_display = rank if rank else "Unranked"
        lines.append(f"{medal} **{name}** — 💀 {kd} KD | 🏆 {rank_display}")

    embed.description = "\n".join(lines)
    embed.set_footer(text="Sorted by KD ratio")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 PUBG BOT — Comenzi Disponibile",
        description="Toate comenzile pe care le poți folosi:",
        color=0x3498db
    )
    embed.add_field(
        name="👤 Profil Personal",
        value=(
            "`/setrank` — Setează rankul tău PUBG (Bronze → Conqueror)\n"
            "`/setkd` — Setează KD-ul tău (ex: `4.50` sau `4,50`)\n"
            "`/setid` — Setează ID-ul tău din joc\n"
            "`/profile` — Vizualizează profilul tău complet"
        ),
        inline=False
    )
    embed.add_field(
        name="🏆 Statistici & Comparații",
        value=(
            "`/leaderboard` — Top 10 jucători după KD\n"
            "`/compare @user1 @user2` — Compară KD și rank între doi jucători"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Social & Distracție",
        value=(
            "`/squad` — Anunță că ești în căutare de squad\n"
            "`/invite @user <hartă>` — Invită un jucător pe o hartă\n"
            "`/clanta @user` — Dă la clantă cuiva 🤣\n"
            "`/ask <întrebare>` — Întrebări despre PUBG (arme, sens, locuri, tips...)"
        ),
        inline=False
    )
    embed.set_footer(text="💡 Scrie / în chat pentru a vedea toate comenzile disponibile!")
    await interaction.response.send_message(embed=embed)

# ─── ASK COMMAND ─────────────────────────────────────────────────────────────

PUBG_KB = {
    "gun": {
        "keywords_en": ["best gun", "best weapon", "best ar", "best rifle", "best smg", "best sniper", "best dmr", "weapon tier", "gun tier"],
        "keywords_ro": ["cea mai buna arma", "cel mai bun pistol", "arme", "pusca", "mitraliera", "sniper", "arma buna", "cea mai tare arma"],
        "title_en": "🔫 Best Guns in PUBG Mobile",
        "title_ro": "🔫 Cele Mai Bune Arme în PUBG Mobile",
        "answer_en": (
            "**S Tier (Best):**\n"
            "• `M416` — Best all-round AR, low recoil, very stable\n"
            "• `AKM` — Highest AR damage, beast at close range\n"
            "• `AWM` — Best sniper, one-shots level 3 helmet\n\n"
            "**A Tier:**\n"
            "• `Beryl M762` — High damage AR, hard to control but lethal\n"
            "• `Mini 14` — Great DMR, very stable at long range\n"
            "• `UMP45` — Best SMG, melts enemies in close range\n\n"
            "**B Tier:**\n"
            "• `SCAR-L` — Stable but lower damage than M416\n"
            "• `SKS` — Good DMR with attachments\n"
            "• `Vector` — High fire rate SMG, deadly in CQC"
        ),
        "answer_ro": (
            "**S Tier (Cele mai bune):**\n"
            "• `M416` — Cea mai bună armă de asalt, recul mic, foarte stabilă\n"
            "• `AKM` — Cel mai mare damage la AR, devastatoare la aproape\n"
            "• `AWM` — Cel mai bun sniper, one-shot chiar și cu cască nivel 3\n\n"
            "**A Tier:**\n"
            "• `Beryl M762` — Damage mare, greu de controlat dar letală\n"
            "• `Mini 14` — DMR excelent, foarte stabil la distanță\n"
            "• `UMP45` — Cel mai bun SMG, distruge la distanță mică\n\n"
            "**B Tier:**\n"
            "• `SCAR-L` — Stabil dar damage mai mic decât M416\n"
            "• `SKS` — DMR bun cu attachments\n"
            "• `Vector` — Rată de tragere mare, mortal în CQC"
        ),
    },
    "sensitivity": {
        "keywords_en": ["sensitivity", "best sens", "gyroscope", "aim settings", "recoil control", "sens settings"],
        "keywords_ro": ["sensibilitate", "sens", "giroscop", "setari aims", "recoil", "setari sensibilitate", "cea mai buna sensibilitate"],
        "title_en": "🎯 Best Sensitivity Settings",
        "title_ro": "🎯 Cele Mai Bune Setări de Sensibilitate",
        "answer_en": (
            "**Camera Sensitivity (No Scope):**\n"
            "• 3rd Person: `100–120`\n"
            "• 1st Person: `100–110`\n"
            "• Camera: `80–100`\n\n"
            "**ADS Sensitivity:**\n"
            "• Red Dot / Holo: `55–65`\n"
            "• 2x Scope: `45–55`\n"
            "• 3x Scope: `35–45`\n"
            "• 4x Scope: `25–35`\n"
            "• 6x Scope: `15–25`\n"
            "• 8x Scope: `10–15`\n\n"
            "**Gyroscope:** `Always On` → 300 all scopes (adjust per feel)\n\n"
            "💡 *Tip: Lower sens = more accurate at long range. Start at 50 and tune from there.*"
        ),
        "answer_ro": (
            "**Sensibilitate Cameră (Fără Lunetă):**\n"
            "• 3rd Person: `100–120`\n"
            "• 1st Person: `100–110`\n"
            "• Cameră: `80–100`\n\n"
            "**Sensibilitate ADS:**\n"
            "• Red Dot / Holo: `55–65`\n"
            "• Lunetă 2x: `45–55`\n"
            "• Lunetă 3x: `35–45`\n"
            "• Lunetă 4x: `25–35`\n"
            "• Lunetă 6x: `15–25`\n"
            "• Lunetă 8x: `10–15`\n\n"
            "**Giroscop:** `Mereu Activ` → 300 la toate lunetele (ajustează după feeling)\n\n"
            "💡 *Sfat: Sensibilitate mică = mai precis la distanță. Începe cu 50 și ajustează.*"
        ),
    },
    "landing": {
        "keywords_en": ["best landing", "best drop", "where to land", "hot drop", "safe drop", "landing spot", "best place to land"],
        "keywords_ro": ["unde aterizez", "unde sa aterizez", "cel mai bun loc", "locuri aterizare", "unde e loot", "hot drop", "loc sigur"],
        "title_en": "🪂 Best Landing Spots",
        "title_ro": "🪂 Cele Mai Bune Locuri de Aterizare",
        "answer_en": (
            "**Erangel 🔥 Hot Drops (high risk, high loot):**\n"
            "• `Pochinki` — Best loot, always crowded\n"
            "• `School / Rozhok` — High action, good for grinding kills\n"
            "• `Mylta Power` — Great loot, less contested than Pochinki\n\n"
            "**Safe Drops (good loot, fewer enemies):**\n"
            "• `Gatka` — Decent loot, usually quiet\n"
            "• `Primorsk` — Safe + good vehicles\n"
            "• `Stalber` — North area, often ignored\n\n"
            "**Miramar:**\n"
            "• Hot: `Pecado`, `El Pozo`\n"
            "• Safe: `Valle del Mar`, `Chumacera`\n\n"
            "**Sanhok:**\n"
            "• Hot: `Bootcamp`, `Ruins`\n"
            "• Safe: `Pai Nan`, `Na Kham`"
        ),
        "answer_ro": (
            "**Erangel 🔥 Hot Drop-uri (risc mare, loot mare):**\n"
            "• `Pochinki` — Cel mai bun loot, mereu aglomerat\n"
            "• `School / Rozhok` — Multă acțiune, bun pentru kills\n"
            "• `Mylta Power` — Loot excelent, mai puțin aglomerat\n\n"
            "**Drop-uri Sigure (loot bun, mai puțini dușmani):**\n"
            "• `Gatka` — Loot decent, de obicei liniștit\n"
            "• `Primorsk` — Sigur + vehicule bune\n"
            "• `Stalber` — Zonă nordică, adesea ignorată\n\n"
            "**Miramar:**\n"
            "• Hot: `Pecado`, `El Pozo`\n"
            "• Sigur: `Valle del Mar`, `Chumacera`\n\n"
            "**Sanhok:**\n"
            "• Hot: `Bootcamp`, `Ruins`\n"
            "• Sigur: `Pai Nan`, `Na Kham`"
        ),
    },
    "attachments": {
        "keywords_en": ["best attachment", "best scope", "compensator", "suppressor", "muzzle", "grip", "foregrip", "stock"],
        "keywords_ro": ["cele mai bune accesorii", "cel mai bun scope", "amortizor", "compensator", "grip", "luneta buna", "accesorii"],
        "title_en": "🔧 Best Attachments",
        "title_ro": "🔧 Cele Mai Bune Accesorii",
        "answer_en": (
            "**Muzzle:**\n"
            "• `Compensator` — Best for ARs, reduces recoil the most\n"
            "• `Suppressor` — Best for stealth, slightly less recoil reduction\n"
            "• `Flash Hider` — Good early game\n\n"
            "**Grip:**\n"
            "• `Angled Foregrip` — Best for ARs (reduces horizontal recoil)\n"
            "• `Vertical Foregrip` — Best for SMGs (reduces vertical recoil)\n"
            "• `Thumb Grip` — Great for ADS speed\n\n"
            "**Scope:**\n"
            "• `6x` — Most versatile, use it at 3x or 6x\n"
            "• `Red Dot` — Best for close range fights\n"
            "• `8x` — Snipers only\n\n"
            "**Stock:** Always equip it — reduces sway and recoil"
        ),
        "answer_ro": (
            "**Țeavă:**\n"
            "• `Compensator` — Cel mai bun pentru AR, reduce cel mai mult reculul\n"
            "• `Suppressor` — Cel mai bun pentru stealth\n"
            "• `Flash Hider` — Bun la începutul jocului\n\n"
            "**Grip:**\n"
            "• `Angled Foregrip` — Cel mai bun pentru AR (reduce reculul orizontal)\n"
            "• `Vertical Foregrip` — Cel mai bun pentru SMG (reduce reculul vertical)\n"
            "• `Thumb Grip` — Excelent pentru viteză ADS\n\n"
            "**Lunetă:**\n"
            "• `6x` — Cea mai versatilă, folosește-o la 3x sau 6x\n"
            "• `Red Dot` — Cel mai bun pentru luptă apropiată\n"
            "• `8x` — Doar pentru snipere\n\n"
            "**Stock:** Pune-l mereu — reduce balansul și reculul"
        ),
    },
    "tips": {
        "keywords_en": ["tips", "how to improve", "how to win", "how to get better", "pro tips", "survive longer", "chicken dinner", "rank up", "how to rank"],
        "keywords_ro": ["sfaturi", "cum sa castig", "cum sa ma imbunatatesc", "cum sa urc", "tips", "cum sa supravietuiesc", "chicken dinner", "cum sa rankuiesc"],
        "title_en": "💡 Pro Tips to Win More",
        "title_ro": "💡 Sfaturi Pro să Câștigi Mai Mult",
        "answer_en": (
            "**Early Game:**\n"
            "• Land on the edge of the plane's path for less competition\n"
            "• Loot fast — prioritize armor, helmet, gun, ammo\n"
            "• Grab a vehicle immediately if you land far from zone\n\n"
            "**Mid Game:**\n"
            "• Stay near the edge of the blue zone, not the center\n"
            "• Don't shoot unless you're sure — gunshots reveal your position\n"
            "• Use natural cover (rocks, trees, hills)\n\n"
            "**Late Game:**\n"
            "• Prone or crouch in tall grass\n"
            "• Always have a smoke grenade ready\n"
            "• Let enemies fight each other, then finish the winner\n"
            "• In final circle — position matters more than gun skill"
        ),
        "answer_ro": (
            "**Early Game:**\n"
            "• Aterizează la marginea traseului avionului pentru mai puțină competiție\n"
            "• Looteaza rapid — prioritizează armură, cască, armă, muniție\n"
            "• Ia un vehicul imediat dacă ești departe de zonă\n\n"
            "**Mid Game:**\n"
            "• Stai la marginea cercului albastru, nu în centru\n"
            "• Nu trage dacă nu ești sigur — împușcăturile îți dezvăluie poziția\n"
            "• Folosește acoperire naturală (pietre, copaci, dealuri)\n\n"
            "**Late Game:**\n"
            "• Culcă-te sau ghemuit în iarbă înaltă\n"
            "• Ai mereu o grenadă de fum pregătită\n"
            "• Lasă dușmanii să se bată între ei, apoi termină câștigătorul\n"
            "• În cercul final — poziționarea contează mai mult decât skill-ul cu arma"
        ),
    },
    "vehicle": {
        "keywords_en": ["best vehicle", "best car", "best bike", "best boat", "which vehicle", "car tier"],
        "keywords_ro": ["cel mai bun vehicul", "cea mai buna masina", "masina buna", "vehicul bun", "ce masina", "motocicleta"],
        "title_en": "🚗 Best Vehicles in PUBG",
        "title_ro": "🚗 Cele Mai Bune Vehicule în PUBG",
        "answer_en": (
            "**🥇 UAZ** — Best overall: fast, durable, fits 4 players\n"
            "**🥈 Buggy** — Fast and low profile, hard to hit\n"
            "**🥉 Dacia** — Good speed, fits 4, but fragile\n\n"
            "**Motorcycle** — Fastest on roads, but very risky (no protection)\n"
            "**Boat** — Essential on Erangel/Sanhok for crossing water fast\n"
            "**Mirado** — Erangel exclusive, very fast on roads\n\n"
            "💡 *Always use a UAZ in the final circles — the doors protect you*"
        ),
        "answer_ro": (
            "**🥇 UAZ** — Cel mai bun overall: rapid, rezistent, 4 jucători\n"
            "**🥈 Buggy** — Rapid și profil mic, greu de lovit\n"
            "**🥉 Dacia** — Viteză bună, 4 locuri, dar mai fragilă\n\n"
            "**Motocicleta** — Cel mai rapid pe drumuri, dar foarte riscant (fără protecție)\n"
            "**Barca** — Esențială pe Erangel/Sanhok pentru traversarea apei rapid\n"
            "**Mirado** — Exclusiv pe Erangel, foarte rapid pe drumuri\n\n"
            "💡 *Folosește mereu UAZ în cercurile finale — ușile te protejează*"
        ),
    },
    "throwable": {
        "keywords_en": ["best throwable", "grenade", "molotov", "smoke", "frag", "stun grenade", "best grenade"],
        "keywords_ro": ["grenade", "grenadă", "molotov", "fum", "cea mai buna grenada", "aruncabile"],
        "title_en": "💣 Best Throwables",
        "title_ro": "💣 Cele Mai Bune Grenade",
        "answer_en": (
            "**🥇 Smoke Grenade** — Most useful: cover revives, block sightlines, escape\n"
            "**🥈 Frag Grenade** — Flush enemies from cover, finish downed players\n"
            "**🥉 Molotov** — Force enemies to move, great for area denial\n"
            "**Stun Grenade** — Underrated, blinds enemies before pushing\n\n"
            "💡 *Always carry at least 2 smokes. They win more games than frags.*"
        ),
        "answer_ro": (
            "**🥇 Grenada de Fum** — Cea mai utilă: acoperă revive-uri, blochează liniile de vedere\n"
            "**🥈 Grenada Frag** — Scoate dușmanii din acoperiș, termină jucătorii doborâți\n"
            "**🥉 Molotov** — Forțează dușmanii să se miște, excelent pentru control zonă\n"
            "**Grenada Orbitoare** — Subestimată, orbește dușmanii înainte de push\n\n"
            "💡 *Poartă mereu cel puțin 2 smoke-uri. Câștigă mai multe jocuri decât frag-urile.*"
        ),
    },
}

def detect_language(question: str) -> str:
    ro_chars = set("ăîâșțĂÎÂȘȚ")
    ro_words = ["cel mai", "cea mai", "cele mai", "cum", "unde", "care", "arme", "arma", "sensibilitate",
                "sfaturi", "locuri", "aterizare", "grenada", "grenade", "masina", "vehicul", "accesorii", "buna", "bun"]
    q = question.lower()
    if any(c in ro_chars for c in question):
        return "ro"
    if any(w in q for w in ro_words):
        return "ro"
    return "en"

def find_topic(question: str):
    q = question.lower()
    for topic, data in PUBG_KB.items():
        all_kw = data["keywords_en"] + data["keywords_ro"]
        if any(kw in q for kw in all_kw):
            return topic, data
    return None, None

@bot.tree.command(name="ask", description="Întreabă orice despre PUBG Mobile")
async def ask(interaction: discord.Interaction, intrebare: str):
    lang = detect_language(intrebare)
    topic, data = find_topic(intrebare)

    if not data:
        if lang == "ro":
            embed = discord.Embed(
                title="❓ Întrebare necunoscută",
                description=(
                    f"Nu știu răspunsul la: **{intrebare}**\n\n"
                    "Încearcă una din acestea:\n"
                    "• `cea mai buna arma`\n"
                    "• `sensibilitate`\n"
                    "• `locuri de aterizare`\n"
                    "• `cele mai bune accesorii`\n"
                    "• `sfaturi sa castig`\n"
                    "• `cel mai bun vehicul`\n"
                    "• `grenade`"
                ),
                color=0xe74c3c
            )
        else:
            embed = discord.Embed(
                title="❓ Unknown question",
                description=(
                    f"I don't know the answer to: **{intrebare}**\n\n"
                    "Try one of these:\n"
                    "• `best gun`\n"
                    "• `best sensitivity`\n"
                    "• `best landing spots`\n"
                    "• `best attachments`\n"
                    "• `tips to win`\n"
                    "• `best vehicle`\n"
                    "• `best grenade`"
                ),
                color=0xe74c3c
            )
        await interaction.response.send_message(embed=embed)
        return

    title   = data["title_ro"]   if lang == "ro" else data["title_en"]
    answer  = data["answer_ro"]  if lang == "ro" else data["answer_en"]

    embed = discord.Embed(title=title, description=answer, color=0x1abc9c)
    embed.set_footer(text=f"Întrebat de {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

# ─── START ───────────────────────────────────────────────────────────────────

token = os.environ.get("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("DISCORD_BOT_TOKEN environment variable not set!")

bot.run(token)
