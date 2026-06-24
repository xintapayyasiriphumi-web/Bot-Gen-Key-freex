import discord
from discord import app_commands
import os

TOKEN = os.environ["DISCORD_TOKEN"]
STATUS_CHANNEL_ID = int(os.environ["STATUS_CHANNEL_ID"])

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

STATUS_STORED_MESSAGE_ID = None

STATUS_CONFIG = {
    "ว่าง": {
        "color": 0x1D9E75,
        "emoji": "🟢",
        "title": "ว่าง — รับงานได้",
        "desc": "ขณะนี้ admin ว่างและพร้อม setup ให้ลูกค้าได้ทันที\nติดต่อผ่าน Ticket ได้เลยครับ",
        "footer": "INSIDEX • STATUS",
    },
    "ยุ่ง": {
        "color": 0xEF9F27,
        "emoji": "🟡",
        "title": "ยุ่ง — กำลัง setup ให้ลูกค้าอยู่",
        "desc": "ขณะนี้ admin กำลัง setup ให้ลูกค้าอยู่\nอาจตอบช้าหน่อย แต่รับคิวได้ครับ",
        "footer": "INSIDEX • STATUS",
    },
    "เต็ม": {
        "color": 0xE24B4A,
        "emoji": "🔴",
        "title": "เต็ม — คิวล้น !",
        "desc": "ขณะนี้คิวเต็มแล้ว ยังไม่รับงานเพิ่ม\nกรุณารอและติดตามสถานะอีกครั้งในภายหลังครับ",
        "footer": "INSIDEX • STATUS",
    },
}


@client.event
async def on_ready():
    await tree.sync()
    print(f"Bot ready: {client.user}")


@tree.command(name="setstatus", description="เปลี่ยนสถานะ INSIDEX (ว่าง / ยุ่ง / เต็ม)")
@app_commands.describe(สถานะ="เลือกสถานะ: ว่าง, ยุ่ง, เต็ม")
@app_commands.choices(สถานะ=[
    app_commands.Choice(name="🟢 ว่างมาซื้อที !", value="ว่างมาซื้อที !"),
    app_commands.Choice(name="🟡 ยุ่งนิดหน่อยจ่ะ", value="ยุ่งนิดหน่อยจ่ะ"),
    app_commands.Choice(name="🔴 คิวล้น !", value="คิวล้น !"),
])
async def setstatus(interaction: discord.Interaction, สถานะ: str):
    global STATUS_STORED_MESSAGE_ID

    cfg = STATUS_CONFIG[สถานะ]
    channel = client.get_channel(STATUS_CHANNEL_ID)

    embed = discord.Embed(
        title=f"{cfg['emoji']}  {cfg['title']}",
        description=cfg["desc"],
        color=cfg["color"],
    )
    embed.set_author(name="INSIDEX", icon_url=interaction.guild.icon.url if interaction.guild.icon else discord.Embed.Empty)
    embed.set_footer(text=cfg["footer"])
    embed.timestamp = discord.utils.utcnow()

    if STATUS_STORED_MESSAGE_ID:
        try:
            old_msg = await channel.fetch_message(STATUS_STORED_MESSAGE_ID)
            await old_msg.edit(embed=embed)
            await interaction.response.send_message(f"✅ อัปเดตสถานะเป็น **{สถานะ}** แล้วครับ", ephemeral=True)
            return
        except discord.NotFound:
            STATUS_STORED_MESSAGE_ID = None

    new_msg = await channel.send(embed=embed)
    STATUS_STORED_MESSAGE_ID = new_msg.id
    await interaction.response.send_message(f"✅ โพสต์สถานะ **{สถานะ}** ในห้องแล้วครับ", ephemeral=True)


client.run(TOKEN)