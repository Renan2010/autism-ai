import ollama
import os
import discord
import asyncio
import subprocess
from discord.ext import commands
import dotenv
from flask import Flask
from threading import Thread
from pyngrok import ngrok

app = Flask('')


@app.route('/')
def home():
    return "server is running"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    thread = Thread(target=run)
    thread.start()


def start_ngrok():
    ngrok_tunnel = ngrok.connect(8080)
    print('Public URL:', ngrok_tunnel.public_url)
    return ngrok_tunnel


async def start_ollama():
    # Start the Ollama server
    print("Starting Ollama server...")
    ollama_subprocess = subprocess.Popen(["ollama", "serve"])
    await asyncio.sleep(5)
    print("Ollama server started.")
    # Download the model
    print("Downloading model...")
    subprocess.run(["ollama", "pull", "gemma3:1b"])
    print("Model downloaded.")
    # Return the subprocess object
    return ollama_subprocess


# Global conversation history
conversation_history = []


async def main():
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='/', intents=intents)

    dotenv.load_dotenv()
    keep_alive()
    start_ngrok()
    ollama_process = await start_ollama()

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")

    async def keep_typing(ctx):
        try:
            while True:
                await ctx.typing()
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass

    @bot.command(name='ask')
    async def ask(ctx, *, message):
        global conversation_history
        print("============================")
        print(f"Received message: {message}")
        print("============================")
        try:
            response_message = await ctx.send("Generating response...")
            typing_task = asyncio.create_task(keep_typing(ctx))

            # Add the user's message to the conversation history
            conversation_history.append({'role': 'user', 'content': message})

            # Maintain a max history length
            max_history_length = 10
            if len(conversation_history) > max_history_length:
                conversation_history = conversation_history[
                    -max_history_length:]

            # System message
            system_message = {
                'role':
                'system',
                'content':
                ("Your name is Autism AI. You are a highly detailed and informative assistant who provides in-depth explanations. "
                 "When responding, aim to provide as much useful information as possible within the 2000 character limit (Discord). "
                 "Elaborate on key points, use examples, and ensure that complex concepts are broken down into simple, digestible parts. "
                 "Adapt your responses to be especially clear and structured for autistic and neurodivergent users."
                 )
            }

            # Add the system message to the conversation history
            messages = [system_message] + conversation_history

            def get_response():
                return ollama.chat(
                    model="gemma3:1b",
                    messages=messages,
                )

            # Get response from Ollama API
            response = await asyncio.to_thread(get_response)
            response_content = response['message']['content']

            print(response_content)

            # Add the assistant's response to the conversation history
            conversation_history.append({
                'role': 'assistant',
                'content': response_content
            })

            # Enviar a resposta em chunks de 2000 caracteres
            max_chars = 2000
            chunks = [
                response_content[i:i + max_chars]
                for i in range(0, len(response_content), max_chars)
            ]

            # Editar a primeira mensagem com o primeiro chunk
            await response_message.edit(content=chunks[0])

            # Enviar os chunks restantes
            for chunk in chunks[1:]:
                await ctx.send(chunk)

        except Exception as e:
            print(f"Error: {e}")
            await ctx.send(
                "An error occurred while processing your request. Sorry.")
        finally:
            typing_task.cancel()

    try:
        await bot.start(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        print(f"Error starting bot: {e}")
    finally:
        ollama_process.terminate()


# Run the bot
asyncio.run(main())
