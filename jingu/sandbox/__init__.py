"""Ephemeral sandbox workflow for AI chat."""

__all__ = ["AiSandboxChatSession", "AiSandboxRunner"]


def __getattr__(name: str):
    if name in __all__:
        from jingu.sandbox.runner import AiSandboxChatSession, AiSandboxRunner

        exports = {
            "AiSandboxChatSession": AiSandboxChatSession,
            "AiSandboxRunner": AiSandboxRunner,
        }
        return exports[name]
    raise AttributeError(name)
