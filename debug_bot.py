# Discord.pyの音声機能を無効化してボットを実行するデバッグ用スクリプト

import sys
import traceback

print("デバッグモードで起動します...")

try:
    # まず音声機能を無効化するパッチを適用
    print("音声機能を無効化します...")
    import disable_voice
    print("音声機能の無効化が完了しました")
    
    # 環境変数のチェック
    import os
    from dotenv import load_dotenv
    load_dotenv()
    print("環境変数をロードしました")
    
    # Discordトークンの確認
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    if not DISCORD_TOKEN:
        print("エラー: DISCORD_TOKENが設定されていません")
        sys.exit(1)
    else:
        print(f"トークンが設定されています: {DISCORD_TOKEN[:5]}...")
    
    # OpenAI APIキーの確認
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not OPENAI_API_KEY:
        print("警告: OPENAI_API_KEYが設定されていません")
    else:
        print(f"OpenAI APIキーが設定されています: {OPENAI_API_KEY[:5]}...")
    
    # ボットをインポートして実行
    print("ボットをインポートします...")
    import bot
    print("ボットのインポートが完了しました")
    
    # ボットを明示的に実行
    print("ボットを実行します...")
    if hasattr(bot, 'bot') and hasattr(bot.bot, 'run'):
        print(f"Discordボットを起動します（トークン: {DISCORD_TOKEN[:5]}...）")
        bot.bot.run(DISCORD_TOKEN)
    else:
        print("エラー: botオブジェクトが見つからないか、runメソッドがありません")
        print(f"利用可能なbot属性: {dir(bot)}")
    
    print("ボットの実行が完了しました")
    
except Exception as e:
    print(f"エラーが発生しました: {str(e)}")
    traceback.print_exc()
