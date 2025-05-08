# Discord.pyの音声機能を無効化するパッチ

import sys
import types

# 音声機能関連のモジュールをモックする
class MockModule(types.ModuleType):
    def __getattr__(self, attr):
        return MockObject()

class MockObject:
    def __init__(self, *args, **kwargs):
        pass
    
    def __call__(self, *args, **kwargs):
        return self
    
    def __getattr__(self, attr):
        return self

# audioopモジュールをモックする
sys.modules['audioop'] = MockModule('audioop')

print("音声機能を無効化しました")