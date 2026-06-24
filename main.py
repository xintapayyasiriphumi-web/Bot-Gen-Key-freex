import discord
from discord.ext import commands
from discord import app_commands
import requests
import json
import os
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────
DISCORD_TOKEN      = os.environ.get("DISCORD_TOKEN", "YOUR_BOT_TOKEN")
KEYAUTH_SELLER_KEY = os.environ.get("KEYAUTH_SELLER_KEY", "5d715834aa685ad04184da6e1c6a6c32")
KEYAUTH_APP_NAME   = "InsidexToolbox"
KEYAUTH_OWNER_ID   = "h73NBoWgLW"
ALLOWED_ROLE_ID    = 1400021532620886056
COOLDOWN_FILE      = "cooldowns.json"

PRODUCTS = {
    "toolbox": {
        "label": "INSIDEX Toolbox",
        "description": "Windows Optimization Suite",
        "expiry": 1,  # วัน
        "emoji": "🛠️",
    }
}

# ── Cooldown helpers ──────────────────────────────────────────────────────
def load_cooldowns():
    try:
        if os.path.exists(COOLDOWN_FILE):
            with open(COOLDOWN_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_cooldowns(data):
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(data, f)

def check_cooldown(user_id: str):
    """คืน None ถ้าผ่าน cooldown แล้ว, คืน datetime ที่จะหมด cooldown ถ้ายังไม่ผ่าน"""
    data = load_cooldowns()
    if user_id in data:
        last_gen = datetime.fromisoformat(data[user_id])
        expires  = last_gen + timedelta(hours=24)
        if datetime.utcnow() < expires:
            return expires
    return None

def set_cooldown(user_id: str):
    data = load_cooldowns()
    data[user_id] = datetime.utcnow().isoformat()
    save_cooldowns(data)

# ── KeyAuth Seller API ────────────────────────────────────────────────────
def keyauth_create_key(expiry_days: int) -> dict:
    """สร้าง key ใหม่ผ่าน KeyAuth Seller API"""
    try:
        r = requests.get(
            "https://keyauth.win/api/seller/",
            params={
                "sellerkey": KEYAUTH_SELLER_KEY,
                "type":      "add",
                "format":    "JSON",
                "expiry":    expiry_days,
                "mask":      "XXXXXX-XXXXXX-XXXXXX-XXXXXX",
                "level":     "1",
                "amount":    "1",
                "owner":     KEYAUTH_OWNER_ID,
                "app":       KEYAUTH_APP_NAME,
            },
            timeout=10
        )
        return r.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

# ── Bot setup ─────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ── Dropdown ─────────────────────────────────────────────────────────────
class ProductSelect(discord.ui.Select):
    def __init__(self, user: discord.Member):
        self.user = user
        options = [
            discord.SelectOption(
                label=v["label"],
                value=k,
                description=v["description"],
                emoji=v["emoji"]
            )
            for k, v in PRODUCTS.items()
        ]
        super().__init__(
            placeholder="เลือกโปรแกรมที่ต้องการ Gen Key...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # ตรวจว่าเป็นคนกดเอง
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ คุณไม่ใช่เจ้าของ command นี้", ephemeral=True
            )
            return

        product_key = self.values[0]
        product     = PRODUCTS[product_key]
        user_id     = str(interaction.user.id)

        # เช็ค cooldown
        cd = check_cooldown(user_id)
        if cd:
            remaining = cd - datetime.utcnow()
            hours     = int(remaining.total_seconds() // 3600)
            minutes   = int((remaining.total_seconds() % 3600) // 60)

            embed = discord.Embed(
                title="⏳ Cooldown Active",
                description=f"คุณได้ Gen Key ไปแล้วในช่วง 24 ชั่วโมงที่ผ่านมา",
                color=0xf59e0b
            )
            embed.add_field(
                name="เหลือเวลา",
                value=f"`{hours}h {minutes}m`",
                inline=False
            )
            embed.set_footer(text="INSIDEX Toolbox • Cooldown 24 Hours")
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Defer ก่อน เพราะ API อาจช้า
        await interaction.response.defer(ephemeral=False)

        # สร้าง key จาก KeyAuth
        result = keyauth_create_key(product["expiry"])

        if not result.get("success"):
            embed = discord.Embed(
                title="❌ Gen Key ล้มเหลว",
                description=f"```{result.get('message', 'Unknown error')}```",
                color=0xef4444
            )
            embed.set_footer(text="INSIDEX Toolbox • ติดต่อ Admin ถ้ายังเกิดปัญหา")
            await interaction.edit_original_response(embed=embed, view=None)
            return

        # ดึง key จาก response
        key = result.get("key", "")
        if not key and "keys" in result:
            key = result["keys"][0] if result["keys"] else ""

        # set cooldown
        set_cooldown(user_id)

        # DM ส่ง key ให้ลูกค้า
        expiry_date = (datetime.utcnow() + timedelta(days=product["expiry"])).strftime("%d/%m/%Y %H:%M UTC")

        dm_embed = discord.Embed(
            title="🔑 INSIDEX License Key",
            description=f"ขอบคุณที่ใช้บริการ **INSIDEX**! นี่คือ key ของคุณ",
            color=0x8b5cf6
        )
        dm_embed.add_field(name="โปรแกรม", value=f"{product['emoji']} {product['label']}", inline=True)
        dm_embed.add_field(name="อายุ",    value=f"`{product['expiry']} วัน`",              inline=True)
        dm_embed.add_field(name="หมดอายุ", value=f"`{expiry_date}`",                        inline=True)
        dm_embed.add_field(
            name="🔐 License Key",
            value=f"```\n{key}\n```",
            inline=False
        )
        dm_embed.add_field(
            name="📌 วิธีใช้",
            value="เปิด **INSIDEX Toolbox** แล้วกรอก key ในช่อง License Key",
            inline=False
        )
        dm_embed.set_footer(text="INSIDEX Toolbox • อย่าแชร์ key นี้ให้ใคร")
        dm_embed.timestamp = discord.utils.utcnow()

        try:
            await interaction.user.send(embed=dm_embed)
            dm_success = True
        except discord.Forbidden:
            dm_success = False

        # แก้ message ใน channel
        if dm_success:
            success_embed = discord.Embed(
                title="✅ Gen Key สำเร็จ!",
                description=f"{interaction.user.mention} ส่ง key ให้ทาง DM แล้ว 📩",
                color=0x22c55e
            )
            success_embed.add_field(name="โปรแกรม", value=f"{product['emoji']} {product['label']}", inline=True)
            success_embed.add_field(name="Cooldown", value="`24 ชั่วโมง`", inline=True)
            success_embed.set_footer(text="INSIDEX Toolbox • Gen Key System")
            success_embed.timestamp = discord.utils.utcnow()
        else:
            success_embed = discord.Embed(
                title="⚠️ Gen Key สำเร็จ แต่ส่ง DM ไม่ได้",
                description=f"{interaction.user.mention} กรุณาเปิด DM แล้วลองใหม่ หรือติดต่อ Admin",
                color=0xf59e0b
            )
            success_embed.add_field(
                name="🔐 Key ของคุณ",
                value=f"```\n{key}\n```",
                inline=False
            )
            success_embed.set_footer(text="INSIDEX Toolbox • Gen Key System")

        await interaction.edit_original_response(embed=success_embed, view=None)


class ProductView(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=60)
        self.add_item(ProductSelect(user))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True


# ── Slash Command ─────────────────────────────────────────────────────────
@tree.command(name="genkey", description="Gen License Key สำหรับ INSIDEX Toolbox")
async def genkey(interaction: discord.Interaction):
    # เช็ค role
    role_ids = [r.id for r in interaction.user.roles]
    if ALLOWED_ROLE_ID not in role_ids:
        embed = discord.Embed(
            title="❌ ไม่มีสิทธิ์",
            description="คุณไม่มี role ที่จำเป็นสำหรับ Gen Key",
            color=0xef4444
        )
        embed.set_footer(text="INSIDEX Toolbox • ซื้อสินค้าก่อนเพื่อรับ role")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # เช็ค cooldown ก่อนโชว์ dropdown
    cd = check_cooldown(str(interaction.user.id))
    if cd:
        remaining = cd - datetime.utcnow()
        hours   = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        embed = discord.Embed(
            title="⏳ Cooldown Active",
            description="คุณได้ Gen Key ไปแล้วในช่วง 24 ชั่วโมงที่ผ่านมา",
            color=0xf59e0b
        )
        embed.add_field(name="เหลือเวลา", value=f"`{hours}h {minutes}m`", inline=False)
        embed.set_footer(text="INSIDEX Toolbox • Cooldown 24 Hours")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # โชว์ dropdown
    embed = discord.Embed(
        title="🔑 INSIDEX Gen Key",
        description="เลือกโปรแกรมที่ต้องการ Gen License Key",
        color=0x8b5cf6
    )
    embed.add_field(name="⏱️ Cooldown", value="`24 ชั่วโมง / ครั้ง`", inline=True)
    embed.add_field(name="📦 สินค้า",   value="`INSIDEX Toolbox`",     inline=True)
    embed.set_footer(text="INSIDEX Toolbox • Gen Key System")
    embed.timestamp = discord.utils.utcnow()

    view = ProductView(interaction.user)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ── Admin command: reset cooldown ─────────────────────────────────────────
@tree.command(name="resetcd", description="[Admin] Reset cooldown ของ user")
@app_commands.describe(user="User ที่ต้องการ reset cooldown")
async def resetcd(interaction: discord.Interaction, user: discord.Member):
    # เช็คว่าเป็น admin
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    data = load_cooldowns()
    user_id = str(user.id)
    if user_id in data:
        del data[user_id]
        save_cooldowns(data)
        await interaction.response.send_message(
            f"✅ Reset cooldown ของ {user.mention} แล้ว", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ {user.mention} ไม่มี cooldown อยู่", ephemeral=True
        )


# ── Events ────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    print(f"[INSIDEX] Bot online: {bot.user}")
    print(f"[INSIDEX] Slash commands synced")


bot.run(DISCORD_TOKEN)