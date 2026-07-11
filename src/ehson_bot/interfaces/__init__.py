"""Interface layer: driving adapters that trigger use cases.

Telegram (aiogram) lives here. It is a thin translation layer: parse an
incoming message into a use-case input DTO, call the use case, format the
result back into a Telegram reply. No business rule is decided here.
"""
