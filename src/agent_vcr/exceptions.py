"""Exception classes for AgentVCR."""


class AgentVCRError(Exception):
    """Base exception for all agent-vcr errors."""
    pass


class CassetteNotFoundError(AgentVCRError):
    """Raised when record_mode is 'none' and the cassette file does not exist."""
    pass


class CannotOverwriteExistingCassetteError(AgentVCRError):
    """Raised when attempting to record in replay-only mode or overwrite without permission."""
    pass


class UnhandledInteractionError(AgentVCRError):
    """Raised when an interaction has no recorded match in replay-only mode."""
    def __init__(self, interaction_info: str):
        super().__init__(
            f"No recorded cassette interaction matched the incoming call: {interaction_info}. "
            "To record new interactions, set record_mode to 'once' or 'new_episodes'."
        )
