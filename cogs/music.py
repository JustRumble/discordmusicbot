import wavelink
from discord.ext import commands
import discord
import datetime
import math


def getactualsongtime(player: wavelink.Player) -> datetime.timedelta:
    tiempo_ahora_s = datetime.timedelta(milliseconds=float(player.position))
    tiempo_ahora_e = datetime.timedelta(seconds=tiempo_ahora_s.seconds)
    return tiempo_ahora_e


def gettotalsongtime(player: wavelink.Player) -> datetime.timedelta:
    tiempo_total_s = datetime.timedelta(milliseconds=float(player.current.length))
    tiempo_total_e = datetime.timedelta(seconds=tiempo_total_s.seconds)
    return tiempo_total_e


def user_in_bot_vc(interaction: discord.Interaction):
    if not interaction.user.voice.channel:
        return False
    if not interaction.guild.voice_client:
        return False
    if interaction.guild.voice_client.channel != interaction.user.voice.channel:
        return False
    return True


class MediaButtons(discord.ui.View):
    def __init__(
        self,
        timeout: float = None,
        embed: discord.Embed = None,
        player: wavelink.Player = None,
    ):
        self.embed = embed
        self.player = player
        super().__init__(timeout=timeout)

    def get_timeout_view(self) -> float:
        return float(
            gettotalsongtime(self.player).seconds
            - getactualsongtime(self.player).seconds
        )

    async def on_timeout(self) -> None:
        await self.disable_btns()
        await self.message.edit(view=self)

    async def disable_btns(self) -> None:
        for btn in self.children:
            btn.disabled = True

    @discord.ui.button(
        label="",
        emoji="<:stop:1200837670151127180>",
        style=discord.ButtonStyle.danger,
    )
    async def stop_song(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        node = wavelink.Pool.get_node()
        player = wavelink.Node.get_player(node, interaction.guild.id)
        if not user_in_bot_vc(interaction):
            return await interaction.response.send_message(
                "Seems you arent in my voice channel or im not playing music",
                ephemeral=True,
            )
        if player.playing:
            await self.disable_btns()
            await interaction.response.edit_message(view=self)
            player.queue.clear()
            await player.disconnect()

    @discord.ui.button(
        label="",
        emoji="<:pausa:1200841413710065704>",
        style=discord.ButtonStyle.blurple,
    )
    async def play_pause(
        self, interaction: discord.Interaction, button: discord.ui.button
    ):
        node = wavelink.Pool.get_node()
        player = wavelink.Node.get_player(node, interaction.guild.id)
        if not user_in_bot_vc(interaction):
            return await interaction.response.send_message(
                "Seems you arent in my voice channel or im not playing music",
                ephemeral=True,
            )

        if player.playing:
            if not player.paused:
                # pausado
                await player.pause(True)
                button.style = discord.ButtonStyle.green
                button.emoji = "<:play:1200837254990549072>"
                self.timeout = None
                self.embed.color = discord.Color.yellow()
                await interaction.response.edit_message(view=self, embed=self.embed)

            else:
                # NO pausado
                await player.pause(False)
                button.style = discord.ButtonStyle.blurple
                button.emoji = "<:pausa:1200841413710065704>"
                self.timeout = self.get_timeout_view()

                self.embed.color = discord.Color.green()
                await interaction.response.edit_message(view=self, embed=self.embed)
        else:
            return await interaction.response.send_message(
                "Im not playing music", ephemeral=True
            )


class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Node {payload.node.identifier} is ready!")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return
        embed = discord.Embed(
            title="Now playing",
            color=discord.Color.blue(),
        )
        mediabuttons = MediaButtons(timeout=None,embed=embed,player=player)
        mediabuttons.timeout = mediabuttons.get_timeout_view()
        mediabuttons.embed.description =f"[{player.current.title}]({player.current.uri}) `{gettotalsongtime(mediabuttons.player)}` \nAlbum: [{player.current.album.name}]({player.current.album.url})"
        if player.current.artwork:
            embed.set_thumbnail(url=player.current.artwork)
        if hasattr(player, "home"):
            mediabuttons.message = await player.home.send(
                embed=embed, view=mediabuttons
            )
            player.message = mediabuttons.message

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        if payload.player:
            print(payload.reason)
            if len(payload.player.queue) > 0:
                await payload.player.play(await payload.player.queue.get_wait())

    @commands.Cog.listener()
    async def on_wavelink_track_exception(
        self, payload: wavelink.TrackExceptionEventPayload
    ):
        player = payload.player
        if player is not None and hasattr(player, "home"):
            await player.home.send(
                f"Error: `{type(payload.exception).__name__}`"
            )
            await player.disconnect()

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        if hasattr(player, "home"):
            await player.home.send("Queue is empty.")
        await player.disconnect()

    @commands.hybrid_command(name="play", aliases=["p"])
    async def playmusic(self, ctx: commands.Context, *, query: str):
        if (
            query.__contains__("https://www.youtube.com/watch")
            or query.__contains__("https://youtu.be/")
            or query.__contains__("https://music.youtube.com/watch")
        ):
            return await ctx.reply(
                "I cant do that", mention_author=False
            )
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True)
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except AttributeError:
            return await ctx.send("You arent in a voice channel lol")
        except discord.errors.ClientException:
            player: wavelink.Player = ctx.voice_client
        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            return await ctx.send(
                f"The player start on the channel {player.home.mention}"
            )
        result: wavelink.Search = await wavelink.Playable.search(
            query, source="spsearch:"
        )
        if isinstance(result, wavelink.Playlist):
            added = await player.queue.put_wait(result)
            embed = discord.Embed(
                title="Playlist added to queue",
                description=f"{result.name} - {added} songs",
                color=discord.Color.blue(),
            )
            if result.artwork:
                embed.set_thumbnail(url=result.artwork)
        else:
            track: wavelink.Playable = result[0]
            await player.queue.put_wait(track)
            embed = discord.Embed(
                title="Song added to queue",
                description=f"[{track.title}]({track.uri})",
                color=discord.Color.blue(),
            )
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
        await ctx.reply(embed=embed, mention_author=False)

        if not player.playing:
            await player.play(player.queue.get())

    @commands.hybrid_command(name="nowplaying", aliases=["np"])
    async def now_playing(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if player is not None:
            embed = discord.Embed(
                title="🎵 Now playing",
                description=f"💿 [{player.current.author}]({player.current.artist.url}) -  [{player.current.title}]({player.current.uri})",
                color=discord.Color.blue(),
            )
            if player.current.artwork:
                embed.set_thumbnail(url=player.current.artwork)
            await ctx.reply(embed=embed, ephemeral=True, mention_author=False)
        else:
            return await ctx.reply(
                "Im not playing music", ephemeral=True, mention_author=False
            )

    @commands.hybrid_command(name="queue", aliases=["q"])
    async def queue_cmd(self, ctx: commands.Context, pag: int = 1):
        player: wavelink.Player = ctx.voice_client
        if player is None:
            return await ctx.reply(
                "Im not playing music", ephemeral=True, mention_author=False
            )
        songs_per_page = 10
        total_pages = math.ceil(len(player.queue) / songs_per_page)
        if total_pages == 0:
            total_pages = 1
        if pag <= 0 or pag > total_pages:
            return await ctx.reply(
                "That page number does not exist.", mention_author=False, ephemeral=True
            )

        def parse_track_len(ms: int) -> datetime.timedelta:
            tiempo_total_s = datetime.timedelta(milliseconds=float(ms))
            tiempo_total_e = datetime.timedelta(seconds=tiempo_total_s.seconds)
            return tiempo_total_e

        def getTracksEmbed():
            start = (pag - 1) * songs_per_page
            end = start + songs_per_page
            embed_tracks = discord.Embed(
                title=f"🎵 Queue 🎵 ({pag} / {total_pages})",
                description=f"**💿 Now playing:** [{player.current.author}]({player.current.artist.url}) - [{player.current.title}]({player.current.uri})\n\n",
                color=discord.Color.blurple(),
            )

            for i, track in enumerate(list(player.queue)[start:end], start=start):
                embed_tracks.description += f"**{i+1}.** [{track.author}]({track.artist.url}) - [{track.title}]({track.uri}) `{parse_track_len(track.length)}` \n"
            return embed_tracks

        async def sendTracksEmbed(embed_tracks: discord.Embed):
            embed_tracks = getTracksEmbed()
            if len(player.queue) < 1:
                embed_tracks.description += (
                    "`Queue is empty`\n**Add some songs!**"
                )
                embed_tracks.title = "🎵 Queue 🎵 (1 / 1)"
                message = await ctx.send(embed=embed_tracks)
            else:
                message = await ctx.send(embed=embed_tracks)

            return message

        await sendTracksEmbed(getTracksEmbed())

    @commands.hybrid_command(name="replay", aliases=["rp", "repeat"])
    async def replay_cmd(self, ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if player is not None:

            await player.play(player.current)
            if hasattr(player, "message"):
                mediabuttons = MediaButtons(timeout=None)
                await mediabuttons.disable_btns()
                await player.message.edit(view=mediabuttons)
            await ctx.reply(
                "Replaying song...",
                ephemeral=True,
                mention_author=False,
            )
        else:
            return await ctx.reply(
                "Im not playing music", ephemeral=True, mention_author=False
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Musica(bot))
