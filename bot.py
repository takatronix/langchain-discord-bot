import os
import sys
import json
import random
import discord
import traceback
from dotenv import load_dotenv
from discord.ext import commands
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

# 環境変数の読み込み
load_dotenv()

# 多重起動の防止は start_bot.sh スクリプトで行うため、ここでは実装しない

# Discordボットのトークン
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
if not DISCORD_TOKEN:
    print("エラー: DISCORD_TOKENが設定されていません。.envファイルを確認してください。")
    sys.exit(1)

# LLMプロバイダーの確認
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')  # デフォルトはOpenAI
BOT_ID = os.getenv('BOT_ID', '')  # ボットのユーザーID（メンション用）
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Discordボットの設定
intents = discord.Intents.default()
intents.message_content = True  # 特権インテントを有効化
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# チャンネルごとの会話履歴を保存する辞書
channel_memories = {}

# ボットの設定を保存する辞書
bot_settings = {
    'response_rate': 10,  # 自動応答する確率（%）
    'monitor_all_channels': False,  # すべてのチャンネルを監視するか
    'monitored_channels': [],  # 監視するチャンネルIDリスト
    'response_mode': 'helpful',  # 応答モード（helpful, concise, detailed）
    'language': 'japanese',  # 応答言語
    'llm_provider': LLM_PROVIDER,  # 使用するLLMプロバイダー
    'llm_model': 'gpt-3.5-turbo',  # 使用するモデル（プロバイダーによって異なる）
    'channel_prompts': {}  # チャンネルごとのプロンプト設定を保存する辞書
}

# 設定ファイルのパス
SETTINGS_FILE = 'bot_settings.json'

# LLMの初期化関数
def initialize_llm():
    provider = bot_settings.get('llm_provider', 'openai')
    model = bot_settings.get('llm_model', 'gpt-3.5-turbo')
    
    # OpenAIの場合
    if provider == 'openai' or not provider:
        return ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model_name=model
        )
    
    # OpenRouterの場合
    elif provider == 'openrouter':
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API Keyが設定されていません。.envファイルを確認してください。")
        
        # OpenRouterのモデル名を正規化
        # OpenRouterではモデル名が完全な形式で必要 (例: openai/gpt-4)
        if '/' not in model:
            if model.startswith('gpt'):
                model = f"openai/{model}"
            else:
                # デフォルトはgpt-4
                model = "openai/gpt-4"
                
        # OpenRouter用のOpenAI互換クライアントを設定
        print(f"OpenRouterを使用します: モデル {model}")
        
        # headersをパラメータとして渡さずに、基本的な設定のみで使用
        return ChatOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            model_name=model
        )
    
    # その他のプロバイダー
    raise NotImplementedError(f"{provider}プロバイダーは現在サポートされていません。!config llm_provider openai コマンドでOpenAIに切り替えてください。")

# Set up LangChain with selected LLM provider
llm = initialize_llm()

# 質問用のプロンプトテンプレート
def get_question_prompt(channel_id=None):
    # システムプロンプトを取得
    system_prompt = bot_settings.get('system_prompt', "あなたは親切なAIアシスタントです。以下の会話履歴を見て、質問に答えてください。\n\n会話履歴:\n{history}\n質問: {question}\n応答:")
    
    # 入力変数名を調整
    system_prompt = system_prompt.replace('{input}', '{question}')
    
    # チャンネルIDが指定され、そのチャンネルにカスタムプロンプトが設定されている場合は、それを追加する
    if channel_id and str(channel_id) in bot_settings['channel_prompts']:
        print(f"チャンネル{channel_id}用のカスタムプロンプトを追加します")
        channel_prompt = bot_settings['channel_prompts'][str(channel_id)]
        # チャンネルプロンプトをシステムプロンプトの前に追加
        template = f"{channel_prompt}\n\n{system_prompt}"
        return PromptTemplate(
            input_variables=["history", "question"],
            template=template
        )
    
    # システムプロンプトのみを使用する
    print("システムプロンプトを使用します")
    return PromptTemplate(
        input_variables=["history", "question"],
        template=system_prompt
    )

# チャット監視用のプロンプトテンプレート
def get_chat_prompt(channel_id=None):
    # システムプロンプトを取得
    system_prompt = bot_settings.get('system_prompt', "あなたはDiscordサーバーで会話を監視し、適切なタイミングでアドバイスや情報提供をする親切なAIアシスタントです。以下の会話履歴を見て、必要に応じてアドバイスや情報を提供してください。もし特に言うことがなければ、応答せずに会話を見守ってください。\n\n会話履歴:\n{history}\n最新のメッセージ: {input}\n応答:")
    
    # チャンネルIDが指定され、そのチャンネルにカスタムプロンプトが設定されている場合は、それを追加する
    if channel_id and str(channel_id) in bot_settings['channel_prompts']:
        print(f"チャンネル{channel_id}用のカスタムプロンプトを追加します")
        channel_prompt = bot_settings['channel_prompts'][str(channel_id)]
        # チャンネルプロンプトをシステムプロンプトの前に追加
        template = f"{channel_prompt}\n\n{system_prompt}"
        return PromptTemplate(
            input_variables=["history", "input"],
            template=template
        )
    
    # システムプロンプトのみを使用する
    print("システムプロンプトを使用します")
    return PromptTemplate(
        input_variables=["history", "input"],
        template=system_prompt
    )

# 設定ファイルの読み込み
def load_settings():
    global bot_settings
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                bot_settings = json.load(f)
            print("設定ファイルを読み込みました")
    except Exception as e:
        print(f"設定ファイルの読み込みに失敗しました: {str(e)}")

# 設定ファイルの保存
def save_settings():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_settings, f, indent=4, ensure_ascii=False)
        print("設定ファイルを保存しました")
    except Exception as e:
        print(f"設定ファイルの保存に失敗しました: {str(e)}")

# 質問用のチェーンを取得
def get_question_chain(channel_id=None):
    # チャンネルIDに基づいたプロンプトを取得
    prompt = get_question_prompt(channel_id)
    
    # チャンネルIDが指定されている場合、会話履歴を使用
    if channel_id and channel_id in channel_memories:
        memory = channel_memories[channel_id]
        print(f"チャンネル{channel_id}の会話履歴を使用します")
        # 会話履歴を取得
        history = memory.load_memory_variables({})['history']
        # LLMChainを使用して履歴と質問を処理
        return LLMChain(llm=llm, prompt=prompt, verbose=True)
    
    # チャンネルIDがない場合や履歴がない場合は、空の履歴でチェーンを返す
    print("会話履歴なしで質問に応答します")
    return LLMChain(llm=llm, prompt=prompt, verbose=True)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    global BOT_ID
    if not BOT_ID:
        BOT_ID = str(bot.user.id)
    
    # 設定ファイルの読み込み
    load_settings()

@bot.event
async def on_message(message):
    # 自分自身のメッセージには応答しない
    if message.author == bot.user:
        return
    
    # コマンド処理を優先
    await bot.process_commands(message)
    
    # コマンドではない通常のメッセージを処理
    if not message.content.startswith(bot.command_prefix):
        # ボットへのメンションがある場合、または設定された確率で応答
        bot_mentioned = f'<@{BOT_ID}>' in message.content or f'<@!{BOT_ID}>' in message.content
        
        # ボットの名前で呼びかけられたかチェック
        bot_name_called = False
        message_lower = message.content.lower()
        
        # ボットの名前とエイリアスをチェック
        if 'bot_name' in bot_settings and 'bot_name_aliases' in bot_settings:
            bot_name = bot_settings['bot_name'].lower()
            bot_aliases = [alias.lower() for alias in bot_settings['bot_name_aliases']]
            
            # 名前が含まれているかチェック
            if bot_name in message_lower:
                bot_name_called = True
                print(f"ボットの名前({bot_name})が呼びかけられました")
            else:
                # エイリアスをチェック
                for alias in bot_aliases:
                    if alias in message_lower:
                        bot_name_called = True
                        print(f"ボットのエイリアス({alias})が呼びかけられました")
                        break
        
        # チャンネルが監視対象かチェック
        channel_monitored = (
            bot_settings['monitor_all_channels'] or 
            message.channel.id in bot_settings['monitored_channels']
        )
        
        # 応答条件の決定
        # 1. メンションされた場合は必ず応答
        # 2. 名前で呼ばれた場合は必ず応答
        # 3. 上記以外の場合は、監視対象チャンネルかつランダム確率で応答
        should_respond = False
        response_reason = ""
        
        if bot_mentioned:
            should_respond = True
            response_reason = "メンション"
        elif bot_name_called:
            should_respond = True
            response_reason = "名前呼びかけ"
        elif channel_monitored and (hash(message.id) % 100) < bot_settings['response_rate']:
            should_respond = True
            response_reason = f"ランダム応答（確率: {bot_settings['response_rate']}%）"
        else:
            # 応答条件を満たさない場合は処理を終了
            return
        
        print(f"応答理由: {response_reason}")
        
        # チャンネルの会話履歴を取得または初期化
        if message.channel.id not in channel_memories:
            channel_memories[message.channel.id] = ConversationBufferMemory(return_messages=True)
        
        memory = channel_memories[message.channel.id]
        
        # 会話履歴にユーザーメッセージを追加
        memory.chat_memory.add_user_message(f"{message.author.display_name}: {message.content}")
        
        # チャット監視用のチェーンを作成
        chat_prompt = get_chat_prompt(message.channel.id)
        print(f"プロンプトテンプレート: {chat_prompt.template}")
        
        # LLMChainを使用して会話履歴を活用
        chat_chain = LLMChain(
            llm=llm,
            prompt=chat_prompt,
            verbose=True
        )
        
        # 会話履歴を取得
        history = memory.load_memory_variables({})['history']
        print(f"会話履歴: {history[:100]}...")
        
        async with message.channel.typing():
            try:
                print(f"LLMにリクエストを送信します: プロバイダー={bot_settings['llm_provider']}, モデル={bot_settings['llm_model']}")
                # チェーンを実行
                response = chat_chain.invoke({"history": history, "input": message.content})
                print(f"LLMからの応答を受信しました: {response}")
                response_text = response["text"].strip()
                print(f"整形された応答テキスト: {response_text}")
                
                # 応答があれば送信
                if response_text and not response_text.lower() in ["なし", "特になし", "応答なし", "none", "no response"]:
                    await message.channel.send(response_text)
                    # ボットの応答も履歴に追加
                    memory.chat_memory.add_ai_message(response_text)
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"エラーが発生しました: {str(e)}")
                print(error_details)
                await message.channel.send(f"OpenAI APIエラーが発生しました: {str(e)}\n管理者に連絡するか、!config llm_provider コマンドで別のプロバイダーに切り替えてください。")

@bot.command(name='ask')
async def ask(ctx, *, question):
    """AIに質問する"""
    # 入力中表示を送信
    async with ctx.typing():
        try:
            # チャンネルの会話履歴を取得または作成
            if ctx.channel.id not in channel_memories:
                channel_memories[ctx.channel.id] = ConversationBufferMemory(return_messages=True)
            
            # チャンネルIDを渡してチェーンを実行
            question_chain = get_question_chain(ctx.channel.id)
            
            # 会話履歴を取得
            memory = channel_memories[ctx.channel.id]
            history = memory.load_memory_variables({})['history']
            
            # 質問を実行
            response = question_chain.invoke({"history": history, "question": question})
            response_text = response["text"]
            
            # 応答を送信
            await ctx.send(response_text)
            
            # 会話履歴に追加
            memory = channel_memories[ctx.channel.id]
            memory.chat_memory.add_user_message(f"{ctx.author.display_name}: {ctx.message.content}")
            memory.chat_memory.add_ai_message(response_text)
            
        except Exception as e:
            error_message = str(e)
            
            # OpenAIのクォータエラーを検出
            if "insufficient_quota" in error_message or "exceeded your current quota" in error_message:
                await ctx.send("OpenAI APIの利用制限に達しました。管理者に連絡するか、`!config llm_provider` コマンドで別のプロバイダーに切り替えてください。")
            # その他のOpenAIエラー
            elif "openai" in error_message.lower():
                await ctx.send(f"OpenAI APIエラーが発生しました: {error_message}\n管理者に連絡するか、`!config llm_provider` コマンドで別のプロバイダーに切り替えてください。")
            # その他のエラー
            else:
                await ctx.send(f"エラーが発生しました: {error_message}")

@bot.command(name='commands')
async def commands_help(ctx):
    """利用可能なコマンドを表示"""
    help_text = """
**利用可能なコマンド:**

**一般ユーザー向け:**
- `!ask [質問]`: AIに質問する
- `!commands`: このヘルプを表示

**管理者向け:**
- `!clear`: チャンネルの会話履歴をクリア
- `!config`: ボットの設定を表示・変更する
- `!monitor`: チャンネルの監視状態を切り替える
- `!set_prompt` / `!prompt`: チャンネルごとのプロンプトを設定する

**ボットとの会話方法:**
- ボットの名前で呼びかける: 「AI_Agent」「AIエージェント」「エージェント」「AI」「ボット」
- メンションする: @AI_Agent
- コマンドを使う: !ask [質問]
"""
    await ctx.send(help_text)

@bot.command(name='clear')
@commands.has_permissions(administrator=True)
async def clear_memory(ctx):
    """チャンネルの会話履歴をクリア（管理者のみ）"""
    if ctx.channel.id in channel_memories:
        channel_memories[ctx.channel.id] = ConversationBufferMemory(return_messages=True)
        await ctx.send("このチャンネルの会話履歴をクリアしました。")
    else:
        await ctx.send("このチャンネルには保存された会話履歴がありません。")

@bot.command(name='config')
@commands.has_permissions(administrator=True)
async def config_command(ctx, setting=None, value=None):
    """ボットの設定を表示・変更する（管理者のみ）"""
    if setting is None:
        # 現在の設定を表示
        settings_str = "現在の設定:\n"
        for key, val in bot_settings.items():
            settings_str += f"`{key}`: `{val}`\n"
        
        settings_str += "\n設定可能な項目:\n"
        settings_str += "`response_rate`: 自動応答する確率（%）\n"
        settings_str += "`monitor_all_channels`: すべてのチャンネルを監視するか（True/False）\n"
        settings_str += "`llm_provider`: 使用するLLMプロバイダー（openai, openrouter, anthropic, google, litellm）\n"
        settings_str += "`llm_model`: 使用するモデル名（プロバイダーによって異なる）\n"
        settings_str += "`system_prompt`: システムプロンプトテンプレート\n"
        
        await ctx.send(settings_str)
        return
    
    # 設定名が存在するか確認
    if setting not in bot_settings:
        await ctx.send(f"設定 `{setting}` は存在しません。`!config` で設定可能な項目を確認してください。")
        return
    
    # 設定値が指定されていない場合は現在の値を表示
    if value is None:
        await ctx.send(f"設定 `{setting}` の現在の値: `{bot_settings[setting]}`")
        return
    
    # 設定を変更
    try:
        # 値の型に応じて変換
        if setting == 'monitor_all_channels':
            if value.lower() in ['true', 'yes', 'on', '1']:
                bot_settings[setting] = True
            elif value.lower() in ['false', 'no', 'off', '0']:
                bot_settings[setting] = False
            else:
                await ctx.send(f"無効な値です。`True` または `False` を指定してください。")
                return
        elif isinstance(bot_settings[setting], int):
            try:
                bot_settings[setting] = int(value)
            except ValueError:
                await ctx.send(f"無効な値です。整数を指定してください。")
                return
        elif isinstance(bot_settings[setting], str):
            if setting == 'llm_provider' and value not in ['openai', 'openrouter', 'anthropic', 'google', 'litellm']:
                await ctx.send(f"無効なLLMプロバイダーです。`openai`, `openrouter`, `anthropic`, `google`, `litellm` のいずれかを指定してください。")
                return
            bot_settings[setting] = value
            
            # LLMプロバイダーが変更された場合、LLMを再初期化
            if setting == 'llm_provider' or setting == 'llm_model':
                global llm
                try:
                    llm = initialize_llm()
                    await ctx.send(f"LLMプロバイダーを `{bot_settings['llm_provider']}` に変更し、モデル `{bot_settings['llm_model']}` で初期化しました。")
                except Exception as e:
                    await ctx.send(f"LLMの初期化中にエラーが発生しました: {str(e)}\n設定は変更されましたが、APIキーが正しく設定されているか確認してください。")
        elif isinstance(bot_settings[setting], list):
            # リスト型の設定は別のコマンドで管理
            await ctx.send(f"リスト型の設定は `!monitor` コマンドで管理してください。")
            return
        
        # 設定を保存
        save_settings()
        
        await ctx.send(f"設定 `{setting}` を `{bot_settings[setting]}` に変更しました。")
    except Exception as e:
        await ctx.send(f"設定の変更中にエラーが発生しました: {str(e)}")

@bot.command(name='set_prompt')
@commands.has_permissions(administrator=True)
async def set_prompt_command(ctx, *, prompt_text=None):
    """チャンネルごとのプロンプトを設定する（管理者のみ）"""
    await set_prompt_internal(ctx, prompt_text)

@bot.command(name='prompt')
@commands.has_permissions(administrator=True)
async def prompt_command(ctx, *, prompt_text=None):
    """チャンネルごとのプロンプトを設定する（set_promptのエイリアス）（管理者のみ）"""
    await set_prompt_internal(ctx, prompt_text)
    
async def set_prompt_internal(ctx, prompt_text=None):
    """チャンネルごとのプロンプトを設定する（管理者のみ）"""
    channel_id = str(ctx.channel.id)
    
    if prompt_text is None:
        # 現在のプロンプトを表示
        if channel_id in bot_settings['channel_prompts']:
            await ctx.send(f"このチャンネルの現在のプロンプト:\n```\n{bot_settings['channel_prompts'][channel_id]}\n```")
        else:
            await ctx.send("このチャンネルにはカスタムプロンプトが設定されていません。デフォルトのプロンプトが使用されます。")
        return
    
    if prompt_text.lower() == 'reset' or prompt_text.lower() == 'default':
        # プロンプトをデフォルトにリセット
        if channel_id in bot_settings['channel_prompts']:
            del bot_settings['channel_prompts'][channel_id]
            save_settings()
            await ctx.send("このチャンネルのプロンプトをデフォルトにリセットしました。")
        else:
            await ctx.send("このチャンネルにはカスタムプロンプトが設定されていません。")
        return
    
    # 新しいプロンプトを設定
    bot_settings['channel_prompts'][channel_id] = prompt_text
    save_settings()
    await ctx.send("このチャンネルのプロンプトを設定しました。")

@bot.command(name='monitor')
@commands.has_permissions(administrator=True)
async def monitor_command(ctx, action=None):
    """チャンネルの監視状態を切り替える（管理者のみ）"""
    channel_id = ctx.channel.id
    
    if action is None:
        # 現在の監視状態を表示
        if bot_settings['monitor_all_channels']:
            await ctx.send("現在、すべてのチャンネルを監視しています。")
        elif channel_id in bot_settings['monitored_channels']:
            await ctx.send("このチャンネルは監視対象です。")
        else:
            await ctx.send("このチャンネルは監視対象ではありません。")
        return
    
    if action.lower() in ['on', 'add', 'enable', 'true']:
        # チャンネルを監視対象に追加
        if channel_id not in bot_settings['monitored_channels']:
            bot_settings['monitored_channels'].append(channel_id)
            save_settings()
            await ctx.send("このチャンネルを監視対象に追加しました。")
        else:
            await ctx.send("このチャンネルはすでに監視対象です。")
    elif action.lower() in ['off', 'remove', 'disable', 'false']:
        # チャンネルを監視対象から削除
        if channel_id in bot_settings['monitored_channels']:
            bot_settings['monitored_channels'].remove(channel_id)
            save_settings()
            await ctx.send("このチャンネルを監視対象から削除しました。")
        else:
            await ctx.send("このチャンネルは監視対象ではありません。")
    elif action.lower() in ['all', 'global']:
        # すべてのチャンネルを監視対象に設定
        bot_settings['monitor_all_channels'] = True
        save_settings()
        await ctx.send("すべてのチャンネルを監視対象に設定しました。")
    elif action.lower() in ['none', 'selective']:
        # 選択的なチャンネル監視に設定
        bot_settings['monitor_all_channels'] = False
        save_settings()
        await ctx.send("選択的なチャンネル監視に設定しました。`!monitor on` で個別のチャンネルを監視対象に追加できます。")
    else:
        await ctx.send("無効なアクションです。`on`, `off`, `all`, `none` のいずれかを指定してください。")

# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
