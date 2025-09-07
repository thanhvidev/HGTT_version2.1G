import asyncio
import discord
from discord import File
from discord.ext import commands
from discord.utils import get
from easy_pil import Editor, load_image_async, Font
import sqlite3
import re
import random

wlc1 = "<a:hgtt_sky:1212268235693621248>"
wlchgtt = "<a:hgtt_a:1058137898228137994>"
wlcH = "<a:chu_h:1215227436954812416>"
wlcG = "<a:chu_g:1215227494408523827>"
wlcT = "<a:chu_t:1215227539858128956>"
traitim = "<:hgtt0:1092691329827487815>"
wel_1 = '<a:wel_1:1358235882657808527>'
wel_2 = '<:wel_2:1358235933442441276>'
wel_3 = '<a:wel_3:1358235939972841654>'
wel_4 = '<a:phaohoahong:1358024352318357574>'
wel_5 = '<:wel_5:1358235947547885738>'
button33 = '<a:button33:1412534340285370489>'
button58 = '<a:button58:1412534176888000622>'
hearts = '<:hearts:1414235687989018695>'
button45 = '<a:button45:1412534253044105376>'
pc = '<a:pc:1414238570041970802>'


class WelcomeView(discord.ui.View):
    def __init__(self, member: discord.Member, enable_buttons=True, timeout: float = 600.0):
        super().__init__(timeout=timeout)
        self.member = member  # Người mới vào server
        self.enable_buttons = enable_buttons
        self.message = None  # Sẽ được gán sau khi gửi message
        self.clicked_users = set()  # Lưu trữ các user đã nhấn nút
        self.counter = 0

    async def disable_all_items(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    async def disable_buttons(self, duration: int):  
        self.welcome.disabled = True
        await self.message.edit(view=self)  
        await asyncio.sleep(duration)  
        self.welcome.disabled = False
        await self.message.edit(view=self)  

    async def on_timeout(self) -> None:
        await self.disable_all_items()
        return await super().on_timeout()

    @discord.ui.button(label="chào mem mới", style=discord.ButtonStyle.green, emoji="<:chao_mem:1358233703578599474>", custom_id="welcome", disabled=False)
    async def welcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Kiểm tra nếu user đã nhấn rồi thì trả lời ephemeral và dừng
        if interaction.user.id in self.clicked_users:
            await interaction.response.send_message("Bạn đã nhấn rồi nè", ephemeral=True)
            return
        
        # Đánh dấu user đã nhấn
        self.clicked_users.add(interaction.user.id)

        list_loichao = [
            "{wel_1} Hé lu {member} nha, chúc cậu 1 ngày vui vẻ! ",
            "{wel_2} {user} chào mừng {member} đến với svl nha, pick role đi b iuu ",
            "{wel_3} {user} chào bạn mới, {member} có gì thắc mắc thì hỏi mình nha",
            "{wel_4} Xin chào {member}, cơm nước gì chưa ng đẹp ơi??",
            "{wel_5} {user} Hello, mừng bro {member} đến sv này nha"
        ]
        message_text = random.choice(list_loichao).format(
            wel_1=wel_1,
            wel_2=wel_2,
            wel_3=wel_3,
            wel_4=wel_4,
            wel_5=wel_5,
            user=interaction.user.mention,
            member=self.member.mention
        )
        await interaction.channel.send(message_text)
        
        # Tăng bộ đếm sau mỗi lần nhấn thành công
        self.counter += 1
        
        # Nếu đã nhấn 5 lần thì disable nút
        if self.counter >= 5:
            button.disabled = True
            if self.message:
                await self.message.edit(view=self)

class Welcome(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != 832579380634451969:
            return

        channel = self.client.get_channel(993153068378116127)
        # tạo embed
        embed = discord.Embed(
            description=(
                f"# ㅤㅤ{button33} 𝐇𝐆𝐓𝐓 𝐗𝐢𝐧 𝐂𝐡𝐚̀𝐨 {button33}\nㅤ\n"
                f"{button58} Để có một trải nghiệm tốt nhất tại sv, bạn vui lòng làm theo các bước sau để bật **hiện tất cả các kênh** nha\n\n"
                f"{pc} **Trên máy tính (PC)**\n"
                "- B1 :  Chuột phải vào tên sv 𝙝𝙖̣𝙩 𝙜𝙞𝙤̂́𝙣𝙜 𝙩𝙖̂𝙢 𝙩𝙝𝙖̂̀𝙣 ở trên cùng màn hình\n"
                "- B2 : Tick vào ô **hiện tất cả các kênh**\n\n\n"
                f"{hearts} **Trên điện thoại**\n"
                "- B1 : Bấm vào tên sv 𝙝𝙖̣𝙩 𝙜𝙞𝙤̂́𝙣𝙜 𝙩𝙖̂𝙢 𝙩𝙝𝙖̂̀𝙣 ở trên cùng màn hình\n"
                "- B2 : Kéo xuống và chọn mục **hiện tất cả các kênh**\n"
                "\n"
            ),
            color=discord.Color.from_rgb(245, 252, 255)
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1053799649938505889/1412703034764558356/image.png")

        # Tạo button link đến kênh 🗨️│nói-khùm-nói-điên
        channel = discord.utils.get(member.guild.text_channels, name="🗨️│nói-khùm-nói-điên")
        view = None
        if channel:
            button = discord.ui.Button(
                label=f"Bấm vào đây ",
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{member.guild.id}/{channel.id}"
            )
            view = discord.ui.View()
            view.add_item(button)

        # thử gửi DM
        try:
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            print(f"[!] Không thể nhắn tin cho {member} (chặn DM).")
            return

        await asyncio.sleep(1)
        # await channel.send(f"# **{traitim} Hé lô {member.mention} nha**")
        view = WelcomeView(member=member)  # Truyền member vào
        message = await channel.send(content= f"# **{traitim} Hé lô {member.mention} nha**", view=view)
        view.message = message
        await view.wait()


    # @commands.Cog.listener()
    # async def on_member_join(self, member):
    #     channel = self.client.get_channel(993153068378116127)
    #     # Lấy các vai trò cần thêm bằng id
    #     role_ids = [1003769660291960912, 1183603041987997756, 1083663296827232306, 1083599160055431268, 1083599309091635240, 1083599263675727912]
    #     roles = [member.guild.get_role(role_id) for role_id in role_ids]
    #     await member.add_roles(*roles)
    #     pos = sum(m.joined_at < member.joined_at for m in member.guild.members if  m.joined_at is not None)
    #     if pos == 1:
    #         te = "st"
    #     elif pos == 2:
    #         te = "nd"
    #     elif pos == 3:
    #         te = "rd"
    #     else:
    #         te = "th"
    #     background = Editor("welcome.png")
    #     if member.avatar:
    #         profile_image = await load_image_async(str(member.avatar.url))
    #     else:
    #         profile_image = "default_avatar.png"

    #     profile = Editor(profile_image).resize((500, 500)).circle_image()  # Thay đổi kích thước profile thành 400x400
    #     poppins = Font.poppins(size=(100), variant=('bold'))
    #     poppins_small = Font.poppins(size=(80), variant=('bold'))

    #     # Tính toán vị trí cho paste profile
    #     background_image = background.image
    #     profile_image = profile.image

    #     background_size = background_image.size
    #     profile_size = profile_image.size

    #     profile_position = ((background_size[0] - profile_size[0]) // 2, 200)  # Nằm ở giữa ngang và cách trên một khoảng

    #     background.paste(profile, profile_position)
    #     background.ellipse(profile_position, 500, 500, outline="white", stroke_width=10)  # Sửa kích thước ellipse tương ứng

    #     text_position = (background_size[0] // 2, profile_position[1] + profile_size[1] + 20)  # Cách dưới profile một khoảng
    #     text_above = (background_size[0] // 2, profile_position[1] - 120) 

    #     background.text(text_above, f"WELCOME", color="#FFA5E7", font=poppins, align="center")
    #     background.text((text_position[0], text_position[1] + 20), f"{member.name}", color="white", font=poppins_small, align="center")
    #     background.text((text_position[0], text_position[1] + 120), f"♡ {pos}{te} ♡", color="#FF9966", font=poppins_small, align="center")

    #     file = File(fp=background.image_bytes, filename="welcome.png")

    #     await channel.send(f"**{wlc1} Ú oà, {member.mention} đã bị bắt cóc đến {wlcH}{wlcG}{wlcT}{wlcT}**\nㅤ\n**{wlc1} 1 là pick roles 2 là iu tao <#1024754536566505513>\nㅤ**",file=file)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Kiểm tra nếu không phải máy chủ với id 832579380634451969 thì thoát
        if member.guild.id != 832579380634451969:
            return

        user_id = member.id
        conn = sqlite3.connect("economy.db")
        cursor = conn.cursor()

        cursor.execute("SELECT marry FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        if result is None:
            conn.close()
            return
        
        marry_info = result[0]
        
        if marry_info.strip() != "":
            pattern = r"<@(\d+)>\s+đã kết hôn với\s+<@(\d+)>"
            match = re.search(pattern, marry_info)
            if match:
                id1 = int(match.group(1))
                id2 = int(match.group(2))
                # Xác định đối tác: nếu thành viên rời đi là id1 thì partner là id2, ngược lại thì partner là id1
                if user_id == id1:
                    partner_id = id2
                elif user_id == id2:
                    partner_id = id1
                else:
                    partner_id = None
            else:
                partner_id = None

            # Xoá người dùng rời khỏi bảng
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            
            # Nếu tìm được partner_id, cập nhật lại dữ liệu của đối tác
            if partner_id:
                cursor.execute("""
                    UPDATE users 
                    SET marry = '', love_marry = 0, setup_marry1 = '', setup_marry2 = ''
                    WHERE user_id = ?
                """, (partner_id,))
        else:
            # Nếu không có thông tin hôn nhân, chỉ cần xoá người dùng khỏi bảng
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        conn.commit()

        channel = self.client.get_channel(1020298594441494538)
        pos = sum(m.joined_at < member.joined_at for m in member.guild.members if  m.joined_at is not None)
        if pos == 1:
            te = "st"
        elif pos == 2:
            te = "nd"
        elif pos == 3:
            te = "rd"
        else:
            te = "th"
        background = Editor("welcome.png")
        if member.avatar:
            profile_image = await load_image_async(str(member.avatar.url))
        else:
            profile_image = "default_avatar.png"

        profile = Editor(profile_image).resize((500, 500)).circle_image()  # Thay đổi kích thước profile thành 400x400
        poppins = Font.poppins(size=(100), variant=('bold'))
        poppins_small = Font.poppins(size=(80), variant=('bold'))

        # Tính toán vị trí cho paste profile
        background_image = background.image
        profile_image = profile.image

        background_size = background_image.size
        profile_size = profile_image.size

        profile_position = ((background_size[0] - profile_size[0]) // 2, 200)  # Nằm ở giữa ngang và cách trên một khoảng

        background.paste(profile, profile_position)
        background.ellipse(profile_position, 500, 500, outline="white", stroke_width=10)  # Sửa kích thước ellipse tương ứng

        text_position = (background_size[0] // 2, profile_position[1] + profile_size[1] + 20)  # Cách dưới profile một khoảng
        text_above = (background_size[0] // 2, profile_position[1] - 120) 

        background.text(text_above, f"GOODBYE", color="#FFA5E7", font=poppins, align="center")
        background.text((text_position[0], text_position[1] + 20), f"{member.name}", color="white", font=poppins_small, align="center")
        background.text((text_position[0], text_position[1] + 120), f"{pos}{te}", color="#FF9966", font=poppins_small, align="center")

        file = File(fp=background.image_bytes, filename="welcome.png")

        await channel.send(f"**{wlc1} Bye bye, {member.mention} đã cúc khỏi server**",file=file)

async def setup(client):
    await client.add_cog(Welcome(client))