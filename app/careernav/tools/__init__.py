"""Career Tools 套件

- logic.py：純業務邏輯（不依賴 strands，可獨立測試）
- career_tools.py：以 @tool 封裝 logic，供 AgentCore Runtime 使用
- data_loader.py / formula.py / profile.py：支援模組

注意：本 __init__ 刻意不 import career_tools，避免在沒有 strands 的
環境（如單元測試）匯入整個套件時失敗。需要工具註冊表時，請直接
`from tools.career_tools import TOOL_REGISTRY`。
"""
