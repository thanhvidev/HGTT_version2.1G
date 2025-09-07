"""
Economy Cog - Multi-Guild Support Version
Fully optimized for multiple Discord servers with separate databases
"""

import asyncio
import time
import typing
import discord
import random
from datetime import datetime, timedelta
from discord.ui import View, Button
from discord.ext import commands, tasks

# Import database helpers
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_helpers import UserDatabase, GuildDatabase, TransactionDatabase, LeaderboardDatabase
from database_manager import db_manager
from Commands.Mod.list_emoji import list_emoji
import config
import logging

logger = logging.getLogger(__name__)

# Emoji constants
saocaunguyen = "<a:sao2:1193346135138508810>"
tickxanh = "<:hgtt_dung:1186838952544575538>"
tickdo = "<:hgtt_sai:1186839020974657657>"
cash = "<:cash:1191596352422019084>"
fishcoin = "<:fishcoin:1213027788672737300>"
tienhatgiong = "<:timcoin:1192458078294122526>"
caunguyen = "<a:emoji_pray:1367337789481422858>"
caunguyen2 = "<:luhuong:1271360787088146504>"
theguitien = "<:cash:1191596352422019084>"
vevang = "<:vevang:1192461054131847260>"
vekc = "<:vekc:1146756758665175040>"
bank = '<:bankhong_2025:1339490810768527420>'
dungset = '<a:dung1:1340173892681072743>'
saiset = '<a:sai1:1340173872535703562>'

def is_guild_owner_or_bot_owner():
    """Check if user is guild owner or bot owner"""
    async def predicate(ctx):
        return (ctx.author == ctx.guild.owner or 
                ctx.author.id in config.BOT_OWNER_IDS)
    return commands.check(predicate)

def is_allowed_channel_check():
    """Check if command is allowed in channel"""
    async def predicate(ctx):
        # Add your allowed channel IDs here
        blocked_channel_ids = [1147035278465310720, 1207593935359320084]
        return ctx.channel.id not in blocked_channel_ids
    return commands.check(predicate)

class Economy(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.confirm_threshold_choices = [3, 4, 5, 6, 7]
        self.work_cooldowns = {}
        self.pray_cooldowns = {}
        
        # Start background tasks
        self.auto_save_task.start()
        
        logger.info("Economy cog initialized with multi-guild support")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.auto_save_task.cancel()
    
    async def check_command_disabled(self, ctx):
        """Check if command is disabled in this channel"""
        guild_id = str(ctx.guild.id)
        command_name = ctx.command.name.lower()
        
        # Check if Toggle cog exists and has settings
        toggle_cog = self.client.get_cog('Toggle')
        if toggle_cog and hasattr(toggle_cog, 'toggles'):
            if guild_id in toggle_cog.toggles:
                if command_name in toggle_cog.toggles[guild_id]:
                    if ctx.channel.id in toggle_cog.toggles[guild_id][command_name]:
                        await ctx.send(f"Lệnh `{command_name}` đã bị tắt ở kênh này.")
                        return True
        return False
    
    @commands.command(aliases=["dangky", "dangki", "dk"], description="Đăng ký tài khoản")
    async def register(self, ctx):
        """Register a new account"""
        if await self.check_command_disabled(ctx):
            return
        
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Kiểm tra xem kênh có ID là 1147035278465310720 hay không
        if ctx.channel.id == 1147035278465310720:
            await ctx.send(f"Hãy dùng lệnh ở kênh khác!")
            return
        
        # Check if already registered
        if await UserDatabase.is_registered(guild_id, user_id):
            await ctx.send(f"{ctx.author.mention}, bạn đã đăng ký tài khoản rồi!")
            return
        
        # Register user with initial balance
        success = await UserDatabase.register_user(guild_id, user_id, 200000)
        
        if success:
            # Try to get custom emoji
            try:
                guild = self.client.get_guild(config.EMOJI_GUILD_ID)
                dk_emoji = await guild.fetch_emoji(1181400074127945799) if guild else "✅"
            except:
                dk_emoji = "✅"
            
            await ctx.send(
                f"{dk_emoji} **| {ctx.author.display_name} đăng kí tài khoản thành công, "
                f"bạn được tặng** __**200k**__ {tienhatgiong}"
            )
            
            # Log transaction
            await TransactionDatabase.log_transaction(
                guild_id, None, user_id, 200000, 
                "register", "Initial balance on registration"
            )
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi đăng ký. Vui lòng thử lại!")
    
    @commands.command(description="xem có bao nhiêu vé")
    async def cash(self, ctx, member: typing.Optional[discord.Member] = None):
        """Check account balance"""
        if await self.check_command_disabled(ctx):
            return
        
        # Kiểm tra xem kênh có ID là 1147035278465310720 hay không
        if ctx.channel.id == 1147035278465310720 or ctx.channel.id == 1207593935359320084:
            return None
        
        target = member or ctx.author
        guild_id = ctx.guild.id
        
        # Check if registered
        if not await UserDatabase.is_registered(guild_id, target.id):
            if target == ctx.author:
                await ctx.send(f"❌ **{ctx.author.display_name}**, bạn chưa đăng kí tài khoản. Bấm `zdk` để đăng kí")
            else:
                await ctx.send(f"❌ **{target.display_name}** chưa đăng kí tài khoản")
            return
        
        # Get user data
        user_data = await UserDatabase.get_user_data(
            guild_id, target.id,
            ['balance', 'num_gold_tickets', 'num_diamond_tickets', 'coin_kc', 'xu_hlw']
        )
        
        if user_data:
            balance = user_data.get('balance', 0)
            gold_tickets = user_data.get('num_gold_tickets', 0)
            diamond_tickets = user_data.get('num_diamond_tickets', 0)
            coin_kc = user_data.get('coin_kc', 0)
            xu_ev = user_data.get('xu_hlw', 0)
            
            # Create message similar to original
            if diamond_tickets == 0:
                await ctx.send(f"{list_emoji.card} **| {target.display_name}** **đang có** **{gold_tickets} {vevang}**, __**{balance:,}**__ {tienhatgiong} và __**{xu_ev}**__ {list_emoji.xu_event}")
            else:
                await ctx.send(f"{list_emoji.card} **| {target.display_name}** **đang có** **{gold_tickets} {vevang}** **{diamond_tickets} {vekc}**, __**{balance:,}**__ {tienhatgiong} và __**{xu_ev}**__ {list_emoji.xu_event}")
        else:
            return None
    
    @commands.command(description="gửi tiền cho mọi người")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def give(self, ctx, receiver: discord.User, amount: int):
        """Transfer money to another user"""
        if await self.check_command_disabled(ctx):
            return
        
        if ctx.channel.id == 1215331218124574740 or ctx.channel.id == 1215331281878130738:
            return None
        
        sender_id = ctx.author.id
        receiver_id = receiver.id
        guild_id = ctx.guild.id
        formatted_amount = "{:,}".format(amount)
        
        # Validation
        if receiver.bot:
            await ctx.send("Không gửi tiền cho bot.")
            return
        
        if sender_id == receiver_id:
            await ctx.send("Tự ở tự ăn hả???")
            return
        
        if amount <= 0:
            await ctx.send("Về học lại toán lớp 1 dùm.")
            return
        
        # Check registration
        if not await UserDatabase.is_registered(guild_id, sender_id) or not await UserDatabase.is_registered(guild_id, receiver_id):
            await ctx.send("bạn chưa đăng kí tài khoản. Bấm `zdk` để đăng kí")
            return
        
        # Check balance
        if not await UserDatabase.has_enough_balance(guild_id, sender_id, amount):
            await ctx.send("Làm gì còn đủ tiền mà gửi!")
            return
        
        # Create confirmation embed
        embed = discord.Embed(title="", description=f"", color=discord.Color.from_rgb(238, 130, 238))
        if ctx.author.avatar:
            avatar_url = ctx.author.avatar.url
        else:
            avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
        
        embed.set_author(name=f"Xác nhận chuyển tiền", icon_url=avatar_url)
        embed.add_field(name="", value=f"- **{ctx.author.mention} sẽ gửi {cash} {receiver.mention}:**", inline=False)
        embed.add_field(name="", value=f"``` {formatted_amount} pinkcoin```", inline=False)
        embed._timestamp = datetime.utcnow()
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction(tickxanh)
        await msg.add_reaction(tickdo)
        
        def check(reaction, user):
            return (user == ctx.author and 
                   reaction.message == msg and 
                   str(reaction.emoji) in [tickxanh, tickdo])
        
        try:
            reaction, _ = await self.client.wait_for('reaction_add', timeout=180.0, check=check)
        except asyncio.TimeoutError:
            embed.color = discord.Color.from_rgb(0, 0, 0)
            embed.description = "Hết thời gian. Giao dịch đã bị hủy bỏ."
            await msg.edit(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
            return
        
        if str(reaction.emoji) == tickxanh:
            # Perform transfer
            success = await UserDatabase.transfer_money(guild_id, sender_id, receiver_id, amount)
            
            if success:
                await msg.delete()  # Xoá tin nhắn gốc
                mgs5 = await ctx.send(f"　")
                await mgs5.edit(content=f"{bank} **{ctx.author.mention}** **đã gửi** __**{formatted_amount}**__ {tienhatgiong} **đến** **{receiver.mention}**.")
        else:
            embed.color = 0xff0000  # Màu đỏ
            embed.description = "Giao dịch đã bị hủy bỏ."
            await msg.edit(embed=embed)
            await asyncio.sleep(5)
            await msg.delete()
    
    @commands.command( description="Làm việc")
    @commands.cooldown(1, 300, commands.BucketType.user)
    @is_allowed_channel_check()
    async def work(self, ctx):
        """Work to earn money"""
        if await self.check_command_disabled(ctx):
            return
        
        if ctx.channel.id in (1273769291099144222, 993153068378116127):
            return
        
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Check registration
        if not await UserDatabase.is_registered(guild_id, user_id):
            await ctx.send("❌ Bạn chưa đăng kí tài khoản. Bấm `zdk` để đăng kí")
            return
        
        # Get user work data
        user_data = await UserDatabase.get_user_data(guild_id, user_id, ['work_so', 'work_time'])
        counter = user_data.get('work_so', 0) if user_data else 0
        threshold = user_data.get('work_time') if user_data else None
        
        # Initialize threshold if not set
        if threshold is None:
            threshold = random.choice(self.confirm_threshold_choices)
            await UserDatabase.update_user_field(guild_id, user_id, 'work_time', threshold)
        
        # Calculate earnings
        earnings = random.randint(1000, 5000)
        
        # Work messages
        work_messages = [
            "đi làm đi~ và được bo",
            "đi ăn xin và được",
            "đi bán vé số và kiếm được",
            "đi lụm ve chai và bán được",
            "đi chém thuê và được trả công",
            "ăn trộm tiền của",
            "ăn cắp tiền của mẹ được",
            "đi phụ hồ và được trả",
            "làm thuê cột bịch nước mắm được trả công",
            "làm bảo vệ và được trả công",
            "đi móc bóc kiếm được",
            "đi làm tay vịn và được khách bo",
        ]
        
        # Check if confirmation needed
        if counter + 1 > threshold:
            # Need confirmation
            confirmed = False
            view = View(timeout=30)
            button = Button(label="Xác nhận làm việc", style=discord.ButtonStyle.primary)
            
            async def confirm_callback(interaction: discord.Interaction):
                nonlocal confirmed
                if interaction.user.id != user_id:
                    return await interaction.response.send_message(
                        "Chỉ chủ lệnh mới xác nhận được.", ephemeral=True
                    )
                confirmed = True
                await interaction.response.defer()
                
                # Process work
                result = random.choice(work_messages)
                
                # Handle stealing/begging
                if result.startswith("đi ăn xin") or result.startswith("ăn trộm"):
                    victims = await GuildDatabase.get_users_with_balance_above(guild_id, 10000, user_id)
                    if victims:
                        victim_id = random.choice([v['user_id'] for v in victims])
                        await UserDatabase.add_balance(guild_id, user_id, earnings)
                        await UserDatabase.add_balance(guild_id, victim_id, -earnings)
                        embed = discord.Embed(color=discord.Color.green())
                        embed.description = (
                            f"**{tickxanh} {ctx.author.mention} {result} <@{victim_id}>** "
                            f"__**{earnings:,}**__ {tienhatgiong}"
                        )
                        await interaction.followup.send(embed=embed)
                else:
                    await UserDatabase.add_balance(guild_id, user_id, earnings)
                    embed = discord.Embed(color=discord.Color.green())
                    embed.description = (
                        f"**{tickxanh} {ctx.author.mention} {result}** "
                        f"__**{earnings:,}**__ {tienhatgiong}"
                    )
                    await interaction.followup.send(embed=embed)
                
                # Reset counter and threshold
                new_threshold = random.choice(self.confirm_threshold_choices)
                await UserDatabase.update_user_field(guild_id, user_id, 'work_so', 0)
                await UserDatabase.update_user_field(guild_id, user_id, 'work_time', new_threshold)
                
                # Log transaction
                await TransactionDatabase.log_transaction(
                    guild_id, None, user_id, earnings, "work", result
                )
                
                await interaction.message.delete()
                view.stop()
            
            button.callback = confirm_callback
            view.add_item(button)
            
            # Send prompt and wait
            prompt = await ctx.send(view=view)
            await view.wait()
            # If timeout without confirmation, delete prompt
            if not confirmed:
                await prompt.delete()
        
        else:
            # Auto work
            result = random.choice(work_messages)
            
            if result.startswith("đi ăn xin") or result.startswith("ăn trộm"):
                victims = await GuildDatabase.get_users_with_balance_above(guild_id, 10000, user_id)
                if victims:
                    victim_id = random.choice([v['user_id'] for v in victims])
                    await UserDatabase.add_balance(guild_id, user_id, earnings)
                    await UserDatabase.add_balance(guild_id, victim_id, -earnings)
            else:
                await UserDatabase.add_balance(guild_id, user_id, earnings)
            
            await UserDatabase.increment_field(guild_id, user_id, 'work_so', 1)
            
            await ctx.send(
                f"**{tickxanh} {ctx.author.mention} {result}** __**{earnings:,}**__ {tienhatgiong}"
            )
            
            # Log transaction
            await TransactionDatabase.log_transaction(
                guild_id, None, user_id, earnings, "work", result
            )
    
    @commands.command( description="Cầu nguyện")
    @commands.cooldown(1, 900, commands.BucketType.user)
    @is_allowed_channel_check()
    async def pray(self, ctx):
        """Pray command"""
        if await self.check_command_disabled(ctx):
            return
        
        if ctx.channel.id == 1273769291099144222:
            return
        
        user_id = ctx.author.id
        guild_id = ctx.guild.id
        
        # Check registration
        if not await UserDatabase.is_registered(guild_id, user_id):
            await ctx.send("❌ Bạn chưa đăng kí tài khoản. Bấm `zdk` để đăng kí")
            return
        
        # Get user pray data
        user_data = await UserDatabase.get_user_data(guild_id, user_id, ['pray', 'pray_so', 'pray_time'])
        pray_count = user_data.get('pray', 0) if user_data else 0
        counter = user_data.get('pray_so', 0) if user_data else 0
        threshold = user_data.get('pray_time') if user_data else None
        
        # Initialize threshold
        if threshold is None:
            threshold = random.choice(self.confirm_threshold_choices)
            await UserDatabase.update_user_field(guild_id, user_id, 'pray_time', threshold)
        
        # Check if confirmation needed
        if counter + 1 > threshold:
            # Need confirmation
            confirmed = False
            view = View(timeout=30)
            button = Button(label="Xác nhận cầu nguyện", style=discord.ButtonStyle.green)
            
            async def confirm_callback(interaction: discord.Interaction):
                nonlocal confirmed
                if interaction.user.id != user_id:
                    return await interaction.response.send_message(
                        "Chỉ người thực hiện lệnh mới có thể xác nhận.", ephemeral=True
                    )
                confirmed = True
                await interaction.response.defer()
                
                # Process pray
                await UserDatabase.increment_field(guild_id, user_id, 'pray', 1)
                await UserDatabase.update_user_field(guild_id, user_id, 'pray_so', 0)
                
                # Set new threshold
                new_threshold = random.choice(self.confirm_threshold_choices)
                await UserDatabase.update_user_field(guild_id, user_id, 'pray_time', new_threshold)
                
                # Get updated count
                new_count = pray_count + 1
                
                await interaction.followup.send(
                    f"{caunguyen} | **{ctx.author.display_name}** thành tâm sám hối thắp được __**{new_count}**__ nén nhang! {caunguyen2}"
                )
                
                await interaction.message.delete()
                view.stop()
            
            button.callback = confirm_callback
            view.add_item(button)
            
            prompt = await ctx.send(view=view)
            await view.wait()
            if not confirmed:
                await prompt.delete()
        
        else:
            # Auto pray
            await UserDatabase.increment_field(guild_id, user_id, 'pray', 1)
            await UserDatabase.increment_field(guild_id, user_id, 'pray_so', 1)
            
            new_count = pray_count + 1
            await ctx.send(
                f"{caunguyen} | **{ctx.author.display_name}** thành tâm sám hối thắp được __**{new_count}**__ nén nhang! {caunguyen2}"
            )
    
    @commands.command(aliases=["zsettien", "set"], description="set tiền cho người khác")
    @commands.cooldown(1, 2, commands.BucketType.user)
    @is_guild_owner_or_bot_owner()
    async def settien(self, ctx, amount: int, member: typing.Optional[discord.Member] = None):
        """Set money for a user (Admin only)"""
        guild_id = ctx.guild.id
        formatted_amount = "{:,}".format(amount)
        
        # Create confirmation embed
        if member is None:
            msg = await ctx.send(f"Bạn có chắc chắn muốn tặng **{formatted_amount}** {tienhatgiong} cho tất cả người dùng?")
        else:
            msg = await ctx.send(f"Bạn có chắc chắn muốn tặng **{formatted_amount}** {tienhatgiong} cho {member.display_name}?")
        
        await msg.add_reaction(dungset)
        await msg.add_reaction(saiset)
        
        def check(reaction, user):
            return (user == ctx.author and 
                   str(reaction.emoji) in [dungset, saiset] and 
                   reaction.message.id == msg.id)
        
        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == dungset:
                if member is None:
                    # Add to all users
                    success = await GuildDatabase.add_balance_to_all(guild_id, amount)
                    if success:
                        await msg.edit(content=f"**HGTT đã tặng** __**{formatted_amount}**__ {tienhatgiong} **cho tất cả người dùng**")
                    else:
                        await msg.edit(content="Có lỗi xảy ra!")
                else:
                    # Check if user is registered
                    if not await UserDatabase.is_registered(guild_id, member.id):
                        # Register them first
                        await UserDatabase.register_user(guild_id, member.id, 0)
                    
                    # Add balance
                    await UserDatabase.add_balance(guild_id, member.id, amount)
                    await msg.edit(content=f"**HGTT đã tặng** __**{formatted_amount}**__ {tienhatgiong} **cho {member.display_name}**")
            else:
                await msg.edit(content="Lệnh đã bị hủy.")
        
        except asyncio.TimeoutError:
            await msg.edit(content="Bạn không phản ứng kịp thời, lệnh đã bị hủy.")
    
    @commands.command(aliases=["rstien"], description="reset tiền cho người khác")
    @commands.cooldown(1, 2, commands.BucketType.user)
    @is_guild_owner_or_bot_owner()
    async def resettien(self, ctx, member: typing.Optional[discord.Member] = None):
        """Reset money for users (Admin only)"""
        guild_id = ctx.guild.id
        
        if member is None:
            # Gửi yêu cầu xác nhận cho toàn bộ người dùng
            msg = await ctx.send("Bạn có chắc chắn muốn reset tiền cho tất cả người dùng?")
        else:
            # Lấy số tiền hiện tại của người dùng
            current_balance = await UserDatabase.get_balance(guild_id, member.id)
            msg = await ctx.send(
                f"Bạn có chắc chắn muốn reset tiền cho {member.display_name}? "
                f"Số tiền hiện tại của họ là: {current_balance:,} VNĐ."
            )
        
        # Đặt emoji phản ứng cho người dùng lựa chọn
        await msg.add_reaction(dungset)
        await msg.add_reaction(saiset)
        
        # Xác nhận người dùng phản ứng
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in [dungset, saiset] and reaction.message.id == msg.id
        
        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=30.0, check=check)
            if str(reaction.emoji) == dungset:
                if member is None:
                    success = await GuildDatabase.reset_all_balances(guild_id)
                    if success:
                        await msg.edit(content="Đã reset tiền cho tất cả người dùng.")
                    else:
                        await msg.edit(content="Có lỗi xảy ra!")
                else:
                    await UserDatabase.set_balance(guild_id, member.id, 0)
                    await msg.edit(content=f"Đã reset tiền cho {member.display_name}.")
            else:
                await msg.edit(content="Lệnh đã bị hủy.")
        except asyncio.TimeoutError:
            await msg.edit(content="Bạn không phản ứng kịp thời, lệnh đã bị hủy.")
        else:
            await ctx.send("Người dùng chưa đăng kí tài khoản.")

    @commands.command(aliases=["nhapdl"], description="cập nhật database")
    @commands.cooldown(1, 2, commands.BucketType.user)
    @is_guild_owner_or_bot_owner()
    async def nhapdulieu(self, ctx):
        try:
            # Force save data (this would be handled by database manager)
            await ctx.send("Cập nhật database thành công!")
        except Exception as e:
            await ctx.send(f"Có lỗi xảy ra: {e}")
    
    @tasks.loop(minutes=30)
    async def auto_save_task(self):
        """Auto save task to ensure data persistence"""
        try:
            # Force write any pending changes
            logger.info("Running auto-save task...")
            # The database manager handles this automatically with WAL mode
        except Exception as e:
            logger.error(f"Auto-save error: {e}")
    
    @auto_save_task.before_loop
    async def before_auto_save(self):
        """Wait for bot to be ready before starting auto-save"""
        await self.client.wait_until_ready()
    
    # Error handlers
    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            mins, secs = divmod(int(error.retry_after), 60)
            msg = await ctx.send(
                f"⏰ | Vui lòng đợi {mins}m{secs}s trước khi làm việc tiếp."
            )
            await asyncio.sleep(2)
            await msg.delete()
            await ctx.message.delete()
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            logger.error(f"Work command error: {error}")
    
    @pray.error
    async def pray_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            mins, secs = divmod(int(error.retry_after), 60)
            msg = await ctx.send(f"⏰ | Vui lòng đợi {mins}m{secs}s trước khi cầu nguyện tiếp.")
            await asyncio.sleep(2)
            await msg.delete()
            await ctx.message.delete()
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            logger.error(f"Pray command error: {error}")
    
    @give.error
    async def give_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Vui lòng đợi **{error.retry_after:.1f}s** trước khi chuyển tiền tiếp!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Sử dụng: `zgive @người_nhận số_tiền`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Số tiền không hợp lệ!")
        else:
            logger.error(f"Give command error: {error}")


async def setup(client):
    await client.add_cog(Economy(client))
    logger.info("Economy cog loaded")