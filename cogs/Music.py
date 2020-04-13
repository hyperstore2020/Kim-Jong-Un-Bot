# Imports
import discord
import youtube_dl
import os
import asyncio
import json
from helper import *
from parameters import *
from discord.ext import commands


opts = {
    "default_search": "ytsearch",
    'format': 'bestaudio/best',
    'quiet': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'extract_flat': 'in_playlist',
    'extractaudio': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'no_warnings': True,
    'sleep_interval': 1,
}


def create_ytdl_source(source):
    player = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            source,
            before_options=" -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 1",
            options='-vn'
        ),
        volume=0.5
    )
    return player


def get_info(url):
    with youtube_dl.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    video = None
    if "_type" in info and info["_type"] == "playlist":
        return get_info(
            info['entries'][0]['url']
        )
    else:
        video = info
    return video


def get_video_info(url):
    video = get_info(url)
    video_format = video['formats'][0]
    stream_url = video_format['url']
    video_url = video['webpage_url']
    title = video['title']
    uploader = video["uploader"] if "uploader" in video else ""
    thumbnail = video["thumbnail"] if "thumbnail" in video else None
    return [stream_url, title, video_url]


class Music(commands.Cog, name='Music'):
    def __init__(self, client):
        self.client = client

    def play_song(self, voice):
        with open('queue.json', 'r') as f:
            queue = json.load(f)
        info = get_video_info(queue[str(voice)][1]['url'])
        source = create_ytdl_source(info[0])
        text_channel = self.client.get_channel(int(
            queue[str(voice)][0]['text_channel']
        ))
        asyncio.run_coroutine_threadsafe(
            text_channel.send(
                embed=create_embed(
                    f'**Now playing**: [{info[1]}]({info[2]})'
                )
            ), self.client.loop
        )

        def after_playing(error):
            with open('queue.json', 'r') as f:
                queue = json.load(f)
            info = queue[str(voice)].pop(1)
            if queue[str(voice)][0]['loop'] == 'all':
                queue[str(voice)].append(info)
            elif queue[str(voice)][0]['loop'] == 'one':
                queue[str(voice)].insert(1, info)
            with open('queue.json', 'w') as f:
                json.dump(queue, f, indent=4)
            if len(queue[str(voice)]) > 1:
                self.play_song(voice)
            else:
                with open('queue.json', 'r') as f:
                    queue = json.load(f)
                queue.pop(str(voice))
                with open('queue.json', 'w') as f:
                    json.dump(queue, f, indent=4)
                asyncio.run_coroutine_threadsafe(
                    text_channel.send(
                        embed=create_embed(
                            'Music queue ended, disconnected from voice'
                        )
                    ), self.client.loop
                )
                asyncio.run_coroutine_threadsafe(
                    voice.disconnect(), self.client.loop)

        voice.play(source, after=after_playing)

    @commands.command(
        name='join',
        aliases=['j', 'connect', ],
        description='Connect to your current voice channel',
        usage=f'`.join`'
    )
    async def join(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        elif ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    "You are not in any voice channel"
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if len(voice.channel.members) == 1:
                    await voice.move_to(channel)
                    await ctx.send(
                        embed=create_embed(
                            f'Bot connected to **{channel}**'
                        )
                    )
                elif voice.is_playing() or voice.is_paused():
                    await ctx.send(
                        embed=create_embed(
                            'Please wait until other members are done listening to music'
                        )
                    )
                else:
                    await voice.move_to(channel)
                    await ctx.send(
                        embed=create_embed(
                            f'Bot connected to **{channel}**'
                        )
                    )
            else:
                voice = await channel.connect(reconnect=True)
                with open('queue.json', 'r') as f:
                    queue = json.load(f)
                queue[str(voice)] = [
                    {
                        'loop': 'off',
                        "text_channel": str(ctx.channel.id),
                    },
                ]
                with open('queue.json', 'w') as f:
                    json.dump(queue, f, indent=4)
                await ctx.send(
                    embed=create_embed(
                        f'Bot connected to **{channel}**'
                    )
                )

    @commands.command(
        name='leave',
        aliases=['dc', 'disconnect'],
        description='Disconnect from the voice channel',
        usage=f'`.leave`'
    )
    async def leave(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        else:
            voice = ctx.voice_client
            if voice != None:
                with open('queue.json', 'r') as f:
                    queue = json.load(f)
                if len(voice.channel.members) == 1:
                    if voice.is_playing() or voice.is_paused():
                        queue[str(voice)] = queue[str(voice)][:2]
                        queue[str(voice)][0]['loop'] = 'off'
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        voice.stop()
                    else:
                        queue.pop(str(voice))
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await voice.disconnect()
                        await ctx.send(
                            embed=create_embed(
                                f'Bot disconnected from **{voice.channel}**'
                            )
                        )
                else:
                    if voice.is_playing() or voice.is_paused():
                        if ctx.author.voice.channel != voice.channel:
                            await ctx.send(
                                embed=create_embed(
                                    'Please wait until other members are done listening to music'
                                )
                            )
                        else:
                            queue[str(voice)] = queue[str(voice)][:2]
                            queue[str(voice)][0]['loop'] = 'off'
                            with open('queue.json', 'w') as f:
                                json.dump(queue, f, indent=4)
                            voice.stop()
                    else:
                        queue.pop(str(voice))
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await voice.disconnect()
                        await ctx.send(
                            embed=create_embed(
                                f'Bot disconnected from **{voice.channel}**'
                            )
                        )
            else:
                await ctx.send(
                    embed=create_embed(
                        'Bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='play',
        aliases=['p', ],
        description='Play music from Youtube',
        usage=f'`.play [url or song name]`'
    )
    async def play(self, ctx, *, url):
        if ctx.author.voice == None:
            await ctx.channel.purge(limit=1)
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            text_channel = ctx.channel
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            with open('queue.json', 'r') as f:
                queue = json.load(f)
            if voice != None:
                if voice.channel != channel:
                    if len(voice.channel.members) == 1:
                        info = get_video_info(url)
                        queue.pop(str(voice))
                        await voice.move_to(channel)
                        queue[str(voice)] = [
                            {
                                'loop': 'off',
                                "text_channel": str(text_channel.id),
                            },
                        ]
                        queue[str(voice)].append(
                            {
                                'url': info[2],
                                'title': info[1]
                            }
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await ctx.channel.purge(limit=1)
                        self.play_song(voice)
                    elif voice.is_playing() or voice.is_paused():
                        await ctx.channel.purge(limit=1)
                        await ctx.send(
                            embed=create_embed(
                                'Please wait until other members are done listening to music'
                            )
                        )
                    else:
                        info = get_video_info(url)
                        queue.pop(str(voice.channel.id))
                        await voice.move_to(channel)
                        queue[str(voice)] = [
                            {
                                'loop': 'off',
                                "text_channel": str(text_channel.id),
                            },
                        ]
                        queue[str(voice)].append(
                            {
                                'url': info[2],
                                'title': info[1]
                            }
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await ctx.channel.purge(limit=1)
                        self.play_song(voice)
                else:
                    if voice.is_playing() or voice.is_paused():
                        info = get_video_info(url)
                        queue[str(voice)].append(
                            {
                                'url': info[2],
                                'title': info[1]
                            }
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await ctx.channel.purge(limit=1)
                        await ctx.send(
                            embed=create_embed(
                                f'Song [{info[1]}]({info[2]}) added to queue'
                            )
                        )
                    else:
                        info = get_video_info(url)
                        queue[str(voice)].append(
                            {
                                'url': info[2],
                                'title': info[1]
                            }
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await ctx.channel.purge(limit=1)
                        self.play_song(voice)

            else:
                voice = await channel.connect(reconnect=True)
                info = get_video_info(url)
                queue[str(voice)] = [
                    {
                        'loop': 'off',
                        "text_channel": str(text_channel.id),
                    },
                ]
                queue[str(voice)].append(
                    {
                        'url': info[2],
                        'title': info[1]
                    }
                )
                with open('queue.json', 'w') as f:
                    json.dump(queue, f, indent=4)
                await ctx.channel.purge(limit=1)
                self.play_song(voice)

    @commands.command(
        name='pause',
        aliases=['pau', 'pa'],
        description='Pauses the music',
        usage=f'`.pause`'
    )
    async def pause(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        elif ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if voice.channel == channel:
                    if voice.is_playing():
                        voice.pause()
                        await ctx.send(
                            embed=create_embed(
                                'Music paused'
                            )
                        )
                    elif voice.is_paused():
                        await ctx.send(
                            embed=create_embed(
                                'Cannot pause while bot was already paused'
                            )
                        )
                    else:
                        await ctx.send(
                            embed=create_embed(
                                'Cannot pause while bot was not playing music'
                            )
                        )
                else:
                    await ctx.send(
                        embed=create_embed(
                            'Please wait until other members are done listening to music'
                        )
                    )
            else:
                await ctx.send(
                    embed=create_embed(
                        'Cannot pause while bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='resume',
        aliases=['res', 're'],
        description='Resume the music',
        usage=f'`.resume`'
    )
    async def resume(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        elif ctx.author.voice == None:
            ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if voice.channel != channel:
                    await ctx.send(
                        embed=create_embed(
                            'Please wait until other members are done listening to music'
                        )
                    )
                else:
                    if voice.is_paused():
                        voice.resume()
                        await ctx.send(
                            embed=create_embed(
                                'Resumed music'
                            )
                        )
                    elif voice.is_playing():
                        await ctx.send(
                            embed=create_embed(
                                'Cannot resume if music is already playing'
                            )
                        )
                    else:
                        await ctx.send(
                            embed=create_embed(
                                'Cannot resume if there is no music to play'
                            )
                        )
            else:
                await ctx.send(
                    embed=create_embed(
                        'Cannot resume while bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='stop',
        aliases=['s', 'st', ],
        description='Stop playing music',
        usage=f'`.stop`'
    )
    async def stop(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        elif ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if len(voice.channel.members) == 1:
                    if voice.is_playing() or voice.is_paused():
                        await ctx.send(
                            embed=create_embed(
                                'Stopped playing music'
                            )
                        )
                    voice.stop()
                elif voice.is_playing() or voice.is_paused():
                    if voice.channel != channel:
                        await ctx.send(
                            embed=create_embed(
                                'Please wait until other members are done listening to music'
                            )
                        )
                    else:
                        with open('queue.json', 'r') as f:
                            queue = json.load(f)
                        queue[str(voice)] = queue[str(voice)][:2]
                        queue[str(voice)][0]['loop'] = 'off'
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                        await ctx.send(
                            embed=create_embed(
                                'Stopped playing music'
                            )
                        )
                        voice.stop()
                else:
                    await ctx.send(
                        embed=create_embed(
                            'Cannot stop if no music is playing'
                        )
                    )
            else:
                await ctx.send(
                    embed=create_embed(
                        'Cannot stop while bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='skip',
        aliases=['sk', ],
        description='Skip the song currently being played',
        usage=f'`.skip`'
    )
    async def skip(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        elif ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if voice.channel != channel:
                    await ctx.send(
                        embed=create_embed(
                            'Please wait until other members are done listening to music'
                        )
                    )
                else:
                    with open('queue.json', 'r') as f:
                        queue = json.load(f)
                    info = queue[str(voice)][1]
                    if queue[str(voice)][0]['loop'] == 'one':
                        queue[str(voice)].pop(1)
                    await ctx.send(
                        embed=create_embed(
                            f'Skipped [{info["title"]}]({info["url"]}), playing next'
                        )
                    )
                    with open('queue.json', 'w') as f:
                        json.dump(queue, f, indent=4)
                    voice.stop()
            else:
                await ctx.send(
                    embed=create_embed(
                        'Bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='queue',
        aliases=['q', ],
        description='Display your current music queue',
        usage=f'`.queue`'
    )
    async def queue(self, ctx, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command does not take in any other argument'
                )
            )
        elif ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if voice.channel != channel:
                    await ctx.send(
                        embed=create_embed(
                            'You are not using music'
                        )
                    )
                else:
                    with open('queue.json', 'r') as f:
                        queue = json.load(f)
                    if len(queue[str(voice)]) == 1:
                        await ctx.send(
                            embed=create_embed(
                                'The music queue is empty'
                            )
                        )
                    else:
                        info = queue[str(voice)][1]
                        output = f'**Now playing**: [{info["title"]}]({info["url"]})\n'
                        if len(queue[str(voice)]) > 2:
                            counter = 1
                            for song in queue[str(voice)][2:]:
                                output += f'{counter}. [{song["title"]}]({song["url"]})\n'
                                counter += 1
                        embed = discord.Embed(
                            color=discord.Color.orange(),
                            description=output
                        )
                        embed.set_author(
                            name=f'Music queue for {ctx.author.voice.channel}'
                        )
                        embed.set_footer(
                            text=f'Repeat: {queue[str(voice)][0]["loop"]}'
                        )
                        await ctx.send(embed=embed)
            else:
                await ctx.send(
                    embed=create_embed(
                        'Bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='dequeue',
        aliases=['rmq', 'rm'],
        description='Remove a song from the music queue',
        usage=f'`.dequeue [song position in music queue]`'
    )
    async def dequeue(self, ctx, position: int, arg=None):
        if arg != None:
            await ctx.send(
                embed=create_embed(
                    'This command only takes in one argument'
                )
            )
        elif ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if voice.channel != channel:
                    await ctx.send(
                        embed=create_embed(
                            'Please wait until other members are done listening to music'
                        )
                    )
                else:
                    with open('queue.json', 'r') as f:
                        queue = json.load(f)
                    if position > len(queue[str(voice)])-2 or position < 0:
                        await ctx.send(
                            embed=create_embed(
                                f'The music queue have **{len(queue[str(voice)])-2}** songs, but you specified more than that!'
                            )
                        )
                    else:
                        info = queue[str(voice)][position+1]
                        queue[str(voice)].pop(position+1)
                        await ctx.send(
                            embed=create_embed(
                                f'Song [{info["title"]}]({info["url"]}) removed from music queue'
                            )
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
            else:
                await ctx.send(
                    embed=create_embed(
                        'Bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='loop',
        aliases=['repeat', ],
        description='Toggle between looping all, one or off',
        usage=f'`.loop [all/one/off]`'
    )
    async def loop(self, ctx, arg=None):
        if ctx.author.voice == None:
            await ctx.send(
                embed=create_embed(
                    'You must be connected to a voice channel to use this command'
                )
            )
        else:
            channel = ctx.author.voice.channel
            voice = ctx.voice_client
            if voice != None:
                if voice.channel != channel:
                    await ctx.send(
                        embed=create_embed(
                            'Please wait until other members are done listening to music'
                        )
                    )
                else:
                    with open('queue.json', 'r') as f:
                        queue = json.load(f)
                    if arg == None or arg == 'all':
                        queue[str(voice)][0]['loop'] = 'all'
                        await ctx.send(
                            embed=create_embed(
                                'Repeating all songs in the music queue'
                            )
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                    elif arg == 'one':
                        queue[str(voice)][0]['loop'] = 'one'
                        await ctx.send(
                            embed=create_embed(
                                'Repeating the current song in the music queue'
                            )
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                    elif arg == 'off':
                        queue[str(voice)][0]['loop'] = 'off'
                        await ctx.send(
                            embed=create_embed(
                                'Repeating song is now off'
                            )
                        )
                        with open('queue.json', 'w') as f:
                            json.dump(queue, f, indent=4)
                    else:
                        await ctx.send(
                            embed=create_embed(
                                'Please use the correct argument'
                            )
                        )
            else:
                await ctx.send(
                    embed=create_embed(
                        'Bot was not connected to any voice channel'
                    )
                )

    @commands.command(
        name='voiceping',
        aliases=['vping', ],
        description='Check the voice latency',
        usage=f'`.voiceping`'
    )
    async def voiceping(self, ctx):
        voice = ctx.voice_client
        if voice == None:
            await ctx.send(
                embed=create_embed(
                    'Bot was not connected to any voice channel'
                )
            )
        else:
            time = round(voice.latency*1000)
            await ctx.send(
                embed=create_embed(
                    f'The voice ping is {time} ms!'
                )
            )

    # Error handler
    @play.error
    async def play_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=create_embed(
                    'The play command also need a link or search keyword to work'
                )
            )

    @dequeue.error
    async def dequeue_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=create_embed(
                    'Please use the correct argument'
                )
            )


# Add cog
def setup(client):
    client.add_cog(Music(client))