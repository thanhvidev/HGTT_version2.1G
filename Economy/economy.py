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
                f"bạn được tặng** __**200,000**__ {tienhatgiong}"
            )
            
            # Log transaction
            await TransactionDatabase.log_transaction(
                guild_id, None, user_id, 200000, 
                "register", "Initial balance on registration"
            )
        else:
            await ctx.send("❌ Đã xảy ra lỗi khi đăng ký. Vui lòng thử lại!")
    
    @commands.command(description="Xem số dư tài khoản")
    async def cash(self, ctx, member: typing.Optional[discord.Member] = None):
        """Check account balance"""
        if await self.check_command_disabled(ctx):
            return
        
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
            
            # Create embed
            embed = discord.Embed(
                title=f"💰 Tài Khoản của {target.display_name}",
                color=discord.Color.gold()
            )
            embed.add_field(name="💵 Số dư", value=f"**{balance:,}** {tienhatgiong}", inline=False)
            
            if gold_tickets > 0:
                embed.add_field(name="🎫 Vé vàng", value=f"**{gold_tickets}** {vevang}", inline=True)
            if diamond_tickets > 0:
                embed.add_field(name="💎 Vé kim cương", value=f"**{diamond_tickets}** {vekc}", inline=True)
            if xu_ev > 0:
                embed.add_field(name="🎪 Xu event", value=f"**{xu_ev}** {list_emoji.xu_event if hasattr(list_emoji, 'xu_event') else '🎪'}", inline=True)
            
            # Add user rank
            rank = await LeaderboardDatabase.get_user_rank(guild_id, target.id)
            if rank:
                embed.set_footer(text=f"Xếp hạng: #{rank} trong server")
            
            await ctx.send(embed=embed)
    
    @commands.command(aliases=["chuyen", "transfer"], description="Chuyển tiền cho người khác")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def give(self, ctx, receiver: discord.User, amount: int):
        """Transfer money to another user"""
        if await self.check_command_disabled(ctx):
            return
        
        sender_id = ctx.author.id
        receiver_id = receiver.id
        guild_id = ctx.guild.id
        
        # Validation
        if receiver.bot:
            await ctx.send("❌ Không thể gửi tiền cho bot.")
            return
        
        if sender_id == receiver_id:
            await ctx.send("❌ Bạn không thể gửi tiền cho chính mình!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Số tiền phải lớn hơn 0!")
            return
        
        # Check registration
        if not await UserDatabase.is_registered(guild_id, sender_id):
            await ctx.send("❌ Bạn chưa đăng kí tài khoản. Bấm `zdk` để đăng kí")
            return
        
        if not await UserDatabase.is_registered(guild_id, receiver_id):
            await ctx.send(f"❌ {receiver.mention} chưa đăng kí tài khoản")
            return
        
        # Check balance
        if not await UserDatabase.has_enough_balance(guild_id, sender_id, amount):
            await ctx.send("❌ Bạn không có đủ tiền để gửi!")
            return
        
        # Create confirmation embed
        embed = discord.Embed(
            title="💸 Xác nhận chuyển tiền",
            description=f"**{ctx.author.mention}** sẽ gửi **{amount:,}** {tienhatgiong} cho **{receiver.mention}**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="React để xác nhận hoặc hủy")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction(tickxanh)
        await msg.add_reaction(tickdo)
        
        def check(reaction, user):
            return (user == ctx.author and 
                   reaction.message == msg and 
                   str(reaction.emoji) in [tickxanh, tickdo])
        
        try:
            reaction, _ = await self.client.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            embed.color = discord.Color.dark_gray()
            embed.description = "⏱️ Hết thời gian. Giao dịch đã bị hủy."
            await msg.edit(embed=embed)
            await msg.clear_reactions()
            return
        
        if str(reaction.emoji) == tickxanh:
            # Perform transfer
            success = await UserDatabase.transfer_money(guild_id, sender_id, receiver_id, amount)
            
            if success:
                embed.color = discord.Color.green()
                embed.description = f"{bank} **{ctx.author.mention}** đã gửi thành công **{amount:,}** {tienhatgiong} cho **{receiver.mention}**"
                await msg.edit(embed=embed)
                
                # Log transaction (already logged in transfer_money)
            else:
                embed.color = discord.Color.red()
                embed.description = "❌ Giao dịch thất bại. Vui lòng thử lại."
                await msg.edit(embed=embed)
        else:
            embed.color = discord.Color.red()
            embed.description = "❌ Giao dịch đã bị hủy."
            await msg.edit(embed=embed)
        
        await msg.clear_reactions()
    
    @commands.command(aliases=["lam", "lamviec"], description="Làm việc kiếm tiền")
    @commands.cooldown(1, 300, commands.BucketType.user)
    @is_allowed_channel_check()
    async def work(self, ctx):
        """Work to earn money"""
        if await self.check_command_disabled(ctx):
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
            "đi làm và được trả",
            "đi bán vé số và kiếm được",
            "đi lụm ve chai và bán được",
            "đi chém thuê và được trả công",
            "đi phụ hồ và được trả",
            "làm bảo vệ và được trả công",
            "đi ship hàng và kiếm được",
            "làm freelancer và nhận được",
            "đi câu cá và bán được",
            "làm thợ sửa xe và được trả"
        ]
        
        # Check if confirmation needed
        if counter + 1 > threshold:
            # Need confirmation
            view = View(timeout=30)
            button = Button(label="Xác nhận làm việc", style=discord.ButtonStyle.primary)
            
            async def confirm_callback(interaction: discord.Interaction):
                if interaction.user.id != user_id:
                    await interaction.response.send_message("❌ Chỉ người dùng lệnh mới có thể xác nhận!", ephemeral=True)
                    return
                
                await interaction.response.defer()
                
                # Process work
                work_msg = random.choice(work_messages)
                await UserDatabase.add_balance(guild_id, user_id, earnings)
                
                # Reset counter and threshold
                new_threshold = random.choice(self.confirm_threshold_choices)
                await UserDatabase.update_user_field(guild_id, user_id, 'work_so', 0)
                await UserDatabase.update_user_field(guild_id, user_id, 'work_time', new_threshold)
                
                # Send result
                embed = discord.Embed(
                    description=f"✅ **{ctx.author.mention}** {work_msg} **{earnings:,}** {tienhatgiong}",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)
                
                # Log transaction
                await TransactionDatabase.log_transaction(
                    guild_id, None, user_id, earnings, "work", work_msg
                )
                
                await interaction.message.delete()
                view.stop()
            
            button.callback = confirm_callback
            view.add_item(button)
            
            await ctx.send(
                f"🔒 **Xác nhận bảo mật**: Vui lòng nhấn nút để xác nhận làm việc",
                view=view
            )
        else:
            # Auto work
            work_msg = random.choice(work_messages)
            await UserDatabase.add_balance(guild_id, user_id, earnings)
            await UserDatabase.increment_field(guild_id, user_id, 'work_so', 1)
            
            embed = discord.Embed(
                description=f"✅ **{ctx.author.mention}** {work_msg} **{earnings:,}** {tienhatgiong}",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            # Log transaction
            await TransactionDatabase.log_transaction(
                guild_id, None, user_id, earnings, "work", work_msg
            )
    
    @commands.command(aliases=["caunguyen"], description="Cầu nguyện")
    @commands.cooldown(1, 900, commands.BucketType.user)
    @is_allowed_channel_check()
    async def pray(self, ctx):
        """Pray command"""
        if await self.check_command_disabled(ctx):
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
            view = View(timeout=30)
            button = Button(label="Xác nhận cầu nguyện", style=discord.ButtonStyle.green)
            
            async def confirm_callback(interaction: discord.Interaction):
                if interaction.user.id != user_id:
                    await interaction.response.send_message("❌ Chỉ người dùng lệnh mới có thể xác nhận!", ephemeral=True)
                    return
                
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
                    f"{caunguyen} **{ctx.author.display_name}** thành tâm sám hối thắp được __**{new_count}**__ nén nhang! {caunguyen2}"
                )
                
                await interaction.message.delete()
                view.stop()
            
            button.callback = confirm_callback
            view.add_item(button)
            
            await ctx.send(
                f"🔒 **Xác nhận bảo mật**: Vui lòng nhấn nút để xác nhận cầu nguyện",
                view=view
            )
        else:
            # Auto pray
            await UserDatabase.increment_field(guild_id, user_id, 'pray', 1)
            await UserDatabase.increment_field(guild_id, user_id, 'pray_so', 1)
            
            new_count = pray_count + 1
            await ctx.send(
                f"{caunguyen} **{ctx.author.display_name}** thành tâm sám hối thắp được __**{new_count}**__ nén nhang! {caunguyen2}"
            )
    
    @commands.command(aliases=["LB", "leaderboard"], description="Xem bảng xếp hạng")
    async def bxh(self, ctx, category: str = "balance"):
        """View leaderboard"""
        if await self.check_command_disabled(ctx):
            return
        
        guild_id = ctx.guild.id
        
        # Determine leaderboard type
        category = category.lower()
        if category in ["tien", "money", "balance", "cash"]:
            field = "balance"
            title = "💰 Top Người Giàu Nhất"
            emoji = tienhatgiong
        elif category in ["pray", "caunguyen"]:
            field = "pray"
            title = "🙏 Top Cầu Nguyện Nhiều Nhất"
            emoji = caunguyen2
        elif category in ["love", "tinh", "marry"]:
            field = "love_marry"
            title = "❤️ Top Tình Yêu"
            emoji = "❤️"
        else:
            field = "balance"
            title = "💰 Top Người Giàu Nhất"
            emoji = tienhatgiong
        
        # Get leaderboard
        leaderboard = await LeaderboardDatabase.get_field_leaderboard(guild_id, field, 10)
        
        if not leaderboard:
            await ctx.send("📊 Chưa có dữ liệu bảng xếp hạng!")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"{title} - {ctx.guild.name}",
            color=discord.Color.gold()
        )
        
        # Build leaderboard text
        description = ""
        for i, entry in enumerate(leaderboard, 1):
            user_id = entry['user_id']
            value = entry[field]
            
            # Get user
            try:
                user = await self.client.fetch_user(user_id)
                username = user.display_name
            except:
                username = f"User {user_id}"
            
            # Medal for top 3
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            
            description += f"{medal} **{i}.** {username}: **{value:,}** {emoji}\n"
        
        embed.description = description
        embed.set_footer(text=f"Dùng {ctx.prefix}bxh [tien/pray/love] để xem các BXH khác")
        
        await ctx.send(embed=embed)
    
    @commands.command(aliases=["settien", "set"], description="Set tiền cho người dùng")
    @commands.cooldown(1, 2, commands.BucketType.user)
    @is_guild_owner_or_bot_owner()
    async def setmoney(self, ctx, amount: int, member: typing.Optional[discord.Member] = None):
        """Set money for a user (Admin only)"""
        guild_id = ctx.guild.id
        
        # Create confirmation embed
        if member is None:
            embed = discord.Embed(
                title="⚠️ Xác nhận",
                description=f"Bạn có chắc muốn tặng **{amount:,}** {tienhatgiong} cho **TẤT CẢ** người dùng?",
                color=discord.Color.yellow()
            )
        else:
            embed = discord.Embed(
                title="⚠️ Xác nhận",
                description=f"Bạn có chắc muốn tặng **{amount:,}** {tienhatgiong} cho **{member.display_name}**?",
                color=discord.Color.yellow()
            )
        
        msg = await ctx.send(embed=embed)
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
                        embed.color = discord.Color.green()
                        embed.description = f"✅ Đã tặng **{amount:,}** {tienhatgiong} cho tất cả người dùng!"
                    else:
                        embed.color = discord.Color.red()
                        embed.description = "❌ Có lỗi xảy ra!"
                else:
                    # Check if user is registered
                    if not await UserDatabase.is_registered(guild_id, member.id):
                        # Register them first
                        await UserDatabase.register_user(guild_id, member.id, 0)
                    
                    # Add balance
                    await UserDatabase.add_balance(guild_id, member.id, amount)
                    embed.color = discord.Color.green()
                    embed.description = f"✅ Đã tặng **{amount:,}** {tienhatgiong} cho **{member.display_name}**!"
                
                await msg.edit(embed=embed)
            else:
                embed.color = discord.Color.red()
                embed.description = "❌ Lệnh đã bị hủy."
                await msg.edit(embed=embed)
        
        except asyncio.TimeoutError:
            embed.color = discord.Color.dark_gray()
            embed.description = "⏱️ Hết thời gian chờ. Lệnh đã bị hủy."
            await msg.edit(embed=embed)
        
        await msg.clear_reactions()
    
    @commands.command(aliases=["resettien", "resetmoney"], description="Reset tiền")
    @commands.cooldown(1, 2, commands.BucketType.user)
    @is_guild_owner_or_bot_owner()
    async def reset_money(self, ctx, member: typing.Optional[discord.Member] = None):
        """Reset money for users (Admin only)"""
        guild_id = ctx.guild.id
        
        # Create confirmation embed
        if member is None:
            embed = discord.Embed(
                title="⚠️ Cảnh báo",
                description="Bạn có chắc muốn **RESET** tiền của **TẤT CẢ** người dùng về 0?",
                color=discord.Color.red()
            )
        else:
            current_balance = await UserDatabase.get_balance(guild_id, member.id)
            embed = discord.Embed(
                title="⚠️ Cảnh báo",
                description=f"Bạn có chắc muốn **RESET** tiền của **{member.display_name}** về 0?\nSố dư hiện tại: **{current_balance:,}** {tienhatgiong}",
                color=discord.Color.red()
            )
        
        msg = await ctx.send(embed=embed)
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
                    # Reset all
                    success = await GuildDatabase.reset_all_balances(guild_id)
                    if success:
                        embed.color = discord.Color.green()
                        embed.description = "✅ Đã reset tiền của tất cả người dùng!"
                    else:
                        embed.color = discord.Color.red()
                        embed.description = "❌ Có lỗi xảy ra!"
                else:
                    # Reset specific user
                    await UserDatabase.set_balance(guild_id, member.id, 0)
                    embed.color = discord.Color.green()
                    embed.description = f"✅ Đã reset tiền của **{member.display_name}**!"
                
                await msg.edit(embed=embed)
            else:
                embed.color = discord.Color.red()
                embed.description = "❌ Lệnh đã bị hủy."
                await msg.edit(embed=embed)
        
        except asyncio.TimeoutError:
            embed.color = discord.Color.dark_gray()
            embed.description = "⏱️ Hết thời gian chờ. Lệnh đã bị hủy."
            await msg.edit(embed=embed)
        
        await msg.clear_reactions()
    
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
            await ctx.send(f"⏱️ Vui lòng đợi **{mins}m {secs}s** trước khi làm việc tiếp!")
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            logger.error(f"Work command error: {error}")
    
    @pray.error
    async def pray_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            mins, secs = divmod(int(error.retry_after), 60)
            await ctx.send(f"⏱️ Vui lòng đợi **{mins}m {secs}s** trước khi cầu nguyện tiếp!")
        elif isinstance(error, commands.CheckFailure):
            pass
        else:
            logger.error(f"Pray command error: {error}")
    
    @give.error
    async def give_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱️ Vui lòng đợi **{error.retry_after:.1f}s** trước khi chuyển tiền tiếp!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Sử dụng: `zgive @người_nhận số_tiền`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Số tiền không hợp lệ!")
        else:
            logger.error(f"Give command error: {error}")

async def setup(client):
    await client.add_cog(Economy(client))