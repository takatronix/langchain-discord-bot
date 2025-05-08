#!/bin/bash
source venv/bin/activate

# 現在のディレクトリをスクリプトのディレクトリに変更
cd "$(dirname "$0")"

# 仮想環境のアクティベート（存在する場合）
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# 既存のボットプロセスを終了
echo "既存のボットプロセスを確認しています..."
PIDS=$(ps aux | grep python | grep -E "bot\.py|debug_bot\.py" | grep -v grep | awk '{print $2}')

if [ -n "$PIDS" ]; then
  echo "既存のボットプロセスを終了します: $PIDS"
  kill $PIDS
  sleep 2
  
  # 強制終了が必要な場合
  REMAINING=$(ps aux | grep python | grep -E "bot\.py|debug_bot\.py" | grep -v grep | awk '{print $2}')
  if [ -n "$REMAINING" ]; then
    echo "強制終了します: $REMAINING"
    kill -9 $REMAINING
  fi
else
  echo "実行中のボットプロセスはありません"
fi

# ロックファイルがあれば削除
if [ -f "bot.lock" ]; then
  echo "古いロックファイルを削除します"
  rm bot.lock
fi

# モード選択
echo "起動モードを選択してください:"
echo "1) 通常モード (bot.py)"
echo "2) デバッグモード - 音声機能無効 (debug_bot.py)"
read -p "選択 (1-2): " choice

case $choice in
  1|"1")
    echo "通常モードで起動します..."
    python bot.py
    ;;
  2|"2"|"２")
    echo "デバッグモードで起動します..."
    python debug_bot.py
    ;;
  *)
    echo "無効な選択です: '$choice'。デバッグモードで起動します..."
    python debug_bot.py
    ;;
esac