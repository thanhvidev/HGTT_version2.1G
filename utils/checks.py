from discord.ext import commands
import config

def is_bot_owner():
    """Check nếu user là owner (lấy từ BOT_OWNER_IDS trong config)"""
    async def predicate(ctx):
        return ctx.author.id in config.BOT_OWNER_IDS
    return commands.check(predicate)

def is_admin():
    """Check nếu user có quyền Administrator"""
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

def is_mod():
    async def predicate(ctx):
        mod_roles = config.MOD_ROLE_IDS.get(str(ctx.guild.id), [])
        # print("MOD_ROLE_IDS:", mod_roles)
        # print("User roles:", [role.id for role in ctx.author.roles])
        if not mod_roles:
            return False
        return any(role.id in mod_roles for role in ctx.author.roles)
    return commands.check(predicate)


