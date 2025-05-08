# LangChain Discord AI Bot

このプロジェクトは、LangChainとOpenAI/OpenRouterを使用したDiscord AI botの実装です。会話を監視し、設定に応じたアドバイスや応答を行うことができます。また、ユーザーからの質問に答えることもできます。名前で呼びかけられた場合にも応答します。

## 主な機能

- **会話監視と自動応答**: チャンネル内の会話を監視し、適切なタイミングでアドバイスや情報を提供
- **質問応答**: ユーザーからの質問に対してAIが回答
- **名前認識**: ボットの名前で呼びかけると応答
- **チャンネル別カスタムプロンプト**: 各チャンネルに異なるAIの性格や応答スタイルを設定可能
- **複数LLMプロバイダー対応**: OpenAI、OpenRouter（Claude、Anthropicなど）をサポート
- **会話履歴の保持**: チャンネルごとに会話の文脈を記憶

## セットアップ

1. 必要なパッケージをインストール:
   ```
   pip install -r requirements.txt
   ```

2. `.env`ファイルを作成し、以下の環境変数を設定:
   ```
   # Discord Bot Token from Discord Developer Portal
   DISCORD_TOKEN=あなたのDiscordボットトークン

   # OpenAI API Key
   OPENAI_API_KEY=あなたのOpenAI APIキー

   # OpenRouter API Key (optional)
   OPENROUTER_API_KEY=あなたのOpenRouter APIキー

   # LLM Provider Selection (openai, openrouter, anthropic, google)
   LLM_PROVIDER=openai

   # LLM Model Selection (gpt-3.5-turbo, gpt-4, anthropic/claude-3.7-sonnet, etc.)
   LLM_MODEL=gpt-4

   # Discord Bot User ID (optional, will be auto-detected if not set)
   # BOT_ID=あなたのボットユーザーID
   ```

3. ボットを実行:
   ```
   ./start_bot.sh
   ```
   または
   ```
   python bot.py  # 通常モード
   python debug_bot.py  # デバッグモード（音声機能無効）
   ```

初回起動時に`bot_settings.json`ファイルが自動的に作成され、デフォルト設定が保存されます。

## 使い方

Discordサーバーで以下の方法でボットと会話できます:

### ボットとの会話方法

1. **名前で呼びかける**:
   - 「AI_Agent、こんにちは」
   - 「AIエージェント、今日の天気は？」
   - 「エージェント、助けて」
   - 「AIって何ができるの？」
   - 「ボット、おはよう」

2. **メンションする**:
   - 「@AI_Agent こんにちは」

3. **コマンドを使用する**:
   - 「!ask 今日の天気は？」

### 一般ユーザー向けコマンド
- `!ask [質問]`: AIに質問をする
- `!commands`: 利用可能なコマンドの一覧を表示

### 管理者向けコマンド
- `!clear`: チャンネルの会話履歴をクリア
- `!config`: ボットの設定を表示・変更する
  - `!config`: 現在の設定を表示
  - `!config [設定名]`: 特定の設定の値を表示
  - `!config [設定名] [値]`: 設定を変更
- `!monitor`: チャンネルの監視状態を切り替える
  - `!monitor`: 現在の監視状態を表示
  - `!monitor on`: 現在のチャンネルを監視対象に追加
  - `!monitor off`: 現在のチャンネルを監視対象から削除
  - `!monitor all`: すべてのチャンネルを監視対象に設定
  - `!monitor none`: 選択的なチャンネル監視に設定
- `!set_prompt` / `!prompt`: チャンネルごとのプロンプトを設定する
  - `!prompt`: 現在のプロンプトを表示
  - `!prompt [プロンプトテキスト]`: 新しいプロンプトを設定
  - `!prompt reset`: デフォルトプロンプトにリセット

## カスタマイズ可能な設定

### 基本設定
- `response_rate`: 自動応答する確率（0-100の整数）
- `monitor_all_channels`: すべてのチャンネルを監視するか（true/false）
- `monitored_channels`: 監視するチャンネルのIDリスト

### LLM設定
- `llm_provider`: 使用するLLMプロバイダー（openai, openrouter, anthropic, google）
- `llm_model`: 使用するモデル名（gpt-4, anthropic/claude-3.7-sonnetなど）

### ボットの名前認識
- `bot_name`: ボットの主要名（デフォルト: "AI_Agent"）
- `bot_name_aliases`: ボットの別名のリスト（デフォルト: ["AIエージェント", "エージェント", "AI", "ボット"]）

### プロンプト設定
- `default_prompt`: デフォルトのプロンプトテンプレート
- `channel_prompts`: チャンネルごとのカスタムプロンプト設定

## プロンプトのカスタマイズ

プロンプトには以下のプレースホルダーを使用できます：

- `{history}`: 会話の履歴
- `{input}`: 最新のユーザーメッセージ

例：
```
あなたは雑談して話を盛り上げるAIアシスタントです。

会話履歴:
{history}
最新のメッセージ: {input}
応答:
```

