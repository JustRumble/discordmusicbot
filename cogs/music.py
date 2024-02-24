import wavelink
from discord.ext import commands
import discord
import datetime


class MusicCommands(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print("El nodo {0} está listo!".format(payload.node.identifier))

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return

        def getactualsongtime() -> datetime.timedelta:
            tiempo_ahora_s = datetime.timedelta(milliseconds=float(player.position))
            tiempo_ahora_e = datetime.timedelta(seconds=tiempo_ahora_s.seconds)
            return tiempo_ahora_e

        def gettotalsongtime() -> datetime.timedelta:
            tiempo_total_s = datetime.timedelta(
                milliseconds=float(player.current.length)
            )
            tiempo_total_e = datetime.timedelta(seconds=tiempo_total_s.seconds)
            return tiempo_total_e

        def get_timeout_view() -> float:
            return float(gettotalsongtime().seconds - getactualsongtime().seconds)

        def user_in_bot_vc(interaction: discord.Interaction):
            if not interaction.user.voice.channel:
                return False
            if not interaction.guild.voice_client:
                return False
            if interaction.guild.voice_client.channel != interaction.user.voice.channel:
                return False
            return True

        class MediaButtons(discord.ui.View):
            def __init__(self, timeout: float = None):
                super().__init__(timeout=timeout)

            async def on_timeout(self) -> None:
                for btn in self.children:
                    btn.disabled = True
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

                if not user_in_bot_vc(interaction):
                    return await interaction.response.send_message(
                        "Parece que no estás en mi canal de voz o no hay musica sonando.",
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
                if not user_in_bot_vc(interaction):
                    return await interaction.response.send_message(
                        "Parece que no estás en mi canal de voz o no hay musica sonando.",
                        ephemeral=True,
                    )

                if player.playing:
                    if not player.paused:
                        # pausado
                        await player.pause(True)
                        button.style = discord.ButtonStyle.green
                        button.emoji = "<:play:1200837254990549072>"
                        self.timeout = None
                        embed.color = discord.Color.yellow()
                        await interaction.response.edit_message(view=self, embed=embed)

                    else:
                        # NO pausado
                        await player.pause(False)
                        button.style = discord.ButtonStyle.blurple
                        button.emoji = "<:pausa:1200841413710065704>"
                        self.timeout = get_timeout_view()
                        
                        embed.color = discord.Color.green()
                        await interaction.response.edit_message(view=self, embed=embed)
                else:
                    return await interaction.response.send_message(
                        "No hay musica sonando", ephemeral=True
                    )

        mediabuttons = MediaButtons(timeout=get_timeout_view())

        embed = discord.Embed(
            title="Ahora suena",
            description=f"[{player.current.title}]({player.current.uri}) `{gettotalsongtime()}` \nAlbum: [{player.current.album.name}]({player.current.album.url})",
            color=discord.Color.blue(),
        )
        if player.current.artwork:
            embed.set_thumbnail(url=player.current.artwork)
        if hasattr(player, "home"):
            mediabuttons.message = await player.home.send(
                embed=embed, view=mediabuttons
            )

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        if payload.player:
            if len(payload.player.queue) >= 1:
                await payload.player.play(await payload.player.queue.get_wait())

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        if hasattr(player, "home"):
            await player.home.send("No hay más canciones por reproducir.")
        await player.disconnect()

    @commands.hybrid_command(name="play", aliases=["p"])
    async def playmusic(self, ctx: commands.Context, *, query: str):
        if (
            query.__contains__("https://www.youtube.com/watch")
            or query.__contains__("https://youtu.be/")
            or query.__contains__("https://music.youtube.com/watch")
        ):
            return await ctx.reply("No puedo reproducir musica de Youtube", mention_author=False)
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True)
        try:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        except AttributeError:
            return await ctx.send("Debes unirte a un canal de voz")
        except discord.errors.ClientException:
            player: wavelink.Player = ctx.voice_client
        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            return await ctx.send(
                f"El reproductor se inicializó en {player.home.mention}"
            )
        result: wavelink.Search = await wavelink.Playable.search(
            query, source="spsearch:"
        )
        if isinstance(result, wavelink.Playlist):
            added = await player.queue.put_wait(result)
            embed = discord.Embed(
                title="Playlist agregada a la cola",
                description=f"{result.name} - {added} canciones",
                color=discord.Color.blue(),
            )
            if result.artwork:
                embed.set_thumbnail(url=result.artwork)
        else:
            track: wavelink.Playable = result[0]
            await player.queue.put_wait(track)
            embed = discord.Embed(
                title="Canción agregada a la cola",
                description=f"{track.title}",
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
                title="Ahora suena",
                description=f"[{player.current.author}]({player.current.artist.url}) -  [{player.current.title}]({player.current.uri})",
                color=discord.Color.blue(),
            )
            if player.current.artwork:
                embed.set_thumbnail(url=player.current.artwork)
            await ctx.reply(embed=embed, ephemeral=True, mention_author=False)
        else:
            return await ctx.reply(
                "No hay musica sonando bro", ephemeral=True, mention_author=False
            )

    @commands.hybrid_command(name="queue", aliases=['q'])
    async def queue_cmd(self, ctx: commands.Context, pag: int = 1):
        player: wavelink.Player = ctx.voice_client
        if player is not None:
            pass
        else: return await ctx.reply("No hay musica sonando", ephemeral=True,mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCommands(bot))
